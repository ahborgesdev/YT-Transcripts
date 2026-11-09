#!/usr/bin/env python3
"""Previsualiza el layout móvil sin compilar la APK.

Ejecuta la app real con el backend `offscreen` de Qt, la redimensiona a un
tamaño de teléfono (360x800 dp por defecto) y guarda una captura. Sirve para
iterar el diseño de `mobile.py` sin esperar 30 minutos a buildozer.

Uso:
    ../.venv/bin/python scripts/preview_mobile.py [ancho] [alto] [salida.png]

Requiere `app/BuscadorYT.py` (lo copia `build.sh`) y PySide6 de escritorio.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT_DIR = HERE.parent / ".android-build"
sys.path.insert(0, str(HERE))

# Debe fijarse antes de importar PySide6. La salida vive fuera de android/
# para que buildozer no la empaquete en la APK.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("BUSCADOR_DATA_DIR", str(OUT_DIR / "preview-data"))


def main() -> int:
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 360
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else OUT_DIR / "preview_mobile.png"

    from PySide6 import QtCore, QtWidgets

    import main as android_main

    app, win, data_dir = android_main.create_app_and_window([sys.argv[0]])
    win.show()
    # En la plataforma offscreen hay que dejar que Qt procese el show() antes
    # de redimensionar; si no, vuelve a su tamaño preferido.
    app.processEvents()
    win.resize(width, height)
    app.processEvents()

    def _grab() -> None:
        pixmap = win.grab()
        output.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(output))
        print(f"Captura: {output} ({pixmap.width()}x{pixmap.height()})")
        print(f"Datos de la prueba: {data_dir}")
        app.quit()

    QtCore.QTimer.singleShot(1200, _grab)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
