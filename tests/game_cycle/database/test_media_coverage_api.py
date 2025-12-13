"""
Unit tests for MediaCoverageAPI.

Tests all CRUD operations for:
- Power rankings
- Headlines
- Narrative arcs
- Press quotes

Part of Milestone 12: Media Coverage, Tollgate 1.
"""

import pytest
import tempfile
import os
import sqlite3
from pathlib import Path

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.media_coverage_api import (
    MediaCoverageAPI,
    PowerRanking,
    Headline,
    NarrativeArc,
    PressQuote
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables directly with sqlite3 (not GameCycleDatabase)
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL DEFAULT 1,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS power_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            previous_rank INTEGER,
            tier TEXT NOT NULL,
            blurb TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, season, week, team_id)
        );

        CREATE TABLE IF NOT EXISTS media_headlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            headline_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            subheadline TEXT,
            body_text TEXT,
            sentiment TEXT,
            priority INTEGER DEFAULT 50,
            team_ids TEXT,
            player_ids TEXT,
            game_id TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS narrative_arcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            arc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'ACTIVE',
            start_week INTEGER NOT NULL,
            end_week INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS press_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            quote_type TEXT NOT NULL,
            speaker_type TEXT NOT NULL,
            speaker_id INTEGER,
            team_id INTEGER,
            quote_text TEXT NOT NULL,
            context TEXT,
            sentiment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Insert test dynasties
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test_dynasty', 'Test Dynasty', 1);
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other Dynasty', 2);
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
    """Create MediaCoverageAPI instance."""
    return MediaCoverageAPI(db)


# ==========================================
# POWER RANKINGS TESTS
# ==========================================

class TestPowerRankings:
    """Tests for power rankings CRUD operations."""

    def test_save_power_rankings(self, api):
        """Test saving power rankings for all teams."""
        rankings = [
            {'team_id': 1, 'rank': 1, 'tier': 'ELITE', 'blurb': 'Chiefs are dominant'},
            {'team_id': 2, 'rank': 2, 'tier': 'ELITE', 'blurb': 'Lions are contenders'},
            {'team_id': 3, 'rank': 3, 'tier': 'CONTENDER', 'previous_rank': 5},
        ]

        count = api.save_power_rankings('test_dynasty', 2025, 1, rankings)

        assert count == 3

        # Verify saved
        result = api.get_power_rankings('test_dynasty', 2025, 1)
        assert len(result) == 3
        assert result[0].rank == 1
        assert result[0].tier == 'ELITE'
        assert result[0].blurb == 'Chiefs are dominant'

    def test_get_power_rankings_sorted_by_rank(self, api):
        """Test that rankings are returned sorted by rank."""
        rankings = [
            {'team_id': 5, 'rank': 3, 'tier': 'CONTENDER'},
            {'team_id': 1, 'rank': 1, 'tier': 'ELITE'},
            {'team_id': 10, 'rank': 2, 'tier': 'ELITE'},
        ]
        api.save_power_rankings('test_dynasty', 2025, 1, rankings)

        result = api.get_power_rankings('test_dynasty', 2025, 1)

        assert result[0].rank == 1
        assert result[1].rank == 2
        assert result[2].rank == 3

    def test_get_team_ranking_history(self, api):
        """Test getting a team's ranking across weeks."""
        # Save rankings for multiple weeks
        api.save_power_rankings('test_dynasty', 2025, 1, [
            {'team_id': 1, 'rank': 5, 'tier': 'CONTENDER'}
        ])
        api.save_power_rankings('test_dynasty', 2025, 2, [
            {'team_id': 1, 'rank': 3, 'previous_rank': 5, 'tier': 'CONTENDER'}
        ])
        api.save_power_rankings('test_dynasty', 2025, 3, [
            {'team_id': 1, 'rank': 1, 'previous_rank': 3, 'tier': 'ELITE'}
        ])

        history = api.get_team_ranking_history('test_dynasty', 2025, 1)

        assert len(history) == 3
        assert history[0].week == 1
        assert history[0].rank == 5
        assert history[2].week == 3
        assert history[2].rank == 1

    def test_power_ranking_movement_property(self, api):
        """Test the movement property on PowerRanking."""
        api.save_power_rankings('test_dynasty', 2025, 2, [
            {'team_id': 1, 'rank': 3, 'previous_rank': 5, 'tier': 'CONTENDER'},
            {'team_id': 2, 'rank': 5, 'previous_rank': 3, 'tier': 'PLAYOFF'},
            {'team_id': 3, 'rank': 10, 'previous_rank': 10, 'tier': 'BUBBLE'},
            {'team_id': 4, 'rank': 1, 'tier': 'ELITE'},  # No previous (NEW)
        ])

        rankings = api.get_power_rankings('test_dynasty', 2025, 2)
        ranking_by_team = {r.team_id: r for r in rankings}

        assert ranking_by_team[1].movement == '▲2'  # Moved up 2
        assert ranking_by_team[2].movement == '▼2'  # Moved down 2
        assert ranking_by_team[3].movement == '—'   # No change
        assert ranking_by_team[4].movement == 'NEW' # No previous

    def test_get_latest_team_ranking(self, api):
        """Test getting a team's most recent ranking."""
        api.save_power_rankings('test_dynasty', 2025, 1, [
            {'team_id': 1, 'rank': 10, 'tier': 'BUBBLE'}
        ])
        api.save_power_rankings('test_dynasty', 2025, 5, [
            {'team_id': 1, 'rank': 3, 'tier': 'CONTENDER'}
        ])

        latest = api.get_latest_team_ranking('test_dynasty', 2025, 1)

        assert latest is not None
        assert latest.week == 5
        assert latest.rank == 3


# ==========================================
# HEADLINES TESTS
# ==========================================

class TestHeadlines:
    """Tests for headlines CRUD operations."""

    def test_save_headline(self, api):
        """Test saving a single headline."""
        headline_data = {
            'headline_type': 'GAME_RECAP',
            'headline': 'Chiefs Dominate Bills 35-14',
            'subheadline': 'Mahomes throws 4 TDs in dominant win',
            'body_text': 'The Kansas City Chiefs...',
            'sentiment': 'POSITIVE',
            'priority': 80,
            'team_ids': [1, 2],
            'player_ids': [101, 102],
            'game_id': 'game_123'
        }

        headline_id = api.save_headline('test_dynasty', 2025, 5, headline_data)

        assert headline_id > 0

        # Verify saved
        headlines = api.get_headlines('test_dynasty', 2025, 5)
        assert len(headlines) == 1
        assert headlines[0].headline == 'Chiefs Dominate Bills 35-14'
        assert headlines[0].team_ids == [1, 2]

    def test_save_headline_requires_type_and_text(self, api):
        """Test that headline_type and headline are required."""
        with pytest.raises(ValueError):
            api.save_headline('test_dynasty', 2025, 1, {'headline': 'Test'})

        with pytest.raises(ValueError):
            api.save_headline('test_dynasty', 2025, 1, {'headline_type': 'GAME_RECAP'})

    def test_get_headlines_sorted_by_priority(self, api):
        """Test headlines are returned sorted by priority."""
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Low priority',
            'priority': 30
        })
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'High priority',
            'priority': 90
        })
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Medium priority',
            'priority': 60
        })

        headlines = api.get_headlines('test_dynasty', 2025, 1)

        assert headlines[0].headline == 'High priority'
        assert headlines[1].headline == 'Medium priority'
        assert headlines[2].headline == 'Low priority'

    def test_get_headlines_by_type(self, api):
        """Test filtering headlines by type."""
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Game recap 1'
        })
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'TRADE',
            'headline': 'Trade headline'
        })
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Game recap 2'
        })

        recaps = api.get_headlines('test_dynasty', 2025, 1, headline_type='GAME_RECAP')

        assert len(recaps) == 2
        assert all(h.headline_type == 'GAME_RECAP' for h in recaps)

    def test_get_top_headlines(self, api):
        """Test getting top N headlines."""
        for i in range(10):
            api.save_headline('test_dynasty', 2025, 1, {
                'headline_type': 'GAME_RECAP',
                'headline': f'Headline {i}',
                'priority': i * 10
            })

        top_5 = api.get_top_headlines('test_dynasty', 2025, 1, limit=5)

        assert len(top_5) == 5
        assert top_5[0].priority == 90  # Highest

    def test_get_headlines_for_team(self, api):
        """Test filtering headlines by team."""
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Chiefs win',
            'team_ids': [1, 2]
        })
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Bills win',
            'team_ids': [3, 4]
        })

        chiefs_headlines = api.get_headlines_for_team('test_dynasty', 2025, 1, team_id=1)

        assert len(chiefs_headlines) == 1
        assert 'Chiefs' in chiefs_headlines[0].headline


# ==========================================
# NARRATIVE ARCS TESTS
# ==========================================

class TestNarrativeArcs:
    """Tests for narrative arcs CRUD operations."""

    def test_save_narrative_arc(self, api):
        """Test saving a narrative arc."""
        arc_data = {
            'season': 2025,
            'arc_type': 'MVP_RACE',
            'title': 'Mahomes vs Allen: MVP Showdown',
            'description': 'Two elite QBs battle for MVP',
            'start_week': 1,
            'metadata': {'candidates': [101, 102]}
        }

        arc_id = api.save_narrative_arc('test_dynasty', arc_data)

        assert arc_id > 0

        # Verify saved
        arcs = api.get_active_arcs('test_dynasty', 2025)
        assert len(arcs) == 1
        assert arcs[0].title == 'Mahomes vs Allen: MVP Showdown'
        assert arcs[0].status == 'ACTIVE'

    def test_save_arc_requires_fields(self, api):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            api.save_narrative_arc('test_dynasty', {
                'season': 2025,
                'arc_type': 'MVP_RACE'
                # Missing title and start_week
            })

    def test_update_arc_status(self, api):
        """Test updating arc status."""
        arc_id = api.save_narrative_arc('test_dynasty', {
            'season': 2025,
            'arc_type': 'PLAYOFF_PUSH',
            'title': 'Lions chase playoff spot',
            'start_week': 10
        })

        # Update to resolved
        result = api.update_arc_status('test_dynasty', arc_id, 'RESOLVED', end_week=17)

        assert result is True

        # Verify no longer in active
        active = api.get_active_arcs('test_dynasty', 2025)
        assert len(active) == 0

    def test_get_arcs_by_type(self, api):
        """Test filtering arcs by type."""
        api.save_narrative_arc('test_dynasty', {
            'season': 2025, 'arc_type': 'MVP_RACE', 'title': 'MVP 1', 'start_week': 1
        })
        api.save_narrative_arc('test_dynasty', {
            'season': 2025, 'arc_type': 'HOT_SEAT', 'title': 'Coach on hot seat', 'start_week': 5
        })
        api.save_narrative_arc('test_dynasty', {
            'season': 2025, 'arc_type': 'MVP_RACE', 'title': 'MVP 2', 'start_week': 1
        })

        mvp_arcs = api.get_arcs_by_type('test_dynasty', 2025, 'MVP_RACE')

        assert len(mvp_arcs) == 2
        assert all(a.arc_type == 'MVP_RACE' for a in mvp_arcs)


# ==========================================
# PRESS QUOTES TESTS
# ==========================================

class TestPressQuotes:
    """Tests for press quotes CRUD operations."""

    def test_save_quote(self, api):
        """Test saving a press quote."""
        quote_data = {
            'quote_type': 'POSTGAME',
            'speaker_type': 'COACH',
            'team_id': 1,
            'quote_text': 'Our defense played lights out tonight.',
            'context': 'After 35-14 win over Bills',
            'sentiment': 'POSITIVE'
        }

        quote_id = api.save_quote('test_dynasty', 2025, 5, quote_data)

        assert quote_id > 0

        # Verify saved
        quotes = api.get_quotes('test_dynasty', 2025, 5)
        assert len(quotes) == 1
        assert 'defense' in quotes[0].quote_text

    def test_save_quote_requires_fields(self, api):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            api.save_quote('test_dynasty', 2025, 1, {
                'quote_type': 'POSTGAME'
                # Missing speaker_type and quote_text
            })

    def test_get_quotes_by_type(self, api):
        """Test filtering quotes by type."""
        api.save_quote('test_dynasty', 2025, 1, {
            'quote_type': 'POSTGAME',
            'speaker_type': 'COACH',
            'quote_text': 'Great win'
        })
        api.save_quote('test_dynasty', 2025, 1, {
            'quote_type': 'PRESSER',
            'speaker_type': 'COACH',
            'quote_text': 'Weekly presser quote'
        })

        postgame = api.get_quotes('test_dynasty', 2025, 1, quote_type='POSTGAME')

        assert len(postgame) == 1
        assert postgame[0].quote_type == 'POSTGAME'

    def test_get_team_quotes(self, api):
        """Test getting quotes for a specific team."""
        api.save_quote('test_dynasty', 2025, 1, {
            'quote_type': 'POSTGAME',
            'speaker_type': 'COACH',
            'team_id': 1,
            'quote_text': 'Chiefs quote'
        })
        api.save_quote('test_dynasty', 2025, 1, {
            'quote_type': 'POSTGAME',
            'speaker_type': 'COACH',
            'team_id': 2,
            'quote_text': 'Bills quote'
        })

        chiefs_quotes = api.get_team_quotes('test_dynasty', 2025, team_id=1)

        assert len(chiefs_quotes) == 1
        assert 'Chiefs' in chiefs_quotes[0].quote_text


# ==========================================
# DYNASTY ISOLATION TESTS
# ==========================================

class TestDynastyIsolation:
    """Tests to verify dynasty isolation in all queries."""

    def test_power_rankings_dynasty_isolation(self, api):
        """Test that power rankings are isolated by dynasty."""
        # Save rankings for two dynasties
        api.save_power_rankings('test_dynasty', 2025, 1, [
            {'team_id': 1, 'rank': 1, 'tier': 'ELITE'}
        ])
        api.save_power_rankings('other_dynasty', 2025, 1, [
            {'team_id': 1, 'rank': 10, 'tier': 'BUBBLE'}
        ])

        # Query each dynasty
        test_rankings = api.get_power_rankings('test_dynasty', 2025, 1)
        other_rankings = api.get_power_rankings('other_dynasty', 2025, 1)

        assert len(test_rankings) == 1
        assert test_rankings[0].rank == 1

        assert len(other_rankings) == 1
        assert other_rankings[0].rank == 10

    def test_headlines_dynasty_isolation(self, api):
        """Test that headlines are isolated by dynasty."""
        api.save_headline('test_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Test dynasty headline'
        })
        api.save_headline('other_dynasty', 2025, 1, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Other dynasty headline'
        })

        test_headlines = api.get_headlines('test_dynasty', 2025, 1)
        other_headlines = api.get_headlines('other_dynasty', 2025, 1)

        assert len(test_headlines) == 1
        assert 'Test dynasty' in test_headlines[0].headline

        assert len(other_headlines) == 1
        assert 'Other dynasty' in other_headlines[0].headline


# ==========================================
# UTILITY METHODS TESTS
# ==========================================

class TestUtilityMethods:
    """Tests for utility methods."""

    def test_delete_week_coverage(self, api):
        """Test deleting all coverage for a week."""
        # Add coverage
        api.save_power_rankings('test_dynasty', 2025, 5, [
            {'team_id': 1, 'rank': 1, 'tier': 'ELITE'}
        ])
        api.save_headline('test_dynasty', 2025, 5, {
            'headline_type': 'GAME_RECAP',
            'headline': 'Test headline'
        })
        api.save_quote('test_dynasty', 2025, 5, {
            'quote_type': 'POSTGAME',
            'speaker_type': 'COACH',
            'quote_text': 'Test quote'
        })

        # Delete
        counts = api.delete_week_coverage('test_dynasty', 2025, 5)

        assert counts['power_rankings'] == 1
        assert counts['headlines'] == 1
        assert counts['quotes'] == 1

        # Verify deleted
        assert len(api.get_power_rankings('test_dynasty', 2025, 5)) == 0
        assert len(api.get_headlines('test_dynasty', 2025, 5)) == 0
        assert len(api.get_quotes('test_dynasty', 2025, 5)) == 0

    def test_get_coverage_summary(self, api):
        """Test getting coverage summary for a week."""
        # Add coverage
        api.save_power_rankings('test_dynasty', 2025, 5, [
            {'team_id': i, 'rank': i, 'tier': 'CONTENDER'} for i in range(1, 6)
        ])
        for i in range(3):
            api.save_headline('test_dynasty', 2025, 5, {
                'headline_type': 'GAME_RECAP',
                'headline': f'Headline {i}'
            })
        api.save_narrative_arc('test_dynasty', {
            'season': 2025,
            'arc_type': 'MVP_RACE',
            'title': 'MVP Race',
            'start_week': 1
        })

        summary = api.get_coverage_summary('test_dynasty', 2025, 5)

        assert summary['power_rankings'] == 5
        assert summary['headlines'] == 3
        assert summary['quotes'] == 0
        assert summary['active_arcs'] == 1
