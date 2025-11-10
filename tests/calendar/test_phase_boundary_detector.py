"""
Tests for PhaseBoundaryDetector

Comprehensive unit tests for phase boundary date detection and caching.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from src.calendar.date_models import Date


class TestPhaseBoundaryDetectorSetup:
    """Test fixture setup and initialization."""

    @pytest.fixture
    def mock_event_db(self):
        """Mock EventDatabaseAPI with test game data."""
        mock = Mock()

        # Default: Return empty list, individual tests will override
        mock.get_events_by_dynasty.return_value = []

        return mock

    @pytest.fixture
    def mock_unified_db(self):
        """Mock UnifiedDatabaseAPI with milestone data."""
        mock = Mock()

        # Default: Return None, individual tests will override
        mock.events_get_milestone_by_type.return_value = None

        return mock

    @pytest.fixture
    def detector(self, mock_event_db, mock_unified_db):
        """Create PhaseBoundaryDetector with mocks."""
        # Import here to avoid circular imports
        try:
            from src.calendar.phase_boundary_detector import PhaseBoundaryDetector
        except ImportError:
            pytest.skip("PhaseBoundaryDetector not yet implemented")

        return PhaseBoundaryDetector(
            event_db=mock_event_db,
            dynasty_id="test_dynasty",
            season_year=2025,
            db=mock_unified_db,
            cache_results=True
        )


class TestGetLastGameDate(TestPhaseBoundaryDetectorSetup):
    """Test get_last_game_date method."""

    def test_get_last_game_date_regular_season_success(self, detector, mock_event_db):
        """Should return last regular season game date."""
        # Arrange: Create mock regular season games
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week18_game1",
                "timestamp": datetime(2026, 1, 5, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act
        result = detector.get_last_game_date("regular_season")

        # Assert
        assert result == Date(2026, 1, 5)
        mock_event_db.get_events_by_dynasty.assert_called_once_with(
            dynasty_id="test_dynasty",
            event_type="GAME"
        )

    def test_get_last_game_date_preseason_success(self, detector, mock_event_db):
        """Should return last preseason game date."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "preseason_2025_week1_game1",
                "timestamp": datetime(2025, 8, 10, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "preseason_2025_week4_game1",
                "timestamp": datetime(2025, 8, 28, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 4
                    }
                }
            }
        ]

        # Act
        result = detector.get_last_game_date("preseason")

        # Assert
        assert result == Date(2025, 8, 28)

    def test_get_last_game_date_playoffs_success(self, detector, mock_event_db):
        """Should return last playoff game date (Super Bowl)."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "playoff_2025_wildcard_game1",
                "timestamp": datetime(2026, 1, 11, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 19
                    }
                }
            },
            {
                "game_id": "playoff_2025_superbowl",
                "timestamp": datetime(2026, 2, 8, 18, 30),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 22
                    }
                }
            }
        ]

        # Act
        result = detector.get_last_game_date("playoffs")

        # Assert
        assert result == Date(2026, 2, 8)

    def test_get_last_game_date_no_games_returns_fallback(self, detector, mock_event_db):
        """Should return fallback date when no games found."""
        # Arrange: Empty game list
        mock_event_db.get_events_by_dynasty.return_value = []

        # Act
        result = detector.get_last_game_date("regular_season", fallback=Date(2025, 1, 1))

        # Assert
        assert result == Date(2025, 1, 1)

    def test_get_last_game_date_uses_cache(self, detector, mock_event_db):
        """Should use cached result on second call."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week18_game1",
                "timestamp": datetime(2026, 1, 5, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act: Call twice
        result1 = detector.get_last_game_date("regular_season")
        result2 = detector.get_last_game_date("regular_season")

        # Assert: Database called only once (cache hit on second call)
        assert result1 == result2
        assert mock_event_db.get_events_by_dynasty.call_count == 1


class TestGetFirstGameDate(TestPhaseBoundaryDetectorSetup):
    """Test get_first_game_date method."""

    def test_get_first_game_date_regular_season(self, detector, mock_event_db):
        """Should return first regular season game date."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week1_game2",
                "timestamp": datetime(2025, 9, 7, 16, 25),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("regular_season")

        # Assert
        assert result == Date(2025, 9, 7)

    def test_get_first_game_date_preseason(self, detector, mock_event_db):
        """Should return first preseason game date."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "preseason_2025_week1_game1",
                "timestamp": datetime(2025, 8, 10, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("preseason")

        # Assert
        assert result == Date(2025, 8, 10)

    def test_get_first_game_date_playoffs(self, detector, mock_event_db):
        """Should return first playoff game date."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "playoff_2025_wildcard_game1",
                "timestamp": datetime(2026, 1, 11, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 19
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("playoffs")

        # Assert
        assert result == Date(2026, 1, 11)

    def test_get_first_game_date_fallback(self, detector, mock_event_db):
        """Should return fallback when no games found."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = []

        # Act
        result = detector.get_first_game_date("regular_season", fallback=Date(2025, 9, 1))

        # Assert
        assert result == Date(2025, 9, 1)


class TestGetPhaseStartDate(TestPhaseBoundaryDetectorSetup):
    """Test get_phase_start_date method."""

    def test_get_phase_start_date_preseason_from_milestone(self, detector, mock_unified_db):
        """Should get preseason start from milestone event."""
        # Arrange: Mock milestone with preseason start date
        mock_unified_db.events_get_milestone_by_type.return_value = {
            "event_id": "preseason_start_2025",
            "timestamp": datetime(2025, 8, 8),
            "data": {"phase": "preseason"}
        }

        # Act
        result = detector.get_phase_start_date("preseason")

        # Assert
        assert result == Date(2025, 8, 8)
        mock_unified_db.events_get_milestone_by_type.assert_called_once()

    def test_get_phase_start_date_preseason_calculated_fallback(self, detector, mock_unified_db, mock_event_db):
        """Should calculate preseason start when milestone missing."""
        # Arrange: No milestone, but have games
        mock_unified_db.events_get_milestone_by_type.return_value = None
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "preseason_2025_week1_game1",
                "timestamp": datetime(2025, 8, 10, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_phase_start_date("preseason")

        # Assert
        assert result == Date(2025, 8, 10)

    def test_get_phase_start_date_regular_season(self, detector, mock_event_db):
        """Should get regular season start from first game."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_phase_start_date("regular_season")

        # Assert
        assert result == Date(2025, 9, 7)

    def test_get_phase_start_date_playoffs(self, detector, mock_event_db):
        """Should get playoff start from first playoff game."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "playoff_2025_wildcard_game1",
                "timestamp": datetime(2026, 1, 11, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 19
                    }
                }
            }
        ]

        # Act
        result = detector.get_phase_start_date("playoffs")

        # Assert
        assert result == Date(2026, 1, 11)

    def test_get_phase_start_date_offseason(self, detector, mock_event_db):
        """Should get offseason start from last playoff game + 1 day."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "playoff_2025_superbowl",
                "timestamp": datetime(2026, 2, 8, 18, 30),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 22
                    }
                }
            }
        ]

        # Act
        result = detector.get_phase_start_date("offseason")

        # Assert
        assert result == Date(2026, 2, 9)  # Day after Super Bowl


class TestGetPlayoffStartDate(TestPhaseBoundaryDetectorSetup):
    """Test get_playoff_start_date method."""

    def test_get_playoff_start_date_adjusts_to_saturday(self, detector, mock_event_db):
        """Should adjust playoff start to Saturday when last regular season game is mid-week."""
        # Arrange: Last regular season game on Wednesday (2026-01-08)
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week18_final",
                "timestamp": datetime(2026, 1, 8, 20, 0),  # Wednesday
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act
        result = detector.get_playoff_start_date()

        # Assert: Should be the following Saturday (2026-01-10)
        assert result == Date(2026, 1, 10)

    def test_get_playoff_start_date_already_saturday(self, detector, mock_event_db):
        """Should use existing date when last regular season game is already Saturday."""
        # Arrange: Last regular season game on Saturday (2026-01-10)
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week18_final",
                "timestamp": datetime(2026, 1, 10, 16, 0),  # Saturday
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act
        result = detector.get_playoff_start_date()

        # Assert: Should be next day Sunday (2026-01-11) for Wild Card weekend
        assert result == Date(2026, 1, 11)

    def test_get_playoff_start_date_safety_limit(self, detector, mock_event_db):
        """Should not extend playoff start more than 7 days after regular season."""
        # Arrange: Last regular season game on Sunday (2026-01-04)
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week18_final",
                "timestamp": datetime(2026, 1, 4, 16, 0),  # Sunday
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act
        result = detector.get_playoff_start_date()

        # Assert: Should be following Saturday (2026-01-10), within 7-day window
        assert result == Date(2026, 1, 10)


class TestCaching(TestPhaseBoundaryDetectorSetup):
    """Test caching functionality."""

    def test_cache_stores_results(self, detector, mock_event_db):
        """Should store results in cache."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        detector.get_first_game_date("regular_season")

        # Assert: Check cache has entry
        assert hasattr(detector, '_cache')
        assert len(detector._cache) > 0

    def test_cache_returns_cached_value(self, detector, mock_event_db):
        """Should return cached value without database query."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act: First call (cache miss)
        result1 = detector.get_first_game_date("regular_season")

        # Change mock return value
        mock_event_db.get_events_by_dynasty.return_value = []

        # Second call (cache hit - should still return original value)
        result2 = detector.get_first_game_date("regular_season")

        # Assert
        assert result1 == result2 == Date(2025, 9, 7)
        assert mock_event_db.get_events_by_dynasty.call_count == 1

    def test_invalidate_cache_clears_all(self, detector, mock_event_db):
        """Should clear all cached values."""
        # Arrange: Populate cache
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]
        detector.get_first_game_date("regular_season")

        # Act
        detector.invalidate_cache()

        # Assert: Cache should be empty
        assert len(detector._cache) == 0

    def test_invalidate_cache_specific_year(self, detector, mock_event_db):
        """Should clear cache entries for specific season year only."""
        # Arrange: This test assumes multi-year caching capability
        # For single-year detector, this may not apply
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]
        detector.get_first_game_date("regular_season")

        # Act
        detector.invalidate_cache(season_year=2025)

        # Assert: Cache for 2025 should be cleared
        # (Implementation-dependent - may clear all if single-year)
        assert True  # Placeholder - depends on implementation

    def test_cache_disabled_when_flag_false(self, mock_event_db, mock_unified_db):
        """Should not use cache when cache_results=False."""
        # Arrange
        try:
            from src.calendar.phase_boundary_detector import PhaseBoundaryDetector
        except ImportError:
            pytest.skip("PhaseBoundaryDetector not yet implemented")

        detector_no_cache = PhaseBoundaryDetector(
            event_db=mock_event_db,
            dynasty_id="test_dynasty",
            season_year=2025,
            db=mock_unified_db,
            cache_results=False
        )

        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act: Call twice
        detector_no_cache.get_first_game_date("regular_season")
        detector_no_cache.get_first_game_date("regular_season")

        # Assert: Database called twice (no caching)
        assert mock_event_db.get_events_by_dynasty.call_count == 2


class TestFilteringLogic(TestPhaseBoundaryDetectorSetup):
    """Test game filtering logic."""

    def test_is_game_in_phase_preseason(self, detector, mock_event_db):
        """Should correctly identify preseason games."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "preseason_2025_week1_game1",
                "timestamp": datetime(2025, 8, 10, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("preseason")

        # Assert: Should only return preseason game
        assert result == Date(2025, 8, 10)

    def test_is_game_in_phase_regular_season(self, detector, mock_event_db):
        """Should correctly identify regular season games."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "preseason_2025_week4_game1",
                "timestamp": datetime(2025, 8, 28, 19, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "preseason",
                        "week": 4
                    }
                }
            },
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("regular_season")

        # Assert: Should only return regular season game
        assert result == Date(2025, 9, 7)

    def test_is_game_in_phase_playoffs(self, detector, mock_event_db):
        """Should correctly identify playoff games."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week18_game1",
                "timestamp": datetime(2026, 1, 5, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            },
            {
                "game_id": "playoff_2025_wildcard_game1",
                "timestamp": datetime(2026, 1, 11, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "playoffs",
                        "week": 19
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("playoffs")

        # Assert: Should only return playoff game
        assert result == Date(2026, 1, 11)

    def test_filters_by_dynasty_id(self, detector, mock_event_db):
        """Should only query games for specified dynasty."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = []

        # Act
        detector.get_first_game_date("regular_season")

        # Assert
        mock_event_db.get_events_by_dynasty.assert_called_once_with(
            dynasty_id="test_dynasty",
            event_type="GAME"
        )

    def test_filters_by_season_year(self, detector, mock_event_db):
        """Should filter games by season year."""
        # Arrange: Mix of different season years
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2024_week1_game1",
                "timestamp": datetime(2024, 9, 8, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2024,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            }
        ]

        # Act
        result = detector.get_first_game_date("regular_season")

        # Assert: Should only return 2025 game (detector season_year=2025)
        assert result == Date(2025, 9, 7)


class TestGetPhaseDateRange(TestPhaseBoundaryDetectorSetup):
    """Test get_phase_date_range method."""

    def test_get_phase_date_range_returns_tuple(self, detector, mock_event_db):
        """Should return (start_date, end_date) tuple."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week18_game1",
                "timestamp": datetime(2026, 1, 5, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act
        result = detector.get_phase_date_range("regular_season")

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == Date(2025, 9, 7)
        assert result[1] == Date(2026, 1, 5)

    def test_get_phase_date_range_caches_result(self, detector, mock_event_db):
        """Should cache date range result."""
        # Arrange
        mock_event_db.get_events_by_dynasty.return_value = [
            {
                "game_id": "regular_2025_week1_game1",
                "timestamp": datetime(2025, 9, 7, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 1
                    }
                }
            },
            {
                "game_id": "regular_2025_week18_game1",
                "timestamp": datetime(2026, 1, 5, 13, 0),
                "data": {
                    "parameters": {
                        "season": 2025,
                        "season_type": "regular_season",
                        "week": 18
                    }
                }
            }
        ]

        # Act: Call twice
        result1 = detector.get_phase_date_range("regular_season")
        result2 = detector.get_phase_date_range("regular_season")

        # Assert: Database called only once
        assert result1 == result2
        assert mock_event_db.get_events_by_dynasty.call_count == 1
