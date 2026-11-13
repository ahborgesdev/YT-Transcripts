#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Setup de BuscadorYT en Linux (Ubuntu/Debian).
#
#   1) comprueba Python 3.10+,
#   2) instala (si faltan) las librerías del sistema que Qt/PySide6 necesita,
#   3) crea el entorno virtual `.venv` e instala `requirements.txt`.
#
# Uso (la primera vez):   ./setup.sh
# Para arrancar después:  ./run.sh      (o: .venv/bin/python BuscadorYT.py)
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

say() { printf '\n\033[1;35m▸ %s\033[0m\n' "$*"; }

# ── 1. Python 3.10+ ────────────────────────────────────────────────────────
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
        if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            PY="$(command -v "$c")"
            break
        fi
    fi
done
if [[ -z "$PY" ]]; then
    echo "No encuentro Python ≥3.10. Instálalo con:" >&2
    echo "  sudo apt install python3.12 python3.12-venv" >&2
    exit 1
fi
say "Python: $PY ($("$PY" -c 'import platform; print(platform.python_version())'))"

# ── 2. Librerías del sistema que Qt/PySide6 necesita ───────────────────────
# Paquete apt  ->  biblioteca .so con la que comprobamos si ya está.
declare -A NEEDED=(
    [libxcb-cursor0]="libxcb-cursor.so.0"
    [libgl1]="libGL.so.1"
    [libegl1]="libEGL.so.1"
    [libxkbcommon-x11-0]="libxkbcommon-x11.so.0"
    [libxcb-xinerama0]="libxcb-xinerama.so.0"
)
MISSING=()
for pkg in "${!NEEDED[@]}"; do
    if ! ldconfig -p 2>/dev/null | grep -q "${NEEDED[$pkg]}"; then
        MISSING+=("$pkg")
    fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
    say "Faltan librerías del sistema: ${MISSING[*]}"
    read -r -p "¿Las instalo con apt? (s/N) " resp
    if [[ "$resp" == "s" || "$resp" == "S" ]]; then
        sudo apt update && sudo apt install -y "${MISSING[@]}"
    else
        echo "Recuerda instalarlas antes de arrancar:"
        echo "  sudo apt install ${MISSING[*]}"
    fi
else
    echo "Librerías del sistema: todas presentes ✓"
fi

# ── 3. Entorno virtual + dependencias Python ───────────────────────────────
if [[ ! -x ".venv/bin/python" ]]; then
    say "Creando el entorno virtual .venv"
    "$PY" -m venv .venv
fi
say "Instalando dependencias (requirements.txt)…"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

say "¡Listo! Para arrancar la app:"
echo "  ./run.sh"
echo "  # o directamente: .venv/bin/python BuscadorYT.py"
