#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Compilando archivos de traduccion..."

for lang in en es; do
    po_file="$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po"
    mo_file="$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.mo"
    if [ -f "$po_file" ]; then
        if command -v msgfmt >/dev/null 2>&1; then
            msgfmt "$po_file" -o "$mo_file"
        else
            python3 -c "from babel.messages import pofile, mofile; mofile.write_mo(open('$mo_file', 'wb'), pofile.read_po(open('$po_file', 'r', encoding='utf-8')))"
        fi
        echo "Traduccion compilada para: $lang"
    else
        echo "Archivo .po no encontrado para idioma: $lang"
    fi
done

echo "Compilacion completada."
echo ""
echo "Archivos creados:"
find "$ROOT_DIR/locale" -name "*.mo" -exec ls -la {} \;

