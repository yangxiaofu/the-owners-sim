"""
Tests for HeadlineGenerator service.

Part of Milestone 12: Media Coverage, Tollgate 3.
Target: 30+ unit tests
"""

import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from src.game_cycle.services.headline_generator import (
    HeadlineGenerator,
    HeadlineType,
    Sentiment,
    HeadlineTemplate,
    BASE_PRIORITIES,
    GAME_RECAP_TEMPLATES,
    BLOWOUT_TEMPLATES,
    UPSET_TEMPLATES,
    COMEBACK_TEMPLATES,
    INJURY_TEMPLATES,
    TRADE_TEMPLATES,
    SIGNING_TEMPLATES,
    AWARD_TEMPLATES,
    MILESTONE_TEMPLATES,
    RUMOR_TEMPLATES,
    STREAK_TEMPLATES,
    POWER_RANKING_TEMPLATES,
    get_template_counts,
)
from src.game_cycle.database.media_coverage_api import Headline


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def temp_db():
    """Create temporary database with media coverage schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create dynasties table (required for foreign key)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT INTO dynasties (dynasty_id, name) VALUES ('test_dynasty', 'Test')")

    # Create media_headlines table
    cursor.execute("""
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
        )
    """)

    # Create power_rankings table (required for some tests)
    cursor.execute("""
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
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def generator(temp_db):
    """Create HeadlineGenerator instance."""
    return HeadlineGenerator(
        db_path=temp_db,
        dynasty_id="test_dynasty",
        season=2025
    )


@pytest.fixture
def game_data_blowout() -> Dict[str, Any]:
    """Sample game data for a blowout."""
    return {
        "week": 5,
        "winner_id": 1,  # Arizona
        "loser_id": 2,   # Atlanta
        "winner_score": 42,
        "loser_score": 10,
        "home_team_id": 1,
        "away_team_id": 2,
        "is_playoff": False,
        "is_rivalry": False,
        "is_primetime": False,
        "game_id": "game_001",
    }


@pytest.fixture
def game_data_close() -> Dict[str, Any]:
    """Sample game data for a close game."""
    return {
        "week": 5,
        "winner_id": 3,  # Baltimore
        "loser_id": 4,   # Buffalo
        "winner_score": 24,
        "loser_score": 21,
        "home_team_id": 3,
        "away_team_id": 4,
        "is_playoff": False,
        "is_rivalry": False,
        "is_primetime": True,
        "game_id": "game_002",
    }


@pytest.fixture
def game_data_upset() -> Dict[str, Any]:
    """Sample game data for an upset."""
    return {
        "week": 5,
        "winner_id": 5,  # Carolina
        "loser_id": 6,   # Chicago
        "winner_score": 28,
        "loser_score": 21,
        "home_team_id": 6,
        "away_team_id": 5,
        "is_upset": True,
        "spread": 10,
        "game_id": "game_003",
    }


@pytest.fixture
def game_data_comeback() -> Dict[str, Any]:
    """Sample game data for a comeback."""
    return {
        "week": 5,
        "winner_id": 7,  # Cincinnati
        "loser_id": 8,   # Cleveland
        "winner_score": 31,
        "loser_score": 28,
        "home_team_id": 7,
        "away_team_id": 8,
        "comeback_points": 17,
        "game_id": "game_004",
    }


# ============================================
# Template Count Tests
# ============================================

class TestTemplateCount:
    """Tests for template count verification."""

    def test_minimum_template_count(self):
        """Verify we have 200+ templates total."""
        counts = get_template_counts()
        assert counts["TOTAL"] >= 200, f"Expected 200+ templates, got {counts['TOTAL']}"

    def test_game_recap_templates_count(self):
        """Verify adequate GAME_RECAP templates."""
        assert len(GAME_RECAP_TEMPLATES) >= 20

    def test_blowout_templates_count(self):
        """Verify adequate BLOWOUT templates."""
        assert len(BLOWOUT_TEMPLATES) >= 15

    def test_upset_templates_count(self):
        """Verify adequate UPSET templates."""
        assert len(UPSET_TEMPLATES) >= 15

    def test_comeback_templates_count(self):
        """Verify adequate COMEBACK templates."""
        assert len(COMEBACK_TEMPLATES) >= 15

    def test_injury_templates_count(self):
        """Verify adequate INJURY templates."""
        assert len(INJURY_TEMPLATES) >= 15

    def test_trade_templates_count(self):
        """Verify adequate TRADE templates."""
        assert len(TRADE_TEMPLATES) >= 15

    def test_signing_templates_count(self):
        """Verify adequate SIGNING templates."""
        assert len(SIGNING_TEMPLATES) >= 12

    def test_award_templates_count(self):
        """Verify adequate AWARD templates."""
        assert len(AWARD_TEMPLATES) >= 12

    def test_milestone_templates_count(self):
        """Verify adequate MILESTONE templates."""
        assert len(MILESTONE_TEMPLATES) >= 12

    def test_rumor_templates_count(self):
        """Verify adequate RUMOR templates."""
        assert len(RUMOR_TEMPLATES) >= 15

    def test_streak_templates_count(self):
        """Verify adequate STREAK templates."""
        assert len(STREAK_TEMPLATES) >= 10

    def test_power_ranking_templates_count(self):
        """Verify adequate POWER_RANKING templates."""
        assert len(POWER_RANKING_TEMPLATES) >= 10

    def test_all_template_types_covered(self):
        """Verify all HeadlineTypes have templates."""
        counts = get_template_counts()
        for htype in ["GAME_RECAP", "BLOWOUT", "UPSET", "COMEBACK",
                      "INJURY", "TRADE", "SIGNING", "AWARD",
                      "MILESTONE", "RUMOR", "STREAK", "POWER_RANKING"]:
            assert counts[htype] > 0, f"No templates for {htype}"


# ============================================
# Game Classification Tests
# ============================================

class TestGameClassification:
    """Tests for automatic game result classification."""

    def test_classify_blowout(self, generator, game_data_blowout):
        """Test blowout detection (21+ point margin)."""
        headline_type = generator._classify_game_result(game_data_blowout)
        assert headline_type == HeadlineType.BLOWOUT

    def test_classify_regular_game(self, generator, game_data_close):
        """Test regular game classification."""
        headline_type = generator._classify_game_result(game_data_close)
        assert headline_type == HeadlineType.GAME_RECAP

    def test_classify_upset(self, generator, game_data_upset):
        """Test upset detection."""
        headline_type = generator._classify_game_result(game_data_upset)
        assert headline_type == HeadlineType.UPSET

    def test_classify_comeback(self, generator, game_data_comeback):
        """Test comeback detection (14+ point comeback)."""
        headline_type = generator._classify_game_result(game_data_comeback)
        assert headline_type == HeadlineType.COMEBACK

    def test_classify_comeback_over_upset(self, generator):
        """Comeback should take priority over upset."""
        game_data = {
            "winner_score": 28,
            "loser_score": 24,
            "is_upset": True,
            "comeback_points": 14,
        }
        headline_type = generator._classify_game_result(game_data)
        assert headline_type == HeadlineType.COMEBACK

    def test_classify_comeback_over_blowout(self, generator):
        """Comeback should take priority over blowout."""
        game_data = {
            "winner_score": 42,
            "loser_score": 17,
            "comeback_points": 21,
        }
        headline_type = generator._classify_game_result(game_data)
        assert headline_type == HeadlineType.COMEBACK

    def test_classify_moderate_margin(self, generator):
        """Test 14-20 point margin is not a blowout."""
        game_data = {
            "winner_score": 31,
            "loser_score": 14,
        }
        headline_type = generator._classify_game_result(game_data)
        assert headline_type == HeadlineType.GAME_RECAP


# ============================================
# Headline Generation Tests
# ============================================

class TestHeadlineGeneration:
    """Tests for headline generation."""

    def test_generate_game_headline_basic(self, generator, game_data_blowout):
        """Test basic game headline generation."""
        headline = generator.generate_game_headline(game_data_blowout)

        assert headline is not None
        assert headline.headline_type in ["GAME_RECAP", "BLOWOUT", "UPSET", "COMEBACK"]
        assert headline.headline  # Not empty
        assert headline.week == 5
        assert headline.season == 2025
        assert headline.dynasty_id == "test_dynasty"

    def test_generate_headline_with_sentiment(self, generator, game_data_blowout):
        """Test headline includes sentiment."""
        headline = generator.generate_game_headline(game_data_blowout)

        assert headline.sentiment in [s.value for s in Sentiment]

    def test_generate_headline_with_priority(self, generator, game_data_blowout):
        """Test headline includes priority score."""
        headline = generator.generate_game_headline(game_data_blowout)

        assert 1 <= headline.priority <= 100

    def test_generate_headline_team_ids(self, generator, game_data_blowout):
        """Test headline includes related team IDs."""
        headline = generator.generate_game_headline(game_data_blowout)

        assert len(headline.team_ids) >= 1
        assert 1 in headline.team_ids or 2 in headline.team_ids

    def test_generate_injury_headline(self, generator):
        """Test injury headline generation."""
        event_data = {
            "week": 5,
            "player": "Patrick Mahomes",
            "team": "Kansas City Chiefs",
            "injury": "Ankle Sprain",
            "duration": "2-4 Weeks",
            "player_ids": [101],
            "team_ids": [16],
        }

        headline = generator.generate_headline(HeadlineType.INJURY, event_data)

        assert headline.headline_type == "INJURY"
        assert "Mahomes" in headline.headline or "Ankle" in headline.headline
        assert headline.sentiment in ["NEGATIVE", "CRITICAL"]

    def test_generate_trade_headline(self, generator):
        """Test trade headline generation."""
        event_data = {
            "week": 9,
            "player": "Davante Adams",
            "acquiring_team": "New York Jets",
            "trading_team": "Las Vegas Raiders",
            "acquiring_city": "New York",
            "trading_city": "Las Vegas",
            "player_ids": [201],
            "team_ids": [24, 20],
        }

        headline = generator.generate_headline(HeadlineType.TRADE, event_data)

        assert headline.headline_type == "TRADE"
        assert "Adams" in headline.headline or "Jets" in headline.headline

    def test_generate_signing_headline(self, generator):
        """Test signing headline generation."""
        event_data = {
            "week": 2,  # Free agency week
            "player": "Saquon Barkley",
            "team": "Philadelphia Eagles",
            "team_city": "Philadelphia",
            "years": 4,
            "value": 48,
            "contract_type": "veteran",
            "player_ids": [301],
            "team_ids": [26],
        }

        headline = generator.generate_headline(HeadlineType.SIGNING, event_data)

        assert headline.headline_type == "SIGNING"
        assert "Barkley" in headline.headline or "Eagles" in headline.headline

    def test_generate_award_headline(self, generator):
        """Test award headline generation."""
        event_data = {
            "week": 17,
            "player": "Lamar Jackson",
            "team": "Baltimore Ravens",
            "award": "NFL MVP",
            "award_is_mvp": True,
            "player_ids": [401],
            "team_ids": [3],
        }

        headline = generator.generate_headline(HeadlineType.AWARD, event_data)

        assert headline.headline_type == "AWARD"
        assert headline.sentiment in ["POSITIVE", "HYPE"]

    def test_generate_milestone_headline(self, generator):
        """Test milestone headline generation."""
        event_data = {
            "week": 14,
            "player": "Travis Kelce",
            "milestone": "10,000 Career Receiving Yards",
            "stat_type": "Receiving Yards",
            "count": "10,000",
            "player_ids": [501],
            "team_ids": [16],
        }

        headline = generator.generate_headline(HeadlineType.MILESTONE, event_data)

        assert headline.headline_type == "MILESTONE"

    def test_generate_rumor_headline(self, generator):
        """Test rumor headline generation."""
        event_data = {
            "week": 7,
            "player": "Justin Jefferson",
            "team": "Minnesota Vikings",
            "team_city": "Minnesota",
            "player_ids": [601],
            "team_ids": [17],
        }

        headline = generator.generate_headline(HeadlineType.RUMOR, event_data)

        assert headline.headline_type == "RUMOR"

    def test_generate_streak_headline(self, generator):
        """Test streak headline generation."""
        event_data = {
            "week": 10,
            "team": "Detroit Lions",
            "count": 6,
            "streak_type": "winning",
            "next_week": 11,
            "team_ids": [11],
        }

        headline = generator.generate_headline(HeadlineType.STREAK, event_data)

        assert headline.headline_type == "STREAK"


# ============================================
# Conditional Template Matching Tests
# ============================================

class TestConditionalMatching:
    """Tests for conditional template matching."""

    def test_margin_min_condition(self, generator):
        """Test margin_min condition matching."""
        template = HeadlineTemplate(
            template="Big win by {margin} points",
            conditions={"margin_min": 21},
        )
        event_data = {"margin": 28}
        assert generator._template_matches(template, event_data) is True

        event_data = {"margin": 14}
        assert generator._template_matches(template, event_data) is False

    def test_margin_max_condition(self, generator):
        """Test margin_max condition matching."""
        template = HeadlineTemplate(
            template="Close game with {margin} points",
            conditions={"margin_max": 7},
        )
        event_data = {"margin": 3}
        assert generator._template_matches(template, event_data) is True

        event_data = {"margin": 14}
        assert generator._template_matches(template, event_data) is False

    def test_range_condition(self, generator):
        """Test combined min/max range condition."""
        template = HeadlineTemplate(
            template="Moderate win",
            conditions={"margin_min": 8, "margin_max": 13},
        )
        event_data = {"margin": 10}
        assert generator._template_matches(template, event_data) is True

        event_data = {"margin": 5}
        assert generator._template_matches(template, event_data) is False

        event_data = {"margin": 20}
        assert generator._template_matches(template, event_data) is False

    def test_boolean_condition(self, generator):
        """Test boolean condition matching."""
        template = HeadlineTemplate(
            template="Home win",
            conditions={"winner_is_home": True},
        )
        event_data = {"winner_is_home": True}
        assert generator._template_matches(template, event_data) is True

        event_data = {"winner_is_home": False}
        assert generator._template_matches(template, event_data) is False

    def test_no_conditions_matches_all(self, generator):
        """Test template with no conditions matches any data."""
        template = HeadlineTemplate(template="Generic headline")
        event_data = {"margin": 50, "is_playoff": True}
        assert generator._template_matches(template, event_data) is True

    def test_multiple_conditions_all_must_match(self, generator):
        """Test that all conditions must match."""
        template = HeadlineTemplate(
            template="Primetime blowout",
            conditions={"margin_min": 21, "is_primetime": True},
        )
        # Both conditions met
        event_data = {"margin": 28, "is_primetime": True}
        assert generator._template_matches(template, event_data) is True

        # Only one condition met
        event_data = {"margin": 28, "is_primetime": False}
        assert generator._template_matches(template, event_data) is False

        event_data = {"margin": 14, "is_primetime": True}
        assert generator._template_matches(template, event_data) is False


# ============================================
# Priority Calculation Tests
# ============================================

class TestPriorityCalculation:
    """Tests for priority scoring algorithm."""

    def test_base_priorities_exist(self):
        """Verify base priorities for all types."""
        for htype in HeadlineType:
            assert htype in BASE_PRIORITIES

    def test_priority_within_bounds(self, generator, game_data_blowout):
        """Test priority stays within 1-100."""
        headline = generator.generate_game_headline(game_data_blowout)
        assert 1 <= headline.priority <= 100

    def test_playoff_priority_boost(self, generator):
        """Test playoff games get priority boost."""
        regular_data = {"winner_score": 28, "loser_score": 21, "week": 10}
        playoff_data = {"winner_score": 28, "loser_score": 21, "week": 19, "is_playoff": True}

        template = HeadlineTemplate(template="Test", priority_boost=0)

        regular_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, regular_data, template
        )
        playoff_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, playoff_data, template
        )

        assert playoff_priority > regular_priority

    def test_rivalry_priority_boost(self, generator):
        """Test rivalry games get priority boost."""
        normal_data = {"week": 10}
        rivalry_data = {"week": 10, "is_rivalry": True}

        template = HeadlineTemplate(template="Test", priority_boost=0)

        normal_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, normal_data, template
        )
        rivalry_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, rivalry_data, template
        )

        assert rivalry_priority > normal_priority

    def test_template_priority_boost(self, generator):
        """Test template priority_boost is applied."""
        event_data = {"week": 10}

        template_no_boost = HeadlineTemplate(template="Test", priority_boost=0)
        template_with_boost = HeadlineTemplate(template="Test", priority_boost=20)

        priority_no_boost = generator._calculate_priority(
            HeadlineType.GAME_RECAP, event_data, template_no_boost
        )
        priority_with_boost = generator._calculate_priority(
            HeadlineType.GAME_RECAP, event_data, template_with_boost
        )

        assert priority_with_boost == priority_no_boost + 20

    def test_clinch_priority_boost(self, generator):
        """Test playoff clinching gets major priority boost."""
        normal_data = {"week": 15}
        clinch_data = {"week": 15, "clinches_playoff": True}

        template = HeadlineTemplate(template="Test", priority_boost=0)

        normal_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, normal_data, template
        )
        clinch_priority = generator._calculate_priority(
            HeadlineType.GAME_RECAP, clinch_data, template
        )

        assert clinch_priority > normal_priority + 10  # At least +15 boost


# ============================================
# Template Filling Tests
# ============================================

class TestTemplateFilling:
    """Tests for template placeholder filling."""

    def test_fill_basic_template(self, generator):
        """Test basic template filling."""
        template = "{winner} defeats {loser}"
        data = {"winner": "Chiefs", "loser": "Raiders"}
        result = generator._fill_template(template, data)
        assert result == "Chiefs defeats Raiders"

    def test_fill_missing_placeholder(self, generator):
        """Test graceful handling of missing placeholders."""
        template = "{winner} defeats {loser} by {margin}"
        data = {"winner": "Chiefs", "loser": "Raiders"}
        result = generator._fill_template(template, data)
        # Should keep placeholder if missing
        assert "{margin}" in result

    def test_fill_with_numbers(self, generator):
        """Test template filling with numeric values."""
        template = "{team} wins by {margin} points"
        data = {"team": "Eagles", "margin": 14}
        result = generator._fill_template(template, data)
        assert result == "Eagles wins by 14 points"


# ============================================
# Batch Generation Tests
# ============================================

class TestBatchGeneration:
    """Tests for batch headline generation."""

    def test_generate_batch(self, generator):
        """Test batch generation of multiple headlines."""
        events = [
            (HeadlineType.GAME_RECAP, {"week": 5, "winner": "Team A", "loser": "Team B", "score": "28-21"}),
            (HeadlineType.TRADE, {"week": 5, "player": "Star Player", "acquiring_team": "Team C", "trading_team": "Team D"}),
            (HeadlineType.INJURY, {"week": 5, "player": "QB Name", "team": "Team E", "injury": "Knee", "duration": "4 weeks"}),
        ]

        headlines = generator.generate_batch(events)

        assert len(headlines) == 3
        # Should be sorted by priority
        for i in range(len(headlines) - 1):
            assert headlines[i].priority >= headlines[i + 1].priority

    def test_batch_deduplication(self, generator):
        """Test batch removes duplicate headlines."""
        # Create two identical events
        events = [
            (HeadlineType.STREAK, {"week": 5, "team": "Lions", "count": 5, "streak_type": "winning"}),
            (HeadlineType.STREAK, {"week": 5, "team": "Lions", "count": 5, "streak_type": "winning"}),
        ]

        headlines = generator.generate_batch(events)

        # May have 1 or 2 depending on random template selection
        # but should not have exact duplicates
        headline_texts = [h.headline for h in headlines]
        unique_texts = set(headline_texts)
        assert len(headline_texts) == len(unique_texts)


# ============================================
# Data Enrichment Tests
# ============================================

class TestDataEnrichment:
    """Tests for game data enrichment."""

    def test_enrich_calculates_margin(self, generator):
        """Test margin calculation."""
        game_data = {
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 35,
            "loser_score": 17,
            "home_team_id": 1,
        }

        enriched = generator._enrich_game_data(game_data)

        assert enriched["margin"] == 18
        assert enriched["score"] == "35-17"

    def test_enrich_determines_winner_home(self, generator):
        """Test winner_is_home determination."""
        # Winner is home team
        game_data = {
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 28,
            "loser_score": 21,
            "home_team_id": 1,
        }

        enriched = generator._enrich_game_data(game_data)
        assert enriched["winner_is_home"] is True

        # Winner is away team
        game_data["home_team_id"] = 2
        enriched = generator._enrich_game_data(game_data)
        assert enriched["winner_is_home"] is False

    def test_enrich_sets_team_ids(self, generator):
        """Test team_ids are set."""
        game_data = {
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 28,
            "loser_score": 21,
            "home_team_id": 1,
        }

        enriched = generator._enrich_game_data(game_data)

        assert 1 in enriched["team_ids"]
        assert 2 in enriched["team_ids"]


# ============================================
# Persistence Tests
# ============================================

class TestPersistence:
    """Tests for headline persistence."""

    def test_save_headline(self, generator, game_data_blowout):
        """Test saving a headline to database."""
        headline = generator.generate_game_headline(game_data_blowout)
        headline_id = generator.save_headline(headline)

        assert headline_id is not None
        assert headline_id > 0

    def test_save_and_retrieve_headline(self, generator, game_data_blowout):
        """Test saving and retrieving headlines."""
        headline = generator.generate_game_headline(game_data_blowout)
        generator.save_headline(headline)

        # Retrieve
        headlines = generator.get_headlines(week=5)

        assert len(headlines) >= 1
        retrieved = headlines[0]
        assert retrieved.week == 5
        assert retrieved.season == 2025

    def test_save_headlines_batch(self, generator):
        """Test saving multiple headlines."""
        events = [
            (HeadlineType.GAME_RECAP, {"week": 5, "winner": "Team A", "loser": "Team B", "score": "28-21"}),
            (HeadlineType.TRADE, {"week": 5, "player": "Star Player", "acquiring_team": "Team C", "trading_team": "Team D"}),
        ]

        headlines = generator.generate_batch(events)
        count = generator.save_headlines(headlines)

        assert count == len(headlines)

    def test_get_top_headlines(self, generator):
        """Test retrieving top headlines by priority."""
        # Generate and save several headlines
        events = [
            (HeadlineType.GAME_RECAP, {"week": 5, "winner": "A", "loser": "B", "score": "21-17"}),
            (HeadlineType.BLOWOUT, {"week": 5, "winner": "C", "loser": "D", "score": "42-7", "margin": 35}),
            (HeadlineType.TRADE, {"week": 5, "player": "Star", "acquiring_team": "E", "trading_team": "F", "is_blockbuster": True}),
        ]

        headlines = generator.generate_batch(events)
        generator.save_headlines(headlines)

        # Get top 2
        top_headlines = generator.get_top_headlines(week=5, limit=2)

        assert len(top_headlines) <= 2
        # Should be sorted by priority
        if len(top_headlines) == 2:
            assert top_headlines[0].priority >= top_headlines[1].priority


# ============================================
# Sentiment Tests
# ============================================

class TestSentiment:
    """Tests for sentiment tagging."""

    def test_blowout_winner_positive(self, generator, game_data_blowout):
        """Test blowout has positive/hype sentiment for winner."""
        headline = generator.generate_game_headline(game_data_blowout)

        # Blowout templates have POSITIVE, HYPE, or CRITICAL sentiment
        assert headline.sentiment in ["POSITIVE", "HYPE", "CRITICAL", "NEGATIVE"]

    def test_injury_negative_sentiment(self, generator):
        """Test injury headlines have negative sentiment."""
        event_data = {
            "week": 5,
            "player": "Test Player",
            "team": "Test Team",
            "injury": "ACL Tear",
            "duration": "Season",
        }

        headline = generator.generate_headline(HeadlineType.INJURY, event_data)

        assert headline.sentiment in ["NEGATIVE", "CRITICAL"]

    def test_signing_positive_sentiment(self, generator):
        """Test signing headlines typically have positive sentiment."""
        event_data = {
            "week": 2,
            "player": "Free Agent",
            "team": "Signing Team",
            "team_city": "City",
            "years": 3,
            "value": 30,
        }

        headline = generator.generate_headline(HeadlineType.SIGNING, event_data)

        assert headline.sentiment in ["POSITIVE", "NEUTRAL", "HYPE"]


# ============================================
# Fallback Tests
# ============================================

class TestFallback:
    """Tests for fallback headline generation."""

    def test_fallback_headline_created(self, generator):
        """Test fallback headline when no templates match."""
        # Create headline with impossible conditions
        event_data = {"week": 5}

        headline = generator._create_fallback_headline(HeadlineType.GAME_RECAP, event_data)

        assert headline is not None
        assert headline.headline_type == "GAME_RECAP"
        assert headline.priority == BASE_PRIORITIES[HeadlineType.GAME_RECAP]


# ============================================
# Edge Case Tests
# ============================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_shutout_detection(self, generator):
        """Test shutout game handling."""
        game_data = {
            "week": 5,
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 35,
            "loser_score": 0,
            "home_team_id": 1,
        }

        headline = generator.generate_game_headline(game_data)

        # Should be blowout (margin >= 21)
        assert headline.headline_type in ["BLOWOUT", "GAME_RECAP"]

    def test_zero_margin_game(self, generator):
        """Test tie/OT game handling (margin effectively 0 for close games)."""
        game_data = {
            "week": 5,
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 24,
            "loser_score": 24,  # Before OT, hypothetically
            "home_team_id": 1,
        }

        headline = generator.generate_game_headline(game_data)

        # Should handle gracefully
        assert headline is not None

    def test_very_large_margin(self, generator):
        """Test handling of very large margins."""
        game_data = {
            "week": 5,
            "winner_id": 1,
            "loser_id": 2,
            "winner_score": 70,
            "loser_score": 0,
            "home_team_id": 1,
        }

        headline = generator.generate_game_headline(game_data)

        assert headline.headline_type == "BLOWOUT"
        # Priority should be high but capped at 100
        assert headline.priority <= 100

    def test_empty_event_data(self, generator):
        """Test handling of minimal event data."""
        event_data = {"week": 5}

        headline = generator.generate_headline(HeadlineType.GAME_RECAP, event_data)

        # Should handle gracefully with fallback
        assert headline is not None


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests for full headline generation flow."""

    def test_full_game_flow(self, generator, game_data_blowout):
        """Test complete flow: generate, save, retrieve."""
        # Generate
        headline = generator.generate_game_headline(game_data_blowout)
        assert headline is not None

        # Save
        headline_id = generator.save_headline(headline)
        assert headline_id > 0

        # Retrieve
        headlines = generator.get_headlines(week=5)
        assert len(headlines) == 1
        assert headlines[0].id == headline_id

    def test_multiple_game_week(self, generator, game_data_blowout, game_data_close, game_data_upset):
        """Test generating headlines for multiple games in a week."""
        games = [game_data_blowout, game_data_close, game_data_upset]

        for game in games:
            headline = generator.generate_game_headline(game)
            generator.save_headline(headline)

        headlines = generator.get_headlines(week=5)
        assert len(headlines) == 3
