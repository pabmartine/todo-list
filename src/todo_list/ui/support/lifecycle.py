from gi.repository import Gtk

from ...debug import debug, debug_method


class WindowLifecycleMixin:
    def _cleanup_ui_state(self):
        if self._in_cleanup:
            debug.log_event("CLEANUP", "Already in cleanup, skipping")
            return

        self._in_cleanup = True
        debug.log_event("CLEANUP", "Starting UI state cleanup")
        try:
            if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
                debug.log_event("CLEANUP", "Closing task info panel")
                self.on_close_task_info(None)

            if hasattr(self, "current_task_info") and self.current_task_info:
                debug.log_event("CLEANUP", f"Clearing current task info: {self.current_task_info.get('title', 'unknown')}")
                self.current_task_info = None

            if hasattr(self, "task_list"):
                self.task_list.unselect_all()
                debug.log_event("CLEANUP", "Cleared task list selection")

            debug.log_event("CLEANUP", "UI state cleanup completed")
        except Exception as exc:
            debug.log_event("CLEANUP", f"Error during cleanup: {exc}")
        finally:
            self._in_cleanup = False

    @debug_method("on_window_close")
    def on_window_close(self, window):
        debug.log_event("WINDOW", "Window closing, saving configuration")
        width = self.get_width()
        height = self.get_height()
        self.config.set("window_width", width)
        self.config.set("window_height", height)
        self.config.set("current_list", self.current_list)
        debug.log_event("WINDOW", f"Saved config: size={width}x{height}, list={self.current_list}")
        return False

    @debug_method("initialize_sample_data")
    def initialize_sample_data(self):
        debug.log_event("INIT", "Initializing sample data")
        self.ensure_inbox_project()

        all_tasks = self.task_manager.tasks.get("all_tasks", [])
        changed = self.task_manager.ensure_task_defaults()
        if not all_tasks:
            debug.log_event("INIT", "No existing tasks, would create sample data here")
        else:
            debug.log_event("INIT", f"Found {len(all_tasks)} existing tasks")
            if changed:
                debug.log_event("INIT", "Persisted missing task defaults")

    def setup_shortcuts(self):
        debug.log_event("UI", "Setting up keyboard shortcuts")
        shortcuts = [("<Control>n", self.on_add_task_shortcut)]
        controller = Gtk.ShortcutController()
        for trigger, callback in shortcuts:
            shortcut = Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(trigger))
            action = Gtk.CallbackAction.new(callback)
            shortcut.set_action(action)
            controller.add_shortcut(shortcut)
        self.add_controller(controller)

    def on_add_task_shortcut(self, widget, args):
        debug.log_event("SHORTCUT", "Ctrl+N pressed, focusing new task entry")
        if hasattr(self, "new_task_entry"):
            self.new_task_entry.grab_focus()
        return True
