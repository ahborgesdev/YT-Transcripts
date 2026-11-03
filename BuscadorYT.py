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

/* ── Botones ── */
QPushButton {
    background-color: #262633;
    border: 1px solid #34343f;
    border-radius: 8px;
    padding: 9px 14px;
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

/* Botones compactos del tamaño de letra (lector) */
QPushButton#fontBtn {
    padding: 2px 9px;
    min-width: 14px;
    font-size: 13px;
    font-weight: 600;
    color: #b9b9c8;
}
QPushButton#fontBtn:hover {
    color: #ffffff;
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
def _escribir_pdf(filepath, title, content, url, owner=""):
    """Genera el PDF de una transcripción con «Página N de M» al pie de cada página."""
    import html as html_module

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

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

    doc.build(story, canvasmaker=_NumberedCanvas)


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

class MainWindow(QtWidgets.QMainWindow):
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

        self.setWindowTitle("YT Transcripts")
        self.resize(1200, 800)
        self.setMinimumSize(1100, 720)

        self._build_ui()

        init_db()
        self._refresh_list()

        if not YT_API_AVAILABLE:
            self._log("⚠️  Módulo 'youtube-transcript-api' no encontrado.\n"
                      "   Instálalo con:  pip install youtube-transcript-api\n", "warn")

    # ── Layout principal ──────────────────────
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        # ── Cabecera ──
        header = QtWidgets.QHBoxLayout()
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
        db_label = QtWidgets.QLabel(f"SQLite · {os.path.basename(DB_PATH)}")
        db_label.setObjectName("appSubtitle")
        header.addWidget(db_label)
        root.addLayout(header)

        divider = QtWidgets.QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        root.addWidget(divider)

        # ── Splitter: izquierda / derecha ──
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([380, 800])

        # ── Registro (siempre visible, debajo del splitter) ──
        log_label = QtWidgets.QLabel("REGISTRO")
        log_label.setObjectName("sectionLabel")
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
        self.btn_download.setMinimumHeight(40)
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
        self.listbox.currentRowChanged.connect(self._on_select)
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

        # Meta info + control del tamaño de letra
        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(6)

        info_box = QtWidgets.QVBoxLayout()
        info_box.setSpacing(1)
        self.lbl_title = QtWidgets.QLabel("Selecciona o descarga una transcripción")
        self.lbl_title.setObjectName("appTitle")
        self.lbl_meta = QtWidgets.QLabel("")
        self.lbl_meta.setObjectName("appSubtitle")
        # La línea de datos lleva el enlace al vídeo: clic = navegador del sistema
        self.lbl_meta.setTextFormat(Qt.RichText)
        self.lbl_meta.setOpenExternalLinks(True)
        self.lbl_meta.setTextInteractionFlags(
            Qt.TextBrowserInteraction  # enlaces con clic + texto seleccionable
        )
        self.lbl_meta.setToolTip("Clic en el enlace para ver el vídeo en el navegador")
        info_box.addWidget(self.lbl_title)
        info_box.addWidget(self.lbl_meta)
        info_row.addLayout(info_box, 1)

        self.lbl_font_size = QtWidgets.QLabel("")
        self.lbl_font_size.setObjectName("appSubtitle")
        self.lbl_font_size.setMinimumWidth(42)
        self.lbl_font_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        info_row.addWidget(self.lbl_font_size, 0, Qt.AlignBottom)

        self.btn_font_dec = QtWidgets.QPushButton("A−")
        self.btn_font_dec.setObjectName("fontBtn")
        self.btn_font_dec.setCursor(Qt.PointingHandCursor)
        self.btn_font_dec.setToolTip("Letra más pequeña (Ctrl + −)")
        self.btn_font_dec.clicked.connect(lambda: self._nudge_read_font(-1))
        info_row.addWidget(self.btn_font_dec, 0, Qt.AlignBottom)

        self.btn_font_inc = QtWidgets.QPushButton("A+")
        self.btn_font_inc.setObjectName("fontBtn")
        self.btn_font_inc.setCursor(Qt.PointingHandCursor)
        self.btn_font_inc.setToolTip("Letra más grande (Ctrl + +)")
        self.btn_font_inc.clicked.connect(lambda: self._nudge_read_font(1))
        info_row.addWidget(self.btn_font_inc, 0, Qt.AlignBottom)

        layout.addLayout(info_row)

        # Visor de transcripción
        self.texto = QtWidgets.QTextEdit()
        self.texto.setObjectName("transcriptView")   # tamaño de letra: ver read_font_qss()
        self.texto.setReadOnly(True)
        self.texto.setPlaceholderText("Aquí se mostrará el texto de la transcripción…")
        layout.addWidget(self.texto, 1)

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
        # Ctrl + rueda sobre el lector = zoom de la letra
        if obj is self.texto.viewport() and event.type() == QtCore.QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                self._nudge_read_font(1 if event.angleDelta().y() > 0 else -1)
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
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        status_row = QtWidgets.QHBoxLayout()
        self.lbl_rag_status = QtWidgets.QLabel("Índice semántico: sin comprobar")
        self.lbl_rag_status.setObjectName("appSubtitle")
        status_row.addWidget(self.lbl_rag_status, 1)

        self.btn_rag_key = QtWidgets.QPushButton("Ajustes")
        self.btn_rag_key.setCursor(Qt.PointingHandCursor)
        self.btn_rag_key.setToolTip("Elegir el redactor (IA), la clave API y el modelo")
        self.btn_rag_key.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        status_row.addWidget(self.btn_rag_key)

        self.btn_rag_index = QtWidgets.QPushButton("Indexar")
        self.btn_rag_index.setCursor(Qt.PointingHandCursor)
        self.btn_rag_index.setToolTip("Indexar transcripciones nuevas o modificadas (semántica local)")
        self.btn_rag_index.clicked.connect(lambda: self._rag_start_index(reindex=False))
        status_row.addWidget(self.btn_rag_index)
        layout.addLayout(status_row)

        ask_row = QtWidgets.QHBoxLayout()
        self.rag_input = QtWidgets.QLineEdit()
        self.rag_input.setPlaceholderText("Pregunta sobre tus transcripciones: «¿qué dijo Dolina sobre los ángeles?»")
        self.rag_input.returnPressed.connect(self._rag_ask)
        self.rag_input.setMinimumHeight(36)
        ask_row.addWidget(self.rag_input, 1)

        self.btn_rag_ask = QtWidgets.QPushButton("Preguntar")
        self.btn_rag_ask.setObjectName("primary")
        self.btn_rag_ask.setCursor(Qt.PointingHandCursor)
        self.btn_rag_ask.setMinimumHeight(36)
        self.btn_rag_ask.clicked.connect(self._rag_ask)
        ask_row.addWidget(self.btn_rag_ask)
        layout.addLayout(ask_row)

        self.rag_answer = QtWidgets.QTextBrowser()
        self.rag_answer.setOpenLinks(False)
        self.rag_answer.setPlaceholderText(
            "La respuesta se redacta solo con tus transcripciones y cita los pasajes.\n"
            "Si no configuras clave API, verás los fragmentos más relevantes."
        )
        self.rag_answer.anchorClicked.connect(self._on_rag_anchor)
        layout.addWidget(self.rag_answer, 3)

        hits_label = QtWidgets.QLabel("PASAJES RECUPERADOS (clic para abrir en la transcripción)")
        hits_label.setObjectName("sectionLabel")
        layout.addWidget(hits_label)

        self.rag_hits = QtWidgets.QListWidget()
        self.rag_hits.setMaximumHeight(190)
        self.rag_hits.itemClicked.connect(self._on_rag_hit_clicked)
        layout.addWidget(self.rag_hits, 2)

        return panel

    # ── Pestaña «Ajustes» ─────────────────────
    def _settings_row(self, etiqueta, campo):
        """Fila «etiqueta: campo» con la etiqueta de ancho fijo."""
        fila = QtWidgets.QHBoxLayout()
        fila.setSpacing(10)
        lbl = QtWidgets.QLabel(etiqueta)
        lbl.setFixedWidth(180)
        fila.addWidget(lbl)
        if isinstance(campo, QtWidgets.QLayout):
            fila.addLayout(campo, 1)
        else:
            fila.addWidget(campo, 1)
        return fila

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
        layout.addLayout(self._settings_row("Redactor", self.cmb_provider))

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
        layout.addLayout(self._settings_row("Modelo", modelo_fila))

        self.edt_base_url = QtWidgets.QLineEdit()
        self.edt_base_url.setPlaceholderText("https://api.deepseek.com")
        layout.addLayout(self._settings_row("Dirección (base_url)", self.edt_base_url))

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
        layout.addLayout(self._settings_row("Clave API", clave_fila))

        nums = QtWidgets.QHBoxLayout()
        nums.setSpacing(10)
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
        nums.addWidget(self.spn_temp)
        nums.addWidget(QtWidgets.QLabel("temperatura"))
        nums.addSpacing(22)
        nums.addWidget(self.spn_max_tokens)
        nums.addWidget(QtWidgets.QLabel("máx. tokens"))
        nums.addStretch(1)
        layout.addLayout(self._settings_row("Ajustes del modelo", nums))

        botones = QtWidgets.QHBoxLayout()
        botones.setSpacing(8)
        self.btn_llm_save = QtWidgets.QPushButton("Guardar")
        self.btn_llm_save.setObjectName("primary")
        self.btn_llm_save.setCursor(Qt.PointingHandCursor)
        self.btn_llm_save.clicked.connect(self._settings_save)
        botones.addWidget(self.btn_llm_save)

        self.btn_llm_test = QtWidgets.QPushButton("Probar conexión")
        self.btn_llm_test.setCursor(Qt.PointingHandCursor)
        self.btn_llm_test.setToolTip("Hace una petición mínima al redactor con los datos del formulario")
        self.btn_llm_test.clicked.connect(self._llm_test)
        botones.addWidget(self.btn_llm_test)

        self.btn_llm_reload = QtWidgets.QPushButton("Recargar del disco")
        self.btn_llm_reload.setCursor(Qt.PointingHandCursor)
        self.btn_llm_reload.setToolTip("Vuelve a leer rag_config.json (descarta cambios sin guardar)")
        self.btn_llm_reload.clicked.connect(self._settings_load)
        botones.addWidget(self.btn_llm_reload)
        botones.addStretch(1)
        layout.addLayout(botones)

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

        lector = QtWidgets.QHBoxLayout()
        lector.setSpacing(8)
        self.spn_font_size = QtWidgets.QSpinBox()
        self.spn_font_size.setRange(READ_FONT_MIN, READ_FONT_MAX)
        self.spn_font_size.setSuffix(" pt")
        self.spn_font_size.setFixedWidth(90)
        self.spn_font_size.setValue(self._ui_cfg["read_font_size"])
        self.spn_font_size.valueChanged.connect(self._on_font_spin_changed)
        lector.addWidget(self.spn_font_size)
        btn_font_reset = QtWidgets.QPushButton(f"Restablecer ({READ_FONT_DEFAULT} pt)")
        btn_font_reset.setCursor(Qt.PointingHandCursor)
        btn_font_reset.clicked.connect(self._reset_read_font)
        lector.addWidget(btn_font_reset)
        lector.addStretch(1)
        layout.addLayout(self._settings_row("Tamaño de letra", lector))

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

        datos = QtWidgets.QHBoxLayout()
        datos.setSpacing(8)
        self.btn_index_now = QtWidgets.QPushButton("Indexar ahora")
        self.btn_index_now.setCursor(Qt.PointingHandCursor)
        self.btn_index_now.clicked.connect(lambda: self._rag_start_index(reindex=False))
        datos.addWidget(self.btn_index_now)

        self.btn_index_rebuild = QtWidgets.QPushButton("Reindexar todo")
        self.btn_index_rebuild.setCursor(Qt.PointingHandCursor)
        self.btn_index_rebuild.setToolTip("Reconstruye el índice completo (tras cambiar de modelo)")
        self.btn_index_rebuild.clicked.connect(lambda: self._rag_start_index(reindex=True))
        datos.addWidget(self.btn_index_rebuild)

        btn_open_dir = QtWidgets.QPushButton("Abrir carpeta de datos")
        btn_open_dir.setCursor(Qt.PointingHandCursor)
        btn_open_dir.clicked.connect(self._open_data_dir)
        datos.addWidget(btn_open_dir)
        datos.addStretch(1)
        layout.addLayout(datos)

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
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # base limpia y consistente para el QSS
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
