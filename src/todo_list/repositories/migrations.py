from ..debug import debug
from ..i18n import translate as _


def _project_slug(name):
    return name.lower().replace(" ", "_").replace("ã", "a")


def migrate_loaded_data(data, projects):
    if "all_tasks" in data:
        tasks = {key: value for key, value in data.items() if key != "projects"}
    else:
        all_tasks = []
        for key, value in data.items():
            if key != "projects" and isinstance(value, list):
                for task in value:
                    if "list_id" not in task:
                        task["list_id"] = key
                    all_tasks.append(task)
        debug.log_event("TASKMAN", f"Migrated {len(all_tasks)} tasks from legacy format")
        tasks = {"all_tasks": all_tasks}

    for task in tasks.get("all_tasks", []):
        task.setdefault("favorite", False)
        task.setdefault("sort_order", 0)
        task.setdefault("subtasks", [])
        normalized_subtasks = []
        for index, subtask in enumerate(task.get("subtasks", []), start=1):
            if not isinstance(subtask, dict):
                continue
            normalized_subtask = {
                "id": subtask.get("id", index),
                "title": subtask.get("title", ""),
                "completed": subtask.get("completed", False),
            }
            normalized_subtasks.append(normalized_subtask)
        task["subtasks"] = normalized_subtasks

    migrated_projects = []
    for project in projects:
        project_copy = dict(project)
        if "id" not in project_copy:
            if project_copy.get("name") in {"Inbox", "Bandeja de entrada", _("Inbox")}:
                project_copy["id"] = "inbox"
            else:
                project_copy["id"] = _project_slug(project_copy["name"])
        project_copy.setdefault("color", "black")
        migrated_projects.append(project_copy)

    return tasks, migrated_projects


def normalize_inbox_projects(tasks, projects):
    inbox_variants = {"Inbox", "Bandeja de entrada", "Bandeja de Entrada", "inbox", _("Inbox")}
    potential_inboxes = [project for project in projects if project.get("id") == "inbox" or project.get("name") in inbox_variants]

    if not potential_inboxes:
        projects.insert(0, {"id": "inbox", "name": _("Inbox"), "color": "black"})
        return tasks, projects

    main_inbox = next((project for project in potential_inboxes if project.get("id") == "inbox"), potential_inboxes[0])
    old_names = {project.get("name") for project in potential_inboxes}
    main_inbox["id"] = "inbox"
    main_inbox["name"] = _("Inbox")
    main_inbox["color"] = "black"

    for task in tasks.get("all_tasks", []):
        if task.get("project") in old_names:
            task["project"] = main_inbox["name"]

    unique_projects = [project for project in projects if project not in potential_inboxes]
    unique_projects.insert(0, main_inbox)
    return tasks, unique_projects
