import datetime

from ..core.debug import debug
from ..core.i18n import translate as _
from ..models.task import Task
from ..repositories.migrations import migrate_loaded_data, normalize_inbox_projects
from ..repositories.task_repository import TaskRepository


class TaskService:
    def __init__(self, repository=None):
        debug.log_event("TASKMAN", "Initializing TaskService")
        self.repository = repository or TaskRepository()
        self.projects = []
        self.tasks = {"all_tasks": []}
        self.update_list_names()
        self.load_tasks()
        if not self.projects:
            self.projects = [{"id": "inbox", "name": _("Inbox"), "color": "black"}]
            self.save_tasks()
        debug.log_event(
            "TASKMAN",
            f"TaskService initialized. Tasks: {len(self.tasks.get('all_tasks', []))}, Projects: {len(self.projects)}",
        )

    def ensure_inbox_project(self):
        inbox_project = self.get_inbox_project()
        if inbox_project:
            self.update_project_names()
            self.save_tasks()
            return inbox_project

        inbox_project = {"id": "inbox", "name": _("Inbox"), "color": "black"}
        self.projects.insert(0, inbox_project)
        self.save_tasks()
        return inbox_project

    def update_list_names(self):
        self.lists = {
            "today": _("Today"),
            "next7": _("Next 7 days"),
            "all": _("All"),
            "overdue": _("Overdue"),
            "favorites": _("Favorites"),
            "archived": _("Archived"),
        }

    def load_tasks(self):
        try:
            raw_data, raw_projects = self.repository.load_data()
            self.tasks, self.projects = migrate_loaded_data(raw_data, raw_projects)
            self.update_project_names()
            self.tasks, self.projects = normalize_inbox_projects(self.tasks, self.projects)
        except Exception as exc:
            debug.log_event("TASKMAN", f"Error loading tasks: {exc}")
            self.tasks = {"all_tasks": []}
            self.projects = []
        return self.tasks

    def save_tasks(self):
        self.repository.save_data(self.tasks, self.projects)

    def update_project_names(self):
        for project in self.projects:
            if project.get("id") == "inbox":
                old_name = project["name"]
                new_name = _("Inbox")
                project["name"] = new_name
                inbox_variants = {"Inbox", "Bandeja de entrada", "Bandeja de Entrada", "inbox", old_name}
                for task in self.tasks.get("all_tasks", []):
                    if task.get("project") in inbox_variants:
                        task["project"] = new_name
                break

    def clean_duplicate_inboxes(self):
        self.tasks, self.projects = normalize_inbox_projects(self.tasks, self.projects)

    def migrate_legacy_projects(self):
        self.tasks, self.projects = migrate_loaded_data({**self.tasks, "projects": self.projects}, self.projects)
        self.clean_duplicate_inboxes()

    def get_inbox_project(self):
        for project in self.projects:
            if project.get("id") == "inbox":
                return project
        return None

    def get_project_by_id(self, project_id):
        for project in self.projects:
            if project.get("id") == project_id:
                return project
        return None

    def get_next_id(self):
        max_id = 0
        for task in self.tasks.get("all_tasks", []):
            if task.get("id", 0) > max_id:
                max_id = task.get("id", 0)
        return max_id + 1

    def add_task(self, list_id, title, due_date=None, priority=0, notes="", project=None, effective_date=None, status="pending"):
        if project is None:
            inbox_project = self.get_inbox_project()
            project = inbox_project["name"] if inbox_project else _("Inbox")

        if status not in ("pending", "in_progress", "completed"):
            status = "pending"

        new_task = Task(
            id=self.get_next_id(),
            title=title,
            completed=(status == "completed"),
            priority=priority,
            notes=notes,
            project=project,
            created_date=datetime.datetime.now().isoformat(),
            effective_date=effective_date,
            list_id=list_id,
            favorite=False,
            sort_order=0,
            subtasks=[],
            status=status,
        )
        task_dict = new_task.to_dict()
        self.tasks.setdefault("all_tasks", []).append(task_dict)
        self.save_tasks()
        return task_dict

    def get_tasks(self, list_id):
        all_tasks = self.tasks.get("all_tasks", [])

        if list_id == "overdue":
            return self._get_overdue_tasks(all_tasks)
        if list_id == "today":
            return self._get_today_tasks(all_tasks)
        if list_id == "next7":
            return self._get_next7_tasks(all_tasks)
        if list_id == "all":
            return [task for task in all_tasks if not task.get("completed", False)]
        if list_id == "favorites":
            return [task for task in all_tasks if task.get("favorite", False) and not task.get("completed", False)]
        if list_id == "archived":
            return [task for task in all_tasks if task.get("completed", False)]
        if list_id.startswith("project_"):
            project_id = list_id.replace("project_", "")
            project = self.get_project_by_id(project_id)
            if not project:
                return []

            project_name = project["name"]
            if project_id == "inbox":
                inbox_variants = {"Inbox", "Bandeja de entrada", "Bandeja de Entrada", "inbox", project_name}
                return [
                    task
                    for task in all_tasks
                    if (task.get("project") == project_name or task.get("project") in inbox_variants)
                    and not task.get("completed", False)
                ]
            return [task for task in all_tasks if task.get("project") == project_name and not task.get("completed", False)]
        return []

    def search_tasks(self, list_id, query):
        normalized_query = (query or "").strip().casefold()
        tasks = self.get_tasks(list_id)
        if not normalized_query:
            return tasks

        result = []
        for task in tasks:
            haystack = " ".join(
                [
                    task.get("title", ""),
                    task.get("notes", ""),
                    task.get("project", ""),
                    " ".join(subtask.get("title", "") for subtask in task.get("subtasks", [])),
                ]
            ).casefold()
            if normalized_query in haystack:
                result.append(task)
        return result

    def _get_today_tasks(self, all_tasks):
        today = datetime.date.today()
        return [task for task in all_tasks if not task.get("completed", False) and self._task_date(task) == today]

    def _get_overdue_tasks(self, all_tasks):
        today = datetime.date.today()
        return [
            task
            for task in all_tasks
            if not task.get("completed", False) and self._task_date(task) is not None and self._task_date(task) < today
        ]

    def _get_next7_tasks(self, all_tasks):
        today = datetime.date.today()
        result = []
        for task in all_tasks:
            if task.get("completed", False):
                continue
            effective_date = self._task_date(task)
            if not effective_date:
                continue
            days_diff = (effective_date - today).days
            if 1 <= days_diff <= 7:
                result.append(task)
        return result

    def _task_date(self, task):
        effective_date_str = task.get("effective_date")
        if not effective_date_str:
            return None
        try:
            return datetime.datetime.fromisoformat(effective_date_str).date()
        except (ValueError, TypeError):
            return None

    def _get_kanban_base_tasks(self, list_id):
        all_tasks = self.tasks.get("all_tasks", [])
        today = datetime.date.today()

        if list_id == "today":
            return [task for task in all_tasks if self._task_date(task) == today]
        if list_id == "next7":
            result = []
            for task in all_tasks:
                effective_date = self._task_date(task)
                if not effective_date:
                    continue
                days_diff = (effective_date - today).days
                if 1 <= days_diff <= 7:
                    result.append(task)
            return result
        if list_id == "overdue":
            return [
                task
                for task in all_tasks
                if self._task_date(task) is not None and self._task_date(task) < today
            ]
        if list_id == "all":
            return list(all_tasks)
        if list_id == "favorites":
            return [task for task in all_tasks if task.get("favorite", False)]
        if list_id == "archived":
            return [task for task in all_tasks if task.get("completed", False)]
        if list_id.startswith("project_"):
            project_id = list_id.replace("project_", "")
            project = self.get_project_by_id(project_id)
            if not project:
                return []

            project_name = project["name"]
            if project_id == "inbox":
                inbox_variants = {"Inbox", "Bandeja de entrada", "Bandeja de Entrada", "inbox", project_name}
                return [
                    task
                    for task in all_tasks
                    if (task.get("project") == project_name or task.get("project") in inbox_variants)
                ]
            return [task for task in all_tasks if task.get("project") == project_name]
        return []

    def get_kanban_tasks(self, list_id, query=None):
        tasks = self._get_kanban_base_tasks(list_id)
        if query:
            normalized_query = query.strip().casefold()
            tasks = [
                task
                for task in tasks
                if normalized_query in " ".join(
                    [
                        task.get("title", ""),
                        task.get("notes", ""),
                        task.get("project", ""),
                        " ".join(subtask.get("title", "") for subtask in task.get("subtasks", [])),
                    ]
                ).casefold()
            ]

        kanban_data = {
            "pending": [],
            "in_progress": [],
            "completed": [],
        }

        for task in tasks:
            status = task.get("status")
            if not status or status not in kanban_data:
                status = "completed" if task.get("completed", False) else "pending"
            kanban_data[status].append(task)

        for col in kanban_data:
            kanban_data[col].sort(key=lambda t: (t.get("sort_order", 0), t.get("id", 0)))

        return kanban_data

    def get_task_count(self, list_id):
        return len(self.get_tasks(list_id))

    def find_task(self, task_id):
        for task in self.tasks.get("all_tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def task_exists(self, task_id):
        return self.find_task(task_id) is not None

    def update_task(self, task_id, **changes):
        task = self.find_task(task_id)
        if not task:
            return None

        if "status" in changes:
            status = changes["status"]
            if status not in ("pending", "in_progress", "completed"):
                status = "pending"
            changes["status"] = status
            if status == "completed":
                changes["completed"] = True
            else:
                changes["completed"] = False
        elif "completed" in changes:
            if changes["completed"]:
                changes["status"] = "completed"
            elif task.get("status") == "completed":
                changes["status"] = "pending"

        task.update(changes)
        self.save_tasks()
        return task

    def ensure_task_defaults(self):
        changed = False
        for task in self.tasks.get("all_tasks", []):
            if "status" not in task:
                task["status"] = "completed" if task.get("completed", False) else "pending"
                changed = True
            if "favorite" not in task:
                task["favorite"] = False
                changed = True
            if "sort_order" not in task:
                task["sort_order"] = 0
                changed = True
            if "subtasks" not in task:
                task["subtasks"] = []
                changed = True
            normalized_subtasks = []
            subtask_changed = False
            for index, subtask in enumerate(task.get("subtasks", []), start=1):
                if not isinstance(subtask, dict):
                    subtask_changed = True
                    continue
                normalized_subtask = {
                    "id": subtask.get("id", index),
                    "title": subtask.get("title", ""),
                    "completed": subtask.get("completed", False),
                }
                if normalized_subtask != subtask:
                    subtask_changed = True
                normalized_subtasks.append(normalized_subtask)
            if subtask_changed:
                task["subtasks"] = normalized_subtasks
                changed = True

        if changed:
            self.save_tasks()
        return changed

    def delete_task(self, task_id):
        all_tasks = self.tasks.get("all_tasks", [])
        original_count = len(all_tasks)
        self.tasks["all_tasks"] = [task for task in all_tasks if task.get("id") != task_id]
        deleted = original_count - len(self.tasks["all_tasks"])
        if deleted:
            self.save_tasks()
        return deleted

    def restore_task(self, task):
        """Put a previously deleted task back, so a delete can be undone."""
        if not task or task.get("id") is None:
            return None
        if self.task_exists(task.get("id")):
            return self.find_task(task.get("id"))

        restored = dict(task)
        self.tasks.setdefault("all_tasks", []).append(restored)
        self.save_tasks()
        return restored

    def clear_archived_tasks(self):
        all_tasks = self.tasks.get("all_tasks", [])
        original_count = len(all_tasks)
        self.tasks["all_tasks"] = [task for task in all_tasks if not task.get("completed", False)]
        deleted = original_count - len(self.tasks["all_tasks"])
        if deleted:
            self.save_tasks()
        return deleted

    def toggle_task_completed(self, task_id):
        task = self.find_task(task_id)
        if not task:
            return None
        new_completed = not task.get("completed", False)
        task["completed"] = new_completed
        task["status"] = "completed" if new_completed else "pending"
        self.save_tasks()
        return task

    def toggle_task_favorite(self, task_id):
        task = self.find_task(task_id)
        if not task:
            return None
        task["favorite"] = not task.get("favorite", False)
        self.save_tasks()
        return task

    def reorder_task(self, dragged_task_id, target_task_id, current_list):
        if dragged_task_id == target_task_id:
            return False

        dragged_task = self.find_task(dragged_task_id)
        target_task = self.find_task(target_task_id)
        if not dragged_task or not target_task:
            return False

        current_tasks = self.get_tasks(current_list)
        dragged_in_list = any(task.get("id") == dragged_task_id for task in current_tasks)
        target_in_list = any(task.get("id") == target_task_id for task in current_tasks)
        if not (dragged_in_list and target_in_list):
            return False

        target_order = target_task.get("sort_order", 0)
        dragged_task["sort_order"] = target_order

        for task in current_tasks:
            if task.get("id") != dragged_task_id and task.get("sort_order", 0) >= target_order:
                task["sort_order"] = task.get("sort_order", 0) + 1

        self.save_tasks()
        return True

    def move_task_kanban(self, task_id, new_status, target_task_id=None):
        task = self.find_task(task_id)
        if not task:
            return None
        if new_status not in ("pending", "in_progress", "completed"):
            return None

        self.update_task(task_id, status=new_status)
        if target_task_id and target_task_id != task_id:
            target_task = self.find_task(target_task_id)
            if target_task:
                target_order = target_task.get("sort_order", 0)
                task["sort_order"] = target_order
                for other in self.tasks.get("all_tasks", []):
                    if (
                        other.get("id") != task_id
                        and other.get("status") == new_status
                        and other.get("sort_order", 0) >= target_order
                    ):
                        other["sort_order"] = other.get("sort_order", 0) + 1
                self.save_tasks()
        return task

    def delete_project(self, project_id):
        if project_id == "inbox":
            return False

        project = self.get_project_by_id(project_id)
        if not project:
            return False

        project_name = project["name"]
        inbox_project = self.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")

        for task in self.tasks.get("all_tasks", []):
            if task.get("project") == project_name:
                task["project"] = inbox_name

        self.projects = [project for project in self.projects if project.get("id") != project_id]
        self.save_tasks()
        return True

    def _get_subtasks(self, task):
        subtasks = task.setdefault("subtasks", [])
        return subtasks

    def _get_next_subtask_id(self, task):
        subtasks = self._get_subtasks(task)
        max_id = 0
        for subtask in subtasks:
            max_id = max(max_id, subtask.get("id", 0))
        return max_id + 1

    def add_subtask(self, task_id, title):
        task = self.find_task(task_id)
        if not task:
            return None

        cleaned_title = (title or "").strip()
        if not cleaned_title:
            return None

        subtask = {
            "id": self._get_next_subtask_id(task),
            "title": cleaned_title,
            "completed": False,
        }
        self._get_subtasks(task).append(subtask)
        self.save_tasks()
        return subtask

    def find_subtask(self, task_id, subtask_id):
        task = self.find_task(task_id)
        if not task:
            return None

        for subtask in self._get_subtasks(task):
            if subtask.get("id") == subtask_id:
                return subtask
        return None

    def update_subtask(self, task_id, subtask_id, **changes):
        subtask = self.find_subtask(task_id, subtask_id)
        if not subtask:
            return None

        if "title" in changes:
            changes["title"] = changes["title"].strip()
            if not changes["title"]:
                return None

        subtask.update(changes)
        self.save_tasks()
        return subtask

    def toggle_subtask_completed(self, task_id, subtask_id):
        subtask = self.find_subtask(task_id, subtask_id)
        if not subtask:
            return None

        subtask["completed"] = not subtask.get("completed", False)
        self.save_tasks()
        return subtask

    def delete_subtask(self, task_id, subtask_id):
        task = self.find_task(task_id)
        if not task:
            return False

        subtasks = self._get_subtasks(task)
        original_count = len(subtasks)
        task["subtasks"] = [subtask for subtask in subtasks if subtask.get("id") != subtask_id]
        deleted = len(task["subtasks"]) != original_count
        if deleted:
            self.save_tasks()
        return deleted

    def export_data(self, export_file):
        self.repository.export_data(export_file, self.tasks, self.projects)

    def import_data(self, import_file):
        raw_data, raw_projects = self.repository.import_data(import_file)
        self.tasks, self.projects = migrate_loaded_data(raw_data, raw_projects)
        self.update_project_names()
        self.tasks, self.projects = normalize_inbox_projects(self.tasks, self.projects)
        if not self.projects:
            self.projects = [{"id": "inbox", "name": _("Inbox"), "color": "black"}]
        self.save_tasks()
        return self.tasks
