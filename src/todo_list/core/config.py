import json
import os
import tempfile

from .constants import DEFAULT_CONFIG
from .debug import debug


def get_config_dir():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return os.path.join(config_home, "todo-list")
    return os.path.join(os.path.expanduser("~"), ".config", "todo-list")


CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_FILE = os.path.join(CONFIG_DIR, "tasks.json")


class ConfigManager:
    def __init__(self):
        debug.log_event("CONFIG", "Initializing ConfigManager")
        self.config_file = CONFIG_FILE
        self.default_config = DEFAULT_CONFIG.copy()
        self.config = self.load_config()
        debug.log_event("CONFIG", f"Config loaded: {self.config}")

    def load_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as handle:
                    loaded_config = json.load(handle)
                    config = self.default_config.copy()
                    config.update(loaded_config)
                    return config
        except Exception as exc:
            debug.log_event("CONFIG", f"Error loading config: {exc}")
        return self.default_config.copy()

    def save_config(self):
        try:
            dirname = os.path.dirname(self.config_file)
            os.makedirs(dirname, exist_ok=True)

            with tempfile.NamedTemporaryFile("w", dir=dirname, delete=False, encoding="utf-8") as temp_file:
                json.dump(self.config, temp_file, indent=2, ensure_ascii=False)
                tempname = temp_file.name

            os.replace(tempname, self.config_file)
            debug.log_event("CONFIG", "Config saved successfully (atomic)")
        except Exception as exc:
            debug.log_event("CONFIG", f"Error saving config: {exc}")
            if "tempname" in locals() and os.path.exists(tempname):
                try:
                    os.remove(tempname)
                except Exception:
                    pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        debug.log_event("CONFIG", f"Setting {key} = {value}")
        self.config[key] = value
        self.save_config()
