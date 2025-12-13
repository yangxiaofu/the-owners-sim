"""
Offensive Coordinator - Offensive play calling and scheme management

The offensive coordinator is responsible for play selection, formation choices,
personnel packages, and implementing offensive concepts and strategies.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .coach_archetype import BaseCoachArchetype, CoachType, FormationPreferences, PlayTypeTendencies


@dataclass
class OffensivePhilosophy:
    """Offensive coordinator specific philosophical traits"""
    # Scheme preferences (0.0-1.0)
    # Balanced defaults - philosophy boosts only trigger when preference > 0.5
    west_coast_preference: float = 0.4          # Short, timing-based passing
    air_raid_preference: float = 0.2            # Spread, high-volume passing
    ground_and_pound_preference: float = 0.45   # Run-heavy (below 0.5 = no boost, base weights apply)
    rpo_usage: float = 0.5                      # Run-pass option frequency
    
    # Innovation and creativity (0.0-1.0)
    motion_usage: float = 0.6                   # Pre-snap motion frequency
    formation_creativity: float = 0.5            # Unique formation usage
    play_action_mastery: float = 0.6            # Play action effectiveness
    gadget_play_frequency: float = 0.1          # Trick plays and gadgets
    
    # Tempo and rhythm (0.0-1.0)
    no_huddle_usage: float = 0.3                # No-huddle offense frequency
    hurry_up_comfort: float = 0.5               # Comfort with fast tempo
    scripted_opening_reliance: float = 0.7      # Stick to scripted plays early


@dataclass
class PersonnelManagement:
    """How the OC manages personnel packages and player usage"""
    # Personnel package preferences (0.0-1.0)
    eleven_personnel_usage: float = 0.6         # 11 personnel (3 WR, 1 TE, 1 RB)
    twelve_personnel_usage: float = 0.4         # 12 personnel (2 WR, 2 TE, 1 RB)
    twenty_one_personnel_usage: float = 0.2     # 21 personnel (2 WR, 1 TE, 2 RB)
    ten_personnel_usage: float = 0.3            # 10 personnel (4 WR, 1 TE, 1 RB)
    
    # Player utilization philosophy
    feature_back_reliance: float = 0.6          # Rely on one primary RB vs committee
    tight_end_involvement: float = 0.5          # How much TEs are used in passing
    slot_receiver_emphasis: float = 0.6         # Focus on slot receiver usage
    deep_threat_prioritization: float = 0.4     # Emphasis on deep ball receivers


@dataclass
class SituationalCalling:
    """Situational play calling tendencies"""
    # Down and distance preferences - granular pass rates for realistic strategy
    # Balanced NFL approach: ~48% pass rate on 1st down for balanced run/pass
    first_down_pass_rate: float = 0.48          # Pass rate on 1st down (balanced)
    second_and_short_pass_rate: float = 0.42    # 2nd & 2-4 yards (run-heavy)
    second_and_medium_pass_rate: float = 0.55   # 2nd & 5-7 yards (slightly pass)
    second_and_long_pass_rate: float = 0.72     # 2nd & 8+ yards (pass-heavy)
    third_and_short_pass_rate: float = 0.45     # 3rd & 1-3 yards (run-heavy)
    third_and_medium_pass_rate: float = 0.65    # 3rd & 4-7 yards (pass-heavy)
    third_and_long_pass_rate: float = 0.88      # 3rd & 8+ yards (pass-heavy)
    goal_line_pass_rate: float = 0.42           # Goal line (run-heavy)
    red_zone_pass_rate: float = 0.52            # Red zone (balanced)
    two_minute_pass_rate: float = 0.82          # Two-minute drill (pass-heavy)

    # Legacy fields (kept for backwards compatibility)
    second_and_long_creativity: float = 0.6     # Creative plays on 2nd & 7+
    third_down_conversion_aggression: float = 0.7  # Risk taking on 3rd down

    # Field position adjustments - stronger run commitment
    red_zone_fade_preference: float = 0.35      # Fade routes in red zone (reduced)
    red_zone_run_commitment: float = 0.65       # Power runs in red zone (increased)
    goal_line_innovation: float = 0.25          # Creative goal line plays (reduced - more power runs)

    # Game situation responses - stronger clock management running
    comeback_route_mastery: float = 0.6         # Comeback routes when behind
    clock_killing_run_game: float = 0.75        # Run game when protecting leads (increased)
    two_minute_drill_efficiency: float = 0.6    # Two-minute offense execution


@dataclass
class OffensiveCoordinator(BaseCoachArchetype):
    """
    Offensive coordinator focused on play calling and offensive scheme management
    
    Handles formation selection, play concepts, personnel packages, and 
    implements the offensive game plan with situational awareness.
    """
    
    # Specialized traits for offensive coordinators
    philosophy: OffensivePhilosophy = field(default_factory=OffensivePhilosophy)
    personnel: PersonnelManagement = field(default_factory=PersonnelManagement)
    situational_calling: SituationalCalling = field(default_factory=SituationalCalling)
    
    # Playbook preferences - list of preferred playbooks
    preferred_playbooks: List[str] = field(default_factory=lambda: ["balanced"])
    
    def __post_init__(self):
        """Initialize offensive coordinator with proper type and validation"""
        self.coach_type = CoachType.OFFENSIVE_COORDINATOR
        super().__post_init__()
    
    def get_formation_preference(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Get formation preferences for a given situation
        
        Args:
            situation: Game situation ('first_down', 'red_zone', 'two_minute', etc.)
            context: Additional context (down, distance, field position, etc.)
        
        Returns:
            Dictionary of formation preferences with weights
        """
        if not context:
            context = {}
        
        base_formations = {
            'i_formation': self.formations.i_formation_preference,
            'shotgun': self.formations.shotgun_preference,
            'pistol': self.formations.pistol_preference,
            'four_wide': self.formations.four_wide_preference,
        }
        
        # Adjust based on situation
        if situation == 'red_zone':
            # More I-formation and goal line packages in red zone
            base_formations['i_formation'] *= 1.5
            base_formations['shotgun'] *= 0.7
            
        elif situation == 'two_minute':
            # More shotgun and four wide in two-minute drill
            base_formations['shotgun'] *= 1.4
            base_formations['four_wide'] *= 1.3
            base_formations['i_formation'] *= 0.6
            
        elif situation == 'third_and_long':
            # Spread formations for passing
            base_formations['shotgun'] *= 1.3
            base_formations['four_wide'] *= 1.4
            
        elif situation == 'short_yardage':
            # Power formations for short yardage
            base_formations['i_formation'] *= 1.6
            base_formations['shotgun'] *= 0.5

        # NEW: Apply game script formation modifiers
        game_context = context.get('game_context')
        if game_context:
            from ..mechanics.game_script_modifiers import GameScriptModifiers

            formation_adjustments = GameScriptModifiers.get_formation_adjustment(
                game_script=game_context.game_script,
                game_script_adherence=self.game_script_adherence
            )

            # Apply multipliers
            for formation, multiplier in formation_adjustments.items():
                if formation in base_formations:
                    base_formations[formation] *= multiplier

        # Normalize weights
        total_weight = sum(base_formations.values())
        if total_weight > 0:
            return {k: v/total_weight for k, v in base_formations.items()}
        
        return base_formations
    
    def get_personnel_package(self, formation: str, situation: str) -> str:
        """
        Select personnel package based on formation and situation
        
        Args:
            formation: Selected formation
            situation: Game situation
        
        Returns:
            Personnel package (e.g., "11", "12", "21", "10")
        """
        # Base personnel preferences
        packages = {
            '11': self.personnel.eleven_personnel_usage,      # 3 WR, 1 TE, 1 RB
            '12': self.personnel.twelve_personnel_usage,      # 2 WR, 2 TE, 1 RB  
            '21': self.personnel.twenty_one_personnel_usage,  # 2 WR, 1 TE, 2 RB
            '10': self.personnel.ten_personnel_usage,         # 4 WR, 1 TE, 1 RB
        }
        
        # Adjust based on formation
        if formation in ['shotgun', 'four_wide']:
            packages['11'] *= 1.3  # More spread personnel in spread formations
            packages['10'] *= 1.5
            packages['21'] *= 0.5  # Less heavy personnel
            
        elif formation == 'i_formation':
            packages['21'] *= 1.4  # More heavy personnel in power formations
            packages['12'] *= 1.2
            packages['10'] *= 0.3  # Much less spread personnel
        
        # Adjust based on situation
        if situation in ['red_zone', 'short_yardage']:
            packages['12'] *= 1.3  # More TEs for blocking
            packages['21'] *= 1.2  # More RBs for power
            
        elif situation in ['two_minute', 'third_and_long']:
            packages['11'] *= 1.2  # More receivers
            packages['10'] *= 1.4
            packages['21'] *= 0.6  # Fewer power packages
        
        # Select highest weighted package
        return max(packages.items(), key=lambda x: x[1])[0]

    def _determine_target_pass_rate(self, situation: str) -> float:
        """
        Determine target pass rate based on down/distance situation.

        This method maps situations to appropriate pass rate fields,
        allowing for realistic down/distance-specific play calling strategy.

        Args:
            situation: Situation string from PlayCallContext (e.g., 'first_down', 'third_and_long')

        Returns:
            Target pass rate (0.0-1.0) for the given situation
        """
        # Map situations to pass rate fields
        # NOTE: Use situational_calling (SituationalCalling), not situational (SituationalTendencies)
        situation_map = {
            'first_down': self.situational_calling.first_down_pass_rate,
            'second_and_short': self.situational_calling.second_and_short_pass_rate,
            'second_and_medium': self.situational_calling.second_and_medium_pass_rate,
            'second_and_long': self.situational_calling.second_and_long_pass_rate,
            'third_and_short': self.situational_calling.third_and_short_pass_rate,
            'third_and_medium': self.situational_calling.third_and_medium_pass_rate,
            'third_and_long': self.situational_calling.third_and_long_pass_rate,
            'goal_line': self.situational_calling.goal_line_pass_rate,
            'red_zone': self.situational_calling.red_zone_pass_rate,
            'two_minute': self.situational_calling.two_minute_pass_rate
        }

        # Return situation-specific rate, or default to 0.50 (50% pass)
        return situation_map.get(situation, 0.50)

    def get_play_concept_preference(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Get preferred play concepts for the situation
        
        Args:
            situation: Game situation
            context: Additional context (formation, personnel, etc.)
        
        Returns:
            Dictionary of concept preferences with weights
        """
        if not context:
            context = {}

        # NEW: Determine target pass rate based on down/distance situation
        target_pass_rate = self._determine_target_pass_rate(situation)
        target_run_rate = 1.0 - target_pass_rate

        # Start with base concepts for all coordinators - NEVER empty
        # NOW: Dynamically scaled based on target pass/run rates instead of hardcoded
        base_run_concepts = {
            'power': 0.35,          # Run - primary power play
            'sweep': 0.25,          # Run - outside run
            'off_tackle': 0.25,     # Run - off-tackle
            'draw': 0.10,           # Run - draw play
            'dive': 0.05,           # Run - interior run
        }

        base_pass_concepts = {
            'slants': 0.34,         # Pass - quick slants
            'quick_out': 0.24,      # Pass - quick outs
            'comeback': 0.24,       # Pass - comeback routes
            'four_verticals': 0.18  # Pass - deep routes
        }

        # Calculate scaling factors to match target pass/run rates
        run_weight_sum = sum(base_run_concepts.values())
        pass_weight_sum = sum(base_pass_concepts.values())

        # Scale weights to achieve target pass/run distribution
        concepts = {}
        for concept, weight in base_run_concepts.items():
            concepts[concept] = weight * (target_run_rate / run_weight_sum)
        for concept, weight in base_pass_concepts.items():
            concepts[concept] = weight * (target_pass_rate / pass_weight_sum)
        
        # Enhance based on philosophy preferences
        if self.philosophy.west_coast_preference > 0.5:
            concepts.update({
                'slants': 0.8,
                'quick_out': 0.7,
                'comeback': 0.6,
                'play_action_short': 0.5
            })
        
        if self.philosophy.air_raid_preference > 0.5:
            concepts.update({
                'four_verticals': 0.8,
                'smash': 0.7,
                'deep_comeback': 0.6,
                'crossing_routes': 0.5
            })
        
        if self.philosophy.ground_and_pound_preference > 0.5:
            # Heavy emphasis on running game
            concepts.update({
                'power': 0.9,           # Power running emphasis
                'sweep': 0.7,           # Outside runs
                'off_tackle': 0.8,      # Off-tackle runs
                'draw': 0.6,            # Draw plays
                'dive': 0.5,            # Interior runs
                'play_action_deep': 0.3 # Only occasional play action (reduced from 0.5)
            })
        
        # Situational adjustments
        if situation == 'red_zone':
            if self.situational_calling.red_zone_fade_preference > 0.5:
                concepts['fade'] = 0.8
            if self.situational_calling.red_zone_run_commitment > 0.5:
                concepts['power'] = concepts.get('power', 0.5) * 1.5
                concepts['off_tackle'] = concepts.get('off_tackle', 0.5) * 1.3
        
        elif situation == 'third_and_long':
            concepts.update({
                'deep_comeback': 0.8,
                'crossing_routes': 0.7,
                'intermediate_routes': 0.6
            })
        
        elif situation == 'two_minute':
            concepts.update({
                'quick_slant': 0.8,
                'sideline_routes': 1.5,  # Boosted from 0.7 to 1.5 (2x+) for clock management
                'out_routes': 1.2,       # Explicit out routes for OOB opportunities
                'comeback': 1.0,         # Comebacks also go to sideline
                'deep_routes': 0.4 if self.situational_calling.two_minute_drill_efficiency > 0.6 else 0.2
            })

        # NEW: Apply game script modifiers if GameContext available
        game_context = context.get('game_context')
        if game_context:
            from ..mechanics.game_script_modifiers import GameScriptModifiers

            # Get run/pass adjustments
            adjustments = GameScriptModifiers.get_run_pass_adjustment(
                game_script=game_context.game_script,
                game_script_adherence=self.game_script_adherence
            )

            # Comprehensive concept type classification
            run_concepts = [
                'power', 'sweep', 'off_tackle', 'draw', 'dive', 'sneak',
                'inside_zone', 'outside_zone', 'counter', 'trap', 'iso',
                'toss', 'pitch', 'option', 'qb_sneak', 'goal_line_power',
                'stretch', 'blast', 'lead', 'cutback'
            ]
            pass_concepts = [
                'slants', 'fade', 'deep_routes', 'quick_out', 'comeback',
                'four_verticals', 'crossing_routes', 'intermediate_routes',
                'sideline_routes', 'quick_slant', 'deep_comeback', 'out_routes',
                'play_action_short', 'play_action_deep', 'play_action_intermediate',
                'play_action_rollout', 'screen', 'check_down', 'short_routes',
                'deep_out', 'pick_play', 'smash', 'tight_end_out', 'slant'
            ]

            for concept in concepts:
                if concept in run_concepts:
                    concepts[concept] *= adjustments['run']
                elif concept in pass_concepts:
                    concepts[concept] *= adjustments['pass']

        # STRICT VALIDATION - never allow empty concept dictionary
        if not concepts:
            raise ValueError(f"Empty concepts dictionary for coordinator {self.name} in situation {situation}")
        
        total_weight = sum(concepts.values())
        if total_weight <= 0:
            raise ValueError(f"All concept weights <= 0 for coordinator {self.name}. Concepts: {concepts}")
        
        return concepts

    def should_spike(self, context: Dict[str, Any]) -> bool:
        """
        Determine if offensive coordinator should call a spike play.

        Spike plays are used to stop the clock in two-minute drill situations
        when trailing and out of timeouts.

        Args:
            context: Game context with time_remaining, score_differential, etc.

        Returns:
            True if spike play should be called
        """
        # Extract context
        time_remaining = context.get('time_remaining', 900)
        quarter = context.get('quarter', 1)
        score_differential = context.get('score_differential', 0)
        down = context.get('down', 1)
        clock_running = context.get('clock_running', True)
        timeouts_remaining = context.get('timeouts_remaining', 3)

        # Spike criteria:
        # 1. Must be in final 2 minutes (two-minute drill)
        # 2. Must be trailing or tied (need points)
        # 3. Clock must be running (otherwise spike wastes a down)
        # 4. Cannot be 4th down
        # 5. Preferably low/no timeouts (spike wastes down but saves timeout)

        # Not in two-minute drill
        if quarter != 4 or time_remaining > 120:
            return False

        # Cannot spike on 4th down
        if down == 4:
            return False

        # Don't spike if winning (let clock run)
        if score_differential > 0:
            return False

        # Don't spike if clock is already stopped
        if not clock_running:
            return False

        # Primary spike scenario: Trailing/tied + clock running + no timeouts
        if score_differential <= 0 and timeouts_remaining == 0:
            # Spike to stop clock when out of timeouts
            return True

        # Secondary spike scenario: Trailing + low on timeouts + critical time
        if score_differential < 0 and timeouts_remaining <= 1 and time_remaining < 60:
            # Final minute, preserve last timeout
            return True

        # Otherwise, use timeout instead (doesn't waste down)
        return False

    def get_offensive_tempo(self, situation: str, context: Dict[str, Any] = None) -> str:
        """
        Determine offensive tempo based on game situation.

        Tempo affects play duration via PlayDuration.calculate_duration().

        Tempo Options:
        - "normal": Default pace (1.0x)
        - "hurry_up": Fast tempo, no huddle (0.6x = 40% faster)
        - "two_minute": Maximum urgency (0.5x = 50% faster)
        - "slow": Clock-killing pace (1.2x = 20% slower)

        Args:
            situation: Game situation string ('two_minute', 'red_zone', etc.)
            context: Additional game context

        Returns:
            Tempo string for PlayDuration
        """
        if context is None:
            context = {}

        time_remaining = context.get('time_remaining', 900)
        quarter = context.get('quarter', 1)
        score_differential = context.get('score_differential', 0)

        # Two-minute drill tempo
        if situation == 'two_minute':
            # Final 2 minutes of half, use maximum urgency
            if score_differential < 0:
                # Trailing: two_minute tempo (50% faster)
                return "two_minute"
            elif score_differential == 0:
                # Tied: hurry_up tempo (40% faster)
                return "hurry_up"
            else:
                # Winning: normal tempo (don't help opponent by going fast)
                return "normal"

        # Late game clock management (not quite two-minute drill)
        if quarter == 4 and time_remaining < 300:  # Final 5 minutes
            if score_differential < -7:
                # Down by 2+ scores: hurry_up to maximize possessions
                return "hurry_up"
            elif score_differential > 7:
                # Up by 2+ scores: slow tempo to kill clock
                return "slow"

        # NEW: Game script tempo adjustments (lower priority than two_minute)
        game_context = context.get('game_context')
        if game_context:
            from ..mechanics.game_script_modifiers import GameScriptModifiers

            script_tempo = GameScriptModifiers.get_tempo_adjustment(
                game_script=game_context.game_script,
                game_script_adherence=self.game_script_adherence
            )

            if script_tempo:
                return script_tempo

        # No-huddle personality trait
        if self.philosophy.no_huddle_usage > 0.7:
            # Coach loves no-huddle - use hurry_up frequently
            return "hurry_up"

        # Default: normal tempo
        return "normal"

    def evaluate_head_coach_influence(self, hc_influence: float, situation: str) -> float:
        """
        Evaluate how head coach influence affects play calling
        
        Args:
            hc_influence: Head coach influence level (0.0-1.0)
            situation: Current situation
        
        Returns:
            Adjusted influence factor for this coordinator
        """
        # Base resistance to head coach control
        resistance = self.adaptability  # Higher adaptability = less resistance to change
        
        # Some coordinators are more autonomous
        autonomy = 1.0 - self.game_script_adherence  # Less adherence = more autonomous
        
        # In critical situations, accept more head coach input
        critical_situations = ['red_zone', 'fourth_down', 'two_minute', 'overtime']
        if situation in critical_situations:
            acceptance = 0.8  # More willing to take direction in critical moments
        else:
            acceptance = resistance * 0.7 + autonomy * 0.3
        
        # Return effective influence (how much HC influence actually affects decisions)
        return hc_influence * acceptance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert offensive coordinator to dictionary for JSON serialization"""
        base_dict = super().to_dict()
        
        # Add offensive coordinator specific data
        base_dict['coach_type'] = self.coach_type.value
        base_dict['philosophy'] = {
            'west_coast_preference': self.philosophy.west_coast_preference,
            'air_raid_preference': self.philosophy.air_raid_preference,
            'ground_and_pound_preference': self.philosophy.ground_and_pound_preference,
            'rpo_usage': self.philosophy.rpo_usage,
            'motion_usage': self.philosophy.motion_usage,
            'formation_creativity': self.philosophy.formation_creativity,
            'play_action_mastery': self.philosophy.play_action_mastery,
            'gadget_play_frequency': self.philosophy.gadget_play_frequency,
            'no_huddle_usage': self.philosophy.no_huddle_usage,
            'hurry_up_comfort': self.philosophy.hurry_up_comfort,
            'scripted_opening_reliance': self.philosophy.scripted_opening_reliance,
        }
        base_dict['personnel'] = {
            'eleven_personnel_usage': self.personnel.eleven_personnel_usage,
            'twelve_personnel_usage': self.personnel.twelve_personnel_usage,
            'twenty_one_personnel_usage': self.personnel.twenty_one_personnel_usage,
            'ten_personnel_usage': self.personnel.ten_personnel_usage,
            'feature_back_reliance': self.personnel.feature_back_reliance,
            'tight_end_involvement': self.personnel.tight_end_involvement,
            'slot_receiver_emphasis': self.personnel.slot_receiver_emphasis,
            'deep_threat_prioritization': self.personnel.deep_threat_prioritization,
        }
        base_dict['situational_calling'] = {
            'first_down_pass_rate': self.situational_calling.first_down_pass_rate,
            'second_and_long_creativity': self.situational_calling.second_and_long_creativity,
            'third_down_conversion_aggression': self.situational_calling.third_down_conversion_aggression,
            'red_zone_fade_preference': self.situational_calling.red_zone_fade_preference,
            'red_zone_run_commitment': self.situational_calling.red_zone_run_commitment,
            'goal_line_innovation': self.situational_calling.goal_line_innovation,
            'comeback_route_mastery': self.situational_calling.comeback_route_mastery,
            'clock_killing_run_game': self.situational_calling.clock_killing_run_game,
            'two_minute_drill_efficiency': self.situational_calling.two_minute_drill_efficiency,
        }
        base_dict['preferred_playbooks'] = self.preferred_playbooks.copy()
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OffensiveCoordinator':
        """Create OffensiveCoordinator from dictionary (JSON loading)"""
        # Extract specialized data
        philosophy_data = data.get('philosophy', {})
        personnel_data = data.get('personnel', {})
        situational_calling_data = data.get('situational_calling', {})
        preferred_playbooks = data.get('preferred_playbooks', ['balanced'])
        
        # Use base class method for common traits
        base_coach = BaseCoachArchetype.from_dict(data)
        
        # Create offensive coordinator with specialized traits
        return cls(
            name=base_coach.name,
            description=base_coach.description,
            coach_type=CoachType.OFFENSIVE_COORDINATOR,
            aggression=base_coach.aggression,
            risk_tolerance=base_coach.risk_tolerance,
            adaptability=base_coach.adaptability,
            conservatism=base_coach.conservatism,
            run_preference=base_coach.run_preference,
            fourth_down_aggression=base_coach.fourth_down_aggression,
            red_zone_aggression=base_coach.red_zone_aggression,
            game_script_adherence=base_coach.game_script_adherence,
            momentum_responsiveness=base_coach.momentum_responsiveness,
            pressure_handling=base_coach.pressure_handling,
            situational=base_coach.situational,
            formations=base_coach.formations,
            play_types=base_coach.play_types,
            philosophy=OffensivePhilosophy(**philosophy_data),
            personnel=PersonnelManagement(**personnel_data),
            situational_calling=SituationalCalling(**situational_calling_data),
            preferred_playbooks=preferred_playbooks,
        )