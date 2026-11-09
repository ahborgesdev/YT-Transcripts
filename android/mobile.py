"""Ajustes de interfaz para pantallas de móvil.

La app de escritorio está pensada para 1200x800 con dos paneles en horizontal.
En un teléfono (~360x800 dp) eso no cabe: aquí se reorganiza la MISMA ventana
sin tocar `BuscadorYT.py`:

* una sola columna (splitter vertical) en lugar de dos paneles;
* cabecera compacta (título y selector de base de datos en dos filas);
* sin barra de menú ni registro;
* pestañas «Transcripción | Preguntar | Ajustes» visibles: el RAG usa BM25
  (rag_android.py) y la IA se llama por la API, sin fastembed/ONNX;
* sin cuaderno PDF (reportlab no se empaqueta en Android);
* objetivos táctiles algo más altos.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

#: Mínimo táctil recomendado por Material Design (dp).
_TOUCH_TARGET = 44


def _hide_label(win: QtWidgets.QWidget, text: str) -> None:
    for label in win.findChildren(QtWidgets.QLabel):
        if label.text().strip() == text:
            label.hide()


def _content(win: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Widget con el layout raíz (detrás del scroll global, si lo hay)."""
    scroll = getattr(win, "_outer_scroll", None)
    if scroll is not None and scroll.widget() is not None:
        return scroll.widget()
    return win.centralWidget()


def _hide_subtitle(win: QtWidgets.QWidget) -> None:
    """La cabecera de escritorio ocupa dos líneas: en móvil sobra."""
    for label in win.findChildren(QtWidgets.QLabel):
        if label.objectName() == "appSubtitle" and label.text().startswith("Descarga, guarda"):
            label.hide()
            return


def _compact_header(win: QtWidgets.QWidget) -> None:
    """Pone el selector de base de datos en su propia fila."""
    root = _content(win).layout()
    if root is None or root.count() == 0:
        return
    header_item = root.itemAt(0)
    header = header_item.layout() if header_item is not None else None
    # La cabecera puede ser un widget (con su propio layout) en vez de un
    # layout suelto: se acepta cualquiera de las dos formas.
    if header is None and header_item is not None and header_item.widget() is not None:
        header = header_item.widget().layout()
    if header is None:
        return

    cmb = getattr(win, "cmb_db", None)
    if cmb is None:
        return

    db_row = None
    for index in range(header.count()):
        item = header.itemAt(index)
        layout = item.layout() if item is not None else None
        if layout is not None and layout.indexOf(cmb) >= 0:
            db_row = layout
            break
    if db_row is None:
        return

    header.removeItem(db_row)
    root.insertLayout(1, db_row)
    db_row.setSpacing(8)
    # Sin esto, el layout insertado se centra y deja un hueco a la izquierda.
    db_row.setAlignment(QtCore.Qt.AlignLeft)
    _hide_label(win, "Base de datos:")

    for name in ("btn_db_open",):
        button = getattr(win, name, None)
        if button is not None:
            button.hide()
    cmb.setMinimumWidth(0)
    cmb.setMaximumWidth(170)

    new_button = getattr(win, "btn_db_new", None)
    if new_button is not None:
        new_button.setFixedWidth(38)
        new_button.setMinimumHeight(_TOUCH_TARGET)


def _single_column(win: QtWidgets.QWidget) -> None:
    splitter = win.findChild(QtWidgets.QSplitter)
    if splitter is None:
        return
    splitter.setOrientation(QtCore.Qt.Vertical)
    splitter.setHandleWidth(14)  # fácil de arrastrar con el dedo
    splitter.setChildrenCollapsible(True)

    # Tras mostrarse la ventana ya hay altura real: reparto 45/55.
    def _balance() -> None:
        height = splitter.height()
        if height > 0:
            splitter.setSizes([int(height * 0.42), int(height * 0.58)])

    QtCore.QTimer.singleShot(0, _balance)


def _enable_tabs(win: QtWidgets.QWidget) -> None:
    """Mantiene las tres pestañas (incluidas Preguntar y Ajustes)."""
    tabs = getattr(win, "tabs", None)
    if tabs is None:
        return
    tabs.tabBar().show()
    tabs.tabBar().setMinimumHeight(42)  # cómodo para el dedo
    if tabs.currentIndex() != 0:
        tabs.setCurrentIndex(0)


class _WrapHeightFitter(QtCore.QObject):
    """Mantiene la altura de un QLabel con wordWrap al cambiar el ancho.

    Qt no siempre recalcula `heightForWidth()` al redimensionar (pasa al
    rotar el móvil): la última línea del título queda cortada. Este filtro
    ajusta la altura mínima sin tocar el resto del layout.
    """

    def __init__(self, label: QtWidgets.QLabel):
        super().__init__(label)
        self._label = label
        self._pending = False
        label.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 (API de Qt)
        if obj is self._label and event.type() in (
                QtCore.QEvent.Resize, QtCore.QEvent.Show):
            self._schedule()
        return False

    def _schedule(self) -> None:
        if self._pending:
            return
        self._pending = True
        QtCore.QTimer.singleShot(0, self._sync)

    def _sync(self) -> None:
        self._pending = False
        label = self._label
        width = label.width()
        if width <= 0:
            return
        height = label.heightForWidth(width)
        if height > 0 and label.minimumHeight() != height:
            label.setMinimumHeight(height)


def _adapt_widgets(win: QtWidgets.QWidget) -> None:
    # El PDF se genera con reportlab, que no se empaqueta en la APK: mejor no
    # ofrecer un botón que sólo puede fallar.
    export = getattr(win, "btn_export", None)
    if export is not None:
        export.hide()

    # Cuaderno de preguntas en PDF: necesita reportlab, que no va en la APK.
    for name in ("btn_qa_save", "chk_qa_open", "btn_qa_open", "lbl_qa_cuaderno"):
        widget = getattr(win, name, None)
        if widget is not None:
            widget.hide()

    # El estado del índice puede ser largo; que no empuje el ancho.
    status = getattr(win, "lbl_rag_status", None)
    if status is not None:
        status.setWordWrap(True)
        status.setMinimumWidth(0)
        status.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                             QtWidgets.QSizePolicy.Preferred)

    # Etiquetas largas de la pestaña «Preguntar»: que envuelvan en vez de
    # forzar el ancho de la ventana (a 360 dp eran 532 px).
    for label in win.findChildren(QtWidgets.QLabel):
        if label.text().startswith("PASAJES RECUPERADOS"):
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                QtWidgets.QSizePolicy.Preferred)

    # Títulos largos de YouTube: que envuelvan en vez de empujar el ancho.
    fitters = []
    for name in ("lbl_title", "lbl_meta"):
        label = getattr(win, name, None)
        if label is not None:
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                QtWidgets.QSizePolicy.Preferred)
            fitters.append(_WrapHeightFitter(label))
    # Evita que el recolector se lleve los filtros.
    win._mobile_wrap_fitters = fitters  # type: ignore[attr-defined]

    # El tamaño en puntos ocupa sitio en la fila del título; los botones A-/A+
    # ya lo indican.
    font_label = getattr(win, "lbl_font_size", None)
    if font_label is not None:
        font_label.hide()

    for name in ("btn_download", "btn_modify", "btn_delete"):
        button = getattr(win, name, None)
        if button is not None:
            button.setMinimumHeight(_TOUCH_TARGET)

    for name in ("btn_font_dec", "btn_font_inc"):
        button = getattr(win, name, None)
        if button is not None:
            button.setMinimumSize(36, 32)


def apply_mobile_layout(win: QtWidgets.QMainWindow) -> None:
    """Aplica el aspecto móvil a `win` (idempotente)."""
    win.setMinimumSize(0, 0)

    menu_bar = win.menuBar()
    if menu_bar is not None:
        menu_bar.hide()

    for layout in (_content(win).layout(),):
        if layout is not None:
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(8)

    # Botones y campos más compactos: con el padding de escritorio tres
    # botones seguidos no caben en 360 dp.
    win.setStyleSheet(
        "QPushButton { padding: 8px 6px; font-size: 12px; }\n"
        "QLineEdit { padding: 8px 10px; }\n"
        "QLabel#appTitle { font-size: 17px; }\n"
        "QTabBar::tab { padding: 9px 12px; font-size: 13px; }\n"
    )

    _hide_subtitle(win)
    _compact_header(win)
    _single_column(win)
    _enable_tabs(win)
    _adapt_widgets(win)

    log_area = getattr(win, "log_area", None)
    if log_area is not None:
        log_area.hide()
    _hide_label(win, "REGISTRO")
