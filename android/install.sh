#!/usr/bin/env bash
# Instala en el móvil/emulador conectado por USB la última APK compilada.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APK="$(find "$HERE/dist" -maxdepth 1 -name '*.apk' -print -quit 2>/dev/null || true)"

if [[ -z "$APK" ]]; then
    echo "No hay APK en $HERE/dist. Ejecuta antes ./build.sh" >&2
    exit 1
fi
if ! command -v adb >/dev/null 2>&1; then
    echo "adb no está instalado (brew install --cask android-platform-tools)" >&2
    exit 1
fi

echo "Dispositivos conectados:"
adb devices
echo
echo "Instalando $APK"
adb install -r "$APK"
echo "Listo. Búscala en el cajón de aplicaciones como «BuscadorYT»."
