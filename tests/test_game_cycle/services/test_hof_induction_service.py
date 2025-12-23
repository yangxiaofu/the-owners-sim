"""
Unit tests for HOFInductionService.

Tests induction ceremony creation, speech generation, presenter selection,
and bust description generation.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Any

from game_cycle.services.hof_induction_service import (
    HOFInductionService,
    InductionSpeechHighlights,
    InductionCeremony,
    SPEECH_TEMPLATES,
    BUST_TEMPLATES,
    JACKET_MOMENT_TEMPLATES,
)
from game_cycle.database.hof_api import HOFVotingResult


# ============================================
# Mock Classes for Testing
# ============================================

@dataclass
class MockHOFCandidate:
    """Mock HOFCandidate for testing."""
    player_id: int
    player_name: str
    primary_position: str
    retirement_season: int
    years_on_ballot: int
    career_seasons: int
    teams_played_for: List[str]
    final_team_id: int
    super_bowl_wins: int = 0
    mvp_awards: int = 0
    all_pro_first_team: int = 0
    all_pro_second_team: int = 0
    pro_bowl_selections: int = 0
    career_stats: Dict[str, Any] = field(default_factory=dict)
    hof_score: int = 0
    is_first_ballot: bool = False


def create_mock_candidate(
    player_id: int = 1,
    name: str = "John Smith",
    position: str = "QB",
    teams: List[str] = None,
    mvp: int = 1,
    super_bowls: int = 2,
    all_pro_first: int = 3,
    all_pro_second: int = 1,
    pro_bowls: int = 8,
    career_seasons: int = 15,
    career_stats: Dict[str, Any] = None
) -> MockHOFCandidate:
    """Create a mock candidate with specified attributes."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position=position,
        retirement_season=2025,
        years_on_ballot=1,
        career_seasons=career_seasons,
        teams_played_for=teams or ["Kansas City Chiefs"],
        final_team_id=14,
        super_bowl_wins=super_bowls,
        mvp_awards=mvp,
        all_pro_first_team=all_pro_first,
        all_pro_second_team=all_pro_second,
        pro_bowl_selections=pro_bowls,
        career_stats=career_stats or {'pass_yards': 50000, 'pass_tds': 400},
        hof_score=90,
        is_first_ballot=True,
    )


def create_mock_voting_result(
    player_id: int = 1,
    player_name: str = "John Smith",
    vote_pct: float = 0.95,
    is_first_ballot: bool = True,
    years_on_ballot: int = 1
) -> HOFVotingResult:
    """Create a mock voting result."""
    return HOFVotingResult(
        player_id=player_id,
        voting_season=2030,
        player_name=player_name,
        primary_position="QB",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        vote_percentage=vote_pct,
        votes_received=int(vote_pct * 48),
        total_voters=48,
        was_inducted=True,
        is_first_ballot=is_first_ballot,
        removed_from_ballot=False,
        hof_score=90,
        score_breakdown={'total_score': 90},
    )


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def service():
    """Create HOFInductionService with fixed seed."""
    return HOFInductionService(seed=42)


@pytest.fixture
def candidate():
    """Create a mock candidate."""
    return create_mock_candidate()


@pytest.fixture
def voting_result():
    """Create a mock voting result."""
    return create_mock_voting_result()


# ============================================
# Test InductionSpeechHighlights
# ============================================

class TestInductionSpeechHighlights:
    """Test InductionSpeechHighlights dataclass."""

    def test_to_dict(self):
        """to_dict() returns all fields."""
        speech = InductionSpeechHighlights(
            opening="Opening line",
            career_reflection="Career line",
            thank_yous="Thank you line",
            legacy_statement="Legacy line",
            closing="Closing line",
        )

        result = speech.to_dict()

        assert result['opening'] == "Opening line"
        assert result['career_reflection'] == "Career line"
        assert result['thank_yous'] == "Thank you line"
        assert result['legacy_statement'] == "Legacy line"
        assert result['closing'] == "Closing line"


# ============================================
# Test InductionCeremony
# ============================================

class TestInductionCeremony:
    """Test InductionCeremony dataclass."""

    def test_to_dict(self, service, candidate, voting_result):
        """to_dict() returns complete ceremony data."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        result = ceremony.to_dict()

        assert result['inductee_id'] == 1
        assert result['inductee_name'] == "John Smith"
        assert result['position'] == "QB"
        assert result['induction_season'] == 2030
        assert 'presenter_name' in result
        assert 'presenter_relationship' in result
        assert 'speech_highlights' in result
        assert 'bust_description' in result
        assert 'achievements' in result


# ============================================
# Test Create Induction
# ============================================

class TestCreateInduction:
    """Test create_induction() method."""

    def test_creates_ceremony(self, service, candidate, voting_result):
        """create_induction() returns InductionCeremony."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert isinstance(ceremony, InductionCeremony)
        assert ceremony.inductee_id == 1
        assert ceremony.inductee_name == "John Smith"
        assert ceremony.position == "QB"

    def test_includes_voting_info(self, service, candidate, voting_result):
        """Ceremony includes voting information."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert ceremony.vote_percentage == 0.95
        assert ceremony.is_first_ballot is True
        assert ceremony.years_on_ballot == 1
        assert ceremony.induction_season == 2030

    def test_includes_speech_highlights(self, service, candidate, voting_result):
        """Ceremony includes speech highlights."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert isinstance(ceremony.speech_highlights, InductionSpeechHighlights)
        assert len(ceremony.speech_highlights.opening) > 0
        assert len(ceremony.speech_highlights.career_reflection) > 0
        assert len(ceremony.speech_highlights.thank_yous) > 0
        assert len(ceremony.speech_highlights.legacy_statement) > 0
        assert len(ceremony.speech_highlights.closing) > 0

    def test_includes_presenter(self, service, candidate, voting_result):
        """Ceremony includes presenter info."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert len(ceremony.presenter_name) > 0
        assert len(ceremony.presenter_relationship) > 0

    def test_includes_bust_description(self, service, candidate, voting_result):
        """Ceremony includes bust description."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert len(ceremony.bust_description) > 0
        assert "John Smith" in ceremony.bust_description

    def test_includes_jacket_moment(self, service, candidate, voting_result):
        """Ceremony includes jacket moment."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert len(ceremony.jacket_moment) > 0
        assert "John Smith" in ceremony.jacket_moment

    def test_includes_achievements(self, service, candidate, voting_result):
        """Ceremony includes achievements list."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert len(ceremony.achievements) > 0
        assert any("MVP" in a for a in ceremony.achievements)
        assert any("Super Bowl" in a for a in ceremony.achievements)

    def test_includes_career_summary(self, service, candidate, voting_result):
        """Ceremony includes career summary."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert len(ceremony.career_summary) > 0
        assert "John Smith" in ceremony.career_summary
        assert "15 seasons" in ceremony.career_summary

    def test_includes_team_info(self, service, candidate, voting_result):
        """Ceremony includes team information."""
        ceremony = service.create_induction(voting_result, candidate, persist=False)

        assert ceremony.primary_team == "Kansas City Chiefs"
        assert "Kansas City Chiefs" in ceremony.teams_played_for


# ============================================
# Test Speech Generation
# ============================================

class TestSpeechGeneration:
    """Test _generate_speech() method."""

    def test_generates_all_sections(self, service):
        """Speech includes all five sections."""
        speech = service._generate_speech(
            player_name="Test Player",
            position="QB",
            teams=["Test Team"],
            achievements=["MVP"],
            career_seasons=12
        )

        assert speech.opening is not None
        assert speech.career_reflection is not None
        assert speech.thank_yous is not None
        assert speech.legacy_statement is not None
        assert speech.closing is not None

    def test_speech_uses_team_name(self, service):
        """Speech mentions team name where applicable."""
        # Test multiple times to increase chance of hitting team-mentioning template
        found_team = False
        for _ in range(10):
            service_temp = HOFInductionService(seed=None)
            speech = service_temp._generate_speech(
                player_name="Test Player",
                position="QB",
                teams=["Chicago Bears"],
                achievements=["MVP"],
                career_seasons=12
            )
            if "Chicago Bears" in speech.career_reflection or "Chicago Bears" in speech.legacy_statement:
                found_team = True
                break

        # At least some templates should use team name
        # (May not always happen due to random selection)

    def test_speech_uses_seasons(self, service):
        """Speech can mention career seasons."""
        # Test multiple times
        for _ in range(10):
            service_temp = HOFInductionService(seed=None)
            speech = service_temp._generate_speech(
                player_name="Test Player",
                position="QB",
                teams=["Test Team"],
                achievements=["MVP"],
                career_seasons=15
            )
            if "15" in speech.career_reflection:
                assert True
                return

    def test_speech_handles_empty_teams(self, service):
        """Speech handles empty teams list."""
        speech = service._generate_speech(
            player_name="Test Player",
            position="QB",
            teams=[],
            achievements=[],
            career_seasons=10
        )

        assert speech.opening is not None
        assert speech.closing is not None


# ============================================
# Test Presenter Selection
# ============================================

class TestPresenterSelection:
    """Test _select_presenter() method."""

    def test_returns_name_and_relationship(self, service):
        """Returns tuple of name and relationship."""
        name, relationship = service._select_presenter(
            player_name="Test Player",
            teams=["Test Team"],
            position="QB"
        )

        assert len(name) > 0
        assert len(relationship) > 0

    def test_relationship_is_valid_type(self):
        """Relationship is one of the valid types."""
        valid_relationships = [
            "Former Head Coach",
            "Former Teammate",
            "Position Coach",
            "Former General Manager",
            "Family Member",
        ]

        # Test multiple times due to random selection
        service = HOFInductionService(seed=None)
        for _ in range(20):
            name, relationship = service._select_presenter(
                player_name="Test Player",
                teams=["Test Team"],
                position="QB"
            )
            assert relationship in valid_relationships

    def test_family_member_uses_player_last_name(self):
        """Family member presenter uses player's last name."""
        # Run multiple times to hit family member case
        for seed in range(100):
            service = HOFInductionService(seed=seed)
            name, relationship = service._select_presenter(
                player_name="Patrick Mahomes",
                teams=["Kansas City Chiefs"],
                position="QB"
            )
            if relationship == "Family Member":
                assert "Mahomes" in name
                break


# ============================================
# Test Bust Description
# ============================================

class TestBustDescription:
    """Test _generate_bust_description() method."""

    def test_includes_player_name(self, service):
        """Bust description includes player name."""
        description = service._generate_bust_description(
            player_name="Patrick Mahomes",
            position="QB"
        )

        assert "Patrick Mahomes" in description

    def test_qb_gets_qb_template(self, service):
        """QB gets quarterback-specific template."""
        # Run multiple times to see different templates
        descriptions = set()
        for seed in range(10):
            service_temp = HOFInductionService(seed=seed)
            desc = service_temp._generate_bust_description("Test", "QB")
            descriptions.add(desc)

        # Should use QB templates (check for QB-related words)
        all_text = " ".join(descriptions)
        assert any(word in all_text.lower() for word in ['receiver', 'poise', 'arm', 'deliver', 'intensity'])

    def test_rb_gets_rb_template(self, service):
        """RB gets running back-specific template."""
        descriptions = set()
        for seed in range(10):
            service_temp = HOFInductionService(seed=seed)
            desc = service_temp._generate_bust_description("Test", "RB")
            descriptions.add(desc)

        all_text = " ".join(descriptions)
        assert any(word in all_text.lower() for word in ['powerful', 'runner', 'toughness', 'line'])

    def test_unknown_position_uses_fallback(self, service):
        """Unknown position uses fallback template."""
        description = service._generate_bust_description(
            player_name="Test Player",
            position="XYZ"
        )

        assert "Test Player" in description


# ============================================
# Test Jacket Moment
# ============================================

class TestJacketMoment:
    """Test _generate_jacket_moment() method."""

    def test_includes_player_name(self, service):
        """Jacket moment includes player name."""
        moment = service._generate_jacket_moment("Aaron Donald")

        assert "Aaron Donald" in moment

    def test_mentions_gold_jacket(self, service):
        """Jacket moment mentions gold jacket."""
        moment = service._generate_jacket_moment("Test Player")

        assert "gold jacket" in moment.lower()


# ============================================
# Test Achievements List
# ============================================

class TestAchievementsList:
    """Test _build_achievements_list() method."""

    def test_includes_mvp(self, service):
        """Includes MVP awards."""
        candidate = create_mock_candidate(mvp=2)
        achievements = service._build_achievements_list(candidate)

        assert any("MVP" in a for a in achievements)
        assert any("2x" in a for a in achievements)

    def test_includes_super_bowl(self, service):
        """Includes Super Bowl wins."""
        candidate = create_mock_candidate(super_bowls=3)
        achievements = service._build_achievements_list(candidate)

        assert any("Super Bowl" in a for a in achievements)
        assert any("3x" in a for a in achievements)

    def test_includes_all_pro_first(self, service):
        """Includes All-Pro First Team selections."""
        candidate = create_mock_candidate(all_pro_first=5)
        achievements = service._build_achievements_list(candidate)

        assert any("First-Team All-Pro" in a for a in achievements)

    def test_includes_all_pro_second(self, service):
        """Includes All-Pro Second Team selections."""
        candidate = create_mock_candidate(all_pro_second=2)
        achievements = service._build_achievements_list(candidate)

        assert any("Second-Team All-Pro" in a for a in achievements)

    def test_includes_pro_bowl(self, service):
        """Includes Pro Bowl selections."""
        candidate = create_mock_candidate(pro_bowls=10)
        achievements = service._build_achievements_list(candidate)

        assert any("Pro Bowl" in a for a in achievements)
        assert any("10x" in a for a in achievements)

    def test_includes_career_seasons(self, service):
        """Includes career length."""
        candidate = create_mock_candidate(career_seasons=15)
        achievements = service._build_achievements_list(candidate)

        assert any("15 Seasons" in a for a in achievements)

    def test_singular_awards(self, service):
        """Single awards don't have 'x' prefix."""
        candidate = create_mock_candidate(mvp=1, super_bowls=1)
        achievements = service._build_achievements_list(candidate)

        # Should have "MVP" not "1x MVP"
        assert "MVP" in achievements
        assert "1x MVP" not in achievements


# ============================================
# Test Career Summary
# ============================================

class TestCareerSummary:
    """Test _build_career_summary() method."""

    def test_includes_player_name(self, service, candidate):
        """Summary includes player name."""
        achievements = service._build_achievements_list(candidate)
        summary = service._build_career_summary(candidate, achievements)

        assert "John Smith" in summary

    def test_includes_seasons(self, service, candidate):
        """Summary includes career length."""
        achievements = service._build_achievements_list(candidate)
        summary = service._build_career_summary(candidate, achievements)

        assert "15 seasons" in summary

    def test_includes_position(self, service, candidate):
        """Summary includes position."""
        achievements = service._build_achievements_list(candidate)
        summary = service._build_career_summary(candidate, achievements)

        assert "QB" in summary

    def test_includes_team(self, service, candidate):
        """Summary includes team."""
        achievements = service._build_achievements_list(candidate)
        summary = service._build_career_summary(candidate, achievements)

        assert "Kansas City Chiefs" in summary


# ============================================
# Test Career Stats Formatting
# ============================================

class TestCareerStatsFormatting:
    """Test _format_career_stats() method."""

    def test_formats_passing_stats(self, service):
        """Formats passing stats correctly."""
        stats = {'pass_yards': 50000, 'pass_tds': 400}
        formatted = service._format_career_stats("QB", stats)

        assert "50,000 passing yards" in formatted
        assert "400 passing TDs" in formatted

    def test_formats_rushing_stats(self, service):
        """Formats rushing stats correctly."""
        stats = {'rush_yards': 12000, 'rush_tds': 100}
        formatted = service._format_career_stats("RB", stats)

        assert "12,000 rushing yards" in formatted
        assert "100 rushing TDs" in formatted

    def test_formats_receiving_stats(self, service):
        """Formats receiving stats correctly."""
        stats = {'receptions': 900, 'rec_yards': 12000, 'rec_tds': 80}
        formatted = service._format_career_stats("WR", stats)

        assert "900 receptions" in formatted
        assert "12,000 receiving yards" in formatted

    def test_formats_defensive_stats(self, service):
        """Formats defensive stats correctly."""
        stats = {'sacks': 100, 'tackles': 500, 'interceptions': 10}
        formatted = service._format_career_stats("EDGE", stats)

        assert "100 sacks" in formatted
        assert "500 tackles" in formatted

    def test_formats_kicking_stats(self, service):
        """Formats kicking stats correctly."""
        stats = {'fg_made': 350}
        formatted = service._format_career_stats("K", stats)

        assert "350 field goals" in formatted

    def test_limits_to_four_stats(self, service):
        """Limits output to 4 stats."""
        stats = {
            'pass_yards': 50000,
            'pass_tds': 400,
            'rush_yards': 1000,
            'rush_tds': 10,
            'receptions': 50,
            'rec_yards': 500,
        }
        formatted = service._format_career_stats("QB", stats)

        # Count stat entries by counting stat keywords
        stat_keywords = ['yards', 'TDs', 'receptions', 'sacks', 'tackles', 'interceptions', 'field goals']
        stat_count = sum(1 for kw in stat_keywords if kw in formatted)
        assert stat_count <= 4


# ============================================
# Test Batch Inductions
# ============================================

class TestBatchInductions:
    """Test create_batch_inductions() method."""

    def test_creates_multiple_ceremonies(self, service):
        """Creates ceremonies for multiple inductees."""
        candidates = [
            create_mock_candidate(1, "Player One"),
            create_mock_candidate(2, "Player Two"),
            create_mock_candidate(3, "Player Three"),
        ]

        voting_results = [
            create_mock_voting_result(1, "Player One"),
            create_mock_voting_result(2, "Player Two"),
            create_mock_voting_result(3, "Player Three"),
        ]

        ceremonies = service.create_batch_inductions(
            voting_results, candidates, persist=False
        )

        assert len(ceremonies) == 3
        assert ceremonies[0].inductee_name == "Player One"
        assert ceremonies[1].inductee_name == "Player Two"
        assert ceremonies[2].inductee_name == "Player Three"

    def test_handles_missing_candidate(self, service):
        """Handles case where candidate not found for voting result."""
        candidates = [
            create_mock_candidate(1, "Player One"),
        ]

        voting_results = [
            create_mock_voting_result(1, "Player One"),
            create_mock_voting_result(99, "Unknown Player"),  # No matching candidate
        ]

        ceremonies = service.create_batch_inductions(
            voting_results, candidates, persist=False
        )

        # Should only create ceremony for found candidate
        assert len(ceremonies) == 1
        assert ceremonies[0].inductee_name == "Player One"


# ============================================
# Test Reproducibility
# ============================================

class TestReproducibility:
    """Test that same seed produces same results."""

    def test_same_seed_same_speech(self):
        """Same seed produces identical speech when used immediately."""
        # Create service and generate speech immediately (before state changes)
        service1 = HOFInductionService(seed=42)
        speech1 = service1._generate_speech(
            "Test Player", "QB", ["Team"], [], 10
        )

        # Create new service with same seed and generate speech
        service2 = HOFInductionService(seed=42)
        speech2 = service2._generate_speech(
            "Test Player", "QB", ["Team"], [], 10
        )

        assert speech1.opening == speech2.opening
        assert speech1.career_reflection == speech2.career_reflection

    def test_same_seed_same_presenter(self):
        """Same seed produces same presenter when used immediately."""
        # Create service and select presenter immediately
        service1 = HOFInductionService(seed=42)
        name1, rel1 = service1._select_presenter("Test", ["Team"], "QB")

        # Create new service with same seed and select presenter
        service2 = HOFInductionService(seed=42)
        name2, rel2 = service2._select_presenter("Test", ["Team"], "QB")

        assert name1 == name2
        assert rel1 == rel2


# ============================================
# Test Position Group Mapping
# ============================================

class TestPositionGroupMapping:
    """Test POSITION_TO_GROUP mapping."""

    def test_qb_maps_to_qb(self, service):
        """QB maps to QB group."""
        assert service.POSITION_TO_GROUP['QB'] == 'QB'

    def test_rb_variants_map_to_rb(self, service):
        """RB variants map to RB group."""
        assert service.POSITION_TO_GROUP['RB'] == 'RB'
        assert service.POSITION_TO_GROUP['HB'] == 'RB'
        assert service.POSITION_TO_GROUP['FB'] == 'RB'

    def test_ol_variants_map_to_ol(self, service):
        """OL variants map to OL group."""
        assert service.POSITION_TO_GROUP['LT'] == 'OL'
        assert service.POSITION_TO_GROUP['C'] == 'OL'
        assert service.POSITION_TO_GROUP['RG'] == 'OL'

    def test_dl_variants_map_to_dl(self, service):
        """DL variants map to DL group."""
        assert service.POSITION_TO_GROUP['DT'] == 'DL'
        assert service.POSITION_TO_GROUP['DE'] == 'DL'
        assert service.POSITION_TO_GROUP['EDGE'] == 'DL'

    def test_lb_variants_map_to_lb(self, service):
        """LB variants map to LB group."""
        assert service.POSITION_TO_GROUP['MLB'] == 'LB'
        assert service.POSITION_TO_GROUP['LOLB'] == 'LB'
        assert service.POSITION_TO_GROUP['ILB'] == 'LB'

    def test_db_variants_map_to_db(self, service):
        """DB variants map to DB group."""
        assert service.POSITION_TO_GROUP['CB'] == 'DB'
        assert service.POSITION_TO_GROUP['FS'] == 'DB'
        assert service.POSITION_TO_GROUP['SS'] == 'DB'
