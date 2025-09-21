"""
Sample Team Standings for Playoff Testing

Realistic NFL team standings data for testing playoff seeding scenarios.
Includes various tiebreaker scenarios and edge cases.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from playoff_system.seeding.seeding_data_models import TeamRecord, PlayoffSeedingInput
from datetime import datetime


class SampleStandings:
    """Factory for creating sample standings scenarios."""

    @staticmethod
    def create_2023_final_standings() -> dict[int, TeamRecord]:
        """
        Recreate approximate 2023 NFL final standings for realistic testing.
        Based on actual 2023 season results.
        """
        standings = {}

        # AFC East
        standings[1] = TeamRecord(  # Buffalo Bills
            team_id=1, wins=11, losses=6,
            division_wins=4, division_losses=2,
            conference_wins=8, conference_losses=4,
            points_for=452, points_against=388,
            strength_of_victory=0.541, strength_of_schedule=0.515
        )
        standings[2] = TeamRecord(  # Miami Dolphins
            team_id=2, wins=11, losses=6,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=393, points_against=381,
            strength_of_victory=0.518, strength_of_schedule=0.507
        )
        standings[3] = TeamRecord(  # New England Patriots
            team_id=3, wins=4, losses=13,
            division_wins=1, division_losses=5,
            conference_wins=3, conference_losses=9,
            points_for=307, points_against=384,
            strength_of_victory=0.412, strength_of_schedule=0.521
        )
        standings[4] = TeamRecord(  # New York Jets
            team_id=4, wins=7, losses=10,
            division_wins=2, division_losses=4,
            conference_wins=5, conference_losses=7,
            points_for=311, points_against=370,
            strength_of_victory=0.471, strength_of_schedule=0.518
        )

        # AFC North
        standings[5] = TeamRecord(  # Baltimore Ravens
            team_id=5, wins=13, losses=4,
            division_wins=5, division_losses=1,
            conference_wins=10, conference_losses=2,
            points_for=427, points_against=327,
            strength_of_victory=0.485, strength_of_schedule=0.495
        )
        standings[6] = TeamRecord(  # Cincinnati Bengals
            team_id=6, wins=9, losses=8,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=397, points_against=424,
            strength_of_victory=0.544, strength_of_schedule=0.512
        )
        standings[7] = TeamRecord(  # Cleveland Browns
            team_id=7, wins=11, losses=6,
            division_wins=4, division_losses=2,
            conference_wins=8, conference_losses=4,
            points_for=357, points_against=317,
            strength_of_victory=0.500, strength_of_schedule=0.503
        )
        standings[8] = TeamRecord(  # Pittsburgh Steelers
            team_id=8, wins=10, losses=7,
            division_wins=2, division_losses=4,
            conference_wins=7, conference_losses=5,
            points_for=320, points_against=289,
            strength_of_victory=0.529, strength_of_schedule=0.509
        )

        # AFC South
        standings[9] = TeamRecord(  # Houston Texans
            team_id=9, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            points_for=434, points_against=371,
            strength_of_victory=0.456, strength_of_schedule=0.485
        )
        standings[10] = TeamRecord(  # Indianapolis Colts
            team_id=10, wins=9, losses=8,
            division_wins=3, division_losses=3,
            conference_wins=6, conference_losses=6,
            points_for=384, points_against=400,
            strength_of_victory=0.485, strength_of_schedule=0.497
        )
        standings[11] = TeamRecord(  # Jacksonville Jaguars
            team_id=11, wins=9, losses=8,
            division_wins=2, division_losses=4,
            conference_wins=6, conference_losses=6,
            points_for=364, points_against=410,
            strength_of_victory=0.456, strength_of_schedule=0.509
        )
        standings[12] = TeamRecord(  # Tennessee Titans
            team_id=12, wins=6, losses=11,
            division_wins=3, division_losses=3,
            conference_wins=4, conference_losses=8,
            points_for=290, points_against=366,
            strength_of_victory=0.485, strength_of_schedule=0.503
        )

        # AFC West
        standings[13] = TeamRecord(  # Denver Broncos
            team_id=13, wins=8, losses=9,
            division_wins=2, division_losses=4,
            conference_wins=6, conference_losses=6,
            points_for=355, points_against=396,
            strength_of_victory=0.479, strength_of_schedule=0.509
        )
        standings[14] = TeamRecord(  # Kansas City Chiefs
            team_id=14, wins=11, losses=6,
            division_wins=5, division_losses=1,
            conference_wins=8, conference_losses=4,
            points_for=410, points_against=336,
            strength_of_victory=0.485, strength_of_schedule=0.479
        )
        standings[15] = TeamRecord(  # Las Vegas Raiders
            team_id=15, wins=8, losses=9,
            division_wins=3, division_losses=3,
            conference_wins=6, conference_losses=6,
            points_for=325, points_against=344,
            strength_of_victory=0.509, strength_of_schedule=0.500
        )
        standings[16] = TeamRecord(  # Los Angeles Chargers
            team_id=16, wins=5, losses=12,
            division_wins=2, division_losses=4,
            conference_wins=4, conference_losses=8,
            points_for=384, points_against=426,
            strength_of_victory=0.412, strength_of_schedule=0.494
        )

        # NFC East
        standings[17] = TeamRecord(  # Dallas Cowboys
            team_id=17, wins=12, losses=5,
            division_wins=5, division_losses=1,
            conference_wins=9, conference_losses=3,
            points_for=509, points_against=352,
            strength_of_victory=0.456, strength_of_schedule=0.479
        )
        standings[18] = TeamRecord(  # New York Giants
            team_id=18, wins=6, losses=11,
            division_wins=1, division_losses=5,
            conference_wins=4, conference_losses=8,
            points_for=321, points_against=371,
            strength_of_victory=0.500, strength_of_schedule=0.515
        )
        standings[19] = TeamRecord(  # Philadelphia Eagles
            team_id=19, wins=11, losses=6,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=410, points_against=379,
            strength_of_victory=0.529, strength_of_schedule=0.515
        )
        standings[20] = TeamRecord(  # Washington Commanders
            team_id=20, wins=4, losses=13,
            division_wins=1, division_losses=5,
            conference_wins=3, conference_losses=9,
            points_for=312, points_against=454,
            strength_of_victory=0.441, strength_of_schedule=0.518
        )

        # NFC North
        standings[21] = TeamRecord(  # Chicago Bears
            team_id=21, wins=7, losses=10,
            division_wins=2, division_losses=4,
            conference_wins=5, conference_losses=7,
            points_for=334, points_against=392,
            strength_of_victory=0.441, strength_of_schedule=0.509
        )
        standings[22] = TeamRecord(  # Detroit Lions
            team_id=22, wins=12, losses=5,
            division_wins=5, division_losses=1,
            conference_wins=8, conference_losses=4,
            points_for=436, points_against=319,
            strength_of_victory=0.456, strength_of_schedule=0.485
        )
        standings[23] = TeamRecord(  # Green Bay Packers
            team_id=23, wins=9, losses=8,
            division_wins=2, division_losses=4,
            conference_wins=6, conference_losses=6,
            points_for=415, points_against=409,
            strength_of_victory=0.485, strength_of_schedule=0.497
        )
        standings[24] = TeamRecord(  # Minnesota Vikings
            team_id=24, wins=7, losses=10,
            division_wins=3, division_losses=3,
            conference_wins=5, conference_losses=7,
            points_for=344, points_against=364,
            strength_of_victory=0.500, strength_of_schedule=0.506
        )

        # NFC South
        standings[25] = TeamRecord(  # Atlanta Falcons
            team_id=25, wins=7, losses=10,
            division_wins=3, division_losses=3,
            conference_wins=5, conference_losses=7,
            points_for=361, points_against=386,
            strength_of_victory=0.471, strength_of_schedule=0.500
        )
        standings[26] = TeamRecord(  # Carolina Panthers
            team_id=26, wins=2, losses=15,
            division_wins=1, division_losses=5,
            conference_wins=2, conference_losses=10,
            points_for=244, points_against=451,
            strength_of_victory=0.412, strength_of_schedule=0.515
        )
        standings[27] = TeamRecord(  # New Orleans Saints
            team_id=27, wins=9, losses=8,
            division_wins=4, division_losses=2,
            conference_wins=6, conference_losses=6,
            points_for=331, points_against=366,
            strength_of_victory=0.456, strength_of_schedule=0.491
        )
        standings[28] = TeamRecord(  # Tampa Bay Buccaneers
            team_id=28, wins=9, losses=8,
            division_wins=3, division_losses=3,
            conference_wins=6, conference_losses=6,
            points_for=394, points_against=394,
            strength_of_victory=0.485, strength_of_schedule=0.497
        )

        # NFC West
        standings[29] = TeamRecord(  # Arizona Cardinals
            team_id=29, wins=4, losses=13,
            division_wins=2, division_losses=4,
            conference_wins=3, conference_losses=9,
            points_for=314, points_against=400,
            strength_of_victory=0.441, strength_of_schedule=0.500
        )
        standings[30] = TeamRecord(  # Los Angeles Rams
            team_id=30, wins=10, losses=7,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=424, points_against=399,
            strength_of_victory=0.471, strength_of_schedule=0.485
        )
        standings[31] = TeamRecord(  # San Francisco 49ers
            team_id=31, wins=12, losses=5,
            division_wins=5, division_losses=1,
            conference_wins=8, conference_losses=4,
            points_for=456, points_against=298,
            strength_of_victory=0.456, strength_of_schedule=0.471
        )
        standings[32] = TeamRecord(  # Seattle Seahawks
            team_id=32, wins=9, losses=8,
            division_wins=3, division_losses=3,
            conference_wins=6, conference_losses=6,
            points_for=366, points_against=359,
            strength_of_victory=0.500, strength_of_schedule=0.494
        )

        return standings

    @staticmethod
    def create_perfect_tie_scenario() -> dict[int, TeamRecord]:
        """
        Create a scenario where multiple teams are perfectly tied.
        Tests the tiebreaker cascade system.
        """
        standings = {}

        # AFC East - All teams tied at 10-7
        standings[1] = TeamRecord(  # Buffalo Bills
            team_id=1, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            points_for=350, points_against=320,
            strength_of_victory=0.500, strength_of_schedule=0.500
        )
        standings[2] = TeamRecord(  # Miami Dolphins
            team_id=2, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            points_for=350, points_against=320,
            strength_of_victory=0.500, strength_of_schedule=0.500
        )
        standings[3] = TeamRecord(  # New England Patriots
            team_id=3, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            points_for=350, points_against=320,
            strength_of_victory=0.500, strength_of_schedule=0.500
        )
        standings[4] = TeamRecord(  # New York Jets
            team_id=4, wins=10, losses=7,
            division_wins=4, division_losses=2,
            conference_wins=7, conference_losses=5,
            points_for=350, points_against=320,
            strength_of_victory=0.500, strength_of_schedule=0.500
        )

        # Add other divisions with varying records for realism
        # AFC North - Clear hierarchy
        standings[5] = TeamRecord(team_id=5, wins=13, losses=4, division_wins=5, division_losses=1, conference_wins=9, conference_losses=3, points_for=400, points_against=280)
        standings[6] = TeamRecord(team_id=6, wins=9, losses=8, division_wins=3, division_losses=3, conference_wins=6, conference_losses=6, points_for=340, points_against=360)
        standings[7] = TeamRecord(team_id=7, wins=7, losses=10, division_wins=2, division_losses=4, conference_wins=5, conference_losses=7, points_for=310, points_against=380)
        standings[8] = TeamRecord(team_id=8, wins=5, losses=12, division_wins=1, division_losses=5, conference_wins=3, conference_losses=9, points_for=280, points_against=420)

        # Continue with other divisions...
        for team_id in range(9, 33):
            wins = 8 if team_id % 4 == 0 else 6
            losses = 17 - wins
            standings[team_id] = TeamRecord(
                team_id=team_id, wins=wins, losses=losses,
                division_wins=wins//3, division_losses=6-wins//3,
                conference_wins=wins//2, conference_losses=12-wins//2,
                points_for=300 + (team_id % 50), points_against=300 + ((team_id+10) % 50)
            )

        return standings

    @staticmethod
    def create_wildcard_tiebreaker_scenario() -> dict[int, TeamRecord]:
        """
        Create a scenario specifically testing wild card tiebreakers.
        Multiple teams from different divisions competing for wild card spots.
        """
        standings = {}

        # Clear division winners
        standings[1] = TeamRecord(team_id=1, wins=14, losses=3, division_wins=6, division_losses=0, conference_wins=10, conference_losses=2, points_for=450, points_against=250)  # AFC East winner
        standings[5] = TeamRecord(team_id=5, wins=13, losses=4, division_wins=5, division_losses=1, conference_wins=9, conference_losses=3, points_for=420, points_against=280)  # AFC North winner
        standings[9] = TeamRecord(team_id=9, wins=12, losses=5, division_wins=5, division_losses=1, conference_wins=8, conference_losses=4, points_for=400, points_against=300)  # AFC South winner
        standings[14] = TeamRecord(team_id=14, wins=11, losses=6, division_wins=4, division_losses=2, conference_wins=8, conference_losses=4, points_for=380, points_against=320)  # AFC West winner

        # Wild card contenders - all tied at 10-7
        standings[2] = TeamRecord(  # Miami (2nd in AFC East)
            team_id=2, wins=10, losses=7,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=360, points_against=340,
            strength_of_victory=0.520, strength_of_schedule=0.510  # Best SOV
        )
        standings[7] = TeamRecord(  # Cleveland (2nd in AFC North)
            team_id=7, wins=10, losses=7,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=340, points_against=350,
            strength_of_victory=0.480, strength_of_schedule=0.515  # Best SOS
        )
        standings[10] = TeamRecord(  # Indianapolis (2nd in AFC South)
            team_id=10, wins=10, losses=7,
            division_wins=2, division_losses=4,
            conference_wins=6, conference_losses=6,  # Worse conference record
            points_for=370, points_against=330,  # Best point differential
            strength_of_victory=0.500, strength_of_schedule=0.500
        )
        standings[15] = TeamRecord(  # Las Vegas (2nd in AFC West)
            team_id=15, wins=10, losses=7,
            division_wins=3, division_losses=3,
            conference_wins=7, conference_losses=5,
            points_for=320, points_against=360,  # Worst point differential
            strength_of_victory=0.490, strength_of_schedule=0.505
        )

        # Fill in remaining teams with lower records
        for team_id in [3, 4, 6, 8, 11, 12, 13, 16]:
            standings[team_id] = TeamRecord(
                team_id=team_id, wins=6, losses=11,
                division_wins=2, division_losses=4,
                conference_wins=4, conference_losses=8,
                points_for=280, points_against=380
            )

        # NFC teams (simplified)
        for team_id in range(17, 33):
            wins = 9 if team_id % 4 == 1 else 7
            losses = 17 - wins
            standings[team_id] = TeamRecord(
                team_id=team_id, wins=wins, losses=losses,
                division_wins=wins//3, division_losses=6-wins//3,
                conference_wins=wins//2, conference_losses=12-wins//2,
                points_for=320 + (team_id % 40), points_against=320 + ((team_id+5) % 40)
            )

        return standings

    @staticmethod
    def create_seeding_input(standings: dict[int, TeamRecord],
                           dynasty_id: str = "test_dynasty",
                           season: int = 2024,
                           head_to_head: dict = None) -> PlayoffSeedingInput:
        """
        Create a complete PlayoffSeedingInput from standings.

        Args:
            standings: Dictionary of team_id -> TeamRecord
            dynasty_id: Dynasty identifier
            season: Season year
            head_to_head: Head-to-head results (optional)

        Returns:
            PlayoffSeedingInput ready for calculation
        """
        if head_to_head is None:
            head_to_head = {}

        return PlayoffSeedingInput(
            final_standings=standings,
            head_to_head_results=head_to_head,
            dynasty_id=dynasty_id,
            season=season,
            calculation_date=datetime.now()
        )


class HeadToHeadScenarios:
    """Factory for creating head-to-head result scenarios."""

    @staticmethod
    def bills_swept_dolphins() -> dict[tuple, str]:
        """Bills beat Dolphins in both games."""
        return {(1, 2): "2-0"}

    @staticmethod
    def split_series() -> dict[tuple, str]:
        """Teams split their series 1-1."""
        return {(1, 2): "1-1"}

    @staticmethod
    def complex_three_way_tie() -> dict[tuple, str]:
        """
        Three-way circular tie scenario.
        Team 1 beats Team 2, Team 2 beats Team 3, Team 3 beats Team 1.
        """
        return {
            (1, 2): "1-0",  # Team 1 beat Team 2
            (2, 3): "1-0",  # Team 2 beat Team 3
            (3, 1): "1-0"   # Team 3 beat Team 1
        }

    @staticmethod
    def afc_east_2023_head_to_head() -> dict[tuple, str]:
        """
        Realistic AFC East 2023 head-to-head results.
        Based on actual season matchups.
        """
        return {
            (1, 2): "1-1",  # Bills-Dolphins split
            (1, 3): "2-0",  # Bills swept Patriots
            (1, 4): "1-1",  # Bills-Jets split
            (2, 3): "2-0",  # Dolphins swept Patriots
            (2, 4): "1-1",  # Dolphins-Jets split
            (3, 4): "1-1"   # Patriots-Jets split
        }


# Quick access for common scenarios
SCENARIO_2023_FINAL = SampleStandings.create_2023_final_standings()
SCENARIO_PERFECT_TIE = SampleStandings.create_perfect_tie_scenario()
SCENARIO_WILDCARD_TIE = SampleStandings.create_wildcard_tiebreaker_scenario()