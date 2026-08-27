from gi.repository import Adw, Gio, GLib, Gtk

from ...core.debug import debug, debug_method
from ...core.i18n import translate as _, translate_plural as ngettext


def _json_filters():
    json_filter = Gtk.FileFilter()
    json_filter.set_name(_("JSON files"))
    json_filter.add_mime_type("application/json")
    json_filter.add_suffix("json")

    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(json_filter)
    return filters, json_filter


class WindowDataActionsMixin:
    @debug_method("on_clear_archived_tasks")
    def on_clear_archived_tasks(self, button):
        archived_tasks = self.task_manager.get_tasks("archived")
        if not archived_tasks:
            self.show_toast(_("There are no archived tasks"))
            return

        dialog = Adw.AlertDialog.new(
            _("Clear Archived Tasks?"),
            ngettext(
                "The archived task will be permanently deleted.",
                "All {} archived tasks will be permanently deleted.",
                len(archived_tasks),
            ).format(len(archived_tasks)),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete All"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_clear_archived_confirmation)
        dialog.present(self)

    def on_clear_archived_confirmation(self, dialog, response):
        debug.log_event("CLEAR_ARCHIVED", f"Dialog response: {response}")
        if response != "delete":
            return

        deleted_count = self.task_manager.clear_archived_tasks()
        self.close_task_details()
        self.refresh_task_list()
        self.refresh_sidebar()
        self.show_toast(
            ngettext("{} archived task deleted", "{} archived tasks deleted", deleted_count).format(
                deleted_count
            )
        )

    def show_export_dialog(self):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export Tasks"))
        dialog.set_initial_name("todo-list-backup.json")
        filters, default_filter = _json_filters()
        dialog.set_filters(filters)
        dialog.set_default_filter(default_filter)
        dialog.save(self, None, self._on_export_finished)

    def _on_export_finished(self, dialog, result):
        try:
            export_file = dialog.save_finish(result)
        except GLib.Error as error:
            # Dismissing the file chooser is not an error worth reporting.
            if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                debug.log_event("EXPORT", f"Export failed: {error.message}")
                self.show_toast(_("Could not export tasks"))
            return

        if not export_file:
            return

        try:
            self.task_manager.export_data(export_file.get_path())
            self.show_toast(_("Tasks exported"))
        except Exception as exc:
            debug.log_event("EXPORT", f"Export failed: {exc}", stack_info=True)
            self.show_toast(_("Could not export tasks"))

    def show_import_dialog(self):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Import Tasks"))
        filters, default_filter = _json_filters()
        dialog.set_filters(filters)
        dialog.set_default_filter(default_filter)
        dialog.open(self, None, self._on_import_finished)

    def _on_import_finished(self, dialog, result):
        try:
            import_file = dialog.open_finish(result)
        except GLib.Error as error:
            if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                debug.log_event("IMPORT", f"Import failed: {error.message}")
                self.show_toast(_("Could not import tasks"))
            return

        if not import_file:
            return

        try:
            self.task_manager.import_data(import_file.get_path())
        except Exception as exc:
            debug.log_event("IMPORT", f"Import failed: {exc}", stack_info=True)
            self.show_toast(_("Could not import tasks"))
            return

        self.search_query = ""
        if hasattr(self, "search_entry"):
            self.search_entry.set_text("")
        self.close_task_details()
        self.refresh_sidebar()
        self.refresh_task_list()
        self.show_toast(_("Tasks imported"))
