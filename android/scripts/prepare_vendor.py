#!/usr/bin/env python3
"""Prepara `android/vendor/` con las dependencias puras de Python.

`pyside6-android-deploy` sólo empaqueta PySide6/Shiboken6: cualquier otro
paquete hay que llevarlo dentro del proyecto. En vez de recompilarlos para
Android (python-for-android no tiene recetas para ellos), se copian tal cual:
todos son Python puro.

Se eliminan las extensiones nativas (.so/.pyd) que pueda traer el wheel del
host porque no sirven para Android; `charset_normalizer` funciona igual con su
implementación de respaldo en Python.

Uso: python scripts/prepare_vendor.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
VENDOR = HERE / "vendor"

# Versiones fijadas: son las que usa la app de escritorio (requirements.txt).
PACKAGES = [
    "requests==2.34.2",
    "urllib3==2.8.0",
    "certifi==2026.10.23",
    "idna==3.20",
    "charset-normalizer==3.5.2",
    "defusedxml==0.7.1",
    "youtube-transcript-api==1.2.4",
]

# Módulos de los que depende la app en tiempo de ejecución.
IMPORTS = [
    "requests",
    "urllib3",
    "certifi",
    "idna",
    "charset_normalizer",
    "defusedxml",
    "youtube_transcript_api",
]


def _pip_install() -> None:
    # Evita escribir en ~/Library/Caches (permisos) y deja la caché en el
    # propio proyecto, que está ignorado por git.
    os.environ.setdefault("PIP_CACHE_DIR", str(HERE.parent / ".android-build" / "pip-cache"))
    command = [
        sys.executable, "-m", "pip", "install",
        "--quiet", "--disable-pip-version-check",
        "--no-compile", "--upgrade",
        "--target", str(VENDOR),
        *PACKAGES,
    ]
    print("[vendor] pip install →", VENDOR)
    subprocess.check_call(command)


def _strip_native_and_cache() -> None:
    for pattern in ("*.so", "*.pyd", "*.dylib", "*.dll"):
        for path in VENDOR.rglob(pattern):
            path.unlink()
    for path in list(VENDOR.rglob("__pycache__")):
        shutil.rmtree(path, ignore_errors=True)
    # Carpetas de tests: no hacen falta dentro de la APK.
    for path in list(VENDOR.rglob("tests")):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def _write_ca_bundle() -> None:
    """Convierte certifi/cacert.pem en un módulo .py.

    Buildozer sólo empaqueta ciertas extensiones (py, png, jpg, qml…); un
    .pem se quedaría fuera de la APK. main.py lo escribe en disco al arrancar.
    """
    cacert = VENDOR / "certifi" / "cacert.pem"
    if not cacert.exists():
        print("[vendor] aviso: no se encontró certifi/cacert.pem", file=sys.stderr)
        return
    pem = cacert.read_text(encoding="utf-8")
    (VENDOR / "_cacert.py").write_text(
        "# Generado por android/scripts/prepare_vendor.py — no editar a mano.\n"
        f"CA_PEM = {pem!r}\n",
        encoding="utf-8",
    )


def _verify() -> None:
    imports = ";".join(f"__import__({name!r})" for name in IMPORTS)
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(VENDOR)!r});"
        f"{imports};"
        "from _cacert import CA_PEM;"
        "assert 'BEGIN CERTIFICATE' in CA_PEM;"
        "print('[vendor] import OK')"
    )
    # -S: sin site-packages, para demostrar que sólo se usa lo empaquetado.
    subprocess.check_call([sys.executable, "-S", "-c", code])


def main() -> None:
    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    VENDOR.mkdir(parents=True)
    _pip_install()
    _strip_native_and_cache()
    _write_ca_bundle()
    _verify()


if __name__ == "__main__":
    main()
