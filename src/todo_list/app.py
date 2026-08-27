import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from .core.constants import APP_ID, APP_NAME, APP_COPYRIGHT, APP_ISSUE_URL, APP_VERSION, APP_WEBSITE
from .core.debug import debug, debug_method
from .core.i18n import translate as _
from .ui.window import TaskManagerWindow


COLOR_SCHEMES = ["default", "light", "dark"]
LANGUAGE_CODES = ["auto", "en", "es"]


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

        for name, callback in (
            ("preferences", self.on_preferences),
            ("import", self.on_import),
            ("export", self.on_export),
            ("shortcuts", self.on_shortcuts),
            ("about", self.on_about),
            ("quit", self.on_quit),
            ("close-window", self.on_close_window),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # Standard GNOME accelerators.
        for action_name, accels in (
            ("app.preferences", ["<Control>comma"]),
            ("app.shortcuts", ["<Control>question"]),
            ("app.quit", ["<Control>q"]),
            ("app.close-window", ["<Control>w"]),
        ):
            self.set_accels_for_action(action_name, accels)

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

    def on_quit(self, action, parameter):
        self.quit()

    def on_close_window(self, action, parameter):
        if hasattr(self, "win"):
            self.win.close()

    def show_preferences_dialog(self):
        dialog = Adw.PreferencesDialog()

        page = Adw.PreferencesPage(title=_("General"))

        appearance_group = Adw.PreferencesGroup(title=_("Appearance"))
        # Three states, so "follow the system" is expressible. The previous
        # boolean switch could not represent it.
        self.color_scheme_row = Adw.ComboRow(title=_("Style"))
        scheme_model = Gtk.StringList()
        for label in (_("Follow System"), _("Light"), _("Dark")):
            scheme_model.append(label)
        self.color_scheme_row.set_model(scheme_model)
        self.color_scheme_row.set_selected(COLOR_SCHEMES.index(self.win.get_color_scheme()))
        self.color_scheme_row.connect("notify::selected", self.on_color_scheme_row_changed)
        appearance_group.add(self.color_scheme_row)
        page.add(appearance_group)

        language_group = Adw.PreferencesGroup(title=_("Language"))
        language_row = Adw.ComboRow(title=_("Interface Language"))
        language_model = Gtk.StringList()
        for label in (_("Auto-detect"), _("English"), _("Spanish")):
            language_model.append(label)
        language_row.set_model(language_model)

        current_lang = self.win.current_language
        language_row.set_selected(
            LANGUAGE_CODES.index(current_lang) if current_lang in LANGUAGE_CODES else 0
        )
        language_row.connect("notify::selected", self.on_language_row_changed)
        language_group.add(language_row)
        page.add(language_group)

        dialog.add(page)
        dialog.present(self.win)

    def on_color_scheme_row_changed(self, combo_row, param):
        selected = combo_row.get_selected()
        if selected < len(COLOR_SCHEMES):
            self.win.change_color_scheme(COLOR_SCHEMES[selected])

    def on_language_row_changed(self, combo_row, param):
        selected = combo_row.get_selected()
        if selected < len(LANGUAGE_CODES):
            action = self.lookup_action("language")
            if action:
                action.activate(GLib.Variant("s", LANGUAGE_CODES[selected]))

    @debug_method("on_shortcuts")
    def on_shortcuts(self, action, parameter):
        """Keyboard shortcuts window, which the HIG lists as a standard item."""
        dialog = Adw.ShortcutsDialog()

        general = Adw.ShortcutsSection(title=_("General"))
        for title, accelerator in (
            (_("New Task"), "<Control>n"),
            (_("Search"), "<Control>f"),
            (_("Preferences"), "<Control>comma"),
            (_("Keyboard Shortcuts"), "<Control>question"),
            (_("Close Window"), "<Control>w"),
            (_("Quit"), "<Control>q"),
        ):
            general.add(Adw.ShortcutsItem(title=title, accelerator=accelerator))
        dialog.add(general)

        tasks = Adw.ShortcutsSection(title=_("Tasks"))
        tasks.add(Adw.ShortcutsItem(title=_("Close Task Details"), accelerator="Escape"))
        dialog.add(tasks)

        dialog.present(self.win)

    @debug_method("on_about")
    def on_about(self, action, parameter):
        about = Adw.AboutDialog(
            application_name=_(APP_NAME),
            application_icon=APP_ID,
            version=APP_VERSION,
            developer_name="pabmartine",
            copyright=APP_COPYRIGHT,
            comments=_("A simple and powerful task management application"),
            license_type=Gtk.License.GPL_3_0,
            website=APP_WEBSITE,
            issue_url=APP_ISSUE_URL,
        )
        about.set_developers(["pabmartine"])
        # Lets translators credit themselves; gettext resolves it per locale.
        translator_credits = _("translator-credits")
        if translator_credits != "translator-credits":
            about.set_translator_credits(translator_credits)
        about.present(self.win)

    @debug_method("on_activate")
    def on_activate(self, app):
        self.win = TaskManagerWindow(application=app)
        self.win.present()
