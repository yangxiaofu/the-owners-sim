"""
Award Race Coverage Service - Weekly award race narrative generation.

Part of Milestone 12: Media Coverage, Tollgate 5.

Generates headlines and narratives for:
- MVP Watch (weekly updates, movement tracking)
- Rookie Watch (OROY/DROY races)
- Award Predictions (mid-season and late-season projections)

Uses AwardsAPI for award race tracking data and integrates with
HeadlineGenerator for persistence.
"""

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.awards_api import AwardsAPI, AwardRaceEntry
from src.game_cycle.database.media_coverage_api import MediaCoverageAPI


# Type alias for headline data dictionaries
HeadlineData = Dict[str, Any]


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class AwardCoverageType(str, Enum):
    """Types of award race coverage."""
    MVP_WATCH = "MVP_WATCH"
    OROY_WATCH = "OROY_WATCH"
    DROY_WATCH = "DROY_WATCH"
    ROOKIE_WATCH = "ROOKIE_WATCH"  # Combined OROY/DROY
    AWARD_PREDICTION = "AWARD_PREDICTION"
    RACE_UPDATE = "RACE_UPDATE"


class MovementType(str, Enum):
    """Types of movement in award standings."""
    RISING = "RISING"      # Moved up 2+ spots
    FALLING = "FALLING"    # Dropped 2+ spots
    STABLE = "STABLE"      # Same or ±1 spot
    NEW_ENTRY = "NEW_ENTRY"  # First time in top 5
    DROPPED_OUT = "DROPPED_OUT"  # Left top 5


# Award type constants (match AwardsAPI)
AWARD_MVP = "mvp"
AWARD_OPOY = "opoy"
AWARD_DPOY = "dpoy"
AWARD_OROY = "oroy"
AWARD_DROY = "droy"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MovementInfo:
    """Information about a player's movement in award standings."""
    player_id: int
    player_name: str
    team_id: int
    position: str
    current_rank: int
    previous_rank: Optional[int]
    current_score: float
    movement_type: MovementType
    spots_moved: int
    week_score: Optional[float] = None

    @property
    def moved_up(self) -> bool:
        """Check if player moved up."""
        return self.movement_type == MovementType.RISING

    @property
    def moved_down(self) -> bool:
        """Check if player moved down."""
        return self.movement_type == MovementType.FALLING


@dataclass
class RaceContext:
    """Context about an award race for narrative generation."""
    award_type: str
    leader: Optional[MovementInfo]
    top_5: List[MovementInfo]
    gap_to_second: float  # Points gap between 1st and 2nd
    is_tight_race: bool   # Gap < 5 points
    is_runaway: bool      # Gap > 20 points
    week: int
    season: int


# =============================================================================
# MVP WATCH TEMPLATES (20+)
# =============================================================================

MVP_LEADER_TEMPLATES = [
    "{player} Continues to Lead MVP Race After Week {week}",
    "{player} Remains Frontrunner in MVP Discussion",
    "{player} Holds Commanding Lead in MVP Race",
    "{player} Still the Man to Beat for MVP",
    "{player}'s MVP Case Grows Stronger Each Week",
    "{player} Unchallenged at Top of MVP Standings",
]

MVP_RISING_TEMPLATES = [
    "{player}'s MVP Case Strengthens After Week {week} Performance",
    "{player} Surging in MVP Race, Now Ranked #{rank}",
    "Watch Out: {player} Making MVP Push",
    "{player} Climbs {spots} Spots in MVP Standings",
    "{player}'s Hot Streak Boosting MVP Candidacy",
    "Rising Star: {player} Enters MVP Conversation",
]

MVP_FALLING_TEMPLATES = [
    "{player} Stumbles, Drops {spots} Spots in MVP Race",
    "{player}'s MVP Hopes Take Hit After Week {week}",
    "Slip Up: {player} Loses Ground in MVP Standings",
    "{player} Falls to #{rank} in MVP Discussion",
    "{player}'s Struggles Open Door for Rivals",
]

MVP_TIGHT_RACE_TEMPLATES = [
    "MVP Race Tightens: {gap} Points Separate Top {n}",
    "Too Close to Call: MVP Race Remains Wide Open",
    "Dead Heat: {player1} and {player2} Neck-and-Neck for MVP",
    "MVP Race Down to the Wire Between {player1} and {player2}",
    "Razor-Thin Margin: MVP Race Has No Clear Leader",
]

MVP_RUNAWAY_TEMPLATES = [
    "{player} Running Away with MVP Award",
    "Is It Over? {player} Holds Massive Lead in MVP Race",
    "{player} Extends Commanding MVP Lead",
    "No Contest: {player} Dominates MVP Standings",
    "{player}'s MVP Lock Growing Stronger by the Week",
]

MVP_NEWCOMER_TEMPLATES = [
    "{player} Crashes MVP Party, Enters Top 5",
    "New Contender: {player} Makes MVP Case",
    "{player} Bursts Into MVP Conversation",
    "Surprise Entry: {player} Now in MVP Mix",
]


# =============================================================================
# ROOKIE WATCH TEMPLATES (15+)
# =============================================================================

OROY_LEADER_TEMPLATES = [
    "{player} Leads Offensive Rookie of the Year Race",
    "{player} Continues Dominant Rookie Campaign",
    "{player}'s Historic Rookie Season Rolling On",
    "OROY Frontrunner {player} Shows Why He Was Drafted",
]

OROY_RISING_TEMPLATES = [
    "{player} Making Strong Push for OROY Honors",
    "Watch This Rookie: {player} Climbing OROY Standings",
    "{player}'s Breakout Has Him in OROY Conversation",
]

DROY_LEADER_TEMPLATES = [
    "{player} Anchoring Defensive Rookie of the Year Race",
    "Defensive Rookie Watch: {player} Leads the Pack",
    "{player} Setting Standard for First-Year Defenders",
    "DROY Frontrunner {player} Making Immediate Impact",
]

DROY_RISING_TEMPLATES = [
    "{player} Emerging as DROY Candidate",
    "Rising Defender: {player} Entering DROY Conversation",
    "{player}'s Play Has Him in DROY Discussion",
]

ROOKIE_COMBINED_TEMPLATES = [
    "Rookie Watch: {oroy_leader} and {droy_leader} Lead Respective Races",
    "Best of the First-Years: {oroy_leader} (O) and {droy_leader} (D) Set Pace",
    "Rookie Class Shining: {oroy_leader}, {droy_leader} Lead Award Races",
]


# =============================================================================
# AWARD PREDICTION TEMPLATES (10+)
# =============================================================================

MID_SEASON_PREDICTION_TEMPLATES = [
    "Mid-Season MVP Projection: {player} at {confidence}% Confidence",
    "Halfway Point: {player} Leads MVP Race with {confidence}% Projection",
    "Week {week} MVP Check: {player} Currently Favored",
    "Mid-Season Awards Outlook: {player} Tops MVP Standings",
]

LATE_SEASON_PREDICTION_TEMPLATES = [
    "Award Race Update: {player} Heavy Favorite for MVP",
    "{player} All But Locks Up MVP with {confidence}% Projection",
    "Final Stretch: {player} Poised to Win MVP",
    "Late-Season MVP Outlook: {player} in Command",
]

PREDICTION_UNCERTAINTY_TEMPLATES = [
    "MVP Still Up for Grabs: No Clear Favorite Emerges",
    "Award Races Remain Unpredictable at Week {week}",
    "Too Early to Call: Multiple MVP Candidates Still in Mix",
]


# =============================================================================
# AWARD RACE COVERAGE SERVICE
# =============================================================================

class AwardRaceCoverageService:
    """
    Service for generating award race coverage headlines and narratives.

    Integrates with AwardsAPI to track weekly standings and movement,
    then generates appropriate headlines based on the race context.
    """

    # Week thresholds for coverage timing
    TRACKING_START_WEEK = 6    # Award tracking begins
    MID_SEASON_WEEK = 9        # Mid-season predictions
    LATE_SEASON_WEEK = 15      # Late-season predictions
    FINAL_WEEK = 18            # Final regular season week

    # Movement thresholds
    RISING_THRESHOLD = 2       # Spots to count as "rising"
    FALLING_THRESHOLD = 2      # Spots to count as "falling"
    TOP_N_TRACKED = 5          # Top N candidates to track

    # Race characterization thresholds
    TIGHT_RACE_GAP = 5.0       # Points gap for "tight race"
    RUNAWAY_GAP = 20.0         # Points gap for "runaway"

    def __init__(
        self,
        db: GameCycleDatabase,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the award race coverage service.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db = db
        self._dynasty_id = dynasty_id
        self._season = season
        self._awards_api = AwardsAPI(db)
        self._media_api = MediaCoverageAPI(db)
        self._logger = logging.getLogger(__name__)

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def generate_weekly_mvp_coverage(self, week: int) -> List[HeadlineData]:
        """
        Generate MVP coverage headlines for a specific week.

        Args:
            week: Week number (1-18)

        Returns:
            List of headline data dictionaries for MVP coverage
        """
        if week < self.TRACKING_START_WEEK:
            return []

        headlines: List[HeadlineData] = []

        # Get current and previous week standings
        current = self._get_standings(AWARD_MVP, week)
        previous = self._get_standings(AWARD_MVP, week - 1) if week > self.TRACKING_START_WEEK else []

        if not current:
            self._logger.warning(f"No MVP standings for week {week}")
            return []

        # Analyze movement and race context
        movements = self._detect_movement(current, previous)
        context = self._build_race_context(AWARD_MVP, current, movements, week)

        # Generate headlines based on context
        headlines.extend(self._generate_mvp_headlines(context, movements))

        # Persist headlines
        for headline in headlines:
            self._media_api.save_headline(
                self._dynasty_id, self._season, week, headline
            )

        return headlines

    def generate_weekly_rookie_coverage(self, week: int) -> List[HeadlineData]:
        """
        Generate rookie award coverage headlines for a specific week.

        Args:
            week: Week number (1-18)

        Returns:
            List of headline data dictionaries for rookie coverage
        """
        if week < self.TRACKING_START_WEEK:
            return []

        headlines: List[HeadlineData] = []

        # Get OROY standings
        oroy_current = self._get_standings(AWARD_OROY, week)
        oroy_previous = self._get_standings(AWARD_OROY, week - 1) if week > self.TRACKING_START_WEEK else []

        # Get DROY standings
        droy_current = self._get_standings(AWARD_DROY, week)
        droy_previous = self._get_standings(AWARD_DROY, week - 1) if week > self.TRACKING_START_WEEK else []

        # Generate OROY headlines
        if oroy_current:
            oroy_movements = self._detect_movement(oroy_current, oroy_previous)
            oroy_context = self._build_race_context(AWARD_OROY, oroy_current, oroy_movements, week)
            headlines.extend(self._generate_rookie_headlines(oroy_context, oroy_movements, is_offensive=True))

        # Generate DROY headlines
        if droy_current:
            droy_movements = self._detect_movement(droy_current, droy_previous)
            droy_context = self._build_race_context(AWARD_DROY, droy_current, droy_movements, week)
            headlines.extend(self._generate_rookie_headlines(droy_context, droy_movements, is_offensive=False))

        # Generate combined rookie headline (every other week)
        if week % 2 == 0 and oroy_current and droy_current:
            combined = self._generate_combined_rookie_headline(
                oroy_current[0] if oroy_current else None,
                droy_current[0] if droy_current else None,
                week
            )
            if combined:
                headlines.append(combined)

        # Persist headlines
        for headline in headlines:
            self._media_api.save_headline(
                self._dynasty_id, self._season, week, headline
            )

        return headlines

    def generate_award_predictions(self, week: int) -> List[HeadlineData]:
        """
        Generate award prediction headlines for a specific week.

        Args:
            week: Week number (1-18)

        Returns:
            List of headline data dictionaries for award predictions
        """
        headlines: List[HeadlineData] = []

        # Only generate predictions at key weeks
        if week not in [self.MID_SEASON_WEEK, self.LATE_SEASON_WEEK, self.FINAL_WEEK - 1]:
            return []

        is_late_season = week >= self.LATE_SEASON_WEEK

        # Get MVP standings
        mvp_standings = self._get_standings(AWARD_MVP, week)
        if mvp_standings:
            mvp_headline = self._generate_prediction_headline(
                mvp_standings, AWARD_MVP, week, is_late_season
            )
            if mvp_headline:
                headlines.append(mvp_headline)

        # Get OPOY standings
        opoy_standings = self._get_standings(AWARD_OPOY, week)
        if opoy_standings:
            opoy_headline = self._generate_prediction_headline(
                opoy_standings, AWARD_OPOY, week, is_late_season
            )
            if opoy_headline:
                headlines.append(opoy_headline)

        # Get DPOY standings
        dpoy_standings = self._get_standings(AWARD_DPOY, week)
        if dpoy_standings:
            dpoy_headline = self._generate_prediction_headline(
                dpoy_standings, AWARD_DPOY, week, is_late_season
            )
            if dpoy_headline:
                headlines.append(dpoy_headline)

        # Persist headlines
        for headline in headlines:
            self._media_api.save_headline(
                self._dynasty_id, self._season, week, headline
            )

        return headlines

    def generate_all_coverage(self, week: int) -> List[HeadlineData]:
        """
        Generate all award race coverage for a specific week.

        Combines MVP, rookie, and prediction coverage.

        Args:
            week: Week number (1-18)

        Returns:
            List of all headline data dictionaries generated
        """
        all_headlines: List[HeadlineData] = []

        # MVP coverage
        all_headlines.extend(self.generate_weekly_mvp_coverage(week))

        # Rookie coverage
        all_headlines.extend(self.generate_weekly_rookie_coverage(week))

        # Award predictions
        all_headlines.extend(self.generate_award_predictions(week))

        self._logger.info(f"Generated {len(all_headlines)} award race headlines for week {week}")
        return all_headlines

    # =========================================================================
    # DATA RETRIEVAL
    # =========================================================================

    def _get_standings(
        self,
        award_type: str,
        week: int
    ) -> List[AwardRaceEntry]:
        """
        Get award race standings for a specific award and week.

        Args:
            award_type: Award type (mvp, oroy, droy, etc.)
            week: Week number

        Returns:
            List of AwardRaceEntry objects sorted by rank
        """
        return self._awards_api.get_award_race_standings(
            self._dynasty_id,
            self._season,
            week,
            award_type
        )

    # =========================================================================
    # MOVEMENT DETECTION
    # =========================================================================

    def _detect_movement(
        self,
        current: List[AwardRaceEntry],
        previous: List[AwardRaceEntry]
    ) -> List[MovementInfo]:
        """
        Detect movement between current and previous week standings.

        Args:
            current: Current week standings
            previous: Previous week standings

        Returns:
            List of MovementInfo for top candidates
        """
        # Build lookup for previous week
        prev_ranks: Dict[int, int] = {
            entry.player_id: entry.rank for entry in previous
        }
        prev_players = set(prev_ranks.keys())

        movements = []
        for entry in current[:self.TOP_N_TRACKED]:
            prev_rank = prev_ranks.get(entry.player_id)

            # Determine movement type
            if prev_rank is None:
                movement_type = MovementType.NEW_ENTRY
                spots_moved = 0
            elif entry.rank < prev_rank - 1:
                movement_type = MovementType.RISING
                spots_moved = prev_rank - entry.rank
            elif entry.rank > prev_rank + 1:
                movement_type = MovementType.FALLING
                spots_moved = entry.rank - prev_rank
            else:
                movement_type = MovementType.STABLE
                spots_moved = abs(entry.rank - prev_rank) if prev_rank else 0

            player_name = f"{entry.first_name or 'Unknown'} {entry.last_name or 'Player'}"

            movements.append(MovementInfo(
                player_id=entry.player_id,
                player_name=player_name,
                team_id=entry.team_id,
                position=entry.position,
                current_rank=entry.rank,
                previous_rank=prev_rank,
                current_score=entry.cumulative_score,
                movement_type=movement_type,
                spots_moved=spots_moved,
                week_score=entry.week_score,
            ))

        return movements

    def _build_race_context(
        self,
        award_type: str,
        standings: List[AwardRaceEntry],
        movements: List[MovementInfo],
        week: int
    ) -> RaceContext:
        """
        Build context about an award race for narrative generation.

        Args:
            award_type: Award type
            standings: Current standings
            movements: Movement information
            week: Current week

        Returns:
            RaceContext object
        """
        leader = movements[0] if movements else None

        # Calculate gap to second
        gap_to_second = 0.0
        if len(standings) >= 2:
            gap_to_second = standings[0].cumulative_score - standings[1].cumulative_score

        return RaceContext(
            award_type=award_type,
            leader=leader,
            top_5=movements[:5],
            gap_to_second=gap_to_second,
            is_tight_race=gap_to_second < self.TIGHT_RACE_GAP,
            is_runaway=gap_to_second > self.RUNAWAY_GAP,
            week=week,
            season=self._season,
        )

    # =========================================================================
    # HEADLINE GENERATION - MVP
    # =========================================================================

    def _generate_mvp_headlines(
        self,
        context: RaceContext,
        movements: List[MovementInfo]
    ) -> List[HeadlineData]:
        """
        Generate MVP coverage headlines based on race context.

        Args:
            context: Race context information
            movements: Movement information for candidates

        Returns:
            List of headline data dictionaries
        """
        headlines: List[HeadlineData] = []

        # 1. Leader headline (always)
        if context.leader:
            leader_headline = self._generate_mvp_leader_headline(context)
            if leader_headline:
                headlines.append(leader_headline)

        # 2. Race characterization (tight or runaway)
        if context.is_runaway:
            runaway_headline = self._generate_mvp_runaway_headline(context)
            if runaway_headline:
                headlines.append(runaway_headline)
        elif context.is_tight_race and len(movements) >= 2:
            tight_headline = self._generate_mvp_tight_race_headline(context, movements)
            if tight_headline:
                headlines.append(tight_headline)

        # 3. Movement headlines (rising/falling candidates)
        for movement in movements[1:]:  # Skip leader
            if movement.movement_type == MovementType.RISING:
                rising_headline = self._generate_mvp_rising_headline(movement, context.week)
                if rising_headline:
                    headlines.append(rising_headline)
                    break  # Only one rising headline
            elif movement.movement_type == MovementType.FALLING:
                falling_headline = self._generate_mvp_falling_headline(movement, context.week)
                if falling_headline:
                    headlines.append(falling_headline)
                    break  # Only one falling headline

        # 4. New entry headline
        new_entries = [m for m in movements if m.movement_type == MovementType.NEW_ENTRY]
        if new_entries:
            entry_headline = self._generate_mvp_newcomer_headline(new_entries[0], context.week)
            if entry_headline:
                headlines.append(entry_headline)

        return headlines

    def _generate_mvp_leader_headline(self, context: RaceContext) -> Optional[HeadlineData]:
        """Generate headline for MVP leader."""
        if not context.leader:
            return None

        template = random.choice(MVP_LEADER_TEMPLATES)
        headline_text = template.format(
            player=context.leader.player_name,
            week=context.week
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "POSITIVE",
            "priority": 70,
            "team_ids": [context.leader.team_id],
            "player_ids": [context.leader.player_id],
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    def _generate_mvp_runaway_headline(self, context: RaceContext) -> Optional[HeadlineData]:
        """Generate headline for runaway MVP race."""
        if not context.leader:
            return None

        template = random.choice(MVP_RUNAWAY_TEMPLATES)
        headline_text = template.format(
            player=context.leader.player_name,
            gap=round(context.gap_to_second, 1)
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "HYPE",
            "priority": 75,
            "team_ids": [context.leader.team_id],
            "player_ids": [context.leader.player_id],
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    def _generate_mvp_tight_race_headline(
        self,
        context: RaceContext,
        movements: List[MovementInfo]
    ) -> Optional[HeadlineData]:
        """Generate headline for tight MVP race."""
        if len(movements) < 2:
            return None

        template = random.choice(MVP_TIGHT_RACE_TEMPLATES)
        headline_text = template.format(
            player1=movements[0].player_name,
            player2=movements[1].player_name,
            gap=round(context.gap_to_second, 1),
            n=min(3, len([m for m in movements if m.current_score >= movements[0].current_score - self.TIGHT_RACE_GAP]))
        )

        player_ids = [movements[0].player_id, movements[1].player_id]
        team_ids = [movements[0].team_id, movements[1].team_id]

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "HYPE",
            "priority": 72,
            "team_ids": team_ids,
            "player_ids": player_ids,
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    def _generate_mvp_rising_headline(
        self,
        movement: MovementInfo,
        week: int
    ) -> Optional[HeadlineData]:
        """Generate headline for rising MVP candidate."""
        template = random.choice(MVP_RISING_TEMPLATES)
        headline_text = template.format(
            player=movement.player_name,
            week=week,
            rank=movement.current_rank,
            spots=movement.spots_moved
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "POSITIVE",
            "priority": 65,
            "team_ids": [movement.team_id],
            "player_ids": [movement.player_id],
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    def _generate_mvp_falling_headline(
        self,
        movement: MovementInfo,
        week: int
    ) -> Optional[HeadlineData]:
        """Generate headline for falling MVP candidate."""
        template = random.choice(MVP_FALLING_TEMPLATES)
        headline_text = template.format(
            player=movement.player_name,
            week=week,
            rank=movement.current_rank,
            spots=movement.spots_moved
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "NEGATIVE",
            "priority": 60,
            "team_ids": [movement.team_id],
            "player_ids": [movement.player_id],
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    def _generate_mvp_newcomer_headline(
        self,
        movement: MovementInfo,
        week: int
    ) -> Optional[HeadlineData]:
        """Generate headline for new MVP candidate."""
        template = random.choice(MVP_NEWCOMER_TEMPLATES)
        headline_text = template.format(
            player=movement.player_name,
            week=week
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "HYPE",
            "priority": 68,
            "team_ids": [movement.team_id],
            "player_ids": [movement.player_id],
            "metadata": {"award_type": AWARD_MVP, "coverage_type": AwardCoverageType.MVP_WATCH.value}
        }

    # =========================================================================
    # HEADLINE GENERATION - ROOKIES
    # =========================================================================

    def _generate_rookie_headlines(
        self,
        context: RaceContext,
        movements: List[MovementInfo],
        is_offensive: bool
    ) -> List[HeadlineData]:
        """
        Generate rookie award coverage headlines.

        Args:
            context: Race context
            movements: Movement information
            is_offensive: True for OROY, False for DROY

        Returns:
            List of headline data dictionaries
        """
        headlines: List[HeadlineData] = []
        award_type = AWARD_OROY if is_offensive else AWARD_DROY
        leader_templates = OROY_LEADER_TEMPLATES if is_offensive else DROY_LEADER_TEMPLATES
        rising_templates = OROY_RISING_TEMPLATES if is_offensive else DROY_RISING_TEMPLATES

        # Leader headline
        if context.leader:
            template = random.choice(leader_templates)
            headline_text = template.format(
                player=context.leader.player_name,
                week=context.week
            )

            headlines.append({
                "headline_type": "AWARD",
                "headline": headline_text,
                "sentiment": "POSITIVE",
                "priority": 60,
                "team_ids": [context.leader.team_id],
                "player_ids": [context.leader.player_id],
                "metadata": {"award_type": award_type, "coverage_type": AwardCoverageType.ROOKIE_WATCH.value}
            })

        # Rising candidate headline
        rising = [m for m in movements[1:] if m.movement_type == MovementType.RISING]
        if rising:
            riser = rising[0]
            template = random.choice(rising_templates)
            headline_text = template.format(
                player=riser.player_name,
                week=context.week,
                rank=riser.current_rank,
                spots=riser.spots_moved
            )

            headlines.append({
                "headline_type": "AWARD",
                "headline": headline_text,
                "sentiment": "POSITIVE",
                "priority": 55,
                "team_ids": [riser.team_id],
                "player_ids": [riser.player_id],
                "metadata": {"award_type": award_type, "coverage_type": AwardCoverageType.ROOKIE_WATCH.value}
            })

        return headlines

    def _generate_combined_rookie_headline(
        self,
        oroy_leader: Optional[AwardRaceEntry],
        droy_leader: Optional[AwardRaceEntry],
        week: int
    ) -> Optional[HeadlineData]:
        """Generate combined OROY/DROY headline."""
        if not oroy_leader or not droy_leader:
            return None

        oroy_name = f"{oroy_leader.first_name or 'Unknown'} {oroy_leader.last_name or 'Player'}"
        droy_name = f"{droy_leader.first_name or 'Unknown'} {droy_leader.last_name or 'Player'}"

        template = random.choice(ROOKIE_COMBINED_TEMPLATES)
        headline_text = template.format(
            oroy_leader=oroy_name,
            droy_leader=droy_name,
            week=week
        )

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": "POSITIVE",
            "priority": 58,
            "team_ids": [oroy_leader.team_id, droy_leader.team_id],
            "player_ids": [oroy_leader.player_id, droy_leader.player_id],
            "metadata": {"coverage_type": AwardCoverageType.ROOKIE_WATCH.value}
        }

    # =========================================================================
    # HEADLINE GENERATION - PREDICTIONS
    # =========================================================================

    def _generate_prediction_headline(
        self,
        standings: List[AwardRaceEntry],
        award_type: str,
        week: int,
        is_late_season: bool
    ) -> Optional[HeadlineData]:
        """
        Generate award prediction headline.

        Args:
            standings: Current standings
            award_type: Award type
            week: Current week
            is_late_season: True if Week 15+

        Returns:
            Headline data dictionary or None
        """
        if not standings:
            return None

        leader = standings[0]
        player_name = f"{leader.first_name or 'Unknown'} {leader.last_name or 'Player'}"

        # Calculate confidence
        confidence = self._calculate_confidence(standings, week)

        # Check for uncertainty
        if confidence < 50 and not is_late_season:
            template = random.choice(PREDICTION_UNCERTAINTY_TEMPLATES)
            headline_text = template.format(
                player=player_name,
                week=week,
                award=self._format_award_name(award_type)
            )
            sentiment = "NEUTRAL"
            priority = 50
        else:
            templates = LATE_SEASON_PREDICTION_TEMPLATES if is_late_season else MID_SEASON_PREDICTION_TEMPLATES
            template = random.choice(templates)
            headline_text = template.format(
                player=player_name,
                week=week,
                confidence=confidence,
                award=self._format_award_name(award_type)
            )
            sentiment = "HYPE" if confidence >= 75 else "POSITIVE"
            priority = 65 if is_late_season else 55

        return {
            "headline_type": "AWARD",
            "headline": headline_text,
            "sentiment": sentiment,
            "priority": priority,
            "team_ids": [leader.team_id],
            "player_ids": [leader.player_id],
            "metadata": {
                "award_type": award_type,
                "coverage_type": AwardCoverageType.AWARD_PREDICTION.value,
                "confidence": confidence
            }
        }

    def _calculate_confidence(
        self,
        standings: List[AwardRaceEntry],
        week: int
    ) -> int:
        """
        Calculate confidence percentage for award prediction.

        Args:
            standings: Current standings
            week: Current week

        Returns:
            Confidence percentage (0-100)
        """
        if not standings:
            return 0

        if len(standings) < 2:
            return 95  # Only one candidate = very confident

        leader_score = standings[0].cumulative_score
        second_score = standings[1].cumulative_score

        # Base confidence from gap
        gap = leader_score - second_score
        gap_factor = min(40, gap * 2)  # Max 40 points from gap

        # Week factor (later weeks = more confidence)
        weeks_remaining = max(0, self.FINAL_WEEK - week)
        week_factor = min(40, (18 - weeks_remaining) * 2.5)

        # Consistency factor (could be enhanced with week-over-week data)
        consistency_factor = 15  # Base consistency

        confidence = int(gap_factor + week_factor + consistency_factor)
        return min(98, max(20, confidence))  # Clamp 20-98

    def _format_award_name(self, award_type: str) -> str:
        """Format award type into readable name."""
        names = {
            AWARD_MVP: "MVP",
            AWARD_OPOY: "OPOY",
            AWARD_DPOY: "DPOY",
            AWARD_OROY: "OROY",
            AWARD_DROY: "DROY",
        }
        return names.get(award_type, award_type.upper())
