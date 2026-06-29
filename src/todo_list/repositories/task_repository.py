import json
import os
import tempfile

from ..core.config import CONFIG_DIR, DATA_FILE
from ..core.debug import debug


class TaskRepository:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file

    def load_data(self):
        debug.log_event("TASKMAN", f"Loading tasks from {self.data_file}")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(self.data_file):
            return {"all_tasks": []}, []

        with open(self.data_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data, data.get("projects", [])

    def save_data(self, tasks, projects):
        dirname = os.path.dirname(self.data_file)
        os.makedirs(dirname, exist_ok=True)
        self._write_payload(self.data_file, {**tasks, "projects": projects})

    def import_data(self, import_file):
        with open(import_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data, data.get("projects", [])

    def export_data(self, export_file, tasks, projects):
        self._write_payload(export_file, {**tasks, "projects": projects})

    def _write_payload(self, output_file, payload):
        dirname = os.path.dirname(output_file) or "."
        os.makedirs(dirname, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile("w", dir=dirname, delete=False, encoding="utf-8") as temp_file:
                json.dump(payload, temp_file, indent=2, ensure_ascii=False)
                tempname = temp_file.name

            os.replace(tempname, output_file)
            debug.log_event("TASKMAN", "Tasks saved successfully (atomic)")
        except Exception as exc:
            debug.log_event("TASKMAN", f"Error saving tasks: {exc}")
            if "tempname" in locals() and os.path.exists(tempname):
                try:
                    os.remove(tempname)
                except Exception:
                    pass
