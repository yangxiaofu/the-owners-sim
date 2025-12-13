"""
Integration tests for TeamAttractivenessService and TeamHistoryAPI.

Tests history tracking, contender score calculation, season recording,
and TeamAttractiveness object building.
Part of Tollgate 4: Team Attractiveness Service.
"""
import os
import tempfile

import pytest

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.team_history_api import TeamHistoryAPI, SeasonHistoryRecord
from src.game_cycle.services.team_attractiveness_service import TeamAttractivenessService


class TestTeamHistoryAPI:
    """Tests for TeamHistoryAPI CRUD operations."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        # Create teams and dynasty for FK constraints
        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'AFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield db, conn

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_record_and_get_season(self, temp_db):
        """Can record and retrieve a season record."""
        db, _ = temp_db
        api = TeamHistoryAPI(db)

        record = SeasonHistoryRecord(
            team_id=10,
            season=2024,
            wins=12,
            losses=5,
            made_playoffs=True,
            playoff_round_reached="divisional",
            won_super_bowl=False,
        )
        result = api.record_season("test_dynasty", record)
        assert result is True

        retrieved = api.get_season_record("test_dynasty", 10, 2024)
        assert retrieved is not None
        assert retrieved.team_id == 10
        assert retrieved.wins == 12
        assert retrieved.losses == 5
        assert retrieved.made_playoffs is True
        assert retrieved.playoff_round_reached == "divisional"
        assert retrieved.won_super_bowl is False

    def test_get_team_history_returns_most_recent(self, temp_db):
        """History returns most recent seasons first, limited to N years."""
        db, _ = temp_db
        api = TeamHistoryAPI(db)

        # Insert 6 seasons
        for year in range(2019, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=10 + (year - 2019),  # 10, 11, 12, 13, 14, 15
                losses=7 - (year - 2019),
            )
            api.record_season("test_dynasty", record)

        # Get last 5 years
        history = api.get_team_history("test_dynasty", 10, years=5)
        assert len(history) == 5

        # Most recent first
        assert history[0].season == 2024
        assert history[0].wins == 15
        assert history[4].season == 2020
        assert history[4].wins == 11

        # 2019 should be excluded (6th year)
        seasons = [h.season for h in history]
        assert 2019 not in seasons

    def test_dynasty_isolation(self, temp_db):
        """History is isolated by dynasty."""
        db, conn = temp_db
        api = TeamHistoryAPI(db)

        # Create second dynasty
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('other_dynasty', 10, 'Other Dynasty')
        """
        )
        conn.commit()

        # Insert same team/season in different dynasties
        record1 = SeasonHistoryRecord(team_id=10, season=2024, wins=12, losses=5)
        record2 = SeasonHistoryRecord(team_id=10, season=2024, wins=4, losses=13)

        api.record_season("test_dynasty", record1)
        api.record_season("other_dynasty", record2)

        # Verify isolation
        h1 = api.get_season_record("test_dynasty", 10, 2024)
        h2 = api.get_season_record("other_dynasty", 10, 2024)

        assert h1.wins == 12
        assert h2.wins == 4

    def test_get_all_teams_for_season(self, temp_db):
        """Can get all team records for a season."""
        db, _ = temp_db
        api = TeamHistoryAPI(db)

        # Insert records for 5 teams
        for team_id in [1, 5, 10, 20, 32]:
            record = SeasonHistoryRecord(
                team_id=team_id,
                season=2024,
                wins=10,
                losses=7,
            )
            api.record_season("test_dynasty", record)

        teams = api.get_all_teams_for_season("test_dynasty", 2024)
        assert len(teams) == 5
        team_ids = [t.team_id for t in teams]
        assert 1 in team_ids
        assert 32 in team_ids


class TestContenderScore:
    """Tests for contender score calculation."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'AFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield db

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_no_history_returns_default(self, temp_db):
        """New dynasty with no history returns 50 contender score."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        score = service.calculate_contender_score(team_id=10)
        assert score == 50

    def test_super_bowl_winner_high_score(self, temp_db):
        """Team with 2 SB wins in 5 years gets high score."""
        api = TeamHistoryAPI(temp_db)

        # Insert 5 seasons with 2 Super Bowl wins
        for i, year in enumerate(range(2020, 2025)):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=14,
                losses=3,
                made_playoffs=True,
                playoff_round_reached="super_bowl",
                won_super_bowl=(year in [2022, 2024]),  # 2 championships
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        score = service.calculate_contender_score(team_id=10)

        # High score expected: 40% current (14-3 = 82%), 30% playoffs (100%),
        # 20% SB (100%), 10% culture (~82%)
        assert score >= 85

    def test_perennial_loser_low_score(self, temp_db):
        """Team with 5 years of losing records gets low score."""
        api = TeamHistoryAPI(temp_db)

        # Insert 5 losing seasons
        for year in range(2020, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=4,
                losses=13,
                made_playoffs=False,
                playoff_round_reached=None,
                won_super_bowl=False,
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        score = service.calculate_contender_score(team_id=10)

        # Low score expected: 40% current (4-13 = 23.5%), 30% playoffs (0%),
        # 20% SB (0%), 10% culture (~23.5%)
        assert score <= 25

    def test_5_year_window_drops_oldest(self, temp_db):
        """6th season drops oldest from calculation."""
        api = TeamHistoryAPI(temp_db)

        # Insert 6 seasons - oldest year was championship, recent are losing
        record_old = SeasonHistoryRecord(
            team_id=10,
            season=2019,
            wins=14,
            losses=3,
            made_playoffs=True,
            playoff_round_reached="super_bowl",
            won_super_bowl=True,
        )
        api.record_season("test_dynasty", record_old)

        # Recent 5 years are losing seasons
        for year in range(2020, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=4,
                losses=13,
                made_playoffs=False,
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        score = service.calculate_contender_score(team_id=10)

        # 2019 championship should be excluded from 5-year window
        # Score should be low (based on 2020-2024 losing seasons only)
        assert score <= 25


class TestSeasonRecording:
    """Tests for recording season results from standings and playoffs."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with standings and playoff data."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        # Create teams
        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'AFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )

        # Create dynasty
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )

        # Insert standings for all 32 teams (season 2024)
        for team_id in range(1, 33):
            wins = 17 - ((team_id - 1) % 14)  # Varying win totals
            losses = 17 - wins
            playoff_seed = team_id if team_id <= 14 else None

            conn.execute(
                """
                INSERT INTO standings
                (dynasty_id, season, team_id, wins, losses, ties,
                 points_for, points_against, division_wins, division_losses,
                 conference_wins, conference_losses, home_wins, home_losses,
                 away_wins, away_losses, playoff_seed, season_type)
                VALUES (?, ?, ?, ?, ?, 0, 350, 300, 4, 2, 8, 4, ?, ?, ?, ?, ?, 'regular_season')
            """,
                (
                    "test_dynasty",
                    2024,
                    team_id,
                    wins,
                    losses,
                    wins // 2,
                    losses // 2,
                    wins - wins // 2,
                    losses - losses // 2,
                    playoff_seed,
                ),
            )

        # Insert playoff bracket
        # Wild Card round (6 games)
        playoff_games = [
            ("wild_card", "AFC", 1, 2, 7, 2),  # Team 2 beats 7
            ("wild_card", "AFC", 2, 3, 6, 3),  # Team 3 beats 6
            ("wild_card", "AFC", 3, 4, 5, 4),  # Team 4 beats 5
            ("wild_card", "NFC", 1, 9, 14, 9),  # Team 9 beats 14
            ("wild_card", "NFC", 2, 10, 13, 10),  # Team 10 beats 13
            ("wild_card", "NFC", 3, 11, 12, 11),  # Team 11 beats 12
        ]

        # Divisional (4 games)
        playoff_games.extend([
            ("divisional", "AFC", 1, 1, 4, 1),  # Team 1 beats 4
            ("divisional", "AFC", 2, 2, 3, 2),  # Team 2 beats 3
            ("divisional", "NFC", 1, 8, 11, 8),  # Team 8 beats 11
            ("divisional", "NFC", 2, 9, 10, 9),  # Team 9 beats 10
        ])

        # Conference (2 games)
        playoff_games.extend([
            ("conference", "AFC", 1, 1, 2, 1),  # Team 1 beats 2
            ("conference", "NFC", 1, 8, 9, 8),  # Team 8 beats 9
        ])

        # Super Bowl
        playoff_games.extend([
            ("super_bowl", "SUPER_BOWL", 1, 1, 8, 1),  # Team 1 wins Super Bowl
        ])

        for round_name, conf, game_num, higher, lower, winner in playoff_games:
            conn.execute(
                """
                INSERT INTO playoff_bracket
                (dynasty_id, season, round_name, conference, game_number,
                 higher_seed, lower_seed, winner, home_score, away_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 28, 21)
            """,
                ("test_dynasty", 2024, round_name, conf, game_num, higher, lower, winner),
            )

        conn.commit()

        yield db

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_record_from_standings_and_playoffs(self, temp_db):
        """Record season correctly merges standings + playoff data."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        stats = service.record_all_season_results()

        assert stats["recorded"] == 32
        assert stats["errors"] == 0

    def test_super_bowl_winner_marked(self, temp_db):
        """Super Bowl winner has won_super_bowl=True."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        service.record_all_season_results()

        # Check Team 1 (Super Bowl winner)
        api = TeamHistoryAPI(temp_db)
        record = api.get_season_record("test_dynasty", 1, 2024)

        assert record is not None
        assert record.won_super_bowl is True
        assert record.playoff_round_reached == "super_bowl"
        assert record.made_playoffs is True

    def test_playoff_loser_round_tracked(self, temp_db):
        """Playoff losers have correct round reached."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        service.record_all_season_results()

        api = TeamHistoryAPI(temp_db)

        # Team 8 lost in Super Bowl
        record8 = api.get_season_record("test_dynasty", 8, 2024)
        assert record8.playoff_round_reached == "super_bowl"
        assert record8.won_super_bowl is False

        # Team 2 lost in Conference
        record2 = api.get_season_record("test_dynasty", 2, 2024)
        assert record2.playoff_round_reached == "conference"


class TestAttractivenessObject:
    """Tests for TeamAttractiveness object building."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'NFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )

        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield db

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_static_data_loaded(self, temp_db):
        """Static fields from config are loaded."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)

        # Dallas Cowboys (team_id=17 in config) - large market, no state tax
        ta = service.get_team_attractiveness(17)

        # Based on team_attractiveness_static.json
        assert ta.market_size > 75  # Dallas is large market
        assert ta.state_income_tax_rate == 0.0  # Texas has no state tax
        assert ta.state == "TX"

    def test_dynamic_data_computed(self, temp_db):
        """Dynamic fields computed from history."""
        api = TeamHistoryAPI(temp_db)

        # Insert 3 years of history with playoffs
        for year in range(2022, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=11,
                losses=6,
                made_playoffs=True,
                playoff_round_reached="divisional",
                won_super_bowl=False,
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        ta = service.get_team_attractiveness(10)

        assert ta.playoff_appearances_5yr == 3
        assert ta.super_bowl_wins_5yr == 0
        assert 0 <= ta.winning_culture_score <= 100
        assert ta.current_season_wins == 11
        assert ta.current_season_losses == 6

    def test_no_history_uses_defaults(self, temp_db):
        """Teams with no history use default values."""
        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        ta = service.get_team_attractiveness(10)

        assert ta.playoff_appearances_5yr == 0
        assert ta.super_bowl_wins_5yr == 0
        assert ta.winning_culture_score == 50  # Default
        assert ta.current_season_wins == 0
        assert ta.current_season_losses == 0


class TestAttractivenessTable:
    """Tests for persisting attractiveness to database table."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'AFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )

        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield db, conn

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_update_attractiveness_table(self, temp_db):
        """Can update team_attractiveness table."""
        db, conn = temp_db
        api = TeamHistoryAPI(db)

        # Insert history
        record = SeasonHistoryRecord(
            team_id=10,
            season=2024,
            wins=12,
            losses=5,
            made_playoffs=True,
            won_super_bowl=False,
        )
        api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(db, "test_dynasty", 2024)
        result = service.update_attractiveness_table(10)
        assert result is True

        # Verify in database
        row = conn.execute(
            """
            SELECT playoff_appearances_5yr, super_bowl_wins_5yr, winning_culture_score
            FROM team_attractiveness
            WHERE dynasty_id = ? AND team_id = ? AND season = ?
        """,
            ("test_dynasty", 10, 2024),
        ).fetchone()

        assert row is not None
        assert row["playoff_appearances_5yr"] == 1
        assert row["super_bowl_wins_5yr"] == 0

    def test_update_all_attractiveness(self, temp_db):
        """Can update attractiveness for all 32 teams."""
        db, _ = temp_db
        service = TeamAttractivenessService(db, "test_dynasty", 2024)
        count = service.update_all_attractiveness()

        assert count == 32


class TestWinningCulture:
    """Tests for winning culture calculation."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        conn = db.get_connection()

        for team_id in range(1, 33):
            conn.execute(
                """
                INSERT INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, 'AFC', 'East')
            """,
                (team_id, f"Team {team_id}", f"T{team_id}"),
            )

        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test_dynasty', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        yield db

        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_high_win_pct_high_culture(self, temp_db):
        """Teams with high 5-year win percentage get high culture score."""
        api = TeamHistoryAPI(temp_db)

        # Insert 5 winning seasons (70%+ win rate)
        for year in range(2020, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=13,
                losses=4,
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        ta = service.get_team_attractiveness(10)

        # 13-4 = 76.5% win rate -> ~76 culture score
        assert ta.winning_culture_score >= 70

    def test_low_win_pct_low_culture(self, temp_db):
        """Teams with low 5-year win percentage get low culture score."""
        api = TeamHistoryAPI(temp_db)

        # Insert 5 losing seasons (25% win rate)
        for year in range(2020, 2025):
            record = SeasonHistoryRecord(
                team_id=10,
                season=year,
                wins=4,
                losses=13,
            )
            api.record_season("test_dynasty", record)

        service = TeamAttractivenessService(temp_db, "test_dynasty", 2024)
        ta = service.get_team_attractiveness(10)

        # 4-13 = 23.5% win rate -> ~23 culture score
        assert ta.winning_culture_score <= 30
