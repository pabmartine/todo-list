import json
import tempfile
import unittest
from pathlib import Path

from todo_list.repositories.task_repository import TaskRepository


class TaskRepositoryTest(unittest.TestCase):
    def test_load_data_returns_defaults_when_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "tasks.json"
            repository = TaskRepository(data_file=str(data_file))

            tasks, projects = repository.load_data()

            self.assertEqual(tasks, {"all_tasks": []})
            self.assertEqual(projects, [])

    def test_save_data_persists_tasks_and_projects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "tasks.json"
            repository = TaskRepository(data_file=str(data_file))
            tasks = {
                "all_tasks": [
                    {
                        "id": 1,
                        "title": "Write tests",
                        "completed": False,
                        "priority": 0,
                        "notes": "",
                        "project": "Inbox",
                        "created_date": "2026-03-07T10:00:00",
                        "effective_date": None,
                        "list_id": "all",
                        "favorite": False,
                        "sort_order": 0,
                    }
                ]
            }
            projects = [{"id": "inbox", "name": "Inbox", "color": "black"}]

            repository.save_data(tasks, projects)

            self.assertTrue(data_file.exists())
            with data_file.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
            self.assertEqual(stored["all_tasks"], tasks["all_tasks"])
            self.assertEqual(stored["projects"], projects)

    def test_export_and_import_data_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "tasks.json"
            export_file = Path(temp_dir) / "backup.json"
            repository = TaskRepository(data_file=str(data_file))
            tasks = {"all_tasks": [{"id": 7, "title": "Export me"}]}
            projects = [{"id": "inbox", "name": "Inbox", "color": "black"}]

            repository.export_data(str(export_file), tasks, projects)
            imported_tasks, imported_projects = repository.import_data(str(export_file))

            self.assertEqual(imported_tasks["all_tasks"][0]["title"], "Export me")
            self.assertEqual(imported_projects, projects)
