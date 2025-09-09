# Todo List

A modern, feature-rich task management application built with Python and GTK 4, designed for productivity and ease of use.

## Features

### Core Functionality
- **Task Management**: Create, edit, complete, and delete tasks with ease
- **Smart Lists**: Organize tasks by Today, Next 7 days, All, Overdue, Favorites, and Archived
- **Custom Projects**: Create unlimited projects with color-coded organization
- **Date Management**: Set effective dates for tasks with built-in calendar picker
- **Notes & Descriptions**: Add detailed notes to any task
- **Favorites System**: Mark important tasks as favorites for quick access
- **Drag & Drop**: Reorder tasks within lists using intuitive drag and drop

### User Experience
- **Multi-language Support**: Available in English and Spanish with auto-detection
- **Dark/Light Theme**: Toggle between themes to match your preference
- **Responsive Design**: Adapts to different window sizes with collapsible panels
- **Keyboard Shortcuts**: Quick task creation with Ctrl+N
- **Persistent Settings**: Saves window size, theme, and language preferences

### Organization Features
- **Project Color Coding**: 40+ available colors for visual project organization
- **Task Grouping**: Automatic grouping by date in relevant views
- **Sort Options**: Sort tasks by date (ascending/descending)
- **Archive Management**: Completed tasks are automatically archived with bulk delete option
- **Smart Filtering**: Overdue tasks are highlighted and easily accessible

## Screenshots

### Main Interface
The clean, modern interface focuses on productivity while maintaining visual appeal.

### Task Details Panel
Comprehensive task editing with date picker, project assignment, and notes.

### Project Management
Easy project creation and editing with extensive color options.

## Installation

### Prerequisites
- Python 3.8+
- GTK 4.0
- libadwaita 1.0

### On Debian/Ubuntu:
```bash
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### On Fedora:
```bash
sudo dnf install python3 python3-gobject gtk4-devel libadwaita-devel
```

### On Arch Linux:
```bash
sudo pacman -S python python-gobject gtk4 libadwaita
```

### Run the Application
```bash
python3 todo-list.py
```

## Configuration

The application stores its configuration and data in:
- **Linux**: `~/.config/todo-list/`
- **Configuration**: `config.json` (theme, language, window size)
- **Data**: `tasks.json` (tasks and projects)

### Configuration Options
- **Language**: Auto-detect, English, Spanish
- **Theme**: Light or Dark mode
- **Window Size**: Automatically saved and restored
- **Current List**: Remembers last selected view

## Usage

### Creating Tasks
1. Use the "New task..." entry at the bottom of the task list
2. Press Enter to create the task
3. Use Ctrl+N shortcut from anywhere in the application

### Managing Projects
1. Click "Add Project" in the header
2. Choose a name and color
3. Tasks can be assigned to projects in the task detail panel

### Task Details
- Click any task to open the detail panel
- Edit title, set dates, add notes, and change project assignment
- Toggle completion status or mark as favorite

### Keyboard Shortcuts
- **Ctrl+N**: Create new task (focuses the new task entry)

### Smart Lists
- **Today**: Tasks with today's date
- **Next 7 days**: Tasks due in the coming week
- **All**: All incomplete tasks
- **Overdue**: Tasks past their due date
- **Favorites**: Starred tasks for quick access
- **Archived**: Completed tasks

## Development

### Project Structure
- **ConfigManager**: Handles application settings and preferences
- **TaskManager**: Core task and project data management
- **TaskManagerWindow**: Main UI window and interactions
- **TaskManagerApplication**: Application lifecycle and global actions

### Key Features Implementation
- **Internationalization**: Full gettext support with fallback
- **Data Persistence**: JSON-based storage with migration support
- **Theme Management**: Adwaita style manager integration
- **Responsive UI**: Adaptive layouts for different screen sizes

### Adding Translations
1. Extract strings: `xgettext --keyword=_ -o todo-list.pot todo-list.py`
2. Create language file: `msginit -l es -i todo-list.pot`
3. Place in `locale/[lang]/LC_MESSAGES/todo-list.mo`

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

### Areas for Contribution
- Additional language translations
- UI/UX improvements
- Performance optimizations
- New features (tags, search, reminders)
- Bug fixes and testing

## License

This project is licensed under the GPL 3.0 License - see the LICENSE file for details.

## Acknowledgments

- Built with GTK 4 and libadwaita for modern Linux desktop integration
- Inspired by modern task management principles
- Thanks to the GNOME project for excellent UI frameworks

## Roadmap

### Planned Features
- [ ] Task search and filtering
- [ ] Recurring tasks
- [ ] Task reminders/notifications
- [ ] Import/export functionality
- [ ] Task templates
- [ ] Time tracking
- [ ] Sync capabilities

### Version History
- **v1.0.0**: Initial release with core task management features