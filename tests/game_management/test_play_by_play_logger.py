"""
Tests for PlayByPlayLogger - unified play-by-play event logging system.

Tests cover:
- Event creation and logging
- Kickoff logging with touchbacks and returns
- Play logging with down/distance tracking
- Special events (two-minute warning, halftime, etc.)
- Export to markdown, JSON, and UI formats
"""

import pytest
from game_management.play_by_play_logger import (
    PlayByPlayLogger, PlayByPlayEvent, PlayByPlayLog, EventType
)


class TestPlayByPlayEvent:
    """Tests for PlayByPlayEvent dataclass"""

    def test_format_down_distance_first_and_ten(self):
        """Test formatting 1st & 10"""
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=900,
            drive_number=1,
            possessing_team_id=1,
            field_position=25,
            down=1,
            distance=10
        )
        assert event.format_down_distance() == "1st & 10"

    def test_format_down_distance_third_and_short(self):
        """Test formatting 3rd & 2"""
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=600,
            drive_number=1,
            possessing_team_id=1,
            field_position=45,
            down=3,
            distance=2
        )
        assert event.format_down_distance() == "3rd & 2"

    def test_format_down_distance_none(self):
        """Test formatting when down is None (e.g., kickoff)"""
        event = PlayByPlayEvent(
            event_type=EventType.KICKOFF,
            quarter=1,
            clock_seconds=900,
            drive_number=1,
            possessing_team_id=1,
            field_position=25
        )
        assert event.format_down_distance() == "--"

    def test_format_field_position_own_territory(self):
        """Test formatting field position in own territory"""
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=900,
            drive_number=1,
            possessing_team_id=1,
            field_position=25
        )
        assert event.format_field_position() == "OWN 25"

    def test_format_field_position_opponent_territory(self):
        """Test formatting field position in opponent territory"""
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=900,
            drive_number=1,
            possessing_team_id=1,
            field_position=75
        )
        assert event.format_field_position() == "OPP 25"

    def test_format_clock(self):
        """Test clock formatting"""
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=125,  # 2:05
            drive_number=1,
            possessing_team_id=1,
            field_position=25
        )
        assert event.format_clock() == "2:05"


class TestPlayByPlayLog:
    """Tests for PlayByPlayLog dataclass"""

    def test_add_event(self):
        """Test adding events to the log"""
        log = PlayByPlayLog(game_id="test_game", home_team_id=1, away_team_id=2)
        event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=900,
            drive_number=1,
            possessing_team_id=1,
            field_position=25
        )
        log.add_event(event)
        assert len(log.events) == 1
        assert log.events[0] == event

    def test_score_tracking(self):
        """Test that scoring events update the score"""
        log = PlayByPlayLog(game_id="test_game", home_team_id=1, away_team_id=2)

        # Home team scores touchdown
        td_event = PlayByPlayEvent(
            event_type=EventType.PLAY,
            quarter=1,
            clock_seconds=600,
            drive_number=1,
            possessing_team_id=1,
            field_position=100,
            is_scoring=True,
            points=6
        )
        log.add_event(td_event)
        assert log.home_score == 6
        assert log.away_score == 0

        # Away team scores field goal
        fg_event = PlayByPlayEvent(
            event_type=EventType.FIELD_GOAL,
            quarter=1,
            clock_seconds=300,
            drive_number=2,
            possessing_team_id=2,
            field_position=70,
            is_scoring=True,
            points=3
        )
        log.add_event(fg_event)
        assert log.home_score == 6
        assert log.away_score == 3

    def test_get_events_by_drive(self):
        """Test filtering events by drive number"""
        log = PlayByPlayLog(game_id="test_game", home_team_id=1, away_team_id=2)

        # Add events from multiple drives
        for drive in [1, 1, 1, 2, 2]:
            log.add_event(PlayByPlayEvent(
                event_type=EventType.PLAY,
                quarter=1,
                clock_seconds=900,
                drive_number=drive,
                possessing_team_id=1,
                field_position=25
            ))

        drive_1_events = log.get_events_by_drive(1)
        assert len(drive_1_events) == 3

        drive_2_events = log.get_events_by_drive(2)
        assert len(drive_2_events) == 2


class TestPlayByPlayLogger:
    """Tests for PlayByPlayLogger class"""

    def test_initialization(self):
        """Test logger initialization"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        assert logger.log.game_id == "test_game"
        assert logger.log.home_team_id == 1
        assert logger.log.away_team_id == 2
        assert len(logger.events) == 0

    def test_log_kickoff_touchback(self):
        """Test logging a touchback kickoff"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        # Mock kickoff result
        class MockKickoff:
            is_touchback = True
            return_yards = 0
            starting_field_position = 25

        logger.log_kickoff(
            kickoff_result=MockKickoff(),
            kicking_team_id=2,
            receiving_team_id=1,
            clock_seconds=900
        )

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == EventType.KICKOFF
        assert event.is_touchback is True
        assert event.field_position == 25
        assert "Touchback" in event.description

    def test_log_kickoff_return(self):
        """Test logging a kickoff return"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockKickoff:
            is_touchback = False
            return_yards = 28
            starting_field_position = 28

        logger.log_kickoff(
            kickoff_result=MockKickoff(),
            kicking_team_id=2,
            receiving_team_id=1,
            clock_seconds=900
        )

        event = logger.events[0]
        assert event.is_touchback is False
        assert event.return_yards == 28
        assert "28" in event.description

    def test_log_play(self):
        """Test logging a standard play"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockPlay:
            yards = 7
            is_scoring_play = False
            is_turnover = False
            achieved_first_down = True
            points = 0
            outcome = "pass_complete"

        logger.log_play(
            play_result=MockPlay(),
            down=1,
            distance=10,
            field_position=25,
            clock_seconds=855,
            possessing_team_id=1
        )

        event = logger.events[0]
        assert event.event_type == EventType.PLAY
        assert event.down == 1
        assert event.distance == 10
        assert event.yards_gained == 7
        assert event.is_first_down is True
        assert event.result_text == "+7"

    def test_log_touchdown(self):
        """Test logging a touchdown play"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockTD:
            yards = 15
            is_scoring_play = True
            is_turnover = False
            achieved_first_down = True
            points = 6
            outcome = "touchdown"

        logger.log_play(
            play_result=MockTD(),
            down=1,
            distance=10,
            field_position=85,  # 15 yards from goal line
            clock_seconds=600,
            possessing_team_id=1
        )

        event = logger.events[0]
        assert event.is_scoring is True
        assert event.points == 6
        assert "TD" in event.result_text

    def test_log_two_minute_warning(self):
        """Test logging two-minute warning"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(2)
        logger.start_drive(5)

        logger.log_two_minute_warning(clock_seconds=120)

        event = logger.events[0]
        assert event.event_type == EventType.TWO_MINUTE_WARNING
        assert "TWO-MINUTE WARNING" in event.description

    def test_export_json(self):
        """Test JSON export format"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockPlay:
            yards = 5
            is_scoring_play = False
            is_turnover = False
            achieved_first_down = False
            points = 0
            outcome = "rush"

        logger.log_play(
            play_result=MockPlay(),
            down=1,
            distance=10,
            field_position=25,
            clock_seconds=855,
            possessing_team_id=1
        )

        json_output = logger.export_json()

        assert json_output["game_id"] == "test_game"
        assert json_output["home_team_id"] == 1
        assert json_output["away_team_id"] == 2
        assert len(json_output["events"]) == 1
        assert json_output["events"][0]["event_type"] == "play"
        assert json_output["events"][0]["down"] == 1
        assert json_output["events"][0]["distance"] == 10

    def test_export_for_ui(self):
        """Test UI export format"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockKickoff:
            is_touchback = True
            return_yards = 0
            starting_field_position = 25

        logger.log_kickoff(
            kickoff_result=MockKickoff(),
            kicking_team_id=2,
            receiving_team_id=1,
            clock_seconds=900
        )

        ui_output = logger.export_for_ui()

        assert len(ui_output) == 1
        assert ui_output[0]["type"] == "kickoff"
        assert ui_output[0]["quarter"] == 1
        assert ui_output[0]["time"] == "15:00"


class TestMarkdownExport:
    """Tests for markdown export functionality"""

    def test_export_markdown_basic(self):
        """Test basic markdown export"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockPlay:
            yards = 7
            is_scoring_play = False
            is_turnover = False
            achieved_first_down = True
            points = 0
            outcome = "pass_complete"

        logger.log_play(
            play_result=MockPlay(),
            down=1,
            distance=10,
            field_position=25,
            clock_seconds=855,
            possessing_team_id=1
        )

        team_names = {1: "Home Team", 2: "Away Team"}
        markdown = logger.export_markdown(team_names)

        assert "# Game:" in markdown
        assert "QUARTER 1" in markdown
        assert "Drive 1" in markdown
        assert "| Qtr | Time | Down | Field Pos | Play Description | Result |" in markdown

    def test_export_markdown_with_kickoff(self):
        """Test markdown export includes kickoffs in table"""
        logger = PlayByPlayLogger("test_game", home_team_id=1, away_team_id=2)
        logger.set_quarter(1)
        logger.start_drive(1)

        class MockKickoff:
            is_touchback = False
            return_yards = 25
            starting_field_position = 25

        logger.log_kickoff(
            kickoff_result=MockKickoff(),
            kicking_team_id=2,
            receiving_team_id=1,
            clock_seconds=900
        )

        team_names = {1: "Home Team", 2: "Away Team"}
        team_abbrevs = {1: "HOM", 2: "AWY"}
        markdown = logger.export_markdown(team_names, team_abbrevs)

        # Kickoff should appear in the table
        assert "Kickoff Return" in markdown or "Kickoff" in markdown
        assert "25" in markdown  # Return yards should appear
