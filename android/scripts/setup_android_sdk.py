#!/usr/bin/env python3
"""Descarga el NDK y el SDK de Android que necesita pyside6-android-deploy.

Los deja en la caché estándar de la herramienta
(`~/.pyside6_android_deploy`), que `pyside6-android-deploy` detecta sola.
Se usan las mismas funciones que el script oficial de Qt for Python, así que
versiones, licencias y rutas coinciden con lo que espera el despliegue.

Primera ejecución: ~1,5 GB y varios minutos. Las siguientes no hacen nada.

Uso: python scripts/setup_android_sdk.py
"""

from __future__ import annotations

import pathlib
import shlex
import subprocess
import sys

CACHE = pathlib.Path.home() / ".pyside6_android_deploy"


def _import_utils():
    """Importa deploy_lib desde el PySide6 instalado.

    deploy_lib usa imports absolutos (`from deploy_lib import ...`), así que su
    directorio debe estar en sys.path; por eso no basta con importar el paquete.
    """
    import PySide6

    scripts_dir = pathlib.Path(PySide6.__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from deploy_lib.android import android_utilities  # noqa: PLC0415

    return android_utilities


def main() -> int:
    utils = _import_utils()

    print(f"[android] caché: {CACHE}")
    print(f"[android] NDK requerido: r{utils.ANDROID_NDK_VERSION}")

    ndk_path = utils.download_android_ndk(CACHE)
    sdk_path = utils.download_android_commandlinetools(CACHE)

    # Acepta TODAS las licencias antes de instalar: sdkmanager pregunta una
    # vez por licencia y el instalador automático sólo respondería a la
    # primera con "sí".
    sdkmanager = sdk_path / "cmdline-tools" / "bin" / "sdkmanager"
    if sdkmanager.exists():
        print("[android] aceptando licencias del SDK")
        subprocess.run(
            f"yes | {shlex.quote(str(sdkmanager))} "
            f"--sdk_root={shlex.quote(str(sdk_path))} --licenses",
            shell=True, check=False, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    utils.install_android_packages(
        android_sdk_dir=sdk_path,
        android_api=utils.DEFAULT_ANDROID_API_LEVEL,
        accept_license=True,
    )

    print()
    print("[android] listo:")
    print(f"  NDK: {ndk_path}")
    print(f"  SDK: {sdk_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
