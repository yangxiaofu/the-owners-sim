"""
Unit Tests for TeamNeedsAnalyzer

Tests team needs analysis including:
- Urgency detection (CRITICAL, HIGH, MEDIUM, LOW, NONE)
- Position tier weighting
- Expiring contract integration
- Dynasty isolation
- Sorting by urgency + position tier
"""

import pytest
import json
import sqlite3
from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency
from database.connection import DatabaseConnection
from database.player_roster_api import PlayerRosterAPI
from depth_chart.depth_chart_api import DepthChartAPI
from salary_cap.cap_database_api import CapDatabaseAPI


@pytest.fixture
def team_needs_analyzer(test_db_with_schema, test_dynasty_id):
    """
    Provides TeamNeedsAnalyzer instance with test database.
    """
    # Initialize full database schema (players, dynasties, team_rosters, etc.)
    db_conn = DatabaseConnection(test_db_with_schema)
    db_conn.initialize_database()

    # Ensure dynasty exists
    db_conn.ensure_dynasty_exists(test_dynasty_id)

    return TeamNeedsAnalyzer(test_db_with_schema, test_dynasty_id)


def insert_test_player_with_position(
    db_path,
    dynasty_id,
    team_id,
    position,
    overall,
    depth_order=99
):
    """
    Insert a test player with specific position and overall rating.

    Returns:
        player_id of inserted player
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Generate unique player_id
    import random
    player_id = random.randint(100000, 999999)

    # Insert player
    conn.execute("""
        INSERT INTO players (dynasty_id, player_id, first_name, last_name, number,
                           positions, attributes, team_id, years_pro, birthdate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dynasty_id,
        player_id,
        "Test",
        f"Player_{position}_{overall}",
        99,
        json.dumps([position]),
        json.dumps({'overall': overall}),
        team_id,
        5,
        '1995-01-01',
        'active'
    ))

    # Add to roster
    conn.execute("""
        INSERT INTO team_rosters (dynasty_id, team_id, player_id, depth_chart_order)
        VALUES (?, ?, ?, ?)
    """, (dynasty_id, team_id, player_id, depth_order))

    conn.commit()
    conn.close()

    return player_id


def create_test_roster_with_gaps(db_path, dynasty_id, team_id):
    """
    Create a test roster with various positional weaknesses.

    Returns:
        Dict mapping position -> list of (player_id, overall, depth_order)
    """
    roster_config = {
        # CRITICAL: No starter
        'quarterback': [],

        # CRITICAL: Starter well below threshold (68 < 70)
        'running_back': [(68, 1), (62, 2)],

        # HIGH: Starter below threshold (72 < 75 for Tier 1)
        'left_tackle': [(72, 1), (68, 2)],

        # HIGH: No depth
        'wide_receiver': [(85, 1)],

        # MEDIUM: Starter okay, weak depth
        'tight_end': [(75, 1), (60, 2), (58, 3)],

        # LOW: Starter good, adequate depth
        'linebacker': [(82, 1), (75, 2), (72, 3)],

        # NONE: Starter great, good depth
        'cornerback': [(90, 1), (82, 2), (78, 3)],
    }

    created_players = {}

    for position, players in roster_config.items():
        created_players[position] = []

        for overall, depth_order in players:
            player_id = insert_test_player_with_position(
                db_path, dynasty_id, team_id, position, overall, depth_order
            )
            created_players[position].append((player_id, overall, depth_order))

    return created_players


class TestUrgencyDetection:
    """Test urgency level detection for different roster scenarios."""

    def test_critical_no_starter(self, team_needs_analyzer, test_db_with_schema,
                                 test_dynasty_id, test_team_id, test_season):
        """Test CRITICAL urgency when position has no starter."""
        # Create roster with no QB
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 80, depth_order=1
        )

        # Analyze
        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)

        # Find QB need
        qb_need = next((n for n in needs if n['position'] == 'quarterback'), None)

        assert qb_need is not None
        assert qb_need['urgency'] == NeedUrgency.CRITICAL
        assert qb_need['starter_overall'] == 0
        assert "No starter" in qb_need['reason']

    def test_critical_starter_well_below_threshold(self, team_needs_analyzer,
                                                    test_db_with_schema, test_dynasty_id,
                                                    test_team_id, test_season):
        """Test CRITICAL urgency when starter is 5+ below threshold."""
        # QB threshold is 75 (Tier 1), so 65 should be CRITICAL
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'quarterback', 65, depth_order=1
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        qb_need = next((n for n in needs if n['position'] == 'quarterback'), None)

        assert qb_need['urgency'] == NeedUrgency.CRITICAL
        assert "well below standard" in qb_need['reason']

    def test_high_starter_below_threshold(self, team_needs_analyzer, test_db_with_schema,
                                          test_dynasty_id, test_team_id, test_season):
        """Test HIGH urgency when starter is below threshold."""
        # QB threshold is 75, so 72 should be HIGH
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'quarterback', 72, depth_order=1
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        qb_need = next((n for n in needs if n['position'] == 'quarterback'), None)

        assert qb_need['urgency'] == NeedUrgency.HIGH
        assert "below standard" in qb_need['reason']

    def test_high_no_depth(self, team_needs_analyzer, test_db_with_schema,
                           test_dynasty_id, test_team_id, test_season):
        """Test HIGH urgency when position has no backup depth."""
        # Create starter with no backups
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'wide_receiver', 85, depth_order=1
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        wr_need = next((n for n in needs if n['position'] == 'wide_receiver'), None)

        assert wr_need['urgency'] == NeedUrgency.HIGH
        assert "No backup depth" in wr_need['reason']

    def test_medium_weak_depth(self, team_needs_analyzer, test_db_with_schema,
                               test_dynasty_id, test_team_id, test_season):
        """Test MEDIUM urgency when starter is okay but depth is weak."""
        # Starter at threshold+3, but backups well below
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 73, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 62, depth_order=2
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 60, depth_order=3
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        rb_need = next((n for n in needs if n['position'] == 'running_back'), None)

        assert rb_need['urgency'] == NeedUrgency.MEDIUM
        assert "Weak depth" in rb_need['reason']

    def test_low_solid_starter(self, team_needs_analyzer, test_db_with_schema,
                               test_dynasty_id, test_team_id, test_season):
        """Test LOW urgency when starter is solid but not elite."""
        # Starter at 80 (threshold+10 for RB), decent depth
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 80, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 75, depth_order=2
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        rb_need = next((n for n in needs if n['position'] == 'running_back'), None)

        assert rb_need['urgency'] == NeedUrgency.LOW

    def test_none_elite_starter_good_depth(self, team_needs_analyzer, test_db_with_schema,
                                           test_dynasty_id, test_team_id, test_season):
        """Test NONE urgency when position is well-staffed."""
        # Elite starter + good depth
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'cornerback', 90, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'cornerback', 82, depth_order=2
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'cornerback', 78, depth_order=3
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)
        cb_need = next((n for n in needs if n['position'] == 'cornerback'), None)

        # Should not appear in needs list (NONE urgency filtered out)
        assert cb_need is None or cb_need['urgency'] == NeedUrgency.NONE


class TestExpiringContractIntegration:
    """Test integration with Gap 1 expiring contract detection."""

    def test_critical_starter_leaving_no_replacement(self, team_needs_analyzer,
                                                     test_db_with_schema, test_dynasty_id,
                                                     test_team_id, test_season):
        """Test CRITICAL when starter leaving and no adequate replacement."""
        # Create starter with expiring contract
        player_id = insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'left_tackle', 80, depth_order=1
        )

        # Create weak backup
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'left_tackle', 65, depth_order=2
        )

        # Add expiring contract
        cap_api = CapDatabaseAPI(test_db_with_schema)
        cap_api.insert_contract(
            player_id=player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season - 2,
            end_year=test_season,
            contract_years=3,
            contract_type='VETERAN',
            total_value=30_000_000
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season,
                                                       include_future_contracts=True)
        lt_need = next((n for n in needs if n['position'] == 'left_tackle'), None)

        assert lt_need['urgency'] == NeedUrgency.CRITICAL
        assert lt_need['starter_leaving'] is True
        assert "Starter leaving, no replacement" in lt_need['reason']

    def test_high_starter_leaving_with_backup(self, team_needs_analyzer, test_db_with_schema,
                                              test_dynasty_id, test_team_id, test_season):
        """Test HIGH when starter leaving but have decent backup."""
        # Create starter with expiring contract
        player_id = insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'wide_receiver', 85, depth_order=1
        )

        # Create decent backup
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'wide_receiver', 78, depth_order=2
        )

        # Add expiring contract
        cap_api = CapDatabaseAPI(test_db_with_schema)
        cap_api.insert_contract(
            player_id=player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season - 1,
            end_year=test_season,
            contract_years=2,
            contract_type='VETERAN',
            total_value=20_000_000
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season,
                                                       include_future_contracts=True)
        wr_need = next((n for n in needs if n['position'] == 'wide_receiver'), None)

        assert wr_need['urgency'] == NeedUrgency.HIGH
        assert wr_need['starter_leaving'] is True
        assert "Starter leaving" in wr_need['reason']


class TestPositionTierWeighting:
    """Test that position tier affects urgency thresholds."""

    def test_tier1_higher_threshold(self, team_needs_analyzer, test_db_with_schema,
                                    test_dynasty_id, test_team_id, test_season):
        """Test that Tier 1 positions (QB) have higher standards."""
        # Create QB at 72 overall (below 75 threshold for Tier 1) + backup
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'quarterback', 72, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'quarterback', 68, depth_order=2
        )

        # Create RB at 72 overall (above 70 threshold for Tier 3) + backup
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 72, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, test_dynasty_id, test_team_id,
            'running_back', 68, depth_order=2
        )

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)

        qb_need = next((n for n in needs if n['position'] == 'quarterback'), None)
        rb_need = next((n for n in needs if n['position'] == 'running_back'), None)

        # QB should be HIGH (below threshold)
        assert qb_need['urgency'] == NeedUrgency.HIGH

        # RB should be LOW or NONE (above threshold)
        assert rb_need is None or rb_need['urgency'].value <= NeedUrgency.LOW.value


class TestSorting:
    """Test that needs are sorted correctly by urgency + position tier."""

    def test_sorting_by_urgency_then_tier(self, team_needs_analyzer, test_db_with_schema,
                                          test_dynasty_id, test_team_id, test_season):
        """Test needs sorted by urgency first, then position tier."""
        # Create roster with various needs
        players = create_test_roster_with_gaps(test_db_with_schema, test_dynasty_id, test_team_id)

        needs = team_needs_analyzer.analyze_team_needs(test_team_id, test_season)

        # Extract urgency scores
        urgency_scores = [n['urgency_score'] for n in needs]

        # Verify descending order
        assert urgency_scores == sorted(urgency_scores, reverse=True)

        # Verify CRITICAL needs come first
        critical_needs = [n for n in needs if n['urgency'] == NeedUrgency.CRITICAL]
        if critical_needs:
            # All CRITICAL needs should be at the beginning
            first_critical_idx = next(i for i, n in enumerate(needs) if n['urgency'] == NeedUrgency.CRITICAL)
            last_critical_idx = next((i for i, n in enumerate(needs) if n['urgency'] != NeedUrgency.CRITICAL), len(needs)) - 1

            assert first_critical_idx == 0


class TestDynastyIsolation:
    """Test that needs analysis respects dynasty isolation."""

    def test_different_dynasties_isolated(self, test_db_with_schema, test_team_id, test_season):
        """Test that different dynasties have isolated needs analysis."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Initialize full database schema first
        db_conn = DatabaseConnection(test_db_with_schema)
        db_conn.initialize_database()

        # Ensure both dynasties exist
        db_conn.ensure_dynasty_exists(dynasty_1)
        db_conn.ensure_dynasty_exists(dynasty_2)

        # Create different rosters for each dynasty
        # Dynasty 1: Weak QB
        insert_test_player_with_position(
            test_db_with_schema, dynasty_1, test_team_id,
            'quarterback', 65, depth_order=1
        )

        # Dynasty 2: Strong QB with good depth (need 2+ backups for Tier 1 positions)
        insert_test_player_with_position(
            test_db_with_schema, dynasty_2, test_team_id,
            'quarterback', 90, depth_order=1
        )
        insert_test_player_with_position(
            test_db_with_schema, dynasty_2, test_team_id,
            'quarterback', 80, depth_order=2
        )
        insert_test_player_with_position(
            test_db_with_schema, dynasty_2, test_team_id,
            'quarterback', 75, depth_order=3
        )

        # Analyze both
        analyzer_1 = TeamNeedsAnalyzer(test_db_with_schema, dynasty_1)
        analyzer_2 = TeamNeedsAnalyzer(test_db_with_schema, dynasty_2)

        needs_1 = analyzer_1.analyze_team_needs(test_team_id, test_season)
        needs_2 = analyzer_2.analyze_team_needs(test_team_id, test_season)

        qb_need_1 = next((n for n in needs_1 if n['position'] == 'quarterback'), None)
        qb_need_2 = next((n for n in needs_2 if n['position'] == 'quarterback'), None)

        # Dynasty 1 should have CRITICAL QB need
        assert qb_need_1 is not None
        assert qb_need_1['urgency'] == NeedUrgency.CRITICAL

        # Dynasty 2 should have no QB need (or NONE)
        assert qb_need_2 is None or qb_need_2['urgency'] == NeedUrgency.NONE


class TestGetTopNeeds:
    """Test get_top_needs() convenience method."""

    def test_top_needs_limited(self, team_needs_analyzer, test_db_with_schema,
                               test_dynasty_id, test_team_id, test_season):
        """Test that get_top_needs() returns limited results."""
        # Create roster with many needs
        create_test_roster_with_gaps(test_db_with_schema, test_dynasty_id, test_team_id)

        # Get top 3 needs
        top_needs = team_needs_analyzer.get_top_needs(test_team_id, test_season, limit=3)

        assert len(top_needs) <= 3

    def test_top_needs_sorted(self, team_needs_analyzer, test_db_with_schema,
                              test_dynasty_id, test_team_id, test_season):
        """Test that top needs are sorted by urgency."""
        # Create roster with various needs
        create_test_roster_with_gaps(test_db_with_schema, test_dynasty_id, test_team_id)

        top_needs = team_needs_analyzer.get_top_needs(test_team_id, test_season, limit=5)

        # Verify descending urgency
        urgency_scores = [n['urgency_score'] for n in top_needs]
        assert urgency_scores == sorted(urgency_scores, reverse=True)
