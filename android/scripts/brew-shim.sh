#!/usr/bin/env bash
# Shim de `brew` para python-for-android en macOS.
#
# Se instala como <venv>/bin/brew y queda delante en el PATH. p4a comprueba
# sus prerrequisitos con `brew --prefix <formula> --installed`; si Homebrew
# no puede escribir sus locks (HOME aislado, sandbox, CI…) esas consultas
# fallan y p4a intenta `brew install`, que tampoco puede.
#
# Aquí respondemos sólo a esas consultas con las rutas reales ya instaladas;
# cualquier otra invocación se delega al brew auténtico.
set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$(dirname "$SELF_DIR")"

if [[ "${1:-}" == "--prefix" ]]; then
    case "${2:-}" in
        cmake)
            # cmake instalado con pip dentro del venv de compilación.
            echo "$VENV"
            exit 0
            ;;
        autoconf|automake|libtool|pkg-config|openssl@3|openssl)
            for opt in /opt/homebrew/opt /usr/local/opt; do
                if [[ -d "$opt/$2" ]]; then
                    echo "$opt/$2"
                    exit 0
                fi
            done
            ;;
    esac
fi

for real in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [[ -x "$real" ]]; then
        exec "$real" "$@"
    fi
done
echo "brew no encontrado" >&2
exit 1
