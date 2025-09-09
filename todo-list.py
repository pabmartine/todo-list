#!/usr/bin/env python3

import sys
import os
import json
import locale
import gettext
import datetime
from pathlib import Path
from collections import OrderedDict
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, Pango, Gdk

# Configuración de internacionalización
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")
DOMAIN = "todo-list"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "todo-list")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_FILE = os.path.join(CONFIG_DIR, "tasks.json")

def setup_locale(language=None):
    """Configurar el idioma de la aplicación"""
    if language:
        os.environ["LANGUAGE"] = language
        os.environ["LC_ALL"] = language
    
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    
    try:
        lang_translations = gettext.translation(DOMAIN, LOCALE_DIR, fallback=True)
        lang_translations.install()
        return lang_translations.gettext
    except Exception:
        return lambda text: text

# Configurar idioma inicial
_ = setup_locale()

class ConfigManager:
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.default_config = {
            "language": "auto",
            "dark_theme": False,
            "window_width": 1200,
            "window_height": 800,
            "current_list": "today",
        }
        self.config = self.load_config()

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
            pass
        return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

class TaskManager:
    def __init__(self):
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

    def update_list_names(self):
        """Actualizar nombres de listas con traducciones"""
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
        for project in self.projects:
            if project.get("id") == "inbox":
                old_name = project["name"]
                new_name = _("Inbox")
                project["name"] = new_name
                if old_name != new_name:
                    # Actualizar tareas con el nuevo nombre
                    all_tasks = self.tasks.get("all_tasks", [])
                    for task in all_tasks:
                        if task.get("project") == old_name:
                            task["project"] = new_name
                break

    def migrate_legacy_projects(self):
        """Migrar proyectos legacy sin ID a la nueva estructura"""
        needs_migration = False
        
        # Verificar si hay proyectos sin ID
        for project in self.projects:
            if "id" not in project:
                needs_migration = True
                break
        
        if needs_migration:
            # Fusionar múltiples proyectos Inbox
            inbox_variants = ["Inbox", "Bandeja de entrada"]
            inbox_projects = [p for p in self.projects if p["name"] in inbox_variants]
            
            if len(inbox_projects) > 1:
                # Mantener el primer proyecto Inbox
                main_inbox = inbox_projects[0]
                main_inbox["id"] = "inbox"
                main_inbox["name"] = _("Inbox")
                
                # Mover tareas de otros proyectos Inbox al principal
                all_tasks = self.tasks.get("all_tasks", [])
                for project in inbox_projects[1:]:
                    for task in all_tasks:
                        if task.get("project") == project["name"]:
                            task["project"] = main_inbox["name"]
                    # Eliminar proyecto duplicado
                    self.projects.remove(project)
            
            # Asignar IDs a proyectos que no los tengan
            for project in self.projects:
                if "id" not in project:
                    if project["name"] == _("Inbox") or project["name"] in inbox_variants:
                        project["id"] = "inbox"
                        project["name"] = _("Inbox")
                    else:
                        # Generar ID basado en el nombre
                        project_id = project["name"].lower().replace(" ", "_").replace("ã", "a")
                        project["id"] = project_id
            
            self.save_tasks()

    def clean_duplicate_inboxes(self):
        """Limpiar proyectos Inbox duplicados"""
        inbox_variants = set(["Inbox", "Bandeja de entrada"])
        current_inbox_name = _("Inbox")
        inbox_variants.add(current_inbox_name)
        
        # Encontrar proyectos potenciales de inbox
        potential_inboxes = [
            p for p in self.projects 
            if p.get("id") == "inbox" or p["name"] in inbox_variants
        ]
        
        if len(potential_inboxes) <= 1:
            return
        
        # Elegir el principal: preferir el que tiene id="inbox"
        main_inbox = next(
            (p for p in potential_inboxes if p.get("id") == "inbox"), 
            potential_inboxes[0]
        )
        
        main_inbox["id"] = "inbox"
        main_inbox["name"] = current_inbox_name
        main_inbox["color"] = "black"
        
        # Nombres de duplicados
        duplicate_names = {p["name"] for p in potential_inboxes}
        
        # Reasignar tareas
        all_tasks = self.tasks.get("all_tasks", [])
        for task in all_tasks:
            if task.get("project") in duplicate_names:
                task["project"] = main_inbox["name"]
        
        # Remover duplicados excepto el principal
        self.projects = [
            p for p in self.projects if p not in potential_inboxes
        ] + [main_inbox]
        
        self.save_tasks()

    def load_tasks(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.projects = data.get("projects", [])
                    
                    # Migrar proyectos legacy
                    self.migrate_legacy_projects()
                    
                    # Limpiar duplicados de inbox
                    self.clean_duplicate_inboxes()
                    
                    if "all_tasks" not in data:
                        all_tasks = []
                        for k, v in data.items():
                            if k != "projects" and isinstance(v, list):
                                for task in v:
                                    if "list_id" not in task:
                                        task["list_id"] = k
                                    all_tasks.append(task)
                        return {"all_tasks": all_tasks}
                    else:
                        return {k: v for k, v in data.items() if k != "projects"}
        except Exception as e:
            pass
        return {"all_tasks": []}

    def save_tasks(self):
        try:
            data = {**self.tasks, "projects": self.projects}
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass

    def add_task(self, list_id, title, due_date=None, priority=0, notes="", project=None, effective_date=None):
        if project is None:
            # Buscar el proyecto Inbox por ID
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
            "effective_date": effective_date if effective_date else now.isoformat(),
            "list_id": list_id,
            "favorite": False,
            "sort_order": 0
        }
        
        if "all_tasks" not in self.tasks:
            self.tasks["all_tasks"] = []
        self.tasks["all_tasks"].append(task)
        self.save_tasks()

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
            # Buscar proyecto por ID
            project = self.get_project_by_id(project_id)
            if project:
                project_name = project["name"]
                result = [task for task in all_tasks if task.get("project") == project_name and not task.get("completed", False)]
            else:
                result = []
        else:
            result = []
        
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
        return len(self.get_tasks(list_id))

    def delete_project(self, project_id):
        """Eliminar proyecto por ID"""
        if project_id == "inbox":
            return  # No permitir eliminar el Inbox
        
        project = self.get_project_by_id(project_id)
        if not project:
            return
            
        project_name = project["name"]
        inbox_project = self.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        
        # Reasignar tareas al Inbox
        all_tasks = self.tasks.get("all_tasks", [])
        for task in all_tasks:
            if task.get("project") == project_name:
                task["project"] = inbox_name
        
        # Remover el proyecto
        self.projects = [p for p in self.projects if p.get("id") != project_id]
        self.save_tasks()

class TaskManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = ConfigManager()
        self.task_manager = TaskManager()
        self.current_language = self.config.get("language", "auto")
        self.current_list = self.config.get("current_list", "today")
        self.sort_ascending = False
        self.current_task_info = None
        self.selected_color = None
        self.selected_color_button = None

        self.ensure_inbox_project()
        self.apply_saved_config()
        self.set_title(_("Todo List"))
        
        window_width = self.config.get("window_width", 1200)
        window_height = self.config.get("window_height", 800)
        self.set_default_size(window_width, window_height)

        self.setup_ui()
        self.setup_custom_css()
        self.setup_shortcuts()
        self.connect("close-request", self.on_window_close)
        self.initialize_sample_data()

    def ensure_inbox_project(self):
        """Asegurar que existe el proyecto Inbox y actualizar su nombre según el idioma"""
        inbox_exists = any(p.get("id") == "inbox" for p in self.task_manager.projects)
        if not inbox_exists:
            inbox_project = {"id": "inbox", "name": _("Inbox"), "color": "black"}
            self.task_manager.projects.insert(0, inbox_project)
            self.task_manager.save_tasks()
        else:
            # Actualizar el nombre del inbox existente al idioma actual
            self.task_manager.update_project_names()
            self.task_manager.save_tasks()

    def apply_saved_config(self):
        saved_language = self.config.get("language", "auto")
        if saved_language != "auto":
            global _
            _ = setup_locale(saved_language)
        dark_theme = self.config.get("dark_theme", False)
        self.apply_theme(dark_theme)

    def apply_theme(self, dark_theme):
        style_manager = Adw.StyleManager.get_default()
        if dark_theme:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def change_language(self, language_code):
        """Cambiar el idioma de la aplicación"""
        global _
        _ = setup_locale(language_code if language_code != "auto" else None)
        self.config.set("language", language_code)
        self.current_language = language_code
        
        # Actualizar nombres de listas y proyectos
        self.task_manager.update_list_names()
        self.task_manager.update_project_names()
        self.task_manager.clean_duplicate_inboxes()  # Limpiar posibles duplicados después de cambio
        self.task_manager.save_tasks()
        
        # Recrear interfaz
        self.recreate_ui()

    def change_theme(self, dark_theme):
        """Cambiar tema de la aplicación"""
        self.apply_theme(dark_theme)
        self.config.set("dark_theme", dark_theme)

    def recreate_ui(self):
        """Recrear la interfaz con los textos actualizados"""
        # Actualizar título de ventana
        self.set_title(_("Todo List"))
        
        # Actualizar tooltips y textos de la interfaz
        self.new_list_btn.set_label(_("Add Project"))
        
        # Actualizar placeholder de nueva tarea
        self.new_task_entry.set_placeholder_text(_("New task..."))
        
        # Actualizar tooltip del botón de borrar archivadas
        if hasattr(self, 'clear_archived_button'):
            self.clear_archived_button.set_tooltip_text(_("Clear all archived tasks"))
        
        # Recrear sidebar
        self.refresh_sidebar()
        
        # Actualizar lista de tareas
        self.refresh_task_list()

    def setup_ui(self):
        self.create_header_bar()
        self.create_main_area()
        self.create_task_info_panel()
        self.setup_layout()
        self.refresh_task_list()

    def create_header_bar(self):
        self.header_bar = Gtk.HeaderBar()
        
        self.new_list_btn = Gtk.Button()
        self.new_list_btn.set_icon_name("project-add-symbolic")
        self.new_list_btn.set_label(_("Add Project"))
        self.new_list_btn.add_css_class("flat")
        self.new_list_btn.connect("clicked", self.on_add_project)
        self.header_bar.pack_start(self.new_list_btn)

        self.header_title = Gtk.Label()
        self.header_title.add_css_class("title")
        self.header_bar.set_title_widget(self.header_title)

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
        self.header_bar.pack_end(menu_button)

        self.set_titlebar(self.header_bar)
    
    def setup_layout(self):
        main_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        sidebar_container = self.create_sidebar()
        sidebar_container.set_size_request(280, -1)
        main_container.append(sidebar_container)
        
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_wide_handle(True)
        self.content_paned.set_hexpand(True)
        
        self.content_paned.set_shrink_start_child(True)
        self.content_paned.set_shrink_end_child(False)
        self.content_paned.set_resize_start_child(True) 
        self.content_paned.set_resize_end_child(False)
        
        self.content_paned.set_start_child(self.main_area)
        main_container.append(self.content_paned)
        
        self.set_child(main_container)
        
        self.update_header_title()

    def on_window_close(self, window):
        width = self.get_width()
        height = self.get_height()
        self.config.set("window_width", width)
        self.config.set("window_height", height)
        self.config.set("current_list", self.current_list)
        return False

    def update_header_title(self):
        self.header_title.set_text("")

    def initialize_sample_data(self):
        self.ensure_inbox_project()
        
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        
        for task in all_tasks:
            if "favorite" not in task:
                task["favorite"] = False
            if "sort_order" not in task:
                task["sort_order"] = 0
        
        if not all_tasks:
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1))
            today = datetime.datetime.now()
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1))
            
            inbox_project = self.task_manager.get_inbox_project()
            inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
                        
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            if all_tasks:
                all_tasks[0]["completed"] = True
                self.task_manager.save_tasks()
        else:
            self.task_manager.save_tasks()

    def create_sidebar(self):
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.add_css_class("sidebar")

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

        projects_label = Gtk.Label(label=_("Projects"), halign=Gtk.Align.START)
        projects_label.add_css_class("title-4")
        projects_label.set_margin_bottom(6)
        content_box.append(projects_label)

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
        sidebar_box.append(scrolled)
        return sidebar_box

    def create_sidebar_row(self, list_id, name, is_project=False, color=None):
        row = Adw.ActionRow(title=name)
        row.set_name(list_id)
        
        if is_project:
            color_dot = Gtk.Box()
            color_dot.add_css_class("project-color")
            # Usar color negro para el proyecto Inbox
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
        try:
            if self.current_list.startswith("project_"):
                child = self.projects_list_group.get_first_child()
                while child:
                    if hasattr(child, 'get_name') and child.get_name() == self.current_list:
                        self.projects_list_group.select_row(child)
                        break
                    child = child.get_next_sibling()
            else:
                child = self.main_list_group.get_first_child()
                while child:
                    if hasattr(child, 'get_name') and child.get_name() == self.current_list:
                        self.main_list_group.select_row(child)
                        break
                    child = child.get_next_sibling()
        except Exception as e:
            pass
        return False

    def on_list_selected(self, listbox, row):
        if row is None: 
            return
        
        list_id = row.get_name()
        
        if not list_id:
            return
            
        if list_id == self.current_list:
            return
            
        if listbox == self.main_list_group:
            self.projects_list_group.unselect_all()
        else:
            self.main_list_group.unselect_all()
            
        self.current_list = list_id
        
        self.refresh_task_list()
        self.update_header_title()
        
        if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
            self.on_close_task_info(None)

    def create_main_area(self):
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
        self.edit_button = Gtk.Button(icon_name="edit-symbolic")
        self.edit_button.add_css_class("flat")
        self.edit_button.connect("clicked", self.on_edit_project)
        self.edit_button.set_visible(False)
        title_box.append(self.edit_button)

        # Botón eliminar
        self.delete_button = Gtk.Button(icon_name="delete-symbolic")
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

        self.refresh_task_list()

    def update_sort_button(self):
        if self.sort_ascending:
            self.sort_button.set_icon_name("view-sort-ascending-symbolic")
            self.sort_button.set_tooltip_text(_("Sort by date: oldest first"))
        else:
            self.sort_button.set_icon_name("view-sort-descending-symbolic")
            self.sort_button.set_tooltip_text(_("Sort by date: newest first"))

    def on_sort_toggle(self, button):
        self.sort_ascending = not self.sort_ascending
        self.update_sort_button()
        self.refresh_task_list()

    def refresh_task_list(self):
        while child := self.task_list.get_first_child():
            self.task_list.remove(child)

        # Actualizar visibilidad de botones
        is_project = self.current_list.startswith("project_")
        project_id = self.current_list.replace("project_", "") if is_project else ""
        is_inbox = project_id == "inbox"
        is_archived = self.current_list == "archived"
        
        self.edit_button.set_visible(is_project and not is_inbox)
        self.delete_button.set_visible(is_project and not is_inbox)
        self.clear_archived_button.set_visible(is_archived)

        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project = self.task_manager.get_project_by_id(project_id)
            if project:
                list_name = project["name"]
                project_color = project["color"]
                self.list_title_label.set_text(list_name)
                
                for color in ["purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime", "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver", "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"]:
                    self.list_title_label.remove_css_class(f"text-color-{color}")
                self.list_title_label.remove_css_class("overdue-title")
                
                if project_id == "inbox":
                    self.list_title_label.remove_css_class("text-color-purple")
                    self.list_title_label.add_css_class("text-color-black")
                elif project_color:
                    self.list_title_label.add_css_class(f"text-color-{project_color}")
            else:
                self.list_title_label.set_text(_("Project not found"))
        else:
            list_name = self.task_manager.lists.get(self.current_list, self.current_list)
            self.list_title_label.set_text(list_name)
            for color in ["purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime", "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver", "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby"]:
                self.list_title_label.remove_css_class(f"text-color-{color}")
            if self.current_list == "overdue":
                self.list_title_label.add_css_class("overdue-title")
            else:
                self.list_title_label.remove_css_class("overdue-title")

        tasks = self.task_manager.get_tasks(self.current_list)
        
        sorted_tasks = self.sort_tasks(tasks)
        
        if len(sorted_tasks) > 0:
            self.task_list_scrolled.set_visible(True)
            if self.should_group_by_date():
                self.create_grouped_task_rows(sorted_tasks)
            else:
                self.create_standard_task_rows(sorted_tasks)
        else:
            self.task_list_scrolled.set_visible(False)
        
        self.update_header_title()

    def should_group_by_date(self):
        groupable_lists = ["today", "all", "overdue", "archived"]
        return self.current_list in groupable_lists

    def create_grouped_task_rows(self, tasks):
        if not tasks:
            return
        
        grouped_tasks = self.group_tasks_by_date(tasks)
        
        for date_key, date_tasks in grouped_tasks.items():
            # Omitir la cabecera "Hoy" cuando estamos en la vista "Hoy"
            if not (self.current_list == "today" and date_key == "hoy"):
                date_header = self.create_date_header(date_key)
                self.task_list.append(date_header)
            
            for task in date_tasks:
                row = self.create_task_row(task)
                self.task_list.append(row)

    def create_standard_task_rows(self, tasks):
        for task in tasks:
            row = self.create_task_row(task)
            self.task_list.append(row)

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
        
        past_days.sort(key=lambda x: int(x.split("_")[1]))
        future_days.sort(key=lambda x: int(x.split("_")[1]))
        
        for key in past_days:
            sorted_groups[key] = grouped[key]
        
        if today_key:
            sorted_groups[today_key] = grouped[today_key]
        
        for key in future_days:
            sorted_groups[key] = grouped[key]
            
        if no_date_key:
            sorted_groups[no_date_key] = grouped[no_date_key]
        
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
        header_row.add_css_class("date-header-row")  # Añadir clase CSS
        
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
                date_key = "0000-01-01T00:00:00" if self.sort_ascending else "9999-12-31T23:59:59"
            else:
                date_key = effective_date
            
            return (sort_order, date_key)
        
        sorted_tasks = sorted(tasks, key=get_sort_key, reverse=not self.sort_ascending)
        
        return sorted_tasks

    def on_clear_archived_tasks(self, button):
        """Mostrar diálogo de confirmación para borrar todas las tareas archivadas"""
        archived_tasks = self.task_manager.get_tasks("archived")
        if not archived_tasks:
            return
        
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
        if response == "delete":
            # Eliminar todas las tareas archivadas
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            self.task_manager.tasks["all_tasks"] = [
                task for task in all_tasks if not task.get("completed", False)
            ]
            
            self.task_manager.save_tasks()
            self.refresh_task_list()
            self.refresh_sidebar()
            
            # Cerrar panel de información si está abierto
            if hasattr(self, 'task_info_panel') and self.task_info_panel.get_visible():
                self.on_close_task_info(None)
        
        dialog.close()
    
    def create_task_row(self, task):
        row = Adw.ActionRow()
        row.set_name(str(task["id"]))
        row.set_title(task["title"])
        row.set_activatable(True)

        if task["completed"]:
            row.add_css_class("dim-label")
        
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
        
        check = Gtk.CheckButton(active=task["completed"])
        check.add_css_class("task-checkbox")
        check.connect("toggled", lambda w, t=task: self.on_task_toggle(t))
        row.add_prefix(check)

        if task.get("project"):
            project_label = Gtk.Label(label=task["project"])
            project_label.add_css_class("dim-label")
            project_label.add_css_class("caption")
            row.add_suffix(project_label)
        
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
            self.on_toggle_favorite(task)
        
        star_button.connect("clicked", toggle_favorite_handler)
        row.add_suffix(star_button)

        drop_target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        
        def on_drop(target, value, x, y):
            return self.on_task_reorder(value, task["id"])
        
        drop_target.connect("drop", on_drop)
        row.add_controller(drop_target)

        return row

    def refresh_sidebar(self):
        try:
            self.recreate_sidebar()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def recreate_sidebar(self):
        try:
            if hasattr(self, 'main_list_group'):
                while child := self.main_list_group.get_first_child():
                    self.main_list_group.remove(child)
                
                for list_id, list_name in self.task_manager.lists.items():
                    row = self.create_sidebar_row(list_id, list_name, is_project=False)
                    self.main_list_group.append(row)
            
            if hasattr(self, 'projects_list_group'):
                while child := self.projects_list_group.get_first_child():
                    self.projects_list_group.remove(child)
                
                for project in self.task_manager.projects:
                    project_id = f"project_{project.get('id', project['name'])}"
                    row = self.create_sidebar_row(project_id, project['name'], 
                                                is_project=True, color=project['color'])
                    self.projects_list_group.append(row)
            
            GLib.idle_add(self.select_current_list)
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def create_task_info_panel(self):
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

    def on_task_row_activated(self, listbox, row):
        task_id_str = row.get_name()
        if not task_id_str: 
            return
        task_id = int(task_id_str)

        found_task = None
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        for task in all_tasks:
            if task.get("id") == task_id:
                found_task = task
                break
        
        if found_task:
            self.on_task_row_clicked(found_task)

    def on_task_row_clicked(self, task):
        width = self.get_width()
        if width < 600:
            self.show_task_info_dialog(task)
        else:
            self.show_task_info_panel(task)

    def show_task_info_panel(self, task):
        self.current_task_info = task
        child = self.task_info_content.get_first_child()
        while child:
            self.task_info_content.remove(child)
            child = self.task_info_content.get_first_child()

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

        self.task_info_panel.set_size_request(400, -1)
        self.task_info_panel.set_hexpand(False)
        
        self.task_info_panel.set_visible(True)
        self.content_paned.set_end_child(self.task_info_panel)
        
        window_width = self.get_width()
        target_position = window_width - 400
        self.content_paned.set_position(target_position)

    def on_open_calendar(self, widget):
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
            except:
                pass
        
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

    def on_date_selected(self, calendar, dialog):
        if self.current_task_info:
            selected_date = calendar.get_date()
            date_obj = datetime.datetime(selected_date.get_year(), 
                                       selected_date.get_month(), 
                                       selected_date.get_day_of_month())
            
            self.current_task_info["effective_date"] = date_obj.isoformat()
            self.task_manager.save_tasks()
            
            self.date_label.set_text(date_obj.strftime("%d/%m/%Y"))
            
            self.refresh_task_list()
            self.refresh_sidebar()
        
        dialog.close()

    def on_today_selected(self, calendar, dialog):
        today = datetime.date.today()
        calendar.select_day(today)
        self.on_date_selected(calendar, dialog)

    def on_date_cleared(self, dialog):
        if self.current_task_info:
            today = datetime.datetime.now()
            self.current_task_info["effective_date"] = today.isoformat()
            self.task_manager.save_tasks()
            
            self.date_label.set_text(today.strftime("%d/%m/%Y"))
            
            self.refresh_task_list()
            self.refresh_sidebar()
        
        dialog.close()

    def on_project_changed_enhanced(self, row, param):
        if self.current_task_info:
            selected_idx = row.get_selected()
            model = row.get_model()
            
            if selected_idx < model.get_n_items():
                project_name = model.get_string(selected_idx)
                self.current_task_info["project"] = project_name
                self.task_manager.save_tasks()
                self.refresh_task_list()
                self.refresh_sidebar()

    def show_task_info_dialog(self, task):
        pass

    def on_close_task_info(self, button):
        self.task_info_panel.set_visible(False)
        self.current_task_info = None
        if hasattr(self, 'content_paned'):
            self.content_paned.set_end_child(None)

    def on_task_title_changed(self, row, param):
        if self.current_task_info:
            new_title = row.get_text()
            self.current_task_info["title"] = new_title
            self.task_manager.save_tasks()
            self.refresh_task_list()

    def on_task_notes_changed(self, buffer):
        if self.current_task_info:
            notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
            self.current_task_info["notes"] = notes
            self.task_manager.save_tasks()

    def on_task_completed_toggled(self, switch, param):
        if self.current_task_info and self.current_task_info["completed"] != switch.get_active():
            self.current_task_info["completed"] = switch.get_active()
            self.task_manager.save_tasks()
            self.refresh_task_list()
            self.refresh_sidebar()

    def on_delete_current_task(self):
        if self.current_task_info:
            task_to_delete_id = self.current_task_info.get('id')
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            original_count = len(all_tasks)
            self.task_manager.tasks["all_tasks"] = [t for t in all_tasks if t.get('id') != task_to_delete_id]
            
            if len(self.task_manager.tasks["all_tasks"]) < original_count:
                self.task_manager.save_tasks()
                self.refresh_task_list()
                self.refresh_sidebar()
                self.on_close_task_info(None)

    def on_task_toggle(self, task):
        task["completed"] = not task["completed"]
        self.task_manager.save_tasks()
        self.refresh_task_list()
        self.refresh_sidebar()

    def on_toggle_favorite(self, task):
        current_favorite = task.get("favorite", False)
        task["favorite"] = not current_favorite
        self.task_manager.save_tasks()
        self.refresh_task_list()
        self.refresh_sidebar()
        new_state = _("added to") if task["favorite"] else _("removed from")
        print(f"{_('Task')} '{task['title']}' {new_state} {_('favorites')}")

    def on_task_reorder(self, dragged_task_id, target_task_id):
        if dragged_task_id == target_task_id:
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
            return False
        
        current_tasks = self.task_manager.get_tasks(self.current_list)
        
        dragged_in_list = any(t.get("id") == dragged_task_id for t in current_tasks)
        target_in_list = any(t.get("id") == target_task_id for t in current_tasks)
        
        if not (dragged_in_list and target_in_list):
            return False
        
        target_order = target_task.get("sort_order", 0)
        dragged_task["sort_order"] = target_order
        
        for task in current_tasks:
            if task.get("id") != dragged_task_id and task.get("sort_order", 0) >= target_order:
                task["sort_order"] = task.get("sort_order", 0) + 1
        
        self.task_manager.save_tasks()
        self.refresh_task_list()
        return True

    def on_new_task_entry_activate(self, entry):
        text = entry.get_text().strip()
        if text:
            list_to_add = "today"
            # Determinar el proyecto basado en la lista actual
            if self.current_list.startswith("project_"):
                project_id = self.current_list.replace("project_", "")
                project = self.task_manager.get_project_by_id(project_id)
                project_name = project["name"] if project else _("Inbox")
            else:
                inbox_project = self.task_manager.get_inbox_project()
                project_name = inbox_project["name"] if inbox_project else _("Inbox")
            
            self.task_manager.add_task(list_to_add, text, project=project_name)
            entry.set_text("")
            self.refresh_task_list()
            self.refresh_sidebar()

    def on_add_project(self, button):
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
        
        # Definir lista de colores con orden de prioridad
        all_colors = [
            "purple", "orange", "blue", "green", "yellow", "red", "pink", "cyan", "teal", "lime",
            "amber", "indigo", "violet", "magenta", "olive", "gray", "brown", "gold", "silver",
            "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby", "lavender", "beige",
            "tan", "salmon", "plum", "khaki", "azure", "ivory", "crimson", "sienna", "chartreuse",
            "peru", "orchid", "aquamarine", "wheat", "slate", "mint", "peach", "chocolate", "fuchsia",
            "saffron", "cobalt", "bronze"
        ]
        
        # Obtener colores usados de proyectos existentes
        used_colors = {project["color"] for project in self.task_manager.projects}
        available_colors = [color for color in all_colors if color not in used_colors][:21]
        
        self.selected_color = available_colors[0] if available_colors else all_colors[0]  # Por defecto al primer disponible
        self.selected_color_button = None
        
        for i, color in enumerate(available_colors):
            button = Gtk.Button()
            button.add_css_class("color-button")
            button.add_css_class(f"color-{color}")
            button.set_hexpand(True)
            button.set_size_request(40, 40)  # Botones más pequeños
            if i == 0:  # Seleccionar primer botón por defecto
                button.add_css_class("selected-color")
                self.selected_color_button = button
            def on_color_clicked(btn, c=color, b=button):
                if self.selected_color_button:
                    self.selected_color_button.remove_css_class("selected-color")
                self.selected_color = c
                self.selected_color_button = b
                b.add_css_class("selected-color")
            button.connect("clicked", on_color_clicked)
            row = i // 7  # 3 filas, 7 columnas
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
                # Generar ID único para el proyecto
                project_id = name.lower().replace(" ", "_").replace("ã", "a")
                # Asegurar que el ID sea único
                existing_ids = {p.get("id") for p in self.task_manager.projects}
                original_id = project_id
                counter = 1
                while project_id in existing_ids:
                    project_id = f"{original_id}_{counter}"
                    counter += 1
                
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
        if hasattr(self, 'projects_list_group'):
            while child := self.projects_list_group.get_first_child():
                self.projects_list_group.remove(child)
            for project in self.task_manager.projects:
                project_id = f"project_{project.get('id', project['name'])}"
                row = self.create_sidebar_row(project_id, project['name'], 
                                            is_project=True, color=project['color'])
                self.projects_list_group.append(row)

    def on_delete_project(self, button):
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            if project_id != "inbox":  # No permitir eliminar el Inbox
                self.task_manager.delete_project(project_id)
                self.current_list = "today"  # Cambiar a una vista válida
                self.refresh_task_list()
                self.refresh_sidebar()

    def on_edit_project(self, button):
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project_to_edit = self.task_manager.get_project_by_id(project_id)
            if project_to_edit:
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
                    "maroon", "navy", "turquoise", "coral", "sky", "emerald", "ruby", "lavender", "beige",
                    "tan", "salmon", "plum", "khaki", "azure", "ivory", "crimson", "sienna", "chartreuse",
                    "peru", "orchid", "aquamarine", "wheat", "slate", "mint", "peach", "chocolate", "fuchsia",
                    "saffron", "cobalt", "bronze"
                ]
                
                # Obtener colores usados de proyectos existentes (excepto el actual)
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
                        # Actualizar nombre y color del proyecto
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
                
                save_btn.connect("clicked", save_project)
                button_box.append(save_btn)
                content.append(button_box)
                dialog.set_content(content)
                dialog.present()

    def setup_shortcuts(self):
        shortcuts = [("<Control>n", self.on_add_task_shortcut)]
        controller = Gtk.ShortcutController()
        for trigger, callback in shortcuts:
            shortcut = Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(trigger))
            action = Gtk.CallbackAction.new(callback)
            shortcut.set_action(action)
            controller.add_shortcut(shortcut)
        self.add_controller(controller)

    def on_add_task_shortcut(self, widget, args):
        if hasattr(self, 'new_task_entry'):
            self.new_task_entry.grab_focus()
        return True

    def setup_custom_css(self):
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
        
        /* Hover solo para filas que no son cabeceras de fecha */
        .boxed-list > row:not(.date-header-row):hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        
        /* Asegurar que las cabeceras de fecha NO tengan hover */
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
        .color-lavender { background-color: #E6E6FA; }
        .color-beige { background-color: #F5F5DC; }
        .color-tan { background-color: #D2B48C; }
        .color-salmon { background-color: #FA8072; }
        .color-plum { background-color: #DDA0DD; }
        .color-khaki { background-color: #F0E68C; }
        .color-azure { background-color: #F0FFFF; }
        .color-ivory { background-color: #FFFFF0; }
        .color-crimson { background-color: #DC143C; }
        .color-sienna { background-color: #A0522D; }
        .color-chartreuse { background-color: #7FFF00; }
        .color-peru { background-color: #CD853F; }
        .color-orchid { background-color: #DA70D6; }
        .color-aquamarine { background-color: #7FFFD4; }
        .color-wheat { background-color: #F5DEB3; }
        .color-slate { background-color: #708090; }
        .color-mint { background-color: #98FF98; }
        .color-peach { background-color: #FFDAB9; }
        .color-chocolate { background-color: #D2691E; }
        .color-fuchsia { background-color: #FF00FF; }
        .color-saffron { background-color: #F4C430; }
        .color-cobalt { background-color: #0047AB; }
        .color-bronze { background-color: #CD7F32; }
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
        .text-color-lavender { color: #E6E6FA; }
        .text-color-beige { color: #F5F5DC; }
        .text-color-tan { color: #D2B48C; }
        .text-color-salmon { color: #FA8072; }
        .text-color-plum { color: #DDA0DD; }
        .text-color-khaki { color: #F0E68C; }
        .text-color-azure { color: #F0FFFF; }
        .text-color-ivory { color: #FFFFF0; }
        .text-color-crimson { color: #DC143C; }
        .text-color-sienna { color: #A0522D; }
        .text-color-chartreuse { color: #7FFF00; }
        .text-color-peru { color: #CD853F; }
        .text-color-orchid { color: #DA70D6; }
        .text-color-aquamarine { color: #7FFFD4; }
        .text-color-wheat { color: #F5DEB3; }
        .text-color-slate { color: #708090; }
        .text-color-mint { color: #98FF98; }
        .text-color-peach { color: #FFDAB9; }
        .text-color-chocolate { color: #D2691E; }
        .text-color-fuchsia { color: #FF00FF; }
        .text-color-saffron { color: #F4C430; }
        .text-color-cobalt { color: #0047AB; }
        .text-color-bronze { color: #CD7F32; }
        .text-color-black { color: #000000; }
        """
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class TaskManagerApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.TaskManager",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self.on_activate)
        self.setup_actions()

    def setup_actions(self):
        # Acción de cambio de idioma
        language_action = Gio.SimpleAction.new_stateful(
            "language", GLib.VariantType.new("s"), GLib.Variant("s", "auto")
        )
        language_action.connect("activate", self.on_language_changed)
        self.add_action(language_action)

        # Acción de preferencias
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences)
        self.add_action(preferences_action)

        # Acción de acerca de
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

    def on_language_changed(self, action, parameter):
        """Cambiar idioma de la aplicación"""
        language_code = parameter.get_string()
        action.set_state(parameter)
        if hasattr(self, "win"):
            self.win.change_language(language_code)

    def on_preferences(self, action, parameter):
        """Mostrar ventana de preferencias"""
        if hasattr(self, "win"):
            self.show_preferences_dialog()

    def show_preferences_dialog(self):
        """Mostrar diálogo de preferencias"""
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
        self.win.change_theme(dark_theme)

    def on_language_row_changed(self, combo_row, param):
        """Manejar cambio en el selector de idioma"""
        selected = combo_row.get_selected()
        language_codes = ["auto", "en", "es"]
        if selected < len(language_codes):
            language_code = language_codes[selected]
            action = self.lookup_action("language")
            if action:
                action.activate(GLib.Variant("s", language_code))

    def on_about(self, action, parameter):
        """Mostrar diálogo Acerca de"""
        about_dialog = Adw.AboutWindow()
        about_dialog.set_transient_for(self.win)
        about_dialog.set_modal(True)
        about_dialog.set_application_name(_("Todo List"))
        about_dialog.set_version("1.0.0")
        about_dialog.set_developer_name("pabmartine")
        about_dialog.set_copyright("© 2025")
        about_dialog.set_comments(_("A simple and powerful task management application"))
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        about_dialog.set_developers(["pabmartine"])
        about_dialog.set_website("https://github.com/pabmartine/todo-list")
        about_dialog.present()

    def on_activate(self, app):
        """Se llama cuando se activa la aplicación"""
        self.win = TaskManagerWindow(application=app)
        self.win.present()


def main():
    """Función principal"""
    app = TaskManagerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()