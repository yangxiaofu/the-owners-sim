"""
Staff Factory - Creates coaching staff combinations

Provides convenient methods to create coaching staffs with different philosophies,
real coach combinations, and procedurally generated staff variations.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import random

from .coaching_staff import CoachingStaff
from .head_coach import HeadCoach, GameManagementTraits, CoordinatorInfluence
from .offensive_coordinator import OffensiveCoordinator, OffensivePhilosophy, PersonnelManagement, SituationalCalling
from .defensive_coordinator import DefensiveCoordinator, DefensivePhilosophy, PersonnelUsage, SituationalDefense
from .special_teams_coordinator import (
    SpecialTeamsCoordinator, SpecialTeamsPhilosophy, SpecialTeamsTraits,
    create_aggressive_special_teams_coordinator, create_conservative_special_teams_coordinator, create_balanced_special_teams_coordinator
)
from .coach_archetype import BaseCoachArchetype, CoachType, SituationalTendencies, FormationPreferences, PlayTypeTendencies


class StaffFactory:
    """Factory for creating coaching staff combinations"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize factory with configuration directory
        
        Args:
            config_dir: Directory containing coaching staff configuration files
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config" / "coaching_staff"
        
        self.config_dir = Path(config_dir)
        self.head_coaches_dir = self.config_dir / "head_coaches"
        self.offensive_coordinators_dir = self.config_dir / "offensive_coordinators"
        self.defensive_coordinators_dir = self.config_dir / "defensive_coordinators"
        self.combinations_dir = self.config_dir / "staff_combinations"
    
    # Factory methods for common staff archetypes
    
    def create_aggressive_staff(self, team_name: str = "Aggressive Team") -> CoachingStaff:
        """
        Create an aggressive coaching staff
        
        Args:
            team_name: Team name for the coaches
        
        Returns:
            Aggressive coaching staff
        """
        # Aggressive head coach
        hc = HeadCoach(
            name=f"{team_name} Head Coach",
            description="Aggressive game manager who takes risks",
            aggression=0.8,
            risk_tolerance=0.8,
            conservatism=0.2,
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=0.8,
                two_minute_drill_aggression=0.9,
                overtime_aggression=0.8
            ),
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=0.6,
                defensive_coordinator_trust=0.6,
                critical_situation_override_threshold=0.4
            )
        )
        
        # Pass-heavy offensive coordinator
        oc = OffensiveCoordinator(
            name=f"{team_name} Offensive Coordinator",
            description="Aggressive, pass-heavy coordinator",
            aggression=0.7,
            run_preference=0.3,  # Pass-heavy
            philosophy=OffensivePhilosophy(
                air_raid_preference=0.8,
                west_coast_preference=0.4,
                ground_and_pound_preference=0.2,
                formation_creativity=0.8,
                gadget_play_frequency=0.2
            ),
            preferred_playbooks=["aggressive", "air_raid"]
        )
        
        # Aggressive defensive coordinator
        dc = DefensiveCoordinator(
            name=f"{team_name} Defensive Coordinator",
            description="Aggressive, blitz-happy coordinator",
            aggression=0.8,
            philosophy=DefensivePhilosophy(
                blitz_frequency=0.6,
                creative_pressure_usage=0.7,
                man_coverage_confidence=0.7,
                press_coverage_aggression=0.8
            ),
            situational=SituationalDefense(
                third_down_pressure_rate=0.8,
                fourth_down_stop_aggression=0.9
            )
        )
        
        # Aggressive special teams coordinator
        st = create_aggressive_special_teams_coordinator(team_name)
        
        return CoachingStaff(hc, oc, dc, st)
    
    def create_conservative_staff(self, team_name: str = "Conservative Team") -> CoachingStaff:
        """
        Create a conservative coaching staff
        
        Args:
            team_name: Team name for the coaches
        
        Returns:
            Conservative coaching staff
        """
        # Conservative head coach
        hc = HeadCoach(
            name=f"{team_name} Head Coach",
            description="Conservative game manager focused on avoiding mistakes",
            aggression=0.3,
            risk_tolerance=0.2,
            conservatism=0.8,
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=0.2,
                two_minute_drill_aggression=0.4,
                timeout_usage_intelligence=0.8
            ),
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=0.8,
                defensive_coordinator_trust=0.8,
                critical_situation_override_threshold=0.2
            )
        )
        
        # Run-heavy offensive coordinator
        oc = OffensiveCoordinator(
            name=f"{team_name} Offensive Coordinator",
            description="Conservative, run-heavy coordinator",
            aggression=0.3,
            run_preference=0.7,  # Run-heavy
            philosophy=OffensivePhilosophy(
                ground_and_pound_preference=0.8,
                west_coast_preference=0.6,
                air_raid_preference=0.2,
                formation_creativity=0.4,
                gadget_play_frequency=0.05
            ),
            preferred_playbooks=["conservative", "ground_and_pound"]
        )
        
        # Conservative defensive coordinator
        dc = DefensiveCoordinator(
            name=f"{team_name} Defensive Coordinator",
            description="Conservative, coverage-focused coordinator",
            aggression=0.3,
            conservatism=0.8,
            philosophy=DefensivePhilosophy(
                blitz_frequency=0.2,
                zone_coverage_preference=0.8,
                safety_help_reliance=0.8,
                four_man_rush_confidence=0.8
            ),
            situational=SituationalDefense(
                prevent_defense_usage=0.6,
                backed_up_defense_conservatism=0.9
            )
        )
        
        # Conservative special teams coordinator
        st = create_conservative_special_teams_coordinator(team_name)
        
        return CoachingStaff(hc, oc, dc, st)
    
    def create_balanced_staff(self, team_name: str = "Balanced Team") -> CoachingStaff:
        """
        Create a balanced coaching staff
        
        Args:
            team_name: Team name for the coaches
        
        Returns:
            Balanced coaching staff
        """
        # Balanced head coach
        hc = HeadCoach(
            name=f"{team_name} Head Coach",
            description="Balanced game manager who adapts to situations",
            aggression=0.5,
            risk_tolerance=0.5,
            conservatism=0.5,
            adaptability=0.8,
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=0.5,
                two_minute_drill_aggression=0.6,
                timeout_usage_intelligence=0.7
            ),
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=0.7,
                defensive_coordinator_trust=0.7
            )
        )
        
        # Balanced offensive coordinator (adjusted for 55% run / 45% pass target)
        # Base concepts in OC are calibrated for 55% run / 45% pass
        # Philosophy preferences must stay AT or BELOW 0.5 to avoid triggering boosts
        # Game script modifiers provide the variation (COMPETITIVE, CONTROL, COMEBACK, etc.)
        oc = OffensiveCoordinator(
            name=f"{team_name} Offensive Coordinator",
            description="Balanced coordinator with multiple looks",
            aggression=0.5,
            run_preference=0.55,  # Slight run preference for 55% target
            game_script_adherence=0.7,  # Higher adherence = stronger game script response
            philosophy=OffensivePhilosophy(
                west_coast_preference=0.45,        # Below 0.5 - no pass boost triggered
                air_raid_preference=0.3,           # Low - minimal pass emphasis
                ground_and_pound_preference=0.50,  # AT 0.5 threshold - no boost (base concepts handle 55% run)
                formation_creativity=0.6,
                rpo_usage=0.5
            ),
            preferred_playbooks=["balanced"]
        )
        
        # Balanced defensive coordinator
        dc = DefensiveCoordinator(
            name=f"{team_name} Defensive Coordinator",
            description="Balanced coordinator who adjusts to opponent",
            aggression=0.5,
            philosophy=DefensivePhilosophy(
                blitz_frequency=0.4,
                zone_coverage_preference=0.6,
                man_coverage_confidence=0.4,
                nickel_heavy_preference=0.6
            ),
            personnel=PersonnelUsage(
                nickel_package_comfort=0.7,
                safety_flexibility=0.8
            )
        )
        
        # Balanced special teams coordinator
        st = create_balanced_special_teams_coordinator(team_name)
        
        return CoachingStaff(hc, oc, dc, st)
    
    # Real NFL coaching staff combinations
    
    def create_chiefs_style_staff(self) -> CoachingStaff:
        """Create Kansas City Chiefs style coaching staff (Reid/Bieniemy era)"""
        # Andy Reid style head coach
        hc = HeadCoach(
            name="Andy Reid Style HC",
            description="Offensive-minded head coach with clock management quirks",
            aggression=0.7,
            adaptability=0.8,
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=0.6,
                two_minute_drill_aggression=0.8,
                timeout_usage_intelligence=0.6  # Reid's timeout management
            )
        )
        
        # Creative, pass-heavy OC
        oc = OffensiveCoordinator(
            name="Chiefs Style OC",
            description="Creative play caller with RPO mastery",
            run_preference=0.3,
            philosophy=OffensivePhilosophy(
                west_coast_preference=0.7,
                rpo_usage=0.8,
                motion_usage=0.9,
                formation_creativity=0.9,
                play_action_mastery=0.8
            ),
            preferred_playbooks=["west_coast", "rpo_concepts"]
        )
        
        # Balanced defensive coordinator
        dc = DefensiveCoordinator(
            name="Chiefs Style DC",
            description="Multiple look defense with situational pressure",
            philosophy=DefensivePhilosophy(
                blitz_frequency=0.4,
                creative_pressure_usage=0.6,
                nickel_heavy_preference=0.7
            )
        )
        
        # Chiefs-style special teams coordinator (known for solid special teams)
        st = create_balanced_special_teams_coordinator("Chiefs")
        st.description = "Solid special teams coordinator with good coverage discipline"
        st.special_teams_traits.coverage_discipline = 0.8
        
        return CoachingStaff(hc, oc, dc, st)
    
    def create_patriots_dynasty_staff(self) -> CoachingStaff:
        """Create New England Patriots dynasty style staff (Belichick era)"""
        # Belichick style head coach
        hc = HeadCoach(
            name="Belichick Style HC",
            description="Situational master with complete control",
            aggression=0.6,
            adaptability=0.9,
            game_script_adherence=0.9,
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=0.5,
                timeout_usage_intelligence=0.9,
                clock_management_skill=0.9
            ),
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=0.5,  # High control
                defensive_coordinator_trust=0.8,  # Belichick IS the DC
                critical_situation_override_threshold=0.2
            )
        )
        
        # Adaptable offensive coordinator
        oc = OffensiveCoordinator(
            name="Patriots Style OC",
            description="Adaptable coordinator who adjusts to personnel",
            adaptability=0.9,
            run_preference=0.5,
            philosophy=OffensivePhilosophy(
                west_coast_preference=0.6,
                formation_creativity=0.7,
                scripted_opening_reliance=0.8
            ),
            preferred_playbooks=["balanced", "situational"]
        )
        
        # Multiple defense coordinator
        dc = DefensiveCoordinator(
            name="Patriots Style DC", 
            description="Multiple defensive looks, takes away opponent's best",
            aggression=0.5,
            adaptability=0.9,
            philosophy=DefensivePhilosophy(
                zone_coverage_preference=0.6,
                man_coverage_confidence=0.7,
                creative_pressure_usage=0.7,
                nickel_heavy_preference=0.8
            )
        )
        
        # Patriots-style special teams coordinator (Belichick emphasis on special teams)
        st = create_balanced_special_teams_coordinator("Patriots")
        st.description = "Detail-oriented special teams coordinator emphasizing situational preparation"
        st.special_teams_traits.punt_fake_detection = 0.9
        st.special_teams_traits.field_goal_fake_detection = 0.9
        st.special_teams_traits.coverage_discipline = 0.9
        
        return CoachingStaff(hc, oc, dc, st)
    
    def create_rams_mcvay_staff(self) -> CoachingStaff:
        """Create LA Rams McVay era style staff"""
        # McVay style head coach
        hc = HeadCoach(
            name="McVay Style HC",
            description="Offensive genius who delegates defensive duties",
            aggression=0.7,
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=0.9,  # McVay calls offense
                defensive_coordinator_trust=0.9,  # Full delegation
                critical_situation_override_threshold=0.4
            )
        )
        
        # Innovative offensive coordinator (McVay himself)
        oc = OffensiveCoordinator(
            name="McVay Style OC",
            description="Innovative play designer with motion mastery",
            aggression=0.8,
            run_preference=0.4,
            philosophy=OffensivePhilosophy(
                west_coast_preference=0.5,
                air_raid_preference=0.4,
                motion_usage=0.95,
                formation_creativity=0.95,
                play_action_mastery=0.9,
                rpo_usage=0.4
            ),
            preferred_playbooks=["mcvay_concepts", "motion_heavy"]
        )
        
        # Aggressive defensive coordinator
        dc = DefensiveCoordinator(
            name="Rams Style DC",
            description="Aggressive coordinator with exotic pressures",
            aggression=0.8,
            philosophy=DefensivePhilosophy(
                blitz_frequency=0.5,
                creative_pressure_usage=0.8,
                man_coverage_confidence=0.6
            )
        )
        
        # Rams-style special teams coordinator
        st = create_balanced_special_teams_coordinator("Rams")
        st.description = "Modern special teams coordinator with aggressive return philosophy"
        st.special_teams_traits.punt_return_aggression = 0.7
        st.special_teams_traits.field_goal_return_preparedness = 0.8
        
        return CoachingStaff(hc, oc, dc, st)
    
    # Procedural generation methods
    
    def generate_random_staff(self, team_name: str = "Generated Team", 
                            archetype_bias: Optional[str] = None) -> CoachingStaff:
        """
        Generate a random coaching staff
        
        Args:
            team_name: Team name for the coaches
            archetype_bias: Optional bias ('aggressive', 'conservative', 'balanced')
        
        Returns:
            Randomly generated coaching staff
        """
        if archetype_bias == 'aggressive':
            base_aggression = random.uniform(0.6, 0.9)
            base_conservatism = random.uniform(0.1, 0.4)
        elif archetype_bias == 'conservative':
            base_aggression = random.uniform(0.1, 0.4)
            base_conservatism = random.uniform(0.6, 0.9)
        else:  # balanced or no bias
            base_aggression = random.uniform(0.3, 0.7)
            base_conservatism = random.uniform(0.3, 0.7)
        
        # Generate head coach
        hc = self._generate_random_head_coach(team_name, base_aggression, base_conservatism)
        
        # Generate coordinators with some correlation to head coach
        oc = self._generate_random_offensive_coordinator(team_name, base_aggression * 0.8 + random.uniform(-0.2, 0.2))
        dc = self._generate_random_defensive_coordinator(team_name, base_aggression * 0.8 + random.uniform(-0.2, 0.2))
        st = self._generate_random_special_teams_coordinator(team_name, base_aggression * 0.8 + random.uniform(-0.2, 0.2))
        
        return CoachingStaff(hc, oc, dc, st)
    
    def _generate_random_head_coach(self, team_name: str, aggression: float, conservatism: float) -> HeadCoach:
        """Generate random head coach"""
        return HeadCoach(
            name=f"{team_name} Head Coach",
            description="Randomly generated head coach",
            aggression=max(0.1, min(0.9, aggression + random.uniform(-0.1, 0.1))),
            risk_tolerance=random.uniform(0.2, 0.8),
            adaptability=random.uniform(0.4, 0.9),
            conservatism=max(0.1, min(0.9, conservatism + random.uniform(-0.1, 0.1))),
            game_management=GameManagementTraits(
                fourth_down_decision_aggression=aggression + random.uniform(-0.2, 0.2),
                two_minute_drill_aggression=random.uniform(0.4, 0.9),
                timeout_usage_intelligence=random.uniform(0.5, 0.9)
            ),
            coordinator_influence=CoordinatorInfluence(
                offensive_coordinator_trust=random.uniform(0.4, 0.9),
                defensive_coordinator_trust=random.uniform(0.4, 0.9),
                critical_situation_override_threshold=random.uniform(0.2, 0.5)
            )
        )
    
    def _generate_random_offensive_coordinator(self, team_name: str, aggression: float) -> OffensiveCoordinator:
        """Generate random offensive coordinator"""
        return OffensiveCoordinator(
            name=f"{team_name} Offensive Coordinator",
            description="Randomly generated offensive coordinator",
            aggression=max(0.1, min(0.9, aggression + random.uniform(-0.2, 0.2))),
            run_preference=random.uniform(0.2, 0.8),
            philosophy=OffensivePhilosophy(
                west_coast_preference=random.uniform(0.2, 0.8),
                air_raid_preference=random.uniform(0.1, 0.7),
                ground_and_pound_preference=random.uniform(0.1, 0.7),
                formation_creativity=random.uniform(0.3, 0.9),
                motion_usage=random.uniform(0.4, 0.9),
                rpo_usage=random.uniform(0.2, 0.8)
            ),
            preferred_playbooks=[random.choice(["balanced", "aggressive", "conservative", "west_coast"])]
        )
    
    def _generate_random_defensive_coordinator(self, team_name: str, aggression: float) -> DefensiveCoordinator:
        """Generate random defensive coordinator"""
        return DefensiveCoordinator(
            name=f"{team_name} Defensive Coordinator",
            description="Randomly generated defensive coordinator",
            aggression=max(0.1, min(0.9, aggression + random.uniform(-0.2, 0.2))),
            philosophy=DefensivePhilosophy(
                four_three_preference=random.uniform(0.3, 0.8),
                three_four_preference=random.uniform(0.2, 0.7),
                blitz_frequency=random.uniform(0.1, 0.7),
                zone_coverage_preference=random.uniform(0.3, 0.8),
                man_coverage_confidence=random.uniform(0.2, 0.8),
                nickel_heavy_preference=random.uniform(0.5, 0.9)
            ),
            personnel=PersonnelUsage(
                nickel_package_comfort=random.uniform(0.5, 0.9),
                dime_package_usage=random.uniform(0.2, 0.7)
            )
        )
    
    def _generate_random_special_teams_coordinator(self, team_name: str, aggression: float) -> SpecialTeamsCoordinator:
        """Generate random special teams coordinator"""
        # Randomly select philosophy
        philosophy_choices = [SpecialTeamsPhilosophy.AGGRESSIVE, SpecialTeamsPhilosophy.CONSERVATIVE, SpecialTeamsPhilosophy.BALANCED]
        philosophy = random.choice(philosophy_choices)
        
        return SpecialTeamsCoordinator(
            name=f"{team_name} Special Teams Coordinator",
            description="Randomly generated special teams coordinator",
            aggression=max(0.1, min(0.9, aggression + random.uniform(-0.2, 0.2))),
            risk_tolerance=random.uniform(0.2, 0.8),
            adaptability=random.uniform(0.4, 0.8),
            philosophy=philosophy,
            special_teams_traits=SpecialTeamsTraits(
                punt_block_aggression=random.uniform(0.2, 0.7),
                punt_return_aggression=random.uniform(0.3, 0.8),
                punt_fake_detection=random.uniform(0.5, 0.9),
                field_goal_block_aggression=random.uniform(0.2, 0.7),
                field_goal_fake_detection=random.uniform(0.6, 0.9),
                field_goal_return_preparedness=random.uniform(0.4, 0.8),
                coverage_discipline=random.uniform(0.5, 0.9),
                special_teams_personnel_trust=random.uniform(0.4, 0.8)
            )
        )
    
    # Configuration file methods
    
    def load_staff_combination(self, combination_name: str) -> CoachingStaff:
        """
        Load pre-defined staff combination from configuration file
        
        Args:
            combination_name: Name of the combination file (without .json)
        
        Returns:
            Loaded coaching staff
        """
        combination_file = self.combinations_dir / f"{combination_name}.json"
        
        if not combination_file.exists():
            raise FileNotFoundError(f"Staff combination file not found: {combination_file}")
        
        with open(combination_file, 'r') as f:
            data = json.load(f)
        
        # Load each coach from their respective files or inline data
        hc_data = data.get('head_coach', {})
        if isinstance(hc_data, str):
            # Reference to external file
            hc = self._load_head_coach(hc_data)
        else:
            # Inline data
            hc = HeadCoach.from_dict(hc_data)
        
        oc_data = data.get('offensive_coordinator', {})
        if isinstance(oc_data, str):
            oc = self._load_offensive_coordinator(oc_data)
        else:
            oc = OffensiveCoordinator.from_dict(oc_data)
        
        dc_data = data.get('defensive_coordinator', {})
        if isinstance(dc_data, str):
            dc = self._load_defensive_coordinator(dc_data)
        else:
            dc = DefensiveCoordinator.from_dict(dc_data)
        
        return CoachingStaff(hc, oc, dc)
    
    def _load_head_coach(self, coach_name: str) -> HeadCoach:
        """Load head coach from file"""
        coach_file = self.head_coaches_dir / f"{coach_name}.json"
        with open(coach_file, 'r') as f:
            data = json.load(f)
        return HeadCoach.from_dict(data)
    
    def _load_offensive_coordinator(self, coach_name: str) -> OffensiveCoordinator:
        """Load offensive coordinator from file"""
        coach_file = self.offensive_coordinators_dir / f"{coach_name}.json"
        with open(coach_file, 'r') as f:
            data = json.load(f)
        return OffensiveCoordinator.from_dict(data)
    
    def _load_defensive_coordinator(self, coach_name: str) -> DefensiveCoordinator:
        """Load defensive coordinator from file"""
        coach_file = self.defensive_coordinators_dir / f"{coach_name}.json"
        with open(coach_file, 'r') as f:
            data = json.load(f)
        return DefensiveCoordinator.from_dict(data)
    
    def get_available_combinations(self) -> List[str]:
        """Get list of available staff combinations"""
        if not self.combinations_dir.exists():
            return []
        
        combination_files = self.combinations_dir.glob("*.json")
        return [f.stem for f in combination_files]
    
    def _create_team_specific_staff(self, team_name: str, hc_type: str, oc_type: str, dc_type: str) -> CoachingStaff:
        """
        Create custom coaching staff based on individual coach type specifications
        
        Args:
            team_name: Team name for the coaches
            hc_type: Head coach type ("aggressive", "conservative", "balanced")
            oc_type: Offensive coordinator type ("pass_heavy", "balanced", "conservative")
            dc_type: Defensive coordinator type ("aggressive", "conservative", "balanced")
        
        Returns:
            Custom coaching staff combination
        """
        # Create head coach based on type
        hc = self._create_head_coach_by_type(team_name, hc_type)
        
        # Create offensive coordinator based on type
        oc = self._create_offensive_coordinator_by_type(team_name, oc_type)
        
        # Create defensive coordinator based on type
        dc = self._create_defensive_coordinator_by_type(team_name, dc_type)
        
        return CoachingStaff(hc, oc, dc)
    
    def _create_head_coach_by_type(self, team_name: str, coach_type: str) -> HeadCoach:
        """Create head coach by type"""
        if coach_type == "ultra_aggressive":
            return HeadCoach(
                name=f"{team_name} Head Coach",
                description="Ultra-aggressive game manager who takes maximum risks",
                aggression=0.95,
                risk_tolerance=0.9,
                conservatism=0.1,
                adaptability=0.7,
                game_management=GameManagementTraits(
                    fourth_down_decision_aggression=0.9,
                    two_minute_drill_aggression=0.95,
                    overtime_aggression=0.9
                ),
                coordinator_influence=CoordinatorInfluence(
                    offensive_coordinator_trust=0.5,
                    defensive_coordinator_trust=0.5,
                    critical_situation_override_threshold=0.2  # Low threshold = overrides often
                )
            )
        elif coach_type == "aggressive":
            return HeadCoach(
                name=f"{team_name} Head Coach",
                description="Aggressive game manager who takes risks",
                aggression=0.8,
                risk_tolerance=0.8,
                conservatism=0.2,
                game_management=GameManagementTraits(
                    fourth_down_decision_aggression=0.8,
                    two_minute_drill_aggression=0.9,
                    overtime_aggression=0.8
                ),
                coordinator_influence=CoordinatorInfluence(
                    offensive_coordinator_trust=0.6,
                    defensive_coordinator_trust=0.6,
                    critical_situation_override_threshold=0.4
                )
            )
        elif coach_type == "ultra_conservative":
            return HeadCoach(
                name=f"{team_name} Head Coach",
                description="Ultra-conservative game manager focused on minimizing all risks",
                aggression=0.1,
                risk_tolerance=0.1,
                conservatism=0.95,
                adaptability=0.4,
                game_management=GameManagementTraits(
                    fourth_down_decision_aggression=0.1,
                    two_minute_drill_aggression=0.3,
                    timeout_usage_intelligence=0.9
                ),
                coordinator_influence=CoordinatorInfluence(
                    offensive_coordinator_trust=0.9,
                    defensive_coordinator_trust=0.9,
                    critical_situation_override_threshold=0.1  # Very low threshold = overrides rarely
                )
            )
        elif coach_type == "conservative":
            return HeadCoach(
                name=f"{team_name} Head Coach",
                description="Conservative game manager focused on avoiding mistakes",
                aggression=0.3,
                risk_tolerance=0.2,
                conservatism=0.8,
                game_management=GameManagementTraits(
                    fourth_down_decision_aggression=0.2,
                    two_minute_drill_aggression=0.4,
                    timeout_usage_intelligence=0.8
                ),
                coordinator_influence=CoordinatorInfluence(
                    offensive_coordinator_trust=0.8,
                    defensive_coordinator_trust=0.8,
                    critical_situation_override_threshold=0.2
                )
            )
        else:  # balanced
            return HeadCoach(
                name=f"{team_name} Head Coach",
                description="Balanced game manager who adapts to situations",
                aggression=0.5,
                risk_tolerance=0.5,
                conservatism=0.5,
                adaptability=0.8,
                game_management=GameManagementTraits(
                    fourth_down_decision_aggression=0.5,
                    two_minute_drill_aggression=0.6,
                    timeout_usage_intelligence=0.7
                ),
                coordinator_influence=CoordinatorInfluence(
                    offensive_coordinator_trust=0.7,
                    defensive_coordinator_trust=0.7
                )
            )
    
    def _create_offensive_coordinator_by_type(self, team_name: str, coach_type: str) -> OffensiveCoordinator:
        """Create offensive coordinator by type"""
        if coach_type == "pass_heavy":
            return OffensiveCoordinator(
                name=f"{team_name} Offensive Coordinator",
                description="Pass-heavy coordinator focused on aerial attack",
                aggression=0.7,
                run_preference=0.3,  # Pass-heavy
                philosophy=OffensivePhilosophy(
                    air_raid_preference=0.8,
                    west_coast_preference=0.6,
                    ground_and_pound_preference=0.2,
                    formation_creativity=0.8,
                    gadget_play_frequency=0.2,
                    motion_usage=0.7
                ),
                preferred_playbooks=["aggressive", "air_raid", "west_coast"]
            )
        elif coach_type == "conservative":
            return OffensiveCoordinator(
                name=f"{team_name} Offensive Coordinator",
                description="Conservative, run-heavy coordinator",
                aggression=0.3,
                run_preference=0.7,  # Run-heavy
                philosophy=OffensivePhilosophy(
                    ground_and_pound_preference=0.8,
                    west_coast_preference=0.6,
                    air_raid_preference=0.2,
                    formation_creativity=0.4,
                    gadget_play_frequency=0.05
                ),
                preferred_playbooks=["conservative", "ground_and_pound"]
            )
        else:  # balanced
            return OffensiveCoordinator(
                name=f"{team_name} Offensive Coordinator",
                description="Balanced coordinator with multiple looks",
                aggression=0.5,
                run_preference=0.5,
                philosophy=OffensivePhilosophy(
                    west_coast_preference=0.6,
                    air_raid_preference=0.4,
                    ground_and_pound_preference=0.4,
                    formation_creativity=0.6,
                    rpo_usage=0.6
                ),
                preferred_playbooks=["balanced", "west_coast"]
            )
    
    def _create_defensive_coordinator_by_type(self, team_name: str, coach_type: str) -> DefensiveCoordinator:
        """Create defensive coordinator by type"""
        if coach_type == "aggressive":
            return DefensiveCoordinator(
                name=f"{team_name} Defensive Coordinator",
                description="Aggressive, blitz-happy coordinator",
                aggression=0.8,
                philosophy=DefensivePhilosophy(
                    blitz_frequency=0.6,
                    creative_pressure_usage=0.7,
                    man_coverage_confidence=0.7,
                    press_coverage_aggression=0.8
                ),
                situational=SituationalDefense(
                    third_down_pressure_rate=0.8,
                    fourth_down_stop_aggression=0.9
                )
            )
        elif coach_type == "conservative":
            return DefensiveCoordinator(
                name=f"{team_name} Defensive Coordinator",
                description="Conservative, coverage-focused coordinator",
                aggression=0.3,
                conservatism=0.8,
                philosophy=DefensivePhilosophy(
                    blitz_frequency=0.2,
                    zone_coverage_preference=0.8,
                    safety_help_reliance=0.8,
                    four_man_rush_confidence=0.8
                ),
                situational=SituationalDefense(
                    prevent_defense_usage=0.6,
                    backed_up_defense_conservatism=0.9
                )
            )
        else:  # balanced
            return DefensiveCoordinator(
                name=f"{team_name} Defensive Coordinator",
                description="Balanced coordinator who adjusts to opponent",
                aggression=0.5,
                philosophy=DefensivePhilosophy(
                    blitz_frequency=0.4,
                    zone_coverage_preference=0.6,
                    man_coverage_confidence=0.4,
                    nickel_heavy_preference=0.6
                ),
                personnel=PersonnelUsage(
                    nickel_package_comfort=0.7,
                    safety_flexibility=0.8
                )
            )