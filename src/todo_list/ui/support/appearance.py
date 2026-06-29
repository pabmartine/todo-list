from gi.repository import Gdk, Gio, Gtk

from ...core.debug import debug
from ...core.i18n import setup_locale, translate as _
from ..styles import APP_CSS


class WindowAppearanceMixin:
    def recreate_ui(self):
        debug.log_event("UI", "Recreating UI with updated texts")

        self.set_title(_("Todo List"))
        if hasattr(self, "sidebar_page"):
            self.sidebar_page.set_title(_("Lists"))
        if hasattr(self, "content_page"):
            self.content_page.set_title(_("Todo List"))
        if hasattr(self, "projects_label"):
            self.projects_label.set_text(_("Projects"))

        if hasattr(self, "new_list_btn"):
            self.new_list_btn.set_tooltip_text(_("Add Project"))
        if hasattr(self, "new_task_entry"):
            self.new_task_entry.set_placeholder_text(_("New task..."))
        if hasattr(self, "search_entry"):
            self.search_entry.set_placeholder_text(_("Search tasks..."))
        if hasattr(self, "clear_archived_button"):
            self.clear_archived_button.set_tooltip_text(_("Clear all archived tasks"))

        if hasattr(self, "menu_model"):
            self.menu_model.remove_all()
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

        self.refresh_sidebar()
        self.refresh_task_list()
        debug.log_event("UI", "UI recreation completed")

    def setup_custom_css(self):
        debug.log_event("UI", "Setting up custom CSS")
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(APP_CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        debug.log_event("UI", "Custom CSS loaded successfully")

    def change_language(self, language_code):
        debug.log_event("WINDOW", f"Changing language to: {language_code}")
        setup_locale(language_code if language_code != "auto" else None)
        self.config.set("language", language_code)
        self.current_language = language_code
        self.task_manager.update_list_names()
        self.task_manager.update_project_names()
        self.task_manager.clean_duplicate_inboxes()
        self.task_manager.save_tasks()
        self.recreate_ui()
