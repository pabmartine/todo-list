# Contributing

## Scope

Contributions should keep the project simple:

- preserve GTK 4 / libadwaita behavior
- avoid mixing UI, persistence and business rules in new code
- prefer small, verifiable changes

## Basic Workflow

1. Make the change
2. Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile todo-list.py src/todo_list/*.py src/todo_list/models/*.py src/todo_list/repositories/*.py src/todo_list/services/*.py src/todo_list/ui/*.py src/todo_list/ui/support/*.py
```

3. If translations changed:

```bash
bash extract_strings.sh
bash compile_translations.sh
```

4. Verify the affected flow manually in the app

## Code Guidelines

- Put persistence logic in `repositories/`
- Put task/project rules in `services/`
- Keep GTK widget logic in `ui/`
- Keep cross-cutting window helpers in `ui/support/`
- Prefer extending services instead of mutating raw task data from the UI
- Keep changes ASCII unless the file already needs accents or localized text

## Documentation

If you change behavior, structure or packaging, update the relevant file in `docs/` and the root `README.md` when needed.
