import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from .constants import APP_ID, APP_NAME, APP_COPYRIGHT, APP_VERSION, APP_WEBSITE
from .debug import debug, debug_method
from .i18n import translate as _
from .ui.window import TaskManagerWindow


class TaskManagerApplication(Adw.Application):
    def __init__(self):
        debug.log_event("APP", "Initializing TaskManagerApplication")
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self.on_activate)
        self.setup_actions()
        debug.log_event("APP", "TaskManagerApplication initialized")

    @debug_method("setup_actions")
    def setup_actions(self):
        language_action = Gio.SimpleAction.new_stateful(
            "language", GLib.VariantType.new("s"), GLib.Variant("s", "auto")
        )
        language_action.connect("activate", self.on_language_changed)
        self.add_action(language_action)

        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences)
        self.add_action(preferences_action)

        import_action = Gio.SimpleAction.new("import", None)
        import_action.connect("activate", self.on_import)
        self.add_action(import_action)

        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", self.on_export)
        self.add_action(export_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

    @debug_method("on_language_changed")
    def on_language_changed(self, action, parameter):
        language_code = parameter.get_string()
        action.set_state(parameter)
        if hasattr(self, "win"):
            self.win.change_language(language_code)

    @debug_method("on_preferences")
    def on_preferences(self, action, parameter):
        if hasattr(self, "win"):
            self.show_preferences_dialog()

    def on_import(self, action, parameter):
        if hasattr(self, "win"):
            self.win.show_import_dialog()

    def on_export(self, action, parameter):
        if hasattr(self, "win"):
            self.win.show_export_dialog()

    def show_preferences_dialog(self):
        dialog = Adw.PreferencesWindow()
        dialog.set_title(_("Preferences"))
        dialog.set_modal(True)
        dialog.set_transient_for(self.win)

        page = Adw.PreferencesPage()
        page.set_title(_("General"))

        language_group = Adw.PreferencesGroup()
        language_group.set_title(_("Language"))
        language_row = Adw.ComboRow()
        language_row.set_title(_("Interface Language"))
        language_model = Gtk.StringList()
        language_model.append(_("Auto-detect"))
        language_model.append(_("English"))
        language_model.append(_("Spanish"))
        language_row.set_model(language_model)

        current_lang = self.win.current_language
        if current_lang == "auto":
            language_row.set_selected(0)
        elif current_lang == "en":
            language_row.set_selected(1)
        elif current_lang == "es":
            language_row.set_selected(2)

        language_row.connect("notify::selected", self.on_language_row_changed)
        language_group.add(language_row)
        page.add(language_group)

        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title(_("Appearance"))
        dark_theme_row = Adw.SwitchRow()
        dark_theme_row.set_title(_("Dark Theme"))
        dark_theme_row.set_subtitle(_("Use dark theme for the application"))
        dark_theme_row.set_active(self.win.config.get("dark_theme", False))
        dark_theme_row.connect("notify::active", self.on_theme_changed)
        appearance_group.add(dark_theme_row)
        page.add(appearance_group)

        dialog.add(page)
        dialog.present()

    def on_theme_changed(self, switch_row, param):
        self.win.change_theme(switch_row.get_active())

    def on_language_row_changed(self, combo_row, param):
        selected = combo_row.get_selected()
        language_codes = ["auto", "en", "es"]
        if selected < len(language_codes):
            action = self.lookup_action("language")
            if action:
                action.activate(GLib.Variant("s", language_codes[selected]))

    @debug_method("on_about")
    def on_about(self, action, parameter):
        about_dialog = Adw.AboutWindow()
        about_dialog.set_transient_for(self.win)
        about_dialog.set_modal(True)
        about_dialog.set_application_name(_(APP_NAME))
        about_dialog.set_application_icon(APP_ID)
        about_dialog.set_version(APP_VERSION)
        about_dialog.set_developer_name("pabmartine")
        about_dialog.set_copyright(APP_COPYRIGHT)
        about_dialog.set_comments(_("A simple and powerful task management application"))
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        about_dialog.set_developers(["pabmartine"])
        about_dialog.set_website(APP_WEBSITE)
        about_dialog.present()

    @debug_method("on_activate")
    def on_activate(self, app):
        self.win = TaskManagerWindow(application=app)
        self.win.present()
