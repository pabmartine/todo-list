from gi.repository import Adw, Gtk

from ..core.constants import PROJECT_COLORS
from ..core.debug import debug, debug_method
from ..core.i18n import translate as _


class ProjectMixin:
    @debug_method("on_add_project")
    def on_add_project(self, button):
        debug.log_event("ADD_PROJECT", "Opening add project dialog")

        dialog = Adw.Window(title=_("Add project"), transient_for=self, modal=True, default_width=400)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )
        title_label = Gtk.Label(label=_("Create new project"), halign=Gtk.Align.START)
        title_label.add_css_class("title-2")
        content.append(title_label)

        name_group = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title=_("Name"))
        name_group.add(name_row)
        content.append(name_group)

        color_group = self._build_project_color_group(PROJECT_COLORS[:-1], set(project["color"] for project in self.task_manager.projects))
        content.append(color_group)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, halign=Gtk.Align.END, margin_top=12)
        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.connect("clicked", lambda b: dialog.close())
        button_box.append(cancel_btn)
        create_btn = Gtk.Button(label=_("Create"), halign=Gtk.Align.END)
        create_btn.add_css_class("suggested-action")

        def create_project(btn):
            name = name_row.get_text().strip()
            color = self.selected_color
            if name and not any(project["name"] == name for project in self.task_manager.projects):
                new_project = self.project_service.create_project(name, color)
                debug.log_event("ADD_PROJECT", f"Creating project: {name} with ID: {new_project['id']} and color: {color}")
                self.refresh_sidebar_projects()
                dialog.close()

        create_btn.connect("clicked", create_project)
        button_box.append(create_btn)
        content.append(button_box)
        dialog.set_content(content)
        dialog.present()

    @debug_method("on_delete_project")
    def on_delete_project(self, button):
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            if project_id != "inbox" and self.project_service.delete_project(project_id):
                self.current_list = "today"
                self.refresh_task_list()
                self.refresh_sidebar()

    @debug_method("on_edit_project")
    def on_edit_project(self, button):
        if not self.current_list.startswith("project_"):
            return

        project_id = self.current_list.replace("project_", "")
        project_to_edit = self.task_manager.get_project_by_id(project_id)
        if not project_to_edit:
            debug.log_event("EDIT_PROJECT", f"Project with ID {project_id} not found")
            return

        dialog = Adw.Window(title=_("Edit project"), transient_for=self, modal=True, default_width=400)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )
        title_label = Gtk.Label(label=_("Edit project"), halign=Gtk.Align.START)
        title_label.add_css_class("title-2")
        content.append(title_label)

        name_group = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title=_("Name"))
        name_row.set_text(project_to_edit["name"])
        name_group.add(name_row)
        content.append(name_group)

        used_colors = {project["color"] for project in self.task_manager.projects if project.get("id") != project_id}
        color_group = self._build_project_color_group(PROJECT_COLORS[:-1], used_colors, current_color=project_to_edit["color"])
        content.append(color_group)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, halign=Gtk.Align.END, margin_top=12)
        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.connect("clicked", lambda b: dialog.close())
        button_box.append(cancel_btn)
        save_btn = Gtk.Button(label=_("Save"), halign=Gtk.Align.End)
        save_btn.add_css_class("suggested-action")

        def save_project(btn):
            new_name = name_row.get_text().strip()
            inbox_project = self.task_manager.get_inbox_project()
            inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
            duplicate = any(project["name"] == new_name for project in self.task_manager.projects if project.get("id") != project_id)
            if new_name and new_name != inbox_name and not duplicate:
                if self.project_service.update_project(project_id, new_name, self.selected_color):
                    self.refresh_task_list()
                    self.refresh_sidebar()
                    dialog.close()

        save_btn.connect("clicked", save_project)
        button_box.append(save_btn)
        content.append(button_box)
        dialog.set_content(content)
        dialog.present()

    def _build_project_color_group(self, all_colors, used_colors, current_color=None):
        color_group = Adw.PreferencesGroup(title=_("Color"))
        color_grid = Gtk.Grid()
        color_grid.set_column_spacing(10)
        color_grid.set_row_spacing(10)
        color_grid.set_margin_top(10)
        color_grid.set_margin_bottom(10)
        color_grid.set_hexpand(True)

        available_colors = [color for color in all_colors if color not in used_colors][:21]
        if current_color and current_color not in available_colors:
            available_colors.append(current_color)

        self.selected_color = current_color or (available_colors[0] if available_colors else all_colors[0])
        self.selected_color_button = None

        for index, color in enumerate(available_colors):
            button = Gtk.Button()
            button.add_css_class("color-button")
            button.add_css_class(f"color-{color}")
            button.set_hexpand(True)
            button.set_size_request(40, 40)
            if color == self.selected_color:
                button.add_css_class("selected-color")
                self.selected_color_button = button

            def on_color_clicked(btn, c=color, b=button):
                if self.selected_color_button:
                    self.selected_color_button.remove_css_class("selected-color")
                self.selected_color = c
                self.selected_color_button = b
                b.add_css_class("selected-color")

            button.connect("clicked", on_color_clicked)
            row = index // 7
            col = index % 7
            color_grid.attach(button, col, row, 1, 1)

        color_group.add(color_grid)
        return color_group
