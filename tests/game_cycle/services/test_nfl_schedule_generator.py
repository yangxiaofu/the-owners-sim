"""
Tests for NFLScheduleGenerator.

Comprehensive test suite for NFL-compliant schedule generation.
Tests cover:
- Basic functionality (272 games, 17 games per team)
- Division games (6 per team, 96 total)
- Rotation logic (3-year in-conference, 4-year cross-conference)
- Home/away balancing (8-9 or 9-8 split)
- Dynasty isolation and edge cases
"""

import os
import tempfile
import pytest
from collections import Counter

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.schedule_rotation_api import ScheduleRotationAPI, RotationState
from src.game_cycle.services.nfl_schedule_generator import NFLScheduleGenerator, Matchup


class TestNFLScheduleGeneratorBasic:
    """Basic functionality tests - validates game counts and structure."""

    @pytest.fixture
    def generator(self):
        """Create generator with temp database."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize database
        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_basic', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_basic")
        yield gen

        # Cleanup
        gen.close()
        os.unlink(db_path)

    def test_generates_exactly_272_games(self, generator):
        """Verify exactly 272 games generated (17 weeks * 16 games)."""
        games = generator.generate_schedule(2025)
        assert len(games) == 272

    def test_every_team_plays_17_games(self, generator):
        """Each of 32 teams plays exactly 17 games."""
        games = generator.generate_schedule(2025)

        team_counts = Counter()
        for game in games:
            home = game['data']['parameters']['home_team_id']
            away = game['data']['parameters']['away_team_id']
            team_counts[home] += 1
            team_counts[away] += 1

        for team_id in range(1, 33):
            assert team_counts[team_id] == 17, f"Team {team_id} plays {team_counts[team_id]} games"

    def test_no_team_plays_itself(self, generator):
        """No team is scheduled against itself."""
        games = generator.generate_schedule(2025)

        for game in games:
            home = game['data']['parameters']['home_team_id']
            away = game['data']['parameters']['away_team_id']
            assert home != away, f"Team {home} scheduled against itself"

    def test_no_excessive_duplicate_matchups(self, generator):
        """Each matchup appears at most twice (home + away for division)."""
        games = generator.generate_schedule(2025)

        matchup_counts = Counter()
        for game in games:
            home = game['data']['parameters']['home_team_id']
            away = game['data']['parameters']['away_team_id']
            pair = tuple(sorted([home, away]))
            matchup_counts[pair] += 1

        # Division rivals appear 2x, all others 1x
        for pair, count in matchup_counts.items():
            assert count <= 2, f"Matchup {pair} appears {count} times"

    def test_exactly_18_weeks_generated(self, generator):
        """Schedule spans exactly 18 weeks (17 games + bye week per team)."""
        games = generator.generate_schedule(2025)

        weeks = set(game['data']['parameters']['week'] for game in games)
        assert weeks == set(range(1, 19)), f"Expected weeks 1-18, got {weeks}"

    def test_valid_games_per_week(self, generator):
        """Each week has valid number of games (13-16 depending on bye weeks)."""
        games = generator.generate_schedule(2025)

        week_counts = Counter(game['data']['parameters']['week'] for game in games)

        # With bye weeks (teams off each week), games per week varies:
        # - Weeks without byes: 16 games
        # - Weeks with 2 byes: 15 games
        # - Weeks with 4 byes: 14 games
        # - Weeks with 6 byes: 13 games
        total = sum(week_counts.values())
        assert total == 272, f"Expected 272 total games, got {total}"

        for week in range(1, 19):
            games_in_week = week_counts.get(week, 0)
            assert 13 <= games_in_week <= 16, f"Week {week} has {games_in_week} games (expected 13-16)"


class TestDivisionGames:
    """Tests for division game generation."""

    @pytest.fixture
    def generator(self):
        """Create generator with temp database."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_division', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_division")
        yield gen

        gen.close()
        os.unlink(db_path)

    def test_division_games_exactly_6_per_team(self, generator):
        """Each team plays exactly 6 division games."""
        games = generator.generate_schedule(2025)

        for team_id in range(1, 33):
            div_games = [
                g for g in games
                if (g['data']['parameters']['home_team_id'] == team_id or
                    g['data']['parameters']['away_team_id'] == team_id)
                and g['data']['metadata']['is_divisional']
            ]
            assert len(div_games) == 6, f"Team {team_id} has {len(div_games)} division games"

    def test_division_rivals_play_twice(self, generator):
        """Division rivals play home + away (2 games total)."""
        games = generator.generate_schedule(2025)

        # Check Bills vs Dolphins (both in AFC East, teams 1 and 2)
        bills_dolphins = [
            g for g in games
            if {g['data']['parameters']['home_team_id'],
                g['data']['parameters']['away_team_id']} == {1, 2}
        ]
        assert len(bills_dolphins) == 2

        # One should be Bills home, one should be Dolphins home
        home_teams = {g['data']['parameters']['home_team_id'] for g in bills_dolphins}
        assert home_teams == {1, 2}

    def test_division_games_marked_divisional(self, generator):
        """All division games have is_divisional flag."""
        games = generator.generate_schedule(2025)

        divisions = {
            1: [1, 2, 3, 4],
            2: [5, 6, 7, 8],
            3: [9, 10, 11, 12],
            4: [13, 14, 15, 16],
            5: [17, 18, 19, 20],
            6: [21, 22, 23, 24],
            7: [25, 26, 27, 28],
            8: [29, 30, 31, 32],
        }

        for game in games:
            home = game['data']['parameters']['home_team_id']
            away = game['data']['parameters']['away_team_id']

            # Find divisions
            home_div = next(d for d, teams in divisions.items() if home in teams)
            away_div = next(d for d, teams in divisions.items() if away in teams)

            if home_div == away_div:
                assert game['data']['metadata']['is_divisional'], \
                    f"Game {home} vs {away} should be divisional"

    def test_total_division_games_is_96(self, generator):
        """Total division games = 96 (32 teams * 6 / 2)."""
        games = generator.generate_schedule(2025)

        div_games = [g for g in games if g['data']['metadata']['is_divisional']]
        assert len(div_games) == 96

    def test_each_division_has_12_internal_games(self, generator):
        """Each division generates 12 internal games (4 teams choose 2 * 2)."""
        matchups = generator._assign_division_games()

        divisions = generator.DIVISIONS

        for division_id, div_teams in divisions.items():
            div_matchups = [
                m for m in matchups
                if m.home_team_id in div_teams and m.away_team_id in div_teams
            ]
            assert len(div_matchups) == 12, f"Division {division_id} has {len(div_matchups)} games"

    def test_division_home_away_balanced(self, generator):
        """Division games balanced: 3 home, 3 away per team."""
        games = generator.generate_schedule(2025)

        for team_id in range(1, 33):
            home_div = [
                g for g in games
                if g['data']['parameters']['home_team_id'] == team_id
                and g['data']['metadata']['is_divisional']
            ]
            away_div = [
                g for g in games
                if g['data']['parameters']['away_team_id'] == team_id
                and g['data']['metadata']['is_divisional']
            ]
            assert len(home_div) == 3, f"Team {team_id} has {len(home_div)} home div games"
            assert len(away_div) == 3, f"Team {team_id} has {len(away_div)} away div games"


class TestRotationLogic:
    """Tests for 3-year and 4-year rotation cycles."""

    @pytest.fixture
    def generator(self):
        """Create generator with temp database."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_rotation', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_rotation")
        yield gen

        gen.close()
        os.unlink(db_path)

    def test_in_conference_rotation_3_year_cycle(self, generator):
        """In-conference opponent rotates on 3-year cycle."""
        # AFC East rotation
        opp_2025 = generator._get_in_conference_opponent_div(1, 2025)
        opp_2026 = generator._get_in_conference_opponent_div(1, 2026)
        opp_2027 = generator._get_in_conference_opponent_div(1, 2027)
        opp_2028 = generator._get_in_conference_opponent_div(1, 2028)  # Should repeat

        # All 3 AFC opponents should appear in cycle
        opponents_in_cycle = {opp_2025, opp_2026, opp_2027}
        assert opponents_in_cycle == {2, 3, 4}, "Should rotate through AFC North/South/West"

        # Cycle repeats after 3 years
        assert opp_2028 == opp_2025

    def test_cross_conference_rotation_4_year_cycle(self, generator):
        """Cross-conference opponent rotates on 4-year cycle."""
        # AFC East rotation against NFC
        opp_2025 = generator._get_cross_conference_opponent_div(1, 2025)
        opp_2026 = generator._get_cross_conference_opponent_div(1, 2026)
        opp_2027 = generator._get_cross_conference_opponent_div(1, 2027)
        opp_2028 = generator._get_cross_conference_opponent_div(1, 2028)
        opp_2029 = generator._get_cross_conference_opponent_div(1, 2029)  # Should repeat

        # All 4 NFC divisions
        opponents_in_cycle = {opp_2025, opp_2026, opp_2027, opp_2028}
        assert opponents_in_cycle == {5, 6, 7, 8}, "Should rotate through all NFC divisions"

        # Cycle repeats after 4 years
        assert opp_2029 == opp_2025

    def test_rotation_state_persists_to_database(self, generator):
        """Rotation state saved after schedule generation."""
        generator.generate_schedule(2025)

        # Query rotation table
        api = ScheduleRotationAPI(generator._db)
        rotations = api.get_all_rotations_for_season("test_rotation", 2025)

        assert len(rotations) == 8  # All 8 divisions

    def test_rotation_state_advances_each_season(self, generator):
        """Rotation state changes between seasons."""
        generator.generate_schedule(2025)
        generator.generate_schedule(2026)

        api = ScheduleRotationAPI(generator._db)
        rot_2025 = api.get_rotation_state("test_rotation", 2025, division_id=1)
        rot_2026 = api.get_rotation_state("test_rotation", 2026, division_id=1)

        # In-conference opponent should differ
        assert rot_2025.in_conference_opponent_div != rot_2026.in_conference_opponent_div

    def test_conference_rotation_games_count(self, generator):
        """In-conference rotation generates 64 games."""
        matchups = generator._assign_conference_rotation(2025)
        assert len(matchups) == 64

    def test_cross_conference_rotation_games_count(self, generator):
        """Cross-conference rotation generates 64 games."""
        matchups = generator._assign_cross_conference_rotation(2025)
        assert len(matchups) == 64

    def test_same_place_finishers_games_count(self, generator):
        """Same-place finishers generate 32 games."""
        matchups = generator._assign_same_place_finishers(2025)
        assert len(matchups) == 32

    def test_17th_game_count(self, generator):
        """17th game generates 16 matchups."""
        matchups = generator._assign_17th_game(2025)
        assert len(matchups) == 16


class TestHomeAwayBalance:
    """Tests for home/away game balancing."""

    @pytest.fixture
    def generator(self):
        """Create generator with temp database."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_balance', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_balance")
        yield gen

        gen.close()
        os.unlink(db_path)

    def test_home_away_balance_8_9_split(self, generator):
        """Each team has 8-9 or 9-8 home/away split."""
        games = generator.generate_schedule(2025)

        for team_id in range(1, 33):
            home = len([
                g for g in games
                if g['data']['parameters']['home_team_id'] == team_id
            ])
            away = len([
                g for g in games
                if g['data']['parameters']['away_team_id'] == team_id
            ])

            assert (home, away) in [(8, 9), (9, 8)], \
                f"Team {team_id} has {home} home, {away} away"

    def test_no_team_has_10_plus_home(self, generator):
        """No team has more than 9 home games."""
        games = generator.generate_schedule(2025)

        for team_id in range(1, 33):
            home = len([
                g for g in games
                if g['data']['parameters']['home_team_id'] == team_id
            ])
            assert home <= 9, f"Team {team_id} has {home} home games"

    def test_no_team_has_10_plus_away(self, generator):
        """No team has more than 9 away games."""
        games = generator.generate_schedule(2025)

        for team_id in range(1, 33):
            away = len([
                g for g in games
                if g['data']['parameters']['away_team_id'] == team_id
            ])
            assert away <= 9, f"Team {team_id} has {away} away games"

    def test_total_home_equals_total_away(self, generator):
        """Total home games equals total away games (272)."""
        games = generator.generate_schedule(2025)

        total_home = len(games)  # Each game has exactly 1 home team
        total_away = len(games)  # Each game has exactly 1 away team

        assert total_home == total_away == 272

    def test_no_team_plays_twice_in_one_week(self, generator):
        """No team plays multiple games in the same week."""
        games = generator.generate_schedule(2025)

        # Check all 18 weeks (not just 17)
        for week in range(1, 19):
            week_games = [g for g in games if g['data']['parameters']['week'] == week]
            teams_this_week = []

            for game in week_games:
                teams_this_week.append(game['data']['parameters']['home_team_id'])
                teams_this_week.append(game['data']['parameters']['away_team_id'])

            # Each team should appear at most once per week (may be 0 if bye week)
            team_counts = Counter(teams_this_week)
            for team_id, count in team_counts.items():
                assert count == 1, f"Team {team_id} plays {count} times in week {week}"


class TestDynastyIsolationAndEdgeCases:
    """Tests for dynasty isolation and edge cases."""

    def test_dynasty_isolation(self):
        """Different dynasties have independent schedules."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create both dynasty records
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('dynasty_1', 'Test Dynasty 1', 1, 2025)
        """)
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('dynasty_2', 'Test Dynasty 2', 1, 2025)
        """)
        db.close()

        try:
            gen1 = NFLScheduleGenerator(db_path=db_path, dynasty_id="dynasty_1")
            gen2 = NFLScheduleGenerator(db_path=db_path, dynasty_id="dynasty_2")

            games1 = gen1.generate_schedule(2025)
            games2 = gen2.generate_schedule(2025)

            # Both should be valid (272 games each)
            assert len(games1) == 272
            assert len(games2) == 272

            # Rotation states should be independent
            api = ScheduleRotationAPI(gen1._db)
            rot1 = api.get_all_rotations_for_season("dynasty_1", 2025)
            rot2 = api.get_all_rotations_for_season("dynasty_2", 2025)

            assert len(rot1) == 8
            assert len(rot2) == 8

            gen1.close()
            gen2.close()

        finally:
            os.unlink(db_path)

    def test_first_season_uses_default_standings(self):
        """First season (no prior standings) uses default ordering."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_first_season', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        try:
            gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_first_season")

            # No prior season data - should work with defaults
            standings = gen._get_divisional_standings(2024)

            # Should return teams in ID order when no standings exist
            for div_id, teams in gen.DIVISIONS.items():
                ranked = standings.get(div_id, teams)
                # With no standings, order is by team_id
                assert len(ranked) == 4

            gen.close()

        finally:
            os.unlink(db_path)

    def test_consecutive_seasons_maintain_rotation(self):
        """Generating multiple consecutive seasons maintains rotation."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test_multi_season', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        try:
            gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="test_multi_season")

            for season in range(2025, 2030):
                games = gen.generate_schedule(season)
                assert len(games) == 272

            gen.close()

        finally:
            os.unlink(db_path)

    def test_handles_empty_database(self):
        """Generator works with fresh database (no history)."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('new_dynasty', 'Test Dynasty', 1, 2025)
        """)
        db.close()

        try:
            gen = NFLScheduleGenerator(db_path=db_path, dynasty_id="new_dynasty")
            games = gen.generate_schedule(2025)

            assert len(games) == 272

            gen.close()

        finally:
            os.unlink(db_path)


class TestScheduleRotationAPI:
    """Tests for ScheduleRotationAPI."""

    @pytest.fixture
    def api(self):
        """Create API with temp database."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(db_path)

        # Create team record for foreign key constraint
        db.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (1, 'Buffalo Bills', 'BUF', 'AFC', 'East')
        """)

        # Create dynasty record for FK constraint on schedule_rotation
        db.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id, season_year)
            VALUES ('test', 'Test Dynasty', 1, 2025)
        """)

        api = ScheduleRotationAPI(db)
        yield api, db, db_path

        db.close()
        os.unlink(db_path)

    def test_save_and_retrieve_rotation_state(self, api):
        """Test save and retrieve rotation state."""
        api_obj, db, db_path = api

        api_obj.save_rotation_state(
            dynasty_id="test",
            season=2025,
            division_id=1,
            in_conference_opponent_div=2,
            cross_conference_opponent_div=5
        )

        result = api_obj.get_rotation_state("test", 2025, 1)
        assert result is not None
        assert result.division_id == 1
        assert result.in_conference_opponent_div == 2
        assert result.cross_conference_opponent_div == 5

    def test_rotation_api_validates_division_id(self, api):
        """ScheduleRotationAPI validates division IDs."""
        api_obj, db, db_path = api

        with pytest.raises(ValueError):
            api_obj.save_rotation_state(
                dynasty_id="test",
                season=2025,
                division_id=0,  # Invalid
                in_conference_opponent_div=2,
                cross_conference_opponent_div=5
            )

        with pytest.raises(ValueError):
            api_obj.save_rotation_state(
                dynasty_id="test",
                season=2025,
                division_id=9,  # Invalid
                in_conference_opponent_div=2,
                cross_conference_opponent_div=5
            )

    def test_rotation_api_prevents_self_play(self, api):
        """Cannot set in-conference opponent to own division."""
        api_obj, db, db_path = api

        with pytest.raises(ValueError):
            api_obj.save_rotation_state(
                dynasty_id="test",
                season=2025,
                division_id=1,
                in_conference_opponent_div=1,  # Same as own division
                cross_conference_opponent_div=5
            )

    def test_rotation_api_validates_conference(self, api):
        """In-conference opponent must be same conference."""
        api_obj, db, db_path = api

        with pytest.raises(ValueError):
            api_obj.save_rotation_state(
                dynasty_id="test",
                season=2025,
                division_id=1,  # AFC
                in_conference_opponent_div=5,  # NFC - wrong conference!
                cross_conference_opponent_div=5
            )

    def test_rotation_api_validates_cross_conference(self, api):
        """Cross-conference opponent must be different conference."""
        api_obj, db, db_path = api

        with pytest.raises(ValueError):
            api_obj.save_rotation_state(
                dynasty_id="test",
                season=2025,
                division_id=1,  # AFC
                in_conference_opponent_div=2,
                cross_conference_opponent_div=2  # AFC - should be NFC!
            )

    def test_initialize_rotations_creates_all_divisions(self, api):
        """Initialize creates rotation records for all 8 divisions."""
        api_obj, db, db_path = api

        api_obj.initialize_rotations("test", 2025)

        rotations = api_obj.get_all_rotations_for_season("test", 2025)
        assert len(rotations) == 8

    def test_delete_rotations_for_dynasty(self, api):
        """Delete removes all rotations for dynasty."""
        api_obj, db, db_path = api

        api_obj.initialize_rotations("test", 2025)
        api_obj.initialize_rotations("test", 2026)

        deleted = api_obj.delete_rotations_for_dynasty("test")
        assert deleted == 16  # 8 per season * 2 seasons

        rotations = api_obj.get_all_rotations_for_season("test", 2025)
        assert len(rotations) == 0
