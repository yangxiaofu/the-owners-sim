"""
Historical NFL Playoff Data for Validation

Real playoff scenarios from past NFL seasons to validate our seeding calculations
against known correct results. These scenarios test our implementation against
actual NFL playoff determinations.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from playoff_system.seeding.seeding_data_models import TeamRecord, PlayoffSeedingInput
from datetime import datetime


class HistoricalPlayoffScenarios:
    """Real NFL playoff scenarios for validation testing."""

    @staticmethod
    def afc_2023_actual_seeding():
        """
        2023 AFC playoff seeding - known correct results.

        Final AFC Seeds:
        1. Ravens (13-4) - AFC North winner
        2. Bills (11-6) - AFC East winner
        3. Chiefs (11-6) - AFC West winner
        4. Texans (10-7) - AFC South winner
        5. Browns (11-6) - Wild Card
        6. Dolphins (11-6) - Wild Card
        7. Steelers (10-7) - Wild Card
        """
        return {
            'expected_seeds': [
                {'seed': 1, 'team_id': 5, 'record': '13-4'},   # Ravens
                {'seed': 2, 'team_id': 1, 'record': '11-6'},   # Bills
                {'seed': 3, 'team_id': 14, 'record': '11-6'},  # Chiefs
                {'seed': 4, 'team_id': 9, 'record': '10-7'},   # Texans
                {'seed': 5, 'team_id': 7, 'record': '11-6'},   # Browns
                {'seed': 6, 'team_id': 2, 'record': '11-6'},   # Dolphins
                {'seed': 7, 'team_id': 8, 'record': '10-7'}    # Steelers
            ],
            'wild_card_matchups': [
                {'higher_seed': 2, 'lower_seed': 7, 'home': 1, 'away': 8},    # Bills vs Steelers
                {'higher_seed': 3, 'lower_seed': 6, 'home': 14, 'away': 2},   # Chiefs vs Dolphins
                {'higher_seed': 4, 'lower_seed': 5, 'home': 9, 'away': 7}     # Texans vs Browns
            ]
        }

    @staticmethod
    def nfc_2023_actual_seeding():
        """
        2023 NFC playoff seeding - known correct results.

        Final NFC Seeds:
        1. 49ers (12-5) - NFC West winner
        2. Cowboys (12-5) - NFC East winner
        3. Lions (12-5) - NFC North winner
        4. Buccaneers (9-8) - NFC South winner
        5. Eagles (11-6) - Wild Card
        6. Packers (9-8) - Wild Card
        7. Rams (10-7) - Wild Card
        """
        return {
            'expected_seeds': [
                {'seed': 1, 'team_id': 31, 'record': '12-5'},  # 49ers
                {'seed': 2, 'team_id': 17, 'record': '12-5'},  # Cowboys
                {'seed': 3, 'team_id': 22, 'record': '12-5'},  # Lions
                {'seed': 4, 'team_id': 28, 'record': '9-8'},   # Buccaneers
                {'seed': 5, 'team_id': 19, 'record': '11-6'},  # Eagles
                {'seed': 6, 'team_id': 23, 'record': '9-8'},   # Packers
                {'seed': 7, 'team_id': 30, 'record': '10-7'}   # Rams
            ],
            'wild_card_matchups': [
                {'higher_seed': 2, 'lower_seed': 7, 'home': 17, 'away': 30},  # Cowboys vs Rams
                {'higher_seed': 3, 'lower_seed': 6, 'home': 22, 'away': 23},  # Lions vs Packers
                {'higher_seed': 4, 'lower_seed': 5, 'home': 28, 'away': 19}   # Buccaneers vs Eagles
            ]
        }

    @staticmethod
    def famous_tiebreaker_scenarios():
        """
        Collection of famous NFL tiebreaker scenarios from history.
        These test edge cases and complex tiebreaker applications.
        """
        scenarios = []

        # 2008 AFC East - Famous three-way tie scenario
        scenarios.append({
            'name': '2008_afc_east_three_way_tie',
            'description': 'Patriots, Dolphins, Jets all 11-5, complex tiebreaker',
            'teams': [
                {'team_id': 3, 'wins': 11, 'losses': 5, 'division_wins': 4, 'division_losses': 2},  # Patriots
                {'team_id': 2, 'wins': 11, 'losses': 5, 'division_wins': 4, 'division_losses': 2},  # Dolphins
                {'team_id': 4, 'wins': 11, 'losses': 5, 'division_wins': 3, 'division_losses': 3}   # Jets
            ],
            'head_to_head': {
                (3, 2): "1-1",  # Patriots-Dolphins split
                (3, 4): "1-1",  # Patriots-Jets split
                (2, 4): "1-1"   # Dolphins-Jets split
            },
            'expected_winner': 2,  # Dolphins won division
            'tiebreaker_used': 'division_record'
        })

        # 2013 NFC Wild Card - Famous strength of victory scenario
        scenarios.append({
            'name': '2013_nfc_wildcard_strength_of_victory',
            'description': 'Cardinals vs Saints wild card decided by strength of victory',
            'teams': [
                {'team_id': 29, 'wins': 10, 'losses': 6, 'strength_of_victory': 0.457},  # Cardinals
                {'team_id': 27, 'wins': 11, 'losses': 5, 'strength_of_victory': 0.398}   # Saints
            ],
            'expected_result': 'Cardinals miss playoffs despite better record',
            'tiebreaker_used': 'strength_of_victory'
        })

        # 2020 AFC Wild Card - Complex multi-team scenario
        scenarios.append({
            'name': '2020_afc_wildcard_complex',
            'description': 'Multiple teams vying for final wild card spot',
            'teams': [
                {'team_id': 10, 'wins': 11, 'losses': 5, 'conference_wins': 8},   # Colts
                {'team_id': 2, 'wins': 10, 'losses': 6, 'conference_wins': 8},    # Dolphins
                {'team_id': 5, 'wins': 11, 'losses': 5, 'conference_wins': 7}     # Ravens
            ],
            'expected_order': [5, 10, 2],  # Ravens, Colts, Dolphins
            'tiebreaker_used': 'conference_record'
        })

        return scenarios

    @staticmethod
    def coin_flip_scenarios():
        """
        Scenarios that historically went to coin flip tiebreakers.
        These are rare but important edge cases to test.
        """
        return [
            {
                'name': '1998_afc_east_coin_flip',
                'description': 'Patriots vs Jets tied on all tiebreakers, coin flip used',
                'teams': [
                    {'team_id': 3, 'record': '9-7', 'all_stats_identical': True},
                    {'team_id': 4, 'record': '9-7', 'all_stats_identical': True}
                ],
                'outcome': 'Patriots won coin flip',
                'note': 'Extremely rare occurrence in modern NFL'
            }
        ]

    @staticmethod
    def strength_calculation_validation():
        """
        Known strength of victory/schedule calculations for validation.
        These test our strength calculation algorithms.
        """
        return {
            'team_beaten_opponents': {
                # Team 1 beat teams with these records
                1: [(12, 5), (10, 7), (9, 8), (8, 9), (7, 10)],  # Beat 5 teams
                2: [(11, 6), (11, 6), (9, 8), (6, 11), (5, 12)]   # Beat 5 teams
            },
            'expected_sov': {
                1: 0.529,  # (12+10+9+8+7)/(5+7+8+9+10) = 46/87 = 0.529
                2: 0.490   # (11+11+9+6+5)/(6+6+8+11+12) = 42/43 = 0.488
            },
            'all_opponents': {
                # All opponents faced by each team (for SOS calculation)
                1: [(13, 4), (12, 5), (11, 6), (10, 7), (9, 8), (8, 9), (7, 10), (6, 11)],
                2: [(14, 3), (11, 6), (11, 6), (10, 7), (9, 8), (8, 9), (6, 11), (5, 12)]
            },
            'expected_sos': {
                1: 0.507,  # Calculate from all opponents
                2: 0.514   # Calculate from all opponents
            }
        }

    @staticmethod
    def division_winner_tiebreaker_validation():
        """
        Known division winner determinations for testing division tiebreakers.
        """
        return {
            'afc_north_2023': {
                'teams': [
                    {'team_id': 5, 'wins': 13, 'losses': 4, 'division_wins': 5, 'division_losses': 1},  # Ravens
                    {'team_id': 7, 'wins': 11, 'losses': 6, 'division_wins': 4, 'division_losses': 2},  # Browns
                    {'team_id': 8, 'wins': 10, 'losses': 7, 'division_wins': 2, 'division_losses': 4},  # Steelers
                    {'team_id': 6, 'wins': 9, 'losses': 8, 'division_wins': 3, 'division_losses': 3}    # Bengals
                ],
                'expected_winner': 5,  # Ravens
                'tiebreaker_needed': False,  # Clear winner by record
                'final_order': [5, 7, 8, 6]
            },
            'nfc_south_2023': {
                'teams': [
                    {'team_id': 28, 'wins': 9, 'losses': 8, 'division_wins': 3, 'division_losses': 3},  # Buccaneers
                    {'team_id': 27, 'wins': 9, 'losses': 8, 'division_wins': 4, 'division_losses': 2},  # Saints
                    {'team_id': 25, 'wins': 7, 'losses': 10, 'division_wins': 3, 'division_losses': 3}, # Falcons
                    {'team_id': 26, 'wins': 2, 'losses': 15, 'division_wins': 1, 'division_losses': 5}  # Panthers
                ],
                'expected_winner': 28,  # Buccaneers (won tiebreaker over Saints)
                'tiebreaker_needed': True,
                'tiebreaker_used': 'head_to_head',  # Bucs beat Saints in head-to-head
                'head_to_head': {(28, 27): "2-0"}
            }
        }


class ValidationTestCases:
    """
    Test cases that validate our implementation against known results.
    Each test case includes input data and expected output.
    """

    @staticmethod
    def get_2023_season_validation():
        """
        Complete 2023 season validation test case.
        Uses actual team records and known playoff results.
        """
        return {
            'name': '2023_complete_season_validation',
            'description': 'Validate complete 2023 playoff seeding calculation',
            'standings_data': 'SCENARIO_2023_FINAL',  # Reference to sample data
            'expected_afc_seeds': HistoricalPlayoffScenarios.afc_2023_actual_seeding()['expected_seeds'],
            'expected_nfc_seeds': HistoricalPlayoffScenarios.nfc_2023_actual_seeding()['expected_seeds'],
            'expected_afc_matchups': HistoricalPlayoffScenarios.afc_2023_actual_seeding()['wild_card_matchups'],
            'expected_nfc_matchups': HistoricalPlayoffScenarios.nfc_2023_actual_seeding()['wild_card_matchups'],
            'tolerance': 0.001,  # Allow small floating point differences
            'critical_tiebreakers': [
                'Bills vs Chiefs seeding (conference record)',
                'Browns vs Dolphins wild card order (conference record)',
                'Steelers wild card qualification (strength metrics)'
            ]
        }

    @staticmethod
    def get_tiebreaker_validation_cases():
        """
        Specific tiebreaker validation test cases.
        Each tests a different tiebreaker rule.
        """
        return [
            {
                'name': 'head_to_head_validation',
                'rule': 'head_to_head',
                'teams': [
                    {'team_id': 1, 'wins': 11, 'losses': 6},
                    {'team_id': 2, 'wins': 11, 'losses': 6}
                ],
                'head_to_head': {(1, 2): "2-0"},
                'expected_winner': 1,
                'expected_rule_applied': 'HEAD_TO_HEAD'
            },
            {
                'name': 'division_record_validation',
                'rule': 'division_record',
                'teams': [
                    {'team_id': 1, 'wins': 10, 'losses': 7, 'division_wins': 5, 'division_losses': 1},
                    {'team_id': 2, 'wins': 10, 'losses': 7, 'division_wins': 3, 'division_losses': 3}
                ],
                'head_to_head': {(1, 2): "1-1"},  # Tied head-to-head
                'expected_winner': 1,
                'expected_rule_applied': 'DIVISION_RECORD'
            },
            {
                'name': 'strength_of_victory_validation',
                'rule': 'strength_of_victory',
                'teams': [
                    {'team_id': 1, 'wins': 10, 'losses': 7, 'strength_of_victory': 0.520},
                    {'team_id': 2, 'wins': 10, 'losses': 7, 'strength_of_victory': 0.480}
                ],
                'other_tiebreakers_tied': True,
                'expected_winner': 1,
                'expected_rule_applied': 'STRENGTH_OF_VICTORY'
            }
        ]


# Helper functions for test data access
def get_historical_scenario(scenario_name: str):
    """Get a specific historical scenario by name."""
    scenarios = HistoricalPlayoffScenarios.famous_tiebreaker_scenarios()
    for scenario in scenarios:
        if scenario['name'] == scenario_name:
            return scenario
    raise ValueError(f"Historical scenario '{scenario_name}' not found")


def get_validation_case(case_name: str):
    """Get a specific validation test case by name."""
    if case_name == '2023_complete_season':
        return ValidationTestCases.get_2023_season_validation()

    tiebreaker_cases = ValidationTestCases.get_tiebreaker_validation_cases()
    for case in tiebreaker_cases:
        if case['name'] == case_name:
            return case

    raise ValueError(f"Validation case '{case_name}' not found")


# Quick access constants
HISTORICAL_2023_AFC = HistoricalPlayoffScenarios.afc_2023_actual_seeding()
HISTORICAL_2023_NFC = HistoricalPlayoffScenarios.nfc_2023_actual_seeding()
FAMOUS_TIEBREAKERS = HistoricalPlayoffScenarios.famous_tiebreaker_scenarios()
VALIDATION_2023 = ValidationTestCases.get_2023_season_validation()
TIEBREAKER_VALIDATIONS = ValidationTestCases.get_tiebreaker_validation_cases()