"""
Momentum Tracker for NFL Game Simulation.

Tracks game momentum for both teams based on recent events (touchdowns, turnovers,
big plays). Momentum affects play outcomes and coaching decisions.

Momentum Range: -20 to +20
- Positive: Team has momentum
- Negative: Team losing momentum
- Zero: Neutral

Decay: 10% per play (recency bias - recent events matter more)
"""

from typing import Dict, Any, List, Tuple


class MomentumTracker:
    """
    Tracks game momentum for both teams.

    Momentum is built from discrete events (touchdowns, turnovers, big plays) and
    decays by 10% after each play to emphasize recency.

    Momentum affects:
    - Play outcomes: ±5% success rate modifier
    - Coach aggression: ±15% fourth down aggression modifier
    - Player confidence: Visible in performance
    """

    def __init__(self):
        """Initialize momentum tracker with neutral momentum."""
        self.home_momentum: float = 0.0
        self.away_momentum: float = 0.0
        self.decay_rate: float = 0.10  # 10% decay per play
        self.min_momentum: float = -20.0
        self.max_momentum: float = 20.0

        # Momentum event values (tuned for balanced gameplay)
        self.EVENT_VALUES = {
            'touchdown': 8.0,              # Scoring always shifts momentum
            'turnover_gain': 10.0,         # Team that GETS the turnover
            'turnover_loss': -10.0,        # Team that LOSES possession
            'big_play_gain': 5.0,          # 20+ yard play
            'fourth_down_conversion': 6.0, # Gutsy call that worked
            'fourth_down_stop': 7.0,       # Defense stops 4th down attempt
            'field_goal_made': 3.0,        # Points on the board
            'field_goal_blocked': 8.0,     # Big defensive play
            'sack': 3.0,                   # Pressure disrupts offense
            'three_and_out': -4.0,         # Offense fails to move ball
            'safety': 10.0,                # Rare, game-changing play
            'blocked_punt': 8.0,           # Special teams momentum swing
        }

    def add_event(self, team: str, event_type: str) -> None:
        """
        Add momentum from game event.

        Args:
            team: 'home' or 'away'
            event_type: Event type from EVENT_VALUES dict
        """
        value = self.EVENT_VALUES.get(event_type, 0.0)

        if value == 0.0:
            return  # Unknown event type, no momentum change

        if team == 'home':
            self.home_momentum += value
            self.home_momentum = self._clamp(self.home_momentum)
        elif team == 'away':
            self.away_momentum += value
            self.away_momentum = self._clamp(self.away_momentum)

    def decay(self) -> None:
        """
        Apply decay to both teams (10% per play).

        This creates recency bias - recent events matter more than past events.
        After 10 plays, an event has decayed to ~35% of original value.
        After 20 plays, an event has decayed to ~12% of original value.
        """
        self.home_momentum *= (1.0 - self.decay_rate)
        self.away_momentum *= (1.0 - self.decay_rate)

        # Zero out if very small (prevents floating point drift)
        if abs(self.home_momentum) < 0.1:
            self.home_momentum = 0.0
        if abs(self.away_momentum) < 0.1:
            self.away_momentum = 0.0

    def get_momentum(self, team: str) -> float:
        """
        Get current momentum for team.

        Args:
            team: 'home' or 'away'

        Returns:
            Momentum value (-20.0 to +20.0)
        """
        if team == 'home':
            return self.home_momentum
        elif team == 'away':
            return self.away_momentum
        else:
            return 0.0

    def get_momentum_modifier(self, team: str) -> float:
        """
        Convert momentum to performance modifier for play outcomes.

        Momentum range: -20 to +20
        Modifier range: 0.95 to 1.05 (±5%)

        Formula: 1.0 + (momentum / 400)
        - Momentum +20 → 1.05 (+5% boost)
        - Momentum 0 → 1.0 (neutral)
        - Momentum -20 → 0.95 (-5% penalty)

        Args:
            team: 'home' or 'away'

        Returns:
            Performance multiplier (0.95 to 1.05)
        """
        momentum = self.get_momentum(team)
        return 1.0 + (momentum / 400.0)

    def get_aggression_modifier(self, team: str) -> float:
        """
        Get coach aggression modifier based on momentum.

        Coaches are more aggressive with positive momentum, conservative with negative.

        Momentum range: -20 to +20
        Aggression modifier range: 0.85 to 1.15 (±15%)

        Formula: 1.0 + (momentum / 133.33)
        - Momentum +20 → 1.15 (+15% more aggressive)
        - Momentum 0 → 1.0 (neutral)
        - Momentum -20 → 0.85 (-15% less aggressive)

        Args:
            team: 'home' or 'away'

        Returns:
            Aggression multiplier (0.85 to 1.15)
        """
        momentum = self.get_momentum(team)
        return 1.0 + (momentum / 133.33)

    def get_momentum_level(self, team: str) -> str:
        """
        Get descriptive momentum level for display.

        Args:
            team: 'home' or 'away'

        Returns:
            Momentum level: 'Hot', 'Warm', 'Neutral', 'Cool', 'Cold'
        """
        momentum = self.get_momentum(team)

        if momentum >= 12.0:
            return 'Hot'
        elif momentum >= 6.0:
            return 'Warm'
        elif momentum > -6.0:
            return 'Neutral'
        elif momentum > -12.0:
            return 'Cool'
        else:
            return 'Cold'

    def get_summary(self) -> Dict[str, Any]:
        """
        Get momentum summary for box score display.

        Returns:
            Dict with momentum values, modifiers, and levels
        """
        return {
            'home_momentum': round(self.home_momentum, 1),
            'away_momentum': round(self.away_momentum, 1),
            'home_modifier': round(self.get_momentum_modifier('home'), 3),
            'away_modifier': round(self.get_momentum_modifier('away'), 3),
            'home_level': self.get_momentum_level('home'),
            'away_level': self.get_momentum_level('away'),
            'home_aggression': round(self.get_aggression_modifier('home'), 3),
            'away_aggression': round(self.get_aggression_modifier('away'), 3)
        }

    def reset(self) -> None:
        """Reset momentum to neutral (used for new games)."""
        self.home_momentum = 0.0
        self.away_momentum = 0.0

    def _clamp(self, value: float) -> float:
        """
        Clamp momentum to valid range.

        Args:
            value: Momentum value

        Returns:
            Clamped value (-20.0 to +20.0)
        """
        return max(self.min_momentum, min(self.max_momentum, value))