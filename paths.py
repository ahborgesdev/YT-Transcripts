"""Dónde viven los datos de BuscadorYT.

El ejecutable puede estar en cualquier sitio (o dentro de un `.app` de macOS):
las bases, los cuadernos, la configuración y el modelo de embeddings viven en
la carpeta de datos del usuario, **fuera** del paquete, para que actualizar o
mover la app no se lleve por delante nada.

Se puede forzar otra carpeta con la variable de entorno `BUSCADORYT_DATA_DIR`
(útil para pruebas o para llevar los datos en un pendrive).
"""

from __future__ import annotations

import os
import shutil
import sys

APP_NAME = "BuscadorYT"


def _platform_data_root() -> str:
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support")
    if os.name == "nt":
        return os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def _code_dir() -> str:
    """Carpeta del código, o del ejecutable si va empaquetado con PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CODE_DIR = _code_dir()
DATA_DIR = (os.environ.get("BUSCADORYT_DATA_DIR")
            or os.path.join(_platform_data_root(), APP_NAME))

DATA_DIR_FALLBACK = False
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    # Sin permiso para crear la carpeta del usuario: último recurso, junto al
    # ejecutable (mejor arrancar con los datos al lado que no arrancar).
    DATA_DIR = CODE_DIR
    DATA_DIR_FALLBACK = True


def data_path(*parts: str) -> str:
    """Ruta dentro de la carpeta de datos."""
    return os.path.join(DATA_DIR, *parts)


def models_dir() -> str:
    """Caché de fastembed (el modelo de embeddings, ~240 MB)."""
    return data_path("models")


def _legacy_candidates() -> list[str]:
    """Carpetas donde puede haber datos de una instalación antigua.

    Incluye la carpeta del ejecutable y, si vamos dentro de un `.app`, la que
    contiene el bundle (ahí es donde estaban las bases en la versión anterior).
    """
    candidatos = [CODE_DIR]
    exe = os.path.abspath(sys.executable)
    marcador = ".app/Contents/MacOS/"
    if marcador in exe:
        bundle = exe.split(marcador)[0] + ".app"
        candidatos.append(os.path.dirname(bundle))

    vistos, unicos = set(), []
    for ruta in candidatos:
        ruta = os.path.abspath(ruta)
        if ruta not in vistos:
            vistos.add(ruta)
            unicos.append(ruta)
    return unicos


def migrate_legacy_data() -> list[str]:
    """Copia a `DATA_DIR` lo que estuviera en una instalación antigua.

    Solo actúa la primera vez: si `DATA_DIR` ya tiene alguna base, no toca nada
    (evita pisar datos). Devuelve la lista de elementos copiados.
    """
    try:
        existentes = os.listdir(DATA_DIR)
    except OSError:
        return []
    if any(nombre.lower().endswith(".db") for nombre in existentes):
        return []

    copiados: list[str] = []
    for legacy in _legacy_candidates():
        if os.path.abspath(legacy) == os.path.abspath(DATA_DIR) or not os.path.isdir(legacy):
            continue
        try:
            nombres = os.listdir(legacy)
        except OSError:
            continue
        for nombre in nombres:
            es_db = nombre.lower().endswith(".db")
            es_cuaderno = nombre.startswith("cuaderno-") and nombre.lower().endswith(".pdf")
            if not (es_db or es_cuaderno):
                continue
            origen = os.path.join(legacy, nombre)
            destino = os.path.join(DATA_DIR, nombre)
            if os.path.isfile(origen) and not os.path.exists(destino):
                try:
                    shutil.copy2(origen, destino)
                    copiados.append(nombre)
                except OSError:
                    pass

        # El modelo de embeddings también, para no re-descargar 240 MB.
        modelos_legacy = os.path.join(legacy, "models")
        modelos_datos = models_dir()
        if os.path.isdir(modelos_legacy) and not os.path.isdir(modelos_datos):
            try:
                shutil.copytree(modelos_legacy, modelos_datos)
                copiados.append("models/")
            except OSError:
                pass
    return copiados
