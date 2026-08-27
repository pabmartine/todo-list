from gi.repository import Adw, Gtk

from ..core.constants import PROJECT_COLORS
from ..core.debug import debug, debug_method
from ..core.i18n import translate as _


def _color_label(color):
    """Human readable, translatable name for a project colour.

    The literals have to appear in the source for xgettext to pick them up, so
    the table is built on each call rather than at import time (which would run
    before the locale is set up).
    """
    labels = {
        "purple": _("Purple"),
        "orange": _("Orange"),
        "blue": _("Blue"),
        "green": _("Green"),
        "yellow": _("Yellow"),
        "red": _("Red"),
        "pink": _("Pink"),
        "cyan": _("Cyan"),
        "teal": _("Teal"),
        "lime": _("Lime"),
        "amber": _("Amber"),
        "indigo": _("Indigo"),
        "violet": _("Violet"),
        "magenta": _("Magenta"),
        "olive": _("Olive"),
        "gray": _("Gray"),
        "brown": _("Brown"),
        "gold": _("Gold"),
        "silver": _("Silver"),
        "maroon": _("Maroon"),
        "navy": _("Navy"),
        "turquoise": _("Turquoise"),
        "coral": _("Coral"),
        "sky": _("Sky"),
        "emerald": _("Emerald"),
        "ruby": _("Ruby"),
    }
    return labels.get(color, color.capitalize())


class ProjectMixin:
    @debug_method("on_add_project")
    def on_add_project(self, button):
        debug.log_event("ADD_PROJECT", "Opening add project dialog")

        used_colors = {project["color"] for project in self.task_manager.projects}
        self._present_project_dialog(
            heading=_("New Project"),
            accept_label=_("Create"),
            name="",
            used_colors=used_colors,
            current_color=None,
            on_accept=self._create_project,
        )

    @debug_method("on_edit_project")
    def on_edit_project(self, button):
        if not self.current_list.startswith("project_"):
            return

        project_id = self.current_list.replace("project_", "")
        project = self.task_manager.get_project_by_id(project_id)
        if not project:
            debug.log_event("EDIT_PROJECT", f"Project with ID {project_id} not found")
            return

        used_colors = {p["color"] for p in self.task_manager.projects if p.get("id") != project_id}
        self._present_project_dialog(
            heading=_("Edit Project"),
            accept_label=_("Save"),
            name=project["name"],
            used_colors=used_colors,
            current_color=project["color"],
            on_accept=lambda name, color: self._save_project(project_id, name, color),
        )

    def _present_project_dialog(self, heading, accept_label, name, used_colors, current_color, on_accept):
        """Show an AdwDialog whose actions live in its header bar, per the HIG."""
        dialog = Adw.Dialog(title=heading, content_width=400)

        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_button)

        accept_button = Gtk.Button(label=accept_label)
        accept_button.add_css_class("suggested-action")
        header.pack_end(accept_button)

        name_group = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title=_("Name"))
        name_row.set_text(name)
        name_group.add(name_row)

        color_group, get_color = self._build_project_color_group(used_colors, current_color)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            margin_top=12,
            margin_bottom=18,
            margin_start=12,
            margin_end=12,
        )
        content.append(name_group)
        content.append(color_group)

        def validate(*_args):
            """Keep the accept button insensitive while the name is unusable,
            instead of silently doing nothing when it is pressed."""
            candidate = name_row.get_text().strip()
            duplicate = candidate.casefold() in {
                p["name"].casefold()
                for p in self.task_manager.projects
                if p["name"].casefold() != name.casefold()
            }
            valid = bool(candidate) and not duplicate
            accept_button.set_sensitive(valid)
            if duplicate:
                name_row.add_css_class("error")
                name_row.set_tooltip_text(_("A project with this name already exists"))
            else:
                name_row.remove_css_class("error")
                name_row.set_tooltip_text(None)

        name_row.connect("notify::text", validate)
        validate()

        def accept(_button=None):
            if not accept_button.get_sensitive():
                return
            if on_accept(name_row.get_text().strip(), get_color()):
                dialog.close()

        accept_button.connect("clicked", accept)
        name_row.connect("entry-activated", lambda row: accept())

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        dialog.set_child(toolbar)
        dialog.set_default_widget(accept_button)
        dialog.set_focus(name_row)
        dialog.present(self)

    def _create_project(self, name, color):
        if not name or any(p["name"].casefold() == name.casefold() for p in self.task_manager.projects):
            return False

        new_project = self.project_service.create_project(name, color)
        debug.log_event("ADD_PROJECT", f"Created project {new_project['id']} ({name}, {color})")
        self.refresh_sidebar_projects()
        self.show_toast(_("Project “{}” created").format(name))
        return True

    def _save_project(self, project_id, name, color):
        inbox_project = self.task_manager.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        duplicate = any(
            p["name"].casefold() == name.casefold()
            for p in self.task_manager.projects
            if p.get("id") != project_id
        )
        if not name or name == inbox_name or duplicate:
            return False

        if not self.project_service.update_project(project_id, name, color):
            return False

        self.refresh_task_list()
        self.refresh_sidebar()
        return True

    @debug_method("on_delete_project")
    def on_delete_project(self, button):
        """Ask before deleting: this reassigns every task in the project."""
        if not self.current_list.startswith("project_"):
            return

        project_id = self.current_list.replace("project_", "")
        if project_id == "inbox":
            return

        project = self.task_manager.get_project_by_id(project_id)
        if not project:
            return

        inbox_project = self.task_manager.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        task_count = self.task_manager.get_task_count(self.current_list)

        dialog = Adw.AlertDialog.new(
            _("Delete Project “{}”?").format(project["name"]),
            _("Its {count} tasks will be moved to {inbox}.").format(count=task_count, inbox=inbox_name)
            if task_count
            else _("The project has no tasks."),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_project_response, project_id, project["name"])
        dialog.present(self)

    def _on_delete_project_response(self, dialog, response, project_id, project_name):
        if response != "delete":
            return

        if self.project_service.delete_project(project_id):
            self.current_list = "today"
            self.close_task_details()
            self.refresh_task_list()
            self.refresh_sidebar()
            self.show_toast(_("Project “{}” deleted").format(project_name))

    def _build_project_color_group(self, used_colors, current_color=None):
        """Colour picker laid out as a grid of swatches.

        The swatches are a real radio group of toggle buttons rather than plain
        buttons with a CSS class toggled by hand, so the selection is reachable
        with the keyboard and exposed to assistive technologies. A colour on its
        own carries no accessible name, hence the label on each swatch.
        """
        color_group = Adw.PreferencesGroup(title=_("Color"))
        color_grid = Gtk.Grid()
        color_grid.set_column_spacing(10)
        color_grid.set_row_spacing(10)
        color_grid.set_margin_top(10)
        color_grid.set_margin_bottom(10)
        color_grid.set_hexpand(True)

        selectable = [color for color in PROJECT_COLORS if color != "black"]
        available_colors = [color for color in selectable if color not in used_colors][:21]
        if current_color and current_color not in available_colors:
            available_colors.append(current_color)
        if not available_colors:
            available_colors = selectable[:21]

        selected = {"color": current_color or available_colors[0]}
        first_button = None

        for index, color in enumerate(available_colors):
            button = Gtk.ToggleButton()
            button.add_css_class("color-button")
            button.add_css_class(f"color-{color}")
            button.set_hexpand(True)
            button.set_size_request(40, 40)

            label = _color_label(color)
            button.set_tooltip_text(label)
            button.update_property([Gtk.AccessibleProperty.LABEL], [label])

            if first_button is None:
                first_button = button
            else:
                button.set_group(first_button)
            button.set_active(color == selected["color"])

            def on_toggled(btn, c=color):
                if btn.get_active():
                    selected["color"] = c

            button.connect("toggled", on_toggled)
            color_grid.attach(button, index % 7, index // 7, 1, 1)

        color_group.add(color_grid)
        return color_group, lambda: selected["color"]
