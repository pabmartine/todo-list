import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from ..core.config import ConfigManager
from ..core.debug import debug, debug_method
from ..core.i18n import setup_locale, translate as _
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
        # The HIG asks apps to keep working down to 360x294 logical pixels.
        self.set_size_request(360, 294)

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
        self.apply_color_scheme(self.get_color_scheme())

    def get_color_scheme(self):
        """Return the stored colour scheme, migrating the old boolean setting."""
        scheme = self.config.get("color_scheme")
        if scheme in ("default", "light", "dark"):
            return scheme
        return "dark" if self.config.get("dark_theme", False) else "default"

    def apply_color_scheme(self, scheme):
        """Follow the system preference unless the user overrides it.

        The previous boolean switch mapped "off" to ColorScheme.DEFAULT, so with
        the switch off and the desktop in dark mode the app stayed dark and the
        switch contradicted what was on screen.
        """
        debug.log_event("WINDOW", f"Applying colour scheme: {scheme}")
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(
            {
                "light": Adw.ColorScheme.FORCE_LIGHT,
                "dark": Adw.ColorScheme.FORCE_DARK,
            }.get(scheme, Adw.ColorScheme.DEFAULT)
        )

    def change_color_scheme(self, scheme):
        """Cambiar el esquema de color de la aplicación"""
        debug.log_event("WINDOW", f"Changing colour scheme to: {scheme}")
        self.apply_color_scheme(scheme)
        self.config.set("color_scheme", scheme)

    def show_toast(self, toast):
        """Show transient feedback. Accepts a string or a ready-made AdwToast."""
        if isinstance(toast, str):
            toast = Adw.Toast.new(toast)
        self.toast_overlay.add_toast(toast)

    @debug_method("setup_ui")
    def setup_ui(self):
        debug.log_event("UI", "Setting up main UI")

        # NavigationSplitView principal
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_sidebar_width_fraction(0.33)
        self.split_view.set_min_sidebar_width(280)
        self.split_view.set_max_sidebar_width(350)

        # Crear componentes
        self.create_sidebar()
        self.create_main_area()

        # The details panel is the end sidebar of an overlay split view, so
        # libadwaita decides whether to show it beside or over the content
        # instead of the previous manual Gtk.Paned plus width checks.
        self.detail_split = Adw.OverlaySplitView()
        self.detail_split.set_sidebar_position(Gtk.PackType.END)
        self.detail_split.set_min_sidebar_width(320)
        self.detail_split.set_max_sidebar_width(400)
        self.detail_split.set_sidebar_width_fraction(0.35)
        self.detail_split.set_show_sidebar(False)
        self.detail_split.set_content(self.content_toolbar)
        self.detail_split.set_sidebar(self.create_task_info_panel())

        self.content_page.set_child(self.detail_split)

        # Configurar split view
        self.split_view.set_sidebar(self.sidebar_page)
        self.split_view.set_content(self.content_page)

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.split_view)
        self.set_content(self.toast_overlay)

        self.setup_breakpoints()
        self.refresh_task_list()
        debug.log_event("UI", "Main UI setup completed")

    def setup_breakpoints(self):
        """Drive the adaptive layout from breakpoints instead of pixel checks.

        `sp` units follow the user's text scaling factor, which the previous
        `self.get_width() < 600` comparisons ignored; those also never
        re-evaluated when the window was resized.
        """
        # Only one breakpoint applies at a time: AdwBreakpointBin uses the last
        # added one whose condition matches, not every matching one. So the
        # conditions are mutually exclusive and the narrower breakpoint repeats
        # the setters of the wider one.
        medium_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("min-width: 601sp and max-width: 900sp")
        )
        medium_bp.add_setter(self.detail_split, "collapsed", True)
        self.add_breakpoint(medium_bp)

        narrow_bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 600sp"))
        narrow_bp.add_setter(self.detail_split, "collapsed", True)
        narrow_bp.add_setter(self.split_view, "collapsed", True)
        self.add_breakpoint(narrow_bp)

    def update_header_title(self):
        # El título de la vista se pinta en el área de contenido
        pass
