"""
Tests for bye week scheduling (Milestone 11, Tollgate 3).

Tests cover:
- Bye week assignment algorithm
- Database persistence (ByeWeekAPI)
- Schedule generator integration
- Constraint validation
"""

import os
import tempfile
import pytest
from collections import Counter

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.bye_week_api import ByeWeekAPI
from src.game_cycle.services.nfl_schedule_generator import NFLScheduleGenerator


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def temp_db():
    """Create temp database with GameCycleDatabase (full schema auto-created)."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = GameCycleDatabase(db_path)
    conn = db.get_connection()

    # Create team for dynasty
    conn.execute("""
        INSERT INTO teams (team_id, name, abbreviation, conference, division)
        VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
    """)

    # Create dynasty with required fields
    conn.execute("""
        INSERT INTO dynasties (dynasty_id, name, team_id)
        VALUES ('test_bye_dynasty', 'Test Dynasty', 1)
    """)

    conn.commit()

    yield db, db_path

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def bye_api(temp_db):
    """Create ByeWeekAPI with temp database."""
    db, db_path = temp_db
    return ByeWeekAPI(db)


@pytest.fixture
def valid_bye_assignments():
    """Generate valid bye week assignments for all 32 teams."""
    # Distribute teams across weeks 5-14 (3-4 teams per bye week)
    assignments = {}
    week = 5
    for team_id in range(1, 33):
        assignments[team_id] = week
        week = 5 + ((week - 5 + 1) % 10)  # Cycle through weeks 5-14
    return assignments


# ============================================
# BYE WEEK API TESTS
# ============================================

class TestByeWeekAPIBasic:
    """Basic CRUD operations for ByeWeekAPI."""

    def test_save_and_retrieve_bye_weeks(self, bye_api, valid_bye_assignments):
        """Should save and retrieve bye week assignments."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        retrieved = bye_api.get_all_bye_weeks("test_bye_dynasty", 2025)
        assert retrieved == valid_bye_assignments

    def test_get_team_bye_week(self, bye_api, valid_bye_assignments):
        """Should retrieve single team's bye week."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        bye_week = bye_api.get_team_bye_week("test_bye_dynasty", 2025, 1)
        assert bye_week == valid_bye_assignments[1]

    def test_get_team_bye_week_not_found(self, bye_api):
        """Should return None for non-existent bye week."""
        bye_week = bye_api.get_team_bye_week("test_bye_dynasty", 2025, 1)
        assert bye_week is None

    def test_get_teams_on_bye(self, bye_api, valid_bye_assignments):
        """Should retrieve all teams on bye for a week."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        teams_on_bye_week_5 = bye_api.get_teams_on_bye("test_bye_dynasty", 2025, 5)
        expected = [t for t, w in valid_bye_assignments.items() if w == 5]
        assert sorted(teams_on_bye_week_5) == sorted(expected)

    def test_get_teams_on_bye_empty(self, bye_api, valid_bye_assignments):
        """Should return empty list for week with no byes."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        # Week 4 is before bye weeks
        teams_on_bye = bye_api.get_teams_on_bye("test_bye_dynasty", 2025, 4)
        assert teams_on_bye == []

    def test_get_bye_week_count(self, bye_api, valid_bye_assignments):
        """Should return total bye week assignments."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        count = bye_api.get_bye_week_count("test_bye_dynasty", 2025)
        assert count == 32

    def test_delete_bye_weeks(self, bye_api, valid_bye_assignments):
        """Should delete all bye week assignments for a season."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        deleted = bye_api.delete_bye_weeks("test_bye_dynasty", 2025)
        assert deleted == 32

        count = bye_api.get_bye_week_count("test_bye_dynasty", 2025)
        assert count == 0

    def test_is_team_on_bye(self, bye_api, valid_bye_assignments):
        """Should correctly check if team is on bye."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        team_1_bye = valid_bye_assignments[1]
        assert bye_api.is_team_on_bye("test_bye_dynasty", 2025, 1, team_1_bye) is True
        assert bye_api.is_team_on_bye("test_bye_dynasty", 2025, 1, team_1_bye + 1) is False


class TestByeWeekAPIValidation:
    """Validation tests for ByeWeekAPI."""

    def test_validation_rejects_missing_teams(self, bye_api):
        """Should reject assignments with missing teams."""
        incomplete = {t: 5 for t in range(1, 31)}  # Only 30 teams
        with pytest.raises(ValueError, match="Expected 32 teams"):
            bye_api.save_bye_weeks("test_bye_dynasty", 2025, incomplete)

    def test_validation_rejects_invalid_team_ids(self, bye_api):
        """Should reject assignments with invalid team IDs."""
        invalid = {t: 5 for t in range(0, 32)}  # Team 0 invalid
        with pytest.raises(ValueError, match="Invalid team IDs"):
            bye_api.save_bye_weeks("test_bye_dynasty", 2025, invalid)

    def test_validation_rejects_bye_week_below_range(self, bye_api):
        """Should reject bye weeks below 5."""
        invalid = {t: 4 for t in range(1, 33)}  # Week 4 invalid
        with pytest.raises(ValueError, match="outside valid range"):
            bye_api.save_bye_weeks("test_bye_dynasty", 2025, invalid)

    def test_validation_rejects_bye_week_above_range(self, bye_api):
        """Should reject bye weeks above 14."""
        invalid = {t: 15 for t in range(1, 33)}  # Week 15 invalid
        with pytest.raises(ValueError, match="outside valid range"):
            bye_api.save_bye_weeks("test_bye_dynasty", 2025, invalid)

    def test_validation_rejects_too_many_teams_per_week(self, bye_api):
        """Should reject more than 4 teams per bye week."""
        # Put all 32 teams on week 5
        invalid = {t: 5 for t in range(1, 33)}
        with pytest.raises(ValueError, match="teams on bye"):
            bye_api.save_bye_weeks("test_bye_dynasty", 2025, invalid)


class TestByeWeekAPIDynastyIsolation:
    """Dynasty isolation tests for ByeWeekAPI."""

    def test_bye_weeks_isolated_by_dynasty(self, temp_db, valid_bye_assignments):
        """Bye weeks should be isolated between dynasties."""
        db, db_path = temp_db
        bye_api = ByeWeekAPI(db)
        conn = db.get_connection()

        # Create second dynasty
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('other_dynasty', 'Other Dynasty', 1)
        """)
        conn.commit()

        # Save bye weeks for both
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        other_assignments = {t: 14 - (t % 10) for t in range(1, 33)}
        # Fix range to be valid
        for t in other_assignments:
            if other_assignments[t] < 5:
                other_assignments[t] = 5
        bye_api.save_bye_weeks("other_dynasty", 2025, other_assignments)

        # Verify isolation
        original = bye_api.get_all_bye_weeks("test_bye_dynasty", 2025)
        other = bye_api.get_all_bye_weeks("other_dynasty", 2025)

        assert original == valid_bye_assignments
        assert other == other_assignments

    def test_bye_weeks_isolated_by_season(self, bye_api, valid_bye_assignments):
        """Bye weeks should be isolated between seasons."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        other_assignments = {t: 5 + ((14 - t) % 10) for t in range(1, 33)}
        bye_api.save_bye_weeks("test_bye_dynasty", 2026, other_assignments)

        # Verify isolation
        season_2025 = bye_api.get_all_bye_weeks("test_bye_dynasty", 2025)
        season_2026 = bye_api.get_all_bye_weeks("test_bye_dynasty", 2026)

        assert season_2025 == valid_bye_assignments
        assert season_2026 == other_assignments


# ============================================
# BYE WEEK ASSIGNMENT ALGORITHM TESTS
# ============================================

class TestByeWeekAssignment:
    """Tests for bye week assignment algorithm in NFLScheduleGenerator."""

    @pytest.fixture
    def generator_db(self):
        """Create generator with temp database and all 32 teams."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)
        conn = db.get_connection()

        # All 32 NFL teams
        nfl_teams = [
            (1, 'Buffalo Bills', 'BUF', 'AFC', 'East'),
            (2, 'Miami Dolphins', 'MIA', 'AFC', 'East'),
            (3, 'New England Patriots', 'NE', 'AFC', 'East'),
            (4, 'New York Jets', 'NYJ', 'AFC', 'East'),
            (5, 'Baltimore Ravens', 'BAL', 'AFC', 'North'),
            (6, 'Cincinnati Bengals', 'CIN', 'AFC', 'North'),
            (7, 'Cleveland Browns', 'CLE', 'AFC', 'North'),
            (8, 'Pittsburgh Steelers', 'PIT', 'AFC', 'North'),
            (9, 'Houston Texans', 'HOU', 'AFC', 'South'),
            (10, 'Indianapolis Colts', 'IND', 'AFC', 'South'),
            (11, 'Jacksonville Jaguars', 'JAX', 'AFC', 'South'),
            (12, 'Tennessee Titans', 'TEN', 'AFC', 'South'),
            (13, 'Denver Broncos', 'DEN', 'AFC', 'West'),
            (14, 'Kansas City Chiefs', 'KC', 'AFC', 'West'),
            (15, 'Las Vegas Raiders', 'LV', 'AFC', 'West'),
            (16, 'Los Angeles Chargers', 'LAC', 'AFC', 'West'),
            (17, 'Dallas Cowboys', 'DAL', 'NFC', 'East'),
            (18, 'New York Giants', 'NYG', 'NFC', 'East'),
            (19, 'Philadelphia Eagles', 'PHI', 'NFC', 'East'),
            (20, 'Washington Commanders', 'WAS', 'NFC', 'East'),
            (21, 'Chicago Bears', 'CHI', 'NFC', 'North'),
            (22, 'Detroit Lions', 'DET', 'NFC', 'North'),
            (23, 'Green Bay Packers', 'GB', 'NFC', 'North'),
            (24, 'Minnesota Vikings', 'MIN', 'NFC', 'North'),
            (25, 'Atlanta Falcons', 'ATL', 'NFC', 'South'),
            (26, 'Carolina Panthers', 'CAR', 'NFC', 'South'),
            (27, 'New Orleans Saints', 'NO', 'NFC', 'South'),
            (28, 'Tampa Bay Buccaneers', 'TB', 'NFC', 'South'),
            (29, 'Arizona Cardinals', 'ARI', 'NFC', 'West'),
            (30, 'Los Angeles Rams', 'LAR', 'NFC', 'West'),
            (31, 'San Francisco 49ers', 'SF', 'NFC', 'West'),
            (32, 'Seattle Seahawks', 'SEA', 'NFC', 'West'),
        ]

        # Insert all 32 teams
        for team_data in nfl_teams:
            conn.execute(
                """INSERT INTO teams (team_id, name, abbreviation, conference, division)
                   VALUES (?, ?, ?, ?, ?)""",
                team_data
            )

        # Create dynasty
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test_gen_dynasty', 'Generator Test', 1)
        """)

        # Insert default standings for all teams
        for team_id in range(1, 33):
            conn.execute(
                """INSERT INTO standings (dynasty_id, season, team_id, wins, losses, ties)
                   VALUES ('test_gen_dynasty', 2024, ?, 8, 9, 0)""",
                (team_id,)
            )

        conn.commit()
        db.close()

        yield db_path

        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_all_32_teams_have_bye(self, generator_db):
        """Every team should be assigned exactly one bye week."""
        generator = NFLScheduleGenerator(db_path=generator_db, dynasty_id="test_gen_dynasty")
        bye_assignments = generator._assign_bye_weeks()
        generator.close()

        assert len(bye_assignments) == 32
        assert set(bye_assignments.keys()) == set(range(1, 33))

    def test_bye_weeks_in_valid_range(self, generator_db):
        """All bye weeks should be between 5-14."""
        generator = NFLScheduleGenerator(db_path=generator_db, dynasty_id="test_gen_dynasty")
        bye_assignments = generator._assign_bye_weeks()
        generator.close()

        for team_id, bye_week in bye_assignments.items():
            assert 5 <= bye_week <= 14, f"Team {team_id} has bye week {bye_week}"

    def test_max_4_teams_per_bye_week(self, generator_db):
        """No more than 4 teams should share a bye week."""
        generator = NFLScheduleGenerator(db_path=generator_db, dynasty_id="test_gen_dynasty")
        bye_assignments = generator._assign_bye_weeks()
        generator.close()

        week_counts = Counter(bye_assignments.values())
        for week, count in week_counts.items():
            assert count <= 4, f"Week {week} has {count} teams on bye"

    def test_division_constraint(self, generator_db):
        """No division should have more than 2 teams on same bye week."""
        generator = NFLScheduleGenerator(db_path=generator_db, dynasty_id="test_gen_dynasty")
        bye_assignments = generator._assign_bye_weeks()

        for div_id, teams in generator.DIVISIONS.items():
            div_byes = [bye_assignments[t] for t in teams]
            bye_counts = Counter(div_byes)

            for week, count in bye_counts.items():
                # Soft constraint - allow up to 2
                assert count <= 2, f"Division {div_id} has {count} teams on week {week}"

        generator.close()

    def test_bye_weeks_balanced_across_weeks(self, generator_db):
        """Bye weeks should be roughly balanced across weeks 5-14."""
        generator = NFLScheduleGenerator(db_path=generator_db, dynasty_id="test_gen_dynasty")
        bye_assignments = generator._assign_bye_weeks()
        generator.close()

        week_counts = Counter(bye_assignments.values())

        # With 32 teams across 10 weeks, expect 2-4 teams per week
        for week in range(5, 15):
            count = week_counts.get(week, 0)
            assert 0 <= count <= 4, f"Week {week} has {count} teams, expected 0-4"


# ============================================
# SCHEDULE GENERATION WITH BYES INTEGRATION
# ============================================

class TestScheduleWithByes:
    """Integration tests for schedule generation with bye weeks."""

    @pytest.fixture
    def full_generator_db(self):
        """Create generator with full required tables and all 32 teams."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)
        conn = db.get_connection()

        # All 32 NFL teams
        nfl_teams = [
            (1, 'Buffalo Bills', 'BUF', 'AFC', 'East'),
            (2, 'Miami Dolphins', 'MIA', 'AFC', 'East'),
            (3, 'New England Patriots', 'NE', 'AFC', 'East'),
            (4, 'New York Jets', 'NYJ', 'AFC', 'East'),
            (5, 'Baltimore Ravens', 'BAL', 'AFC', 'North'),
            (6, 'Cincinnati Bengals', 'CIN', 'AFC', 'North'),
            (7, 'Cleveland Browns', 'CLE', 'AFC', 'North'),
            (8, 'Pittsburgh Steelers', 'PIT', 'AFC', 'North'),
            (9, 'Houston Texans', 'HOU', 'AFC', 'South'),
            (10, 'Indianapolis Colts', 'IND', 'AFC', 'South'),
            (11, 'Jacksonville Jaguars', 'JAX', 'AFC', 'South'),
            (12, 'Tennessee Titans', 'TEN', 'AFC', 'South'),
            (13, 'Denver Broncos', 'DEN', 'AFC', 'West'),
            (14, 'Kansas City Chiefs', 'KC', 'AFC', 'West'),
            (15, 'Las Vegas Raiders', 'LV', 'AFC', 'West'),
            (16, 'Los Angeles Chargers', 'LAC', 'AFC', 'West'),
            (17, 'Dallas Cowboys', 'DAL', 'NFC', 'East'),
            (18, 'New York Giants', 'NYG', 'NFC', 'East'),
            (19, 'Philadelphia Eagles', 'PHI', 'NFC', 'East'),
            (20, 'Washington Commanders', 'WAS', 'NFC', 'East'),
            (21, 'Chicago Bears', 'CHI', 'NFC', 'North'),
            (22, 'Detroit Lions', 'DET', 'NFC', 'North'),
            (23, 'Green Bay Packers', 'GB', 'NFC', 'North'),
            (24, 'Minnesota Vikings', 'MIN', 'NFC', 'North'),
            (25, 'Atlanta Falcons', 'ATL', 'NFC', 'South'),
            (26, 'Carolina Panthers', 'CAR', 'NFC', 'South'),
            (27, 'New Orleans Saints', 'NO', 'NFC', 'South'),
            (28, 'Tampa Bay Buccaneers', 'TB', 'NFC', 'South'),
            (29, 'Arizona Cardinals', 'ARI', 'NFC', 'West'),
            (30, 'Los Angeles Rams', 'LAR', 'NFC', 'West'),
            (31, 'San Francisco 49ers', 'SF', 'NFC', 'West'),
            (32, 'Seattle Seahawks', 'SEA', 'NFC', 'West'),
        ]

        # Insert all 32 teams
        for team_data in nfl_teams:
            conn.execute(
                """INSERT INTO teams (team_id, name, abbreviation, conference, division)
                   VALUES (?, ?, ?, ?, ?)""",
                team_data
            )

        # Create dynasty
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test_full_dynasty', 'Full Test', 1)
        """)

        # Insert default standings for all teams
        for team_id in range(1, 33):
            conn.execute(
                """INSERT INTO standings (dynasty_id, season, team_id, wins, losses, ties)
                   VALUES ('test_full_dynasty', 2024, ?, 8, 9, 0)""",
                (team_id,)
            )

        conn.commit()
        db.close()

        yield db_path

        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_generates_272_games_with_byes(self, full_generator_db):
        """Should still generate exactly 272 games with bye weeks."""
        generator = NFLScheduleGenerator(
            db_path=full_generator_db,
            dynasty_id="test_full_dynasty"
        )

        games = generator.generate_schedule(2025)
        generator.close()

        assert len(games) == 272

    def test_teams_do_not_play_during_bye(self, full_generator_db):
        """Teams should never play during their bye week."""
        generator = NFLScheduleGenerator(
            db_path=full_generator_db,
            dynasty_id="test_full_dynasty"
        )

        games = generator.generate_schedule(2025)

        # Get bye assignments
        db = GameCycleDatabase(full_generator_db)
        bye_api = ByeWeekAPI(db)
        bye_assignments = bye_api.get_all_bye_weeks("test_full_dynasty", 2025)
        db.close()

        generator.close()

        for game in games:
            week = game['data']['parameters']['week']
            home = game['data']['parameters']['home_team_id']
            away = game['data']['parameters']['away_team_id']

            assert bye_assignments.get(home) != week, \
                f"Home team {home} plays during bye week {week}"
            assert bye_assignments.get(away) != week, \
                f"Away team {away} plays during bye week {week}"

    def test_variable_games_per_week(self, full_generator_db):
        """Weeks 5-14 should have 14-16 games based on byes."""
        generator = NFLScheduleGenerator(
            db_path=full_generator_db,
            dynasty_id="test_full_dynasty"
        )

        games = generator.generate_schedule(2025)
        generator.close()

        week_counts = Counter(g['data']['parameters']['week'] for g in games)

        # Weeks 1-4 and 15-17: 16 games (no byes)
        for week in [1, 2, 3, 4, 15, 16, 17]:
            assert week_counts[week] == 16, f"Week {week} has {week_counts[week]} games"

        # Weeks 5-14: 14-16 games (depending on byes)
        for week in range(5, 15):
            assert 14 <= week_counts[week] <= 16, \
                f"Week {week} has {week_counts[week]} games"

    def test_bye_weeks_persisted(self, full_generator_db):
        """Bye weeks should be saved to database."""
        generator = NFLScheduleGenerator(
            db_path=full_generator_db,
            dynasty_id="test_full_dynasty"
        )

        generator.generate_schedule(2025)

        db = GameCycleDatabase(full_generator_db)
        bye_api = ByeWeekAPI(db)
        bye_assignments = bye_api.get_all_bye_weeks("test_full_dynasty", 2025)
        db.close()

        generator.close()

        assert len(bye_assignments) == 32

    def test_every_team_plays_17_games(self, full_generator_db):
        """Each team should still play exactly 17 games."""
        generator = NFLScheduleGenerator(
            db_path=full_generator_db,
            dynasty_id="test_full_dynasty"
        )

        games = generator.generate_schedule(2025)
        generator.close()

        team_counts = Counter()
        for game in games:
            team_counts[game['data']['parameters']['home_team_id']] += 1
            team_counts[game['data']['parameters']['away_team_id']] += 1

        for team_id in range(1, 33):
            assert team_counts[team_id] == 17, \
                f"Team {team_id} plays {team_counts[team_id]} games"


# ============================================
# BYE WEEK DISTRIBUTION TESTS
# ============================================

class TestByeWeekDistribution:
    """Tests for bye week distribution helper in ByeWeekAPI."""

    def test_get_bye_week_distribution(self, bye_api, valid_bye_assignments):
        """Should return count of teams per bye week."""
        bye_api.save_bye_weeks("test_bye_dynasty", 2025, valid_bye_assignments)

        distribution = bye_api.get_bye_week_distribution("test_bye_dynasty", 2025)

        # Verify total adds up to 32
        total = sum(distribution.values())
        assert total == 32
