import gettext
import locale
import os
from pathlib import Path

from .constants import APP_DOMAIN
from .debug import debug


def _fallback_ngettext(singular, plural, n):
    return singular if n == 1 else plural


_current_gettext = lambda text: text
_current_ngettext = _fallback_ngettext


def get_locale_dir():
    project_locale = Path(__file__).resolve().parents[3] / "locale"
    possible_dirs = [
        Path("/app/share/locale"),
        project_locale,
        Path("/usr/share/locale"),
    ]

    for locale_dir in possible_dirs:
        if locale_dir.exists():
            return str(locale_dir)

    return str(project_locale)


def setup_locale(language=None):
    global _current_gettext, _current_ngettext

    debug.log_event("LOCALE", f"Setting up locale: {language}")

    if language and language != "auto":
        try:
            os.environ["LANGUAGE"] = language
            os.environ["LC_MESSAGES"] = language
        except Exception:
            pass

    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, "C.UTF-8")
        except locale.Error:
            pass

    try:
        locale_dir = "/app/share/locale" if (Path("/app").exists() or os.environ.get("FLATPAK_ID")) else get_locale_dir()

        if os.path.exists(locale_dir):
            translations = gettext.translation(APP_DOMAIN, locale_dir, fallback=True)
            translations.install()
            _current_gettext = translations.gettext
            _current_ngettext = translations.ngettext
            debug.log_event("LOCALE", "Translations loaded successfully")
            return _current_gettext

        debug.log_event("LOCALE", "No translations found, using fallback")
    except Exception as exc:
        debug.log_event("LOCALE", f"Error setting up locale: {exc}")

    _current_gettext = lambda text: text
    _current_ngettext = _fallback_ngettext
    return _current_gettext


def translate(text):
    return _current_gettext(text)


def translate_plural(singular, plural, n):
    """Pick the right plural form for `n`.

    Needed because a phrase cannot be assembled from separately translated
    fragments: `_('day' if n == 1 else 'days')` is not even extractable by
    xgettext, so those fragments never reached the catalogues.
    """
    return _current_ngettext(singular, plural, n)


setup_locale()
