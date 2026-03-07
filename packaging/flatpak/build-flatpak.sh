#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_ID="com.pabmartine.TodoList"
BUILD_DIR="$ROOT_DIR/build-dir"
REPO_DIR="$ROOT_DIR/repo"
MANIFEST="$ROOT_DIR/packaging/flatpak/com.pabmartine.TodoList.yaml"

echo "Preparando construccion de Flatpak..."

rm -rf "$BUILD_DIR" "$REPO_DIR"

echo "Verificando runtimes de Flatpak..."
if ! flatpak list --runtime | grep -q "org.gnome.Platform.*48"; then
    echo "Instalando runtime de GNOME Platform 48..."
    flatpak install --user flathub org.gnome.Platform//48 org.gnome.Sdk//48 -y
fi

echo "Compilando traducciones..."
bash "$ROOT_DIR/scripts/compile_translations.sh"

echo "Construyendo Flatpak..."
flatpak-builder --user --install --force-clean "$BUILD_DIR" "$MANIFEST"

echo "Creando repositorio local..."
flatpak-builder --user --repo="$REPO_DIR" --force-clean "$BUILD_DIR" "$MANIFEST"

echo "Creando bundle..."
flatpak build-bundle "$REPO_DIR" "$ROOT_DIR/$APP_ID.flatpak" "$APP_ID"

echo "Flatpak construido exitosamente."
echo
echo "Bundle generado:"
echo "  $ROOT_DIR/$APP_ID.flatpak"
echo
echo "Comandos utiles:"
echo "  Instalar el bundle:"
echo "    flatpak install --user \"$ROOT_DIR/$APP_ID.flatpak\""
echo
echo "  Ejecutar la app instalada:"
echo "    flatpak run $APP_ID"
echo
echo "  Ejecutar directamente desde el repositorio local generado:"
echo "    flatpak run --user --sideload-repo=\"$REPO_DIR\" $APP_ID"
