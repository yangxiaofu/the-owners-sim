#!/usr/bin/env python3
"""
Full Game Simulator

A clean, modular NFL game simulator that can be built up piece by piece.
Starting with basic team initialization and ready for incremental feature additions.
"""

from team_management.teams.team_loader import get_team_by_id
from team_management.personnel import TeamRosterGenerator
from constants.team_ids import TeamIDs
from game_management.game_manager import GameManager
from game_management.game_loop_controller import GameLoopController, GameResult, DriveResult
from game_management.drive_transition_manager import DriveTransitionManager
from game_management.overtime_manager import OvertimeType, create_overtime_manager
import json
from pathlib import Path
import time
from typing import Optional, Dict, List, Any


class FullGameSimulator:
    """
    Complete NFL game simulator with modular architecture.
    
    Designed to be built incrementally with individual systems
    added piece by piece for easy testing and development.
    """
    
    def __init__(self, away_team_id: int, home_team_id: int,
                 dynasty_id: Optional[str] = None,
                 db_path: Optional[str] = None,
                 overtime_type: str = "regular_season"):
        """
        Initialize game simulator with two teams.

        Args:
            away_team_id: Numerical team ID for away team (1-32)
            home_team_id: Numerical team ID for home team (1-32)
            dynasty_id: Dynasty context (REQUIRED for database rosters, None for demo mode)
            db_path: Database path (REQUIRED for database rosters, None for demo mode)
            overtime_type: Type of overtime rules ("regular_season" or "playoffs")
        """
        # Load team data
        self.away_team = get_team_by_id(away_team_id)
        self.home_team = get_team_by_id(home_team_id)

        # Validate team loading
        if not self.away_team:
            raise ValueError(f"Could not load away team with ID: {away_team_id}")
        if not self.home_team:
            raise ValueError(f"Could not load home team with ID: {home_team_id}")
        if away_team_id == home_team_id:
            raise ValueError("Away and home teams must be different")

        # Store team IDs for easy access
        self.away_team_id = away_team_id
        self.home_team_id = home_team_id

        # Store dynasty context
        self.dynasty_id = dynasty_id
        self.db_path = db_path

        # Store overtime type for game simulation
        self.overtime_type = OvertimeType.PLAYOFFS if overtime_type == "playoffs" else OvertimeType.REGULAR_SEASON

        # Load team rosters (database or synthetic)
        if dynasty_id and db_path:
            # Production mode: Load from database
            self.away_roster = TeamRosterGenerator.load_team_roster(
                away_team_id, dynasty_id=dynasty_id, db_path=db_path
            )
            self.home_roster = TeamRosterGenerator.load_team_roster(
                home_team_id, dynasty_id=dynasty_id, db_path=db_path
            )
            roster_source = f"database (dynasty: {dynasty_id})"
        else:
            # Demo mode: Use synthetic rosters
            self.away_roster = TeamRosterGenerator.generate_synthetic_roster(away_team_id)
            self.home_roster = TeamRosterGenerator.generate_synthetic_roster(home_team_id)
            roster_source = "synthetic (demo mode)"

        print(f"🏈 Full Game Simulator Initialized")
        print(f"   Away Team: {self.away_team.full_name} (ID: {self.away_team_id})")
        print(f"   Home Team: {self.home_team.full_name} (ID: {self.home_team_id})")
        print(f"   Matchup: {self.away_team.abbreviation} @ {self.home_team.abbreviation}")
        print(f"   Away Roster: {len(self.away_roster)} players ({roster_source})")
        print(f"   Home Roster: {len(self.home_roster)} players ({roster_source})")

        # Initialize GameManager for core game management
        self.game_manager = GameManager(self.home_team, self.away_team)

        # Load coaching staff
        self.away_coaching_staff = self._load_coaching_staff(away_team_id)
        self.home_coaching_staff = self._load_coaching_staff(home_team_id)

        print(f"   Away Coaching Staff: {self.away_coaching_staff['head_coach']['name']}")
        print(f"   Home Coaching Staff: {self.home_coaching_staff['head_coach']['name']}")

        # Start game (includes coin toss)
        self.game_manager.start_game()

        # Display coin toss results
        coin_toss_results = self.game_manager._get_team_name(self.game_manager.coin_toss_winner)
        receiving_team = self.game_manager.possession_manager.get_possessing_team_id()
        print(f"   Coin Toss Winner: {coin_toss_results}")
        print(f"   Receiving Team: {receiving_team}")
        print(f"   Game Status: {self.game_manager.get_game_state().phase.value}")



    def simulate_game(self, date=None) -> GameResult:
        """
        Main game simulation method - Complete NFL game simulation
        
        Integrates GameLoopController with existing FullGameSimulator infrastructure
        for comprehensive game simulation with statistics tracking.
        
        Returns:
            GameResult: Complete game result with statistics, drive summaries, and outcomes
        """
        print(f"\n🎮 Starting Full Game Simulation...")
        print(f"⚡ {self.away_team.full_name} @ {self.home_team.full_name}")
        print(f"🏟️  Location: {self.home_team.city}")
        
        # Record simulation start time for performance tracking
        simulation_start_time = time.time()

        # Initialize GameLoopController with all required components
        try:
            # Create overtime manager based on configured type
            overtime_manager = create_overtime_manager(self.overtime_type)

            game_loop_controller = GameLoopController(
                game_manager=self.game_manager,
                home_team=self.home_team,
                away_team=self.away_team,
                home_coaching_staff_config=self.home_coaching_staff,
                away_coaching_staff_config=self.away_coaching_staff,
                home_roster=self.home_roster,
                away_roster=self.away_roster,
                overtime_manager=overtime_manager,
                game_date=date
            )

            print("✅ GameLoopController initialized successfully")

            # Run complete game simulation
            print("\n🏈 Beginning Full Game Simulation...")
            game_result = game_loop_controller.run_game()

            # Record simulation completion time
            simulation_end_time = time.time()
            simulation_duration = simulation_end_time - simulation_start_time

            # Store results and controller for API access
            self._game_result = game_result
            self._game_loop_controller = game_loop_controller  # Store controller for live stats access
            self._simulation_duration = simulation_duration

            # Game simulation complete - no persistence in standalone mode
            print(f"\n📊 Game complete - results available via get_game_result()")

            # Display final results
            print(f"\n🏁 GAME COMPLETE!")
            print(f"⏱️  Simulation Time: {simulation_duration:.2f} seconds")
            print(f"📊 Final Score:")
            
            # Convert team ID-based final score to team names for display
            final_score = game_result.final_score
            for team_id, score in final_score.items():
                team_name = self._get_team_name(team_id)
                print(f"   {team_name}: {score}")
            
            # Determine winner
            winner = game_result.winner
            if winner:
                print(f"🏆 Winner: {winner.full_name}")
            else:
                print("🤝 Game ended in a tie")
                
            print(f"📈 Total Plays: {game_result.total_plays}")
            print(f"🚗 Total Drives: {game_result.total_drives}")
            
            return game_result
            
        except Exception as e:
            print(f"❌ Game simulation failed: {e}")
            print("🔧 Falling back to basic game state...")
            
            # Fallback: return basic game state information
            game_state = self.game_manager.get_game_state()
            
            # Create minimal GameResult for compatibility
            fallback_result = self._create_fallback_game_result(game_state, simulation_start_time, date)
            self._game_result = fallback_result
            self._simulation_duration = time.time() - simulation_start_time
            
            return fallback_result

    
    def get_team_info(self):
        """
        Get detailed information about both teams
        
        Returns:
            Dictionary with team information
        """
        return {
            "away_team": {
                "id": self.away_team_id,
                "name": self.away_team.full_name,
                "city": self.away_team.city,
                "nickname": self.away_team.nickname,
                "abbreviation": self.away_team.abbreviation,
                "conference": self.away_team.conference,
                "division": self.away_team.division,
                "colors": self.away_team.colors,
                "roster_size": len(self.away_roster)
            },
            "home_team": {
                "id": self.home_team_id,
                "name": self.home_team.full_name,
                "city": self.home_team.city,
                "nickname": self.home_team.nickname,
                "abbreviation": self.home_team.abbreviation,
                "conference": self.home_team.conference,
                "division": self.home_team.division,
                "colors": self.home_team.colors,
                "roster_size": len(self.home_roster)
            }
        }
    
    def get_away_roster(self):
        """
        Get the away team's complete roster
        
        Returns:
            List of Player objects for away team
        """
        return self.away_roster
    
    def get_home_roster(self):
        """
        Get the home team's complete roster
        
        Returns:
            List of Player objects for home team
        """
        return self.home_roster
    
    def get_roster_by_team(self, team_id: int):
        """
        Get roster by team ID
        
        Args:
            team_id: Team ID (away_team_id or home_team_id)
            
        Returns:
            List of Player objects for the specified team
        """
        if team_id == self.away_team_id:
            return self.away_roster
        elif team_id == self.home_team_id:
            return self.home_roster
        else:
            raise ValueError(f"Team ID {team_id} not in this game. Available: {self.away_team_id}, {self.home_team_id}")
    
    def get_starting_lineup(self, team_id: int, position_group: str = None):
        """
        Get starting players for a team, optionally filtered by position group
        
        Args:
            team_id: Team ID
            position_group: Optional position filter (e.g., 'QB', 'RB', 'WR')
            
        Returns:
            List of Player objects matching criteria, sorted by overall rating
        """
        roster = self.get_roster_by_team(team_id)
        
        if position_group:
            # Filter by position group
            filtered_players = [player for player in roster if player.primary_position == position_group]
            # Sort by overall rating (highest first)
            return sorted(filtered_players, key=lambda p: p.get_rating('overall'), reverse=True)
        else:
            # Return all players sorted by overall rating
            return sorted(roster, key=lambda p: p.get_rating('overall'), reverse=True)
    
    def get_team_depth_chart(self, team_id: int):
        """
        Get organized depth chart by position for a team
        
        Args:
            team_id: Team ID
            
        Returns:
            Dictionary with positions as keys and lists of players as values
        """
        roster = self.get_roster_by_team(team_id)
        depth_chart = {}
        
        for player in roster:
            position = player.primary_position
            if position not in depth_chart:
                depth_chart[position] = []
            depth_chart[position].append(player)
        
        # Sort each position by overall rating (highest first)
        for position in depth_chart:
            depth_chart[position].sort(key=lambda p: p.get_rating('overall'), reverse=True)
        
        return depth_chart
    
    def get_game_clock(self):
        """
        Get access to the game clock
        
        Returns:
            GameClock object for time tracking and queries
        """
        return self.game_manager.game_clock
    
    def get_scoreboard(self):
        """
        Get access to the scoreboard
        
        Returns:
            Scoreboard object for scoring operations
        """
        return self.game_manager.scoreboard
    
    def get_game_status(self):
        """
        Get comprehensive game status information
        
        Returns:
            Dictionary with current game state including time, score, and phase
        """
        game_state = self.game_manager.get_game_state()
        return {
            "quarter": game_state.quarter,
            "time_display": game_state.time_remaining,
            "game_phase": game_state.phase.value,
            "away_score": game_state.score[self.away_team_id],
            "home_score": game_state.score[self.home_team_id],
            "away_team": self.away_team.abbreviation,
            "home_team": self.home_team.abbreviation,
            "is_halftime": game_state.phase.value == "halftime",
            "is_two_minute_warning": game_state.two_minute_warning
        }
    
    
    def get_possession_manager(self):
        """Get access to possession manager"""
        return self.game_manager.possession_manager
    
    def get_field_tracker(self):
        """Get access to field tracker"""
        # Field tracking is now handled within DriveManager in GameManager
        if self.game_manager.current_drive:
            return self.game_manager.current_drive.field_tracker
        return None
    
    def get_current_field_position(self):
        """Get current ball field position"""
        if self.game_manager.current_drive:
            return self.game_manager.current_drive.get_current_field_position()
        return None
    
    def get_coin_toss_results(self):
        """Get coin toss results for external access"""
        return {
            "winner": self.game_manager._get_team_name(self.game_manager.coin_toss_winner) if self.game_manager.coin_toss_winner else None,
            "receiving_team": self._get_team_name(self.game_manager.possession_manager.get_possessing_team_id()),
            "opening_kickoff_team": self.game_manager._get_team_name(self.game_manager.opening_kickoff_team) if self.game_manager.opening_kickoff_team else None
        }
    
    def _load_coaching_staff(self, team_id: int):
        """Load coaching staff configuration for a team"""
        try:
            # Load team coaching styles mapping
            config_dir = Path(__file__).parent.parent / "config"
            team_styles_path = config_dir / "team_coaching_styles.json"
            
            with open(team_styles_path, 'r') as f:
                team_styles = json.load(f)
            
            # Get coaching staff names for this team
            team_config = team_styles.get(str(team_id))
            if not team_config:
                return self._get_fallback_coaching_staff(team_id)
            
            # Load individual coach configs
            coaching_staff = {}
            
            # Load head coach
            hc_name = team_config["head_coach"]
            hc_path = config_dir / "coaching_staff" / "head_coaches" / f"{hc_name}.json"
            with open(hc_path, 'r') as f:
                coaching_staff["head_coach"] = json.load(f)
            
            # Load offensive coordinator
            oc_name = team_config["offensive_coordinator"]
            oc_path = config_dir / "coaching_staff" / "offensive_coordinators" / f"{oc_name}.json"
            with open(oc_path, 'r') as f:
                coaching_staff["offensive_coordinator"] = json.load(f)
            
            # Load defensive coordinator
            dc_name = team_config["defensive_coordinator"]
            dc_path = config_dir / "coaching_staff" / "defensive_coordinators" / f"{dc_name}.json"
            with open(dc_path, 'r') as f:
                coaching_staff["defensive_coordinator"] = json.load(f)
            
            return coaching_staff
            
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load coaching staff for team {team_id}: {e}")
            return self._get_fallback_coaching_staff(team_id)
    
    def _get_fallback_coaching_staff(self, team_id: int):
        """Get fallback coaching staff if real configs can't be loaded"""
        team_name = self._get_team_name(team_id)
        return {
            "head_coach": {"name": f"{team_name} Head Coach", "description": "Generic head coach"},
            "offensive_coordinator": {"name": f"{team_name} Offensive Coordinator", "description": "Generic OC"},
            "defensive_coordinator": {"name": f"{team_name} Defensive Coordinator", "description": "Generic DC"}
        }
    
    def _get_team_name(self, team_id: int) -> str:
        """Get team display name by ID"""
        if team_id == self.home_team_id:
            return self.home_team.full_name
        elif team_id == self.away_team_id:
            return self.away_team.full_name
        else:
            return f"Team {team_id}"
    
    def _create_fallback_game_result(self, game_state, start_time, date=None) -> GameResult:
        """Create minimal GameResult when full simulation fails"""
        from game_management.game_loop_controller import GameResult
        
        return GameResult(
            home_team=self.home_team,
            away_team=self.away_team,
            final_score={
                self.home_team_id: game_state.score[self.home_team_id],
                self.away_team_id: game_state.score[self.away_team_id]
            },
            winner=None,  # No winner in fallback
            total_plays=game_state.total_plays,
            total_drives=0,  # No drives completed in fallback
            game_duration_minutes=int((time.time() - start_time) / 60),
            drive_results=[],
            final_statistics=None,
            date=date
        )
    
    def get_away_coaching_staff(self):
        """Get away team coaching staff"""
        return self.away_coaching_staff
    
    def get_home_coaching_staff(self):
        """Get home team coaching staff"""
        return self.home_coaching_staff
    
    def get_coaching_staff_by_team(self, team_id: int):
        """Get coaching staff by team ID"""
        if team_id == self.away_team_id:
            return self.away_coaching_staff
        elif team_id == self.home_team_id:
            return self.home_coaching_staff
        else:
            raise ValueError(f"Team ID {team_id} not in this game")
    
    # ============================================================================
    # PHASE 4: COMPREHENSIVE STATISTICS ACCESS API METHODS
    # ============================================================================
    
    def get_game_result(self) -> Optional[GameResult]:
        """
        Get the complete game result
        
        Returns:
            GameResult object with comprehensive game data, or None if no game has been simulated
        """
        return getattr(self, '_game_result', None)
    
    def get_final_score(self) -> Dict[str, Any]:
        """
        Get enhanced final score with metadata
        
        Returns:
            Dictionary with final scores, winner info, and game metadata
        """
        if not hasattr(self, '_game_result') or not self._game_result:
            return {
                "scores": {
                    self.away_team.team_id: 0,
                    self.home_team.team_id: 0
                },
                "team_names": {
                    self.away_team.team_id: self.away_team.full_name,
                    self.home_team.team_id: self.home_team.full_name
                },
                "winner_id": None,
                "winner_name": None,
                "game_completed": False,
                "simulation_time": 0.0
            }
        
        game_result = self._game_result
        
        # Keep original team ID-based scores for system consistency
        scores = game_result.final_score  # Maintains team IDs as keys: {22: 21, 23: 14}
        
        # Create team names mapping for display purposes
        team_names = {}
        for team_id in game_result.final_score.keys():
            team_names[team_id] = self._get_team_name(team_id)
            
        return {
            "scores": scores,  # Team ID keyed: {22: 21, 23: 14}
            "team_names": team_names,  # Team ID to name mapping: {22: "Detroit Lions", 23: "Green Bay Packers"}
            "winner_id": game_result.winner.team_id if game_result.winner else None,
            "winner_name": game_result.winner.full_name if game_result.winner else None,
            "total_plays": game_result.total_plays,
            "total_drives": game_result.total_drives,
            "game_duration_minutes": game_result.game_duration_minutes,
            "game_completed": True,
            "simulation_time": getattr(self, '_simulation_duration', 0.0)
        }
    
    def __str__(self):
        """String representation of the game"""
        return f"FullGameSimulator({self.away_team.abbreviation} @ {self.home_team.abbreviation})"
    
    def __repr__(self):
        """Detailed string representation"""
        return f"FullGameSimulator(away_team_id={self.away_team_id}, home_team_id={self.home_team_id})"

