import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw

from ..config import ConfigManager
from ..debug import debug, debug_method
from ..i18n import setup_locale, translate as _
from ..services.project_service import ProjectService
from ..services.task_service import TaskService as TaskManager
from .projects import ProjectMixin
from .sidebar import SidebarMixin
from .support import WindowAppearanceMixin, WindowDataActionsMixin, WindowLifecycleMixin
from .task_detail import TaskDetailMixin
from .task_list import TaskListMixin


class TaskManagerWindow(
    SidebarMixin,
    ProjectMixin,
    TaskDetailMixin,
    TaskListMixin,
    WindowAppearanceMixin,
    WindowDataActionsMixin,
    WindowLifecycleMixin,
    Adw.ApplicationWindow,
):
    def __init__(self, **kwargs):
        debug.log_event("WINDOW", "Starting window initialization")
        super().__init__(**kwargs)
        
        # Variables de estado con debug
        self.config = ConfigManager()
        self.task_manager = TaskManager()
        self.project_service = ProjectService(self.task_manager)
        self.current_language = self.config.get("language", "auto")
        self.current_list = self.config.get("current_list", "today")
        self.search_query = ""
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
        inbox_project = self.task_manager.ensure_inbox_project()
        if inbox_project:
            debug.log_event("WINDOW", "Inbox project ensured")

    def apply_saved_config(self):
        debug.log_event("WINDOW", "Applying saved configuration")
        saved_language = self.config.get("language", "auto")
        if saved_language != "auto":
            setup_locale(saved_language)
        dark_theme = self.config.get("dark_theme", False)
        self.apply_theme(dark_theme)

    def apply_theme(self, dark_theme):
        debug.log_event("WINDOW", f"Applying theme - dark: {dark_theme}")
        style_manager = Adw.StyleManager.get_default()
        if dark_theme:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def change_theme(self, dark_theme):
        """Cambiar tema de la aplicación"""
        debug.log_event("WINDOW", f"Changing theme to dark: {dark_theme}")
        self.apply_theme(dark_theme)
        self.config.set("dark_theme", dark_theme)

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

    def update_header_title(self):
        # Ya no necesitamos actualizar un título separado
        pass
