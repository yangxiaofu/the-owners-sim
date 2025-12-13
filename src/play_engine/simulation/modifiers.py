"""
Environmental and Situational Modifiers for Play Simulation.

Provides utilities for applying various modifiers to play parameters:
- Weather effects (rain, snow, heavy wind)
- Crowd noise effects (away team disadvantage)
- Momentum effects (hot/cold streaks)
- Clutch performance effects (pressure situations)
- Prevent defense effects

Part of play engine refactoring to consolidate duplicate modifier logic.
"""

from typing import Dict


class EnvironmentalModifiers:
    """
    Static utility class for applying environmental modifiers to play parameters.

    All methods are stateless and operate on parameter dictionaries.
    """

    # ============================================
    # Weather Modifiers
    # ============================================

    @staticmethod
    def apply_weather_to_run_params(
        avg_yards: float,
        variance: float,
        weather_condition: str
    ) -> tuple:
        """
        Apply weather modifiers to run play parameters.

        Weather effects on run plays:
        - Rain: -5% yards (wet conditions affect ball handling, footing)
        - Snow: -10% yards, +15% variance (slips and big plays)
        - Heavy wind: Minimal effect on run plays

        Args:
            avg_yards: Base average yards per carry
            variance: Base variance for yards distribution
            weather_condition: Weather condition string ("clear", "rain", "snow", "heavy_wind")

        Returns:
            Tuple of (modified_avg_yards, modified_variance)
        """
        modified_avg_yards = avg_yards
        modified_variance = variance

        if weather_condition == 'rain':
            modified_avg_yards *= 0.95  # -5% yards in rain
        elif weather_condition == 'snow':
            modified_avg_yards *= 0.90  # -10% yards in snow
            modified_variance *= 1.15   # More slips and big plays

        return modified_avg_yards, modified_variance

    @staticmethod
    def apply_weather_to_pass_params(params: Dict, weather_condition: str) -> Dict:
        """
        Apply weather modifiers to pass play parameters.

        Weather effects on pass plays (based on NFL research):
        - Rain: Wet ball reduces grip (-10% accuracy, -15% deep passes)
        - Snow: Visibility + wet ball (-15% accuracy, -25% deep passes)
        - Heavy Wind: Affects ball trajectory (-30% deep passes, +15% air yards variance)

        Args:
            params: Dictionary of pass play parameters (completion_rate, int_rate, avg_air_yards, etc.)
            weather_condition: Weather condition string

        Returns:
            Modified params dictionary
        """
        if weather_condition == "clear":
            return params

        modified_params = params.copy()

        # Determine if this is a deep pass based on avg_air_yards parameter
        avg_air_yards = modified_params.get('avg_air_yards', 8.0)
        is_deep_pass = avg_air_yards >= 15.0

        if weather_condition == "rain":
            # Wet ball reduces accuracy
            modified_params['completion_rate'] *= 0.90  # -10% overall
            if is_deep_pass:
                modified_params['completion_rate'] *= 0.85  # Additional -15% for deep passes
            modified_params['int_rate'] *= 1.05  # +5% more tipped balls become INTs

        elif weather_condition == "snow":
            # Visibility issues + wet ball
            modified_params['completion_rate'] *= 0.85  # -15% overall
            if is_deep_pass:
                modified_params['completion_rate'] *= 0.75  # Additional -25% for deep passes
            modified_params['int_rate'] *= 1.10  # +10% more interceptions
            modified_params['avg_air_yards'] *= 0.95  # QBs throw shorter in snow

        elif weather_condition == "heavy_wind":
            # Wind affects ball trajectory
            if is_deep_pass:
                modified_params['completion_rate'] *= 0.70  # -30% for deep passes
                modified_params['avg_air_yards'] *= 1.15   # Wind carries ball further (unpredictable)
            modified_params['int_rate'] *= 1.08  # +8% more interceptions (wind causes errors)

        # Clamp completion rate to realistic range (weather can't make it impossible)
        modified_params['completion_rate'] = max(modified_params['completion_rate'], 0.15)  # Min 15%

        return modified_params

    # ============================================
    # Crowd Noise Modifiers
    # ============================================

    @staticmethod
    def apply_crowd_noise_to_run_params(
        avg_yards: float,
        crowd_noise_level: int,
        is_away_team: bool
    ) -> float:
        """
        Apply crowd noise modifiers to run play parameters.

        Crowd noise has minimal effect on run plays (no audibles needed).
        Slight effect on snap timing for away team.

        Args:
            avg_yards: Base average yards per carry
            crowd_noise_level: Noise intensity (0-100)
            is_away_team: Whether offensive team is away team

        Returns:
            Modified average yards
        """
        if not is_away_team or crowd_noise_level == 0:
            return avg_yards

        # Crowd affects snap timing slightly
        noise_factor = crowd_noise_level / 100.0
        return avg_yards * (1.0 - noise_factor * 0.03)  # Up to -3% yards

    @staticmethod
    def apply_crowd_noise_to_pass_params(
        params: Dict,
        crowd_noise_level: int,
        is_away_team: bool
    ) -> Dict:
        """
        Apply crowd noise modifiers to pass play parameters.

        Crowd noise affects away team significantly:
        - Communication breakdowns increase false starts (handled in penalty engine)
        - QB audibles harder to hear - more sacks (confusion)
        - Cadence timing disrupted - lower completion rate

        Args:
            params: Dictionary of pass play parameters
            crowd_noise_level: Noise intensity (0-100)
            is_away_team: Whether offensive team is away team

        Returns:
            Modified params dictionary
        """
        if not is_away_team or crowd_noise_level == 0:
            return params

        modified_params = params.copy()

        # Scale effects based on crowd noise (0-100 scale)
        noise_factor = crowd_noise_level / 100.0  # 0.0 to 1.0

        # Away team communication issues
        modified_params['sack_rate'] *= (1.0 + noise_factor * 0.10)     # Up to +10% sacks
        modified_params['completion_rate'] *= (1.0 - noise_factor * 0.05)  # Up to -5% completion
        modified_params['pressure_rate'] *= (1.0 + noise_factor * 0.08)    # Up to +8% pressure

        return modified_params

    # ============================================
    # Momentum Modifiers
    # ============================================

    @staticmethod
    def apply_momentum_to_run_params(avg_yards: float, momentum_modifier: float) -> float:
        """
        Apply momentum modifiers to run play parameters.

        Momentum affects offensive running performance:
        - Positive momentum (+20 -> 1.05): +5% yards per carry
        - Negative momentum (-20 -> 0.95): -5% yards per carry

        Args:
            avg_yards: Base average yards per carry
            momentum_modifier: Momentum modifier (0.95 to 1.05)

        Returns:
            Modified average yards
        """
        if momentum_modifier == 1.0:
            return avg_yards

        return avg_yards * momentum_modifier

    @staticmethod
    def apply_momentum_to_pass_params(params: Dict, momentum_modifier: float) -> Dict:
        """
        Apply momentum modifiers to pass play parameters.

        Momentum affects offensive passing performance:
        - Positive momentum: +completion, fewer sacks/INTs
        - Negative momentum: -completion, more sacks/INTs

        Args:
            params: Dictionary of pass play parameters
            momentum_modifier: Momentum modifier (0.95 to 1.05)

        Returns:
            Modified params dictionary
        """
        if momentum_modifier == 1.0:
            return params

        modified_params = params.copy()

        modified_params['completion_rate'] *= momentum_modifier
        modified_params['sack_rate'] /= momentum_modifier  # Inverse for negative stats
        modified_params['int_rate'] /= momentum_modifier   # Inverse for negative stats

        # Clamp to realistic ranges
        modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
        modified_params['sack_rate'] = max(modified_params['sack_rate'], 0.01)
        modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        return modified_params

    # ============================================
    # Prevent Defense Modifiers
    # ============================================

    @staticmethod
    def apply_prevent_defense_to_run_params(
        avg_yards: float,
        variance: float,
        coverage_scheme: str
    ) -> tuple:
        """
        Apply prevent defense modifiers to run play parameters.

        Prevent defense is weak against the run:
        - Only 3-4 players in the box (everyone else in deep coverage)
        - Light box = easier running lanes, more explosive runs

        Args:
            avg_yards: Base average yards per carry
            variance: Base variance
            coverage_scheme: Defensive coverage scheme

        Returns:
            Tuple of (modified_avg_yards, modified_variance)
        """
        if coverage_scheme != "Prevent":
            return avg_yards, variance

        # Increase average yards per carry
        modified_avg_yards = avg_yards + 1.0  # +1.0 yards per carry

        # Increase variance (more explosive runs possible with light box)
        modified_variance = variance * 1.2  # +20% variance

        return modified_avg_yards, modified_variance

    @staticmethod
    def apply_prevent_defense_to_pass_params(params: Dict, coverage_scheme: str) -> Dict:
        """
        Apply prevent defense modifiers to pass play parameters.

        Prevent defense characteristics:
        - 3-man rush (weak pressure) - drastically lower sack rate
        - 6 DBs in soft zone - higher completion rate overall
        - Deep coverage prioritized - prevent deep passes

        Args:
            params: Dictionary of pass play parameters
            coverage_scheme: Defensive coverage scheme

        Returns:
            Modified params dictionary
        """
        if coverage_scheme != "Prevent":
            return params

        modified_params = params.copy()

        # Increase completion rate (easier to complete passes vs prevent)
        modified_params['completion_rate'] *= 1.20  # +20% completion

        # Drastically reduced sack rate (3-man rush can't generate pressure)
        modified_params['sack_rate'] *= 0.4  # -60% sacks

        # Clamp completion rate to realistic maximum
        modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)

        return modified_params

    # ============================================
    # Clutch Performance Modifiers
    # ============================================

    @staticmethod
    def apply_clutch_to_pass_params(
        params: Dict,
        clutch_factor: float,
        qb_composure: int = 75
    ) -> Dict:
        """
        Apply composure-based performance modifiers in clutch situations.

        Clutch situations (urgency >= 0.5):
        - 4th quarter, close game (score diff <= 7)
        - Final 2 minutes
        - Overtime

        Composure modifiers:
        - High composure (90+): Up to +10% in extreme clutch
        - Low composure (<60): Up to -15% in extreme clutch
        - Medium composure (60-89): Linear scaling

        Args:
            params: Dictionary of pass play parameters
            clutch_factor: Clutch pressure level (0.0-1.0)
            qb_composure: QB composure rating (0-100, default 75)

        Returns:
            Modified params dictionary
        """
        if clutch_factor < 0.5:
            return params  # Not a clutch situation

        modified_params = params.copy()

        # Calculate composure modifier based on QB's composure rating
        if qb_composure >= 90:
            # Elite composure: positive modifier in clutch
            composure_modifier = 1.0 + (clutch_factor - 0.5) * 0.20  # Up to +10% at urgency 1.0
        elif qb_composure < 60:
            # Poor composure: negative modifier in clutch
            composure_modifier = 1.0 - (clutch_factor - 0.5) * 0.30  # Up to -15% at urgency 1.0
        else:
            # Average composure: minimal effect, scales linearly
            composure_delta = (qb_composure - 75) / 30.0  # -0.5 to +0.47
            composure_modifier = 1.0 + composure_delta * (clutch_factor - 0.5) * 0.15

        # Apply composure modifier to key stats
        modified_params['completion_rate'] *= composure_modifier
        modified_params['int_rate'] /= composure_modifier  # Inverse: better composure = fewer INTs

        # Clamp to realistic ranges
        modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
        modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        return modified_params

    # ============================================
    # Performance Tracker (Hot/Cold Streaks)
    # ============================================

    @staticmethod
    def apply_performance_streak_to_run_params(
        offensive_modifier: float,
        performance_tracker,
        player_id: int
    ) -> float:
        """
        Apply hot/cold streak modifier to run play offensive modifier.

        Args:
            offensive_modifier: Current offensive modifier
            performance_tracker: PlayerPerformanceTracker instance
            player_id: Player ID to check streak for

        Returns:
            Modified offensive modifier
        """
        if performance_tracker is None or player_id is None:
            return offensive_modifier

        performance_modifier = performance_tracker.get_modifier(player_id)
        return offensive_modifier * performance_modifier  # 0.85 (ICE_COLD), 1.0 (NEUTRAL), or 1.15 (ON_FIRE)

    @staticmethod
    def apply_performance_streak_to_pass_params(
        params: Dict,
        performance_tracker,
        qb_id: int
    ) -> Dict:
        """
        Apply hot/cold streak modifier to pass play parameters.

        Args:
            params: Dictionary of pass play parameters
            performance_tracker: PlayerPerformanceTracker instance
            qb_id: QB player ID to check streak for

        Returns:
            Modified params dictionary
        """
        if performance_tracker is None or qb_id is None:
            return params

        modified_params = params.copy()
        performance_modifier = performance_tracker.get_modifier(qb_id)

        # Apply to completion rate (primary QB stat)
        modified_params['completion_rate'] *= performance_modifier
        # Inverse for negative stats (hot QBs throw fewer INTs)
        modified_params['int_rate'] /= performance_modifier

        # Clamp to realistic ranges
        modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
        modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        return modified_params