"""RAG ligero para Android: BM25 local + redacción opcional vía API.

Sustituye a `rag.py` en la APK. El original usa fastembed/ONNX (no disponible
en Android); este mantiene la MISMA API que consume BuscadorYT.py:

    index_pending(...), index_stats(), search(...), answer(...), RagError, Hit

La recuperación es BM25 sobre los fragmentos de `transcripts.db` (sin vectores
ni descargas de modelos). La redacción reutiliza `rag_config.json` y cualquier
API compatible con OpenAI a través de `requests` (ya empaquetado en la APK).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import unicodedata
from collections import Counter
from dataclasses import dataclass

MODEL_NAME = "bm25-es"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
DEFAULT_K = 6

# Parámetros BM25 habituales para textos cortos/medios.
K1 = 1.5
B = 0.75

# main.py los ajusta a las rutas reales de la app (directorio privado de Android).
DB_PATH = (os.environ.get("TRANSCRIP_DB_FILE")
           or os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripts.db"))
CONFIG_PATH = os.path.join(os.path.dirname(DB_PATH), "rag_config.json")

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
# BASE DE DATOS
# ─────────────────────────────────────────────
def get_conn(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, timeout=30)
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
# TROCEADO (mismo criterio que rag.py, sin embeddings)
# ─────────────────────────────────────────────
def _sentence_spans(text: str) -> list[tuple[int, int]]:
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
    spans = _sentence_spans(text)
    chunks: list[tuple[str, int, int]] = []
    cur: list[tuple[int, int]] = []

    for start, end in spans:
        if cur and (end - cur[0][0]) > size:
            chunks.append((text[cur[0][0]:cur[-1][1]], cur[0][0], cur[-1][1]))
            while len(cur) > 1 and (cur[-1][1] - cur[1][0]) > overlap:
                cur.pop(0)
        cur.append((start, end))
    if cur:
        chunks.append((text[cur[0][0]:cur[-1][1]], cur[0][0], cur[-1][1]))
    return chunks


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    return [c for c, _, _ in chunk_spans(text, size, overlap)]


# ─────────────────────────────────────────────
# TOKENIZACIÓN Y BM25
# ─────────────────────────────────────────────
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _fold(text: str) -> str:
    """Minúsculas y sin acentos: «transcripción» y «transcripcion» coinciden."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(_fold(text))


def _hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def _delete_video_chunks(conn: sqlite3.Connection, video_id: str) -> None:
    try:  # una base indexada en escritorio puede tener también vectores
        conn.execute(
            "DELETE FROM chunk_vec WHERE chunk_id IN "
            "(SELECT id FROM chunks WHERE video_id = ?)", (video_id,))
    except sqlite3.OperationalError:
        pass
    conn.execute("DELETE FROM chunks WHERE video_id = ?", (video_id,))


# ─────────────────────────────────────────────
# INDEXADO
# ─────────────────────────────────────────────
_index_lock = threading.Lock()


def _index_one(conn: sqlite3.Connection, video_id: str, title: str,
               content: str) -> tuple[str, list[str]]:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT content_hash, model FROM rag_meta WHERE video_id = ?", (video_id,)
    ).fetchone()
    digest = _hash(content)
    if row and row["content_hash"] == digest and row["model"] == MODEL_NAME:
        return "ok", []

    state = "cambiado" if row else "nuevo"
    _delete_video_chunks(conn, video_id)
    pieces = chunk_spans(content)
    for i, (piece, start, end) in enumerate(pieces):
        conn.execute(
            "INSERT INTO chunks (video_id, ord, text, start_char, end_char) "
            "VALUES (?, ?, ?, ?, ?)",
            (video_id, i, piece, start, end),
        )
    conn.execute(
        """INSERT INTO rag_meta (video_id, content_hash, model, updated_at)
           VALUES (?, ?, ?, datetime('now'))
           ON CONFLICT(video_id) DO UPDATE SET
             content_hash=excluded.content_hash,
             model=excluded.model,
             updated_at=excluded.updated_at""",
        (video_id, digest, MODEL_NAME),
    )
    conn.commit()
    return state, [p for p, _, _ in pieces]


def index_pending(conn: sqlite3.Connection | None = None, reindex: bool = False,
                  progress=None, only_video_ids=None) -> dict:
    own = conn is None
    conn = conn or get_conn()
    try:
        with _index_lock:
            ensure_schema(conn)
            if reindex:
                try:
                    conn.execute("DELETE FROM chunk_vec")
                except sqlite3.OperationalError:
                    pass
                conn.execute("DELETE FROM chunks")
                conn.execute("DELETE FROM rag_meta")
                conn.commit()

            rows = conn.execute(
                "SELECT video_id, title, content FROM transcripts "
                "WHERE content IS NOT NULL AND length(content) > 0"
            ).fetchall()
            if only_video_ids is not None:
                wanted = set(only_video_ids)
                rows = [r for r in rows if r["video_id"] in wanted]

            summary = {"nuevos": 0, "cambiados": 0, "sin_cambios": 0,
                       "fragmentos": 0, "videos": len(rows)}
            for i, r in enumerate(rows, 1):
                state, pieces = _index_one(
                    conn, r["video_id"], r["title"] or "", r["content"])
                summary[{"nuevo": "nuevos", "cambiado": "cambiados",
                         "ok": "sin_cambios"}[state]] += 1
                summary["fragmentos"] += len(pieces)
                if progress:
                    progress(i, len(rows), r["video_id"], state)
            return summary
    finally:
        if own:
            conn.close()


def delete_video_index(conn: sqlite3.Connection, video_id: str) -> None:
    _delete_video_chunks(conn, video_id)
    conn.execute("DELETE FROM rag_meta WHERE video_id = ?", (video_id,))
    conn.commit()


def index_stats(conn: sqlite3.Connection | None = None) -> dict:
    own = conn is None
    conn = conn or get_conn()
    try:
        ensure_schema(conn)
        n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        n_videos = conn.execute(
            "SELECT COUNT(DISTINCT video_id) FROM chunks").fetchone()[0]
        n_total = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        return {
            "videos_indexados": n_videos,
            "videos_totales": n_total,
            "fragmentos": n_chunks,
            "vectores": 0,
            "modelo": MODEL_NAME,
            "dim": 0,
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


_index_cache: dict = {"key": None, "docs": None, "df": None, "avgdl": 1.0}
_cache_lock = threading.Lock()


def _cache_key(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(MAX(id), 0) FROM chunks").fetchone()
    return (DB_PATH, int(row[0]), int(row[1]))


def _load_index(conn: sqlite3.Connection):
    """Construye (y cachea) el índice BM25 en memoria para la base activa."""
    key = _cache_key(conn)
    with _cache_lock:
        if _index_cache["key"] == key and _index_cache["docs"] is not None:
            return _index_cache["docs"], _index_cache["df"], _index_cache["avgdl"]

        rows = conn.execute(
            """SELECT c.id, c.video_id, c.ord, c.text, c.start_char, c.end_char,
                      t.title, t.url
               FROM chunks c
               JOIN transcripts t ON t.video_id = c.video_id
               ORDER BY c.id"""
        ).fetchall()

        docs = []
        df: Counter = Counter()
        total_len = 0
        for r in rows:
            # El título pesa el doble: ayuda a desambiguar temas parecidos.
            tokens = tokenize(r["title"] or "") * 2 + tokenize(r["text"])
            tf = Counter(tokens)
            dl = sum(tf.values()) or 1
            docs.append((r, tf, dl))
            total_len += dl
            for term in tf:
                df[term] += 1

        avgdl = (total_len / len(docs)) if docs else 1.0
        _index_cache.update(key=key, docs=docs, df=df, avgdl=avgdl)
        return docs, df, avgdl


def search(query: str, k: int = DEFAULT_K,
           conn: sqlite3.Connection | None = None) -> list[Hit]:
    own = conn is None
    conn = conn or get_conn()
    try:
        ensure_schema(conn)
        if conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0:
            # Primera pregunta sin pulsar «Indexar»: se indexa aquí mismo
            # (el worker ya corre en un hilo aparte).
            index_pending(conn=conn)

        docs, df, avgdl = _load_index(conn)
        terms = list(dict.fromkeys(tokenize(query)))
        if not docs:
            raise RagError(
                "No hay transcripciones indexadas. Descarga alguna y pulsa «Indexar».")
        if not terms:
            return []

        n_docs = len(docs)
        idf = {}
        for term in terms:
            d = df.get(term, 0)
            idf[term] = math.log(1.0 + (n_docs - d + 0.5) / (d + 0.5)) if d else 0.0

        scored = []
        for row, tf, dl in docs:
            score = 0.0
            norm = K1 * (1.0 - B + B * dl / avgdl)
            for term in terms:
                f = tf.get(term)
                if not f:
                    continue
                score += idf[term] * (f * (K1 + 1.0)) / (f + norm)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:k]
        best = top[0][0] if top else 1.0
        return [
            Hit(
                score=float(score / best),
                video_id=row["video_id"],
                title=row["title"] or "",
                url=row["url"] or "",
                ord=int(row["ord"]),
                text=row["text"],
                start_char=int(row["start_char"] or 0),
                end_char=int(row["end_char"] or 0),
            )
            for score, row in top
        ]
    finally:
        if own:
            conn.close()


# ─────────────────────────────────────────────
# REDACCIÓN (API compatible OpenAI)
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
    host = (base_url or "").lower()
    return any(h in host for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))


def api_key(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    key = (os.environ.get(cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "")
           or cfg.get("api_key", ""))
    if not key and _is_local_base_url(cfg.get("base_url", "")):
        return "local"
    return key


SYSTEM_PROMPT = (
    "Eres un asistente que responde preguntas sobre transcripciones de vídeos de YouTube. "
    "Usa EXCLUSIVAMENTE los pasajes numerados que recibes como contexto. "
    "Si el contexto no basta para responder, dilo claramente y señala qué información falta; "
    "no inventes datos ni completes con conocimiento externo. "
    "Responde en el idioma de la pregunta, de forma clara y concisa (máximo ~250 palabras). "
    "Cita las fuentes con una marca por fuente, al final de cada afirmación que las use: "
    "por ejemplo [1] o [2][3]."
)


def build_context(hits: list[Hit]) -> str:
    return "\n\n".join(
        f"[{i}] Vídeo: {h.title}\nURL: {h.url}\nFragmento: {h.text}"
        for i, h in enumerate(hits, 1)
    )


def answer(question: str, k: int = DEFAULT_K, cfg: dict | None = None,
           hits: list[Hit] | None = None) -> dict:
    import requests  # empaquetado en vendor/

    cfg = cfg or load_config()
    hits = hits if hits is not None else search(question, k=k)
    if not hits:
        raise RagError("No hay pasajes relevantes para esa pregunta.")
    key = api_key(cfg)
    if not key:
        raise RagError(
            "No hay API key configurada. Añádela en «Ajustes» o elige el "
            "redactor «Sin redactor» para buscar sin IA.")

    payload = {
        "model": cfg.get("model", DEFAULT_LLM["model"]),
        "temperature": cfg.get("temperature", 0.2),
        "max_tokens": cfg.get("max_tokens", 900),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"Contexto:\n\n{build_context(hits)}\n\nPregunta: {question}"},
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
    text = resp.json()["choices"][0]["message"]["content"].strip()
    return {"respuesta": text, "hits": hits, "modelo": payload["model"]}
