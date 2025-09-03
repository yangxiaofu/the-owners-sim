import random
from typing import Dict
from game_engine.plays.play_types import PlayType
from game_engine.plays.data_structures import PlayResult
from game_engine.plays.statistics_extractor import StatisticsExtractor, PassPlayData
from game_engine.field.field_state import FieldState


class PassGameBalance:
    """
    Centralized configuration for pass game balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect passing game balance.
    Adjust these values to change how the passing game plays:
    - Higher effectiveness weights favor certain factors
    - Stronger situational modifiers create more realistic game situations
    - Sack rates and outcome probabilities affect risk/reward balance
    """
    
    # === CORE EFFECTIVENESS CALCULATION ===
    # How much each factor contributes to pass success (must sum to 1.0)
    # Adjusted to be less harsh - NFL passing is more successful than our algorithm was producing
    QB_EFFECTIVENESS_WEIGHT = 0.35     # How much QB attributes matter (0.0-1.0)
    WR_EFFECTIVENESS_WEIGHT = 0.25     # How much WR attributes matter (0.0-1.0)
    PROTECTION_WEIGHT = 0.25           # How much pass protection matters (0.0-1.0)
    COVERAGE_WEIGHT = 0.15             # How much DB coverage matters (0.0-1.0)
    
    # === SACK CALCULATION WEIGHTS ===
    OL_PROTECTION_WEIGHT = 0.7         # O-line is primary protection
    RB_PROTECTION_WEIGHT = 0.2         # RB pass protection contribution  
    TE_PROTECTION_WEIGHT = 0.1         # TE pass protection contribution
    
    DL_RUSH_WEIGHT = 0.8               # D-line primary pass rush
    LB_BLITZ_WEIGHT = 0.15             # LB blitz contribution
    DB_BLITZ_WEIGHT = 0.05             # DB blitz contribution
    
    # === SACK PROBABILITY SETTINGS ===
    BASE_SACK_RATE = 0.13              # 13% baseline sack rate (increased from 11%)
    MAX_SACK_RATE = 0.40               # Cap at 40% even with terrible protection
    BLITZ_MULTIPLIER = 1.4             # Blitz increases pass rush by 40%
    BASE_LB_RUSH = 0.3                 # LB contribution when not blitzing
    
    # === SITUATIONAL MODIFIERS ===
    # Down and distance effects
    THIRD_AND_LONG_SACK_MULTIPLIER = 1.3    # 3rd & long increases sack risk
    FIRST_DOWN_SACK_REDUCTION = 0.9         # 1st down reduces sack risk
    THIRD_AND_LONG_COMPLETION_PENALTY = 0.9  # 3rd & long harder completions
    FIRST_DOWN_COMPLETION_BONUS = 1.05       # 1st down easier completions
    
    # Field position effects
    RED_ZONE_SACK_REDUCTION = 0.8           # Red zone reduces sack risk (shorter routes)
    DEEP_TERRITORY_SACK_INCREASE = 1.1      # Deep territory increases sack risk
    RED_ZONE_COMPLETION_BONUS = 1.15        # ULTRA-THINK: Increased from 1.1 to 1.15 for better red zone performance
    GOAL_LINE_THRESHOLD = 80                # ULTRA-THINK: Changed from 95 to 80 to match NFL red zone definition (80-95)
    DEEP_TERRITORY_THRESHOLD = 20           # Field position considered "deep territory"
    
    # QB mobility factor
    QB_MOBILITY_SACK_REDUCTION = 0.002      # Per point of mobility above 50
    
    # === SACK YARDAGE ===
    BASE_SACK_YARDS = -6                    # Average sack yardage
    MIN_SACK_YARDS = -15                    # Maximum loss on sack
    MAX_SACK_YARDS = -1                     # Minimum loss on sack  
    SACK_YARDS_VARIANCE = 4                 # Variance in sack yardage
    
    # === OUTCOME PROBABILITIES ===
    BASE_INT_RATE = 0.028                   # 2.8% base interception rate (increased from 2.2%)
    BASE_TD_RATE = 0.02                     # 2.0% base touchdown rate (ULTRA-THINK: Final reduction from 2.5% to achieve NFL 4.5% target)
    TD_MIN_YARDS = 12                       # Minimum yards to be eligible for TD (reduced from 15)
    
    # === YARDS AFTER CATCH ===
    YAC_MULTIPLIER = 1.0                    # How much of total yards is YAC (increased from 0.75)
    SPEED_YAC_BONUS = 0.15                  # Bonus for high-speed receivers
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense"""
        # Effectiveness weights should sum to 1.0
        total_weight = (cls.QB_EFFECTIVENESS_WEIGHT + cls.WR_EFFECTIVENESS_WEIGHT + 
                       cls.PROTECTION_WEIGHT + cls.COVERAGE_WEIGHT)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Effectiveness weights must sum to 1.0, got {total_weight}")
        
        # Protection weights should sum to 1.0
        total_protection = (cls.OL_PROTECTION_WEIGHT + cls.RB_PROTECTION_WEIGHT + 
                           cls.TE_PROTECTION_WEIGHT)
        if abs(total_protection - 1.0) > 0.001:
            raise ValueError(f"Protection weights must sum to 1.0, got {total_protection}")
        
        # Probabilities should be between 0 and 1
        probabilities = [cls.BASE_SACK_RATE, cls.BASE_INT_RATE, cls.BASE_TD_RATE]
        for prob in probabilities:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability {prob} must be between 0 and 1")


# Validate configuration on import
PassGameBalance.validate_configuration()


# Route Concept Matchup Matrix Configuration (KISS: Simple dictionary structure)
ROUTE_CONCEPT_MATRICES = {
    "quick_game": {
        "qb_attributes": ["accuracy", "release_time"],
        "wr_attributes": ["route_running", "hands"], 
        "base_completion": 0.75,  # ULTRA-THINK: Reduced from 0.78 for formation variety balance
        "base_yards": 8.5,  # Increased from 7.0 to boost YPA
        "time_to_throw": 2.1,  # Seconds - quick release
        "vs_man_modifier": 1.2,    # Good vs man coverage
        "vs_zone_modifier": 0.9,   # Harder vs zone
        "vs_blitz_modifier": 1.4,  # Excellent vs blitz
        "vs_prevent_modifier": 1.1,
        "variance": 0.6
    },
    "intermediate": {
        "qb_attributes": ["accuracy", "decision_making"],
        "wr_attributes": ["route_running", "hands"],
        "base_completion": 0.68,  # ULTRA-THINK: Increased from 0.65 for formation variety
        "base_yards": 16.0,  # Increased from 14.0
        "time_to_throw": 3.2,  # Standard development time
        "vs_man_modifier": 1.0,
        "vs_zone_modifier": 1.3,   # Good vs zone coverage
        "vs_blitz_modifier": 0.8,
        "vs_prevent_modifier": 1.2,
        "variance": 0.8
    },
    "vertical": {
        "qb_attributes": ["arm_strength", "accuracy"],
        "wr_attributes": ["speed", "hands"],
        "base_completion": 0.45,
        "base_yards": 25.0,  # Increased from 22.0
        "time_to_throw": 4.1,  # Long development - high sack risk
        "vs_man_modifier": 1.4,    # Excellent vs man coverage
        "vs_zone_modifier": 0.7,
        "vs_blitz_modifier": 0.6,  # Poor vs blitz
        "vs_prevent_modifier": 0.5,
        "variance": 1.4
    },
    "screens": {
        "qb_attributes": ["decision_making", "release_time"],
        "wr_attributes": ["speed", "vision"], 
        "rb_attributes": ["vision", "speed"],  # RBs involved in screens
        "base_completion": 0.82,  # ULTRA-THINK: Increased from 0.80 for formation variety
        "base_yards": 9.5,  # Increased from 8.0
        "time_to_throw": 1.8,  # Very quick - beats rush
        "vs_man_modifier": 1.1,
        "vs_zone_modifier": 1.0,
        "vs_blitz_modifier": 1.6,  # Excellent vs blitz
        "vs_prevent_modifier": 1.3,
        "variance": 1.2
    },
    "play_action": {
        "qb_attributes": ["arm_strength", "play_action"],
        "wr_attributes": ["speed", "route_running"],
        "base_completion": 0.58,  # ULTRA-THINK: Increased from 0.55 for formation variety
        "base_yards": 20.0,  # Increased from 18.0
        "time_to_throw": 4.8,  # Longest - fake handoff + development
        "vs_man_modifier": 1.2,
        "vs_zone_modifier": 1.1,
        "vs_blitz_modifier": 0.4,  # Terrible vs blitz
        "vs_prevent_modifier": 0.8,
        "variance": 1.1
    }
}


class PassPlay(PlayType):
    """Handles all passing play simulation logic"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a passing play using selected personnel"""
        
        # Ensure position mapping is populated for realistic player names
        if personnel.individual_players:
            personnel.auto_populate_position_map()
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Apply formation modifier
        formation_modifier = self._get_formation_modifier(
            personnel.formation, personnel.defensive_call, "pass"
        )
        
        # Store simulation data for statistics extraction
        simulation_data = {}
        
        outcome, yards_gained = self._calculate_yards_from_route_matchup_matrix_with_stats(
            offense_ratings, defense_ratings, personnel, formation_modifier, field_state, simulation_data
        )
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("pass", outcome)
        is_turnover = outcome == "interception"
        is_score = outcome == "touchdown"
        score_points = self._calculate_points(outcome)
        
        # Extract comprehensive statistics
        extractor = StatisticsExtractor()
        pass_data = PassPlayData(
            qb_effectiveness=simulation_data.get('qb_effectiveness', 0.0),
            wr_effectiveness=simulation_data.get('wr_effectiveness', 0.0),
            protection_effectiveness=simulation_data.get('protection_effectiveness', 0.0),
            coverage_effectiveness=simulation_data.get('coverage_effectiveness', 0.0),
            rush_advantage=simulation_data.get('rush_advantage', 0.0),
            coverage_modifier=simulation_data.get('coverage_modifier', 1.0),
            route_concept=simulation_data.get('route_concept', 'intermediate'),
            coverage_type=simulation_data.get('coverage_type', 'zone'),
            final_completion=simulation_data.get('final_completion', 0.0),
            outcome=outcome
        )
        
        play_stats = extractor.extract_pass_statistics(personnel, pass_data)
        
        # Create play result
        play_result = PlayResult(
            play_type="pass",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points,
            
            # Comprehensive statistics
            quarterback=play_stats.get('quarterback'),
            receiver=play_stats.get('receiver'),
            pass_rusher=play_stats.get('pass_rusher'),
            coverage_defender=play_stats.get('coverage_defender'),
            passes_defended_by=play_stats.get('passes_defended_by', []),
            quarterback_hits_by=play_stats.get('quarterback_hits_by', []),
            quarterback_hurries_by=play_stats.get('quarterback_hurries_by', []),
            protection_breakdowns=play_stats.get('protection_breakdowns', []),
            clean_pocket=play_stats.get('clean_pocket', False),
            perfect_protection=play_stats.get('perfect_protection', False),
            pressure_applied=play_stats.get('pressure_applied', False),
            coverage_beaten=play_stats.get('coverage_beaten', False),
            interceptions_by=play_stats.get('interceptions_by')
        )
        
        # Populate situational context from field state
        self._populate_situational_context(play_result, field_state)
        
        return play_result
    
    def _determine_route_concept(self, formation: str, field_state: FieldState) -> str:
        """SOLID: Single responsibility - classify route concept based on formation and situation"""
        
        # Goal line situations (YAGNI: only basic goal line logic)
        if field_state.is_goal_line():
            return "quick_game"
        
        # Down and distance logic (situational awareness)
        if field_state.down == 3 and field_state.yards_to_go > 7:  # 3rd and long
            return "vertical"
        elif field_state.down == 3 and field_state.yards_to_go <= 3:  # 3rd and short
            return "quick_game"
        
        # SOLID: Open/Closed principle - new formations added via configuration
        formation_to_route_concept = {
            "shotgun": "quick_game",
            "shotgun_spread": "vertical", 
            "I_formation": "play_action",
            "singleback": "intermediate",
            "pistol": "intermediate",
            "goal_line": "quick_game"
        }
        
        return formation_to_route_concept.get(formation, "intermediate")  # Safe default
    
    def _determine_defensive_coverage(self, defensive_call: str, personnel) -> str:
        """SOLID: Single responsibility - determine coverage type based on defensive call"""
        
        # Coverage mapping based on defensive call
        coverage_mapping = {
            "man_coverage": "man",
            "zone_coverage": "zone", 
            "blitz": "blitz",
            "prevent": "prevent",
            "nickel_pass": "zone",
            "dime_pass": "man",
            "base_defense": "zone"
        }
        
        return coverage_mapping.get(defensive_call, "zone")  # Safe default
    
    def _calculate_sack_probability_with_stats(self, offense_ratings: Dict, defense_ratings: Dict, 
                                   personnel, field_state: FieldState, route_concept: str) -> tuple[tuple[str, int], float]:
        """SOLID: Single responsibility - calculate sack probability before route development with stats tracking"""
        
        # Step 1: Get pass protection strength
        ol_rating = offense_ratings.get('ol', 50)
        rb_protection = self._get_rb_pass_protection(personnel.rb_on_field)
        te_protection = self._get_te_pass_protection(getattr(personnel, 'te_on_field', None)) 
        
        total_protection = (
            ol_rating * PassGameBalance.OL_PROTECTION_WEIGHT +
            rb_protection * PassGameBalance.RB_PROTECTION_WEIGHT +
            te_protection * PassGameBalance.TE_PROTECTION_WEIGHT
        )
        
        # Step 2: Get pass rush strength  
        dl_rating = defense_ratings.get('dl', 50)
        lb_blitz = self._get_lb_blitz_pressure(personnel, defense_ratings)
        db_blitz = self._get_db_blitz_pressure(personnel, defense_ratings)
        
        total_rush = (
            dl_rating * PassGameBalance.DL_RUSH_WEIGHT +
            lb_blitz * PassGameBalance.LB_BLITZ_WEIGHT +
            db_blitz * PassGameBalance.DB_BLITZ_WEIGHT
        )
        
        # Calculate rush advantage for statistics
        rush_advantage = total_rush / (total_protection + 20)  # Avoid division by zero
        
        # Step 3: Apply time to throw from route concept
        matrix = ROUTE_CONCEPT_MATRICES[route_concept]
        time_to_throw = matrix["time_to_throw"]
        
        # Step 4: Calculate base sack probability
        sack_probability = self._calculate_base_sack_rate(total_protection, total_rush, time_to_throw)
        
        # Step 5: Apply situational modifiers
        sack_probability = self._apply_sack_situational_modifiers(sack_probability, field_state, personnel)
        
        # Step 6: Determine outcome
        if random.random() < sack_probability:
            sack_yards = self._calculate_sack_yardage(total_rush, total_protection)
            return ("sack", sack_yards), rush_advantage
        
        return ("no_sack", 0), rush_advantage
    
    def _calculate_sack_probability(self, offense_ratings: Dict, defense_ratings: Dict, 
                                   personnel, field_state: FieldState, route_concept: str) -> tuple[str, int]:
        """SOLID: Single responsibility - calculate sack probability before route development"""
        
        sack_outcome, _ = self._calculate_sack_probability_with_stats(
            offense_ratings, defense_ratings, personnel, field_state, route_concept
        )
        return sack_outcome
    
    def _get_rb_pass_protection(self, rb) -> float:
        """YAGNI: Simple RB pass protection calculation"""
        if not rb:
            return 30  # No RB = poor protection
        
        protection_rating = getattr(rb, 'pass_protection', 50)
        # RBs typically 30-70 range in pass pro
        return max(30, min(70, protection_rating))
    
    def _get_te_pass_protection(self, te) -> float:
        """YAGNI: Simple TE pass protection calculation"""
        if not te:
            return 50  # No TE = average protection
        
        protection_rating = getattr(te, 'pass_protection', 60)
        # Handle cases where getattr returns non-numeric values (like Mock objects)
        if not isinstance(protection_rating, (int, float)):
            protection_rating = 60  # Default fallback
        # TEs typically better pass protectors than RBs
        return max(40, min(80, protection_rating))
    
    def _get_lb_blitz_pressure(self, personnel, defense_ratings: Dict) -> float:
        """Calculate linebacker blitz pressure"""
        base_lb_rating = defense_ratings.get('lb', 50)
        
        # Check if defensive call indicates blitz
        blitz_calls = ["blitz", "safety_blitz", "corner_blitz"]
        if personnel.defensive_call in blitz_calls:
            return base_lb_rating * PassGameBalance.BLITZ_MULTIPLIER
        
        return base_lb_rating * PassGameBalance.BASE_LB_RUSH
    
    def _get_db_blitz_pressure(self, personnel, defense_ratings: Dict) -> float:
        """Calculate defensive back blitz pressure"""
        base_db_rating = defense_ratings.get('db', 50)
        
        # Only certain calls bring DB blitz
        db_blitz_calls = ["safety_blitz", "corner_blitz"]
        if personnel.defensive_call in db_blitz_calls:
            return base_db_rating * 0.8  # DBs not as good pass rushers
        
        return 0  # No DB rush normally
    
    def _calculate_base_sack_rate(self, protection: float, rush: float, time_to_throw: float) -> float:
        """KISS: Core sack rate calculation"""
        
        # Base formula: rush effectiveness vs protection, adjusted by time
        rush_advantage = rush / (protection + 20)  # Avoid division by zero
        time_factor = max(0.5, time_to_throw / 3.0)  # Longer routes = more sack risk
        
        base_sack_rate = PassGameBalance.BASE_SACK_RATE * rush_advantage * time_factor
        
        # Cap at reasonable maximum
        return min(PassGameBalance.MAX_SACK_RATE, base_sack_rate)
    
    def _apply_sack_situational_modifiers(self, base_sack_rate: float, field_state: FieldState, personnel) -> float:
        """SOLID: Single responsibility - apply game situation modifiers to sack probability"""
        
        modified_rate = base_sack_rate
        
        # Down and distance effects
        if field_state.down == 3 and field_state.yards_to_go > 7:
            modified_rate *= PassGameBalance.THIRD_AND_LONG_SACK_MULTIPLIER  # Defense can pin ears back
        elif field_state.down == 1:
            modified_rate *= PassGameBalance.FIRST_DOWN_SACK_REDUCTION  # Less predictable
        
        # Field position effects
        if field_state.field_position >= PassGameBalance.GOAL_LINE_THRESHOLD:
            modified_rate *= PassGameBalance.RED_ZONE_SACK_REDUCTION  # Compressed field, shorter routes
        elif field_state.field_position <= PassGameBalance.DEEP_TERRITORY_THRESHOLD:
            modified_rate *= PassGameBalance.DEEP_TERRITORY_SACK_INCREASE  # Defense can be aggressive
        
        # QB mobility factor
        qb = getattr(personnel, 'qb_on_field', None)
        if qb:
            mobility = getattr(qb, 'mobility', 50)
            mobility_factor = 1.0 - ((mobility - 50) * PassGameBalance.QB_MOBILITY_SACK_REDUCTION)
            modified_rate *= max(0.5, mobility_factor)  # Mobile QBs reduce sack rate
        
        return max(0.0, modified_rate)
    
    def _calculate_sack_yardage(self, rush_strength: float, protection_strength: float) -> int:
        """YAGNI: Simple sack yardage calculation"""
        
        # Stronger rush = QB driven back further
        rush_factor = rush_strength / 100.0
        base_sack_yards = PassGameBalance.BASE_SACK_YARDS
        
        # Add variance based on rush strength
        variance_range = PassGameBalance.SACK_YARDS_VARIANCE * rush_factor
        sack_yards = base_sack_yards + random.uniform(-variance_range, 0)
        
        # Cap at reasonable limits
        return max(PassGameBalance.MAX_SACK_YARDS, min(PassGameBalance.MIN_SACK_YARDS, int(sack_yards)))
    
    def _calculate_qb_effectiveness_for_route_concept(self, qb, route_concept: str) -> float:
        """SOLID: Single responsibility - calculate QB effectiveness for specific route concept"""
        
        if not qb:
            return 0.5  # Default average effectiveness
        
        # SOLID: Dependency inversion - depends on QB interface, not implementation
        matrix = ROUTE_CONCEPT_MATRICES[route_concept]
        total_rating = 0
        
        # KISS: Simple average calculation of relevant attributes
        for attribute in matrix["qb_attributes"]:
            rating = getattr(qb, attribute, 50)  # Safe attribute access with fallback
            total_rating += rating
        
        avg_rating = total_rating / len(matrix["qb_attributes"])
        return avg_rating / 100  # Normalize to 0-1 range
    
    def _calculate_wr_effectiveness_for_route_concept(self, wr, route_concept: str) -> float:
        """SOLID: Single responsibility - calculate WR effectiveness for specific route concept"""
        
        if not wr:
            return 0.5  # Default average effectiveness
        
        # SOLID: Dependency inversion - depends on WR interface, not implementation
        matrix = ROUTE_CONCEPT_MATRICES[route_concept]
        total_rating = 0
        
        # KISS: Simple average calculation of relevant attributes
        for attribute in matrix["wr_attributes"]:
            rating = getattr(wr, attribute, 50)  # Safe attribute access with fallback
            total_rating += rating
        
        avg_rating = total_rating / len(matrix["wr_attributes"])
        return avg_rating / 100  # Normalize to 0-1 range
    
    def _calculate_yards_from_route_matchup_matrix_with_stats(self, offense_ratings: Dict, defense_ratings: Dict,
                                                  personnel, formation_modifier: float, field_state: FieldState, simulation_data: Dict) -> tuple[str, int]:
        """SOLID: Single responsibility - main yards calculation using route concept matchup matrix with statistics tracking"""
        
        # Step 1: Determine route concept and coverage
        route_concept = self._determine_route_concept(personnel.formation, field_state)
        coverage_type = self._determine_defensive_coverage(personnel.defensive_call, personnel)
        matrix = ROUTE_CONCEPT_MATRICES[route_concept]
        
        # Store basic data
        simulation_data['route_concept'] = route_concept
        simulation_data['coverage_type'] = coverage_type
        
        # Step 2: SACK CALCULATION (happens first - can end play immediately)
        sack_outcome, rush_advantage = self._calculate_sack_probability_with_stats(
            offense_ratings, defense_ratings, personnel, field_state, route_concept
        )
        
        simulation_data['rush_advantage'] = rush_advantage
        
        if sack_outcome[0] == "sack":
            return sack_outcome
        
        # Step 3: Calculate QB effectiveness for this route concept
        qb = getattr(personnel, 'qb_on_field', None)
        qb_effectiveness = self._calculate_qb_effectiveness_for_route_concept(qb, route_concept)
        simulation_data['qb_effectiveness'] = qb_effectiveness
        
        # Step 4: Calculate WR effectiveness for this route concept  
        wr = getattr(personnel, 'primary_wr', None)
        wr_effectiveness = self._calculate_wr_effectiveness_for_route_concept(wr, route_concept)
        simulation_data['wr_effectiveness'] = wr_effectiveness
        
        # Step 5: Calculate protection effectiveness (for non-sack scenarios)
        ol_rating = offense_ratings.get('ol', 50)
        rb_protection = self._get_rb_pass_protection(personnel.rb_on_field)
        te_protection = self._get_te_pass_protection(getattr(personnel, 'te_on_field', None))
        
        protection_effectiveness = (
            ol_rating * PassGameBalance.OL_PROTECTION_WEIGHT +
            rb_protection * PassGameBalance.RB_PROTECTION_WEIGHT +
            te_protection * PassGameBalance.TE_PROTECTION_WEIGHT
        ) / 100.0  # Normalize to 0-1 range
        simulation_data['protection_effectiveness'] = protection_effectiveness
        
        # Step 6: Calculate coverage effectiveness (DB vs route concept)
        db_rating = defense_ratings.get('db', 50)
        coverage_modifier = matrix[f"vs_{coverage_type}_modifier"]
        coverage_effectiveness = db_rating / 100.0  # Normalize
        simulation_data['coverage_effectiveness'] = coverage_effectiveness
        simulation_data['coverage_modifier'] = coverage_modifier
        
        # Step 7: Combine all factors (KISS: simple weighted calculation)
        # ULTRA-THINK FIX: Fixed backwards team correlation bug
        # Elite defense was creating negative effectiveness, boosting offense!
        defensive_resistance = coverage_effectiveness * 1.2  # More moderate amplification
        defensive_impact = max(0.0, min(1.0, 1.0 - defensive_resistance))  # Clamp to 0-1 range
        
        combined_effectiveness = (
            qb_effectiveness * PassGameBalance.QB_EFFECTIVENESS_WEIGHT +
            wr_effectiveness * PassGameBalance.WR_EFFECTIVENESS_WEIGHT +
            protection_effectiveness * PassGameBalance.PROTECTION_WEIGHT +
            defensive_impact * PassGameBalance.COVERAGE_WEIGHT
        )
        
        # Step 8: Apply to base completion rate using additive approach (less harsh than multiplicative)
        # Ultra-think: Effectiveness should modify completion rate, not multiply it harshly
        # NFL-calibrated: Average effectiveness (0.7) should give ~95% of base completion
        effectiveness_modifier = 0.9 + (combined_effectiveness - 0.7) * 0.3  # Much gentler scaling
        base_with_effectiveness = matrix["base_completion"] * effectiveness_modifier
        
        # Apply formation and coverage modifiers (also made less harsh)
        final_completion = base_with_effectiveness * formation_modifier * (0.85 + coverage_modifier * 0.15)
        
        # Step 9: Apply situational modifiers
        final_completion = self._apply_pass_situational_modifiers(final_completion, field_state, route_concept)
        simulation_data['final_completion'] = final_completion
        
        # Step 10: Determine outcome and return
        return self._determine_pass_outcome(final_completion, matrix, route_concept, coverage_type, field_state)
    
    def _calculate_yards_from_route_matchup_matrix(self, offense_ratings: Dict, defense_ratings: Dict,
                                                  personnel, formation_modifier: float, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - main yards calculation using route concept matchup matrix"""
        
        simulation_data = {}  # Temporary storage, not used in this version
        return self._calculate_yards_from_route_matchup_matrix_with_stats(
            offense_ratings, defense_ratings, personnel, formation_modifier, field_state, simulation_data
        )
    
    def _apply_pass_situational_modifiers(self, base_completion: float, field_state: FieldState, route_concept: str) -> float:
        """SOLID: Single responsibility - apply game situation modifiers to completion probability"""
        
        modified_completion = base_completion
        
        # ULTRA-THINK FIX: Aggressive 3rd Down completion modifiers
        # Down and distance modifiers
        if field_state.down == 3:
            if field_state.yards_to_go > 7:
                # 3rd and long: BOOST (teams design plays specifically to convert)
                modified_completion *= 1.08  # 8% boost for 3rd and long situations  
            else:
                # 3rd and short: Even bigger boost for conversion attempts
                modified_completion *= 1.18  # 18% boost for short yardage conversions (increased from 15%)
        elif field_state.down == 1:
            modified_completion *= PassGameBalance.FIRST_DOWN_COMPLETION_BONUS  # Less predictable
        
        # Field position modifiers
        if field_state.field_position >= PassGameBalance.GOAL_LINE_THRESHOLD:
            modified_completion *= PassGameBalance.RED_ZONE_COMPLETION_BONUS  # Compressed field helps
        
        return max(0.0, min(1.0, modified_completion))  # Keep in valid range
    
    def _determine_pass_outcome(self, completion_probability: float, matrix: Dict, route_concept: str, coverage_type: str, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - determine final pass outcome with red zone logic"""
        
        # Interception check (happens first on attempts)
        int_probability = PassGameBalance.BASE_INT_RATE
        
        # ULTRA-THINK FIX: More aggressive INT modifiers to reach NFL 2.2%
        # These don't affect completion rate since they happen before completion check
        if coverage_type == "man" and route_concept == "vertical":
            int_probability *= 1.6  # Higher INT risk on deep man coverage
        elif coverage_type == "blitz":
            int_probability *= 1.5  # Blitz forces quick throws = more INTs
        elif coverage_type == "man":
            int_probability *= 1.3  # Man coverage generally higher INT risk
        
        # 3rd and long increases INT risk (desperate throws)
        if field_state.down == 3 and field_state.yards_to_go > 7:
            int_probability *= 1.4  # Increased from 1.2
            
        # Deep territory increases INT risk (risky throws)
        if field_state.field_position <= 25:
            int_probability *= 1.25  # Increased from 1.15
            
        # Pressure situations increase INT risk
        if field_state.down >= 3:
            int_probability *= 1.15  # Any 3rd/4th down pressure
        
        if random.random() < int_probability:
            return "interception", 0
        
        # Completion check
        if random.random() < completion_probability:
            # Completed pass - calculate yards
            base_yards = matrix["base_yards"]
            variance = random.uniform(0.7, 1.0 + matrix["variance"] * 0.3)
            final_yards = base_yards * variance
            
            # Add YAC component
            final_yards = self._add_yac_component(final_yards, route_concept)
            
            # ULTRA-THINK FIX: Aggressive 3rd Down yards boost for conversions
            if field_state.down == 3:
                # More aggressive boost to reach NFL 40% conversion rate
                base_boost = min(4.0, field_state.yards_to_go * 0.3)  # Increased multiplier
                # Extra boost for longer 3rd downs (they need more help)
                if field_state.yards_to_go > 7:
                    base_boost += 2.0  # Extra 2 yards for 3rd and long
                final_yards += base_boost
            
            yards = max(0, int(final_yards))
            
            # Check for touchdown - field position aware (no probability, just physics)
            final_position = field_state.field_position + yards
            if final_position >= 100:
                return "touchdown", yards
            
            return "gain", yards
        else:
            # Incomplete pass
            return "incomplete", 0
    
    def _add_yac_component(self, base_yards: float, route_concept: str) -> float:
        """YAGNI: Simple YAC (Yards After Catch) calculation"""
        
        # Different route concepts have different YAC potential
        yac_multipliers = {
            "quick_game": 0.3,    # Limited YAC on quick routes
            "intermediate": 0.5,  # Moderate YAC potential
            "vertical": 0.6,      # High YAC potential on completions
            "screens": 0.8,       # Very high YAC potential
            "play_action": 0.4    # Moderate YAC
        }
        
        yac_potential = yac_multipliers.get(route_concept, 0.45)
        yac_yards = base_yards * yac_potential * PassGameBalance.YAC_MULTIPLIER
        
        return base_yards + yac_yards
    
