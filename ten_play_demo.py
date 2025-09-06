#!/usr/bin/env python3
"""
Quarter Simulation Demo - Browns vs 49ers

Simulates a full quarter of NFL gameplay between Cleveland Browns and San Francisco 49ers,
with integrated possession tracking, timestamps, field position tracking, and 
scoreboard updates.
"""

import sys
import os
import random

# Add src directory to Python path  
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from constants.team_ids import TeamIDs
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from play_engine.core.engine import simulate
from play_engine.core.params import PlayEngineParams
from play_engine.play_calls.play_call_factory import PlayCallFactory
from play_engine.play_calls.offensive_play_call import OffensivePlayCall
from play_engine.play_calls.defensive_play_call import DefensivePlayCall
from play_engine.game_state.field_position import FieldPosition, FieldTracker, FieldZone
from play_engine.game_state.game_state_manager import GameStateManager, GameState
from play_engine.game_state.down_situation import DownState
from play_engine.simulation.stats import PlayStatsSummary, PlayerStatsAccumulator
from game_management.scoreboard import Scoreboard, ScoringType
from game_management.scoring_mapper import ScoringTypeMapper
from play_engine.game_state.drive_manager import (
    DriveManager, DriveManagerParams, DriveAssessmentResult, 
    ScoreContext, DriveEndReason, DriveStatus
)
from play_engine.game_state.game_clock import GameClock
from play_engine.game_state.possession_manager import PossessionManager, PossessionChange


# Using GameClock for proper NFL timing and quarter management


class DriveBasedDemo:
    """Main demo class for quarter-based simulation with comprehensive drive and possession management"""
    
    def __init__(self):
        """Initialize demo with teams, scoreboard, drive manager, and game state"""
        print("🏈 Quarter Simulation Demo: Cleveland Browns vs San Francisco 49ers")
        print("=" * 60)
        
        # Initialize teams
        self.setup_teams()
        
        # Initialize scoreboard
        self.setup_scoreboard()
        
        # Initialize drive manager and comprehensive game state
        self.setup_drive_manager()
        
        # Initialize field tracking and game state
        self.setup_game_state()
        
        # Initialize play factory
        self.play_factory = PlayCallFactory()
        
        # Initialize player stats accumulator for the game
        game_id = f"Browns_vs_49ers_Q{self.game_clock.quarter}"
        self.player_stats_accumulator = PlayerStatsAccumulator(game_id)
        
        print(f" Game initialized - {self.get_team_name(self.home_team)} vs {self.get_team_name(self.away_team)}")
        print(f"=� Starting position: {self.current_game_state.field_position.yard_line}-yard line")
        print(f"=� Initial score: {self.scoreboard}")
        print()
    
    def setup_teams(self):
        """Set up Lions and Packers teams with rosters"""
        self.home_team = TeamIDs.CLEVELAND_BROWNS
        self.away_team = TeamIDs.SAN_FRANCISCO_49ERS
        
        print(f">� Generating {self.get_team_name(self.home_team)} roster...")
        self.home_roster = TeamRosterGenerator.generate_sample_roster(self.home_team)
        self.home_personnel = PersonnelPackageManager(self.home_roster)
        
        print(f">� Generating {self.get_team_name(self.away_team)} roster...")
        self.away_roster = TeamRosterGenerator.generate_sample_roster(self.away_team)
        self.away_personnel = PersonnelPackageManager(self.away_roster)
    
    def setup_scoreboard(self):
        """Initialize scoreboard for Lions vs Packers"""
        self.scoreboard = Scoreboard(self.home_team, self.away_team)
    
    def setup_drive_manager(self):
        """Initialize drive manager and comprehensive game context"""
        # Initialize drive manager
        self.drive_manager = DriveManager()
        
        # Initialize possession manager with Browns starting possession
        self.possession_manager = PossessionManager(str(self.home_team))
        
        # Initialize game clock starting at Q1 15:00
        self.game_clock = GameClock(
            quarter=1, 
            time_remaining_seconds=900  # 15:00 in seconds
        )
        
        # Initialize score context (starts 0-0, Browns are home team)
        self.score_context = ScoreContext(
            home_score=0,
            away_score=0,
            possessing_team_is_home=True  # Browns start with possession
        )
        
        # Track drives for statistics
        self.total_drives_completed = 0
        # No more drive target - simulation runs until end of quarter
    
    def setup_game_state(self):
        """Initialize field position and game state tracking"""
        # Start at Browns 25-yard line (typical kickoff position)
        starting_position = FieldPosition(
            yard_line=25,
            possession_team=str(self.home_team),
            field_zone=FieldZone.OWN_GOAL_LINE
        )
        
        starting_down_state = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=35  # 25 + 10 yards for first down
        )
        
        self.current_game_state = GameState(
            field_position=starting_position,
            down_state=starting_down_state,
            possessing_team=str(self.home_team)
        )
        
        self.field_tracker = FieldTracker()
        self.game_state_manager = GameStateManager()
    
    
    def get_team_name(self, team_id):
        """Get team name for display"""
        if team_id == TeamIDs.CLEVELAND_BROWNS:
            return "Browns"
        elif team_id == TeamIDs.SAN_FRANCISCO_49ERS:
            return "49ers"
        else:
            return f"Team {team_id}"
    
    def get_possession_team_name(self):
        """Get name of team currently in possession"""
        possession_id = int(self.possession_manager.get_possessing_team())
        return self.get_team_name(possession_id)
    
    def select_random_play(self):
        """Select situationally-aware offensive and defensive plays"""
        from play_engine.play_types.offensive_types import OffensivePlayType
        from play_engine.play_types.defensive_types import DefensivePlayType
        from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
        
        # Get current situation
        down = self.current_game_state.down_state.current_down
        yards_to_go = self.current_game_state.down_state.yards_to_go
        field_position = self.current_game_state.field_position.yard_line
        
        # Situational play selection
        if down == 4:
            # 4th down situations
            if field_position >= 60 and field_position <= 85:
                # Field goal range
                offensive_options = [
                    {
                        "name": "Field Goal Attempt",
                        "play_type": OffensivePlayType.PASS,  # Simplified as pass for now
                        "formation": OffensiveFormation.I_FORMATION,
                        "concept": "field_goal"
                    }
                ]
            elif yards_to_go <= 2:
                # Short yardage - run heavy
                offensive_options = [
                    {
                        "name": "Power Run",
                        "play_type": OffensivePlayType.RUN,
                        "formation": OffensiveFormation.I_FORMATION,
                        "concept": "power"
                    },
                    {
                        "name": "QB Sneak",
                        "play_type": OffensivePlayType.RUN,
                        "formation": OffensiveFormation.I_FORMATION,
                        "concept": "sneak"
                    }
                ]
            else:
                # Punt or desperation pass
                offensive_options = [
                    {
                        "name": "Punt",
                        "play_type": OffensivePlayType.PASS,  # Simplified as pass for now
                        "formation": OffensiveFormation.I_FORMATION,
                        "concept": "punt"
                    },
                    {
                        "name": "Hail Mary",
                        "play_type": OffensivePlayType.PASS,
                        "formation": OffensiveFormation.FOUR_WIDE,
                        "concept": "verticals"
                    }
                ]
        elif down == 3 and yards_to_go >= 7:
            # 3rd and long - pass heavy
            offensive_options = [
                {
                    "name": "Quick Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.SHOTGUN,
                    "concept": "slants"
                },
                {
                    "name": "Deep Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.FOUR_WIDE,
                    "concept": "verticals"
                },
                {
                    "name": "Screen Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.SHOTGUN,
                    "concept": "screen"
                }
            ]
        elif down == 3 and yards_to_go <= 3:
            # 3rd and short - balanced
            offensive_options = [
                {
                    "name": "Power Run",
                    "play_type": OffensivePlayType.RUN,
                    "formation": OffensiveFormation.I_FORMATION,
                    "concept": "power"
                },
                {
                    "name": "Quick Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.SHOTGUN,
                    "concept": "slants"
                }
            ]
        elif down <= 2:
            # Early downs - balanced but slightly run heavy
            offensive_options = [
                {
                    "name": "Power Run",
                    "play_type": OffensivePlayType.RUN,
                    "formation": OffensiveFormation.I_FORMATION,
                    "concept": "power"
                },
                {
                    "name": "Sweep Run", 
                    "play_type": OffensivePlayType.RUN,
                    "formation": OffensiveFormation.I_FORMATION,
                    "concept": "sweep"
                },
                {
                    "name": "Quick Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.SHOTGUN,
                    "concept": "slants"
                },
                {
                    "name": "Play Action",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.I_FORMATION,
                    "concept": "play_action"
                }
            ]
        else:
            # Default options
            offensive_options = [
                {
                    "name": "Power Run",
                    "play_type": OffensivePlayType.RUN,
                    "formation": OffensiveFormation.I_FORMATION,
                    "concept": "power"
                },
                {
                    "name": "Quick Pass",
                    "play_type": OffensivePlayType.PASS,
                    "formation": OffensiveFormation.SHOTGUN,
                    "concept": "slants"
                }
            ]
        
        # Defensive play selection based on down and distance
        if down == 4:
            defensive_options = [
                {
                    "name": "Punt Block",
                    "play_type": DefensivePlayType.COVER_2,
                    "formation": DefensiveFormation.FOUR_THREE,
                    "coverage": "zone"
                }
            ]
        elif down == 3 and yards_to_go >= 7:
            # 3rd and long - pass defense
            defensive_options = [
                {
                    "name": "Nickel Coverage",
                    "play_type": DefensivePlayType.COVER_3,
                    "formation": DefensiveFormation.NICKEL,
                    "coverage": "zone"
                },
                {
                    "name": "Man Coverage",
                    "play_type": DefensivePlayType.MAN_COVERAGE,
                    "formation": DefensiveFormation.NICKEL,
                    "coverage": "man"
                }
            ]
        else:
            # Standard defensive options
            defensive_options = [
                {
                    "name": "4-3 Base",
                    "play_type": DefensivePlayType.COVER_2,
                    "formation": DefensiveFormation.FOUR_THREE,
                    "coverage": "zone"
                },
                {
                    "name": "Nickel Coverage",
                    "play_type": DefensivePlayType.COVER_3,
                    "formation": DefensiveFormation.NICKEL,
                    "coverage": "zone"  
                },
                {
                    "name": "Man Coverage",
                    "play_type": DefensivePlayType.MAN_COVERAGE,
                    "formation": DefensiveFormation.FOUR_THREE,
                    "coverage": "man"
                }
            ]
        
        # Select random plays from situational options
        selected_offensive = random.choice(offensive_options)
        selected_defensive = random.choice(defensive_options)
        
        # Create play calls
        offensive_play_call = OffensivePlayCall(
            play_type=selected_offensive["play_type"],
            formation=selected_offensive["formation"],
            concept=selected_offensive["concept"]
        )
        
        defensive_play_call = DefensivePlayCall(
            play_type=selected_defensive["play_type"],
            formation=selected_defensive["formation"],
            coverage=selected_defensive["coverage"]
        )
        
        return {
            "offensive": {
                "name": selected_offensive["name"],
                "play_call": offensive_play_call
            },
            "defensive": {
                "name": selected_defensive["name"],
                "play_call": defensive_play_call
            }
        }
    
    def execute_play(self, play_calls):
        """Execute the play and get results"""
        # Determine which team has possession using PossessionManager
        possession_id = int(self.possession_manager.get_possessing_team())
        
        if possession_id == self.home_team:
            offensive_team = self.home_team
            defensive_team = self.away_team
            offensive_personnel = self.home_personnel
            defensive_personnel = self.away_personnel
        else:
            offensive_team = self.away_team
            defensive_team = self.home_team  
            offensive_personnel = self.away_personnel
            defensive_personnel = self.home_personnel
        
        # Get personnel for formations
        offensive_players = offensive_personnel.get_offensive_personnel(
            play_calls["offensive"]["play_call"].get_formation()
        )
        defensive_players = defensive_personnel.get_defensive_personnel(
            play_calls["defensive"]["play_call"].get_formation()
        )
        
        # Create play engine params
        play_params = PlayEngineParams(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_play_call=play_calls["offensive"]["play_call"],
            defensive_play_call=play_calls["defensive"]["play_call"]
        )
        
        # Execute the play
        play_result = simulate(play_params)
        
        return play_result, offensive_team
    
    def update_game_state(self, play_result):
        """Update game state using GameStateManager for field position and down tracking"""
        # Create PlayStatsSummary from PlayResult using engine's timing
        play_summary = PlayStatsSummary(
            play_type=play_result.outcome,
            yards_gained=play_result.yards,
            time_elapsed=play_result.time_elapsed  # Use engine's realistic timing
        )
        
        # Process through GameStateManager for comprehensive state updates
        game_state_result = self.game_state_manager.process_play(
            self.current_game_state,
            play_summary
        )
        
        return game_state_result
    
    def handle_scoring(self, field_result, scoring_team_id):
        """Handle scoring and update scoreboard"""
        if field_result.is_scored:
            scoring_type = ScoringTypeMapper.from_field_result(field_result.scoring_type)
            if scoring_type:
                # For safety, points go to the opposing team
                if field_result.scoring_type == "safety":
                    if scoring_team_id == self.home_team:
                        actual_scoring_team = self.away_team
                    else:
                        actual_scoring_team = self.home_team
                else:
                    actual_scoring_team = scoring_team_id
                
                self.scoreboard.add_score(
                    actual_scoring_team,
                    scoring_type,
                    f"{field_result.scoring_type.title()}"
                )
                
                return True, field_result.scoring_type, field_result.points_scored
        
        return False, None, 0
    
    def handle_possession_change(self, game_state_result):
        """Handle possession changes due to turnover on downs, scoring, etc."""
        if game_state_result.down_result.turnover_on_downs:
            # Turnover on downs - flip possession
            current_possession = int(self.current_game_state.possessing_team)
            new_possession = self.away_team if current_possession == self.home_team else self.home_team
            
            # Create new game state with flipped field position
            new_field_position = FieldPosition(
                yard_line=100 - game_state_result.field_result.new_field_position.yard_line,
                possession_team=str(new_possession),
                field_zone=game_state_result.field_result.new_field_position.field_zone
            )
            
            # Create new drive starting at this position
            new_down_state = self.game_state_manager.down_tracker.create_new_drive(new_field_position.yard_line)
            
            self.current_game_state = GameState(
                field_position=new_field_position,
                down_state=new_down_state,
                possessing_team=str(new_possession)
            )
        
        elif game_state_result.scoring_occurred:
            # Scoring play - would typically lead to kickoff (simplified for demo)
            # For demo purposes, just continue with current possession
            pass
    
    def format_down_distance(self, down_state):
        """Format down and distance display (e.g., '1st & 10', '3rd & 3')"""
        ordinal_map = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        down_text = ordinal_map.get(down_state.current_down, f"{down_state.current_down}th")
        return f"{down_text} & {down_state.yards_to_go}"
    
    def display_down_progression(self, game_state_result):
        """Display down progression results"""
        if game_state_result.down_result.first_down_achieved:
            print("   ⭐ FIRST DOWN! Reset to 1st & 10")
        elif game_state_result.down_result.turnover_on_downs:
            print("   🔄 TURNOVER ON DOWNS! Possession changes")
        elif game_state_result.new_game_state:
            # Show new down situation
            new_down = self.format_down_distance(game_state_result.new_game_state.down_state)
            print(f"   Down Progression: Now {new_down}")
    
    def display_possession_change_if_occurred(self):
        """Display possession change with timestamp if one occurred recently"""
        recent_changes = self.possession_manager.get_recent_possession_changes(1)
        if recent_changes:
            change = recent_changes[0]
            timestamp_str = change.timestamp.strftime("%H:%M:%S.%f")[:-3]  # Format with milliseconds
            old_team_name = self.get_team_name(int(change.previous_team))
            new_team_name = self.get_team_name(int(change.new_team))
            print(f"   🔄 POSSESSION CHANGE [{timestamp_str}]: {old_team_name} → {new_team_name} ({change.reason})")
    
    def display_play_result(self, play_num, play_calls, play_result, game_state_result, 
                           scoring_info, offensive_team):
        """Display comprehensive play results"""
        print(f"<� PLAY {play_num}: {self.get_possession_team_name()} at {self.current_game_state.field_position.yard_line}-yard line")
        print(f"   {play_calls['offensive']['name'].replace('_', ' ').title()} vs {play_calls['defensive']['name'].replace('_', ' ').title()}")
        offensive_formation = str(play_calls['offensive']['play_call'].get_formation()).replace('_', ' ').title()
        defensive_formation = str(play_calls['defensive']['play_call'].get_formation()).replace('_', ' ').title()
        print(f"   Formation: {offensive_formation} vs {defensive_formation}")
        # Show time elapsed and result with player information
        time_elapsed = game_state_result.play_summary.time_elapsed
        key_players = play_result.get_key_players()
        player_info = f" | {key_players}" if key_players else ""
        print(f"   Result: {play_result.outcome}, {play_result.yards:+d} yards ({time_elapsed:.1f} seconds){player_info}")
        
        # Show down progression
        self.display_down_progression(game_state_result)
        
        # Show field position change
        old_yard_line = self.current_game_state.field_position.yard_line
        new_yard_line = game_state_result.field_result.new_field_position.yard_line
        print(f"   Field Position: {old_yard_line}-yard line � {new_yard_line}-yard line")
        
        # Show scoring if occurred
        scored, scoring_type, points = scoring_info
        if scored:
            scoring_team_name = self.get_team_name(self.scoreboard.get_leading_team() if not self.scoreboard.is_tied() else offensive_team)
            print(f"   <� SCORE! {scoring_type.upper()} for {scoring_team_name} (+{points} points)")
        
        # Show current scoreboard
        browns_score = self.scoreboard.get_team_score(self.home_team)
        niners_score = self.scoreboard.get_team_score(self.away_team)
        print(f"   =📊 Scoreboard: Browns {browns_score}, 49ers {niners_score}")
        
        print()
    
    def advance_game_clock(self, seconds_elapsed: float):
        """Advance the game clock by specified seconds using proper GameClock"""
        clock_result = self.game_clock.advance_time(seconds_elapsed)
        
        # Handle clock events from the sophisticated GameClock
        if clock_result.clock_events:
            for event in clock_result.clock_events:
                print(f"        ⏰ {event}")
        
        # Handle quarter transitions
        if clock_result.quarter_ended:
            if clock_result.quarter_started:
                print(f"        🏈 Starting Q{clock_result.quarter_started}")
        
        # Handle two-minute warning
        if clock_result.two_minute_warning:
            print(f"        ⚠️  Two-minute warning!")
        
        return clock_result
    
    def update_score_context(self):
        """Update score context from current scoreboard"""
        home_score = self.scoreboard.get_team_score(self.home_team)
        away_score = self.scoreboard.get_team_score(self.away_team)
        possessing_team_id = int(self.possession_manager.get_possessing_team())
        possessing_team_is_home = (possessing_team_id == self.home_team)
        
        self.score_context = ScoreContext(
            home_score=home_score,
            away_score=away_score,
            possessing_team_is_home=possessing_team_is_home
        )
    
    def start_new_drive(self, drive_number: int):
        """Start a new drive with clean header"""
        # Determine starting field position (simplified - usually kickoff at 25)
        starting_position = 25
        possessing_team = self.possession_manager.get_possessing_team()
        
        # Clean drive header
        team_name = self.get_team_name(int(possessing_team))
        game_time = self.game_clock.get_time_display()
        browns_score = self.scoreboard.get_team_score(self.home_team)
        niners_score = self.scoreboard.get_team_score(self.away_team)
        
        print(f"\n🏈 DRIVE {drive_number} - {team_name} at {starting_position}-yard line - {game_time} (Browns {browns_score}, 49ers {niners_score})")
        
        # Start the drive in DriveManager
        self.drive_manager.start_new_drive(
            starting_position=starting_position,
            possessing_team=possessing_team,
            starting_quarter=self.game_clock.quarter,
            starting_time=self.game_clock.time_remaining_seconds
        )
    
    def run_drive(self):
        """Run plays until the current drive ends"""
        play_number_in_drive = 0
        
        while self.drive_manager.has_active_drive():
            play_number_in_drive += 1
            
            # Select and execute play
            play_calls = self.select_random_play()
            play_result, offensive_team = self.execute_play(play_calls)
            
            # Update game state
            game_state_result = self.update_game_state(play_result)
            
            # Accumulate player stats for the game
            self.player_stats_accumulator.add_play_stats(game_state_result.play_summary)
            
            # Advance game clock
            self.advance_game_clock(game_state_result.play_summary.time_elapsed)
            
            # Update score context
            self.update_score_context()
            
            # Handle scoring
            scoring_info = self.handle_scoring(game_state_result.field_result, offensive_team)
            
            # Create DriveManagerParams for drive assessment
            drive_params = DriveManagerParams(
                game_state_result=game_state_result,
                game_clock=self.game_clock,
                score_context=self.score_context,
                field_position=game_state_result.field_result.new_field_position.yard_line,
                possessing_team=self.possession_manager.get_possessing_team()
            )
            
            # Assess drive status
            drive_result = self.drive_manager.assess_drive_status(drive_params)
            
            # Display clean play result
            self.display_clean_play(
                play_number_in_drive, play_calls, play_result, game_state_result,
                scoring_info, offensive_team, drive_result
            )
            
            # Update game state for next play or handle drive end
            if drive_result.drive_continues:
                if game_state_result.new_game_state is not None:
                    self.current_game_state = game_state_result.new_game_state
            else:
                # Drive ended
                self.handle_drive_end(drive_result)
                break
    
    def should_end_quarter(self) -> bool:
        """Check if quarter should end (time expiration)"""
        return self.game_clock.is_end_of_quarter
    
    def handle_drive_end(self, drive_result: DriveAssessmentResult):
        """Handle the end of a drive with minimal output"""
        self.total_drives_completed += 1
        
        # Handle possession change for next drive using PossessionManager
        if drive_result.next_possession_team and not self.should_end_quarter():
            # Switch possession
            if drive_result.next_possession_team == "Opponent":
                # Simple logic: switch possession
                current_team = int(self.possession_manager.get_possessing_team())
                new_team = self.away_team if current_team == self.home_team else self.home_team
                # Update possession manager with reason
                drive_reason = drive_result.end_reason.value.replace('_', ' ').title()
                self.possession_manager.change_possession(str(new_team), drive_reason)
            else:
                new_team = current_team  # Keep current possession (like after safety)
            
            # Create new starting position for next drive
            new_field_position = FieldPosition(
                yard_line=25,  # Typical kickoff position
                possession_team=str(new_team),
                field_zone=FieldZone.OWN_GOAL_LINE
            )
            
            new_down_state = DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=35
            )
            
            self.current_game_state = GameState(
                field_position=new_field_position,
                down_state=new_down_state,
                possessing_team=str(new_team)
            )
    
    def display_clean_play(self, play_num, play_calls, play_result, game_state_result, 
                          scoring_info, offensive_team, drive_result):
        """Display clean single-line play-by-play for flow assessment"""
        # Get current down and distance
        down_text = self.format_down_distance(self.current_game_state.down_state)
        
        # Get play type (simplified)
        play_type = "RUN" if "run" in play_result.outcome.lower() else "PASS"
        
        # Get game clock
        game_time_str = self.game_clock.get_time_display()
        
        # Get player information
        key_players = play_result.get_key_players()
        player_info = f" | {key_players}" if key_players else ""
        
        # Check for first down
        first_down_note = ""
        if game_state_result.down_result.first_down_achieved:
            first_down_note = " (FIRST DOWN)"
        
        # Check for scoring
        scored, scoring_type, points = scoring_info
        if scored:
            scoring_team_name = self.get_team_name(offensive_team)
            first_down_note = f" 🏆 {scoring_type.upper()}!"
        
        # Single line output
        print(f"{down_text} - {play_type} - {play_result.yards:+d} yards - {game_time_str}{player_info}{first_down_note}")
        
        # Show possession change or drive end if applicable
        if not drive_result.drive_continues:
            reason = drive_result.end_reason.value.replace('_', ' ').title()
            print(f"  → Drive ends: {reason}")
    
    def run_simulation(self):
        """Run the quarter-based simulation"""
        print("🚀 Starting Q1 simulation (15:00)...")
        print("-" * 40)
        
        while not self.should_end_quarter():
            # Start a new drive
            drive_number = self.total_drives_completed + 1
            self.start_new_drive(drive_number)
            
            # Run plays until drive ends
            self.run_drive()
            
            # Check if quarter should end (time expiration)
            if self.should_end_quarter():
                print("\n⏰ END OF QUARTER 1 - Time Expired!")
                break
        
        self.display_final_results()
    
    def display_final_results(self):
        """Display final game summary"""
        print("🏁 FINAL GAME RESULTS")
        print("=" * 60)
        
        # Show score with team names instead of IDs
        browns_score = self.scoreboard.get_team_score(self.home_team)
        niners_score = self.scoreboard.get_team_score(self.away_team)
        print(f"Final Score: Browns {browns_score}, 49ers {niners_score}")
        
        if self.scoreboard.is_tied():
            print("> Game ended in a tie!")
        else:
            leading_team_id = self.scoreboard.get_leading_team()
            leading_team_name = self.get_team_name(leading_team_id)
            score_difference = self.scoreboard.get_score_difference()
            print(f"<� {leading_team_name} win by {score_difference} points!")
        
        # Show scoring history
        history = self.scoreboard.get_scoring_history()
        if history:
            print(f"\n=� Scoring Summary ({len(history)} scoring plays):")
            for i, event in enumerate(history, 1):
                team_name = self.get_team_name(event.team_id)
                print(f"  {i}. {team_name} {event.scoring_type.name} ({event.points} pts)")
                if event.description:
                    print(f"     {event.description}")
        
        # Drive history analysis  
        drive_history = self.drive_manager.get_drive_history()
        if drive_history:
            print(f"\n📈 DRIVE SUMMARY ({len(drive_history)} completed drives):")
            
            # Drive-by-drive breakdown
            browns_drives = []
            niners_drives = []
            
            for i, drive in enumerate(drive_history, 1):
                team_name = self.get_team_name(int(drive.possessing_team)) if drive.possessing_team.isdigit() else drive.possessing_team
                end_reason = drive.end_reason.value.replace('_', ' ').title() if drive.end_reason else "Ongoing"
                
                print(f"  Drive {i}: {team_name}")
                print(f"    Result: {end_reason}")
                print(f"    Stats: {drive.stats.plays_run} plays, {drive.stats.total_yards} yards")
                print(f"    Time: {drive.stats.time_of_possession_seconds}s possession")
                
                if int(drive.possessing_team) == self.home_team:
                    browns_drives.append(drive)
                else:
                    niners_drives.append(drive)
            
            # Team drive statistics
            print(f"\n📋 TEAM DRIVE STATISTICS:")
            self.display_team_drive_stats("Browns", browns_drives)
            self.display_team_drive_stats("49ers", niners_drives)
            
            # Game efficiency metrics
            print(f"\n⚡ EFFICIENCY METRICS:")
            total_plays = sum(drive.stats.plays_run for drive in drive_history)
            total_yards = sum(drive.stats.total_yards for drive in drive_history)
            avg_yards_per_play = total_yards / total_plays if total_plays > 0 else 0
            
            print(f"  Total Plays: {total_plays}")
            print(f"  Total Yards: {total_yards}")
            print(f"  Average Yards per Play: {avg_yards_per_play:.1f}")
            
            scoring_drives = len([d for d in drive_history if d.end_reason in [DriveEndReason.TOUCHDOWN, DriveEndReason.FIELD_GOAL]])
            scoring_pct = (scoring_drives / len(drive_history)) * 100 if drive_history else 0
            print(f"  Scoring Drives: {scoring_drives}/{len(drive_history)} ({scoring_pct:.1f}%)")
        
        # Add comprehensive possession analysis
        self.display_possession_summary()
        
        # Add simple prompt for player stats testing
        print(f"\n🔍 View player stats? (y/n): ", end="")
        try:
            user_input = input().strip().lower()
            if user_input.startswith('y'):
                self.show_player_stats_menu()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting stats menu.")
    
    def display_team_drive_stats(self, team_name: str, drives):
        """Display comprehensive team drive statistics"""
        if not drives:
            print(f"  {team_name}: No completed drives")
            return
        
        total_plays = sum(drive.stats.plays_run for drive in drives)
        total_yards = sum(drive.stats.total_yards for drive in drives)
        total_time = sum(drive.stats.time_of_possession_seconds for drive in drives)
        
        # Drive outcomes
        touchdowns = len([d for d in drives if d.end_reason == DriveEndReason.TOUCHDOWN])
        field_goals = len([d for d in drives if d.end_reason == DriveEndReason.FIELD_GOAL])
        turnovers = len([d for d in drives if d.end_reason in [DriveEndReason.TURNOVER_INTERCEPTION, DriveEndReason.TURNOVER_FUMBLE]])
        punts = len([d for d in drives if d.end_reason == DriveEndReason.PUNT])
        turnover_on_downs = len([d for d in drives if d.end_reason == DriveEndReason.TURNOVER_ON_DOWNS])
        
        avg_plays_per_drive = total_plays / len(drives) if drives else 0
        avg_yards_per_drive = total_yards / len(drives) if drives else 0
        avg_time_per_drive = total_time / len(drives) if drives else 0
        
        print(f"  {team_name}: {len(drives)} drives")
        print(f"    Avg per drive: {avg_plays_per_drive:.1f} plays, {avg_yards_per_drive:.1f} yards, {avg_time_per_drive:.0f}s")
        print(f"    Outcomes: {touchdowns} TD, {field_goals} FG, {turnovers} TO, {punts} punts, {turnover_on_downs} failed 4th downs")
    
    def display_possession_summary(self):
        """Display comprehensive possession tracking summary with timestamps"""
        print(f"\n🔄 POSSESSION TRACKING SUMMARY:")
        
        # Show possession counts
        browns_possessions = self.possession_manager.get_possession_count(str(self.home_team))
        niners_possessions = self.possession_manager.get_possession_count(str(self.away_team))
        total_possessions = browns_possessions + niners_possessions
        
        print(f"  Total Possessions: {total_possessions}")
        print(f"    Browns: {browns_possessions} ({(browns_possessions/total_possessions*100):.1f}%)" if total_possessions > 0 else "    Browns: 0 (0.0%)")
        print(f"    49ers: {niners_possessions} ({(niners_possessions/total_possessions*100):.1f}%)" if total_possessions > 0 else "    49ers: 0 (0.0%)")
        
        # Show possession history with timestamps
        possession_history = self.possession_manager.get_possession_history()
        if possession_history:
            print(f"\n  📅 Possession Changes ({len(possession_history)} changes):")
            for i, change in enumerate(possession_history, 1):
                timestamp_str = change.timestamp.strftime("%H:%M:%S.%f")[:-3]
                old_team_name = self.get_team_name(int(change.previous_team))
                new_team_name = self.get_team_name(int(change.new_team))
                print(f"    {i}. [{timestamp_str}] {old_team_name} → {new_team_name} ({change.reason})")
        else:
            print(f"\n  No possession changes during quarter")
        
        # Show final possession
        final_possessing_team = self.get_team_name(int(self.possession_manager.get_possessing_team()))
        print(f"\n  Final Possession: {final_possessing_team}")
    
    def show_player_stats_menu(self):
        """Simple terminal selection for testing player stats"""
        while True:
            print(f"\n📊 PLAYER STATS TESTING")
            print("1. Show all players with stats")
            print("2. Look up specific player")  
            print("3. Show stats summary")
            print("4. Back to game")
            
            choice = input("Choice (1-4): ").strip()
            
            if choice == "1":
                self._display_all_players()
            elif choice == "2":
                name = input("Enter player name: ").strip()
                self._display_player_lookup(name)
            elif choice == "3":
                self._display_stats_summary()
            elif choice == "4":
                break
            else:
                print("Invalid choice. Please enter 1-4.")
    
    def _display_all_players(self):
        """Show all players with stats - for testing"""
        players = self.player_stats_accumulator.get_all_players_with_stats()
        if not players:
            print("No player stats recorded yet.")
            return
        
        print(f"\nPlayers with stats ({len(players)} total):")
        for player in sorted(players, key=lambda x: x.position):
            key_stats = player.get_total_stats()
            print(f"  {player.get_player_summary()}: {len(key_stats)} stat categories")
            # Show a few key stats for quick overview
            if key_stats:
                sample_stats = []
                if player.carries > 0:
                    sample_stats.append(f"{player.carries} carries, {player.rushing_yards} yards")
                if player.pass_attempts > 0:
                    comp_pct = (player.completions / player.pass_attempts * 100) if player.pass_attempts > 0 else 0
                    sample_stats.append(f"{player.completions}/{player.pass_attempts} ({comp_pct:.1f}%), {player.passing_yards} yards")
                if player.receptions > 0:
                    sample_stats.append(f"{player.receptions} rec, {player.receiving_yards} yards")
                if player.tackles > 0 or player.assisted_tackles > 0:
                    total_tackles = player.tackles + player.assisted_tackles
                    sample_stats.append(f"{total_tackles} tackles")
                if sample_stats:
                    print(f"    Key stats: {'; '.join(sample_stats)}")
    
    def _display_player_lookup(self, name: str):
        """Look up specific player - for testing"""
        if not name:
            print("Please enter a player name.")
            return
            
        # Simple search through accumulated players
        found_players = []
        for player in self.player_stats_accumulator.get_all_players_with_stats():
            if name.lower() in player.player_name.lower():
                found_players.append(player)
        
        if found_players:
            for player in found_players:
                stats = player.get_total_stats()
                print(f"\n{player.get_player_summary()}:")
                if stats:
                    for stat_name, value in stats.items():
                        readable_name = stat_name.replace('_', ' ').title()
                        print(f"  {readable_name}: {value}")
                else:
                    print("  No stats recorded")
        else:
            print(f"No player found matching '{name}'")
    
    def _display_stats_summary(self):
        """Show overall stats summary - for testing"""
        total_players = self.player_stats_accumulator.get_player_count()
        total_plays = self.player_stats_accumulator.get_plays_processed()
        
        print(f"\n📈 GAME STATS SUMMARY")
        print(f"Total players with stats: {total_players}")
        print(f"Total plays processed: {total_plays}")
        
        if total_players > 0:
            # Show position breakdown
            positions = {}
            for player in self.player_stats_accumulator.get_all_players_with_stats():
                pos = player.position
                positions[pos] = positions.get(pos, 0) + 1
            
            print(f"\nPosition breakdown:")
            for position, count in sorted(positions.items()):
                print(f"  {position}: {count} players")
            
            # Show some leading performers if available
            print(f"\nLeading performers:")
            all_players = self.player_stats_accumulator.get_all_players_with_stats()
            
            # Leading rusher
            rushers = [p for p in all_players if p.carries > 0]
            if rushers:
                leading_rusher = max(rushers, key=lambda x: x.rushing_yards)
                avg = leading_rusher.rushing_yards / leading_rusher.carries if leading_rusher.carries > 0 else 0
                print(f"  Rushing: {leading_rusher.player_name} - {leading_rusher.carries} carries, {leading_rusher.rushing_yards} yards ({avg:.1f} avg)")
            
            # Leading passer
            passers = [p for p in all_players if p.pass_attempts > 0]
            if passers:
                leading_passer = max(passers, key=lambda x: x.passing_yards)
                comp_pct = (leading_passer.completions / leading_passer.pass_attempts * 100) if leading_passer.pass_attempts > 0 else 0
                print(f"  Passing: {leading_passer.player_name} - {leading_passer.completions}/{leading_passer.pass_attempts} ({comp_pct:.1f}%), {leading_passer.passing_yards} yards")
            
            # Leading receiver
            receivers = [p for p in all_players if p.receptions > 0]
            if receivers:
                leading_receiver = max(receivers, key=lambda x: x.receiving_yards)
                print(f"  Receiving: {leading_receiver.player_name} - {leading_receiver.receptions} rec, {leading_receiver.receiving_yards} yards")
            
            # Leading tackler
            tacklers = [p for p in all_players if p.tackles > 0 or p.assisted_tackles > 0]
            if tacklers:
                leading_tackler = max(tacklers, key=lambda x: x.tackles + (x.assisted_tackles * 0.5))
                total_tackles = leading_tackler.tackles + leading_tackler.assisted_tackles
                print(f"  Tackling: {leading_tackler.player_name} - {total_tackles} tackles ({leading_tackler.tackles} solo)")


def main():
    """Run the quarter-based Browns vs 49ers demo"""
    # Set random seed for reproducibility (optional)
    # random.seed(42)
    
    demo = DriveBasedDemo()
    demo.run_simulation()


if __name__ == "__main__":
    main()