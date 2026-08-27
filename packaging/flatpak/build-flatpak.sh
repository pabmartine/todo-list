#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_ID="com.pabmartine.TodoList"
BUILD_DIR="$ROOT_DIR/build-dir"
REPO_DIR="$ROOT_DIR/repo"
MANIFEST="$ROOT_DIR/packaging/flatpak/com.pabmartine.TodoList.yaml"

echo "Preparando construccion de Flatpak..."

rm -rf "$BUILD_DIR" "$REPO_DIR"

# La version se lee del manifiesto: estaba fijada a 48 mientras el manifiesto
# declaraba otra, asi que la comprobacion pasaba sin tener el runtime correcto.
RUNTIME_VERSION="$(sed -n 's/^runtime-version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p' "$MANIFEST")"

echo "Verificando runtimes de Flatpak (version $RUNTIME_VERSION)..."
for rt in org.gnome.Platform org.gnome.Sdk; do
    if ! flatpak info "$rt//$RUNTIME_VERSION" >/dev/null 2>&1; then
        echo "Instalando $rt//$RUNTIME_VERSION..."
        flatpak install --user flathub "$rt//$RUNTIME_VERSION" -y
    fi
done

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
echo "  Ejecutar directamente usando flatpak-builder:"
echo "    flatpak-builder --run \"$BUILD_DIR\" \"$MANIFEST\" todo-list"

