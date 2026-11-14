"""Icon names, with explicit fallbacks.

Most names this app has always used are provided by common desktop icon themes
but are *not* part of Adwaita, and the Flatpak runtime ships only Adwaita plus
hicolor. A bare name therefore looked right in a system install and rendered a
broken-image placeholder in the Flatpak build.

Each entry lists the original name first, so the app keeps its usual look
wherever the icon theme provides it, followed by the Adwaita name to fall back
to. Resolution is done by asking the icon theme directly rather than through
Gio.ThemedIcon, whose multi-name lookup weighs available sizes and so does not
reliably honour the order given.
"""

from gi.repository import Gdk, Gtk


ICON_NAMES = {
    "add": ["ymuse-add-symbolic", "list-add-symbolic"],
    "list-today": ["go-jump-today-symbolic", "task-due-symbolic"],
    "list-next7": ["date-next-symbolic", "x-office-calendar-symbolic"],
    "list-all": ["emblem-documents-symbolic", "view-list-bullet-symbolic"],
    "list-overdue": ["appointment-missed-symbolic"],
    "list-favorites": ["folder-favorites-symbolic", "starred-symbolic"],
    "list-archived": ["archive-symbolic", "checkbox-checked-symbolic"],
    "drag-handle": ["drag-surface-symbolic", "list-drag-handle-symbolic"],
    # The "on" state keeps its original name, which is the filled star the app
    # has always shown. The "off" state does not: it used "favorite-symbolic",
    # which on a system where that also resolves to a filled star (it comes
    # from Breeze here) made the two states indistinguishable.
    # "non-starred-symbolic" is the standard counterpart and is an outline by
    # definition, so the pair is always filled vs outline.
    "star-on": ["folder-favorites-symbolic", "starred-symbolic"],
    "star-off": ["non-starred-symbolic"],
    "folder": ["folder-symbolic"],
    "view-list": ["view-list-bullet-symbolic", "view-list-symbolic"],
    "view-kanban": ["view-column-symbolic", "view-grid-symbolic"],
    "kanban-pending": ["document-open-symbolic", "radio-symbolic", "circle-symbolic"],
    "kanban-progress": ["system-run-symbolic", "media-playback-start-symbolic", "emblem-synchronizing-symbolic"],
    "kanban-completed": ["emblem-ok-symbolic", "task-complete-symbolic", "checkbox-checked-symbolic"],
}

_resolved = {}


def name(key):
    """First name in the chain that the current icon theme actually provides."""
    if key in _resolved:
        return _resolved[key]

    candidates = ICON_NAMES[key]
    chosen = candidates[-1]

    display = Gdk.Display.get_default()
    if display is not None:
        theme = Gtk.IconTheme.get_for_display(display)
        for candidate in candidates:
            if theme.has_icon(candidate):
                chosen = candidate
                break
        _resolved[key] = chosen

    return chosen


def image(key, pixel_size=None):
    img = Gtk.Image.new_from_icon_name(name(key))
    if pixel_size is not None:
        img.set_pixel_size(pixel_size)
    return img
