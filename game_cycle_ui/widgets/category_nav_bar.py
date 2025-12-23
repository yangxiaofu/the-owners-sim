"""
Category Navigation Bar Widget

A horizontal navigation bar with category buttons that show dropdown menus.
Replaces QTabWidget with a scalable, grouped navigation system.

Usage:
    nav_bar = CategoryNavBar()
    nav_bar.view_selected.connect(self._on_view_selected)

    # Phase-based visibility
    nav_bar.set_category_visible("Offseason", False)
    nav_bar.set_item_visible("Game Day", "Playoffs", True)
"""

from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QAction


# Navigation structure with view keys
# Each category has items that map to view keys used in main_window
NAVIGATION_STRUCTURE = {
    "Game Day": {
        "items": [
            ("Season", "season"),
            ("Schedule", "schedule"),
            ("Playoffs", "playoffs"),
        ],
    },
    "My Team": {
        "items": [
            ("Roster", "roster"),
            ("Injuries", "injuries"),
        ],
    },
    "League": {
        "items": [
            ("Standings", "standings"),
            ("Stats", "stats"),
            ("Grades", "grades"),
        ],
    },
    "Front Office": {
        "items": [
            ("Owner", "owner"),
            ("Finances", "finances"),
            ("Inbox", "inbox"),
        ],
    },
    "Media": {
        "items": [
            ("News", "news"),
            ("Transactions", "transactions"),
        ],
    },
    "Offseason": {
        "items": [
            ("Overview", "offseason_overview"),
            ("Season Recap", "season_recap"),
        ],
    },
}

# Ordered list of category names (to maintain consistent order)
CATEGORY_ORDER = [
    "Game Day",
    "My Team",
    "League",
    "Front Office",
    "Media",
    "Offseason",
]


# Stylesheet matching existing ESPN dark theme from theme.py
CATEGORY_NAV_STYLE = """
    QWidget#CategoryNavBar {
        background: #1a1a1a;
        border-bottom: 2px solid #cc0000;
    }
    QToolButton {
        background: #333333;
        color: #888888;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        margin: 4px 2px;
        font-size: 13px;
        font-weight: bold;
    }
    QToolButton:hover {
        background: #3a3a3a;
        color: #ffffff;
    }
    QToolButton:checked {
        background: #444444;
        color: #ffffff;
    }
    QToolButton::menu-indicator {
        image: none;
    }
"""

DROPDOWN_MENU_STYLE = """
    QMenu {
        background: #1a1a1a;
        border: 1px solid #444444;
        border-radius: 4px;
        padding: 4px 0;
    }
    QMenu::item {
        padding: 10px 24px;
        color: #ffffff;
    }
    QMenu::item:selected {
        background: #444444;
    }
    QMenu::item:disabled {
        color: #666666;
    }
    QMenu::separator {
        height: 1px;
        background: #444444;
        margin: 4px 12px;
    }
"""


class CategoryNavBar(QWidget):
    """
    Horizontal navigation bar with category buttons and dropdown menus.

    Signals:
        view_selected(str): Emitted when a menu item is clicked.
            The str is the view key (e.g., "stats", "roster", "offseason_overview").
    """

    view_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CategoryNavBar")
        self.setStyleSheet(CATEGORY_NAV_STYLE)

        # Storage for buttons and menus
        self._buttons: Dict[str, QToolButton] = {}
        self._menus: Dict[str, QMenu] = {}
        self._menu_actions: Dict[str, Dict[str, QAction]] = {}  # category -> {item_name -> action}
        self._current_view: Optional[str] = None
        self._active_menu: Optional[str] = None  # Track which menu is currently open

        # Mapping from view_key to category name for highlighting
        self._view_to_category: Dict[str, str] = {}

        # Badge tracking (for visual indicators like 🔴 urgent, 🔵 action)
        self._category_badges: Dict[str, Optional[str]] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Build the navigation bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(4)

        # Create buttons for each category
        for category_name in CATEGORY_ORDER:
            category_config = NAVIGATION_STRUCTURE.get(category_name, {})
            items = category_config.get("items", [])

            # Create the category button with dropdown arrow in text
            button = QToolButton()
            button.setText(f"{category_name} ▼")
            button.setPopupMode(QToolButton.InstantPopup)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

            # Create the dropdown menu
            menu = QMenu(self)
            menu.setStyleSheet(DROPDOWN_MENU_STYLE)

            # Track actions for this category
            self._menu_actions[category_name] = {}

            # Add items to menu
            for display_name, view_key in items:
                action = menu.addAction(display_name)
                action.setData(view_key)
                action.triggered.connect(
                    lambda checked, vk=view_key: self._on_item_clicked(vk)
                )
                self._menu_actions[category_name][display_name] = action

                # Map view_key to category for highlighting
                self._view_to_category[view_key] = category_name

            button.setMenu(menu)

            # Track menu visibility for hover-switching
            menu.aboutToShow.connect(
                lambda cat=category_name: self._on_menu_show(cat)
            )
            menu.aboutToHide.connect(self._on_menu_hide)

            # Install event filter for hover detection
            button.installEventFilter(self)

            # Store references
            self._buttons[category_name] = button
            self._menus[category_name] = menu

            layout.addWidget(button)

        # Add stretch to push buttons left
        layout.addStretch()

    def _on_menu_show(self, category_name: str):
        """Track when a menu is shown."""
        self._active_menu = category_name

    def _on_menu_hide(self):
        """Track when a menu is hidden."""
        self._active_menu = None

    def eventFilter(self, obj, event):
        """Handle hover events on buttons to switch menus."""
        if event.type() == QEvent.Enter:
            # Check if this is one of our buttons and a menu is currently open
            if self._active_menu is not None:
                for category_name, button in self._buttons.items():
                    if obj == button and category_name != self._active_menu:
                        # Close current menu and open hovered button's menu
                        current_menu = self._menus.get(self._active_menu)
                        if current_menu:
                            current_menu.close()
                        # Show the new menu
                        button.showMenu()
                        break
        return super().eventFilter(obj, event)

    def _on_item_clicked(self, view_key: str):
        """Handle menu item click."""
        self._current_view = view_key
        self._update_button_states()
        self.view_selected.emit(view_key)

    def _update_button_states(self):
        """Update button checked states based on current view."""
        current_category = self._view_to_category.get(self._current_view)

        for category_name, button in self._buttons.items():
            button.setChecked(category_name == current_category)

    def set_category_visible(self, category: str, visible: bool):
        """
        Show or hide an entire category.

        Args:
            category: Category name (e.g., "Offseason")
            visible: True to show, False to hide
        """
        button = self._buttons.get(category)
        if button:
            button.setVisible(visible)

    def set_item_visible(self, category: str, item_name: str, visible: bool):
        """
        Show or hide a specific menu item.

        Args:
            category: Category name (e.g., "Game Day")
            item_name: Item display name (e.g., "Playoffs")
            visible: True to show, False to hide
        """
        actions = self._menu_actions.get(category, {})
        action = actions.get(item_name)
        if action:
            action.setVisible(visible)

    def set_item_enabled(self, category: str, item_name: str, enabled: bool):
        """
        Enable or disable a specific menu item.

        Args:
            category: Category name (e.g., "Game Day")
            item_name: Item display name (e.g., "Playoffs")
            enabled: True to enable, False to disable
        """
        actions = self._menu_actions.get(category, {})
        action = actions.get(item_name)
        if action:
            action.setEnabled(enabled)

    def set_current_view(self, view_key: str):
        """
        Set the current view (highlights the corresponding category).

        Args:
            view_key: The view key (e.g., "stats", "roster")
        """
        self._current_view = view_key
        self._update_button_states()

    def get_current_view(self) -> Optional[str]:
        """Get the currently selected view key."""
        return self._current_view

    def get_category_for_view(self, view_key: str) -> Optional[str]:
        """Get the category name that contains a view key."""
        return self._view_to_category.get(view_key)

    def set_category_badge(self, category: str, badge_type: Optional[str]):
        """
        Add a badge to a category button.

        Args:
            category: Category name (e.g., "Game Day", "Front Office")
            badge_type: "urgent" (red dot 🔴), "action" (blue dot 🔵), or None (remove badge)
        """
        button = self._buttons.get(category)
        if not button:
            return

        # Track badge state
        self._category_badges[category] = badge_type

        # Update button text with appropriate badge
        if badge_type == "urgent":
            button.setText(f"{category} 🔴▼")
        elif badge_type == "action":
            button.setText(f"{category} 🔵▼")
        else:
            button.setText(f"{category} ▼")
