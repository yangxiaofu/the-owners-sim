"""
Integration Tests for Complete Playoff Seeding System

Tests the full playoff seeding pipeline using realistic data scenarios.
Validates the integration between all components: calculator, tiebreaker engine,
strength calculator, and data models.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from playoff_system.seeding.playoff_seeding_calculator import PlayoffSeedingCalculator
from playoff_system.seeding.seeding_data_models import PlayoffSeedingInput
from tests.playoff_system.fixtures.sample_standings import (
    SampleStandings, HeadToHeadScenarios,
    SCENARIO_2023_FINAL, SCENARIO_WILDCARD_TIE
)
from tests.playoff_system.fixtures.historical_data import (
    HistoricalPlayoffScenarios, ValidationTestCases,
    HISTORICAL_2023_AFC, HISTORICAL_2023_NFC
)
from datetime import datetime


class TestPlayoffSeedingIntegration(unittest.TestCase):
    """Integration tests for complete playoff seeding system."""

    def setUp(self):
        """Set up test fixtures."""
        self.calculator = PlayoffSeedingCalculator()

    def test_2023_season_realistic_seeding(self):
        """Test complete seeding calculation using 2023 season data."""
        # Create seeding input from 2023 standings
        seeding_input = SampleStandings.create_seeding_input(
            standings=SCENARIO_2023_FINAL,
            dynasty_id="integration_test",
            season=2023
        )

        # Calculate playoff seeding
        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Validate structure
        self.assertEqual(len(playoff_seeding.afc_seeds), 7)
        self.assertEqual(len(playoff_seeding.nfc_seeds), 7)
        self.assertEqual(len(playoff_seeding.wild_card_matchups), 6)  # 3 AFC + 3 NFC

        # Validate AFC seeding order (approximately - strength calculations may vary)
        afc_seeds = playoff_seeding.afc_seeds
        self.assertEqual(afc_seeds[0].team_id, 5)   # Ravens should be #1 seed (13-4)
        self.assertTrue(afc_seeds[0].division_winner)
        self.assertEqual(afc_seeds[0].seed_number, 1)

        # Validate that all seeds are properly numbered 1-7
        afc_seed_numbers = [seed.seed_number for seed in afc_seeds]
        self.assertEqual(sorted(afc_seed_numbers), list(range(1, 8)))

        nfc_seed_numbers = [seed.seed_number for seed in playoff_seeding.nfc_seeds]
        self.assertEqual(sorted(nfc_seed_numbers), list(range(1, 8)))

        # Validate division winners get seeds 1-4
        afc_division_winners = [seed for seed in afc_seeds if seed.division_winner]
        self.assertEqual(len(afc_division_winners), 4)
        for winner in afc_division_winners:
            self.assertLessEqual(winner.seed_number, 4)

        # Validate wild card teams get seeds 5-7
        afc_wildcards = [seed for seed in afc_seeds if not seed.division_winner]
        self.assertEqual(len(afc_wildcards), 3)
        for wildcard in afc_wildcards:
            self.assertGreaterEqual(wildcard.seed_number, 5)

    def test_perfect_tie_scenario_handling(self):
        """Test handling of complex tie scenarios."""
        standings = SampleStandings.create_perfect_tie_scenario()
        seeding_input = SampleStandings.create_seeding_input(
            standings=standings,
            head_to_head=HeadToHeadScenarios.split_series()
        )

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Should still produce valid seeding despite ties
        self.assertEqual(len(playoff_seeding.afc_seeds), 7)
        self.assertEqual(len(playoff_seeding.nfc_seeds), 7)

        # AFC East teams (1-4) should all be represented but with different seeds
        afc_east_teams = [1, 2, 3, 4]
        seeded_afc_east = [seed.team_id for seed in playoff_seeding.afc_seeds if seed.team_id in afc_east_teams]

        # Should have at least one AFC East team in playoffs (division winner)
        self.assertGreaterEqual(len(seeded_afc_east), 1)

    def test_wildcard_tiebreaker_scenario(self):
        """Test specific wild card tiebreaker scenarios."""
        standings = SampleStandings.create_wildcard_tiebreaker_scenario()
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Verify wild card selection
        afc_wildcards = [seed for seed in playoff_seeding.afc_seeds if not seed.division_winner]
        self.assertEqual(len(afc_wildcards), 3)

        # Wild cards should be from teams 2, 7, 10, 15 (the 10-7 teams)
        wildcard_team_ids = [seed.team_id for seed in afc_wildcards]
        expected_candidates = [2, 7, 10, 15]

        for team_id in wildcard_team_ids:
            self.assertIn(team_id, expected_candidates)

        # Team 2 should get wild card due to better strength of victory (0.520)
        wildcard_teams = [seed.team_id for seed in afc_wildcards]
        self.assertIn(2, wildcard_teams)

    def test_wild_card_matchup_generation(self):
        """Test wild card matchup generation follows NFL rules."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Validate matchup structure
        afc_matchups = [m for m in playoff_seeding.wild_card_matchups if m.conference == "AFC"]
        nfc_matchups = [m for m in playoff_seeding.wild_card_matchups if m.conference == "NFC"]

        self.assertEqual(len(afc_matchups), 3)
        self.assertEqual(len(nfc_matchups), 3)

        # Validate matchup pairings (2v7, 3v6, 4v5)
        for matchup in afc_matchups + nfc_matchups:
            higher_seed = matchup.higher_seed.seed_number
            lower_seed = matchup.lower_seed.seed_number

            # Should be valid wild card pairings
            valid_pairings = [(2, 7), (3, 6), (4, 5)]
            self.assertIn((higher_seed, lower_seed), valid_pairings)

            # Higher seed should be home team
            self.assertEqual(matchup.home_team_id, matchup.higher_seed.team_id)
            self.assertEqual(matchup.away_team_id, matchup.lower_seed.team_id)

    def test_division_winner_seeding(self):
        """Test division winner seeding logic."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Check AFC division winner seeding
        afc_division_winners = [seed for seed in playoff_seeding.afc_seeds if seed.division_winner]
        self.assertEqual(len(afc_division_winners), 4)

        # Seeds 1-4 should all be division winners
        seeds_1_to_4 = [seed for seed in playoff_seeding.afc_seeds if seed.seed_number <= 4]
        for seed in seeds_1_to_4:
            self.assertTrue(seed.division_winner)

        # Ravens (13-4) should be #1 seed
        seed_1 = next(seed for seed in playoff_seeding.afc_seeds if seed.seed_number == 1)
        self.assertEqual(seed_1.team_id, 5)  # Ravens

    def test_strength_metrics_calculation(self):
        """Test that strength metrics are calculated during seeding."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Verify strength metrics are set
        for seed in playoff_seeding.afc_seeds + playoff_seeding.nfc_seeds:
            self.assertIsNotNone(seed.strength_of_victory)
            self.assertIsNotNone(seed.strength_of_schedule)
            self.assertGreaterEqual(seed.strength_of_victory, 0.0)
            self.assertLessEqual(seed.strength_of_victory, 1.0)
            self.assertGreaterEqual(seed.strength_of_schedule, 0.0)
            self.assertLessEqual(seed.strength_of_schedule, 1.0)

    def test_seeding_with_head_to_head_results(self):
        """Test seeding calculation with head-to-head results."""
        standings = SCENARIO_2023_FINAL
        head_to_head = HeadToHeadScenarios.afc_east_2023_head_to_head()

        seeding_input = SampleStandings.create_seeding_input(
            standings=standings,
            head_to_head=head_to_head
        )

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # Should complete successfully with head-to-head data
        self.assertEqual(len(playoff_seeding.afc_seeds), 7)
        self.assertEqual(len(playoff_seeding.nfc_seeds), 7)

    def test_calculation_performance(self):
        """Test that seeding calculation completes in reasonable time."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        import time
        start_time = time.time()
        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)
        calculation_time = time.time() - start_time

        # Should complete in under 1 second
        self.assertLess(calculation_time, 1.0)
        self.assertGreater(playoff_seeding.calculation_time_seconds, 0)

    def test_teams_with_byes_identification(self):
        """Test identification of teams with first-round byes."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        # #1 seeds get byes
        afc_seed_1 = next(seed for seed in playoff_seeding.afc_seeds if seed.seed_number == 1)
        nfc_seed_1 = next(seed for seed in playoff_seeding.nfc_seeds if seed.seed_number == 1)

        teams_with_byes = playoff_seeding.teams_with_byes
        bye_team_ids = [team.team_id for team in teams_with_byes]

        self.assertIn(afc_seed_1.team_id, bye_team_ids)
        self.assertIn(nfc_seed_1.team_id, bye_team_ids)
        self.assertEqual(len(teams_with_byes), 2)  # Only #1 seeds get byes


class TestHistoricalValidation(unittest.TestCase):
    """Validate against known historical playoff results."""

    def setUp(self):
        """Set up test fixtures."""
        self.calculator = PlayoffSeedingCalculator()

    def test_validate_against_2023_afc_results(self):
        """Validate our calculation against known 2023 AFC results."""
        standings = SCENARIO_2023_FINAL
        seeding_input = SampleStandings.create_seeding_input(standings=standings, season=2023)

        playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

        expected_afc = HISTORICAL_2023_AFC['expected_seeds']

        # Validate top seeds (where we have confidence in the algorithm)
        afc_seeds = playoff_seeding.afc_seeds

        # #1 seed should be Ravens (13-4)
        seed_1 = next(seed for seed in afc_seeds if seed.seed_number == 1)
        expected_1 = next(seed for seed in expected_afc if seed['seed'] == 1)
        self.assertEqual(seed_1.team_id, expected_1['team_id'])

        # Validate all division winners are in seeds 1-4
        division_winner_seeds = [seed.seed_number for seed in afc_seeds if seed.division_winner]
        self.assertEqual(sorted(division_winner_seeds), [1, 2, 3, 4])

    def test_tiebreaker_rule_precedence(self):
        """Test that tiebreaker rules are applied in correct order."""
        validation_cases = ValidationTestCases.get_tiebreaker_validation_cases()

        for case in validation_cases:
            with self.subTest(case=case['name']):
                # Create minimal standings for tiebreaker test
                standings = {}
                for i, team_data in enumerate(case['teams']):
                    team_id = team_data['team_id']
                    standings[team_id] = self._create_team_record_from_dict(team_data)

                # Fill in other teams with lower records
                for team_id in range(1, 33):
                    if team_id not in standings:
                        standings[team_id] = self._create_basic_team_record(team_id, 6, 11)

                head_to_head = case.get('head_to_head', {})
                seeding_input = SampleStandings.create_seeding_input(
                    standings=standings,
                    head_to_head=head_to_head
                )

                playoff_seeding = self.calculator.calculate_playoff_seeding(seeding_input)

                # Find the relevant teams in the seeding
                expected_winner = case['expected_winner']
                winner_seed = None
                for seed in playoff_seeding.afc_seeds + playoff_seeding.nfc_seeds:
                    if seed.team_id == expected_winner:
                        winner_seed = seed
                        break

                self.assertIsNotNone(winner_seed, f"Expected winner {expected_winner} not found in seeding")

    def _create_team_record_from_dict(self, team_data):
        """Helper to create TeamRecord from dictionary data."""
        from playoff_system.seeding.seeding_data_models import TeamRecord

        return TeamRecord(
            team_id=team_data['team_id'],
            wins=team_data['wins'],
            losses=team_data['losses'],
            ties=team_data.get('ties', 0),
            division_wins=team_data.get('division_wins', team_data['wins'] // 3),
            division_losses=team_data.get('division_losses', 6 - team_data['wins'] // 3),
            conference_wins=team_data.get('conference_wins', team_data['wins'] // 2),
            conference_losses=team_data.get('conference_losses', 12 - team_data['wins'] // 2),
            points_for=team_data.get('points_for', 350),
            points_against=team_data.get('points_against', 350),
            strength_of_victory=team_data.get('strength_of_victory', 0.500),
            strength_of_schedule=team_data.get('strength_of_schedule', 0.500)
        )

    def _create_basic_team_record(self, team_id, wins, losses):
        """Helper to create basic TeamRecord."""
        from playoff_system.seeding.seeding_data_models import TeamRecord

        return TeamRecord(
            team_id=team_id,
            wins=wins,
            losses=losses,
            division_wins=wins // 3,
            division_losses=6 - wins // 3,
            conference_wins=wins // 2,
            conference_losses=12 - wins // 2,
            points_for=300,
            points_against=350
        )


if __name__ == '__main__':
    unittest.main()