from gi.repository import Adw, Gio, GLib, Gtk

from ..core.debug import debug, debug_method
from ..core.i18n import translate as _


class SidebarMixin:
    @debug_method("create_sidebar")
    def create_sidebar(self):
        debug.log_event("UI", "Creating sidebar")

        self.sidebar_page = Adw.NavigationPage()
        self.sidebar_page.set_title(_("Lists"))
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

        projects_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        projects_header_box.set_margin_bottom(6)

        self.projects_label = Gtk.Label(label=_("Projects"), halign=Gtk.Align.START)
        self.projects_label.add_css_class("title-4")
        self.projects_label.set_hexpand(True)
        projects_header_box.append(self.projects_label)

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
                "archived": "archive-symbolic",
            }
            icon = Gtk.Image.new_from_icon_name(icon_name_map.get(list_id, "folder-symbolic"))
            row.add_prefix(icon)

        count_label = Gtk.Label(label=str(self.task_manager.get_task_count(list_id)))
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

        self._cleanup_ui_state()

        if listbox == self.main_list_group:
            self.projects_list_group.unselect_all()
        else:
            self.main_list_group.unselect_all()

        self.current_list = list_id
        self.refresh_task_list()
        self.update_header_title()

        if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
            self.on_close_task_info(None)

    @debug_method("create_main_area")
    def create_main_area(self):
        debug.log_event("UI", "Creating main area")

        self.content_page = Adw.NavigationPage()
        self.content_page.set_title(_("Todo List"))
        self.content_page.set_tag("content")

        content_toolbar = Adw.ToolbarView()
        content_header = Adw.HeaderBar()

        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self.menu_model = Gio.Menu()

        language_menu = Gio.Menu()
        language_menu.append(_("Auto-detect"), "app.language::auto")
        language_menu.append(_("English"), "app.language::en")
        language_menu.append(_("Spanish"), "app.language::es")
        self.menu_model.append_submenu(_("Language"), language_menu)

        main_section = Gio.Menu()
        main_section.append(_("Import"), "app.import")
        main_section.append(_("Export"), "app.export")
        main_section.append(_("Preferences"), "app.preferences")
        main_section.append(_("About"), "app.about")
        self.menu_model.append_section(None, main_section)

        menu_button.set_menu_model(self.menu_model)
        content_header.pack_end(menu_button)
        content_toolbar.add_top_bar(content_header)

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

        self.edit_button = Gtk.Button(icon_name="text-editor-symbolic")
        self.edit_button.add_css_class("flat")
        self.edit_button.connect("clicked", self.on_edit_project)
        self.edit_button.set_visible(False)
        title_box.append(self.edit_button)

        self.delete_button = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_button.add_css_class("flat")
        self.delete_button.connect("clicked", self.on_delete_project)
        self.delete_button.set_visible(False)
        title_box.append(self.delete_button)

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

        self.search_entry = Gtk.SearchEntry(placeholder_text=_("Search tasks..."))
        self.search_entry.set_key_capture_widget(self)
        self.search_entry.connect("search-changed", self.on_search_changed)
        content_box.append(self.search_entry)

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
        self.sort_ascending = not self.sort_ascending
        self.update_sort_button()
        self.refresh_task_list()

    def on_search_changed(self, entry):
        self.search_query = entry.get_text().strip()
        self.refresh_task_list()

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

            if hasattr(self, "projects_list_group") and self.projects_list_group:
                while child := self.projects_list_group.get_first_child():
                    self.projects_list_group.remove(child)
                for project in self.task_manager.projects:
                    project_id = f"project_{project.get('id', project['name'])}"
                    self.projects_list_group.append(
                        self.create_sidebar_row(project_id, project["name"], is_project=True, color=project["color"])
                    )

            GLib.idle_add(self.select_current_list)
        except Exception as exc:
            debug.log_event("SIDEBAR", f"Error in recreate_sidebar: {exc}", stack_info=True)

    def refresh_sidebar_projects(self):
        debug.log_event("SIDEBAR", "Refreshing sidebar projects only")
        if hasattr(self, "projects_list_group"):
            while child := self.projects_list_group.get_first_child():
                self.projects_list_group.remove(child)
            for project in self.task_manager.projects:
                project_id = f"project_{project.get('id', project['name'])}"
                row = self.create_sidebar_row(project_id, project["name"], is_project=True, color=project["color"])
                self.projects_list_group.append(row)
