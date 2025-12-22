"""
Awards Service - Main orchestrator for NFL award calculations.

Coordinates eligibility checking, criteria scoring, voting simulation,
and database storage for all awards including:
- 6 Major Awards: MVP, OPOY, DPOY, OROY, DROY, CPOY
- All-Pro Teams: 44 players (22 First Team + 22 Second Team)
- Pro Bowl Rosters: AFC and NFC conference selections
- Statistical Leaders: Top 10 in 15 categories

Part of Milestone 10: Awards System, Tollgate 4.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Set

from .awards.models import (
    AwardType,
    AwardScore,
    PlayerCandidate,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
)
from .awards.result_models import (
    AwardResult,
    AllProTeam,
    AllProSelection,
    ProBowlRoster,
    ProBowlSelection,
    StatisticalLeadersResult,
    StatisticalLeaderEntry,
    SuperBowlMVPResult,
)

logger = logging.getLogger(__name__)


# ============================================
# Constants
# ============================================

# All-Pro position slots (22 total per team)
ALL_PRO_SLOTS: Dict[str, int] = {
    # Offense (11)
    'QB': 1,
    'RB': 2,
    'FB': 1,
    'WR': 2,
    'TE': 1,
    'LT': 1,
    'LG': 1,
    'C': 1,
    'RG': 1,
    'RT': 1,
    # Defense (11)
    'EDGE': 2,
    'DT': 2,
    'LOLB': 1,
    'MLB': 1,
    'ROLB': 1,
    'CB': 2,
    'FS': 1,
    'SS': 1,
    # Special Teams (2)
    'K': 1,
    'P': 1,
}

# Pro Bowl slots per position per conference (matches real NFL: 44 per conference)
PRO_BOWL_SLOTS: Dict[str, int] = {
    # Offense (21)
    'QB': 3,
    'RB': 3,
    'FB': 1,
    'WR': 4,
    'TE': 2,
    'OT': 3,     # Offensive Tackles (was LT: 2, RT: 2 = 4 total)
    'OG': 3,     # Offensive Guards (was LG: 2, RG: 2 = 4 total)
    'C': 2,      # Centers (unchanged)
    # Defense (18)
    'DE': 3,     # Defensive Ends (was EDGE: 4)
    'DT': 3,     # Defensive Tackles (was 4)
    'OLB': 3,    # Outside Linebackers (was LOLB: 2, ROLB: 2 = 4 total)
    'ILB': 2,    # Inside Linebackers (was MLB: 2)
    'CB': 4,     # Cornerbacks (unchanged)
    'FS': 1,     # Free Safety (was 2)
    'SS': 2,     # Strong Safeties (unchanged)
    # Special Teams (5)
    'K': 1,      # Kicker (unchanged)
    'P': 1,      # Punter (unchanged)
    'LS': 1,     # Long Snapper (NEW)
    'RS': 1,     # Return Specialist (NEW)
    'ST': 1,     # Special Teamer (NEW)
}
# Total: 44 per conference, 88 total (matches real NFL Pro Bowl)

# Maps Pro Bowl slot positions to actual player positions
# This allows consolidated Pro Bowl positions (OT, OG, OLB) to include multiple player positions
PRO_BOWL_POSITION_MAPPING: Dict[str, List[str]] = {
    # Offensive Line (consolidated)
    'OT': ['LT', 'RT', 'T', 'OT'],           # Offensive Tackles
    'OG': ['LG', 'RG', 'G', 'OG'],           # Offensive Guards
    'C': ['C'],                               # Centers
    # Defensive Line (consolidated)
    'DE': ['DE', 'EDGE', 'LE', 'RE'],        # Defensive Ends
    'DT': ['DT', 'NT'],                       # Defensive Tackles
    # Linebackers (consolidated)
    'OLB': ['OLB', 'LOLB', 'ROLB'],          # Outside Linebackers
    'ILB': ['ILB', 'MLB', 'LB'],             # Inside Linebackers
    # Defensive Backs
    'FS': ['FS'],                             # Free Safeties
    'SS': ['SS'],                             # Strong Safeties
    'CB': ['CB'],                             # Cornerbacks
    # Special Teams
    'LS': ['LS'],                             # Long Snappers
    'RS': ['KR', 'PR'],                       # Return Specialists (kick/punt returners)
    'ST': ['ST'],                             # Special Teamers (non-primary position)
    # Direct position mappings (unchanged positions)
    'QB': ['QB'],                             # Quarterbacks
    'RB': ['RB'],                             # Running Backs
    'FB': ['FB'],                             # Fullbacks
    'WR': ['WR'],                             # Wide Receivers
    'TE': ['TE'],                             # Tight Ends
    'K': ['K'],                               # Kickers
    'P': ['P'],                               # Punters
}

# Position name mapping (full name -> abbreviation for Pro Bowl/All-Pro matching)
POSITION_TO_ABBREVIATION: Dict[str, str] = {
    # Offense
    'quarterback': 'QB',
    'running_back': 'RB',
    'halfback': 'RB',
    'fullback': 'FB',
    'wide_receiver': 'WR',
    'tight_end': 'TE',
    'left_tackle': 'LT',
    'left_guard': 'LG',
    'center': 'C',
    'right_guard': 'RG',
    'right_tackle': 'RT',
    'offensive_tackle': 'LT',  # Default to LT
    'offensive_guard': 'LG',  # Default to LG
    'guard': 'LG',
    'tackle': 'LT',
    # Defense
    'defensive_end': 'EDGE',
    'edge': 'EDGE',
    'defensive_tackle': 'DT',
    'nose_tackle': 'DT',
    'linebacker': 'MLB',  # Generic linebacker -> MLB
    'inside_linebacker': 'MLB',
    'middle_linebacker': 'MLB',
    'mike_linebacker': 'MLB',
    'outside_linebacker': 'LOLB',  # Default to LOLB
    'left_outside_linebacker': 'LOLB',
    'right_outside_linebacker': 'ROLB',
    'sam_linebacker': 'ROLB',
    'will_linebacker': 'LOLB',
    'cornerback': 'CB',
    'safety': 'FS',  # Generic safety -> FS
    'free_safety': 'FS',
    'strong_safety': 'SS',
    # Special Teams
    'kicker': 'K',
    'punter': 'P',
    'long_snapper': 'LS',
}

# Statistical leader categories
STAT_CATEGORIES: List[tuple[str, Optional[str]]] = [
    # Passing (QB-only)
    ('passing_yards', 'QB'),
    ('passing_tds', 'QB'),
    ('passer_rating', 'QB'),
    # Rushing (all eligible)
    ('rushing_yards', None),
    ('rushing_tds', None),
    # Receiving (all eligible)
    ('receiving_yards', None),
    ('receiving_tds', None),
    ('receptions', None),
    # Defense (all defensive positions)
    ('sacks', None),
    ('interceptions', None),
    ('tackles_total', None),
    ('forced_fumbles', None),
]

# AFC team IDs (1-16)
AFC_TEAM_IDS: Set[int] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}

# NFC team IDs (17-32)
NFC_TEAM_IDS: Set[int] = {17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32}


# ============================================
# Awards Service
# ============================================

class AwardsService:
    """
    Main orchestrator for all award calculations.

    Follows the service layer pattern with lazy-loaded dependencies.
    Never makes direct database calls - uses dedicated APIs.

    Usage:
        service = AwardsService(db_path, dynasty_id, season)
        results = service.calculate_all_awards()
        all_pro = service.select_all_pro_teams()
        stat_leaders = service.record_statistical_leaders()
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the Awards Service.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Season year to calculate awards for
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Lazy-loaded dependencies (None until first access)
        self._db = None
        self._eligibility_checker = None
        self._voting_engine = None
        self._awards_api = None
        self._stats_api = None

        # Cached candidates list (populated once, reused for all position queries)
        self._cached_all_candidates: Optional[List[PlayerCandidate]] = None

        self._logger = logging.getLogger(__name__)

    # ============================================
    # Lazy-Loaded Properties
    # ============================================

    def _get_db(self):
        """Lazy-load GameCycleDatabase."""
        if self._db is None:
            from ..database.connection import GameCycleDatabase
            self._db = GameCycleDatabase(self._db_path)
        return self._db

    @property
    def eligibility_checker(self):
        """Lazy-load EligibilityChecker."""
        if self._eligibility_checker is None:
            from .awards.eligibility import EligibilityChecker
            self._eligibility_checker = EligibilityChecker(
                self._db_path, self._dynasty_id, self._season
            )
        return self._eligibility_checker

    @property
    def voting_engine(self):
        """Lazy-load VotingEngine (new instance each time for fresh randomness)."""
        if self._voting_engine is None:
            from .awards.voting_engine import VotingEngine
            self._voting_engine = VotingEngine(num_voters=50)
        return self._voting_engine

    @property
    def awards_api(self):
        """Lazy-load AwardsAPI."""
        if self._awards_api is None:
            from ..database.awards_api import AwardsAPI
            self._awards_api = AwardsAPI(self._get_db())
        return self._awards_api

    @property
    def stats_api(self):
        """Lazy-load StatsAPI."""
        if self._stats_api is None:
            from src.statistics.stats_api import StatsAPI
            self._stats_api = StatsAPI(self._db_path, self._dynasty_id)
        return self._stats_api

    # ============================================
    # Major Award Calculations
    # ============================================

    def calculate_mvp(self) -> AwardResult:
        """
        Calculate MVP with voting simulation.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.MVP, 'mvp')

    def calculate_opoy(self) -> AwardResult:
        """
        Calculate Offensive Player of the Year.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.OPOY, 'opoy')

    def calculate_dpoy(self) -> AwardResult:
        """
        Calculate Defensive Player of the Year.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.DPOY, 'dpoy')

    def calculate_oroy(self) -> AwardResult:
        """
        Calculate Offensive Rookie of the Year.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.OROY, 'oroy')

    def calculate_droy(self) -> AwardResult:
        """
        Calculate Defensive Rookie of the Year.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.DROY, 'droy')

    def calculate_cpoy(self) -> AwardResult:
        """
        Calculate Comeback Player of the Year.

        Returns:
            AwardResult with winner and finalists
        """
        return self._calculate_award(AwardType.CPOY, 'cpoy')

    def calculate_all_awards(self) -> Dict[str, AwardResult]:
        """
        Calculate all 6 major awards.

        Returns:
            Dict mapping award_id to AwardResult
        """
        self._logger.info(f"Calculating all awards for {self._season}...")

        results = {
            'mvp': self.calculate_mvp(),
            'opoy': self.calculate_opoy(),
            'dpoy': self.calculate_dpoy(),
            'oroy': self.calculate_oroy(),
            'droy': self.calculate_droy(),
            'cpoy': self.calculate_cpoy(),
        }

        # Log summary
        winners = [
            f"{award_id.upper()}: {r.winner.player_name}"
            for award_id, r in results.items()
            if r.winner
        ]
        self._logger.info(f"Awards calculated: {', '.join(winners)}")

        return results

    # ============================================
    # Super Bowl MVP
    # ============================================

    def calculate_super_bowl_mvp(
        self,
        game_id: str,
        winning_team_id: int
    ) -> Optional[SuperBowlMVPResult]:
        """
        Calculate Super Bowl MVP based on game performance.

        Evaluates all players from both teams based on their game stats,
        with weighted scoring for different stat categories.

        Args:
            game_id: The Super Bowl game ID
            winning_team_id: Team ID of the winning team

        Returns:
            SuperBowlMVPResult with MVP player and stats, or None if no data
        """
        self._logger.info(f"Calculating Super Bowl MVP for game {game_id}...")

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row

            # Get all player stats from the Super Bowl game
            query = """
                SELECT
                    player_id,
                    player_name,
                    team_id,
                    position,
                    passing_yards,
                    passing_tds,
                    passing_interceptions,
                    passing_completions,
                    passing_attempts,
                    rushing_yards,
                    rushing_tds,
                    receiving_yards,
                    receiving_tds,
                    receptions,
                    sacks,
                    interceptions,
                    tackles_total,
                    forced_fumbles,
                    fumbles_recovered
                FROM player_game_stats
                WHERE dynasty_id = ? AND game_id = ?
            """
            cursor = conn.execute(query, (self._dynasty_id, game_id))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self._logger.warning(f"No player stats found for game {game_id}")
                return None

            # Calculate MVP score for each player
            candidates = []
            for row in rows:
                # Calculate weighted MVP score
                # Weights prioritize impact plays (TDs) over volume stats
                score = 0.0

                # Passing contribution
                passing_yards = row['passing_yards'] or 0
                passing_tds = row['passing_tds'] or 0
                passing_ints = row['passing_interceptions'] or 0
                score += passing_yards * 0.04  # 4 points per 100 yards
                score += passing_tds * 6.0     # 6 points per TD
                score -= passing_ints * 4.0    # -4 points per INT

                # Rushing contribution
                rushing_yards = row['rushing_yards'] or 0
                rushing_tds = row['rushing_tds'] or 0
                score += rushing_yards * 0.1   # 10 points per 100 yards
                score += rushing_tds * 6.0     # 6 points per TD

                # Receiving contribution
                receiving_yards = row['receiving_yards'] or 0
                receiving_tds = row['receiving_tds'] or 0
                receptions = row['receptions'] or 0
                score += receiving_yards * 0.1  # 10 points per 100 yards
                score += receiving_tds * 6.0    # 6 points per TD
                score += receptions * 0.5       # 0.5 points per reception

                # Defensive contribution
                sacks = row['sacks'] or 0
                interceptions = row['interceptions'] or 0
                forced_fumbles = row['forced_fumbles'] or 0
                fumbles_recovered = row['fumbles_recovered'] or 0
                tackles = row['tackles_total'] or 0
                score += sacks * 3.0           # 3 points per sack
                score += interceptions * 6.0   # 6 points per INT
                score += forced_fumbles * 3.0  # 3 points per FF
                score += fumbles_recovered * 3.0
                score += tackles * 0.2         # 0.2 points per tackle

                # Winning team bonus (slight preference to winning team players)
                is_winning_team = row['team_id'] == winning_team_id
                if is_winning_team:
                    score *= 1.1  # 10% bonus for winning team

                candidates.append({
                    'player_id': int(row['player_id']) if row['player_id'] else 0,
                    'player_name': row['player_name'] or 'Unknown',
                    'team_id': row['team_id'],
                    'position': row['position'] or '',
                    'score': score,
                    'is_winning_team': is_winning_team,
                    'stats': {
                        'passing_yards': passing_yards,
                        'passing_tds': passing_tds,
                        'passing_interceptions': passing_ints,
                        'passing_completions': row['passing_completions'] or 0,
                        'passing_attempts': row['passing_attempts'] or 0,
                        'rushing_yards': rushing_yards,
                        'rushing_tds': rushing_tds,
                        'receiving_yards': receiving_yards,
                        'receiving_tds': receiving_tds,
                        'receptions': receptions,
                        'sacks': sacks,
                        'interceptions': interceptions,
                        'tackles_total': tackles,
                        'forced_fumbles': forced_fumbles,
                        'fumbles_recovered': fumbles_recovered,
                    }
                })

            # Sort by score descending
            candidates.sort(key=lambda x: x['score'], reverse=True)

            if not candidates:
                return None

            # MVP is the highest scorer
            mvp = candidates[0]
            self._logger.info(
                f"Super Bowl MVP: {mvp['player_name']} ({mvp['position']}) - "
                f"Score: {mvp['score']:.1f}"
            )

            # Normalize position name
            position = mvp['position'].lower() if mvp['position'] else ''
            position_abbrev = POSITION_TO_ABBREVIATION.get(position, position.upper())

            return SuperBowlMVPResult(
                season=self._season,
                game_id=game_id,
                player_id=mvp['player_id'],
                player_name=mvp['player_name'],
                team_id=mvp['team_id'],
                position=position_abbrev,
                winning_team=mvp['is_winning_team'],
                stat_line=mvp['stats'],
                mvp_score=mvp['score'],
            )

        except Exception as e:
            self._logger.error(f"Failed to calculate Super Bowl MVP: {e}", exc_info=True)
            return None

    def get_super_bowl_mvp(self) -> Optional[SuperBowlMVPResult]:
        """
        READ already-calculated Super Bowl MVP from database (fast, no recalculation).

        Use this for UI display when MVP has already been calculated.

        Returns:
            SuperBowlMVPResult loaded from database, or None if not found
        """
        try:
            mvp_data = self.awards_api.get_super_bowl_mvp(
                self._dynasty_id, self._season
            )
            if not mvp_data:
                return None

            return SuperBowlMVPResult(
                season=self._season,
                game_id=mvp_data.get('game_id', ''),
                player_id=mvp_data.get('player_id', 0),
                player_name=mvp_data.get('player_name', 'Unknown'),
                team_id=mvp_data.get('team_id', 0),
                position=mvp_data.get('position', ''),
                winning_team=mvp_data.get('winning_team', True),
                stat_line=mvp_data.get('stat_line', {}),
                mvp_score=mvp_data.get('mvp_score', 0.0),
            )
        except Exception as e:
            self._logger.warning(f"Failed to load Super Bowl MVP from database: {e}")
            return None

    def get_calculated_awards(self) -> Dict[str, AwardResult]:
        """
        READ already-calculated awards from database (fast, no recalculation).

        Use this for UI display when awards have already been calculated.
        Returns empty AwardResults for awards that don't exist.

        Returns:
            Dict mapping award_id to AwardResult (loaded from database)
        """
        self._logger.debug(f"Loading calculated awards for {self._season}...")

        results = {}
        for award_id in ['mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy']:
            results[award_id] = self._load_award_from_db(award_id)

        return results

    def _load_award_from_db(self, award_id: str) -> AwardResult:
        """Load a single award from database (no calculation)."""
        try:
            # Get winners/finalists from database
            winners = self.awards_api.get_award_winners(
                self._dynasty_id, self._season, award_id
            )

            if not winners:
                return AwardResult(
                    award_id=award_id,
                    season=self._season,
                    winner=None,
                    finalists=[],
                    all_votes=[],
                    candidates_evaluated=0
                )

            # Convert database records to VotingResult format
            from .awards.voting_engine import VotingResult
            voting_results = []
            for w in winners:
                # Get player name and position from database
                player_name = self._get_player_name(w.player_id)
                position = self._get_player_position(w.player_id)
                voting_results.append(VotingResult(
                    player_id=w.player_id,
                    player_name=player_name,
                    team_id=w.team_id,
                    position=position,
                    total_points=int(w.vote_points),
                    vote_share=w.vote_share,
                ))

            winner = voting_results[0] if voting_results else None
            finalists = voting_results[1:5] if len(voting_results) > 1 else []

            return AwardResult(
                award_id=award_id,
                season=self._season,
                winner=winner,
                finalists=finalists,
                all_votes=voting_results,
                candidates_evaluated=len(voting_results)
            )

        except Exception as e:
            self._logger.warning(f"Failed to load {award_id} from database: {e}")
            return AwardResult(
                award_id=award_id,
                season=self._season,
                winner=None,
                finalists=[],
                all_votes=[],
                candidates_evaluated=0
            )

    def _get_player_name(self, player_id: int) -> str:
        """Get player name from database."""
        try:
            row = self._get_db().query_one(
                """SELECT first_name, last_name FROM players
                   WHERE dynasty_id = ? AND player_id = ?""",
                (self._dynasty_id, player_id)
            )
            if row:
                return f"{row[0]} {row[1]}"
            return f"Player {player_id}"
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to get player name for {player_id}: {e}")
            return f"Player {player_id}"

    def _get_player_position(self, player_id: int) -> str:
        """Get player primary position from database."""
        import json
        try:
            row = self._get_db().query_one(
                """SELECT positions FROM players
                   WHERE dynasty_id = ? AND player_id = ?""",
                (self._dynasty_id, player_id)
            )
            if row and row[0]:
                # positions is a JSON array like ["quarterback", "punter"]
                positions = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if positions and len(positions) > 0:
                    # Convert full position name to abbreviation
                    pos_name = positions[0].lower()
                    return POSITION_TO_ABBREVIATION.get(pos_name, pos_name.upper())
            return ''
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to get player position for {player_id}: {e}")
            return ''

    def _get_player_grade(self, player_id: int) -> float:
        """Get player's season grade from player_season_grades table."""
        try:
            row = self._get_db().query_one(
                """SELECT overall_grade FROM player_season_grades
                   WHERE dynasty_id = ? AND season = ? AND player_id = ?""",
                (self._dynasty_id, self._season, player_id)
            )
            return row[0] if row else 0.0
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to get player grade for {player_id}: {e}", exc_info=True)
            return 0.0

    def _calculate_award(self, award_type: AwardType, award_id: str) -> AwardResult:
        """
        Calculate a single award with voting simulation.

        Uses tracked nominees when available (for performance optimization).
        Falls back to full candidate search if no tracking data exists.

        Args:
            award_type: The AwardType enum value
            award_id: String identifier for database storage

        Returns:
            AwardResult with winner, finalists, and all votes
        """
        self._logger.info(f"Calculating {award_id.upper()} for {self._season}...")

        try:
            # 1. Try to get pre-tracked nominees (performance optimization)
            # CPOY is not tracked weekly (requires previous season comparison)
            candidates = None
            if award_type != AwardType.CPOY:
                candidates = self._get_tracked_candidates(award_type, award_id)
                if candidates:
                    self._logger.info(f"Using {len(candidates)} tracked nominees for {award_id.upper()}")

            # 2. Fall back to full candidate search if no tracking data
            if not candidates:
                candidates = self.eligibility_checker.get_eligible_candidates_fast(award_type)

            if not candidates:
                self._logger.warning(f"No {award_id.upper()} candidates for {self._season}")
                return AwardResult(
                    award_id=award_id,
                    season=self._season,
                    winner=None,
                    finalists=[],
                    all_votes=[],
                    candidates_evaluated=0
                )

            self._logger.debug(f"Found {len(candidates)} eligible candidates for {award_id.upper()}")

            # 2. Score each candidate using appropriate criteria
            from .awards.award_criteria import get_criteria_for_award
            criteria = get_criteria_for_award(award_type)
            award_scores = [criteria.calculate_score(c) for c in candidates]

            # 3. Conduct voting simulation
            voting_results = self.voting_engine.conduct_voting(award_id, award_scores)

            # 4. Store results in database
            self._store_award_results(award_id, voting_results, candidates)

            # 5. Return structured result
            winner = voting_results[0] if voting_results else None
            finalists = voting_results[1:5] if len(voting_results) > 1 else []

            if winner:
                self._logger.info(
                    f"{award_id.upper()} Winner: {winner.player_name} "
                    f"({winner.total_points} pts, {winner.vote_share:.1%})"
                )

            return AwardResult(
                award_id=award_id,
                season=self._season,
                winner=winner,
                finalists=finalists,
                all_votes=voting_results,
                candidates_evaluated=len(candidates)
            )

        except Exception as e:
            self._logger.error(f"Failed to calculate {award_id.upper()}: {e}", exc_info=True)
            return AwardResult(
                award_id=award_id,
                season=self._season,
                winner=None,
                finalists=[],
                all_votes=[],
                candidates_evaluated=0
            )

    def _get_tracked_candidates(
        self,
        award_type: AwardType,
        award_id: str
    ) -> Optional[List[PlayerCandidate]]:
        """
        Get pre-tracked nominees for faster award calculation.

        Uses the award_race_tracking table populated during weeks 10-18.
        Returns None if no tracking data exists (falls back to full search).

        Args:
            award_type: The AwardType enum value
            award_id: String identifier for the award

        Returns:
            List of PlayerCandidate if tracking data exists, None otherwise
        """
        try:
            # Check if tracking data exists
            if not self.awards_api.has_tracking_data(self._dynasty_id, self._season):
                self._logger.debug(f"No tracking data for {self._season}, using full search")
                return None

            # Get latest tracked nominees
            tracked = self.awards_api.get_tracked_nominees(
                self._dynasty_id, self._season, award_id
            )

            if not tracked:
                self._logger.debug(f"No tracked nominees for {award_id}, using full search")
                return None

            # Convert tracked entries to PlayerCandidate objects
            # We need to populate the full candidate data for proper scoring
            candidates = []
            for entry in tracked:
                # Use eligibility checker to populate full candidate data
                candidate = self.eligibility_checker.get_candidate_by_id(
                    entry.player_id, award_type
                )
                if candidate:
                    candidates.append(candidate)
                else:
                    self._logger.debug(
                        f"Could not populate candidate data for player {entry.player_id}"
                    )

            if not candidates:
                return None

            self._logger.debug(
                f"Retrieved {len(candidates)} tracked candidates for {award_id}"
            )
            return candidates

        except Exception as e:
            self._logger.warning(f"Failed to get tracked candidates: {e}")
            return None

    def _store_award_results(
        self,
        award_id: str,
        voting_results: List[Any],
        candidates: List[PlayerCandidate]
    ) -> None:
        """
        Store award voting results in database.

        Args:
            award_id: Award identifier
            voting_results: List of VotingResult
            candidates: Original candidate list for stats snapshot
        """
        try:
            # Create candidate lookup by player_id
            candidate_lookup = {c.player_id: c for c in candidates}
            voting_date = date.today().isoformat()

            # Store top 5 as winners
            for rank, result in enumerate(voting_results[:5], start=1):
                self.awards_api.insert_award_winner(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    award_id=award_id,
                    player_id=result.player_id,
                    team_id=result.team_id,
                    vote_points=result.total_points,
                    vote_share=result.vote_share,
                    rank=rank,
                    is_winner=(rank == 1),
                    voting_date=voting_date
                )

            # Store all as nominees with stats snapshot
            for rank, result in enumerate(voting_results, start=1):
                candidate = candidate_lookup.get(result.player_id)
                stats_snapshot = candidate.to_dict() if candidate else {}
                grade_snapshot = candidate.overall_grade if candidate else 0.0

                self.awards_api.insert_nominee(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    award_id=award_id,
                    player_id=result.player_id,
                    team_id=result.team_id,
                    nomination_rank=rank,
                    stats_snapshot=stats_snapshot,
                    grade_snapshot=grade_snapshot
                )

            self._logger.debug(f"Stored {len(voting_results)} results for {award_id}")

        except Exception as e:
            self._logger.error(f"Failed to store {award_id} results: {e}", exc_info=True)

    # ============================================
    # All-Pro Selection
    # ============================================

    def get_all_pro_teams(self) -> AllProTeam:
        """
        READ already-selected All-Pro teams from database (fast, no re-selection).

        Use this for UI display when All-Pro teams have already been selected.

        Returns:
            AllProTeam loaded from database
        """
        try:
            # API returns {'FIRST_TEAM': [...], 'SECOND_TEAM': [...]}
            selections_by_team = self.awards_api.get_all_pro_teams(
                self._dynasty_id, self._season
            )

            first_team: Dict[str, List[AllProSelection]] = {}
            second_team: Dict[str, List[AllProSelection]] = {}
            total = 0

            # Process FIRST_TEAM selections
            for sel in selections_by_team.get('FIRST_TEAM', []):
                player_name = self._get_player_name(sel.player_id)
                all_pro_sel = AllProSelection(
                    player_id=sel.player_id,
                    player_name=player_name,
                    team_id=sel.team_id,
                    position=sel.position,
                    team_type='FIRST_TEAM',
                    overall_grade=self._get_player_grade(sel.player_id),
                    position_rank=0,
                )
                if sel.position not in first_team:
                    first_team[sel.position] = []
                first_team[sel.position].append(all_pro_sel)
                total += 1

            # Process SECOND_TEAM selections
            for sel in selections_by_team.get('SECOND_TEAM', []):
                player_name = self._get_player_name(sel.player_id)
                all_pro_sel = AllProSelection(
                    player_id=sel.player_id,
                    player_name=player_name,
                    team_id=sel.team_id,
                    position=sel.position,
                    team_type='SECOND_TEAM',
                    overall_grade=self._get_player_grade(sel.player_id),
                    position_rank=0,
                )
                if sel.position not in second_team:
                    second_team[sel.position] = []
                second_team[sel.position].append(all_pro_sel)
                total += 1

            return AllProTeam(
                season=self._season,
                first_team=first_team,
                second_team=second_team,
                total_selections=total
            )

        except Exception as e:
            self._logger.warning(f"Failed to load All-Pro from database: {e}")
            return AllProTeam(season=self._season, total_selections=0)

    def select_all_pro_teams(self) -> AllProTeam:
        """
        Select All-Pro teams (44 players: 22 First Team + 22 Second Team).

        Selects top players at each position based on grades and performance.

        Returns:
            AllProTeam with first_team and second_team selections
        """
        self._logger.info(f"Selecting All-Pro teams for {self._season}...")

        try:
            first_team: Dict[str, List[AllProSelection]] = {}
            second_team: Dict[str, List[AllProSelection]] = {}
            total_selections = 0
            selection_date = date.today().isoformat()

            for position, slots in ALL_PRO_SLOTS.items():
                # Get candidates for this position (with All-Pro stat minimums)
                position_candidates = self._get_position_candidates(
                    position,
                    apply_all_pro_stat_minimums=True
                )

                if not position_candidates:
                    self._logger.warning(f"No candidates for All-Pro {position}")
                    first_team[position] = []
                    second_team[position] = []
                    continue

                # Score and rank candidates
                from .awards.award_criteria import AllProCriteria
                criteria = AllProCriteria()
                scored = criteria.rank_candidates(position_candidates)

                # Select First Team (top N)
                first_team_picks = scored[:slots]
                first_team[position] = []

                for idx, score in enumerate(first_team_picks):
                    selection = AllProSelection(
                        player_id=score.player_id,
                        player_name=score.player_name,
                        team_id=score.team_id,
                        position=position,
                        team_type='FIRST_TEAM',
                        overall_grade=score.grade_component,
                        position_rank=idx + 1,
                    )
                    first_team[position].append(selection)
                    total_selections += 1

                    # Store in database
                    self.awards_api.insert_all_pro_selection(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        player_id=score.player_id,
                        team_id=score.team_id,
                        position=position,
                        team_type='FIRST_TEAM',
                        vote_points=int(score.final_score * 10),
                        vote_share=score.final_score / 100,
                        selection_date=selection_date
                    )

                # Select Second Team (next N)
                second_team_picks = scored[slots:slots * 2]
                second_team[position] = []

                for idx, score in enumerate(second_team_picks):
                    selection = AllProSelection(
                        player_id=score.player_id,
                        player_name=score.player_name,
                        team_id=score.team_id,
                        position=position,
                        team_type='SECOND_TEAM',
                        overall_grade=score.grade_component,
                        position_rank=slots + idx + 1,
                    )
                    second_team[position].append(selection)
                    total_selections += 1

                    # Store in database
                    self.awards_api.insert_all_pro_selection(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        player_id=score.player_id,
                        team_id=score.team_id,
                        position=position,
                        team_type='SECOND_TEAM',
                        vote_points=int(score.final_score * 10),
                        vote_share=score.final_score / 100,
                        selection_date=selection_date
                    )

            result = AllProTeam(
                season=self._season,
                first_team=first_team,
                second_team=second_team,
                total_selections=total_selections
            )

            self._logger.info(
                f"All-Pro selection complete: {result.first_team_count} first team, "
                f"{result.second_team_count} second team"
            )

            return result

        except Exception as e:
            self._logger.error(f"Failed to select All-Pro teams: {e}", exc_info=True)
            return AllProTeam(season=self._season, total_selections=0)

    def _get_position_candidates(
        self,
        position: str,
        apply_all_pro_stat_minimums: bool = False
    ) -> List[PlayerCandidate]:
        """
        Get eligible candidates for a Pro Bowl/All-Pro position slot.

        Uses position mapping to handle consolidated positions (e.g., OT includes LT and RT).
        Uses cached candidate list to avoid repeated database queries.
        Normalizes position names to handle different formats (e.g., "wide_receiver" -> "WR").

        Args:
            position: Pro Bowl/All-Pro position slot (e.g., "OT", "OG", "OLB", "QB")
            apply_all_pro_stat_minimums: If True, apply position-specific stat minimums
                                         (e.g., RB needs 100 carries). Used for All-Pro only.

        Returns:
            List of PlayerCandidate for that position (duplicates removed)
        """
        # Use cached candidates if available (for Pro Bowl/All-Pro efficiency)
        if self._cached_all_candidates is None:
            # Use FAST method with SQL-level filtering (~0.5s vs ~44s)
            self._cached_all_candidates = self.eligibility_checker.get_eligible_candidates_fast(
                AwardType.MVP,
                per_position_limit=20,  # Plenty for Pro Bowl + alternates
            )
            self._logger.info(f"Cached {len(self._cached_all_candidates)} eligible candidates (fast)")

        # Get actual player positions that map to this Pro Bowl slot
        mapped_positions = PRO_BOWL_POSITION_MAPPING.get(
            position,
            [position]  # Fallback to direct match if not in mapping
        )

        position_candidates = []
        seen_players = set()  # Track player IDs to avoid duplicates

        for c in self._cached_all_candidates:
            # Skip if we've already added this player
            if c.player_id in seen_players:
                continue

            # Normalize candidate's position to abbreviation for comparison
            candidate_pos = c.position.lower() if c.position else ''
            normalized_pos = POSITION_TO_ABBREVIATION.get(candidate_pos, c.position.upper())

            # Check if candidate's position matches any of the mapped positions
            if normalized_pos in mapped_positions:
                position_candidates.append(c)
                seen_players.add(c.player_id)

        # Apply All-Pro stat minimums if requested
        if apply_all_pro_stat_minimums:
            filtered_candidates = []

            for candidate in position_candidates:
                # Check position-specific stat minimums
                is_eligible, reason = self.eligibility_checker.check_all_pro_stat_minimums(
                    player_id=candidate.player_id,
                    position=position
                )

                if not is_eligible:
                    self._logger.debug(
                        f"[All-Pro] {candidate.player_name} ({position}) filtered: {reason}"
                    )
                    continue

                filtered_candidates.append(candidate)

            self._logger.info(
                f"[All-Pro] {position}: {len(filtered_candidates)}/{len(position_candidates)} "
                f"candidates passed stat minimums"
            )

            return filtered_candidates

        return position_candidates

    # ============================================
    # Pro Bowl Selection
    # ============================================

    def get_pro_bowl_rosters(self) -> ProBowlRoster:
        """
        READ already-selected Pro Bowl rosters from database (fast, no re-selection).

        Use this for UI display when Pro Bowl has already been selected.

        Returns:
            ProBowlRoster loaded from database
        """
        try:
            afc_roster: Dict[str, List[ProBowlSelection]] = {}
            nfc_roster: Dict[str, List[ProBowlSelection]] = {}
            total = 0

            # API returns {'AFC': [...], 'NFC': [...]} when no conference filter
            all_selections = self.awards_api.get_pro_bowl_roster(
                self._dynasty_id, self._season
            )

            for conference in ['AFC', 'NFC']:
                selections = all_selections.get(conference, [])
                roster = afc_roster if conference == 'AFC' else nfc_roster

                for sel in selections:
                    player_name = self._get_player_name(sel.player_id)
                    # Look up actual grade from player_season_grades
                    pro_bowl_sel = ProBowlSelection(
                        player_id=sel.player_id,
                        player_name=player_name,
                        team_id=sel.team_id,
                        position=sel.position,
                        conference=conference,
                        selection_type=sel.selection_type or 'RESERVE',
                        overall_grade=self._get_player_grade(sel.player_id),
                        combined_score=sel.combined_score if sel.combined_score else 0,
                    )

                    if sel.position not in roster:
                        roster[sel.position] = []
                    roster[sel.position].append(pro_bowl_sel)
                    total += 1

            return ProBowlRoster(
                season=self._season,
                afc_roster=afc_roster,
                nfc_roster=nfc_roster,
                total_selections=total
            )

        except Exception as e:
            self._logger.warning(f"Failed to load Pro Bowl from database: {e}")
            return ProBowlRoster(season=self._season, total_selections=0)

    def select_pro_bowl_rosters(self) -> ProBowlRoster:
        """
        Select Pro Bowl rosters for AFC and NFC.

        Separates players by conference and selects top performers
        at each position.

        Returns:
            ProBowlRoster with AFC and NFC rosters
        """
        self._logger.info(f"Selecting Pro Bowl rosters for {self._season}...")

        try:
            afc_roster: Dict[str, List[ProBowlSelection]] = {}
            nfc_roster: Dict[str, List[ProBowlSelection]] = {}
            total_selections = 0
            selection_date = date.today().isoformat()

            for position, slots in PRO_BOWL_SLOTS.items():
                # Get all candidates for this position
                all_candidates = self._get_position_candidates(position)

                # Split by conference
                afc_candidates = [c for c in all_candidates if c.team_id in AFC_TEAM_IDS]
                nfc_candidates = [c for c in all_candidates if c.team_id in NFC_TEAM_IDS]

                # Score and select using ProBowlCriteria (stats-heavy, like fan voting)
                from .awards.award_criteria import ProBowlCriteria
                criteria = ProBowlCriteria()

                # AFC selections
                afc_scored = criteria.rank_candidates(afc_candidates) if afc_candidates else []
                afc_roster[position] = []

                for idx, score in enumerate(afc_scored[:slots]):
                    selection_type = 'STARTER' if idx < 2 else 'RESERVE'
                    selection = ProBowlSelection(
                        player_id=score.player_id,
                        player_name=score.player_name,
                        team_id=score.team_id,
                        position=position,
                        conference='AFC',
                        selection_type=selection_type,
                        overall_grade=score.grade_component,
                        combined_score=score.final_score,
                    )
                    afc_roster[position].append(selection)
                    total_selections += 1

                    # Store in database
                    self.awards_api.insert_pro_bowl_selection(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        player_id=score.player_id,
                        team_id=score.team_id,
                        conference='AFC',
                        position=position,
                        selection_type=selection_type,
                        combined_score=score.final_score,
                        selection_date=selection_date
                    )

                # NFC selections
                nfc_scored = criteria.rank_candidates(nfc_candidates) if nfc_candidates else []
                nfc_roster[position] = []

                for idx, score in enumerate(nfc_scored[:slots]):
                    selection_type = 'STARTER' if idx < 2 else 'RESERVE'
                    selection = ProBowlSelection(
                        player_id=score.player_id,
                        player_name=score.player_name,
                        team_id=score.team_id,
                        position=position,
                        conference='NFC',
                        selection_type=selection_type,
                        overall_grade=score.grade_component,
                        combined_score=score.final_score,
                    )
                    nfc_roster[position].append(selection)
                    total_selections += 1

                    # Store in database
                    self.awards_api.insert_pro_bowl_selection(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        player_id=score.player_id,
                        team_id=score.team_id,
                        conference='NFC',
                        position=position,
                        selection_type=selection_type,
                        combined_score=score.final_score,
                        selection_date=selection_date
                    )

            result = ProBowlRoster(
                season=self._season,
                afc_roster=afc_roster,
                nfc_roster=nfc_roster,
                total_selections=total_selections
            )

            self._logger.info(
                f"Pro Bowl selection complete: AFC={result.afc_count}, NFC={result.nfc_count}"
            )

            return result

        except Exception as e:
            self._logger.error(f"Failed to select Pro Bowl rosters: {e}", exc_info=True)
            return ProBowlRoster(season=self._season, total_selections=0)

    # ============================================
    # Statistical Leaders
    # ============================================

    def get_statistical_leaders(self) -> StatisticalLeadersResult:
        """
        READ already-recorded statistical leaders from database (fast, no re-recording).

        Use this for UI display when stat leaders have already been recorded.

        Returns:
            StatisticalLeadersResult loaded from database
        """
        try:
            leaders_by_category: Dict[str, List[StatisticalLeaderEntry]] = {}
            total = 0

            for category, _ in STAT_CATEGORIES:
                leaders = self.awards_api.get_stat_leaders(
                    self._dynasty_id, self._season, category
                )

                category_leaders = []
                for leader in leaders:
                    player_name = self._get_player_name(leader.player_id)
                    entry = StatisticalLeaderEntry(
                        player_id=leader.player_id,
                        player_name=player_name,
                        team_id=leader.team_id,
                        position=leader.position or '',
                        stat_category=category,
                        stat_value=leader.stat_value,
                        league_rank=leader.league_rank,
                    )
                    category_leaders.append(entry)
                    total += 1

                leaders_by_category[category] = category_leaders

            return StatisticalLeadersResult(
                season=self._season,
                leaders_by_category=leaders_by_category,
                total_recorded=total
            )

        except Exception as e:
            self._logger.warning(f"Failed to load stat leaders from database: {e}")
            return StatisticalLeadersResult(season=self._season, total_recorded=0)

    def record_statistical_leaders(self) -> StatisticalLeadersResult:
        """
        Record top 10 in each major statistical category.

        Returns:
            StatisticalLeadersResult with leaders by category
        """
        self._logger.info(f"Recording statistical leaders for {self._season}...")

        try:
            leaders_by_category: Dict[str, List[StatisticalLeaderEntry]] = {}
            total_recorded = 0
            recorded_date = date.today().isoformat()

            for category, position_filter in STAT_CATEGORIES:
                # Get players with this stat
                players = self._get_players_with_stat(category, position_filter)

                if not players:
                    self._logger.debug(f"No players found for {category}")
                    leaders_by_category[category] = []
                    continue

                # Sort by stat value descending
                players.sort(key=lambda p: p.get(category, 0), reverse=True)

                # Record top 10
                category_leaders = []
                for rank, player in enumerate(players[:10], start=1):
                    stat_value = player.get(category, 0)

                    entry = StatisticalLeaderEntry(
                        player_id=player['player_id'],
                        player_name=player.get('player_name', 'Unknown'),
                        team_id=player['team_id'],
                        position=player.get('position', ''),
                        stat_category=category,
                        stat_value=stat_value,
                        league_rank=rank,
                    )
                    category_leaders.append(entry)
                    total_recorded += 1

                    # Store in database
                    self.awards_api.record_stat_leader(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        stat_category=category,
                        player_id=player['player_id'],
                        team_id=player['team_id'],
                        position=player.get('position', ''),
                        stat_value=int(stat_value) if isinstance(stat_value, (int, float)) else 0,
                        league_rank=rank,
                        recorded_date=recorded_date
                    )

                leaders_by_category[category] = category_leaders

            result = StatisticalLeadersResult(
                season=self._season,
                leaders_by_category=leaders_by_category,
                total_recorded=total_recorded
            )

            self._logger.info(
                f"Statistical leaders recorded: {len(result.categories_recorded)} categories, "
                f"{total_recorded} total entries"
            )

            return result

        except Exception as e:
            self._logger.error(f"Failed to record statistical leaders: {e}", exc_info=True)
            return StatisticalLeadersResult(season=self._season, total_recorded=0)

    def _get_players_with_stat(
        self,
        category: str,
        position_filter: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Get all players with values for a statistical category.

        Uses direct SQL query to player_game_stats to get actual stat leaders,
        NOT filtered by grade (which would miss high-stat low-grade players).

        Args:
            category: Stat category name (e.g., 'passing_yards')
            position_filter: Optional position to filter (e.g., 'QB')

        Returns:
            List of player dicts with stat values
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row

            # Map category to SQL column and position filter
            position_clause = ""
            if position_filter == 'QB':
                position_clause = "AND pgs.position = 'QB'"

            # Handle passer_rating specially - it's calculated, not stored
            if category == 'passer_rating':
                query = """
                    SELECT
                        pgs.player_id,
                        pgs.player_name,
                        pgs.team_id,
                        pgs.position,
                        CASE
                            WHEN SUM(pgs.passing_attempts) >= 250 THEN
                                -- NFL passer rating formula approximation (using SQLite MIN/MAX)
                                -- Minimum 250 attempts = 13.9 att/game in 18-game season (NFL standard: 14 att/game)
                                (
                                    (MIN(2.375, MAX(0, (SUM(pgs.passing_completions) * 1.0 / SUM(pgs.passing_attempts) - 0.3) * 5))) +
                                    (MIN(2.375, MAX(0, (SUM(pgs.passing_yards) * 1.0 / SUM(pgs.passing_attempts) - 3) * 0.25))) +
                                    (MIN(2.375, MAX(0, (SUM(pgs.passing_tds) * 1.0 / SUM(pgs.passing_attempts)) * 20))) +
                                    (MIN(2.375, MAX(0, 2.375 - (SUM(pgs.passing_interceptions) * 1.0 / SUM(pgs.passing_attempts)) * 25)))
                                ) * 100 / 6
                            ELSE 0
                        END as stat_value
                    FROM player_game_stats pgs
                    INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                    WHERE pgs.dynasty_id = ?
                        AND g.season = ?
                        AND pgs.season_type = 'regular_season'
                        AND pgs.position = 'QB'
                    GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
                    HAVING SUM(pgs.passing_attempts) >= 250
                    ORDER BY stat_value DESC
                    LIMIT 50
                """
            else:
                query = f"""
                    SELECT
                        pgs.player_id,
                        pgs.player_name,
                        pgs.team_id,
                        pgs.position,
                        SUM(pgs.{category}) as stat_value
                    FROM player_game_stats pgs
                    INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                    WHERE pgs.dynasty_id = ?
                        AND g.season = ?
                        AND pgs.season_type = 'regular_season'
                        {position_clause}
                    GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
                    HAVING SUM(pgs.{category}) > 0
                    ORDER BY stat_value DESC
                    LIMIT 50
                """

            cursor = conn.execute(query, (self._dynasty_id, self._season))
            rows = cursor.fetchall()
            conn.close()

            players = []
            for row in rows:
                players.append({
                    'player_id': row['player_id'],
                    'player_name': row['player_name'],
                    'team_id': row['team_id'],
                    'position': row['position'],
                    category: row['stat_value'],
                })

            return players

        except Exception as e:
            self._logger.error(f"Failed to get players for {category}: {e}")
            return []

    # ============================================
    # Utility Methods
    # ============================================

    def awards_already_calculated(self) -> bool:
        """
        Check if awards have already been calculated for this season.

        Returns:
            True if any award winners exist for this season
        """
        try:
            existing = self.awards_api.get_award_winners(
                dynasty_id=self._dynasty_id,
                season=self._season
            )
            return len(existing) > 0
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to check if awards already calculated: {e}", exc_info=True)
            return False

    def clear_season_awards(self) -> Dict[str, int]:
        """
        Clear all awards for this season (useful for recalculation).

        Returns:
            Dict with counts of cleared records
        """
        try:
            return self.awards_api.clear_season_awards(
                dynasty_id=self._dynasty_id,
                season=self._season
            )
        except Exception as e:
            self._logger.error(f"Failed to clear season awards: {e}")
            return {}

    def __repr__(self) -> str:
        return (
            f"AwardsService(dynasty={self._dynasty_id}, season={self._season})"
        )