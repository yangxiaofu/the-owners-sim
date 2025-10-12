"""
Standings Store

Store for team standings with automatic sorting and playoff calculations.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .base_store import BaseStore
# GameResult from simulation removed - using shared.game_result instead
# from simulation.results.game_result import GameResult
from shared.game_result import GameResult

try:
    from database.connection import DatabaseConnection
except ImportError:
    DatabaseConnection = None

# Import shared NFL structure constants
try:
    from playoff_system.constants import NFL_DIVISIONS, NFL_CONFERENCES
    SHARED_CONSTANTS_AVAILABLE = True
except ImportError:
    # Fallback to local definitions if shared constants not available
    SHARED_CONSTANTS_AVAILABLE = False


@dataclass
class TeamStanding:
    """Base team standing with core record tracking"""
    team_id: int
    wins: int = 0
    losses: int = 0
    ties: int = 0
    division_place: int = 1
    
    @property
    def games_played(self) -> int:
        """Total games played"""
        return self.wins + self.losses + self.ties
    
    @property
    def win_percentage(self) -> float:
        """Calculate win percentage"""
        if self.games_played == 0:
            return 0.0
        return (self.wins + (self.ties * 0.5)) / self.games_played
        
    @property
    def record_string(self) -> str:
        """Get record as string (e.g., '10-6')"""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"


# NFL Division structure - use shared constants when available, fallback to local
if SHARED_CONSTANTS_AVAILABLE:
    # Use shared constants from playoff_system.constants
    # Convert division names from underscore to space format for compatibility
    _SHARED_DIVISIONS = NFL_DIVISIONS
    _SHARED_CONFERENCES = NFL_CONFERENCES

    # Convert to local format (spaces instead of underscores)
    NFL_DIVISIONS = {
        division_name.replace('_', ' '): team_ids
        for division_name, team_ids in _SHARED_DIVISIONS.items()
    }
    NFL_CONFERENCES = _SHARED_CONFERENCES
else:
    # Fallback local definitions for backwards compatibility
    NFL_DIVISIONS = {
        'AFC East': [1, 2, 3, 4],
        'AFC North': [5, 6, 7, 8],
        'AFC South': [9, 10, 11, 12],
        'AFC West': [13, 14, 15, 16],
        'NFC East': [17, 18, 19, 20],
        'NFC North': [21, 22, 23, 24],
        'NFC South': [25, 26, 27, 28],
        'NFC West': [29, 30, 31, 32]
    }

    NFL_CONFERENCES = {
        'AFC': list(range(1, 17)),
        'NFC': list(range(17, 33))
    }


@dataclass
class EnhancedTeamStanding(TeamStanding):
    """Extended standing with additional tracking"""
    division_wins: int = 0
    division_losses: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    home_wins: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_losses: int = 0
    points_for: int = 0
    points_against: int = 0
    streak: str = ""  # e.g., "W3", "L2"
    last_5: str = ""  # e.g., "3-2"

    @property
    def point_differential(self) -> int:
        """Calculate point differential"""
        return self.points_for - self.points_against

    @property
    def division_record(self) -> str:
        """Get division record string"""
        return f"{self.division_wins}-{self.division_losses}"

    @property
    def conference_record(self) -> str:
        """Get conference record string"""
        return f"{self.conference_wins}-{self.conference_losses}"


class StandingsStore(BaseStore[EnhancedTeamStanding]):
    """
    Store for team standings with automatic updates and sorting.

    Maintains division, conference, and overall standings with
    playoff seeding calculations.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """Initialize standings store."""
        super().__init__("standings")

        # Database connection for persistence
        self.db_connection = DatabaseConnection(database_path) if DatabaseConnection else None
        self.dynasty_id: Optional[str] = None
        self.current_season: Optional[int] = None

        # Initialize all teams with 0-0 records for regular season
        # Playoff standings will be created on-demand when first playoff game is played
        self._initialize_standings(season_type="regular_season")

        # Standings by grouping AND season_type
        # Structure: {season_type: {division/conference: [team_ids]}}
        self.division_standings: Dict[str, Dict[str, List[int]]] = {
            "regular_season": {},
            "playoffs": {}
        }
        self.conference_standings: Dict[str, Dict[str, List[int]]] = {
            "regular_season": {},
            "playoffs": {}
        }
        self.overall_standings: Dict[str, List[int]] = {
            "regular_season": [],
            "playoffs": []
        }

        # Head-to-head records for tiebreaking (keyed by team pair, tracked per season_type)
        # Structure: {(team1, team2, season_type): {'team1_wins': 0, 'team2_wins': 0, 'ties': 0}}
        self.head_to_head: Dict[Tuple[int, int, str], Dict[str, int]] = defaultdict(
            lambda: {'team1_wins': 0, 'team2_wins': 0, 'ties': 0}
        )

        # Recent results for streak tracking (tracked per team, per season_type)
        # Structure: {(team_id, season_type): ['W', 'L', 'W', ...]}
        self.recent_results: Dict[Tuple[int, str], List[str]] = defaultdict(list)

        self._sort_all_standings()

    def set_dynasty_context(self, dynasty_id: str, season: int) -> None:
        """
        Set dynasty and season context for database persistence.
        
        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        self.dynasty_id = dynasty_id
        self.current_season = season

    def add(self, key: str, item: EnhancedTeamStanding) -> None:
        """
        Add or update a team's standing.

        Args:
            key: Team ID as string
            item: Team standing
        """
        if self.is_locked():
            self.logger.warning(f"Cannot add to locked store {self.store_name}")
            return

        team_id = int(key)
        self.data[key] = item

        # Re-sort standings
        self._sort_all_standings()

        # Immediate database persistence
        self._persist_to_database(team_id, item)

        self._update_metadata()
        self._log_transaction('add', key, True, {
            'team_id': team_id,
            'record': f"{item.wins}-{item.losses}"
        })

    def get(self, key: str) -> Optional[EnhancedTeamStanding]:
        """
        Get a team's standing.

        Args:
            key: Team ID as string

        Returns:
            Team standing if found
        """
        return self.data.get(key)

    def get_all(self) -> Dict[str, EnhancedTeamStanding]:
        """Get all team standings."""
        return self.data.copy()

    def clear(self) -> None:
        """Reset all standings to 0-0."""
        if self.is_locked():
            self.logger.warning(f"Cannot clear locked store {self.store_name}")
            return

        self._initialize_standings()
        self.head_to_head.clear()
        self.recent_results.clear()
        self._sort_all_standings()

        self._update_metadata()
        self._log_transaction('clear', None, True)

    def validate(self) -> bool:
        """
        Validate standings consistency.

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check all 32 teams are present
            if len(self.data) != 32:
                self.logger.error(f"Expected 32 teams, found {len(self.data)}")
                return False

            # Verify division assignments
            for division, teams in NFL_DIVISIONS.items():
                for team_id in teams:
                    if str(team_id) not in self.data:
                        self.logger.error(f"Team {team_id} missing from standings")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def update_from_game_result(self, result: GameResult) -> None:
        """
        Update standings based on a game result.

        Auto-detects season_type from GameResult and routes to the correct standing record.
        Regular season games update regular_season standings.
        Playoff games update playoffs standings.

        Args:
            result: Game result to process
        """
        if self.is_locked():
            self.logger.warning("Cannot update locked standings")
            return

        # 🔑 AUTO-DETECT season_type from GameResult
        season_type = getattr(result, 'season_type', 'regular_season')

        home_id = result.home_team.team_id
        away_id = result.away_team.team_id

        # 🔑 BUILD COMPOSITE KEYS with season_type
        home_key = f"{home_id}_{season_type}"
        away_key = f"{away_id}_{season_type}"

        home_standing = self.data.get(home_key)
        away_standing = self.data.get(away_key)

        # 🔑 LAZY CREATION: If playoff standings don't exist yet, create them
        if not home_standing:
            self.logger.info(f"Creating {season_type} standing for team {home_id}")
            home_standing = self._create_standing_for_team(home_id, season_type)
            self.data[home_key] = home_standing

        if not away_standing:
            self.logger.info(f"Creating {season_type} standing for team {away_id}")
            away_standing = self._create_standing_for_team(away_id, season_type)
            self.data[away_key] = away_standing

        # Determine winner
        if result.home_score > result.away_score:
            # Home team wins
            home_standing.wins += 1
            home_standing.home_wins += 1
            away_standing.losses += 1
            away_standing.away_losses += 1

            self.recent_results[(result.home_team.team_id, season_type)].append('W')
            self.recent_results[(result.away_team.team_id, season_type)].append('L')

            # Update head-to-head (now includes season_type)
            self._update_head_to_head(result.home_team.team_id, result.away_team.team_id, 'home', season_type)

        elif result.away_score > result.home_score:
            # Away team wins
            away_standing.wins += 1
            away_standing.away_wins += 1
            home_standing.losses += 1
            home_standing.home_losses += 1

            self.recent_results[(result.away_team.team_id, season_type)].append('W')
            self.recent_results[(result.home_team.team_id, season_type)].append('L')

            # Update head-to-head (now includes season_type)
            self._update_head_to_head(result.home_team.team_id, result.away_team.team_id, 'away', season_type)

        else:
            # Tie
            home_standing.ties += 1
            away_standing.ties += 1

            self.recent_results[(result.home_team.team_id, season_type)].append('T')
            self.recent_results[(result.away_team.team_id, season_type)].append('T')

            # Update head-to-head (now includes season_type)
            self._update_head_to_head(result.home_team.team_id, result.away_team.team_id, 'tie', season_type)

        # Update points
        home_standing.points_for += result.home_score
        home_standing.points_against += result.away_score
        away_standing.points_for += result.away_score
        away_standing.points_against += result.home_score

        # Update division/conference records
        self._update_division_conference_records(result, home_standing, away_standing)

        # Update streaks (now includes season_type)
        self._update_streaks(result.home_team.team_id, home_standing, season_type)
        self._update_streaks(result.away_team.team_id, away_standing, season_type)

        # Re-sort standings FOR THIS SEASON TYPE
        self._sort_standings_by_type(season_type)

        # Immediate database persistence for both teams (now includes season_type)
        self._persist_to_database(result.home_team.team_id, home_standing, season_type)
        self._persist_to_database(result.away_team.team_id, away_standing, season_type)

        self.logger.info(f"Updated {season_type} standings for game: {result.away_team.team_id} @ {result.home_team.team_id}")

    def get_division_standings(self, division: str, season_type: str = "regular_season") -> List[EnhancedTeamStanding]:
        """
        Get sorted standings for a division and season type.

        Args:
            division: Division name (e.g., "AFC East", "NFC North")
            season_type: "regular_season" or "playoffs" (default: "regular_season")

        Returns:
            Sorted list of team standings for this division/season_type
        """
        team_ids = self.division_standings.get(season_type, {}).get(division, [])
        return [
            self.data[f"{tid}_{season_type}"]
            for tid in team_ids
            if f"{tid}_{season_type}" in self.data
        ]

    def get_conference_standings(self, conference: str, season_type: str = "regular_season") -> List[EnhancedTeamStanding]:
        """
        Get sorted standings for a conference and season type.

        Args:
            conference: Conference name ('AFC' or 'NFC')
            season_type: "regular_season" or "playoffs" (default: "regular_season")

        Returns:
            Sorted list of team standings for this conference/season_type
        """
        team_ids = self.conference_standings.get(season_type, {}).get(conference, [])
        return [
            self.data[f"{tid}_{season_type}"]
            for tid in team_ids
            if f"{tid}_{season_type}" in self.data
        ]

    def get_playoff_picture(self) -> Dict[str, Any]:
        """
        Get current playoff seedings.

        Returns:
            Dictionary with playoff seedings by conference
        """
        playoff_picture = {}

        for conference in ['AFC', 'NFC']:
            standings = self.get_conference_standings(conference)

            # Division winners (top 4 seeds)
            division_winners = []
            wildcards = []

            for division, teams in NFL_DIVISIONS.items():
                if conference in division:
                    division_leader = self.get_division_standings(division)[0]
                    division_winners.append(division_leader)

            # Sort division winners by record
            division_winners.sort(key=lambda t: (t.win_percentage, t.wins), reverse=True)

            # Get wildcards (next best 3 teams)
            for team in standings:
                if team not in division_winners and len(wildcards) < 3:
                    wildcards.append(team)

            playoff_picture[conference] = {
                '1_seed': division_winners[0] if len(division_winners) > 0 else None,
                '2_seed': division_winners[1] if len(division_winners) > 1 else None,
                '3_seed': division_winners[2] if len(division_winners) > 2 else None,
                '4_seed': division_winners[3] if len(division_winners) > 3 else None,
                '5_seed': wildcards[0] if len(wildcards) > 0 else None,
                '6_seed': wildcards[1] if len(wildcards) > 1 else None,
                '7_seed': wildcards[2] if len(wildcards) > 2 else None
            }

        return playoff_picture

    def get_team_standing(self, team_id: int, season_type: str = "regular_season") -> Optional[EnhancedTeamStanding]:
        """
        Get standing for a specific team and season type.

        Args:
            team_id: Team identifier (1-32)
            season_type: "regular_season" or "playoffs" (default: "regular_season")

        Returns:
            Team standing if found, None otherwise
        """
        key = f"{team_id}_{season_type}"
        return self.data.get(key)

    def _initialize_standings(self, season_type: str = "regular_season") -> None:
        """
        Initialize standings for all 32 teams for a specific season type.

        Args:
            season_type: "regular_season" or "playoffs"
        """
        for team_id in range(1, 33):
            # Determine division place (1-4 within division)
            division_place = ((team_id - 1) % 4) + 1

            standing = EnhancedTeamStanding(
                team_id=team_id,
                wins=0,
                losses=0,
                ties=0,
                division_place=division_place
            )
            # Use composite key: team_id_season_type
            key = f"{team_id}_{season_type}"
            self.data[key] = standing

    def _create_standing_for_team(self, team_id: int, season_type: str) -> EnhancedTeamStanding:
        """
        Create a new standing record for a team/season_type combination.

        Used for lazy creation of playoff standings when first playoff game is played.

        Args:
            team_id: Team identifier (1-32)
            season_type: "regular_season" or "playoffs"

        Returns:
            New EnhancedTeamStanding with 0-0 record
        """
        division_place = ((team_id - 1) % 4) + 1
        return EnhancedTeamStanding(
            team_id=team_id,
            wins=0,
            losses=0,
            ties=0,
            division_place=division_place
        )

    def _sort_all_standings(self) -> None:
        """Sort all standings (division, conference, overall) for BOTH season types."""
        # Sort for both regular_season and playoffs
        for season_type in ["regular_season", "playoffs"]:
            self._sort_standings_by_type(season_type)

    def _sort_standings_by_type(self, season_type: str) -> None:
        """
        Sort standings for a specific season type.

        Args:
            season_type: "regular_season" or "playoffs"
        """
        # Get all teams for this season type
        teams_for_type = [
            standing for key, standing in self.data.items()
            if key.endswith(f"_{season_type}")
        ]

        # If no teams exist for this season type yet, skip
        if not teams_for_type:
            return

        # Sort each division
        for division, team_ids in NFL_DIVISIONS.items():
            division_teams = []
            for tid in team_ids:
                key = f"{tid}_{season_type}"
                if key in self.data:
                    division_teams.append(self.data[key])

            if division_teams:
                division_teams.sort(key=lambda t: (
                    t.win_percentage,
                    t.wins,
                    t.division_wins,
                    t.point_differential
                ), reverse=True)

                if season_type not in self.division_standings:
                    self.division_standings[season_type] = {}
                self.division_standings[season_type][division] = [t.team_id for t in division_teams]

                # Update division places
                for i, team in enumerate(division_teams):
                    team.division_place = i + 1

        # Sort each conference
        for conference, team_ids in NFL_CONFERENCES.items():
            conference_teams = []
            for tid in team_ids:
                key = f"{tid}_{season_type}"
                if key in self.data:
                    conference_teams.append(self.data[key])

            if conference_teams:
                conference_teams.sort(key=lambda t: (
                    t.win_percentage,
                    t.wins,
                    t.conference_wins,
                    t.point_differential
                ), reverse=True)

                if season_type not in self.conference_standings:
                    self.conference_standings[season_type] = {}
                self.conference_standings[season_type][conference] = [t.team_id for t in conference_teams]

        # Sort overall for this season type
        all_teams_for_type = list(teams_for_type)
        all_teams_for_type.sort(key=lambda t: (
            t.win_percentage,
            t.wins,
            t.point_differential
        ), reverse=True)
        self.overall_standings[season_type] = [t.team_id for t in all_teams_for_type]

    def _update_division_conference_records(self, result: GameResult,
                                           home_standing: EnhancedTeamStanding,
                                           away_standing: EnhancedTeamStanding) -> None:
        """Update division and conference win/loss records."""
        home_division = self._get_team_division(result.home_team_id)
        away_division = self._get_team_division(result.away_team_id)
        home_conference = self._get_team_conference(result.home_team_id)
        away_conference = self._get_team_conference(result.away_team_id)

        # Check if division game
        if home_division == away_division:
            if result.home_score > result.away_score:
                home_standing.division_wins += 1
                away_standing.division_losses += 1
            elif result.away_score > result.home_score:
                away_standing.division_wins += 1
                home_standing.division_losses += 1

        # Check if conference game
        if home_conference == away_conference:
            if result.home_score > result.away_score:
                home_standing.conference_wins += 1
                away_standing.conference_losses += 1
            elif result.away_score > result.home_score:
                away_standing.conference_wins += 1
                home_standing.conference_losses += 1

    def _update_head_to_head(self, team1_id: int, team2_id: int, winner: str, season_type: str) -> None:
        """
        Update head-to-head record for a specific season type.

        Args:
            team1_id: First team ID (home team typically)
            team2_id: Second team ID (away team typically)
            winner: 'home', 'away', or 'tie'
            season_type: "regular_season" or "playoffs"
        """
        # Key now includes season_type for separation
        key = tuple(sorted([team1_id, team2_id]) + [season_type])

        if winner == 'home' and team1_id < team2_id:
            self.head_to_head[key]['team1_wins'] += 1
        elif winner == 'home':
            self.head_to_head[key]['team2_wins'] += 1
        elif winner == 'away' and team1_id < team2_id:
            self.head_to_head[key]['team2_wins'] += 1
        elif winner == 'away':
            self.head_to_head[key]['team1_wins'] += 1
        else:  # tie
            self.head_to_head[key]['ties'] += 1

    def _update_streaks(self, team_id: int, standing: EnhancedTeamStanding, season_type: str) -> None:
        """
        Update win/loss streaks and last 5 games for a specific season type.

        Args:
            team_id: Team identifier
            standing: Team standing to update
            season_type: "regular_season" or "playoffs"
        """
        # Recent results now keyed by (team_id, season_type)
        recent = self.recent_results[(team_id, season_type)]

        # Calculate current streak
        if recent:
            current = recent[-1]
            streak_count = 1

            for i in range(len(recent) - 2, -1, -1):
                if recent[i] == current:
                    streak_count += 1
                else:
                    break

            standing.streak = f"{current}{streak_count}"

        # Calculate last 5
        if len(recent) >= 5:
            last_5 = recent[-5:]
            wins = last_5.count('W')
            losses = last_5.count('L')
            standing.last_5 = f"{wins}-{losses}"

    def _get_team_division(self, team_id: int) -> Optional[str]:
        """Get division for a team."""
        for division, teams in NFL_DIVISIONS.items():
            if team_id in teams:
                return division
        return None

    def _get_team_conference(self, team_id: int) -> Optional[str]:
        """Get conference for a team."""
        for conference, teams in NFL_CONFERENCES.items():
            if team_id in teams:
                return conference
        return None

    # REMOVED: get_standings() method - use DatabaseAPI.get_standings() instead
    # All retrieval operations should go through the database API for consistency

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize standings for persistence.

        Returns:
            Serializable dictionary
        """
        return {
            'standings': {
                team_id: {
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'ties': standing.ties,
                    'division_wins': standing.division_wins,
                    'division_losses': standing.division_losses,
                    'conference_wins': standing.conference_wins,
                    'conference_losses': standing.conference_losses,
                    'home_wins': standing.home_wins,
                    'home_losses': standing.home_losses,
                    'away_wins': standing.away_wins,
                    'away_losses': standing.away_losses,
                    'points_for': standing.points_for,
                    'points_against': standing.points_against,
                    'streak': standing.streak,
                    'last_5': standing.last_5,
                    'division_place': standing.division_place
                }
                for team_id, standing in self.data.items()
            },
            'head_to_head': {
                f"{k[0]}_{k[1]}": v for k, v in self.head_to_head.items()
            }
        }

    def _persist_to_database(self, team_id: int, standing: EnhancedTeamStanding, season_type: str) -> None:
        """
        Persist team standing to database immediately with season_type.

        Args:
            team_id: Team identifier
            standing: Team standing data
            season_type: "regular_season" or "playoffs"
        """
        if not self.db_connection or not self.dynasty_id or not self.current_season:
            self.logger.warning("Database persistence not available - missing connection or context")
            return

        try:
            # Use INSERT OR REPLACE to handle updates
            # CRITICAL: Include season_type in query for proper record separation
            query = '''
                INSERT OR REPLACE INTO standings (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    division_wins, division_losses, conference_wins, conference_losses,
                    home_wins, home_losses, away_wins, away_losses,
                    points_for, points_against, point_differential,
                    current_streak, division_rank
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            params = (
                self.dynasty_id, team_id, self.current_season, season_type,  # ⭐ Added season_type
                standing.wins, standing.losses, standing.ties,
                standing.division_wins, standing.division_losses,
                standing.conference_wins, standing.conference_losses,
                standing.home_wins, standing.home_losses,
                standing.away_wins, standing.away_losses,
                standing.points_for, standing.points_against,
                standing.point_differential, standing.streak,
                standing.division_place
            )

            self.db_connection.execute_update(query, params)
            self.logger.debug(f"Persisted {season_type} standings for team {team_id}")

        except Exception as e:
            self.logger.error(f"Failed to persist {season_type} standings for team {team_id}: {e}")