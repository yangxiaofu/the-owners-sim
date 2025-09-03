"""
Play-by-Play Auditor - Complete audit trail of all game state changes

This module provides comprehensive auditing capabilities for game simulation,
tracking every state change, decision, and result for debugging, replay, and
analysis purposes.

The auditor maintains a complete immutable record of:
- Every play result with full context
- All state transitions and their triggers  
- Decision-making processes and logic paths
- System events and performance markers
- Error conditions and recovery actions

Design Principles:
- Immutable audit trail: records can never be modified after creation
- Complete context: every entry includes full situational context
- Fast querying: optimized for analysis and debugging queries
- Minimal overhead: efficient logging that doesn't impact game performance
- Replay capable: sufficient detail to replay any game scenario
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union, Iterator
from enum import Enum
import time
import json
from datetime import datetime
from uuid import uuid4

from game_engine.state_transitions.data_structures.game_state_transition import GameStateTransition
from game_engine.plays.data_structures import PlayResult


class AuditEventType(Enum):
    """Types of events that can be audited"""
    PLAY_EXECUTED = "play_executed"
    STATE_TRANSITION = "state_transition"  
    POSSESSION_CHANGE = "possession_change"
    SCORE_UPDATE = "score_update"
    CLOCK_UPDATE = "clock_update"
    QUARTER_CHANGE = "quarter_change"
    DRIVE_START = "drive_start"
    DRIVE_END = "drive_end"
    TIMEOUT = "timeout"
    PENALTY = "penalty"
    INJURY = "injury"
    SUBSTITUTION = "substitution"
    CHALLENGE = "challenge"
    SYSTEM_EVENT = "system_event"
    ERROR_CONDITION = "error_condition"
    GAME_START = "game_start"
    GAME_END = "game_end"
    VALIDATION_FAILURE = "validation_failure"
    PERFORMANCE_MARKER = "performance_marker"


@dataclass(frozen=True)
class GameContext:
    """Immutable snapshot of game context at time of event"""
    game_time: int  # Seconds remaining in game
    quarter: int
    down: int
    distance: int
    field_position: int
    possession_team_id: str
    home_score: int
    away_score: int
    
    # Additional context
    timeouts_remaining: Dict[str, int] = field(default_factory=dict)
    red_zone: bool = False
    goal_line: bool = False
    two_minute_warning: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'game_time': self.game_time,
            'quarter': self.quarter,
            'down': self.down,
            'distance': self.distance,
            'field_position': self.field_position,
            'possession_team_id': self.possession_team_id,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'timeouts_remaining': dict(self.timeouts_remaining),
            'red_zone': self.red_zone,
            'goal_line': self.goal_line,
            'two_minute_warning': self.two_minute_warning
        }


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit trail entry"""
    # Core identification
    entry_id: str
    timestamp: float  # Unix timestamp
    sequence_number: int  # Sequential ordering within game
    event_type: AuditEventType
    
    # Game context
    game_context: GameContext
    
    # Event-specific data
    play_result: Optional[PlayResult] = None
    state_transition: Optional[GameStateTransition] = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    performance_data: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization and analysis"""
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'sequence_number': self.sequence_number,
            'event_type': self.event_type.value,
            'game_context': self.game_context.to_dict(),
            'play_result': self._serialize_play_result(),
            'state_transition': self._serialize_state_transition(),
            'event_data': dict(self.event_data),
            'description': self.description,
            'tags': list(self.tags),
            'performance_data': dict(self.performance_data)
        }
    
    def _serialize_play_result(self) -> Optional[Dict[str, Any]]:
        """Serialize play result for JSON compatibility"""
        if not self.play_result:
            return None
            
        # Convert PlayResult dataclass to dict
        result_dict = {
            'play_type': self.play_result.play_type,
            'outcome': self.play_result.outcome,
            'yards_gained': self.play_result.yards_gained,
            'time_elapsed': self.play_result.time_elapsed,
            'is_turnover': self.play_result.is_turnover,
            'is_score': self.play_result.is_score,
            'score_points': self.play_result.score_points,
            'description': self.play_result.get_summary()
        }
        
        # Add optional fields if present
        if self.play_result.primary_player:
            result_dict['primary_player'] = self.play_result.primary_player
        if self.play_result.quarterback:
            result_dict['quarterback'] = self.play_result.quarterback
        if self.play_result.receiver:
            result_dict['receiver'] = self.play_result.receiver
        if self.play_result.rusher:
            result_dict['rusher'] = self.play_result.rusher
            
        return result_dict
    
    def _serialize_state_transition(self) -> Optional[Dict[str, Any]]:
        """Serialize state transition for JSON compatibility"""
        if not self.state_transition:
            return None
        # TODO: Implement when GameStateTransition is available
        return {"placeholder": "state_transition_serialization"}


@dataclass
class AuditQuery:
    """Query builder for audit trail analysis"""
    event_types: Optional[List[AuditEventType]] = None
    team_id: Optional[str] = None
    quarter: Optional[int] = None
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    tags: Optional[List[str]] = None
    time_range: Optional[tuple] = None  # (start_timestamp, end_timestamp)
    
    def matches(self, entry: AuditEntry) -> bool:
        """Check if entry matches query criteria"""
        if self.event_types and entry.event_type not in self.event_types:
            return False
            
        if self.team_id and entry.game_context.possession_team_id != self.team_id:
            return False
            
        if self.quarter and entry.game_context.quarter != self.quarter:
            return False
            
        if self.start_sequence and entry.sequence_number < self.start_sequence:
            return False
            
        if self.end_sequence and entry.sequence_number > self.end_sequence:
            return False
            
        if self.tags and not any(tag in entry.tags for tag in self.tags):
            return False
            
        if self.time_range:
            start_time, end_time = self.time_range
            if entry.timestamp < start_time or entry.timestamp > end_time:
                return False
                
        return True


class PlayByPlayAuditor:
    """
    Comprehensive audit trail system for game simulation.
    
    Provides complete immutable record of all game events, state changes, and
    decision processes for debugging, analysis, and replay capabilities.
    
    Key Features:
    - Immutable audit trail with complete context
    - Fast querying and analysis capabilities  
    - Minimal performance overhead during gameplay
    - Complete replay capability from audit log
    - Error tracking and debugging support
    - Performance monitoring integration
    """
    
    def __init__(self, game_id: str, home_team_id: str, away_team_id: str):
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Audit trail storage
        self.audit_trail: List[AuditEntry] = []
        self.sequence_counter = 0
        
        # Performance tracking
        self.game_start_time = time.time()
        self.last_performance_check = self.game_start_time
        
        # Quick lookup indices for efficient querying
        self.entries_by_type: Dict[AuditEventType, List[AuditEntry]] = {}
        self.entries_by_team: Dict[str, List[AuditEntry]] = {}
        self.entries_by_quarter: Dict[int, List[AuditEntry]] = {}
        
        # Error tracking
        self.error_count = 0
        self.validation_failures = 0
        
        # Record game start
        self.record_system_event(
            "game_started",
            f"Game {game_id} started: {home_team_id} vs {away_team_id}",
            tags=["game_start", "system"]
        )
    
    def create_game_context(self, game_state) -> GameContext:
        """Create immutable game context snapshot from current game state"""
        # TODO: Extract from actual GameState object when available
        return GameContext(
            game_time=getattr(game_state.clock, 'time_remaining', 3600),
            quarter=getattr(game_state.clock, 'quarter', 1),
            down=getattr(game_state.field, 'down', 1),
            distance=getattr(game_state.field, 'yards_to_go', 10),
            field_position=getattr(game_state.field, 'field_position', 50),
            possession_team_id=getattr(game_state.field, 'possession_team_id', self.home_team_id),
            home_score=getattr(game_state.scoreboard, 'home_score', 0),
            away_score=getattr(game_state.scoreboard, 'away_score', 0),
            red_zone=getattr(game_state.field, 'field_position', 50) > 80,
            goal_line=getattr(game_state.field, 'field_position', 50) > 90,
            two_minute_warning=getattr(game_state.clock, 'time_remaining', 3600) <= 120
        )
    
    def record_play(self, play_result: PlayResult, game_state, 
                   description: Optional[str] = None, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record a play execution in the audit trail"""
        
        context = self.create_game_context(game_state)
        
        # Generate performance data
        current_time = time.time()
        perf_data = {
            "execution_time": current_time - self.last_performance_check,
            "game_duration": current_time - self.game_start_time
        }
        self.last_performance_check = current_time
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=current_time,
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.PLAY_EXECUTED,
            game_context=context,
            play_result=play_result,
            description=description or play_result.get_summary(),
            tags=tags or self._generate_play_tags(play_result),
            performance_data=perf_data
        )
        
        self._add_entry(entry)
        return entry
    
    def record_state_transition(self, transition: GameStateTransition, game_state,
                               description: str, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record a state transition in the audit trail"""
        
        context = self.create_game_context(game_state)
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.STATE_TRANSITION,
            game_context=context,
            state_transition=transition,
            description=description,
            tags=tags or ["state_change"]
        )
        
        self._add_entry(entry)
        return entry
    
    def record_possession_change(self, old_team: str, new_team: str, reason: str, 
                                game_state, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record possession change event"""
        
        context = self.create_game_context(game_state)
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.POSSESSION_CHANGE,
            game_context=context,
            description=f"Possession changed from {old_team} to {new_team}: {reason}",
            tags=tags or ["possession", reason],
            event_data={
                "old_team": old_team,
                "new_team": new_team,
                "reason": reason
            }
        )
        
        self._add_entry(entry)
        return entry
    
    def record_score(self, team_id: str, points: int, play_type: str, 
                    game_state, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record scoring event"""
        
        context = self.create_game_context(game_state)
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.SCORE_UPDATE,
            game_context=context,
            description=f"{team_id} scores {points} points via {play_type}",
            tags=tags or ["scoring", play_type],
            event_data={
                "scoring_team": team_id,
                "points": points,
                "play_type": play_type,
                "new_score": {
                    "home": context.home_score,
                    "away": context.away_score
                }
            }
        )
        
        self._add_entry(entry)
        return entry
    
    def record_drive_event(self, event_type: str, team_id: str, game_state, 
                          drive_data: Optional[Dict] = None, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record drive start/end events"""
        
        context = self.create_game_context(game_state)
        
        audit_type = AuditEventType.DRIVE_START if event_type == "start" else AuditEventType.DRIVE_END
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=audit_type,
            game_context=context,
            description=f"Drive {event_type} for {team_id}",
            tags=tags or ["drive", event_type, team_id],
            event_data=drive_data or {}
        )
        
        self._add_entry(entry)
        return entry
    
    def record_system_event(self, event_name: str, description: str, 
                           event_data: Optional[Dict] = None, tags: Optional[List[str]] = None) -> AuditEntry:
        """Record system-level events (game start/end, errors, etc.)"""
        
        # For system events, create minimal context
        minimal_context = GameContext(
            game_time=0, quarter=0, down=0, distance=0, field_position=0,
            possession_team_id="", home_score=0, away_score=0
        )
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.SYSTEM_EVENT,
            game_context=minimal_context,
            description=description,
            tags=tags or ["system"],
            event_data=event_data or {"event_name": event_name}
        )
        
        self._add_entry(entry)
        return entry
    
    def record_error(self, error_type: str, error_message: str, 
                    error_data: Optional[Dict] = None, game_state=None) -> AuditEntry:
        """Record error conditions for debugging"""
        
        self.error_count += 1
        
        context = self.create_game_context(game_state) if game_state else GameContext(
            game_time=0, quarter=0, down=0, distance=0, field_position=0,
            possession_team_id="", home_score=0, away_score=0
        )
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.ERROR_CONDITION,
            game_context=context,
            description=f"{error_type}: {error_message}",
            tags=["error", error_type],
            event_data=error_data or {"error_type": error_type, "message": error_message}
        )
        
        self._add_entry(entry)
        return entry
    
    def record_validation_failure(self, validation_type: str, details: str, 
                                 game_state=None) -> AuditEntry:
        """Record validation failures"""
        
        self.validation_failures += 1
        
        context = self.create_game_context(game_state) if game_state else GameContext(
            game_time=0, quarter=0, down=0, distance=0, field_position=0,
            possession_team_id="", home_score=0, away_score=0
        )
        
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=time.time(),
            sequence_number=self._next_sequence(),
            event_type=AuditEventType.VALIDATION_FAILURE,
            game_context=context,
            description=f"Validation failed: {validation_type} - {details}",
            tags=["validation", "failure", validation_type],
            event_data={"validation_type": validation_type, "details": details}
        )
        
        self._add_entry(entry)
        return entry
    
    def _generate_play_tags(self, play_result: PlayResult) -> List[str]:
        """Generate appropriate tags for a play result"""
        tags = ["play", play_result.play_type, play_result.outcome]
        
        if play_result.is_score:
            tags.append("scoring")
        if play_result.is_turnover:
            tags.append("turnover")
        if play_result.big_play:
            tags.append("big_play")
        if play_result.explosive_play:
            tags.append("explosive")
        if play_result.red_zone_play:
            tags.append("red_zone")
        if play_result.goal_line_play:
            tags.append("goal_line")
        if play_result.two_minute_drill:
            tags.append("two_minute")
        if play_result.down == 3:
            tags.append("third_down")
        elif play_result.down == 4:
            tags.append("fourth_down")
            
        return tags
    
    def _next_sequence(self) -> int:
        """Generate next sequence number"""
        self.sequence_counter += 1
        return self.sequence_counter
    
    def _add_entry(self, entry: AuditEntry) -> None:
        """Add entry to audit trail and update indices"""
        self.audit_trail.append(entry)
        
        # Update indices
        if entry.event_type not in self.entries_by_type:
            self.entries_by_type[entry.event_type] = []
        self.entries_by_type[entry.event_type].append(entry)
        
        if entry.game_context.possession_team_id:
            team_id = entry.game_context.possession_team_id
            if team_id not in self.entries_by_team:
                self.entries_by_team[team_id] = []
            self.entries_by_team[team_id].append(entry)
        
        if entry.game_context.quarter > 0:
            quarter = entry.game_context.quarter
            if quarter not in self.entries_by_quarter:
                self.entries_by_quarter[quarter] = []
            self.entries_by_quarter[quarter].append(entry)
    
    # === QUERY AND ANALYSIS METHODS ===
    
    def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Execute query against audit trail"""
        results = []
        for entry in self.audit_trail:
            if query.matches(entry):
                results.append(entry)
        return results
    
    def get_plays_by_type(self, play_type: str) -> List[AuditEntry]:
        """Get all plays of a specific type"""
        return [entry for entry in self.entries_by_type.get(AuditEventType.PLAY_EXECUTED, [])
                if entry.play_result and entry.play_result.play_type == play_type]
    
    def get_plays_by_team(self, team_id: str) -> List[AuditEntry]:
        """Get all plays by a specific team"""
        return self.entries_by_team.get(team_id, [])
    
    def get_plays_by_quarter(self, quarter: int) -> List[AuditEntry]:
        """Get all entries from a specific quarter"""
        return self.entries_by_quarter.get(quarter, [])
    
    def get_scoring_plays(self) -> List[AuditEntry]:
        """Get all scoring plays"""
        return [entry for entry in self.entries_by_type.get(AuditEventType.PLAY_EXECUTED, [])
                if entry.play_result and entry.play_result.is_score]
    
    def get_turnovers(self) -> List[AuditEntry]:
        """Get all turnover plays"""
        return [entry for entry in self.entries_by_type.get(AuditEventType.PLAY_EXECUTED, [])
                if entry.play_result and entry.play_result.is_turnover]
    
    def get_drive_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all drives"""
        drive_starts = self.entries_by_type.get(AuditEventType.DRIVE_START, [])
        drive_ends = self.entries_by_type.get(AuditEventType.DRIVE_END, [])
        
        drives = []
        for i, start in enumerate(drive_starts):
            drive_info = {
                "start_sequence": start.sequence_number,
                "start_time": start.timestamp,
                "team": start.game_context.possession_team_id,
                "start_field_position": start.game_context.field_position
            }
            
            # Find corresponding end
            if i < len(drive_ends):
                end = drive_ends[i]
                drive_info.update({
                    "end_sequence": end.sequence_number,
                    "end_time": end.timestamp,
                    "duration": end.timestamp - start.timestamp,
                    "end_field_position": end.game_context.field_position
                })
            
            drives.append(drive_info)
        
        return drives
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors and issues"""
        errors = self.entries_by_type.get(AuditEventType.ERROR_CONDITION, [])
        validation_failures = self.entries_by_type.get(AuditEventType.VALIDATION_FAILURE, [])
        
        return {
            "total_errors": len(errors),
            "total_validation_failures": len(validation_failures),
            "error_details": [entry.to_dict() for entry in errors],
            "validation_details": [entry.to_dict() for entry in validation_failures],
            "error_types": list(set(entry.event_data.get("error_type", "unknown") for entry in errors)),
            "validation_types": list(set(entry.event_data.get("validation_type", "unknown") for entry in validation_failures))
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance analysis from audit trail"""
        all_entries = self.audit_trail
        
        if not all_entries:
            return {"error": "No entries in audit trail"}
        
        game_duration = all_entries[-1].timestamp - all_entries[0].timestamp
        
        # Extract performance data
        execution_times = []
        for entry in all_entries:
            if "execution_time" in entry.performance_data:
                execution_times.append(entry.performance_data["execution_time"])
        
        perf_summary = {
            "game_duration_seconds": game_duration,
            "total_entries": len(all_entries),
            "entries_per_second": len(all_entries) / game_duration if game_duration > 0 else 0,
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "min_execution_time": min(execution_times) if execution_times else 0
        }
        
        return perf_summary
    
    def export_to_json(self, filename: Optional[str] = None) -> str:
        """Export complete audit trail to JSON format"""
        export_data = {
            "game_id": self.game_id,
            "home_team": self.home_team_id,
            "away_team": self.away_team_id,
            "game_start_time": self.game_start_time,
            "export_timestamp": time.time(),
            "total_entries": len(self.audit_trail),
            "entries": [entry.to_dict() for entry in self.audit_trail],
            "summary": {
                "errors": self.get_error_summary(),
                "performance": self.get_performance_summary(),
                "drives": self.get_drive_summary()
            }
        }
        
        json_str = json.dumps(export_data, indent=2, default=str)
        
        if filename:
            with open(filename, 'w') as f:
                f.write(json_str)
                
        return json_str
    
    def create_replay_script(self) -> List[Dict[str, Any]]:
        """Create replay script from audit trail"""
        replay_events = []
        
        for entry in self.audit_trail:
            if entry.event_type in [AuditEventType.PLAY_EXECUTED, AuditEventType.STATE_TRANSITION]:
                replay_event = {
                    "sequence": entry.sequence_number,
                    "type": entry.event_type.value,
                    "context": entry.game_context.to_dict(),
                    "description": entry.description
                }
                
                if entry.play_result:
                    replay_event["play_result"] = entry._serialize_play_result()
                
                replay_events.append(replay_event)
        
        return replay_events
    
    def reset(self) -> None:
        """Reset auditor for new game"""
        self.__init__(self.game_id, self.home_team_id, self.away_team_id)