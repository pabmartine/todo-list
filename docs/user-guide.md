# User Guide

## Main Concepts

- A task has a title, notes, project, date, status lifecycle (`pending`, `in_progress`, `completed`), completion state, favorite flag, and optional subtasks.
- A project groups tasks and has a distinctive color.
- Smart lists are dynamic generated views based on dates and task properties, not separate task stores.
- Dual view modes: **List View** for linear review and organization, and **Kanban View** for workflow and status-oriented tracking.

## Smart Lists

- `Today`: tasks dated today
- `Next 7 days`: tasks scheduled within the next week
- `All`: all incomplete tasks
- `Overdue`: incomplete tasks with a past date
- `Favorites`: starred incomplete tasks
- `Archived`: completed tasks

## Basic Usage

### Create A Task

Type in the `New task...` entry and press Enter. When creating a task outside of a specific project (such as in Smart Lists), you will be prompted to select an assigned project in the task detail panel before proceeding.

### View Switcher: List and Kanban Views

Use the view switcher toggle buttons in the center of the header bar to alternate between:

- **List View**: Displays tasks grouped by date headings or lists, with inline completion toggles and drag handles.
- **Kanban View**: Visualizes tasks across three columns representing status:
  - **Pending**: Tasks queued or awaiting start.
  - **In progress**: Tasks currently being worked on.
  - **Completed**: Finished tasks.

The selected view mode is automatically saved in your preferences.

### Using the Kanban Board

In Kanban view:

- Each card displays the task title, project badge with project color, favorite star, and subtask completion count (e.g. `✓ 2/3`).
- **Drag and Drop**: Drag any card by its handle and drop it into a different column to instantly update its status.
- **Card Selection**: Clicking a card opens the task detail panel, and the card remains highlighted while the panel is active.

### Task Status Lifecycle

Tasks progress through three explicit statuses: `pending`, `in_progress`, and `completed`.

You can update a task's status in two ways:
1. Dragging the task card to a different column on the Kanban board.
2. Opening the task details panel and choosing from the **Status** dropdown under the Organization section.

Marking a task completed via the checkbox or switch automatically syncs its status to `completed`.

### Edit A Task

Select a task to open its detail view. Depending on the window width, it appears as a side panel or a small-screen detail page.

You can edit:

- Title
- Date
- Notes / Description
- Project assignment
- Status (`Pending`, `In progress`, `Completed`)
- Completed state
- Subtasks checklist

### Favorite A Task

Use the star button in the task row or Kanban card.

### Manage Subtasks

Open a task and use the `Subtasks` section to:

- Add a new checklist item
- Mark a subtask as completed
- Rename a subtask
- Delete a subtask

Tasks with subtasks show a completion summary (e.g., `Subtareas: 2/3` or `✓ 2/3`) in both list and Kanban views.

### Search Tasks

Use the `Search tasks...` field above the list or board (or Ctrl+F) to filter tasks within the current view in real time.

### Manage Projects

Use the add/edit/delete project actions from the sidebar header and project views. Tasks require an assigned project to ensure organization.

### Reorder Tasks

Drag a task by its handle and drop it over another task in the same visible list, or across columns in Kanban view.

## Preferences

From the application menu (or Ctrl+comma) you can change:

- Interface language (Automatic, English, Spanish)
- Style: follow the system preference, or force light or dark

Window size, selected list, and active view mode are remembered automatically.

Press Ctrl+question to see every keyboard shortcut.

## Import And Export

From the application menu you can:

- Import tasks from a JSON backup
- Export the current data to a JSON file via the native file chooser portal
