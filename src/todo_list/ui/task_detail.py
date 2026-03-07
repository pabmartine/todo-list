import datetime

from gi.repository import Adw, Gtk

from ..debug import debug, debug_method
from ..i18n import translate as _


class TaskDetailMixin:
    @debug_method("create_task_info_panel")
    def create_task_info_panel(self):
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

        self.task_info_page = Adw.NavigationPage()
        self.task_info_page.set_title(_("Task Details"))
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
            debug.log_event(
                "TASK_CLICK",
                f"Found task: '{found_task.get('title', 'unknown')}' (ID: {found_task.get('id', 'unknown')})",
            )
            self.on_task_row_clicked(found_task)
            return

        debug.log_event("TASK_CLICK", f"ERROR: Task with ID {task_id} not found in task list")
        debug.log_event("TASK_CLICK", f"Available task IDs: {[t.get('id') for t in all_tasks]}")

    @debug_method("on_task_row_clicked")
    def on_task_row_clicked(self, task):
        debug.log_event(
            "TASK_CLICK",
            f"Task row clicked: '{task.get('title', 'unknown')}' (ID: {task.get('id', 'unknown')})",
        )

        task_id = task.get("id")
        if task_id is None:
            debug.log_event("TASK_CLICK", "ERROR: Task has no ID")
            return

        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        task_exists = any(t.get("id") == task_id for t in all_tasks)
        if not task_exists:
            debug.log_event("TASK_CLICK", f"ERROR: Task {task_id} no longer exists in task manager")
            return

        if self.get_width() < 600:
            debug.log_event("TASK_CLICK", "Using dialog mode (small screen)")
            self.show_task_info_dialog(task)
        else:
            debug.log_event("TASK_CLICK", "Using panel mode (large screen)")
            self.show_task_info_panel(task)

    def show_task_info_dialog(self, task):
        debug.log_event("TASK_INFO", "Routing small-screen task details through panel flow")
        self.show_task_info_panel(task)

    @debug_method("show_task_info_panel")
    def show_task_info_panel(self, task):
        try:
            debug.log_event("TASK_INFO", f"Showing task info panel for task {task.get('id')}: '{task.get('title', 'unknown')}'")
            self.current_task_info = task
            debug.log_event("TASK_INFO", f"Set current_task_info to: {task.get('title', 'unknown')}")

            if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
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
                except Exception:
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
            notes_view = Gtk.TextView(
                buffer=self.task_notes_buffer,
                wrap_mode=Gtk.WrapMode.WORD,
                margin_top=8,
                margin_bottom=8,
                margin_start=12,
                margin_end=12,
            )
            notes_scrolled.set_child(notes_view)

            self.task_info_content.append(notes_group)
            self.task_info_content.append(notes_scrolled)

            project_group = Adw.PreferencesGroup(title=_("Organization"))
            project_row = Adw.ComboRow(title=_("Project"))

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

            subtasks_group = Adw.PreferencesGroup(title=_("Subtasks"))
            subtasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            subtasks_box.set_margin_top(6)
            subtasks_box.set_margin_bottom(6)

            for subtask in task.get("subtasks", []):
                subtasks_box.append(self.create_subtask_row(task["id"], subtask))

            add_subtask_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            self.new_subtask_entry = Gtk.Entry(placeholder_text=_("New subtask..."))
            self.new_subtask_entry.set_hexpand(True)
            self.new_subtask_entry.connect("activate", self.on_add_subtask_activate)
            add_subtask_box.append(self.new_subtask_entry)

            add_subtask_button = Gtk.Button(label=_("Add"))
            add_subtask_button.add_css_class("suggested-action")
            add_subtask_button.connect("clicked", self.on_add_subtask_clicked)
            add_subtask_box.append(add_subtask_button)

            subtasks_box.append(add_subtask_box)
            subtasks_group.add(subtasks_box)
            self.task_info_content.append(subtasks_group)

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
            delete_row.connect("activated", lambda w: self.on_delete_current_task())
            actions_group.add(delete_row)
            self.task_info_content.append(actions_group)

            if self.get_width() < 600:
                debug.log_event("TASK_INFO", "Using NavigationPage mode")
                if not hasattr(self, "task_info_page"):
                    self.task_info_page = Adw.NavigationPage()
                    self.task_info_page.set_title(_("Task Details"))
                    self.task_info_page.set_tag("task-info")
                    self.task_info_page.set_child(self.task_info_panel)

                self.split_view.set_content(self.task_info_page)
            else:
                debug.log_event("TASK_INFO", "Using panel mode")

                if not hasattr(self, "content_paned") or self.content_paned.get_parent() != self.content_page:
                    debug.log_event("TASK_INFO", "Creating/recreating content_paned structure")
                    self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
                    self.content_paned.set_wide_handle(True)
                    self.content_paned.set_hexpand(True)
                    self.content_paned.set_shrink_start_child(True)
                    self.content_paned.set_shrink_end_child(False)
                    self.content_paned.set_resize_start_child(True)
                    self.content_paned.set_resize_end_child(False)

                    current_content = self.content_page.get_child()
                    if isinstance(current_content, Gtk.Paned):
                        debug.log_event("TASK_INFO", "Extracting content from existing paned")
                        actual_content = current_content.get_start_child()
                        current_content.set_start_child(None)
                        current_content.set_end_child(None)
                    else:
                        actual_content = current_content

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

                self.task_info_panel.set_size_request(400, -1)
                self.task_info_panel.set_hexpand(False)
                self.task_info_panel.set_visible(True)
                self.content_paned.set_end_child(self.task_info_panel)

                target_position = self.get_width() - 400
                self.content_paned.set_position(target_position)
                debug.log_event("TASK_INFO", f"Set paned position to: {target_position}")

            debug.log_event("TASK_INFO", "Task info panel shown successfully")
        except Exception as exc:
            debug.log_event("TASK_INFO", f"ERROR in show_task_info_panel: {exc}", stack_info=True)

    def create_subtask_row(self, task_id, subtask):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        toggle = Gtk.CheckButton(active=subtask.get("completed", False))
        toggle.connect("toggled", lambda button, sid=subtask["id"]: self.on_subtask_toggled(sid))
        row_box.append(toggle)

        title_entry = Gtk.Entry()
        title_entry.set_hexpand(True)
        title_entry.set_text(subtask.get("title", ""))
        title_entry.connect("activate", lambda entry, sid=subtask["id"]: self.on_subtask_title_activate(entry, sid))
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", lambda controller, sid=subtask["id"], entry=title_entry: self.on_subtask_title_focus_out(entry, sid))
        title_entry.add_controller(focus_controller)
        if subtask.get("completed", False):
            title_entry.add_css_class("dim-label")
        row_box.append(title_entry)

        delete_button = Gtk.Button(icon_name="user-trash-symbolic")
        delete_button.add_css_class("flat")
        delete_button.connect("clicked", lambda button, sid=subtask["id"]: self.on_delete_subtask(sid))
        row_box.append(delete_button)
        return row_box

    def refresh_current_task_panel(self):
        if not self.current_task_info:
            return

        refreshed_task = self.task_manager.find_task(self.current_task_info.get("id"))
        if not refreshed_task:
            self.on_close_task_info(None)
            return

        self.show_task_info_panel(refreshed_task)

    def on_add_subtask_activate(self, entry):
        self._create_subtask_from_entry(entry)

    def on_add_subtask_clicked(self, button):
        self._create_subtask_from_entry(self.new_subtask_entry)

    def _create_subtask_from_entry(self, entry):
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

    def on_subtask_title_activate(self, entry, subtask_id):
        self._update_subtask_title(entry, subtask_id)

    def on_subtask_title_focus_out(self, entry, subtask_id):
        self._update_subtask_title(entry, subtask_id)
        return False

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
        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        found_task = None
        for task in all_tasks:
            if task.get("id") == task_id:
                found_task = task
                break

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
            except Exception as exc:
                debug.log_event("CALENDAR", f"Error pre-selecting date: {exc}")

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
            date_obj = datetime.datetime(
                selected_date.get_year(),
                selected_date.get_month(),
                selected_date.get_day_of_month(),
            )
            old_date = self.current_task_info.get("effective_date", "None")
            new_date = date_obj.isoformat()

            debug.log_event("CALENDAR", f"Date changing from '{old_date}' to '{new_date}'")
            debug.log_event("CALENDAR", f"Task ID: {self.current_task_info.get('id')}")
            debug.log_event("CALENDAR", f"Task title: {self.current_task_info.get('title')}")

            task_id = self.current_task_info.get("id")
            if not self.task_manager.task_exists(task_id):
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found in task manager!")
                dialog.close()
                return

            updated_task = self.task_manager.update_task(task_id, effective_date=new_date)
            self.current_task_info = updated_task
            debug.log_event("CALENDAR", f"Task effective_date updated to: {new_date}")

            actual_date = self.current_task_info.get("effective_date")
            debug.log_event("CALENDAR", f"Verification - actual date in task: {actual_date}")

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
        calendar.select_day(datetime.date.today())
        self.on_date_selected(calendar, dialog)

    def on_date_cleared(self, dialog):
        debug.log_event("CALENDAR", "=== DATE CLEAR STARTED ===")
        debug.log_event("CALENDAR", f"Current task info: {self.current_task_info}")

        if self.current_task_info:
            old_date = self.current_task_info.get("effective_date", "None")
            debug.log_event("CALENDAR", f"Clearing date from '{old_date}' to 'None'")

            task_id = self.current_task_info.get("id")
            if not self.task_manager.task_exists(task_id):
                debug.log_event("CALENDAR", f"ERROR: Task {task_id} not found!")
                dialog.close()
                return

            updated_task = self.task_manager.update_task(task_id, effective_date=None)
            self.current_task_info = updated_task

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

    @debug_method("on_close_task_info")
    def on_close_task_info(self, button):
        debug.log_event("TASK_INFO", "Closing task info panel")

        try:
            self.task_info_panel.set_visible(False)
            if hasattr(self, "current_task_info"):
                current_title = self.current_task_info.get("title", "unknown") if self.current_task_info else "None"
                debug.log_event("TASK_INFO", f"Clearing current_task_info: {current_title}")
                self.current_task_info = None

            if hasattr(self, "content_paned"):
                debug.log_event("TASK_INFO", "Removing panel from paned view (keeping structure)")
                self.content_paned.set_end_child(None)

            if self.get_width() < 600:
                debug.log_event("TASK_INFO", "Restoring content from navigation page")
                self.split_view.set_content(self.content_page)

            debug.log_event("TASK_INFO", "Task info panel closed successfully")
        except Exception as exc:
            debug.log_event("TASK_INFO", f"Error closing task info panel: {exc}", stack_info=True)

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
        debug.log_event("TASK_DELETE", "Deleting current task")
        if not self.current_task_info:
            return

        task_to_delete_id = self.current_task_info.get("id")
        task_title = self.current_task_info.get("title", "unknown")
        debug.log_event("TASK_DELETE", f"Deleting task {task_to_delete_id}: '{task_title}'")

        if self.task_manager.delete_task(task_to_delete_id):
            debug.log_event("TASK_DELETE", "Task deleted successfully")
            self.refresh_task_list()
            self.refresh_sidebar()
            self.on_close_task_info(None)
            return

        debug.log_event("TASK_DELETE", "ERROR: Task was not found for deletion")
