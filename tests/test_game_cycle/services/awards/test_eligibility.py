"""
Tests for award eligibility checking.

Part of Milestone 10: Awards System, Tollgate 2.
Target: 25 tests covering games played, position filtering, rookie detection, CPOY criteria.
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
import json

from src.game_cycle.services.awards.eligibility import (
    EligibilityChecker,
    MINIMUM_GAMES,
    MINIMUM_SNAPS,
    FULL_SEASON_GAMES,
)
from src.game_cycle.services.awards.models import (
    AwardType,
    PlayerCandidate,
    EligibilityResult,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
)


class TestGamesPlayedEligibility:
    """Tests for minimum games played requirement (12 games)."""

    def test_minimum_games_met(self, db_path, dynasty_id, season):
        """Player with 17 games should be eligible."""
        # Insert player with 17 games
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 1, 'Patrick', 'Mahomes', 15, 1, '["QB"]', 7)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 1, 1, 'QB', 95.0, 1100)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        # Mock stats_api to return 17 games
        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(1, AwardType.MVP)

        assert result.is_eligible is True
        assert result.games_played == 17
        assert 'games' not in ' '.join(result.reasons).lower()

    def test_minimum_games_not_met(self, db_path, dynasty_id, season):
        """Player with 8 games should be ineligible."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 2, 'Injured', 'Player', 10, 1, '["WR"]', 3)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 2, 1, 'WR', 78.0, 400)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 8}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(2, AwardType.MVP)

        assert result.is_eligible is False
        assert result.games_played == 8
        assert any('games' in r.lower() for r in result.reasons)

    def test_exactly_12_games_eligible(self, db_path, dynasty_id, season):
        """Player with exactly 12 games should be eligible (boundary case)."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 3, 'Boundary', 'Player', 20, 2, '["RB"]', 5)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 3, 2, 'RB', 85.0, 600)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 12}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(3, AwardType.MVP)

        assert result.is_eligible is True
        assert result.games_played == 12

    def test_11_games_ineligible(self, db_path, dynasty_id, season):
        """Player with 11 games should be ineligible (just below minimum)."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 4, 'Almost', 'Eligible', 25, 3, '["TE"]', 4)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 4, 3, 'TE', 82.0, 550)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 11}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(4, AwardType.MVP)

        assert result.is_eligible is False
        assert result.games_played == 11


class TestPositionEligibility:
    """Tests for position-based eligibility filtering."""

    def test_offensive_player_eligible_for_opoy(self, db_path, dynasty_id, season):
        """QB should be eligible for OPOY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 10, 'Josh', 'Allen', 17, 4, '["QB"]', 6)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 10, 4, 'QB', 92.0, 1050)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(10, AwardType.OPOY)

        assert result.is_eligible is True
        assert result.position_group == 'offense'

    def test_defensive_player_ineligible_for_opoy(self, db_path, dynasty_id, season):
        """EDGE rusher should be ineligible for OPOY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 11, 'Myles', 'Garrett', 95, 5, '["EDGE"]', 7)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 11, 5, 'EDGE', 94.0, 850)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(11, AwardType.OPOY)

        assert result.is_eligible is False
        assert 'not eligible for opoy' in ' '.join(result.reasons).lower()
        assert result.position_group == 'defense'

    def test_defensive_player_eligible_for_dpoy(self, db_path, dynasty_id, season):
        """CB should be eligible for DPOY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 12, 'Sauce', 'Gardner', 1, 6, '["CB"]', 2)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 12, 6, 'CB', 90.0, 900)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(12, AwardType.DPOY)

        assert result.is_eligible is True
        assert result.position_group == 'defense'

    def test_offensive_player_ineligible_for_dpoy(self, db_path, dynasty_id, season):
        """RB should be ineligible for DPOY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 13, 'Derrick', 'Henry', 22, 7, '["RB"]', 8)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 13, 7, 'RB', 92.0, 800)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(13, AwardType.DPOY)

        assert result.is_eligible is False
        assert 'not eligible for dpoy' in ' '.join(result.reasons).lower()

    def test_mvp_open_to_all_positions(self, db_path, dynasty_id, season):
        """MVP should be open to both offensive and defensive players."""
        conn = sqlite3.connect(db_path)
        # Insert defensive player
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 14, 'Micah', 'Parsons', 11, 8, '["EDGE"]', 3)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 14, 8, 'EDGE', 93.0, 870)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(14, AwardType.MVP)

        # Defensive player should be eligible for MVP
        assert result.is_eligible is True
        assert 'position' not in ' '.join(result.reasons).lower()


class TestRookieEligibility:
    """Tests for rookie detection and ROY eligibility."""

    def test_rookie_detection_years_pro_zero(self, db_path, dynasty_id, season):
        """Player with years_pro=0 should be detected as rookie."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 20, 'Caleb', 'Williams', 18, 9, '["QB"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 20, 9, 'QB', 82.0, 1000)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(20, AwardType.OROY)

        assert result.is_rookie is True
        assert result.is_eligible is True

    def test_rookie_eligible_for_oroy(self, db_path, dynasty_id, season):
        """Offensive rookie should be eligible for OROY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 21, 'Marvin', 'Harrison Jr', 84, 10, '["WR"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 21, 10, 'WR', 85.0, 750)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 16}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(21, AwardType.OROY)

        assert result.is_eligible is True
        assert result.is_rookie is True
        assert result.position_group == 'offense'

    def test_non_rookie_ineligible_for_oroy(self, db_path, dynasty_id, season):
        """Non-rookie should be ineligible for OROY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 22, 'Veteran', 'WR', 88, 11, '["WR"]', 5)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 22, 11, 'WR', 88.0, 800)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(22, AwardType.OROY)

        assert result.is_eligible is False
        assert result.is_rookie is False
        assert 'not a rookie' in ' '.join(result.reasons).lower()

    def test_defensive_rookie_eligible_for_droy(self, db_path, dynasty_id, season):
        """Defensive rookie should be eligible for DROY."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 23, 'Quinyon', 'Mitchell', 27, 12, '["CB"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 23, 12, 'CB', 85.0, 900)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(23, AwardType.DROY)

        assert result.is_eligible is True
        assert result.is_rookie is True
        assert result.position_group == 'defense'


class TestCPOYEligibility:
    """Tests for Comeback Player of the Year eligibility."""

    def test_cpoy_injury_comeback(self, db_path, dynasty_id, season):
        """Player who missed 10 games last season should be CPOY eligible."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 30, 'Joe', 'Burrow', 9, 13, '["QB"]', 5)
        )
        # Current season grade
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 30, 13, 'QB', 90.0, 1050, 17)
        )
        # Previous season grade (missed 10 games)
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season - 1, 30, 13, 'QB', 72.0, 400, 8)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(30, AwardType.CPOY)

        assert result.is_eligible is True

    def test_cpoy_performance_comeback(self, db_path, dynasty_id, season):
        """Player who improved grade by 10+ points should be CPOY eligible."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 31, 'Geno', 'Smith', 7, 14, '["QB"]', 10)
        )
        # Current season grade (big improvement)
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 31, 14, 'QB', 85.0, 1000, 17)
        )
        # Previous season grade (lower)
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season - 1, 31, 14, 'QB', 70.0, 950, 17)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(31, AwardType.CPOY)

        assert result.is_eligible is True

    def test_cpoy_rookie_ineligible(self, db_path, dynasty_id, season):
        """Rookies should be ineligible for CPOY (no previous season)."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 32, 'Rookie', 'QB', 5, 15, '["QB"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 32, 15, 'QB', 80.0, 950, 17)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(32, AwardType.CPOY)

        assert result.is_eligible is False
        assert 'rookie' in ' '.join(result.reasons).lower()

    def test_cpoy_no_comeback_narrative_ineligible(self, db_path, dynasty_id, season):
        """Player with steady performance (no comeback) should be ineligible."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 33, 'Steady', 'Eddie', 44, 16, '["RB"]', 6)
        )
        # Current season grade
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 33, 16, 'RB', 82.0, 700, 17)
        )
        # Previous season grade (nearly identical, played full season)
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season - 1, 33, 16, 'RB', 80.0, 720, 17)  # Only 2 point improvement, 1 game missed
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(33, AwardType.CPOY)

        assert result.is_eligible is False
        assert 'comeback narrative' in ' '.join(result.reasons).lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_player_not_found(self, db_path, dynasty_id, season):
        """Checking nonexistent player should return ineligible."""
        checker = EligibilityChecker(db_path, dynasty_id, season)

        result = checker.check_eligibility(99999, AwardType.MVP)

        assert result.is_eligible is False
        assert result.player_name == "Unknown"
        assert 'player not found' in ' '.join(result.reasons).lower()

    def test_missing_stats_data(self, db_path, dynasty_id, season):
        """Player with no stats should be handled gracefully."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 40, 'No', 'Stats', 99, 17, '["WR"]', 2)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 40, 17, 'WR', 75.0, 500)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = None  # No stats
            checker._stats_api = mock_stats

            result = checker.check_eligibility(40, AwardType.MVP)

        # Should be ineligible due to 0 games played
        assert result.is_eligible is False
        assert result.games_played == 0

    def test_multiple_positions_uses_primary(self, db_path, dynasty_id, season):
        """Player with multiple positions should use first position."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 41, 'Multi', 'Position', 12, 18, '["TE", "FB"]', 4)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 41, 18, 'TE', 78.0, 600)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 16}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(41, AwardType.OPOY)

        assert result.is_eligible is True
        assert result.position_group == 'offense'

    def test_unknown_position_defaults_to_offense(self, db_path, dynasty_id, season):
        """Unknown position should default to offense group."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 42, 'Unknown', 'Position', 50, 19, '["XXX"]', 3)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 42, 19, 'XXX', 70.0, 400)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 14}
            checker._stats_api = mock_stats

            result = checker.check_eligibility(42, AwardType.MVP)

        # Unknown position defaults to offense
        assert result.position_group == 'offense'


class TestGetEligibleCandidates:
    """Tests for get_eligible_candidates method."""

    def test_get_mvp_candidates_returns_eligible_players(self, db_path, dynasty_id, season):
        """get_eligible_candidates should return only eligible players."""
        conn = sqlite3.connect(db_path)
        # Eligible player 1
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 50, 'Eligible', 'One', 1, 20, '["QB"]', 5)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 50, 20, 'QB', 92.0, 1000, 17)
        )
        # Eligible player 2
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 51, 'Eligible', 'Two', 2, 21, '["RB"]', 3)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 51, 21, 'RB', 88.0, 700, 16)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            # Mock to return 17 games for player 50, 16 for player 51
            def get_stats(player_id, season):
                if player_id == '50':
                    return {'games_played': 17, 'passing_yards': 4500}
                elif player_id == '51':
                    return {'games_played': 16, 'rushing_yards': 1500}
                return {'games_played': 0}
            mock_stats.get_player_season_stats.side_effect = get_stats
            checker._stats_api = mock_stats

            # Mock standings
            with patch.object(checker, '_standings_api') as mock_standings:
                mock_standing = Mock()
                mock_standing.wins = 12
                mock_standing.losses = 5
                mock_standing.ties = 0
                mock_standing.playoff_seed = 2
                mock_standing.division_wins = 5
                mock_standing.conference_wins = 10
                mock_standings.get_team_standing.return_value = mock_standing
                checker._standings_api = mock_standings

                candidates = checker.get_eligible_candidates(AwardType.MVP)

        assert len(candidates) == 2
        assert all(isinstance(c, PlayerCandidate) for c in candidates)
        # Should be sorted by overall_grade descending
        assert candidates[0].overall_grade >= candidates[1].overall_grade

    def test_get_oroy_candidates_filters_rookies(self, db_path, dynasty_id, season):
        """OROY candidates should only include offensive rookies."""
        conn = sqlite3.connect(db_path)
        # Rookie QB
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 60, 'Rookie', 'QB', 7, 22, '["QB"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 60, 22, 'QB', 82.0, 950, 16)
        )
        # Veteran WR (should be excluded)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 61, 'Veteran', 'WR', 81, 23, '["WR"]', 6)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 61, 23, 'WR', 90.0, 800, 17)
        )
        # Rookie CB (should be excluded - defensive)
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 62, 'Rookie', 'CB', 28, 24, '["CB"]', 0)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 62, 24, 'CB', 85.0, 850, 17)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 16}
            checker._stats_api = mock_stats

            with patch.object(checker, '_standings_api') as mock_standings:
                mock_standing = Mock()
                mock_standing.wins = 10
                mock_standing.losses = 7
                mock_standing.ties = 0
                mock_standing.playoff_seed = 5
                mock_standing.division_wins = 3
                mock_standing.conference_wins = 8
                mock_standings.get_team_standing.return_value = mock_standing
                checker._standings_api = mock_standings

                candidates = checker.get_eligible_candidates(AwardType.OROY)

        # Should only return the rookie QB
        assert len(candidates) == 1
        assert candidates[0].player_id == 60
        assert candidates[0].is_rookie is True
        assert candidates[0].position_group == 'offense'

    def test_empty_candidates_when_no_grades(self, db_path, dynasty_id, season):
        """Should return empty list when no season grades exist."""
        checker = EligibilityChecker(db_path, dynasty_id, season)

        candidates = checker.get_eligible_candidates(AwardType.MVP)

        assert candidates == []

    def test_candidates_sorted_by_grade(self, db_path, dynasty_id, season):
        """Candidates should be sorted by overall_grade descending."""
        conn = sqlite3.connect(db_path)
        # Player with lower grade
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 70, 'Lower', 'Grade', 70, 25, '["QB"]', 4)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 70, 25, 'QB', 75.0, 950, 17)
        )
        # Player with higher grade
        conn.execute(
            """INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, years_pro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, 71, 'Higher', 'Grade', 71, 26, '["QB"]', 6)
        )
        conn.execute(
            """INSERT INTO player_season_grades (dynasty_id, season, player_id, team_id, position, overall_grade, total_snaps, games_graded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, season, 71, 26, 'QB', 95.0, 1050, 17)
        )
        conn.commit()
        conn.close()

        checker = EligibilityChecker(db_path, dynasty_id, season)

        with patch.object(checker, '_stats_api') as mock_stats:
            mock_stats.get_player_season_stats.return_value = {'games_played': 17}
            checker._stats_api = mock_stats

            with patch.object(checker, '_standings_api') as mock_standings:
                mock_standing = Mock()
                mock_standing.wins = 11
                mock_standing.losses = 6
                mock_standing.ties = 0
                mock_standing.playoff_seed = 3
                mock_standing.division_wins = 4
                mock_standing.conference_wins = 9
                mock_standings.get_team_standing.return_value = mock_standing
                checker._standings_api = mock_standings

                candidates = checker.get_eligible_candidates(AwardType.MVP)

        # Higher grade should be first
        assert candidates[0].player_id == 71
        assert candidates[0].overall_grade == 95.0
        assert candidates[1].player_id == 70
        assert candidates[1].overall_grade == 75.0
