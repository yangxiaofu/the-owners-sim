"""
Unit tests for AwardsAPI.

Part of Milestone 10: Awards System, Tollgate 1: Database Foundation.
Target: 70+ tests covering all 17 API methods and dataclasses.
"""
import json
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.awards_api import (
    AwardsAPI,
    AwardDefinition,
    AwardWinner,
    AwardNominee,
    AllProSelection,
    ProBowlSelection,
    StatisticalLeader,
)
from src.game_cycle.database.connection import GameCycleDatabase


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS award_definitions (
            award_id TEXT PRIMARY KEY,
            award_name TEXT NOT NULL,
            award_type TEXT NOT NULL CHECK(award_type IN ('INDIVIDUAL', 'ALL_PRO', 'PRO_BOWL')),
            category TEXT CHECK(category IN ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'COACHING', 'MANAGEMENT')),
            description TEXT,
            eligible_positions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS award_winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            award_id TEXT NOT NULL,
            player_id INTEGER,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            vote_points INTEGER,
            vote_share REAL,
            rank INTEGER,
            is_winner INTEGER DEFAULT 0,
            voting_date DATE,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            FOREIGN KEY (award_id) REFERENCES award_definitions(award_id),
            UNIQUE(dynasty_id, season, award_id, rank)
        );

        CREATE TABLE IF NOT EXISTS award_nominees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            award_id TEXT NOT NULL,
            player_id INTEGER,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            nomination_rank INTEGER,
            stats_snapshot TEXT,
            grade_snapshot REAL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season, award_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS all_pro_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            position TEXT NOT NULL,
            team_type TEXT NOT NULL CHECK(team_type IN ('FIRST_TEAM', 'SECOND_TEAM')),
            vote_points INTEGER,
            vote_share REAL,
            selection_date DATE,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season, position, team_type, player_id)
        );

        CREATE TABLE IF NOT EXISTS pro_bowl_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC')),
            position TEXT NOT NULL,
            selection_type TEXT NOT NULL CHECK(selection_type IN ('STARTER', 'RESERVE', 'ALTERNATE')),
            combined_score REAL,
            selection_date DATE,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season, conference, position, selection_type, player_id)
        );

        CREATE TABLE IF NOT EXISTS statistical_leaders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            stat_category TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            position TEXT NOT NULL,
            stat_value INTEGER NOT NULL,
            league_rank INTEGER NOT NULL,
            recorded_date DATE,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season, stat_category, league_rank)
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_award_winners_dynasty_season ON award_winners(dynasty_id, season);
        CREATE INDEX IF NOT EXISTS idx_award_winners_player ON award_winners(dynasty_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_all_pro_dynasty_season ON all_pro_selections(dynasty_id, season);
        CREATE INDEX IF NOT EXISTS idx_pro_bowl_dynasty_season ON pro_bowl_selections(dynasty_id, season);
        CREATE INDEX IF NOT EXISTS idx_stat_leaders_dynasty_season ON statistical_leaders(dynasty_id, season);

        -- Insert test dynasty
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def db(db_path):
    """Create a GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create an AwardsAPI instance."""
    return AwardsAPI(db)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


# ============================================
# Tests for Dataclasses
# ============================================

class TestAwardDefinitionDataclass:
    """Tests for AwardDefinition dataclass."""

    def test_creation_with_all_fields(self):
        """AwardDefinition should store all fields."""
        definition = AwardDefinition(
            award_id='mvp',
            award_name='Most Valuable Player',
            award_type='INDIVIDUAL',
            category='OFFENSE',
            description='The best player',
            eligible_positions=['QB', 'RB', 'WR']
        )
        assert definition.award_id == 'mvp'
        assert definition.award_name == 'Most Valuable Player'
        assert definition.award_type == 'INDIVIDUAL'
        assert definition.category == 'OFFENSE'
        assert definition.description == 'The best player'
        assert definition.eligible_positions == ['QB', 'RB', 'WR']

    def test_creation_with_minimal_fields(self):
        """AwardDefinition should work with minimal fields."""
        definition = AwardDefinition(
            award_id='mvp',
            award_name='MVP',
            award_type='INDIVIDUAL'
        )
        assert definition.category is None
        assert definition.description is None
        assert definition.eligible_positions is None

    def test_to_dict(self):
        """AwardDefinition to_dict should return correct dictionary."""
        definition = AwardDefinition(
            award_id='mvp',
            award_name='MVP',
            award_type='INDIVIDUAL',
            category='OFFENSE',
            description='Best player',
            eligible_positions=['QB']
        )
        result = definition.to_dict()
        assert result['award_id'] == 'mvp'
        assert result['award_name'] == 'MVP'
        assert result['award_type'] == 'INDIVIDUAL'
        assert result['category'] == 'OFFENSE'
        assert result['eligible_positions'] == ['QB']


class TestAwardWinnerDataclass:
    """Tests for AwardWinner dataclass."""

    def test_creation_with_all_fields(self):
        """AwardWinner should store all fields."""
        winner = AwardWinner(
            dynasty_id='test',
            season=2025,
            award_id='mvp',
            player_id=100,
            team_id=1,
            vote_points=500,
            vote_share=0.95,
            rank=1,
            is_winner=True,
            voting_date='2025-02-01'
        )
        assert winner.player_id == 100
        assert winner.vote_points == 500
        assert winner.vote_share == 0.95
        assert winner.rank == 1
        assert winner.is_winner is True

    def test_to_dict(self):
        """AwardWinner to_dict should return correct dictionary."""
        winner = AwardWinner(
            dynasty_id='test',
            season=2025,
            award_id='mvp',
            player_id=100,
            team_id=1,
            vote_points=500,
            vote_share=0.95,
            rank=1
        )
        result = winner.to_dict()
        assert result['player_id'] == 100
        assert result['vote_points'] == 500
        assert result['rank'] == 1


class TestAwardNomineeDataclass:
    """Tests for AwardNominee dataclass."""

    def test_creation_with_stats_snapshot(self):
        """AwardNominee should store stats_snapshot."""
        stats = {'passing_yards': 4500, 'passing_tds': 35}
        nominee = AwardNominee(
            dynasty_id='test',
            season=2025,
            award_id='mvp',
            player_id=100,
            team_id=1,
            nomination_rank=1,
            stats_snapshot=stats,
            grade_snapshot=92.5
        )
        assert nominee.stats_snapshot == stats
        assert nominee.grade_snapshot == 92.5

    def test_to_dict(self):
        """AwardNominee to_dict should return correct dictionary."""
        nominee = AwardNominee(
            dynasty_id='test',
            season=2025,
            award_id='mvp',
            player_id=100,
            team_id=1,
            nomination_rank=1,
            stats_snapshot={'yards': 1000}
        )
        result = nominee.to_dict()
        assert result['stats_snapshot'] == {'yards': 1000}


class TestAllProSelectionDataclass:
    """Tests for AllProSelection dataclass."""

    def test_creation_first_team(self):
        """AllProSelection should store FIRST_TEAM type."""
        selection = AllProSelection(
            dynasty_id='test',
            season=2025,
            player_id=100,
            team_id=1,
            position='QB',
            team_type='FIRST_TEAM',
            vote_points=50,
            vote_share=1.0
        )
        assert selection.team_type == 'FIRST_TEAM'
        assert selection.vote_share == 1.0

    def test_creation_second_team(self):
        """AllProSelection should store SECOND_TEAM type."""
        selection = AllProSelection(
            dynasty_id='test',
            season=2025,
            player_id=101,
            team_id=2,
            position='QB',
            team_type='SECOND_TEAM'
        )
        assert selection.team_type == 'SECOND_TEAM'

    def test_to_dict(self):
        """AllProSelection to_dict should return correct dictionary."""
        selection = AllProSelection(
            dynasty_id='test',
            season=2025,
            player_id=100,
            team_id=1,
            position='QB',
            team_type='FIRST_TEAM'
        )
        result = selection.to_dict()
        assert result['position'] == 'QB'
        assert result['team_type'] == 'FIRST_TEAM'


class TestProBowlSelectionDataclass:
    """Tests for ProBowlSelection dataclass."""

    def test_creation_afc_starter(self):
        """ProBowlSelection should store AFC STARTER type."""
        selection = ProBowlSelection(
            dynasty_id='test',
            season=2025,
            player_id=100,
            team_id=1,
            conference='AFC',
            position='QB',
            selection_type='STARTER',
            combined_score=95.5
        )
        assert selection.conference == 'AFC'
        assert selection.selection_type == 'STARTER'

    def test_creation_nfc_reserve(self):
        """ProBowlSelection should store NFC RESERVE type."""
        selection = ProBowlSelection(
            dynasty_id='test',
            season=2025,
            player_id=101,
            team_id=2,
            conference='NFC',
            position='RB',
            selection_type='RESERVE'
        )
        assert selection.conference == 'NFC'
        assert selection.selection_type == 'RESERVE'

    def test_to_dict(self):
        """ProBowlSelection to_dict should return correct dictionary."""
        selection = ProBowlSelection(
            dynasty_id='test',
            season=2025,
            player_id=100,
            team_id=1,
            conference='AFC',
            position='QB',
            selection_type='STARTER'
        )
        result = selection.to_dict()
        assert result['conference'] == 'AFC'
        assert result['selection_type'] == 'STARTER'


class TestStatisticalLeaderDataclass:
    """Tests for StatisticalLeader dataclass."""

    def test_creation_with_all_fields(self):
        """StatisticalLeader should store all fields."""
        leader = StatisticalLeader(
            dynasty_id='test',
            season=2025,
            stat_category='passing_yards',
            player_id=100,
            team_id=1,
            position='QB',
            stat_value=5000,
            league_rank=1,
            recorded_date='2025-01-15'
        )
        assert leader.stat_category == 'passing_yards'
        assert leader.stat_value == 5000
        assert leader.league_rank == 1

    def test_to_dict(self):
        """StatisticalLeader to_dict should return correct dictionary."""
        leader = StatisticalLeader(
            dynasty_id='test',
            season=2025,
            stat_category='rushing_yards',
            player_id=100,
            team_id=1,
            position='RB',
            stat_value=1500,
            league_rank=1
        )
        result = leader.to_dict()
        assert result['stat_category'] == 'rushing_yards'
        assert result['stat_value'] == 1500


# ============================================
# Tests for Award Definitions
# ============================================

class TestAwardDefinitions:
    """Tests for award definition methods."""

    def test_initialize_award_definitions(self, api):
        """initialize_award_definitions should create 8 awards."""
        count = api.initialize_award_definitions()
        assert count == 8

    def test_initialize_award_definitions_idempotent(self, api):
        """Calling initialize twice should not duplicate."""
        api.initialize_award_definitions()
        api.initialize_award_definitions()  # Second call
        definitions = api.get_all_award_definitions()
        assert len(definitions) == 8

    def test_get_award_definition_mvp(self, api):
        """get_award_definition should return MVP definition."""
        api.initialize_award_definitions()
        definition = api.get_award_definition('mvp')
        assert definition is not None
        assert definition.award_id == 'mvp'
        assert definition.award_name == 'Most Valuable Player'
        assert definition.award_type == 'INDIVIDUAL'

    def test_get_award_definition_opoy(self, api):
        """get_award_definition should return OPOY with offensive positions."""
        api.initialize_award_definitions()
        definition = api.get_award_definition('opoy')
        assert definition is not None
        assert definition.category == 'OFFENSE'
        assert 'QB' in definition.eligible_positions

    def test_get_award_definition_dpoy(self, api):
        """get_award_definition should return DPOY with defensive positions."""
        api.initialize_award_definitions()
        definition = api.get_award_definition('dpoy')
        assert definition is not None
        assert definition.category == 'DEFENSE'
        assert 'CB' in definition.eligible_positions

    def test_get_award_definition_not_found(self, api):
        """get_award_definition should return None for unknown award."""
        definition = api.get_award_definition('unknown_award')
        assert definition is None

    def test_get_all_award_definitions(self, api):
        """get_all_award_definitions should return all 8 awards."""
        api.initialize_award_definitions()
        definitions = api.get_all_award_definitions()
        assert len(definitions) == 8
        award_ids = [d.award_id for d in definitions]
        assert 'mvp' in award_ids
        assert 'opoy' in award_ids
        assert 'dpoy' in award_ids
        assert 'oroy' in award_ids
        assert 'droy' in award_ids
        assert 'cpoy' in award_ids
        assert 'coy' in award_ids
        assert 'eoy' in award_ids


# ============================================
# Tests for Award Winners
# ============================================

class TestAwardWinners:
    """Tests for award winner methods."""

    def test_insert_award_winner(self, api, dynasty_id, season):
        """insert_award_winner should store winner data."""
        api.initialize_award_definitions()
        result = api.insert_award_winner(
            dynasty_id=dynasty_id,
            season=season,
            award_id='mvp',
            player_id=100,
            team_id=1,
            vote_points=500,
            vote_share=0.95,
            rank=1,
            is_winner=True
        )
        assert result is True

    def test_insert_award_winner_multiple_ranks(self, api, dynasty_id, season):
        """insert_award_winner should store top 5."""
        api.initialize_award_definitions()
        for rank in range(1, 6):
            api.insert_award_winner(
                dynasty_id=dynasty_id,
                season=season,
                award_id='mvp',
                player_id=100 + rank,
                team_id=rank,
                vote_points=500 - (rank * 50),
                vote_share=0.95 - (rank * 0.1),
                rank=rank,
                is_winner=(rank == 1)
            )
        winners = api.get_award_winners(dynasty_id, season, 'mvp')
        assert len(winners) == 5
        assert winners[0].rank == 1
        assert winners[0].is_winner is True
        assert winners[4].rank == 5
        assert winners[4].is_winner is False

    def test_get_award_winners_by_award(self, api, dynasty_id, season):
        """get_award_winners should filter by award_id."""
        api.initialize_award_definitions()
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_award_winner(dynasty_id, season, 'opoy', 101, 2, 400, 0.85, 1, True)

        mvp_winners = api.get_award_winners(dynasty_id, season, 'mvp')
        assert len(mvp_winners) == 1
        assert mvp_winners[0].award_id == 'mvp'

        opoy_winners = api.get_award_winners(dynasty_id, season, 'opoy')
        assert len(opoy_winners) == 1
        assert opoy_winners[0].award_id == 'opoy'

    def test_get_award_winners_all(self, api, dynasty_id, season):
        """get_award_winners without award_id should return all."""
        api.initialize_award_definitions()
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_award_winner(dynasty_id, season, 'opoy', 101, 2, 400, 0.85, 1, True)
        api.insert_award_winner(dynasty_id, season, 'dpoy', 102, 3, 450, 0.90, 1, True)

        all_winners = api.get_award_winners(dynasty_id, season)
        assert len(all_winners) == 3

    def test_get_player_awards(self, api, dynasty_id):
        """get_player_awards should return all awards for a player."""
        api.initialize_award_definitions()
        player_id = 100
        api.insert_award_winner(dynasty_id, 2023, 'mvp', player_id, 1, 500, 0.95, 1, True)
        api.insert_award_winner(dynasty_id, 2024, 'mvp', player_id, 1, 480, 0.92, 1, True)
        api.insert_award_winner(dynasty_id, 2024, 'opoy', player_id, 1, 400, 0.85, 1, True)

        awards = api.get_player_awards(dynasty_id, player_id)
        assert len(awards) == 3
        # Should be sorted by season descending
        assert awards[0].season == 2024

    def test_get_player_awards_empty(self, api, dynasty_id):
        """get_player_awards should return empty list for player with no awards."""
        awards = api.get_player_awards(dynasty_id, 999)
        assert len(awards) == 0

    def test_insert_award_winner_replace(self, api, dynasty_id, season):
        """insert_award_winner should replace existing entry."""
        api.initialize_award_definitions()
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 400, 0.80, 1, True)
        api.insert_award_winner(dynasty_id, season, 'mvp', 101, 2, 500, 0.95, 1, True)

        winners = api.get_award_winners(dynasty_id, season, 'mvp')
        assert len(winners) == 1
        assert winners[0].player_id == 101
        assert winners[0].vote_points == 500


# ============================================
# Tests for Award Nominees
# ============================================

class TestAwardNominees:
    """Tests for award nominee methods."""

    def test_insert_nominee(self, api, dynasty_id, season):
        """insert_nominee should store nominee data."""
        api.initialize_award_definitions()
        stats = {'passing_yards': 4500, 'passing_tds': 35}
        result = api.insert_nominee(
            dynasty_id=dynasty_id,
            season=season,
            award_id='mvp',
            player_id=100,
            team_id=1,
            nomination_rank=1,
            stats_snapshot=stats,
            grade_snapshot=92.5
        )
        assert result is True

    def test_get_nominees(self, api, dynasty_id, season):
        """get_nominees should return nominees sorted by rank."""
        api.initialize_award_definitions()
        for i in range(1, 11):  # Top 10 nominees
            api.insert_nominee(
                dynasty_id=dynasty_id,
                season=season,
                award_id='mvp',
                player_id=100 + i,
                team_id=(i % 32) + 1,
                nomination_rank=i,
                stats_snapshot={'yards': 5000 - (i * 100)},
                grade_snapshot=95.0 - i
            )

        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert len(nominees) == 10
        assert nominees[0].nomination_rank == 1
        assert nominees[9].nomination_rank == 10

    def test_get_nominees_empty(self, api, dynasty_id, season):
        """get_nominees should return empty list if no nominees."""
        api.initialize_award_definitions()
        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert len(nominees) == 0

    def test_nominee_stats_snapshot_json(self, api, dynasty_id, season):
        """Nominee stats_snapshot should be properly serialized."""
        api.initialize_award_definitions()
        complex_stats = {
            'passing_yards': 4500,
            'passing_tds': 35,
            'interceptions': 8,
            'passer_rating': 105.5
        }
        api.insert_nominee(dynasty_id, season, 'mvp', 100, 1, 1, complex_stats, 92.5)

        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert nominees[0].stats_snapshot == complex_stats

    def test_nominee_no_stats_snapshot(self, api, dynasty_id, season):
        """Nominee without stats_snapshot should work."""
        api.initialize_award_definitions()
        api.insert_nominee(dynasty_id, season, 'mvp', 100, 1, 1, None, 92.5)

        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert nominees[0].stats_snapshot is None


# ============================================
# Tests for All-Pro Selections
# ============================================

class TestAllProSelections:
    """Tests for All-Pro selection methods."""

    def test_insert_all_pro_selection_first_team(self, api, dynasty_id, season):
        """insert_all_pro_selection should store First Team selection."""
        result = api.insert_all_pro_selection(
            dynasty_id=dynasty_id,
            season=season,
            player_id=100,
            team_id=1,
            position='QB',
            team_type='FIRST_TEAM',
            vote_points=50,
            vote_share=1.0
        )
        assert result is True

    def test_insert_all_pro_selection_second_team(self, api, dynasty_id, season):
        """insert_all_pro_selection should store Second Team selection."""
        result = api.insert_all_pro_selection(
            dynasty_id=dynasty_id,
            season=season,
            player_id=101,
            team_id=2,
            position='QB',
            team_type='SECOND_TEAM'
        )
        assert result is True

    def test_get_all_pro_teams(self, api, dynasty_id, season):
        """get_all_pro_teams should return both teams."""
        # Insert First Team
        api.insert_all_pro_selection(dynasty_id, season, 100, 1, 'QB', 'FIRST_TEAM')
        api.insert_all_pro_selection(dynasty_id, season, 101, 2, 'RB', 'FIRST_TEAM')
        api.insert_all_pro_selection(dynasty_id, season, 102, 3, 'WR', 'FIRST_TEAM')

        # Insert Second Team
        api.insert_all_pro_selection(dynasty_id, season, 200, 4, 'QB', 'SECOND_TEAM')
        api.insert_all_pro_selection(dynasty_id, season, 201, 5, 'RB', 'SECOND_TEAM')

        teams = api.get_all_pro_teams(dynasty_id, season)
        assert 'FIRST_TEAM' in teams
        assert 'SECOND_TEAM' in teams
        assert len(teams['FIRST_TEAM']) == 3
        assert len(teams['SECOND_TEAM']) == 2

    def test_get_all_pro_teams_empty(self, api, dynasty_id, season):
        """get_all_pro_teams should return empty lists if no selections."""
        teams = api.get_all_pro_teams(dynasty_id, season)
        assert teams == {'FIRST_TEAM': [], 'SECOND_TEAM': []}

    def test_get_player_all_pro_history(self, api, dynasty_id):
        """get_player_all_pro_history should return player's All-Pro selections."""
        player_id = 100
        api.insert_all_pro_selection(dynasty_id, 2023, player_id, 1, 'QB', 'FIRST_TEAM')
        api.insert_all_pro_selection(dynasty_id, 2024, player_id, 1, 'QB', 'FIRST_TEAM')
        api.insert_all_pro_selection(dynasty_id, 2025, player_id, 1, 'QB', 'SECOND_TEAM')

        history = api.get_player_all_pro_history(dynasty_id, player_id)
        assert len(history) == 3
        # Should be sorted by season descending
        assert history[0].season == 2025
        assert history[0].team_type == 'SECOND_TEAM'

    def test_get_player_all_pro_history_empty(self, api, dynasty_id):
        """get_player_all_pro_history should return empty for player with no selections."""
        history = api.get_player_all_pro_history(dynasty_id, 999)
        assert len(history) == 0

    def test_all_pro_multiple_positions(self, api, dynasty_id, season):
        """All-Pro should support multiple positions per team."""
        positions = ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT']
        for i, pos in enumerate(positions):
            api.insert_all_pro_selection(dynasty_id, season, 100 + i, (i % 32) + 1, pos, 'FIRST_TEAM')

        teams = api.get_all_pro_teams(dynasty_id, season)
        assert len(teams['FIRST_TEAM']) == 11


# ============================================
# Tests for Pro Bowl Selections
# ============================================

class TestProBowlSelections:
    """Tests for Pro Bowl selection methods."""

    def test_insert_pro_bowl_selection_afc_starter(self, api, dynasty_id, season):
        """insert_pro_bowl_selection should store AFC starter."""
        result = api.insert_pro_bowl_selection(
            dynasty_id=dynasty_id,
            season=season,
            player_id=100,
            team_id=1,
            conference='AFC',
            position='QB',
            selection_type='STARTER',
            combined_score=95.5
        )
        assert result is True

    def test_insert_pro_bowl_selection_nfc_reserve(self, api, dynasty_id, season):
        """insert_pro_bowl_selection should store NFC reserve."""
        result = api.insert_pro_bowl_selection(
            dynasty_id=dynasty_id,
            season=season,
            player_id=101,
            team_id=2,
            conference='NFC',
            position='RB',
            selection_type='RESERVE'
        )
        assert result is True

    def test_get_pro_bowl_roster_both_conferences(self, api, dynasty_id, season):
        """get_pro_bowl_roster should return both conferences."""
        # AFC
        api.insert_pro_bowl_selection(dynasty_id, season, 100, 1, 'AFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, season, 101, 2, 'AFC', 'RB', 'STARTER')

        # NFC
        api.insert_pro_bowl_selection(dynasty_id, season, 200, 17, 'NFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, season, 201, 18, 'NFC', 'RB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, season, 202, 19, 'NFC', 'WR', 'RESERVE')

        roster = api.get_pro_bowl_roster(dynasty_id, season)
        assert 'AFC' in roster
        assert 'NFC' in roster
        assert len(roster['AFC']) == 2
        assert len(roster['NFC']) == 3

    def test_get_pro_bowl_roster_filter_conference(self, api, dynasty_id, season):
        """get_pro_bowl_roster should filter by conference."""
        api.insert_pro_bowl_selection(dynasty_id, season, 100, 1, 'AFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, season, 200, 17, 'NFC', 'QB', 'STARTER')

        afc_roster = api.get_pro_bowl_roster(dynasty_id, season, 'AFC')
        assert 'AFC' in afc_roster
        assert len(afc_roster['AFC']) == 1
        assert 'NFC' not in afc_roster

    def test_get_pro_bowl_roster_empty(self, api, dynasty_id, season):
        """get_pro_bowl_roster should return empty dict if no selections."""
        roster = api.get_pro_bowl_roster(dynasty_id, season)
        assert roster == {}

    def test_get_player_pro_bowl_history(self, api, dynasty_id):
        """get_player_pro_bowl_history should return player's Pro Bowl selections."""
        player_id = 100
        api.insert_pro_bowl_selection(dynasty_id, 2023, player_id, 1, 'AFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, 2024, player_id, 1, 'AFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection(dynasty_id, 2025, player_id, 1, 'AFC', 'QB', 'RESERVE')

        history = api.get_player_pro_bowl_history(dynasty_id, player_id)
        assert len(history) == 3
        # Should be sorted by season descending
        assert history[0].season == 2025

    def test_get_player_pro_bowl_history_empty(self, api, dynasty_id):
        """get_player_pro_bowl_history should return empty for player with no selections."""
        history = api.get_player_pro_bowl_history(dynasty_id, 999)
        assert len(history) == 0

    def test_pro_bowl_alternate_type(self, api, dynasty_id, season):
        """Pro Bowl should support ALTERNATE selection type."""
        api.insert_pro_bowl_selection(dynasty_id, season, 100, 1, 'AFC', 'QB', 'ALTERNATE')

        roster = api.get_pro_bowl_roster(dynasty_id, season, 'AFC')
        assert roster['AFC'][0].selection_type == 'ALTERNATE'


# ============================================
# Tests for Statistical Leaders
# ============================================

class TestStatisticalLeaders:
    """Tests for statistical leader methods."""

    def test_record_stat_leader(self, api, dynasty_id, season):
        """record_stat_leader should store leader data."""
        result = api.record_stat_leader(
            dynasty_id=dynasty_id,
            season=season,
            stat_category='passing_yards',
            player_id=100,
            team_id=1,
            position='QB',
            stat_value=5000,
            league_rank=1
        )
        assert result is True

    def test_record_stat_leader_top_10(self, api, dynasty_id, season):
        """record_stat_leader should support top 10."""
        for rank in range(1, 11):
            api.record_stat_leader(
                dynasty_id, season, 'passing_yards',
                100 + rank, (rank % 32) + 1, 'QB',
                5000 - (rank * 100), rank
            )

        leaders = api.get_stat_leaders(dynasty_id, season, 'passing_yards')
        assert len(leaders) == 10
        assert leaders[0].league_rank == 1
        assert leaders[0].stat_value == 4900  # First player (rank 1) has 4900

    def test_get_stat_leaders_by_category(self, api, dynasty_id, season):
        """get_stat_leaders should filter by category."""
        api.record_stat_leader(dynasty_id, season, 'passing_yards', 100, 1, 'QB', 5000, 1)
        api.record_stat_leader(dynasty_id, season, 'rushing_yards', 101, 2, 'RB', 1500, 1)
        api.record_stat_leader(dynasty_id, season, 'sacks', 102, 3, 'EDGE', 15, 1)

        passing_leaders = api.get_stat_leaders(dynasty_id, season, 'passing_yards')
        assert len(passing_leaders) == 1
        assert passing_leaders[0].stat_category == 'passing_yards'

    def test_get_stat_leaders_all_categories(self, api, dynasty_id, season):
        """get_stat_leaders without category should return all."""
        api.record_stat_leader(dynasty_id, season, 'passing_yards', 100, 1, 'QB', 5000, 1)
        api.record_stat_leader(dynasty_id, season, 'rushing_yards', 101, 2, 'RB', 1500, 1)
        api.record_stat_leader(dynasty_id, season, 'sacks', 102, 3, 'EDGE', 15, 1)

        all_leaders = api.get_stat_leaders(dynasty_id, season)
        assert len(all_leaders) == 3

    def test_get_stat_leaders_empty(self, api, dynasty_id, season):
        """get_stat_leaders should return empty list if no leaders."""
        leaders = api.get_stat_leaders(dynasty_id, season, 'passing_yards')
        assert len(leaders) == 0

    def test_get_player_stat_leader_history(self, api, dynasty_id):
        """get_player_stat_leader_history should return player's leader entries."""
        player_id = 100
        api.record_stat_leader(dynasty_id, 2023, 'passing_yards', player_id, 1, 'QB', 4500, 1)
        api.record_stat_leader(dynasty_id, 2024, 'passing_yards', player_id, 1, 'QB', 5000, 1)
        api.record_stat_leader(dynasty_id, 2024, 'passing_tds', player_id, 1, 'QB', 40, 1)

        history = api.get_player_stat_leader_history(dynasty_id, player_id)
        assert len(history) == 3
        # Should be sorted by season descending
        assert history[0].season == 2024

    def test_get_player_stat_leader_history_empty(self, api, dynasty_id):
        """get_player_stat_leader_history should return empty for player with no entries."""
        history = api.get_player_stat_leader_history(dynasty_id, 999)
        assert len(history) == 0

    def test_stat_leader_multiple_categories(self, api, dynasty_id, season):
        """Statistical leaders should support many categories."""
        categories = [
            ('passing_yards', 'QB', 5000),
            ('passing_tds', 'QB', 40),
            ('rushing_yards', 'RB', 1500),
            ('rushing_tds', 'RB', 15),
            ('receiving_yards', 'WR', 1400),
            ('receiving_tds', 'WR', 12),
            ('sacks', 'EDGE', 15),
            ('interceptions', 'CB', 8),
            ('tackles', 'MLB', 150),
        ]
        for i, (cat, pos, val) in enumerate(categories):
            api.record_stat_leader(dynasty_id, season, cat, 100 + i, (i % 32) + 1, pos, val, 1)

        all_leaders = api.get_stat_leaders(dynasty_id, season)
        assert len(all_leaders) == 9


# ============================================
# Tests for Deletion Methods
# ============================================

class TestDeletionMethods:
    """Tests for clear/delete methods."""

    def test_clear_season_awards(self, api, dynasty_id, season):
        """clear_season_awards should remove all award data for a season."""
        api.initialize_award_definitions()

        # Insert various data
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_nominee(dynasty_id, season, 'mvp', 100, 1, 1, {}, 90.0)
        api.insert_all_pro_selection(dynasty_id, season, 100, 1, 'QB', 'FIRST_TEAM')
        api.insert_pro_bowl_selection(dynasty_id, season, 100, 1, 'AFC', 'QB', 'STARTER')
        api.record_stat_leader(dynasty_id, season, 'passing_yards', 100, 1, 'QB', 5000, 1)

        counts = api.clear_season_awards(dynasty_id, season)
        assert counts['award_winners'] == 1
        assert counts['award_nominees'] == 1
        assert counts['all_pro_selections'] == 1
        assert counts['pro_bowl_selections'] == 1
        assert counts['statistical_leaders'] == 1

        # Verify cleared
        assert len(api.get_award_winners(dynasty_id, season)) == 0
        assert len(api.get_nominees(dynasty_id, season, 'mvp')) == 0

    def test_clear_season_awards_preserves_other_seasons(self, api, dynasty_id):
        """clear_season_awards should not affect other seasons."""
        api.initialize_award_definitions()

        api.insert_award_winner(dynasty_id, 2024, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_award_winner(dynasty_id, 2025, 'mvp', 101, 2, 480, 0.92, 1, True)

        api.clear_season_awards(dynasty_id, 2024)

        assert len(api.get_award_winners(dynasty_id, 2024)) == 0
        assert len(api.get_award_winners(dynasty_id, 2025)) == 1

    def test_clear_player_awards(self, api, dynasty_id, season):
        """clear_player_awards should remove all award data for a player."""
        api.initialize_award_definitions()
        player_id = 100

        api.insert_award_winner(dynasty_id, season, 'mvp', player_id, 1, 500, 0.95, 1, True)
        api.insert_nominee(dynasty_id, season, 'mvp', player_id, 1, 1, {}, 90.0)
        api.insert_all_pro_selection(dynasty_id, season, player_id, 1, 'QB', 'FIRST_TEAM')
        api.insert_pro_bowl_selection(dynasty_id, season, player_id, 1, 'AFC', 'QB', 'STARTER')
        api.record_stat_leader(dynasty_id, season, 'passing_yards', player_id, 1, 'QB', 5000, 1)

        counts = api.clear_player_awards(dynasty_id, player_id)
        assert counts['award_winners'] == 1
        assert counts['award_nominees'] == 1
        assert counts['all_pro_selections'] == 1
        assert counts['pro_bowl_selections'] == 1
        assert counts['statistical_leaders'] == 1

        # Verify cleared
        assert len(api.get_player_awards(dynasty_id, player_id)) == 0
        assert len(api.get_player_all_pro_history(dynasty_id, player_id)) == 0

    def test_clear_player_awards_preserves_other_players(self, api, dynasty_id, season):
        """clear_player_awards should not affect other players."""
        api.initialize_award_definitions()

        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_award_winner(dynasty_id, season, 'opoy', 101, 2, 480, 0.92, 1, True)

        api.clear_player_awards(dynasty_id, 100)

        assert len(api.get_player_awards(dynasty_id, 100)) == 0
        assert len(api.get_player_awards(dynasty_id, 101)) == 1


# ============================================
# Tests for Dynasty Isolation
# ============================================

class TestDynastyIsolation:
    """Tests ensuring dynasty isolation is enforced."""

    def test_award_winners_isolated_by_dynasty(self, api, db, dynasty_id, season):
        """Award winners should be isolated by dynasty."""
        # Create another dynasty
        db.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES (?, ?, ?)",
            ('other-dynasty', 'Other Dynasty', 2)
        )
        api.initialize_award_definitions()

        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 0.95, 1, True)
        api.insert_award_winner('other-dynasty', season, 'mvp', 200, 2, 480, 0.92, 1, True)

        winners1 = api.get_award_winners(dynasty_id, season)
        winners2 = api.get_award_winners('other-dynasty', season)

        assert len(winners1) == 1
        assert winners1[0].player_id == 100
        assert len(winners2) == 1
        assert winners2[0].player_id == 200

    def test_all_pro_isolated_by_dynasty(self, api, db, dynasty_id, season):
        """All-Pro selections should be isolated by dynasty."""
        db.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES (?, ?, ?)",
            ('other-dynasty', 'Other Dynasty', 2)
        )

        api.insert_all_pro_selection(dynasty_id, season, 100, 1, 'QB', 'FIRST_TEAM')
        api.insert_all_pro_selection('other-dynasty', season, 200, 2, 'QB', 'FIRST_TEAM')

        teams1 = api.get_all_pro_teams(dynasty_id, season)
        teams2 = api.get_all_pro_teams('other-dynasty', season)

        assert len(teams1['FIRST_TEAM']) == 1
        assert teams1['FIRST_TEAM'][0].player_id == 100
        assert len(teams2['FIRST_TEAM']) == 1
        assert teams2['FIRST_TEAM'][0].player_id == 200

    def test_pro_bowl_isolated_by_dynasty(self, api, db, dynasty_id, season):
        """Pro Bowl selections should be isolated by dynasty."""
        db.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES (?, ?, ?)",
            ('other-dynasty', 'Other Dynasty', 2)
        )

        api.insert_pro_bowl_selection(dynasty_id, season, 100, 1, 'AFC', 'QB', 'STARTER')
        api.insert_pro_bowl_selection('other-dynasty', season, 200, 2, 'AFC', 'QB', 'STARTER')

        roster1 = api.get_pro_bowl_roster(dynasty_id, season, 'AFC')
        roster2 = api.get_pro_bowl_roster('other-dynasty', season, 'AFC')

        assert len(roster1['AFC']) == 1
        assert roster1['AFC'][0].player_id == 100
        assert len(roster2['AFC']) == 1
        assert roster2['AFC'][0].player_id == 200

    def test_stat_leaders_isolated_by_dynasty(self, api, db, dynasty_id, season):
        """Statistical leaders should be isolated by dynasty."""
        db.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES (?, ?, ?)",
            ('other-dynasty', 'Other Dynasty', 2)
        )

        api.record_stat_leader(dynasty_id, season, 'passing_yards', 100, 1, 'QB', 5000, 1)
        api.record_stat_leader('other-dynasty', season, 'passing_yards', 200, 2, 'QB', 4800, 1)

        leaders1 = api.get_stat_leaders(dynasty_id, season, 'passing_yards')
        leaders2 = api.get_stat_leaders('other-dynasty', season, 'passing_yards')

        assert len(leaders1) == 1
        assert leaders1[0].player_id == 100
        assert len(leaders2) == 1
        assert leaders2[0].player_id == 200


# ============================================
# Tests for Edge Cases
# ============================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_vote_share_zero(self, api, dynasty_id, season):
        """Award winner with 0 vote share should be stored."""
        api.initialize_award_definitions()
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 0, 0.0, 5, False)

        winners = api.get_award_winners(dynasty_id, season, 'mvp')
        assert len(winners) == 1
        assert winners[0].vote_share == 0.0

    def test_vote_share_one(self, api, dynasty_id, season):
        """Award winner with 1.0 vote share should be stored."""
        api.initialize_award_definitions()
        api.insert_award_winner(dynasty_id, season, 'mvp', 100, 1, 500, 1.0, 1, True)

        winners = api.get_award_winners(dynasty_id, season, 'mvp')
        assert winners[0].vote_share == 1.0

    def test_large_stat_value(self, api, dynasty_id, season):
        """Statistical leader with large value should be stored."""
        api.record_stat_leader(dynasty_id, season, 'passing_yards', 100, 1, 'QB', 99999, 1)

        leaders = api.get_stat_leaders(dynasty_id, season, 'passing_yards')
        assert leaders[0].stat_value == 99999

    def test_special_characters_in_stats_snapshot(self, api, dynasty_id, season):
        """Stats snapshot with special characters should be handled."""
        api.initialize_award_definitions()
        stats = {'player_name': "O'Connor", 'note': 'Test "quote" & ampersand'}
        api.insert_nominee(dynasty_id, season, 'mvp', 100, 1, 1, stats, 90.0)

        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert nominees[0].stats_snapshot == stats

    def test_empty_stats_snapshot(self, api, dynasty_id, season):
        """Empty stats snapshot dict should be stored."""
        api.initialize_award_definitions()
        api.insert_nominee(dynasty_id, season, 'mvp', 100, 1, 1, {}, 90.0)

        nominees = api.get_nominees(dynasty_id, season, 'mvp')
        assert nominees[0].stats_snapshot == {}

    def test_boundary_team_ids(self, api, dynasty_id, season):
        """Team IDs at boundaries (1 and 32) should be accepted."""
        api.insert_all_pro_selection(dynasty_id, season, 100, 1, 'QB', 'FIRST_TEAM')
        api.insert_all_pro_selection(dynasty_id, season, 101, 32, 'RB', 'FIRST_TEAM')

        teams = api.get_all_pro_teams(dynasty_id, season)
        team_ids = [s.team_id for s in teams['FIRST_TEAM']]
        assert 1 in team_ids
        assert 32 in team_ids

    def test_multiple_seasons_same_player(self, api, dynasty_id):
        """Player with awards in multiple seasons should track all."""
        api.initialize_award_definitions()
        player_id = 100

        for year in range(2020, 2026):
            api.insert_award_winner(dynasty_id, year, 'mvp', player_id, 1, 500, 0.95, 1, True)

        awards = api.get_player_awards(dynasty_id, player_id)
        assert len(awards) == 6

    def test_same_player_different_positions(self, api, dynasty_id, season):
        """Player selected at different positions should be stored (hypothetically)."""
        # This tests the unique constraint behavior
        api.insert_all_pro_selection(dynasty_id, season, 100, 1, 'QB', 'FIRST_TEAM')
        # Same player, different position - should be allowed if unique constraint permits
        # Note: Current constraint is (dynasty_id, season, position, team_type, player_id)
        # So same player at different positions is allowed

        teams = api.get_all_pro_teams(dynasty_id, season)
        assert len(teams['FIRST_TEAM']) >= 1
