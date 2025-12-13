"""
Rivalry Modifiers - Gameplay effects for rivalry games.

Part of Milestone 11: Schedule & Rivalries, Tollgate 5.

Rivalry games have enhanced atmosphere and higher stakes, which affects:
- Player performance (offensive/defensive boosts)
- Turnover probability (more chaos in intense rivalries)
- Penalty rates (more chippy play)
- Home field advantage (amplified crowd noise)

Usage:
    from game_management.rivalry_modifiers import calculate_rivalry_modifiers

    modifiers = calculate_rivalry_modifiers(
        rivalry=rivalry,
        head_to_head=h2h_record,
        home_team_id=22,
        away_team_id=23,
        is_playoff=False
    )

    # Apply to play parameters
    play_params.offensive_rating *= modifiers.home_offensive_boost
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

# Import models - use try/except for flexibility
try:
    from src.game_cycle.models.rivalry import Rivalry
    from src.game_cycle.models.head_to_head import HeadToHeadRecord
except ImportError:
    # Allow running tests without full import chain
    Rivalry = None
    HeadToHeadRecord = None


class IntensityLevel(Enum):
    """Rivalry intensity levels for modifier scaling."""
    LEGENDARY = "legendary"    # 90-100: Historic rivalries (Bears-Packers)
    INTENSE = "intense"        # 70-89: Strong division rivalries
    MODERATE = "moderate"      # 50-69: Regular division games
    MILD = "mild"              # 30-49: Occasional matchups
    MINIMAL = "minimal"        # 1-29: Rare opponents

    @classmethod
    def from_intensity(cls, intensity: int) -> "IntensityLevel":
        """Get intensity level from numeric value."""
        if intensity >= 90:
            return cls.LEGENDARY
        elif intensity >= 70:
            return cls.INTENSE
        elif intensity >= 50:
            return cls.MODERATE
        elif intensity >= 30:
            return cls.MILD
        return cls.MINIMAL


@dataclass
class RivalryGameModifiers:
    """
    Modifiers applied during rivalry games.

    All multipliers are centered around 1.0 (no effect):
    - > 1.0 = boost/increase
    - < 1.0 = penalty/decrease

    Attributes:
        home_offensive_boost: Multiplier for home team offensive rating (0.95-1.10)
        home_defensive_boost: Multiplier for home team defensive rating (0.95-1.10)
        away_offensive_boost: Multiplier for away team offensive rating (0.95-1.10)
        away_defensive_boost: Multiplier for away team defensive rating (0.95-1.10)
        turnover_variance: Multiplier for turnover probability (1.0-1.5)
        penalty_rate_modifier: Multiplier for penalty probability (1.0-1.4)
        crowd_noise_boost: Additional home field boost (1.0-1.3)
        intensity_level: The calculated intensity level
        is_revenge_game_home: True if home team lost last meeting
        is_revenge_game_away: True if away team lost last meeting
        home_on_streak: Number of consecutive wins by home team vs away
        away_on_streak: Number of consecutive wins by away team vs home
    """
    home_offensive_boost: float = 1.0
    home_defensive_boost: float = 1.0
    away_offensive_boost: float = 1.0
    away_defensive_boost: float = 1.0
    turnover_variance: float = 1.0
    penalty_rate_modifier: float = 1.0
    crowd_noise_boost: float = 1.0
    intensity_level: IntensityLevel = IntensityLevel.MINIMAL
    is_revenge_game_home: bool = False
    is_revenge_game_away: bool = False
    home_on_streak: int = 0
    away_on_streak: int = 0

    @property
    def is_rivalry_game(self) -> bool:
        """True if this is a rivalry game with meaningful modifiers."""
        return self.intensity_level != IntensityLevel.MINIMAL

    @property
    def total_home_boost(self) -> float:
        """Combined offensive and defensive boost for home team."""
        return (self.home_offensive_boost + self.home_defensive_boost) / 2

    @property
    def total_away_boost(self) -> float:
        """Combined offensive and defensive boost for away team."""
        return (self.away_offensive_boost + self.away_defensive_boost) / 2

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "home_offensive_boost": self.home_offensive_boost,
            "home_defensive_boost": self.home_defensive_boost,
            "away_offensive_boost": self.away_offensive_boost,
            "away_defensive_boost": self.away_defensive_boost,
            "turnover_variance": self.turnover_variance,
            "penalty_rate_modifier": self.penalty_rate_modifier,
            "crowd_noise_boost": self.crowd_noise_boost,
            "intensity_level": self.intensity_level.value,
            "is_revenge_game_home": self.is_revenge_game_home,
            "is_revenge_game_away": self.is_revenge_game_away,
            "home_on_streak": self.home_on_streak,
            "away_on_streak": self.away_on_streak,
        }


def calculate_rivalry_modifiers(
    rivalry: Optional["Rivalry"],
    head_to_head: Optional["HeadToHeadRecord"],
    home_team_id: int,
    away_team_id: int,
    is_playoff: bool = False,
) -> RivalryGameModifiers:
    """
    Calculate gameplay modifiers for a rivalry game.

    The modifiers are calculated based on:
    1. Rivalry intensity (0-100 scale)
    2. Head-to-head history (streaks, recent results)
    3. Revenge game factor (lost last meeting)
    4. Playoff stakes

    Args:
        rivalry: Rivalry object between teams, or None for non-rivalry
        head_to_head: HeadToHeadRecord between teams, or None
        home_team_id: ID of the home team
        away_team_id: ID of the away team
        is_playoff: True if this is a playoff game

    Returns:
        RivalryGameModifiers with calculated values
    """
    # No rivalry = no modifiers (return defaults)
    if rivalry is None:
        return RivalryGameModifiers()

    # Get intensity level
    intensity = rivalry.intensity
    intensity_level = IntensityLevel.from_intensity(intensity)

    # Base modifiers from intensity
    modifiers = _calculate_intensity_modifiers(intensity, intensity_level)

    # Add head-to-head effects if available
    if head_to_head is not None:
        modifiers = _apply_head_to_head_effects(
            modifiers, head_to_head, home_team_id, away_team_id
        )

    # Playoff boost
    if is_playoff:
        modifiers = _apply_playoff_boost(modifiers)

    return modifiers


def _calculate_intensity_modifiers(
    intensity: int,
    intensity_level: IntensityLevel
) -> RivalryGameModifiers:
    """
    Calculate base modifiers from rivalry intensity.

    Intensity effects:
    - Legendary (90+): Major boosts, high variance, lots of penalties
    - Intense (70-89): Strong effects, elevated stakes
    - Moderate (50-69): Noticeable effects
    - Mild (30-49): Minor effects
    - Minimal (<30): Negligible effects
    """
    # Scale intensity to modifier range
    # intensity 0-100 maps to multiplier adjustments

    # Offensive/defensive boost: players try harder in rivalry games
    # Range: 1.0 to 1.08 (up to 8% boost at max intensity)
    performance_boost = 1.0 + (intensity / 100) * 0.08

    # Turnover variance: more chaos in intense games
    # Range: 1.0 to 1.40 (up to 40% more turnovers at max intensity)
    turnover_var = 1.0 + (intensity / 100) * 0.40

    # Penalty rate: chippy play increases penalties
    # Range: 1.0 to 1.35 (up to 35% more penalties at max intensity)
    penalty_mod = 1.0 + (intensity / 100) * 0.35

    # Crowd noise: enhanced home field advantage
    # Range: 1.0 to 1.25 (up to 25% boost at max intensity)
    crowd_boost = 1.0 + (intensity / 100) * 0.25

    return RivalryGameModifiers(
        home_offensive_boost=performance_boost,
        home_defensive_boost=performance_boost,
        away_offensive_boost=performance_boost,
        away_defensive_boost=performance_boost,
        turnover_variance=turnover_var,
        penalty_rate_modifier=penalty_mod,
        crowd_noise_boost=crowd_boost,
        intensity_level=intensity_level,
    )


def _apply_head_to_head_effects(
    modifiers: RivalryGameModifiers,
    h2h: "HeadToHeadRecord",
    home_team_id: int,
    away_team_id: int,
) -> RivalryGameModifiers:
    """
    Apply effects based on head-to-head history.

    Effects:
    - Revenge game: Team that lost last meeting gets motivation boost
    - Winning streak: Team on streak gets confidence boost
    - Losing streak: Team on losing streak gets desperation boost
    """
    # Determine streak status
    home_on_streak = 0
    away_on_streak = 0

    if h2h.current_streak_team == home_team_id:
        home_on_streak = h2h.current_streak_count
    elif h2h.current_streak_team == away_team_id:
        away_on_streak = h2h.current_streak_count

    # Revenge game detection
    is_revenge_home = (h2h.last_meeting_winner == away_team_id)
    is_revenge_away = (h2h.last_meeting_winner == home_team_id)

    # Calculate streak/revenge boosts
    # Revenge game: +3% offense, +2% defense
    revenge_offense_boost = 0.03
    revenge_defense_boost = 0.02

    # Winning streak: +1% defense per win (max +5%)
    # Confidence makes them play smarter defense
    streak_defense_boost = min(0.05, 0.01 * max(home_on_streak, away_on_streak))

    # Losing streak (opponent has long streak): +2% offense
    # Desperation makes them take more chances
    if home_on_streak >= 3:
        # Away team is desperate
        modifiers.away_offensive_boost += 0.02
    if away_on_streak >= 3:
        # Home team is desperate
        modifiers.home_offensive_boost += 0.02

    # Apply revenge game boosts
    if is_revenge_home:
        modifiers.home_offensive_boost += revenge_offense_boost
        modifiers.home_defensive_boost += revenge_defense_boost
    if is_revenge_away:
        modifiers.away_offensive_boost += revenge_offense_boost
        modifiers.away_defensive_boost += revenge_defense_boost

    # Apply streak confidence boost (to team on streak)
    if home_on_streak > 0:
        modifiers.home_defensive_boost += streak_defense_boost
    if away_on_streak > 0:
        modifiers.away_defensive_boost += streak_defense_boost

    # Update modifiers with streak info
    modifiers.home_on_streak = home_on_streak
    modifiers.away_on_streak = away_on_streak
    modifiers.is_revenge_game_home = is_revenge_home
    modifiers.is_revenge_game_away = is_revenge_away

    return modifiers


def _apply_playoff_boost(modifiers: RivalryGameModifiers) -> RivalryGameModifiers:
    """
    Apply additional modifiers for playoff rivalry games.

    Playoff games increase all effects:
    - Performance boosts increase by 2%
    - Turnover variance increases by 10%
    - Penalty rate increases by 5%
    """
    # Playoff intensity multiplier
    playoff_boost = 1.02  # 2% additional boost

    modifiers.home_offensive_boost *= playoff_boost
    modifiers.home_defensive_boost *= playoff_boost
    modifiers.away_offensive_boost *= playoff_boost
    modifiers.away_defensive_boost *= playoff_boost

    modifiers.turnover_variance *= 1.10  # 10% more variance
    modifiers.penalty_rate_modifier *= 1.05  # 5% more penalties

    return modifiers


def get_rivalry_game_description(modifiers: RivalryGameModifiers) -> str:
    """
    Get a human-readable description of the rivalry game atmosphere.

    Args:
        modifiers: The calculated modifiers for the game

    Returns:
        Description string for display/commentary
    """
    if not modifiers.is_rivalry_game:
        return ""

    descriptions = {
        IntensityLevel.LEGENDARY: "A legendary rivalry matchup! The intensity is off the charts.",
        IntensityLevel.INTENSE: "An intense rivalry game with heightened stakes.",
        IntensityLevel.MODERATE: "A solid rivalry matchup with playoff-like atmosphere.",
        IntensityLevel.MILD: "A rivalry game with some extra edge.",
        IntensityLevel.MINIMAL: "A competitive divisional matchup.",
    }

    base_desc = descriptions.get(modifiers.intensity_level, "")

    extras = []
    if modifiers.is_revenge_game_home:
        extras.append("Home team seeking revenge after last meeting's loss")
    if modifiers.is_revenge_game_away:
        extras.append("Away team looking to avenge their previous defeat")
    if modifiers.home_on_streak >= 3:
        extras.append(f"Home team riding a {modifiers.home_on_streak}-game winning streak in this rivalry")
    if modifiers.away_on_streak >= 3:
        extras.append(f"Away team has won the last {modifiers.away_on_streak} meetings")

    if extras:
        return f"{base_desc} {'. '.join(extras)}."
    return base_desc


# Pre-defined modifier sets for testing/reference
NO_RIVALRY_MODIFIERS = RivalryGameModifiers()

LEGENDARY_RIVALRY_MODIFIERS = RivalryGameModifiers(
    home_offensive_boost=1.08,
    home_defensive_boost=1.08,
    away_offensive_boost=1.08,
    away_defensive_boost=1.08,
    turnover_variance=1.40,
    penalty_rate_modifier=1.35,
    crowd_noise_boost=1.25,
    intensity_level=IntensityLevel.LEGENDARY,
)

DIVISION_RIVALRY_MODIFIERS = RivalryGameModifiers(
    home_offensive_boost=1.04,
    home_defensive_boost=1.04,
    away_offensive_boost=1.04,
    away_defensive_boost=1.04,
    turnover_variance=1.20,
    penalty_rate_modifier=1.20,
    crowd_noise_boost=1.15,
    intensity_level=IntensityLevel.MODERATE,
)
