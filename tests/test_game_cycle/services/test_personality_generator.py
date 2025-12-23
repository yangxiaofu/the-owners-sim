"""
Tests for PersonalityGenerator service.

Covers:
- Dynasty-wide personality generation (296-424 total)
- Fan personality generation (8-12 per team)
- Beat reporter generation (1 per team)
- League-wide media generation (HOT_TAKE, STATS_ANALYST)
- Handle uniqueness enforcement
- Template-based name generation
- Validation logic

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 8.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path

from src.game_cycle.services.personality_generator import (
    PersonalityGenerator,
    generate_personalities_for_dynasty,
    FAN_ARCHETYPES,
    MEDIA_TYPES
)


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_templates():
    """Mock template configuration data."""
    return {
        'team_data': {
            '1': {'abbrev': 'BUF', 'nickname': 'Bills', 'city': 'Buffalo'},
            '2': {'abbrev': 'MIA', 'nickname': 'Dolphins', 'city': 'Miami'},
            '3': {'abbrev': 'NE', 'nickname': 'Patriots', 'city': 'New England'},
        },
        'fan_name_templates': {
            'OPTIMIST': {
                'handles': ['{abbrev}Believer', '{nickname}Fan'],
                'display_names': ['{city} Believer', '{nickname} Superfan']
            },
            'PESSIMIST': {
                'handles': ['{abbrev}Doom', '{nickname}Pessimist'],
                'display_names': ['{city} Cynic', '{nickname} Skeptic']
            },
            'BANDWAGON': {
                'handles': ['{abbrev}Bandwagon', '{nickname}NewFan'],
                'display_names': ['{city} Bandwagon', '{nickname} New Fan']
            }
        },
        'media_name_templates': {
            'BEAT_REPORTER': {
                'handles': ['{abbrev}Insider', '{abbrev}Reporter'],
                'display_names': ['{abbrev} Insider', '{abbrev} Beat Writer']
            },
            'HOT_TAKE': {
                'handles': ['HotTakeKing', 'ControversialCoach', 'SkipBaylessClone'],
                'display_names': ['Hot Take King', 'Controversial Coach', 'Skip Bayless Clone']
            },
            'STATS_ANALYST': {
                'handles': ['StatsGuru', 'NumbersCruncher', 'AnalyticsNerd'],
                'display_names': ['Stats Guru', 'Numbers Cruncher', 'Analytics Nerd']
            }
        },
        'archetype_sentiment_biases': {
            'OPTIMIST': 0.5,
            'PESSIMIST': -0.5,
            'BANDWAGON': 0.3,
            'STATS_NERD': 0.0,
            'OLD_TIMER': -0.2,
            'HOT_HEAD': 0.0,
            'MEME_LORD': 0.4,
            'TRADE_ANALYST': 0.0,
            'CONSPIRACY': -0.3,
            'BALANCED': 0.0
        },
        'archetype_posting_frequencies': {
            'OPTIMIST': 'ALL_EVENTS',
            'PESSIMIST': 'LOSS_ONLY',
            'BANDWAGON': 'WIN_ONLY',
            'STATS_NERD': 'ALL_EVENTS',
            'OLD_TIMER': 'ALL_EVENTS',
            'HOT_HEAD': 'EMOTIONAL_MOMENTS',
            'MEME_LORD': 'ALL_EVENTS',
            'TRADE_ANALYST': 'ALL_EVENTS',
            'CONSPIRACY': 'ALL_EVENTS',
            'BALANCED': 'ALL_EVENTS'
        }
    }


@pytest.fixture
def mock_db():
    """Mock GameCycleDatabase instance."""
    return MagicMock()


@pytest.fixture
def mock_personality_api():
    """Mock SocialPersonalityAPI."""
    api = MagicMock()
    api.create_personality.side_effect = lambda **kwargs: len(api.create_personality.call_args_list)
    api.get_all_personalities.return_value = []
    return api


@pytest.fixture
def generator(mock_db, mock_personality_api, mock_templates):
    """Create PersonalityGenerator with mocked dependencies."""
    with patch('src.game_cycle.services.personality_generator.SocialPersonalityAPI', return_value=mock_personality_api):
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_templates))):
            gen = PersonalityGenerator(mock_db, dynasty_id='test_dynasty')
            gen.api = mock_personality_api
            gen.templates = mock_templates
            return gen


# ==========================================
# TEAM FAN GENERATION
# ==========================================

class TestTeamFanGeneration:
    """Test team-specific fan personality generation."""

    def test_generates_8_to_12_fans_per_team(self, generator):
        """Each team should get 8-12 fan personalities."""
        personality_ids = generator._generate_team_fans(team_id=1)

        assert len(personality_ids) >= 8
        assert len(personality_ids) <= 12

    def test_fans_use_valid_archetypes(self, generator, mock_personality_api):
        """All fans should use valid FAN_ARCHETYPES."""
        generator._generate_team_fans(team_id=1)

        # Check each create_personality call used valid archetype
        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'FAN':
                assert kwargs['archetype'] in FAN_ARCHETYPES

    def test_fans_assigned_to_correct_team(self, generator, mock_personality_api):
        """All fans should be assigned to the correct team."""
        generator._generate_team_fans(team_id=5)

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'FAN':
                assert kwargs['team_id'] == 5

    def test_fan_sentiment_bias_matches_archetype(self, generator, mock_personality_api, mock_templates):
        """Fan sentiment bias should match archetype configuration."""
        # Manually add full archetype templates
        for archetype in FAN_ARCHETYPES:
            if archetype not in generator.templates['fan_name_templates']:
                generator.templates['fan_name_templates'][archetype] = {
                    'handles': ['Test'],
                    'display_names': ['Test']
                }

        generator._generate_team_fans(team_id=1)

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'FAN':
                archetype = kwargs['archetype']
                expected_bias = mock_templates['archetype_sentiment_biases'][archetype]
                assert kwargs['sentiment_bias'] == expected_bias

    def test_fan_posting_frequency_matches_archetype(self, generator, mock_personality_api, mock_templates):
        """Fan posting frequency should match archetype configuration."""
        # Add templates for all archetypes
        for archetype in FAN_ARCHETYPES:
            if archetype not in generator.templates['fan_name_templates']:
                generator.templates['fan_name_templates'][archetype] = {
                    'handles': ['Test'],
                    'display_names': ['Test']
                }

        generator._generate_team_fans(team_id=1)

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'FAN':
                archetype = kwargs['archetype']
                expected_freq = mock_templates['archetype_posting_frequencies'][archetype]
                assert kwargs['posting_frequency'] == expected_freq


# ==========================================
# HANDLE GENERATION & UNIQUENESS
# ==========================================

class TestHandleGeneration:
    """Test handle/display name generation and uniqueness."""

    def test_handle_starts_with_at_symbol(self, generator):
        """All handles should start with '@'."""
        team_data = generator.templates['team_data']['1']
        templates = generator.templates['fan_name_templates']['OPTIMIST']

        handle, _ = generator._generate_handle_and_display(templates, team_data)

        assert handle.startswith('@')

    def test_template_placeholders_filled(self, generator):
        """Template placeholders should be replaced with team data."""
        team_data = {'abbrev': 'BUF', 'nickname': 'Bills', 'city': 'Buffalo'}
        templates = {
            'handles': ['{abbrev}Fan'],
            'display_names': ['{city} Superfan']
        }

        handle, display_name = generator._generate_handle_and_display(templates, team_data)

        assert handle == '@BUFFan'
        assert display_name == 'Buffalo Superfan'

    def test_handle_uniqueness_enforced(self, generator, mock_personality_api):
        """Duplicate handles should have numbers appended."""
        # First creation - handle is unique
        id1 = generator._create_fan_personality(team_id=1, archetype='OPTIMIST')
        first_handle = mock_personality_api.create_personality.call_args_list[0][1]['handle']

        # Second creation with same archetype/team - should get different handle
        id2 = generator._create_fan_personality(team_id=1, archetype='OPTIMIST')
        second_handle = mock_personality_api.create_personality.call_args_list[1][1]['handle']

        # Handles should be different (either by randomness or fallback numbering)
        assert first_handle != second_handle or first_handle.rstrip('0123456789') != second_handle.rstrip('0123456789')

    def test_handle_uniqueness_fallback_after_retries(self, generator, mock_personality_api):
        """After 10 retries, should append random number to ensure uniqueness."""
        # Fill used_handles to force collision
        generator.used_handles = {'@BUFBeliever', '@BillsFan'}

        # Mock template to always return same handle
        with patch.object(generator, '_generate_handle_and_display', return_value=('@BUFBeliever', 'Test Name')):
            personality_id = generator._create_fan_personality(team_id=1, archetype='OPTIMIST')

        # Should have created with modified handle
        created_handle = mock_personality_api.create_personality.call_args[1]['handle']
        assert created_handle.startswith('@BUFBeliever')
        assert created_handle != '@BUFBeliever'  # Should have number appended


# ==========================================
# BEAT REPORTER GENERATION
# ==========================================

class TestBeatReporterGeneration:
    """Test beat reporter personality generation."""

    def test_beat_reporter_uses_team_abbreviation(self, generator, mock_personality_api):
        """Beat reporters should use team abbreviation in handle."""
        generator._generate_beat_reporter(team_id=1)

        created_handle = mock_personality_api.create_personality.call_args[1]['handle']
        assert 'BUF' in created_handle

    def test_beat_reporter_has_neutral_sentiment(self, generator, mock_personality_api):
        """Beat reporters should have neutral sentiment bias (0.0)."""
        generator._generate_beat_reporter(team_id=1)

        kwargs = mock_personality_api.create_personality.call_args[1]
        assert kwargs['sentiment_bias'] == 0.0

    def test_beat_reporter_posts_on_all_events(self, generator, mock_personality_api):
        """Beat reporters should post on all events."""
        generator._generate_beat_reporter(team_id=1)

        kwargs = mock_personality_api.create_personality.call_args[1]
        assert kwargs['posting_frequency'] == 'ALL_EVENTS'

    def test_beat_reporter_assigned_to_team(self, generator, mock_personality_api):
        """Beat reporters should be assigned to their team."""
        generator._generate_beat_reporter(team_id=10)

        kwargs = mock_personality_api.create_personality.call_args[1]
        assert kwargs['team_id'] == 10
        assert kwargs['personality_type'] == 'BEAT_REPORTER'

    def test_beat_reporter_no_archetype(self, generator, mock_personality_api):
        """Beat reporters should have no archetype."""
        generator._generate_beat_reporter(team_id=1)

        kwargs = mock_personality_api.create_personality.call_args[1]
        assert kwargs['archetype'] is None


# ==========================================
# LEAGUE-WIDE MEDIA GENERATION
# ==========================================

class TestLeagueWideMediaGeneration:
    """Test league-wide media personality generation."""

    def test_hot_take_count_in_range(self, generator):
        """Should generate 5-8 hot-take analysts."""
        personality_ids = generator._generate_league_wide_media('HOT_TAKE')

        assert len(personality_ids) >= 5
        assert len(personality_ids) <= 8

    def test_stats_analyst_count_in_range(self, generator):
        """Should generate 3-5 stats analysts."""
        personality_ids = generator._generate_league_wide_media('STATS_ANALYST')

        assert len(personality_ids) >= 3
        assert len(personality_ids) <= 5

    def test_invalid_media_type_raises_error(self, generator):
        """Invalid media type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid media_type"):
            generator._generate_league_wide_media('INVALID_TYPE')

    def test_league_wide_media_has_no_team(self, generator, mock_personality_api):
        """League-wide media should have team_id=None."""
        generator._generate_league_wide_media('HOT_TAKE')

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            assert kwargs['team_id'] is None

    def test_hot_take_has_polarized_bias(self, generator, mock_personality_api):
        """Hot-take analysts should have slight sentiment bias (-0.3 to 0.3)."""
        generator._generate_league_wide_media('HOT_TAKE')

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'HOT_TAKE':
                assert -0.3 <= kwargs['sentiment_bias'] <= 0.3

    def test_stats_analyst_has_neutral_bias(self, generator, mock_personality_api):
        """Stats analysts should have neutral sentiment bias (0.0)."""
        generator._generate_league_wide_media('STATS_ANALYST')

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'STATS_ANALYST':
                assert kwargs['sentiment_bias'] == 0.0

    def test_hot_take_posts_on_emotional_moments(self, generator, mock_personality_api):
        """Hot-take analysts should post on emotional moments."""
        generator._generate_league_wide_media('HOT_TAKE')

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'HOT_TAKE':
                assert kwargs['posting_frequency'] == 'EMOTIONAL_MOMENTS'

    def test_stats_analyst_posts_on_all_events(self, generator, mock_personality_api):
        """Stats analysts should post on all events."""
        generator._generate_league_wide_media('STATS_ANALYST')

        for call in mock_personality_api.create_personality.call_args_list:
            kwargs = call[1]
            if kwargs['personality_type'] == 'STATS_ANALYST':
                assert kwargs['posting_frequency'] == 'ALL_EVENTS'


# ==========================================
# FULL GENERATION
# ==========================================

class TestFullGeneration:
    """Test complete dynasty personality generation."""

    def test_generate_all_personalities_creates_all_types(self, generator, mock_personality_api):
        """Should create fans, beat reporters, and league-wide media."""
        # Add templates for all archetypes
        for archetype in FAN_ARCHETYPES:
            if archetype not in generator.templates['fan_name_templates']:
                generator.templates['fan_name_templates'][archetype] = {
                    'handles': ['Test'],
                    'display_names': ['Test']
                }

        # Add team data for all 32 teams
        for team_id in range(1, 33):
            if str(team_id) not in generator.templates['team_data']:
                generator.templates['team_data'][str(team_id)] = {
                    'abbrev': f'T{team_id}',
                    'nickname': f'Team{team_id}',
                    'city': f'City{team_id}'
                }

        counts = generator.generate_all_personalities()

        assert counts['fans'] >= 256  # 8 per team * 32 teams
        assert counts['fans'] <= 384  # 12 per team * 32 teams
        assert counts['beat_reporters'] == 32  # 1 per team
        assert 5 <= counts['hot_takes'] <= 8
        assert 3 <= counts['stats_analysts'] <= 5

    def test_total_personality_count_in_range(self, generator, mock_personality_api):
        """Total personalities should be 296-424."""
        # Add templates for all archetypes
        for archetype in FAN_ARCHETYPES:
            if archetype not in generator.templates['fan_name_templates']:
                generator.templates['fan_name_templates'][archetype] = {
                    'handles': ['Test'],
                    'display_names': ['Test']
                }

        # Add team data for all 32 teams
        for team_id in range(1, 33):
            if str(team_id) not in generator.templates['team_data']:
                generator.templates['team_data'][str(team_id)] = {
                    'abbrev': f'T{team_id}',
                    'nickname': f'Team{team_id}',
                    'city': f'City{team_id}'
                }

        counts = generator.generate_all_personalities()
        total = counts['fans'] + counts['beat_reporters'] + counts['hot_takes'] + counts['stats_analysts']

        assert 296 <= total <= 424


# ==========================================
# VALIDATION
# ==========================================

class TestValidation:
    """Test personality generation validation."""

    def test_validate_checks_total_count(self, generator, mock_personality_api):
        """Validation should check total personality count."""
        # Mock 100 personalities (outside valid range)
        mock_personality_api.get_all_personalities.return_value = [Mock() for _ in range(100)]

        validation = generator.validate_generation()

        assert validation['valid'] is False
        assert any('Total personality count' in issue for issue in validation['issues'])

    def test_validate_checks_beat_reporter_count(self, generator, mock_personality_api):
        """Validation should ensure exactly 32 beat reporters."""
        # Mock 320 personalities with only 20 beat reporters
        personalities = [
            Mock(personality_type='BEAT_REPORTER', team_id=i, archetype=None)
            for i in range(1, 21)
        ]
        personalities.extend([
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST')
            for _ in range(300)
        ])
        mock_personality_api.get_all_personalities.return_value = personalities

        validation = generator.validate_generation()

        assert validation['valid'] is False
        assert any('32 beat reporters' in issue for issue in validation['issues'])

    def test_validate_checks_handle_uniqueness(self, generator, mock_personality_api):
        """Validation should detect duplicate handles."""
        # Create personalities with duplicate handles
        personalities = [
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST', handle='@DuplicateHandle'),
            Mock(personality_type='FAN', team_id=2, archetype='PESSIMIST', handle='@DuplicateHandle'),
            Mock(personality_type='FAN', team_id=3, archetype='BANDWAGON', handle='@UniqueHandle')
        ]
        mock_personality_api.get_all_personalities.return_value = personalities

        validation = generator.validate_generation()

        assert validation['valid'] is False
        assert any('Duplicate handles' in issue for issue in validation['issues'])

    def test_validate_success_for_valid_generation(self, generator, mock_personality_api):
        """Validation should pass for valid generation."""
        # Mock valid personality set
        personalities = []

        # 32 beat reporters
        for team_id in range(1, 33):
            personalities.append(
                Mock(personality_type='BEAT_REPORTER', team_id=team_id, archetype=None, handle=f'@BeatReporter{team_id}')
            )

        # 10 fans per team (320 total)
        for team_id in range(1, 33):
            for i in range(10):
                personalities.append(
                    Mock(personality_type='FAN', team_id=team_id, archetype='OPTIMIST', handle=f'@Fan{team_id}_{i}')
                )

        # 6 hot-take analysts
        for i in range(6):
            personalities.append(
                Mock(personality_type='HOT_TAKE', team_id=None, archetype=None, handle=f'@HotTake{i}')
            )

        # 4 stats analysts
        for i in range(4):
            personalities.append(
                Mock(personality_type='STATS_ANALYST', team_id=None, archetype=None, handle=f'@Stats{i}')
            )

        mock_personality_api.get_all_personalities.return_value = personalities

        validation = generator.validate_generation()

        assert validation['valid'] is True
        assert len(validation['issues']) == 0


# ==========================================
# SUMMARY GENERATION
# ==========================================

class TestSummaryGeneration:
    """Test generation summary statistics."""

    def test_summary_includes_total_count(self, generator, mock_personality_api):
        """Summary should include total personality count."""
        mock_personality_api.get_all_personalities.return_value = [
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST')
            for _ in range(10)
        ]

        summary = generator.get_generation_summary()

        assert summary['total'] == 10

    def test_summary_groups_by_type(self, generator, mock_personality_api):
        """Summary should group personalities by type."""
        mock_personality_api.get_all_personalities.return_value = [
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST'),
            Mock(personality_type='FAN', team_id=2, archetype='PESSIMIST'),
            Mock(personality_type='BEAT_REPORTER', team_id=1, archetype=None),
            Mock(personality_type='HOT_TAKE', team_id=None, archetype=None)
        ]

        summary = generator.get_generation_summary()

        assert summary['by_type']['FAN'] == 2
        assert summary['by_type']['BEAT_REPORTER'] == 1
        assert summary['by_type']['HOT_TAKE'] == 1

    def test_summary_groups_by_team(self, generator, mock_personality_api):
        """Summary should group personalities by team."""
        mock_personality_api.get_all_personalities.return_value = [
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST'),
            Mock(personality_type='FAN', team_id=1, archetype='PESSIMIST'),
            Mock(personality_type='FAN', team_id=2, archetype='OPTIMIST')
        ]

        summary = generator.get_generation_summary()

        assert summary['by_team'][1] == 2
        assert summary['by_team'][2] == 1

    def test_summary_groups_by_archetype(self, generator, mock_personality_api):
        """Summary should group fan personalities by archetype."""
        mock_personality_api.get_all_personalities.return_value = [
            Mock(personality_type='FAN', team_id=1, archetype='OPTIMIST'),
            Mock(personality_type='FAN', team_id=2, archetype='OPTIMIST'),
            Mock(personality_type='FAN', team_id=3, archetype='PESSIMIST')
        ]

        summary = generator.get_generation_summary()

        assert summary['by_archetype']['OPTIMIST'] == 2
        assert summary['by_archetype']['PESSIMIST'] == 1


# ==========================================
# CONVENIENCE FUNCTION
# ==========================================

class TestConvenienceFunction:
    """Test convenience function for full generation."""

    @patch('src.game_cycle.services.personality_generator.PersonalityGenerator')
    def test_convenience_function_returns_complete_results(self, mock_generator_class, mock_db):
        """Convenience function should return counts, summary, and validation."""
        mock_instance = Mock()
        mock_instance.generate_all_personalities.return_value = {
            'fans': 320,
            'beat_reporters': 32,
            'hot_takes': 6,
            'stats_analysts': 4
        }
        mock_instance.get_generation_summary.return_value = {'total': 362}
        mock_instance.validate_generation.return_value = {'valid': True, 'issues': []}
        mock_generator_class.return_value = mock_instance

        results = generate_personalities_for_dynasty(mock_db, 'test_dynasty')

        assert 'counts' in results
        assert 'summary' in results
        assert 'validation' in results
        assert results['counts']['fans'] == 320
        assert results['validation']['valid'] is True
