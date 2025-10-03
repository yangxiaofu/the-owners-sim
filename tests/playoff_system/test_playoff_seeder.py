"""
Unit Tests for Playoff Seeder

Tests playoff seeding calculation logic with various scenarios.
"""

import pytest

from playoff_system.playoff_seeder import PlayoffSeeder
from stores.standings_store import EnhancedTeamStanding


class TestPlayoffSeeder:
    """Unit tests for PlayoffSeeder."""

    @pytest.fixture
    def seeder(self):
        """Create a playoff seeder instance."""
        return PlayoffSeeder()

    @pytest.fixture
    def mock_standings_basic(self):
        """
        Mock standings with clear winners.

        AFC East: 1=12-4, 2=8-8, 3=6-10, 4=4-12
        AFC North: 5=11-5, 6=9-7, 7=7-9, 8=5-11
        AFC South: 9=10-6, 10=9-7, 11=6-10, 12=3-13
        AFC West: 13=13-3, 14=10-6, 15=8-8, 16=5-11

        AFC Seeding should be:
        1. Team 13 (13-3) - AFC West winner
        2. Team 1 (12-4) - AFC East winner
        3. Team 5 (11-5) - AFC North winner
        4. Team 9 (10-6) - AFC South winner
        5. Team 14 (10-6) - Wildcard
        6. Team 10 (9-7) - Wildcard
        7. Team 6 (9-7) - Wildcard
        """
        standings = {}

        # AFC East
        standings[1] = EnhancedTeamStanding(
            team_id=1, wins=12, losses=4, points_for=420, points_against=310,
            division_wins=5, division_losses=1, conference_wins=9, conference_losses=3
        )
        standings[2] = EnhancedTeamStanding(
            team_id=2, wins=8, losses=8, points_for=350, points_against=350,
            division_wins=3, division_losses=3, conference_wins=6, conference_losses=6
        )
        standings[3] = EnhancedTeamStanding(
            team_id=3, wins=6, losses=10, points_for=280, points_against=380,
            division_wins=2, division_losses=4, conference_wins=4, conference_losses=8
        )
        standings[4] = EnhancedTeamStanding(
            team_id=4, wins=4, losses=12, points_for=240, points_against=420,
            division_wins=1, division_losses=5, conference_wins=3, conference_losses=9
        )

        # AFC North
        standings[5] = EnhancedTeamStanding(
            team_id=5, wins=11, losses=5, points_for=410, points_against=320,
            division_wins=4, division_losses=2, conference_wins=8, conference_losses=4
        )
        standings[6] = EnhancedTeamStanding(
            team_id=6, wins=9, losses=7, points_for=370, points_against=340,
            division_wins=3, division_losses=3, conference_wins=7, conference_losses=5
        )
        standings[7] = EnhancedTeamStanding(
            team_id=7, wins=7, losses=9, points_for=310, points_against=360,
            division_wins=2, division_losses=4, conference_wins=5, conference_losses=7
        )
        standings[8] = EnhancedTeamStanding(
            team_id=8, wins=5, losses=11, points_for=270, points_against=400,
            division_wins=1, division_losses=5, conference_wins=4, conference_losses=8
        )

        # AFC South
        standings[9] = EnhancedTeamStanding(
            team_id=9, wins=10, losses=6, points_for=390, points_against=330,
            division_wins=5, division_losses=1, conference_wins=8, conference_losses=4
        )
        standings[10] = EnhancedTeamStanding(
            team_id=10, wins=9, losses=7, points_for=360, points_against=350,
            division_wins=4, division_losses=2, conference_wins=7, conference_losses=5
        )
        standings[11] = EnhancedTeamStanding(
            team_id=11, wins=6, losses=10, points_for=290, points_against=370,
            division_wins=2, division_losses=4, conference_wins=5, conference_losses=7
        )
        standings[12] = EnhancedTeamStanding(
            team_id=12, wins=3, losses=13, points_for=220, points_against=430,
            division_wins=1, division_losses=5, conference_wins=2, conference_losses=10
        )

        # AFC West
        standings[13] = EnhancedTeamStanding(
            team_id=13, wins=13, losses=3, points_for=450, points_against=280,
            division_wins=5, division_losses=1, conference_wins=10, conference_losses=2
        )
        standings[14] = EnhancedTeamStanding(
            team_id=14, wins=10, losses=6, points_for=400, points_against=320,
            division_wins=4, division_losses=2, conference_wins=8, conference_losses=4
        )
        standings[15] = EnhancedTeamStanding(
            team_id=15, wins=8, losses=8, points_for=340, points_against=360,
            division_wins=3, division_losses=3, conference_wins=6, conference_losses=6
        )
        standings[16] = EnhancedTeamStanding(
            team_id=16, wins=5, losses=11, points_for=260, points_against=410,
            division_wins=2, division_losses=4, conference_wins=4, conference_losses=8
        )

        # NFC - simplified for testing (just need some data)
        for team_id in range(17, 33):
            wins = 16 - (team_id % 8)
            standings[team_id] = EnhancedTeamStanding(
                team_id=team_id, wins=wins, losses=16-wins,
                points_for=wins * 25, points_against=(16-wins) * 25,
                division_wins=wins//2, division_losses=(16-wins)//2,
                conference_wins=wins, conference_losses=16-wins
            )

        return standings

    def test_calculate_seeding_basic_structure(self, seeder, mock_standings_basic):
        """Test that seeding calculation returns correct structure."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        assert result.season == 2024
        assert result.week == 18
        assert len(result.afc.seeds) == 7
        assert len(result.nfc.seeds) == 7
        assert result.calculation_date is not None

    def test_division_winners_occupy_seeds_1_to_4(self, seeder, mock_standings_basic):
        """Test that division winners are seeded 1-4."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Check AFC
        for i, seed in enumerate(result.afc.seeds[:4], start=1):
            assert seed.division_winner is True, f"Seed {i} should be division winner"
            assert seed.seed == i

        # Check NFC
        for i, seed in enumerate(result.nfc.seeds[:4], start=1):
            assert seed.division_winner is True, f"Seed {i} should be division winner"
            assert seed.seed == i

    def test_wildcards_occupy_seeds_5_to_7(self, seeder, mock_standings_basic):
        """Test that wildcards are seeded 5-7."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Check AFC
        for i, seed in enumerate(result.afc.seeds[4:], start=5):
            assert seed.division_winner is False, f"Seed {i} should be wildcard"
            assert seed.seed == i

        # Check NFC
        for i, seed in enumerate(result.nfc.seeds[4:], start=5):
            assert seed.division_winner is False, f"Seed {i} should be wildcard"
            assert seed.seed == i

    def test_afc_seeding_order(self, seeder, mock_standings_basic):
        """Test that AFC teams are seeded correctly by record."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Expected AFC seeding based on mock data:
        # 1. Team 13 (13-3) - AFC West
        # 2. Team 1 (12-4) - AFC East
        # 3. Team 5 (11-5) - AFC North
        # 4. Team 9 (10-6) - AFC South
        # 5. Team 14 (10-6) - Wildcard
        # 6. Team 10 (9-7) - Wildcard
        # 7. Team 6 (9-7) - Wildcard

        seeds = result.afc.seeds
        assert seeds[0].team_id == 13, "Team 13 should be #1 seed"
        assert seeds[1].team_id == 1, "Team 1 should be #2 seed"
        assert seeds[2].team_id == 5, "Team 5 should be #3 seed"
        assert seeds[3].team_id == 9, "Team 9 should be #4 seed"
        assert seeds[4].team_id == 14, "Team 14 should be #5 seed (wildcard)"

    def test_seeds_sorted_by_win_percentage(self, seeder, mock_standings_basic):
        """Test that seeds are sorted by win percentage within their groups."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Check AFC division winners sorted
        afc_div_winners = result.afc.division_winners
        for i in range(len(afc_div_winners) - 1):
            current_wp = afc_div_winners[i].win_percentage
            next_wp = afc_div_winners[i+1].win_percentage
            assert current_wp >= next_wp, \
                f"Seed {i+1} ({current_wp:.3f}) should have >= win % than seed {i+2} ({next_wp:.3f})"

        # Check AFC wildcards sorted
        afc_wildcards = result.afc.wildcards
        for i in range(len(afc_wildcards) - 1):
            current_wp = afc_wildcards[i].win_percentage
            next_wp = afc_wildcards[i+1].win_percentage
            assert current_wp >= next_wp, \
                f"WC {i+5} ({current_wp:.3f}) should have >= win % than WC {i+6} ({next_wp:.3f})"

    def test_get_seed_by_team_id(self, seeder, mock_standings_basic):
        """Test retrieving seed by team ID."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Test AFC team
        seed = result.get_seed(13)
        assert seed is not None
        assert seed.team_id == 13
        assert seed.seed == 1

        # Test NFC team
        seed = result.get_seed(17)
        assert seed is not None
        assert seed.team_id == 17

    def test_is_in_playoffs(self, seeder, mock_standings_basic):
        """Test playoff status check."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Top teams should be in playoffs
        assert result.is_in_playoffs(13) is True, "Team 13 should be in playoffs"
        assert result.is_in_playoffs(1) is True, "Team 1 should be in playoffs"

        # Bottom teams should not be in playoffs
        assert result.is_in_playoffs(4) is False, "Team 4 should not be in playoffs"
        assert result.is_in_playoffs(12) is False, "Team 12 should not be in playoffs"

    def test_conference_seeding_properties(self, seeder, mock_standings_basic):
        """Test ConferenceSeeding helper properties."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Test get_seed_by_number
        afc_seed_1 = result.afc.get_seed_by_number(1)
        assert afc_seed_1 is not None
        assert afc_seed_1.seed == 1
        assert afc_seed_1.team_id == 13

        # Test get_seed_by_team
        team_5_seed = result.afc.get_seed_by_team(5)
        assert team_5_seed is not None
        assert team_5_seed.team_id == 5
        assert team_5_seed.seed == 3

    def test_clinched_and_eliminated(self, seeder, mock_standings_basic):
        """Test clinched and eliminated team tracking."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # AFC should have 7 clinched, 9 eliminated
        assert len(result.afc.clinched_teams) == 7
        assert len(result.afc.eliminated_teams) == 9

        # Top seed should be clinched
        assert result.is_clinched(13) is True

        # Bottom team should be eliminated
        assert result.is_eliminated(12) is True

    def test_playoff_matchups(self, seeder, mock_standings_basic):
        """Test wild card matchup generation."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        matchups = result.get_matchups()

        # Should have 3 AFC and 3 NFC matchups
        assert len(matchups['AFC']) == 3
        assert len(matchups['NFC']) == 3

        # AFC matchups should be (2v7, 3v6, 4v5)
        # Verify structure (actual team IDs may vary)
        afc_seeds = {seed.seed: seed.team_id for seed in result.afc.seeds}

        assert matchups['AFC'][0] == (afc_seeds[2], afc_seeds[7])  # 2 vs 7
        assert matchups['AFC'][1] == (afc_seeds[3], afc_seeds[6])  # 3 vs 6
        assert matchups['AFC'][2] == (afc_seeds[4], afc_seeds[5])  # 4 vs 5

    def test_to_dict_serialization(self, seeder, mock_standings_basic):
        """Test seeding can be serialized to dictionary."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        seeding_dict = result.to_dict()

        assert seeding_dict['season'] == 2024
        assert seeding_dict['week'] == 18
        assert 'afc' in seeding_dict
        assert 'nfc' in seeding_dict
        assert len(seeding_dict['afc']['seeds']) == 7
        assert len(seeding_dict['nfc']['seeds']) == 7

    def test_seed_label_property(self, seeder, mock_standings_basic):
        """Test PlayoffSeed label generation."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Seed 1 should have bye label
        assert "#1 Seed (Bye)" in result.afc.seeds[0].seed_label

        # Seeds 2-4 should be division winners
        assert "Division Winner" in result.afc.seeds[1].seed_label

        # Seeds 5-7 should be wildcards
        assert "Wild Card" in result.afc.seeds[4].seed_label

    def test_record_string_property(self, seeder, mock_standings_basic):
        """Test record string formatting."""
        result = seeder.calculate_seeding(mock_standings_basic, season=2024, week=18)

        # Test normal record
        seed = result.afc.seeds[0]
        assert seed.record_string == f"{seed.wins}-{seed.losses}"

        # Test with ties (create standings with ties)
        standings_with_ties = mock_standings_basic.copy()
        standings_with_ties[1] = EnhancedTeamStanding(
            team_id=1, wins=10, losses=5, ties=1,
            points_for=400, points_against=300
        )

        result_with_ties = seeder.calculate_seeding(standings_with_ties, season=2024, week=18)
        seed_with_tie = result_with_ties.get_seed(1)

        if seed_with_tie and seed_with_tie.ties > 0:
            assert f"-{seed_with_tie.ties}" in seed_with_tie.record_string


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
