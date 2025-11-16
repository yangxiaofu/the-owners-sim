"""
Unit Tests for DraftOrderService

Tests draft order calculation including:
- Basic draft order calculation with clear records
- Non-playoff teams drafting first (picks 1-18)
- Playoff team ordering by round
- Strength of schedule tiebreakers
- Multi-round generation (7 rounds, 262 picks)
- Edge cases and validation
"""

import pytest
from offseason.draft_order_service import (
    DraftOrderService,
    TeamRecord,
    DraftPickOrder
)


class TestDraftOrderService:
    """Test suite for DraftOrderService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return DraftOrderService(dynasty_id="test_dynasty", season_year=2025)

    @pytest.fixture
    def sample_standings(self):
        """
        Create sample 32-team standings with realistic NFL records.

        Teams distributed as:
        - Non-playoff teams (18): Team IDs 1-18 with records 4-13 to 9-8
        - Wild Card losers (6): Team IDs 19-24 with records 10-7 to 11-6
        - Divisional losers (4): Team IDs 25-28 with records 11-6 to 12-5
        - Conference losers (2): Team IDs 29-30 with records 13-4
        - Super Bowl loser (1): Team ID 31 with record 14-3
        - Super Bowl winner (1): Team ID 32 with record 15-2
        """
        standings = []

        # Non-playoff teams (18 teams, IDs 1-18)
        # Records from 4-13 to 9-8 (increasing win%)
        non_playoff_records = [
            (1, 4, 13, 0, 0.235),   # Worst record
            (2, 5, 12, 0, 0.294),
            (3, 5, 12, 0, 0.294),
            (4, 6, 11, 0, 0.353),
            (5, 6, 11, 0, 0.353),
            (6, 7, 10, 0, 0.412),
            (7, 7, 10, 0, 0.412),
            (8, 7, 10, 0, 0.412),
            (9, 8, 9, 0, 0.471),
            (10, 8, 9, 0, 0.471),
            (11, 8, 9, 0, 0.471),
            (12, 8, 9, 0, 0.471),
            (13, 9, 8, 0, 0.529),
            (14, 9, 8, 0, 0.529),
            (15, 9, 8, 0, 0.529),
            (16, 9, 8, 0, 0.529),
            (17, 9, 8, 0, 0.529),
            (18, 9, 8, 0, 0.529),
        ]

        for team_id, wins, losses, ties, win_pct in non_playoff_records:
            standings.append(TeamRecord(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                win_percentage=win_pct
            ))

        # Wild Card losers (6 teams, IDs 19-24)
        wild_card_records = [
            (19, 10, 7, 0, 0.588),
            (20, 10, 7, 0, 0.588),
            (21, 11, 6, 0, 0.647),
            (22, 11, 6, 0, 0.647),
            (23, 11, 6, 0, 0.647),
            (24, 11, 6, 0, 0.647),
        ]

        for team_id, wins, losses, ties, win_pct in wild_card_records:
            standings.append(TeamRecord(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                win_percentage=win_pct
            ))

        # Divisional losers (4 teams, IDs 25-28)
        divisional_records = [
            (25, 11, 6, 0, 0.647),
            (26, 12, 5, 0, 0.706),
            (27, 12, 5, 0, 0.706),
            (28, 12, 5, 0, 0.706),
        ]

        for team_id, wins, losses, ties, win_pct in divisional_records:
            standings.append(TeamRecord(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                win_percentage=win_pct
            ))

        # Conference losers (2 teams, IDs 29-30)
        conference_records = [
            (29, 13, 4, 0, 0.765),
            (30, 13, 4, 0, 0.765),
        ]

        for team_id, wins, losses, ties, win_pct in conference_records:
            standings.append(TeamRecord(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                win_percentage=win_pct
            ))

        # Super Bowl teams (2 teams, IDs 31-32)
        super_bowl_records = [
            (31, 14, 3, 0, 0.824),  # Loser
            (32, 15, 2, 0, 0.882),  # Winner
        ]

        for team_id, wins, losses, ties, win_pct in super_bowl_records:
            standings.append(TeamRecord(
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=ties,
                win_percentage=win_pct
            ))

        return standings

    @pytest.fixture
    def sample_playoff_results(self):
        """Create sample playoff results matching the standings fixture"""
        return {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],  # 6 teams
            'divisional_losers': [25, 26, 27, 28],  # 4 teams
            'conference_losers': [29, 30],  # 2 teams
            'super_bowl_loser': 31,  # 1 team
            'super_bowl_winner': 32  # 1 team
        }

    @pytest.fixture
    def sample_schedules(self):
        """
        Create sample schedules for SOS calculations.

        Returns dict mapping team_id -> list of 17 opponent team_ids.
        For simplicity, we'll create schedules that result in different SOS values.
        """
        schedules = {}

        # Non-playoff teams (1-18) - varying opponent strengths
        # Team 1 plays weak opponents (low SOS)
        schedules[1] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

        # Team 2 plays slightly stronger opponents (higher SOS)
        schedules[2] = [1, 3, 4, 5, 6, 7, 8, 9, 19, 20, 21, 22, 23, 24, 25, 26, 27]

        # Team 3 plays same record opponents but different teams (for tie testing)
        schedules[3] = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 28]

        # Fill in rest of non-playoff teams with moderate schedules
        for team_id in range(4, 19):
            schedules[team_id] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

        # Playoff teams (19-32) - all play strong opponents
        for team_id in range(19, 33):
            schedules[team_id] = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 19, 18, 17, 16]

        return schedules

    # ============================================================================
    # BASIC FUNCTIONALITY TESTS
    # ============================================================================

    def test_service_initialization(self, service):
        """Test service is initialized correctly"""
        assert service.dynasty_id == "test_dynasty"
        assert service.season_year == 2025
        assert service._sos_cache == {}

    def test_basic_draft_order_calculation(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test basic draft order calculation returns 224 picks"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        assert len(draft_order) == 224, "Should generate 224 total picks (7 rounds × 32 picks)"
        assert all(isinstance(pick, DraftPickOrder) for pick in draft_order)

    def test_non_playoff_teams_draft_first(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that non-playoff teams get picks 1-18"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Check Round 1 picks 1-18 are all non-playoff teams
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        non_playoff_picks = round_1_picks[:18]

        # All picks 1-18 should be non-playoff teams (IDs 1-18)
        non_playoff_team_ids = {pick.team_id for pick in non_playoff_picks}
        assert non_playoff_team_ids.issubset(set(range(1, 19))), \
            "Picks 1-18 should all be non-playoff teams (IDs 1-18)"

        # All should have reason "non_playoff"
        assert all(pick.reason == "non_playoff" for pick in non_playoff_picks)

    def test_playoff_teams_draft_after_non_playoff(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that playoff teams draft after non-playoff teams"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Check Round 1 picks 19-32 are all playoff teams
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        playoff_picks = round_1_picks[18:]  # Picks 19-32

        # All picks 19-32 should be playoff teams (IDs 19-32)
        playoff_team_ids = {pick.team_id for pick in playoff_picks}
        assert playoff_team_ids.issubset(set(range(19, 33))), \
            "Picks 19-32 should all be playoff teams (IDs 19-32)"

    def test_super_bowl_winner_gets_pick_32(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that Super Bowl winner gets pick 32"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Find pick 32 in Round 1
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        pick_32 = round_1_picks[31]  # Index 31 = pick 32

        assert pick_32.team_id == 32, "Super Bowl winner (team 32) should have pick 32"
        assert pick_32.reason == "super_bowl_win"
        assert pick_32.pick_in_round == 32
        assert pick_32.overall_pick == 32

    # ============================================================================
    # TIEBREAKER TESTS
    # ============================================================================

    def test_strength_of_schedule_tiebreaker(self, service, sample_standings):
        """Test SOS tiebreaker for teams with identical records"""
        # Create two teams with identical 8-9 records
        team_a_schedule = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]  # Weak opponents
        team_b_schedule = [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 18, 17, 16]  # Strong opponents

        sos_a = service.calculate_strength_of_schedule(9, sample_standings, team_a_schedule)
        sos_b = service.calculate_strength_of_schedule(10, sample_standings, team_b_schedule)

        # Team A played weaker opponents (lower SOS)
        assert sos_a < sos_b, "Team A should have lower SOS (weaker opponents)"

        # In draft order, team with easier schedule (lower SOS) should pick first
        teams_to_sort = [9, 10]
        sorted_teams = service._sort_teams_by_record(teams_to_sort, sample_standings, reverse=False)

        assert sorted_teams[0] == 9, "Team with easier schedule should draft first"
        assert sorted_teams[1] == 10, "Team with harder schedule should draft second"

    def test_sos_calculation_accuracy(self, service, sample_standings):
        """Test that SOS calculation is mathematically correct"""
        # Create a specific schedule with known opponent win percentages
        # Team 1 plays teams 2, 3, 4 (all with specific records)
        schedule = [2, 3, 4]  # 3 opponents

        # Get opponent win percentages
        team_2_win_pct = 0.294  # 5-12
        team_3_win_pct = 0.294  # 5-12
        team_4_win_pct = 0.353  # 6-11

        expected_sos = (team_2_win_pct + team_3_win_pct + team_4_win_pct) / 3
        calculated_sos = service.calculate_strength_of_schedule(1, sample_standings, schedule)

        assert abs(calculated_sos - expected_sos) < 0.001, \
            f"SOS should be {expected_sos:.3f}, got {calculated_sos:.3f}"

    def test_sos_cache_usage(self, service, sample_standings):
        """Test that SOS results are cached and reused"""
        schedule = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

        # Calculate SOS first time
        sos_1 = service.calculate_strength_of_schedule(1, sample_standings, schedule)

        # Calculate SOS second time (should use cache)
        sos_2 = service.calculate_strength_of_schedule(1, sample_standings, None)  # No schedule needed

        assert sos_1 == sos_2, "Cached SOS should match original calculation"
        assert 1 in service._sos_cache, "Team 1 SOS should be in cache"

    # ============================================================================
    # PLAYOFF ORDERING TESTS
    # ============================================================================

    def test_wild_card_losers_get_picks_19_24(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test Wild Card losers get picks 19-24"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 picks 19-24
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        wild_card_picks = round_1_picks[18:24]  # Picks 19-24 (indices 18-23)

        # All should be Wild Card losers
        wild_card_team_ids = {pick.team_id for pick in wild_card_picks}
        expected_wc_teams = set(sample_playoff_results['wild_card_losers'])

        assert wild_card_team_ids == expected_wc_teams, \
            "Picks 19-24 should be Wild Card losers"

        # All should have reason "wild_card_loss"
        assert all(pick.reason == "wild_card_loss" for pick in wild_card_picks)

    def test_divisional_losers_get_picks_25_28(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test Divisional Round losers get picks 25-28"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 picks 25-28
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        divisional_picks = round_1_picks[24:28]  # Picks 25-28 (indices 24-27)

        # All should be Divisional losers
        divisional_team_ids = {pick.team_id for pick in divisional_picks}
        expected_div_teams = set(sample_playoff_results['divisional_losers'])

        assert divisional_team_ids == expected_div_teams, \
            "Picks 25-28 should be Divisional Round losers"

        # All should have reason "divisional_loss"
        assert all(pick.reason == "divisional_loss" for pick in divisional_picks)

    def test_conference_losers_get_picks_29_30(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test Conference Championship losers get picks 29-30"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 picks 29-30
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        conference_picks = round_1_picks[28:30]  # Picks 29-30 (indices 28-29)

        # All should be Conference losers
        conference_team_ids = {pick.team_id for pick in conference_picks}
        expected_conf_teams = set(sample_playoff_results['conference_losers'])

        assert conference_team_ids == expected_conf_teams, \
            "Picks 29-30 should be Conference Championship losers"

        # All should have reason "conference_loss"
        assert all(pick.reason == "conference_loss" for pick in conference_picks)

    def test_super_bowl_teams_last(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test Super Bowl loser (31) and winner (32) draft last"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 picks 31-32
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        pick_31 = round_1_picks[30]
        pick_32 = round_1_picks[31]

        # Pick 31 should be Super Bowl loser
        assert pick_31.team_id == sample_playoff_results['super_bowl_loser']
        assert pick_31.reason == "super_bowl_loss"
        assert pick_31.pick_in_round == 31

        # Pick 32 should be Super Bowl winner
        assert pick_32.team_id == sample_playoff_results['super_bowl_winner']
        assert pick_32.reason == "super_bowl_win"
        assert pick_32.pick_in_round == 32

    # ============================================================================
    # MULTI-ROUND GENERATION TESTS
    # ============================================================================

    def test_all_seven_rounds_generated(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that all 7 rounds are generated (224 picks)"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Check total picks
        assert len(draft_order) == 224, "Should have 224 total picks (7 rounds × 32 picks)"

        # Check each round has 32 picks
        for round_num in range(1, 8):
            round_picks = [pick for pick in draft_order if pick.round_number == round_num]
            assert len(round_picks) == 32, f"Round {round_num} should have 32 picks"

    def test_round_2_same_order_as_round_1(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that round 2+ use same team order as round 1"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 and Round 2 team orders
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        round_2_picks = [pick for pick in draft_order if pick.round_number == 2]

        round_1_team_order = [pick.team_id for pick in round_1_picks]
        round_2_team_order = [pick.team_id for pick in round_2_picks]

        assert round_1_team_order == round_2_team_order, \
            "Round 2 should use same team order as Round 1"

    def test_all_rounds_same_order(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that all 7 rounds use the same team order"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get team order for each round
        round_orders = []
        for round_num in range(1, 8):
            round_picks = [pick for pick in draft_order if pick.round_number == round_num]
            team_order = [pick.team_id for pick in round_picks]
            round_orders.append(team_order)

        # All rounds should have same order
        first_round_order = round_orders[0]
        for round_num, round_order in enumerate(round_orders[1:], start=2):
            assert round_order == first_round_order, \
                f"Round {round_num} order should match Round 1 order"

    def test_overall_pick_numbering(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that overall_pick is numbered correctly 1-224"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Check overall_pick sequence
        expected_overall_picks = list(range(1, 225))  # 1 to 224
        actual_overall_picks = [pick.overall_pick for pick in draft_order]

        assert actual_overall_picks == expected_overall_picks, \
            "overall_pick should be numbered 1-224 sequentially"

    def test_round_2_starts_at_pick_33(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that round 2 starts at overall pick 33"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get first pick of Round 2
        round_2_picks = [pick for pick in draft_order if pick.round_number == 2]
        first_round_2_pick = round_2_picks[0]

        assert first_round_2_pick.overall_pick == 33, \
            "Round 2 should start at overall pick 33"
        assert first_round_2_pick.pick_in_round == 1, \
            "First pick in Round 2 should have pick_in_round = 1"

    # ============================================================================
    # EDGE CASE AND VALIDATION TESTS
    # ============================================================================

    def test_invalid_team_count_too_few(self, service, sample_playoff_results):
        """Test validation error for too few teams"""
        # Create standings with only 30 teams
        standings = [
            TeamRecord(team_id=i, wins=8, losses=9, ties=0, win_percentage=0.471)
            for i in range(1, 31)  # Only 30 teams
        ]

        with pytest.raises(ValueError, match="Expected 32 team records"):
            service.calculate_draft_order(standings, sample_playoff_results)

    def test_invalid_team_count_too_many(self, service, sample_playoff_results):
        """Test validation error for too many teams"""
        # Create standings with 34 teams
        standings = [
            TeamRecord(team_id=i, wins=8, losses=9, ties=0, win_percentage=0.471)
            for i in range(1, 35)  # 34 teams
        ]

        with pytest.raises(ValueError, match="Expected 32 team records"):
            service.calculate_draft_order(standings, sample_playoff_results)

    def test_missing_playoff_result_keys(self, service, sample_standings):
        """Test validation error for missing playoff result keys"""
        incomplete_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 28],
            # Missing conference_losers, super_bowl_loser, super_bowl_winner
        }

        with pytest.raises(ValueError, match="Missing required playoff result keys"):
            service.calculate_draft_order(sample_standings, incomplete_results)

    def test_invalid_wild_card_count(self, service, sample_standings):
        """Test validation error for wrong number of wild card losers"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23],  # Only 5 instead of 6
            'divisional_losers': [25, 26, 27, 28],
            'conference_losers': [29, 30],
            'super_bowl_loser': 31,
            'super_bowl_winner': 32
        }

        with pytest.raises(ValueError, match="Expected 6 wild card losers"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_invalid_divisional_count(self, service, sample_standings):
        """Test validation error for wrong number of divisional losers"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27],  # Only 3 instead of 4
            'conference_losers': [29, 30],
            'super_bowl_loser': 31,
            'super_bowl_winner': 32
        }

        with pytest.raises(ValueError, match="Expected 4 divisional losers"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_invalid_conference_count(self, service, sample_standings):
        """Test validation error for wrong number of conference losers"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 28],
            'conference_losers': [29],  # Only 1 instead of 2
            'super_bowl_loser': 31,
            'super_bowl_winner': 32
        }

        with pytest.raises(ValueError, match="Expected 2 conference losers"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_duplicate_playoff_teams(self, service, sample_standings):
        """Test validation error for duplicate teams in playoff results"""
        duplicate_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 19],  # Team 19 appears twice
            'conference_losers': [29, 30],
            'super_bowl_loser': 31,
            'super_bowl_winner': 32
        }

        with pytest.raises(ValueError, match="Duplicate teams found in playoff results"):
            service.calculate_draft_order(sample_standings, duplicate_results)

    def test_invalid_super_bowl_loser_type(self, service, sample_standings):
        """Test validation error for non-integer super_bowl_loser"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 28],
            'conference_losers': [29, 30],
            'super_bowl_loser': "31",  # String instead of int
            'super_bowl_winner': 32
        }

        with pytest.raises(ValueError, match="super_bowl_loser must be an integer"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_invalid_super_bowl_winner_type(self, service, sample_standings):
        """Test validation error for non-integer super_bowl_winner"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 28],
            'conference_losers': [29, 30],
            'super_bowl_loser': 31,
            'super_bowl_winner': [32]  # List instead of int
        }

        with pytest.raises(ValueError, match="super_bowl_winner must be an integer"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_wrong_total_playoff_teams(self, service, sample_standings):
        """Test validation error for wrong total playoff team count"""
        invalid_results = {
            'wild_card_losers': [19, 20, 21, 22, 23, 24],
            'divisional_losers': [25, 26, 27, 28],
            'conference_losers': [29, 30],
            'super_bowl_loser': 31,
            'super_bowl_winner': 31  # Same as loser (duplicate)
        }

        with pytest.raises(ValueError, match="Duplicate teams found in playoff results"):
            service.calculate_draft_order(sample_standings, invalid_results)

    def test_sos_calculation_missing_schedule(self, service, sample_standings):
        """Test that SOS calculation requires schedule"""
        with pytest.raises(ValueError, match="Schedule required for team"):
            service.calculate_strength_of_schedule(1, sample_standings, None)

    def test_sos_calculation_empty_schedule(self, service, sample_standings):
        """Test that SOS calculation rejects empty schedule"""
        with pytest.raises(ValueError, match="Schedule required for team"):
            service.calculate_strength_of_schedule(1, sample_standings, [])

    # ============================================================================
    # DATA STRUCTURE TESTS
    # ============================================================================

    def test_team_record_dataclass(self):
        """Test TeamRecord dataclass creation and string representation"""
        record = TeamRecord(
            team_id=1,
            wins=11,
            losses=6,
            ties=0,
            win_percentage=0.647
        )

        assert record.team_id == 1
        assert record.wins == 11
        assert record.losses == 6
        assert record.ties == 0
        assert record.win_percentage == 0.647
        assert str(record) == "11-6-0"

    def test_team_record_with_ties(self):
        """Test TeamRecord string representation with ties"""
        record = TeamRecord(
            team_id=5,
            wins=10,
            losses=6,
            ties=1,
            win_percentage=0.618
        )

        assert str(record) == "10-6-1"

    def test_draft_pick_order_dataclass(self):
        """Test DraftPickOrder dataclass creation"""
        pick = DraftPickOrder(
            round_number=1,
            pick_in_round=1,
            overall_pick=1,
            team_id=15,
            original_team_id=15,
            reason="non_playoff",
            team_record="4-13-0",
            strength_of_schedule=0.485
        )

        assert pick.round_number == 1
        assert pick.pick_in_round == 1
        assert pick.overall_pick == 1
        assert pick.team_id == 15
        assert pick.original_team_id == 15
        assert pick.reason == "non_playoff"
        assert pick.team_record == "4-13-0"
        assert pick.strength_of_schedule == 0.485

    def test_draft_pick_order_string_representation(self):
        """Test DraftPickOrder string representation"""
        pick = DraftPickOrder(
            round_number=2,
            pick_in_round=15,
            overall_pick=47,
            team_id=22,
            original_team_id=22,
            reason="wild_card_loss",
            team_record="11-6-0",
            strength_of_schedule=0.520
        )

        expected = "Round 2, Pick 15 (#47 overall): Team 22 - wild_card_loss (11-6-0, SOS: 0.520)"
        assert str(pick) == expected

    def test_reason_field_values(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that reason field values are correct for all pick types"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get Round 1 picks
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]

        # Check reason values for different pick ranges
        expected_reasons = {
            (1, 18): "non_playoff",
            (19, 24): "wild_card_loss",
            (25, 28): "divisional_loss",
            (29, 30): "conference_loss",
            (31, 31): "super_bowl_loss",
            (32, 32): "super_bowl_win"
        }

        for (start, end), expected_reason in expected_reasons.items():
            for pick_num in range(start, end + 1):
                pick = round_1_picks[pick_num - 1]
                assert pick.reason == expected_reason, \
                    f"Pick {pick_num} should have reason '{expected_reason}', got '{pick.reason}'"

    def test_original_team_id_matches_team_id(self, service, sample_standings, sample_playoff_results, sample_schedules):
        """Test that original_team_id matches team_id initially (before trades)"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # All picks should have original_team_id == team_id initially
        for pick in draft_order:
            assert pick.original_team_id == pick.team_id, \
                f"Pick {pick.overall_pick}: original_team_id should match team_id initially"

    # ============================================================================
    # PARAMETRIZED TESTS
    # ============================================================================

    @pytest.mark.parametrize("round_num,expected_first_pick,expected_last_pick", [
        (1, 1, 32),
        (2, 33, 64),
        (3, 65, 96),
        (4, 97, 128),
        (5, 129, 160),
        (6, 161, 192),
        (7, 193, 224),
    ])
    def test_round_pick_ranges(self, service, sample_standings, sample_playoff_results,
                               sample_schedules, round_num, expected_first_pick, expected_last_pick):
        """Test that each round has correct overall pick range"""
        # Pre-populate SOS cache
        for team_id, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(team_id, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Get picks for this round
        round_picks = [pick for pick in draft_order if pick.round_number == round_num]

        # Check first and last overall picks
        assert round_picks[0].overall_pick == expected_first_pick, \
            f"Round {round_num} should start at pick {expected_first_pick}"
        assert round_picks[-1].overall_pick == expected_last_pick, \
            f"Round {round_num} should end at pick {expected_last_pick}"

    @pytest.mark.parametrize("team_id,expected_reason", [
        (1, "non_playoff"),   # Non-playoff team
        (19, "wild_card_loss"),  # Wild Card loser
        (25, "divisional_loss"),  # Divisional loser
        (29, "conference_loss"),  # Conference loser
        (31, "super_bowl_loss"),  # Super Bowl loser
        (32, "super_bowl_win"),   # Super Bowl winner
    ])
    def test_team_reason_mapping(self, service, sample_standings, sample_playoff_results,
                                 sample_schedules, team_id, expected_reason):
        """Test that specific teams get correct reasons"""
        # Pre-populate SOS cache
        for tid, schedule in sample_schedules.items():
            service.calculate_strength_of_schedule(tid, sample_standings, schedule)

        draft_order = service.calculate_draft_order(sample_standings, sample_playoff_results)

        # Find this team's Round 1 pick
        round_1_picks = [pick for pick in draft_order if pick.round_number == 1]
        team_pick = next(pick for pick in round_1_picks if pick.team_id == team_id)

        assert team_pick.reason == expected_reason, \
            f"Team {team_id} should have reason '{expected_reason}'"
