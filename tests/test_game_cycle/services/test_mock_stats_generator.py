"""
Tests for Mock Stats Generator

Validates that the mock stats generator produces:
1. Rating-weighted stats (elite players get better numbers)
2. Full stat coverage (all columns from player_game_stats)
3. Internal consistency (passing_yards == sum of receiving_yards)
4. Score alignment (TDs*6 + FGs*3 + XPs ≈ final score)
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.game_cycle.services.mock_stats_generator import MockStatsGenerator, MockGameStats


@pytest.fixture
def temp_db():
    """Create temporary database with sample roster."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create minimal schema
    cursor.execute("""
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            first_name TEXT,
            last_name TEXT,
            team_id INTEGER,
            positions TEXT,
            attributes TEXT,
            UNIQUE(dynasty_id, player_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE team_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            depth_chart_order INTEGER DEFAULT 99,
            roster_status TEXT DEFAULT 'active',
            UNIQUE(dynasty_id, team_id, player_id)
        )
    """)

    # Insert test dynasty
    cursor.execute("INSERT INTO dynasties (dynasty_id, name) VALUES (?, ?)", ('test_dynasty', 'Test Dynasty'))

    # Insert sample players for team 1 (offense)
    players = [
        # QB
        (1, 'Patrick', 'Mahomes', 1, '["quarterback"]', '{"overall": 99, "throw_power": 95, "throw_accuracy": 98}'),
        # RBs
        (2, 'Christian', 'McCaffrey', 1, '["running_back"]', '{"overall": 95, "speed": 97, "agility": 96}'),
        (3, 'Backup', 'RB', 1, '["running_back"]', '{"overall": 75, "speed": 80, "agility": 78}'),
        # WRs
        (4, 'Tyreek', 'Hill', 1, '["wide_receiver"]', '{"overall": 98, "speed": 99, "route_running": 92}'),
        (5, 'Davante', 'Adams', 1, '["wide_receiver"]', '{"overall": 96, "speed": 88, "route_running": 99}'),
        (6, 'WR3', 'Slot', 1, '["wide_receiver"]', '{"overall": 82, "speed": 85, "route_running": 84}'),
        # TE
        (7, 'Travis', 'Kelce', 1, '["tight_end"]', '{"overall": 97, "speed": 85, "route_running": 93}'),
        # Kicker
        (8, 'Justin', 'Tucker', 1, '["kicker"]', '{"overall": 99, "kick_power": 99, "kick_accuracy": 99}'),
        # OL
        (9, 'Trent', 'Williams', 1, '["left_tackle"]', '{"overall": 96, "strength": 95, "pass_block": 97}'),
        (10, 'Quenton', 'Nelson', 1, '["left_guard"]', '{"overall": 95, "strength": 98, "run_block": 96}'),
        (11, 'Jason', 'Kelce', 1, '["center"]', '{"overall": 93, "strength": 90, "awareness": 95}'),
        (12, 'Zack', 'Martin', 1, '["right_guard"]', '{"overall": 94, "strength": 96, "pass_block": 93}'),
        (13, 'Lane', 'Johnson', 1, '["right_tackle"]', '{"overall": 94, "strength": 94, "pass_block": 95}'),
        # Defense
        (14, 'TJ', 'Watt', 1, '["outside_linebacker"]', '{"overall": 99, "speed": 90, "power_moves": 98}'),
        (15, 'Aaron', 'Donald', 1, '["defensive_tackle"]', '{"overall": 99, "strength": 99, "pass_rush": 99}'),
        (16, 'Micah', 'Parsons', 1, '["outside_linebacker"]', '{"overall": 96, "speed": 93, "pass_rush": 94}'),
        (17, 'Fred', 'Warner', 1, '["middle_linebacker"]', '{"overall": 95, "speed": 88, "awareness": 96}'),
        (18, 'Jalen', 'Ramsey', 1, '["cornerback"]', '{"overall": 96, "speed": 92, "man_coverage": 97}'),
        (19, 'Trevon', 'Diggs', 1, '["cornerback"]', '{"overall": 92, "speed": 90, "zone_coverage": 90}'),
        (20, 'Derwin', 'James', 1, '["strong_safety"]', '{"overall": 95, "speed": 91, "hit_power": 94}'),
        (21, 'Minkah', 'Fitzpatrick', 1, '["free_safety"]', '{"overall": 94, "speed": 89, "zone_coverage": 95}'),
    ]

    for player_id, first, last, team, positions, attrs in players:
        cursor.execute(
            "INSERT INTO players (dynasty_id, player_id, first_name, last_name, team_id, positions, attributes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('test_dynasty', player_id, first, last, team, positions, attrs)
        )
        cursor.execute(
            "INSERT INTO team_rosters (dynasty_id, team_id, player_id, depth_chart_order, roster_status) VALUES (?, ?, ?, ?, ?)",
            ('test_dynasty', team, player_id, player_id, 'active')
        )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestMockStatsGenerator:
    """Test suite for MockStatsGenerator."""

    def test_initialization(self, temp_db):
        """Test generator initialization."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')
        assert generator.db_path == temp_db
        assert generator.dynasty_id == 'test_dynasty'

    def test_generate_returns_mock_stats(self, temp_db):
        """Test that generate() returns MockGameStats object."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        result = generator.generate(
            game_id='game_001',
            home_team_id=1,
            away_team_id=1,
            home_score=28,
            away_score=21
        )

        assert isinstance(result, MockGameStats)
        assert result.game_id == 'game_001'
        assert result.home_team_id == 1
        assert result.away_team_id == 1
        assert result.home_score == 28
        assert result.away_score == 21
        assert isinstance(result.player_stats, list)
        assert len(result.player_stats) > 0

    def test_score_decomposition(self, temp_db):
        """Test _estimate_scoring_plays correctly decomposes scores."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        # Test zero score
        tds, fgs, xps = generator._estimate_scoring_plays(0)
        assert tds == 0 and fgs == 0 and xps == 0

        # Test field goal only
        tds, fgs, xps = generator._estimate_scoring_plays(3)
        assert tds == 0 and fgs == 1

        # Test 3 TDs with XPs (21 points)
        tds, fgs, xps = generator._estimate_scoring_plays(21)
        assert tds == 3
        assert xps == 3

        # Test 4 TDs + 1 FG (31 points)
        tds, fgs, xps = generator._estimate_scoring_plays(31)
        assert tds == 4
        assert fgs >= 1

    def test_passing_yards_equal_receiving_yards(self, temp_db):
        """Test internal consistency: passing_yards == sum(receiving_yards)."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        # NOTE: Using same team_id for both teams because we only have one roster in test DB
        # This is fine - we're testing per-team stat consistency
        result = generator.generate(
            game_id='game_002',
            home_team_id=1,
            away_team_id=1,
            home_score=24,
            away_score=17
        )

        # Since both teams have team_id=1, we need to separate by position groups
        # Just test that WITHIN the QB's stat group, their passing equals their team's receiving
        # We'll verify this by checking the first half of stats (home team)

        # Split stats in half (home team vs away team)
        half = len(result.player_stats) // 2
        home_stats = result.player_stats[:half]

        # Get QB passing yards from home team
        qb_stats = [s for s in home_stats if s['position'] == 'QB']
        if qb_stats:
            passing_yards = qb_stats[0]['passing_yards']

            # Get all receiving yards from home team
            recv_stats = [s for s in home_stats if s['receiving_yards'] > 0]
            total_receiving = sum(s['receiving_yards'] for s in recv_stats)

            # Should match (within 1 yard due to rounding)
            assert abs(passing_yards - total_receiving) <= 1, \
                f"Passing yards ({passing_yards}) != receiving yards ({total_receiving})"

    def test_rating_weighted_values(self, temp_db):
        """Test that _rating_weighted_value produces correct ranges."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        # Test low rating
        low_val = generator._rating_weighted_value(10, 30, 40)
        assert 7 <= low_val <= 33  # Allow variance

        # Test high rating
        high_val = generator._rating_weighted_value(10, 30, 99)
        assert 7 <= high_val <= 33

        # High rating should trend toward max
        high_vals = [generator._rating_weighted_value(10, 30, 99) for _ in range(20)]
        avg_high = sum(high_vals) / len(high_vals)

        low_vals = [generator._rating_weighted_value(10, 30, 40) for _ in range(20)]
        avg_low = sum(low_vals) / len(low_vals)

        assert avg_high > avg_low, "High-rated players should get better stats"

    def test_all_stat_columns_present(self, temp_db):
        """Test that all required stat columns are present in output."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        result = generator.generate(
            game_id='game_003',
            home_team_id=1,
            away_team_id=1,
            home_score=20,
            away_score=13
        )

        # Required columns from player_game_stats schema
        required_fields = [
            'dynasty_id', 'game_id', 'player_id', 'player_name', 'team_id', 'position',
            'season_type',
            # Passing
            'passing_yards', 'passing_tds', 'passing_attempts', 'passing_completions',
            'passing_interceptions', 'passing_sacks', 'passing_sack_yards', 'passing_rating',
            # Rushing
            'rushing_yards', 'rushing_tds', 'rushing_attempts', 'rushing_long', 'rushing_fumbles',
            # Receiving
            'receiving_yards', 'receiving_tds', 'receptions', 'targets',
            'receiving_long', 'receiving_drops',
            # Defensive
            'tackles_total', 'tackles_solo', 'tackles_assist', 'sacks', 'interceptions',
            'forced_fumbles', 'fumbles_recovered', 'passes_defended',
            # Kicking
            'field_goals_made', 'field_goals_attempted', 'extra_points_made',
            'extra_points_attempted', 'punts', 'punt_yards',
            # OL
            'pancakes', 'sacks_allowed', 'hurries_allowed', 'pressures_allowed',
            'run_blocking_grade', 'pass_blocking_efficiency', 'missed_assignments',
            'holding_penalties', 'false_start_penalties', 'downfield_blocks',
            'double_team_blocks', 'chip_blocks',
            # Snaps
            'snap_counts_offense', 'snap_counts_defense', 'snap_counts_special_teams',
            # Fantasy
            'fantasy_points'
        ]

        # Check first stat entry has all fields
        if result.player_stats:
            first_stat = result.player_stats[0]
            for field in required_fields:
                assert field in first_stat, f"Missing required field: {field}"

    def test_positions_covered(self, temp_db):
        """Test that all position groups have stats."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        result = generator.generate(
            game_id='game_004',
            home_team_id=1,
            away_team_id=1,
            home_score=35,
            away_score=14
        )

        positions = [s['position'] for s in result.player_stats]

        # Should have representation from all groups
        assert 'QB' in positions, "Missing QB stats"
        assert 'RB' in positions, "Missing RB stats"
        assert any(p in positions for p in ['WR', 'TE']), "Missing receiver stats"
        assert 'K' in positions, "Missing kicker stats"
        assert any(p in positions for p in ['LT', 'LG', 'C', 'RG', 'RT']), "Missing OL stats"
        assert any('LB' in p or 'DE' in p or 'CB' in p or 'S' in p for p in positions), "Missing defensive stats"

    def test_passer_rating_calculation(self, temp_db):
        """Test passer rating calculation is in valid range."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        # Test good performance
        rating = generator._calculate_passer_rating(
            attempts=30,
            completions=22,
            yards=300,
            tds=3,
            ints=0
        )
        assert 0 <= rating <= 158.3
        assert rating > 100, "Good performance should yield high rating"

        # Test poor performance
        rating = generator._calculate_passer_rating(
            attempts=30,
            completions=12,
            yards=120,
            tds=0,
            ints=3
        )
        assert 0 <= rating <= 158.3

    def test_fantasy_points_calculation(self, temp_db):
        """Test fantasy points are calculated correctly."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        # Test QB with 300 yards, 3 TDs
        points = generator._calculate_fantasy_points(
            passing_yards=300,
            passing_tds=3,
            interceptions=1
        )
        expected = 300 * 0.04 + 3 * 4 - 1 * 2  # 12 + 12 - 2 = 22
        assert points == pytest.approx(expected, rel=0.01)

        # Test RB with 100 rush yards, 1 TD, 50 rec yards
        points = generator._calculate_fantasy_points(
            rushing_yards=100,
            rushing_tds=1,
            receiving_yards=50,
            receptions=5
        )
        expected = 100 * 0.1 + 1 * 6 + 50 * 0.1 + 5 * 0.5  # 10 + 6 + 5 + 2.5 = 23.5
        assert points == pytest.approx(expected, rel=0.01)

    def test_high_scoring_game(self, temp_db):
        """Test generator handles high-scoring games."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        result = generator.generate(
            game_id='game_005',
            home_team_id=1,
            away_team_id=1,
            home_score=52,
            away_score=48
        )

        assert len(result.player_stats) > 0

        # Should have multiple TDs
        home_stats = [s for s in result.player_stats if s['team_id'] == 1]
        total_tds = sum(
            s['passing_tds'] + s['rushing_tds'] + s['receiving_tds']
            for s in home_stats
        )
        assert total_tds >= 6, "High-scoring game should have many TDs"

    def test_low_scoring_game(self, temp_db):
        """Test generator handles low-scoring games."""
        generator = MockStatsGenerator(temp_db, 'test_dynasty')

        result = generator.generate(
            game_id='game_006',
            home_team_id=1,
            away_team_id=1,
            home_score=9,
            away_score=6
        )

        assert len(result.player_stats) > 0

        # Low-scoring game should have field goals (1 TD + 1 FG = 10, or 3 FGs = 9)
        # Just verify kicker has some stats
        half = len(result.player_stats) // 2
        home_stats = result.player_stats[:half]
        kicker_stats = [s for s in home_stats if s['position'] == 'K']
        if kicker_stats:
            # Should have at least 1 FG or some XPs
            assert kicker_stats[0]['field_goals_made'] >= 1 or kicker_stats[0]['extra_points_made'] >= 1, \
                "Low-scoring game should have kicking activity"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
