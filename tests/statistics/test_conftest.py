"""
Tests for statistics fixtures to verify they work correctly.

Validates that all fixtures provide correct data structure and content.
"""
import sqlite3
import pytest


def test_in_memory_db_schema(in_memory_db):
    """Test that in_memory_db creates correct schema"""
    cursor = in_memory_db.cursor()

    # Verify table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_game_stats'")
    assert cursor.fetchone() is not None, "player_game_stats table should exist"

    # Verify columns exist
    cursor.execute("PRAGMA table_info(player_game_stats)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        'dynasty_id', 'game_id', 'season_type', 'player_id', 'player_name', 'team_id', 'position',
        'passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts', 'passing_interceptions',
        'rushing_yards', 'rushing_tds', 'rushing_attempts',
        'receiving_yards', 'receiving_tds', 'receptions', 'targets',
        'tackles_total', 'sacks', 'interceptions',
        'field_goals_made', 'field_goals_attempted', 'extra_points_made', 'extra_points_attempted'
    }

    assert expected_columns.issubset(columns), f"Missing columns: {expected_columns - columns}"


def test_in_memory_db_row_count(in_memory_db):
    """Test that in_memory_db contains expected number of rows"""
    cursor = in_memory_db.cursor()

    # Total rows (20 QBs + 20 RBs + 20 WRs/TEs + 10 DEF + 5 K = 75)
    cursor.execute("SELECT COUNT(*) FROM player_game_stats")
    total_count = cursor.fetchone()[0]
    assert total_count == 75, f"Expected 75 total rows, got {total_count}"

    # QB count
    cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE position = 'QB'")
    qb_count = cursor.fetchone()[0]
    assert qb_count == 20, f"Expected 20 QBs, got {qb_count}"

    # RB count
    cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE position = 'RB'")
    rb_count = cursor.fetchone()[0]
    assert rb_count == 20, f"Expected 20 RBs, got {rb_count}"

    # WR/TE count
    cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE position IN ('WR', 'TE')")
    wr_count = cursor.fetchone()[0]
    assert wr_count == 20, f"Expected 20 WRs/TEs, got {wr_count}"

    # Defensive player count
    cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE position IN ('LB', 'DE', 'CB', 'S')")
    def_count = cursor.fetchone()[0]
    assert def_count == 10, f"Expected 10 defensive players, got {def_count}"

    # Kicker count
    cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE position = 'K'")
    k_count = cursor.fetchone()[0]
    assert k_count == 5, f"Expected 5 kickers, got {k_count}"


def test_sample_qb_stats_fixture(sample_qb_stats):
    """Test that sample_qb_stats returns correct data"""
    # Should have 20 QBs
    assert len(sample_qb_stats) == 20, f"Expected 20 QBs, got {len(sample_qb_stats)}"

    # Check first QB (highest passing yards)
    first_qb = sample_qb_stats[0]
    assert first_qb['position'] == 'QB'
    assert first_qb['player_name'] == 'Perfect QB'  # 400 yards
    assert first_qb['passing_yards'] == 400

    # Verify all QBs have required fields
    required_fields = [
        'player_id', 'player_name', 'team_id', 'position',
        'passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts',
        'passing_interceptions', 'rushing_yards', 'rushing_tds'
    ]
    for qb in sample_qb_stats:
        assert qb['position'] == 'QB'
        for field in required_fields:
            assert field in qb, f"Missing field {field} in QB stats"

    # Verify descending order by passing yards
    for i in range(len(sample_qb_stats) - 1):
        assert sample_qb_stats[i]['passing_yards'] >= sample_qb_stats[i+1]['passing_yards'], \
            "QBs should be sorted by passing yards descending"


def test_sample_rb_stats_fixture(sample_rb_stats):
    """Test that sample_rb_stats returns correct data"""
    # Should have 20 RBs
    assert len(sample_rb_stats) == 20, f"Expected 20 RBs, got {len(sample_rb_stats)}"

    # Check first RB (highest rushing yards)
    first_rb = sample_rb_stats[0]
    assert first_rb['position'] == 'RB'
    assert first_rb['player_name'] == 'Derrick Henry'  # 165 yards
    assert first_rb['rushing_yards'] == 165

    # Verify all RBs have required fields
    required_fields = [
        'player_id', 'player_name', 'team_id', 'position',
        'rushing_yards', 'rushing_tds', 'rushing_attempts',
        'receiving_yards', 'receiving_tds', 'receptions'
    ]
    for rb in sample_rb_stats:
        assert rb['position'] == 'RB'
        for field in required_fields:
            assert field in rb, f"Missing field {field} in RB stats"

    # Verify descending order by rushing yards
    for i in range(len(sample_rb_stats) - 1):
        assert sample_rb_stats[i]['rushing_yards'] >= sample_rb_stats[i+1]['rushing_yards'], \
            "RBs should be sorted by rushing yards descending"


def test_sample_wr_stats_fixture(sample_wr_stats):
    """Test that sample_wr_stats returns correct data"""
    # Should have 20 WRs/TEs
    assert len(sample_wr_stats) == 20, f"Expected 20 WRs/TEs, got {len(sample_wr_stats)}"

    # Check first WR (highest receiving yards)
    first_wr = sample_wr_stats[0]
    assert first_wr['position'] in ('WR', 'TE')
    assert first_wr['player_name'] == 'Tyreek Hill'  # 152 yards
    assert first_wr['receiving_yards'] == 152

    # Verify all WRs/TEs have required fields
    required_fields = [
        'player_id', 'player_name', 'team_id', 'position',
        'receiving_yards', 'receiving_tds', 'receptions', 'targets'
    ]
    for wr in sample_wr_stats:
        assert wr['position'] in ('WR', 'TE')
        for field in required_fields:
            assert field in wr, f"Missing field {field} in WR/TE stats"

    # Verify descending order by receiving yards
    for i in range(len(sample_wr_stats) - 1):
        assert sample_wr_stats[i]['receiving_yards'] >= sample_wr_stats[i+1]['receiving_yards'], \
            "WRs/TEs should be sorted by receiving yards descending"


def test_sample_all_stats_fixture(sample_all_stats):
    """Test that sample_all_stats returns all players"""
    # Should have 75 total players
    assert len(sample_all_stats) == 75, f"Expected 75 total players, got {len(sample_all_stats)}"

    # Count positions
    position_counts = {}
    for player in sample_all_stats:
        pos = player['position']
        position_counts[pos] = position_counts.get(pos, 0) + 1

    assert position_counts.get('QB', 0) == 20, f"Expected 20 QBs"
    assert position_counts.get('RB', 0) == 20, f"Expected 20 RBs"
    assert position_counts.get('WR', 0) + position_counts.get('TE', 0) == 20, f"Expected 20 WRs/TEs"
    assert position_counts.get('K', 0) == 5, f"Expected 5 kickers"

    # Verify all required fields exist
    required_fields = [
        'player_id', 'player_name', 'team_id', 'position',
        'passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts', 'passing_interceptions',
        'rushing_yards', 'rushing_tds', 'rushing_attempts',
        'receiving_yards', 'receiving_tds', 'receptions', 'targets',
        'tackles_total', 'sacks', 'interceptions',
        'field_goals_made', 'field_goals_attempted', 'extra_points_made', 'extra_points_attempted'
    ]
    for player in sample_all_stats:
        for field in required_fields:
            assert field in player, f"Missing field {field} in player stats"


def test_known_passer_ratings_fixture(known_passer_ratings):
    """Test that known_passer_ratings contains expected data"""
    # Should have 20 QB ratings
    assert len(known_passer_ratings) == 20, f"Expected 20 passer ratings, got {len(known_passer_ratings)}"

    # Check some specific ratings
    assert known_passer_ratings['Perfect QB'] == 158.3, "Perfect rating should be 158.3"
    assert known_passer_ratings['Aaron Rodgers 2011'] == 139.9, "Aaron Rodgers 2011 should have 139.9 rating"
    assert known_passer_ratings['Patrick Mahomes'] == 122.3, "Patrick Mahomes should have 122.3 rating"

    # Check that all ratings are between 0 and 158.3
    for player, rating in known_passer_ratings.items():
        assert 0 <= rating <= 158.3, f"{player} has invalid rating {rating}"

    # Check that worst QB has lowest rating
    assert known_passer_ratings['Bryce Young'] == 42.3, "Bryce Young should have lowest rating"


def test_sample_teams_fixture(sample_teams):
    """Test that sample_teams contains expected data"""
    # Should have 32 teams
    assert len(sample_teams) == 32, f"Expected 32 teams, got {len(sample_teams)}"

    # Check structure of first team
    first_team = sample_teams[0]
    assert len(first_team) == 4, "Each team should have 4 fields"
    team_id, team_name, conference, division = first_team
    assert isinstance(team_id, int), "team_id should be integer"
    assert isinstance(team_name, str), "team_name should be string"
    assert conference in ('AFC', 'NFC'), f"Invalid conference {conference}"
    assert division in ('East', 'North', 'South', 'West'), f"Invalid division {division}"

    # Count conferences (should be 16 AFC, 16 NFC)
    afc_count = sum(1 for t in sample_teams if t[2] == 'AFC')
    nfc_count = sum(1 for t in sample_teams if t[2] == 'NFC')
    assert afc_count == 16, f"Expected 16 AFC teams, got {afc_count}"
    assert nfc_count == 16, f"Expected 16 NFC teams, got {nfc_count}"

    # Count divisions (should be 4 per conference = 8 total, 4 teams per division)
    divisions = {}
    for team_id, team_name, conference, division in sample_teams:
        key = f"{conference}_{division}"
        divisions[key] = divisions.get(key, 0) + 1

    # Each division should have exactly 4 teams
    for div_key, count in divisions.items():
        assert count == 4, f"Division {div_key} should have 4 teams, has {count}"


def test_defensive_stats_in_db(in_memory_db):
    """Test that defensive players have correct stats"""
    cursor = in_memory_db.cursor()

    # Get defensive players
    cursor.execute("""
        SELECT player_name, position, tackles_total, sacks, interceptions
        FROM player_game_stats
        WHERE position IN ('LB', 'DE', 'CB', 'S')
        ORDER BY tackles_total DESC
    """)

    def_players = cursor.fetchall()
    assert len(def_players) == 10, f"Expected 10 defensive players, got {len(def_players)}"

    # Check that elite pass rushers have sacks
    cursor.execute("""
        SELECT player_name, sacks
        FROM player_game_stats
        WHERE position IN ('DE', 'LB') AND sacks > 0
        ORDER BY sacks DESC
    """)
    pass_rushers = cursor.fetchall()
    assert len(pass_rushers) >= 3, "Should have at least 3 pass rushers with sacks"

    # Check that DBs have interceptions
    cursor.execute("""
        SELECT player_name, interceptions
        FROM player_game_stats
        WHERE position IN ('CB', 'S') AND interceptions > 0
    """)
    dbs_with_ints = cursor.fetchall()
    assert len(dbs_with_ints) >= 3, "Should have at least 3 DBs with interceptions"


def test_kicker_stats_in_db(in_memory_db):
    """Test that kickers have correct special teams stats"""
    cursor = in_memory_db.cursor()

    # Get kickers
    cursor.execute("""
        SELECT player_name, field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted
        FROM player_game_stats
        WHERE position = 'K'
        ORDER BY field_goals_made DESC
    """)

    kickers = cursor.fetchall()
    assert len(kickers) == 5, f"Expected 5 kickers, got {len(kickers)}"

    # All kickers should have field goal attempts
    for kicker in kickers:
        name, fg_made, fg_att, xp_made, xp_att = kicker
        assert fg_att > 0, f"{name} should have field goal attempts"
        assert fg_made <= fg_att, f"{name} FG made should not exceed attempts"
        assert xp_made <= xp_att, f"{name} XP made should not exceed attempts"


def test_dynasty_id_consistency(in_memory_db):
    """Test that all records use 'test_dynasty' dynasty_id"""
    cursor = in_memory_db.cursor()

    cursor.execute("SELECT DISTINCT dynasty_id FROM player_game_stats")
    dynasty_ids = [row[0] for row in cursor.fetchall()]

    assert len(dynasty_ids) == 1, f"Expected 1 dynasty_id, got {len(dynasty_ids)}"
    assert dynasty_ids[0] == 'test_dynasty', f"Expected 'test_dynasty', got '{dynasty_ids[0]}'"


def test_season_type_consistency(in_memory_db):
    """Test that all records use 'regular_season' season_type"""
    cursor = in_memory_db.cursor()

    cursor.execute("SELECT DISTINCT season_type FROM player_game_stats")
    season_types = [row[0] for row in cursor.fetchall()]

    assert len(season_types) == 1, f"Expected 1 season_type, got {len(season_types)}"
    assert season_types[0] == 'regular_season', f"Expected 'regular_season', got '{season_types[0]}'"


def test_fixture_integration(sample_qb_stats, sample_rb_stats, sample_wr_stats, known_passer_ratings):
    """Test that fixtures work together correctly"""
    # Verify QB names in sample_qb_stats match known_passer_ratings
    qb_names_in_stats = {qb['player_name'] for qb in sample_qb_stats}
    qb_names_in_ratings = set(known_passer_ratings.keys())

    assert qb_names_in_stats == qb_names_in_ratings, \
        f"QB names mismatch: {qb_names_in_stats ^ qb_names_in_ratings}"

    # Verify no duplicate player IDs across positions
    all_player_ids = set()
    for qb in sample_qb_stats:
        all_player_ids.add(qb['player_id'])
    for rb in sample_rb_stats:
        assert rb['player_id'] not in all_player_ids, f"Duplicate player_id: {rb['player_id']}"
        all_player_ids.add(rb['player_id'])
    for wr in sample_wr_stats:
        assert wr['player_id'] not in all_player_ids, f"Duplicate player_id: {wr['player_id']}"
        all_player_ids.add(wr['player_id'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
