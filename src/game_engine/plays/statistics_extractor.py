from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..personnel.player_selector import PersonnelPackage
from ..simulation.blocking.data_structures import BlockingResult


@dataclass
class PassPlayData:
    """Container for pass play simulation data"""
    qb_effectiveness: float
    wr_effectiveness: float
    protection_effectiveness: float
    coverage_effectiveness: float
    rush_advantage: float
    coverage_modifier: float
    route_concept: str
    coverage_type: str
    final_completion: float
    outcome: str


@dataclass
class RunPlayData:
    """Container for run play simulation data"""
    rb_effectiveness: float
    blocking_results: List[BlockingResult]
    yards_gained: int
    expected_yards: float
    outcome: str


class StatisticsExtractor:
    """Extracts comprehensive statistics from play simulation data"""
    
    def extract_pass_statistics(self, personnel: PersonnelPackage, 
                               pass_data: PassPlayData) -> Dict[str, Any]:
        """Extract all pass-related statistics"""
        
        stats = {}
        
        # Basic player assignments
        stats['quarterback'] = self._get_player_name(personnel.position_player_map.get('quarterback'))
        stats['receiver'] = self._identify_primary_receiver(personnel, pass_data)
        
        # Pass rush statistics
        if pass_data.rush_advantage > 1.2:  # High pressure situation
            stats['pressure_applied'] = True
            stats['pass_rusher'] = self._identify_primary_rusher(personnel, pass_data)
            
            # Differentiate between sack, hit, hurry based on effectiveness and rush advantage
            if pass_data.outcome == 'sack':
                # Sack already handled by outcome
                pass
            elif pass_data.qb_effectiveness < 0.6:  # QB significantly affected by pressure
                if pass_data.rush_advantage > 1.5:  # Very high pressure
                    stats['quarterback_hits_by'] = [stats['pass_rusher']]
                else:
                    stats['quarterback_hurries_by'] = [stats['pass_rusher']]
        
        # Coverage statistics
        if pass_data.coverage_effectiveness > 0.8:  # Good coverage
            coverage_defender = self._identify_coverage_defender(personnel, pass_data)
            if coverage_defender:
                stats['coverage_defender'] = coverage_defender
                
                if pass_data.outcome == 'incomplete':
                    stats['passes_defended_by'] = [coverage_defender]
                elif pass_data.outcome == 'interception':
                    stats['interceptions_by'] = coverage_defender
        
        # Protection analysis
        protection_breakdowns = self._analyze_protection_breakdowns(personnel, pass_data)
        stats['protection_breakdowns'] = protection_breakdowns
        stats['clean_pocket'] = len(protection_breakdowns) == 0 and pass_data.rush_advantage < 1.1
        stats['perfect_protection'] = pass_data.protection_effectiveness > 0.9
        
        # Coverage beaten analysis
        base_completion = self._get_base_completion_rate(pass_data.route_concept, pass_data.coverage_type)
        stats['coverage_beaten'] = pass_data.final_completion > base_completion
        
        return stats
    
    def extract_run_statistics(self, personnel: PersonnelPackage, 
                              run_data: RunPlayData) -> Dict[str, Any]:
        """Extract all run-related statistics"""
        
        stats = {}
        
        # Basic player assignments
        stats['rusher'] = self._get_player_name(personnel.rb_on_field)
        
        # Blocking analysis
        pancakes = []
        key_blocks = []
        protection_failures = []
        
        for block_result in run_data.blocking_results:
            blocker_name = self._get_position_player_name(personnel, block_result.blocker_position)
            defender_name = self._get_position_player_name(personnel, block_result.defender_position, is_defense=True)
            
            if block_result.success and block_result.impact_factor > 0.8:
                # High-impact successful block
                rating_diff = block_result.blocker_rating - block_result.defender_rating
                if rating_diff > 15:  # Significant rating advantage = pancake
                    pancakes.append(blocker_name)
                else:
                    key_blocks.append(blocker_name)
                    
            elif not block_result.success and block_result.impact_factor > 0.6:
                # Failed block with high impact on play
                protection_failures.append({
                    'blocker': blocker_name,
                    'defender': defender_name
                })
        
        stats['pancakes_by'] = pancakes
        stats['key_blocks_by'] = key_blocks
        stats['protection_breakdowns'] = protection_failures
        
        # RB performance analysis
        yards_over_expected = run_data.yards_gained - run_data.expected_yards
        
        if yards_over_expected > 3:  # RB created extra yards
            stats['broken_tackles'] = min(2, max(0, int(yards_over_expected / 4)))
            # Identify which defenders likely missed tackles
            stats['missed_tackles_by'] = self._identify_missed_tacklers(
                personnel, yards_over_expected
            )
        
        # Primary and assist tackler identification
        if run_data.yards_gained >= 0 and run_data.outcome != 'touchdown':
            tackler_info = self._identify_tacklers(personnel, run_data)
            stats['tackler'] = tackler_info.get('primary')
            stats['assist_tackler'] = tackler_info.get('assist')
        
        # Defensive performance
        if run_data.yards_gained < 0:
            stats['tackles_for_loss_by'] = [self._identify_tfl_player(personnel, run_data.blocking_results)]
        
        # Perfect blocking analysis
        stats['perfect_protection'] = all(br.success for br in run_data.blocking_results)
        
        return stats
    
    def _get_player_name(self, player) -> Optional[str]:
        """Get player name from player object or ID"""
        if not player:
            return None
        
        # Handle player objects with name attribute (like MockPlayer)
        if hasattr(player, 'name'):
            return str(player.name)
        
        # Handle player objects that can be converted to string
        if hasattr(player, '__str__') and str(player) != str(type(player)):
            player_str = str(player)
            # Remove "Player_" prefix if it exists
            if player_str.startswith("Player_"):
                return player_str[7:]  # Remove "Player_" prefix
            return player_str
        
        # Fallback for string IDs or other types
        if isinstance(player, str):
            # Remove "Player_" prefix if it exists
            if player.startswith("Player_"):
                return player[7:]  # Remove "Player_" prefix
            return player
        
        # Final fallback - convert to string
        return str(player)
    
    def _get_position_player_name(self, personnel: PersonnelPackage, position: str, 
                                 is_defense: bool = False) -> Optional[str]:
        """Get player name for a specific position using enhanced mapping"""
        
        # First try the direct position mapping (NEW - Enhanced system)
        player = personnel.get_player_by_position(position)
        if player:
            return self._get_player_name(player)
        
        # Fallback to existing logic for backward compatibility
        if is_defense:
            # Get defensive player at position
            if hasattr(personnel, f'{position.lower()}_on_field'):
                player_id = getattr(personnel, f'{position.lower()}_on_field')
                return self._get_player_name(player_id)
        else:
            # Get offensive player at position
            position_mapping = {
                'LT': 'lt_on_field', 'LG': 'lg_on_field', 'C': 'c_on_field',
                'RG': 'rg_on_field', 'RT': 'rt_on_field', 'TE': 'te_on_field',
                'FB': 'fb_on_field'
            }
            
            if position in position_mapping:
                attr_name = position_mapping[position]
                if hasattr(personnel, attr_name):
                    player_id = getattr(personnel, attr_name)
                    return self._get_player_name(player_id)
        
        # Final fallback to generic naming
        return f"{position}_Player"
    
    def _identify_primary_receiver(self, personnel: PersonnelPackage, 
                                  pass_data: PassPlayData) -> Optional[str]:
        """Identify the primary receiver targeted on the play"""
        # For now, use first WR - can be enhanced with route concept analysis
        if hasattr(personnel, 'wr_on_field') and personnel.wr_on_field:
            if isinstance(personnel.wr_on_field, list):
                return self._get_player_name(personnel.wr_on_field[0])
            else:
                return self._get_player_name(personnel.wr_on_field)
        return "WR"
    
    def _identify_primary_rusher(self, personnel: PersonnelPackage, 
                               pass_data: PassPlayData) -> Optional[str]:
        """Identify the defender who generated the most pressure"""
        # Simplified logic - can be enhanced with detailed pressure tracking
        if hasattr(personnel, 'dl_on_field') and personnel.dl_on_field:
            if isinstance(personnel.dl_on_field, list):
                # Return strongest pass rusher (first DL for now)
                return self._get_player_name(personnel.dl_on_field[0])
            else:
                return self._get_player_name(personnel.dl_on_field)
        return "DE"
    
    def _identify_coverage_defender(self, personnel: PersonnelPackage, 
                                   pass_data: PassPlayData) -> Optional[str]:
        """Identify the defender in coverage on the primary receiver"""
        # Simplified logic based on coverage type
        if pass_data.coverage_type in ['man', 'cover_1']:
            # Man coverage - likely a CB
            if hasattr(personnel, 'cb_on_field') and personnel.cb_on_field:
                if isinstance(personnel.cb_on_field, list):
                    return self._get_player_name(personnel.cb_on_field[0])
                else:
                    return self._get_player_name(personnel.cb_on_field)
        elif pass_data.coverage_type in ['cover_2', 'cover_3']:
            # Zone coverage - could be safety help
            if hasattr(personnel, 'safety_on_field') and personnel.safety_on_field:
                if isinstance(personnel.safety_on_field, list):
                    return self._get_player_name(personnel.safety_on_field[0])
                else:
                    return self._get_player_name(personnel.safety_on_field)
        
        return "CB"
    
    def _analyze_protection_breakdowns(self, personnel: PersonnelPackage, 
                                     pass_data: PassPlayData) -> List[Dict[str, str]]:
        """Analyze which protection assignments failed"""
        breakdowns = []
        
        # If protection was poor and pressure was applied
        if pass_data.protection_effectiveness < 0.6 and pass_data.rush_advantage > 1.3:
            # Identify likely breakdown - simplified logic
            breakdown = {
                'blocker': self._get_position_player_name(personnel, 'RT'),  # Common pressure point
                'defender': self._get_position_player_name(personnel, 'DE', is_defense=True)
            }
            breakdowns.append(breakdown)
        
        return breakdowns
    
    def _identify_missed_tacklers(self, personnel: PersonnelPackage, 
                                 yards_over_expected: float) -> List[str]:
        """Identify defenders who likely missed tackles based on yards over expected"""
        missed_tacklers = []
        
        # Simplified logic - more yards over expected = more missed tackles
        if yards_over_expected > 5:
            # Likely missed a linebacker tackle
            if hasattr(personnel, 'lb_on_field') and personnel.lb_on_field:
                if isinstance(personnel.lb_on_field, list):
                    missed_tacklers.append(self._get_player_name(personnel.lb_on_field[0]))
                else:
                    missed_tacklers.append(self._get_player_name(personnel.lb_on_field))
            else:
                missed_tacklers.append("LB")
        
        return missed_tacklers
    
    def _identify_tacklers(self, personnel: PersonnelPackage, 
                          run_data: RunPlayData) -> Dict[str, Optional[str]]:
        """Identify primary and assist tacklers"""
        # Simplified logic - use defensive players based on play result
        tacklers = {'primary': None, 'assist': None}
        
        # Primary tackler logic based on yards gained and blocking success
        failed_blocks = [br for br in run_data.blocking_results if not br.success]
        
        if failed_blocks:
            # Defender who won their block likely made the tackle
            best_defender = max(failed_blocks, key=lambda br: br.impact_factor)
            tacklers['primary'] = self._get_position_player_name(
                personnel, best_defender.defender_position, is_defense=True
            )
            
            # If multiple failed blocks, secondary defender assists
            if len(failed_blocks) > 1:
                other_defenders = [br for br in failed_blocks if br != best_defender]
                assist_defender = max(other_defenders, key=lambda br: br.impact_factor)
                tacklers['assist'] = self._get_position_player_name(
                    personnel, assist_defender.defender_position, is_defense=True
                )
        else:
            # All blocks succeeded, but play was stopped - likely safety/LB cleanup
            if hasattr(personnel, 'safety_on_field') and personnel.safety_on_field:
                tacklers['primary'] = self._get_player_name(personnel.safety_on_field)
            else:
                tacklers['primary'] = "Safety"
        
        return tacklers
    
    def _identify_tfl_player(self, personnel: PersonnelPackage, 
                            blocking_results: List[BlockingResult]) -> str:
        """Identify the defender who made the tackle for loss"""
        # Find the defender who won their matchup with highest impact
        successful_defenders = [br for br in blocking_results if not br.success]
        
        if successful_defenders:
            best_defender = max(successful_defenders, key=lambda br: br.impact_factor)
            return self._get_position_player_name(
                personnel, best_defender.defender_position, is_defense=True
            )
        
        return "DT"  # Default to interior lineman for TFL
    
    def _get_base_completion_rate(self, route_concept: str, coverage_type: str) -> float:
        """Get base completion rate for route vs coverage matchup"""
        # Simplified completion rate matrix
        completion_matrix = {
            ('slant', 'man'): 0.75,
            ('slant', 'zone'): 0.65,
            ('out', 'man'): 0.65,
            ('out', 'zone'): 0.70,
            ('go', 'man'): 0.45,
            ('go', 'zone'): 0.40,
            ('comeback', 'man'): 0.70,
            ('comeback', 'zone'): 0.75,
        }
        
        return completion_matrix.get((route_concept, coverage_type), 0.60)
    
    def calculate_expected_yards(self, blocking_results: List[BlockingResult]) -> float:
        """Calculate expected yards based on blocking performance"""
        if not blocking_results:
            return 0.0
        
        # Simple expected yards calculation based on blocking success
        total_impact = sum(br.impact_factor for br in blocking_results)
        success_impact = sum(br.impact_factor for br in blocking_results if br.success)
        
        success_rate = success_impact / total_impact if total_impact > 0 else 0
        
        # Base expected yards adjusted by blocking success
        base_expected = 4.0  # Average run attempt
        return base_expected * (0.5 + success_rate)