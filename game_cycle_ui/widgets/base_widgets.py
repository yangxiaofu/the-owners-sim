"""
Base Widget Classes - Standardized patterns for common widget types.

Provides abstract base classes for consistent widget architecture:
- ReadOnlyDataWidget: Widgets that display data without user interaction
- Consistent styling, header creation, and error handling patterns
"""

from abc import ABCMeta, abstractmethod
from PySide6.QtWidgets import QFrame, QLabel
from PySide6.QtCore import Qt
from game_cycle_ui.theme import Typography, ESPN_THEME, TextColors


# Custom metaclass that combines Qt's metaclass with ABCMeta
class QABCMeta(type(QFrame), ABCMeta):
    """Metaclass that combines Qt's metaclass with ABC's metaclass."""
    pass


class ReadOnlyDataWidget(QFrame, metaclass=QABCMeta):
    """
    Base class for widgets that display data without user interaction.

    Features:
    - Standardized card styling
    - Consistent section headers
    - Abstract _setup_ui() for subclass implementation

    Usage:
        class MyWidget(ReadOnlyDataWidget):
            def _setup_ui(self):
                layout = QVBoxLayout(self)
                header = self._create_section_header("MY SECTION")
                layout.addWidget(header)
                # ... add more widgets
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_frame()
        self._setup_ui()

    def _setup_frame(self):
        """Apply standard ESPN card styling."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            {self.__class__.__name__} {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
            }}
        """)

    def _create_section_header(self, text: str) -> QLabel:
        """
        Create a standardized section header label.

        Args:
            text: Header text (e.g., "SEASON PERFORMANCE")

        Returns:
            QLabel with standard styling
        """
        header = QLabel(text)
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        return header

    @abstractmethod
    def _setup_ui(self):
        """
        Override this method to create the widget's UI layout.

        This method is called after the frame styling is applied.
        Subclasses must implement this to define their layout.
        """
        pass


class InteractiveDataWidget(QFrame, metaclass=QABCMeta):
    """
    Base class for widgets with user interaction (buttons, inputs, etc.).

    Features:
    - Standardized card styling
    - Consistent section headers
    - Abstract _setup_ui() and _setup_connections() for subclass implementation

    Usage:
        class MyWidget(InteractiveDataWidget):
            def _setup_ui(self):
                # Create layout and widgets
                pass

            def _setup_connections(self):
                # Connect signals and slots
                pass
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_frame()
        self._setup_ui()
        self._setup_connections()

    def _setup_frame(self):
        """Apply standard ESPN card styling."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            {self.__class__.__name__} {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
            }}
        """)

    def _create_section_header(self, text: str) -> QLabel:
        """
        Create a standardized section header label.

        Args:
            text: Header text (e.g., "GENERAL MANAGER")

        Returns:
            QLabel with standard styling
        """
        header = QLabel(text)
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        return header

    @abstractmethod
    def _setup_ui(self):
        """
        Override this method to create the widget's UI layout.

        This method is called after the frame styling is applied.
        Subclasses must implement this to define their layout.
        """
        pass

    @abstractmethod
    def _setup_connections(self):
        """
        Override this method to connect signals and slots.

        This method is called after _setup_ui() completes.
        Subclasses must implement this to define signal connections.
        """
        pass
