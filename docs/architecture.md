# Architecture

## Goal

The project is organized to keep three concerns separated:

- UI and GTK/libadwaita widget code
- application rules for tasks and projects
- persistence and migration of local JSON data

## Layers

### Entry Points

- `todo-list.py`: root wrapper for local execution
- `src/todo_list/main.py`: Python entrypoint
- `src/todo_list/app.py`: `Adw.Application` and global actions

### Core Infrastructure

- `src/todo_list/config.py`: configuration paths and persisted UI settings
- `src/todo_list/i18n.py`: gettext bootstrap and runtime language changes
- `src/todo_list/debug.py`: debug logger and decorators
- `src/todo_list/constants.py`: app constants and default values

### Domain And Persistence

- `src/todo_list/models/`: basic task and project data structures
- `src/todo_list/repositories/task_repository.py`: JSON load/save
- `src/todo_list/repositories/migrations.py`: legacy data normalization and inbox cleanup
- `src/todo_list/services/task_service.py`: task queries and mutations
- `src/todo_list/services/project_service.py`: project creation, update and deletion

Tasks may also contain embedded `subtasks`, implemented as a lightweight checklist stored inside each task record.

### UI

- `src/todo_list/ui/window.py`: main window coordinator
- `src/todo_list/ui/support/appearance.py`: runtime UI refresh, CSS and language-related window helpers
- `src/todo_list/ui/support/data_actions.py`: archive cleanup and import/export actions
- `src/todo_list/ui/support/lifecycle.py`: cleanup, shortcuts and window lifecycle helpers
- `src/todo_list/ui/sidebar.py`: sidebar, navigation and main-area construction
- `src/todo_list/ui/projects.py`: project dialogs and project-specific UI actions
- `src/todo_list/ui/task_list.py`: task list refresh, grouping, rows and task-list interactions
- `src/todo_list/ui/task_detail.py`: task detail panel, date editing and task detail actions
- `src/todo_list/ui/styles.py`: application CSS

## Current State

The architecture is split by package and responsibility. `ui/window.py` now acts mainly as the coordinator, while task list behavior and task detail behavior live in dedicated UI modules.

## Runtime Flow

1. `todo-list.py` adds `src/` to `sys.path` and calls `todo_list.main`.
2. `main.py` creates `TaskManagerApplication`.
3. `app.py` builds the main window and app-level actions.
4. `TaskService` loads tasks/projects from JSON through `TaskRepository`.
5. UI widgets query and mutate data through services.

## Validation

Automated coverage is intentionally small and focused:

- `tests/test_task_repository.py`: JSON load/save/import/export behavior
- `tests/test_task_service.py`: list filters, favorites, archive cleanup, reorder and import/export flow
- `tests/test_migrations.py`: legacy task migration and inbox normalization rules

## Persistence Model

The app uses local JSON files only. There is no server, sync layer or database.

- `config.json` stores UI preferences
- `tasks.json` stores tasks and projects

Saves are atomic: data is written to a temporary file and then replaced.
