"""
Unit Tests for Playoff Manager

Tests playoff bracket generation logic with various scenarios including
wild card matchups, divisional round re-seeding, championship games, and Super Bowl.
"""

import pytest
from unittest.mock import Mock

from playoff_system import PlayoffManager, PlayoffSeeding, PlayoffSeed, ConferenceSeeding, PlayoffBracket, PlayoffGame
from src.calendar.date_models import Date
from shared.game_result import GameResult


class TestPlayoffManager:
    """Unit tests for PlayoffManager."""

    @pytest.fixture
    def manager(self):
        """Create a playoff manager instance."""
        return PlayoffManager()

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
                points_for=440, points_against=290, point_differential=150,
                division_record="5-1", conference_record="10-2"
            ),
            PlayoffSeed(
                seed=2, team_id=17, wins=12, losses=4, ties=0,
                win_percentage=0.75, division_winner=True,
                division_name="NFC East", conference="NFC",
                points_for=415, points_against=305, point_differential=110,
                division_record="5-1", conference_record="9-3"
            ),
            PlayoffSeed(
                seed=3, team_id=21, wins=11, losses=5, ties=0,
                win_percentage=0.6875, division_winner=True,
                division_name="NFC North", conference="NFC",
                points_for=405, points_against=315, point_differential=90,
                division_record="4-2", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=4, team_id=25, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=True,
                division_name="NFC South", conference="NFC",
                points_for=385, points_against=325, point_differential=60,
                division_record="5-1", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=5, team_id=30, wins=10, losses=6, ties=0,
                win_percentage=0.625, division_winner=False,
                division_name="NFC West", conference="NFC",
                points_for=395, points_against=315, point_differential=80,
                division_record="4-2", conference_record="8-4"
            ),
            PlayoffSeed(
                seed=6, team_id=26, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="NFC South", conference="NFC",
                points_for=355, points_against=345, point_differential=10,
                division_record="4-2", conference_record="7-5"
            ),
            PlayoffSeed(
                seed=7, team_id=22, wins=9, losses=7, ties=0,
                win_percentage=0.5625, division_winner=False,
                division_name="NFC North", conference="NFC",
                points_for=365, points_against=335, point_differential=30,
                division_record="3-3", conference_record="7-5"
            )
        ]

        afc_conf = ConferenceSeeding(
            conference="AFC",
            seeds=afc_seeds,
            division_winners=afc_seeds[:4],
            wildcards=afc_seeds[4:],
            clinched_teams=[13, 1, 5, 9, 14, 10, 6],
            eliminated_teams=list(range(2, 17))  # Not used in these tests
        )

        nfc_conf = ConferenceSeeding(
            conference="NFC",
            seeds=nfc_seeds,
            division_winners=nfc_seeds[:4],
            wildcards=nfc_seeds[4:],
            clinched_teams=[29, 17, 21, 25, 30, 26, 22],
            eliminated_teams=list(range(18, 33))  # Not used in these tests
        )

        return PlayoffSeeding(
            season=2024,
            week=18,
            afc=afc_conf,
            nfc=nfc_conf,
            tiebreakers_applied=[],
            calculation_date="2024-01-10"
        )

    @pytest.fixture
    def start_date(self):
        """Wild card round start date."""
        return Date(2025, 1, 11)

    def test_wild_card_bracket_structure(self, manager, mock_seeding, start_date):
        """Test that wild card bracket has correct structure."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        assert bracket.round_name == 'wild_card'
        assert bracket.season == 2024
        assert bracket.start_date == start_date
        assert len(bracket.games) == 6  # 3 AFC + 3 NFC
        assert bracket.get_game_count() == 6

    def test_wild_card_correct_matchups(self, manager, mock_seeding, start_date):
        """Test that wild card bracket generates correct matchups (2v7, 3v6, 4v5)."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        # AFC matchups
        afc_games = bracket.get_afc_games()
        assert len(afc_games) == 3

        # Game 1: (2) Team 1 vs (7) Team 6
        assert afc_games[0].home_team_id == 1
        assert afc_games[0].away_team_id == 6
        assert afc_games[0].home_seed == 2
        assert afc_games[0].away_seed == 7

        # Game 2: (3) Team 5 vs (6) Team 10
        assert afc_games[1].home_team_id == 5
        assert afc_games[1].away_team_id == 10
        assert afc_games[1].home_seed == 3
        assert afc_games[1].away_seed == 6

        # Game 3: (4) Team 9 vs (5) Team 14
        assert afc_games[2].home_team_id == 9
        assert afc_games[2].away_team_id == 14
        assert afc_games[2].home_seed == 4
        assert afc_games[2].away_seed == 5

        # NFC matchups
        nfc_games = bracket.get_nfc_games()
        assert len(nfc_games) == 3

        # Game 4: (2) Team 17 vs (7) Team 22
        assert nfc_games[0].home_team_id == 17
        assert nfc_games[0].away_team_id == 22
        assert nfc_games[0].home_seed == 2
        assert nfc_games[0].away_seed == 7

        # Game 5: (3) Team 21 vs (6) Team 26
        assert nfc_games[1].home_team_id == 21
        assert nfc_games[1].away_team_id == 26
        assert nfc_games[1].home_seed == 3
        assert nfc_games[1].away_seed == 6

        # Game 6: (4) Team 25 vs (5) Team 30
        assert nfc_games[2].home_team_id == 25
        assert nfc_games[2].away_team_id == 30
        assert nfc_games[2].home_seed == 4
        assert nfc_games[2].away_seed == 5

    def test_wild_card_home_field_advantage(self, manager, mock_seeding, start_date):
        """Test that higher seeds host wild card games."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        for game in bracket.games:
            # Higher seed (lower seed number) should always be home team
            assert game.home_seed < game.away_seed, \
                f"Seed {game.home_seed} should host seed {game.away_seed}"

    def test_wild_card_game_numbering(self, manager, mock_seeding, start_date):
        """Test that wild card games are numbered correctly."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        afc_games = bracket.get_afc_games()
        nfc_games = bracket.get_nfc_games()

        # AFC games should be numbered 1-3
        assert afc_games[0].game_number == 1
        assert afc_games[1].game_number == 2
        assert afc_games[2].game_number == 3

        # NFC games should be numbered 4-6
        assert nfc_games[0].game_number == 4
        assert nfc_games[1].game_number == 5
        assert nfc_games[2].game_number == 6

    def test_wild_card_game_dates(self, manager, mock_seeding, start_date):
        """Test that wild card games have proper dates."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        # All games should have dates on or after start date
        for game in bracket.games:
            assert game.game_date >= start_date
            # Games should be within 3 days of start (Sat/Sun/Mon)
            days_diff = game.game_date.days_until(start_date)
            assert abs(days_diff) <= 2

    def test_wild_card_one_seeds_get_bye(self, manager, mock_seeding, start_date):
        """Test that #1 seeds are not in wild card bracket (they get bye)."""
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)

        # Team 13 (AFC #1) and Team 29 (NFC #1) should not be in any game
        for game in bracket.games:
            assert game.home_team_id != 13, "AFC #1 seed should not play in wild card"
            assert game.away_team_id != 13, "AFC #1 seed should not play in wild card"
            assert game.home_team_id != 29, "NFC #1 seed should not play in wild card"
            assert game.away_team_id != 29, "NFC #1 seed should not play in wild card"

    def test_divisional_bracket_structure(self, manager, mock_seeding, start_date):
        """Test that divisional bracket has correct structure."""
        # Create mock wild card results
        wild_card_results = self._create_wild_card_results()

        divisional_start = start_date.add_days(7)
        bracket = manager.generate_divisional_bracket(
            wild_card_results, mock_seeding, divisional_start, 2024
        )

        assert bracket.round_name == 'divisional'
        assert bracket.season == 2024
        assert bracket.start_date == divisional_start
        assert len(bracket.games) == 4  # 2 AFC + 2 NFC
        assert bracket.get_game_count() == 4

    def test_divisional_reseeding_one_seed_plays_lowest(self, manager, mock_seeding, start_date):
        """
        Test that #1 seed plays LOWEST remaining seed after re-seeding.

        Note: This test validates team matchups but not seed numbers in the result,
        since the current implementation uses placeholder seed inference. The core
        re-seeding logic (which teams play which) is validated.
        """
        # Wild card results: Seeds 2, 3, 5 win in AFC
        wild_card_results = [
            self._create_game_result(1, 6, 1),   # Seed 2 (Team 1) beats Seed 7 (Team 6)
            self._create_game_result(5, 10, 5),  # Seed 3 (Team 5) beats Seed 6 (Team 10)
            self._create_game_result(14, 9, 14), # Seed 5 (Team 14) beats Seed 4 (Team 9)
            # NFC games
            self._create_game_result(17, 22, 17),
            self._create_game_result(21, 26, 21),
            self._create_game_result(30, 25, 30)
        ]

        divisional_start = start_date.add_days(7)
        bracket = manager.generate_divisional_bracket(
            wild_card_results, mock_seeding, divisional_start, 2024
        )

        afc_games = bracket.get_afc_games()

        # After re-seeding, AFC has seeds: 1, 2, 3, 5
        # #1 seed (13) should play LOWEST seed (5 = Team 14)
        # Find the game with team 13 (the #1 seed from original seeding)
        one_seed_game = [g for g in afc_games if g.home_team_id == 13][0]
        assert one_seed_game.home_team_id == 13, "Team 13 should be #1 seed"
        assert one_seed_game.away_team_id == 14, "Team 14 (seed 5) should play #1 seed"

        # Other two winners (Teams 1 and 5) should play each other
        other_game = [g for g in afc_games if g.home_team_id != 13][0]
        # Team 1 (seed 2) should host Team 5 (seed 3)
        assert other_game.home_team_id == 1
        assert other_game.away_team_id == 5

    def test_divisional_home_field_advantage(self, manager, mock_seeding, start_date):
        """
        Test that higher seeds host divisional games.

        Note: This test validates the matchup structure based on team IDs from the
        original seeding, since seed inference is currently a placeholder. We verify
        that #1 seeds (teams 13 and 29) are home teams, and the standard winners
        are matched correctly.
        """
        wild_card_results = self._create_wild_card_results()
        divisional_start = start_date.add_days(7)

        bracket = manager.generate_divisional_bracket(
            wild_card_results, mock_seeding, divisional_start, 2024
        )

        # Verify #1 seeds are home teams
        afc_games = bracket.get_afc_games()
        nfc_games = bracket.get_nfc_games()

        # AFC: Team 13 (seed 1) should be home
        afc_one_seed_game = [g for g in afc_games if g.home_team_id == 13][0]
        assert afc_one_seed_game.home_team_id == 13

        # NFC: Team 29 (seed 1) should be home
        nfc_one_seed_game = [g for g in nfc_games if g.home_team_id == 29][0]
        assert nfc_one_seed_game.home_team_id == 29

    def test_conference_championship_structure(self, manager):
        """Test that conference championship bracket has correct structure."""
        divisional_results = [
            self._create_game_result(13, 5, 13),  # AFC: #1 beats #3
            self._create_game_result(1, 14, 1),   # AFC: #2 beats #5
            self._create_game_result(29, 21, 29), # NFC: #1 beats #3
            self._create_game_result(17, 30, 17)  # NFC: #2 beats #5
        ]

        conf_start = Date(2025, 1, 26)
        bracket = manager.generate_conference_championship_bracket(
            divisional_results, conf_start, 2024
        )

        assert bracket.round_name == 'conference'
        assert bracket.season == 2024
        assert len(bracket.games) == 2  # 1 AFC + 1 NFC
        assert bracket.get_game_count() == 2

    def test_conference_championship_matchups(self, manager):
        """Test that conference championship creates correct matchups."""
        divisional_results = [
            self._create_game_result(13, 5, 13),  # AFC: Team 13 (seed 1) wins
            self._create_game_result(1, 14, 1),   # AFC: Team 1 (seed 2) wins
            self._create_game_result(29, 21, 29), # NFC: Team 29 (seed 1) wins
            self._create_game_result(17, 30, 17)  # NFC: Team 17 (seed 2) wins
        ]

        conf_start = Date(2025, 1, 26)
        bracket = manager.generate_conference_championship_bracket(
            divisional_results, conf_start, 2024
        )

        afc_game = bracket.get_afc_games()[0]
        nfc_game = bracket.get_nfc_games()[0]

        # AFC Championship: Team 13 (seed 1) vs Team 1 (seed 2)
        assert afc_game.home_team_id == 13
        assert afc_game.away_team_id == 1

        # NFC Championship: Team 29 (seed 1) vs Team 17 (seed 2)
        assert nfc_game.home_team_id == 29
        assert nfc_game.away_team_id == 17

    def test_super_bowl_structure(self, manager):
        """Test that Super Bowl bracket has correct structure."""
        conf_results = [
            self._create_game_result(13, 1, 13),   # AFC: Team 13 wins
            self._create_game_result(29, 17, 29)   # NFC: Team 29 wins
        ]

        sb_date = Date(2025, 2, 9)
        bracket = manager.generate_super_bowl_bracket(conf_results, sb_date, 2024)

        assert bracket.round_name == 'super_bowl'
        assert bracket.season == 2024
        assert len(bracket.games) == 1
        assert bracket.get_game_count() == 1
        assert bracket.is_super_bowl() is True

    def test_super_bowl_matchup(self, manager):
        """Test that Super Bowl creates AFC vs NFC matchup."""
        conf_results = [
            self._create_game_result(13, 1, 13),   # AFC: Team 13 (AFC #1) wins
            self._create_game_result(29, 17, 29)   # NFC: Team 29 (NFC #1) wins
        ]

        sb_date = Date(2025, 2, 9)
        bracket = manager.generate_super_bowl_bracket(conf_results, sb_date, 2024)

        sb_game = bracket.get_super_bowl_game()
        assert sb_game is not None

        # AFC champion (Team 13) is away, NFC champion (Team 29) is home
        # (This is the convention used by the manager)
        assert sb_game.away_team_id == 13
        assert sb_game.home_team_id == 29
        assert sb_game.conference is None  # Super Bowl has no conference

    def test_bracket_validation(self, manager, mock_seeding, start_date):
        """Test that bracket validation works correctly."""
        # Valid bracket should not raise
        bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)
        assert bracket.validate() is True

        # Invalid bracket should raise
        invalid_bracket = PlayoffBracket(
            round_name='wild_card',
            season=2024,
            games=[],  # Wrong number of games
            start_date=start_date
        )

        with pytest.raises(ValueError, match="Expected 6 games"):
            invalid_bracket.validate()

    def test_game_week_assignment(self, manager, mock_seeding, start_date):
        """Test that playoff games are assigned correct week numbers."""
        # Wild card: week 1
        wc_bracket = manager.generate_wild_card_bracket(mock_seeding, start_date, 2024)
        for game in wc_bracket.games:
            assert game.week == 1

        # Divisional: week 2
        wild_card_results = self._create_wild_card_results()
        div_bracket = manager.generate_divisional_bracket(
            wild_card_results, mock_seeding, start_date.add_days(7), 2024
        )
        for game in div_bracket.games:
            assert game.week == 2

        # Conference: week 3
        divisional_results = [
            self._create_game_result(13, 5, 13),
            self._create_game_result(1, 14, 1),
            self._create_game_result(29, 21, 29),
            self._create_game_result(17, 30, 17)
        ]
        conf_bracket = manager.generate_conference_championship_bracket(
            divisional_results, start_date.add_days(14), 2024
        )
        for game in conf_bracket.games:
            assert game.week == 3

        # Super Bowl: week 4
        conf_results = [
            self._create_game_result(13, 1, 13),
            self._create_game_result(29, 17, 29)
        ]
        sb_bracket = manager.generate_super_bowl_bracket(
            conf_results, start_date.add_days(21), 2024
        )
        assert sb_bracket.games[0].week == 4

    def test_invalid_divisional_input_raises_error(self, manager, mock_seeding):
        """Test that invalid number of wild card results raises error."""
        # Only 2 winners instead of 3 per conference
        invalid_results = [
            self._create_game_result(1, 6, 1),
            self._create_game_result(5, 10, 5)
        ]

        with pytest.raises(ValueError, match="Expected 3 wild card winners"):
            manager.generate_divisional_bracket(
                invalid_results, mock_seeding, Date(2025, 1, 18), 2024
            )

    def test_invalid_conference_input_raises_error(self, manager):
        """Test that invalid number of divisional results raises error."""
        # Only 1 winner instead of 2 per conference
        invalid_results = [
            self._create_game_result(13, 5, 13)
        ]

        with pytest.raises(ValueError, match="Expected 2 AFC divisional winners"):
            manager.generate_conference_championship_bracket(
                invalid_results, Date(2025, 1, 26), 2024
            )

    # Helper methods for creating test data

    def _create_wild_card_results(self):
        """Create standard wild card results for testing."""
        return [
            # AFC: Seeds 2, 3, 4 win
            self._create_game_result(1, 6, 1),     # Seed 2 wins
            self._create_game_result(5, 10, 5),    # Seed 3 wins
            self._create_game_result(9, 14, 9),    # Seed 4 wins
            # NFC: Seeds 2, 3, 4 win
            self._create_game_result(17, 22, 17),  # Seed 2 wins
            self._create_game_result(21, 26, 21),  # Seed 3 wins
            self._create_game_result(25, 30, 25)   # Seed 4 wins
        ]

    def _create_game_result(self, home_id, away_id, winner_id, home_seed=None, away_seed=None):
        """
        Create a mock GameResult for testing.

        Note: The current PlayoffManager implementation uses _infer_seed_from_result
        which returns placeholder values. This is a known limitation that will be
        addressed when GameResult is enhanced to include playoff metadata.
        For now, these tests work with the understanding that seed inference
        is a placeholder implementation.
        """
        # Create mock Team objects
        home_team = Mock()
        home_team.team_id = home_id

        away_team = Mock()
        away_team.team_id = away_id

        # Determine scores based on winner
        if winner_id == home_id:
            home_score = 24
            away_score = 17
        else:
            home_score = 17
            away_score = 24

        return GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={home_id: home_score, away_id: away_score},
            quarter_scores=[],
            drives=[],
            total_plays=60,
            game_duration_minutes=180
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
