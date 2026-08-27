import datetime

from gi.repository import Adw, Gtk

from ..core.debug import debug, debug_method
from ..core.i18n import translate as _


class TaskDetailMixin:
    @debug_method("create_task_info_panel")
    def create_task_info_panel(self):
        """Build the task details panel.

        The panel is the end sidebar of an AdwOverlaySplitView, so libadwaita
        handles the adaptive behaviour: side by side on wide windows, overlaid
        on narrow ones.
        """
        debug.log_event("UI", "Creating task info panel")

        detail_header = Adw.HeaderBar()
        detail_header.set_show_end_title_buttons(False)
        detail_header.set_title_widget(Adw.WindowTitle(title=_("Task Details")))

        close_button = Gtk.Button(icon_name="window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.set_tooltip_text(_("Close task details"))
        close_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Close task details")])
        close_button.connect("clicked", self.on_close_task_info)
        detail_header.pack_end(close_button)

        self.task_info_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.task_info_content.set_margin_top(12)
        self.task_info_content.set_margin_bottom(12)
        self.task_info_content.set_margin_start(12)
        self.task_info_content.set_margin_end(12)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.task_info_content)

        self.detail_toolbar = Adw.ToolbarView()
        self.detail_toolbar.add_top_bar(detail_header)
        self.detail_toolbar.set_content(scrolled)

        debug.log_event("UI", "Task info panel created successfully")
        return self.detail_toolbar

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

        if not task_id_str.isdigit():
            debug.log_event("TASK_CLICK", f"Ignoring non-task row: '{task_id_str}'")
            return

        task_id = int(task_id_str)
        debug.log_event("TASK_CLICK", f"Looking for task with ID: {task_id}")

        found_task = self.task_manager.find_task(task_id)
        if found_task:
            debug.log_event(
                "TASK_CLICK",
                f"Found task: '{found_task.get('title', 'unknown')}' (ID: {found_task.get('id', 'unknown')})",
            )
            self.show_task_info_panel(found_task)
            return

        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        debug.log_event("TASK_CLICK", f"ERROR: Task with ID {task_id} not found in task list")
        debug.log_event("TASK_CLICK", f"Available task IDs: {[t.get('id') for t in all_tasks]}")

    @debug_method("show_task_info_panel")
    def show_task_info_panel(self, task):
        try:
            debug.log_event("TASK_INFO", f"Showing task info panel for task {task.get('id')}: '{task.get('title', 'unknown')}'")
            self.current_task_info = task

            child_count = 0
            while child := self.task_info_content.get_first_child():
                child_count += 1
                self.task_info_content.remove(child)
            debug.log_event("TASK_INFO", f"Removed {child_count} previous child widgets")

            self._build_title_group(task)
            self._build_date_group(task)
            self._build_description_group(task)
            self._build_organization_group(task)
            self._build_subtasks_group(task)
            self._build_actions_group(task)

            self.detail_split.set_show_sidebar(True)
            debug.log_event("TASK_INFO", "Task info panel shown successfully")
        except Exception as exc:
            debug.log_event("TASK_INFO", f"ERROR in show_task_info_panel: {exc}", stack_info=True)

    def _build_title_group(self, task):
        title_group = Adw.PreferencesGroup(title=_("Task"))
        self.task_title_entry = Adw.EntryRow(title=_("Title"))
        self.task_title_entry.set_text(task["title"])
        self.task_title_entry.connect("notify::text", self.on_task_title_changed)
        title_group.add(self.task_title_entry)
        self.task_info_content.append(title_group)

    def _build_date_group(self, task):
        date_group = Adw.PreferencesGroup(title=_("Date"))
        self.task_date_row = Adw.ActionRow(title=_("Effective date"))

        current_date_str = _("No date")
        if task.get("effective_date"):
            try:
                date_obj = datetime.datetime.fromisoformat(task["effective_date"])
                current_date_str = date_obj.strftime("%d/%m/%Y")
            except Exception:
                pass

        self.date_label = Gtk.Label(label=current_date_str)
        self.date_label.add_css_class("dim-label")
        self.task_date_row.add_suffix(self.date_label)

        calendar_button = Gtk.Button(icon_name="x-office-calendar-symbolic", valign=Gtk.Align.CENTER)
        calendar_button.add_css_class("flat")
        calendar_button.set_tooltip_text(_("Select date"))
        calendar_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Select date")])
        calendar_button.connect("clicked", self.on_open_calendar)
        self.task_date_row.add_suffix(calendar_button)

        self.task_date_row.set_activatable(True)
        self.task_date_row.connect("activated", self.on_open_calendar)

        date_group.add(self.task_date_row)
        self.task_info_content.append(date_group)

    def _build_description_group(self, task):
        notes_group = Adw.PreferencesGroup(title=_("Description"))

        self.task_notes_buffer = Gtk.TextBuffer(text=task.get("notes", ""))
        self.task_notes_buffer.connect("changed", self.on_task_notes_changed)
        notes_view = Gtk.TextView(
            buffer=self.task_notes_buffer,
            wrap_mode=Gtk.WrapMode.WORD,
            top_margin=8,
            bottom_margin=8,
            left_margin=12,
            right_margin=12,
        )
        notes_view.update_property([Gtk.AccessibleProperty.LABEL], [_("Description")])

        notes_scrolled = Gtk.ScrolledWindow(height_request=100, vexpand=False)
        notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        notes_scrolled.add_css_class("card")
        notes_scrolled.set_child(notes_view)

        # Added to the group rather than next to it, so it lines up with the
        # other groups in the panel.
        notes_group.add(notes_scrolled)
        self.task_info_content.append(notes_group)

    def _build_organization_group(self, task):
        project_group = Adw.PreferencesGroup(title=_("Organization"))
        project_row = Adw.ComboRow(title=_("Project"))

        inbox_project = self.task_manager.get_inbox_project()
        inbox_name = inbox_project["name"] if inbox_project else _("Inbox")
        project_names = [inbox_name] + [p["name"] for p in self.task_manager.projects if p.get("id") != "inbox"]

        project_row.set_model(Gtk.StringList.new(project_names))
        current_project = task.get("project", inbox_name)
        try:
            project_row.set_selected(project_names.index(current_project))
        except ValueError:
            project_row.set_selected(0)

        project_row.connect("notify::selected", self.on_project_changed_enhanced)
        project_group.add(project_row)
        self.task_info_content.append(project_group)

    def _build_subtasks_group(self, task):
        subtasks_group = Adw.PreferencesGroup(title=_("Subtasks"))

        for subtask in task.get("subtasks", []):
            subtasks_group.add(self.create_subtask_row(subtask))

        self.new_subtask_entry = Adw.EntryRow(title=_("New subtask"))
        self.new_subtask_entry.set_show_apply_button(True)
        self.new_subtask_entry.connect("apply", self.on_add_subtask_activate)
        subtasks_group.add(self.new_subtask_entry)

        self.task_info_content.append(subtasks_group)

    def _build_actions_group(self, task):
        actions_group = Adw.PreferencesGroup(title=_("Actions"))

        completed_row = Adw.SwitchRow(title=_("Completed"), active=task["completed"])
        completed_row.connect("notify::active", self.on_task_completed_toggled)
        actions_group.add(completed_row)

        delete_row = Adw.ActionRow(title=_("Delete task"))
        delete_button = Gtk.Button(label=_("Delete"), valign=Gtk.Align.CENTER)
        delete_button.add_css_class("destructive-action")
        delete_button.connect("clicked", lambda btn: self.on_delete_current_task())
        delete_row.add_suffix(delete_button)
        delete_row.set_activatable_widget(delete_button)
        actions_group.add(delete_row)

        self.task_info_content.append(actions_group)

    def create_subtask_row(self, subtask):
        """A subtask is a row of a preferences group, so it uses AdwEntryRow.

        The previous raw Gtk.Box added straight into the group did not get the
        group's row styling, which is why subtasks looked unframed.
        """
        row = Adw.EntryRow(title=_("Subtask"))
        row.set_text(subtask.get("title", ""))
        row.set_show_apply_button(True)

        toggle = Gtk.CheckButton(active=subtask.get("completed", False), valign=Gtk.Align.CENTER)
        toggle.set_tooltip_text(_("Mark as completed"))
        toggle.update_property([Gtk.AccessibleProperty.LABEL], [_("Mark as completed")])
        toggle.connect("toggled", lambda button, sid=subtask["id"]: self.on_subtask_toggled(sid))
        row.add_prefix(toggle)

        delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        delete_button.add_css_class("flat")
        delete_button.set_tooltip_text(_("Delete subtask"))
        delete_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Delete subtask")])
        delete_button.connect("clicked", lambda button, sid=subtask["id"]: self.on_delete_subtask(sid))
        row.add_suffix(delete_button)

        row.connect("apply", lambda entry, sid=subtask["id"]: self._update_subtask_title(entry, sid))
        if subtask.get("completed", False):
            row.add_css_class("dim-label")
        return row

    def refresh_current_task_panel(self):
        if not self.current_task_info:
            return

        refreshed_task = self.task_manager.find_task(self.current_task_info.get("id"))
        if not refreshed_task:
            self.close_task_details()
            return

        self.show_task_info_panel(refreshed_task)

    def on_add_subtask_activate(self, entry):
        if not self.current_task_info:
            return

        subtask = self.task_manager.add_subtask(self.current_task_info.get("id"), entry.get_text())
        if not subtask:
            return

        entry.set_text("")
        self.current_task_info = self.task_manager.find_task(self.current_task_info.get("id"))
        self.refresh_task_list()
        self.refresh_current_task_panel()

    def on_subtask_toggled(self, subtask_id):
        if not self.current_task_info:
            return

        updated_subtask = self.task_manager.toggle_subtask_completed(self.current_task_info.get("id"), subtask_id)
        if not updated_subtask:
            return

        self.current_task_info = self.task_manager.find_task(self.current_task_info.get("id"))
        self.refresh_task_list()
        self.refresh_current_task_panel()

    def _update_subtask_title(self, entry, subtask_id):
        if not self.current_task_info:
            return

        updated_subtask = self.task_manager.update_subtask(
            self.current_task_info.get("id"),
            subtask_id,
            title=entry.get_text(),
        )
        if not updated_subtask:
            existing_subtask = self.task_manager.find_subtask(self.current_task_info.get("id"), subtask_id)
            if existing_subtask:
                entry.set_text(existing_subtask.get("title", ""))
            return

        self.current_task_info = self.task_manager.find_task(self.current_task_info.get("id"))
        self.refresh_task_list()

    def on_delete_subtask(self, subtask_id):
        if not self.current_task_info:
            return

        deleted = self.task_manager.delete_subtask(self.current_task_info.get("id"), subtask_id)
        if not deleted:
            return

        self.current_task_info = self.task_manager.find_task(self.current_task_info.get("id"))
        self.refresh_task_list()
        self.refresh_current_task_panel()

    def _verify_task_integrity_after_date_change(self):
        debug.log_event("INTEGRITY", "=== TASK INTEGRITY CHECK ===")
        if not self.current_task_info:
            debug.log_event("INTEGRITY", "No current task info")
            return False

        task_id = self.current_task_info.get("id")
        found_task = self.task_manager.find_task(task_id)
        if not found_task:
            debug.log_event("INTEGRITY", f"ERROR: Task {task_id} not found in task manager!")
            return False

        current_date = self.current_task_info.get("effective_date")
        manager_date = found_task.get("effective_date")
        if current_date != manager_date:
            debug.log_event(
                "INTEGRITY",
                f"ERROR: Date mismatch - current_task_info: {current_date}, manager: {manager_date}",
            )
            return False

        debug.log_event("INTEGRITY", f"Task {task_id} integrity OK - date: {current_date}")
        return True

    @debug_method("on_open_calendar")
    def on_open_calendar(self, widget):
        debug.log_event("CALENDAR", "=== CALENDAR DIALOG OPENING ===")
        debug.log_event("CALENDAR", f"Current task info: {self.current_task_info.get('title') if self.current_task_info else 'None'}")

        calendar = Gtk.Calendar(show_heading=True, show_day_names=True, show_week_numbers=False)
        if self.current_task_info and self.current_task_info.get("effective_date"):
            try:
                date_obj = datetime.datetime.fromisoformat(self.current_task_info["effective_date"])
                self._select_calendar_date(calendar, date_obj)
                debug.log_event("CALENDAR", f"Pre-selected date: {date_obj.date()}")
            except Exception as exc:
                debug.log_event("CALENDAR", f"Error pre-selecting date: {exc}")

        dialog = Adw.Dialog(title=_("Select date"), content_width=360)

        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_button)

        select_button = Gtk.Button(label=_("Select"))
        select_button.add_css_class("suggested-action")
        select_button.connect("clicked", lambda b: self.on_date_selected(calendar, dialog))
        header.pack_end(select_button)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        content.append(calendar)

        quick_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True)
        today_button = Gtk.Button(label=_("Today"))
        today_button.connect("clicked", lambda b: self.on_today_selected(calendar, dialog))
        quick_actions.append(today_button)

        clear_button = Gtk.Button(label=_("No date"))
        clear_button.connect("clicked", lambda b: self.on_date_cleared(dialog))
        quick_actions.append(clear_button)
        content.append(quick_actions)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        dialog.set_child(toolbar)
        dialog.set_default_widget(select_button)
        dialog.present(self)
        debug.log_event("CALENDAR", "Calendar dialog presented")

    def on_date_selected(self, calendar, dialog):
        debug.log_event("CALENDAR", "=== DATE SELECTION STARTED ===")

        if self.current_task_info:
            selected_date = calendar.get_date()
            date_obj = datetime.datetime(
                selected_date.get_year(),
                selected_date.get_month(),
                selected_date.get_day_of_month(),
            )
            old_date = self.current_task_info.get("effective_date", "None")
            new_date = date_obj.isoformat()

            debug.log_event("CALENDAR", f"Date changing from '{old_date}' to '{new_date}'")
            debug.log_event("CALENDAR", f"Task ID: {self.current_task_info.get('id')}")

            task_id = self.current_task_info.get("id")
            if not self.task_manager.task_exists(task_id):
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found in task manager!")
                dialog.close()
                return

            self.current_task_info = self.task_manager.update_task(task_id, effective_date=new_date)
            debug.log_event("CALENDAR", f"Task effective_date updated to: {new_date}")

            try:
                self.date_label.set_text(date_obj.strftime("%d/%m/%Y"))
            except Exception as exc:
                debug.log_event("CALENDAR", f"ERROR updating date label: {exc}")

            try:
                self.refresh_task_list()
                self.refresh_sidebar()
            except Exception as exc:
                debug.log_event("CALENDAR", f"ERROR refreshing after date change: {exc}", stack_info=True)

            if not self._verify_task_integrity_after_date_change():
                debug.log_event("CALENDAR", "INTEGRITY CHECK FAILED after date change")
                self._recover_from_ui_error()
        else:
            debug.log_event("CALENDAR", "ERROR: No current_task_info available")

        dialog.close()

    def on_today_selected(self, calendar, dialog):
        debug.log_event("CALENDAR", "Today button selected")
        self._select_calendar_date(calendar, datetime.date.today())
        self.on_date_selected(calendar, dialog)

    @staticmethod
    def _select_calendar_date(calendar, date):
        """Gtk.Calendar.select_day() is deprecated; set the properties instead.

        Gtk.Calendar counts months from 0, unlike datetime.
        """
        calendar.set_year(date.year)
        calendar.set_month(date.month - 1)
        calendar.set_day(date.day)

    def on_date_cleared(self, dialog):
        debug.log_event("CALENDAR", "=== DATE CLEAR STARTED ===")

        if self.current_task_info:
            old_date = self.current_task_info.get("effective_date", "None")
            debug.log_event("CALENDAR", f"Clearing date from '{old_date}' to 'None'")

            task_id = self.current_task_info.get("id")
            if not self.task_manager.task_exists(task_id):
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found!")
                dialog.close()
                return

            self.current_task_info = self.task_manager.update_task(task_id, effective_date=None)

            try:
                self.date_label.set_text(_("No date"))
            except Exception as exc:
                debug.log_event("CALENDAR", f"ERROR updating date label: {exc}")

            try:
                self.refresh_task_list()
                self.refresh_sidebar()
            except Exception as exc:
                debug.log_event("CALENDAR", f"ERROR in refresh after date clear: {exc}", stack_info=True)

            if not self._verify_task_integrity_after_date_change():
                debug.log_event("CALENDAR", "INTEGRITY CHECK FAILED after date clear")
                self._recover_from_ui_error()

        dialog.close()

    def on_project_changed_enhanced(self, row, param):
        debug.log_event("PROJECT_CHANGE", "Project changed in task info")
        if not self.current_task_info:
            return

        selected_idx = row.get_selected()
        model = row.get_model()
        if selected_idx >= model.get_n_items():
            return

        project_name = model.get_string(selected_idx)
        debug.log_event("PROJECT_CHANGE", f"Changed to project: {project_name}")
        updated_task = self.task_manager.update_task(self.current_task_info.get("id"), project=project_name)
        if updated_task:
            self.current_task_info = updated_task
            self.refresh_task_list()
            self.refresh_sidebar()

    def close_task_details(self):
        """Hide the details panel, if it is showing."""
        if not hasattr(self, "detail_split"):
            return
        if self.detail_split.get_show_sidebar():
            debug.log_event("TASK_INFO", "Closing task info panel")
            self.detail_split.set_show_sidebar(False)
        self.current_task_info = None

    @debug_method("on_close_task_info")
    def on_close_task_info(self, button=None):
        self.close_task_details()

    def on_task_title_changed(self, row, param):
        debug.log_event("TASK_EDIT", "Task title changed")
        if not self.current_task_info:
            return

        new_title = row.get_text()
        old_title = self.current_task_info.get("title", "unknown")
        debug.log_event("TASK_EDIT", f"Title changed from '{old_title}' to '{new_title}'")
        updated_task = self.task_manager.update_task(self.current_task_info.get("id"), title=new_title)
        if updated_task:
            self.current_task_info = updated_task
            self.refresh_task_list()

    def on_task_notes_changed(self, buffer):
        debug.log_event("TASK_EDIT", "Task notes changed")
        if not self.current_task_info:
            return

        notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        updated_task = self.task_manager.update_task(self.current_task_info.get("id"), notes=notes)
        if updated_task:
            self.current_task_info = updated_task

    def on_task_completed_toggled(self, switch, param):
        debug.log_event("TASK_EDIT", f"Task completed toggled to: {switch.get_active()}")
        if self.current_task_info and self.current_task_info["completed"] != switch.get_active():
            updated_task = self.task_manager.update_task(
                self.current_task_info.get("id"),
                completed=switch.get_active(),
            )
            if updated_task:
                self.current_task_info = updated_task
                self.refresh_task_list()
                self.refresh_sidebar()

    def on_delete_current_task(self):
        """Delete the open task, offering an undo toast rather than a prompt.

        The HIG prefers a reversible action over a confirmation dialog for
        single-item deletions.
        """
        debug.log_event("TASK_DELETE", "Deleting current task")
        if not self.current_task_info:
            return

        snapshot = dict(self.current_task_info)
        task_title = snapshot.get("title", "unknown")
        debug.log_event("TASK_DELETE", f"Deleting task {snapshot.get('id')}: '{task_title}'")

        if not self.task_manager.delete_task(snapshot.get("id")):
            debug.log_event("TASK_DELETE", "ERROR: Task was not found for deletion")
            return

        debug.log_event("TASK_DELETE", "Task deleted successfully")
        self.close_task_details()
        self.refresh_task_list()
        self.refresh_sidebar()

        toast = Adw.Toast.new(_("“{}” deleted").format(task_title))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", lambda t: self._undo_task_delete(snapshot))
        self.show_toast(toast)

    def _undo_task_delete(self, snapshot):
        self.task_manager.restore_task(snapshot)
        self.refresh_task_list()
        self.refresh_sidebar()
        debug.log_event("TASK_DELETE", f"Restored task {snapshot.get('id')}")
