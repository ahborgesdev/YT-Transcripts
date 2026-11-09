#!/usr/bin/env python3
"""Punto de entrada de la versión Android de YT Transcripts.

`pyside6-android-deploy` exige que el fichero de entrada se llame `main.py` y
que esté en el directorio del proyecto. Este lanzador es una capa fina sobre
`app/BuscadorYT.py` (copia de `../BuscadorYT.py` que refresca `build.sh`):

* añade `app/` y `vendor/` al `sys.path` (las dependencias puras de Python
  viajan dentro de la APK porque python-for-android sólo empaqueta PySide6);
* mueve los datos (SQLite, ui_config.json, rag_config.json) al directorio
  privado y escribible de la app, tal y como exige Android;
* instala un almacén de certificados raíz propio (Android no expone el
  almacén del sistema a CPython);
* adapta la ventana al formato móvil (una columna, sin menú ni registro).

El código de escritorio no se toca: todo lo específico de Android vive aquí.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_SRC = HERE / "app"
VENDOR = HERE / "vendor"


# ─────────────────────────────────────────────
# Entorno de ejecución
# ─────────────────────────────────────────────
def _prepare_sys_path() -> None:
    """Coloca las dependencias empaquetadas delante del resto de rutas."""
    for path in (HERE, VENDOR, APP_SRC):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def _data_dir() -> str:
    """Directorio privado y escribible de la aplicación.

    En Android, `QStandardPaths.AppDataLocation` apunta a
    /data/user/0/<paquete>/files. En escritorio (para pruebas) devuelve la
    carpeta habitual de datos de la app.
    """
    from PySide6.QtCore import QStandardPaths

    override = os.environ.get("BUSCADOR_DATA_DIR")
    candidates = [
        override,
        QStandardPaths.writableLocation(QStandardPaths.AppDataLocation),
        os.environ.get("ANDROID_PRIVATE"),
        str(HERE),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".write-probe")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            return candidate
        except OSError:
            continue
    return str(HERE)


def _install_ca_bundle(data_dir: str) -> str | None:
    """Escribe el bundle de CAs y se lo enseña a requests/ssl.

    `vendor/_cacert.py` lo genera `scripts/prepare_vendor.py` a partir de
    certifi. Android no tiene /etc/ssl/certs, así que sin esto cualquier
    petición HTTPS falla con "certificate verify failed".
    """
    try:
        from _cacert import CA_PEM  # type: ignore[import-not-found]
    except ImportError:
        return None

    ca_path = os.path.join(data_dir, "cacert.pem")
    try:
        needs_write = True
        if os.path.exists(ca_path):
            needs_write = os.path.getsize(ca_path) != len(CA_PEM)
        if needs_write:
            with open(ca_path, "w", encoding="ascii", newline="\n") as fh:
                fh.write(CA_PEM)
        os.environ["REQUESTS_CA_BUNDLE"] = ca_path
        os.environ["CURL_CA_BUNDLE"] = ca_path
        os.environ["SSL_CERT_FILE"] = ca_path
    except OSError:
        return None

    # requests pasa certifi.where() a urllib3 cuando verify=True.
    try:
        import certifi
        import certifi.core

        certifi.where = lambda: ca_path  # type: ignore[assignment]
        certifi.core.where = lambda: ca_path  # type: ignore[assignment]
    except ImportError:
        pass
    return ca_path


def _load_core(data_dir: str):
    """Importa BuscadorYT y redirige sus rutas de datos a `data_dir`."""
    # En Android no hay fastembed/ONNX: `rag` es el backend BM25 ligero. Los
    # workers de BuscadorYT hacen `import rag`, así que basta con registrarlo
    # en sys.modules antes de crear la ventana.
    import rag_android

    sys.modules.setdefault("rag", rag_android)

    # paths.py resuelve la carpeta de datos al importar la app: se la fijamos
    # antes para que use el directorio privado de Android y no ~/.local/share.
    os.environ["BUSCADORYT_DATA_DIR"] = data_dir

    import BuscadorYT as core  # noqa: N813  (módulo de la app)

    core.APP_DIR = data_dir
    core.DB_PATH = os.path.join(data_dir, "transcripts.db")
    core.UI_CONFIG_PATH = os.path.join(data_dir, "ui_config.json")
    core.RAG_CONFIG_PATH = os.path.join(data_dir, "rag_config.json")
    os.environ["TRANSCRIP_DB_FILE"] = core.DB_PATH

    # Recuerda la última base usada (ui_config.json), pero sin diálogos:
    # en Android la base inicial es siempre transcripts.db.
    core.set_active_db(core.db_initial_path())

    rag_android.CONFIG_PATH = core.RAG_CONFIG_PATH
    rag_android.DB_PATH = core.DB_PATH

    # La app de escritorio exige fastembed en _rag_module; aquí no hace falta.
    def _rag_module(self, silent: bool = False):
        rag = sys.modules.get("rag")
        if rag is None:
            if not silent:
                from PySide6 import QtWidgets

                QtWidgets.QMessageBox.critical(
                    self, "RAG no disponible",
                    "No se pudo cargar el índice de búsqueda local.")
            return None
        rag.DB_PATH = core.DB_PATH
        return rag

    def _settings_refresh_info(self):
        if not hasattr(self, "lbl_settings_info"):
            return
        rag = sys.modules.get("rag")
        lineas = [
            f"Base de datos: {core.DB_PATH}",
            f"Configuración: {core.RAG_CONFIG_PATH}",
            "Búsqueda: BM25 local (sin ONNX ni descargas de modelos)",
        ]
        if rag is not None:
            try:
                st = rag.index_stats()
                lineas.append(
                    f"Índice: {st['videos_indexados']}/{st['videos_totales']} vídeos · "
                    f"{st['fragmentos']} fragmentos")
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"Índice: error ({exc})")
        self.lbl_settings_info.setText("\n".join(lineas))

    core.MainWindow._rag_module = _rag_module
    core.MainWindow._settings_refresh_info = _settings_refresh_info
    return core


def _schedule_autoindex(win) -> None:
    """Indexa en segundo plano la primera vez (BM25 es rápido)."""
    from PySide6 import QtCore

    def _run() -> None:
        rag = sys.modules.get("rag")
        if rag is None:
            return
        try:
            st = rag.index_stats()
            if st["videos_totales"] and st["fragmentos"] == 0:
                win._rag_start_index()
        except Exception:  # noqa: BLE001
            pass

    QtCore.QTimer.singleShot(2000, _run)


# ─────────────────────────────────────────────
# Aplicación
# ─────────────────────────────────────────────
def create_app_and_window(argv: list[str] | None = None):
    """Crea QApplication + MainWindow listos para mostrar.

    Devuelve (app, ventana, data_dir). La ventana ya tiene aplicado el
    aspecto móvil de `mobile.py`.
    """
    _prepare_sys_path()

    from PySide6 import QtWidgets

    from mobile import apply_mobile_layout  # noqa: PLC0415  (tras sys.path)

    argv = list(sys.argv if argv is None else argv)
    app = QtWidgets.QApplication(argv)
    app.setApplicationName("YT Transcripts")
    app.setApplicationDisplayName("YT Transcripts")
    app.setOrganizationName("yt-transcripts")

    data_dir = _data_dir()
    ca_path = _install_ca_bundle(data_dir)
    core = _load_core(data_dir)

    app.setStyle("Fusion")  # base limpia y consistente para el QSS
    app.setStyleSheet(core.QSS)

    win = core.MainWindow()
    apply_mobile_layout(win)
    _schedule_autoindex(win)

    if ca_path is None:
        win._log("⚠️  Sin bundle de CAs: las peticiones HTTPS pueden fallar.", "warn")
    return app, win, data_dir


def _report_fatal(exc: BaseException, data_dir: str | None) -> None:
    """Deja rastro del error (logcat + archivo) antes de morir."""
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(detail, file=sys.stderr)
    if data_dir:
        try:
            with open(os.path.join(data_dir, "crash.log"), "a", encoding="utf-8") as fh:
                fh.write(detail + "\n")
        except OSError:
            pass
    try:
        from PySide6 import QtWidgets

        QtWidgets.QMessageBox.critical(
            None, "YT Transcripts",
            "La aplicación no pudo arrancar:\n\n" + str(exc)[:600])
    except Exception:  # pragma: no cover  (sin Qt no hay diálogo posible)
        pass


def main() -> None:
    data_dir = None
    try:
        app, win, data_dir = create_app_and_window()
        win.show()
        sys.exit(app.exec())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001  (queremos rastro en el móvil)
        _report_fatal(exc, data_dir)
        sys.exit(1)


if __name__ == "__main__":
    main()
