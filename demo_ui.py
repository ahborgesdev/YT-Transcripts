"""
Demo de interfaz — BuscadorYT con PySide6 (Qt6)
Solo es un vistazo al look moderno; no descarga ni toca la BD.
Ejecuta:  python3 demo_ui.py
"""

import sys
from PySide6 import QtWidgets, QtCore, QtGui

# ─────────────────────────────────────────────
# TEMA DARK MODERNO (QSS)
# ─────────────────────────────────────────────
QSS = """
* {
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #e8e8f0;
}

QMainWindow, QWidget {
    background-color: #15151d;
}

/* ── Barra de título / cabecera ── */
QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.2px;
}
QLabel#appSubtitle {
    font-size: 12px;
    color: #8b8b9e;
}
QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #9b9bae;
    text-transform: uppercase;
    letter-spacing: 0.6px;
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
QTextEdit, QTextBrowser {
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
"""

TRANSCRIPT_MUESTRA = """El universo es vasto y, sin embargo, todo lo que conocemos parece caber en un puñado de leyes sencillas. La gravedad curva el espacio, la luz se propaga en ondas y la materia se organiza en estructuras cada vez más complejas.

Cuando observamos el cielo nocturno, estamos mirando hacia atrás en el tiempo. La luz de las estrellas más lejanas ha viajado miles de millones de años para llegar hasta nosotros, y en ese viaje nos cuenta la historia del cosmos.

Pero la ciencia no se detiene en la contemplación. Cada respuesta abre nuevas preguntas, y cada descubrimiento nos obliga a revisar lo que creíamos saber. Esa es, quizá, la lección más valiosa: el conocimiento no es un destino, sino un camino.

Hoy hablaremos de tres ideas que cambiaron nuestra forma de entender la realidad: la relatividad, la mecánica cuántica y la teoría de la evolución. Tres revoluciones que, en menos de dos siglos, transformaron por completo la imagen que tenemos de nosotros mismos y del universo que habitamos."""


class DemoWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YT Transcripts · Demo de interfaz")
        self.resize(1180, 780)
        self.setMinimumSize(900, 600)
        self._build_ui()

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
        subtitle = QtWidgets.QLabel("Descarga, guarda y exporta transcripciones de YouTube")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        db_label = QtWidgets.QLabel("SQLite · transcripts.db")
        db_label.setObjectName("appSubtitle")
        header.addWidget(db_label)
        root.addLayout(header)

        divider = QtWidgets.QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        root.addWidget(divider)

        # ── Splitter: izquierda / derecha ──
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([360, 800])

    def _build_left_panel(self):
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # URL
        url_label = QtWidgets.QLabel("URL O ID DEL VIDEO")
        url_label.setObjectName("sectionLabel")
        layout.addWidget(url_label)

        url = QtWidgets.QLineEdit()
        url.setPlaceholderText("https://www.youtube.com/watch?v=…  o  el ID de 11 caracteres")
        url.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        layout.addWidget(url)

        # Idioma
        lang_label = QtWidgets.QLabel("IDIOMA PREFERIDO")
        lang_label.setObjectName("sectionLabel")
        layout.addWidget(lang_label)

        lang_row = QtWidgets.QHBoxLayout()
        lang_row.setSpacing(14)
        for text, checked in [("ES", True), ("EN", False), ("Auto", False)]:
            rb = QtWidgets.QRadioButton(text)
            rb.setChecked(checked)
            lang_row.addWidget(rb)
        lang_row.addStretch(1)
        layout.addLayout(lang_row)

        # Descargar
        download = QtWidgets.QPushButton("⬇  Descargar transcripción")
        download.setObjectName("primary")
        download.setCursor(QtCore.Qt.PointingHandCursor)
        download.setMinimumHeight(40)
        layout.addWidget(download)

        # Progreso
        progress = QtWidgets.QProgressBar()
        progress.setRange(0, 0)  # indeterminado
        progress.setVisible(False)
        layout.addWidget(progress)

        div2 = QtWidgets.QFrame()
        div2.setObjectName("divider")
        div2.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(div2)

        # Lista de transcripciones
        list_label = QtWidgets.QLabel("TUS TRANSCRIPCIONES")
        list_label.setObjectName("sectionLabel")
        layout.addWidget(list_label)

        lista = QtWidgets.QListWidget()
        samples = [
            "El universo en tres revoluciones  ·  Kurzgesagt  [es]",
            "How quantum computers work  ·  Veritasium  [en]",
            "Historia de la música clásica  ·  Jaime Altozano  [es]",
            "The Fermi Paradox explained  ·  Kurzgesagt  [en]",
            "Aprende Python desde cero  ·  MoureDev  [es]",
        ]
        for i, s in enumerate(samples):
            item = QtWidgets.QListWidgetItem(s)
            lista.addItem(item)
        lista.setCurrentRow(0)
        layout.addWidget(lista, 1)

        # Botones de acción
        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)
        btn_mod = QtWidgets.QPushButton("Modificar")
        btn_mod.setCursor(QtCore.Qt.PointingHandCursor)
        btn_export = QtWidgets.QPushButton("Exportar a PDF")
        btn_export.setCursor(QtCore.Qt.PointingHandCursor)
        btn_del = QtWidgets.QPushButton("Eliminar")
        btn_del.setObjectName("danger")
        btn_del.setCursor(QtCore.Qt.PointingHandCursor)
        actions.addWidget(btn_mod)
        actions.addWidget(btn_export)
        actions.addWidget(btn_del)
        layout.addLayout(actions)

        return panel

    def _build_right_panel(self):
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Meta
        title = QtWidgets.QLabel("El universo en tres revoluciones")
        title.setObjectName("appTitle")
        meta = QtWidgets.QLabel("https://youtu.be/dQw4w9WgXcQ  ·  idioma: es  ·  Kurzgesagt  ·  1.842 caracteres")
        meta.setObjectName("appSubtitle")
        layout.addWidget(title)
        layout.addWidget(meta)

        # Visor de transcripción
        transcript = QtWidgets.QTextEdit()
        transcript.setReadOnly(True)
        transcript.setPlainText(TRANSCRIPT_MUESTRA)
        f = QtGui.QFont()
        f.setFamily("-apple-system")
        f.setPointSize(15)
        transcript.setFont(f)
        transcript.document().setDefaultStyleSheet(
            "body { line-height: 150%; }"
        )
        layout.addWidget(transcript, 1)

        # Log
        log_label = QtWidgets.QLabel("REGISTRO")
        log_label.setObjectName("sectionLabel")
        layout.addWidget(log_label)

        log = QtWidgets.QTextEdit()
        log.setReadOnly(True)
        log.setFixedHeight(88)
        mono = QtGui.QFont("Menlo")
        mono.setPointSize(11)
        log.setFont(mono)
        log.setPlainText(
            "[14:02:11] ✅ Guardado: dQw4w9WgXcQ [El universo…] [Kurzgesagt] [es] (1.842 chars)\n"
            "[14:01:58] ⏳ Descargando transcripción para dQw4w9WgXcQ …\n"
            "[13:58:40] 📄 PDF exportado: El_universo_en_tres_revoluciones.pdf"
        )
        layout.addWidget(log)

        return panel


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # base limpia y consistente para el QSS
    app.setStyleSheet(QSS)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
