"""Piezas de responsividad mobile-first para BuscadorYT.

La idea es la de Bootstrap, traducida a Qt:

* **Tokens**: una escala fija de espaciado (múltiplos de 8), para que todo
  respire igual en todas partes.
* **Breakpoints**: por ancho lógico del widget (dp), no por píxeles físicos.
  `compact` es móvil; `medium` tableta pequeña / ventana estrecha; `wide`
  escritorio.
* **FieldRow**: la fila «etiqueta | campo» pasa a «etiqueta encima del campo»
  en compact, que es el patrón de los formularios de toda la vida.
* **FlowLayout**: las hileras de botones hacen *wrap* como las utilidades
  flex de Bootstrap, en vez de comprimirse hasta desaparecer.

En Qt no hay `@media`: el equivalente es mirar `width()` en `resizeEvent` y
recolocar. Por eso `MainWindow` mezcla `ResponsiveMixin` y aplica el modo en
`_apply_breakpoint(mode)`.
"""

from PySide6 import QtCore, QtWidgets

# ── Breakpoints (ancho lógico, en dp) ─────────
COMPACT_MAX = 600      # móvil
MEDIUM_MAX = 900       # ventana estrecha / tableta

MODE_COMPACT = "compact"
MODE_MEDIUM = "medium"
MODE_WIDE = "wide"

# ── Tokens ────────────────────────────────────
SPACE_UNIT = 8
LABEL_WIDTH = 180


def space(n: float) -> int:
    """Espaciado de la casa: `space(1)` = 8 dp."""
    return int(round(SPACE_UNIT * n))


def mode_for(width: int) -> str:
    """Modo de maquetación para un ancho lógico dado."""
    if width < COMPACT_MAX:
        return MODE_COMPACT
    if width < MEDIUM_MAX:
        return MODE_MEDIUM
    return MODE_WIDE


class ResponsiveMixin:
    """Llama a `_apply_breakpoint(mode)` cuando cambia el ancho.

    Se mezcla con la ventana (`class MainWindow(ResponsiveMixin, QMainWindow)`)
    y solo avisa cuando el modo cambia de verdad, no en cada píxel. Un guardia
    evita reentradas si el propio recolocado dispara otro `resizeEvent`.
    """

    def resizeEvent(self, event):  # noqa: N802 (API de Qt)
        super().resizeEvent(event)
        mode = mode_for(self.width())
        if mode == getattr(self, "_layout_mode", None):
            return
        if getattr(self, "_in_breakpoint", False):
            return
        self._layout_mode = mode
        if hasattr(self, "_apply_breakpoint"):
            self._in_breakpoint = True
            try:
                self._apply_breakpoint(mode)
            finally:
                self._in_breakpoint = False


class FieldRow(QtWidgets.QWidget):
    """Fila de formulario adaptativa: etiqueta al lado o encima del campo.

    Además del breakpoint de la ventana, mira **su propio ancho**: en una
    ventana «medium» el panel derecho puede quedarse en ~300 dp y ahí la
    etiqueta de 180 dp no deja respirar al campo. Por debajo de
    `STACK_BELOW` la fila se apila sola.
    """

    STACK_BELOW = 460

    def __init__(self, label: str, field: QtWidgets.QWidget,
                 label_width: int = LABEL_WIDTH, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel(label)
        self.field = field
        self._label_width = label_width
        self._window_mode = MODE_WIDE
        self._mode = None

        self._grid = QtWidgets.QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(space(1.25))
        self._grid.setVerticalSpacing(space(0.25))
        self._grid.addWidget(self.label, 0, 0)
        self._grid.addWidget(self.field, 0, 1)
        self._grid.setColumnStretch(1, 1)
        self._apply()

    def set_mode(self, mode: str) -> None:
        self._window_mode = mode
        self._apply()

    def resizeEvent(self, event):  # noqa: N802 (API de Qt)
        super().resizeEvent(event)
        self._apply()

    def _apply(self) -> None:
        apilada = (self._window_mode == MODE_COMPACT
                   or self.width() < self.STACK_BELOW)
        mode = MODE_COMPACT if apilada else self._window_mode
        if mode == self._mode:
            return
        self._mode = mode
        self._grid.removeWidget(self.label)
        self._grid.removeWidget(self.field)
        if apilada:
            # Etiqueta encima y el campo a todo el ancho (patrón móvil).
            self._grid.addWidget(self.label, 0, 0, 1, 2)
            self._grid.addWidget(self.field, 1, 0, 1, 2)
            self.label.setMinimumWidth(0)
            self.label.setMaximumWidth(16777215)
        else:
            # Etiqueta a la izquierda con ancho fijo; el campo estira.
            self._grid.addWidget(self.label, 0, 0)
            self._grid.addWidget(self.field, 0, 1)
            self.label.setFixedWidth(self._label_width)


class FlowWidget(QtWidgets.QWidget):
    """Contenedor con FlowLayout que ocupa su ancho natural.

    La política `Maximum` evita que el layout padre lo estire: si los botones
    caben en una fila, se quedan en una fila; si no, el FlowLayout los parte.
    """

    def __init__(self, widgets, hspacing: int = space(1),
                 vspacing: int = space(1), parent=None):
        super().__init__(parent)
        self.flow = FlowLayout(self, hspacing=hspacing, vspacing=vspacing)
        for widget in widgets:
            self.flow.addWidget(widget)
        policy = self.sizePolicy()
        policy.setHeightForWidth(True)
        policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        policy.setVerticalPolicy(QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(policy)

    def setSpacing(self, spacing):  # noqa: N802
        self.flow.setSpacing(spacing)


class FlowLayout(QtWidgets.QLayout):
    """Layout que coloca los hijos en filas y hace wrap al llegar al borde."""

    def __init__(self, parent=None, hspacing: int = space(1),
                 vspacing: int = space(1)):
        super().__init__(parent)
        self._items = []
        self._h = hspacing
        self._v = vspacing
        self._busy = False
        self.setContentsMargins(0, 0, 0, 0)

    # ── API de QLayout ──
    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):  # noqa: N802
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # noqa: N802
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._do_layout(QtCore.QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):  # noqa: N802
        if self._busy:
            return
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802
        width = height = 0
        for item in self._items:
            hint = item.sizeHint()
            width += hint.width() + self._h
            height = max(height, hint.height())
        margins = self.contentsMargins()
        if self._items:
            width -= self._h
        return QtCore.QSize(width + margins.left() + margins.right(),
                            height + margins.top() + margins.bottom())

    def minimumSize(self):  # noqa: N802
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QtCore.QSize(margins.left() + margins.right(),
                                   margins.top() + margins.bottom())

    # ── Utilidad ──
    def setSpacing(self, spacing):  # noqa: N802
        self._h = self._v = int(spacing)
        self.invalidate()

    def _do_layout(self, rect: QtCore.QRect, test_only: bool) -> int:
        """Coloca los hijos en filas; devuelve la altura necesaria."""
        if self._busy:
            return rect.y()
        self._busy = True
        try:
            margins = self.contentsMargins()
            area = rect.adjusted(margins.left(), margins.top(),
                                 -margins.right(), -margins.bottom())
            x, y = area.x(), area.y()
            line_height = 0
            for item in self._items:
                hint = item.sizeHint()
                if x + hint.width() > area.right() and line_height > 0:
                    x = area.x()
                    y += line_height + self._v
                    line_height = 0
                if not test_only:
                    item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
                x += hint.width() + self._h
                line_height = max(line_height, hint.height())
            return y + line_height - rect.y() + margins.bottom()
        finally:
            self._busy = False
