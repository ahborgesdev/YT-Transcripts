#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Compila la APK cuando `sdkmanager` no puede actualizar platform-tools
# (sin salida a dl.google.com, entornos aislados, etc.).
#
# El SDK ya trae platform-tools; buildozer solo intenta *actualizarlo* al
# empezar y aborta si el `sdkmanager` antiguo no descarga sus manifiestos.
# La solución es `android.skip_update = True` en buildozer.spec… pero el
# despliegue de PySide6 borra y regenera ese fichero en cada pasada. Así que:
#
#   1) se ejecuta build.sh con KEEP_DEPLOYMENT_FILES=1 (deja los ficheros),
#   2) se parchea buildozer.spec,
#   3) se lanza buildozer directamente.
#
# Uso:  ./build-skip-sdk-update.sh
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
HOME_BUILD="$ROOT/.android-build/home"
VENV="$ROOT/.venv-android"

export HOME="$HOME_BUILD"
# Gradle y las herramientas Android usan user.home, no $HOME:
# se les redirige para que no escriban fuera del proyecto.
export GRADLE_USER_HOME="$HOME_BUILD/.gradle"
export ANDROID_USER_HOME="$HOME_BUILD/.android"
mkdir -p "$ANDROID_USER_HOME"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
export PYTHONFORANDROID_PREREQUISITES_INSTALL_INTERACTIVE=0
export SSL_CERT_FILE="$ROOT/.android-build/cacert.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export CURL_CA_BUNDLE="$SSL_CERT_FILE"
export PATH="$VENV/bin:$ROOT/.android-build/tools/make-wrapper:$ROOT/.android-build/tools/make-install/bin:$JAVA_HOME/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

say() { printf '\n\033[1;35m▸ %s\033[0m\n' "$*"; }

say "1/3 Preprando despliegue (se espera que falle en sdkmanager)"
KEEP_DEPLOYMENT_FILES=1 "$HERE/build.sh" || true

if [[ ! -f "$HERE/buildozer.spec" ]]; then
    echo "No se generó buildozer.spec: revisa la salida anterior." >&2
    exit 1
fi

say "2/3 Desactivando la actualización del SDK"
"$VENV/bin/python" - "$HERE/buildozer.spec" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
line = "android.skip_update = True"
if line in text:
    print("  ya estaba puesto")
    sys.exit(0)
if "[buildozer]" in text:
    text = text.replace("[buildozer]", f"{line}\n\n[buildozer]", 1)
else:
    text += f"\n{line}\n"
open(path, "w", encoding="utf-8").write(text)
print("  android.skip_update = True añadido a [app]")
PY

say "2b/3 Añadiendo permiso de «todos los archivos» (para exportar a Descargas)"
"$VENV/bin/python" - "$HERE/buildozer.spec" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
perm = "android.permission.MANAGE_EXTERNAL_STORAGE"
if perm in text:
    print("  ya estaba puesto")
    sys.exit(0)
needle = "android.permissions = "
if needle in text:
    text = text.replace(needle, needle + perm + ", ", 1)
    open(path, "w", encoding="utf-8").write(text)
    print("  MANAGE_EXTERNAL_STORAGE añadido")
else:
    print("  no se encontró android.permissions (se omite)", file=sys.stderr)
PY

say "3/3 Compilando con buildozer (20-40 min la primera vez)"
cd "$HERE"
"$VENV/bin/python" -m buildozer android debug

APK="$(find "$HERE/dist" -maxdepth 1 -name '*.apk' -print -quit 2>/dev/null || true)"
if [[ -n "$APK" ]]; then
    say "APK creada: $APK"
    echo "Instálala con:  adb install -r \"$APK\""
else
    echo "No encuentro la APK en $HERE/dist" >&2
    exit 1
fi
