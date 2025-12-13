"""
Tackler Selection - Parameterized tackler selection for play simulation.

Provides utilities for selecting which defenders make tackles based on:
- Position-weighted probabilities
- Yards gained (affects assisted tackle probability)
- Play type (run vs pass has different distributions)

Part of play engine refactoring to consolidate duplicate tackler selection logic.
"""

import random
from typing import List, Tuple, Dict


class TacklerSelector:
    """
    Utility class for selecting tacklers with position-weighted probabilities.

    Position weights differ by play type to reflect NFL reality:
    - Run plays: Linebackers dominate (65%)
    - Pass plays: Defensive backs dominate (70%)
    """

    # Position weight distributions by play type
    # Values represent share of tackles for each position group

    RUN_PLAY_WEIGHTS = {
        'linebacker': 0.65,       # Primary run stoppers
        'safety': 0.25,           # Second level, deep plays
        'defensive_line': 0.08,   # TFLs, stuff plays only
        'cornerback': 0.02,       # Rare, mostly edge runs
    }

    PASS_PLAY_WEIGHTS = {
        'defensive_back': 0.70,   # In coverage, closest to catch point
        'linebacker': 0.25,       # Zone drops, underneath coverage
        'defensive_line': 0.05,   # Rare, short completions or screens
    }

    # Position mappings for categorization
    LINEBACKER_POSITIONS = frozenset([
        'mike_linebacker', 'sam_linebacker', 'will_linebacker', 'linebacker',
        'inside_linebacker', 'outside_linebacker', 'ilb', 'olb'
    ])

    SAFETY_POSITIONS = frozenset([
        'safety', 'free_safety', 'strong_safety', 'fs', 'ss'
    ])

    DEFENSIVE_LINE_POSITIONS = frozenset([
        'defensive_end', 'defensive_tackle', 'nose_tackle', 'de', 'dt', 'nt'
    ])

    CORNERBACK_POSITIONS = frozenset([
        'cornerback', 'cb', 'nickel_cornerback', 'ncb'
    ])

    DEFENSIVE_BACK_POSITIONS = frozenset([
        'cornerback', 'cb', 'safety', 'free_safety', 'strong_safety',
        'fs', 'ss', 'nickel_cornerback', 'ncb'
    ])

    # ============================================
    # Main Selection Methods
    # ============================================

    @classmethod
    def select_run_tacklers(
        cls,
        yards_gained: int,
        potential_tacklers: List,
        long_run_threshold: int = 5,
        assisted_tackle_prob: float = 0.6
    ) -> List[Tuple]:
        """
        Select tacklers for run plays using NFL-realistic position weights.

        Args:
            yards_gained: Yards gained on the play
            potential_tacklers: List of defensive players who could make tackles
            long_run_threshold: Yards threshold for considering assisted tackles
            assisted_tackle_prob: Probability of assisted tackle on long runs

        Returns:
            List of (player, is_assisted) tuples
        """
        return cls._select_tacklers(
            yards_gained=yards_gained,
            potential_tacklers=potential_tacklers,
            weight_config=cls.RUN_PLAY_WEIGHTS,
            categorize_func=cls._categorize_for_run,
            long_threshold=long_run_threshold,
            assisted_prob=assisted_tackle_prob
        )

    @classmethod
    def select_pass_tacklers(
        cls,
        yac_yards: int,
        potential_tacklers: List,
        long_yac_threshold: int = 8,
        assisted_tackle_prob: float = 0.6
    ) -> List[Tuple]:
        """
        Select tacklers for pass plays (after catch) using NFL-realistic position weights.

        Args:
            yac_yards: Yards after catch gained on the play
            potential_tacklers: List of defensive players who could make tackles
            long_yac_threshold: YAC threshold for considering assisted tackles
            assisted_tackle_prob: Probability of assisted tackle on long YAC

        Returns:
            List of (player, is_assisted) tuples
        """
        return cls._select_tacklers(
            yards_gained=yac_yards,
            potential_tacklers=potential_tacklers,
            weight_config=cls.PASS_PLAY_WEIGHTS,
            categorize_func=cls._categorize_for_pass,
            long_threshold=long_yac_threshold,
            assisted_prob=assisted_tackle_prob
        )

    # ============================================
    # Core Selection Logic
    # ============================================

    @classmethod
    def _select_tacklers(
        cls,
        yards_gained: int,
        potential_tacklers: List,
        weight_config: Dict[str, float],
        categorize_func,
        long_threshold: int,
        assisted_prob: float
    ) -> List[Tuple]:
        """
        Core tackler selection logic with configurable weights.

        Args:
            yards_gained: Yards gained on the play
            potential_tacklers: List of defensive players
            weight_config: Position category to weight mapping
            categorize_func: Function to categorize players by position
            long_threshold: Yards threshold for assisted tackles
            assisted_prob: Probability of assisted tackle

        Returns:
            List of (player, is_assisted) tuples
        """
        if not potential_tacklers:
            return []

        tacklers = []

        # More yards = more likely to have assisted tackles
        if yards_gained >= long_threshold:
            # Long play: likely 1 primary tackler + 1 assisted
            primary_tackler = cls._select_by_weight(potential_tacklers, weight_config, categorize_func)
            tacklers.append((primary_tackler, False))

            # Chance of assisted tackle
            if random.random() < assisted_prob:
                remaining = [p for p in potential_tacklers if p != primary_tackler]
                if remaining:
                    assisted_tackler = cls._select_by_weight(remaining, weight_config, categorize_func)
                    tacklers.append((assisted_tackler, True))
        else:
            # Short play: likely just 1 tackler
            primary_tackler = cls._select_by_weight(potential_tacklers, weight_config, categorize_func)
            tacklers.append((primary_tackler, False))

        return tacklers

    @classmethod
    def _select_by_weight(
        cls,
        potential_tacklers: List,
        weight_config: Dict[str, float],
        categorize_func
    ):
        """
        Select a single tackler using position-weighted probabilities.

        Args:
            potential_tacklers: List of defensive players
            weight_config: Position category to weight mapping
            categorize_func: Function to categorize players

        Returns:
            Selected player
        """
        if not potential_tacklers:
            return None

        # Categorize players
        categorized = categorize_func(potential_tacklers)

        # Build weighted selection pool
        candidates = []
        weights = []

        for category, category_weight in weight_config.items():
            players_in_category = categorized.get(category, [])
            if players_in_category:
                candidates.extend(players_in_category)
                # Distribute category weight evenly among players in category
                per_player_weight = category_weight / len(players_in_category)
                weights.extend([per_player_weight] * len(players_in_category))

        # Fallback to uniform if no categorized players
        if not candidates:
            return random.choice(potential_tacklers)

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(potential_tacklers)

        normalized_weights = [w / total_weight for w in weights]

        # Use weighted random selection
        return random.choices(candidates, weights=normalized_weights, k=1)[0]

    # ============================================
    # Position Categorization
    # ============================================

    @classmethod
    def _categorize_for_run(cls, players: List) -> Dict[str, List]:
        """
        Categorize players for run play tackle distribution.

        Categories: linebacker, safety, defensive_line, cornerback
        """
        categorized = {
            'linebacker': [],
            'safety': [],
            'defensive_line': [],
            'cornerback': [],
        }

        for player in players:
            pos = player.primary_position.lower()

            if pos in cls.LINEBACKER_POSITIONS:
                categorized['linebacker'].append(player)
            elif pos in cls.SAFETY_POSITIONS:
                categorized['safety'].append(player)
            elif pos in cls.DEFENSIVE_LINE_POSITIONS:
                categorized['defensive_line'].append(player)
            elif pos in cls.CORNERBACK_POSITIONS:
                categorized['cornerback'].append(player)

        return categorized

    @classmethod
    def _categorize_for_pass(cls, players: List) -> Dict[str, List]:
        """
        Categorize players for pass play tackle distribution.

        Categories: defensive_back, linebacker, defensive_line
        """
        categorized = {
            'defensive_back': [],
            'linebacker': [],
            'defensive_line': [],
        }

        for player in players:
            pos = player.primary_position.lower()

            if pos in cls.DEFENSIVE_BACK_POSITIONS:
                categorized['defensive_back'].append(player)
            elif pos in cls.LINEBACKER_POSITIONS:
                categorized['linebacker'].append(player)
            elif pos in cls.DEFENSIVE_LINE_POSITIONS:
                categorized['defensive_line'].append(player)

        return categorized