import datetime
import time
from collections import OrderedDict

from gi.repository import Adw, Gdk, GLib, Gtk

from ..core.debug import debug, debug_method
from ..core.i18n import translate as _


PROJECT_TEXT_COLORS = [
    "purple",
    "orange",
    "blue",
    "green",
    "yellow",
    "red",
    "pink",
    "cyan",
    "teal",
    "lime",
    "amber",
    "indigo",
    "violet",
    "magenta",
    "olive",
    "gray",
    "brown",
    "gold",
    "silver",
    "maroon",
    "navy",
    "turquoise",
    "coral",
    "sky",
    "emerald",
    "ruby",
]


class TaskListMixin:
    @debug_method("refresh_task_list")
    def refresh_task_list(self):
        debug.log_event("REFRESH_TASKS", "=== REFRESH STARTED ===")
        debug.log_event("REFRESH_TASKS", f"Current list: {self.current_list}")
        debug.log_event(
            "REFRESH_TASKS",
            f"Current task info: {self.current_task_info.get('title') if self.current_task_info else 'None'}",
        )

        current_time = time.time()
        if self._refresh_in_progress or (current_time - self._last_refresh_time) < 0.1:
            debug.log_event("REFRESH_TASKS", "Refresh in progress or too recent, skipping")
            return

        self._refresh_in_progress = True
        self._last_refresh_time = current_time

        try:
            all_tasks = self.task_manager.tasks.get("all_tasks", [])
            debug.log_event("REFRESH_TASKS", f"Total tasks in manager: {len(all_tasks)}")

            invalid_tasks = [task for task in all_tasks if task.get("id") is None]
            if invalid_tasks:
                debug.log_event("REFRESH_TASKS", f"WARNING: Found {len(invalid_tasks)} tasks without IDs")

            task_ids = [task.get("id") for task in all_tasks if task.get("id") is not None]
            if len(task_ids) != len(set(task_ids)):
                debug.log_event("REFRESH_TASKS", "WARNING: Duplicate task IDs detected")

            row_count = 0
            while child := self.task_list.get_first_child():
                row_count += 1
                if hasattr(child, "get_name"):
                    debug.log_event("REFRESH_TASKS", f"Removing row: {child.get_name()}")
                self.task_list.remove(child)
            debug.log_event("REFRESH_TASKS", f"Removed {row_count} existing rows")

            self._update_list_actions()
            self._update_list_title()

            debug.log_event("REFRESH_TASKS", f"Getting tasks for list: {self.current_list}")
            tasks = self.task_manager.search_tasks(self.current_list, self.search_query)
            debug.log_event("REFRESH_TASKS", f"Retrieved {len(tasks)} tasks")

            for index, task in enumerate(tasks):
                task_id = task.get("id", "NO_ID")
                task_title = task.get("title", "NO_TITLE")
                task_date = task.get("effective_date")
                task_date_str = str(task_date)[:10] if task_date else "NO_DATE"
                debug.log_event("REFRESH_TASKS", f"Task {index}: ID={task_id}, Title='{task_title}', Date='{task_date_str}'")

            sorted_tasks = self.sort_tasks(tasks)
            debug.log_event("REFRESH_TASKS", f"Tasks sorted, count: {len(sorted_tasks)}")

            if sorted_tasks:
                self.task_list_scrolled.set_visible(True)
                if self.should_group_by_date():
                    debug.log_event("REFRESH_TASKS", "Using grouped task rows")
                    self.create_grouped_task_rows(sorted_tasks)
                else:
                    debug.log_event("REFRESH_TASKS", "Using standard task rows")
                    self.create_standard_task_rows(sorted_tasks)
            else:
                debug.log_event("REFRESH_TASKS", "No tasks to show")
                self.task_list_scrolled.set_visible(False)

            final_row_count = 0
            child = self.task_list.get_first_child()
            while child:
                final_row_count += 1
                if hasattr(child, "get_name"):
                    debug.log_event("REFRESH_TASKS", f"Final row {final_row_count}: {child.get_name() or 'HEADER'}")
                child = child.get_next_sibling()

            debug.log_event("REFRESH_TASKS", f"Created {final_row_count} new rows")
            self.update_header_title()
            debug.log_event("REFRESH_TASKS", "=== REFRESH COMPLETED SUCCESSFULLY ===")
        except Exception as exc:
            debug.log_event("REFRESH_TASKS", f"=== REFRESH ERROR: {exc} ===", stack_info=True)
            try:
                self.task_list_scrolled.set_visible(False)
                debug.log_event("REFRESH_TASKS", "Hidden task list after error")
            except Exception:
                pass
        finally:
            self._refresh_in_progress = False

    def _update_list_actions(self):
        is_project = self.current_list.startswith("project_")
        project_id = self.current_list.replace("project_", "") if is_project else ""
        is_inbox = project_id == "inbox"
        is_archived = self.current_list == "archived"

        self.edit_button.set_visible(is_project and not is_inbox)
        self.delete_button.set_visible(is_project and not is_inbox)
        self.clear_archived_button.set_visible(is_archived)
        debug.log_event(
            "REFRESH_TASKS",
            f"Button visibility - edit: {is_project and not is_inbox}, delete: {is_project and not is_inbox}, clear: {is_archived}",
        )

    def _clear_project_title_colors(self):
        for color in PROJECT_TEXT_COLORS:
            self.list_title_label.remove_css_class(f"text-color-{color}")

    def _update_list_title(self):
        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project = self.task_manager.get_project_by_id(project_id)
            if not project:
                self.list_title_label.set_text(_("Project not found"))
                debug.log_event("REFRESH_TASKS", f"Project {project_id} not found")
                return

            list_name = project["name"]
            project_color = project["color"]
            self.list_title_label.set_text(list_name)
            self._clear_project_title_colors()
            self.list_title_label.remove_css_class("overdue-title")

            if project_id == "inbox":
                self.list_title_label.remove_css_class("text-color-purple")
                self.list_title_label.add_css_class("text-color-black")
            elif project_color:
                self.list_title_label.add_css_class(f"text-color-{project_color}")

            debug.log_event("REFRESH_TASKS", f"Set project title: {list_name} with color: {project_color}")
            return

        list_name = self.task_manager.lists.get(self.current_list, self.current_list)
        self.list_title_label.set_text(list_name)
        self._clear_project_title_colors()
        if self.current_list == "overdue":
            self.list_title_label.add_css_class("overdue-title")
        else:
            self.list_title_label.remove_css_class("overdue-title")
        debug.log_event("REFRESH_TASKS", f"Set list title: {list_name}")

    def should_group_by_date(self):
        should_group = self.current_list in ["today", "all", "overdue", "archived"]
        debug.log_event("REFRESH_TASKS", f"Should group by date: {should_group} (list: {self.current_list})")
        return should_group

    def create_grouped_task_rows(self, tasks):
        if not tasks:
            debug.log_event("REFRESH_TASKS", "No tasks for grouped rows")
            return

        grouped_tasks = self.group_tasks_by_date(tasks)
        debug.log_event("REFRESH_TASKS", f"Grouped into {len(grouped_tasks)} date groups")
        for date_key, date_tasks in grouped_tasks.items():
            if not (self.current_list == "today" and date_key == "hoy"):
                self.task_list.append(self.create_date_header(date_key))
                debug.log_event("REFRESH_TASKS", f"Added date header: {date_key}")

            for task in date_tasks:
                self.task_list.append(self.create_task_row(task))
                debug.log_event(
                    "REFRESH_TASKS",
                    f"Added task row: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})",
                )

    def create_standard_task_rows(self, tasks):
        debug.log_event("REFRESH_TASKS", f"Creating {len(tasks)} standard task rows")
        for task in tasks:
            self.task_list.append(self.create_task_row(task))
            debug.log_event("REFRESH_TASKS", f"Added task row: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})")

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

            grouped.setdefault(date_key, []).append(task)
        return self.sort_date_groups(grouped)

    def sort_date_groups(self, grouped):
        sorted_groups = OrderedDict()
        keys = list(grouped.keys())
        past_days = [key for key in keys if key.startswith("hace_")]
        future_days = [key for key in keys if key.startswith("en_")]
        today_key = "hoy" if "hoy" in keys else None
        no_date_key = "sin_fecha" if "sin_fecha" in keys else None

        past_days.sort(key=lambda value: int(value.split("_")[1]))
        future_days.sort(key=lambda value: int(value.split("_")[1]))

        group_order = []
        if self.sort_ascending:
            group_order.extend(reversed(past_days))
            if today_key:
                group_order.append(today_key)
            group_order.extend(future_days)
        else:
            group_order.extend(reversed(future_days))
            if today_key:
                group_order.append(today_key)
            group_order.extend(past_days)

        if no_date_key:
            group_order.append(no_date_key)

        for key in group_order:
            sorted_groups[key] = grouped[key]
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
        header_row.add_css_class("date-header-row")

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
                date_key = "9999-12-31T23:59:59" if self.sort_ascending else "0000-01-01T00:00:00"
            else:
                date_key = effective_date
            return (date_key, sort_order)

        return sorted(tasks, key=get_sort_key, reverse=not self.sort_ascending)

    @debug_method("create_task_row")
    def create_task_row(self, task):
        debug.log_event("CREATE_ROW", f"Creating row for task: {task.get('title', 'unknown')} (ID: {task.get('id', 'unknown')})")

        row = Adw.ActionRow()
        task_id = task.get("id")
        if task_id is not None:
            row.set_name(str(task_id))
        else:
            debug.log_event("CREATE_ROW", f"WARNING: Task has no ID: {task}")

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
            return Gdk.ContentProvider.new_for_value(task["id"])

        def drag_begin(source, drag):
            paintable = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).lookup_icon(
                "drag-surface-symbolic", None, 24, 1, Gtk.TextDirection.NONE, 0
            )
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

        subtasks = task.get("subtasks", [])
        if subtasks:
            completed_subtasks = sum(1 for subtask in subtasks if subtask.get("completed", False))
            row.set_subtitle(_("Subtasks: {}/{}").format(completed_subtasks, len(subtasks)))

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
            debug.log_event("FAVORITE_CLICK", f"Favorite clicked for task {task.get('id')}: {task.get('title')}")
            self.on_toggle_favorite(task)

        star_button.connect("clicked", toggle_favorite_handler)
        row.add_suffix(star_button)

        drop_target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        drop_target.connect("drop", lambda target, value, x, y: self.on_task_reorder(value, task["id"]))
        row.add_controller(drop_target)

        debug.log_event("CREATE_ROW", f"Row created successfully for task {task.get('id')}")
        return row

    @debug_method("on_task_toggle")
    def on_task_toggle(self, task):
        debug.log_event("TASK_TOGGLE", f"Toggling completion for task {task.get('id')}: '{task.get('title', 'unknown')}'")
        updated_task = self.task_manager.toggle_task_completed(task.get("id"))
        if updated_task:
            debug.log_event("TASK_TOGGLE", f"Task completion changed to {updated_task.get('completed', False)}")
            self.refresh_task_list()
            self.refresh_sidebar()

    @debug_method("on_toggle_favorite")
    def on_toggle_favorite(self, task):
        task_id = task.get("id", "unknown")
        task_title = task.get("title", "unknown")
        debug.log_event("FAVORITE_TOGGLE", f"Starting favorite toggle for task {task_id}: '{task_title}'")

        if hasattr(self, "_updating_favorite") and self._updating_favorite:
            debug.log_event("FAVORITE_TOGGLE", f"Already updating favorite for task {task_id}, skipping")
            return

        try:
            self._updating_favorite = True
            current_favorite = task.get("favorite", False)
            updated_task = self.task_manager.toggle_task_favorite(task_id)
            if not updated_task:
                return

            new_favorite = updated_task.get("favorite", False)
            debug.log_event("FAVORITE_TOGGLE", f"Task {task_id} favorite changing from {current_favorite} to {new_favorite}")
            new_state = _("added to") if new_favorite else _("removed from")
            print(f"{_('Task')} '{task_title}' {new_state} {_('favorites')}")
            GLib.idle_add(self._delayed_refresh_after_favorite, task_id, task_title, new_favorite)
        except Exception as exc:
            debug.log_event("FAVORITE_TOGGLE", f"ERROR in on_toggle_favorite for task {task_id}: {exc}", stack_info=True)
        finally:
            self._updating_favorite = False

    def _delayed_refresh_after_favorite(self, task_id, task_title, is_favorite):
        try:
            debug.log_event("FAVORITE_REFRESH", f"Delayed refresh after favorite toggle for task {task_id}: '{task_title}'")
            self._verify_ui_state("before_favorite_refresh")
            self.refresh_sidebar()
            self.refresh_task_list()
            self._verify_ui_state("after_favorite_refresh")
            debug.log_event("FAVORITE_REFRESH", f"Delayed refresh completed for task {task_id}")
        except Exception as exc:
            debug.log_event("FAVORITE_REFRESH", f"ERROR in delayed refresh for task {task_id}: {exc}", stack_info=True)
            self._recover_from_ui_error()
        return False

    def _verify_ui_state(self, context):
        try:
            debug.log_event("UI_STATE", f"=== UI STATE VERIFICATION ({context}) ===")
            debug.log_event("UI_STATE", f"Current list: {self.current_list}")
            debug.log_event(
                "UI_STATE",
                f"Task info panel visible: {getattr(self, 'task_info_panel', None) and self.task_info_panel.get_visible()}",
            )
            debug.log_event("UI_STATE", f"Current task info: {self.current_task_info.get('title') if self.current_task_info else None}")
            debug.log_event("UI_STATE", f"Window size: {self.get_width()}x{self.get_height()}")
            debug.log_event("UI_STATE", f"Total tasks: {len(self.task_manager.tasks.get('all_tasks', []))}")
            debug.log_event("UI_STATE", f"UI state valid: {getattr(self, '_ui_state_valid', True)}")
            debug.log_event("UI_STATE", f"Refresh in progress: {getattr(self, '_refresh_in_progress', False)}")
            debug.log_event("UI_STATE", f"Updating favorite: {getattr(self, '_updating_favorite', False)}")
            debug.log_event("UI_STATE", "================================")
        except Exception as exc:
            debug.log_event("UI_STATE", f"Error verifying UI state: {exc}")

    def _recover_from_ui_error(self):
        debug.log_event("RECOVERY", "Attempting UI error recovery")
        try:
            self._refresh_in_progress = False
            self._updating_favorite = False
            self._refreshing_sidebar = False
            self._in_cleanup = False

            if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
                self.on_close_task_info(None)

            self.current_task_info = None
            GLib.idle_add(self._safe_ui_refresh)
            debug.log_event("RECOVERY", "UI recovery initiated")
        except Exception as exc:
            debug.log_event("RECOVERY", f"ERROR in UI recovery: {exc}")

    def _safe_ui_refresh(self):
        try:
            debug.log_event("SAFE_REFRESH", "Starting safe UI refresh")
            self.refresh_task_list()
            self.refresh_sidebar()
            debug.log_event("SAFE_REFRESH", "Safe UI refresh completed")
        except Exception as exc:
            debug.log_event("SAFE_REFRESH", f"Error in safe refresh: {exc}")
        return False

    @debug_method("on_task_reorder")
    def on_task_reorder(self, dragged_task_id, target_task_id):
        debug.log_event("REORDER", f"Reordering: drag {dragged_task_id} to target {target_task_id}")
        if dragged_task_id == target_task_id:
            debug.log_event("REORDER", "Same task, no reorder needed")
            return False

        if self.task_manager.reorder_task(dragged_task_id, target_task_id, self.current_list):
            self.refresh_task_list()
            debug.log_event("REORDER", "Task reorder completed")
            return True

        debug.log_event("REORDER", "Reorder rejected by service")
        return False

    @debug_method("on_new_task_entry_activate")
    def on_new_task_entry_activate(self, entry):
        text = entry.get_text().strip()
        debug.log_event("NEW_TASK", f"Creating new task: '{text}'")
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

        if self.current_list.startswith("project_"):
            project_id = self.current_list.replace("project_", "")
            project = self.task_manager.get_project_by_id(project_id)
            project_name = project["name"] if project else _("Inbox")
        else:
            inbox_project = self.task_manager.get_inbox_project()
            project_name = inbox_project["name"] if inbox_project else _("Inbox")

        debug.log_event("NEW_TASK", f"Adding to project: {project_name}, Date: {effective_date}")
        self.task_manager.add_task(list_to_add, text, project=project_name, effective_date=effective_date)
        entry.set_text("")
        self.refresh_task_list()
        self.refresh_sidebar()
        debug.log_event("NEW_TASK", "New task created successfully")
