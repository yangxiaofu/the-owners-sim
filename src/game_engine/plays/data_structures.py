from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class PlayResult:
    """Result of a single play execution with enhanced tracking"""
    # Core play information
    play_type: str        # "run", "pass", "punt", "field_goal", "kickoff"
    outcome: str          # "gain", "touchdown", "incomplete", "sack", "fumble", "interception"
    yards_gained: int     # -10 to 80+ yards
    time_elapsed: int     # seconds off clock
    is_turnover: bool     # fumble, interception
    is_score: bool        # touchdown, field goal, safety
    score_points: int     # points scored on this play (0, 2, 3, 6)
    final_field_position: Optional[int] = None  # Final field position after play (for kickoffs, punts)
    
    # Enhanced tracking information
    primary_player: Optional[str] = None      # Player who carried/caught/threw the ball
    tackler: Optional[str] = None             # Player who made the tackle
    formation: Optional[str] = None           # Offensive formation used
    defensive_call: Optional[str] = None      # Defensive scheme
    play_description: str = ""                # Human-readable play description
    
    # === COMPREHENSIVE PLAYER TRACKING ===
    quarterback: Optional[str] = None
    receiver: Optional[str] = None            # Primary receiver
    rusher: Optional[str] = None
    assist_tackler: Optional[str] = None      # Secondary tackler
    
    # === PASSING STATISTICS ===
    pass_rusher: Optional[str] = None         # Primary pass rusher
    coverage_defender: Optional[str] = None
    passes_defended_by: List[str] = field(default_factory=list)  # All DBs who defended
    quarterback_hits_by: List[str] = field(default_factory=list) # DL who hit QB
    quarterback_hurries_by: List[str] = field(default_factory=list) # DL who hurried QB
    
    # Pass protection tracking
    protection_breakdowns: List[Dict] = field(default_factory=list) # Which blocks failed
    clean_pocket: bool = False                # No pressure on QB
    
    # === RUNNING STATISTICS ===
    pancakes_by: List[str] = field(default_factory=list)        # OL who pancaked defenders
    key_blocks_by: List[str] = field(default_factory=list)      # Critical successful blocks
    missed_tackles_by: List[str] = field(default_factory=list)  # Defenders who missed tackles
    broken_tackles: int = 0                   # Number of tackles broken by RB
    
    # === DEFENSIVE STATISTICS ===  
    tackles_for_loss_by: List[str] = field(default_factory=list)
    fumbles_forced_by: Optional[str] = None
    fumbles_recovered_by: Optional[str] = None
    interceptions_by: Optional[str] = None
    
    # Context information  
    down: int = 0                            # Down when play was executed
    distance: int = 0                        # Distance needed for first down
    field_position: int = 0                  # Yard line where play started
    quarter: int = 0                         # Quarter when play occurred
    game_clock: int = 0                      # Time remaining when play started
    
    # Advanced metrics (for future use)
    pressure_applied: bool = False            # Was QB under pressure
    coverage_beaten: bool = False             # Was defender beaten on the play
    big_play: bool = False                   # 20+ yard gain
    explosive_play: bool = False             # 40+ yards
    goal_line_play: bool = False             # Play inside 10 yard line
    missed_tackle: bool = False
    perfect_protection: bool = False          # All blocks successful
    
    # === CONVERSION ATTEMPT TRACKING ===
    conversion_attempt: Optional[str] = None   # "extra_point" or "two_point" if this is a conversion
    conversion_result: Optional[str] = None    # "good" or "missed" for conversion attempts
    conversion_decision_factors: List[str] = field(default_factory=list)  # Factors that influenced 2-point decision
    
    # === MATCHUP ANALYSIS ===
    key_matchup_winner: Optional[str] = None    # Player who won critical matchup
    key_matchup_loser: Optional[str] = None     # Player who lost critical matchup
    
    # === SITUATIONAL CONTEXT ===
    down_conversion: bool = False             # Did play result in first down/TD
    red_zone_play: bool = False
    two_minute_drill: bool = False
    
    # === PENALTY TRACKING ===
    penalty_occurred: bool = False
    penalty_type: Optional[str] = None
    penalized_player: Optional[str] = None
    penalty_yards: int = 0
    penalty_automatic_first_down: bool = False
    penalty_phase: Optional[str] = None  # "pre_snap", "during_play", "post_play"
    penalty_description: str = ""
    penalty_team: Optional[str] = None   # "offense" or "defense"
    
    # Multiple penalties support
    additional_penalties: List[Dict] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Generate a human-readable summary of the play"""
        if self.play_description:
            return self.play_description
            
        # Generate basic description
        if self.play_type == "run":
            if self.outcome == "touchdown":
                return f"{self.yards_gained}-yard rushing touchdown"
            elif self.outcome == "fumble":
                return f"{self.yards_gained}-yard run, fumble"
            else:
                return f"{self.yards_gained}-yard rush"
        elif self.play_type == "pass":
            if self.outcome == "touchdown":
                return f"{self.yards_gained}-yard passing touchdown"
            elif self.outcome == "interception":
                return "Pass intercepted"
            elif self.outcome == "incomplete":
                return "Pass incomplete"
            elif self.outcome == "sack":
                return f"Sack for {abs(self.yards_gained)} yards"
            else:
                return f"{self.yards_gained}-yard pass completion"
        elif self.play_type == "field_goal":
            if self.outcome == "field_goal":
                return "Field goal good"
            else:
                return "Field goal missed"
        elif self.play_type == "punt":
            return f"{self.yards_gained}-yard punt"
        elif self.play_type == "kickoff":
            if self.outcome == "touchback":
                return f"Kickoff touchback to {self.final_field_position}-yard line"
            elif self.outcome == "touchdown":
                return f"Kickoff return for {self.yards_gained}-yard touchdown"
            elif self.outcome == "onside_recovery":
                return f"Onside kick recovered"
            elif self.outcome == "fumble":
                return f"Kickoff return, fumble"
            else:
                return f"Kickoff return for {self.yards_gained} yards"
        
        return f"{self.play_type}: {self.outcome} for {self.yards_gained} yards"
    
    def get_enhanced_summary(self) -> str:
        """Generate rich play-by-play commentary with player names and statistics"""
        
        if self.play_type == "pass":
            return self._generate_pass_commentary()
        elif self.play_type == "run":
            return self._generate_run_commentary()
        
        return self.get_summary()  # Fallback to basic summary
    
    def _generate_pass_commentary(self) -> str:
        """Generate detailed passing play commentary"""
        
        qb_name = self.quarterback or "QB"
        receiver_name = self.receiver or "receiver"
        
        if self.outcome == "gain":
            description = f"{qb_name} passes to {receiver_name} for {self.yards_gained} yards"
            if self.tackler:
                description += f", tackled by {self.tackler}"
                if self.assist_tackler:
                    description += f" and {self.assist_tackler}"
                    
        elif self.outcome == "touchdown":
            description = f"{qb_name} throws {self.yards_gained}-yard TD pass to {receiver_name}"
            
        elif self.outcome == "incomplete":
            description = f"{qb_name} passes to {receiver_name}, incomplete"
            if self.passes_defended_by:
                description += f" - pass defended by {self.passes_defended_by[0]}"
                
        elif self.outcome == "sack":
            if self.pass_rusher:
                description = f"{self.pass_rusher} sacks {qb_name} for {abs(self.yards_gained)} yards"
            else:
                description = f"{qb_name} sacked for {abs(self.yards_gained)} yards"
                
        elif self.outcome == "interception":
            if self.interceptions_by:
                description = f"{self.interceptions_by} intercepts pass from {qb_name}"
            else:
                description = f"Pass intercepted from {qb_name}"
        else:
            description = self.get_summary()
        
        # Add pressure information
        if self.quarterback_hits_by:
            description += f" - {self.quarterback_hits_by[0]} hits the quarterback"
        elif self.quarterback_hurries_by:
            description += f" - {self.quarterback_hurries_by[0]} hurries the quarterback"
        elif self.clean_pocket:
            description += " - clean pocket"
        
        # Add protection breakdown details
        if self.protection_breakdowns:
            breakdown = self.protection_breakdowns[0]
            description += f" - protection breakdown: {breakdown.get('blocker', 'blocker')} beaten by {breakdown.get('defender', 'defender')}"
        
        # Add penalty information
        if self.penalty_occurred:
            description += f" - PENALTY: {self.penalty_description}"
        
        return description
    
    def _generate_run_commentary(self) -> str:
        """Generate detailed running play commentary"""
        
        rusher_name = self.rusher or "RB"
        
        if self.outcome == "gain":
            description = f"{rusher_name} rushes for {self.yards_gained} yards"
            if self.tackler:
                description += f", tackled by {self.tackler}"
                if self.assist_tackler:
                    description += f" and {self.assist_tackler}"
                    
        elif self.outcome == "touchdown":
            description = f"{rusher_name} rushes for {self.yards_gained}-yard touchdown"
        elif self.outcome == "fumble":
            description = f"{rusher_name} rushes for {self.yards_gained} yards, fumble"
            if self.fumbles_forced_by:
                description += f" forced by {self.fumbles_forced_by}"
        else:
            description = self.get_summary()
        
        # Add blocking highlights
        if self.pancakes_by:
            description += f" - {self.pancakes_by[0]} pancakes his defender"
        elif self.key_blocks_by:
            description += f" - key block by {self.key_blocks_by[0]}"
        
        # Add RB performance details
        if self.broken_tackles > 0:
            description += f" - breaks {self.broken_tackles} tackle{'s' if self.broken_tackles > 1 else ''}"
        
        if self.missed_tackles_by:
            description += f" - {self.missed_tackles_by[0]} misses the tackle"
        
        # Add negative plays
        if self.tackles_for_loss_by:
            description += f" - tackled for loss by {self.tackles_for_loss_by[0]}"
        
        # Add penalty information
        if self.penalty_occurred:
            description += f" - PENALTY: {self.penalty_description}"
        
        return description