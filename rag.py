"""
rag.py — RAG (búsqueda semántica + respuesta con citas) sobre transcripts.db

Piezas:
  · chunks:        troceado del texto de cada transcripción (~900 caracteres).
  · embeddings:    multilingüe local (fastembed / ONNX, MiniLM-L12-v2, 384 dims).
  · chunk_vec:     vectores float32 en el MISMO transcripts.db (BLOB).
  · search():      coseno en numpy (top-k), sin ANN ni servicio externo.
  · answer():      pasajes numerados + DeepSeek (API compatible OpenAI).

Uso CLI:
    python rag.py index [--reindex]
    python rag.py search "consulta" [-k 6]
    python rag.py ask "pregunta" [-k 6] [--no-llm]
    python rag.py stats

La UI (BuscadorYT.py) importa search/answer/index_pending desde aquí.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import requests

# Misma resolución que BuscadorYT.py: junto al script o junto al ejecutable empaquetado.
# La UI puede fijar la base activa con TRANSCRIP_DB_FILE (bases con nombre:
# costura.db, cocina.db…); TRANSCRIP_DB se mantiene por compatibilidad (carpeta).
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = (os.environ.get("TRANSCRIP_DB_FILE")
           or os.path.join(os.environ.get("TRANSCRIP_DB") or BASE_DIR, "transcripts.db"))

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
CHUNK_SIZE = 900          # caracteres por fragmento
CHUNK_OVERLAP = 120       # solape entre fragmentos consecutivos
DEFAULT_K = 6

CONFIG_PATH = os.path.join(BASE_DIR, "rag_config.json")

DEFAULT_LLM = {
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "api_key_env": "DEEPSEEK_API_KEY",
    "temperature": 0.2,
    "max_tokens": 900,
}


class RagError(RuntimeError):
    pass


# ─────────────────────────────────────────────
# CONEXIÓN Y ESQUEMA
# ─────────────────────────────────────────────
def get_conn(path: str | None = None) -> sqlite3.Connection:
    """Conexión a la base activa.

    `path` se resuelve en cada llamada (no como valor por defecto, que quedaría
    congelado al importar) para que la UI pueda cambiar de base de datos
    reasignando `rag.DB_PATH`.
    """
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id    TEXT    NOT NULL,
            ord         INTEGER NOT NULL,
            text        TEXT    NOT NULL,
            start_char  INTEGER,
            end_char    INTEGER,
            UNIQUE (video_id, ord)
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_video ON chunks (video_id);

        CREATE TABLE IF NOT EXISTS chunk_vec (
            chunk_id    INTEGER PRIMARY KEY REFERENCES chunks (id) ON DELETE CASCADE,
            dim         INTEGER NOT NULL,
            model       TEXT    NOT NULL,
            vec         BLOB    NOT NULL
        );

        /* hash del contenido indexado por vídeo: permite re-indexar solo lo cambiado */
        CREATE TABLE IF NOT EXISTS rag_meta (
            video_id    TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            model       TEXT NOT NULL,
            updated_at  TEXT
        );
        """
    )
    conn.commit()


# ─────────────────────────────────────────────
# TROCEADO (con offsets exactos para citar)
# ─────────────────────────────────────────────
def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Spans (start, end) de frases en el texto, conservando el original."""
    import re

    spans: list[tuple[int, int]] = []

    def in_paragraph(start: int, end: int) -> None:
        cursor = start
        for m in re.finditer(r"(?<=[.!?…])\s+", text[start:end]):
            spans.append((cursor, start + m.start()))
            cursor = start + m.end()
        if cursor < end:
            spans.append((cursor, end))

    para_start = 0
    for m in re.finditer(r"\n{2,}", text):
        in_paragraph(para_start, m.start())
        para_start = m.end()
    in_paragraph(para_start, len(text))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def chunk_spans(text: str, size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[tuple[str, int, int]]:
    """Agrupa frases en fragmentos de ~size caracteres con solape de ~overlap.

    Devuelve (texto, start, end) donde texto == text[start:end] exactamente,
    para que la cita pueda resaltarse en el visor.
    """
    spans = _sentence_spans(text)
    chunks: list[tuple[str, int, int]] = []
    cur: list[tuple[int, int]] = []

    for start, end in spans:
        if cur and (end - cur[0][0]) > size:
            chunks.append((text[cur[0][0]:cur[-1][1]], cur[0][0], cur[-1][1]))
            # conservamos el final como solape para no cortar ideas
            while len(cur) > 1 and (cur[-1][1] - cur[1][0]) > overlap:
                cur.pop(0)
        cur.append((start, end))
    if cur:
        chunks.append((text[cur[0][0]:cur[-1][1]], cur[0][0], cur[-1][1]))
    return chunks


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    return [c for c, _, _ in chunk_spans(text, size, overlap)]


# ─────────────────────────────────────────────
# EMBEDDINGS (fastembed, ONNX, lazy)
# ─────────────────────────────────────────────
_embedder = None


def get_embedder():
    """Carga perezosa del modelo; solo se descarga en el primer indexado.

    El caché se fija junto a la app (models/) en vez del directorio temporal
    por defecto de fastembed, que se vacía al reiniciar y forzaría a
    descargar ~240 MB cada vez.
    """
    global _embedder
    if _embedder is None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover
            raise RagError(
                "Falta fastembed. Instálalo con:  pip install fastembed"
            ) from exc
        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH") or os.path.join(BASE_DIR, "models")
        _embedder = TextEmbedding(model_name=MODEL_NAME, cache_dir=cache_dir)
    return _embedder


def _iter_embeddings(texts: list[str], kind: str = "passage") -> np.ndarray:
    """kind='passage' para indexar, 'query' para preguntar (e5 usa prefijos)."""
    emb = get_embedder()
    method = getattr(emb, f"{kind}_embed", None)
    if method is None:  # versiones antiguas de fastembed
        prefix = "passage: " if kind == "passage" else "query: "
        method = lambda xs: emb.embed([prefix + x for x in xs])  # noqa: E731
    vecs = np.asarray(list(method(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-12)


def embed_texts(texts: list[str]) -> np.ndarray:
    return _iter_embeddings(texts, "passage")


# ─────────────────────────────────────────────
# INDEXADO
# ─────────────────────────────────────────────
def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _index_one(conn: sqlite3.Connection, video_id: str, title: str, content: str) -> tuple[str, list[str]]:
    """Devuelve (estado, fragmentos): estado en {'nuevo', 'cambiado', 'ok'}."""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT content_hash, model FROM rag_meta WHERE video_id = ?", (video_id,)
    ).fetchone()
    h = _hash(content)
    if row and row["content_hash"] == h and row["model"] == MODEL_NAME:
        return "ok", []
    state = "cambiado" if row else "nuevo"
    conn.execute("DELETE FROM chunk_vec WHERE chunk_id IN (SELECT id FROM chunks WHERE video_id = ?)", (video_id,))
    conn.execute("DELETE FROM chunks WHERE video_id = ?", (video_id,))

    pieces = chunk_spans(content)
    # el título ayuda a desambiguar pasajes de temas parecidos
    corpus = [f"Vídeo: {title}\n{p}" for p, _, _ in pieces]
    vecs = embed_texts(corpus) if corpus else np.zeros((0, DIM), dtype=np.float32)

    for i, ((piece, start, end), vec) in enumerate(zip(pieces, vecs)):
        cur = conn.execute(
            "INSERT INTO chunks (video_id, ord, text, start_char, end_char) VALUES (?,?,?,?,?)",
            (video_id, i, piece, start, end),
        )
        conn.execute(
            "INSERT INTO chunk_vec (chunk_id, dim, model, vec) VALUES (?,?,?,?)",
            (cur.lastrowid, int(vec.shape[0]), MODEL_NAME, vec.astype(np.float32).tobytes()),
        )
    conn.execute(
        """INSERT INTO rag_meta (video_id, content_hash, model, updated_at)
           VALUES (?,?,?,datetime('now'))
           ON CONFLICT(video_id) DO UPDATE SET
             content_hash=excluded.content_hash, model=excluded.model, updated_at=excluded.updated_at""",
        (video_id, h, MODEL_NAME),
    )
    conn.commit()
    return state, [p for p, _, _ in pieces]


def index_pending(conn: sqlite3.Connection | None = None, reindex: bool = False,
                  progress=None, only_video_ids: Iterable[str] | None = None) -> dict:
    """Indexa transcripciones nuevas o modificadas. Devuelve un resumen."""
    own = conn is None
    conn = conn or get_conn()
    try:
        ensure_schema(conn)
        if reindex:
            conn.execute("DELETE FROM chunk_vec")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM rag_meta")
            conn.commit()
        rows = conn.execute(
            "SELECT video_id, title, content FROM transcripts WHERE content IS NOT NULL AND length(content) > 0"
        ).fetchall()
        if only_video_ids is not None:
            wanted = set(only_video_ids)
            rows = [r for r in rows if r["video_id"] in wanted]

        summary = {"nuevos": 0, "cambiados": 0, "sin_cambios": 0, "fragmentos": 0, "videos": len(rows)}
        for i, r in enumerate(rows, 1):
            state, pieces = _index_one(conn, r["video_id"], r["title"] or "", r["content"])
            summary[{"nuevo": "nuevos", "cambiado": "cambiados", "ok": "sin_cambios"}[state]] += 1
            summary["fragmentos"] += len(pieces)
            if progress:
                progress(i, len(rows), r["video_id"], state)
        return summary
    finally:
        if own:
            conn.close()


def delete_video_index(conn: sqlite3.Connection, video_id: str) -> None:
    conn.execute("DELETE FROM chunk_vec WHERE chunk_id IN (SELECT id FROM chunks WHERE video_id = ?)", (video_id,))
    conn.execute("DELETE FROM chunks WHERE video_id = ?", (video_id,))
    conn.execute("DELETE FROM rag_meta WHERE video_id = ?", (video_id,))
    conn.commit()


def index_stats(conn: sqlite3.Connection | None = None) -> dict:
    own = conn is None
    conn = conn or get_conn()
    try:
        ensure_schema(conn)
        n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        n_vecs = conn.execute("SELECT COUNT(*) FROM chunk_vec").fetchone()[0]
        n_videos = conn.execute("SELECT COUNT(DISTINCT video_id) FROM chunks").fetchone()[0]
        n_total = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        return {
            "videos_indexados": n_videos,
            "videos_totales": n_total,
            "fragmentos": n_chunks,
            "vectores": n_vecs,
            "modelo": MODEL_NAME,
            "dim": DIM,
        }
    finally:
        if own:
            conn.close()


# ─────────────────────────────────────────────
# BÚSQUEDA
# ─────────────────────────────────────────────
@dataclass
class Hit:
    score: float
    video_id: str
    title: str
    url: str
    ord: int
    text: str
    start_char: int
    end_char: int


def _load_matrix(conn: sqlite3.Connection) -> tuple[np.ndarray, list[sqlite3.Row]]:
    rows = conn.execute(
        """SELECT v.chunk_id, v.vec, c.video_id, c.ord, c.text, c.start_char, c.end_char,
                  t.title, t.url
           FROM chunk_vec v
           JOIN chunks c ON c.id = v.chunk_id
           JOIN transcripts t ON t.video_id = c.video_id"""
    ).fetchall()
    if not rows:
        return np.zeros((0, DIM), dtype=np.float32), []
    mat = np.vstack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])
    return mat, rows


def search(query: str, k: int = DEFAULT_K, conn: sqlite3.Connection | None = None) -> list[Hit]:
    own = conn is None
    conn = conn or get_conn()
    try:
        ensure_schema(conn)  # por si es una base recién creada (sin índice aún)
        mat, rows = _load_matrix(conn)
        if not rows:
            raise RagError("El índice está vacío. Ejecuta primero el indexado (python rag.py index).")
        q = _iter_embeddings([query], "query")[0]
        scores = mat @ q
        order = np.argsort(scores)[::-1][:k]
        return [
            Hit(
                score=float(scores[i]),
                video_id=rows[i]["video_id"],
                title=rows[i]["title"] or "",
                url=rows[i]["url"] or "",
                ord=int(rows[i]["ord"]),
                text=rows[i]["text"],
                start_char=int(rows[i]["start_char"] or 0),
                end_char=int(rows[i]["end_char"] or 0),
            )
            for i in order
            if scores[i] > 0
        ]
    finally:
        if own:
            conn.close()


# ─────────────────────────────────────────────
# RESPUESTA (LLM)
# ─────────────────────────────────────────────
def load_config() -> dict:
    cfg = dict(DEFAULT_LLM)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(**kwargs) -> None:
    cfg = load_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def _is_local_base_url(base_url: str) -> bool:
    """True para servidores en el propio equipo (Ollama, LM Studio, llama.cpp)."""
    host = (base_url or "").lower()
    return any(h in host for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))


def api_key(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    key = os.environ.get(cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "") or cfg.get("api_key", "")
    if not key and _is_local_base_url(cfg.get("base_url", "")):
        return "local"  # los servidores locales no comprueban la clave
    return key


SYSTEM_PROMPT = (
    "Eres un asistente que responde preguntas sobre transcripciones de vídeos de YouTube. "
    "Usa EXCLUSIVAMENTE los pasajes numerados que recibes como contexto. "
    "Si el contexto no basta para responder, dilo claramente y señala qué información falta; "
    "no inventes datos ni completes con conocimiento externo. "
    "Responde en el idioma de la pregunta, de forma clara y concisa (máximo ~250 palabras). "
    "Cita las fuentes con una marca por fuente, al final de cada afirmación que las use: "
    "por ejemplo [1] o [2][3] (no agrupes números dentro de unos mismos corchetes)."
)


def build_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(
            f"[{i}] Vídeo: {h.title}\n"
            f"URL: {h.url}\n"
            f"Fragmento: {h.text}"
        )
    return "\n\n".join(blocks)


def answer(question: str, k: int = DEFAULT_K, cfg: dict | None = None,
           hits: list[Hit] | None = None) -> dict:
    """Devuelve {'respuesta': str, 'hits': [...], 'modelo': str}."""
    cfg = cfg or load_config()
    hits = hits if hits is not None else search(question, k=k)
    key = api_key(cfg)
    if not key:
        raise RagError(
            "No hay API key configurada. Define la variable DEEPSEEK_API_KEY "
            "o guárdala con save_config(api_key=...)."
        )
    payload = {
        "model": cfg.get("model", DEFAULT_LLM["model"]),
        "temperature": cfg.get("temperature", 0.2),
        "max_tokens": cfg.get("max_tokens", 900),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexto:\n\n{build_context(hits)}\n\nPregunta: {question}"},
        ],
    }
    resp = requests.post(
        cfg.get("base_url", DEFAULT_LLM["base_url"]).rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if resp.status_code != 200:
        raise RagError(f"Error del LLM ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()
    return {"respuesta": text, "hits": hits, "modelo": payload["model"]}


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def _print_hits(hits: list[Hit]) -> None:
    for i, h in enumerate(hits, 1):
        snippet = h.text[:260].replace("\n", " ")
        print(f"[{i}] {h.score:.3f}  {h.title}  (frag. {h.ord})\n    {snippet}…\n")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "index":
        reindex = "--reindex" in args
        def progress(i, n, vid, state):
            print(f"  [{i}/{n}] {vid}: {state}", flush=True)
        summary = index_pending(reindex=reindex, progress=progress)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if cmd == "stats":
        print(json.dumps(index_stats(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("search", "ask"):
        k = DEFAULT_K
        if "-k" in args:
            k = int(args[args.index("-k") + 1])
            del args[args.index("-k"):args.index("-k") + 2]
        query = " ".join(args).strip()
        if not query:
            print("Falta la consulta")
            return 2
        hits = search(query, k=k)
        _print_hits(hits)
        if cmd == "ask":
            if "--no-llm" in args:
                return 0
            try:
                out = answer(query, k=k, hits=hits)
            except (RagError, requests.RequestException) as exc:
                print(f"\nNo se pudo generar la respuesta: {exc}")
                return 1
            print("\n" + out["respuesta"])
        return 0
    print(f"Comando desconocido: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
