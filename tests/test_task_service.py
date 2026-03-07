import datetime
import tempfile
import unittest
from pathlib import Path

from todo_list.repositories.task_repository import TaskRepository
from todo_list.services.task_service import TaskService


class TaskServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "tasks.json"
        self.repository = TaskRepository(data_file=str(self.data_file))
        self.service = TaskService(repository=self.repository)
        self.service.projects = [
            {"id": "inbox", "name": "Inbox", "color": "black"},
            {"id": "work", "name": "Work", "color": "blue"},
        ]
        today = datetime.date.today()
        self.service.tasks = {
            "all_tasks": [
                self._task(1, "Today task", effective_date=today.isoformat()),
                self._task(2, "Next week task", effective_date=(today + datetime.timedelta(days=3)).isoformat()),
                self._task(3, "Overdue task", effective_date=(today - datetime.timedelta(days=1)).isoformat()),
                self._task(4, "Favorite task", favorite=True),
                self._task(5, "Archived task", completed=True),
                self._task(6, "Project task", project="Work"),
            ]
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _task(self, task_id, title, **overrides):
        task = {
            "id": task_id,
            "title": title,
            "completed": False,
            "priority": 0,
            "notes": "",
            "project": "Inbox",
            "created_date": "2026-03-07T10:00:00",
            "effective_date": None,
            "list_id": "all",
            "favorite": False,
            "sort_order": task_id,
            "subtasks": [],
        }
        task.update(overrides)
        return task

    def test_get_tasks_filters_date_based_lists(self):
        self.assertEqual([task["id"] for task in self.service.get_tasks("today")], [1])
        self.assertEqual([task["id"] for task in self.service.get_tasks("next7")], [2])
        self.assertEqual([task["id"] for task in self.service.get_tasks("overdue")], [3])

    def test_get_tasks_filters_favorites_archived_and_projects(self):
        self.assertEqual([task["id"] for task in self.service.get_tasks("favorites")], [4])
        self.assertEqual([task["id"] for task in self.service.get_tasks("archived")], [5])
        self.assertEqual([task["id"] for task in self.service.get_tasks("project_work")], [6])

    def test_search_tasks_filters_current_view(self):
        result = self.service.search_tasks("all", "favorite")

        self.assertEqual([task["id"] for task in result], [4])

    def test_toggle_task_favorite_flips_flag_and_persists(self):
        updated_task = self.service.toggle_task_favorite(1)

        self.assertIsNotNone(updated_task)
        self.assertTrue(updated_task["favorite"])

        reloaded_service = TaskService(repository=self.repository)
        reloaded_task = reloaded_service.find_task(1)
        self.assertTrue(reloaded_task["favorite"])

    def test_add_update_toggle_and_delete_subtask(self):
        created_subtask = self.service.add_subtask(1, "Buy tickets")

        self.assertIsNotNone(created_subtask)
        self.assertEqual(created_subtask["title"], "Buy tickets")
        self.assertEqual(len(self.service.find_task(1)["subtasks"]), 1)

        updated_subtask = self.service.update_subtask(1, created_subtask["id"], title="Buy train tickets")
        self.assertEqual(updated_subtask["title"], "Buy train tickets")

        toggled_subtask = self.service.toggle_subtask_completed(1, created_subtask["id"])
        self.assertTrue(toggled_subtask["completed"])

        deleted = self.service.delete_subtask(1, created_subtask["id"])
        self.assertTrue(deleted)
        self.assertEqual(self.service.find_task(1)["subtasks"], [])

    def test_search_tasks_matches_subtask_titles(self):
        self.service.find_task(1)["subtasks"] = [{"id": 1, "title": "Passport", "completed": False}]

        result = self.service.search_tasks("all", "passport")

        self.assertEqual([task["id"] for task in result], [1])

    def test_clear_archived_tasks_removes_completed_tasks(self):
        deleted_count = self.service.clear_archived_tasks()

        self.assertEqual(deleted_count, 1)
        self.assertIsNone(self.service.find_task(5))

    def test_delete_project_moves_tasks_back_to_inbox(self):
        deleted = self.service.delete_project("work")

        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_project_by_id("work"))
        self.assertEqual(self.service.find_task(6)["project"], "Inbox")

    def test_reorder_task_moves_sort_order_within_current_list(self):
        self.service.tasks["all_tasks"] = [
            self._task(1, "A", sort_order=0),
            self._task(2, "B", sort_order=1),
            self._task(3, "C", sort_order=2),
        ]

        moved = self.service.reorder_task(1, 3, "all")

        self.assertTrue(moved)
        self.assertEqual(self.service.find_task(1)["sort_order"], 2)
        self.assertEqual(self.service.find_task(3)["sort_order"], 3)

    def test_export_and_import_data_replace_current_state(self):
        export_file = Path(self.temp_dir.name) / "backup.json"

        self.service.export_data(str(export_file))
        self.service.tasks = {"all_tasks": []}
        self.service.projects = []
        self.service.import_data(str(export_file))

        self.assertEqual(len(self.service.tasks["all_tasks"]), 6)
        self.assertIsNotNone(self.service.get_inbox_project())

    def test_import_data_migrates_legacy_payload(self):
        legacy_file = Path(self.temp_dir.name) / "legacy.json"
        legacy_file.write_text(
            """
{
  "today": [
    {
      "id": 9,
      "title": "Legacy task",
      "completed": false,
      "project": "Inbox"
    }
  ],
  "projects": [
    {
      "name": "Inbox"
    }
  ]
}
""".strip(),
            encoding="utf-8",
        )

        self.service.import_data(str(legacy_file))

        self.assertEqual(len(self.service.tasks["all_tasks"]), 1)
        self.assertEqual(self.service.tasks["all_tasks"][0]["list_id"], "today")
        self.assertFalse(self.service.tasks["all_tasks"][0]["favorite"])
        self.assertEqual(self.service.get_inbox_project()["id"], "inbox")
