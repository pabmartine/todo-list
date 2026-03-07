APP_CSS = """
window {
    background-color: @window_bg_color;
}

.boxed-list {
    background-color: transparent;
    border: none;
    border-radius: 0px;
}

.boxed-list > row {
    margin-bottom: 0px;
    background-color: transparent;
    border: none;
    padding: 8px 12px;
    border-radius: 0px;
    transition: background-color 0.2s ease;
}

.boxed-list > row:not(.date-header-row):hover {
    background-color: rgba(0, 0, 0, 0.05);
}

.boxed-list > row.date-header-row:hover {
    background-color: transparent !important;
}

.boxed-list > row:first-child {
    border-top: none;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
}

.boxed-list > row:last-child {
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}

.boxed-list > row:only-child {
    border-radius: 0px;
    border: none;
}

.date-header {
    font-size: 12px;
    opacity: 0.7;
}

.date-header-past {
    color: #dc2626;
    font-weight: bold;
    opacity: 1;
}

.date-header-today {
    color: #2563eb;
    font-weight: bold;
    opacity: 1;
}

.date-header-future {
    color: #16a34a;
    font-weight: bold;
    opacity: 1;
}

adw-action-row {
    min-height: 44px;
}

adw-action-row .title {
    font-size: 14px;
    font-weight: normal;
}

.new-task-entry {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    border: 1px solid alpha(@borders, 0.3);
    box-shadow: none;
    padding: 8px 12px;
    margin-top: 6px;
    font-size: 14px;
}

.new-task-entry image {
    opacity: 0.6;
    margin-right: 8px;
}

.title-1 {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 16px;
    margin-top: 8px;
    background-color: transparent;
}

.overdue-title {
    color: @error_color;
}

.drag-handle-icon {
    opacity: 0.4;
    margin-right: 8px;
}

.caption {
    font-size: 12px;
    opacity: 0.7;
}

.dim-label {
    opacity: 0.6;
}

button.flat {
    min-height: 48px !important;
    min-width: 48px !important;
    padding: 12px !important;
}

.task-checkbox {
    padding: 0;
    min-height: 12px !important;
    min-width: 12px !important;
    -gtk-icon-size: 12px !important;
}

.task-checkbox check {
    min-height: 12px !important;
    min-width: 12px !important;
    border-radius: 3px !important;
    margin: 0 !important;
    border-width: 1px;
}

.boxed-list .task-checkbox check {
    min-height: 12px !important;
    min-width: 12px !important;
}

.sidebar {
    border-right: 1px solid @borders;
    background-color: rgba(0, 0, 0, 0.03);
}

.navigation-sidebar {
    background-color: transparent;
}

.navigation-sidebar row {
    border-radius: 6px;
}

.project-color {
    border-radius: 4px;
    min-width: 16px;
    min-height: 10px;
    margin-right: 8px;
}

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

.color-button.selected-color {
    border: 3px solid @accent_color;
}

.color-purple { background-color: #9333ea; }
.color-orange { background-color: #ea580c; }
.color-blue { background-color: #2563eb; }
.color-green { background-color: #16a34a; }
.color-yellow { background-color: #ca8a04; }
.color-red { background-color: #dc2626; }
.color-pink { background-color: #ec4899; }
.color-cyan { background-color: #06b6d4; }
.color-teal { background-color: #14b8a6; }
.color-lime { background-color: #84cc16; }
.color-amber { background-color: #f59e0b; }
.color-indigo { background-color: #4f46e5; }
.color-violet { background-color: #a855f7; }
.color-magenta { background-color: #d946ef; }
.color-olive { background-color: #6b7280; }
.color-gray { background-color: #718096; }
.color-brown { background-color: #8B4513; }
.color-gold { background-color: #FFD700; }
.color-silver { background-color: #C0C0C0; }
.color-maroon { background-color: #800000; }
.color-navy { background-color: #000080; }
.color-turquoise { background-color: #40E0D0; }
.color-coral { background-color: #FF7F50; }
.color-sky { background-color: #87CEEB; }
.color-emerald { background-color: #2E8B57; }
.color-ruby { background-color: #E0115F; }
.color-black { background-color: #000000; }

.text-color-purple { color: #9333ea; }
.text-color-orange { color: #ea580c; }
.text-color-blue { color: #2563eb; }
.text-color-green { color: #16a34a; }
.text-color-yellow { color: #ca8a04; }
.text-color-red { color: #dc2626; }
.text-color-pink { color: #ec4899; }
.text-color-cyan { color: #06b6d4; }
.text-color-teal { color: #14b8a6; }
.text-color-lime { color: #84cc16; }
.text-color-amber { color: #f59e0b; }
.text-color-indigo { color: #4f46e5; }
.text-color-violet { color: #a855f7; }
.text-color-magenta { color: #d946ef; }
.text-color-olive { color: #6b7280; }
.text-color-gray { color: #718096; }
.text-color-brown { color: #8B4513; }
.text-color-gold { color: #FFD700; }
.text-color-silver { color: #C0C0C0; }
.text-color-maroon { color: #800000; }
.text-color-navy { color: #000080; }
.text-color-turquoise { color: #40E0D0; }
.text-color-coral { color: #FF7F50; }
.text-color-sky { color: #87CEEB; }
.text-color-emerald { color: #2E8B57; }
.text-color-ruby { color: #E0115F; }
.text-color-black { color: #000000; }
"""
