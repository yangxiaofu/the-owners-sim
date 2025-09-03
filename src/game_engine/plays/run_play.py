import random
from typing import Dict, List
from game_engine.plays.play_types import PlayType
from game_engine.plays.data_structures import PlayResult
from game_engine.plays.statistics_extractor import StatisticsExtractor, RunPlayData
from game_engine.field.field_state import FieldState
from game_engine.simulation.blocking.data_structures import RunPlayCall, BlockingResult
from game_engine.simulation.blocking.simulator import BlockingSimulator
from game_engine.simulation.blocking.strategies import RunBlockingStrategy
from game_engine.plays.run_plays import DetailedRunSimulator


class RunGameBalance:
    """
    Centralized configuration for run game balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect running game balance.
    Adjust these values to change how the running game plays:
    - Higher effectiveness weights favor certain factors
    - Tighter variance ranges create more consistent results
    - Stronger situational modifiers create more realistic game situations
    """
    
    # === CORE EFFECTIVENESS CALCULATION ===
    # How much each factor contributes to run success (must sum to 1.0)
    RB_EFFECTIVENESS_WEIGHT = 0.5      # How much RB attributes matter (0.0-1.0)
    BLOCKING_EFFECTIVENESS_WEIGHT = 0.5 # How much O-line vs D-line matters (0.0-1.0)
    
    # === VARIANCE AND RANDOMNESS ===
    # Base variance range applied to all runs
    BASE_VARIANCE_MIN = 0.7    # Minimum multiplier (0.7 = 30% reduction possible)
    BASE_VARIANCE_MAX = 1.0    # Base maximum before run-type variance kicks in
    VARIANCE_MULTIPLIER = 0.3  # How much run-type variance affects max (0.0-1.0)
    
    # === SITUATIONAL MODIFIERS ===
    # Down and distance effects
    THIRD_AND_SHORT_PENALTY = 0.85    # 3rd & short run penalty (defense expecting)
    FIRST_DOWN_BONUS = 1.05           # 1st down run bonus (more unpredictable)
    
    # Field position effects
    GOAL_LINE_COMPRESSION = 0.7       # Non-power runs near goal line penalty
    DEEP_TERRITORY_BONUS = 1.1        # Runs from own 20 or less bonus
    GOAL_LINE_THRESHOLD = 95          # Field position considered "goal line"
    DEEP_TERRITORY_THRESHOLD = 20     # Field position considered "deep territory"
    
    # === BREAKAWAY LOGIC ===
    BREAKAWAY_MIN_YARDS = 8           # Minimum yards needed for breakaway chance
    BREAKAWAY_BASE_CHANCE = 0.06      # Base breakaway probability (6%)
    BREAKAWAY_EXCESS_BONUS = 0.001    # Bonus per rating point above threshold (0.1%)
    BREAKAWAY_YARDS_MIN = 15          # Minimum bonus yards on breakaway
    BREAKAWAY_YARDS_MAX = 35          # Maximum bonus yards on breakaway
    
    # === OUTCOME DETERMINATION ===
    # Fumble logic
    FUMBLE_CHANCE_STUFFED = 0.03      # Fumble chance on stuffed runs (3%)
    FUMBLE_MAX_LOSS = -2              # Maximum loss on fumble
    
    # Touchdown logic  
    TOUCHDOWN_MIN_YARDS = 15          # Minimum yards to be eligible for TD
    TOUCHDOWN_CHANCE = 0.12           # TD chance on long runs (12%)
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense"""
        # Effectiveness weights should sum to 1.0
        total_weight = cls.RB_EFFECTIVENESS_WEIGHT + cls.BLOCKING_EFFECTIVENESS_WEIGHT
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Effectiveness weights must sum to 1.0, got {total_weight}")
        
        # Variance values should be reasonable
        if cls.BASE_VARIANCE_MIN >= cls.BASE_VARIANCE_MAX:
            raise ValueError("BASE_VARIANCE_MIN must be less than BASE_VARIANCE_MAX")
        
        # Probabilities should be between 0 and 1
        probabilities = [
            cls.BREAKAWAY_BASE_CHANCE, cls.FUMBLE_CHANCE_STUFFED, cls.TOUCHDOWN_CHANCE
        ]
        for prob in probabilities:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability {prob} must be between 0 and 1")


# Validate configuration on import
RunGameBalance.validate_configuration()


# Situational Matchup Matrix Configuration (KISS: Simple dictionary structure)
MATCHUP_MATRICES = {
    "power_run": {
        "rb_attributes": ["power", "vision"],
        "base_yards": 3.5,
        "ol_modifier": 1.3,
        "dl_modifier": 1.2,
        "variance": 0.8,
        "breakaway_threshold": 85
    },
    "outside_zone": {
        "rb_attributes": ["speed", "agility"],
        "base_yards": 3.0,
        "ol_modifier": 1.0,
        "dl_modifier": 0.8,
        "variance": 1.3,
        "breakaway_threshold": 80
    },
    "inside_zone": {
        "rb_attributes": ["vision", "agility"],
        "base_yards": 3.8,
        "ol_modifier": 1.1,
        "dl_modifier": 1.0,
        "variance": 1.0,
        "breakaway_threshold": 82
    },
    "draw_play": {
        "rb_attributes": ["vision", "elusiveness"],
        "base_yards": 4.5,
        "ol_modifier": 0.9,
        "dl_modifier": 0.7,
        "variance": 1.4,
        "breakaway_threshold": 78
    },
    "goal_line_power": {
        "rb_attributes": ["power", "strength"],
        "base_yards": 1.5,
        "ol_modifier": 1.4,
        "dl_modifier": 1.3,
        "variance": 0.6,
        "breakaway_threshold": 95
    }
}


class RunPlay(PlayType):
    """Handles all running play simulation logic"""
    
    def __init__(self):
        self.detailed_run_simulator = DetailedRunSimulator()
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a running play using selected personnel"""
        
        # Ensure position mapping is populated for realistic player names
        if personnel.individual_players:
            personnel.auto_populate_position_map()
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Apply formation modifier
        formation_modifier = self._get_formation_modifier(
            personnel.formation, personnel.defensive_call, "run"
        )
        
        # Get detailed blocking results for statistics
        blocking_results = self._simulate_blocking_matchups(personnel, offense_ratings, defense_ratings, field_state)
        
        # Use situational matchup matrix algorithm with blocking context
        outcome, yards_gained, expected_yards = self._calculate_yards_from_matchup_matrix_with_stats(
            offense_ratings, defense_ratings, personnel, formation_modifier, field_state, blocking_results
        )
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("run", outcome)
        is_turnover = outcome == "fumble"
        is_score = outcome == "touchdown"
        score_points = self._calculate_points(outcome)
        
        # Extract comprehensive statistics
        extractor = StatisticsExtractor()
        run_data = RunPlayData(
            rb_effectiveness=self._calculate_rb_effectiveness_for_run_type(
                personnel.rb_on_field, self._determine_run_type(personnel.formation, field_state)
            ),
            blocking_results=blocking_results,
            yards_gained=yards_gained,
            expected_yards=expected_yards,
            outcome=outcome
        )
        
        play_stats = extractor.extract_run_statistics(personnel, run_data)
        
        # Create play result
        play_result = PlayResult(
            play_type="run",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points,
            
            # Comprehensive statistics
            rusher=play_stats.get('rusher'),
            tackler=play_stats.get('tackler'),
            assist_tackler=play_stats.get('assist_tackler'),
            pancakes_by=play_stats.get('pancakes_by', []),
            key_blocks_by=play_stats.get('key_blocks_by', []),
            missed_tackles_by=play_stats.get('missed_tackles_by', []),
            broken_tackles=play_stats.get('broken_tackles', 0),
            tackles_for_loss_by=play_stats.get('tackles_for_loss_by', []),
            protection_breakdowns=play_stats.get('protection_breakdowns', []),
            perfect_protection=play_stats.get('perfect_protection', False)
        )
        
        # Populate situational context from field state
        self._populate_situational_context(play_result, field_state)
        
        return play_result
    
    def _determine_run_type(self, formation: str, field_state: FieldState) -> str:
        """SOLID: Single responsibility - classify run type based on formation and situation"""
        
        # Goal line situations (YAGNI: only basic goal line logic)
        if field_state.is_goal_line() and field_state.is_short_yardage():
            return "goal_line_power"
        
        # SOLID: Open/Closed principle - new formations added via configuration
        formation_to_run_type = {
            "I_formation": "power_run",
            "goal_line": "goal_line_power",
            "singleback": "inside_zone",
            "shotgun": "draw_play",
            "pistol": "inside_zone"
        }
        
        return formation_to_run_type.get(formation, "inside_zone")  # Safe default
    
    def _calculate_rb_effectiveness_for_run_type(self, rb, run_type: str) -> float:
        """SOLID: Single responsibility - calculate RB effectiveness for specific run type"""
        
        if not rb:
            return 0.5  # Default average effectiveness
        
        # SOLID: Dependency inversion - depends on RB interface, not implementation
        matrix = MATCHUP_MATRICES[run_type]
        total_rating = 0
        
        # KISS: Simple average calculation of relevant attributes
        for attribute in matrix["rb_attributes"]:
            rating = getattr(rb, attribute, 50)  # Safe attribute access with fallback
            total_rating += rating
        
        avg_rating = total_rating / len(matrix["rb_attributes"])
        return avg_rating / 100  # Normalize to 0-1 range
    
    def _simulate_blocking_matchups(self, personnel, offense_ratings: Dict, defense_ratings: Dict, field_state: FieldState) -> List[BlockingResult]:
        """Simulate detailed blocking matchups for statistics extraction"""
        
        # Create simplified blocker and defender mappings
        blockers = {
            "LT": offense_ratings.get('ol', 50) + random.randint(-5, 5),
            "LG": offense_ratings.get('ol', 50) + random.randint(-5, 5),
            "C": offense_ratings.get('ol', 50) + random.randint(-5, 5),
            "RG": offense_ratings.get('ol', 50) + random.randint(-5, 5),
            "RT": offense_ratings.get('ol', 50) + random.randint(-5, 5)
        }
        
        defenders = {
            "LE": defense_ratings.get('dl', 50) + random.randint(-5, 5),
            "DT": defense_ratings.get('dl', 50) + random.randint(-5, 5),
            "RE": defense_ratings.get('dl', 50) + random.randint(-5, 5),
            "MLB": defense_ratings.get('lb', 50) + random.randint(-5, 5)
        }
        
        # Create blocking context
        from ..simulation.blocking.strategies import BlockingContext
        
        run_type = self._determine_run_type(personnel.formation, field_state)
        context = BlockingContext(
            blocking_type="run_blocking",
            play_details={"play_type": run_type, "direction": "center"},
            situation={
                "down": field_state.down,
                "yards_to_go": field_state.yards_to_go,
                "field_position": field_state.field_position
            }
        )
        
        # Simulate blocking matchups
        blocking_simulator = BlockingSimulator(RunBlockingStrategy())
        return blocking_simulator.simulate_matchups(blockers, defenders, context)
    
    def _calculate_yards_from_matchup_matrix_with_stats(self, offense_ratings: Dict, defense_ratings: Dict,
                                           personnel, formation_modifier: float, field_state: FieldState, 
                                           blocking_results: List[BlockingResult]) -> tuple[str, int, float]:
        """SOLID: Single responsibility - main yards calculation using matchup matrix with statistics tracking"""
        
        # Step 1: Determine run type based on situation
        run_type = self._determine_run_type(personnel.formation, field_state)
        matrix = MATCHUP_MATRICES[run_type]
        
        # Step 2: Calculate RB effectiveness for this run type
        rb_effectiveness = self._calculate_rb_effectiveness_for_run_type(
            personnel.rb_on_field, run_type
        )
        
        # Step 3: Calculate blocking effectiveness using actual blocking results
        blocking_effectiveness = self._calculate_blocking_effectiveness_from_results(blocking_results, matrix)
        
        # Step 4: Combine factors (KISS: simple weighted average)
        combined_effectiveness = (rb_effectiveness * 0.5 + blocking_effectiveness * 0.5) * formation_modifier
        
        # Step 5: Apply to base yards with run-type specific variance
        base_yards = matrix["base_yards"] * combined_effectiveness
        expected_yards = base_yards  # Store for statistics
        
        variance = random.uniform(
            RunGameBalance.BASE_VARIANCE_MIN, 
            RunGameBalance.BASE_VARIANCE_MAX + matrix["variance"] * RunGameBalance.VARIANCE_MULTIPLIER
        )
        final_yards = base_yards * variance
        
        # Step 6: Apply situational modifiers
        final_yards = self._apply_situational_modifiers(final_yards, field_state, run_type)
        
        # Step 7: Check for breakaway potential (YAGNI: simple logic)
        if self._check_breakaway_potential(personnel.rb_on_field, matrix, final_yards):
            final_yards += random.uniform(
                RunGameBalance.BREAKAWAY_YARDS_MIN, 
                RunGameBalance.BREAKAWAY_YARDS_MAX
            )
        
        # Step 8: Determine outcome and return
        yards = max(-5, int(final_yards))  # Allow negative yards for TFL
        outcome, final_yards = self._determine_play_outcome(yards, run_type, field_state)
        return outcome, final_yards, expected_yards
    
    def _calculate_yards_from_matchup_matrix(self, offense_ratings: Dict, defense_ratings: Dict,
                                           personnel, formation_modifier: float, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - main yards calculation using matchup matrix"""
        
        # Create simplified blocking results for backward compatibility
        blocking_results = []
        outcome, yards, _ = self._calculate_yards_from_matchup_matrix_with_stats(
            offense_ratings, defense_ratings, personnel, formation_modifier, field_state, blocking_results
        )
        return outcome, yards
    
    def _calculate_blocking_effectiveness_from_results(self, blocking_results: List[BlockingResult], matrix: Dict) -> float:
        """Calculate blocking effectiveness from actual blocking simulation results"""
        
        if not blocking_results:
            return 0.5  # Default average effectiveness
        
        # Calculate overall blocking grade
        total_weighted_success = 0.0
        total_weight = 0.0
        
        for result in blocking_results:
            weight = result.impact_factor
            success_value = 1.0 if result.success else 0.0
            
            total_weighted_success += success_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        overall_grade = total_weighted_success / total_weight
        
        # Apply run-type specific modifiers
        return overall_grade * matrix.get("ol_modifier", 1.0)
    
    def _apply_situational_modifiers(self, base_yards: float, field_state: FieldState, run_type: str) -> float:
        """SOLID: Single responsibility - apply game situation modifiers"""
        
        modified_yards = base_yards
        
        # YAGNI: Only essential situational modifiers
        # Down and distance modifiers
        if field_state.down == 3 and field_state.yards_to_go <= 2:
            modified_yards *= RunGameBalance.THIRD_AND_SHORT_PENALTY  # 3rd and short - defense expecting run
        elif field_state.down == 1:
            modified_yards *= RunGameBalance.FIRST_DOWN_BONUS  # 1st down - more unpredictable
        
        # Field position modifiers
        if field_state.field_position >= RunGameBalance.GOAL_LINE_THRESHOLD:
            if run_type != "goal_line_power":
                modified_yards *= RunGameBalance.GOAL_LINE_COMPRESSION  # Compressed field
        elif field_state.field_position <= RunGameBalance.DEEP_TERRITORY_THRESHOLD:
            modified_yards *= RunGameBalance.DEEP_TERRITORY_BONUS  # Defense playing it safe
        
        return modified_yards
    
    def _check_breakaway_potential(self, rb, matrix: Dict, current_yards: float) -> bool:
        """YAGNI: Simple breakaway logic based on RB attributes and run type"""
        
        if not rb or current_yards < RunGameBalance.BREAKAWAY_MIN_YARDS:
            return False
        
        # Calculate breakaway ability based on run-type specific attributes
        total_rating = 0
        for attribute in matrix["rb_attributes"]:
            rating = getattr(rb, attribute, 50)
            total_rating += rating
        
        avg_rating = total_rating / len(matrix["rb_attributes"])
        
        # Simple threshold check
        if avg_rating >= matrix["breakaway_threshold"]:
            # Base chance, with bonus for exceeding threshold
            excess = avg_rating - matrix["breakaway_threshold"]
            breakaway_chance = RunGameBalance.BREAKAWAY_BASE_CHANCE + (excess * RunGameBalance.BREAKAWAY_EXCESS_BONUS)
            return random.random() < breakaway_chance
        
        return False
    
    def _determine_play_outcome(self, yards: int, run_type: str, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - determine final play outcome"""
        
        # Fumble check (YAGNI: simple logic)
        if yards <= 0 and random.random() < RunGameBalance.FUMBLE_CHANCE_STUFFED:
            return "fumble", max(RunGameBalance.FUMBLE_MAX_LOSS, yards)
        
        # Touchdown check - use field position awareness
        current_position = field_state.field_position
        if yards >= RunGameBalance.TOUCHDOWN_MIN_YARDS and random.random() < RunGameBalance.TOUCHDOWN_CHANCE:
            # Return final field position (100) for touchdown, not gained yards
            final_position = min(100, current_position + yards)
            return "touchdown", final_position
        
        # Loss vs gain determination
        if yards < 0:
            return "loss", yards
        else:
            return "gain", yards
    
    def _simulate_detailed_run(self, offense: Dict, defense: Dict) -> tuple[str, int]:
        """Legacy detailed simulation - kept for backward compatibility"""
        play_call = RunPlayCall.default_inside_run()
        detailed_result = self.detailed_run_simulator.simulate_run(offense, defense, play_call)
        return detailed_result.outcome, detailed_result.yards_gained
    
