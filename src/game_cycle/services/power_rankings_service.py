"""
Power Rankings Service - Weekly power rankings calculation and blurb generation.

Part of Milestone 12: Media Coverage, Tollgate 2.

Generates NFL-style power rankings based on:
- Win-Loss Record (30%)
- Point Differential (20%)
- Recent Performance Last 4 Games (20%)
- Strength of Victory (15%)
- Quality Wins (10%)
- Injuries Impact (5%)

Uses adaptive weights for early season (Weeks 1-3) when sample size is limited.
"""

import json
import logging
import random
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.media_coverage_api import MediaCoverageAPI, PowerRanking
from src.game_cycle.database.standings_api import StandingsAPI, TeamStanding
from src.game_cycle.database.box_scores_api import BoxScoresAPI
from src.game_cycle.database.head_to_head_api import HeadToHeadAPI


class Tier(str, Enum):
    """Power rankings tier classification."""
    ELITE = "ELITE"
    CONTENDER = "CONTENDER"
    PLAYOFF = "PLAYOFF"
    BUBBLE = "BUBBLE"
    REBUILDING = "REBUILDING"


@dataclass
class TeamPowerData:
    """Intermediate data for power ranking calculation."""
    team_id: int
    team_name: str
    city: str

    # Component scores (0-100 scale)
    record_score: float = 0.0
    point_diff_score: float = 0.0
    recent_score: float = 0.0
    sov_score: float = 0.0
    quality_wins_score: float = 0.0
    injury_score: float = 0.0

    # Final calculated values
    power_score: float = 0.0
    rank: int = 0
    tier: str = ""

    # Additional context for blurbs
    wins: int = 0
    losses: int = 0
    ties: int = 0
    point_differential: int = 0
    streak_type: Optional[str] = None  # "W" or "L"
    streak_count: int = 0
    recent_record: str = ""  # e.g., "3-1 L4"


# =============================================================================
# BLURB TEMPLATES (100+ total)
# =============================================================================

ELITE_TEMPLATES = [
    "{team} continues to dominate, looking like the team to beat.",
    "No one wants to face {team} in January.",
    "{team}'s {strength} is simply unstoppable right now.",
    "Super Bowl favorites {team} keep rolling.",
    "Championship-caliber football from {team}.",
    "{team} is playing at an elite level on both sides of the ball.",
    "The {nickname} are firing on all cylinders.",
    "{city} is dreaming of a parade route.",
    "Week after week, {team} proves they're the class of the NFL.",
    "Is this {team}'s year? They're certainly playing like it.",
    "{team} continues their dominant run through the league.",
    "Everyone is chasing {team} right now.",
    "The {nickname} look unbeatable when they're clicking.",
    "{team} making a statement: this is their conference.",
    "Hard to find any weaknesses in {team}'s game.",
    "Historic season taking shape in {city}.",
    "{team} playing with the confidence of a champion.",
    "The rest of the league is on notice after {team}'s latest performance.",
    "{team} has that championship swagger.",
    "Elite in every phase of the game - that's {team}.",
]

CONTENDER_TEMPLATES = [
    "{team} is a legitimate Super Bowl contender.",
    "The {nickname} are building something special.",
    "{team} has proven they belong among the NFL's elite.",
    "Don't sleep on {team} come playoff time.",
    "{city} has a team built for a deep playoff run.",
    "{team} continues to impress, stacking quality wins.",
    "The {nickname} are clicking at the right time.",
    "{team}'s {strength} gives them a real edge in the postseason.",
    "A few plays away from elite status - that's {team}.",
    "Dangerous team when playing their best football.",
    "{team} has the pieces to make noise in January.",
    "The {nickname} are rounding into playoff form.",
    "{team} proving the preseason hype was justified.",
    "One of the hottest teams in football right now.",
    "{team} continues to climb the rankings with consistent play.",
    "Watch out for {team} - they're getting better each week.",
    "The {nickname} have answered every question so far.",
    "{team} has the look of a team that could get hot at the right time.",
    "Solid on both sides of the ball, {team} is a problem for opponents.",
    "{team} is peaking at the perfect time.",
]

PLAYOFF_TEMPLATES = [
    "{team} is firmly in the playoff picture.",
    "The {nickname} are fighting for postseason positioning.",
    "{team} needs to keep winning to secure a playoff spot.",
    "Playoff-caliber team, but {team} needs to prove it down the stretch.",
    "The {nickname} are in the mix, but face a tough road ahead.",
    "{team} has work to do but remains a playoff threat.",
    "Wild card hunting in {city}.",
    "{team} is right where they want to be heading into December.",
    "The {nickname} are battling for their playoff lives.",
    "Every game matters now for {team}.",
    "{team} can't afford many more slip-ups.",
    "Solid team with playoff aspirations in {city}.",
    "The {nickname} are keeping themselves relevant in the playoff race.",
    "{team} needs their stars to step up down the stretch.",
    "Playoff berth within reach for {team}, but nothing is guaranteed.",
    "The pressure is mounting for {team} in a tight race.",
    "{team} is a team no one wants to play in the wild card round.",
    "Scrappy team that's finding ways to win.",
    "{team} showing resilience in a competitive conference.",
    "The {nickname} are playoff-caliber but need consistency.",
]

BUBBLE_TEMPLATES = [
    "{team} is on the outside looking in at the playoff picture.",
    "The {nickname} are fighting to stay relevant.",
    "{team}'s playoff hopes are fading fast.",
    "Inconsistency continues to plague {team}.",
    "The {nickname} need to string some wins together.",
    "{team} is running out of time to make a push.",
    "Disappointing season taking shape in {city}.",
    "The {nickname} are better than their record suggests.",
    "{team} can't seem to find any momentum.",
    "Questions mounting in {city} after another tough stretch.",
    "{team} needs a lot of help to make the playoffs now.",
    "The season is slipping away for {team}.",
    "Hard to trust {team} with the season on the line.",
    "The {nickname} are caught in no-man's land.",
    "{team} is neither good enough nor bad enough to feel good about.",
    "Changes may be coming in {city} if things don't turn around.",
    "A frustrating year for {team} and their fans.",
    "The {nickname} have shown flashes but can't sustain success.",
    "{team} is a team searching for an identity.",
    "Too many losses for {team} to climb back into the race.",
]

REBUILDING_TEMPLATES = [
    "{team} is playing for draft position at this point.",
    "The future is the focus in {city}.",
    "A long offseason awaits {team}.",
    "The {nickname} are looking ahead to next year.",
    "{team} is in full rebuilding mode.",
    "Growing pains continue for {team}.",
    "A difficult season, but lessons being learned in {city}.",
    "{team} needs to find some positives in a lost season.",
    "The {nickname} are playing for pride now.",
    "{team} fans are already looking at mock drafts.",
    "Experience for the young players is the silver lining for {team}.",
    "Next year can't come soon enough in {city}.",
    "{team} is building for the future, not the present.",
    "The {nickname} are learning what it takes to compete.",
    "{team} has some pieces, but needs more to contend.",
    "A reset is coming in {city}.",
    "The {nickname} are playing out the string.",
    "{team}'s season has been one to forget.",
    "Not much going right for {team} this year.",
    "Patience is required in {city} as the rebuild continues.",
]

# Movement-specific templates
RISING_TEMPLATES = [
    "{team} ({movement}) is one of the hottest teams in football.",
    "The {nickname} surge {movement} spots after impressive wins.",
    "{team} ({movement}) continues their climb up the rankings.",
    "Major momentum building in {city}. {team} jumps {movement} spots.",
    "{team} leaps {movement} spots after a statement performance.",
]

FALLING_TEMPLATES = [
    "{team} ({movement}) tumbles after a rough week.",
    "The {nickname} drop {movement} spots following disappointing loss.",
    "{team} ({movement}) falls after a bad performance.",
    "Freefall in {city}. {team} plummets {movement} spots.",
    "A reality check for {team} who drop {movement} spots.",
]

STEADY_TEMPLATES = [
    "{team} holds steady at {rank}.",
    "No change for {team}, still ranked {rank}.",
    "{team} maintains their position at No. {rank}.",
]

# Streak-specific additions
WINNING_STREAK_PHRASES = [
    "Winners of {count} straight.",
    "Currently riding a {count}-game winning streak.",
    "{count} consecutive victories for the {nickname}.",
    "The {nickname} have won {count} in a row.",
]

LOSING_STREAK_PHRASES = [
    "Losers of {count} straight.",
    "Currently on a {count}-game losing skid.",
    "{count} consecutive losses for the {nickname}.",
    "The {nickname} have dropped {count} in a row.",
]


class PowerRankingsService:
    """
    Service for generating weekly power rankings.

    Calculates rankings using weighted factors and generates
    narrative blurbs for each team. Supports adaptive weights
    for early season when sample size is limited.
    """

    # Standard weights (used after Week 3)
    STANDARD_WEIGHTS = {
        'record': 0.30,
        'point_diff': 0.20,
        'recent': 0.20,
        'sov': 0.15,
        'quality_wins': 0.10,
        'injuries': 0.05,
    }

    # Early season weights (Weeks 1-3) - more weight on record, less on recent
    EARLY_SEASON_WEIGHTS = {
        'record': 0.45,
        'point_diff': 0.30,
        'recent': 0.05,  # Not enough games for meaningful L4
        'sov': 0.10,
        'quality_wins': 0.05,
        'injuries': 0.05,
    }

    # Tier boundaries (rank ranges)
    TIER_BOUNDARIES = {
        Tier.ELITE: (1, 4),
        Tier.CONTENDER: (5, 10),
        Tier.PLAYOFF: (11, 16),
        Tier.BUBBLE: (17, 22),
        Tier.REBUILDING: (23, 32),
    }

    # Movement thresholds for templates
    SIGNIFICANT_RISE = 3
    SIGNIFICANT_FALL = 3

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize PowerRankingsService.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Initialize database connection and APIs
        self._db = GameCycleDatabase(db_path)
        self._standings_api = StandingsAPI(self._db)
        self._box_scores_api = BoxScoresAPI(db_path)
        self._head_to_head_api = HeadToHeadAPI(self._db)
        self._media_api = MediaCoverageAPI(self._db)

        # Load team data
        self._teams_data = self._load_teams_data()

    def _load_teams_data(self) -> Dict[int, Dict[str, Any]]:
        """Load team information from JSON."""
        teams_file = Path(__file__).parent.parent.parent / "data" / "teams.json"
        try:
            with open(teams_file) as f:
                data = json.load(f)
                # Convert string keys to int
                return {int(k): v for k, v in data.get("teams", {}).items()}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._logger.warning(f"Could not load teams.json: {e}")
            return {}

    def _get_team_info(self, team_id: int) -> Tuple[str, str, str]:
        """Get team name, city, and nickname."""
        team = self._teams_data.get(team_id, {})
        return (
            team.get("full_name", f"Team {team_id}"),
            team.get("city", "Unknown"),
            team.get("nickname", f"Team {team_id}")
        )

    def calculate_rankings(self, week: int) -> List[PowerRanking]:
        """
        Calculate power rankings for a given week.

        Args:
            week: Week number (1-18 for regular season)

        Returns:
            List of PowerRanking objects sorted by rank
        """
        self._logger.info(
            f"Calculating power rankings for Week {week} "
            f"(dynasty={self._dynasty_id}, season={self._season})"
        )

        # Get standings for all teams
        self._logger.debug(
            f"Querying standings: dynasty={self._dynasty_id}, season={self._season}"
        )
        standings = self._standings_api.get_standings(self._dynasty_id, self._season)

        if not standings:
            self._logger.error(
                f"No standings data found for dynasty={self._dynasty_id}, season={self._season}. "
                f"Cannot calculate power rankings without standings. "
                f"Check if games have been simulated and standings are being saved correctly."
            )
            return []

        self._logger.debug(f"Retrieved {len(standings)} teams from standings")
        if standings:
            sample_teams = [s.team_id for s in standings[:3]]
            self._logger.debug(f"Sample team IDs from standings: {sample_teams}")

        # Determine weights based on week
        weights = self._get_weights_for_week(week)

        # Calculate power data for each team
        team_data_list: List[TeamPowerData] = []

        for standing in standings:
            team_data = self._calculate_team_power_data(standing, week, weights)
            team_data_list.append(team_data)

        # Sort by power score (descending)
        team_data_list.sort(key=lambda x: x.power_score, reverse=True)

        # Assign ranks and tiers
        for idx, team_data in enumerate(team_data_list, start=1):
            team_data.rank = idx
            team_data.tier = self._get_tier_for_rank(idx).value

        # Get previous rankings for movement calculation
        previous_rankings = self._get_previous_rankings(week)

        # Generate PowerRanking objects with blurbs
        rankings: List[PowerRanking] = []
        for team_data in team_data_list:
            previous_rank = previous_rankings.get(team_data.team_id)
            blurb = self._generate_blurb(team_data, previous_rank)

            ranking = PowerRanking(
                id=None,  # Will be assigned on save
                dynasty_id=self._dynasty_id,
                season=self._season,
                week=week,
                team_id=team_data.team_id,
                rank=team_data.rank,
                previous_rank=previous_rank,
                tier=team_data.tier,
                blurb=blurb,
                team_name=team_data.team_name,  # Optional field with team name
                created_at=None
            )
            rankings.append(ranking)

        return rankings

    def calculate_and_save_rankings(self, week: int) -> List[PowerRanking]:
        """
        Calculate and persist power rankings.

        Args:
            week: Week number

        Returns:
            List of saved PowerRanking objects
        """
        rankings = self.calculate_rankings(week)

        if rankings:
            # Convert PowerRanking objects to dicts for the API
            rankings_dicts = [
                {
                    'team_id': r.team_id,
                    'rank': r.rank,
                    'previous_rank': r.previous_rank,
                    'tier': r.tier,
                    'blurb': r.blurb,
                }
                for r in rankings
            ]
            self._media_api.save_power_rankings(
                dynasty_id=self._dynasty_id,
                season=self._season,
                week=week,
                rankings=rankings_dicts
            )
            self._logger.info(f"Saved {len(rankings)} power rankings for Week {week}")

        return rankings

    def _get_weights_for_week(self, week: int) -> Dict[str, float]:
        """Get appropriate weights based on week number."""
        if week <= 3:
            return self.EARLY_SEASON_WEIGHTS.copy()
        return self.STANDARD_WEIGHTS.copy()

    def _calculate_team_power_data(
        self,
        standing: TeamStanding,
        week: int,
        weights: Dict[str, float]
    ) -> TeamPowerData:
        """
        Calculate all power score components for a team.

        Args:
            standing: Team's current standing record
            week: Current week number
            weights: Component weights to use

        Returns:
            TeamPowerData with all component scores
        """
        team_name, city, nickname = self._get_team_info(standing.team_id)

        team_data = TeamPowerData(
            team_id=standing.team_id,
            team_name=team_name,
            city=city,
            wins=standing.wins,
            losses=standing.losses,
            ties=standing.ties,
            point_differential=standing.point_differential,
        )

        # Calculate individual component scores (0-100 scale)
        team_data.record_score = self._calculate_record_score(standing)
        team_data.point_diff_score = self._calculate_point_diff_score(standing, week)
        team_data.recent_score = self._calculate_recent_score(standing.team_id, week)
        team_data.sov_score = self._calculate_sov_score(standing.team_id)
        team_data.quality_wins_score = self._calculate_quality_wins_score(standing.team_id)
        team_data.injury_score = self._calculate_injury_score(standing.team_id)

        # Calculate weighted power score
        team_data.power_score = (
            team_data.record_score * weights['record'] +
            team_data.point_diff_score * weights['point_diff'] +
            team_data.recent_score * weights['recent'] +
            team_data.sov_score * weights['sov'] +
            team_data.quality_wins_score * weights['quality_wins'] +
            team_data.injury_score * weights['injuries']
        )

        # Calculate streak info
        streak_type, streak_count = self._calculate_streak(standing.team_id)
        team_data.streak_type = streak_type
        team_data.streak_count = streak_count

        # Calculate recent record string
        team_data.recent_record = self._get_recent_record_string(standing.team_id, week)

        return team_data

    def _calculate_record_score(self, standing: TeamStanding) -> float:
        """
        Calculate record-based score (0-100).

        Uses win percentage with adjustment for ties.
        """
        total_games = standing.wins + standing.losses + standing.ties
        if total_games == 0:
            return 50.0  # Neutral score for no games

        win_pct = standing.win_percentage
        return win_pct * 100

    def _calculate_point_diff_score(self, standing: TeamStanding, week: int) -> float:
        """
        Calculate point differential score (0-100).

        Normalizes point differential to a 0-100 scale.
        Average NFL point differential per game is roughly ±10 points.
        """
        total_games = standing.wins + standing.losses + standing.ties
        if total_games == 0:
            return 50.0

        # Calculate per-game differential
        pg_diff = standing.point_differential / total_games

        # Normalize: +15 PPG diff = 100, -15 PPG diff = 0, 0 = 50
        # Scale: Every point of differential is worth ~3.33 points on 100 scale
        normalized = 50 + (pg_diff * 3.33)

        # Clamp to 0-100
        return max(0, min(100, normalized))

    def _calculate_recent_score(self, team_id: int, week: int) -> float:
        """
        Calculate recent performance score (L4 games).

        Looks at last 4 box scores to determine recent form.
        """
        # Get recent box scores
        box_scores = self._box_scores_api.get_team_box_scores(
            dynasty_id=self._dynasty_id,
            team_id=team_id,
            season=self._season,
            limit=4
        )

        if not box_scores:
            return 50.0  # Neutral if no games

        # Calculate recent win/loss from scores
        wins = 0
        total = len(box_scores)
        point_diff = 0

        for box in box_scores:
            # We need to check opponent's score
            game_boxes = self._box_scores_api.get_game_box_scores(
                dynasty_id=self._dynasty_id,
                game_id=box.game_id
            )

            our_score = box.total_score
            opp_score = 0
            for gb in game_boxes:
                if gb.team_id != team_id:
                    opp_score = gb.total_score
                    break

            if our_score > opp_score:
                wins += 1
            point_diff += (our_score - opp_score)

        # Weight: 60% wins, 40% point differential
        win_pct_score = (wins / total) * 100 if total > 0 else 50

        # Point diff in recent games
        avg_diff = point_diff / total if total > 0 else 0
        diff_score = 50 + (avg_diff * 2.5)  # Smaller scale for recent
        diff_score = max(0, min(100, diff_score))

        return win_pct_score * 0.6 + diff_score * 0.4

    def _calculate_sov_score(self, team_id: int) -> float:
        """
        Calculate Strength of Victory score.

        SOV = Combined win percentage of teams defeated.
        """
        # Get all H2H records for this team
        records = self._head_to_head_api.get_team_all_records(
            dynasty_id=self._dynasty_id,
            team_id=team_id
        )

        if not records:
            return 50.0  # Neutral if no games

        # Get standings for all teams
        all_standings = {
            s.team_id: s for s in
            self._standings_api.get_standings(self._dynasty_id, self._season)
        }

        total_opp_win_pct = 0.0
        wins_count = 0

        for record in records:
            # Determine which team is the opponent
            opp_id = record.team_b_id if record.team_a_id == team_id else record.team_a_id

            # Get wins against this opponent
            if record.team_a_id == team_id:
                wins = record.team_a_wins
            else:
                wins = record.team_b_wins

            if wins > 0 and opp_id in all_standings:
                opp_standing = all_standings[opp_id]
                # Add opponent's win pct for each win
                total_opp_win_pct += opp_standing.win_percentage * wins
                wins_count += wins

        if wins_count == 0:
            return 30.0  # Below average if no wins

        avg_opp_win_pct = total_opp_win_pct / wins_count
        return avg_opp_win_pct * 100

    def _calculate_quality_wins_score(self, team_id: int) -> float:
        """
        Calculate quality wins score.

        Quality win = beating a team with winning record.
        """
        records = self._head_to_head_api.get_team_all_records(
            dynasty_id=self._dynasty_id,
            team_id=team_id
        )

        if not records:
            return 50.0

        all_standings = {
            s.team_id: s for s in
            self._standings_api.get_standings(self._dynasty_id, self._season)
        }

        quality_wins = 0
        total_wins = 0

        for record in records:
            opp_id = record.team_b_id if record.team_a_id == team_id else record.team_a_id

            if record.team_a_id == team_id:
                wins = record.team_a_wins
            else:
                wins = record.team_b_wins

            total_wins += wins

            if wins > 0 and opp_id in all_standings:
                opp_standing = all_standings[opp_id]
                if opp_standing.win_percentage > 0.5:
                    quality_wins += wins

        if total_wins == 0:
            return 30.0

        # Quality win ratio, scaled to 0-100
        ratio = quality_wins / total_wins
        return ratio * 100

    def _calculate_injury_score(self, team_id: int) -> float:
        """
        Calculate injury impact score.

        Higher score = healthier team (less injury impact).
        This requires access to injury service, which may not always be available.
        """
        # For now, return a neutral score
        # In full implementation, would check InjuryService.get_active_injuries(team_id)
        # and calculate impact based on player importance
        try:
            from src.game_cycle.services.injury_service import InjuryService

            injury_service = InjuryService(
                self._db_path, self._dynasty_id, self._season
            )
            active_injuries = injury_service.get_active_injuries(team_id)

            # More injuries = lower score
            # No injuries = 100, 5+ injuries = 50, 10+ = 25
            injury_count = len(active_injuries)

            if injury_count == 0:
                return 100.0
            elif injury_count <= 2:
                return 90.0
            elif injury_count <= 4:
                return 75.0
            elif injury_count <= 6:
                return 60.0
            elif injury_count <= 8:
                return 45.0
            else:
                return 30.0

        except Exception as e:
            self._logger.debug(f"Could not calculate injury impact: {e}")
            return 75.0  # Default to slightly healthy

    def _calculate_streak(self, team_id: int) -> Tuple[Optional[str], int]:
        """
        Calculate current winning/losing streak.

        Returns:
            Tuple of (streak_type: 'W' or 'L', streak_count)
        """
        box_scores = self._box_scores_api.get_team_box_scores(
            dynasty_id=self._dynasty_id,
            team_id=team_id,
            season=self._season,
            limit=10
        )

        if not box_scores:
            return None, 0

        streak_type = None
        streak_count = 0

        for box in box_scores:
            game_boxes = self._box_scores_api.get_game_box_scores(
                dynasty_id=self._dynasty_id,
                game_id=box.game_id
            )

            our_score = box.total_score
            opp_score = 0
            for gb in game_boxes:
                if gb.team_id != team_id:
                    opp_score = gb.total_score
                    break

            result = 'W' if our_score > opp_score else ('L' if opp_score > our_score else 'T')

            if streak_type is None:
                streak_type = result
                streak_count = 1
            elif result == streak_type:
                streak_count += 1
            else:
                break  # Streak ended

        return streak_type if streak_type in ('W', 'L') else None, streak_count

    def _get_recent_record_string(self, team_id: int, week: int) -> str:
        """Get L4 record string like '3-1 L4'."""
        box_scores = self._box_scores_api.get_team_box_scores(
            dynasty_id=self._dynasty_id,
            team_id=team_id,
            season=self._season,
            limit=4
        )

        if not box_scores:
            return "N/A"

        wins = 0
        losses = 0

        for box in box_scores:
            game_boxes = self._box_scores_api.get_game_box_scores(
                dynasty_id=self._dynasty_id,
                game_id=box.game_id
            )

            our_score = box.total_score
            opp_score = 0
            for gb in game_boxes:
                if gb.team_id != team_id:
                    opp_score = gb.total_score
                    break

            if our_score > opp_score:
                wins += 1
            elif opp_score > our_score:
                losses += 1

        games = len(box_scores)
        return f"{wins}-{losses} L{games}"

    def _get_tier_for_rank(self, rank: int) -> Tier:
        """Get tier classification for a given rank."""
        for tier, (low, high) in self.TIER_BOUNDARIES.items():
            if low <= rank <= high:
                return tier
        return Tier.REBUILDING  # Default for ranks > 32

    def _get_previous_rankings(self, current_week: int) -> Dict[int, int]:
        """Get previous week's rankings for movement calculation."""
        if current_week <= 1:
            return {}

        previous = self._media_api.get_power_rankings(
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=current_week - 1
        )

        return {r.team_id: r.rank for r in previous}

    def _generate_blurb(
        self,
        team_data: TeamPowerData,
        previous_rank: Optional[int]
    ) -> str:
        """
        Generate narrative blurb for a team's ranking.

        Considers tier, movement, and streaks for variety.
        """
        tier = Tier(team_data.tier)
        rank = team_data.rank

        # Get template pool based on tier
        template_pool = self._get_tier_templates(tier)

        # Check for significant movement
        movement = None
        if previous_rank is not None:
            movement = previous_rank - rank  # Positive = moved up

            if movement >= self.SIGNIFICANT_RISE:
                # Use rising template occasionally
                if random.random() < 0.5:
                    template_pool = RISING_TEMPLATES
            elif movement <= -self.SIGNIFICANT_FALL:
                if random.random() < 0.5:
                    template_pool = FALLING_TEMPLATES

        # Select random template
        template = random.choice(template_pool)

        # Prepare substitution data
        team_name, city, nickname = self._get_team_info(team_data.team_id)

        # Determine strength mention
        strength = self._determine_team_strength(team_data)

        # Format movement string
        movement_str = ""
        if movement is not None:
            if movement > 0:
                movement_str = f"▲{movement}"
            elif movement < 0:
                movement_str = f"▼{abs(movement)}"
            else:
                movement_str = "—"

        # Fill template
        blurb = template.format(
            team=team_name,
            city=city,
            nickname=nickname,
            rank=rank,
            strength=strength,
            movement=movement_str,
            count=team_data.streak_count,
        )

        # Optionally append streak info
        if team_data.streak_count >= 3:
            if team_data.streak_type == 'W':
                streak_phrase = random.choice(WINNING_STREAK_PHRASES).format(
                    count=team_data.streak_count,
                    nickname=nickname
                )
                blurb = f"{blurb} {streak_phrase}"
            elif team_data.streak_type == 'L':
                streak_phrase = random.choice(LOSING_STREAK_PHRASES).format(
                    count=team_data.streak_count,
                    nickname=nickname
                )
                blurb = f"{blurb} {streak_phrase}"

        return blurb

    def _get_tier_templates(self, tier: Tier) -> List[str]:
        """Get template list for a tier."""
        mapping = {
            Tier.ELITE: ELITE_TEMPLATES,
            Tier.CONTENDER: CONTENDER_TEMPLATES,
            Tier.PLAYOFF: PLAYOFF_TEMPLATES,
            Tier.BUBBLE: BUBBLE_TEMPLATES,
            Tier.REBUILDING: REBUILDING_TEMPLATES,
        }
        return mapping.get(tier, BUBBLE_TEMPLATES)

    def _determine_team_strength(self, team_data: TeamPowerData) -> str:
        """Determine which aspect to highlight as team strength."""
        # Simple heuristic based on scores
        if team_data.point_diff_score > 70:
            return "dominant play"
        elif team_data.recent_score > 75:
            return "recent surge"
        elif team_data.sov_score > 70:
            return "quality victories"
        elif team_data.quality_wins_score > 60:
            return "big-game performances"
        else:
            return "overall effort"

    # =========================================================================
    # Public Query Methods
    # =========================================================================

    def get_rankings(self, week: int) -> List[PowerRanking]:
        """
        Get saved power rankings for a week.

        Args:
            week: Week number

        Returns:
            List of PowerRanking objects
        """
        return self._media_api.get_power_rankings(
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=week
        )

    def get_team_ranking_history(self, team_id: int) -> List[PowerRanking]:
        """
        Get ranking history for a specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of PowerRanking objects across all weeks
        """
        return self._media_api.get_team_ranking_history(
            dynasty_id=self._dynasty_id,
            season=self._season,
            team_id=team_id
        )

    def get_movement_display(
        self,
        current_rank: int,
        previous_rank: Optional[int]
    ) -> str:
        """
        Get display string for ranking movement.

        Args:
            current_rank: Current week rank
            previous_rank: Previous week rank (or None)

        Returns:
            Movement string like "▲3", "▼2", "—", or "NEW"
        """
        if previous_rank is None:
            return "NEW"

        diff = previous_rank - current_rank
        if diff > 0:
            return f"▲{diff}"
        elif diff < 0:
            return f"▼{abs(diff)}"
        return "—"
