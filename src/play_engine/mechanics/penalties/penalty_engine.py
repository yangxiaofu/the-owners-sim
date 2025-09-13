"""
Penalty Engine - Core Logic for NFL Penalty Simulation

The PenaltyEngine is responsible for:
1. Determining when penalties occur based on player discipline and game situation
2. Selecting which player commits the penalty
3. Applying penalty effects to play results
4. Creating comprehensive penalty tracking data

Integrates with the two-stage run play simulation system.
"""

import random
import math
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from .penalty_config_loader import get_penalty_config
from .penalty_data_structures import PenaltyInstance, PlayerPenaltyStats, TeamPenaltyStats
from ....team_management.players.player import Player


@dataclass
class PlayContext:
    """Context information for penalty determination"""
    quarter: int = 1
    time_remaining: str = "15:00"
    down: int = 1
    distance: int = 10
    field_position: int = 50  # Yards from own goal line
    score_differential: int = 0
    is_home_team: bool = True
    play_type: str = "run"
    offensive_formation: str = "i_formation"
    defensive_formation: str = "4_3_base"


@dataclass
class PenaltyResult:
    """Result of penalty determination and application"""
    penalty_occurred: bool = False
    penalty_instance: Optional[PenaltyInstance] = None
    modified_yards: int = 0  # Final play result after penalty
    automatic_first_down: bool = False
    play_negated: bool = False
    down_change: int = 0  # Change in down (usually 0 or reset to 1)
    distance_change: int = 0  # Change in distance to go


class PenaltyEngine:
    """Core engine for determining and applying penalties in football simulation"""
    
    def __init__(self):
        self.config_loader = get_penalty_config()
        
        # Penalty timing categories
        self.PRE_SNAP_PENALTIES = ["false_start", "encroachment", "offsides", "delay_of_game", "illegal_formation"]
        self.DURING_PLAY_PENALTIES = ["offensive_holding", "face_mask", "unnecessary_roughness", "illegal_contact"]
        self.POST_PLAY_PENALTIES = ["unsportsmanlike_conduct"]
    
    def check_for_penalty(self, 
                         offensive_players: List[Player],
                         defensive_players: List[Player],
                         context: PlayContext,
                         original_play_yards: int = 0) -> PenaltyResult:
        """
        Main penalty determination method
        
        Args:
            offensive_players: List of 11 offensive players
            defensive_players: List of 11 defensive players  
            context: Game situation context
            original_play_yards: Yards gained before penalty consideration
            
        Returns:
            PenaltyResult with penalty determination and effects
        """
        
        # Phase 1: Determine if a penalty occurs
        penalty_type = self._determine_penalty_occurrence(offensive_players, defensive_players, context)
        
        if penalty_type is None:
            return PenaltyResult(penalty_occurred=False, modified_yards=original_play_yards)
        
        # Phase 2: Select the player who committed the penalty
        guilty_player = self._select_guilty_player(penalty_type, offensive_players, defensive_players, context)
        
        # Phase 3: Create penalty instance with full context
        penalty_instance = self._create_penalty_instance(
            penalty_type, guilty_player, context, original_play_yards
        )
        
        # Phase 4: Apply penalty effects to play result
        penalty_result = self._apply_penalty_effects(penalty_instance, original_play_yards)
        
        return penalty_result
    
    def _determine_penalty_occurrence(self, 
                                    offensive_players: List[Player],
                                    defensive_players: List[Player], 
                                    context: PlayContext) -> Optional[str]:
        """
        Determine if a penalty occurs and what type
        
        Returns:
            Penalty type string if penalty occurs, None otherwise
        """
        
        # Calculate team discipline factors
        team_penalty_modifier = self._calculate_team_penalty_modifier(
            offensive_players + defensive_players, context.is_home_team
        )
        
        # Get all available penalty types
        available_penalties = self.config_loader.get_available_penalty_types()
        
        # Check each penalty type for occurrence
        for penalty_type in available_penalties:
            if self._should_penalty_occur(penalty_type, team_penalty_modifier, context):
                return penalty_type
        
        return None
    
    def _should_penalty_occur(self, penalty_type: str, team_modifier: float, context: PlayContext) -> bool:
        """Determine if a specific penalty type should occur"""
        
        # Get base penalty rate
        base_rate = self.config_loader.get_penalty_base_rate(penalty_type)
        
        # Apply team discipline modifier
        modified_rate = base_rate * team_modifier
        
        # Apply situational modifier
        situational_modifier = self.config_loader.get_situational_modifier(
            penalty_type, context.down, context.distance, context.field_position
        )
        final_rate = modified_rate * situational_modifier
        
        # Apply home field advantage
        home_modifier = self.config_loader.get_home_field_modifier(context.is_home_team)
        final_rate *= home_modifier
        
        # Roll for penalty occurrence
        return random.random() < final_rate
    
    def _calculate_team_penalty_modifier(self, all_players: List[Player], is_home_team: bool) -> float:
        """
        Calculate team-wide penalty modifier based on player discipline
        
        Args:
            all_players: All 22 players on field
            is_home_team: Whether team being evaluated is home team
            
        Returns:
            Modifier where 1.0 = average, <1.0 = fewer penalties, >1.0 = more penalties
        """
        
        if not all_players:
            return 1.0
        
        # Calculate weighted average of discipline ratings
        total_weight = 0
        weighted_discipline = 0
        
        for player in all_players:
            # Position-based weights (key positions matter more)
            position = player.primary_position
            weight = self._get_position_penalty_weight(position)
            
            discipline = player.get_rating("discipline")
            weighted_discipline += discipline * weight
            total_weight += weight
        
        if total_weight == 0:
            return 1.0
        
        avg_discipline = weighted_discipline / total_weight
        
        # Convert discipline rating to penalty modifier
        # Higher discipline = fewer penalties
        if avg_discipline >= 85:
            modifier = 0.6
        elif avg_discipline >= 70:
            modifier = 0.8
        elif avg_discipline >= 50:
            modifier = 1.0
        elif avg_discipline >= 30:
            modifier = 1.3
        else:
            modifier = 1.6
        
        return modifier
    
    def _get_position_penalty_weight(self, position: str) -> float:
        """Get how much a position's discipline affects team penalty rate"""
        
        # Key positions that affect penalties more
        high_impact_positions = {
            "quarterback": 1.5,      # QB discipline affects many penalties
            "center": 1.3,           # Center sets protection/calls
            "mike_linebacker": 1.2,  # MLB is defensive QB
            "left_tackle": 1.2,      # LT protects blind side
            "strong_safety": 1.1     # SS involved in many plays
        }
        
        return high_impact_positions.get(position, 1.0)
    
    def _select_guilty_player(self, 
                             penalty_type: str,
                             offensive_players: List[Player],
                             defensive_players: List[Player],
                             context: PlayContext) -> Player:
        """
        Select which specific player committed the penalty
        
        Args:
            penalty_type: Type of penalty that occurred
            offensive_players: Offensive players on field
            defensive_players: Defensive players on field
            context: Game situation
            
        Returns:
            Player object who committed the penalty
        """
        
        # Get penalty context information
        penalty_contexts = self.config_loader.get_penalty_contexts(penalty_type)
        typical_positions = penalty_contexts.get("typical_positions", [])
        
        # Determine if it's an offensive or defensive penalty
        offensive_penalties = ["offensive_holding", "false_start", "delay_of_game", "illegal_formation"]
        
        if penalty_type in offensive_penalties:
            candidate_players = offensive_players
        else:
            candidate_players = defensive_players
        
        # Filter to players at typical positions for this penalty
        position_filtered = []
        for player in candidate_players:
            if not typical_positions or player.primary_position in typical_positions:
                position_filtered.append(player)
        
        if not position_filtered:
            position_filtered = candidate_players  # Fallback to all players
        
        # Weight selection by player's penalty tendency
        weighted_players = []
        for player in position_filtered:
            # Players with worse discipline more likely to commit penalties
            penalty_modifier = player.get_penalty_modifier()
            weight = penalty_modifier
            
            # Add position-specific tendency
            weight *= self._get_position_penalty_tendency(player.primary_position, penalty_type)
            
            weighted_players.append((player, weight))
        
        # Select player based on weights
        if not weighted_players:
            return random.choice(candidate_players)
        
        total_weight = sum(weight for _, weight in weighted_players)
        random_value = random.random() * total_weight
        
        current_weight = 0
        for player, weight in weighted_players:
            current_weight += weight
            if random_value <= current_weight:
                return player
        
        # Fallback
        return weighted_players[0][0]
    
    def _get_position_penalty_tendency(self, position: str, penalty_type: str) -> float:
        """Get position-specific tendency for certain penalty types"""
        
        try:
            # Load discipline effects to get position tendencies
            config_dict = self.config_loader.load_config()
            if hasattr(config_dict, 'discipline_effects'):
                discipline_effects = config_dict.discipline_effects
            else:
                discipline_effects = config_dict.get('discipline_effects', {})
                
            position_tendencies = discipline_effects.get("position_penalty_tendencies", {})
            
            # Check each position group
            for group_name, group_info in position_tendencies.items():
                # Ensure group_info is a dictionary
                if isinstance(group_info, dict):
                    positions = group_info.get("positions", [])
                    if position in positions:
                        increased_penalties = group_info.get("increased_penalties", {})
                        return increased_penalties.get(penalty_type, 1.0)
        except (AttributeError, KeyError, TypeError) as e:
            # If configuration structure is not as expected, return default
            pass
        
        return 1.0  # Default tendency
    
    def _create_penalty_instance(self, 
                                penalty_type: str,
                                guilty_player: Player,
                                context: PlayContext,
                                original_play_yards: int) -> PenaltyInstance:
        """Create comprehensive penalty instance with all context"""
        
        # Get penalty configuration
        yards_assessed = self.config_loader.get_penalty_yardage(penalty_type)
        automatic_first = self.config_loader.is_automatic_first_down(penalty_type)
        negates_play = self.config_loader.does_negate_play(penalty_type)
        penalty_timing = self.config_loader.get_penalty_timing(penalty_type)
        
        # Generate context description
        penalty_contexts = self.config_loader.get_penalty_contexts(penalty_type)
        possible_contexts = penalty_contexts.get("contexts", ["Generic penalty context"])
        context_description = random.choice(possible_contexts)
        
        # Create penalty instance
        penalty_instance = PenaltyInstance(
            penalty_type=penalty_type,
            penalized_player_name=guilty_player.name,
            penalized_player_number=guilty_player.number,
            penalized_player_position=guilty_player.primary_position,
            team_penalized="home" if context.is_home_team else "away",
            
            # Penalty impact
            yards_assessed=yards_assessed,
            automatic_first_down=automatic_first,
            automatic_loss_of_down=False,  # Rare, could be added later
            negated_play=negates_play,
            
            # Game context
            quarter=context.quarter,
            time_remaining=context.time_remaining,
            down=context.down,
            distance=context.distance,
            field_position=context.field_position,
            score_differential=context.score_differential,
            
            # Play context
            original_play_result=original_play_yards if not negates_play else None,
            play_type=context.play_type,
            formation_offensive=context.offensive_formation,
            formation_defensive=context.defensive_formation,
            
            # Penalty details
            penalty_timing=penalty_timing,
            context_description=context_description,
            referee_explanation=f"{penalty_type.replace('_', ' ').title()}, #{guilty_player.number} {guilty_player.primary_position}",
            
            # Player attributes at time of penalty
            discipline_rating=guilty_player.get_rating("discipline"),
            composure_rating=guilty_player.get_rating("composure"),
            pressure_situation=self._is_pressure_situation(context)
        )
        
        return penalty_instance
    
    def _is_pressure_situation(self, context: PlayContext) -> bool:
        """Determine if current context is a pressure situation"""
        
        # Red zone
        if context.field_position >= 80:
            return True
        
        # Fourth down
        if context.down == 4:
            return True
        
        # Third and long
        if context.down == 3 and context.distance >= 8:
            return True
        
        # Fourth quarter with close score
        if context.quarter == 4 and abs(context.score_differential) <= 7:
            return True
        
        # Two-minute situation (simplified)
        if context.time_remaining.startswith("1:") or context.time_remaining.startswith("0:"):
            return True
        
        return False
    
    def _apply_penalty_effects(self, penalty: PenaltyInstance, original_yards: int) -> PenaltyResult:
        """Apply penalty effects to play result and game state"""
        
        if penalty.negated_play:
            # Play is completely negated, only penalty yardage applies
            final_yards = penalty.yards_assessed
            penalty.final_play_result = final_yards
        else:
            # Play result stands, penalty yardage is added
            final_yards = original_yards + penalty.yards_assessed
            penalty.final_play_result = final_yards
        
        # Determine down and distance changes
        down_change = 0
        distance_change = penalty.yards_assessed
        
        if penalty.automatic_first_down and penalty.yards_assessed > 0:
            # Defensive penalty with automatic first down
            down_change = 1 - penalty.down  # Reset to 1st down
            distance_change = -penalty.distance  # Reset distance to 10 (handled by game engine)
        
        return PenaltyResult(
            penalty_occurred=True,
            penalty_instance=penalty,
            modified_yards=final_yards,
            automatic_first_down=penalty.automatic_first_down,
            play_negated=penalty.negated_play,
            down_change=down_change,
            distance_change=distance_change
        )
    
    def calculate_team_discipline_score(self, players: List[Player]) -> Dict[str, Any]:
        """
        Calculate comprehensive team discipline metrics
        
        Args:
            players: List of all team players
            
        Returns:
            Dictionary with team discipline analysis
        """
        if not players:
            return {"error": "No players provided"}
        
        # Overall discipline metrics
        disciplines = [p.get_rating("discipline") for p in players]
        composures = [p.get_rating("composure") for p in players]
        experiences = [p.get_rating("experience") for p in players]
        
        discipline_avg = sum(disciplines) / len(disciplines)
        composure_avg = sum(composures) / len(composures)
        experience_avg = sum(experiences) / len(experiences)
        
        # Identify penalty-prone players
        penalty_prone = [p for p in players if p.is_penalty_prone()]
        
        # Position group analysis
        position_analysis = {}
        position_groups = {
            "offensive_line": ["left_tackle", "left_guard", "center", "right_guard", "right_tackle"],
            "skill_positions": ["quarterback", "running_back", "wide_receiver", "tight_end"],
            "defensive_line": ["defensive_end", "defensive_tackle", "nose_tackle"],
            "linebackers": ["mike_linebacker", "sam_linebacker", "will_linebacker", "inside_linebacker", "outside_linebacker"],
            "secondary": ["cornerback", "nickel_cornerback", "free_safety", "strong_safety"]
        }
        
        for group_name, positions in position_groups.items():
            group_players = [p for p in players if p.primary_position in positions]
            if group_players:
                group_discipline = sum(p.get_rating("discipline") for p in group_players) / len(group_players)
                position_analysis[group_name] = {
                    "avg_discipline": round(group_discipline, 1),
                    "player_count": len(group_players),
                    "penalty_prone_count": len([p for p in group_players if p.is_penalty_prone()])
                }
        
        return {
            "team_discipline_score": round(discipline_avg, 1),
            "team_composure_score": round(composure_avg, 1),
            "team_experience_score": round(experience_avg, 1),
            "overall_penalty_modifier": self._calculate_team_penalty_modifier(players, True),
            "penalty_prone_players": len(penalty_prone),
            "penalty_prone_percentage": round(len(penalty_prone) / len(players) * 100, 1),
            "position_group_analysis": position_analysis,
            "discipline_grade": self._get_discipline_grade(discipline_avg),
            "projected_penalties_per_game": self._project_penalties_per_game(discipline_avg)
        }
    
    def _get_discipline_grade(self, avg_discipline: float) -> str:
        """Convert discipline score to letter grade"""
        if avg_discipline >= 90:
            return "A+"
        elif avg_discipline >= 85:
            return "A"
        elif avg_discipline >= 80:
            return "A-"
        elif avg_discipline >= 75:
            return "B+"
        elif avg_discipline >= 70:
            return "B"
        elif avg_discipline >= 65:
            return "B-"
        elif avg_discipline >= 60:
            return "C+"
        elif avg_discipline >= 55:
            return "C"
        elif avg_discipline >= 50:
            return "C-"
        else:
            return "D or F"
    
    def _project_penalties_per_game(self, avg_discipline: float) -> float:
        """Project penalties per game based on team discipline"""
        # NFL average is about 6-7 penalties per team per game
        base_penalties = 6.5
        
        # Adjust based on discipline
        if avg_discipline >= 85:
            return round(base_penalties * 0.6, 1)
        elif avg_discipline >= 70:
            return round(base_penalties * 0.8, 1)  
        elif avg_discipline >= 50:
            return round(base_penalties * 1.0, 1)
        elif avg_discipline >= 30:
            return round(base_penalties * 1.3, 1)
        else:
            return round(base_penalties * 1.6, 1)