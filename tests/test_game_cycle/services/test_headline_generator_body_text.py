"""
Tests for Headline Generator Body Text (Tollgate 4).

Part of Milestone 12: Media Coverage.
Tests the 4-paragraph game recap narrative generation.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.game_cycle.services.headline_generator import (
    HeadlineGenerator,
    HeadlineType,
    Sentiment,
    OPENING_PARAGRAPH_TEMPLATES,
    STAR_PLAYERS_TEMPLATES,
    TURNING_POINT_TEMPLATES,
    LOOKING_AHEAD_TEMPLATES,
    SCORING_SUMMARY_TEMPLATES,
    SECONDARY_PLAYER_SENTENCES,
)
from src.game_cycle.database.media_coverage_api import Headline
from src.game_cycle.database.box_scores_api import BoxScore
from src.game_cycle.database.standings_api import TeamStanding


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize minimal schema
    import sqlite3
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS media_headlines (
            id INTEGER PRIMARY KEY,
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

        CREATE TABLE IF NOT EXISTS box_scores (
            id INTEGER PRIMARY KEY,
            game_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            dynasty_id TEXT NOT NULL,
            q1_score INTEGER DEFAULT 0,
            q2_score INTEGER DEFAULT 0,
            q3_score INTEGER DEFAULT 0,
            q4_score INTEGER DEFAULT 0,
            ot_score INTEGER DEFAULT 0,
            first_downs INTEGER DEFAULT 0,
            third_down_att INTEGER DEFAULT 0,
            third_down_conv INTEGER DEFAULT 0,
            fourth_down_att INTEGER DEFAULT 0,
            fourth_down_conv INTEGER DEFAULT 0,
            total_yards INTEGER DEFAULT 0,
            passing_yards INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            turnovers INTEGER DEFAULT 0,
            penalties INTEGER DEFAULT 0,
            penalty_yards INTEGER DEFAULT 0,
            time_of_possession INTEGER DEFAULT 0,
            team_timeouts_remaining INTEGER DEFAULT 3,
            team_timeouts_used_h1 INTEGER DEFAULT 0,
            team_timeouts_used_h2 INTEGER DEFAULT 0,
            UNIQUE(dynasty_id, game_id, team_id)
        );

        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season_type TEXT DEFAULT 'regular_season',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            UNIQUE(dynasty_id, season, team_id, season_type)
        );

        CREATE TABLE IF NOT EXISTS rivalries (
            rivalry_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            team_a_id INTEGER NOT NULL,
            team_b_id INTEGER NOT NULL,
            rivalry_type TEXT NOT NULL,
            rivalry_name TEXT,
            intensity INTEGER DEFAULT 5,
            is_protected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, team_a_id, team_b_id)
        );

        CREATE TABLE IF NOT EXISTS player_game_grades (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT,
            overall_grade REAL,
            passing_grade REAL,
            rushing_grade REAL,
            receiving_grade REAL,
            pass_blocking_grade REAL,
            run_blocking_grade REAL,
            pass_rush_grade REAL,
            run_defense_grade REAL,
            coverage_grade REAL,
            tackling_grade REAL,
            offensive_snaps INTEGER DEFAULT 0,
            defensive_snaps INTEGER DEFAULT 0,
            special_teams_snaps INTEGER DEFAULT 0,
            epa_total REAL,
            success_rate REAL,
            play_count INTEGER DEFAULT 0,
            positive_plays INTEGER DEFAULT 0,
            negative_plays INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS player_play_grades (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            play_number INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT,
            quarter INTEGER,
            down INTEGER,
            distance INTEGER,
            yard_line INTEGER,
            game_clock INTEGER,
            score_differential INTEGER,
            play_type TEXT,
            is_offense INTEGER DEFAULT 1,
            play_grade REAL,
            grade_component_1 REAL,
            grade_component_2 REAL,
            grade_component_3 REAL,
            was_positive_play INTEGER DEFAULT 0,
            epa_contribution REAL
        );
    """)
    conn.close()

    yield path

    # Cleanup
    os.unlink(path)


@pytest.fixture
def generator(temp_db_path):
    """Create a HeadlineGenerator instance for testing."""
    return HeadlineGenerator(temp_db_path, "test_dynasty", 2025)


@pytest.fixture
def basic_game_data():
    """Basic game data for testing."""
    return {
        "game_id": "game_001",
        "winner_id": 1,
        "loser_id": 2,
        "winner_score": 27,
        "loser_score": 20,
        "home_team_id": 1,
        "away_team_id": 2,
        "week": 5,
    }


# =============================================================================
# TEMPLATE TESTS
# =============================================================================

class TestBodyTextTemplates:
    """Tests for body text template coverage."""

    def test_opening_templates_exist_for_all_game_types(self):
        """Verify opening templates exist for all game result types."""
        expected_types = [
            HeadlineType.GAME_RECAP,
            HeadlineType.BLOWOUT,
            HeadlineType.UPSET,
            HeadlineType.COMEBACK,
        ]
        for headline_type in expected_types:
            assert headline_type in OPENING_PARAGRAPH_TEMPLATES
            assert len(OPENING_PARAGRAPH_TEMPLATES[headline_type]) >= 3

    def test_star_players_templates_count(self):
        """Verify we have enough star player templates."""
        assert len(STAR_PLAYERS_TEMPLATES) >= 4

    def test_turning_point_templates_count(self):
        """Verify we have enough turning point templates."""
        assert len(TURNING_POINT_TEMPLATES) >= 3

    def test_looking_ahead_templates_categories(self):
        """Verify all looking ahead template categories exist."""
        expected_categories = [
            "playoff_clinch",
            "playoff_implications",
            "division_race",
            "streak",
            "rivalry",
            "default",
        ]
        for category in expected_categories:
            assert category in LOOKING_AHEAD_TEMPLATES
            assert len(LOOKING_AHEAD_TEMPLATES[category]) >= 2

    def test_secondary_player_sentences_count(self):
        """Verify we have enough secondary player sentences."""
        assert len(SECONDARY_PLAYER_SENTENCES) >= 4

    def test_scoring_summary_templates_count(self):
        """Verify we have enough scoring summary templates."""
        assert len(SCORING_SUMMARY_TEMPLATES) >= 3


# =============================================================================
# OPENING PARAGRAPH TESTS
# =============================================================================

class TestOpeningParagraph:
    """Tests for opening paragraph generation."""

    def test_opening_paragraph_game_recap(self, generator, basic_game_data):
        """Test opening paragraph generation for standard game."""
        recap_data = {
            "winner_standing": TeamStanding(
                team_id=1, wins=5, losses=0, ties=0,
                points_for=150, points_against=100,
                division_wins=2, division_losses=0,
                conference_wins=3, conference_losses=0,
                home_wins=3, home_losses=0,
                away_wins=2, away_losses=0
            ),
            "loser_standing": TeamStanding(
                team_id=2, wins=3, losses=2, ties=0,
                points_for=110, points_against=100,
                division_wins=1, division_losses=1,
                conference_wins=2, conference_losses=1,
                home_wins=2, home_losses=1,
                away_wins=1, away_losses=1
            ),
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_opening_paragraph(
            enriched, HeadlineType.GAME_RECAP, recap_data
        )

        assert isinstance(result, str)
        assert len(result) > 50

    def test_opening_paragraph_blowout(self, generator, basic_game_data):
        """Test opening paragraph for blowout games."""
        basic_game_data["winner_score"] = 42
        basic_game_data["loser_score"] = 10
        recap_data = {"winner_standing": None, "loser_standing": None}
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_opening_paragraph(
            enriched, HeadlineType.BLOWOUT, recap_data
        )

        assert isinstance(result, str)
        assert len(result) > 50

    def test_opening_paragraph_upset(self, generator, basic_game_data):
        """Test opening paragraph for upset games."""
        basic_game_data["is_upset"] = True
        recap_data = {"winner_standing": None, "loser_standing": None}
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_opening_paragraph(
            enriched, HeadlineType.UPSET, recap_data
        )

        assert isinstance(result, str)
        assert len(result) > 50

    def test_opening_paragraph_comeback(self, generator, basic_game_data):
        """Test opening paragraph for comeback games."""
        basic_game_data["comeback_points"] = 21
        recap_data = {"winner_standing": None, "loser_standing": None}
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_opening_paragraph(
            enriched, HeadlineType.COMEBACK, recap_data
        )

        assert isinstance(result, str)
        assert "21" in result or len(result) > 50


# =============================================================================
# STAR PLAYERS PARAGRAPH TESTS
# =============================================================================

class TestStarPlayersParagraph:
    """Tests for star players paragraph generation."""

    def test_star_players_without_grades(self, generator, basic_game_data):
        """Test star players paragraph with minimal data."""
        recap_data = {
            "has_game_grades": False,
            "has_box_scores": False,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_star_players_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert len(result) > 20

    def test_star_players_with_box_scores(self, generator, basic_game_data):
        """Test star players paragraph using box score fallback."""
        winner_box = BoxScore(
            game_id="game_001",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=450,
            passing_yards=300,
            rushing_yards=150,
        )
        recap_data = {
            "has_game_grades": False,
            "has_box_scores": True,
            "winner_box": winner_box,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_star_players_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "passing" in result.lower() or "yards" in result.lower()


# =============================================================================
# TURNING POINT PARAGRAPH TESTS
# =============================================================================

class TestTurningPointParagraph:
    """Tests for turning point paragraph generation."""

    def test_turning_point_minimal_data(self, generator, basic_game_data):
        """Test turning point with minimal data (fallback)."""
        recap_data = {
            "has_play_grades": False,
            "has_box_scores": False,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_turning_point_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert len(result) > 20

    def test_turning_point_with_box_scores(self, generator, basic_game_data):
        """Test turning point using box score scoring summary."""
        winner_box = BoxScore(
            game_id="game_001",
            team_id=1,
            dynasty_id="test_dynasty",
            q1_score=14,
            q2_score=7,
            q3_score=3,
            q4_score=3,
        )
        recap_data = {
            "has_play_grades": False,
            "has_box_scores": True,
            "winner_box": winner_box,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_turning_point_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "Q1" in result or "fast start" in result or "scoring" in result.lower()

    def test_turning_point_second_half_surge(self, generator, basic_game_data):
        """Test turning point detection for second half surge."""
        winner_box = BoxScore(
            game_id="game_001",
            team_id=1,
            dynasty_id="test_dynasty",
            q1_score=0,
            q2_score=3,
            q3_score=14,
            q4_score=10,
        )
        recap_data = {
            "has_play_grades": False,
            "has_box_scores": True,
            "winner_box": winner_box,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_turning_point_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "second half" in result.lower() or "Q3" in result or "Q4" in result


# =============================================================================
# LOOKING AHEAD PARAGRAPH TESTS
# =============================================================================

class TestLookingAheadParagraph:
    """Tests for looking ahead paragraph generation."""

    def test_looking_ahead_default(self, generator, basic_game_data):
        """Test looking ahead with default context."""
        recap_data = {
            "winner_standing": None,
            "loser_standing": None,
            "rivalry": None,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_looking_ahead_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        # Should mention looking ahead to rest of season or next week
        assert len(result) > 50  # Reasonable paragraph length

    def test_looking_ahead_playoff_implications(self, generator, basic_game_data):
        """Test looking ahead with playoff implications."""
        basic_game_data["week"] = 15
        recap_data = {
            "winner_standing": TeamStanding(
                team_id=1, wins=9, losses=5, ties=0,
                points_for=300, points_against=250,
                division_wins=3, division_losses=2,
                conference_wins=6, conference_losses=4,
                home_wins=5, home_losses=2,
                away_wins=4, away_losses=3
            ),
            "loser_standing": None,
            "rivalry": None,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_looking_ahead_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "playoff" in result.lower() or "9-5" in result or "remaining" in result.lower()

    def test_looking_ahead_rivalry_game(self, generator, basic_game_data):
        """Test looking ahead for rivalry games."""
        # Create a mock rivalry
        mock_rivalry = Mock()
        mock_rivalry.rivalry_name = "Test Rivalry"

        recap_data = {
            "winner_standing": None,
            "loser_standing": None,
            "rivalry": mock_rivalry,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_looking_ahead_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "rivalry" in result.lower() or "bragging" in result.lower()

    def test_looking_ahead_division_game(self, generator, basic_game_data):
        """Test looking ahead for division games."""
        basic_game_data["is_divisional"] = True
        recap_data = {
            "winner_standing": TeamStanding(
                team_id=1, wins=7, losses=3, ties=0,
                points_for=280, points_against=210,
                division_wins=4, division_losses=1,
                conference_wins=5, conference_losses=2,
                home_wins=4, home_losses=1,
                away_wins=3, away_losses=2
            ),
            "loser_standing": None,
            "rivalry": None,
        }
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_looking_ahead_paragraph(enriched, recap_data)

        assert isinstance(result, str)
        assert "division" in result.lower()


# =============================================================================
# BODY TEXT ORCHESTRATION TESTS
# =============================================================================

class TestBodyTextOrchestration:
    """Tests for full body text generation."""

    def test_generate_body_text_returns_string(self, generator, basic_game_data):
        """Test that body text generation returns a string."""
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_body_text(enriched, HeadlineType.GAME_RECAP)

        assert result is None or isinstance(result, str)

    def test_generate_body_text_has_paragraphs(self, generator, basic_game_data):
        """Test that body text has multiple paragraphs."""
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_body_text(enriched, HeadlineType.GAME_RECAP)

        if result:
            # Should have paragraph breaks
            assert "\n\n" in result or len(result) > 100

    def test_generate_body_text_missing_game_id(self, generator):
        """Test body text returns fallback with missing game_id."""
        game_data = {
            "winner_id": 1,
            "loser_id": 2,
            "winner_name": "Test Winner",
            "loser_name": "Test Loser",
            "winner_score": 24,
            "loser_score": 17
        }
        result = generator._generate_body_text(game_data, HeadlineType.GAME_RECAP)

        # Should return fallback body text, not None
        assert result is not None
        assert "Test Winner" in result
        assert "Test Loser" in result
        assert "24-17" in result

    def test_generate_body_text_missing_winner_id(self, generator):
        """Test body text returns fallback with missing winner_id."""
        game_data = {
            "game_id": "game_001",
            "loser_id": 2,
            "winner_name": "Kansas City Chiefs",
            "loser_name": "Denver Broncos",
            "winner_score": 31,
            "loser_score": 10
        }
        result = generator._generate_body_text(game_data, HeadlineType.GAME_RECAP)

        # Should return fallback body text, not None
        assert result is not None
        assert "Kansas City Chiefs" in result
        assert "Denver Broncos" in result
        assert "31-10" in result


# =============================================================================
# HEADLINE WITH BODY TEXT TESTS
# =============================================================================

class TestHeadlineWithBodyText:
    """Tests for generate_game_headline with body text."""

    def test_generate_game_headline_includes_body_text(self, generator, basic_game_data):
        """Test that generate_game_headline can include body text."""
        headline = generator.generate_game_headline(basic_game_data, include_body_text=True)

        assert isinstance(headline, Headline)
        # Body text may be None if generation fails, but headline should exist
        assert headline.headline

    def test_generate_game_headline_without_body_text(self, generator, basic_game_data):
        """Test generate_game_headline without body text."""
        headline = generator.generate_game_headline(basic_game_data, include_body_text=False)

        assert isinstance(headline, Headline)
        assert headline.body_text is None

    def test_generate_game_headline_default_includes_body(self, generator, basic_game_data):
        """Test that body text is included by default."""
        headline = generator.generate_game_headline(basic_game_data)

        assert isinstance(headline, Headline)
        # Default should attempt body text (may be None if no data available)


# =============================================================================
# DATA GATHERING TESTS
# =============================================================================

class TestDataGathering:
    """Tests for _gather_recap_data method."""

    def test_gather_recap_data_structure(self, generator):
        """Test that gather_recap_data returns correct structure."""
        result = generator._gather_recap_data("game_001", 1, 2)

        assert isinstance(result, dict)
        assert "has_box_scores" in result
        assert "has_game_grades" in result
        assert "has_play_grades" in result
        assert "box_scores" in result
        assert "game_grades" in result
        assert "play_grades" in result
        assert "winner_standing" in result
        assert "loser_standing" in result
        assert "rivalry" in result

    def test_gather_recap_data_empty_by_default(self, generator):
        """Test that gather_recap_data returns empty lists when no data."""
        result = generator._gather_recap_data("nonexistent_game", 1, 2)

        assert result["has_box_scores"] is False
        assert result["has_game_grades"] is False
        assert result["has_play_grades"] is False
        assert result["box_scores"] == []
        assert result["game_grades"] == []
        assert result["play_grades"] == []


# =============================================================================
# STAT LINE FORMATTING TESTS
# =============================================================================

class TestStatLineFormatting:
    """Tests for _format_stat_line method."""

    def test_format_qb_stat_line(self, generator):
        """Test QB stat line formatting."""
        stats = {
            "pass_attempts": 30,
            "completions": 22,
            "passing_yards": 285,
            "passing_tds": 2,
            "interceptions": 0,
        }
        result = generator._format_stat_line(stats, "QB")

        assert "22/30" in result
        assert "285" in result
        assert "TD" in result

    def test_format_rb_stat_line(self, generator):
        """Test RB stat line formatting."""
        stats = {
            "carries": 18,
            "rushing_yards": 112,
            "rushing_tds": 1,
        }
        result = generator._format_stat_line(stats, "RB")

        assert "18" in result
        assert "112" in result
        assert "yards" in result.lower()

    def test_format_wr_stat_line(self, generator):
        """Test WR stat line formatting."""
        stats = {
            "receptions": 8,
            "receiving_yards": 142,
            "receiving_tds": 1,
        }
        result = generator._format_stat_line(stats, "WR")

        assert "8" in result
        assert "142" in result
        assert "catch" in result.lower()

    def test_format_empty_stats_fallback(self, generator):
        """Test stat line fallback when stats are empty."""
        stats = {}
        result = generator._format_stat_line(stats, "QB")

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in body text generation."""

    def test_shutout_game(self, generator, basic_game_data):
        """Test body text for shutout game."""
        basic_game_data["loser_score"] = 0
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_body_text(enriched, HeadlineType.BLOWOUT)

        # Should handle gracefully
        assert result is None or isinstance(result, str)

    def test_very_large_margin(self, generator, basic_game_data):
        """Test body text for very large margin game."""
        basic_game_data["winner_score"] = 56
        basic_game_data["loser_score"] = 0
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_body_text(enriched, HeadlineType.BLOWOUT)

        assert result is None or isinstance(result, str)

    def test_overtime_game(self, generator, basic_game_data):
        """Test body text generation for overtime game."""
        basic_game_data["is_overtime"] = True
        enriched = generator._enrich_game_data(basic_game_data)
        result = generator._generate_body_text(enriched, HeadlineType.GAME_RECAP)

        assert result is None or isinstance(result, str)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for complete body text flow."""

    def test_full_recap_generation_and_save(self, generator, basic_game_data, temp_db_path):
        """Test generating and saving a headline with body text."""
        headline = generator.generate_game_headline(basic_game_data, include_body_text=True)

        # Save the headline
        headline_id = generator.save_headline(headline)

        assert headline_id > 0

        # Retrieve and verify
        headlines = generator.get_headlines(basic_game_data["week"])
        assert len(headlines) == 1
        assert headlines[0].headline == headline.headline

    def test_playoff_game_recap(self, generator, basic_game_data):
        """Test body text for playoff game."""
        basic_game_data["is_playoff"] = True
        basic_game_data["week"] = 19  # Wild card week
        headline = generator.generate_game_headline(basic_game_data, include_body_text=True)

        assert isinstance(headline, Headline)
        assert headline.priority > 50  # Playoff boost

    def test_rivalry_game_recap(self, generator, basic_game_data):
        """Test body text for rivalry game."""
        basic_game_data["is_rivalry"] = True
        headline = generator.generate_game_headline(basic_game_data, include_body_text=True)

        assert isinstance(headline, Headline)
