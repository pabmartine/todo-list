from ..core.i18n import translate as _
from ..models.project import Project


def _slugify_project_id(name):
    return name.lower().replace(" ", "_").replace("ã", "a")


class ProjectService:
    def __init__(self, task_service):
        self.task_service = task_service

    def create_project(self, name, color):
        project_id = _slugify_project_id(name)
        existing_ids = {project.get("id") for project in self.task_service.projects}
        original_id = project_id
        counter = 1
        while project_id in existing_ids:
            project_id = f"{original_id}_{counter}"
            counter += 1

        project = Project(id=project_id, name=name, color=color)
        self.task_service.projects.append(project.to_dict())
        self.task_service.save_tasks()
        return project.to_dict()

    def update_project(self, project_id, new_name, new_color):
        project = self.task_service.get_project_by_id(project_id)
        if not project:
            return False

        inbox_project = self.task_service.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        if not new_name or new_name == inbox_name:
            return False

        old_name = project["name"]
        project["name"] = new_name
        project["color"] = new_color

        for task in self.task_service.tasks.get("all_tasks", []):
            if task.get("project") == old_name:
                task["project"] = new_name

        self.task_service.save_tasks()
        return True

    def delete_project(self, project_id):
        return self.task_service.delete_project(project_id)
