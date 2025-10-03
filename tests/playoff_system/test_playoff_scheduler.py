"""
Unit Tests for Playoff Scheduler

Tests playoff scheduling integration with EventDatabaseAPI.
Covers wild card scheduling, progressive bracket generation,
and GameEvent creation with correct parameters.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from playoff_system.playoff_scheduler import PlayoffScheduler
from playoff_system.playoff_manager import PlayoffManager
from playoff_system.seeding_models import PlayoffSeeding, PlayoffSeed, ConferenceSeeding
from playoff_system.bracket_models import PlayoffBracket, PlayoffGame
from calendar.date_models import Date
from events.event_database_api import EventDatabaseAPI
from events.game_event import GameEvent
from shared.game_result import GameResult


class TestPlayoffScheduler:
    """Unit tests for PlayoffScheduler."""

    @pytest.fixture
    def mock_event_db_api(self):
        """Create a mock EventDatabaseAPI."""
        mock_api = Mock(spec=EventDatabaseAPI)
        # Mock store_event to return event IDs
        mock_api.store_event = Mock(side_effect=lambda event: f"event_{id(event)}")
        return mock_api

    @pytest.fixture
    def playoff_manager(self):
        """Create a real PlayoffManager instance."""
        return PlayoffManager()

    @pytest.fixture
    def scheduler(self, mock_event_db_api, playoff_manager):
        """Create a PlayoffScheduler with mocked dependencies."""
        return PlayoffScheduler(
            event_db_api=mock_event_db_api,
            playoff_manager=playoff_manager
        )

    @pytest.fixture
    def mock_seeding(self):
        """
        Create mock playoff seeding for both conferences.

        AFC Seeds:
        1. Team 13 (13-3) - AFC West
        2. Team 1 (12-4) - AFC East
        3. Team 5 (11-5) - AFC North
        4. Team 9 (10-6) - AFC South
        5. Team 14 (10-6) - Wildcard
        6. Team 10 (9-7) - Wildcard
        7. Team 6 (9-7) - Wildcard

        NFC Seeds:
        1. Team 29 (13-3) - NFC West
        2. Team 17 (12-4) - NFC East
        3. Team 21 (11-5) - NFC North
        4. Team 25 (10-6) - NFC South
        5. Team 30 (10-6) - Wildcard
        6. Team 26 (9-7) - Wildcard
        7. Team 22 (9-7) - Wildcard
        """
        # AFC Seeds
        afc_seeds = [
            PlayoffSeed(
                seed=1, team_id=13, wins=13, losses=3, ties=0,
                win_percentage=0.8125, division_winner=True,
                division_name="AFC West", conference="AFC",
                points_for=450, points_against=280, point_differential=170,
                division_record="5-1", conference_record="10-2"
            ),
            PlayoffSeed(
                seed=2, team_id=1, wins=12, losses=4, ties=0,
                win_percentage=0.75, division_winner=True,
                division_name="AFC East", conference="AFC",
                points_for=420, points_against=310, point_differential=110,
                division_record="5-1", conference_record="9-3"
            ),
            PlayoffSeed(
                seed=3, team_id=5, wins=11, losses=5, ties=0,
                win_percentage=0.6875, division_winner=True,
                division_name="AFC North", conference="AFC",
                points_for=410, points_against=320, point_differential=90,
                division_record="4-2", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=4, team_id=9, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=True,
                division_name="AFC South", conference="AFC",
                points_for=390, points_against=330, point_differential=60,
                division_record="5-1", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=5, team_id=14, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=False,
                division_name="AFC West", conference="AFC",
                points_for=400, points_against=320, point_differential=80,
                division_record="4-2", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=6, team_id=10, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="AFC South", conference="AFC",
                points_for=360, points_against=350, point_differential=10,
                division_record="4-2", conference_record="7-5"
            ),
            PlayoffSeed(
                seed=7, team_id=6, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="AFC North", conference="AFC",
                points_for=370, points_against=340, point_differential=30,
                division_record="3-3", conference_record="7-5"
            )
        ]

        # NFC Seeds
        nfc_seeds = [
            PlayoffSeed(
                seed=1, team_id=29, wins=13, losses=3, ties=0,
                win_percentage=0.8125, division_winner=True,
                division_name="NFC West", conference="NFC",
                points_for=460, points_against=290, point_differential=170,
                division_record="6-0", conference_record="10-2"
            ),
            PlayoffSeed(
                seed=2, team_id=17, wins=12, losses=4, ties=0,
                win_percentage=0.75, division_winner=True,
                division_name="NFC East", conference="NFC",
                points_for=430, points_against=300, point_differential=130,
                division_record="5-1", conference_record="9-3"
            ),
            PlayoffSeed(
                seed=3, team_id=21, wins=11, losses=5, ties=0,
                win_percentage=0.6875, division_winner=True,
                division_name="NFC North", conference="NFC",
                points_for=400, points_against=310, point_differential=90,
                division_record="5-1", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=4, team_id=25, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=True,
                division_name="NFC South", conference="NFC",
                points_for=380, points_against=340, point_differential=40,
                division_record="4-2", conference_record="7-5"
            ),
            PlayoffSeed(
                seed=5, team_id=30, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=False,
                division_name="NFC West", conference="NFC",
                points_for=395, points_against=330, point_differential=65,
                division_record="3-3", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=6, team_id=26, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="NFC South", conference="NFC",
                points_for=370, points_against=360, point_differential=10,
                division_record="3-3", conference_record="7-5"
            ),
            PlayoffSeed(
                seed=7, team_id=22, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="NFC North", conference="NFC",
                points_for=360, points_against=350, point_differential=10,
                division_record="3-3", conference_record="6-6"
            )
        ]

        afc_conference = ConferenceSeeding(
            conference="AFC",
            seeds=afc_seeds,
            division_winners=afc_seeds[:4],
            wildcards=afc_seeds[4:],
            clinched_teams=[s.team_id for s in afc_seeds],
            eliminated_teams=[]
        )

        nfc_conference = ConferenceSeeding(
            conference="NFC",
            seeds=nfc_seeds,
            division_winners=nfc_seeds[:4],
            wildcards=nfc_seeds[4:],
            clinched_teams=[s.team_id for s in nfc_seeds],
            eliminated_teams=[]
        )

        return PlayoffSeeding(
            season=2024,
            week=18,
            afc=afc_conference,
            nfc=nfc_conference,
            tiebreakers_applied=[],
            calculation_date="2024-01-07T12:00:00"
        )

    @pytest.fixture
    def start_date(self):
        """Create a start date for wild card round."""
        return Date(2024, 1, 13)

    def test_schedule_wild_card_round_creates_six_events(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test that wild card scheduling creates exactly 6 GameEvent objects."""
        result = scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Verify 6 events were stored
        assert mock_event_db_api.store_event.call_count == 6

        # Verify result structure
        assert result['games_scheduled'] == 6
        assert len(result['event_ids']) == 6
        assert result['round_name'] == 'wild_card'
        assert result['start_date'] == start_date

    def test_schedule_wild_card_round_returns_event_ids(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test that wild card scheduling returns proper event IDs."""
        result = scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Verify all event IDs are returned
        assert len(result['event_ids']) == 6
        # Each event ID should be a string
        for event_id in result['event_ids']:
            assert isinstance(event_id, str)
            assert event_id.startswith('event_')

    def test_schedule_wild_card_round_creates_correct_game_events(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test that GameEvent objects are created with correct parameters."""
        scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Get all stored events
        stored_events = [
            call.args[0] for call in mock_event_db_api.store_event.call_args_list
        ]

        # Verify all are GameEvent objects
        assert len(stored_events) == 6
        for event in stored_events:
            assert isinstance(event, GameEvent)

        # Verify each event has correct parameters
        for event in stored_events:
            # Should be playoff game
            assert event.season_type == "playoffs"
            assert event.overtime_type == "playoffs"
            assert event.season == 2024
            assert event.week == 1  # Wild card week

            # Team IDs should be valid (1-32)
            assert 1 <= event.away_team_id <= 32
            assert 1 <= event.home_team_id <= 32
            assert event.away_team_id != event.home_team_id

    def test_schedule_wild_card_round_matchups(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test that wild card matchups are correct (2v7, 3v6, 4v5)."""
        scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        stored_events = [
            call.args[0] for call in mock_event_db_api.store_event.call_args_list
        ]

        # Expected matchups
        expected_matchups = [
            # AFC: (2)v(7), (3)v(6), (4)v(5)
            (1, 6),   # #2 AFC East vs #7 Wildcard
            (5, 10),  # #3 AFC North vs #6 Wildcard
            (9, 14),  # #4 AFC South vs #5 Wildcard
            # NFC: (2)v(7), (3)v(6), (4)v(5)
            (17, 22), # #2 NFC East vs #7 Wildcard
            (21, 26), # #3 NFC North vs #6 Wildcard
            (25, 30), # #4 NFC South vs #5 Wildcard
        ]

        # Verify matchups (order may vary)
        actual_matchups = [(e.home_team_id, e.away_team_id) for e in stored_events]
        assert len(actual_matchups) == 6

        for expected in expected_matchups:
            assert expected in actual_matchups

    def test_schedule_next_round_wild_card_to_divisional(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test progressive scheduling from wild card to divisional round."""
        # Create mock wild card results (winners: #6, #5, #4 from AFC; #6, #5, #4 from NFC)
        wild_card_results = self._create_mock_game_results([
            (6, 1),   # #7 beats #2 (upset)
            (10, 5),  # #6 beats #3 (upset)
            (14, 9),  # #5 beats #4
            (22, 17), # #7 beats #2 (NFC upset)
            (26, 21), # #6 beats #3 (NFC upset)
            (30, 25), # #5 beats #4 (NFC)
        ])

        divisional_start = Date(2024, 1, 20)

        result = scheduler.schedule_next_round(
            completed_results=wild_card_results,
            current_round='wild_card',
            original_seeding=mock_seeding,
            start_date=divisional_start,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Verify 4 divisional games created (2 AFC, 2 NFC)
        assert result['games_scheduled'] == 4
        assert len(result['event_ids']) == 4
        assert result['round_name'] == 'divisional'

        # Verify events stored
        assert mock_event_db_api.store_event.call_count == 4

        stored_events = [
            call.args[0] for call in mock_event_db_api.store_event.call_args_list
        ]

        for event in stored_events:
            assert event.season_type == "playoffs"
            assert event.overtime_type == "playoffs"
            assert event.week == 2  # Divisional week

    def test_schedule_next_round_divisional_to_conference(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test progressive scheduling from divisional to conference championships."""
        # Create mock divisional results (winners: 2 AFC teams, 2 NFC teams)
        divisional_results = self._create_mock_game_results([
            (13, 14), # AFC #1 beats #5
            (6, 10),  # AFC #7 beats #6
            (29, 30), # NFC #1 beats #5
            (22, 26), # NFC #7 beats #6
        ])

        conference_start = Date(2024, 1, 28)

        result = scheduler.schedule_next_round(
            completed_results=divisional_results,
            current_round='divisional',
            original_seeding=mock_seeding,
            start_date=conference_start,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Verify 2 conference championship games created
        assert result['games_scheduled'] == 2
        assert len(result['event_ids']) == 2
        assert result['round_name'] == 'conference'

        # Verify events stored
        assert mock_event_db_api.store_event.call_count == 2

        stored_events = [
            call.args[0] for call in mock_event_db_api.store_event.call_args_list
        ]

        for event in stored_events:
            assert event.season_type == "playoffs"
            assert event.overtime_type == "playoffs"
            assert event.week == 3  # Conference championship week

    def test_schedule_next_round_conference_to_super_bowl(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test progressive scheduling from conference championships to Super Bowl."""
        # Create mock conference championship results
        conference_results = self._create_mock_game_results([
            (13, 6),  # AFC Champion: Team 13
            (29, 22), # NFC Champion: Team 29
        ])

        super_bowl_date = Date(2024, 2, 11)

        result = scheduler.schedule_next_round(
            completed_results=conference_results,
            current_round='conference',
            original_seeding=mock_seeding,
            start_date=super_bowl_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        # Verify 1 Super Bowl game created
        assert result['games_scheduled'] == 1
        assert len(result['event_ids']) == 1
        assert result['round_name'] == 'super_bowl'

        # Verify event stored
        assert mock_event_db_api.store_event.call_count == 1

        stored_event = mock_event_db_api.store_event.call_args_list[0].args[0]
        assert stored_event.season_type == "playoffs"
        assert stored_event.overtime_type == "playoffs"
        assert stored_event.week == 4  # Super Bowl week

        # Verify it's AFC vs NFC champion
        assert stored_event.away_team_id == 13  # AFC Champion
        assert stored_event.home_team_id == 29  # NFC Champion

    def test_schedule_next_round_invalid_round_raises_error(
        self, scheduler, mock_seeding, start_date
    ):
        """Test that invalid round name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown round"):
            scheduler.schedule_next_round(
                completed_results=[],
                current_round='invalid_round',
                original_seeding=mock_seeding,
                start_date=start_date,
                season=2024,
                dynasty_id="test_dynasty"
            )

    def test_game_event_game_ids_are_unique(
        self, scheduler, mock_seeding, start_date, mock_event_db_api
    ):
        """Test that each GameEvent has a unique game_id."""
        scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="test_dynasty"
        )

        stored_events = [
            call.args[0] for call in mock_event_db_api.store_event.call_args_list
        ]

        # Extract game_ids
        game_ids = [event.get_game_id() for event in stored_events]

        # Verify all game_ids are unique
        assert len(game_ids) == len(set(game_ids))

        # Verify game_id format includes dynasty_id
        for game_id in game_ids:
            assert "test_dynasty" in game_id
            assert "2024" in game_id
            assert "wild_card" in game_id

    def test_playoff_scheduler_integration_with_playoff_manager(
        self, mock_event_db_api, mock_seeding, start_date
    ):
        """Test that PlayoffScheduler correctly integrates with PlayoffManager."""
        # Create real instances
        real_manager = PlayoffManager()
        scheduler = PlayoffScheduler(
            event_db_api=mock_event_db_api,
            playoff_manager=real_manager
        )

        result = scheduler.schedule_wild_card_round(
            seeding=mock_seeding,
            start_date=start_date,
            season=2024,
            dynasty_id="integration_test"
        )

        # Verify bracket was generated by PlayoffManager
        assert isinstance(result['bracket'], PlayoffBracket)
        assert result['bracket'].round_name == 'wild_card'
        assert len(result['bracket'].games) == 6

        # Verify GameEvents were created and stored
        assert mock_event_db_api.store_event.call_count == 6

    # Helper method
    def _create_mock_game_results(self, matchups):
        """
        Create mock GameResult objects.

        Args:
            matchups: List of tuples (winner_id, loser_id)

        Returns:
            List of mock GameResult objects
        """
        results = []

        for winner_id, loser_id in matchups:
            # Create minimal mock objects
            winner_team = Mock()
            winner_team.team_id = winner_id

            loser_team = Mock()
            loser_team.team_id = loser_id

            game_result = Mock(spec=GameResult)
            game_result.home_team = winner_team
            game_result.away_team = loser_team
            game_result.final_score = {
                winner_id: 24,
                loser_id: 17
            }

            results.append(game_result)

        return results
