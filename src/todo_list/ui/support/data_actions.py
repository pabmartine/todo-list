from gi.repository import Adw, Gtk

from ...core.debug import debug, debug_method
from ...core.i18n import translate as _


class WindowDataActionsMixin:
    @debug_method("on_clear_archived_tasks")
    def on_clear_archived_tasks(self, button):
        archived_tasks = self.task_manager.get_tasks("archived")
        if not archived_tasks:
            debug.log_event("CLEAR_ARCHIVED", "No archived tasks to clear")
            return

        debug.log_event("CLEAR_ARCHIVED", f"Showing confirmation dialog for {len(archived_tasks)} tasks")
        dialog = Adw.MessageDialog.new(
            self,
            _("Clear Archived Tasks"),
            _("Are you sure you want to permanently delete all {} archived tasks?").format(len(archived_tasks)),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete All"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_clear_archived_confirmation)
        dialog.present()

    def on_clear_archived_confirmation(self, dialog, response):
        debug.log_event("CLEAR_ARCHIVED", f"Dialog response: {response}")
        if response == "delete":
            deleted_count = self.task_manager.clear_archived_tasks()
            debug.log_event("CLEAR_ARCHIVED", f"Deleted {deleted_count} archived tasks")
            self.refresh_task_list()
            self.refresh_sidebar()
            if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
                self.on_close_task_info(None)
        dialog.close()

    def show_export_dialog(self):
        dialog = Gtk.FileChooserNative.new(
            _("Export tasks"),
            self,
            Gtk.FileChooserAction.SAVE,
            _("Export"),
            _("Cancel"),
        )
        dialog.set_current_name("todo-list-backup.json")
        dialog.connect("response", self.on_export_dialog_response)
        dialog.show()

    def on_export_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            export_file = dialog.get_file()
            if export_file:
                self.task_manager.export_data(export_file.get_path())
        dialog.destroy()

    def show_import_dialog(self):
        dialog = Gtk.FileChooserNative.new(
            _("Import tasks"),
            self,
            Gtk.FileChooserAction.OPEN,
            _("Import"),
            _("Cancel"),
        )
        dialog.connect("response", self.on_import_dialog_response)
        dialog.show()

    def on_import_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            import_file = dialog.get_file()
            if import_file:
                self.task_manager.import_data(import_file.get_path())
                self.search_query = ""
                if hasattr(self, "search_entry"):
                    self.search_entry.set_text("")
                self.refresh_sidebar()
                self.refresh_task_list()
                if hasattr(self, "task_info_panel") and self.task_info_panel.get_visible():
                    self.on_close_task_info(None)
        dialog.destroy()
