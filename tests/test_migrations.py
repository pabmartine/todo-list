import unittest

from todo_list.repositories.migrations import migrate_loaded_data, normalize_inbox_projects


class MigrationTest(unittest.TestCase):
    def test_migrate_loaded_data_converts_legacy_lists_to_all_tasks(self):
        legacy_data = {
            "today": [{"id": 1, "title": "Today task"}],
            "favorites": [{"id": 2, "title": "Favorite task", "favorite": True}],
        }
        projects = [{"name": "Work", "color": "blue"}]

        tasks, migrated_projects = migrate_loaded_data(legacy_data, projects)

        self.assertEqual(len(tasks["all_tasks"]), 2)
        self.assertEqual(tasks["all_tasks"][0]["list_id"], "today")
        self.assertEqual(tasks["all_tasks"][1]["list_id"], "favorites")
        self.assertFalse(tasks["all_tasks"][0]["favorite"])
        self.assertEqual(tasks["all_tasks"][0]["sort_order"], 0)
        self.assertEqual(tasks["all_tasks"][0]["subtasks"], [])
        self.assertEqual(migrated_projects[0]["id"], "work")

    def test_migrate_loaded_data_normalizes_subtasks(self):
        data = {
            "all_tasks": [
                {
                    "id": 1,
                    "title": "Parent",
                    "subtasks": [{"title": "Child"}],
                }
            ]
        }

        tasks, _ = migrate_loaded_data(data, [])

        self.assertEqual(tasks["all_tasks"][0]["subtasks"][0]["id"], 1)
        self.assertEqual(tasks["all_tasks"][0]["subtasks"][0]["title"], "Child")
        self.assertFalse(tasks["all_tasks"][0]["subtasks"][0]["completed"])

    def test_normalize_inbox_projects_merges_duplicate_inboxes_and_repoints_tasks(self):
        tasks = {
            "all_tasks": [
                {"id": 1, "title": "A", "project": "Inbox"},
                {"id": 2, "title": "B", "project": "Bandeja de entrada"},
            ]
        }
        projects = [
            {"id": "custom", "name": "Inbox", "color": "red"},
            {"id": "inbox", "name": "Bandeja de entrada", "color": "blue"},
            {"id": "work", "name": "Work", "color": "green"},
        ]

        normalized_tasks, normalized_projects = normalize_inbox_projects(tasks, projects)

        self.assertEqual(normalized_projects[0]["id"], "inbox")
        self.assertEqual(normalized_projects[0]["name"], "Inbox")
        self.assertEqual(normalized_projects[0]["color"], "black")
        self.assertEqual(len([project for project in normalized_projects if project["id"] == "inbox"]), 1)
        self.assertEqual(normalized_tasks["all_tasks"][0]["project"], "Inbox")
        self.assertEqual(normalized_tasks["all_tasks"][1]["project"], "Inbox")

    def test_normalize_inbox_projects_creates_inbox_when_missing(self):
        tasks = {"all_tasks": []}
        projects = [{"id": "work", "name": "Work", "color": "green"}]

        _, normalized_projects = normalize_inbox_projects(tasks, projects)

        self.assertEqual(normalized_projects[0]["id"], "inbox")
        self.assertEqual(normalized_projects[0]["name"], "Inbox")
