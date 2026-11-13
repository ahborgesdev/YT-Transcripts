#!/usr/bin/env bash
# Arranca BuscadorYT usando el entorno virtual creado por setup.sh.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [[ ! -x ".venv/bin/python" ]]; then
    echo "No encuentro .venv/bin/python. Ejecuta antes ./setup.sh" >&2
    exit 1
fi

exec .venv/bin/python BuscadorYT.py "$@"
