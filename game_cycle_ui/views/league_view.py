"""
League View - Main League dashboard with sidebar and tabbed content.

Displays league overview information including standings, playoff picture,
and league leaders in a sidebar + tabs layout matching Team View pattern.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import ESPN_THEME, TAB_STYLE, PRIMARY_BUTTON_STYLE, Typography, FontSizes, TextColors
from game_cycle_ui.widgets.league_sidebar_widget import LeagueSidebarWidget
from game_cycle_ui.widgets.standings_table_widget import StandingsTableWidget
from game_cycle_ui.widgets.playoff_picture_widget import PlayoffPictureWidget
from game_cycle_ui.widgets.league_leaders_widget import LeagueLeadersWidget

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.standings_api import StandingsAPI
from game_cycle.database.player_stats_api import PlayerSeasonStatsAPI


class LeagueView(QWidget):
    """
    Main League dashboard view with sidebar + tabbed content.

    Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │ LEAGUE OVERVIEW                                    [Refresh]    │
    ├───────────────┬─────────────────────────────────────────────────┤
    │ SIDEBAR       │ [Standings]  [Playoff Picture]  [League Leaders]│
    │ ────────────  │ ─────────────────────────────────────────────── │
    │ Week 13       │ (Tab content area)                              │
    │               │                                                  │
    │ CLINCHED      │                                                  │
    │ • KC Chiefs   │                                                  │
    │               │                                                  │
    │ ELIMINATED    │                                                  │
    │ • NE Patriots │                                                  │
    │               │                                                  │
    │ TOP PERFORMERS│                                                  │
    │ ────────────  │                                                  │
    │ Pass: J.Goff  │                                                  │
    │   4,200 YDS   │                                                  │
    └───────────────┴─────────────────────────────────────────────────┘
    """

    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: int = 2024
        self._teams_data: Dict[int, Dict] = {}
        self._logger = logging.getLogger(__name__)

        self._setup_ui()
        self._load_teams_data()

    def _setup_ui(self):
        """Build the League View layout."""
        self.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header = self._create_header()
        main_layout.addWidget(header)

        # Content area: sidebar + tabs
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left sidebar
        self.sidebar = LeagueSidebarWidget()
        content_layout.addWidget(self.sidebar)

        # Main tabbed content
        tabs_container = self._create_tabs_container()
        content_layout.addWidget(tabs_container, 1)

        main_layout.addLayout(content_layout)

    def _create_header(self) -> QFrame:
        """Create the header bar with title and refresh button."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border-bottom: 3px solid {ESPN_THEME['red']};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        # Title
        title = QLabel("LEAGUE OVERVIEW")
        title.setFont(Typography.H4)
        title.setStyleSheet(f"color: {ESPN_THEME['text_primary']}; letter-spacing: 2px;")
        layout.addWidget(title)

        layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self.refresh_btn)

        return header

    def _create_tabs_container(self) -> QWidget:
        """Create the tabbed content container."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        # Tab 1: Standings
        self.standings_widget = StandingsTableWidget()
        self.tabs.addTab(self.standings_widget, "Standings")

        # Tab 2: Playoff Picture
        self.playoff_widget = PlayoffPictureWidget()
        self.tabs.addTab(self.playoff_widget, "Playoff Picture")

        # Tab 3: League Leaders
        self.leaders_widget = LeagueLeadersWidget()
        self.tabs.addTab(self.leaders_widget, "League Leaders")

        layout.addWidget(self.tabs)

        return container

    def _load_teams_data(self):
        """Load team metadata from teams.json."""
        teams_path = Path(__file__).parent.parent.parent / "src" / "data" / "teams.json"
        try:
            with open(teams_path, "r") as f:
                data = json.load(f)
                self._teams_data = {
                    int(k): v for k, v in data.get("teams", {}).items()
                }
        except Exception as e:
            self._logger.error(f"Failed to load teams.json: {e}", exc_info=True)
            self._teams_data = {}

    # =========================================================================
    # Public API
    # =========================================================================

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set the context for data loading.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle database
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self.refresh_data()

    def refresh_data(self):
        """Refresh all league data from database."""
        if not self._dynasty_id or not self._db_path:
            return

        self._load_standings()
        self._load_playoff_picture()
        self._load_league_leaders()
        self._update_sidebar()

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_standings(self):
        """Load standings data and populate widget."""
        try:
            db = GameCycleDatabase(self._db_path)
            standings_api = StandingsAPI(db)
            standings = standings_api.get_standings(
                self._dynasty_id, self._season, 'regular_season'
            )

            # Convert to dict format expected by widget
            standings_list = []
            for standing in standings:
                team_data = self._teams_data.get(standing.team_id, {})
                standings_list.append({
                    'team_id': standing.team_id,
                    'team_abbrev': team_data.get('abbreviation', f'T{standing.team_id}'),
                    'team_name': team_data.get('full_name', f'Team {standing.team_id}'),
                    'conference': team_data.get('conference', 'AFC'),
                    'division': team_data.get('division', 'North'),
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'ties': standing.ties,
                    'points_for': standing.points_for,
                    'points_against': standing.points_against,
                    'playoff_seed': standing.playoff_seed,
                    'streak': self._calculate_streak(standing),
                    'home_record': f"{standing.home_wins}-{standing.home_losses}",
                    'away_record': f"{standing.away_wins}-{standing.away_losses}",
                    'division_record': f"{standing.division_wins}-{standing.division_losses}",
                })

            self.standings_widget.set_standings(standings_list)

        except Exception as e:
            self._logger.error(f"Failed to load standings: {e}", exc_info=True)

    def _calculate_streak(self, standing) -> str:
        """Calculate win/loss streak (placeholder - would need game history)."""
        # This would ideally query recent games to determine streak
        # For now, return placeholder
        return "--"

    def _load_playoff_picture(self):
        """Load playoff picture data and populate widget."""
        try:
            db = GameCycleDatabase(self._db_path)
            standings_api = StandingsAPI(db)
            standings = standings_api.get_standings(
                self._dynasty_id, self._season, 'regular_season'
            )

            # Separate by conference
            afc_teams = []
            nfc_teams = []

            for standing in standings:
                team_data = self._teams_data.get(standing.team_id, {})
                team_info = {
                    'team_id': standing.team_id,
                    'team_abbrev': team_data.get('abbreviation', f'T{standing.team_id}'),
                    'team_name': team_data.get('full_name', f'Team {standing.team_id}'),
                    'conference': team_data.get('conference', 'AFC'),
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'ties': standing.ties,
                    'playoff_seed': standing.playoff_seed,
                    'clinch_type': self._get_clinch_type(standing),
                }

                if team_data.get('conference') == 'AFC':
                    afc_teams.append(team_info)
                else:
                    nfc_teams.append(team_info)

            # Sort by playoff seed or wins
            afc_teams.sort(key=lambda t: (
                t['playoff_seed'] if t['playoff_seed'] else 999,
                -t['wins']
            ))
            nfc_teams.sort(key=lambda t: (
                t['playoff_seed'] if t['playoff_seed'] else 999,
                -t['wins']
            ))

            # Get seeds (teams with playoff_seed 1-7)
            afc_seeds = [t for t in afc_teams if t.get('playoff_seed') and 1 <= t['playoff_seed'] <= 7]
            nfc_seeds = [t for t in nfc_teams if t.get('playoff_seed') and 1 <= t['playoff_seed'] <= 7]

            # Fill to 7 if needed
            afc_unseeded = [t for t in afc_teams if not t.get('playoff_seed')]
            nfc_unseeded = [t for t in nfc_teams if not t.get('playoff_seed')]

            while len(afc_seeds) < 7 and afc_unseeded:
                afc_seeds.append(afc_unseeded.pop(0))
            while len(nfc_seeds) < 7 and nfc_unseeded:
                nfc_seeds.append(nfc_unseeded.pop(0))

            # In the hunt (remaining non-eliminated teams)
            in_hunt = afc_unseeded + nfc_unseeded

            # Eliminated (placeholder - would need elimination calculation)
            eliminated = []

            self.playoff_widget.set_playoff_data(
                afc_seeds[:7], nfc_seeds[:7], in_hunt, eliminated
            )

        except Exception as e:
            self._logger.error(f"Failed to load playoff picture: {e}", exc_info=True)

    def _get_clinch_type(self, standing) -> Optional[str]:
        """Determine clinch type based on playoff seed."""
        if not standing.playoff_seed:
            return None
        if standing.playoff_seed <= 1:
            return 'bye'
        elif standing.playoff_seed <= 4:
            return 'division'
        elif standing.playoff_seed <= 7:
            return 'playoff'
        return None

    def _load_league_leaders(self):
        """Load league leaders data and populate widget."""
        try:
            player_stats_api = PlayerSeasonStatsAPI(self._db_path)

            # Aggregate stats across all teams
            all_player_stats: Dict[int, Dict[str, Any]] = {}

            for team_id in range(1, 33):
                team_stats = player_stats_api.get_team_player_stats(
                    self._dynasty_id, team_id, self._season, 'regular_season'
                )
                for player_id, stats in team_stats.items():
                    stats['team_id'] = team_id
                    all_player_stats[player_id] = stats

            # Build leaders dict
            leaders = self._calculate_leaders(all_player_stats)
            self.leaders_widget.set_leaders(leaders)

        except Exception as e:
            self._logger.error(f"Failed to load league leaders: {e}", exc_info=True)

    def _calculate_leaders(self, all_stats: Dict[int, Dict]) -> Dict[str, List[Dict]]:
        """
        Calculate top 5 leaders in each category.

        Args:
            all_stats: Dict mapping player_id -> stats dict

        Returns:
            Dict mapping category key -> list of top 5 players
        """
        # Load player names (would need player API - using placeholder)
        leaders = {}

        categories = [
            ('passing_yards', 'passing_yards'),
            ('passing_tds', 'passing_tds'),
            ('rushing_yards', 'rushing_yards'),
            ('rushing_tds', 'rushing_tds'),
            ('receiving_yards', 'receiving_yards'),
            ('receptions', 'receptions'),
            ('sacks', 'sacks'),
            ('interceptions', 'interceptions'),
        ]

        for display_key, stat_key in categories:
            # Sort by stat value
            sorted_players = sorted(
                all_stats.items(),
                key=lambda x: x[1].get(stat_key, 0),
                reverse=True
            )[:5]

            # Format for widget
            leader_list = []
            for player_id, stats in sorted_players:
                team_id = stats.get('team_id', 0)
                team_data = self._teams_data.get(team_id, {})
                # Get player name from stats (already in database)
                full_name = stats.get('player_name', f"Player {player_id}")
                # Format as "F. LastName" for compact display
                name_parts = full_name.split() if full_name else []
                if len(name_parts) >= 2:
                    display_name = f"{name_parts[0][0]}. {name_parts[-1]}"
                else:
                    display_name = full_name
                leader_list.append({
                    'player_id': player_id,
                    'name': display_name,
                    'team': team_data.get('abbreviation', '???'),
                    'value': stats.get(stat_key, 0),
                })

            leaders[display_key] = leader_list

        return leaders

    def _update_sidebar(self):
        """Update sidebar with current week and top performers."""
        try:
            # Get current week from dynasty_state
            db = GameCycleDatabase(self._db_path)
            row = db.query_one(
                "SELECT current_week, current_phase FROM dynasty_state WHERE dynasty_id = ?",
                (self._dynasty_id,)
            )

            if row:
                week = row['current_week'] if row['current_week'] else 1
                phase = row['current_phase'] if row['current_phase'] else 'regular_season'
                self.sidebar.set_week(week, phase)

            # Get clinched/eliminated teams from standings
            standings_api = StandingsAPI(db)
            standings = standings_api.get_standings(
                self._dynasty_id, self._season, 'regular_season'
            )

            clinched = []
            for standing in standings:
                if standing.playoff_seed and 1 <= standing.playoff_seed <= 7:
                    team_data = self._teams_data.get(standing.team_id, {})
                    clinch_type = 'division' if standing.playoff_seed <= 4 else 'playoff'
                    clinched.append({
                        'name': team_data.get('abbreviation', f'T{standing.team_id}'),
                        'type': clinch_type,
                    })

            self.sidebar.set_clinched_teams(clinched[:8])
            self.sidebar.set_eliminated_teams([])  # Would need elimination calculation

            # Top performers from league leaders
            player_stats_api = PlayerSeasonStatsAPI(self._db_path)
            top_performers = {}

            # Get top in each category
            for team_id in range(1, 33):
                team_stats = player_stats_api.get_team_player_stats(
                    self._dynasty_id, team_id, self._season, 'regular_season'
                )
                for player_id, stats_raw in team_stats.items():
                    # Convert sqlite3.Row to dict if needed
                    stats = dict(stats_raw) if hasattr(stats_raw, 'keys') else stats_raw
                    team_data = self._teams_data.get(team_id, {})

                    # Check each category
                    if stats.get('passing_yards', 0) > top_performers.get('pass', {}).get('value', 0):
                        top_performers['pass'] = {
                            'name': stats.get('player_name', f"Player {player_id}"),
                            'team': team_data.get('abbreviation', ''),
                            'value': stats['passing_yards'],
                        }
                    if stats.get('rushing_yards', 0) > top_performers.get('rush', {}).get('value', 0):
                        top_performers['rush'] = {
                            'name': stats.get('player_name', f"Player {player_id}"),
                            'team': team_data.get('abbreviation', ''),
                            'value': stats['rushing_yards'],
                        }
                    if stats.get('receiving_yards', 0) > top_performers.get('rec', {}).get('value', 0):
                        top_performers['rec'] = {
                            'name': stats.get('player_name', f"Player {player_id}"),
                            'team': team_data.get('abbreviation', ''),
                            'value': stats['receiving_yards'],
                        }
                    if stats.get('sacks', 0) > top_performers.get('sacks', {}).get('value', 0):
                        top_performers['sacks'] = {
                            'name': stats.get('player_name', f"Player {player_id}"),
                            'team': team_data.get('abbreviation', ''),
                            'value': stats['sacks'],
                        }
                    if stats.get('interceptions', 0) > top_performers.get('int', {}).get('value', 0):
                        top_performers['int'] = {
                            'name': stats.get('player_name', f"Player {player_id}"),
                            'team': team_data.get('abbreviation', ''),
                            'value': stats['interceptions'],
                        }

            self.sidebar.set_top_performers(top_performers)

        except Exception as e:
            self._logger.error(f"Failed to update sidebar: {e}", exc_info=True)

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_data()
        self.refresh_requested.emit()

    def clear(self):
        """Clear all view data."""
        self.sidebar.clear()
        self.standings_widget.clear()
        self.playoff_widget.clear()
        self.leaders_widget.clear()
