"""
Awards API for game_cycle.

Handles database operations for the NFL Awards System including:
- Award winners (MVP, OPOY, DPOY, OROY, DROY, CPOY, COY, EOY)
- Award nominees (top 10 candidates per award)
- All-Pro selections (First Team and Second Team)
- Pro Bowl selections (AFC/NFC rosters)
- Statistical leaders (top 10 per category)
"""

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Any

from .connection import GameCycleDatabase


# ============================================
# Dataclasses
# ============================================

@dataclass
class AwardDefinition:
    """Represents an award definition."""
    award_id: str
    award_name: str
    award_type: str  # 'INDIVIDUAL', 'ALL_PRO', 'PRO_BOWL'
    category: Optional[str] = None  # 'OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'COACHING', 'MANAGEMENT'
    description: Optional[str] = None
    eligible_positions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'award_id': self.award_id,
            'award_name': self.award_name,
            'award_type': self.award_type,
            'category': self.category,
            'description': self.description,
            'eligible_positions': self.eligible_positions,
        }


@dataclass
class AwardWinner:
    """Represents an award winner or finalist."""
    dynasty_id: str
    season: int
    award_id: str
    player_id: int
    team_id: int
    vote_points: int
    vote_share: float
    rank: int
    is_winner: bool = False
    voting_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'award_id': self.award_id,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'vote_points': self.vote_points,
            'vote_share': self.vote_share,
            'rank': self.rank,
            'is_winner': self.is_winner,
            'voting_date': self.voting_date,
        }


@dataclass
class AwardNominee:
    """Represents an award nominee."""
    dynasty_id: str
    season: int
    award_id: str
    player_id: int
    team_id: int
    nomination_rank: int
    stats_snapshot: Optional[Dict[str, Any]] = None
    grade_snapshot: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'award_id': self.award_id,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'nomination_rank': self.nomination_rank,
            'stats_snapshot': self.stats_snapshot,
            'grade_snapshot': self.grade_snapshot,
        }


@dataclass
class AllProSelection:
    """Represents an All-Pro selection."""
    dynasty_id: str
    season: int
    player_id: int
    team_id: int
    position: str
    team_type: str  # 'FIRST_TEAM' or 'SECOND_TEAM'
    vote_points: Optional[int] = None
    vote_share: Optional[float] = None
    selection_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'position': self.position,
            'team_type': self.team_type,
            'vote_points': self.vote_points,
            'vote_share': self.vote_share,
            'selection_date': self.selection_date,
        }


@dataclass
class ProBowlSelection:
    """Represents a Pro Bowl selection."""
    dynasty_id: str
    season: int
    player_id: int
    team_id: int
    conference: str  # 'AFC' or 'NFC'
    position: str
    selection_type: str  # 'STARTER', 'RESERVE', 'ALTERNATE'
    combined_score: Optional[float] = None
    selection_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'conference': self.conference,
            'position': self.position,
            'selection_type': self.selection_type,
            'combined_score': self.combined_score,
            'selection_date': self.selection_date,
        }


@dataclass
class StatisticalLeader:
    """Represents a statistical leader entry."""
    dynasty_id: str
    season: int
    stat_category: str
    player_id: int
    team_id: int
    position: str
    stat_value: int
    league_rank: int
    recorded_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'stat_category': self.stat_category,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'position': self.position,
            'stat_value': self.stat_value,
            'league_rank': self.league_rank,
            'recorded_date': self.recorded_date,
        }


@dataclass
class AwardRaceEntry:
    """Represents an entry in the award race tracking table."""
    dynasty_id: str
    season: int
    week: int
    award_type: str  # 'mvp', 'opoy', 'dpoy', 'oroy', 'droy'
    player_id: int
    team_id: int
    position: str
    cumulative_score: float
    rank: int
    week_score: Optional[float] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'week': self.week,
            'award_type': self.award_type,
            'player_id': self.player_id,
            'team_id': self.team_id,
            'position': self.position,
            'cumulative_score': self.cumulative_score,
            'week_score': self.week_score,
            'rank': self.rank,
            'first_name': self.first_name,
            'last_name': self.last_name,
        }


@dataclass
class SuperBowlMVP:
    """Represents a Super Bowl MVP record."""
    dynasty_id: str
    season: int
    game_id: str
    player_id: int
    player_name: str
    team_id: int
    position: str
    winning_team: bool
    stat_line: Optional[Dict[str, Any]] = None
    mvp_score: float = 0.0
    awarded_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'game_id': self.game_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'winning_team': self.winning_team,
            'stat_line': self.stat_line,
            'mvp_score': self.mvp_score,
            'awarded_date': self.awarded_date,
        }


# ============================================
# AwardsAPI Class
# ============================================

class AwardsAPI:
    """
    API for Awards System database operations.

    Handles:
    - Award winners (top 5 vote-getters per award)
    - Award nominees (top 10 candidates)
    - All-Pro selections (44 players)
    - Pro Bowl selections (AFC/NFC rosters)
    - Statistical leaders (top 10 per category)
    """

    # Standard award definitions
    AWARD_DEFINITIONS = [
        ('mvp', 'Most Valuable Player', 'INDIVIDUAL', None,
         'The most outstanding player in the league', None),
        ('opoy', 'Offensive Player of the Year', 'INDIVIDUAL', 'OFFENSE',
         'The most outstanding offensive player',
         '["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "FB"]'),
        ('dpoy', 'Defensive Player of the Year', 'INDIVIDUAL', 'DEFENSE',
         'The most outstanding defensive player',
         '["LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS", "EDGE"]'),
        ('oroy', 'Offensive Rookie of the Year', 'INDIVIDUAL', 'OFFENSE',
         'The most outstanding offensive rookie',
         '["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "FB"]'),
        ('droy', 'Defensive Rookie of the Year', 'INDIVIDUAL', 'DEFENSE',
         'The most outstanding defensive rookie',
         '["LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS", "EDGE"]'),
        ('cpoy', 'Comeback Player of the Year', 'INDIVIDUAL', None,
         'Outstanding comeback from injury or decline', None),
        ('coy', 'Coach of the Year', 'INDIVIDUAL', 'COACHING',
         'The most outstanding head coach', None),
        ('eoy', 'Executive of the Year', 'INDIVIDUAL', 'MANAGEMENT',
         'The most outstanding general manager', None),
    ]

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # ============================================
    # Award Definitions
    # ============================================

    def initialize_award_definitions(self) -> int:
        """
        Ensure all 8 standard award definitions exist in the database.

        Returns:
            Number of awards inserted (0 if already exist)
        """
        count = 0
        for award_def in self.AWARD_DEFINITIONS:
            try:
                self.db.execute(
                    """INSERT OR IGNORE INTO award_definitions
                       (award_id, award_name, award_type, category, description, eligible_positions)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    award_def
                )
                count += 1
            except Exception:
                pass  # Already exists
        return count

    def get_award_definition(self, award_id: str) -> Optional[AwardDefinition]:
        """
        Get a specific award definition.

        Args:
            award_id: Award identifier (e.g., 'mvp', 'opoy')

        Returns:
            AwardDefinition if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT award_id, award_name, award_type, category, description, eligible_positions
               FROM award_definitions WHERE award_id = ?""",
            (award_id,)
        )
        if not row:
            return None
        return self._row_to_award_definition(row)

    def get_all_award_definitions(self) -> List[AwardDefinition]:
        """
        Get all award definitions.

        Returns:
            List of all AwardDefinition records
        """
        rows = self.db.query_all(
            """SELECT award_id, award_name, award_type, category, description, eligible_positions
               FROM award_definitions ORDER BY award_id"""
        )
        return [self._row_to_award_definition(row) for row in rows]

    # ============================================
    # Award Winners
    # ============================================

    def insert_award_winner(
        self,
        dynasty_id: str,
        season: int,
        award_id: str,
        player_id: int,
        team_id: int,
        vote_points: int,
        vote_share: float,
        rank: int,
        is_winner: bool = False,
        voting_date: Optional[str] = None
    ) -> bool:
        """
        Insert an award winner or finalist.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_id: Award identifier
            player_id: Player ID
            team_id: Team ID (1-32)
            vote_points: Total weighted vote points
            vote_share: Percentage of possible points (0.0-1.0)
            rank: Finish position (1=winner, 2-5=finalists)
            is_winner: True if this is the winner (rank 1)
            voting_date: Date of voting (optional)

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO award_winners
               (dynasty_id, season, award_id, player_id, team_id,
                vote_points, vote_share, rank, is_winner, voting_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, award_id, player_id, team_id,
                vote_points, vote_share, rank, 1 if is_winner else 0,
                voting_date or date.today().isoformat()
            )
        )
        return True

    def get_award_winners(
        self,
        dynasty_id: str,
        season: int,
        award_id: Optional[str] = None
    ) -> List[AwardWinner]:
        """
        Get award winners/finalists for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_id: Optional filter by specific award

        Returns:
            List of AwardWinner records sorted by award_id and rank
        """
        if award_id:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, award_id, player_id, team_id,
                          vote_points, vote_share, rank, is_winner, voting_date
                   FROM award_winners
                   WHERE dynasty_id = ? AND season = ? AND award_id = ?
                   ORDER BY rank""",
                (dynasty_id, season, award_id)
            )
        else:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, award_id, player_id, team_id,
                          vote_points, vote_share, rank, is_winner, voting_date
                   FROM award_winners
                   WHERE dynasty_id = ? AND season = ?
                   ORDER BY award_id, rank""",
                (dynasty_id, season)
            )
        return [self._row_to_award_winner(row) for row in rows]

    def get_player_awards(
        self,
        dynasty_id: str,
        player_id: int
    ) -> List[AwardWinner]:
        """
        Get all awards for a specific player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            List of AwardWinner records sorted by season descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, award_id, player_id, team_id,
                      vote_points, vote_share, rank, is_winner, voting_date
               FROM award_winners
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY season DESC, award_id""",
            (dynasty_id, player_id)
        )
        return [self._row_to_award_winner(row) for row in rows]

    # ============================================
    # Award Nominees
    # ============================================

    def insert_nominee(
        self,
        dynasty_id: str,
        season: int,
        award_id: str,
        player_id: int,
        team_id: int,
        nomination_rank: int,
        stats_snapshot: Optional[Dict[str, Any]] = None,
        grade_snapshot: Optional[float] = None
    ) -> bool:
        """
        Insert an award nominee.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_id: Award identifier
            player_id: Player ID
            team_id: Team ID (1-32)
            nomination_rank: Ranking among nominees (1-10)
            stats_snapshot: JSON-serializable stats dictionary
            grade_snapshot: Overall grade at nomination

        Returns:
            True if successful
        """
        stats_json = json.dumps(stats_snapshot) if stats_snapshot is not None else None
        self.db.execute(
            """INSERT OR REPLACE INTO award_nominees
               (dynasty_id, season, award_id, player_id, team_id,
                nomination_rank, stats_snapshot, grade_snapshot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, award_id, player_id, team_id,
                nomination_rank, stats_json, grade_snapshot
            )
        )
        return True

    def get_nominees(
        self,
        dynasty_id: str,
        season: int,
        award_id: str
    ) -> List[AwardNominee]:
        """
        Get nominees for a specific award.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_id: Award identifier

        Returns:
            List of AwardNominee records sorted by nomination_rank
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, award_id, player_id, team_id,
                      nomination_rank, stats_snapshot, grade_snapshot
               FROM award_nominees
               WHERE dynasty_id = ? AND season = ? AND award_id = ?
               ORDER BY nomination_rank""",
            (dynasty_id, season, award_id)
        )
        return [self._row_to_award_nominee(row) for row in rows]

    # ============================================
    # All-Pro Selections
    # ============================================

    def insert_all_pro_selection(
        self,
        dynasty_id: str,
        season: int,
        player_id: int,
        team_id: int,
        position: str,
        team_type: str,
        vote_points: Optional[int] = None,
        vote_share: Optional[float] = None,
        selection_date: Optional[str] = None
    ) -> bool:
        """
        Insert an All-Pro selection.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            player_id: Player ID
            team_id: Team ID (1-32)
            position: Player position
            team_type: 'FIRST_TEAM' or 'SECOND_TEAM'
            vote_points: Total vote points (optional)
            vote_share: Vote share percentage (optional)
            selection_date: Date of selection (optional)

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO all_pro_selections
               (dynasty_id, season, player_id, team_id, position,
                team_type, vote_points, vote_share, selection_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, player_id, team_id, position,
                team_type, vote_points, vote_share,
                selection_date or date.today().isoformat()
            )
        )
        return True

    def get_all_pro_teams(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, List[AllProSelection]]:
        """
        Get All-Pro teams for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary with 'FIRST_TEAM' and 'SECOND_TEAM' keys,
            each containing a list of AllProSelection records
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, player_id, team_id, position,
                      team_type, vote_points, vote_share, selection_date
               FROM all_pro_selections
               WHERE dynasty_id = ? AND season = ?
               ORDER BY team_type, position""",
            (dynasty_id, season)
        )

        result = {'FIRST_TEAM': [], 'SECOND_TEAM': []}
        for row in rows:
            selection = self._row_to_all_pro_selection(row)
            if selection.team_type in result:
                result[selection.team_type].append(selection)
        return result

    def get_player_all_pro_history(
        self,
        dynasty_id: str,
        player_id: int
    ) -> List[AllProSelection]:
        """
        Get All-Pro history for a specific player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            List of AllProSelection records sorted by season descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, player_id, team_id, position,
                      team_type, vote_points, vote_share, selection_date
               FROM all_pro_selections
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY season DESC""",
            (dynasty_id, player_id)
        )
        return [self._row_to_all_pro_selection(row) for row in rows]

    # ============================================
    # Pro Bowl Selections
    # ============================================

    def insert_pro_bowl_selection(
        self,
        dynasty_id: str,
        season: int,
        player_id: int,
        team_id: int,
        conference: str,
        position: str,
        selection_type: str,
        combined_score: Optional[float] = None,
        selection_date: Optional[str] = None
    ) -> bool:
        """
        Insert a Pro Bowl selection.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            player_id: Player ID
            team_id: Team ID (1-32)
            conference: 'AFC' or 'NFC'
            position: Player position
            selection_type: 'STARTER', 'RESERVE', or 'ALTERNATE'
            combined_score: Fan+Coach+Player combined score (optional)
            selection_date: Date of selection (optional)

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO pro_bowl_selections
               (dynasty_id, season, player_id, team_id, conference,
                position, selection_type, combined_score, selection_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, player_id, team_id, conference,
                position, selection_type, combined_score,
                selection_date or date.today().isoformat()
            )
        )
        return True

    def get_pro_bowl_roster(
        self,
        dynasty_id: str,
        season: int,
        conference: Optional[str] = None
    ) -> Dict[str, List[ProBowlSelection]]:
        """
        Get Pro Bowl roster for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            conference: Optional filter by 'AFC' or 'NFC'

        Returns:
            Dictionary with 'AFC' and/or 'NFC' keys,
            each containing a list of ProBowlSelection records
        """
        if conference:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, player_id, team_id, conference,
                          position, selection_type, combined_score, selection_date
                   FROM pro_bowl_selections
                   WHERE dynasty_id = ? AND season = ? AND conference = ?
                   ORDER BY selection_type, position""",
                (dynasty_id, season, conference)
            )
        else:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, player_id, team_id, conference,
                          position, selection_type, combined_score, selection_date
                   FROM pro_bowl_selections
                   WHERE dynasty_id = ? AND season = ?
                   ORDER BY conference, selection_type, position""",
                (dynasty_id, season)
            )

        result: Dict[str, List[ProBowlSelection]] = {}
        for row in rows:
            selection = self._row_to_pro_bowl_selection(row)
            if selection.conference not in result:
                result[selection.conference] = []
            result[selection.conference].append(selection)
        return result

    def get_player_pro_bowl_history(
        self,
        dynasty_id: str,
        player_id: int
    ) -> List[ProBowlSelection]:
        """
        Get Pro Bowl history for a specific player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            List of ProBowlSelection records sorted by season descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, player_id, team_id, conference,
                      position, selection_type, combined_score, selection_date
               FROM pro_bowl_selections
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY season DESC""",
            (dynasty_id, player_id)
        )
        return [self._row_to_pro_bowl_selection(row) for row in rows]

    # ============================================
    # Statistical Leaders
    # ============================================

    def record_stat_leader(
        self,
        dynasty_id: str,
        season: int,
        stat_category: str,
        player_id: int,
        team_id: int,
        position: str,
        stat_value: int,
        league_rank: int,
        recorded_date: Optional[str] = None
    ) -> bool:
        """
        Record a statistical leader entry.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stat_category: Stat category (e.g., 'passing_yards', 'rushing_yards')
            player_id: Player ID
            team_id: Team ID (1-32)
            position: Player position
            stat_value: The stat value
            league_rank: League rank for this stat (1-10)
            recorded_date: Date recorded (optional)

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO statistical_leaders
               (dynasty_id, season, stat_category, player_id, team_id,
                position, stat_value, league_rank, recorded_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, stat_category, player_id, team_id,
                position, stat_value, league_rank,
                recorded_date or date.today().isoformat()
            )
        )
        return True

    def get_stat_leaders(
        self,
        dynasty_id: str,
        season: int,
        category: Optional[str] = None
    ) -> List[StatisticalLeader]:
        """
        Get statistical leaders for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            category: Optional filter by stat category

        Returns:
            List of StatisticalLeader records
        """
        if category:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, stat_category, player_id, team_id,
                          position, stat_value, league_rank, recorded_date
                   FROM statistical_leaders
                   WHERE dynasty_id = ? AND season = ? AND stat_category = ?
                   ORDER BY league_rank""",
                (dynasty_id, season, category)
            )
        else:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, stat_category, player_id, team_id,
                          position, stat_value, league_rank, recorded_date
                   FROM statistical_leaders
                   WHERE dynasty_id = ? AND season = ?
                   ORDER BY stat_category, league_rank""",
                (dynasty_id, season)
            )
        return [self._row_to_stat_leader(row) for row in rows]

    def get_player_stat_leader_history(
        self,
        dynasty_id: str,
        player_id: int
    ) -> List[StatisticalLeader]:
        """
        Get statistical leader history for a specific player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            List of StatisticalLeader records sorted by season descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, season, stat_category, player_id, team_id,
                      position, stat_value, league_rank, recorded_date
               FROM statistical_leaders
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY season DESC, stat_category""",
            (dynasty_id, player_id)
        )
        return [self._row_to_stat_leader(row) for row in rows]

    # ============================================
    # Award Race Tracking (Weekly Performance Tracking)
    # ============================================

    def upsert_award_race_entry(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        award_type: str,
        player_id: int,
        team_id: int,
        position: str,
        cumulative_score: float,
        rank: int,
        week_score: Optional[float] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> bool:
        """
        Insert or update an award race tracking entry.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number (10-18 typically)
            award_type: Award type ('mvp', 'opoy', 'dpoy', 'oroy', 'droy')
            player_id: Player ID
            team_id: Team ID (1-32)
            position: Player position
            cumulative_score: Season-to-date weighted score
            rank: Current rank for this award
            week_score: This week's performance score (optional)
            first_name: Player first name (denormalized)
            last_name: Player last name (denormalized)

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO award_race_tracking
               (dynasty_id, season, week, award_type, player_id, team_id,
                position, cumulative_score, week_score, rank, first_name, last_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, week, award_type, player_id, team_id,
                position, cumulative_score, week_score, rank, first_name, last_name
            )
        )
        return True

    def batch_upsert_award_race_entries(
        self,
        entries: List[AwardRaceEntry]
    ) -> int:
        """
        Batch insert/update multiple award race tracking entries.

        Args:
            entries: List of AwardRaceEntry objects

        Returns:
            Number of entries inserted/updated
        """
        if not entries:
            return 0

        data = [
            (
                e.dynasty_id, e.season, e.week, e.award_type, e.player_id, e.team_id,
                e.position, e.cumulative_score, e.week_score, e.rank, e.first_name, e.last_name
            )
            for e in entries
        ]

        self.db.executemany(
            """INSERT OR REPLACE INTO award_race_tracking
               (dynasty_id, season, week, award_type, player_id, team_id,
                position, cumulative_score, week_score, rank, first_name, last_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data
        )
        return len(entries)

    def get_award_race_standings(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        award_type: Optional[str] = None
    ) -> List[AwardRaceEntry]:
        """
        Get current award race standings for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            award_type: Optional filter by award type

        Returns:
            List of AwardRaceEntry records sorted by award_type and rank
        """
        if award_type:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, week, award_type, player_id, team_id,
                          position, cumulative_score, week_score, rank, first_name, last_name
                   FROM award_race_tracking
                   WHERE dynasty_id = ? AND season = ? AND week = ? AND award_type = ?
                   ORDER BY rank""",
                (dynasty_id, season, week, award_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT dynasty_id, season, week, award_type, player_id, team_id,
                          position, cumulative_score, week_score, rank, first_name, last_name
                   FROM award_race_tracking
                   WHERE dynasty_id = ? AND season = ? AND week = ?
                   ORDER BY award_type, rank""",
                (dynasty_id, season, week)
            )
        return [self._row_to_award_race_entry(row) for row in rows]

    def get_latest_award_race_standings(
        self,
        dynasty_id: str,
        season: int,
        award_type: Optional[str] = None
    ) -> List[AwardRaceEntry]:
        """
        Get the most recent award race standings for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_type: Optional filter by award type

        Returns:
            List of AwardRaceEntry records from the latest tracked week
        """
        # First, find the latest week with tracking data
        latest_week_row = self.db.query_one(
            """SELECT MAX(week) as latest_week
               FROM award_race_tracking
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )

        if not latest_week_row or latest_week_row['latest_week'] is None:
            return []

        latest_week = latest_week_row['latest_week']
        return self.get_award_race_standings(dynasty_id, season, latest_week, award_type)

    def get_tracked_nominees(
        self,
        dynasty_id: str,
        season: int,
        award_type: str
    ) -> List[AwardRaceEntry]:
        """
        Get final tracked nominees for end-of-season award calculation.
        Returns the latest week's tracked players for the specified award.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            award_type: Award type ('mvp', 'opoy', 'dpoy', 'oroy', 'droy')

        Returns:
            List of AwardRaceEntry records for the award
        """
        return self.get_latest_award_race_standings(dynasty_id, season, award_type)

    def has_tracking_data(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """
        Check if award race tracking data exists for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if tracking data exists
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM award_race_tracking
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return row is not None and row['count'] > 0

    def clear_award_race_tracking(
        self,
        dynasty_id: str,
        season: int,
        week: Optional[int] = None
    ) -> int:
        """
        Clear award race tracking data.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Optional specific week to clear (clears all if None)

        Returns:
            Number of records deleted
        """
        if week is not None:
            cursor = self.db.execute(
                """DELETE FROM award_race_tracking
                   WHERE dynasty_id = ? AND season = ? AND week = ?""",
                (dynasty_id, season, week)
            )
        else:
            cursor = self.db.execute(
                """DELETE FROM award_race_tracking
                   WHERE dynasty_id = ? AND season = ?""",
                (dynasty_id, season)
            )
        return cursor.rowcount

    # ============================================
    # Super Bowl MVP
    # ============================================

    def _ensure_super_bowl_mvp_table(self) -> None:
        """Ensure the super_bowl_mvp table exists."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS super_bowl_mvp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                game_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
                position TEXT,
                winning_team INTEGER DEFAULT 1,
                stat_line TEXT,
                mvp_score REAL DEFAULT 0,
                awarded_date TEXT,
                UNIQUE(dynasty_id, season)
            )
        """)

    def insert_super_bowl_mvp(
        self,
        dynasty_id: str,
        season: int,
        game_id: str,
        player_id: int,
        player_name: str,
        team_id: int,
        position: str,
        winning_team: bool = True,
        stat_line: Optional[Dict[str, Any]] = None,
        mvp_score: float = 0.0,
        awarded_date: Optional[str] = None
    ) -> bool:
        """
        Insert a Super Bowl MVP record.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            game_id: Super Bowl game ID
            player_id: MVP player ID
            player_name: MVP player name
            team_id: MVP player's team ID
            position: Player position
            winning_team: True if MVP was on winning team
            stat_line: Dict of key stats from the game
            mvp_score: Calculated MVP score
            awarded_date: Date awarded (optional)

        Returns:
            True if successful
        """
        self._ensure_super_bowl_mvp_table()
        stat_line_json = json.dumps(stat_line) if stat_line is not None else None

        self.db.execute(
            """INSERT OR REPLACE INTO super_bowl_mvp
               (dynasty_id, season, game_id, player_id, player_name, team_id,
                position, winning_team, stat_line, mvp_score, awarded_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, game_id, player_id, player_name, team_id,
                position, 1 if winning_team else 0, stat_line_json, mvp_score,
                awarded_date or date.today().isoformat()
            )
        )
        return True

    def get_super_bowl_mvp(
        self,
        dynasty_id: str,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get Super Bowl MVP for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary with MVP data, or None if not found
        """
        self._ensure_super_bowl_mvp_table()
        row = self.db.query_one(
            """SELECT dynasty_id, season, game_id, player_id, player_name, team_id,
                      position, winning_team, stat_line, mvp_score, awarded_date
               FROM super_bowl_mvp
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        if not row:
            return None

        stat_line = None
        if row['stat_line']:
            try:
                stat_line = json.loads(row['stat_line'])
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'dynasty_id': row['dynasty_id'],
            'season': row['season'],
            'game_id': row['game_id'],
            'player_id': row['player_id'],
            'player_name': row['player_name'],
            'team_id': row['team_id'],
            'position': row['position'],
            'winning_team': bool(row['winning_team']),
            'stat_line': stat_line,
            'mvp_score': row['mvp_score'],
            'awarded_date': row['awarded_date'],
        }

    def has_super_bowl_mvp(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """
        Check if Super Bowl MVP exists for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if MVP exists
        """
        self._ensure_super_bowl_mvp_table()
        row = self.db.query_one(
            """SELECT COUNT(*) as count FROM super_bowl_mvp
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return row is not None and row['count'] > 0

    # ============================================
    # Deletion Methods (for testing)
    # ============================================

    def clear_season_awards(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, int]:
        """
        Clear all award data for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary with counts of deleted records per table
        """
        counts = {}

        cursor = self.db.execute(
            "DELETE FROM award_winners WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['award_winners'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM award_nominees WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['award_nominees'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM all_pro_selections WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['all_pro_selections'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM pro_bowl_selections WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['pro_bowl_selections'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM statistical_leaders WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['statistical_leaders'] = cursor.rowcount

        # Also clear Super Bowl MVP (table may not exist in older databases)
        try:
            cursor = self.db.execute(
                "DELETE FROM super_bowl_mvp WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season)
            )
            counts['super_bowl_mvp'] = cursor.rowcount
        except Exception:
            counts['super_bowl_mvp'] = 0

        return counts

    def clear_player_awards(
        self,
        dynasty_id: str,
        player_id: int
    ) -> Dict[str, int]:
        """
        Clear all award data for a player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            Dictionary with counts of deleted records per table
        """
        counts = {}

        cursor = self.db.execute(
            "DELETE FROM award_winners WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['award_winners'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM award_nominees WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['award_nominees'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM all_pro_selections WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['all_pro_selections'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM pro_bowl_selections WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['pro_bowl_selections'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM statistical_leaders WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['statistical_leaders'] = cursor.rowcount

        return counts

    # ============================================
    # Private Helper Methods
    # ============================================

    def _row_to_award_definition(self, row) -> AwardDefinition:
        """Convert database row to AwardDefinition."""
        eligible_positions = None
        if row['eligible_positions']:
            try:
                eligible_positions = json.loads(row['eligible_positions'])
            except (json.JSONDecodeError, TypeError):
                pass

        return AwardDefinition(
            award_id=row['award_id'],
            award_name=row['award_name'],
            award_type=row['award_type'],
            category=row['category'],
            description=row['description'],
            eligible_positions=eligible_positions,
        )

    def _row_to_award_winner(self, row) -> AwardWinner:
        """Convert database row to AwardWinner."""
        return AwardWinner(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            award_id=row['award_id'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            vote_points=row['vote_points'],
            vote_share=row['vote_share'],
            rank=row['rank'],
            is_winner=bool(row['is_winner']),
            voting_date=row['voting_date'],
        )

    def _row_to_award_nominee(self, row) -> AwardNominee:
        """Convert database row to AwardNominee."""
        stats_snapshot = None
        if row['stats_snapshot']:
            try:
                stats_snapshot = json.loads(row['stats_snapshot'])
            except (json.JSONDecodeError, TypeError):
                pass

        return AwardNominee(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            award_id=row['award_id'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            nomination_rank=row['nomination_rank'],
            stats_snapshot=stats_snapshot,
            grade_snapshot=row['grade_snapshot'],
        )

    def _row_to_all_pro_selection(self, row) -> AllProSelection:
        """Convert database row to AllProSelection."""
        return AllProSelection(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            position=row['position'],
            team_type=row['team_type'],
            vote_points=row['vote_points'],
            vote_share=row['vote_share'],
            selection_date=row['selection_date'],
        )

    def _row_to_pro_bowl_selection(self, row) -> ProBowlSelection:
        """Convert database row to ProBowlSelection."""
        return ProBowlSelection(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            conference=row['conference'],
            position=row['position'],
            selection_type=row['selection_type'],
            combined_score=row['combined_score'],
            selection_date=row['selection_date'],
        )

    def _row_to_stat_leader(self, row) -> StatisticalLeader:
        """Convert database row to StatisticalLeader."""
        return StatisticalLeader(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            stat_category=row['stat_category'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            position=row['position'],
            stat_value=row['stat_value'],
            league_rank=row['league_rank'],
            recorded_date=row['recorded_date'],
        )

    def _row_to_award_race_entry(self, row) -> AwardRaceEntry:
        """Convert database row to AwardRaceEntry."""
        return AwardRaceEntry(
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            week=row['week'],
            award_type=row['award_type'],
            player_id=row['player_id'],
            team_id=row['team_id'],
            position=row['position'],
            cumulative_score=row['cumulative_score'],
            week_score=row['week_score'],
            rank=row['rank'],
            first_name=row['first_name'],
            last_name=row['last_name'],
        )
