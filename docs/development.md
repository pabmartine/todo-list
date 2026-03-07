# Development

## Run Locally

Preferred commands:

```bash
python3 todo-list.py
```

or:

```bash
PYTHONPATH=src python3 -m todo_list.main
```

## Useful Commands

Compile Python files:

```bash
python3 -m py_compile todo-list.py src/todo_list/*.py src/todo_list/models/*.py src/todo_list/repositories/*.py src/todo_list/services/*.py src/todo_list/ui/*.py src/todo_list/ui/support/*.py
```

Update translation catalogs:

```bash
bash extract_strings.sh
```

Compile translations:

```bash
bash compile_translations.sh
```

Build Flatpak:

```bash
bash build-flatpak.sh
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Packaging As Python Project

The package metadata lives in `pyproject.toml`.

Installed console command:

```bash
todo-list
```

## Validation Strategy

Current validation is based on:

- `unittest` for repository and service behavior
- `py_compile`
- manual UI verification for GTK/libadwaita flows

Current automated coverage includes:

- repository save/load/import/export
- task service list filters, favorites, archive cleanup and reorder
- legacy migration and inbox normalization

## Recommended Workflow

1. Make the code change
2. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`
3. Run `py_compile`
4. If translations changed, update `.po` and `.mo`
5. Verify the affected flow manually in the app
