from dataclasses import dataclass


@dataclass
class Task:
    id: int
    title: str
    completed: bool
    priority: int
    notes: str
    project: str
    created_date: str
    effective_date: str | None
    list_id: str
    favorite: bool
    sort_order: int
    subtasks: list[dict]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "completed": self.completed,
            "priority": self.priority,
            "notes": self.notes,
            "project": self.project,
            "created_date": self.created_date,
            "effective_date": self.effective_date,
            "list_id": self.list_id,
            "favorite": self.favorite,
            "sort_order": self.sort_order,
            "subtasks": self.subtasks,
        }
