"""
PlayByPlayLogger - Unified play-by-play event logging system.

Single source of truth for all play-by-play events including:
- Kickoffs and kickoff returns
- Offensive/defensive plays
- Special teams (punts, field goals, PATs)
- Timeouts, two-minute warnings, quarter ends

Replaces scattered logging across:
- DriveManager.play_history
- GameLoopController.drive_results
- PlayByPlayDisplay
- BoxScoreDialog exports
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class EventType(Enum):
    """Types of play-by-play events"""
    KICKOFF = "kickoff"
    PLAY = "play"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"
    PAT = "pat"
    TWO_POINT = "two_point"
    TIMEOUT = "timeout"
    TWO_MINUTE_WARNING = "two_minute_warning"
    QUARTER_END = "quarter_end"
    HALFTIME = "halftime"
    GAME_START = "game_start"
    GAME_END = "game_end"
    PENALTY = "penalty"  # Standalone penalty (declined/offsetting)


@dataclass
class PlayByPlayEvent:
    """
    Unified event for all play-by-play logging.

    This is the core data structure that represents any event
    that can occur during a football game.
    """
    event_type: EventType
    quarter: int
    clock_seconds: int  # Seconds remaining in quarter (0-900)
    drive_number: int   # 0 for pre-game/halftime events

    # Team context
    possessing_team_id: int  # 0 for neutral events
    field_position: int      # 0-100 scale (0 = own goal line, 100 = opponent goal line)

    # Play-specific fields (None for non-plays like timeouts)
    down: Optional[int] = None
    distance: Optional[int] = None
    yards_gained: Optional[int] = None

    # Description fields
    description: str = ""      # Human-readable play description
    result_text: str = ""      # Short result ("+5", "TD", "INT", etc.)

    # Outcome flags
    is_scoring: bool = False
    is_turnover: bool = False
    is_first_down: bool = False
    points: int = 0

    # Kickoff-specific fields
    kicking_team_id: Optional[int] = None
    receiving_team_id: Optional[int] = None
    is_touchback: bool = False
    return_yards: int = 0

    # Raw data for detailed export (preserves original objects)
    raw_data: Optional[Dict[str, Any]] = None

    def format_down_distance(self) -> str:
        """Format down and distance for display (shows 'Goal' when in goal-to-go situation)"""
        if self.down is None or self.distance is None:
            return "--"
        ordinal = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(self.down, f"{self.down}th")
        # Goal-to-go: when the first down line would be at or past the goal line
        if self.field_position + self.distance >= 100:
            return f"{ordinal} & Goal"
        return f"{ordinal} & {self.distance}"

    def format_field_position(self) -> str:
        """Format field position for display"""
        if self.field_position <= 50:
            return f"OWN {self.field_position}"
        else:
            return f"OPP {100 - self.field_position}"

    def format_clock(self) -> str:
        """Format clock time for display (MM:SS)"""
        minutes = self.clock_seconds // 60
        seconds = self.clock_seconds % 60
        return f"{minutes}:{seconds:02d}"


@dataclass
class PlayByPlayLog:
    """
    Complete game log containing all play-by-play events.

    Provides methods to query events by drive, quarter, or type.
    """
    game_id: str
    home_team_id: int
    away_team_id: int
    events: List[PlayByPlayEvent] = field(default_factory=list)

    # Score tracking (updated as events are added)
    home_score: int = 0
    away_score: int = 0

    def add_event(self, event: PlayByPlayEvent) -> None:
        """Add an event to the log"""
        self.events.append(event)
        # Update score if this is a scoring event
        if event.is_scoring and event.points > 0:
            if event.possessing_team_id == self.home_team_id:
                self.home_score += event.points
            elif event.possessing_team_id == self.away_team_id:
                self.away_score += event.points

    def get_events_by_drive(self, drive_number: int) -> List[PlayByPlayEvent]:
        """Get all events for a specific drive"""
        return [e for e in self.events if e.drive_number == drive_number]

    def get_events_by_quarter(self, quarter: int) -> List[PlayByPlayEvent]:
        """Get all events for a specific quarter"""
        return [e for e in self.events if e.quarter == quarter]

    def get_events_by_type(self, event_type: EventType) -> List[PlayByPlayEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.event_type == event_type]

    def get_drive_numbers(self) -> List[int]:
        """Get unique drive numbers in order"""
        seen = set()
        drives = []
        for e in self.events:
            if e.drive_number > 0 and e.drive_number not in seen:
                seen.add(e.drive_number)
                drives.append(e.drive_number)
        return drives

    def get_score_at_event(self, event_index: int) -> tuple:
        """Calculate score at a specific event index"""
        home = 0
        away = 0
        for i, event in enumerate(self.events):
            if i > event_index:
                break
            if event.is_scoring and event.points > 0:
                if event.possessing_team_id == self.home_team_id:
                    home += event.points
                elif event.possessing_team_id == self.away_team_id:
                    away += event.points
        return (home, away)


class PlayByPlayLogger:
    """
    Single source of truth for play-by-play event logging.

    Usage:
        logger = PlayByPlayLogger("game_123", home_id=1, away_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)
        logger.log_kickoff(kickoff_result, kicking_team_id=1, receiving_team_id=2, clock_seconds=900)
        logger.log_play(play_result, down=1, distance=10, field_position=25, clock_seconds=855)
        ...
        markdown = logger.export_markdown(team_names={1: "Team A", 2: "Team B"})
    """

    def __init__(self, game_id: str, home_team_id: int, away_team_id: int):
        self.log = PlayByPlayLog(game_id, home_team_id, away_team_id)
        self._current_drive = 0
        self._current_quarter = 1

    @property
    def events(self) -> List[PlayByPlayEvent]:
        """Access the event list"""
        return self.log.events

    def set_quarter(self, quarter: int) -> None:
        """Set the current quarter for subsequent events"""
        self._current_quarter = quarter

    def start_drive(self, drive_number: int) -> None:
        """Start a new drive"""
        self._current_drive = drive_number

    def log_kickoff(
        self,
        kickoff_result: Any,
        kicking_team_id: int,
        receiving_team_id: int,
        clock_seconds: int
    ) -> None:
        """
        Log a kickoff event.

        Args:
            kickoff_result: The KickoffResult object from simulation
            kicking_team_id: Team performing the kickoff
            receiving_team_id: Team receiving the kickoff
            clock_seconds: Seconds remaining in quarter
        """
        is_touchback = getattr(kickoff_result, 'is_touchback', False)
        return_yards = getattr(kickoff_result, 'return_yards', 0)
        starting_pos = getattr(kickoff_result, 'starting_field_position', 25)

        if is_touchback:
            description = "Kickoff: Touchback"
            result_text = "TB"
        elif return_yards > 0:
            description = f"Kickoff Return: {return_yards} yards"
            result_text = f"+{return_yards}"
        else:
            description = "Kickoff"
            result_text = ""

        event = PlayByPlayEvent(
            event_type=EventType.KICKOFF,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=receiving_team_id,
            field_position=starting_pos,
            description=description,
            result_text=result_text,
            kicking_team_id=kicking_team_id,
            receiving_team_id=receiving_team_id,
            is_touchback=is_touchback,
            return_yards=return_yards,
            raw_data={'kickoff_result': kickoff_result}
        )
        self.log.add_event(event)

    def log_play(
        self,
        play_result: Any,
        down: int,
        distance: int,
        field_position: int,
        clock_seconds: int,
        possessing_team_id: Optional[int] = None
    ) -> None:
        """
        Log a standard play event (run, pass, etc).

        Args:
            play_result: The PlayResult object from simulation
            down: Current down (1-4)
            distance: Yards to first down
            field_position: Field position (0-100)
            clock_seconds: Seconds remaining in quarter
            possessing_team_id: Override for possessing team (uses play_result if None)
        """
        team_id = possessing_team_id or getattr(play_result, 'possessing_team_id', 0)
        yards = getattr(play_result, 'yards', 0)
        is_scoring = getattr(play_result, 'is_scoring_play', False)
        is_turnover = getattr(play_result, 'is_turnover', False)
        is_first_down = getattr(play_result, 'achieved_first_down', False)
        points = getattr(play_result, 'points', 0)

        # Format result text
        if is_scoring and points == 6:
            result_text = f"**+{100 - field_position} TD**"
        elif is_scoring and points == 3:
            result_text = "FG"
        elif is_turnover:
            result_text = f"{yards:+d} TO"
        else:
            result_text = f"{yards:+d}"

        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=team_id,
            field_position=field_position,
            down=down,
            distance=distance,
            yards_gained=yards,
            description=self._format_play_description(play_result),
            result_text=result_text,
            is_scoring=is_scoring,
            is_turnover=is_turnover,
            is_first_down=is_first_down,
            points=points,
            raw_data={'play_result': play_result}
        )
        self.log.add_event(event)

    def log_punt(
        self,
        punt_result: Any,
        punting_team_id: int,
        receiving_team_id: int,
        down: int,
        distance: int,
        field_position: int,
        clock_seconds: int
    ) -> None:
        """Log a punt event"""
        punt_distance = getattr(punt_result, 'punt_distance', 0)
        return_yards = getattr(punt_result, 'return_yards', 0)
        net_yards = punt_distance - return_yards

        if return_yards > 0:
            description = f"Punt {punt_distance}yds (ret {return_yards})"
        else:
            description = f"Punt {punt_distance}yds"

        event = PlayByPlayEvent(
            event_type=EventType.PUNT,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=punting_team_id,
            field_position=field_position,
            down=down,
            distance=distance,
            yards_gained=net_yards,
            description=description,
            result_text=f"+{net_yards}",
            raw_data={'punt_result': punt_result}
        )
        self.log.add_event(event)

    def log_field_goal(
        self,
        fg_result: Any,
        kicking_team_id: int,
        field_position: int,
        clock_seconds: int,
        down: int = 4,
        distance: int = 10
    ) -> None:
        """Log a field goal attempt"""
        is_good = getattr(fg_result, 'is_good', False) or getattr(fg_result, 'made', False)
        distance_yards = 100 - field_position + 17  # Add 17 for end zone + holder position

        if is_good:
            description = f"FG GOOD {distance_yards}yds"
            points = 3
        else:
            description = f"FG MISSED {distance_yards}yds"
            points = 0

        event = PlayByPlayEvent(
            event_type=EventType.FIELD_GOAL,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=kicking_team_id,
            field_position=field_position,
            down=down,
            distance=distance,
            description=description,
            result_text="+0" if is_good else "MISS",
            is_scoring=is_good,
            points=points,
            raw_data={'fg_result': fg_result}
        )
        self.log.add_event(event)

    def log_pat(
        self,
        pat_result: Any,
        kicking_team_id: int,
        clock_seconds: int
    ) -> None:
        """Log a PAT (extra point) attempt"""
        is_good = getattr(pat_result, 'success', False) or getattr(pat_result, 'made', False)
        pat_type = getattr(pat_result, 'type', 'extra_point')

        if pat_type == 'two_point':
            description = "2-Point Conversion GOOD" if is_good else "2-Point Conversion FAILED"
            points = 2 if is_good else 0
            event_type = EventType.TWO_POINT
        else:
            description = "Extra Point GOOD" if is_good else "Extra Point MISSED"
            points = 1 if is_good else 0
            event_type = EventType.PAT

        event = PlayByPlayEvent(
            event_type=event_type,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=kicking_team_id,
            field_position=98,  # PATs are from the 2-yard line
            description=description,
            result_text=f"+{points}",
            is_scoring=is_good,
            points=points,
            raw_data={'pat_result': pat_result}
        )
        self.log.add_event(event)

    def log_penalty(
        self,
        penalty_type: str,
        yards_assessed: int,
        team_penalized: str,
        clock_seconds: int,
        field_position: int,
        down: int,
        distance: int,
        possessing_team_id: int,
        penalized_player_name: str = "",
        penalized_player_number: int = 0,
        penalty_accepted: bool = True,
        enforcement_spot: str = "previous_spot",
        new_field_position: int = 0,
        new_down: int = 0,
        new_distance: int = 0,
        is_first_down: bool = False,
        play_negated: bool = False,
        raw_penalty_data: Any = None
    ) -> None:
        """
        Log a penalty event with full enforcement details.

        Args:
            penalty_type: Type of penalty (e.g., "offensive_holding", "false_start")
            yards_assessed: Yards assessed for the penalty (negative for offensive)
            team_penalized: "home" or "away"
            clock_seconds: Seconds remaining in quarter
            field_position: Field position when penalty occurred
            down: Down when penalty occurred
            distance: Distance when penalty occurred
            possessing_team_id: Team with possession when penalty occurred
            penalized_player_name: Name of player who committed penalty (optional)
            penalized_player_number: Jersey number of player (optional)
            penalty_accepted: Whether the penalty was accepted
            enforcement_spot: Enforcement spot used ("previous_spot", "spot_of_foul", etc.)
            new_field_position: Ball position after enforcement
            new_down: Down after enforcement
            new_distance: Distance after enforcement
            is_first_down: Whether penalty resulted in first down
            play_negated: Whether the play was negated
            raw_penalty_data: Raw penalty data object for detailed export
        """
        # Format penalty description
        penalty_name = penalty_type.replace("_", " ").title()
        if penalized_player_number > 0:
            player_info = f"#{penalized_player_number}"
            if penalized_player_name:
                player_info += f" {penalized_player_name}"
        else:
            player_info = ""

        if penalty_accepted:
            if player_info:
                description = f"PENALTY - {penalty_name} on {player_info}, {abs(yards_assessed)} yards"
            else:
                description = f"PENALTY - {penalty_name}, {abs(yards_assessed)} yards"

            if is_first_down:
                description += ", Automatic First Down"
            elif play_negated:
                description += ", Replay Down"
        else:
            description = f"PENALTY - {penalty_name} DECLINED"

        # Result text shows yards and new situation
        if penalty_accepted:
            if new_field_position > 0 and new_down > 0:
                ordinal = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(new_down, f"{new_down}th")
                if is_first_down:
                    result_text = f"{yards_assessed:+d} → {ordinal} & {new_distance}"
                else:
                    result_text = f"{yards_assessed:+d}"
            else:
                result_text = f"{yards_assessed:+d}"
        else:
            result_text = "DECLINED"

        event = PlayByPlayEvent(
            event_type=EventType.PENALTY,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=possessing_team_id,
            field_position=field_position,
            down=down,
            distance=distance,
            yards_gained=yards_assessed if penalty_accepted else 0,
            description=description,
            result_text=result_text,
            is_scoring=False,
            is_turnover=False,
            is_first_down=is_first_down,
            points=0,
            raw_data={
                'penalty_type': penalty_type,
                'yards_assessed': yards_assessed,
                'team_penalized': team_penalized,
                'penalty_accepted': penalty_accepted,
                'enforcement_spot': enforcement_spot,
                'new_field_position': new_field_position,
                'new_down': new_down,
                'new_distance': new_distance,
                'play_negated': play_negated,
                'penalized_player_name': penalized_player_name,
                'penalized_player_number': penalized_player_number,
                'raw_penalty_data': raw_penalty_data
            }
        )
        self.log.add_event(event)

    def log_special_event(
        self,
        event_type: EventType,
        description: str,
        clock_seconds: int
    ) -> None:
        """
        Log a special event (timeout, two-minute warning, etc).

        Args:
            event_type: Type of special event
            description: Description text
            clock_seconds: Seconds remaining in quarter
        """
        event = PlayByPlayEvent(
            event_type=event_type,
            quarter=self._current_quarter,
            clock_seconds=clock_seconds,
            drive_number=self._current_drive,
            possessing_team_id=0,
            field_position=0,
            description=description
        )
        self.log.add_event(event)

    def log_two_minute_warning(self, clock_seconds: int = 120) -> None:
        """Log the two-minute warning"""
        self.log_special_event(
            EventType.TWO_MINUTE_WARNING,
            "TWO-MINUTE WARNING",
            clock_seconds
        )

    def log_quarter_end(self, quarter: int) -> None:
        """Log end of quarter"""
        self.log_special_event(
            EventType.QUARTER_END,
            f"End of Quarter {quarter}",
            0
        )

    def log_halftime(self) -> None:
        """Log halftime"""
        self.log_special_event(
            EventType.HALFTIME,
            "HALFTIME",
            0
        )

    def _format_play_description(self, play_result: Any) -> str:
        """Format a play result into a human-readable description"""
        outcome = getattr(play_result, 'outcome', None)
        yards = getattr(play_result, 'yards', 0)

        if outcome is None:
            return "Play"

        # Handle enum or string outcome
        if hasattr(outcome, 'value'):
            outcome_str = outcome.value
        else:
            outcome_str = str(outcome)

        outcome_lower = outcome_str.lower()

        # Get player info if available
        players = ""
        if hasattr(play_result, 'get_key_players'):
            players = play_result.get_key_players()
            if players:
                players = f" ({players})"

        # Check for touchdown
        is_td = getattr(play_result, 'is_scoring_play', False) and getattr(play_result, 'points', 0) == 6

        # Format based on play type
        if outcome_lower == 'incomplete' or 'deflected' in outcome_lower:
            return f"Incomplete{players}"
        elif outcome_lower == 'completion' or ('complete' in outcome_lower and 'incomplete' not in outcome_lower):
            desc = f"Pass{players}"
            if is_td:
                desc += " **TD**"
            return desc
        elif outcome_lower == 'interception':
            return f"INT{players}"
        elif 'sack' in outcome_lower:
            return f"Sack{players}"
        elif 'scramble' in outcome_lower:
            # QB scramble - format as "QB Scrambles for X yards, tackled by Defender"
            qb_name = ""
            tackler_info = ""
            if players:
                inner = players.strip(" ()")
                if ", tackled by " in inner:
                    parts = inner.split(", tackled by ")
                    qb_name = parts[0]
                    tackler_info = f", tackled by {parts[1]}"
                else:
                    qb_name = inner

            if is_td:
                return f"{qb_name} Scrambles for {yards} yards **TD**"
            else:
                return f"{qb_name} Scrambles for {yards} yards{tackler_info}"
        elif 'rush' in outcome_lower or 'run' in outcome_lower:
            desc = f"Rush{players}"
            if is_td:
                desc += " **TD**"
            return desc
        elif 'pass' in outcome_lower:
            if 'incomplete' in outcome_lower:
                return f"Incomplete{players}"
            elif yards == 0:
                return f"Incomplete{players}"
            else:
                desc = f"Pass{players}"
                if is_td:
                    desc += " **TD**"
                return desc
        else:
            # Fallback
            return outcome_str.replace('_', ' ').title() + players

    # ========== EXPORT METHODS ==========

    def export_markdown(
        self,
        team_names: Dict[int, str],
        team_abbrevs: Optional[Dict[int, str]] = None
    ) -> str:
        """
        Export the log as markdown formatted play-by-play.

        Args:
            team_names: Mapping of team_id to full team name
            team_abbrevs: Mapping of team_id to abbreviation (optional)

        Returns:
            Markdown formatted string
        """
        if team_abbrevs is None:
            team_abbrevs = {tid: name[:3].upper() for tid, name in team_names.items()}

        lines = []
        home_name = team_names.get(self.log.home_team_id, "Home")
        away_name = team_names.get(self.log.away_team_id, "Away")
        home_abbr = team_abbrevs.get(self.log.home_team_id, "HOM")
        away_abbr = team_abbrevs.get(self.log.away_team_id, "AWY")

        # Header
        lines.append(f"# Game: {away_name} vs {home_name}")
        lines.append(f"**Game ID:** {self.log.game_id}")
        lines.append("---\n")

        current_quarter = 0
        current_drive = 0
        drive_events = []

        for event in self.log.events:
            # Quarter header
            if event.quarter != current_quarter and event.quarter > 0:
                # Flush previous drive
                if drive_events:
                    lines.extend(self._format_drive_table(drive_events, team_names, team_abbrevs))
                    drive_events = []

                current_quarter = event.quarter
                lines.append(f"---\n# QUARTER {current_quarter}\n---\n")

            # Drive header
            if event.drive_number != current_drive and event.drive_number > 0:
                # Flush previous drive
                if drive_events:
                    lines.extend(self._format_drive_table(drive_events, team_names, team_abbrevs))
                    drive_events = []

                current_drive = event.drive_number
                team_name = team_names.get(event.possessing_team_id, "Unknown")
                team_abbr = team_abbrevs.get(event.possessing_team_id, "UNK")
                lines.append(f"\n## Drive {current_drive} (Q{current_quarter}): {team_name} ({team_abbr})\n")

            # Collect events for this drive
            if event.event_type in (EventType.KICKOFF, EventType.PLAY, EventType.PUNT,
                                     EventType.FIELD_GOAL, EventType.PAT, EventType.TWO_POINT,
                                     EventType.PENALTY):
                drive_events.append(event)
            elif event.event_type == EventType.TWO_MINUTE_WARNING:
                drive_events.append(event)
            elif event.event_type == EventType.HALFTIME:
                if drive_events:
                    lines.extend(self._format_drive_table(drive_events, team_names, team_abbrevs))
                    drive_events = []
                lines.append(f"\n---\n## HALFTIME\n**Score:** {away_abbr} {self.log.away_score} - {home_abbr} {self.log.home_score}\n---\n")

        # Flush remaining drive events
        if drive_events:
            lines.extend(self._format_drive_table(drive_events, team_names, team_abbrevs))

        # Final score
        lines.append(f"\n---\n# FINAL SCORE\n**{away_name} {self.log.away_score} - {home_name} {self.log.home_score}**\n---\n")

        return "\n".join(lines)

    def _format_drive_table(
        self,
        events: List[PlayByPlayEvent],
        team_names: Dict[int, str],
        team_abbrevs: Dict[int, str]
    ) -> List[str]:
        """Format a drive's events as a markdown table"""
        lines = []

        # Table header
        lines.append("\n| Qtr | Time | Down | Field Pos | Play Description | Result |")
        lines.append("|-----|------|------|-----------|------------------|--------|")

        for event in events:
            if event.event_type == EventType.TWO_MINUTE_WARNING:
                lines.append(f"| Q{event.quarter} | {event.format_clock()} | | | **TWO-MINUTE WARNING** | |")
                continue

            if event.event_type == EventType.KICKOFF:
                kicking = team_abbrevs.get(event.kicking_team_id, "???")
                receiving = team_abbrevs.get(event.receiving_team_id, "???")
                if event.is_touchback:
                    desc = f"Kickoff ({kicking} to {receiving}): Touchback"
                else:
                    desc = f"Kickoff Return ({kicking} to {receiving}): {event.return_yards} yds"
                lines.append(f"| Q{event.quarter} | {event.format_clock()} | -- | -- | {desc} | {event.result_text} |")
            else:
                lines.append(
                    f"| Q{event.quarter} | {event.format_clock()} | {event.format_down_distance()} | "
                    f"{event.format_field_position()} | {event.description} | {event.result_text} |"
                )

        return lines

    def export_json(self) -> Dict[str, Any]:
        """
        Export the log as a JSON-serializable dictionary.

        Returns:
            Dictionary with game info and events list
        """
        events_list = []
        for e in self.log.events:
            event_data = {
                "event_type": e.event_type.value,
                "quarter": e.quarter,
                "clock_seconds": e.clock_seconds,
                "clock_display": e.format_clock(),
                "drive_number": e.drive_number,
                "possessing_team_id": e.possessing_team_id,
                "field_position": e.field_position,
                "field_position_display": e.format_field_position() if e.field_position > 0 else None,
                "down": e.down,
                "distance": e.distance,
                "down_distance_display": e.format_down_distance() if e.down else None,
                "yards_gained": e.yards_gained,
                "description": e.description,
                "result": e.result_text,
                "is_scoring": e.is_scoring,
                "is_turnover": e.is_turnover,
                "is_first_down": e.is_first_down,
                "points": e.points,
            }

            # Add kickoff-specific fields
            if e.event_type == EventType.KICKOFF:
                event_data["is_touchback"] = e.is_touchback
                event_data["return_yards"] = e.return_yards

            # Add penalty-specific fields from raw_data
            if e.event_type == EventType.PENALTY and e.raw_data:
                event_data["penalty"] = {
                    "type": e.raw_data.get("penalty_type"),
                    "yards_assessed": e.raw_data.get("yards_assessed"),
                    "team_penalized": e.raw_data.get("team_penalized"),
                    "penalty_accepted": e.raw_data.get("penalty_accepted"),
                    "enforcement_spot": e.raw_data.get("enforcement_spot"),
                    "new_field_position": e.raw_data.get("new_field_position"),
                    "new_down": e.raw_data.get("new_down"),
                    "new_distance": e.raw_data.get("new_distance"),
                    "play_negated": e.raw_data.get("play_negated"),
                    "penalized_player_name": e.raw_data.get("penalized_player_name"),
                    "penalized_player_number": e.raw_data.get("penalized_player_number"),
                }

            events_list.append(event_data)

        return {
            "game_id": self.log.game_id,
            "home_team_id": self.log.home_team_id,
            "away_team_id": self.log.away_team_id,
            "final_score": {
                "home": self.log.home_score,
                "away": self.log.away_score
            },
            "events": events_list
        }

    def export_for_ui(self) -> List[Dict[str, Any]]:
        """
        Export events in a format suitable for UI display.

        Returns:
            List of event dictionaries with display-friendly fields
        """
        return [
            {
                "type": e.event_type.value,
                "quarter": e.quarter,
                "time": e.format_clock(),
                "drive": e.drive_number,
                "down_distance": e.format_down_distance(),
                "field_pos": e.format_field_position() if e.field_position > 0 else "",
                "description": e.description,
                "result": e.result_text,
                "is_scoring": e.is_scoring,
                "is_turnover": e.is_turnover,
                "points": e.points,
            }
            for e in self.log.events
        ]

    def export_json_by_drives(self) -> Dict[str, Any]:
        """
        Export JSON grouped by drives (matches BoxScoreDialog format).

        This format is backwards-compatible with the existing JSON export
        structure while including kickoffs as "play 0" in each drive.

        Returns:
            Dictionary with game info and drives list, each containing plays
        """
        drives: Dict[int, Dict[str, Any]] = {}

        for event in self.log.events:
            drive_num = event.drive_number
            if drive_num <= 0:
                continue  # Skip events not associated with a drive

            # Initialize drive if not exists
            if drive_num not in drives:
                drives[drive_num] = {
                    "drive_number": drive_num,
                    "possessing_team_id": event.possessing_team_id,
                    "possessing_team": "",  # Will be enriched by caller
                    "starting_field_position": 0,
                    "total_plays": 0,
                    "total_yards": 0,
                    "time_of_possession_seconds": 0,
                    "outcome": "",
                    "points_scored": 0,
                    "plays": []
                }

            # Build play data based on event type
            if event.event_type == EventType.KICKOFF:
                play_data = {
                    "play_number": 0,  # Kickoff is "play 0"
                    "down": None,
                    "distance": None,
                    "yard_line": event.field_position,
                    "outcome": "touchback" if event.is_touchback else "kickoff_return",
                    "yards_gained": event.return_yards or 0,
                    "time_elapsed": 0,
                    "is_scoring_play": False,
                    "is_turnover": False,
                    "is_first_down": False,
                    "points": 0,
                    "is_kickoff": True
                }
                # Insert kickoff at beginning of plays list
                drives[drive_num]["plays"].insert(0, play_data)
                drives[drive_num]["starting_field_position"] = event.field_position

            elif event.event_type == EventType.PLAY:
                play_num = len([p for p in drives[drive_num]["plays"] if not p.get("is_kickoff", False)]) + 1
                play_data = {
                    "play_number": play_num,
                    "down": event.down,
                    "distance": event.distance,
                    "yard_line": event.field_position,
                    "outcome": event.description,
                    "yards_gained": event.yards_gained or 0,
                    "time_elapsed": 0,  # Not tracked in events currently
                    "is_scoring_play": event.is_scoring,
                    "is_turnover": event.is_turnover,
                    "is_first_down": event.is_first_down,
                    "points": event.points,
                    "is_kickoff": False
                }
                drives[drive_num]["plays"].append(play_data)
                drives[drive_num]["total_plays"] += 1
                drives[drive_num]["total_yards"] += event.yards_gained or 0
                if event.is_scoring:
                    drives[drive_num]["points_scored"] += event.points

            elif event.event_type in (EventType.FIELD_GOAL, EventType.PUNT, EventType.PAT, EventType.TWO_POINT):
                # Special plays
                play_num = len([p for p in drives[drive_num]["plays"] if not p.get("is_kickoff", False)]) + 1
                play_data = {
                    "play_number": play_num,
                    "down": event.down,
                    "distance": event.distance,
                    "yard_line": event.field_position,
                    "outcome": event.description or event.event_type.value,
                    "yards_gained": event.yards_gained or 0,
                    "time_elapsed": 0,
                    "is_scoring_play": event.is_scoring,
                    "is_turnover": event.is_turnover,
                    "is_first_down": False,
                    "points": event.points,
                    "is_kickoff": False
                }
                drives[drive_num]["plays"].append(play_data)
                drives[drive_num]["total_plays"] += 1
                if event.is_scoring:
                    drives[drive_num]["points_scored"] += event.points

        return {
            "game_id": self.log.game_id,
            "home_team_id": self.log.home_team_id,
            "away_team_id": self.log.away_team_id,
            "final_score": {
                "home": self.log.home_score,
                "away": self.log.away_score
            },
            "drives": [drives[k] for k in sorted(drives.keys())]
        }

    # ========== FACTORY METHODS ==========

    @classmethod
    def from_game_result(cls, game_result: Any) -> 'PlayByPlayLogger':
        """
        Create a PlayByPlayLogger from an existing GameResult.

        This is a converter that takes the existing drive/play data
        from GameResult and populates the unified logger format.

        Args:
            game_result: GameResult object with drives and plays

        Returns:
            Populated PlayByPlayLogger instance
        """
        home_team = game_result.home_team
        away_team = game_result.away_team
        game_id = getattr(game_result, 'game_id', f"game_{away_team.abbreviation}_at_{home_team.abbreviation}")

        logger = cls(game_id, home_team.team_id, away_team.team_id)

        # Process each drive
        for drive_num, drive in enumerate(game_result.drives, 1):
            quarter = getattr(drive, 'quarter_started', 1)
            logger.set_quarter(quarter)
            logger.start_drive(drive_num)

            possessing_team_id = getattr(drive, 'possessing_team_id', home_team.team_id)

            # Log kickoff if present (at start of drive)
            kickoff_result = getattr(drive, 'kickoff_result', None)
            if kickoff_result:
                kicking_team_id = getattr(kickoff_result, 'kicking_team_id', 0)
                if kicking_team_id == 0:
                    # Infer kicking team as opponent of receiving team
                    kicking_team_id = away_team.team_id if possessing_team_id == home_team.team_id else home_team.team_id

                clock_seconds = getattr(drive, 'starting_clock_seconds', 900)
                logger.log_kickoff(
                    kickoff_result=kickoff_result,
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=possessing_team_id,
                    clock_seconds=clock_seconds
                )

            # Log plays
            plays = getattr(drive, 'plays', [])
            current_down = getattr(drive, 'starting_down', 1)
            current_distance = getattr(drive, 'starting_distance', 10)
            field_position = getattr(drive, 'starting_field_position', 25)

            # Calculate starting clock and elapsed time
            drive_start_clock = getattr(drive, 'starting_clock_seconds', 900)
            cumulative_time = 0

            for play in plays:
                play_time = getattr(play, 'time_elapsed', 0)
                clock_seconds = max(0, drive_start_clock - cumulative_time)

                # Check for two-minute warning (Q2 and Q4)
                if quarter in [2, 4]:
                    time_before = clock_seconds
                    time_after = max(0, clock_seconds - play_time)
                    if time_before > 120 >= time_after:
                        logger.log_two_minute_warning(clock_seconds=120)

                # Log the play
                logger.log_play(
                    play_result=play,
                    down=current_down,
                    distance=current_distance,
                    field_position=field_position,
                    clock_seconds=clock_seconds,
                    possessing_team_id=possessing_team_id
                )

                # Log penalty if one occurred on this play
                if getattr(play, 'penalty_occurred', False):
                    enforcement = getattr(play, 'enforcement_result', None)
                    stats_summary = getattr(play, 'player_stats_summary', None)
                    penalty_instance = getattr(stats_summary, 'penalty_instance', None) if stats_summary else None

                    if penalty_instance or enforcement:
                        # Determine team_penalized - convert "offense"/"defense" to "home"/"away"
                        if penalty_instance:
                            penalty_type = getattr(penalty_instance, 'penalty_type', 'unknown')
                            team_penalized_raw = getattr(penalty_instance, 'team_penalized', 'offense')
                            if team_penalized_raw == 'offense':
                                team_penalized = 'home' if possessing_team_id == home_team.team_id else 'away'
                            else:
                                team_penalized = 'away' if possessing_team_id == home_team.team_id else 'home'
                            penalized_player_name = getattr(penalty_instance, 'penalized_player_name', '')
                            penalized_player_number = getattr(penalty_instance, 'penalized_player_number', 0)
                            yards_assessed = getattr(penalty_instance, 'yards_assessed', 0)
                        else:
                            penalty_type = 'unknown'
                            team_penalized = 'unknown'
                            penalized_player_name = ''
                            penalized_player_number = 0
                            yards_assessed = getattr(play, 'penalty_yards', 0)

                        logger.log_penalty(
                            penalty_type=penalty_type,
                            yards_assessed=yards_assessed,
                            team_penalized=team_penalized,
                            clock_seconds=clock_seconds,
                            field_position=field_position,
                            down=current_down,
                            distance=current_distance,
                            possessing_team_id=possessing_team_id,
                            penalized_player_name=penalized_player_name,
                            penalized_player_number=penalized_player_number,
                            penalty_accepted=getattr(enforcement, 'penalty_accepted', True) if enforcement else True,
                            enforcement_spot=enforcement.enforcement_spot.value if enforcement else 'previous_spot',
                            new_field_position=enforcement.new_yard_line if enforcement else 0,
                            new_down=enforcement.new_down if enforcement else 0,
                            new_distance=enforcement.new_yards_to_go if enforcement else 0,
                            is_first_down=enforcement.is_first_down if enforcement else False,
                            play_negated=getattr(play, 'play_negated', False),
                            raw_penalty_data=penalty_instance
                        )

                cumulative_time += play_time

                # Update down/distance from play snapshots if available
                if hasattr(play, 'down_after_play') and play.down_after_play is not None:
                    current_down = play.down_after_play
                    current_distance = getattr(play, 'distance_after_play', 10)
                    field_position = getattr(play, 'field_position_after_play', field_position)
                else:
                    # Fallback: simple progression
                    yards = getattr(play, 'yards', 0)
                    if getattr(play, 'achieved_first_down', False) or yards >= current_distance:
                        current_down = 1
                        field_position = min(100, field_position + yards)
                        current_distance = min(10, 100 - field_position)
                    else:
                        current_down = min(4, current_down + 1)
                        current_distance = max(1, current_distance - yards)
                        field_position = min(100, field_position + yards)

            # Log PAT if present
            pat_result = getattr(drive, 'pat_result', None)
            if pat_result:
                logger.log_pat(
                    pat_result=pat_result,
                    kicking_team_id=possessing_team_id,
                    clock_seconds=0
                )

        # Set final scores
        final_score = getattr(game_result, 'final_score', {})
        logger.log.home_score = final_score.get(home_team.team_id, 0)
        logger.log.away_score = final_score.get(away_team.team_id, 0)

        return logger
