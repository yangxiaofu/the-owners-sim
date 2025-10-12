"""
Playoff Bracket Widget - Displays NFL playoff tournament bracket.

Shows complete playoff structure with all rounds and game matchups.
Updates with scores and winners as games are completed.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional, List, Dict, Any
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import get_team_by_id


class GameCardWidget(QFrame):
    """
    Widget displaying a single playoff game matchup.

    Shows team names, seeds, scores (if played), and game status.
    """

    def __init__(self, game_data: Dict[str, Any], game_result: Optional[Dict[str, Any]] = None):
        """
        Initialize game card.

        Args:
            game_data: PlayoffGame data (away_team_id, home_team_id, seeds, date)
            game_result: Optional game result (scores, winner_id)
        """
        super().__init__()
        self.game_data = game_data
        self.game_result = game_result

        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the game card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Get team information
        away_team_id = self.game_data.get('away_team_id')
        home_team_id = self.game_data.get('home_team_id')
        away_seed = self.game_data.get('away_seed')
        home_seed = self.game_data.get('home_seed')

        # Get team names
        away_team = get_team_by_id(away_team_id) if away_team_id else None
        home_team = get_team_by_id(home_team_id) if home_team_id else None

        away_name = f"{away_team.city} {away_team.nickname}" if away_team else f"Team {away_team_id}"
        home_name = f"{home_team.city} {home_team.nickname}" if home_team else f"Team {home_team_id}"

        # Check if game is completed
        is_complete = self.game_result and self.game_result.get('success', False)
        winner_id = self.game_result.get('winner_id') if is_complete else None

        # Away team row
        away_layout = QHBoxLayout()
        away_layout.setSpacing(6)

        away_seed_label = QLabel(f"#{away_seed}")
        away_seed_label.setFixedWidth(25)
        away_seed_label.setAlignment(Qt.AlignCenter)
        away_seed_font = QFont()
        away_seed_font.setPointSize(9)
        away_seed_font.setBold(True)
        away_seed_label.setFont(away_seed_font)
        away_layout.addWidget(away_seed_label)

        away_team_label = QLabel(away_name)
        away_team_font = QFont()
        away_team_font.setPointSize(10)
        if winner_id == away_team_id:
            away_team_font.setBold(True)
            away_team_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        away_team_label.setFont(away_team_font)
        away_layout.addWidget(away_team_label, stretch=1)

        # Score for away team (if game completed)
        if is_complete:
            away_score = self.game_result.get('away_score', 0)
            away_score_label = QLabel(str(away_score))
            away_score_label.setFixedWidth(30)
            away_score_label.setAlignment(Qt.AlignCenter)
            score_font = QFont()
            score_font.setPointSize(10)
            score_font.setBold(True)
            away_score_label.setFont(score_font)
            away_layout.addWidget(away_score_label)

        layout.addLayout(away_layout)

        # "at" label
        at_label = QLabel("@")
        at_label.setAlignment(Qt.AlignCenter)
        at_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(at_label)

        # Home team row
        home_layout = QHBoxLayout()
        home_layout.setSpacing(6)

        home_seed_label = QLabel(f"#{home_seed}")
        home_seed_label.setFixedWidth(25)
        home_seed_label.setAlignment(Qt.AlignCenter)
        home_seed_font = QFont()
        home_seed_font.setPointSize(9)
        home_seed_font.setBold(True)
        home_seed_label.setFont(home_seed_font)
        home_layout.addWidget(home_seed_label)

        home_team_label = QLabel(home_name)
        home_team_font = QFont()
        home_team_font.setPointSize(10)
        if winner_id == home_team_id:
            home_team_font.setBold(True)
            home_team_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        home_team_label.setFont(home_team_font)
        home_layout.addWidget(home_team_label, stretch=1)

        # Score for home team (if game completed)
        if is_complete:
            home_score = self.game_result.get('home_score', 0)
            home_score_label = QLabel(str(home_score))
            home_score_label.setFixedWidth(30)
            home_score_label.setAlignment(Qt.AlignCenter)
            score_font = QFont()
            score_font.setPointSize(10)
            score_font.setBold(True)
            home_score_label.setFont(score_font)
            home_layout.addWidget(home_score_label)

        layout.addLayout(home_layout)

        # Game date/status
        if is_complete:
            status_label = QLabel("FINAL")
            status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        else:
            game_date = self.game_data.get('game_date', 'TBD')
            status_label = QLabel(str(game_date))
            status_label.setStyleSheet("color: #666666; font-size: 9pt;")

        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)

        # Set card background
        if is_complete:
            self.setStyleSheet("QFrame { background-color: #F1F8E9; border: 1px solid #9CCC65; border-radius: 4px; }")
        else:
            self.setStyleSheet("QFrame { background-color: #FAFAFA; border: 1px solid #CCCCCC; border-radius: 4px; }")


class PlayoffBracketWidget(QWidget):
    """
    Widget displaying complete NFL playoff bracket.

    Shows all playoff rounds with game matchups, scores, and winners.
    Updates dynamically as games are completed.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize playoff bracket widget."""
        super().__init__(parent)

        self.bracket_data: Optional[Dict[str, Any]] = None
        self.original_seeding: Optional[Any] = None  # Store playoff seeding for bye teams

        # UI components
        self.wild_card_container: Optional[QWidget] = None
        self.divisional_container: Optional[QWidget] = None
        self.conference_container: Optional[QWidget] = None
        self.super_bowl_container: Optional[QWidget] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the bracket UI structure."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Scroll area for bracket
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Container for bracket rounds
        bracket_container = QWidget()
        bracket_layout = QHBoxLayout(bracket_container)
        bracket_layout.setSpacing(20)
        bracket_layout.setAlignment(Qt.AlignTop)

        # Create round sections (left to right)
        self.wild_card_container = self._create_round_section("Wild Card")
        self.divisional_container = self._create_round_section("Divisional")
        self.conference_container = self._create_round_section("Conference")
        self.super_bowl_container = self._create_round_section("Super Bowl")

        bracket_layout.addWidget(self.wild_card_container)
        bracket_layout.addWidget(self.divisional_container)
        bracket_layout.addWidget(self.conference_container)
        bracket_layout.addWidget(self.super_bowl_container)
        bracket_layout.addStretch()

        scroll_area.setWidget(bracket_container)
        main_layout.addWidget(scroll_area)

    def _create_round_section(self, round_name: str) -> QWidget:
        """
        Create a section for one playoff round.

        Args:
            round_name: Round display name

        Returns:
            QWidget container for the round
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Round title
        title = QLabel(round_name)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Games container (will be populated with game cards)
        games_container = QWidget()
        games_container.setObjectName("games_container")  # Set unique identifier
        games_layout = QVBoxLayout(games_container)
        games_layout.setSpacing(8)
        games_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(games_container)

        layout.addStretch()

        container.setMinimumWidth(220)
        return container

    def update_bracket(self, bracket_data: Optional[Dict[str, Any]], round_results: Optional[Dict[str, List[Dict]]] = None) -> None:
        """
        Update bracket display with new data.

        Args:
            bracket_data: Complete bracket structure from controller
            round_results: Game results by round {'wild_card': [...], 'divisional': [...], ...}
        """
        self.bracket_data = bracket_data

        if not bracket_data:
            self._show_no_data_message()
            return

        # Store original seeding for displaying bye teams
        self.original_seeding = bracket_data.get('original_seeding')

        # Update each round (pass seeding data for bye team display)
        self._update_round(self.wild_card_container, bracket_data.get('wild_card'),
                          round_results.get('wild_card', []) if round_results else [],
                          seeding_data=None)  # Wild Card doesn't show bye teams
        self._update_round(self.divisional_container, bracket_data.get('divisional'),
                          round_results.get('divisional', []) if round_results else [],
                          seeding_data=self.original_seeding)  # Show #1 and #2 seeds
        self._update_round(self.conference_container, bracket_data.get('conference'),
                          round_results.get('conference', []) if round_results else [],
                          seeding_data=None)  # Conference round doesn't show bye teams
        self._update_round(self.super_bowl_container, bracket_data.get('super_bowl'),
                          round_results.get('super_bowl', []) if round_results else [],
                          seeding_data=None)  # Super Bowl doesn't show bye teams

    def _update_round(self, round_container: QWidget, bracket: Any, results: List[Dict], seeding_data: Optional[Any] = None) -> None:
        """
        Update a single round with game data.

        Args:
            round_container: QWidget container for the round
            bracket: PlayoffBracket object for the round
            results: List of game results for this round
            seeding_data: Optional playoff seeding data for displaying bye teams
        """
        if not round_container:
            return

        # Find games container within round container using unique object name
        games_container = round_container.findChild(QWidget, "games_container")
        if not games_container:
            return

        # Clear existing games
        layout = games_container.layout()
        if not layout:
            return

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not bracket or not hasattr(bracket, 'games'):
            # If we have seeding data, show bye teams for Divisional round
            if seeding_data and hasattr(seeding_data, 'afc') and hasattr(seeding_data, 'nfc'):
                self._show_bye_teams(layout, seeding_data)
                return

            # Otherwise show "TBD" message
            tbd_label = QLabel("Games not yet scheduled")
            tbd_label.setAlignment(Qt.AlignCenter)
            tbd_label.setStyleSheet("color: #888888; font-style: italic; padding: 20px;")
            layout.addWidget(tbd_label)
            return

        # Create game cards for each game in round
        games = bracket.games if hasattr(bracket, 'games') else []

        # Group games by conference (for wild card, divisional, conference)
        afc_games = [g for g in games if hasattr(g, 'conference') and g.conference == 'AFC']
        nfc_games = [g for g in games if hasattr(g, 'conference') and g.conference == 'NFC']

        # Display AFC games
        if afc_games:
            afc_label = QLabel("AFC")
            afc_label.setStyleSheet("font-weight: bold; color: #1976D2; padding: 4px;")
            layout.addWidget(afc_label)

            for game in afc_games:
                game_dict = self._game_to_dict(game)
                game_result = self._find_game_result(game_dict, results)
                game_card = GameCardWidget(game_dict, game_result)
                layout.addWidget(game_card)

        # Display NFC games
        if nfc_games:
            nfc_label = QLabel("NFC")
            nfc_label.setStyleSheet("font-weight: bold; color: #C62828; padding: 4px;")
            layout.addWidget(nfc_label)

            for game in nfc_games:
                game_dict = self._game_to_dict(game)
                game_result = self._find_game_result(game_dict, results)
                game_card = GameCardWidget(game_dict, game_result)
                layout.addWidget(game_card)

        # Display Super Bowl game (no conference)
        if not afc_games and not nfc_games and games:
            for game in games:
                game_dict = self._game_to_dict(game)
                game_result = self._find_game_result(game_dict, results)
                game_card = GameCardWidget(game_dict, game_result)
                layout.addWidget(game_card)

        # Force Qt to update the display
        round_container.update()

    def _game_to_dict(self, game: Any) -> Dict[str, Any]:
        """
        Convert PlayoffGame object to dictionary.

        Args:
            game: PlayoffGame object

        Returns:
            Dictionary with game data
        """
        return {
            'away_team_id': game.away_team_id if hasattr(game, 'away_team_id') else None,
            'home_team_id': game.home_team_id if hasattr(game, 'home_team_id') else None,
            'away_seed': game.away_seed if hasattr(game, 'away_seed') else 0,
            'home_seed': game.home_seed if hasattr(game, 'home_seed') else 0,
            'game_date': game.game_date if hasattr(game, 'game_date') else 'TBD',
            'round_name': game.round_name if hasattr(game, 'round_name') else '',
            'conference': game.conference if hasattr(game, 'conference') else None
        }

    def _find_game_result(self, game_dict: Dict[str, Any], results: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Find the result for a specific game.

        Args:
            game_dict: Game data dictionary
            results: List of game results for this round

        Returns:
            Game result dictionary or None if not found
        """
        away_id = game_dict.get('away_team_id')
        home_id = game_dict.get('home_team_id')

        for result in results:
            if result.get('away_team_id') == away_id and result.get('home_team_id') == home_id:
                return result

        return None

    def _show_bye_teams(self, layout: Any, seeding_data: Any) -> None:
        """
        Show bye teams (#1 seeds) for Divisional round.

        Args:
            layout: Layout to add bye team cards to
            seeding_data: Playoff seeding data with AFC and NFC conferences
        """
        # AFC #1 seed (bye team)
        afc_label = QLabel("AFC")
        afc_label.setStyleSheet("font-weight: bold; color: #1976D2; padding: 4px;")
        layout.addWidget(afc_label)

        # Get #1 seed from AFC
        if seeding_data.afc and seeding_data.afc.seeds:
            afc_one_seed = seeding_data.afc.seeds[0]  # First seed is #1
            bye_card = self._create_bye_team_card(afc_one_seed)
            layout.addWidget(bye_card)

        # NFC #1 seed (bye team)
        nfc_label = QLabel("NFC")
        nfc_label.setStyleSheet("font-weight: bold; color: #C62828; padding: 4px;")
        layout.addWidget(nfc_label)

        # Get #1 seed from NFC
        if seeding_data.nfc and seeding_data.nfc.seeds:
            nfc_one_seed = seeding_data.nfc.seeds[0]  # First seed is #1
            bye_card = self._create_bye_team_card(nfc_one_seed)
            layout.addWidget(bye_card)

    def _create_bye_team_card(self, seed_info: Any) -> QFrame:
        """
        Create a card for a bye team (team awaiting Wild Card winner).

        Args:
            seed_info: PlayoffSeed object with team_id, seed, record_string

        Returns:
            QFrame widget displaying bye team
        """
        card = QFrame()
        card.setFrameStyle(QFrame.Box | QFrame.Plain)
        card.setLineWidth(1)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Get team info
        team = get_team_by_id(seed_info.team_id)
        team_name = f"{team.city} {team.nickname}" if team else f"Team {seed_info.team_id}"

        # Seed + Team name row
        team_layout = QHBoxLayout()
        team_layout.setSpacing(6)

        seed_label = QLabel(f"#{seed_info.seed}")
        seed_label.setFixedWidth(25)
        seed_label.setAlignment(Qt.AlignCenter)
        seed_font = QFont()
        seed_font.setPointSize(9)
        seed_font.setBold(True)
        seed_label.setFont(seed_font)
        team_layout.addWidget(seed_label)

        team_label = QLabel(team_name)
        team_font = QFont()
        team_font.setPointSize(10)
        team_font.setBold(True)
        team_label.setFont(team_font)
        team_layout.addWidget(team_label, stretch=1)

        layout.addLayout(team_layout)

        # BYE indicator
        bye_label = QLabel("BYE")
        bye_label.setAlignment(Qt.AlignCenter)
        bye_label.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 11pt; padding: 2px;")
        layout.addWidget(bye_label)

        # "vs TBD" row
        vs_label = QLabel("vs")
        vs_label.setAlignment(Qt.AlignCenter)
        vs_label.setStyleSheet("color: #666666; font-style: italic; font-size: 9pt;")
        layout.addWidget(vs_label)

        tbd_label = QLabel("TBD (Wild Card winner)")
        tbd_label.setAlignment(Qt.AlignCenter)
        tbd_font = QFont()
        tbd_font.setPointSize(9)
        tbd_font.setItalic(True)
        tbd_label.setFont(tbd_font)
        tbd_label.setStyleSheet("color: #999999;")
        layout.addWidget(tbd_label)

        # Projected date (estimate)
        date_label = QLabel("Jan 24-25, 2026")
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setStyleSheet("color: #666666; font-size: 9pt; font-style: italic;")
        layout.addWidget(date_label)

        # Different styling for bye teams (light blue background)
        card.setStyleSheet("QFrame { background-color: #E3F2FD; border: 1px solid #90CAF9; border-radius: 4px; }")

        return card

    def _show_no_data_message(self) -> None:
        """Show message when no bracket data is available."""
        # Clear all round containers
        for container in [self.wild_card_container, self.divisional_container,
                         self.conference_container, self.super_bowl_container]:
            if not container:
                continue

            games_container = container.findChild(QWidget)
            if games_container:
                layout = games_container.layout()
                if layout:
                    while layout.count():
                        child = layout.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()

                    message = QLabel("No bracket data available")
                    message.setAlignment(Qt.AlignCenter)
                    message.setStyleSheet("color: #888888; font-style: italic; padding: 20px;")
                    layout.addWidget(message)
