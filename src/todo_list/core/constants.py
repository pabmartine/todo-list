APP_ID = "com.pabmartine.TodoList"
APP_NAME = "Todo List"
APP_DOMAIN = "todo-list"
APP_VERSION = "1.4.0"
APP_WEBSITE = "https://github.com/pabmartine/todo-list"
APP_ISSUE_URL = "https://github.com/pabmartine/todo-list/issues"
APP_COPYRIGHT = "© 2025"

SMART_LIST_IDS = (
    "today",
    "next7",
    "all",
    "overdue",
    "favorites",
    "archived",
)

PROJECT_COLORS = [
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
    "black",
]

DEFAULT_CONFIG = {
    "language": "auto",
    # "color_scheme" is deliberately absent: when it is missing, the window
    # migrates the old boolean "dark_theme" key and otherwise falls back to
    # "default", which follows the system preference as the HIG asks.
    "window_width": 1200,
    "window_height": 800,
    "current_list": "today",
}
