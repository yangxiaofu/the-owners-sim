"""
Asset List Widget - Displays trade assets (players and draft picks).

Shows "WE SEND" and "WE RECEIVE" sections with formatted asset items:
- Players: Name (POS, OVR) • Age XX • $X.XM cap hit
- Picks: YYYY Round X (Original Team)

Includes arrow indicators (→ for sending, ← for receiving).
"""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from game_cycle_ui.theme import Colors, TextColors, Typography


class AssetListWidget(QWidget):
    """
    Widget for displaying trade assets in sending/receiving sections.

    Shows two sections:
    1. WE SEND → (assets going out)
    2. WE RECEIVE ← (assets coming in)
    """

    def __init__(
        self,
        sending: List[Dict[str, Any]] = None,
        receiving: List[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize asset list widget.

        Args:
            sending: List of assets being sent (players/picks)
            receiving: List of assets being received (players/picks)
            parent: Parent widget
        """
        super().__init__(parent)
        self._sending = sending or []
        self._receiving = receiving or []
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Sending section
        if self._sending:
            sending_section = self._create_asset_section(
                title="WE SEND",
                arrow="→",
                assets=self._sending,
                arrow_color=Colors.ERROR  # Red for sending
            )
            layout.addWidget(sending_section)

        # Receiving section
        if self._receiving:
            receiving_section = self._create_asset_section(
                title="WE RECEIVE",
                arrow="←",
                assets=self._receiving,
                arrow_color=Colors.SUCCESS  # Green for receiving
            )
            layout.addWidget(receiving_section)

    def _create_asset_section(
        self,
        title: str,
        arrow: str,
        assets: List[Dict[str, Any]],
        arrow_color: str
    ) -> QWidget:
        """
        Create a section showing sending or receiving assets.

        Args:
            title: Section title ("WE SEND" or "WE RECEIVE")
            arrow: Arrow character ("→" or "←")
            assets: List of asset dictionaries
            arrow_color: Color for arrow indicator

        Returns:
            QWidget containing the section
        """
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(8, 8, 8, 8)
        section_layout.setSpacing(6)

        # Section header
        header = QLabel(title)
        header.setFont(Typography.CAPTION_BOLD)
        header.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        section_layout.addWidget(header)

        # Asset items
        for asset in assets:
            item_widget = self._create_asset_item(asset, arrow, arrow_color)
            section_layout.addWidget(item_widget)

        return section

    def _create_asset_item(
        self,
        asset: Dict[str, Any],
        arrow: str,
        arrow_color: str
    ) -> QWidget:
        """
        Create a single asset item (player or pick).

        Args:
            asset: Asset dictionary with 'type', 'name', 'position', etc.
            arrow: Arrow character
            arrow_color: Color for arrow

        Returns:
            QWidget for the asset item
        """
        item = QWidget()
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(8)

        # Arrow indicator
        arrow_label = QLabel(arrow)
        arrow_label.setStyleSheet(f"""
            color: {arrow_color};
            font-size: 18px;
            font-weight: bold;
        """)
        arrow_label.setFixedWidth(20)
        item_layout.addWidget(arrow_label)

        # Asset details
        if asset.get("type") == "player":
            details_text = self._format_player_asset(asset)
        elif asset.get("type") == "pick":
            details_text = self._format_pick_asset(asset)
        else:
            details_text = "Unknown asset type"

        details_label = QLabel(details_text)
        details_label.setFont(Typography.BODY)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
        """)
        item_layout.addWidget(details_label, stretch=1)

        return item

    def _format_player_asset(self, player: Dict[str, Any]) -> str:
        """
        Format player asset as: Name (POS, OVR) • Age XX • $X.XM.

        Args:
            player: Player dictionary

        Returns:
            Formatted string
        """
        name = player.get("name", "Unknown Player")
        position = player.get("position", "??")
        overall = player.get("overall", 0)
        age = player.get("age")
        cap_hit = player.get("cap_hit", 0)

        # Format cap hit in millions
        cap_hit_str = f"${cap_hit / 1_000_000:.1f}M"

        parts = [f"<b>{name}</b> ({position}, {overall} OVR)"]

        if age is not None:
            parts.append(f"Age {age}")

        if cap_hit > 0:
            parts.append(cap_hit_str)

        return " • ".join(parts)

    def _format_pick_asset(self, pick: Dict[str, Any]) -> str:
        """
        Format draft pick as: YYYY Round X (Original Team).

        Args:
            pick: Pick dictionary

        Returns:
            Formatted string
        """
        year = pick.get("year", "????")
        round_num = pick.get("round", "?")
        team = pick.get("team", "Unknown Team")

        # Convert round number to ordinal
        ordinal = self._get_ordinal(round_num)

        return f"<b>{year} {ordinal} Round Pick</b> ({team})"

    def _get_ordinal(self, n: int) -> str:
        """
        Convert number to ordinal string (1st, 2nd, 3rd, etc.).

        Args:
            n: Number

        Returns:
            Ordinal string
        """
        if isinstance(n, str):
            try:
                n = int(n)
            except ValueError:
                return str(n)

        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

        return f"{n}{suffix}"

    def set_assets(self, sending: List[Dict[str, Any]], receiving: List[Dict[str, Any]]):
        """
        Update displayed assets.

        Args:
            sending: New sending assets
            receiving: New receiving assets
        """
        self._sending = sending
        self._receiving = receiving

        # Rebuild UI
        # Clear existing widgets
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Rebuild
        self._setup_ui()
