"""
YouTube Transcript Downloader
App de escritorio macOS con PySide6 (Qt6) + SQLite
"""

import html
import importlib.util
import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime

import requests
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut, QTextCursor

from responsive import (
    FieldRow, FlowWidget, MODE_COMPACT, MODE_MEDIUM, MODE_WIDE,
    ResponsiveMixin, mode_for, space,
)

# --- Intento importar youtube_transcript_api ---
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    YT_API_AVAILABLE = True
except ImportError:
    YT_API_AVAILABLE = False


# ─────────────────────────────────────────────
# TEMA DARK MODERNO (QSS)
# ─────────────────────────────────────────────
QSS = """
* {
    font-size: 13px;
    color: #e8e8f0;
}

QMainWindow, QWidget {
    background-color: #15151d;
}

/* ── Cabecera ── */
QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#appSubtitle {
    font-size: 12px;
    color: #8b8b9e;
}
QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #9b9bae;
}

/* ── Campos de texto ── */
QLineEdit {
    background-color: #1e1e2a;
    border: 1px solid #2e2e3e;
    border-radius: 8px;
    padding: 10px 12px;
    color: #f0f0f6;
    selection-background-color: #6c5ce7;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border: 1px solid #6c5ce7;
    background-color: #20202e;
}
QLineEdit::placeholder {
    color: #5c5c70;
}

/* ── Selectores (combo y numéricos) ── */
QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1e1e2a;
    border: 1px solid #2e2e3e;
    border-radius: 8px;
    padding: 6px 10px;
    color: #f0f0f6;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #3e3e52;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #6c5ce7;
}
QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: #565665;
    background-color: #1f1f28;
    border-color: #26262f;
}
/* Campo de texto interno de un desplegable editable */
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0;
    color: #f0f0f6;
}
/* El desplegable es una ventana aparte: se estiliza por separado */
QComboBox QAbstractItemView {
    background-color: #20202e;
    border: 1px solid #2e2e3e;
    color: #e8e8f0;
    selection-background-color: #6c5ce7;
    selection-color: #ffffff;
    outline: none;
}
QScrollArea {
    border: none;
    background: transparent;
}

/* ── Botones ──
   Una sola métrica para todos: misma altura, mismo radio y misma tipografía.
   La jerarquía la marca el color (#primary / #danger / neutro), no el tamaño. */
QPushButton {
    background-color: #262633;
    border: 1px solid #34343f;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 20px;
    color: #e8e8f0;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2e2e3c;
    border-color: #3e3e4c;
}
QPushButton:pressed {
    background-color: #222230;
}
QPushButton:disabled {
    color: #565665;
    background-color: #1f1f28;
    border-color: #26262f;
}

/* Botones compactos del tamaño de letra (lector): misma altura, más estrechos */
QPushButton#fontBtn {
    padding: 8px 10px;
    min-width: 14px;
    font-size: 13px;
    font-weight: 600;
    color: #b9b9c8;
}
QPushButton#fontBtn:hover {
    color: #ffffff;
    border-color: #6c5ce7;
}
QPushButton#fontBtn:checked {
    color: #ffffff;
    background-color: #6c5ce7;
    border-color: #6c5ce7;
}

/* Botón primario (acento) */
QPushButton#primary {
    background-color: #6c5ce7;
    border: 1px solid #6c5ce7;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primary:hover {
    background-color: #7c6cf0;
    border-color: #7c6cf0;
}
QPushButton#primary:pressed {
    background-color: #5c4cd0;
}

/* Botón peligro (eliminar) */
QPushButton#danger {
    background-color: transparent;
    border: 1px solid #4a2a2e;
    color: #ff6b7a;
}
QPushButton#danger:hover {
    background-color: #3a2228;
    border-color: #6b2f3a;
    color: #ff8592;
}

/* ── Radios (idioma) ── */
QRadioButton {
    spacing: 6px;
    color: #b9b9c8;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #3a3a4c;
    background-color: #1e1e2a;
}
QRadioButton::indicator:hover {
    border-color: #6c5ce7;
}
QRadioButton::indicator:checked {
    border: 2px solid #6c5ce7;
    background-color: #6c5ce7;
}
QRadioButton:checked {
    color: #ffffff;
}

/* ── Barra de progreso ── */
QProgressBar {
    background-color: #1e1e2a;
    border: 1px solid #2e2e3e;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #6c5ce7;
    border-radius: 5px;
}

/* ── Lista ── */
QListWidget {
    background-color: #1b1b25;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    margin: 2px 2px;
    border-radius: 8px;
    color: #cfcfdd;
}
QListWidget::item:hover {
    background-color: #262634;
}
QListWidget::item:selected {
    background-color: #3a3370;
    color: #ffffff;
}

/* ── Visor de texto / log ── */
QTextEdit {
    background-color: #1b1b25;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 6px;
    color: #d6d6e2;
    selection-background-color: #6c5ce7;
    selection-color: #ffffff;
}

/* ── Separador ── */
QFrame#divider {
    background-color: #262630;
    max-height: 1px;
    border: none;
}

/* ── Scrollbars finas ── */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #363646;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #464658;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #363646;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0px;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #15151d;
}
QSplitter::handle:hover {
    background-color: #262630;
}

/* ── Pestañas ── */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background-color: #1b1b25;
    color: #9b9bae;
    border: 1px solid #2a2a38;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 7px 18px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #262634;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    color: #e8e8f0;
}
QTextBrowser {
    background-color: #1b1b25;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 8px;
    color: #d6d6e2;
    selection-background-color: #6c5ce7;
    selection-color: #ffffff;
}
"""


def linkify_citations(text: str) -> str:
    """Convierte las citas [n] en enlaces internos clicables.

    Los modelos agrupan a veces varias fuentes: «[1, 4]». Esto enlaza cada
    número por separado para que todas las citas abran su pasaje.
    """
    def _repl(m):
        numeros = re.findall(r"\d+", m.group(1))
        return ", ".join(
            f'<a href="hit:{n}" style="color:#8f7bff">[{n}]</a>' for n in numeros)

    return re.sub(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]", _repl, text)


def read_font_qss(size_pt: int) -> str:
    """Regla que fija el tamaño de letra del visor de transcripciones.

    No sirve QTextEdit.setFont(): la regla global «* { font-size: 13px }» de la
    hoja de estilo vuelve a imponer su tamaño al pulir el widget. Una regla
    propia por objectName gana por especificidad (id > universal) y, al aplicar-
    la sobre el widget, solo se re-pule el visor (unos 13 ms en vez de ~70 ms de
    repulir toda la ventana).
    """
    return f"QTextEdit#transcriptView {{ font-size: {int(size_pt)}pt; }}"


# ─────────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────────
# En desarrollo la BD vive junto al script; en una app empaquetada con
# PyInstaller, junto al ejecutable (para que los datos persistan, ya que
# `__file__` dentro del empaquetado apunta a un directorio temporal).
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(APP_DIR, "transcripts.db")
UI_CONFIG_PATH = os.path.join(APP_DIR, "ui_config.json")

# Tamaño de letra del lector de transcripciones (en puntos)
READ_FONT_DEFAULT = 18
READ_FONT_MIN = 12
READ_FONT_MAX = 40


def load_ui_config() -> dict:
    """Preferencias de la interfaz (tamaño de letra del lector, etc.)."""
    cfg = {"read_font_size": READ_FONT_DEFAULT}
    if os.path.exists(UI_CONFIG_PATH):
        try:
            with open(UI_CONFIG_PATH, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if isinstance(saved, dict):
                cfg.update(saved)
        except (OSError, json.JSONDecodeError):
            pass
    try:
        cfg["read_font_size"] = max(READ_FONT_MIN,
                                    min(READ_FONT_MAX, int(cfg["read_font_size"])))
    except (TypeError, ValueError):
        cfg["read_font_size"] = READ_FONT_DEFAULT
    return cfg


def save_ui_config(**kwargs) -> None:
    cfg = load_ui_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        with open(UI_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass  # sin permiso de escritura: la app sigue funcionando igual


# ── Bases de datos con nombre ──
# La app trabaja sobre UNA base activa a la vez. Las bases viven junto a la
# app (sea el script o el ejecutable empaquetado) para que la carpeta siga
# siendo portable: costura.db, cocina.db, transcripts.db…
DB_NAME_DEFAULT = "transcripts"


def _sanitize_db_name(raw: str) -> str:
    """Convierte lo que escribe el usuario en un nombre de archivo seguro."""
    name = (raw or "").strip()
    if name.lower().endswith(".db"):
        name = name[:-3]
    # Letras, números, guion, guion_bajo y punto; el resto pasa a «_».
    name = re.sub(r"[^\w.-]+", "_", name, flags=re.UNICODE).strip("._- ")
    name = name[:60].strip("._- ")
    return name or DB_NAME_DEFAULT


def db_stem(path: str | None = None) -> str:
    """Nombre de la base activa sin extensión (títulos, nombre del cuaderno)."""
    return os.path.splitext(os.path.basename(path or DB_PATH))[0]


def db_path(name: str) -> str:
    """Ruta de `<name>.db` dentro de la carpeta de la app."""
    return os.path.join(APP_DIR, _sanitize_db_name(name) + ".db")


def set_active_db(path: str) -> None:
    """Cambia la base activa para toda la app (UI y rag.py)."""
    global DB_PATH
    DB_PATH = os.path.abspath(path)
    # rag.py puede importarse más tarde (import perezoso): le pasamos la base
    # activa por entorno para que lo haga ya apuntando a la correcta.
    os.environ["TRANSCRIP_DB_FILE"] = DB_PATH
    rag = sys.modules.get("rag")
    if rag is not None:  # si rag ya está importado, que use la nueva base
        rag.DB_PATH = DB_PATH


def db_initial_path() -> str:
    """Base activa según ui_config.json (transcripts.db si aún no hay ninguna)."""
    saved = os.path.basename(str(load_ui_config().get("db_name") or "").strip())
    if not saved:
        return db_path(DB_NAME_DEFAULT)
    if not saved.lower().endswith(".db"):
        saved += ".db"
    return os.path.join(APP_DIR, saved)


def _bases_disponibles() -> list[str]:
    """Nombres de las bases (*.db) que hay en la carpeta de la app."""
    try:
        return sorted(f for f in os.listdir(APP_DIR) if f.lower().endswith(".db"))
    except OSError:
        return []


# ─────────────────────────────────────────────
# REDACCIÓN CON IA (LLM) — parámetro del proyecto
# ─────────────────────────────────────────────
# La tab «Ajustes» se construye a partir de esta tabla: añadir un proveedor
# es añadir una fila. `needs_key` solo afecta a la interfaz (Ollama y LM Studio
# ignoran la clave). Toda elección se guarda en rag_config.json, que es el mismo
# archivo que lee rag.py para redactar la respuesta.
LLM_PROVIDERS = {
    "none": {
        "label": "Sin IA · solo pasajes",
        "base_url": "",
        "model": "",
        "needs_key": False,
        "hint": "No sale nada de tu equipo: «Preguntar» enseña los pasajes más "
                "relevantes y tú los abres en la transcripción.",
    },
    "deepseek": {
        "label": "DeepSeek · nube",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "needs_key": True,
        "hint": "API compatible con OpenAI. Solo se envían tu pregunta y los ~6 "
                "pasajes recuperados. Clave en platform.deepseek.com.",
    },
    "ollama": {
        "label": "Ollama · local",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b-instruct",
        "needs_key": False,
        "hint": "Todo en tu equipo: instala Ollama, «ollama pull qwen2.5:7b-instruct» "
                "y deja «ollama serve» en marcha. No necesita clave.",
    },
    "custom": {
        "label": "Otro compatible con OpenAI",
        "base_url": "",
        "model": "",
        "needs_key": True,
        "hint": "LM Studio, llama.cpp, Groq, OpenRouter… pega la dirección "
                "(termina en /v1) y el modelo de ese servicio.",
    },
}

RAG_CONFIG_PATH = os.path.join(APP_DIR, "rag_config.json")

# Modelo de búsqueda (lo usa rag.py; se replican aquí para poder mostrarlo
# en Ajustes aunque fastembed no esté instalado).
RAG_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RAG_MODEL_DIM = 384
RAG_MODEL_LABEL = RAG_MODEL_NAME.split("/")[-1]

RAG_CONFIG_DEFAULT = {
    "provider": "deepseek",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "api_key_env": "DEEPSEEK_API_KEY",
    "api_key": "",
    "temperature": 0.2,
    "max_tokens": 900,
}


def load_rag_config() -> dict:
    """Preferencias de redacción; rag.py lee este mismo rag_config.json."""
    cfg = dict(RAG_CONFIG_DEFAULT)
    if os.path.exists(RAG_CONFIG_PATH):
        try:
            with open(RAG_CONFIG_PATH, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if isinstance(saved, dict):
                cfg.update(saved)
        except (OSError, json.JSONDecodeError):
            pass
    if cfg.get("provider") not in LLM_PROVIDERS:
        cfg["provider"] = RAG_CONFIG_DEFAULT["provider"]
    return cfg


def save_rag_config(**kwargs) -> None:
    cfg = load_rag_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    with open(RAG_CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id    TEXT    NOT NULL UNIQUE,
            title       TEXT,
            owner       TEXT,
            url         TEXT,
            language    TEXT,
            content     TEXT,
            created_at  TEXT
        )
    """)
    # Migración: añade la columna 'owner' a bases de datos ya existentes.
    cols = [r[1] for r in c.execute("PRAGMA table_info(transcripts)")]
    if "owner" not in cols:
        c.execute("ALTER TABLE transcripts ADD COLUMN owner TEXT")
    # Preguntas y respuestas guardadas para el «cuaderno» en PDF de cada base.
    c.execute("""
        CREATE TABLE IF NOT EXISTS qa_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT    NOT NULL,
            answer      TEXT    NOT NULL,
            sources     TEXT,
            provider    TEXT,
            model       TEXT,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_transcript(video_id, title, owner, url, language, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO transcripts (video_id, title, owner, url, language, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (video_id, title, owner, url, language, content, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()

def update_transcript(video_id, title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE transcripts SET title = ? WHERE video_id = ?
    """, (title, video_id))
    conn.commit()
    conn.close()

def get_all_transcripts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, video_id, language, owner, created_at FROM transcripts ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_transcript_content(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title, url, language, content, owner FROM transcripts WHERE video_id = ?", (video_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_transcript(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM transcripts WHERE video_id = ?", (video_id,))
    conn.commit()
    conn.close()

# ── Cuaderno de preguntas y respuestas (PDF) ──
def save_qa(question, answer, sources=None, provider="", model=""):
    """Añade una pregunta-respuesta al historial de la base activa."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO qa_log (question, answer, sources, provider, model, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (question, answer, json.dumps(sources or [], ensure_ascii=False),
             provider, model, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()

def get_qa_entries():
    """Historial de preguntas de la base activa, en orden de creación."""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, question, answer, sources, provider, model, created_at "
            "FROM qa_log ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0], "question": r[1], "answer": r[2],
            "sources": json.loads(r[3]) if r[3] else [],
            "provider": r[4], "model": r[5], "created_at": r[6],
        }
        for r in rows
    ]

def transcript_exists(video_id):
    """Devuelve True si ya tenemos esta transcripción guardada en la BD."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM transcripts WHERE video_id = ?", (video_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# ─────────────────────────────────────────────
# LÓGICA YOUTUBE
# ─────────────────────────────────────────────

def extract_video_id(url_or_id: str):
    """Extrae el video_id de una URL de YouTube o lo devuelve si ya es un ID."""
    patterns = [
        r"(?:[?&]v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$"
    ]
    for p in patterns:
        m = re.search(p, url_or_id.strip())
        if m:
            return m.group(1)
    return None

def video_url(video_id: str, stored_url: str | None = None) -> str:
    """URL del vídeo para abrirlo en el navegador, siempre utilizable.

    Se respeta la URL guardada si es válida; si falta o está roto (pasa con
    transcripciones importadas o bases de datos antiguas), se reconstruye desde
    el video_id, así el enlace nunca queda muerto.
    """
    url = (stored_url or "").strip()
    if re.match(r"^https?://\S+$", url):
        return url
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_video_meta(video_id: str) -> tuple[str, str]:
    """
    Obtiene (título, propietario) del vídeo con la API oEmbed de YouTube (sin clave).
    Devuelve (video_id, "") como respaldo si no se puede obtener.
    """
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        title = data.get("title", "").strip()
        owner = data.get("author_name", "").strip()
        return (title or video_id, owner)
    except Exception:
        return (video_id, "")

def fetch_transcript(video_id: str, lang: str = "es") -> tuple[str, str]:
    """
    Versión que usa el método fetch() de INSTANCIA (el único que funciona)
    """
    try:
        # Preparar idiomas
        if lang == "auto":
            langs = ["es", "en", "fr", "de", "it", "pt"]
        else:
            langs = [lang]

        # Crear instancia y usar fetch() - ¡ASÍ funciona!
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=langs, preserve_formatting=True)

        # Limpiar a texto plano legible (sin HTML, sin cortes, sin timestamps)
        text = clean_transcript_text(transcript)

        # Determinar idioma usado (esto es lo más complicado)
        # Por defecto devolvemos el solicitado
        lang_used = lang if lang != "auto" else "es"

        return text, str(lang_used)

    except Exception as e:
        raise RuntimeError(f"Error al obtener transcripción: {e}")

def _piece_text(piece) -> str:
    """Devuelve el texto de un fragmento (objeto de la API o dict)."""
    if hasattr(piece, "text"):
        return getattr(piece, "text", "") or ""
    if isinstance(piece, dict):
        return piece.get("text", "") or ""
    return str(piece)


# Fin de frase: signo de puntuación (con posible comilla de cierre)
# seguido de espacio y mayúscula / cifra / comilla de apertura.
_SENTENCE_END = re.compile(r'([.!?…]["»”]?)\s+(?=[A-ZÁÉÍÓÚÑ¿¡"“«0-9])')

# Marcadores de sonido de los subtítulos automáticos: [música], [aplausos], [risas]…
_SOUND_TAG = re.compile(r"\[[^\]]{1,40}\]")


def clean_transcript_text(pieces) -> str:
    """
    Convierte los fragmentos de subtítulos en texto plano legible:
      · une los cortes a mitad de frase (los subtítulos no respetan la puntuación),
      · normaliza espacios y saltos de línea,
      · elimina marcadores de sonido tipo [música],
      · divide en párrafos por límites de frase.
    """
    texts = [t.strip() for t in (_piece_text(p) for p in pieces) if t and t.strip()]
    if not texts:
        return ""

    full = " ".join(texts)
    full = re.sub(r"\s+", " ", full).strip()
    full = _SOUND_TAG.sub(" ", full)
    full = re.sub(r"\s+", " ", full).strip()

    return "\n\n".join(_split_paragraphs(full))


def _split_sentences(text: str) -> list:
    """Parte el texto en frases conservando la puntuación final."""
    marked = _SENTENCE_END.sub(r"\1\n", text)
    return [p.strip() for p in marked.split("\n") if p.strip()]


def _split_paragraphs(text: str, sentences_per_para: int = 4, max_chars: int = 700) -> list:
    """Agrupa las frases en párrafos de tamaño legible."""
    paragraphs = []
    buffer = []
    buffer_len = 0

    for sentence in _split_sentences(text):
        buffer.append(sentence)
        buffer_len += len(sentence)
        if len(buffer) >= sentences_per_para or buffer_len >= max_chars:
            paragraphs.append(" ".join(buffer))
            buffer = []
            buffer_len = 0

    if buffer:
        paragraphs.append(" ".join(buffer))

    return paragraphs


# ─────────────────────────────────────────────
# EXPORTACIÓN A PDF
# ─────────────────────────────────────────────
def _pdf_canvas_numerado():
    """Canvas de reportlab que escribe «Página N de M» al pie de cada página.

    Se construye de forma perezosa (la clase necesita el módulo ya importado)
    y lo comparten el PDF de una transcripción y el cuaderno de preguntas.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    class _NumberedCanvas(pdf_canvas.Canvas):
        """Canvas que aplaza el cierre de página para poder escribir el total."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_states = []

        def showPage(self):
            self._page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._page_states)
            for state in self._page_states:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total):
            self.saveState()
            y = 12 * mm
            self.setStrokeColor(colors.HexColor('#D0D0D0'))
            self.setLineWidth(0.5)
            self.line(20 * mm, y + 4 * mm, A4[0] - 20 * mm, y + 4 * mm)
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.HexColor('#777777'))
            self.drawCentredString(A4[0] / 2.0, y, f'Página {self._pageNumber} de {total}')
            self.restoreState()

    return _NumberedCanvas


def _escribir_pdf(filepath, title, content, url, owner=""):
    """Genera el PDF de una transcripción con «Página N de M» al pie de cada página."""
    import html as html_module

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    author_style = ParagraphStyle(
        'Author', parent=styles['Normal'],
        fontSize=12, leading=16, alignment=TA_LEFT,
        textColor=colors.HexColor('#555555'), spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, leading=14, alignment=TA_LEFT,
        spaceAfter=6, fontName='Helvetica'
    )
    link_style = ParagraphStyle(
        'Link', parent=styles['Normal'],
        fontSize=8, leading=11, alignment=TA_LEFT,
        textColor=colors.HexColor('#1155CC'), spaceAfter=14,
    )

    story = []
    story.append(Paragraph(html_module.escape(title), title_style))
    story.append(Spacer(1, 4))
    if owner:
        story.append(Paragraph(html_module.escape(owner), author_style))
        story.append(Spacer(1, 4))
    story.append(Paragraph(f'<link href="{url}">{html_module.escape(url)}</link>', link_style))
    story.append(Spacer(1, 10))

    for line in content.splitlines():
        line = line.strip()
        if line:
            story.append(Paragraph(html_module.escape(line), body_style))

    doc.build(story, canvasmaker=_pdf_canvas_numerado())


def _escribir_cuaderno_pdf(filepath, db_title, entries):
    """Regenera el cuaderno completo de preguntas y respuestas de una base.

    Se reconstruye desde `qa_log` en cada guardado, así el PDF siempre refleja
    todas las preguntas (y no depende de ir parcheando páginas).
    """
    import html as html_module

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"Cuaderno de preguntas · {db_title}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CuadernoTitle', parent=styles['Title'],
        fontName='Helvetica-Bold', fontSize=20, leading=24, spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        'CuadernoMeta', parent=styles['Normal'], alignment=TA_LEFT,
        fontName='Helvetica', fontSize=9.5, leading=13,
        textColor=colors.HexColor('#666666'), spaceAfter=16,
    )
    question_style = ParagraphStyle(
        'CuadernoQuestion', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12.5, leading=16,
        textColor=colors.HexColor('#3b2f7a'),
        spaceBefore=14, spaceAfter=3,
    )
    date_style = ParagraphStyle(
        'CuadernoDate', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8.5, leading=11,
        textColor=colors.HexColor('#888888'), spaceAfter=7,
    )
    body_style = ParagraphStyle(
        'CuadernoBody', parent=styles['Normal'], alignment=TA_LEFT,
        fontName='Helvetica', fontSize=10, leading=14, spaceAfter=6,
    )
    sources_label = ParagraphStyle(
        'CuadernoSourcesLabel', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=11,
        textColor=colors.HexColor('#555555'), spaceBefore=8, spaceAfter=3,
    )
    source_style = ParagraphStyle(
        'CuadernoSources', parent=styles['Normal'], alignment=TA_LEFT,
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=colors.HexColor('#1155CC'), leftIndent=12, spaceAfter=2,
    )
    pasaje_style = ParagraphStyle(
        'CuadernoPasaje', parent=styles['Normal'], alignment=TA_LEFT,
        fontName='Helvetica-Oblique', fontSize=9, leading=12.5,
        textColor=colors.HexColor('#333333'), leftIndent=12, rightIndent=8,
        spaceBefore=1, spaceAfter=9,
    )

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    story = [
        Paragraph("Cuaderno de preguntas", title_style),
        Paragraph(
            f"Base de datos: <b>{html_module.escape(db_title)}</b> · "
            f"{len(entries)} pregunta(s) · actualizado el {fecha}", meta_style),
    ]

    for i, entry in enumerate(entries, 1):
        story.append(Paragraph(
            f"{i}. {html_module.escape(entry['question'])}", question_style))
        creado = (entry.get("created_at") or "").replace("T", " ")
        extras = [creado] if creado else []
        provider = entry.get("provider") or ""
        model = entry.get("model") or ""
        if provider or model:
            extras.append(" ".join(x for x in (provider, model) if x))
        if extras:
            story.append(Paragraph(
                html_module.escape(" · ".join(extras)), date_style))

        for parrafo in (entry.get("answer") or "").splitlines():
            parrafo = parrafo.strip()
            if parrafo:
                story.append(Paragraph(html_module.escape(parrafo), body_style))

        pasajes = entry.get("sources") or []
        if pasajes:
            story.append(Paragraph("Pasajes recuperados", sources_label))
            for j, fuente in enumerate(pasajes, 1):
                titulo = str(fuente.get("title") or fuente.get("video_id") or "")
                url = (fuente.get("url")
                       or f"https://www.youtube.com/watch?v={fuente.get('video_id', '')}")
                story.append(Paragraph(
                    f'[{j}] <link href="{html_module.escape(url, quote=True)}">'
                    f'{html_module.escape(titulo)}</link>', source_style))
                # El texto exacto del pasaje, igual que al pulsarlo en la app.
                texto_pasaje = (fuente.get("text") or "").strip()
                if texto_pasaje:
                    story.append(Paragraph(
                        f"«{html_module.escape(texto_pasaje)}»", pasaje_style))

    doc.build(story, canvasmaker=_pdf_canvas_numerado())


# ─────────────────────────────────────────────
# WORKER DE DESCARGA (hilo + señales Qt)
# ─────────────────────────────────────────────
class DownloadWorker(QtCore.QObject):
    """Ejecuta la descarga en un hilo aparte y notifica con señales Qt."""
    ok = QtCore.Signal(str, str, str, str, str)  # video_id, title, owner, lang_used, text
    err = QtCore.Signal(str)

    def __init__(self, video_id: str, lang: str):
        super().__init__()
        self.video_id = video_id
        self.lang = lang

    def run(self):
        try:
            text, lang_used = fetch_transcript(self.video_id, self.lang)
            url = f"https://youtu.be/{self.video_id}"
            title, owner = fetch_video_meta(self.video_id)
            save_transcript(self.video_id, title, owner, url, lang_used, text)
            self.ok.emit(self.video_id, title, owner, lang_used, text)
        except Exception as e:
            # Mensaje amigable si YouTube bloquea la IP (error 429 / IpBlocked)
            if type(e).__name__ in ("IpBlocked", "RequestBlocked"):
                error_msg = (
                    "YouTube está bloqueando temporalmente tu conexión "
                    "(demasiadas peticiones seguidas).\n\n"
                    "No es un error del programa. Para resolverlo:\n"
                    "  1) Cambia de IP: reinicia el router, usa una VPN o los datos del móvil.\n"
                    "  2) O espera entre 24 y 48 h a que se levante el bloqueo.\n\n"
                    "Consejo: evita descargar muchos videos seguidos y aprovecha los que ya tienes guardados."
                )
            else:
                error_msg = f"{type(e).__name__}: {e}"
            self.err.emit(error_msg)


# ─────────────────────────────────────────────
# TRABAJADORES RAG (hilos con señales Qt)
# ─────────────────────────────────────────────
class RagIndexWorker(QtCore.QObject):
    """Indexa transcripciones nuevas o modificadas sin bloquear la UI."""
    log = QtCore.Signal(str)
    done = QtCore.Signal(dict)
    err = QtCore.Signal(str)

    def __init__(self, reindex: bool = False, only_video_ids=None):
        super().__init__()
        self.reindex = reindex
        self.only_video_ids = only_video_ids

    def run(self):
        try:
            import rag

            def progress(i, n, vid, state):
                if state != "ok":
                    self.log.emit(f"   [{i}/{n}] {vid}: {state}")

            summary = rag.index_pending(
                reindex=self.reindex, progress=progress, only_video_ids=self.only_video_ids)
            self.done.emit(summary)
        except Exception as exc:  # noqa: BLE001
            self.err.emit(f"{type(exc).__name__}: {exc}")


class RagAskWorker(QtCore.QObject):
    """Recupera pasajes y, si el redactor está activo, redacta la respuesta."""
    ok = QtCore.Signal(dict)
    err = QtCore.Signal(str)

    def __init__(self, question: str, k: int = 6, use_llm: bool = True):
        super().__init__()
        self.question = question
        self.k = k
        self.use_llm = use_llm

    def run(self):
        try:
            import rag
            hits = rag.search(self.question, k=self.k)
            if not self.use_llm:
                self.ok.emit({"respuesta": "", "hits": hits, "modo": "sin-redactor"})
                return
            try:
                out = rag.answer(self.question, k=self.k, hits=hits)
                out["modo"] = "llm"
            except rag.RagError as exc:
                out = {"respuesta": "", "hits": hits, "error_llm": str(exc),
                       "modo": "solo-recuperacion"}
            self.ok.emit(out)
        except Exception as exc:  # noqa: BLE001
            self.err.emit(f"{type(exc).__name__}: {exc}")


class ModelListWorker(QtCore.QObject):
    """Pregunta al servidor del redactor qué modelos tiene instalados."""
    ok = QtCore.Signal(list)
    err = QtCore.Signal(str)

    def __init__(self, base_url: str, api_key: str = ""):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key

    def run(self):
        try:
            import requests

            url = self.base_url.rstrip("/") + "/models"
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                self.err.emit(f"El servidor respondió {resp.status_code}: {resp.text[:160]}")
                return
            data = (resp.json() or {}).get("data") or []
            ids = [d.get("id") for d in data if isinstance(d, dict) and d.get("id")]
            self.ok.emit(ids)
        except Exception as exc:  # noqa: BLE001
            self.err.emit(f"{type(exc).__name__}: {exc}")


class LlmTestWorker(QtCore.QObject):
    """Prueba la conexión con el redactor configurado, sin guardar nada."""
    ok = QtCore.Signal(str)
    err = QtCore.Signal(str)

    def __init__(self, base_url: str, model: str, api_key: str):
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.api_key = api_key

    def run(self):
        try:
            import requests

            url = self.base_url.rstrip("/") + "/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Responde solo: OK"}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
                timeout=25,
            )
            if resp.status_code != 200:
                self.err.emit(f"El servidor respondió {resp.status_code}: {resp.text[:200]}")
                return
            data = resp.json()
            texto = ""
            try:
                texto = data["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, TypeError):
                pass
            self.ok.emit(f"Conectado a {self.model}" + (f" · respondió: «{texto[:40]}»" if texto else ""))
        except Exception as exc:  # noqa: BLE001
            self.err.emit(f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────

class DbCombo(QtWidgets.QComboBox):
    """Selector de base de datos que refresca la lista justo antes de abrirse."""

    aboutToShow = QtCore.Signal()

    def showPopup(self):  # noqa: N802 — API de Qt
        self.aboutToShow.emit()
        super().showPopup()


class MainWindow(ResponsiveMixin, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # ── Control de descargas: pausa mínima entre peticiones a YouTube ──
        # Evita que YouTube bloquee la IP por exceso de peticiones seguidas.
        self._last_download_ts = 0.0
        self._min_download_interval = 10.0   # segundos entre descargas

        self._worker = None
        self._worker_thread = None

        # Preferencias de UI (tamaño de letra del lector)
        self._ui_cfg = load_ui_config()
        self._zoom_accum = 0.0   # acumulador del zoom por pellizco (trackpad)

        self.setWindowTitle(f"YT Transcripts · {db_stem()}")
        self.resize(1200, 800)
        # Mobile-first: la ventana tiene que caber en un móvil (Moto ≈ 432 dp).
        self.setMinimumSize(380, 680)

        # Filas y hileras que se recolocan al cambiar de breakpoint.
        self._field_rows = []
        self._flow_rows = []

        self._build_ui()
        self._build_menu()
        self._refresh_db_combo()

        self._layout_mode = mode_for(self.width())
        self._apply_breakpoint(self._layout_mode)

        # F11 entra/sale del modo lectura; Esc también sale.
        atajo = QShortcut(QKeySequence("F11"), self)
        atajo.setContext(Qt.WindowShortcut)
        atajo.activated.connect(self.btn_read.toggle)
        atajo = QShortcut(QKeySequence(Qt.Key_Escape), self)
        atajo.setContext(Qt.WindowShortcut)
        atajo.activated.connect(self._exit_reading)

        try:
            init_db()
            self._refresh_list()
        except Exception as exc:  # noqa: BLE001 — p. ej. base bloqueada por otro programa
            self._log(f"❌ No se pudo preparar la base {os.path.basename(DB_PATH)}: {exc}", "err")
            QtWidgets.QMessageBox.critical(
                self, "No se pudo abrir la base",
                f"No se pudo preparar la base de datos:\n{DB_PATH}\n\n{exc}")
        self._update_qa_widgets()
        self._log(f"🗂  Base de datos activa: {os.path.basename(DB_PATH)}")

        if not YT_API_AVAILABLE:
            self._log("⚠️  Módulo 'youtube-transcript-api' no encontrado.\n"
                      "   Instálalo con:  pip install youtube-transcript-api\n", "warn")

    # ── Responsividad (mobile-first) ──────────
    def _apply_breakpoint(self, mode):
        """Recoloca la ventana según el ancho: compact / medium / wide.

        En compact: márgenes y espaciados pequeños, cabecera apilada, splitter
        en vertical y formularios con la etiqueta encima del campo. En wide se
        vuelve a la disposición de escritorio.
        """
        if getattr(self, "_reading", False):
            return   # en modo lectura manda el texto: no se recoloca nada
        compact = mode == MODE_COMPACT

        root = getattr(self, "_root_layout", None)
        if root is not None:
            margen = space(1.5) if compact else space(2.5)
            root.setContentsMargins(margen, margen, margen, space(1.5))
            root.setSpacing(space(1) if compact else space(1.75))

        header = getattr(self, "_header_layout", None)
        if header is not None:
            # La cabecera solo va en una línea en escritorio.
            apilada = mode != MODE_WIDE
            header.setDirection(
                QtWidgets.QBoxLayout.TopToBottom if apilada
                else QtWidgets.QBoxLayout.LeftToRight)
            header.setStretch(1, 0 if apilada else 1)

        splitter = getattr(self, "_splitter", None)
        if splitter is not None:
            if compact:
                splitter.setOrientation(Qt.Vertical)
                # Reparto proporcional: lista arriba, pestañas abajo.
                splitter.setStretchFactor(0, 2)
                splitter.setStretchFactor(1, 3)
            else:
                splitter.setOrientation(Qt.Horizontal)
                splitter.setStretchFactor(0, 0)
                splitter.setStretchFactor(1, 1)
                splitter.setSizes([300, 900] if mode == MODE_MEDIUM else [380, 800])

        for fila in getattr(self, "_field_rows", []):
            fila.set_mode(mode)
        for flujo in getattr(self, "_flow_rows", []):
            flujo.setSpacing(space(0.75) if compact else space(1))

        # En el móvil el registro se queda en tres líneas para dejar aire.
        log = getattr(self, "log_area", None)
        if log is not None:
            log.setFixedHeight(space(7) if compact else space(9.75))

        # Filas de «información + acción»: apiladas en compact.
        for nombre in ("_info_row", "_rag_status_row", "_rag_ask_row"):
            fila = getattr(self, nombre, None)
            if fila is None:
                continue
            fila.setDirection(
                QtWidgets.QBoxLayout.TopToBottom if compact
                else QtWidgets.QBoxLayout.LeftToRight)
            fila.setStretch(0, 0 if compact else 1)

    # ── Base de datos: menú y cambio en caliente ──
    def _build_menu(self):
        menu = self.menuBar().addMenu("Base de datos")
        act_nueva = menu.addAction("Nueva base de datos…")
        act_nueva.triggered.connect(self._new_db_dialog)
        act_abrir = menu.addAction("Abrir base de datos…")
        act_abrir.triggered.connect(self._open_db_dialog)
        self._db_submenu = menu.addMenu("Bases disponibles")
        self._db_submenu.aboutToShow.connect(self._populate_db_menu)
        menu.addSeparator()
        act_carpeta = menu.addAction("Mostrar carpeta de la app")
        act_carpeta.triggered.connect(self._open_data_dir)

    def _populate_db_menu(self):
        """Rellena «Bases disponibles» con las *.db de la carpeta de la app."""
        self._db_submenu.clear()
        activa = os.path.basename(DB_PATH)
        bases = _bases_disponibles()
        if not bases:
            vacio = self._db_submenu.addAction("(no hay bases en la carpeta)")
            vacio.setEnabled(False)
            return
        for nombre in bases:
            act = self._db_submenu.addAction(nombre)
            act.setCheckable(True)
            act.setChecked(nombre == activa)
            act.triggered.connect(
                lambda _checked=False, r=os.path.join(APP_DIR, nombre): self._switch_db(r))

    def _refresh_db_combo(self):
        """Refresca el selector visible con todas las *.db de la carpeta."""
        activa = os.path.basename(DB_PATH)
        bases = _bases_disponibles()
        if activa not in bases:
            bases = [activa] + bases
        self.cmb_db.blockSignals(True)
        self.cmb_db.clear()
        for nombre in bases:
            self.cmb_db.addItem(nombre, os.path.join(APP_DIR, nombre))
        indice = self.cmb_db.findText(activa)
        if indice >= 0:
            self.cmb_db.setCurrentIndex(indice)
        self.cmb_db.blockSignals(False)

    def _on_db_combo(self, indice):
        ruta = self.cmb_db.itemData(indice)
        if ruta and os.path.abspath(ruta) != os.path.abspath(DB_PATH):
            self._switch_db(ruta)

    def _new_db_dialog(self):
        nombre, ok = QtWidgets.QInputDialog.getText(
            self, "Nueva base de datos",
            "Nombre de la base de datos (se creará «nombre.db»):", text="")
        if not ok:
            return
        nombre = _sanitize_db_name(nombre)
        ruta = os.path.join(APP_DIR, nombre + ".db")
        if os.path.exists(ruta) and QtWidgets.QMessageBox.question(
                self, "Ya existe",
                f"«{nombre}.db» ya existe.\n\n¿Quieres abrirla?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes) != QtWidgets.QMessageBox.Yes:
            return
        self._switch_db(ruta)

    def _open_db_dialog(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Abrir base de datos", APP_DIR, "Bases SQLite (*.db)")
        if not ruta:
            return
        if os.path.dirname(os.path.abspath(ruta)) != os.path.abspath(APP_DIR):
            QtWidgets.QMessageBox.warning(
                self, "Base fuera de la carpeta",
                "De momento las bases de datos deben estar en la carpeta de la app:\n\n"
                f"{APP_DIR}\n\nCopia el archivo ahí y vuelve a abrirlo.")
            return
        self._switch_db(ruta)

    def _switch_db(self, ruta):
        """Cambia la base activa sin reiniciar la app."""
        ruta = os.path.abspath(ruta)
        if ruta == os.path.abspath(DB_PATH):
            return
        ocupado = any(
            hilo is not None and hilo.is_alive()
            for hilo in (getattr(self, "_worker_thread", None),
                         getattr(self, "_rag_ask_thread", None),
                         getattr(self, "_rag_index_thread", None)))
        if ocupado:
            QtWidgets.QMessageBox.information(
                self, "Espera un momento",
                "Hay una descarga o una consulta en curso.\n"
                "Termínala antes de cambiar de base de datos.")
            self._refresh_db_combo()
            return

        anterior = DB_PATH
        try:
            set_active_db(ruta)
            init_db()
        except Exception as exc:  # noqa: BLE001 — base bloqueada, corrupta, sin permisos…
            set_active_db(anterior)
            detalle = str(exc)
            pista = ""
            if "locked" in detalle.lower() or "busy" in detalle.lower():
                pista = ("\n\nParece que otro programa la tiene abierta "
                         "(DB Browser, otra copia de la app…).\n"
                         "Ciérrala y vuelve a intentarlo.")
            self._log(
                f"❌ No se pudo abrir {os.path.basename(ruta)}: {detalle}", "err")
            self._refresh_db_combo()  # el selector vuelve a la base que sigue activa
            QtWidgets.QMessageBox.critical(
                self, "No se pudo abrir la base",
                f"No se pudo abrir:\n{ruta}\n\n{detalle}{pista}")
            return

        save_ui_config(db_name=os.path.basename(ruta))
        self.setWindowTitle(f"YT Transcripts · {db_stem()}")
        self._refresh_db_combo()

        # Limpiar todo lo que pertenecía a la base anterior.
        self.listbox.blockSignals(True)
        self.listbox.clear()
        self.listbox.blockSignals(False)
        self.lbl_title.setText("Selecciona o descarga una transcripción")
        self.lbl_meta.setText("")
        self.lbl_meta.setVisible(False)
        self.texto.clear()
        self.rag_hits.clear()
        self.rag_answer.clear()
        self._rag_hits = []
        self._last_qa = None
        self.btn_qa_save.setEnabled(False)
        self._update_qa_widgets()

        try:
            self._refresh_list()
        except Exception as exc:  # noqa: BLE001
            self._log(f"⚠️  No se pudo leer la lista de la nueva base: {exc}", "warn")
        self._rag_refresh_status()
        self._log(f"🗂  Base de datos activa: {os.path.basename(ruta)}")

    # ── Layout principal ──────────────────────
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)
        self._root_layout = root

        # ── Cabecera ──
        header = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self._header_layout = header
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(1)
        app_title = QtWidgets.QLabel("▶  YT Transcripts")
        app_title.setObjectName("appTitle")
        subtitle = QtWidgets.QLabel("Descarga, guarda y pregunta a tus transcripciones de YouTube")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)

        # Selector visible de base de datos (temas: costura, ciencia, general…)
        db_row = QtWidgets.QHBoxLayout()
        db_row.setSpacing(6)
        db_tag = QtWidgets.QLabel("Base de datos:")
        db_tag.setObjectName("appSubtitle")
        db_row.addWidget(db_tag)

        self.cmb_db = DbCombo()
        self.cmb_db.setMinimumWidth(180)
        self.cmb_db.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.cmb_db.setToolTip("Cambia de base de datos (tema) sin cerrar la app")
        self.cmb_db.aboutToShow.connect(self._refresh_db_combo)
        self.cmb_db.activated.connect(self._on_db_combo)
        db_row.addWidget(self.cmb_db)

        self.btn_db_new = QtWidgets.QPushButton("＋")
        self.btn_db_new.setFixedWidth(34)
        self.btn_db_new.setCursor(Qt.PointingHandCursor)
        self.btn_db_new.setToolTip("Nueva base de datos…")
        self.btn_db_new.clicked.connect(self._new_db_dialog)
        db_row.addWidget(self.btn_db_new)

        self.btn_db_open = QtWidgets.QPushButton("Abrir…")
        self.btn_db_open.setCursor(Qt.PointingHandCursor)
        self.btn_db_open.setToolTip("Abrir una base de datos existente de la carpeta de la app")
        self.btn_db_open.clicked.connect(self._open_db_dialog)
        db_row.addWidget(self.btn_db_open)

        header.addLayout(db_row)
        self._header_widget = QtWidgets.QWidget()
        self._header_widget.setLayout(header)
        root.addWidget(self._header_widget)

        divider = QtWidgets.QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        self._divider = divider
        root.addWidget(divider)

        # ── Splitter: izquierda / derecha ──
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        self._splitter = splitter
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        self._left_panel = self._build_left_panel()
        splitter.addWidget(self._left_panel)
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([380, 800])

        # ── Registro (siempre visible, debajo del splitter) ──
        log_label = QtWidgets.QLabel("REGISTRO")
        log_label.setObjectName("sectionLabel")
        log_label.setWordWrap(True)
        self._log_label = log_label
        root.addWidget(log_label)
        self._build_log_area(root)

    # ── Panel izquierdo: descarga + lista ─────
    def _build_left_panel(self):
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # URL
        url_label = QtWidgets.QLabel("URL O ID DEL VIDEO")
        url_label.setObjectName("sectionLabel")
        layout.addWidget(url_label)

        self.url_input = QtWidgets.QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=…  o  el ID de 11 caracteres")
        self.url_input.returnPressed.connect(self._start_download)
        layout.addWidget(self.url_input)

        # Idioma
        lang_label = QtWidgets.QLabel("IDIOMA PREFERIDO")
        lang_label.setObjectName("sectionLabel")
        layout.addWidget(lang_label)

        lang_row = QtWidgets.QHBoxLayout()
        lang_row.setSpacing(14)
        self.lang_group = QtWidgets.QButtonGroup(self)
        self._lang_radios = {}
        for code, text in [("es", "ES"), ("en", "EN"), ("auto", "Auto")]:
            rb = QtWidgets.QRadioButton(text)
            rb.setChecked(code == "es")
            self._lang_radios[code] = rb
            self.lang_group.addButton(rb)
            lang_row.addWidget(rb)
        lang_row.addStretch(1)
        layout.addLayout(lang_row)

        # Descargar
        self.btn_download = QtWidgets.QPushButton("⬇  Descargar transcripción")
        self.btn_download.setObjectName("primary")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.clicked.connect(self._start_download)
        layout.addWidget(self.btn_download)

        # Progreso
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # indeterminado
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        div2 = QtWidgets.QFrame()
        div2.setObjectName("divider")
        div2.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(div2)

        # Lista de transcripciones
        list_label = QtWidgets.QLabel("TUS TRANSCRIPCIONES")
        list_label.setObjectName("sectionLabel")
        layout.addWidget(list_label)

        self.listbox = QtWidgets.QListWidget()
        # Los títulos son texto principal: se leen enteros (wrap), sin «…».
        self.listbox.setWordWrap(True)
        self.listbox.setTextElideMode(Qt.ElideNone)
        self.listbox.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listbox.setResizeMode(QtWidgets.QListView.Adjust)
        self.listbox.currentRowChanged.connect(self._on_select)
        self.listbox.itemDoubleClicked.connect(self._enter_reading_on_double)
        layout.addWidget(self.listbox, 1)

        # Botones de acción
        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)

        self.btn_modify = QtWidgets.QPushButton("Modificar")
        self.btn_modify.setCursor(Qt.PointingHandCursor)
        self.btn_modify.clicked.connect(self._modify_selected)

        self.btn_export = QtWidgets.QPushButton("Exportar a PDF")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._exporta_selected)

        self.btn_delete = QtWidgets.QPushButton("Eliminar")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete_selected)

        actions.addWidget(self.btn_modify)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_delete)
        layout.addLayout(actions)

        return panel

    # ── Panel derecho: visor + pestaña RAG ────
    def _build_right_panel(self):
        self.tabs = QtWidgets.QTabWidget()
        # Sin modo documento: ese modo hace que Fusion pinte una fina línea clara
        # sobre la barra de pestañas, y la hoja de estilo no puede quitarla
        # (QTabWidget::pane no la cubre). El aspecto lo da todo el QSS de las tabs.
        self.tabs.setDocumentMode(False)
        self.tabs.addTab(self._build_viewer_tab(), "Transcripción")
        self.tabs.addTab(self._build_rag_tab(), "Preguntar")
        self.tabs.addTab(self._build_settings_tab(), "Ajustes")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        return self.tabs

    def _build_viewer_tab(self):
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # Meta info + control del tamaño de letra (se apila en compact)
        self._info_row = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self._info_row.setSpacing(6)

        info_box = QtWidgets.QVBoxLayout()
        info_box.setSpacing(1)
        self.lbl_title = QtWidgets.QLabel("Selecciona o descarga una transcripción")
        self.lbl_title.setObjectName("appTitle")
        self.lbl_title.setWordWrap(True)
        self.lbl_meta = QtWidgets.QLabel("")
        self.lbl_meta.setObjectName("appSubtitle")
        self.lbl_meta.setWordWrap(True)
        # La línea de datos lleva el enlace al vídeo: clic = navegador del sistema
        self.lbl_meta.setTextFormat(Qt.RichText)
        self.lbl_meta.setOpenExternalLinks(True)
        self.lbl_meta.setTextInteractionFlags(
            Qt.TextBrowserInteraction  # enlaces con clic + texto seleccionable
        )
        self.lbl_meta.setToolTip("Clic en el enlace para ver el vídeo en el navegador")
        self.lbl_meta.setVisible(False)
        info_box.addWidget(self.lbl_title)
        info_box.addWidget(self.lbl_meta)
        self._info_row.addLayout(info_box, 1)

        controles = QtWidgets.QWidget()
        controles_box = QtWidgets.QHBoxLayout(controles)
        controles_box.setContentsMargins(0, 0, 0, 0)
        controles_box.setSpacing(6)

        self.lbl_font_size = QtWidgets.QLabel("")
        self.lbl_font_size.setObjectName("appSubtitle")
        self.lbl_font_size.setMinimumWidth(42)
        self.lbl_font_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        controles_box.addWidget(self.lbl_font_size, 0, Qt.AlignBottom)

        self.btn_font_dec = QtWidgets.QPushButton("A−")
        self.btn_font_dec.setObjectName("fontBtn")
        self.btn_font_dec.setCursor(Qt.PointingHandCursor)
        self.btn_font_dec.setToolTip("Letra más pequeña (Ctrl + −)")
        self.btn_font_dec.clicked.connect(lambda: self._nudge_read_font(-1))
        controles_box.addWidget(self.btn_font_dec, 0, Qt.AlignBottom)

        self.btn_font_inc = QtWidgets.QPushButton("A+")
        self.btn_font_inc.setObjectName("fontBtn")
        self.btn_font_inc.setCursor(Qt.PointingHandCursor)
        self.btn_font_inc.setToolTip("Letra más grande (Ctrl + +)")
        self.btn_font_inc.clicked.connect(lambda: self._nudge_read_font(1))
        controles_box.addWidget(self.btn_font_inc, 0, Qt.AlignBottom)

        self.btn_read = QtWidgets.QPushButton("⛶")
        self.btn_read.setObjectName("fontBtn")
        self.btn_read.setCursor(Qt.PointingHandCursor)
        self.btn_read.setCheckable(True)
        self.btn_read.setToolTip("Modo lectura: solo el texto a pantalla completa (F11)")
        self.btn_read.toggled.connect(self._toggle_reading)
        controles_box.addWidget(self.btn_read, 0, Qt.AlignBottom)

        # Columna de lectura: ancho cómodo en vez de líneas kilométricas.
        self.btn_column = QtWidgets.QPushButton("▭")
        self.btn_column.setObjectName("fontBtn")
        self.btn_column.setCursor(Qt.PointingHandCursor)
        self.btn_column.setCheckable(True)
        self.btn_column.setChecked(True)
        self.btn_column.setVisible(False)
        self.btn_column.setToolTip(
            "Columna de lectura: limita el ancho de las líneas (solo en modo lectura)")
        self.btn_column.toggled.connect(lambda _v: self._apply_reading_column())
        controles_box.addWidget(self.btn_column, 0, Qt.AlignBottom)
        controles_box.addStretch(1)
        self._info_row.addWidget(controles, 0, Qt.AlignBottom)

        layout.addLayout(self._info_row)

        # Visor de transcripción
        self.texto = QtWidgets.QTextEdit()
        self.texto.setObjectName("transcriptView")   # tamaño de letra: ver read_font_qss()
        self.texto.setReadOnly(True)
        # El texto ocupa todo el ancho disponible y envuelve por la ventana.
        self.texto.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self.texto.setPlaceholderText("Aquí se mostrará el texto de la transcripción…")
        # Marco centrado: en modo lectura se limita el ancho del visor (columna).
        marco = QtWidgets.QHBoxLayout()
        marco.setContentsMargins(0, 0, 0, 0)
        marco.addStretch(1)
        marco.addWidget(self.texto, 100)
        marco.addStretch(1)
        layout.addLayout(marco, 1)

        # Ctrl + rueda también cambia la letra, pasando por las mismas funciones
        # (si dejáramos el zoom interno de QTextEdit, el tamaño guardado y el
        # mostrado quedarían desincronizados).
        self.texto.viewport().installEventFilter(self)
        self._apply_read_font_size(self._ui_cfg["read_font_size"])

        # Atajos de teclado: Ctrl+=/Ctrl++ agrandan, Ctrl+− reduce, Ctrl+0 restablece
        for seq, delta in (("Ctrl+=", 1), ("Ctrl++", 1), ("Ctrl+-", -1)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WindowShortcut)
            sc.activated.connect(lambda d=delta: self._nudge_read_font(d))
        sc = QShortcut(QKeySequence("Ctrl+0"), self)
        sc.setContext(Qt.WindowShortcut)
        sc.activated.connect(self._reset_read_font)

        return panel

    # ── Modo lectura (solo el texto, a pantalla completa) ──
    def _toggle_reading(self, activo: bool):
        """Oculta todo lo que no sea el texto; el lector ocupa la ventana."""
        self._reading = bool(activo)
        for widget in (self._header_widget, self._divider, self._left_panel,
                       self._log_label, self.log_area):
            widget.setVisible(not self._reading)
        self.tabs.tabBar().setVisible(not self._reading)
        # Un splitter con un hijo oculto sigue contando su ancho mínimo:
        # se colapsa el panel izquierdo a 0 para que el texto use toda la ventana.
        self._left_panel.setMaximumWidth(0 if self._reading else 16777215)
        if self._reading:
            # El splitter, aun con el panel oculto, impone su ancho mínimo:
            # en modo lectura las pestañas salen a la raíz y el splitter se esconde.
            self._splitter.hide()
            self._root_layout.addWidget(self.tabs, 1)
            self.tabs.show()
            self.tabs.setCurrentIndex(0)
            self._root_layout.setContentsMargins(0, 0, 0, 0)
            self._root_layout.setSpacing(0)
        else:
            self._splitter.addWidget(self.tabs)
            self._splitter.show()
            self._apply_breakpoint(getattr(self, "_layout_mode", MODE_WIDE))
        if hasattr(self, "btn_column"):
            self.btn_column.setVisible(self._reading)
        self._apply_reading_column()

    def _apply_reading_column(self):
        """Columna de lectura: limita el ancho del visor y lo centra."""
        if not hasattr(self, "btn_column"):
            return
        en_columna = (getattr(self, "_reading", False)
                      and self.btn_column.isChecked())
        self.texto.setMaximumWidth(space(90) if en_columna else 16777215)

    def _exit_reading(self):
        if getattr(self, "_reading", False):
            self.btn_read.setChecked(False)

    def _enter_reading_on_double(self, _item=None):
        """Doble clic en una transcripción = abrirla en modo lectura."""
        if not self.btn_read.isChecked():
            self.btn_read.setChecked(True)

    # ── Tamaño de letra del lector ────────────
    def _apply_read_font_size(self, size: int):
        size = max(READ_FONT_MIN, min(READ_FONT_MAX, int(size)))
        self._ui_cfg["read_font_size"] = size

        # Vía principal: regla de estilo propia del visor (ver read_font_qss)
        self.texto.setStyleSheet(read_font_qss(size))

        # Refuerzo: fuente del documento (el texto es plano y hereda esta)
        font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        font.setPointSize(size)
        self.texto.document().setDefaultFont(font)

        self.lbl_font_size.setText(f"{size} pt")
        self.btn_font_dec.setEnabled(size > READ_FONT_MIN)
        self.btn_font_inc.setEnabled(size < READ_FONT_MAX)
        if hasattr(self, "spn_font_size"):
            self.spn_font_size.blockSignals(True)
            self.spn_font_size.setValue(size)
            self.spn_font_size.blockSignals(False)

    def _nudge_read_font(self, delta: int):
        self._apply_read_font_size(self._ui_cfg["read_font_size"] + delta)
        save_ui_config(read_font_size=self._ui_cfg["read_font_size"])

    def _reset_read_font(self):
        self._apply_read_font_size(READ_FONT_DEFAULT)
        save_ui_config(read_font_size=READ_FONT_DEFAULT)

    def eventFilter(self, obj, event):
        # Sobre el lector: Ctrl + rueda y pellizco del trackpad = zoom de letra
        if obj is self.texto.viewport():
            if event.type() == QtCore.QEvent.Wheel:
                if event.modifiers() & Qt.ControlModifier:
                    self._nudge_read_font(1 if event.angleDelta().y() > 0 else -1)
                    return True
            elif event.type() == QtCore.QEvent.NativeGesture:
                if event.gestureType() == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
                    # El trackpad manda valores pequeños y continuos: se acumulan
                    # y se da un paso de letra cada ~0,15 de gesto.
                    self._zoom_accum += event.value()
                    if abs(self._zoom_accum) >= 0.15:
                        self._nudge_read_font(1 if self._zoom_accum > 0 else -1)
                        self._zoom_accum = 0.0
                    return True
        return super().eventFilter(obj, event)

    def _build_log_area(self, root_layout):
        self.log_area = QtWidgets.QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(78)
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(11)
        self.log_area.setFont(mono)
        root_layout.addWidget(self.log_area)

    # ── Pestaña «Preguntar» (RAG) ─────────────
    def _build_rag_tab(self):
        panel = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(panel)
        outer.setContentsMargins(0, 8, 0, 0)
        outer.setSpacing(0)

        # En compact no cabe todo: scroll como en Ajustes.
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        inner = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 10, 4)
        layout.setSpacing(10)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self._rag_status_row = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self._rag_status_row.setSpacing(8)
        self.lbl_rag_status = QtWidgets.QLabel("Índice semántico: sin comprobar")
        self.lbl_rag_status.setObjectName("appSubtitle")
        self.lbl_rag_status.setWordWrap(True)
        self._rag_status_row.addWidget(self.lbl_rag_status, 1)

        self.btn_rag_key = QtWidgets.QPushButton("Ajustes")
        self.btn_rag_key.setCursor(Qt.PointingHandCursor)
        self.btn_rag_key.setToolTip("Elegir el redactor (IA), la clave API y el modelo")
        self.btn_rag_key.clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        self.btn_rag_index = QtWidgets.QPushButton("Indexar")
        self.btn_rag_index.setCursor(Qt.PointingHandCursor)
        self.btn_rag_index.setToolTip("Indexar transcripciones nuevas o modificadas (semántica local)")
        self.btn_rag_index.clicked.connect(lambda: self._rag_start_index(reindex=False))

        # Los dos botones van juntos en una fila propia: en compact la etiqueta
        # cae a su línea y ellos quedan debajo, lado a lado.
        botones_estado = QtWidgets.QHBoxLayout()
        botones_estado.setSpacing(8)
        botones_estado.addWidget(self.btn_rag_key)
        botones_estado.addWidget(self.btn_rag_index)
        botones_estado.addStretch(1)
        self._rag_status_row.addLayout(botones_estado)
        layout.addLayout(self._rag_status_row)

        self._rag_ask_row = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self._rag_ask_row.setSpacing(8)
        self.rag_input = QtWidgets.QLineEdit()
        self.rag_input.setPlaceholderText("Pregunta sobre tus transcripciones: «¿qué dijo Dolina sobre los ángeles?»")
        self.rag_input.returnPressed.connect(self._rag_ask)
        self.rag_input.setMinimumHeight(36)
        self._rag_ask_row.addWidget(self.rag_input, 1)

        self.btn_rag_ask = QtWidgets.QPushButton("Preguntar")
        self.btn_rag_ask.setObjectName("primary")
        self.btn_rag_ask.setCursor(Qt.PointingHandCursor)
        self.btn_rag_ask.clicked.connect(self._rag_ask)
        self._rag_ask_row.addWidget(self.btn_rag_ask)
        layout.addLayout(self._rag_ask_row)

        self.rag_answer = QtWidgets.QTextBrowser()
        self.rag_answer.setOpenLinks(False)
        self.rag_answer.setPlaceholderText(
            "La respuesta se redacta solo con tus transcripciones y cita los pasajes.\n"
            "Si no configuras clave API, verás los fragmentos más relevantes."
        )
        self.rag_answer.anchorClicked.connect(self._on_rag_anchor)
        self.rag_answer.setMinimumHeight(160)
        layout.addWidget(self.rag_answer, 3)

        # ── Cuaderno de preguntas en PDF (botones con wrap) ──
        self.btn_qa_save = QtWidgets.QPushButton("Añadir al cuaderno (PDF)")
        self.btn_qa_save.setCursor(Qt.PointingHandCursor)
        self.btn_qa_save.setToolTip(
            "Guarda esta pregunta y su respuesta en el cuaderno PDF de la base\n"
            "activa y lo regenera con todas las preguntas anteriores")
        self.btn_qa_save.setEnabled(False)
        self.btn_qa_save.clicked.connect(self._rag_save_qa)

        self.chk_qa_open = QtWidgets.QCheckBox("Abrir PDF al guardar")
        self.chk_qa_open.setChecked(True)
        self.chk_qa_open.setToolTip("Abre el cuaderno en el visor de PDF tras cada guardado")

        self.btn_qa_open = QtWidgets.QPushButton("Abrir cuaderno")
        self.btn_qa_open.setCursor(Qt.PointingHandCursor)
        self.btn_qa_open.clicked.connect(self._open_cuaderno)
        self.btn_qa_open.setEnabled(False)

        self.lbl_qa_cuaderno = QtWidgets.QLabel("")
        self.lbl_qa_cuaderno.setObjectName("appSubtitle")
        self.lbl_qa_cuaderno.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._flow_row(
            [self.btn_qa_save, self.chk_qa_open, self.btn_qa_open, self.lbl_qa_cuaderno]))

        hits_label = QtWidgets.QLabel("PASAJES RECUPERADOS (clic para abrir en la transcripción)")
        hits_label.setObjectName("sectionLabel")
        hits_label.setWordWrap(True)
        layout.addWidget(hits_label)

        self.rag_hits = QtWidgets.QListWidget()
        # Sin techo: puede estirarse en vertical (la zona de «filas tupla»).
        self.rag_hits.setMinimumHeight(110)
        self.rag_hits.setWordWrap(True)
        self.rag_hits.setTextElideMode(Qt.ElideNone)
        self.rag_hits.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rag_hits.itemClicked.connect(self._on_rag_hit_clicked)
        layout.addWidget(self.rag_hits, 2)

        return panel

    # ── Pestaña «Ajustes» ─────────────────────
    def _settings_row(self, etiqueta, campo):
        """Fila etiqueta/campo que se apila sola en compact (responsive.FieldRow)."""
        if isinstance(campo, QtWidgets.QLayout):
            contenedor = QtWidgets.QWidget()
            contenedor.setLayout(campo)
            campo = contenedor
        fila = FieldRow(etiqueta, campo)
        fila.set_mode(getattr(self, "_layout_mode", MODE_WIDE))
        self._field_rows.append(fila)
        return fila

    def _flow_row(self, widgets):
        """Hilera de botones que hace wrap en vez de comprimirse (FlowWidget)."""
        contenedor = FlowWidget(widgets, hspacing=space(1), vspacing=space(1))
        self._flow_rows.append(contenedor)
        return contenedor

    def _build_settings_tab(self):
        panel = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(panel)
        outer.setContentsMargins(0, 8, 0, 0)
        outer.setSpacing(0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        inner = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 10, 4)
        layout.setSpacing(6)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Redacción con IA ──
        seccion = QtWidgets.QLabel("REDACCIÓN CON IA")
        seccion.setObjectName("sectionLabel")
        layout.addWidget(seccion)

        self.cmb_provider = QtWidgets.QComboBox()
        for clave, preset in LLM_PROVIDERS.items():
            self.cmb_provider.addItem(preset["label"], clave)
        self.cmb_provider.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(self._settings_row("Redactor", self.cmb_provider))

        self.lbl_provider_hint = QtWidgets.QLabel("")
        self.lbl_provider_hint.setObjectName("appSubtitle")
        self.lbl_provider_hint.setWordWrap(True)
        layout.addWidget(self.lbl_provider_hint)

        modelo_fila = QtWidgets.QHBoxLayout()
        modelo_fila.setSpacing(8)
        self.cmb_model = QtWidgets.QComboBox()
        self.cmb_model.setEditable(True)   # se puede escribir o elegir de los detectados
        self.cmb_model.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.cmb_model.lineEdit().setPlaceholderText("p. ej. deepseek-chat")
        modelo_fila.addWidget(self.cmb_model, 1)

        self.btn_detect_models = QtWidgets.QPushButton("Detectar")
        self.btn_detect_models.setCursor(Qt.PointingHandCursor)
        self.btn_detect_models.setToolTip(
            "Pregunta al servidor qué modelos tiene instalados (Ollama, LM Studio…)")
        self.btn_detect_models.clicked.connect(self._detect_models)
        modelo_fila.addWidget(self.btn_detect_models)
        layout.addWidget(self._settings_row("Modelo", modelo_fila))

        self.edt_base_url = QtWidgets.QLineEdit()
        self.edt_base_url.setPlaceholderText("https://api.deepseek.com")
        layout.addWidget(self._settings_row("Dirección (base_url)", self.edt_base_url))

        clave_fila = QtWidgets.QHBoxLayout()
        clave_fila.setSpacing(8)
        self.edt_api_key = QtWidgets.QLineEdit()
        self.edt_api_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.edt_api_key.setPlaceholderText("sk-…")
        clave_fila.addWidget(self.edt_api_key, 1)
        self.btn_show_key = QtWidgets.QPushButton("Ver")
        self.btn_show_key.setObjectName("fontBtn")
        self.btn_show_key.setCursor(Qt.PointingHandCursor)
        self.btn_show_key.setCheckable(True)
        self.btn_show_key.setFixedWidth(52)
        self.btn_show_key.setToolTip("Mostrar u ocultar la clave")
        self.btn_show_key.toggled.connect(self._toggle_key_visibility)
        clave_fila.addWidget(self.btn_show_key)
        layout.addWidget(self._settings_row("Clave API", clave_fila))

        self.spn_temp = QtWidgets.QDoubleSpinBox()
        self.spn_temp.setRange(0.0, 1.5)
        self.spn_temp.setSingleStep(0.1)
        self.spn_temp.setDecimals(1)
        self.spn_temp.setFixedWidth(90)
        self.spn_temp.setToolTip("0 = respuestas más literales · 1 = más creativas")
        self.spn_max_tokens = QtWidgets.QSpinBox()
        self.spn_max_tokens.setRange(100, 4000)
        self.spn_max_tokens.setSingleStep(50)
        self.spn_max_tokens.setFixedWidth(100)
        self.spn_max_tokens.setToolTip("Longitud máxima de la respuesta redactada")
        nums = [self.spn_temp, QtWidgets.QLabel("temperatura"),
                self.spn_max_tokens, QtWidgets.QLabel("máx. tokens")]
        layout.addWidget(self._settings_row("Ajustes del modelo", self._flow_row(nums)))

        self.btn_llm_save = QtWidgets.QPushButton("Guardar")
        self.btn_llm_save.setObjectName("primary")
        self.btn_llm_save.setCursor(Qt.PointingHandCursor)
        self.btn_llm_save.clicked.connect(self._settings_save)

        self.btn_llm_test = QtWidgets.QPushButton("Probar conexión")
        self.btn_llm_test.setCursor(Qt.PointingHandCursor)
        self.btn_llm_test.setToolTip("Hace una petición mínima al redactor con los datos del formulario")
        self.btn_llm_test.clicked.connect(self._llm_test)

        self.btn_llm_reload = QtWidgets.QPushButton("Recargar del disco")
        self.btn_llm_reload.setCursor(Qt.PointingHandCursor)
        self.btn_llm_reload.setToolTip("Vuelve a leer rag_config.json (descarta cambios sin guardar)")
        self.btn_llm_reload.clicked.connect(self._settings_load)
        layout.addWidget(self._flow_row(
            [self.btn_llm_save, self.btn_llm_test, self.btn_llm_reload]))

        self.lbl_llm_status = QtWidgets.QLabel("")
        self.lbl_llm_status.setObjectName("appSubtitle")
        self.lbl_llm_status.setWordWrap(True)
        layout.addWidget(self.lbl_llm_status)

        # ── Lector ──
        divisor = QtWidgets.QFrame()
        divisor.setObjectName("divider")
        divisor.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(divisor)

        seccion2 = QtWidgets.QLabel("LECTOR")
        seccion2.setObjectName("sectionLabel")
        layout.addWidget(seccion2)

        self.spn_font_size = QtWidgets.QSpinBox()
        self.spn_font_size.setRange(READ_FONT_MIN, READ_FONT_MAX)
        self.spn_font_size.setSuffix(" pt")
        self.spn_font_size.setFixedWidth(90)
        self.spn_font_size.setValue(self._ui_cfg["read_font_size"])
        self.spn_font_size.valueChanged.connect(self._on_font_spin_changed)
        btn_font_reset = QtWidgets.QPushButton(f"Restablecer ({READ_FONT_DEFAULT} pt)")
        btn_font_reset.setCursor(Qt.PointingHandCursor)
        btn_font_reset.clicked.connect(self._reset_read_font)
        layout.addWidget(self._settings_row(
            "Tamaño de letra", self._flow_row([self.spn_font_size, btn_font_reset])))

        # ── Datos e índice ──
        divisor2 = QtWidgets.QFrame()
        divisor2.setObjectName("divider")
        divisor2.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(divisor2)

        seccion3 = QtWidgets.QLabel("DATOS E ÍNDICE")
        seccion3.setObjectName("sectionLabel")
        layout.addWidget(seccion3)

        self.lbl_settings_info = QtWidgets.QLabel("")
        self.lbl_settings_info.setObjectName("appSubtitle")
        self.lbl_settings_info.setWordWrap(True)
        self.lbl_settings_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.lbl_settings_info)

        self.btn_index_now = QtWidgets.QPushButton("Indexar ahora")
        self.btn_index_now.setCursor(Qt.PointingHandCursor)
        self.btn_index_now.clicked.connect(lambda: self._rag_start_index(reindex=False))

        self.btn_index_rebuild = QtWidgets.QPushButton("Reindexar todo")
        self.btn_index_rebuild.setCursor(Qt.PointingHandCursor)
        self.btn_index_rebuild.setToolTip("Reconstruye el índice completo (tras cambiar de modelo)")
        self.btn_index_rebuild.clicked.connect(lambda: self._rag_start_index(reindex=True))

        btn_open_dir = QtWidgets.QPushButton("Abrir carpeta de datos")
        btn_open_dir.setCursor(Qt.PointingHandCursor)
        btn_open_dir.clicked.connect(self._open_data_dir)
        layout.addWidget(self._flow_row(
            [self.btn_index_now, self.btn_index_rebuild, btn_open_dir]))

        self._settings_load()
        self._settings_refresh_info()
        return panel

    # ── Ajustes: lectura y escritura ──────────
    def _settings_load(self):
        cfg = load_rag_config()
        idx = self.cmb_provider.findData(cfg["provider"])
        self.cmb_provider.blockSignals(True)
        self.cmb_provider.setCurrentIndex(max(0, idx))
        self.cmb_provider.blockSignals(False)
        self.cmb_model.setEditText(cfg.get("model", ""))
        self.edt_base_url.setText(cfg.get("base_url", ""))
        self.edt_api_key.setText(cfg.get("api_key", ""))
        self.spn_temp.setValue(float(cfg.get("temperature", 0.2)))
        self.spn_max_tokens.setValue(int(cfg.get("max_tokens", 900)))
        self._settings_update_enabled()
        self.lbl_llm_status.setText(
            f"Configuración leída de {os.path.basename(RAG_CONFIG_PATH)}"
            if os.path.exists(RAG_CONFIG_PATH) else "Sin guardar aún: todo por defecto")

    def _settings_update_enabled(self):
        provedor = self.cmb_provider.currentData()
        preset = LLM_PROVIDERS[provedor]
        activo = provedor != "none"
        self.lbl_provider_hint.setText(preset["hint"])

        for w in (self.cmb_model, self.edt_base_url, self.spn_temp, self.spn_max_tokens):
            w.setEnabled(activo)
        self.edt_api_key.setEnabled(activo and preset["needs_key"])
        self.btn_show_key.setEnabled(activo and preset["needs_key"])
        self.btn_llm_test.setEnabled(activo)
        self.btn_detect_models.setEnabled(activo)
        self.btn_llm_save.setEnabled(True)
        if not preset["needs_key"]:
            self.edt_api_key.setPlaceholderText("no hace falta")
        else:
            self.edt_api_key.setPlaceholderText("sk-…")
        self._settings_refresh_info()

    def _on_provider_changed(self):
        preset = LLM_PROVIDERS[self.cmb_provider.currentData()]
        self.edt_base_url.setText(preset["base_url"])
        self.cmb_model.setEditText(preset["model"])
        if not preset["needs_key"]:
            self.edt_api_key.clear()
        self._settings_update_enabled()

    def _toggle_key_visibility(self, visible: bool):
        self.edt_api_key.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Normal if visible
            else QtWidgets.QLineEdit.EchoMode.Password)
        self.btn_show_key.setText("Ocultar" if visible else "Ver")

    def _settings_save(self):
        provedor = self.cmb_provider.currentData()
        preset = LLM_PROVIDERS[provedor]
        base_url = self.edt_base_url.text().strip() or preset["base_url"]
        model = self.cmb_model.currentText().strip() or preset["model"]

        if provedor != "none" and not (base_url and model):
            QtWidgets.QMessageBox.warning(
                self, "Faltan datos",
                "Con un redactor activo hacen falta la dirección (base_url) y el modelo.")
            return

        api_key = self.edt_api_key.text().strip()
        if not preset["needs_key"] and not api_key:
            api_key = None  # no pisar la clave guardada por si vuelves a la nube
        try:
            save_rag_config(
                provider=provedor,
                base_url=base_url,
                model=model,
                api_key=api_key,
                temperature=round(float(self.spn_temp.value()), 2),
                max_tokens=int(self.spn_max_tokens.value()),
            )
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self, "No se pudo guardar", f"No se pudo escribir {RAG_CONFIG_PATH}:\n\n{exc}")
            return

        etiqueta = preset["label"]
        self.lbl_llm_status.setText(
            f"Guardado · redactor: {etiqueta}" + (f" · {model}" if provedor != "none" else ""))
        self._log(f"⚙️  Ajustes guardados: {etiqueta}" + (f" ({model})" if provedor != "none" else ""), "ok")
        self._rag_refresh_status()

    def _llm_test(self):
        provedor = self.cmb_provider.currentData()
        if provedor == "none":
            return
        base_url = self.edt_base_url.text().strip() or LLM_PROVIDERS[provedor]["base_url"]
        model = self.cmb_model.currentText().strip() or LLM_PROVIDERS[provedor]["model"]
        if not (base_url and model):
            self.lbl_llm_status.setText("Completa la dirección y el modelo antes de probar.")
            return
        if getattr(self, "_llm_test_thread", None) and self._llm_test_thread.is_alive():
            return

        self.btn_llm_test.setEnabled(False)
        self.btn_llm_test.setText("Probando…")
        self.lbl_llm_status.setText(f"Contactando con {base_url} …")

        worker = LlmTestWorker(base_url, model, self.edt_api_key.text().strip())
        worker.ok.connect(self._on_llm_test_ok)
        worker.err.connect(self._on_llm_test_err)

        def target():
            worker.run()

        self._llm_test_thread = threading.Thread(target=target, daemon=True)
        self._llm_test_thread.start()

    def _detect_models(self):
        provedor = self.cmb_provider.currentData()
        base_url = self.edt_base_url.text().strip() or LLM_PROVIDERS[provedor]["base_url"]
        if not base_url:
            self.lbl_llm_status.setText("Escribe primero la dirección del servidor.")
            return
        if getattr(self, "_detect_thread", None) and self._detect_thread.is_alive():
            return

        self.btn_detect_models.setEnabled(False)
        self.btn_detect_models.setText("Buscando…")
        self.lbl_llm_status.setText(f"Preguntando a {base_url} qué modelos tiene…")

        worker = ModelListWorker(base_url, self.edt_api_key.text().strip())
        worker.ok.connect(self._on_models_detected)
        worker.err.connect(self._on_models_detect_err)

        def target():
            worker.run()

        self._detect_thread = threading.Thread(target=target, daemon=True)
        self._detect_thread.start()

    def _on_models_detected(self, ids):
        self.btn_detect_models.setEnabled(True)
        self.btn_detect_models.setText("Detectar")
        if not ids:
            self.lbl_llm_status.setText(
                "El servidor responde, pero no tiene modelos instalados "
                "(en Ollama: «ollama pull qwen2.5:7b-instruct»).")
            return
        escrito = self.cmb_model.currentText().strip()
        self.cmb_model.blockSignals(True)
        self.cmb_model.clear()
        self.cmb_model.addItems(ids)
        if escrito and escrito not in ids:
            self.cmb_model.setEditText(escrito)
        elif escrito in ids:
            self.cmb_model.setCurrentText(escrito)
        else:
            self.cmb_model.setCurrentText(ids[0])
        self.cmb_model.blockSignals(False)
        cuantos = f"{len(ids)} modelo{'s' if len(ids) != 1 else ''}"
        self.lbl_llm_status.setText(f"Detectado{'s' if len(ids) != 1 else ''} {cuantos} · elige en «Modelo»")
        self._log(f"🔍 Modelos disponibles: {', '.join(ids[:6])}", "ok")

    def _on_models_detect_err(self, msg):
        self.btn_detect_models.setEnabled(True)
        self.btn_detect_models.setText("Detectar")
        self.lbl_llm_status.setText(
            f"❌ No se pudo consultar el servidor: {msg}")
        self._log(f"❌ Detección de modelos: {msg}", "err")

    def _on_llm_test_ok(self, msg):
        self.btn_llm_test.setEnabled(True)
        self.btn_llm_test.setText("Probar conexión")
        self.lbl_llm_status.setText(f"✅ {msg}")
        self._log(f"✅ Redactor: {msg}", "ok")

    def _on_llm_test_err(self, msg):
        self.btn_llm_test.setEnabled(True)
        self.btn_llm_test.setText("Probar conexión")
        self.lbl_llm_status.setText(f"❌ {msg}")
        self._log(f"❌ Prueba del redactor: {msg}", "err")

    def _settings_refresh_info(self):
        if not hasattr(self, "lbl_settings_info"):
            return
        lineas = [
            f"Base de datos: {DB_PATH}",
            f"Configuración: {RAG_CONFIG_PATH}",
            f"Modelo de búsqueda: {RAG_MODEL_LABEL} (local, {RAG_MODEL_DIM} dims)",
        ]
        rag = self._rag_module(silent=True)
        if rag is not None:
            try:
                st = rag.index_stats()
                lineas.append(
                    f"Índice: {st['videos_indexados']}/{st['videos_totales']} vídeos · "
                    f"{st['fragmentos']} fragmentos · {st['vectores']} vectores")
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"Índice: error ({exc})")
        else:
            lineas.append("Índice: sin dependencias RAG (pip install fastembed numpy)")
        self.lbl_settings_info.setText("\n".join(lineas))

    def _open_data_dir(self):
        QtGui.QDesktopServices.openUrl(QUrl.fromLocalFile(APP_DIR))

    def _on_font_spin_changed(self, valor):
        self._apply_read_font_size(int(valor))
        save_ui_config(read_font_size=int(valor))

    def _on_tab_changed(self, index):
        if index == 1:
            if self._rag_module(silent=True) is None:
                self.lbl_rag_status.setText(
                    "RAG no disponible · instala fastembed y numpy (pip install fastembed numpy)")
                return
            self._rag_refresh_status()
        elif index == 2:
            self._settings_refresh_info()

    # ── RAG: estado del índice ────────────────
    def _rag_module(self, silent: bool = False):
        try:
            if importlib.util.find_spec("fastembed") is None:
                raise ImportError("falta el paquete fastembed")
            import rag  # import perezoso: la app funciona sin las dependencias RAG
            rag.DB_PATH = DB_PATH  # la base activa puede haber cambiado en caliente
        except ImportError as exc:
            if not silent:
                QtWidgets.QMessageBox.critical(
                    self, "RAG no disponible",
                    "Faltan dependencias para la búsqueda semántica.\n\n"
                    "Instálalas con:\n\n    pip install fastembed numpy\n\n"
                    f"Detalle: {exc}")
            return None
        return rag

    def _rag_refresh_status(self):
        rag = self._rag_module(silent=True)
        if rag is None:
            return
        redactor = LLM_PROVIDERS[load_rag_config()["provider"]]["label"]
        try:
            st = rag.index_stats()
        except Exception as exc:  # noqa: BLE001
            self.lbl_rag_status.setText(f"Índice: error ({exc})")
            return
        if st["fragmentos"] == 0:
            self.lbl_rag_status.setText("Índice vacío · pulsa «Indexar» una sola vez")
        elif st["videos_indexados"] < st["videos_totales"]:
            self.lbl_rag_status.setText(
                f"Índice: {st['videos_indexados']}/{st['videos_totales']} vídeos · "
                f"{st['fragmentos']} fragmentos · pulsa «Indexar»")
        else:
            self.lbl_rag_status.setText(
                f"Índice: {st['videos_indexados']} vídeos · {st['fragmentos']} fragmentos · "
                f"redactor: {redactor}")

    # ── RAG: indexado ─────────────────────────
    def _rag_start_index(self, reindex: bool = False, only_video_ids=None):
        rag = self._rag_module()
        if rag is None:
            return
        if getattr(self, "_rag_index_thread", None) and self._rag_index_thread.is_alive():
            return
        self.btn_rag_index.setEnabled(False)
        self.btn_rag_index.setText("Indexando…")
        self._log("🧠 Indexando transcripciones (la primera vez descarga el modelo)…")

        worker = RagIndexWorker(reindex=reindex, only_video_ids=only_video_ids)
        worker.log.connect(self._on_rag_index_log)
        worker.done.connect(self._on_rag_index_done)
        worker.err.connect(self._on_rag_index_err)

        def target():
            worker.run()

        self._rag_index_thread = threading.Thread(target=target, daemon=True)
        self._rag_index_thread.start()

    def _on_rag_index_log(self, msg):
        self._log(msg)

    def _on_rag_index_done(self, summary):
        self.btn_rag_index.setEnabled(True)
        self.btn_rag_index.setText("Indexar")
        self._log(
            f"🧠 Índice: {summary['nuevos']} nuevos, {summary['cambiados']} actualizados, "
            f"{summary['sin_cambios']} sin cambios · {summary['fragmentos']} fragmentos", "ok")
        self._rag_refresh_status()

    def _on_rag_index_err(self, msg):
        self.btn_rag_index.setEnabled(True)
        self.btn_rag_index.setText("Indexar")
        self._log(f"❌ Error indexando: {msg}", "err")

    # ── RAG: preguntar ────────────────────────
    def _rag_ask(self):
        question = self.rag_input.text().strip()
        if not question:
            return
        rag = self._rag_module()
        if rag is None:
            return
        if getattr(self, "_rag_ask_thread", None) and self._rag_ask_thread.is_alive():
            return

        self.btn_rag_ask.setEnabled(False)
        self.btn_rag_ask.setText("Pensando…")
        self.rag_hits.clear()
        self.rag_answer.setHtml(
            '<p style="color:#9b9bae"><i>Buscando en tus transcripciones…</i></p>')

        use_llm = load_rag_config()["provider"] != "none"
        worker = RagAskWorker(question, use_llm=use_llm)
        worker.ok.connect(self._on_rag_answer)
        worker.err.connect(self._on_rag_ask_err)

        def target():
            worker.run()

        self._rag_ask_thread = threading.Thread(target=target, daemon=True)
        self._rag_ask_thread.start()

    def _on_rag_ask_err(self, msg):
        self.btn_rag_ask.setEnabled(True)
        self.btn_rag_ask.setText("Preguntar")
        self.rag_answer.setHtml(
            f'<p style="color:#FF453A">{html.escape(msg)}</p>')

    def _on_rag_answer(self, out):
        self.btn_rag_ask.setEnabled(True)
        self.btn_rag_ask.setText("Preguntar")

        hits = out.get("hits") or []
        self._rag_hits = hits
        self.rag_hits.clear()
        for i, h in enumerate(hits, 1):
            label = f"[{i}] {h.title[:70]}  ·  {h.score:.2f}"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, i - 1)
            self.rag_hits.addItem(item)

        if out.get("modo") == "llm":
            body = html.escape(out["respuesta"])
            body = linkify_citations(body)
            body = body.replace("\n", "<br>")
            html_doc = f"<p>{body}</p>"
        else:
            if out.get("modo") == "sin-redactor":
                note = ("Redactor desactivado: modo recuperación. Puedes activar una IA en "
                        "«Ajustes» para que redacte la respuesta citando estos pasajes.")
            else:
                note = ("No se pudo redactar la respuesta. Revisa el redactor en «Ajustes» "
                        "(clave API o servidor local).")
            if out.get("error_llm"):
                self._log(f"⚠️  {out['error_llm']}", "warn")
            html_doc = (
                f'<p style="color:#FF9F0A">{html.escape(note)}</p>'
                '<p style="color:#9b9bae">Pasajes más relevantes (clic para abrir):</p>'
                "<ol style='color:#d6d6e2'>"
                + "".join(
                    f'<li><a href="hit:{i}" style="color:#8f7bff">{html.escape(h.title)}</a><br>'
                    f"<span style='color:#b9b9c8'>{html.escape(h.text[:280])}…</span></li>"
                    for i, h in enumerate(hits, 1)
                )
                + "</ol>"
            )
        self.rag_answer.setHtml(html_doc)
        self._log(f"🔎 «{self.rag_input.text().strip()[:60]}» → {len(hits)} pasajes")

        # Datos para poder añadir esta consulta al cuaderno PDF.
        respuesta = (out.get("respuesta") or "").strip()
        self._last_qa = {
            "question": self.rag_input.text().strip(),
            "answer": respuesta,
            "sources": [
                {"title": h.title, "video_id": h.video_id,
                 "url": video_url(h.video_id, getattr(h, "url", None)),
                 "score": round(float(h.score), 3),
                 # El texto del pasaje viaja con la pregunta: es lo que se
                 # imprime en el cuaderno PDF (no solo el enlace al vídeo).
                 "text": (h.text or "").strip(),
                 "start_char": int(getattr(h, "start_char", 0) or 0),
                 "end_char": int(getattr(h, "end_char", 0) or 0)}
                for h in hits
            ],
        }
        self.btn_qa_save.setEnabled(bool(respuesta))
        self.btn_qa_save.setToolTip(
            "Guarda esta pregunta y su respuesta en el cuaderno PDF de la base activa"
            if respuesta else
            "No hay respuesta redactada que guardar: activa un redactor en «Ajustes»")

    # ── Cuaderno de preguntas (PDF) ──
    def _cuaderno_path(self) -> str:
        return os.path.join(APP_DIR, f"cuaderno-{db_stem()}.pdf")

    def _update_qa_widgets(self):
        ruta = self._cuaderno_path()
        existe = os.path.exists(ruta)
        self.btn_qa_open.setEnabled(existe)
        self.lbl_qa_cuaderno.setText(os.path.basename(ruta))
        self.lbl_qa_cuaderno.setToolTip(ruta)
        self.btn_qa_open.setToolTip(
            f"Abre {os.path.basename(ruta)}" if existe
            else "Aún no hay cuaderno: guarda una respuesta con «Añadir al cuaderno»")
        return ruta

    def _rag_save_qa(self):
        qa = getattr(self, "_last_qa", None)
        if not qa or not qa.get("answer"):
            QtWidgets.QMessageBox.information(
                self, "Sin respuesta redactada",
                "Esta consulta no tiene una respuesta de texto que guardar.\n"
                "Activa un redactor en «Ajustes» para que redacte la respuesta.")
            return
        cfg = load_rag_config()
        try:
            save_qa(qa["question"], qa["answer"], qa["sources"],
                    cfg.get("provider", ""), cfg.get("model", ""))
            entradas = get_qa_entries()
            ruta = self._cuaderno_path()
            _escribir_cuaderno_pdf(ruta, db_stem(), entradas)
        except Exception as exc:  # noqa: BLE001
            self._log(f"❌ Error creando el cuaderno: {exc}", "err")
            QtWidgets.QMessageBox.critical(
                self, "Error al guardar", f"No se pudo generar el PDF:\n\n{exc}")
            return
        self._log(f"📄 Cuaderno actualizado: {ruta} ({len(entradas)} preguntas)", "ok")
        self._update_qa_widgets()
        self.btn_qa_save.setEnabled(False)  # evita guardar dos veces la misma respuesta
        if self.chk_qa_open.isChecked():
            self._open_cuaderno()

    def _open_cuaderno(self):
        ruta = self._cuaderno_path()
        if not os.path.exists(ruta):
            self._log("El cuaderno aún no existe: guarda una respuesta primero.", "warn")
            return
        QtGui.QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))

    def _on_rag_anchor(self, url):
        if url.scheme() == "hit":
            try:
                idx = int(url.path()) - 1
            except ValueError:
                return
            hits = getattr(self, "_rag_hits", [])
            if 0 <= idx < len(hits):
                self._rag_open_hit(hits[idx])

    def _on_rag_hit_clicked(self, item):
        idx = item.data(Qt.UserRole)
        hits = getattr(self, "_rag_hits", [])
        if idx is not None and 0 <= idx < len(hits):
            self._rag_open_hit(hits[idx])

    def _rag_open_hit(self, hit):
        """Abre la transcripción del pasaje y resalta el fragmento citado."""
        self.tabs.setCurrentIndex(0)
        for i in range(self.listbox.count()):
            if self.listbox.item(i).data(Qt.UserRole) == hit.video_id:
                self.listbox.setCurrentRow(i)
                break
        else:
            self._show_content(hit.video_id)

        doc = self.texto.document()
        max_pos = max(0, doc.characterCount() - 1)
        start = min(hit.start_char or 0, max_pos)
        cursor = QTextCursor(doc)
        cursor.setPosition(start)
        if hit.end_char and hit.end_char > hit.start_char:
            cursor.setPosition(min(hit.end_char, max_pos), QTextCursor.KeepAnchor)
        self.texto.setTextCursor(cursor)
        self.texto.ensureCursorVisible()

    # ── Descargar ─────────────────────────────
    def _start_download(self):
        if not YT_API_AVAILABLE:
            QtWidgets.QMessageBox.critical(
                self, "Módulo faltante",
                "Instala la dependencia:\n\npip install youtube-transcript-api")
            return

        raw = self.url_input.text().strip()
        if not raw:
            QtWidgets.QMessageBox.warning(self, "Campo vacío", "Ingresa una URL o ID de YouTube.")
            return

        video_id = extract_video_id(raw)
        if not video_id:
            QtWidgets.QMessageBox.critical(self, "URL inválida", "No se pudo extraer el ID del video.")
            return

        lang = self._current_lang()
        if lang == "auto":
            lang = "es"  # fallback; fetch_transcript tomará lo disponible

        # ── Caché: no volver a pedir a YouTube lo que ya tenemos guardado ──
        if transcript_exists(video_id):
            resp = QtWidgets.QMessageBox.question(
                self, "Ya existe",
                f"Ya tienes esta transcripción en la base de datos.\n\n"
                f"¿Volver a descargarla de YouTube?\n"
                f"Si eliges «No» se mostrará la copia guardada sin tocar YouTube.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if resp == QtWidgets.QMessageBox.No:
                self.url_input.clear()
                self._show_content(video_id)
                self._log(f"↩  Ya estaba guardada: {video_id} (no se ha vuelto a descargar)", "ok")
                return

        # ── Pausa mínima entre descargas (evita que YouTube bloquee la IP) ──
        delay = max(0.0, self._min_download_interval - (time.time() - self._last_download_ts))
        self._last_download_ts = time.time() + delay
        if delay > 0:
            self._log(f"⏸  Pausa de seguridad de {delay:.0f}s antes de descargar…", "warn")

        self._set_busy(True)
        self._log(f"⏳ Descargando transcripción para {video_id} …")

        worker = DownloadWorker(video_id, lang)
        worker.ok.connect(self._on_download_ok)
        worker.err.connect(self._on_download_err)
        self._worker = worker

        def target():
            if delay > 0:
                time.sleep(delay)
            worker.run()

        thread = threading.Thread(target=target, daemon=True)
        self._worker_thread = thread
        thread.start()

    def _on_download_ok(self, video_id, title, owner, lang_used, text):
        self._set_busy(False)
        self._log(f"✅ Guardado: {video_id} [{title}] [{owner}] [{lang_used}] ({len(text)} chars)", "ok")
        self.url_input.clear()
        self._refresh_list()
        self._show_content(video_id)
        # Indexado semántico incremental en segundo plano (si RAG está disponible)
        if self._rag_module(silent=True) is not None:
            self._rag_start_index(only_video_ids=[video_id])

    def _on_download_err(self, msg):
        self._set_busy(False)
        self._log(f"❌ Error: {msg}", "err")
        QtWidgets.QMessageBox.critical(self, "Error al descargar", msg)

    def _current_lang(self) -> str:
        for code, rb in self._lang_radios.items():
            if rb.isChecked():
                return code
        return "es"

    # ── Lista y selección ─────────────────────
    def _refresh_list(self):
        self.listbox.blockSignals(True)
        self.listbox.clear()
        for row in get_all_transcripts():
            id_, title, video_id, lang, owner, created_at = row
            label = f"{title or video_id}  [{lang}]"
            if owner:
                label = f"{title or video_id}  ·  {owner}  [{lang}]"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, video_id)
            self.listbox.addItem(item)
        self.listbox.blockSignals(False)

    def _selected_video_id(self):
        item = self.listbox.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _on_select(self, row):
        if row < 0:
            return
        video_id = self._selected_video_id()
        if video_id:
            self._show_content(video_id)

    def _show_content(self, video_id):
        row = get_transcript_content(video_id)
        if not row:
            return

        title, url, lang, content, owner = row
        self.lbl_title.setText(title or video_id)

        # Enlace al vídeo: se construye siempre (aunque falte la URL guardada) y
        # el QLabel lo abre en el navegador al pulsarlo.
        href = video_url(video_id, url)
        partes = [
            f'<a href="{html.escape(href, quote=True)}" '
            f'style="color:#8f7bff; text-decoration:underline">{html.escape(href)}</a>',
            f"idioma: {html.escape(str(lang or '—'))}",
        ]
        if owner:
            partes.append(html.escape(owner))
        partes.append(f"{len(content)} caracteres")
        self.lbl_meta.setText("  ·  ".join(partes))
        self.lbl_meta.setVisible(True)

        self.texto.setPlainText(content)

    def _delete_selected(self):
        video_id = self._selected_video_id()
        if not video_id:
            return
        if QtWidgets.QMessageBox.question(
            self, "Eliminar", f"¿Eliminar la transcripción de {video_id}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        ) == QtWidgets.QMessageBox.Yes:
            delete_transcript(video_id)
            if self._rag_module(silent=True) is not None:
                try:
                    import rag
                    rag.delete_video_index(rag.get_conn(), video_id)
                except Exception:  # noqa: BLE001 — el borrado del texto no debe fallar por el índice
                    pass
            self._log(f"🗑  Eliminado: {video_id}")
            self._refresh_list()
            self.lbl_title.setText("Selecciona o descarga una transcripción")
            self.lbl_meta.setText("")
            self.lbl_meta.setVisible(False)
            self.texto.clear()

    def _modify_selected(self):
        video_id = self._selected_video_id()
        if not video_id:
            return

        current_title = ""
        row = get_transcript_content(video_id)
        if row:
            current_title = row[0] or ""

        nuevo_titulo, ok = QtWidgets.QInputDialog.getText(
            self, "Editar título", "Ingresa el nuevo título:", text=current_title)
        if not ok or not nuevo_titulo.strip():
            return
        nuevo_titulo = nuevo_titulo.strip()

        if QtWidgets.QMessageBox.question(
            self, "Modificar", f"¿Modificar el título «{nuevo_titulo}» de {video_id}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        ) == QtWidgets.QMessageBox.Yes:
            update_transcript(video_id, title=nuevo_titulo)
            self._log(f"✏️  Modificado: {video_id} → {nuevo_titulo}")
            self._refresh_list()
            self._show_content(video_id)
            # el título forma parte del embedding: reindexar ese vídeo
            if self._rag_module(silent=True) is not None:
                try:
                    import rag
                    rag.delete_video_index(rag.get_conn(), video_id)
                    self._rag_start_index(only_video_ids=[video_id])
                except Exception:  # noqa: BLE001
                    pass

    def _exporta_selected(self):
        video_id = self._selected_video_id()
        if not video_id:
            return
        row = get_transcript_content(video_id)
        if not row:
            QtWidgets.QMessageBox.critical(self, "Error", "No se encontró el contenido.")
            return

        title, url, lang, content, owner = row

        if QtWidgets.QMessageBox.question(
            self, "Exportar", f"¿Exportar «{title}» a PDF?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        ) == QtWidgets.QMessageBox.Yes:
            try:
                self._exportar_pdf(title, content, url, owner)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error al exportar", str(e))
                self._log(f"❌ Error exportando PDF: {e}", "err")

    def _safe_filename(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "transcripcion"

    def _exportar_pdf(self, title, content, url, owner=""):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guardar PDF como…", f"{self._safe_filename(title)}.pdf", "PDF (*.pdf)"
        )
        if not filepath:
            return

        _escribir_pdf(filepath, title, content, url, owner)
        self._log(f"📄 PDF exportado: {filepath}", "ok")
        QtWidgets.QMessageBox.information(self, "Exportado", f"PDF guardado en:\n{filepath}")

    # ── Helpers ───────────────────────────────
    def _set_busy(self, busy: bool):
        self.btn_download.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 0)  # indeterminado
            self.progress.setVisible(True)
        else:
            self.progress.setVisible(False)

    def _log(self, msg: str, tag: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        color = {"warn": "#FF9F0A", "ok": "#30D158", "err": "#FF453A"}.get(tag, "#b9b9c8")
        safe = html.escape(msg)
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_area.setTextCursor(cursor)
        self.log_area.insertHtml(
            f'<span style="color:#6b6b7a">[{ts}]</span> '
            f'<span style="color:{color}">{safe}</span><br>'
        )
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())


# ─────────────────────────────────────────────
def _ensure_initial_db():
    """Resuelve la base activa al arrancar.

    La primera vez pide un nombre (por defecto «transcripts»), de modo que se
    pueda crear una base por tema: costura.db, cocina.db… Las siguientes
    veces recuerda la última usada en ui_config.json. Si esa base ya no está
    (la renombraste o moviste), ofrece las que sí existen en la carpeta en vez
    de crear una vacía en silencio.
    """
    cfg = load_ui_config()
    guardada = str(cfg.get("db_name") or "").strip()
    if guardada:
        ruta = db_initial_path()
        if os.path.exists(ruta):
            set_active_db(ruta)
            return
        disponibles = _bases_disponibles()
        if disponibles:
            eleccion, ok = QtWidgets.QInputDialog.getItem(
                None, "Base de datos no encontrada",
                f"No encuentro «{os.path.basename(ruta)}» en la carpeta de la app.\n\n"
                "Elige con qué base quieres trabajar:",
                disponibles, 0, False)
            if ok and eleccion:
                set_active_db(os.path.join(APP_DIR, eleccion))
                save_ui_config(db_name=eleccion)
                return
        set_active_db(ruta)  # se vuelve a crear vacía, como antes
        save_ui_config(db_name=os.path.basename(ruta))
        return

    nombre, ok = QtWidgets.QInputDialog.getText(
        None, "Base de datos",
        "Ponle nombre a tu base de datos.\n\n"
        "Se creará «nombre.db» junto a la aplicación (por ejemplo, costura.db\n"
        "o cocina.db). Si lo dejas vacío se usará la general: transcripts.db.\n\n"
        "Nombre:",
        text=DB_NAME_DEFAULT,
    )
    if not ok:
        nombre = ""
    nombre = _sanitize_db_name(nombre)
    set_active_db(os.path.join(APP_DIR, nombre + ".db"))
    save_ui_config(db_name=nombre + ".db")


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # base limpia y consistente para el QSS
    app.setStyleSheet(QSS)
    _ensure_initial_db()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
