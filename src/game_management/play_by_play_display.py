"""
Play-by-Play Display System

Enhanced display system for real-time game progression, drive summaries,
and play-by-play narration with game context and formatting.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from play_engine.core.play_result import PlayResult
from play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from play_engine.game_state.game_clock import GameClock, ClockResult
from game_management.scoreboard import Scoreboard, ScoringEvent
from team_management.teams.team_loader import Team


class DisplayStyle(Enum):
    """Display formatting styles"""
    MINIMAL = "minimal"         # Just basic play results
    STANDARD = "standard"       # Standard play-by-play
    DETAILED = "detailed"       # Detailed with context and statistics
    BROADCAST = "broadcast"     # TV broadcast style commentary


@dataclass
class PlayDisplay:
    """Formatted play information for display"""
    play_number: int
    quarter: int
    time_remaining: str
    down_and_distance: str
    field_position: str
    possessing_team: str
    play_description: str
    result_summary: str
    context_notes: List[str]
    score_change: Optional[str] = None
    penalty_info: Optional[str] = None


@dataclass
class DriveDisplay:
    """Formatted drive summary for display"""
    drive_number: int
    possessing_team: str
    starting_position: str
    ending_position: str
    drive_result: str
    total_plays: int
    total_yards: int
    time_of_possession: str
    key_plays: List[str]


class PlayByPlayDisplay:
    """
    Enhanced play-by-play display system with context-aware formatting.
    
    Provides multiple display styles from minimal to broadcast-quality commentary.
    Handles drive summaries, scoring plays, penalties, and game context.
    """
    
    def __init__(self, 
                 home_team: Team, 
                 away_team: Team,
                 style: DisplayStyle = DisplayStyle.STANDARD):
        """
        Initialize play-by-play display
        
        Args:
            home_team: Home team object
            away_team: Away team object
            style: Display formatting style
        """
        self.home_team = home_team
        self.away_team = away_team
        self.style = style
        self.play_counter = 0
        self.drive_counter = 0
        # Track two-minute warning display to show only once per half
        self._two_minute_warning_shown_first_half = False
        self._two_minute_warning_shown_second_half = False

    def reset_for_new_game(self):
        """Reset display state for a new game"""
        self.play_counter = 0
        self.drive_counter = 0
        self._two_minute_warning_shown_first_half = False
        self._two_minute_warning_shown_second_half = False

    def format_play_result(self, 
                          play_result: PlayResult,
                          drive_manager: DriveManager,
                          game_clock: GameClock,
                          scoreboard: Scoreboard,
                          context: Dict[str, any] = None) -> PlayDisplay:
        """
        Format a play result for display
        
        Args:
            play_result: PlayResult to format
            drive_manager: Current drive state
            game_clock: Current game time
            scoreboard: Current score
            context: Additional context information
            
        Returns:
            PlayDisplay with formatted play information
        """
        self.play_counter += 1
        
        # Get basic game state
        quarter = game_clock.quarter
        time_remaining = game_clock.get_time_display()
        
        # Get down and distance
        down_state = drive_manager.current_down_state
        down_and_distance = f"{self._ordinal(down_state.current_down)} & {down_state.yards_to_go}"
        
        # Get field position
        field_pos = drive_manager.current_position
        field_position = self._format_field_position(field_pos.yard_line, field_pos.possession_team)
        
        # Get possessing team name
        possessing_team_name = self._get_team_name(field_pos.possession_team)
        
        # Generate play description and result
        play_description = self._generate_play_description(play_result)
        result_summary = self._generate_result_summary(play_result, down_state)
        
        # Generate context notes
        context_notes = self._generate_context_notes(play_result, drive_manager, game_clock, context)
        
        # Check for scoring plays
        score_change = None
        if hasattr(play_result, 'points_scored') and play_result.points_scored > 0:
            new_scores = scoreboard.get_score()
            score_change = f"{possessing_team_name} scores {play_result.points_scored} points! {self._format_score_display(new_scores)}"
        
        # Check for penalties - check both PlayResult and player_stats_summary
        penalty_info = None
        has_penalty = False

        # Check PlayResult.penalty_occurred first
        if hasattr(play_result, 'penalty_occurred') and play_result.penalty_occurred:
            has_penalty = True

        # Also check if penalty_instance exists in player_stats_summary
        if hasattr(play_result, 'player_stats_summary') and play_result.player_stats_summary:
            if hasattr(play_result.player_stats_summary, 'penalty_instance') and play_result.player_stats_summary.penalty_instance:
                has_penalty = True

        if has_penalty:
            penalty_info = self._format_penalty_info(play_result)
        
        return PlayDisplay(
            play_number=self.play_counter,
            quarter=quarter,
            time_remaining=time_remaining,
            down_and_distance=down_and_distance,
            field_position=field_position,
            possessing_team=possessing_team_name,
            play_description=play_description,
            result_summary=result_summary,
            context_notes=context_notes,
            score_change=score_change,
            penalty_info=penalty_info
        )
    
    def format_drive_summary(self, 
                           completed_drive: DriveManager,
                           drive_plays: List[PlayDisplay]) -> DriveDisplay:
        """
        Format a completed drive summary
        
        Args:
            completed_drive: Completed DriveManager
            drive_plays: List of plays from this drive
            
        Returns:
            DriveDisplay with formatted drive summary
        """
        self.drive_counter += 1
        
        possessing_team_name = self._get_team_name(completed_drive.get_possessing_team_id())
        starting_pos = completed_drive.get_starting_field_position()
        ending_pos = completed_drive.get_field_position().yard_line
        drive_result = self._format_drive_result(completed_drive.get_drive_end_reason())
        
        # Calculate drive statistics
        total_plays = len(drive_plays)
        total_yards = ending_pos - starting_pos  # Simplified calculation
        
        # Extract key plays (big gains, turnovers, scores)
        key_plays = self._extract_key_plays(drive_plays)
        
        return DriveDisplay(
            drive_number=self.drive_counter,
            possessing_team=possessing_team_name,
            starting_position=self._format_field_position(starting_pos, completed_drive.get_possessing_team_id()),
            ending_position=self._format_field_position(ending_pos, completed_drive.get_possessing_team_id()),
            drive_result=drive_result,
            total_plays=total_plays,
            total_yards=total_yards,
            time_of_possession="N/A",  # Would need time tracking
            key_plays=key_plays
        )
    
    def display_play(self, play_display: PlayDisplay) -> str:
        """
        Generate display string for a play
        
        Args:
            play_display: PlayDisplay to format
            
        Returns:
            Formatted string representation
        """
        if self.style == DisplayStyle.MINIMAL:
            return self._format_minimal_play(play_display)
        elif self.style == DisplayStyle.DETAILED:
            return self._format_detailed_play(play_display)
        elif self.style == DisplayStyle.BROADCAST:
            return self._format_broadcast_play(play_display)
        else:  # STANDARD
            return self._format_standard_play(play_display)
    
    def display_drive_summary(self, drive_display: DriveDisplay) -> str:
        """
        Generate display string for a drive summary
        
        Args:
            drive_display: DriveDisplay to format
            
        Returns:
            Formatted string representation
        """
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"DRIVE #{drive_display.drive_number} SUMMARY - {drive_display.possessing_team.upper()}")
        lines.append('=' * 60)
        lines.append(f"Start: {drive_display.starting_position}")
        lines.append(f"End: {drive_display.ending_position}")
        lines.append(f"Result: {drive_display.drive_result}")
        lines.append(f"Plays: {drive_display.total_plays} | Yards: {drive_display.total_yards:+d}")
        
        if drive_display.key_plays:
            lines.append(f"\nKey Plays:")
            for key_play in drive_display.key_plays:
                lines.append(f"  • {key_play}")
        
        lines.append('=' * 60)
        return '\n'.join(lines)
    
    def display_quarter_summary(self, quarter: int, quarter_plays: List[PlayDisplay]) -> str:
        """
        Generate quarter summary display
        
        Args:
            quarter: Quarter number
            quarter_plays: All plays from the quarter
            
        Returns:
            Formatted quarter summary
        """
        lines = []
        lines.append(f"\n{'*' * 50}")
        lines.append(f"END OF QUARTER {quarter}")
        lines.append('*' * 50)
        lines.append(f"Total plays this quarter: {len(quarter_plays)}")
        
        # Count scoring plays
        scoring_plays = [p for p in quarter_plays if p.score_change]
        if scoring_plays:
            lines.append(f"Scoring plays: {len(scoring_plays)}")
            for play in scoring_plays:
                lines.append(f"  • {play.score_change}")
        
        lines.append('*' * 50)
        return '\n'.join(lines)
    
    def _format_minimal_play(self, play: PlayDisplay) -> str:
        """Format play in minimal style"""
        return f"[Q{play.quarter} {play.time_remaining}] {play.play_description} - {play.result_summary}"
    
    def _format_standard_play(self, play: PlayDisplay) -> str:
        """Format play in standard style"""
        lines = []
        
        # Game situation line
        situation = f"Q{play.quarter} {play.time_remaining} | {play.down_and_distance} at {play.field_position}"
        lines.append(f"[Play #{play.play_number}] {situation}")
        
        # Play description and result
        lines.append(f"🏈 {play.possessing_team}: {play.play_description}")
        lines.append(f"📊 Result: {play.result_summary}")
        
        # Score change
        if play.score_change:
            lines.append(f"🎯 {play.score_change}")
        
        # Penalty info
        if play.penalty_info:
            lines.append(f"⚠️  {play.penalty_info}")
        
        # Context notes
        for note in play.context_notes:
            lines.append(f"ℹ️  {note}")
        
        return '\n'.join(lines) + '\n'
    
    def _format_detailed_play(self, play: PlayDisplay) -> str:
        """Format play in detailed style with extra context"""
        lines = []
        
        # Detailed game situation
        lines.append(f"{'─' * 70}")
        lines.append(f"PLAY #{play.play_number} | Q{play.quarter} {play.time_remaining}")
        lines.append(f"Situation: {play.down_and_distance} at {play.field_position}")
        lines.append(f"Possession: {play.possessing_team}")
        lines.append(f"{'─' * 70}")
        
        # Play details
        lines.append(f"Play: {play.play_description}")
        lines.append(f"Result: {play.result_summary}")
        
        # Additional information
        if play.score_change:
            lines.append(f"\n🎯 SCORE: {play.score_change}")
        
        if play.penalty_info:
            lines.append(f"\n⚠️  PENALTY: {play.penalty_info}")
        
        if play.context_notes:
            lines.append(f"\nContext:")
            for note in play.context_notes:
                lines.append(f"  • {note}")
        
        return '\n'.join(lines) + '\n'
    
    def _format_broadcast_play(self, play: PlayDisplay) -> str:
        """Format play in broadcast commentary style"""
        lines = []
        
        # Broadcast-style setup
        lines.append(f"With {play.time_remaining} remaining in the {self._ordinal(play.quarter)} quarter...")
        lines.append(f"{play.possessing_team} faces {play.down_and_distance} at the {play.field_position}.")
        lines.append(f"{play.play_description}")
        lines.append(f"{play.result_summary}")
        
        if play.score_change:
            lines.append(f"TOUCHDOWN! {play.score_change}")
        
        return '\n'.join(lines) + '\n'
    
    def _generate_play_description(self, play_result: PlayResult) -> str:
        """Generate descriptive play text with proper outcome differentiation"""
        # If a pre-formatted description exists, use it
        if hasattr(play_result, 'play_description') and play_result.play_description:
            return play_result.play_description

        # Extract outcome and player information
        outcome = getattr(play_result, 'outcome', 'unknown')
        yards = getattr(play_result, 'yards', 0)

        # Get key players if stats are available
        key_players = ""
        if play_result.has_player_stats():
            key_players = play_result.get_key_players()

        # Handle different outcome types
        if outcome == 'sack':
            # Sacks: Show QB SACKED by defender
            if key_players:
                # Extract QB and tackler from key_players string
                parts = key_players.split(', tackled by ')
                if len(parts) == 2:
                    qb_name = parts[0]
                    tackler_name = parts[1]
                    return f"{qb_name} SACKED by {tackler_name}"
                else:
                    return f"QB SACKED for {abs(yards)} yard loss"
            return f"Quarterback sacked for {abs(yards)} yard loss"

        elif outcome == 'incomplete':
            # Incomplete passes: Show pass incomplete (no tackler)
            if key_players:
                # Extract passer and receiver
                if ' to ' in key_players:
                    passer_receiver = key_players.split(', tackled by ')[0]  # Remove tackler if present
                    return f"Pass {passer_receiver} - INCOMPLETE"
                else:
                    return f"Pass by {key_players.split(',')[0]} - INCOMPLETE"
            return "Pass incomplete"

        elif outcome == 'deflected_incomplete':
            # Deflected passes
            if key_players:
                passer_receiver = key_players.split(', tackled by ')[0]
                return f"Pass {passer_receiver} - DEFLECTED INCOMPLETE"
            return "Pass deflected incomplete"

        elif outcome == 'completion':
            # Completed passes: Show passer, receiver, and tackler
            if key_players:
                return f"Pass {key_players}"
            return f"Pass completed for {yards} yards"

        elif outcome == 'interception':
            # Interceptions
            if key_players:
                return f"INTERCEPTION - {key_players}"
            return "Pass intercepted"

        elif outcome == 'rush':
            # Running plays
            if key_players:
                return f"Rush by {key_players}"
            return f"Rush for {yards} yards"

        elif 'fake_' in outcome:
            # ✅ FIX: Handle fake field goal and fake punt plays with proper formatting
            # Outcomes: fake_run_success, fake_run_failed, fake_pass_success, fake_pass_failed
            if 'run' in outcome:
                play_type = "Run"
            elif 'pass' in outcome:
                play_type = "Pass"
            else:
                play_type = "Attempt"

            if 'success' in outcome:
                return f"Fake FG ({play_type}) - SUCCESSFUL for {yards} yards"
            elif 'interception' in outcome:
                return f"Fake FG (Pass) - INTERCEPTED"
            else:  # failed
                return f"Fake FG ({play_type}) - FAILED"

        elif 'field_goal' in outcome:
            # Field goals
            if 'made' in outcome or outcome == 'field_goal_good':
                return "Field goal GOOD"
            elif 'blocked' in outcome:
                return "Field goal BLOCKED"
            elif 'missed' in outcome:
                if 'wide_left' in outcome:
                    return "Field goal MISSED wide left"
                elif 'wide_right' in outcome:
                    return "Field goal MISSED wide right"
                elif 'short' in outcome:
                    return "Field goal MISSED short"
                else:
                    return "Field goal MISSED"
            return "Field goal attempt"

        elif 'punt_fake' in outcome:
            # Fake punt plays
            if 'success' in outcome:
                return f"Fake Punt - SUCCESSFUL for {yards} yards"
            elif 'interception' in outcome:
                return "Fake Punt - INTERCEPTED"
            else:
                return "Fake Punt - FAILED"

        elif outcome == 'punt':
            # Punt plays
            return "Punt"

        elif outcome == 'kickoff':
            # Kickoff plays
            return "Kickoff"

        # Fallback to basic description
        play_type = getattr(play_result, 'play_type', 'Unknown Play')
        return f"{play_type} play"
    
    def _generate_result_summary(self, play_result: PlayResult, down_state) -> str:
        """Generate result summary text"""
        yards = getattr(play_result, 'yards_gained', 0)
        
        if yards > 0:
            result = f"{yards} yard gain"
        elif yards < 0:
            result = f"{abs(yards)} yard loss"
        else:
            result = "No gain"
        
        # Add first down info if applicable
        if hasattr(play_result, 'first_down_achieved') and play_result.first_down_achieved:
            result += " - FIRST DOWN"
        
        return result
    
    def _generate_context_notes(self,
                              play_result: PlayResult,
                              drive_manager: DriveManager,
                              game_clock: GameClock,
                              context: Dict[str, any] = None) -> List[str]:
        """Generate contextual notes about the play"""
        notes = []

        # Two-minute warning - only show ONCE per half when clock first crosses 2:00
        if game_clock.is_two_minute_warning_active:
            if game_clock.quarter == 2 and not self._two_minute_warning_shown_first_half:
                notes.append("⏱️ TWO-MINUTE WARNING - Q2")
                self._two_minute_warning_shown_first_half = True
            elif game_clock.quarter == 4 and not self._two_minute_warning_shown_second_half:
                notes.append("⏱️ TWO-MINUTE WARNING - Q4")
                self._two_minute_warning_shown_second_half = True

        # Check for timeout usage (from context or clock result)
        if context:
            if context.get('timeout_called'):
                team = context.get('timeout_team', 'Team')
                timeout_num = context.get('timeout_number', '')
                if timeout_num:
                    notes.append(f"⏸️ Timeout called by {team} (Timeout #{timeout_num})")
                else:
                    notes.append(f"⏸️ Timeout called by {team}")

        # Clock stopped due to out of bounds
        if hasattr(play_result, 'went_out_of_bounds') and play_result.went_out_of_bounds:
            notes.append("⏱️ Clock stopped - ball carrier out of bounds")

        # Red zone
        field_pos = drive_manager.current_position
        if field_pos.yard_line >= 80:  # In red zone
            notes.append("🎯 Red zone opportunity")

        # Fourth down situations
        down_state = drive_manager.current_down_state
        if down_state.current_down == 4:
            notes.append("⚠️ Fourth down - critical play")

        # Goal line stand
        if field_pos.yard_line >= 95:
            notes.append("🛡️ Goal line stand")

        # Clock management - hurry-up offense
        if hasattr(play_result, 'time_elapsed'):
            if play_result.time_elapsed < 10:
                notes.append("⚡ Quick play - hurry-up offense")
            elif play_result.time_elapsed > 30:
                notes.append("🐌 Long play - significant time elapsed")

        return notes
    
    def _format_penalty_info(self, play_result: PlayResult) -> str:
        """Format penalty information from penalty instance"""
        # Check for penalty instance with detailed information
        if hasattr(play_result, 'player_stats_summary') and play_result.player_stats_summary:
            if hasattr(play_result.player_stats_summary, 'penalty_instance') and play_result.player_stats_summary.penalty_instance:
                penalty = play_result.player_stats_summary.penalty_instance

                # Extract penalty details
                penalty_type = penalty.penalty_type.replace('_', ' ').title()
                player_number = penalty.penalized_player_number
                player_name = penalty.penalized_player_name
                yards = abs(penalty.yards_assessed)

                # Format: "[PENALTY] Holding on #75 (Smith) - 10 yards"
                penalty_str = f"[PENALTY] {penalty_type} on #{player_number}"

                # Add player name if not a generic name
                if player_name and not ('Starting' in player_name or 'Backup' in player_name):
                    penalty_str += f" ({player_name.split()[-1]})"  # Last name only

                penalty_str += f" - {yards} yards"

                # Add automatic first down or loss of down info
                if penalty.automatic_first_down:
                    penalty_str += " (Automatic First Down)"
                elif penalty.automatic_loss_of_down:
                    penalty_str += " (Loss of Down)"

                return penalty_str

        # Fallback to basic penalty info from PlayResult
        if hasattr(play_result, 'penalty_yards') and play_result.penalty_yards:
            penalty_type = getattr(play_result, 'penalty_type', 'Penalty')
            penalty_type = penalty_type.replace('_', ' ').title()
            yards = abs(play_result.penalty_yards)
            return f"[PENALTY] {penalty_type} - {yards} yards"

        return "[PENALTY] Penalty occurred"
    
    def _format_drive_result(self, drive_end_reason: DriveEndReason) -> str:
        """Format drive ending reason"""
        reason_map = {
            DriveEndReason.TOUCHDOWN: "Touchdown",
            DriveEndReason.FIELD_GOAL: "Field goal",
            DriveEndReason.PUNT: "Punt",
            DriveEndReason.TURNOVER: "Turnover",
            DriveEndReason.TURNOVER_ON_DOWNS: "Turnover on downs",
            DriveEndReason.SAFETY: "Safety",
            DriveEndReason.TIME_EXPIRATION: "Time expired"
        }
        return reason_map.get(drive_end_reason, str(drive_end_reason))
    
    def _extract_key_plays(self, drive_plays: List[PlayDisplay]) -> List[str]:
        """Extract key plays from a drive"""
        key_plays = []
        
        for play in drive_plays:
            # Big plays (15+ yards)
            if "15" in play.result_summary or "20" in play.result_summary:
                key_plays.append(f"{play.play_description} for big gain")
            
            # Scoring plays
            if play.score_change:
                key_plays.append(play.score_change)
            
            # Penalties
            if play.penalty_info:
                key_plays.append(f"Penalty: {play.penalty_info}")
            
            # Fourth down conversions
            if "4th" in play.down_and_distance and "FIRST DOWN" in play.result_summary:
                key_plays.append("Fourth down conversion")
        
        return key_plays[:3]  # Limit to top 3 key plays
    
    def _format_field_position(self, yard_line: int, team_id: int) -> str:
        """Format field position display"""
        team_abbrev = self._get_team_abbrev(team_id)
        
        if yard_line <= 50:
            return f"{team_abbrev} {yard_line}"
        else:
            opposing_yard_line = 100 - yard_line
            opposing_team_id = self.away_team.team_id if team_id == self.home_team.team_id else self.home_team.team_id
            opposing_abbrev = self._get_team_abbrev(opposing_team_id)
            return f"{opposing_abbrev} {opposing_yard_line}"
    
    def _format_score_display(self, scores: Dict[int, int]) -> str:
        """Format current score display"""
        home_score = scores[self.home_team.team_id]
        away_score = scores[self.away_team.team_id]
        return f"{self.away_team.abbreviation} {away_score} - {self.home_team.abbreviation} {home_score}"
    
    def _get_team_name(self, team_id: int) -> str:
        """Get team full name by ID"""
        if team_id == self.home_team.team_id:
            return self.home_team.full_name
        elif team_id == self.away_team.team_id:
            return self.away_team.full_name
        return f"Team {team_id}"
    
    def _get_team_abbrev(self, team_id: int) -> str:
        """Get team abbreviation by ID"""
        if team_id == self.home_team.team_id:
            return self.home_team.abbreviation
        elif team_id == self.away_team.team_id:
            return self.away_team.abbreviation
        return f"T{team_id}"
    
    def _ordinal(self, number: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, 4th)"""
        if 10 <= number % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
        return f"{number}{suffix}"