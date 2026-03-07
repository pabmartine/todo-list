# Packaging

## Flatpak

Canonical Flatpak files:

- `packaging/flatpak/com.pabmartine.TodoList.yaml`
- `packaging/flatpak/build-flatpak.sh`

Compatibility wrappers remain at the repository root:

- `build-flatpak.sh`
- `compile_translations.sh`
- `extract_strings.sh`

## Resources Outside The Python Package

- `data/`: desktop file, appstream metadata and icons
- `locale/`: gettext catalogs
- `docs/`: project documentation

## Flatpak Runtime Notes

The Flatpak launcher:

- sets `PYTHONPATH=/app/src`
- runs `python3 -m todo_list.main`
- installs desktop resources and translations into standard Flatpak locations

## Output Artifacts

The Flatpak build may generate local artifacts such as:

- `build-dir/`
- `repo/`
- `com.pabmartine.TodoList.flatpak`

These are treated as build outputs and are ignored by git.
