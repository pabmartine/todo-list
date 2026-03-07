#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_FILE="$(mktemp)"
trap 'rm -f "$TEMP_FILE"' EXIT

find "$ROOT_DIR/src/todo_list" -name "*.py" | sort > "$TEMP_FILE"

xgettext --language=Python \
         --keyword=_ \
         --output="$ROOT_DIR/locale/todo-list.pot" \
         --from-code=UTF-8 \
         --add-comments \
         --copyright-holder="pabmartine" \
         --package-name="Todo List" \
         --package-version="1.0.4" \
         --files-from="$TEMP_FILE"

echo "Archivo .pot generado en locale/todo-list.pot"

for lang in en es; do
    mkdir -p "$ROOT_DIR/locale/$lang/LC_MESSAGES"

    if [ -f "$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po" ]; then
        msgmerge --backup=none --update "$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po" "$ROOT_DIR/locale/todo-list.pot"
        echo "Archivo .po actualizado para idioma: $lang"
    else
        msginit --input="$ROOT_DIR/locale/todo-list.pot" \
                --output-file="$ROOT_DIR/locale/$lang/LC_MESSAGES/todo-list.po" \
                --locale="$lang"
        echo "Archivo .po creado para idioma: $lang"
    fi
done

echo "Proceso completado. Ahora edita los archivos .po para anadir las traducciones."
