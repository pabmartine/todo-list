#!/bin/bash

# Script para compilar archivos .po a .mo (archivos binarios que usa gettext)

echo "Compilando archivos de traducción..."

# Compilar traducciones para cada idioma
for lang in en es; do
    if [ -f "locale/$lang/LC_MESSAGES/task-manager.po" ]; then
        msgfmt "locale/$lang/LC_MESSAGES/task-manager.po" \
               -o "locale/$lang/LC_MESSAGES/task-manager.mo"
        echo "Traducción compilada para: $lang"
    else
        echo "Archivo .po no encontrado para idioma: $lang"
    fi
done

echo "Compilación completada."
echo ""
echo "Archivos creados:"
find locale -name "*.mo" -exec ls -la {} \;