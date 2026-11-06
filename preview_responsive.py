"""Vista previa de la interfaz a tamaños de dispositivo (el «devtools» de escritorio).

Como en el navegador: eliges móvil, tableta o PC, y ves cómo responde la app.

Uso:
    python3 preview_responsive.py                 # pestaña Ajustes, 3 tamaños
    python3 preview_responsive.py --tab all       # las tres pestañas
    python3 preview_responsive.py --sizes 432x960,800x1280,1200x800
    python3 preview_responsive.py --open          # abre la galería HTML al terminar
    python3 preview_responsive.py --live 432x960  # ventana real a ese tamaño

Las capturas van a `preview/` y se genera `preview/index.html` con todas, para
compararlas de un vistazo.
"""

from __future__ import annotations

import argparse
import html
import os
import sys

TABS = {"transcripcion": 0, "preguntar": 1, "ajustes": 2}

PRESETS = {
    "moto-g54": (432, 960),
    "tablet": (800, 1280),
    "escritorio": (1200, 800),
}


def _parse_sizes(raw: str | None) -> list[tuple[str, int, int]]:
    if not raw:
        return [(name, w, h) for name, (w, h) in PRESETS.items()]
    out = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "x" not in item:
            raise SystemExit(f"Tamaño no válido: {item!r} (usa ANCHOxALTO, p. ej. 432x960)")
        width, height = item.lower().split("x", 1)
        out.append((item, int(width), int(height)))
    return out


def _build_gallery(rutas, out_dir: str, sizes) -> str:
    """Página HTML con las capturas agrupadas por tamaño, estilo devtools."""
    por_tamano: dict[str, list[tuple[str, str]]] = {}
    for ruta, tamano, pestaña in rutas:
        por_tamano.setdefault(tamano, []).append((pestaña, ruta))

    bloques = []
    for tamano, capturas in por_tamano.items():
        # modo = el que usaría la app con ese ancho (mismos breakpoints)
        if "x" in tamano:
            ancho = int(tamano.lower().split("x")[0])
        else:
            ancho = sizes.get(tamano, (0, 0))[0]
        modo = ("compact" if ancho < 600 else "medium" if ancho < 900 else "wide")
        imgs = "".join(
            f'<figure><img src="{html.escape(ruta)}" alt="{html.escape(pestaña)}">'
            f"<figcaption>{html.escape(pestaña)}</figcaption></figure>"
            for pestaña, ruta in capturas
        )
        bloques.append(
            f'<section><h2>{html.escape(tamano)} '
            f'<span class="modo">{modo}</span></h2>'
            f'<div class="fila">{imgs}</div></section>'
        )

    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>BuscadorYT · vista previa</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ background:#141418; color:#e8e8f0; font:14px/1.4 -apple-system, system-ui, sans-serif;
         margin:0; padding:24px; }}
  h1 {{ font-size:18px; margin:0 0 4px; }}
  p.sub {{ color:#9b9bae; margin:0 0 24px; }}
  section {{ margin-bottom:32px; }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#c9c9d8;
        margin:0 0 10px; }}
  .modo {{ display:inline-block; margin-left:8px; padding:2px 8px; border-radius:99px;
           background:#262633; color:#8f7bff; font-size:11px; letter-spacing:.02em; }}
  .fila {{ display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }}
  figure {{ margin:0; background:#1b1b22; border:1px solid #2a2a35; border-radius:12px;
            padding:10px; }}
  img {{ display:block; max-height:640px; width:auto; border-radius:8px; }}
  figcaption {{ color:#9b9bae; font-size:12px; margin-top:6px; }}
</style></head>
<body>
<h1>BuscadorYT · vista previa responsable</h1>
<p class="sub">Generado con <code>preview_responsive.py</code> · breakpoints: compact &lt;600 · medium &lt;900 · wide</p>
{''.join(bloques)}
</body></html>
"""
    ruta = os.path.join(out_dir, "index.html")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(description="Capturas de la interfaz a tamaños de dispositivo")
    parser.add_argument("--tab", default="ajustes",
                        help="transcripcion | preguntar | ajustes | all (por defecto ajustes)")
    parser.add_argument("--sizes", default=None,
                        help="ANCHOxALTO separados por comas (por defecto los presets)")
    parser.add_argument("--out", default="preview", help="carpeta de salida")
    parser.add_argument("--open", action="store_true", help="abre la galería al terminar")
    parser.add_argument("--live", default=None, metavar="ANCHOxALTO",
                        help="no captura: abre la ventana real a ese tamaño")
    parser.add_argument("--reading", action="store_true",
                        help="captura el modo lectura (solo el texto)")
    parser.add_argument("--select", type=int, default=None, metavar="FILA",
                        help="selecciona esa fila de la lista antes de capturar")
    args = parser.parse_args()

    if args.live:
        width, height = (int(v) for v in args.live.lower().split("x"))
        from PySide6 import QtWidgets
        import BuscadorYT as app_mod
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setStyleSheet(app_mod.QSS)
        ventana = app_mod.MainWindow()
        ventana.resize(width, height)
        ventana.show()
        return app.exec()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    import BuscadorYT as app_mod

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(app_mod.QSS)

    if args.tab == "all":
        pestañas = list(TABS.items())
    elif args.tab in TABS:
        pestañas = [(args.tab, TABS[args.tab])]
    else:
        raise SystemExit(f"Pestaña desconocida: {args.tab!r} (usa {', '.join(TABS)} o all)")

    sizes = _parse_sizes(args.sizes)
    os.makedirs(args.out, exist_ok=True)

    ventana = app_mod.MainWindow()
    # Sin show() la ventana no recibe resizeEvent (y los breakpoints no cambian).
    ventana.show()
    app.processEvents()
    generadas = []
    for nombre, width, height in sizes:
        ventana.resize(width, height)
        for pestaña, indice in pestañas:
            ventana.tabs.setCurrentIndex(indice)
            if args.select is not None and indice == 0:
                ventana.listbox.setCurrentRow(args.select)
            if args.reading:
                ventana.tabs.setCurrentIndex(0)
                ventana.btn_read.setChecked(True)
            app.processEvents()
            sufijo = "_lectura" if args.reading else ""
            archivo = f"{nombre}_{pestaña}{sufijo}.png".lower()
            ruta = os.path.join(args.out, archivo)
            ventana.grab().save(ruta)
            if args.reading:
                ventana.btn_read.setChecked(False)
            generadas.append((ruta, nombre, pestaña + (" · lectura" if args.reading else "")))
            print(f"  {nombre:12} {pestaña:14} → {ruta}  (modo {app_mod.mode_for(width)})")

    ventana.close()
    galeria = _build_gallery(generadas, args.out, dict(PRESETS))
    print(f"Galería: {galeria}")
    if args.open:
        from PySide6 import QtGui, QtCore
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(galeria)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
