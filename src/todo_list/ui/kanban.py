import datetime
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk

from ..core.debug import debug, debug_method
from ..core.i18n import translate as _
from . import icons


class KanbanMixin:
    """Provides the 3-column interactive Kanban board view and its cards."""

    @debug_method("create_kanban_area")
    def create_kanban_area(self):
        debug.log_event("KANBAN", "Creating kanban area")

        self.kanban_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.kanban_area.add_css_class("kanban-board-wrapper")
        self.kanban_area.set_hexpand(True)
        self.kanban_area.set_vexpand(True)

        # Title and project action buttons
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box.set_margin_top(8)
        title_box.set_margin_bottom(8)

        self.kanban_title_label = Gtk.Label()
        self.kanban_title_label.set_halign(Gtk.Align.START)
        self.kanban_title_label.add_css_class("title-1")
        self.kanban_title_label.set_hexpand(True)
        title_box.append(self.kanban_title_label)

        self.kanban_edit_button = Gtk.Button(icon_name="document-edit-symbolic")
        self.kanban_edit_button.add_css_class("flat")
        self.kanban_edit_button.set_tooltip_text(_("Edit project"))
        self.kanban_edit_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Edit project")])
        self.kanban_edit_button.connect("clicked", self.on_edit_project)
        self.kanban_edit_button.set_visible(False)
        title_box.append(self.kanban_edit_button)

        self.kanban_delete_button = Gtk.Button(icon_name="user-trash-symbolic")
        self.kanban_delete_button.add_css_class("flat")
        self.kanban_delete_button.set_tooltip_text(_("Delete project"))
        self.kanban_delete_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Delete project")])
        self.kanban_delete_button.connect("clicked", self.on_delete_project)
        self.kanban_delete_button.set_visible(False)
        title_box.append(self.kanban_delete_button)

        self.kanban_area.append(title_box)

        # Search bar
        self.kanban_search_entry = Gtk.SearchEntry(placeholder_text=_("Search tasks..."))
        self.kanban_search_entry.connect("search-changed", self.on_kanban_search_changed)
        self.kanban_area.append(self.kanban_search_entry)

        # Board container with horizontal scrolling
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self.kanban_board_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.kanban_board_box.set_homogeneous(True)
        self.kanban_board_box.set_hexpand(True)
        self.kanban_board_box.set_vexpand(True)
        self.kanban_board_box.set_margin_top(8)

        self.kanban_columns = {}
        column_defs = [
            ("pending", _("Pending"), "kanban-pending", "kanban-badge-pending"),
            ("in_progress", _("In progress"), "kanban-progress", "kanban-badge-progress"),
            ("completed", _("Completed"), "kanban-completed", "kanban-badge-completed"),
        ]

        for col_id, col_title, icon_key, badge_class in column_defs:
            col_box = self._create_kanban_column(col_id, col_title, icon_key, badge_class)
            self.kanban_board_box.append(col_box)

        scrolled.set_child(self.kanban_board_box)
        self.kanban_area.append(scrolled)
        return self.kanban_area

    def _create_kanban_column(self, col_id, col_title, icon_key, badge_class):
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        column.add_css_class("kanban-column")
        column.set_hexpand(True)
        column.set_vexpand(True)
        column.set_size_request(260, -1)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("kanban-column-header")

        icon = icons.image(icon_key)
        header.append(icon)

        title_lbl = Gtk.Label(label=col_title)
        title_lbl.add_css_class("kanban-column-title")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_hexpand(True)
        header.append(title_lbl)

        badge = Gtk.Label(label="0")
        badge.add_css_class("kanban-badge")
        badge.add_css_class(badge_class)
        header.append(badge)

        column.append(header)

        # Quick add entry for "pending" column
        if col_id == "pending":
            quick_add = Gtk.Entry(placeholder_text=_("New task..."))
            quick_add.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, icons.name("add"))
            quick_add.connect("activate", self.on_kanban_new_task_activate)
            quick_add.update_property([Gtk.AccessibleProperty.LABEL], [_("New task")])
            quick_add.set_margin_bottom(4)
            column.append(quick_add)
            self.kanban_quick_add_entry = quick_add

        # Scrolled list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("kanban-card-list")

        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        placeholder.add_css_class("kanban-empty-placeholder")
        empty_lbl = Gtk.Label(label=_("No tasks"))
        empty_lbl.add_css_class("dim-label")
        placeholder.append(empty_lbl)
        listbox.set_placeholder(placeholder)

        scrolled.set_child(listbox)
        column.append(scrolled)

        # Drop target for the entire column
        drop_target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        drop_target.connect("drop", lambda target, value, x, y, cid=col_id: self.on_kanban_drop(value, cid))
        drop_target.connect("enter", lambda target, x, y, c=column: self._on_column_drag_enter(c))
        drop_target.connect("leave", lambda target, c=column: self._on_column_drag_leave(c))
        column.add_controller(drop_target)

        self.kanban_columns[col_id] = {
            "box": column,
            "badge": badge,
            "listbox": listbox,
        }
        return column

    def _on_column_drag_enter(self, column):
        column.add_css_class("kanban-drop-target")
        return Gdk.DragAction.MOVE

    def _on_column_drag_leave(self, column):
        column.remove_css_class("kanban-drop-target")

    def on_kanban_new_task_activate(self, entry):
        text = entry.get_text().strip()
        if not text:
            return

        list_to_add = self.current_list
        effective_date = None
        if self.current_list == "today":
            effective_date = datetime.datetime.now().isoformat()
        elif self.current_list == "next7":
            effective_date = datetime.datetime.combine(
                datetime.date.today() + datetime.timedelta(days=1),
                datetime.time.min,
            ).isoformat()
        elif self.current_list == "overdue":
            effective_date = datetime.datetime.combine(
                datetime.date.today() - datetime.timedelta(days=1),
                datetime.time.min,
            ).isoformat()

        must_select_project = False
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project = self.task_manager.get_project_by_id(project_id)
            project_name = project["name"] if project else None
        else:
            if len(self.task_manager.projects) > 1:
                project_name = ""
                must_select_project = True
            else:
                inbox_project = self.task_manager.get_inbox_project()
                project_name = inbox_project["name"] if inbox_project else None

        new_task = self.task_manager.add_task(
            list_to_add,
            text,
            project=project_name,
            effective_date=effective_date,
            status="pending",
        )
        entry.set_text("")
        self.refresh_task_list()
        self.refresh_sidebar()

        if must_select_project:
            self.show_task_info_panel(new_task)
            self.show_toast(_("Please select a project for the new task"))
            self.highlight_project_requirement()

    def create_kanban_card(self, task, column_status):
        row = Gtk.ListBoxRow()
        row.set_name(str(task["id"]))

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.add_css_class("card")
        card_box.add_css_class("kanban-card")

        is_panel_shown = (
            hasattr(self, "detail_split")
            and self.detail_split.get_show_sidebar()
            and self.current_task_info is not None
        )
        if is_panel_shown and str(task.get("id")) == str(self.current_task_info.get("id")):
            card_box.add_css_class("is-selected")

        # Top row: Drag handle, Checkbox, Title, Favorite button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Drag handle
        handle = icons.image("drag-handle")
        handle.add_css_class("drag-handle-icon")
        handle.set_tooltip_text(_("Drag to move"))
        handle.set_cursor(Gdk.Cursor.new_from_name("grab", None))

        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)

        def prepare_drag(source, x, y, t_id=task["id"]):
            return Gdk.ContentProvider.new_for_value(t_id)

        def drag_begin(source, drag):
            paintable = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).lookup_icon(
                icons.name("drag-handle"), None, 16, 1, Gtk.TextDirection.NONE, 0
            )
            drag_source.set_icon(paintable, 0, 0)

        drag_source.connect("prepare", prepare_drag)
        drag_source.connect("drag-begin", drag_begin)
        handle.add_controller(drag_source)
        top_row.append(handle)

        # Title Label
        is_completed = task.get("completed", False)
        title_lbl = Gtk.Label(label=task.get("title", ""), wrap=True, xalign=0)
        title_lbl.set_hexpand(True)
        if is_completed:
            title_lbl.add_css_class("dim-label")
        top_row.append(title_lbl)

        # Star button
        is_favorite = task.get("favorite", False)
        star_btn = Gtk.Button(valign=Gtk.Align.CENTER)
        star_btn.set_child(icons.image("star-on" if is_favorite else "star-off"))
        star_btn.add_css_class("flat")
        star_label = _("Remove from favorites") if is_favorite else _("Add to favorites")
        star_btn.set_tooltip_text(star_label)
        star_btn.update_property([Gtk.AccessibleProperty.LABEL], [star_label])
        if is_favorite:
            star_btn.add_css_class("favorite-active")
        star_btn.connect("clicked", lambda b, t=task: self.on_toggle_favorite(t))
        top_row.append(star_btn)

        card_box.append(top_row)

        # Bottom metadata row
        meta_items = []
        has_meta = False

        # Subtasks
        subtasks = task.get("subtasks", [])
        if subtasks:
            has_meta = True
            done_subtasks = sum(1 for s in subtasks if s.get("completed", False))
            subtask_lbl = Gtk.Label(label=f"✓ {done_subtasks}/{len(subtasks)}")
            subtask_lbl.add_css_class("caption")
            subtask_lbl.add_css_class("dim-label")
            meta_items.append(subtask_lbl)

        # Project tag
        if task.get("project"):
            has_meta = True
            proj_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            proj_dot = Gtk.Box()
            proj_dot.add_css_class("project-color")
            p_color = "black"
            for p in self.task_manager.projects:
                if p.get("name") == task["project"]:
                    p_color = p.get("color", "black")
                    break
            proj_dot.add_css_class(f"color-{p_color}")
            proj_box.append(proj_dot)

            proj_lbl = Gtk.Label(label=task["project"])
            proj_lbl.add_css_class("caption")
            proj_lbl.add_css_class("dim-label")
            proj_box.append(proj_lbl)
            meta_items.append(proj_box)
        else:
            has_meta = True
            no_proj_lbl = Gtk.Label(label=_("No project"))
            no_proj_lbl.add_css_class("caption")
            no_proj_lbl.add_css_class("date-header-past")
            meta_items.append(no_proj_lbl)

        if has_meta:
            meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            meta_row.set_margin_top(4)
            for item in meta_items:
                meta_row.append(item)
            card_box.append(meta_row)

        # Drop target on the card
        card_drop = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        card_drop.connect(
            "drop",
            lambda target, value, x, y, col_id=column_status, t_id=task["id"]: self.on_kanban_drop(
                value, col_id, target_task_id=t_id
            ),
        )
        row.add_controller(card_drop)

        # Click gesture to show details
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", lambda g, n, x, y, t=task: self.on_kanban_card_clicked(t))
        row.add_controller(click_gesture)

        row.set_child(card_box)
        return row

    def on_kanban_card_clicked(self, task):
        task_id = task.get("id")
        if not task_id:
            return

        if hasattr(self, "is_project_selection_pending") and self.is_project_selection_pending():
            if self.current_task_info and self.current_task_info.get("id") != task_id:
                self.show_toast(_("Please select a project for the task first"))
                self.highlight_project_requirement()
                return

        fresh_task = self.task_manager.find_task(task_id) or task
        self.show_task_info_panel(fresh_task)
        self.update_kanban_selection()

    def update_kanban_selection(self):
        if not hasattr(self, "kanban_columns") or not self.kanban_columns:
            return

        is_panel_shown = (
            hasattr(self, "detail_split")
            and self.detail_split.get_show_sidebar()
            and self.current_task_info is not None
        )
        target_id_str = str(self.current_task_info.get("id")) if is_panel_shown else None

        for col_info in self.kanban_columns.values():
            listbox = col_info["listbox"]
            child = listbox.get_first_child()
            while child:
                if isinstance(child, Gtk.ListBoxRow):
                    row_id = child.get_name()
                    card = child.get_child()
                    if card and hasattr(card, "add_css_class"):
                        if target_id_str and row_id == target_id_str:
                            card.add_css_class("is-selected")
                        else:
                            card.remove_css_class("is-selected")
                child = child.get_next_sibling()

    def on_kanban_drop(self, dragged_task_id, new_status, target_task_id=None):
        if not dragged_task_id:
            return False

        if hasattr(self, "is_project_selection_pending") and self.is_project_selection_pending():
            self.show_toast(_("Please select a project for the task first"))
            self.highlight_project_requirement()
            return False

        task = self.task_manager.find_task(dragged_task_id)
        if not task:
            return False

        old_status = task.get("status", "pending")
        if old_status == new_status and target_task_id is None:
            return True

        updated = self.task_manager.move_task_kanban(dragged_task_id, new_status, target_task_id)
        if updated:
            if (
                hasattr(self, "current_task_info")
                and self.current_task_info
                and self.current_task_info.get("id") == dragged_task_id
            ):
                self.current_task_info = updated
                if hasattr(self, "refresh_current_task_panel"):
                    self.refresh_current_task_panel()

            self.refresh_task_list()
            self.refresh_sidebar()

            status_names = {
                "pending": _("Pending"),
                "in_progress": _("In progress"),
                "completed": _("Completed"),
            }
            status_label = status_names.get(new_status, new_status)
            self.show_toast(_("“{}” moved to {}").format(task.get("title", ""), status_label))
            return True
        return False

    def on_kanban_search_changed(self, entry):
        self.search_query = entry.get_text()
        if hasattr(self, "search_entry") and self.search_entry.get_text() != self.search_query:
            self.search_entry.set_text(self.search_query)
        self.refresh_kanban_board()

    def refresh_kanban_board(self):
        if not hasattr(self, "kanban_columns") or not self.kanban_columns:
            return

        title_text = ""
        if hasattr(self, "list_title_label") and self.list_title_label.get_label():
            title_text = self.list_title_label.get_label()
        elif self.current_list.startswith("project_"):
            p_id = self.current_list.replace("project_", "")
            proj = self.task_manager.get_project_by_id(p_id)
            title_text = proj["name"] if proj else _("Project")
        else:
            title_text = self.task_manager.lists.get(self.current_list, _("Tasks"))

        self.kanban_title_label.set_label(title_text)

        is_custom_project = self.current_list.startswith("project_") and self.current_list != "project_inbox"
        self.kanban_edit_button.set_visible(is_custom_project)
        self.kanban_delete_button.set_visible(is_custom_project)

        kanban_data = self.task_manager.get_kanban_tasks(self.current_list, self.search_query)

        for col_id, col_info in self.kanban_columns.items():
            tasks = kanban_data.get(col_id, [])
            col_info["badge"].set_label(str(len(tasks)))

            listbox = col_info["listbox"]
            while child := listbox.get_first_child():
                listbox.remove(child)

            for task in tasks:
                card = self.create_kanban_card(task, col_id)
                listbox.append(card)

        self.update_kanban_selection()
