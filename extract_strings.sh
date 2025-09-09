#!/bin/bash

# Script para extraer todas las cadenas marcadas con _() del código Python
# y generar/actualizar los archivos .pot y .po

# Crear directorio locale si no existe
mkdir -p locale

# Extraer todas las cadenas del archivo Python
xgettext --language=Python \
         --keyword=_ \
         --output=locale/task-manager.pot \
         --from-code=UTF-8 \
         --add-comments \
         --copyright-holder="Tu Nombre" \
         --package-name="Task Manager" \
         --package-version="1.0.0" \
         todo-list.py

echo "Archivo .pot generado en locale/task-manager.pot"

# Crear o actualizar archivos .po para cada idioma
for lang in en es; do
    mkdir -p locale/$lang/LC_MESSAGES
    
    if [ -f locale/$lang/LC_MESSAGES/task-manager.po ]; then
        # Actualizar archivo existente
        msgmerge --update locale/$lang/LC_MESSAGES/task-manager.po locale/task-manager.pot
        echo "Archivo .po actualizado para idioma: $lang"
    else
        # Crear nuevo archivo
        msginit --input=locale/task-manager.pot \
                --output-file=locale/$lang/LC_MESSAGES/task-manager.po \
                --locale=$lang
        echo "Archivo .po creado para idioma: $lang"
    fi
done

echo "Proceso completado. Ahora edita los archivos .po para añadir las traducciones."