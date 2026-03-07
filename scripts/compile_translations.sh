#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Compilando archivos de traduccion..."

for lang in en es; do
    if [ -f "$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po" ]; then
        msgfmt "$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po" \
               -o "$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.mo"
        echo "Traduccion compilada para: $lang"
    else
        echo "Archivo .po no encontrado para idioma: $lang"
    fi
done

echo "Compilacion completada."
echo ""
echo "Archivos creados:"
find "$ROOT_DIR/locale" -name "*.mo" -exec ls -la {} \;

