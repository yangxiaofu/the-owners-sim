"""
Season Constants

Centralized constants for NFL season simulation to eliminate magic numbers.
All game counts, timing parameters, and configuration values are defined here.

Usage:
    from season.season_constants import SeasonConstants

    if games_played >= SeasonConstants.REGULAR_SEASON_GAME_COUNT:
        # Transition to playoffs
"""


class SeasonConstants:
    """
    NFL Season simulation constants.

    This class provides all numeric constants used throughout the season
    simulation system, eliminating magic numbers and improving maintainability.
    """

    # ==================== Game Counts ====================

    # Preseason
    PRESEASON_WEEKS = 3
    """Number of preseason weeks (reduced from 4 in modern NFL)"""

    PRESEASON_GAME_COUNT = 48
    """Total preseason games (32 teams × 3 weeks / 2 teams per game)"""

    # Regular Season
    REGULAR_SEASON_WEEKS = 18
    """Number of regular season weeks (18-week schedule introduced in 2021)"""

    REGULAR_SEASON_GAMES_PER_TEAM = 17
    """Games per team in regular season"""

    REGULAR_SEASON_GAME_COUNT = 272
    """Total regular season games (32 teams × 17 games / 2 teams per game)"""

    # Playoffs
    PLAYOFF_GAME_COUNT = 13
    """
    Total playoff games:
    - Wild Card Round: 6 games (3 AFC + 3 NFC)
    - Divisional Round: 4 games (2 AFC + 2 NFC)
    - Conference Championships: 2 games (1 AFC + 1 NFC)
    - Super Bowl: 1 game
    """

    WILD_CARD_GAMES = 6
    DIVISIONAL_GAMES = 4
    CONFERENCE_CHAMPIONSHIP_GAMES = 2
    SUPER_BOWL_GAMES = 1

    # ==================== Timing ====================

    PLAYOFF_DELAY_DAYS = 14
    """Days between last regular season game and Wild Card weekend"""

    WILD_CARD_WEEKDAY = 5  # Saturday (Python calendar module weekday constant)
    """Wild Card games start on Saturday (weekday constant: 5)"""

    DATE_ADJUSTMENT_SAFETY_LIMIT = 30
    """
    Maximum days to search for correct weekday when adjusting dates.
    Prevents infinite loops in date calculation.
    """

    # ==================== Draft ====================

    DRAFT_ROUNDS = 7
    """Number of NFL draft rounds"""

    NFL_TEAMS_COUNT = 32
    """Total number of NFL teams"""

    DRAFT_PROSPECTS_PER_ROUND = NFL_TEAMS_COUNT
    """Draft picks per round (one per team)"""

    DRAFT_TOTAL_PROSPECTS = DRAFT_ROUNDS * DRAFT_PROSPECTS_PER_ROUND
    """Total draft prospects generated per year (7 rounds × 32 teams = 224)"""

    # ==================== Roster Limits ====================

    ACTIVE_ROSTER_SIZE = 53
    """Active roster size during regular season"""

    OFFSEASON_ROSTER_SIZE = 90
    """Maximum roster size during offseason"""

    PRACTICE_SQUAD_SIZE = 16
    """Practice squad roster slots"""

    # ==================== Season Phases ====================

    # Phase-specific week ranges (for validation)
    PRESEASON_WEEK_MIN = 1
    PRESEASON_WEEK_MAX = PRESEASON_WEEKS

    REGULAR_SEASON_WEEK_MIN = 1
    REGULAR_SEASON_WEEK_MAX = REGULAR_SEASON_WEEKS

    # ==================== Validation Thresholds ====================

    MIN_GAMES_FOR_STANDINGS = 1
    """Minimum games played before standings are meaningful"""

    PLAYOFF_PICTURE_RELEVANT_WEEK = 10
    """Week when playoff picture becomes relevant (Week 10+)"""

    # ==================== Database Query Limits ====================

    MAX_WEEK_FOR_REGULAR_SEASON_QUERY = 18
    """Maximum week number to include in regular season game queries"""

    MAX_WEEK_FOR_PRESEASON_QUERY = 4
    """Maximum week number to include in preseason game queries"""


class PhaseNames:
    """
    Standardized phase name strings for database queries and display.

    Use these instead of hardcoded strings to ensure consistency.
    """

    PRESEASON = "preseason"
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"
    OFFSEASON = "offseason"

    # Database phase name variants (lowercase for database compatibility)
    DB_PRESEASON = "preseason"
    DB_REGULAR_SEASON = "regular_season"
    DB_PLAYOFFS = "playoffs"
    DB_OFFSEASON = "offseason"

    # Display variants (capitalized for UI)
    DISPLAY_PRESEASON = "Preseason"
    DISPLAY_REGULAR_SEASON = "Regular Season"
    DISPLAY_PLAYOFFS = "Playoffs"
    DISPLAY_OFFSEASON = "Offseason"


class GameIDPrefixes:
    """
    Game ID prefixes for filtering different game types.

    These prefixes are used in event database queries to distinguish
    between regular season, playoff, and preseason games.
    """

    PRESEASON = "preseason_"
    PLAYOFF = "playoff_"
    # Regular season games have no prefix (just game_YYYY_WW_AWAYID_HOMEID)


# Backwards compatibility aliases
PRESEASON_GAME_COUNT = SeasonConstants.PRESEASON_GAME_COUNT
REGULAR_SEASON_GAME_COUNT = SeasonConstants.REGULAR_SEASON_GAME_COUNT
PLAYOFF_GAME_COUNT = SeasonConstants.PLAYOFF_GAME_COUNT
DRAFT_TOTAL_PROSPECTS = SeasonConstants.DRAFT_TOTAL_PROSPECTS
