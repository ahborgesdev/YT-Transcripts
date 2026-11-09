#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Compila BuscadorYT.py en una APK de Android con pyside6-android-deploy.
#
#   ./build.sh              # compilación completa (descarga NDK/SDK la 1ª vez)
#   ./build.sh --skip-sdk   # no descarga NDK/SDK (ya están en la caché)
#   ./build.sh --clean      # borra artefactos de build antes de compilar
#
# Todo lo pesado (venv, wheels, caché de pip) vive FUERA de android/ para que
# buildozer no lo meta en la APK.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
CACHE="$ROOT/.android-build"
VENV="$ROOT/.venv-android"
WHEELS="$CACHE/wheels"

SKIP_SDK=0
CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --skip-sdk) SKIP_SDK=1 ;;
        --clean) CLEAN=1 ;;
        -h|--help) sed -n '3,10p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "Opción desconocida: $arg" >&2; exit 2 ;;
    esac
done

say() { printf '\n\033[1;35m▸ %s\033[0m\n' "$*"; }

# ── 1. Intérprete de Python para compilar ─────────────────────────────────
# La app corre en CPython 3.14 (lo construye python-for-android); el host sólo
# necesita 3.10-3.14 y PySide6 6.12.
if [[ -n "${PYTHON:-}" ]]; then
    PY="$PYTHON"
else
    PY=""
    for candidate in python3.14 python3.13 python3.12 /opt/homebrew/bin/python3.13 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
                PY="$(command -v "$candidate")"
                break
            fi
        fi
    done
fi
if [[ -z "$PY" ]]; then
    echo "No encuentro Python ≥3.10. Instala python3.13 (brew install python@3.13)." >&2
    exit 1
fi
say "Python de compilación: $PY ($("$PY" -c 'import platform; print(platform.python_version())'))"

# ── 2. Entorno virtual de herramientas ────────────────────────────────────
export PIP_CACHE_DIR="$CACHE/pip-cache"
mkdir -p "$CACHE"
if [[ ! -x "$VENV/bin/python" ]]; then
    say "Creando el entorno de compilación en $VENV"
    if "$PY" -c 'import PySide6' >/dev/null 2>&1; then
        # Aprovecha el PySide6 ya instalado en el sistema (evita ~500 MB).
        "$PY" -m venv --system-site-packages "$VENV"
    else
        "$PY" -m venv "$VENV"
    fi
fi
# buildozer busca `cython` y compañía en el PATH, no en site-packages.
export VIRTUAL_ENV="$VENV"
export PATH="$VENV/bin:$PATH"

# El Python del host puede no tener CAs (p. ej. el framework de python.org sin
# "Install Certificates.command"). Generamos un bundle estable en la caché y
# lo exportamos para pip y para las descargas de buildozer/p4a.
CA_BUNDLE="$CACHE/cacert.pem"
if [[ ! -s "$CA_BUNDLE" ]]; then
    "$VENV/bin/python" - "$CA_BUNDLE" <<'PYEOF'
import shutil
import sys
import pip._vendor.certifi as certifi

shutil.copyfile(certifi.where(), sys.argv[1])
PYEOF
fi
export SSL_CERT_FILE="$CA_BUNDLE"
export REQUESTS_CA_BUNDLE="$CA_BUNDLE"
export CURL_CA_BUNDLE="$CA_BUNDLE"

"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r "$HERE/requirements-build.txt"

PYSIDE_VERSION="$("$VENV/bin/python" -c 'import PySide6; print(PySide6.__version__)' 2>/dev/null || true)"
if [[ "$PYSIDE_VERSION" != "6.12.0" ]]; then
    say "Instalando PySide6 6.12.0 en el entorno de compilación"
    "$VENV/bin/python" -m pip install --quiet "PySide6==6.12.0"
fi
say "PySide6: $("$VENV/bin/python" -c 'import PySide6; print(PySide6.__version__)')"

# p4a en macOS comprueba cmake y otros prerrequisitos con Homebrew, no con
# el PATH. Si Homebrew no puede actualizar su API (HOME aislado, CI, sandbox),
# esas consultas fallan y el build se detiene. El shim responde a las
# consultas de p4a usando lo ya instalado y delega el resto al brew real.
if [[ "$(uname -s)" == "Darwin" ]]; then
    cp -f "$HERE/scripts/brew-shim.sh" "$VENV/bin/brew"
    chmod +x "$VENV/bin/brew"
fi

# p4a ejecuta comandos con `sh`, que abre un PTY para stdout. En CI,
# contenedores o sandboxes sin /dev/ptmx eso falla; en ese caso activamos un
# parche que hace que `sh` use tuberías normales.
if ! "$VENV/bin/python" -c 'import pty; pty.openpty()' >/dev/null 2>&1; then
    SITE_PACKAGES="$("$VENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
    cp -f "$HERE/scripts/sitecustomize_no_pty.py" "$SITE_PACKAGES/"
    echo "import sitecustomize_no_pty" > "$SITE_PACKAGES/buscador_no_pty.pth"
fi

# El make de macOS es GNU 3.81 (2006) y las recetas de p4a (automake)
# necesitan >= 3.82. Si no hay uno moderno, compilamos GNU make en la caché.
MAKE_TOOL="$CACHE/tools/make-install/bin/make"
if [[ ! -x "$MAKE_TOOL" ]]; then
    if ! make --version 2>/dev/null | head -1 | awk '{ exit !($3 + 0 >= 3.82) }'; then
        say "Compilando GNU make 4.4.1 (el make del sistema es demasiado antiguo)"
        mkdir -p "$CACHE/tools"
        ( cd "$CACHE/tools" \
          && curl -fsSL -o make-4.4.1.tar.gz https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz \
          && tar -xzf make-4.4.1.tar.gz \
          && cd make-4.4.1 \
          && ./configure --prefix="$CACHE/tools/make-install" --disable-nls >/dev/null \
          && sh ./build.sh >/dev/null \
          && ./make install >/dev/null )
    fi
fi
if [[ -x "$MAKE_TOOL" ]]; then
    # p4a pasa a las recetas un entorno mínimo sin TMPDIR, y make acaba
    # escribiendo en /var/tmp (bloqueado en sandboxes). Este wrapper le da un
    # TMPDIR escribible sin tocar p4a.
    MAKE_WRAPPER_DIR="$CACHE/tools/make-wrapper"
    mkdir -p "$MAKE_WRAPPER_DIR"
    cat > "$MAKE_WRAPPER_DIR/make" <<EOF
#!/usr/bin/env bash
if [[ -z "\${TMPDIR:-}" ]]; then
    export TMPDIR="\${HOME:-/tmp}/tmp"
    mkdir -p "\$TMPDIR" 2>/dev/null || true
fi
exec "$MAKE_TOOL" "\$@"
EOF
    chmod +x "$MAKE_WRAPPER_DIR/make"
    export PATH="$MAKE_WRAPPER_DIR:$(dirname "$MAKE_TOOL"):$PATH"
fi

# ── 3. Wheels de PySide6/Shiboken6 para Android (aarch64) ────────────────
mkdir -p "$WHEELS"
WHEEL_PYSIDE="$WHEELS/pyside6-6.12.0-android_aarch64.whl"
WHEEL_SHIBOKEN="$WHEELS/shiboken6-6.12.0-android_aarch64.whl"
download() {
    local url="$1" out="$2"
    if [[ -s "$out" ]]; then return; fi
    say "Descargando $(basename "$out")"
    curl -fL --retry 3 --connect-timeout 20 --progress-bar -o "$out.part" "$url"
    mv "$out.part" "$out"
}
download \
    "https://download.qt.io/official_releases/QtForPython/pyside6/pyside6-6.12.0-6.12.0-cp310-abi3-android_aarch64.whl" \
    "$WHEEL_PYSIDE"
download \
    "https://download.qt.io/official_releases/QtForPython/shiboken6/shiboken6-6.12.0-6.12.0-cp310-abi3-android_aarch64.whl" \
    "$WHEEL_SHIBOKEN"

# ── 4. Código de la app + dependencias puras ─────────────────────────────
say "Copiando BuscadorYT.py y sus módulos a app/"
mkdir -p "$HERE/app"
cp -f "$ROOT/BuscadorYT.py" "$HERE/app/BuscadorYT.py"
cp -f "$ROOT/paths.py" "$HERE/app/paths.py"
cp -f "$ROOT/responsive.py" "$HERE/app/responsive.py"

say "Preparando dependencias de Python para la APK"
"$VENV/bin/python" "$HERE/scripts/prepare_vendor.py"

# ── 5. NDK + SDK de Android (caché compartida de Qt) ─────────────────────
if [[ "$SKIP_SDK" -eq 0 ]]; then
    say "Comprobando NDK/SDK de Android (la 1ª vez descarga ~1,5 GB)"
    "$VENV/bin/python" "$HERE/scripts/setup_android_sdk.py"
fi

# ── 6. Despliegue ─────────────────────────────────────────────────────────
if [[ "$CLEAN" -eq 1 ]]; then
    say "Limpiando artefactos anteriores"
    rm -rf "$HERE/deployment" "$HERE/dist" "$HERE/.buildozer" "$HERE/buildozer.spec"
fi

DEPLOY_SCRIPT="$("$VENV/bin/python" - <<'PY'
import pathlib
import PySide6
print(pathlib.Path(PySide6.__file__).resolve().parent / "scripts" / "android_deploy.py")
PY
)"
if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
    echo "No encuentro android_deploy.py dentro de PySide6." >&2
    exit 1
fi

say "Lanzando pyside6-android-deploy (la primera compilación tarda 20-40 min)"
cd "$HERE"
export PYTHONFORANDROID_PREREQUISITES_INSTALL_INTERACTIVE=0
KEEP_FLAG=""
if [[ "${KEEP_DEPLOYMENT_FILES:-0}" == "1" ]]; then
    KEEP_FLAG="--keep-deployment-files"
fi
# shellcheck disable=SC2086  # KEEP_FLAG vacío debe desaparecer, no ir como ""
"$VENV/bin/python" "$DEPLOY_SCRIPT" \
    --config-file "$HERE/pysidedeploy.spec" \
    --force --verbose $KEEP_FLAG

# ── 7. Resultado ──────────────────────────────────────────────────────────
APK="$(find "$HERE/dist" -maxdepth 1 -name '*.apk' -print -quit 2>/dev/null || true)"
if [[ -n "$APK" ]]; then
    say "APK creada: $APK"
    echo "Instálala con:  adb install -r \"$APK\""
else
    echo "No encuentro la APK en $HERE/dist (revisa la salida anterior)." >&2
    exit 1
fi
