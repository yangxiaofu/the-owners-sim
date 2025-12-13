"""
Tests for FlexScheduler - NFL-style late-season schedule adjustments.

Part of Milestone 11: Schedule & Rivalries, Tollgate 8.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List

from src.game_cycle.services.flex_scheduler import (
    FlexScheduler,
    PlayoffImplications,
    FlexRecommendation,
    FLEX_THRESHOLD,
)
from src.game_cycle.database.standings_api import TeamStanding
from src.game_cycle.models.rivalry import Rivalry, RivalryType
from src.game_cycle.models.game_slot import GameSlot


# -------------------- Fixtures --------------------

@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    db = MagicMock()
    db.query_all = MagicMock(return_value=[])
    db.query_one = MagicMock(return_value=None)
    db.execute = MagicMock()
    db._conn = MagicMock()
    db._conn.commit = MagicMock()
    db._conn.rollback = MagicMock()
    return db


@pytest.fixture
def flex_scheduler(mock_db):
    """Create a FlexScheduler with mocked database."""
    with patch('src.game_cycle.services.flex_scheduler.StandingsAPI'):
        with patch('src.game_cycle.services.flex_scheduler.RivalryAPI'):
            scheduler = FlexScheduler(mock_db, "test_dynasty")
            return scheduler


@pytest.fixture
def sample_standings() -> List[TeamStanding]:
    """Create sample standings for 16-team conference."""
    standings = []
    # AFC standings (team_ids 1-16)
    for i in range(1, 17):
        # Teams ranked 1-7 have good records, 8-16 have worse records
        if i <= 7:
            wins = 10 - (i - 1)  # 10, 9, 8, 7, 6, 5, 4 wins
            losses = 17 - 10 - (10 - wins)
        else:
            wins = 4 - (i - 8)  # 4, 3, 2, 1, 0, etc
            wins = max(0, wins)
            losses = 17 - wins

        standings.append(TeamStanding(
            team_id=i,
            wins=wins,
            losses=losses,
            ties=0,
            points_for=300 + (10 - i) * 20,
            points_against=250 + (i - 1) * 15,
            division_wins=wins // 3,
            division_losses=losses // 3,
            conference_wins=wins // 2,
            conference_losses=losses // 2,
            home_wins=wins // 2,
            home_losses=losses // 2,
            away_wins=wins - wins // 2,
            away_losses=losses - losses // 2,
        ))
    return standings


@pytest.fixture
def sample_rivalries() -> List[Rivalry]:
    """Create sample rivalries."""
    return [
        Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            intensity=95,
            rivalry_name="Epic Rivalry",
        ),
        Rivalry(
            team_a_id=3, team_b_id=4,
            rivalry_type=RivalryType.HISTORIC,
            intensity=80,
            rivalry_name="Historic Battle",
        ),
        Rivalry(
            team_a_id=5, team_b_id=6,
            rivalry_type=RivalryType.GEOGRAPHIC,
            intensity=50,
            rivalry_name="Regional Foes",
        ),
    ]


# -------------------- PlayoffImplications Tests --------------------

class TestPlayoffImplications:
    """Tests for PlayoffImplications dataclass."""

    def test_implication_score_no_stakes(self):
        """Empty implications should score 0."""
        impl = PlayoffImplications(team_id=1)
        assert impl.implication_score == 0

    def test_implication_score_clinch_playoff(self):
        """Clinching playoff should add 15 points."""
        impl = PlayoffImplications(team_id=1, can_clinch_playoff=True)
        assert impl.implication_score == 15

    def test_implication_score_clinch_division(self):
        """Clinching division should add 12 points."""
        impl = PlayoffImplications(team_id=1, can_clinch_division=True)
        assert impl.implication_score == 12

    def test_implication_score_clinch_bye(self):
        """Clinching bye should add 10 points."""
        impl = PlayoffImplications(team_id=1, can_clinch_bye=True)
        assert impl.implication_score == 10

    def test_implication_score_elimination(self):
        """Elimination game should add 12 points."""
        impl = PlayoffImplications(team_id=1, elimination_game=True)
        assert impl.implication_score == 12

    def test_implication_score_wild_card(self):
        """Wild card race should add 5 points."""
        impl = PlayoffImplications(team_id=1, wild_card_race=True)
        assert impl.implication_score == 5

    def test_implication_score_division_title(self):
        """Division title game should add 10 points."""
        impl = PlayoffImplications(team_id=1, division_title_game=True)
        assert impl.implication_score == 10

    def test_implication_score_combined(self):
        """Combined implications should sum correctly."""
        impl = PlayoffImplications(
            team_id=1,
            can_clinch_playoff=True,    # +15
            can_clinch_division=True,   # +12
            wild_card_race=True,        # +5
        )
        assert impl.implication_score == 32

    def test_implication_score_capped_at_50(self):
        """Score should be capped at 50."""
        impl = PlayoffImplications(
            team_id=1,
            can_clinch_playoff=True,    # +15
            can_clinch_division=True,   # +12
            can_clinch_bye=True,        # +10
            elimination_game=True,      # +12
            wild_card_race=True,        # +5
            division_title_game=True,   # +10 = 64 total
        )
        assert impl.implication_score == 50  # Capped


class TestFlexRecommendation:
    """Tests for FlexRecommendation dataclass."""

    def test_flex_recommendation_fields(self):
        """FlexRecommendation should store all fields correctly."""
        rec = FlexRecommendation(
            game_to_flex_in="game_123",
            game_to_flex_out="game_456",
            target_slot=GameSlot.SUNDAY_NIGHT,
            reason="playoff_clinch",
            appeal_delta=25,
            flex_in_appeal=85,
            flex_out_appeal=60,
        )

        assert rec.game_to_flex_in == "game_123"
        assert rec.game_to_flex_out == "game_456"
        assert rec.target_slot == GameSlot.SUNDAY_NIGHT
        assert rec.reason == "playoff_clinch"
        assert rec.appeal_delta == 25
        assert rec.flex_in_appeal == 85
        assert rec.flex_out_appeal == 60


# -------------------- FlexScheduler Method Tests --------------------

class TestFlexSchedulerMethods:
    """Tests for FlexScheduler internal methods."""

    def test_get_flexable_slots_before_week_12(self, flex_scheduler):
        """Weeks before 12 should have no flexable slots."""
        for week in range(1, 12):
            slots = flex_scheduler._get_flexable_slots(week)
            assert slots == []

    def test_get_flexable_slots_weeks_12_14(self, flex_scheduler):
        """Weeks 12-14 should only allow SNF flex."""
        for week in [12, 13, 14]:
            slots = flex_scheduler._get_flexable_slots(week)
            assert slots == [GameSlot.SUNDAY_NIGHT]

    def test_get_flexable_slots_weeks_15_17(self, flex_scheduler):
        """Weeks 15-17 should allow SNF, TNF, and MNF flex."""
        for week in [15, 16, 17]:
            slots = flex_scheduler._get_flexable_slots(week)
            assert GameSlot.SUNDAY_NIGHT in slots
            assert GameSlot.THURSDAY_NIGHT in slots
            assert GameSlot.MONDAY_NIGHT in slots
            assert len(slots) == 3

    def test_is_primetime_slot_true(self, flex_scheduler):
        """Primetime slots should be identified correctly."""
        primetime_slots = ['TNF', 'SNF', 'MNF', 'KICKOFF', 'TG_EARLY', 'TG_LATE', 'TG_NIGHT', 'XMAS']
        for slot in primetime_slots:
            assert flex_scheduler._is_primetime_slot(slot) is True

    def test_is_primetime_slot_false(self, flex_scheduler):
        """Non-primetime slots should return False."""
        regular_slots = ['SUN_EARLY', 'SUN_LATE', 'SUN']
        for slot in regular_slots:
            assert flex_scheduler._is_primetime_slot(slot) is False

    def test_build_rivalry_map(self, flex_scheduler, sample_rivalries):
        """Rivalry map should be built with sorted keys."""
        rivalry_map = flex_scheduler._build_rivalry_map(sample_rivalries)

        # Keys should be (min, max) tuples
        assert (1, 2) in rivalry_map
        assert (3, 4) in rivalry_map
        assert (5, 6) in rivalry_map

        # Verify values
        assert rivalry_map[(1, 2)].intensity == 95
        assert rivalry_map[(3, 4)].intensity == 80


class TestFlexAppealCalculation:
    """Tests for flex appeal calculation."""

    def test_get_current_win_appeal(self, flex_scheduler, sample_standings):
        """Win appeal should scale with combined wins."""
        # Team 1 has 10 wins, Team 2 has 9 wins = 19 combined
        appeal = flex_scheduler._get_current_win_appeal(1, 2, sample_standings)
        # 19 * 1.5 = 28.5, capped at 25
        assert appeal == 25

    def test_get_current_win_appeal_low(self, flex_scheduler, sample_standings):
        """Low win teams should have lower appeal."""
        # Team 15 and 16 have few wins
        appeal = flex_scheduler._get_current_win_appeal(15, 16, sample_standings)
        assert appeal < 10

    def test_get_rivalry_appeal_high(self, flex_scheduler, sample_rivalries):
        """High intensity rivalry should add significant appeal."""
        rivalry_map = flex_scheduler._build_rivalry_map(sample_rivalries)
        # Rivalry intensity 95 * 0.2 = 19
        appeal = flex_scheduler._get_rivalry_appeal(1, 2, rivalry_map)
        assert appeal == 19

    def test_get_rivalry_appeal_moderate(self, flex_scheduler, sample_rivalries):
        """Moderate rivalry should add moderate appeal."""
        rivalry_map = flex_scheduler._build_rivalry_map(sample_rivalries)
        # Rivalry intensity 80 * 0.2 = 16
        appeal = flex_scheduler._get_rivalry_appeal(3, 4, rivalry_map)
        assert appeal == 16

    def test_get_rivalry_appeal_no_rivalry(self, flex_scheduler):
        """No rivalry should return 0."""
        appeal = flex_scheduler._get_rivalry_appeal(1, 30, {})
        assert appeal == 0

    def test_get_market_appeal_large_markets(self, flex_scheduler):
        """Large market teams should have high appeal."""
        # Cowboys (17) are market #1
        appeal = flex_scheduler._get_market_appeal(17, 18)  # Cowboys vs Giants
        assert appeal >= 10

    def test_get_market_appeal_small_markets(self, flex_scheduler):
        """Small market teams should have lower appeal."""
        # Jacksonville (11) is market #32
        appeal = flex_scheduler._get_market_appeal(11, 10)  # Jaguars vs lower market team
        assert appeal < 10


class TestEvaluateFlexOpportunities:
    """Tests for evaluate_flex_opportunities method."""

    def test_returns_empty_before_week_12(self, flex_scheduler):
        """Should return empty list for weeks before 12."""
        result = flex_scheduler.evaluate_flex_opportunities(
            season=2025, current_week=8, target_week=10
        )
        assert result == []

    def test_returns_empty_after_week_17(self, flex_scheduler):
        """Should return empty list for target weeks after 17."""
        result = flex_scheduler.evaluate_flex_opportunities(
            season=2025, current_week=16, target_week=18
        )
        assert result == []


class TestFlexThreshold:
    """Tests for FLEX_THRESHOLD constant."""

    def test_flex_threshold_value(self):
        """FLEX_THRESHOLD should be 15."""
        assert FLEX_THRESHOLD == 15


# -------------------- Integration Tests --------------------

class TestFlexSchedulerIntegration:
    """Integration tests for FlexScheduler (require database fixtures)."""

    @pytest.mark.skip(reason="Requires full database setup")
    def test_full_flex_evaluation_workflow(self):
        """Test complete flex evaluation workflow."""
        pass

    @pytest.mark.skip(reason="Requires full database setup")
    def test_execute_flex_updates_database(self):
        """Test that execute_flex properly updates game_slots."""
        pass


# -------------------- Edge Case Tests --------------------

class TestFlexSchedulerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_playoff_implications_empty_standings(self, flex_scheduler):
        """Should handle empty standings gracefully."""
        impl = flex_scheduler.calculate_playoff_implications(
            season=2025, week=12, team_id=1, opponent_id=2, standings=[]
        )
        assert impl.team_id == 1
        assert impl.implication_score == 0

    def test_flex_appeal_with_none_standings(self, flex_scheduler):
        """Should handle None standings gracefully."""
        # Mock the standings_api to return empty
        flex_scheduler._standings_api.get_standings = MagicMock(return_value=[])

        appeal = flex_scheduler.calculate_game_flex_appeal(
            season=2025, week=12,
            home_team_id=1, away_team_id=2,
            standings=None, rivalry_map=None
        )
        # Should return some value based on market size at minimum
        assert isinstance(appeal, int)
        assert 0 <= appeal <= 100
