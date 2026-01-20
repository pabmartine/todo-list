#!/usr/bin/env python3

import sys
import os
import json
import locale
import gettext
import datetime
import functools
import time
import threading
import tempfile
from pathlib import Path
from collections import OrderedDict
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, Pango, Gdk

# Sistema de Debug Avanzado
class DebugTracker:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
        self.max_events = 200
        self.enabled = True
    
    def log_event(self, event_type, details, stack_info=False):
        if not self.enabled:
            return
            
        with self.lock:
            timestamp = time.time()
            event = {
                'timestamp': timestamp,
                'type': event_type,
                'details': details,
                'thread': threading.current_thread().name
            }
            
            if stack_info:
                import traceback
                event['stack'] = traceback.format_stack()
            
            self.events.append(event)
            
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
            
            # Imprimir inmediatamente con timestamp más legible
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{time_str}.{int((timestamp % 1) * 1000):03d}] {event_type}: {details}")
            
            if stack_info and 'stack' in event:
                print("  Stack trace (last 3):")
                for line in event['stack'][-3:]:
                    print(f"    {line.strip()}")
    
    def dump_recent_events(self, last_n=30):
        with self.lock:
            print("\n" + "="*50)
            print("ÚLTIMOS EVENTOS DE DEBUG")
            print("="*50)
            for event in self.events[-last_n:]:
                time_str = time.strftime("%H:%M:%S", time.localtime(event['timestamp']))
                print(f"[{time_str}] {event['type']}: {event['details']}")
            print("="*50 + "\n")

# Singleton global para debug
debug = DebugTracker()

def debug_method(method_name):
    """Decorador para trackear métodos críticos"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            debug.log_event(f"{method_name}_START", f"Args: {len(args)}")
            try:
                result = func(self, *args, **kwargs)
                debug.log_event(f"{method_name}_END", "Success")
                return result
            except Exception as e:
                debug.log_event(f"{method_name}_ERROR", f"Error: {e}", stack_info=True)
                raise
        return wrapper
    return decorator

# Configuración de internacionalización
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")
DOMAIN = "todo-list"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "todo-list")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_FILE = os.path.join(CONFIG_DIR, "tasks.json")

def get_locale_dir():
    """Obtener directorio de locale apropiado"""
    possible_dirs = [
        "/app/share/locale",
        os.path.join(os.path.dirname(__file__), "locale"),
        "/usr/share/locale"
    ]
    
    for locale_dir in possible_dirs:
        if os.path.exists(locale_dir):
            return locale_dir
    
    return os.path.join(os.path.dirname(__file__), "locale")

def get_config_dir():
    """Obtener directorio de configuración apropiado"""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return os.path.join(config_home, "todo-list")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "todo-list")

LOCALE_DIR = get_locale_dir()
DOMAIN = "todo-list"

CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_FILE = os.path.join(CONFIG_DIR, "tasks.json")

def setup_locale(language=None):
    """Configurar el idioma de la aplicación - Compatible con Flatpak"""
    debug.log_event("LOCALE", f"Setting up locale: {language}")
    
    if language and language != "auto":
        try:
            os.environ["LANGUAGE"] = language
            os.environ["LC_MESSAGES"] = language
        except:
            pass
    
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, "C.UTF-8")
        except locale.Error:
            pass
    
    try:
        is_flatpak = os.path.exists("/app") or os.environ.get("FLATPAK_ID")
        
        if is_flatpak:
            locale_dir = "/app/share/locale"
        else:
            locale_dir = LOCALE_DIR
        
        if os.path.exists(locale_dir):
            lang_translations = gettext.translation(DOMAIN, locale_dir, fallback=True)
            lang_translations.install()
            debug.log_event("LOCALE", "Translations loaded successfully")
            return lang_translations.gettext
        else:
            debug.log_event("LOCALE", "No translations found, using fallback")
            return lambda text: text
            
    except Exception as e:
        debug.log_event("LOCALE", f"Error setting up locale: {e}")
        return lambda text: text

# Configurar idioma inicial
_ = setup_locale()

class ConfigManager:
    def __init__(self):
        debug.log_event("CONFIG", "Initializing ConfigManager")
        self.config_file = CONFIG_FILE
        self.default_config = {
            "language": "auto",
            "dark_theme": False,
            "window_width": 1200,
            "window_height": 800,
            "current_list": "today",
        }
        self.config = self.load_config()
        debug.log_event("CONFIG", f"Config loaded: {self.config}")

    def load_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    config = self.default_config.copy()
                    config.update(loaded_config)
                    return config
        except Exception as e:
            debug.log_event("CONFIG", f"Error loading config: {e}")
        return self.default_config.copy()

    def save_config(self):
        try:
            dirname = os.path.dirname(self.config_file)
            os.makedirs(dirname, exist_ok=True)
            
            # Atomic save
            with tempfile.NamedTemporaryFile("w", dir=dirname, delete=False, encoding="utf-8") as tf:
                json.dump(self.config, tf, indent=2, ensure_ascii=False)
                tempname = tf.name
                
            os.replace(tempname, self.config_file)
            debug.log_event("CONFIG", "Config saved successfully (atomic)")
        except Exception as e:
            debug.log_event("CONFIG", f"Error saving config: {e}")
            if 'tempname' in locals() and os.path.exists(tempname):
                try:
                    os.remove(tempname)
                except:
                    pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        debug.log_event("CONFIG", f"Setting {key} = {value}")
        self.config[key] = value
        self.save_config()

class TaskManager:
    def __init__(self):
        debug.log_event("TASKMAN", "Initializing TaskManager")
        self.data_file = DATA_FILE
        self.lists = {
            "today": _("Today"), 
            "next7": _("Next 7 days"),
            "all": _("All"),
            "overdue": _("Overdue"),
            "favorites": _("Favorites"),
            "archived": _("Archived")
        }
        self.projects = []
        self.tasks = self.load_tasks()
        if not self.projects:
            self.projects = [
                {"id": "inbox", "name": _("Inbox"), "color": "black"}
            ]
            self.save_tasks()
        debug.log_event("TASKMAN", f"TaskManager initialized. Tasks: {len(self.tasks.get('all_tasks', []))}, Projects: {len(self.projects)}")

    def update_list_names(self):
        """Actualizar nombres de listas con traducciones"""
        debug.log_event("TASKMAN", "Updating list names")
        self.lists = {
            "today": _("Today"), 
            "next7": _("Next 7 days"),
            "all": _("All"),
            "overdue": _("Overdue"),
            "favorites": _("Favorites"),
            "archived": _("Archived")
        }

    def update_project_names(self):
        """Actualizar nombre del proyecto Inbox según el idioma actual"""
        debug.log_event("TASKMAN", "Updating project names")
        for project in self.projects:
            if project.get("id") == "inbox":
                old_name = project["name"]
                new_name = _("Inbox")
                project["name"] = new_name
                if old_name != new_name:
                    debug.log_event("TASKMAN", f"Updating inbox name from '{old_name}' to '{new_name}'")
                    all_tasks = self.tasks.get("all_tasks", [])
                    for task in all_tasks:
                        if task.get("project") == old_name:
                            task["project"] = new_name
                break

    def migrate_legacy_projects(self):
        """Migrar proyectos legacy sin ID a la nueva estructura"""
        debug.log_event("TASKMAN", "Checking for legacy project migration")
        needs_migration = False
        
        for project in self.projects:
            if "id" not in project:
                needs_migration = True
                break
        
        if needs_migration:
            debug.log_event("TASKMAN", "Starting legacy project migration")
            inbox_variants = ["Inbox", "Bandeja de entrada"]
            inbox_projects = [p for p in self.projects if p["name"] in inbox_variants]
            
            if len(inbox_projects) > 1:
                main_inbox = inbox_projects[0]
                main_inbox["id"] = "inbox"
                main_inbox["name"] = _("Inbox")
                
                all_tasks = self.tasks.get("all_tasks", [])
                for project in inbox_projects[1:]:
                    for task in all_tasks:
                        if task.get("project") == project["name"]:
                            task["project"] = main_inbox["name"]
                    self.projects.remove(project)
            
            for project in self.projects:
                if "id" not in project:
                    if project["name"] == _("Inbox") or project["name"] in inbox_variants:
                        project["id"] = "inbox"
                        project["name"] = _("Inbox")
                    else:
                        project_id = project["name"].lower().replace(" ", "_").replace("ã", "a")
                        project["id"] = project_id
            
            self.save_tasks()
            debug.log_event("TASKMAN", "Legacy project migration completed")

    def clean_duplicate_inboxes(self):
        """Limpiar proyectos Inbox duplicados"""
        debug.log_event("TASKMAN", "Cleaning duplicate inboxes")
        inbox_variants = set(["Inbox", "Bandeja de entrada"])
        current_inbox_name = _("Inbox")
        inbox_variants.add(current_inbox_name)
        
        potential_inboxes = [
            p for p in self.projects 
            if p.get("id") == "inbox" or p["name"] in inbox_variants
        ]
        
        if len(potential_inboxes) <= 1:
            debug.log_event("TASKMAN", "No duplicate inboxes found")
            return
        
        debug.log_event("TASKMAN", f"Found {len(potential_inboxes)} potential inbox duplicates")
        
        main_inbox = next(
            (p for p in potential_inboxes if p.get("id") == "inbox"), 
            potential_inboxes[0]
        )
        
        main_inbox["id"] = "inbox"
        main_inbox["name"] = current_inbox_name
        main_inbox["color"] = "black"
        
        duplicate_names = {p["name"] for p in potential_inboxes}
        
        all_tasks = self.tasks.get("all_tasks", [])
        for task in all_tasks:
            if task.get("project") in duplicate_names:
                task["project"] = main_inbox["name"]
        
        self.projects = [
            p for p in self.projects if p not in potential_inboxes
        ] + [main_inbox]
        
        self.save_tasks()
        debug.log_event("TASKMAN", "Duplicate inboxes cleaned")

    def load_tasks(self):
        debug.log_event("TASKMAN", f"Loading tasks from {self.data_file}")
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.projects = data.get("projects", [])
                    
                    self.migrate_legacy_projects()
                    self.clean_duplicate_inboxes()
                    
                    if "all_tasks" not in data:
                        all_tasks = []
                        for k, v in data.items():
                            if k != "projects" and isinstance(v, list):
                                for task in v:
                                    if "list_id" not in task:
                                        task["list_id"] = k
                                    all_tasks.append(task)
                        debug.log_event("TASKMAN", f"Migrated {len(all_tasks)} tasks from legacy format")
                        return {"all_tasks": all_tasks}
                    else:
                        debug.log_event("TASKMAN", f"Loaded {len(data.get('all_tasks', []))} tasks")
                        return {k: v for k, v in data.items() if k != "projects"}
        except Exception as e:
            debug.log_event("TASKMAN", f"Error loading tasks: {e}")
        return {"all_tasks": []}

    def save_tasks(self):
        try:
            data = {**self.tasks, "projects": self.projects}
            dirname = os.path.dirname(self.data_file)
            os.makedirs(dirname, exist_ok=True)
            
            # Atomic save: write to temp file then rename
            with tempfile.NamedTemporaryFile("w", dir=dirname, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=2, ensure_ascii=False)
                tempname = tf.name
            
            os.replace(tempname, self.data_file)
            debug.log_event("TASKMAN", "Tasks saved successfully (atomic)")
        except Exception as e:
            debug.log_event("TASKMAN", f"Error saving tasks: {e}")
            if 'tempname' in locals() and os.path.exists(tempname):
                try:
                    os.remove(tempname)
                except:
                    pass

    def add_task(self, list_id, title, due_date=None, priority=0, notes="", project=None, effective_date=None):
        debug.log_event("TASKMAN", f"Adding task: '{title}' to list {list_id}")
        if project is None:
            inbox_project = self.get_inbox_project()
            project = inbox_project["name"] if inbox_project else _("Inbox")
        
        now = datetime.datetime.now()
        task = {
            "id": self.get_next_id(),
            "title": title,
            "completed": False,
            "priority": priority,
            "notes": notes,
            "project": project,
            "created_date": now.isoformat(),
            "effective_date": effective_date,
            "list_id": list_id,
            "favorite": False,
            "sort_order": 0
        }
        
        if "all_tasks" not in self.tasks:
            self.tasks["all_tasks"] = []
        self.tasks["all_tasks"].append(task)
        self.save_tasks()
        debug.log_event("TASKMAN", f"Task added with ID: {task['id']}")

    def get_inbox_project(self):
        """Obtener el proyecto Inbox por ID"""
        for project in self.projects:
            if project.get("id") == "inbox":
                return project
        return None

    def get_next_id(self):
        max_id = 0
        all_tasks = self.tasks.get("all_tasks", [])
        for task in all_tasks:
            if task.get("id", 0) > max_id:
                max_id = task.get("id", 0)
        return max_id + 1

    def get_tasks(self, list_id):
        debug.log_event("TASKMAN", f"Getting tasks for list: {list_id}")
        all_tasks = self.tasks.get("all_tasks", [])
        
        if list_id == "overdue":
            result = self._get_overdue_tasks(all_tasks)
        elif list_id == "today":
            result = self._get_today_tasks(all_tasks)
        elif list_id == "next7":
            result = self._get_next7_tasks(all_tasks)
        elif list_id == "all":
            result = [task for task in all_tasks if not task.get("completed", False)]
        elif list_id == "favorites":
            result = [task for task in all_tasks if task.get("favorite", False) and not task.get("completed", False)]
        elif list_id == "archived":
            result = [task for task in all_tasks if task.get("completed", False)]
        elif list_id.startswith("project_"):
            project_id = list_id.replace("project_", "")
            project = self.get_project_by_id(project_id)
            if project:
                project_name = project["name"]
                result = [task for task in all_tasks if task.get("project") == project_name and not task.get("completed", False)]
            else:
                result = []
        else:
            result = []
        
        debug.log_event("TASKMAN", f"Retrieved {len(result)} tasks for list {list_id}")
        return result

    def get_project_by_id(self, project_id):
        """Obtener proyecto por ID"""
        for project in self.projects:
            if project.get("id") == project_id:
                return project
        return None

    def _get_today_tasks(self, all_tasks):
        today = datetime.date.today()
        today_tasks = []
        
        for task in all_tasks:
            if task.get("completed", False):
                continue
                
            effective_date_str = task.get("effective_date")
            if not effective_date_str:
                continue
                
            try:
                effective_date = datetime.datetime.fromisoformat(effective_date_str).date()
                if effective_date == today:
                    today_tasks.append(task)
            except (ValueError, TypeError):
                pass
                
        return today_tasks

    def _get_overdue_tasks(self, all_tasks):
        today = datetime.date.today()
        overdue = []
        
        for task in all_tasks:
            if task.get("completed", False):
                continue
                
            effective_date_str = task.get("effective_date")
            if not effective_date_str:
                continue
                
            try:
                effective_date = datetime.datetime.fromisoformat(effective_date_str).date()
                if effective_date < today:
                    overdue.append(task)
            except (ValueError, TypeError):
                pass
                
        return overdue

    def _get_next7_tasks(self, all_tasks):
        today = datetime.date.today()
        next7_tasks = []
        
        for task in all_tasks:
            if task.get("completed", False):
                continue
                
            effective_date_str = task.get("effective_date")
            if not effective_date_str:
                continue
                
            try:
                effective_date = datetime.datetime.fromisoformat(effective_date_str).date()
                days_diff = (effective_date - today).days
                if 1 <= days_diff <= 7:
                    next7_tasks.append(task)
            except (ValueError, TypeError):
                pass
                
        return next7_tasks

    def get_task_count(self, list_id):
        count = len(self.get_tasks(list_id))
        debug.log_event("TASKMAN", f"Task count for {list_id}: {count}")
        return count

    def delete_project(self, project_id):
        """Eliminar proyecto por ID"""
        debug.log_event("TASKMAN", f"Deleting project: {project_id}")
        if project_id == "inbox":
            debug.log_event("TASKMAN", "Cannot delete inbox project")
            return
        
        project = self.get_project_by_id(project_id)
        if not project:
            debug.log_event("TASKMAN", f"Project {project_id} not found")
            return
            
        project_name = project["name"]
        inbox_project = self.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        
        all_tasks = self.tasks.get("all_tasks", [])
        tasks_moved = 0
        for task in all_tasks:
            if task.get("project") == project_name:
                task["project"] = inbox_name
                tasks_moved += 1
        
        self.projects = [p for p in self.projects if p.get("id") != project_id]
        self.save_tasks()
        debug.log_event("TASKMAN", f"Project deleted, moved {tasks_moved} tasks to inbox")

class TaskManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        debug.log_event("WINDOW", "Starting window initialization")
        super().__init__(**kwargs)
        
        # Variables de estado con debug
        self.config = ConfigManager()
        self.task_manager = TaskManager()
        self.current_language = self.config.get("language", "auto")
        self.current_list = self.config.get("current_list", "today")
        self.sort_ascending = False
        self.current_task_info = None
        self.selected_color = None
        self.selected_color_button = None

        # Variables de control de estado
        self._ui_state_valid = True
        self._last_refresh_time = 0
        self._refresh_in_progress = False
        self._updating_favorite = False
        self._refreshing_sidebar = False
        self._in_cleanup = False

        debug.log_event("WINDOW", f"Window state initialized - current_list: {self.current_list}")

        self.ensure_inbox_project()
        self.apply_saved_config()
        self.set_title(_("Todo List"))
        
        window_width = self.config.get("window_width", 1200)
        window_height = self.config.get("window_height", 800)
        self.set_default_size(window_width, window_height)
        self.set_size_request(360, 200)

        self.setup_ui()
        self.setup_custom_css()
        self.setup_shortcuts()
        self.connect("close-request", self.on_window_close)
        self.initialize_sample_data()
        
        debug.log_event("WINDOW", "Window initialization completed")

    def ensure_inbox_project(self):
        """Asegurar que existe el proyecto Inbox y actualizar su nombre según el idioma"""
        debug.log_event("WINDOW", "Ensuring inbox project exists")
        inbox_exists = any(p.get("id") == "inbox" for p in self.task_manager.projects)
        if not inbox_exists:
            inbox_project = {"id": "inbox", "name": _("Inbox"), "color": "black"}
            self.task_manager.projects.insert(0, inbox_project)
            self.task_manager.save_tasks()
            debug.log_event("WINDOW", "Created inbox project")
        else:
            self.task_manager.update_project_names()
            self.task_manager.save_tasks()
            debug.log_event("WINDOW", "Updated existing inbox project")

    def apply_saved_config(self):
        debug.log_event("WINDOW", "Applying saved configuration")
        saved_language = self.config.get("language", "auto")
        if saved_language != "auto":
            global _
            _ = setup_locale(saved_language)
        dark_theme = self.config.get("dark_theme", False)
        self.apply_theme(dark_theme)

    def apply_theme(self, dark_theme):
        debug.log_event("WINDOW", f"Applying theme - dark: {dark_theme}")
        style_manager = Adw.StyleManager.get_default()
        if dark_theme:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def change_language(self, language_code):
        """Cambiar el idioma de la aplicación"""
        debug.log_event("WINDOW", f"Changing language to: {language_code}")
        global _
        _ = setup_locale(language_code if language_code != "auto" else None)
        self.config.set("language", language_code)
        self.current_language = language_code
        
        self.task_manager.update_list_names()
        self.task_manager.update_project_names()
        self.task_manager.clean_duplicate_inboxes()
        self.task_manager.save_tasks()
        
        self.recreate_ui()

    def change_theme(self, dark_theme):
        """Cambiar tema de la aplicación"""
        debug.log_event("WINDOW", f"Changing theme to dark: {dark_theme}")
        self.apply_theme(dark_theme)
        self.config.set("dark_theme", dark_theme)

    def recreate_ui(self):
        """Recrear la interfaz con los textos actualizados"""
        debug.log_event("UI", "Recreating UI with updated texts")
        
        self.set_title(_("Todo List"))
        
        if hasattr(self, 'new_list_btn'):
            self.new_list_btn.set_tooltip_text(_("Add Project"))
        
        if hasattr(self, 'new_task_entry'):
            self.new_task_entry.set_placeholder_text(_("New task..."))
        
        if hasattr(self, 'clear_archived_button'):
            self.clear_archived_button.set_tooltip_text(_("Clear all archived tasks"))
        
        self.refresh_sidebar()
        self.refresh_task_list()
        debug.log_event("UI", "UI recreation completed")

    def _cleanup_ui_state(self):
        """Limpiar estado de UI antes de cambios importantes"""
        if self._in_cleanup:
            debug.log_event("CLEANUP", "Already in cleanup, skipping")
            return
            
        self._in_cleanup = True
        debug.log_event("CLEANUP", "Starting UI state cleanup")
        
        try:
            # Cerrar panel de info
            if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
                debug.log_event("CLEANUP", "Closing task info panel")
                self.on_close_task_info(None)
            
            # Limpiar selección actual
            if hasattr(self, 'current_task_info') and self.current_task_info:
                debug.log_event("CLEANUP", f"Clearing current task info: {self.current_task_info.get('title', 'unknown')}")
                self.current_task_info = None
            
            # Limpiar selección de la lista de tareas
            if hasattr(self, 'task_list'):
                self.task_list.unselect_all()
                debug.log_event("CLEANUP", "Cleared task list selection")
            
            debug.log_event("CLEANUP", "UI state cleanup completed")
        except Exception as e:
            debug.log_event("CLEANUP", f"Error during cleanup: {e}")
        finally:
            self._in_cleanup = False

    @debug_method("setup_ui")
    def setup_ui(self):
        debug.log_event("UI", "Setting up main UI")
        
        # Breakpoint para colapsar en pantallas pequeñas
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 600sp"))
        self.add_breakpoint(breakpoint)
        
        # NavigationSplitView principal
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_sidebar_width_fraction(0.33)
        self.split_view.set_min_sidebar_width(280)
        self.split_view.set_max_sidebar_width(350)
        
        # Conectar breakpoint para colapsar
        breakpoint.add_setter(self.split_view, "collapsed", True)
        
        # Crear componentes
        self.create_sidebar()
        self.create_main_area()
        self.create_task_info_panel()
        
        # Configurar split view
        self.split_view.set_sidebar(self.sidebar_page)
        self.split_view.set_content(self.content_page)
        
        self.set_content(self.split_view)
        
        self.refresh_task_list()
        debug.log_event("UI", "Main UI setup completed")

    @debug_method("create_sidebar")
    def create_sidebar(self):
        """Crear sidebar usando NavigationPage"""
        debug.log_event("UI", "Creating sidebar")
        
        self.sidebar_page = Adw.NavigationPage()
        self.sidebar_page.set_title(_("Lists"))  # TÍTULO AÑADIDO
        self.sidebar_page.set_tag("sidebar")
        
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_header = Adw.HeaderBar()
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_content.set_margin_top(12)
        sidebar_content.set_margin_bottom(12)
        sidebar_content.set_margin_start(12)
        sidebar_content.set_margin_end(12)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(12)

        self.main_list_group = Gtk.ListBox()
        self.main_list_group.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.main_list_group.add_css_class("navigation-sidebar")
        self.main_list_group.connect("row-activated", self.on_list_selected)

        for list_id, list_name in self.task_manager.lists.items():
            row = self.create_sidebar_row(list_id, list_name, is_project=False)
            self.main_list_group.append(row)
        content_box.append(self.main_list_group)

        separator = Gtk.Separator(margin_top=6, margin_bottom=6)
        content_box.append(separator)

        # Header para proyectos con botón
        projects_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        projects_header_box.set_margin_bottom(6)

        projects_label = Gtk.Label(label=_("Projects"), halign=Gtk.Align.START)
        projects_label.add_css_class("title-4")
        projects_label.set_hexpand(True)
        projects_header_box.append(projects_label)

        self.new_list_btn = Gtk.Button()
        self.new_list_btn.set_icon_name("ymuse-add-symbolic")
        self.new_list_btn.add_css_class("flat")
        self.new_list_btn.set_tooltip_text(_("Add Project"))
        self.new_list_btn.connect("clicked", self.on_add_project)
        projects_header_box.append(self.new_list_btn)

        content_box.append(projects_header_box)

        self.projects_list_group = Gtk.ListBox()
        self.projects_list_group.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.projects_list_group.add_css_class("navigation-sidebar")
        self.projects_list_group.connect("row-activated", self.on_list_selected)

        for project in self.task_manager.projects:
            project_id = f"project_{project.get('id', project['name'])}"
            row = self.create_sidebar_row(project_id, project['name'], is_project=True, color=project['color'])
            self.projects_list_group.append(row)
        content_box.append(self.projects_list_group)

        GLib.idle_add(self.select_current_list)

        scrolled.set_child(content_box)
        sidebar_content.append(scrolled)
        
        sidebar_toolbar.set_content(sidebar_content)
        self.sidebar_page.set_child(sidebar_toolbar)
        
        debug.log_event("UI", "Sidebar created successfully")

    def create_sidebar_row(self, list_id, name, is_project=False, color=None):
        debug.log_event("UI", f"Creating sidebar row: {list_id} - {name}")
        
        row = Adw.ActionRow(title=name)
        row.set_name(list_id)
        
        if is_project:
            color_dot = Gtk.Box()
            color_dot.add_css_class("project-color")
            inbox_project = self.task_manager.get_inbox_project()
            if inbox_project and name == inbox_project["name"]:
                color_dot.remove_css_class("color-purple")
                color_dot.add_css_class("color-black")
            elif color:
                color_dot.add_css_class(f"color-{color}")
            row.add_prefix(color_dot)
        else:
            icon_name_map = {
                "today": "go-jump-today-symbolic", 
                "next7": "date-next-symbolic",
                "all": "emblem-documents-symbolic", 
                "overdue": "appointment-missed-symbolic",
                "favorites": "folder-favorites-symbolic",
                "archived": "archive-symbolic"
            }
            icon_name = icon_name_map.get(list_id, "folder-symbolic")
            icon = Gtk.Image.new_from_icon_name(icon_name)
            row.add_prefix(icon)

        count = self.task_manager.get_task_count(list_id)
        
        count_label = Gtk.Label(label=str(count))
        count_label.add_css_class("dim-label")
        count_label.set_name(f"count_{list_id}")
        row.add_suffix(count_label)
        
        row.set_activatable(True)
        
        return row

    def select_current_list(self):
        debug.log_event("UI", f"Selecting current list: {self.current_list}")
        try:
            if self.current_list.startswith("project_"):
                child = self.projects_list_group.get_first_child()
                while child:
                    if hasattr(child, 'get_name') and child.get_name() == self.current_list:
                        self.projects_list_group.select_row(child)
                        debug.log_event("UI", f"Selected project row: {self.current_list}")
                        break
                    child = child.get_next_sibling()
            else:
                child = self.main_list_group.get_first_child()
                while child:
                    if hasattr(child, 'get_name') and child.get_name() == self.current_list:
                        self.main_list_group.select_row(child)
                        debug.log_event("UI", f"Selected main list row: {self.current_list}")
                        break
                    child = child.get_next_sibling()
        except Exception as e:
            debug.log_event("UI", f"Error selecting current list: {e}")
        return False

    @debug_method("on_list_selected")
    def on_list_selected(self, listbox, row):
        if row is None: 
            debug.log_event("LIST_SELECT", "Row is None, ignoring")
            return
        
        list_id = row.get_name()
        debug.log_event("LIST_SELECT", f"Selected list: {list_id}, current: {self.current_list}")
        
        if not list_id:
            debug.log_event("LIST_SELECT", "No list_id found in row")
            return
            
        if list_id == self.current_list:
            debug.log_event("LIST_SELECT", "Same list selected, ignoring")
            return
        
        # Limpiar estado antes del cambio
        debug.log_event("LIST_SELECT", "Cleaning UI state before list change")
        self._cleanup_ui_state()
            
        if listbox == self.main_list_group:
            self.projects_list_group.unselect_all()
            debug.log_event("LIST_SELECT", "Unselected projects list")
        else:
            self.main_list_group.unselect_all()
            debug.log_event("LIST_SELECT", "Unselected main list")
            
        old_list = self.current_list
        self.current_list = list_id
        debug.log_event("LIST_SELECT", f"Changed from {old_list} to {list_id}")
        
        self.refresh_task_list()
        self.update_header_title()
        
        # Cerrar panel de info si está abierto
        if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
            debug.log_event("LIST_SELECT", "Closing task info panel after list change")
            self.on_close_task_info(None)

    @debug_method("create_main_area")
    def create_main_area(self):
        """Crear área principal con el título de la aplicación centrado en la barra de título"""
        debug.log_event("UI", "Creating main area")
        
        self.content_page = Adw.NavigationPage()
        self.content_page.set_title(_("Todo List"))
        self.content_page.set_tag("content")
        
        content_toolbar = Adw.ToolbarView()
        content_header = Adw.HeaderBar()
        
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_model = Gio.Menu()
        
        # Sección de idioma
        language_menu = Gio.Menu()
        language_menu.append(_("Auto-detect"), "app.language::auto")
        language_menu.append(_("English"), "app.language::en")
        language_menu.append(_("Spanish"), "app.language::es")
        menu_model.append_submenu(_("Language"), language_menu)
        
        # Sección principal
        main_section = Gio.Menu()
        main_section.append(_("Preferences"), "app.preferences")
        main_section.append(_("About"), "app.about")
        menu_model.append_section(None, main_section)
        
        menu_button.set_menu_model(menu_model)
        content_header.pack_end(menu_button)
        
        content_toolbar.add_top_bar(content_header)
        
        # Contenido principal
        self.main_area = Adw.Clamp()
        self.main_area.set_maximum_size(840)
        self.main_area.set_margin_start(24)
        self.main_area.set_margin_end(24)
        
        vertical_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_area.set_child(vertical_wrapper)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_margin_top(12)
        content_box.set_vexpand(False)
        content_box.set_valign(Gtk.Align.START)
        vertical_wrapper.append(content_box)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.list_title_label = Gtk.Label()
        self.list_title_label.set_halign(Gtk.Align.START)
        self.list_title_label.add_css_class("title-1")
        self.list_title_label.set_hexpand(True)
        title_box.append(self.list_title_label)

        # Botón editar
        self.edit_button = Gtk.Button(icon_name="text-editor-symbolic")
        self.edit_button.add_css_class("flat")
        self.edit_button.connect("clicked", self.on_edit_project)
        self.edit_button.set_visible(False)
        title_box.append(self.edit_button)

        # Botón eliminar
        self.delete_button = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_button.add_css_class("flat")
        self.delete_button.connect("clicked", self.on_delete_project)
        self.delete_button.set_visible(False)
        title_box.append(self.delete_button)

        # Botón borrar archivadas
        self.clear_archived_button = Gtk.Button(icon_name="list-remove-all-symbolic")
        self.clear_archived_button.add_css_class("flat")
        self.clear_archived_button.set_tooltip_text(_("Clear all archived tasks"))
        self.clear_archived_button.connect("clicked", self.on_clear_archived_tasks)
        self.clear_archived_button.set_visible(False)
        title_box.append(self.clear_archived_button)

        self.sort_button = Gtk.Button()
        self.sort_button.add_css_class("flat")
        self.sort_button.connect("clicked", self.on_sort_toggle)
        self.update_sort_button()
        title_box.append(self.sort_button)
        
        content_box.append(title_box)

        self.task_list_scrolled = Gtk.ScrolledWindow()
        self.task_list_scrolled.set_vexpand(True)
        self.task_list_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.task_list_scrolled.set_propagate_natural_height(True)

        self.task_list = Gtk.ListBox()
        self.task_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.task_list.connect("row-activated", self.on_task_row_activated)
        self.task_list.add_css_class("boxed-list")
        self.task_list_scrolled.set_child(self.task_list)
        content_box.append(self.task_list_scrolled)

        self.new_task_entry = Gtk.Entry(placeholder_text=_("New task..."))
        self.new_task_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "list-add-symbolic")
        self.new_task_entry.add_css_class("new-task-entry")
        self.new_task_entry.connect("activate", self.on_new_task_entry_activate)
        content_box.append(self.new_task_entry)

        content_toolbar.set_content(self.main_area)
        self.content_page.set_child(content_toolbar)

        self.refresh_task_list()
        debug.log_event("UI", "Main area created successfully")

    def update_sort_button(self):
        if self.sort_ascending:
            self.sort_button.set_icon_name("view-sort-ascending-symbolic")
            self.sort_button.set_tooltip_text(_("Sort by date: oldest first"))
        else:
            self.sort_button.set_icon_name("view-sort-descending-symbolic")
            self.sort_button.set_tooltip_text(_("Sort by date: newest first"))

    @debug_method("on_sort_toggle")
    def on_sort_toggle(self, button):
        debug.log_event("SORT", f"Toggling sort from {self.sort_ascending}")
        self.sort_ascending = not self.sort_ascending
        self.update_sort_button()
        self.refresh_task_list()

    @debug_method("refresh_task_list")
    def refresh_task_list(self):
        debug.log_event("REFRESH_TASKS", f"=== REFRESH STARTED ===")
        debug.log_event("REFRESH_TASKS", f"Current list: {self.current_list}")
        debug.log_event("REFRESH_TASKS", f"Current task info: {self.current_task_info.get('title') if self.current_task_info else 'None'}")
        
        # Prevenir refrescos concurrentes
        current_time = time.time()
        if self._refresh_in_progress or (current_time - self._last_refresh_time) < 0.1:
            debug.log_event("REFRESH_TASKS", "Refresh in progress or too recent, skipping")
            return
        
        self._refresh_in_progress = True
        self._last_refresh_time = current_time
        
        try:
            # Verificar integridad de datos ANTES de empezar
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            debug.log_event("REFRESH_TASKS", f"Total tasks in manager: {len(all_tasks)}")
            
            # Verificar que todas las tareas tienen IDs válidos
            invalid_tasks = [t for t in all_tasks if t.get('id') is None]
            if invalid_tasks:
                debug.log_event("REFRESH_TASKS", f"WARNING: Found {len(invalid_tasks)} tasks without IDs")
            
            # Verificar duplicados de ID
            task_ids = [t.get('id') for t in all_tasks if t.get('id') is not None]
            if len(task_ids) != len(set(task_ids)):
                debug.log_event("REFRESH_TASKS", f"WARNING: Duplicate task IDs detected")
            
            # Limpiar lista con conteo
            row_count = 0
            while child := self.task_list.get_first_child():
                row_count += 1
                # Verificar si es una fila de tarea válida antes de eliminar
                if hasattr(child, 'get_name'):
                    child_name = child.get_name()
                    debug.log_event("REFRESH_TASKS", f"Removing row: {child_name}")
                self.task_list.remove(child)
            
            debug.log_event("REFRESH_TASKS", f"Removed {row_count} existing rows")

            # Actualizar visibilidad de botones
            is_project = self.current_list.startswith("project_")
            project_id = self.current_list.replace("project_", "") if is_project else ""
            is_inbox = project_id == "inbox"
            is_archived = self.current_list == "archived"
            
            self.edit_button.set_visible(is_project and not is_inbox)
            self.delete_button.set_visible(is_project and not is_inbox)
            self.clear_archived_button.set_visible(is_archived)

            debug.log_event("REFRESH_TASKS", f"Button visibility - edit: {is_project and not is_inbox}, delete: {is_project and not is_inbox}, clear: {is_archived}")

            # Actualizar título y color
            if self.current_list.startswith("project_"):
                project_id = self.current_list.replace("project_", "")
                project = self.task_manager.get_project_by_id(project_id)
                if project:
                    list_name = project["name"]
                    project_color = project["color"]
                    self.list_title_label.set_text(list_name)
                    
                    # Limpiar todas las clases de color
                    for color in ["purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime", "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver", "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"]:
                        self.list_title_label.remove_css_class(f"text-color-{color}")
                    self.list_title_label.remove_css_class("overdue-title")
                    
                    if project_id == "inbox":
                        self.list_title_label.remove_css_class("text-color-purple")
                        self.list_title_label.add_css_class("text-color-black")
                    elif project_color:
                        self.list_title_label.add_css_class(f"text-color-{project_color}")
                    
                    debug.log_event("REFRESH_TASKS", f"Set project title: {list_name} with color: {project_color}")
                else:
                    self.list_title_label.set_text(_("Project not found"))
                    debug.log_event("REFRESH_TASKS", f"Project {project_id} not found")
            else:
                list_name = self.task_manager.lists.get(self.current_list, self.current_list)
                self.list_title_label.set_text(list_name)
                
                # Limpiar colores
                for color in ["purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime", "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver", "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"]:
                    self.list_title_label.remove_css_class(f"text-color-{color}")
                
                if self.current_list == "overdue":
                    self.list_title_label.add_css_class("overdue-title")
                else:
                    self.list_title_label.remove_css_class("overdue-title")
                
                debug.log_event("REFRESH_TASKS", f"Set list title: {list_name}")

            # Obtener y mostrar tareas
            debug.log_event("REFRESH_TASKS", f"Getting tasks for list: {self.current_list}")
            tasks = self.task_manager.get_tasks(self.current_list)
            debug.log_event("REFRESH_TASKS", f"Retrieved {len(tasks)} tasks")
            
            # Verificar las tareas obtenidas
            for i, task in enumerate(tasks):
                task_id = task.get('id', 'NO_ID')
                task_title = task.get('title', 'NO_TITLE')
                task_date = task.get('effective_date', 'NO_DATE')
                debug.log_event("REFRESH_TASKS", f"Task {i}: ID={task_id}, Title='{task_title}', Date='{task_date[:10] if task_date != 'NO_DATE' else task_date}'")
            
            sorted_tasks = self.sort_tasks(tasks)
            debug.log_event("REFRESH_TASKS", f"Tasks sorted, count: {len(sorted_tasks)}")
            
            if len(sorted_tasks) > 0:
                self.task_list_scrolled.set_visible(True)
                if self.should_group_by_date():
                    debug.log_event("REFRESH_TASKS", "Using grouped task rows")
                    self.create_grouped_task_rows(sorted_tasks)
                else:
                    debug.log_event("REFRESH_TASKS", "Using standard task rows")
                    self.create_standard_task_rows(sorted_tasks)
            else:
                debug.log_event("REFRESH_TASKS", "No tasks to show")
                self.task_list_scrolled.set_visible(False)
            
            # Verificar que se crearon las filas correctamente
            final_row_count = 0
            child = self.task_list.get_first_child()
            while child:
                final_row_count += 1
                if hasattr(child, 'get_name'):
                    child_name = child.get_name() or "HEADER"
                    debug.log_event("REFRESH_TASKS", f"Final row {final_row_count}: {child_name}")
                child = child.get_next_sibling()
            
            debug.log_event("REFRESH_TASKS", f"Created {final_row_count} new rows")
            self.update_header_title()
            debug.log_event("REFRESH_TASKS", "=== REFRESH COMPLETED SUCCESSFULLY ===")
            
        except Exception as e:
            debug.log_event("REFRESH_TASKS", f"=== REFRESH ERROR: {e} ===", stack_info=True)
            # Intentar recuperación básica
            try:
                self.task_list_scrolled.set_visible(False)
                debug.log_event("REFRESH_TASKS", "Hidden task list after error")
            except:
                pass
        finally:
            self._refresh_in_progress = False

    def should_group_by_date(self):
        groupable_lists = ["today", "all", "overdue", "archived"]
        should_group = self.current_list in groupable_lists
        debug.log_event("REFRESH_TASKS", f"Should group by date: {should_group} (list: {self.current_list})")
        return should_group

    def create_grouped_task_rows(self, tasks):
        if not tasks:
            debug.log_event("REFRESH_TASKS", "No tasks for grouped rows")
            return
        
        grouped_tasks = self.group_tasks_by_date(tasks)
        debug.log_event("REFRESH_TASKS", f"Grouped into {len(grouped_tasks)} date groups")
        
        for date_key, date_tasks in grouped_tasks.items():
            # Omitir la cabecera "Hoy" cuando estamos en la vista "Hoy"
            if not (self.current_list == "today" and date_key == "hoy"):
                date_header = self.create_date_header(date_key)
                self.task_list.append(date_header)
                debug.log_event("REFRESH_TASKS", f"Added date header: {date_key}")
            
            for task in date_tasks:
                row = self.create_task_row(task)
                self.task_list.append(row)
                debug.log_event("REFRESH_TASKS", f"Added task row: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})")

    def create_standard_task_rows(self, tasks):
        debug.log_event("REFRESH_TASKS", f"Creating {len(tasks)} standard task rows")
        for task in tasks:
            row = self.create_task_row(task)
            self.task_list.append(row)
            debug.log_event("REFRESH_TASKS", f"Added task row: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})")

    def group_tasks_by_date(self, tasks):
        grouped = OrderedDict()
        today = datetime.date.today()
        
        for task in tasks:
            effective_date_str = task.get("effective_date")
            if not effective_date_str:
                date_key = "sin_fecha"
            else:
                try:
                    effective_date = datetime.datetime.fromisoformat(effective_date_str).date()
                    days_diff = (today - effective_date).days
                    
                    if days_diff == 0:
                        date_key = "hoy"
                    elif days_diff > 0:
                        date_key = f"hace_{days_diff}_dias"
                    else:
                        date_key = f"en_{abs(days_diff)}_dias"
                except (ValueError, TypeError):
                    date_key = "sin_fecha"

            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(task)
        
        return self.sort_date_groups(grouped)

    def sort_date_groups(self, grouped):
        sorted_groups = OrderedDict()
        
        keys = list(grouped.keys())
        
        past_days = [k for k in keys if k.startswith("hace_")]
        future_days = [k for k in keys if k.startswith("en_")]
        today_key = "hoy" if "hoy" in keys else None
        no_date_key = "sin_fecha" if "sin_fecha" in keys else None
        
        # past_days: 1 (Yesterday) ... 10 (Long Ago) -> Descending Date
        past_days.sort(key=lambda x: int(x.split("_")[1]))
        
        # future_days: 1 (Tomorrow) ... 10 (Far Future) -> Ascending Date
        future_days.sort(key=lambda x: int(x.split("_")[1]))
        
        group_order = []
        
        if self.sort_ascending:
            # Oldest First: Long Ago -> Yesterday -> Today -> Tomorrow -> Far Future
            group_order.extend(reversed(past_days))
            if today_key:
                group_order.append(today_key)
            group_order.extend(future_days)
        else:
            # Newest First: Far Future -> Tomorrow -> Today -> Yesterday -> Long Ago
            group_order.extend(reversed(future_days))
            if today_key:
                group_order.append(today_key)
            group_order.extend(past_days)
            
        # Append No Date at the end
        if no_date_key:
            group_order.append(no_date_key)
            
        for key in group_order:
            sorted_groups[key] = grouped[key]
        
        return sorted_groups

    def create_date_header(self, date_key):
        if date_key == "hoy":
            header_text = _("Today")
            header_class = "date-header-today"
        elif date_key == "sin_fecha":
            header_text = _("No date")
            header_class = "date-header-no-date"
        elif date_key.startswith("hace_"):
            days = int(date_key.split("_")[1])
            header_text = f"{days} {_('day' if days == 1 else 'days')} {_('ago')}"
            header_class = "date-header-past"
        elif date_key.startswith("en_"):
            days = int(date_key.split("_")[1])
            header_text = f"{_('In')} {days} {_('day' if days == 1 else 'days')}"
            header_class = "date-header-future"
        else:
            header_text = date_key
            header_class = "date-header-default"
        
        header_row = Gtk.ListBoxRow()
        header_row.set_selectable(False)
        header_row.set_activatable(False)
        header_row.add_css_class("date-header-row")
        
        header_label = Gtk.Label(label=header_text)
        header_label.set_halign(Gtk.Align.START)
        header_label.add_css_class("date-header")
        header_label.add_css_class(header_class)
        header_label.set_margin_top(12)
        header_label.set_margin_bottom(6)
        header_label.set_margin_start(12)
        header_label.set_margin_end(12)
        
        header_row.set_child(header_label)
        
        return header_row

    def sort_tasks(self, tasks):
        if not tasks: 
            return []
        
        def get_sort_key(task):
            sort_order = task.get("sort_order", 0)
            effective_date = task.get("effective_date")
            if not effective_date:
                # If sorting ascending (oldest first), we want no date LAST -> 9999
                # If sorting descending (newest first), we want no date LAST -> 0000 (because reverse=True)
                date_key = "9999-12-31T23:59:59" if self.sort_ascending else "0000-01-01T00:00:00"
            else:
                date_key = effective_date
            
            # Prioritize date sorting over manual sort order
            return (date_key, sort_order)
        
        sorted_tasks = sorted(tasks, key=get_sort_key, reverse=not self.sort_ascending)
        
        return sorted_tasks

    @debug_method("on_clear_archived_tasks")
    def on_clear_archived_tasks(self, button):
        """Mostrar diálogo de confirmación para borrar todas las tareas archivadas"""
        archived_tasks = self.task_manager.get_tasks("archived")
        if not archived_tasks:
            debug.log_event("CLEAR_ARCHIVED", "No archived tasks to clear")
            return
        
        debug.log_event("CLEAR_ARCHIVED", f"Showing confirmation dialog for {len(archived_tasks)} tasks")
        
        dialog = Adw.MessageDialog.new(
            self,
            _("Clear Archived Tasks"),
            _("Are you sure you want to permanently delete all {} archived tasks?").format(len(archived_tasks))
        )
        
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete All"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self.on_clear_archived_confirmation)
        dialog.present()

    def on_clear_archived_confirmation(self, dialog, response):
        """Manejar la respuesta del diálogo de confirmación"""
        debug.log_event("CLEAR_ARCHIVED", f"Dialog response: {response}")
        if response == "delete":
            # Eliminar todas las tareas archivadas
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            original_count = len(all_tasks)
            self.task_manager.tasks["all_tasks"] = [
                task for task in all_tasks if not task.get("completed", False)
            ]
            
            deleted_count = original_count - len(self.task_manager.tasks["all_tasks"])
            debug.log_event("CLEAR_ARCHIVED", f"Deleted {deleted_count} archived tasks")
            
            self.task_manager.save_tasks()
            self.refresh_task_list()
            self.refresh_sidebar()
            
            # Cerrar panel de información si está abierto
            if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
                self.on_close_task_info(None)
        
        dialog.close()

    @debug_method("create_task_row")
    def create_task_row(self, task):
        debug.log_event("CREATE_ROW", f"Creating row for task: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})")
        
        row = Adw.ActionRow()
        task_id = task.get("id")
        if task_id is not None:
            row.set_name(str(task_id))
        else:
            debug.log_event("CREATE_ROW", f"WARNING: Task has no ID: {task}")
        
        row.set_title(task["title"])
        row.set_activatable(True)

        if task["completed"]:
            row.add_css_class("dim-label")
        
        # Handle de arrastrar
        handle = Gtk.Image.new_from_icon_name("drag-surface-symbolic")
        handle.add_css_class("drag-handle-icon")
        handle.set_pixel_size(24)
        
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        
        def prepare_drag(source, x, y):
            content = Gdk.ContentProvider.new_for_value(task["id"])
            return content
        
        def drag_begin(source, drag):
            paintable = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).lookup_icon(
                "drag-surface-symbolic", None, 24, 1, Gtk.TextDirection.NONE, 0)
            drag_source.set_icon(paintable, 0, 0)
        
        drag_source.connect("prepare", prepare_drag)
        drag_source.connect("drag-begin", drag_begin)
        handle.add_controller(drag_source)
        
        row.add_prefix(handle)
        
        # Checkbox
        check = Gtk.CheckButton(active=task["completed"])
        check.add_css_class("task-checkbox")
        check.connect("toggled", lambda w, t=task: self.on_task_toggle(t))
        row.add_prefix(check)

        # Proyecto
        if task.get("project"):
            project_label = Gtk.Label(label=task["project"])
            project_label.add_css_class("dim-label")
            project_label.add_css_class("caption")
            row.add_suffix(project_label)
        
        # Botón de favorito
        is_favorite = task.get("favorite", False)
        star_icon = "folder-favorites-symbolic" if is_favorite else "favorite-symbolic"
        star_image = Gtk.Image.new_from_icon_name(star_icon)
        star_image.set_pixel_size(24)
        star_button = Gtk.Button()
        star_button.set_child(star_image)
        star_button.add_css_class("flat")
        if is_favorite:
            star_button.add_css_class("favorite-active")
        
        def toggle_favorite_handler(button):
            debug.log_event("FAVORITE_CLICK", f"Favorite clicked for task {task.get('id')}: {task.get('title')}")
            self.on_toggle_favorite(task)
        
        star_button.connect("clicked", toggle_favorite_handler)
        row.add_suffix(star_button)

        # Drop target para reordenar
        drop_target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        
        def on_drop(target, value, x, y):
            return self.on_task_reorder(value, task["id"])
        
        drop_target.connect("drop", on_drop)
        row.add_controller(drop_target)

        debug.log_event("CREATE_ROW", f"Row created successfully for task {task.get('id')}")
        return row

    @debug_method("refresh_sidebar")
    def refresh_sidebar(self):
        try:
            debug.log_event("SIDEBAR", "Starting sidebar refresh")
            
            # Prevenir múltiples refrescos concurrentes
            if hasattr(self, '_refreshing_sidebar') and self._refreshing_sidebar:
                debug.log_event("SIDEBAR", "Sidebar refresh already in progress, skipping")
                return
                
            self._refreshing_sidebar = True
            self.recreate_sidebar()
            debug.log_event("SIDEBAR", "Sidebar refresh completed")
            
        except Exception as e:
            debug.log_event("SIDEBAR", f"Error in refresh_sidebar: {e}", stack_info=True)
        finally:
            self._refreshing_sidebar = False

    @debug_method("recreate_sidebar")
    def recreate_sidebar(self):
        try:
            debug.log_event("SIDEBAR", "Recreating sidebar content")
            
            # Verificar que los widgets existen antes de manipularlos
            if hasattr(self, 'main_list_group') and self.main_list_group:
                debug.log_event("SIDEBAR", "Clearing main list group")
                row_count = 0
                while child := self.main_list_group.get_first_child():
                    row_count += 1
                    self.main_list_group.remove(child)
                debug.log_event("SIDEBAR", f"Removed {row_count} main list rows")
                
                for list_id, list_name in self.task_manager.lists.items():
                    row = self.create_sidebar_row(list_id, list_name, is_project=False)
                    self.main_list_group.append(row)
                    
                debug.log_event("SIDEBAR", f"Added {len(self.task_manager.lists)} main list rows")
            
            if hasattr(self, 'projects_list_group') and self.projects_list_group:
                debug.log_event("SIDEBAR", "Clearing projects list group")
                row_count = 0
                while child := self.projects_list_group.get_first_child():
                    row_count += 1
                    self.projects_list_group.remove(child)
                debug.log_event("SIDEBAR", f"Removed {row_count} project rows")
                
                for project in self.task_manager.projects:
                    project_id = f"project_{project.get('id', project['name'])}"
                    row = self.create_sidebar_row(project_id, project['name'], 
                                                is_project=True, color=project['color'])
                    self.projects_list_group.append(row)
                    
                debug.log_event("SIDEBAR", f"Added {len(self.task_manager.projects)} project rows")
            
            # Usar GLib.idle_add para la selección
            GLib.idle_add(self.select_current_list)
            
        except Exception as e:
            debug.log_event("SIDEBAR", f"Error in recreate_sidebar: {e}", stack_info=True)

    @debug_method("create_task_info_panel")
    def create_task_info_panel(self):
        """Crear panel de información de tareas"""
        debug.log_event("UI", "Creating task info panel")
        
        self.task_info_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.task_info_panel.add_css_class("task-info-panel")
        self.task_info_panel.set_visible(False)
        
        self.task_info_panel.set_hexpand(False)
        self.task_info_panel.set_vexpand(True)
        self.task_info_panel.set_size_request(400, -1)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(6)
        spacer = Gtk.Box(hexpand=True)
        header_box.append(spacer)
        close_button = Gtk.Button(icon_name="window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.add_css_class("circular")
        close_button.connect("clicked", self.on_close_task_info)
        header_box.append(close_button)
        self.task_info_panel.append(header_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.task_info_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.task_info_content.set_margin_start(12)
        self.task_info_content.set_margin_end(12)
        self.task_info_content.set_margin_bottom(12)
        scrolled.set_child(self.task_info_content)
        self.task_info_panel.append(scrolled)

        # Crear NavigationPage para pantallas pequeñas
        self.task_info_page = Adw.NavigationPage()
        self.task_info_page.set_title(_("Task Details"))  # TÍTULO EXPLÍCITO
        self.task_info_page.set_tag("task-info")
        
        debug.log_event("UI", "Task info panel created successfully")

    @debug_method("on_task_row_activated")
    def on_task_row_activated(self, listbox, row):
        if row is None:
            debug.log_event("TASK_CLICK", "Row is None in on_task_row_activated")
            return
            
        task_id_str = row.get_name()
        debug.log_event("TASK_CLICK", f"Task row activated - row name: '{task_id_str}'")
        
        if not task_id_str:
            debug.log_event("TASK_CLICK", "No task ID found in row name")
            return
        
        # Verificar si es una fila de cabecera de fecha
        if task_id_str == "" or not task_id_str.isdigit():
            debug.log_event("TASK_CLICK", f"Ignoring non-task row: '{task_id_str}'")
            return
            
        try:
            task_id = int(task_id_str)
            debug.log_event("TASK_CLICK", f"Looking for task with ID: {task_id}")
        except ValueError:
            debug.log_event("TASK_CLICK", f"Invalid task ID format: '{task_id_str}'")
            return

        found_task = None
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        debug.log_event("TASK_CLICK", f"Total tasks available: {len(all_tasks)}")
        
        for task in all_tasks:
            if task.get("id") == task_id:
                found_task = task
                break
        
        if found_task:
            debug.log_event("TASK_CLICK", f"Found task: '{found_task.get('title', 'unknown')}' (ID: {found_task.get('id', 'unknown')})")
            self.on_task_row_clicked(found_task)
        else:
            debug.log_event("TASK_CLICK", f"ERROR: Task with ID {task_id} not found in task list")
            debug.log_event("TASK_CLICK", f"Available task IDs: {[t.get('id') for t in all_tasks]}")

    @debug_method("on_task_row_clicked")
    def on_task_row_clicked(self, task):
        debug.log_event("TASK_CLICK", f"Task row clicked: '{task.get('title', 'unknown')}' (ID: {task.get('id', 'unknown')})")
        
        # Verificar que la tarea sigue existiendo
        task_id = task.get('id')
        if task_id is None:
            debug.log_event("TASK_CLICK", "ERROR: Task has no ID")
            return
            
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        task_exists = any(t.get('id') == task_id for t in all_tasks)
        
        if not task_exists:
            debug.log_event("TASK_CLICK", f"ERROR: Task {task_id} no longer exists in task manager")
            return
        
        width = self.get_width()
        debug.log_event("TASK_CLICK", f"Window width: {width}px")
        
        if width < 600:
            debug.log_event("TASK_CLICK", "Using dialog mode (small screen)")
            self.show_task_info_dialog(task)
        else:
            debug.log_event("TASK_CLICK", "Using panel mode (large screen)")
            self.show_task_info_panel(task)

    def show_task_info_dialog(self, task):
        # Para pantallas pequeñas, crear un diálogo simple
        debug.log_event("TASK_INFO", "show_task_info_dialog not implemented yet")
        pass

    @debug_method("show_task_info_panel")
    def show_task_info_panel(self, task):
        try:
            debug.log_event("TASK_INFO", f"Showing task info panel for task {task.get('id')}: '{task.get('title', 'unknown')}'")
            
            # IMPORTANTE: NO cerrar panel anterior aquí, solo limpiar el contenido
            # El panel se reutiliza en lugar de recrearse
            
            self.current_task_info = task
            debug.log_event("TASK_INFO", f"Set current_task_info to: {task.get('title', 'unknown')}")
            
            # Limpiar contenido anterior SOLO si el panel ya está visible
            if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
                debug.log_event("TASK_INFO", "Panel already visible, clearing content only")
                child_count = 0
                child = self.task_info_content.get_first_child()
                while child:
                    child_count += 1
                    self.task_info_content.remove(child)
                    child = self.task_info_content.get_first_child()
                debug.log_event("TASK_INFO", f"Removed {child_count} previous child widgets")
            else:
                debug.log_event("TASK_INFO", "Panel not visible, will create fresh")

            # Crear contenido del panel
            title_group = Adw.PreferencesGroup(title=_("Task"))
            self.task_title_entry = Adw.EntryRow(title=_("Title"))
            self.task_title_entry.set_text(task["title"])
            self.task_title_entry.connect("notify::text", self.on_task_title_changed)
            title_group.add(self.task_title_entry)
            self.task_info_content.append(title_group)

            date_group = Adw.PreferencesGroup(title=_("Date"))
            
            self.task_date_row = Adw.ActionRow(title=_("Effective date"))
            
            current_date_str = _("No date")
            if task.get("effective_date"):
                try:
                    date_obj = datetime.datetime.fromisoformat(task["effective_date"])
                    current_date_str = date_obj.strftime("%d/%m/%Y")
                except:
                    pass
            
            self.date_label = Gtk.Label(label=current_date_str)
            self.date_label.add_css_class("dim-label")
            self.task_date_row.add_suffix(self.date_label)
            
            calendar_button = Gtk.Button()
            calendar_button.set_icon_name("x-office-calendar-symbolic")
            calendar_button.add_css_class("flat")
            calendar_button.connect("clicked", self.on_open_calendar)
            self.task_date_row.add_suffix(calendar_button)
            
            self.task_date_row.set_activatable(True)
            self.task_date_row.connect("activated", self.on_open_calendar)
            
            date_group.add(self.task_date_row)
            self.task_info_content.append(date_group)

            notes_group = Adw.PreferencesGroup(title=_("Description"))
            notes_scrolled = Gtk.ScrolledWindow(height_request=100, vexpand=False)
            notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            notes_scrolled.add_css_class("description-card")
            
            self.task_notes_buffer = Gtk.TextBuffer(text=task.get("notes", ""))
            self.task_notes_buffer.connect("changed", self.on_task_notes_changed)
            notes_view = Gtk.TextView(buffer=self.task_notes_buffer, wrap_mode=Gtk.WrapMode.WORD, 
                                     margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
            notes_scrolled.set_child(notes_view)
            
            self.task_info_content.append(notes_group)
            self.task_info_content.append(notes_scrolled)
            
            project_group = Adw.PreferencesGroup(title=_("Organization"))
            project_row = Adw.ComboRow(title=_("Project"))
            
            # Obtener nombres de proyectos, poniendo Inbox primero
            inbox_project = self.task_manager.get_inbox_project()
            inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
            project_names = [inbox_name] + [p["name"] for p in self.task_manager.projects if p.get("id") != "inbox"]
            
            model = Gtk.StringList.new(project_names)
            project_row.set_model(model)
            
            current_project = task.get("project", inbox_name)
            try:
                selected_idx = project_names.index(current_project)
                project_row.set_selected(selected_idx)
            except ValueError:
                project_row.set_selected(0)
            
            project_row.connect("notify::selected", self.on_project_changed_enhanced)
            project_group.add(project_row)
            self.task_info_content.append(project_group)
            
            actions_group = Adw.PreferencesGroup(title=_("Actions"))
            completed_row = Adw.SwitchRow(title=_("Completed"), active=task["completed"])
            completed_row.connect("notify::active", self.on_task_completed_toggled)
            actions_group.add(completed_row)
            delete_row = Adw.ActionRow(title=_("Delete task"))
            delete_button = Gtk.Button(label=_("Delete"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            delete_button.add_css_class("destructive-action")
            delete_button.connect("clicked", lambda btn: self.on_delete_current_task())
            delete_row.add_suffix(delete_button)
            delete_row.set_activatable(True)
            delete_row.connect('activated', lambda w: self.on_delete_current_task())
            actions_group.add(delete_row)
            self.task_info_content.append(actions_group)

            # Mostrar el panel - LÓGICA MEJORADA
            width = self.get_width()
            if width < 600:
                debug.log_event("TASK_INFO", "Using NavigationPage mode")
                if not hasattr(self, 'task_info_page'):
                    self.task_info_page = Adw.NavigationPage()
                    self.task_info_page.set_title(_("Task Details"))
                    self.task_info_page.set_tag("task-info")
                    self.task_info_page.set_child(self.task_info_panel)
                
                self.split_view.set_content(self.task_info_page)
            else:
                debug.log_event("TASK_INFO", "Using panel mode")
                
                # VERIFICAR si ya tenemos content_paned configurado
                if not hasattr(self, 'content_paned') or self.content_paned.get_parent() != self.content_page:
                    debug.log_event("TASK_INFO", "Creating/recreating content_paned structure")
                    
                    # Crear nuevo content_paned
                    self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
                    self.content_paned.set_wide_handle(True)
                    self.content_paned.set_hexpand(True)
                    
                    self.content_paned.set_shrink_start_child(True)
                    self.content_paned.set_shrink_end_child(False)
                    self.content_paned.set_resize_start_child(True) 
                    self.content_paned.set_resize_end_child(False)
                    
                    # Obtener el contenido actual del content_page
                    current_content = self.content_page.get_child()
                    
                    # Si el contenido actual es un content_paned, obtener su contenido izquierdo
                    if isinstance(current_content, Gtk.Paned):
                        debug.log_event("TASK_INFO", "Extracting content from existing paned")
                        actual_content = current_content.get_start_child()
                        current_content.set_start_child(None)
                        current_content.set_end_child(None)
                    else:
                        actual_content = current_content
                    
                    # Configurar la nueva estructura
                    if actual_content:
                        self.content_page.set_child(None)
                        self.content_paned.set_start_child(actual_content)
                        self.content_page.set_child(self.content_paned)
                        debug.log_event("TASK_INFO", "Content_paned structure created")
                    else:
                        debug.log_event("TASK_INFO", "ERROR: No content found to move to paned")
                        return
                else:
                    debug.log_event("TASK_INFO", "Reusing existing content_paned structure")
                
                # Configurar el panel
                self.task_info_panel.set_size_request(400, -1)
                self.task_info_panel.set_hexpand(False)
                self.task_info_panel.set_visible(True)
                
                # Añadir el panel al lado derecho
                self.content_paned.set_end_child(self.task_info_panel)
                
                # Configurar posición
                window_width = self.get_width()
                target_position = window_width - 400
                self.content_paned.set_position(target_position)
                debug.log_event("TASK_INFO", f"Set paned position to: {target_position}")
            
            debug.log_event("TASK_INFO", "Task info panel shown successfully")
            
        except Exception as e:
            debug.log_event("TASK_INFO", f"ERROR in show_task_info_panel: {e}", stack_info=True)

    def _verify_task_integrity_after_date_change(self):
        """Verificar integridad de datos después de cambiar fechas"""
        debug.log_event("INTEGRITY", "=== TASK INTEGRITY CHECK ===")
        
        if not self.current_task_info:
            debug.log_event("INTEGRITY", "No current task info")
            return False
        
        task_id = self.current_task_info.get('id')
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        
        # Encontrar la tarea en la lista principal
        found_task = None
        for task in all_tasks:
            if task.get('id') == task_id:
                found_task = task
                break
        
        if not found_task:
            debug.log_event("INTEGRITY", f"ERROR: Task {task_id} not found in task manager!")
            return False
        
        # Verificar que las fechas coinciden
        current_date = self.current_task_info.get('effective_date')
        manager_date = found_task.get('effective_date')
        
        if current_date != manager_date:
            debug.log_event("INTEGRITY", f"ERROR: Date mismatch - current_task_info: {current_date}, manager: {manager_date}")
            return False
        
        debug.log_event("INTEGRITY", f"Task {task_id} integrity OK - date: {current_date}")
        return True                            

    @debug_method("on_open_calendar")
    def on_open_calendar(self, widget):
        debug.log_event("CALENDAR", "=== CALENDAR DIALOG OPENING ===")
        debug.log_event("CALENDAR", f"Current task info: {self.current_task_info.get('title') if self.current_task_info else 'None'}")
        
        dialog = Gtk.Dialog(title=_("Select date"), transient_for=self, modal=True)
        dialog.set_default_size(300, 400)
        
        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_start(24)
        content_area.set_margin_end(24)
        content_area.set_margin_top(24)
        content_area.set_margin_bottom(24)
        
        title_label = Gtk.Label(label=_("Task effective date"))
        title_label.add_css_class("title-4")
        content_area.append(title_label)
        
        calendar = Gtk.Calendar()
        calendar.set_show_heading(True)
        calendar.set_show_day_names(True)
        calendar.set_show_week_numbers(False)
        
        if self.current_task_info and self.current_task_info.get("effective_date"):
            try:
                date_obj = datetime.datetime.fromisoformat(self.current_task_info["effective_date"])
                calendar.select_day(date_obj.date())
                debug.log_event("CALENDAR", f"Pre-selected date: {date_obj.date()}")
            except Exception as e:
                debug.log_event("CALENDAR", f"Error pre-selecting date: {e}")
        
        content_area.append(calendar)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)
        
        clear_button = Gtk.Button(label=_("No date"))
        clear_button.connect("clicked", lambda b: self.on_date_cleared(dialog))
        button_box.append(clear_button)
        
        today_button = Gtk.Button(label=_("Today"))
        today_button.connect("clicked", lambda b: self.on_today_selected(calendar, dialog))
        button_box.append(today_button)
        
        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.connect("clicked", lambda b: dialog.close())
        button_box.append(cancel_button)
        
        accept_button = Gtk.Button(label=_("Accept"))
        accept_button.add_css_class("suggested-action")
        accept_button.connect("clicked", lambda b: self.on_date_selected(calendar, dialog))
        button_box.append(accept_button)
        
        content_area.append(button_box)
        
        dialog.present()
        debug.log_event("CALENDAR", "Calendar dialog presented")

    def on_date_selected(self, calendar, dialog):
        debug.log_event("CALENDAR", "=== DATE SELECTION STARTED ===")
        debug.log_event("CALENDAR", f"Current task info before change: {self.current_task_info}")
        
        if self.current_task_info:
            selected_date = calendar.get_date()
            date_obj = datetime.datetime(selected_date.get_year(), 
                                       selected_date.get_month(), 
                                       selected_date.get_day_of_month())
            
            old_date = self.current_task_info.get("effective_date", "None")
            new_date = date_obj.isoformat()
            
            debug.log_event("CALENDAR", f"Date changing from '{old_date}' to '{new_date}'")
            debug.log_event("CALENDAR", f"Task ID: {self.current_task_info.get('id')}")
            debug.log_event("CALENDAR", f"Task title: {self.current_task_info.get('title')}")
            
            # Verificar que la tarea existe en el task manager antes de cambiar
            task_id = self.current_task_info.get('id')
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            task_exists = any(t.get('id') == task_id for t in all_tasks)
            
            if not task_exists:
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found in task manager!")
                debug.log_event("CALENDAR", f"Available task IDs: {[t.get('id') for t in all_tasks]}")
                dialog.close()
                return
            
            # Cambiar la fecha
            self.current_task_info["effective_date"] = new_date
            debug.log_event("CALENDAR", f"Task effective_date updated to: {new_date}")
            
            # Verificar que el cambio se aplicó
            actual_date = self.current_task_info.get("effective_date")
            debug.log_event("CALENDAR", f"Verification - actual date in task: {actual_date}")
            
            # Guardar tareas
            debug.log_event("CALENDAR", "Saving tasks to file...")
            try:
                self.task_manager.save_tasks()
                debug.log_event("CALENDAR", "Tasks saved successfully")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR saving tasks: {e}", stack_info=True)
                dialog.close()
                return
            
            # Actualizar la etiqueta de fecha
            try:
                formatted_date = date_obj.strftime("%d/%m/%Y")
                self.date_label.set_text(formatted_date)
                debug.log_event("CALENDAR", f"Date label updated to: {formatted_date}")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR updating date label: {e}")
            
            # Verificar estado antes del refresh
            debug.log_event("CALENDAR", "=== PRE-REFRESH STATE CHECK ===")
            debug.log_event("CALENDAR", f"Current list: {self.current_list}")
            debug.log_event("CALENDAR", f"Total tasks in manager: {len(self.task_manager.tasks.get('all_tasks', []))}")
            debug.log_event("CALENDAR", f"Task info panel visible: {self.task_info_panel.get_visible()}")
            
            # Refresh con control de errores
            debug.log_event("CALENDAR", "Starting refresh after date change...")
            try:
                self.refresh_task_list()
                debug.log_event("CALENDAR", "Task list refresh completed")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR in refresh_task_list: {e}", stack_info=True)
            
            try:
                self.refresh_sidebar()
                debug.log_event("CALENDAR", "Sidebar refresh completed")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR in refresh_sidebar: {e}", stack_info=True)
            
            # Verificar estado después del refresh
            debug.log_event("CALENDAR", "=== POST-REFRESH STATE CHECK ===")
            debug.log_event("CALENDAR", f"Current task info still valid: {self.current_task_info is not None}")
            if self.current_task_info:
                debug.log_event("CALENDAR", f"Task info date after refresh: {self.current_task_info.get('effective_date')}")
            
            # Verificar integridad después del cambio
            if not self._verify_task_integrity_after_date_change():
                debug.log_event("CALENDAR", "INTEGRITY CHECK FAILED after date change")
                self._recover_from_ui_error()
            
            debug.log_event("CALENDAR", "=== DATE SELECTION COMPLETED ===")
        else:
            debug.log_event("CALENDAR", "ERROR: No current_task_info available")
        
        dialog.close()

    def on_today_selected(self, calendar, dialog):
        debug.log_event("CALENDAR", "Today button selected")
        today = datetime.date.today()
        calendar.select_day(today)
        self.on_date_selected(calendar, dialog)

    def on_date_cleared(self, dialog):
        debug.log_event("CALENDAR", "=== DATE CLEAR STARTED ===")
        debug.log_event("CALENDAR", f"Current task info: {self.current_task_info}")
        
        if self.current_task_info:
            today = datetime.datetime.now()
            old_date = self.current_task_info.get("effective_date", "None")
            new_date = None
            
            debug.log_event("CALENDAR", f"Clearing date from '{old_date}' to '{new_date}'")
            
            # Verificar existencia de tarea
            task_id = self.current_task_info.get('id')
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            task_exists = any(t.get('id') == task_id for t in all_tasks)
            
            if not task_exists:
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found!")
                debug.log_event("CALENDAR", f"Available task IDs: {[t.get('id') for t in all_tasks]}")
                dialog.close()
                return
            
            self.current_task_info["effective_date"] = new_date
            debug.log_event("CALENDAR", f"Task date cleared to: {new_date}")
            
            try:
                self.task_manager.save_tasks()
                debug.log_event("CALENDAR", "Tasks saved after date clear")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR saving after date clear: {e}", stack_info=True)
                dialog.close()
                return
            
            try:
                self.date_label.set_text(_("No date"))
                debug.log_event("CALENDAR", f"Date label updated to No Date")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR updating date label: {e}")
            
            # Refresh controlado
            debug.log_event("CALENDAR", "Starting refresh after date clear...")
            try:
                self.refresh_task_list()
                self.refresh_sidebar()
                debug.log_event("CALENDAR", "Refresh completed after date clear")
            except Exception as e:
                debug.log_event("CALENDAR", f"ERROR in refresh after date clear: {e}", stack_info=True)
            
            # Verificar integridad después del cambio
            if not self._verify_task_integrity_after_date_change():
                debug.log_event("CALENDAR", "INTEGRITY CHECK FAILED after date clear")
                self._recover_from_ui_error()
            
            debug.log_event("CALENDAR", "=== DATE CLEAR COMPLETED ===")
        
        dialog.close()

    def on_project_changed_enhanced(self, row, param):
        debug.log_event("PROJECT_CHANGE", "Project changed in task info")
        if self.current_task_info:
            selected_idx = row.get_selected()
            model = row.get_model()
            
            if selected_idx < model.get_n_items():
                project_name = model.get_string(selected_idx)
                debug.log_event("PROJECT_CHANGE", f"Changed to project: {project_name}")
                self.current_task_info["project"] = project_name
                self.task_manager.save_tasks()
                self.refresh_task_list()
                self.refresh_sidebar()

    @debug_method("on_close_task_info")
    def on_close_task_info(self, button):
        debug.log_event("TASK_INFO", "Closing task info panel")
        
        try:
            # Solo ocultar el panel, NO destruir la estructura content_paned
            self.task_info_panel.set_visible(False)
            
            if hasattr(self, 'current_task_info'):
                debug.log_event("TASK_INFO", f"Clearing current_task_info: {self.current_task_info.get('title', 'unknown') if self.current_task_info else 'None'}")
                self.current_task_info = None
            
            # Remover el panel del content_paned pero mantener la estructura
            if hasattr(self, 'content_paned'):
                debug.log_event("TASK_INFO", "Removing panel from paned view (keeping structure)")
                self.content_paned.set_end_child(None)
                # NO destruir content_paned aquí - lo mantenemos para reutilizar
            
            # Si está usando NavigationPage, volver al contenido principal
            width = self.get_width()
            if width < 600:
                debug.log_event("TASK_INFO", "Restoring content from navigation page")
                self.split_view.set_content(self.content_page)
            
            debug.log_event("TASK_INFO", "Task info panel closed successfully")
            
        except Exception as e:
            debug.log_event("TASK_INFO", f"Error closing task info panel: {e}", stack_info=True)

    def on_task_title_changed(self, row, param):
        debug.log_event("TASK_EDIT", "Task title changed")
        if self.current_task_info:
            new_title = row.get_text()
            old_title = self.current_task_info.get("title", "unknown")
            debug.log_event("TASK_EDIT", f"Title changed from '{old_title}' to '{new_title}'")
            self.current_task_info["title"] = new_title
            self.task_manager.save_tasks()
            self.refresh_task_list()

    def on_task_notes_changed(self, buffer):
        debug.log_event("TASK_EDIT", "Task notes changed")
        if self.current_task_info:
            notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
            self.current_task_info["notes"] = notes
            self.task_manager.save_tasks()

    def on_task_completed_toggled(self, switch, param):
        debug.log_event("TASK_EDIT", f"Task completed toggled to: {switch.get_active()}")
        if self.current_task_info and self.current_task_info["completed"] != switch.get_active():
            self.current_task_info["completed"] = switch.get_active()
            self.task_manager.save_tasks()
            self.refresh_task_list()
            self.refresh_sidebar()

    def on_delete_current_task(self):
        debug.log_event("TASK_DELETE", "Deleting current task")
        if self.current_task_info:
            task_to_delete_id = self.current_task_info.get('id')
            task_title = self.current_task_info.get('title', 'unknown')
            debug.log_event("TASK_DELETE", f"Deleting task {task_to_delete_id}: '{task_title}'")
            
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            original_count = len(all_tasks)
            self.task_manager.tasks["all_tasks"] = [t for t in all_tasks if t.get('id') != task_to_delete_id]
            
            if len(self.task_manager.tasks["all_tasks"]) < original_count:
                debug.log_event("TASK_DELETE", "Task deleted successfully")
                self.task_manager.save_tasks()
                self.refresh_task_list()
                self.refresh_sidebar()
                self.on_close_task_info(None)
            else:
                debug.log_event("TASK_DELETE", "ERROR: Task was not found for deletion")

    @debug_method("on_task_toggle")
    def on_task_toggle(self, task):
        debug.log_event("TASK_TOGGLE", f"Toggling completion for task {task.get('id')}: '{task.get('title', 'unknown')}'")
        old_completed = task.get("completed", False)
        task["completed"] = not old_completed
        debug.log_event("TASK_TOGGLE", f"Task completion changed from {old_completed} to {task['completed']}")
        self.task_manager.save_tasks()
        self.refresh_task_list()
        self.refresh_sidebar()

    @debug_method("on_toggle_favorite")
    def on_toggle_favorite(self, task):
        """Toggle favorite con control anti-concurrencia mejorado"""
        task_id = task.get('id', 'unknown')
        task_title = task.get('title', 'unknown')
        debug.log_event("FAVORITE_TOGGLE", f"Starting favorite toggle for task {task_id}: '{task_title}'")
        
        # Prevenir múltiples ejecuciones concurrentes
        if hasattr(self, '_updating_favorite') and self._updating_favorite:
            debug.log_event("FAVORITE_TOGGLE", f"Already updating favorite for task {task_id}, skipping")
            return
        
        try:
            self._updating_favorite = True
            current_favorite = task.get("favorite", False)
            new_favorite = not current_favorite
            
            debug.log_event("FAVORITE_TOGGLE", f"Task {task_id} favorite changing from {current_favorite} to {new_favorite}")
            
            task["favorite"] = new_favorite
            self.task_manager.save_tasks()
            
            new_state = _("added to") if new_favorite else _("removed from")
            print(f"{_('Task')} '{task_title}' {new_state} {_('favorites')}")
            
            # Usar GLib.idle_add para refrescar de manera segura
            GLib.idle_add(self._delayed_refresh_after_favorite, task_id, task_title, new_favorite)
            
        except Exception as e:
            debug.log_event("FAVORITE_TOGGLE", f"ERROR in on_toggle_favorite for task {task_id}: {e}", stack_info=True)
        finally:
            self._updating_favorite = False

    def _delayed_refresh_after_favorite(self, task_id, task_title, is_favorite):
        """Refrescar UI de manera controlada después del toggle de favoritos"""
        try:
            debug.log_event("FAVORITE_REFRESH", f"Delayed refresh after favorite toggle for task {task_id}: '{task_title}'")
            
            # Verificar el estado de la UI antes del refresh
            self._verify_ui_state("before_favorite_refresh")
            
            self.refresh_sidebar()
            self.refresh_task_list()
            
            # Verificar el estado después
            self._verify_ui_state("after_favorite_refresh")
            
            debug.log_event("FAVORITE_REFRESH", f"Delayed refresh completed for task {task_id}")
            
        except Exception as e:
            debug.log_event("FAVORITE_REFRESH", f"ERROR in delayed refresh for task {task_id}: {e}", stack_info=True)
            # Intento de recuperación
            self._recover_from_ui_error()
        
        return False  # No repetir

    def _verify_ui_state(self, context):
        """Verificar el estado de la UI para debug"""
        try:
            debug.log_event("UI_STATE", f"=== UI STATE VERIFICATION ({context}) ===")
            debug.log_event("UI_STATE", f"Current list: {self.current_list}")
            debug.log_event("UI_STATE", f"Task info panel visible: {getattr(self, 'task_info_panel', None) and self.task_info_panel.get_visible()}")
            debug.log_event("UI_STATE", f"Current task info: {self.current_task_info.get('title') if self.current_task_info else None}")
            debug.log_event("UI_STATE", f"Window size: {self.get_width()}x{self.get_height()}")
            debug.log_event("UI_STATE", f"Total tasks: {len(self.task_manager.tasks.get('all_tasks', []))}")
            debug.log_event("UI_STATE", f"UI state valid: {getattr(self, '_ui_state_valid', True)}")
            debug.log_event("UI_STATE", f"Refresh in progress: {getattr(self, '_refresh_in_progress', False)}")
            debug.log_event("UI_STATE", f"Updating favorite: {getattr(self, '_updating_favorite', False)}")
            debug.log_event("UI_STATE", "================================")
        except Exception as e:
            debug.log_event("UI_STATE", f"Error verifying UI state: {e}")

    def _recover_from_ui_error(self):
        """Método para recuperarse de errores de UI"""
        debug.log_event("RECOVERY", "Attempting UI error recovery")
        
        try:
            # Resetear flags de estado
            self._refresh_in_progress = False
            self._updating_favorite = False
            self._refreshing_sidebar = False
            self._in_cleanup = False
            
            # Cerrar panels abiertos
            if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
                self.on_close_task_info(None)
            
            # Resetear estado
            self.current_task_info = None
            
            # Refrescar UI de manera controlada
            GLib.idle_add(self._safe_ui_refresh)
            
            debug.log_event("RECOVERY", "UI recovery initiated")
            
        except Exception as e:
            debug.log_event("RECOVERY", f"ERROR in UI recovery: {e}")

    def _safe_ui_refresh(self):
        """Refresh seguro de la UI"""
        try:
            debug.log_event("SAFE_REFRESH", "Starting safe UI refresh")
            self.refresh_task_list()
            self.refresh_sidebar()
            debug.log_event("SAFE_REFRESH", "Safe UI refresh completed")
        except Exception as e:
            debug.log_event("SAFE_REFRESH", f"Error in safe refresh: {e}")
        return False

    @debug_method("on_task_reorder")
    def on_task_reorder(self, dragged_task_id, target_task_id):
        debug.log_event("REORDER", f"Reordering: drag {dragged_task_id} to target {target_task_id}")
        
        if dragged_task_id == target_task_id:
            debug.log_event("REORDER", "Same task, no reorder needed")
            return False
        
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        
        dragged_task = None
        target_task = None
        
        for task in all_tasks:
            if task.get("id") == dragged_task_id:
                dragged_task = task
            elif task.get("id") == target_task_id:
                target_task = task
        
        if not dragged_task or not target_task:
            debug.log_event("REORDER", f"Tasks not found - dragged: {dragged_task is not None}, target: {target_task is not None}")
            return False
        
        current_tasks = self.task_manager.get_tasks(self.current_list)
        
        dragged_in_list = any(t.get("id") == dragged_task_id for t in current_tasks)
        target_in_list = any(t.get("id") == target_task_id for t in current_tasks)
        
        if not (dragged_in_list and target_in_list):
            debug.log_event("REORDER", f"Tasks not in current list - dragged: {dragged_in_list}, target: {target_in_list}")
            return False
        
        target_order = target_task.get("sort_order", 0)
        dragged_task["sort_order"] = target_order
        
        for task in current_tasks:
            if task.get("id") != dragged_task_id and task.get("sort_order", 0) >= target_order:
                task["sort_order"] = task.get("sort_order", 0) + 1
        
        self.task_manager.save_tasks()
        self.refresh_task_list()
        debug.log_event("REORDER", "Task reorder completed")
        return True        

    @debug_method("on_new_task_entry_activate")
    def on_new_task_entry_activate(self, entry):
        text = entry.get_text().strip()
        debug.log_event("NEW_TASK", f"Creating new task: '{text}'")
        
        if text:
            # Respect current list context
            list_to_add = self.current_list
            effective_date = None
            
            # Determine date based on list type
            if self.current_list in ["today", "next7", "overdue"]:
                effective_date = datetime.datetime.now().isoformat()
            
            # Determinar el proyecto basado en la lista actual
            if self.current_list.startswith("project_"):
                project_id = self.current_list.replace("project_", "")
                project = self.task_manager.get_project_by_id(project_id)
                project_name = project["name"] if project else _("Inbox")
            else:
                inbox_project = self.task_manager.get_inbox_project()
                project_name = inbox_project["name"] if inbox_project else _("Inbox")
            
            debug.log_event("NEW_TASK", f"Adding to project: {project_name}, Date: {effective_date}")
            self.task_manager.add_task(list_to_add, text, project=project_name, effective_date=effective_date)
            entry.set_text("")
            self.refresh_task_list()
            self.refresh_sidebar()
            debug.log_event("NEW_TASK", "New task created successfully")

    @debug_method("on_add_project")
    def on_add_project(self, button):
        debug.log_event("ADD_PROJECT", "Opening add project dialog")
        
        dialog = Adw.Window(title=_("Add project"), transient_for=self, modal=True, default_width=400)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, 
                         margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        title_label = Gtk.Label(label=_("Create new project"), halign=Gtk.Align.START)
        title_label.add_css_class("title-2")
        content.append(title_label)
        
        name_group = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title=_("Name"))
        name_group.add(name_row)
        content.append(name_group)
        
        color_group = Adw.PreferencesGroup(title=_("Color"))
        color_grid = Gtk.Grid()
        color_grid.set_column_spacing(10)
        color_grid.set_row_spacing(10)
        color_grid.set_margin_top(10)
        color_grid.set_margin_bottom(10)
        color_grid.set_hexpand(True)
        
        # Definir lista de colores
        all_colors = [
            "purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime",
            "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver",
            "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"
        ]
        
        # Obtener colores usados
        used_colors = {project["color"] for project in self.task_manager.projects}
        available_colors = [color for color in all_colors if color not in used_colors][:21]
        
        self.selected_color = available_colors[0] if available_colors else all_colors[0]
        self.selected_color_button = None
        
        for i, color in enumerate(available_colors):
            button = Gtk.Button()
            button.add_css_class("color-button")
            button.add_css_class(f"color-{color}")
            button.set_hexpand(True)
            button.set_size_request(40, 40)
            if i == 0:
                button.add_css_class("selected-color")
                self.selected_color_button = button
            def on_color_clicked(btn, c=color, b=button):
                if self.selected_color_button:
                    self.selected_color_button.remove_css_class("selected-color")
                self.selected_color = c
                self.selected_color_button = b
                b.add_css_class("selected-color")
            button.connect("clicked", on_color_clicked)
            row = i // 7
            col = i % 7
            color_grid.attach(button, col, row, 1, 1)
        
        color_group.add(color_grid)
        content.append(color_group)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, 
                           halign=Gtk.Align.END, margin_top=12)
        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.connect("clicked", lambda b: dialog.close())
        button_box.append(cancel_btn)
        create_btn = Gtk.Button(label=_("Create"), halign=Gtk.Align.END)
        create_btn.add_css_class("suggested-action")
        
        def create_project(btn):
            name = name_row.get_text().strip()
            color = self.selected_color
            if name and not any(p["name"] == name for p in self.task_manager.projects):
                # Generar ID único
                project_id = name.lower().replace(" ", "_").replace("ã", "a")
                existing_ids = {p.get("id") for p in self.task_manager.projects}
                original_id = project_id
                counter = 1
                while project_id in existing_ids:
                    project_id = f"{original_id}_{counter}"
                    counter += 1
                
                debug.log_event("ADD_PROJECT", f"Creating project: {name} with ID: {project_id} and color: {color}")
                new_project = {"id": project_id, "name": name, "color": color}
                self.task_manager.projects.append(new_project)
                self.task_manager.save_tasks()
                self.refresh_sidebar_projects()
                dialog.close()
        
        create_btn.connect("clicked", create_project)
        button_box.append(create_btn)
        content.append(button_box)
        dialog.set_content(content)
        dialog.present()
    
    def refresh_sidebar_projects(self):
        debug.log_event("SIDEBAR", "Refreshing sidebar projects only")
        if hasattr(self, 'projects_list_group'):
            while child := self.projects_list_group.get_first_child():
                self.projects_list_group.remove(child)
            for project in self.task_manager.projects:
                project_id = f"project_{project.get('id', project['name'])}"
                row = self.create_sidebar_row(project_id, project['name'], 
                                            is_project=True, color=project['color'])
                self.projects_list_group.append(row)

    @debug_method("on_delete_project")
    def on_delete_project(self, button):
        debug.log_event("DELETE_PROJECT", f"Deleting project for list: {self.current_list}")
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            if project_id != "inbox":
                debug.log_event("DELETE_PROJECT", f"Deleting project ID: {project_id}")
                self.task_manager.delete_project(project_id)
                self.current_list = "today"
                self.refresh_task_list()
                self.refresh_sidebar()
                debug.log_event("DELETE_PROJECT", "Project deleted, switched to today view")
            else:
                debug.log_event("DELETE_PROJECT", "Cannot delete inbox project")

    @debug_method("on_edit_project")
    def on_edit_project(self, button):
        debug.log_event("EDIT_PROJECT", f"Editing project for list: {self.current_list}")
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project_to_edit = self.task_manager.get_project_by_id(project_id)
            if project_to_edit:
                debug.log_event("EDIT_PROJECT", f"Opening edit dialog for project: {project_to_edit['name']}")
                
                dialog = Adw.Window(title=_("Edit project"), transient_for=self, modal=True, default_width=400)
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, 
                                margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
                title_label = Gtk.Label(label=_("Edit project"), halign=Gtk.Align.START)
                title_label.add_css_class("title-2")
                content.append(title_label)
                
                name_group = Adw.PreferencesGroup()
                name_row = Adw.EntryRow(title=_("Name"))
                name_row.set_text(project_to_edit["name"])
                name_group.add(name_row)
                content.append(name_group)
                
                color_group = Adw.PreferencesGroup(title=_("Color"))
                color_grid = Gtk.Grid()
                color_grid.set_column_spacing(10)
                color_grid.set_row_spacing(10)
                color_grid.set_margin_top(10)
                color_grid.set_margin_bottom(10)
                color_grid.set_hexpand(True)
                
                all_colors = [
                    "purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime",
                    "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver",
                    "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"
                ]
                
                # Obtener colores usados (excepto el actual)
                used_colors = {project["color"] for project in self.task_manager.projects if project.get("id") != project_id}
                available_colors = [color for color in all_colors if color not in used_colors][:21]
                
                # Añadir el color actual si no está en la lista
                current_color = project_to_edit["color"]
                if current_color not in available_colors:
                    available_colors.append(current_color)
                
                self.selected_color = current_color
                self.selected_color_button = None
                
                for i, color in enumerate(available_colors):
                    button = Gtk.Button()
                    button.add_css_class("color-button")
                    button.add_css_class(f"color-{color}")
                    button.set_hexpand(True)
                    button.set_size_request(40, 40)
                    if color == current_color:
                        button.add_css_class("selected-color")
                        self.selected_color_button = button
                    def on_color_clicked(btn, c=color, b=button):
                        if self.selected_color_button:
                            self.selected_color_button.remove_css_class("selected-color")
                        self.selected_color = c
                        self.selected_color_button = b
                        b.add_css_class("selected-color")
                    button.connect("clicked", on_color_clicked)
                    row = i // 7
                    col = i % 7
                    color_grid.attach(button, col, row, 1, 1)
                
                color_group.add(color_grid)
                content.append(color_group)
                
                button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, 
                                   halign=Gtk.Align.END, margin_top=12)
                cancel_btn = Gtk.Button(label=_("Cancel"))
                cancel_btn.connect("clicked", lambda b: dialog.close())
                button_box.append(cancel_btn)
                save_btn = Gtk.Button(label=_("Save"), halign=Gtk.Align.End)
                save_btn.add_css_class("suggested-action")
                
                def save_project(btn):
                    new_name = name_row.get_text().strip()
                    inbox_project = self.task_manager.get_inbox_project()
                    inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
                    
                    if (new_name and new_name != inbox_name and 
                        not any(p["name"] == new_name for p in self.task_manager.projects if p.get("id") != project_id)):
                        
                        debug.log_event("EDIT_PROJECT", f"Saving project changes: name='{new_name}', color='{self.selected_color}'")
                        
                        # Actualizar nombre y color
                        old_name = project_to_edit["name"]
                        project_to_edit["name"] = new_name
                        project_to_edit["color"] = self.selected_color
                        
                        # Actualizar tareas con el nuevo nombre del proyecto
                        all_tasks = self.task_manager.tasks.get("all_tasks", [])
                        for task in all_tasks:
                            if task.get("project") == old_name:
                                task["project"] = new_name
                        
                        self.task_manager.save_tasks()
                        self.refresh_task_list()
                        self.refresh_sidebar()
                        dialog.close()
                        debug.log_event("EDIT_PROJECT", "Project saved successfully")
                
                save_btn.connect("clicked", save_project)
                button_box.append(save_btn)
                content.append(button_box)
                dialog.set_content(content)
                dialog.present()
            else:
                debug.log_event("EDIT_PROJECT", f"Project with ID {project_id} not found")

    @debug_method("on_window_close")
    def on_window_close(self, window):
        debug.log_event("WINDOW", "Window closing, saving configuration")
        width = self.get_width()
        height = self.get_height()
        self.config.set("window_width", width)
        self.config.set("window_height", height)
        self.config.set("current_list", self.current_list)
        debug.log_event("WINDOW", f"Saved config: size={width}x{height}, list={self.current_list}")
        return False

    def update_header_title(self):
        # Ya no necesitamos actualizar un título separado
        pass

    @debug_method("initialize_sample_data")
    def initialize_sample_data(self):
        debug.log_event("INIT", "Initializing sample data")
        self.ensure_inbox_project()
        
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        
        # Asegurar que todas las tareas tengan los campos necesarios
        for task in all_tasks:
            if "favorite" not in task:
                task["favorite"] = False
            if "sort_order" not in task:
                task["sort_order"] = 0
        
        if not all_tasks:
            debug.log_event("INIT", "No existing tasks, would create sample data here")
        else:
            debug.log_event("INIT", f"Found {len(all_tasks)} existing tasks")
            self.task_manager.save_tasks()

    def setup_shortcuts(self):
        debug.log_event("UI", "Setting up keyboard shortcuts")
        shortcuts = [("<Control>n", self.on_add_task_shortcut)]
        controller = Gtk.ShortcutController()
        for trigger, callback in shortcuts:
            shortcut = Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(trigger))
            action = Gtk.CallbackAction.new(callback)
            shortcut.set_action(action)
            controller.add_shortcut(shortcut)
        self.add_controller(controller)

    def on_add_task_shortcut(self, widget, args):
        debug.log_event("SHORTCUT", "Ctrl+N pressed, focusing new task entry")
        if hasattr(self, 'new_task_entry'):
            self.new_task_entry.grab_focus()
        return True

    def setup_custom_css(self):
        debug.log_event("UI", "Setting up custom CSS")
        css_provider = Gtk.CssProvider()
        css_data = """
        window {
            background-color: @window_bg_color;
        }
        
        .boxed-list {
            background-color: transparent;
            border: none;
            border-radius: 0px;
        }

        .boxed-list > row {
            margin-bottom: 0px;
            background-color: transparent;
            border: none;
            padding: 8px 12px;
            border-radius: 0px;
            transition: background-color 0.2s ease;
        }
        
        .boxed-list > row:not(.date-header-row):hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        
        .boxed-list > row.date-header-row:hover {
            background-color: transparent !important;
        }
        
        .boxed-list > row:first-child { 
            border-top: none;
            border-top-left-radius: 0px; 
            border-top-right-radius: 0px; 
        }
        
        .boxed-list > row:last-child { 
            border-bottom-left-radius: 0px; 
            border-bottom-right-radius: 0px; 
        }

        .boxed-list > row:only-child {
            border-radius: 0px;
            border: none;
        }

        .date-header {
            font-size: 12px;
            opacity: 0.7;
        }

        .date-header-past {
            color: #dc2626;
            font-weight: bold;
            opacity: 1;
        }

        .date-header-today {
            color: #2563eb;
            font-weight: bold;
            opacity: 1;
        }

        .date-header-future {
            color: #16a34a;
            font-weight: bold;
            opacity: 1;
        }        
        
        adw-action-row {
            min-height: 44px;
        }

        adw-action-row .title {
            font-size: 14px;
            font-weight: normal;
        }
        
        .new-task-entry {
            background-color: rgba(0, 0, 0, 0.05);
            border-radius: 8px;
            border: 1px solid alpha(@borders, 0.3);
            box-shadow: none;
            padding: 8px 12px;
            margin-top: 6px;
            font-size: 14px;
        }
        
        .new-task-entry image {
            opacity: 0.6;
            margin-right: 8px;
        }

        .title-1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 16px;
            margin-top: 8px;
            background-color: transparent;
        }

        .overdue-title {
            color: @error_color;
        }

        .drag-handle-icon {
            opacity: 0.4;
            margin-right: 8px;
        }
        
        .caption {
            font-size: 12px;
            opacity: 0.7;
        }

        .dim-label {
            opacity: 0.6;
        }

        button.flat {
            min-height: 48px !important;
            min-width: 48px !important;
            padding: 12px !important;
        }

        .task-checkbox {
            padding: 0;
            min-height: 12px !important;
            min-width: 12px !important;
            -gtk-icon-size: 12px !important;
        }

        .task-checkbox check {
            min-height: 12px !important;
            min-width: 12px !important;
            border-radius: 3px !important;
            margin: 0 !important;
            border-width: 1px;
        }

        .boxed-list .task-checkbox check {
            min-height: 12px !important;
            min-width: 12px !important;
        }
        
        .sidebar {
            border-right: 1px solid @borders;
            background-color: rgba(0, 0, 0, 0.03);
        }
        
        .navigation-sidebar {
            background-color: transparent;
        }

        .navigation-sidebar row {
            border-radius: 6px;
        }
        
        .project-color {
            border-radius: 4px;
            min-width: 16px;
            min-height: 10px;
            margin-right: 8px;
        }

        .color-button {
            border-radius: 8px;
            min-width: 40px;
            min-height: 40px;
            padding: 0;
            border: 1px solid alpha(@borders, 0.3);
        }

        .color-button:hover {
            opacity: 0.8;
        }

        .color-button.selected-color {
            border: 3px solid @accent_color;
        }

        .color-purple { background-color: #9333ea; }
        .color-orange { background-color: #ea580c; }
        .color-blue { background-color: #2563eb; }
        .color-green { background-color: #16a34a; }
        .color-yellow { background-color: #ca8a04; }
        .color-red { background-color: #dc2626; }
        .color-pink { background-color: #ec4899; }
        .color-cyan { background-color: #06b6d4; }
        .color-teal { background-color: #14b8a6; }
        .color-lime { background-color: #84cc16; }
        .color-amber { background-color: #f59e0b; }
        .color-indigo { background-color: #4f46e5; }
        .color-violet { background-color: #a855f7; }
        .color-magenta { background-color: #d946ef; }
        .color-olive { background-color: #6b7280; }
        .color-gray { background-color: #718096; }
        .color-brown { background-color: #8B4513; }
        .color-gold { background-color: #FFD700; }
        .color-silver { background-color: #C0C0C0; }
        .color-maroon { background-color: #800000; }
        .color-navy { background-color: #000080; }
        .color-turquoise { background-color: #40E0D0; }
        .color-coral { background-color: #FF7F50; }
        .color-sky { background-color: #87CEEB; }
        .color-emerald { background-color: #2E8B57; }
        .color-ruby { background-color: #E0115F; }
        .color-black { background-color: #000000; }
        
        .text-color-purple { color: #9333ea; }
        .text-color-orange { color: #ea580c; }
        .text-color-blue { color: #2563eb; }
        .text-color-green { color: #16a34a; }
        .text-color-yellow { color: #ca8a04; }
        .text-color-red { color: #dc2626; }
        .text-color-pink { color: #ec4899; }
        .text-color-cyan { color: #06b6d4; }
        .text-color-teal { color: #14b8a6; }
        .text-color-lime { color: #84cc16; }
        .text-color-amber { color: #f59e0b; }
        .text-color-indigo { color: #4f46e5; }
        .text-color-violet { color: #a855f7; }
        .text-color-magenta { color: #d946ef; }
        .text-color-olive { color: #6b7280; }
        .text-color-gray { color: #718096; }
        .text-color-brown { color: #8B4513; }
        .text-color-gold { color: #FFD700; }
        .text-color-silver { color: #C0C0C0; }
        .text-color-maroon { color: #800000; }
        .text-color-navy { color: #000080; }
        .text-color-turquoise { color: #40E0D0; }
        .text-color-coral { color: #FF7F50; }
        .text-color-sky { color: #87CEEB; }
        .text-color-emerald { color: #2E8B57; }
        .text-color-ruby { color: #E0115F; }
        .text-color-black { color: #000000; }
        """
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        debug.log_event("UI", "Custom CSS loaded successfully")


class TaskManagerApplication(Adw.Application):
    def __init__(self):
        debug.log_event("APP", "Initializing TaskManagerApplication")
        super().__init__(
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self.on_activate)
        self.setup_actions()
        debug.log_event("APP", "TaskManagerApplication initialized")

    @debug_method("setup_actions")
    def setup_actions(self):
        debug.log_event("APP", "Setting up application actions")
        
        # Acción de cambio de idioma
        language_action = Gio.SimpleAction.new_stateful(
            "language", GLib.VariantType.new("s"), GLib.Variant("s", "auto")
        )
        language_action.connect("activate", self.on_language_changed)
        self.add_action(language_action)
        debug.log_event("APP", "Language action added")

        # Acción de preferencias
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences)
        self.add_action(preferences_action)
        debug.log_event("APP", "Preferences action added")

        # Acción de acerca de
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
        debug.log_event("APP", "About action added")

    @debug_method("on_language_changed")
    def on_language_changed(self, action, parameter):
        """Cambiar idioma de la aplicación"""
        language_code = parameter.get_string()
        debug.log_event("APP", f"Language change requested: {language_code}")
        action.set_state(parameter)
        if hasattr(self, "win"):
            self.win.change_language(language_code)

    @debug_method("on_preferences")
    def on_preferences(self, action, parameter):
        """Mostrar ventana de preferencias"""
        debug.log_event("APP", "Preferences requested")
        if hasattr(self, "win"):
            self.show_preferences_dialog()

    def show_preferences_dialog(self):
        """Mostrar diálogo de preferencias"""
        debug.log_event("PREFS", "Opening preferences dialog")
        
        dialog = Adw.PreferencesWindow()
        dialog.set_title(_("Preferences"))
        dialog.set_modal(True)
        dialog.set_transient_for(self.win)

        # Página de preferencias generales
        page = Adw.PreferencesPage()
        page.set_title(_("General"))

        # Grupo de idioma
        language_group = Adw.PreferencesGroup()
        language_group.set_title(_("Language"))

        # Selector de idioma
        language_row = Adw.ComboRow()
        language_row.set_title(_("Interface Language"))
        language_model = Gtk.StringList()
        language_model.append(_("Auto-detect"))
        language_model.append(_("English"))
        language_model.append(_("Spanish"))
        language_row.set_model(language_model)

        # Establecer selección actual
        current_lang = self.win.current_language
        if current_lang == "auto":
            language_row.set_selected(0)
        elif current_lang == "en":
            language_row.set_selected(1)
        elif current_lang == "es":
            language_row.set_selected(2)

        language_row.connect("notify::selected", self.on_language_row_changed)
        language_group.add(language_row)
        page.add(language_group)

        # Grupo de apariencia
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title(_("Appearance"))

        # Switch para tema oscuro
        dark_theme_row = Adw.SwitchRow()
        dark_theme_row.set_title(_("Dark Theme"))
        dark_theme_row.set_subtitle(_("Use dark theme for the application"))
        dark_theme_row.set_active(self.win.config.get("dark_theme", False))
        dark_theme_row.connect("notify::active", self.on_theme_changed)
        appearance_group.add(dark_theme_row)
        page.add(appearance_group)

        dialog.add(page)
        dialog.present()

    def on_theme_changed(self, switch_row, param):
        """Manejar cambio de tema"""
        dark_theme = switch_row.get_active()
        debug.log_event("PREFS", f"Theme changed to dark: {dark_theme}")
        self.win.change_theme(dark_theme)

    def on_language_row_changed(self, combo_row, param):
        """Manejar cambio en el selector de idioma"""
        selected = combo_row.get_selected()
        language_codes = ["auto", "en", "es"]
        if selected < len(language_codes):
            language_code = language_codes[selected]
            debug.log_event("PREFS", f"Language row changed to: {language_code}")
            action = self.lookup_action("language")
            if action:
                action.activate(GLib.Variant("s", language_code))

    @debug_method("on_about")
    def on_about(self, action, parameter):
        """Mostrar diálogo Acerca de con icono"""
        debug.log_event("APP", "About dialog requested")
        
        about_dialog = Adw.AboutWindow()
        about_dialog.set_transient_for(self.win)
        about_dialog.set_modal(True)
        about_dialog.set_application_name(_("Todo List"))
        about_dialog.set_application_icon("com.pabmartine.TodoList")
        about_dialog.set_version("1.0.4")  # Versión con debug
        about_dialog.set_developer_name("pabmartine")
        about_dialog.set_copyright("© 2025")
        about_dialog.set_comments(_("A simple and powerful task management application"))
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        about_dialog.set_developers(["pabmartine"])
        about_dialog.set_website("https://github.com/pabmartine/todo-list")
        about_dialog.present()

    @debug_method("on_activate")
    def on_activate(self, app):
        """Se llama cuando se activa la aplicación"""
        debug.log_event("APP", "Application activated")
        try:
            self.win = TaskManagerWindow(application=app)
            debug.log_event("APP", "Main window created successfully")
            self.win.present()
            debug.log_event("APP", "Main window presented")
            
            # Mostrar estado inicial en el log
            debug.log_event("APP", f"Initial window size: {self.win.get_width()}x{self.win.get_height()}")
            debug.log_event("APP", f"Initial list: {self.win.current_list}")
            debug.log_event("APP", f"Total projects: {len(self.win.task_manager.projects)}")
            debug.log_event("APP", f"Total tasks: {len(self.win.task_manager.tasks.get('all_tasks', []))}")
            
            # Dump de eventos iniciales después de un momento
            def dump_initial_events():
                debug.dump_recent_events(50)
                return False
            GLib.timeout_add_seconds(2, dump_initial_events)
            
        except Exception as e:
            debug.log_event("APP", f"ERROR during activation: {e}", stack_info=True)


def main():
    """Función principal con logging mejorado"""
    debug.log_event("MAIN", "=== STARTING TODO LIST APPLICATION ===")
    debug.log_event("MAIN", f"Python version: {sys.version}")
    debug.log_event("MAIN", f"GTK version: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")
    
    try:
        app = TaskManagerApplication()
        debug.log_event("MAIN", "Application created successfully")
        
        result = app.run(sys.argv)
        debug.log_event("MAIN", f"Application finished with code: {result}")
        
        # Dump final de eventos al salir
        debug.log_event("MAIN", "=== FINAL DEBUG DUMP ===")
        debug.dump_recent_events(100)
        
        return result
        
    except Exception as e:
        debug.log_event("MAIN", f"CRITICAL ERROR in main: {e}", stack_info=True)
        debug.dump_recent_events(50)
        return 1


if __name__ == "__main__":
    main()        