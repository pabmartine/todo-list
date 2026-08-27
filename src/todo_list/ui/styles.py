"""Application specific CSS.

The app's own scoped classes are kept as they were. What was removed are the
rules that redefined *platform* classes, because those leaked out of this app's
widgets: `.boxed-list` (now replaced by the app's own `.task-list`), a global
`button.flat { min-height: 48px !important }` that also inflated every header
bar, and redefinitions of `.title-1`, `.caption` and `.dim-label`.

Hardcoded `rgba(0, 0, 0, ...)` values are expressed against named Adwaita
colours instead: they render the same in the light scheme and stay visible in
the dark one.
"""

APP_CSS = """
/*
 * Task list.
 *
 * A flat list on the window background, which is this app's design. It uses
 * its own class rather than overriding Adwaita's `.boxed-list`: that class
 * draws a bordered card, so cancelling the border and background of a platform
 * class was both fighting the platform and getting the card clipped by the
 * surrounding scrolled window.
 */
.task-list {
    background-color: transparent;
}

.task-list > row {
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 8px 12px;
    transition: background-color 200ms ease;
}

.task-list > row:not(.date-header-row):hover {
    background-color: alpha(@window_fg_color, 0.05);
}

.task-list > row.date-header-row {
    background-color: transparent;
}

/* Date group headings. Sizes are relative so they follow text scaling. */
.date-header {
    font-size: 0.9em;
    opacity: 0.7;
}

.date-header-past {
    color: @error_color;
    font-weight: bold;
    opacity: 1;
}

.date-header-today {
    color: @accent_color;
    font-weight: bold;
    opacity: 1;
}

.date-header-future {
    color: @success_color;
    font-weight: bold;
    opacity: 1;
}

.overdue-title {
    color: @error_color;
}

.new-task-entry {
    background-color: alpha(@window_fg_color, 0.05);
    border-radius: 8px;
    border: 1px solid alpha(@borders, 0.3);
    box-shadow: none;
    padding: 8px 12px;
    margin-top: 6px;
}

.new-task-entry image {
    opacity: 0.6;
    margin-right: 8px;
}

.task-checkbox {
    padding: 0;
    min-height: 12px;
    min-width: 12px;
}

.task-checkbox check {
    min-height: 12px;
    min-width: 12px;
    border-radius: 3px;
    margin: 0;
    border-width: 1px;
}

.drag-handle-icon {
    opacity: 0.4;
    margin-right: 8px;
}

/* Small colour bar that identifies a project. */
.project-color {
    border-radius: 4px;
    min-width: 16px;
    min-height: 10px;
    margin-right: 8px;
}

/* Colour picker used by the add/edit project dialogs. */
.color-button {
    border-radius: 8px;
    min-width: 40px;
    min-height: 40px;
    padding: 0;
    border: 1px solid alpha(@borders, 0.3);
}

.color-button:hover {
    opacity: 0.8;
}

.color-button:checked {
    border: 3px solid @accent_color;
}

/* The description text view sits inside a .card, so it must not paint its own
   view background on top of the card. */
.card textview,
.card textview text {
    background: none;
}

/*
 * Project colours, as stored in the user's data.
 *
 * `black` is the Inbox colour. A literal #000000 was invisible against a dark
 * window background, so it resolves against the foreground colour instead.
 */
.color-black     { background-color: alpha(@window_fg_color, 0.6); }
.color-purple    { background-color: #9333ea; }
.color-orange    { background-color: #ea580c; }
.color-blue      { background-color: #2563eb; }
.color-green     { background-color: #16a34a; }
.color-yellow    { background-color: #ca8a04; }
.color-red       { background-color: #dc2626; }
.color-pink      { background-color: #ec4899; }
.color-cyan      { background-color: #06b6d4; }
.color-teal      { background-color: #14b8a6; }
.color-lime      { background-color: #84cc16; }
.color-amber     { background-color: #f59e0b; }
.color-indigo    { background-color: #4f46e5; }
.color-violet    { background-color: #a855f7; }
.color-magenta   { background-color: #d946ef; }
.color-olive     { background-color: #6b7280; }
.color-gray      { background-color: #718096; }
.color-brown     { background-color: #8B4513; }
.color-gold      { background-color: #FFD700; }
.color-silver    { background-color: #C0C0C0; }
.color-maroon    { background-color: #800000; }
.color-navy      { background-color: #000080; }
.color-turquoise { background-color: #40E0D0; }
.color-coral     { background-color: #FF7F50; }
.color-sky       { background-color: #87CEEB; }
.color-emerald   { background-color: #2E8B57; }
.color-ruby      { background-color: #E0115F; }

.text-color-black     { color: alpha(@window_fg_color, 0.85); }
.text-color-purple    { color: #9333ea; }
.text-color-orange    { color: #ea580c; }
.text-color-blue      { color: #2563eb; }
.text-color-green     { color: #16a34a; }
.text-color-yellow    { color: #ca8a04; }
.text-color-red       { color: #dc2626; }
.text-color-pink      { color: #ec4899; }
.text-color-cyan      { color: #06b6d4; }
.text-color-teal      { color: #14b8a6; }
.text-color-lime      { color: #84cc16; }
.text-color-amber     { color: #f59e0b; }
.text-color-indigo    { color: #4f46e5; }
.text-color-violet    { color: #a855f7; }
.text-color-magenta   { color: #d946ef; }
.text-color-olive     { color: #6b7280; }
.text-color-gray      { color: #718096; }
.text-color-brown     { color: #8B4513; }
.text-color-gold      { color: #FFD700; }
.text-color-silver    { color: #C0C0C0; }
.text-color-maroon    { color: #800000; }
.text-color-navy      { color: #000080; }
.text-color-turquoise { color: #40E0D0; }
.text-color-coral     { color: #FF7F50; }
.text-color-sky       { color: #87CEEB; }
.text-color-emerald   { color: #2E8B57; }
.text-color-ruby      { color: #E0115F; }
"""
