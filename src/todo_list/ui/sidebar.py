from gi.repository import Adw, Gio, GLib, Gtk

from ..core.debug import debug, debug_method
from ..core.i18n import translate as _, translate_plural as ngettext
from . import icons


# Smart list icons. The names resolve through icons.py, which keeps the
# original name and falls back to an Adwaita one when the theme lacks it.
SMART_LIST_ICON_KEYS = {
    "today": "list-today",
    "next7": "list-next7",
    "all": "list-all",
    "overdue": "list-overdue",
    "favorites": "list-favorites",
    "archived": "list-archived",
}


class SidebarMixin:
    @debug_method("create_sidebar")
    def create_sidebar(self):
        debug.log_event("UI", "Creating sidebar")

        self.sidebar_page = Adw.NavigationPage()
        self.sidebar_page.set_title(_("Lists"))
        self.sidebar_page.set_tag("sidebar")

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_header = Adw.HeaderBar()
        # The HIG places the primary menu above the sidebar list when a window
        # has a sidebar, rather than at the end of the content header bar: the
        # menu holds app-wide actions, and next to the window controls it reads
        # as a window control. It also keeps the menu on the top-level view
        # once the split view collapses and the sidebar becomes its own page.
        sidebar_header.pack_end(self._create_menu_button())
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

        projects_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        projects_header_box.set_margin_bottom(6)

        self.projects_label = Gtk.Label(label=_("Projects"), halign=Gtk.Align.START)
        self.projects_label.add_css_class("title-4")
        self.projects_label.set_hexpand(True)
        projects_header_box.append(self.projects_label)

        self.new_list_btn = Gtk.Button()
        self.new_list_btn.set_child(icons.image("add"))
        self.new_list_btn.add_css_class("flat")
        self.new_list_btn.set_tooltip_text(_("Add Project"))
        self.new_list_btn.update_property([Gtk.AccessibleProperty.LABEL], [_("Add Project")])
        self.new_list_btn.connect("clicked", self.on_add_project)
        projects_header_box.append(self.new_list_btn)

        content_box.append(projects_header_box)

        self.projects_list_group = Gtk.ListBox()
        self.projects_list_group.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.projects_list_group.add_css_class("navigation-sidebar")
        self.projects_list_group.connect("row-activated", self.on_list_selected)

        for project in self.task_manager.projects:
            project_id = f"project_{project.get('id', project['name'])}"
            row = self.create_sidebar_row(project_id, project["name"], is_project=True, color=project["color"])
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
                color_dot.add_css_class("color-black")
            elif color:
                color_dot.add_css_class(f"color-{color}")
            row.add_prefix(color_dot)
        else:
            row.add_prefix(icons.image(SMART_LIST_ICON_KEYS.get(list_id, "folder")))

        count = self.task_manager.get_task_count(list_id)
        count_label = Gtk.Label(label=str(count))
        count_label.add_css_class("dim-label")
        count_label.set_name(f"count_{list_id}")
        row.add_suffix(count_label)
        row.set_activatable(True)
        # A screen reader would otherwise read the bare number without saying
        # what it counts.
        row.update_property(
            [Gtk.AccessibleProperty.DESCRIPTION],
            [ngettext("{} task", "{} tasks", count).format(count)],
        )
        return row

    def select_current_list(self):
        debug.log_event("UI", f"Selecting current list: {self.current_list}")
        try:
            if self.current_list.startswith("project_"):
                child = self.projects_list_group.get_first_child()
                while child:
                    if hasattr(child, "get_name") and child.get_name() == self.current_list:
                        self.projects_list_group.select_row(child)
                        break
                    child = child.get_next_sibling()
            else:
                child = self.main_list_group.get_first_child()
                while child:
                    if hasattr(child, "get_name") and child.get_name() == self.current_list:
                        self.main_list_group.select_row(child)
                        break
                    child = child.get_next_sibling()
        except Exception as exc:
            debug.log_event("UI", f"Error selecting current list: {exc}")
        return False

    @debug_method("on_list_selected")
    def on_list_selected(self, listbox, row):
        if row is None:
            return

        list_id = row.get_name()
        if not list_id or list_id == self.current_list:
            return

        if self.is_project_selection_pending():
            self.show_toast(_("Please select a project for the task first"))
            self.highlight_project_requirement()
            GLib.idle_add(self.select_current_list)
            return

        self._cleanup_ui_state()

        if listbox == self.main_list_group:
            self.projects_list_group.unselect_all()
        else:
            self.main_list_group.unselect_all()

        self.current_list = list_id
        self.refresh_task_list()
        if hasattr(self, "refresh_kanban_board"):
            self.refresh_kanban_board()
        self.update_header_title()

        self.close_task_details()
        # On a collapsed split view the sidebar is a separate page, so move on
        # to the content once a list has been picked.
        if self.split_view.get_collapsed():
            self.split_view.set_show_content(True)

    @debug_method("create_main_area")
    def create_main_area(self):
        debug.log_event("UI", "Creating main area")

        self.content_page = Adw.NavigationPage()
        self.content_page.set_title(_("Todo List"))
        self.content_page.set_tag("content")

        self.content_toolbar = Adw.ToolbarView()
        # The primary menu lives above the sidebar list, see create_sidebar().
        content_header = Adw.HeaderBar()
        self.content_toolbar.add_top_bar(content_header)

        # Segmented view switcher buttons in content_header
        switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switcher_box.add_css_class("linked")

        self.list_view_btn = Gtk.ToggleButton()
        self.list_view_btn.set_icon_name(icons.name("view-list"))
        self.list_view_btn.set_tooltip_text(_("List view"))
        self.list_view_btn.update_property([Gtk.AccessibleProperty.LABEL], [_("List view")])
        self.list_view_btn.connect("toggled", self.on_view_switcher_toggled)

        self.kanban_view_btn = Gtk.ToggleButton()
        self.kanban_view_btn.set_group(self.list_view_btn)
        self.kanban_view_btn.set_icon_name(icons.name("view-kanban"))
        self.kanban_view_btn.set_tooltip_text(_("Kanban view"))
        self.kanban_view_btn.update_property([Gtk.AccessibleProperty.LABEL], [_("Kanban view")])
        self.kanban_view_btn.connect("toggled", self.on_view_switcher_toggled)

        switcher_box.append(self.list_view_btn)
        switcher_box.append(self.kanban_view_btn)
        content_header.set_title_widget(switcher_box)

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

        # The original stylesheet got this spacing by redefining Adwaita's
        # .title-1; widget margins achieve the same without touching a
        # platform class.
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_box.set_margin_top(8)
        title_box.set_margin_bottom(16)
        self.list_title_label = Gtk.Label()
        self.list_title_label.set_halign(Gtk.Align.START)
        self.list_title_label.add_css_class("title-1")
        self.list_title_label.set_hexpand(True)
        title_box.append(self.list_title_label)

        self.edit_button = Gtk.Button(icon_name="document-edit-symbolic")
        self.edit_button.add_css_class("flat")
        self.edit_button.set_tooltip_text(_("Edit project"))
        self.edit_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Edit project")])
        self.edit_button.connect("clicked", self.on_edit_project)
        self.edit_button.set_visible(False)
        title_box.append(self.edit_button)

        self.delete_button = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_button.add_css_class("flat")
        self.delete_button.set_tooltip_text(_("Delete project"))
        self.delete_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Delete project")])
        self.delete_button.connect("clicked", self.on_delete_project)
        self.delete_button.set_visible(False)
        title_box.append(self.delete_button)

        self.clear_archived_button = Gtk.Button(icon_name="list-remove-all-symbolic")
        self.clear_archived_button.add_css_class("flat")
        self.clear_archived_button.set_tooltip_text(_("Clear all archived tasks"))
        self.clear_archived_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("Clear all archived tasks")]
        )
        self.clear_archived_button.connect("clicked", self.on_clear_archived_tasks)
        self.clear_archived_button.set_visible(False)
        title_box.append(self.clear_archived_button)

        self.sort_button = Gtk.Button()
        self.sort_button.add_css_class("flat")
        self.sort_button.connect("clicked", self.on_sort_toggle)
        self.update_sort_button()
        title_box.append(self.sort_button)
        content_box.append(title_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text=_("Search tasks..."))
        # No set_key_capture_widget(): key capture runs in the capture phase, so
        # it swallowed typing meant for the always visible "new task" entry.
        self.search_entry.connect("search-changed", self.on_search_changed)
        content_box.append(self.search_entry)

        content_box.append(self._task_area())

        self.new_task_entry = Gtk.Entry(placeholder_text=_("New task..."))
        self.new_task_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, icons.name("add"))
        self.new_task_entry.connect("activate", self.on_new_task_entry_activate)
        self.new_task_entry.update_property([Gtk.AccessibleProperty.LABEL], [_("New task")])
        content_box.append(self.new_task_entry)

        self.kanban_area = self.create_kanban_area()

        self.view_stack = Gtk.Stack()
        self.view_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.view_stack.add_named(self.main_area, "list")
        self.view_stack.add_named(self.kanban_area, "kanban")

        initial_view = getattr(self, "current_view", "list")
        if initial_view == "kanban":
            self.kanban_view_btn.set_active(True)
            self.view_stack.set_visible_child_name("kanban")
        else:
            self.list_view_btn.set_active(True)
            self.view_stack.set_visible_child_name("list")

        self.content_toolbar.set_content(self.view_stack)
        # The page's child is set by setup_ui(), which wraps this toolbar in the
        # details overlay split view. Parenting it here would make
        # AdwOverlaySplitView.set_content() fail.
        debug.log_event("UI", "Main area created successfully")

    def _task_area(self):
        """The task list, plus a placeholder shown when there is nothing to list."""
        self.task_list = Gtk.ListBox()
        self.task_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.task_list.add_css_class("task-list")
        self.task_list.connect("row-activated", self.on_task_row_activated)

        self.task_list_scrolled = Gtk.ScrolledWindow()
        self.task_list_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.task_list_scrolled.set_vexpand(True)
        self.task_list_scrolled.set_propagate_natural_height(True)
        self.task_list_scrolled.set_child(self.task_list)

        self.empty_state = Adw.StatusPage(
            title=_("No Tasks"),
            description=_("Tasks you add appear here."),
        )
        self.empty_state.set_icon_name(icons.name("list-archived"))

        self.task_area_stack = Gtk.Stack()
        self.task_area_stack.add_named(self.task_list_scrolled, "tasks")
        self.task_area_stack.add_named(self.empty_state, "empty")
        self.task_area_stack.set_vexpand(True)
        return self.task_area_stack

    def _create_menu_button(self):
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_button.set_tooltip_text(_("Main Menu"))
        menu_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Main Menu")])
        self.menu_model = Gio.Menu()
        self.populate_menu_model()
        menu_button.set_menu_model(self.menu_model)
        return menu_button

    def populate_menu_model(self):
        """(Re)build the primary menu.

        Language is not repeated here: it already lives in Preferences, and the
        HIG lists Keyboard Shortcuts and About as standard primary menu items.
        """
        self.menu_model.remove_all()

        data_section = Gio.Menu()
        data_section.append(_("Import…"), "app.import")
        data_section.append(_("Export…"), "app.export")
        self.menu_model.append_section(None, data_section)

        app_section = Gio.Menu()
        app_section.append(_("Preferences"), "app.preferences")
        app_section.append(_("Keyboard Shortcuts"), "app.shortcuts")
        app_section.append(_("About Todo List"), "app.about")
        self.menu_model.append_section(None, app_section)

    def update_sort_button(self):
        if self.sort_ascending:
            self.sort_button.set_icon_name("view-sort-ascending-symbolic")
            label = _("Sort by date: oldest first")
        else:
            self.sort_button.set_icon_name("view-sort-descending-symbolic")
            label = _("Sort by date: newest first")
        self.sort_button.set_tooltip_text(label)
        self.sort_button.update_property([Gtk.AccessibleProperty.LABEL], [label])

    @debug_method("on_sort_toggle")
    def on_sort_toggle(self, button):
        self.sort_ascending = not self.sort_ascending
        self.update_sort_button()
        self.refresh_task_list()
        if hasattr(self, "refresh_kanban_board"):
            self.refresh_kanban_board()

    def on_search_changed(self, entry):
        self.search_query = entry.get_text().strip()
        if (
            hasattr(self, "kanban_search_entry")
            and self.kanban_search_entry.get_text().strip() != self.search_query
        ):
            self.kanban_search_entry.set_text(self.search_query)
        self.refresh_task_list()
        if hasattr(self, "refresh_kanban_board"):
            self.refresh_kanban_board()

    def start_search(self):
        """Focus the search entry (Ctrl+F)."""
        if getattr(self, "current_view", "list") == "kanban" and hasattr(self, "kanban_search_entry"):
            self.kanban_search_entry.grab_focus()
        elif hasattr(self, "search_entry"):
            self.search_entry.grab_focus()

    def on_view_switcher_toggled(self, button):
        if not button.get_active():
            return
        if button == getattr(self, "list_view_btn", None):
            self.set_active_view("list")
        elif button == getattr(self, "kanban_view_btn", None):
            self.set_active_view("kanban")

    def set_active_view(self, view_name):
        self.current_view = view_name
        if hasattr(self, "config"):
            self.config.set("current_view", view_name)
        if hasattr(self, "view_stack"):
            self.view_stack.set_visible_child_name(view_name)
        if view_name == "list":
            if hasattr(self, "list_view_btn") and not self.list_view_btn.get_active():
                self.list_view_btn.set_active(True)
            self.refresh_task_list()
        else:
            if hasattr(self, "kanban_view_btn") and not self.kanban_view_btn.get_active():
                self.kanban_view_btn.set_active(True)
            if hasattr(self, "refresh_kanban_board"):
                self.refresh_kanban_board()

    @debug_method("refresh_sidebar")
    def refresh_sidebar(self):
        try:
            if hasattr(self, "_refreshing_sidebar") and self._refreshing_sidebar:
                return
            self._refreshing_sidebar = True
            self.recreate_sidebar()
        except Exception as exc:
            debug.log_event("SIDEBAR", f"Error in refresh_sidebar: {exc}", stack_info=True)
        finally:
            self._refreshing_sidebar = False

    @debug_method("recreate_sidebar")
    def recreate_sidebar(self):
        try:
            if hasattr(self, "main_list_group") and self.main_list_group:
                while child := self.main_list_group.get_first_child():
                    self.main_list_group.remove(child)
                for list_id, list_name in self.task_manager.lists.items():
                    self.main_list_group.append(self.create_sidebar_row(list_id, list_name, is_project=False))

            self.refresh_sidebar_projects()
            GLib.idle_add(self.select_current_list)
        except Exception as exc:
            debug.log_event("SIDEBAR", f"Error in recreate_sidebar: {exc}", stack_info=True)

    def refresh_sidebar_projects(self):
        debug.log_event("SIDEBAR", "Refreshing sidebar projects only")
        if not hasattr(self, "projects_list_group"):
            return

        while child := self.projects_list_group.get_first_child():
            self.projects_list_group.remove(child)
        for project in self.task_manager.projects:
            project_id = f"project_{project.get('id', project['name'])}"
            row = self.create_sidebar_row(project_id, project["name"], is_project=True, color=project["color"])
            self.projects_list_group.append(row)
