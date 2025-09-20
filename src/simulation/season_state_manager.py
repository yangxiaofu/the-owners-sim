"""
Season State Manager

Centralized manager for tracking and updating season progression state,
including standings, player statistics, team performance, and narrative events.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import logging

from .results.base_result import ProcessingResult, ProcessingContext


@dataclass
class TeamSeasonState:
    """Season state for a single team"""
    team_id: int
    
    # Record tracking
    wins: int = 0
    losses: int = 0
    ties: int = 0
    
    # Advanced metrics
    points_for: int = 0
    points_against: int = 0
    momentum: float = 0.0
    
    # Team chemistry and development
    chemistry_level: float = 75.0  # Base chemistry
    coaching_effectiveness: float = 0.75
    
    # Injury and fatigue tracking
    active_injuries: List[str] = field(default_factory=list)
    team_fatigue_level: float = 0.0
    
    # Season progression markers
    last_game_date: Optional[date] = None
    games_played: int = 0
    
    def get_win_percentage(self) -> float:
        """Calculate win percentage"""
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + (self.ties * 0.5)) / total_games
    
    def get_point_differential(self) -> int:
        """Get point differential for the season"""
        return self.points_for - self.points_against


@dataclass
class PlayerSeasonStats:
    """Season statistics for a player"""
    player_name: str
    team_id: int
    position: str = ""
    
    # Game participation
    games_played: int = 0
    games_started: int = 0
    
    # Offensive statistics
    passing_yards: int = 0
    passing_tds: int = 0
    passing_ints: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    
    # Defensive statistics
    tackles: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    fumble_recoveries: int = 0
    
    # Development and condition
    overall_rating_change: float = 0.0
    injury_weeks_missed: int = 0
    current_fatigue: float = 0.0
    
    def get_total_touchdowns(self) -> int:
        """Get total touchdowns scored"""
        return self.passing_tds + self.rushing_tds + self.receiving_tds
    
    def get_total_yards(self) -> int:
        """Get total offensive yards"""
        return self.passing_yards + self.rushing_yards + self.receiving_yards


@dataclass
class SeasonNarrative:
    """Tracks narrative events and storylines throughout the season"""
    season_year: int
    
    # Major storylines and events
    major_storylines: List[str] = field(default_factory=list)
    milestone_achievements: List[str] = field(default_factory=list)
    surprising_developments: List[str] = field(default_factory=list)
    
    # Weekly highlights
    weekly_highlights: Dict[int, List[str]] = field(default_factory=dict)  # week -> highlights
    
    # Season phases
    preseason_events: List[str] = field(default_factory=list)
    regular_season_events: List[str] = field(default_factory=list)
    playoff_events: List[str] = field(default_factory=list)
    
    def add_weekly_highlight(self, week: int, highlight: str) -> None:
        """Add a highlight for a specific week"""
        if week not in self.weekly_highlights:
            self.weekly_highlights[week] = []
        self.weekly_highlights[week].append(highlight)


class SeasonStateManager:
    """
    Centralized manager for season state and progression tracking.
    
    Aggregates and manages all season-level state including team standings,
    player statistics, injuries, and narrative developments.
    """
    
    def __init__(self, season_year: int = 2024):
        """
        Initialize season state manager
        
        Args:
            season_year: The year of the season to track
        """
        self.season_year = season_year
        self.logger = logging.getLogger(f"{__name__}.SeasonStateManager")
        
        # Core state tracking
        self.team_states: Dict[int, TeamSeasonState] = {}
        self.player_stats: Dict[str, PlayerSeasonStats] = {}  # player_name -> stats
        
        # Season progression
        self.current_week: int = 0
        self.season_phase: str = "preseason"  # preseason, regular_season, playoffs, offseason
        self.current_date: Optional[date] = None
        
        # Narrative and storylines
        self.narrative = SeasonNarrative(season_year)
        
        # State change tracking
        self.state_changes_log: List[Dict[str, Any]] = []
        self.processing_history: List[str] = []
        
        # Initialize default team states (32 NFL teams)
        self._initialize_team_states()
    
    def _initialize_team_states(self) -> None:
        """Initialize default state for all NFL teams"""
        for team_id in range(1, 33):  # Teams 1-32
            self.team_states[team_id] = TeamSeasonState(team_id=team_id)
    
    def apply_processing_result(self, processing_result: ProcessingResult, context: ProcessingContext) -> None:
        """
        Apply a processing result to update season state
        
        Args:
            processing_result: Result from event processing
            context: Processing context with date/week information
        """
        try:
            # Update current season context
            self._update_season_context(context)
            
            # Apply state changes
            self._apply_state_changes(processing_result, context)
            
            # Update statistics
            self._apply_statistics_updates(processing_result, context)
            
            # Process side effects and narrative elements
            self._process_side_effects(processing_result, context)
            
            # Log this processing
            self.processing_history.append(f"{context.current_date}: {processing_result.processing_type}")
            
            self.logger.debug(f"Applied {processing_result.processing_type} result for {len(processing_result.teams_updated)} teams")
            
        except Exception as e:
            self.logger.error(f"Error applying processing result: {str(e)}", exc_info=True)
    
    def _update_season_context(self, context: ProcessingContext) -> None:
        """Update season context from processing context"""
        if context.current_date:
            self.current_date = context.current_date.date() if isinstance(context.current_date, datetime) else context.current_date
        
        if context.season_week != self.current_week:
            self.current_week = context.season_week
            self.logger.info(f"Season progressed to Week {self.current_week}")
        
        if context.season_phase != self.season_phase:
            old_phase = self.season_phase
            self.season_phase = context.season_phase
            self.logger.info(f"Season phase changed from {old_phase} to {self.season_phase}")
            self.narrative.add_weekly_highlight(self.current_week, f"Season entered {self.season_phase} phase")
    
    def _apply_state_changes(self, processing_result: ProcessingResult, context: ProcessingContext) -> None:
        """Apply state changes to team and player states"""
        for key, value in processing_result.state_changes.items():
            self._apply_single_state_change(key, value, context, processing_result.teams_updated)
            
            # Log state change for debugging
            self.state_changes_log.append({
                "date": context.current_date.isoformat() if context.current_date else "unknown",
                "key": key,
                "value": value,
                "source": processing_result.processing_type
            })
    
    def _apply_single_state_change(self, key: str, value: Any, context: ProcessingContext, teams_updated: List[int]) -> None:
        """Apply a single state change"""
        if key.startswith("team_"):
            self._apply_team_state_change(key, value, context)
        elif key.startswith("player_"):
            self._apply_player_state_change(key, value, context, teams_updated)
        elif key in ["game_history_entry", "training_history_entry", "scouting_history_entry", 
                     "administrative_history_entry", "rest_history_entry"]:
            # Store historical entries for later analysis
            self._store_historical_entry(key, value, context)
    
    def _apply_team_state_change(self, key: str, value: Any, context: ProcessingContext) -> None:
        """Apply state change to team"""
        # Parse team ID from key (e.g., "team_1_wins" -> team_id = 1)
        parts = key.split("_")
        if len(parts) < 3:
            return
            
        try:
            team_id = int(parts[1])
            attribute = "_".join(parts[2:])
        except (ValueError, IndexError):
            self.logger.warning(f"Could not parse team state change key: {key}")
            return
        
        if team_id not in self.team_states:
            self.logger.warning(f"Unknown team ID in state change: {team_id}")
            return
        
        team_state = self.team_states[team_id]
        
        # Apply the state change
        if attribute == "wins":
            team_state.wins += int(value)
        elif attribute == "losses":
            team_state.losses += int(value)
        elif attribute == "ties":
            team_state.ties += int(value)
        elif attribute == "momentum":
            team_state.momentum += float(value)
        elif attribute == "chemistry" or attribute == "overall_chemistry":
            team_state.chemistry_level += float(value)
        elif attribute == "fatigue_level":
            team_state.team_fatigue_level += float(value)
        elif attribute == "coaching_effectiveness":
            team_state.coaching_effectiveness += float(value)
        elif hasattr(team_state, attribute):
            # Generic attribute setting
            current_value = getattr(team_state, attribute)
            if isinstance(current_value, (int, float)):
                setattr(team_state, attribute, current_value + value)
            else:
                setattr(team_state, attribute, value)
        
        # Update games played from game results
        if attribute in ["wins", "losses", "ties"]:
            team_state.games_played = team_state.wins + team_state.losses + team_state.ties
            if context.current_date:
                team_state.last_game_date = context.current_date.date() if isinstance(context.current_date, datetime) else context.current_date
    
    def _apply_player_state_change(self, key: str, value: Any, context: ProcessingContext, teams_updated: List[int]) -> None:
        """Apply state change to player"""
        # Parse player name from key (e.g., "player_John_Smith_passing_yards")
        parts = key.split("_")
        if len(parts) < 3:
            return
        
        # Find where player name ends and attribute begins
        # Look for common stat/attribute names
        attribute_indicators = ["passing", "rushing", "receiving", "season", "games", "overall", 
                              "injury", "fatigue", "contract", "roster", "negotiation"]
        
        player_name_parts = []
        attribute_parts = []
        found_attribute = False
        
        for i, part in enumerate(parts[1:], 1):  # Skip "player_"
            if not found_attribute and any(part.lower().startswith(indicator) for indicator in attribute_indicators):
                found_attribute = True
                attribute_parts = parts[i:]
                break
            elif not found_attribute:
                player_name_parts.append(part)
        
        if not attribute_parts:
            # Fallback: assume last part is attribute
            if len(player_name_parts) > 0:
                attribute_parts = [player_name_parts.pop()]
        
        player_name = "_".join(player_name_parts)
        attribute = "_".join(attribute_parts)
        
        if not player_name:
            self.logger.warning(f"Could not parse player name from key: {key}")
            return
        
        # Get or create player stats
        if player_name not in self.player_stats:
            # Try to determine team from context or affected teams
            team_id = 0
            if hasattr(context, 'team_id'):
                team_id = context.team_id
            elif len(teams_updated) == 1:
                team_id = teams_updated[0]
            
            self.player_stats[player_name] = PlayerSeasonStats(
                player_name=player_name,
                team_id=team_id
            )
        
        player_stats = self.player_stats[player_name]
        
        # Apply the state change
        if attribute.startswith("season_"):
            # Season statistics
            stat_name = attribute[7:]  # Remove "season_" prefix
            if hasattr(player_stats, stat_name):
                current_value = getattr(player_stats, stat_name)
                setattr(player_stats, stat_name, current_value + value)
        elif attribute == "games_played":
            player_stats.games_played += int(value)
        elif attribute == "overall_rating":
            player_stats.overall_rating_change += float(value)
        elif attribute == "fatigue":
            player_stats.current_fatigue += float(value)
        elif hasattr(player_stats, attribute):
            # Generic attribute update
            current_value = getattr(player_stats, attribute)
            if isinstance(current_value, (int, float)):
                setattr(player_stats, attribute, current_value + value)
            else:
                setattr(player_stats, attribute, value)
    
    def _apply_statistics_updates(self, processing_result: ProcessingResult, context: ProcessingContext) -> None:
        """Apply statistics updates (currently just logged)"""
        if processing_result.statistics_generated:
            self.logger.debug(f"Statistics updated: {list(processing_result.statistics_generated.keys())}")
    
    def _process_side_effects(self, processing_result: ProcessingResult, context: ProcessingContext) -> None:
        """Process side effects and add to narrative"""
        for side_effect in processing_result.side_effects:
            # Add significant side effects to weekly highlights
            if self._is_significant_side_effect(side_effect):
                self.narrative.add_weekly_highlight(context.season_week, side_effect)
            
            # Check for milestone achievements
            if "milestone" in side_effect.lower() or "record" in side_effect.lower():
                self.narrative.milestone_achievements.append(f"Week {context.season_week}: {side_effect}")
            
            # Check for surprising developments
            if any(keyword in side_effect.lower() for keyword in ["surprising", "unexpected", "breakthrough", "upset"]):
                self.narrative.surprising_developments.append(f"Week {context.season_week}: {side_effect}")
    
    def _is_significant_side_effect(self, side_effect: str) -> bool:
        """Determine if a side effect is significant enough for narrative"""
        significant_keywords = [
            "major", "significant", "breakthrough", "milestone", "record", 
            "exceptional", "outstanding", "dramatic", "upset", "impressive"
        ]
        return any(keyword in side_effect.lower() for keyword in significant_keywords)
    
    def _store_historical_entry(self, entry_type: str, entry_data: Any, context: ProcessingContext) -> None:
        """Store historical entries for later analysis"""
        # This could be expanded to maintain detailed historical records
        self.logger.debug(f"Historical entry stored: {entry_type}")
    
    def get_team_standings(self, sort_by: str = "win_percentage") -> List[TeamSeasonState]:
        """
        Get current team standings
        
        Args:
            sort_by: How to sort teams ("win_percentage", "wins", "point_differential")
            
        Returns:
            List of team states sorted by the specified metric
        """
        teams = list(self.team_states.values())
        
        if sort_by == "win_percentage":
            teams.sort(key=lambda t: t.get_win_percentage(), reverse=True)
        elif sort_by == "wins":
            teams.sort(key=lambda t: t.wins, reverse=True)
        elif sort_by == "point_differential":
            teams.sort(key=lambda t: t.get_point_differential(), reverse=True)
        
        return teams
    
    def get_player_leaders(self, stat_category: str, limit: int = 10) -> List[PlayerSeasonStats]:
        """
        Get leading players in a statistical category
        
        Args:
            stat_category: The statistic to rank by
            limit: Number of players to return
            
        Returns:
            List of top players in that category
        """
        players = [p for p in self.player_stats.values() if hasattr(p, stat_category)]
        players.sort(key=lambda p: getattr(p, stat_category), reverse=True)
        return players[:limit]
    
    def get_season_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the season state"""
        return {
            "season_year": self.season_year,
            "current_week": self.current_week,
            "season_phase": self.season_phase,
            "current_date": self.current_date.isoformat() if self.current_date else None,
            "teams_tracked": len(self.team_states),
            "players_tracked": len(self.player_stats),
            "total_games_played": sum(team.games_played for team in self.team_states.values()) // 2,  # Divide by 2 since each game involves 2 teams
            "major_storylines": len(self.narrative.major_storylines),
            "milestone_achievements": len(self.narrative.milestone_achievements),
            "processing_events": len(self.processing_history)
        }
    
    def reset_season(self, new_season_year: int) -> None:
        """Reset for a new season"""
        self.season_year = new_season_year
        self.current_week = 0
        self.season_phase = "preseason"
        self.current_date = None
        
        # Reset team states
        for team_state in self.team_states.values():
            team_state.wins = 0
            team_state.losses = 0
            team_state.ties = 0
            team_state.points_for = 0
            team_state.points_against = 0
            team_state.momentum = 0.0
            team_state.games_played = 0
            team_state.last_game_date = None
        
        # Clear player stats
        self.player_stats.clear()
        
        # Reset narrative
        self.narrative = SeasonNarrative(new_season_year)
        
        # Clear logs
        self.state_changes_log.clear()
        self.processing_history.clear()
        
        self.logger.info(f"Season reset to {new_season_year}")