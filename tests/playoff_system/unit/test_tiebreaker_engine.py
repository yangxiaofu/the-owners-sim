"""
Unit Tests for NFLTiebreakerEngine

Tests the individual tiebreaker rules and their application according
to official NFL procedures.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from playoff_system.seeding.nfl_tiebreaker_engine import NFLTiebreakerEngine
from playoff_system.seeding.seeding_data_models import TeamRecord, TiebreakerRule


class TestNFLTiebreakerEngine(unittest.TestCase):
    """Test cases for NFL tiebreaker engine."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = NFLTiebreakerEngine()

    def test_head_to_head_two_teams_clear_winner(self):
        """Test head-to-head tiebreaker with clear winner."""
        # Team 1 beat Team 2 twice
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        teams = [team1, team2]

        # Team 1 beat Team 2 2-0
        head_to_head = {(1, 2): "2-0"}

        result = self.engine._apply_head_to_head_two_teams(teams, head_to_head)

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.HEAD_TO_HEAD)
        self.assertEqual(result.winner_team_id, 1)
        self.assertIn(2, result.eliminated_teams)
        self.assertTrue(result.was_decisive)

    def test_head_to_head_two_teams_tied(self):
        """Test head-to-head tiebreaker with tied record."""
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        teams = [team1, team2]

        # Teams split their games 1-1
        head_to_head = {(1, 2): "1-1"}

        result = self.engine._apply_head_to_head_two_teams(teams, head_to_head)

        # Should return None because head-to-head is tied
        self.assertIsNone(result)

    def test_head_to_head_no_games_played(self):
        """Test head-to-head when teams haven't played."""
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        teams = [team1, team2]

        # No head-to-head games
        head_to_head = {}

        result = self.engine._apply_head_to_head_two_teams(teams, head_to_head)

        # Should return None because no head-to-head games
        self.assertIsNone(result)

    def test_division_record_tiebreaker(self):
        """Test division record tiebreaker."""
        # Team 1 has better division record
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            division_wins=5, division_losses=1
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            division_wins=3, division_losses=3
        )
        teams = [team1, team2]

        result = self.engine._apply_division_record(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.DIVISION_RECORD)
        self.assertEqual(result.winner_team_id, 1)
        self.assertIn(2, result.eliminated_teams)

    def test_division_record_tied(self):
        """Test division record when teams are tied."""
        # Both teams have same division record
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            division_wins=4, division_losses=2
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            division_wins=4, division_losses=2
        )
        teams = [team1, team2]

        result = self.engine._apply_division_record(teams, {})

        # Should return None because division records are tied
        self.assertIsNone(result)

    def test_conference_record_tiebreaker(self):
        """Test conference record tiebreaker."""
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            conference_wins=8, conference_losses=4
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            conference_wins=7, conference_losses=5
        )
        teams = [team1, team2]

        result = self.engine._apply_conference_record(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.CONFERENCE_RECORD)
        self.assertEqual(result.winner_team_id, 1)

    def test_strength_of_victory_tiebreaker(self):
        """Test strength of victory tiebreaker."""
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            strength_of_victory=0.600
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            strength_of_victory=0.550
        )
        teams = [team1, team2]

        result = self.engine._apply_strength_of_victory(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.STRENGTH_OF_VICTORY)
        self.assertEqual(result.winner_team_id, 1)

    def test_strength_of_schedule_tiebreaker(self):
        """Test strength of schedule tiebreaker."""
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            strength_of_schedule=0.520
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            strength_of_schedule=0.480
        )
        teams = [team1, team2]

        result = self.engine._apply_strength_of_schedule(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.STRENGTH_OF_SCHEDULE)
        self.assertEqual(result.winner_team_id, 1)

    def test_net_points_all_tiebreaker(self):
        """Test net points in all games tiebreaker."""
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            points_for=350, points_against=300  # +50 differential
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            points_for=320, points_against=310  # +10 differential
        )
        teams = [team1, team2]

        result = self.engine._apply_net_points_all(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.NET_POINTS_ALL)
        self.assertEqual(result.winner_team_id, 1)

    def test_coin_flip_tiebreaker(self):
        """Test coin flip tiebreaker (last resort)."""
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        teams = [team1, team2]

        result = self.engine._apply_coin_flip(teams, {})

        self.assertIsNotNone(result)
        self.assertEqual(result.rule_applied, TiebreakerRule.COIN_FLIP)
        self.assertIn(result.winner_team_id, [1, 2])
        self.assertTrue(result.was_decisive)

    def test_division_tie_cascade(self):
        """Test division tiebreaker cascade."""
        # Two teams with same overall record
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            strength_of_victory=0.500,
            strength_of_schedule=0.500,
            points_for=300, points_against=280  # +20 differential
        )
        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            division_wins=4, division_losses=2,  # Same division record
            conference_wins=6, conference_losses=6,  # Worse conference record
            strength_of_victory=0.500,
            strength_of_schedule=0.500,
            points_for=290, points_against=285  # +5 differential
        )

        teams = [team1, team2]
        head_to_head = {(1, 2): "1-1"}  # Split head-to-head

        result = self.engine.break_division_tie(teams, head_to_head)

        # Should return teams in order with team1 first (better conference record)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].team_id, 1)
        self.assertEqual(result[1].team_id, 2)

    def test_wildcard_tie_different_from_division(self):
        """Test that wildcard tiebreakers follow different rules."""
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        teams = [team1, team2]

        # Wild card tie should use different method order
        division_result = self.engine.break_division_tie(teams, {})
        wildcard_result = self.engine.break_wildcard_tie(teams, {})

        # Both should return ordered teams (may be same order but different process)
        self.assertEqual(len(division_result), 2)
        self.assertEqual(len(wildcard_result), 2)

    def test_three_team_tie_handling(self):
        """Test handling of three-team ties."""
        team1 = TeamRecord(team_id=1, wins=10, losses=7)
        team2 = TeamRecord(team_id=2, wins=10, losses=7)
        team3 = TeamRecord(team_id=3, wins=10, losses=7)
        teams = [team1, team2, team3]

        result = self.engine.break_division_tie(teams, {})

        # Should return all three teams in some order
        self.assertEqual(len(result), 3)
        returned_ids = [team.team_id for team in result]
        self.assertIn(1, returned_ids)
        self.assertIn(2, returned_ids)
        self.assertIn(3, returned_ids)


class TestTiebreakerScenarios(unittest.TestCase):
    """Test complex tiebreaker scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = NFLTiebreakerEngine()

    def test_realistic_afc_east_scenario(self):
        """Test realistic AFC East division race scenario."""
        # Bills and Dolphins tied at 11-6
        bills = TeamRecord(
            team_id=1, wins=11, losses=6,  # Buffalo Bills
            division_wins=4, division_losses=2,
            conference_wins=8, conference_losses=4,
            points_for=420, points_against=350
        )

        dolphins = TeamRecord(
            team_id=2, wins=11, losses=6,  # Miami Dolphins
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=380, points_against=340
        )

        teams = [bills, dolphins]

        # Bills swept Dolphins 2-0 in head-to-head
        head_to_head = {(1, 2): "2-0"}

        result = self.engine.break_division_tie(teams, head_to_head)

        # Bills should win division on head-to-head
        self.assertEqual(result[0].team_id, 1)  # Bills
        self.assertEqual(result[1].team_id, 2)  # Dolphins

    def test_complex_wildcard_scenario(self):
        """Test complex wild card scenario with multiple teams."""
        # Four teams competing for final wild card spot
        steelers = TeamRecord(
            team_id=8, wins=9, losses=8,  # Pittsburgh
            conference_wins=6, conference_losses=6,
            strength_of_victory=0.520,
            points_for=320, points_against=310
        )

        colts = TeamRecord(
            team_id=10, wins=9, losses=8,  # Indianapolis
            conference_wins=6, conference_losses=6,
            strength_of_victory=0.480,
            points_for=310, points_against=315
        )

        teams = [steelers, colts]

        result = self.engine.break_wildcard_tie(teams, {})

        # Steelers should win on strength of victory
        self.assertEqual(result[0].team_id, 8)  # Steelers

    def test_perfect_tie_scenario(self):
        """Test scenario where teams are tied on everything."""
        team1 = TeamRecord(
            team_id=1, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            strength_of_victory=0.500,
            strength_of_schedule=0.500,
            points_for=300, points_against=300
        )

        team2 = TeamRecord(
            team_id=2, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            strength_of_victory=0.500,
            strength_of_schedule=0.500,
            points_for=300, points_against=300
        )

        teams = [team1, team2]
        head_to_head = {(1, 2): "1-1"}  # Split

        # Should eventually resolve with coin flip
        result = self.engine.break_division_tie(teams, head_to_head)

        self.assertEqual(len(result), 2)
        # One team should be first, but we can't predict which due to randomness


if __name__ == '__main__':
    unittest.main()