"""Tests for injury models and enums."""

import pytest
from src.game_cycle.models.injury_models import (
    InjuryType,
    InjurySeverity,
    BodyPart,
    Injury,
    InjuryRisk,
    INJURY_TYPE_TO_BODY_PART,
    INJURY_SEVERITY_WEEKS,
    INJURY_TYPE_SEVERITY_RANGE,
    DEFAULT_INJURY_RISKS,
)


class TestInjuryEnums:
    """Test injury enum definitions."""

    def test_injury_type_count(self):
        """Should have 20 injury types."""
        assert len(InjuryType) == 20

    def test_injury_type_values(self):
        """All injury types have string values."""
        for injury_type in InjuryType:
            assert isinstance(injury_type.value, str)
            assert len(injury_type.value) > 0

    def test_injury_severity_values(self):
        """All severities have string values."""
        assert InjurySeverity.MINOR.value == "minor"
        assert InjurySeverity.MODERATE.value == "moderate"
        assert InjurySeverity.SEVERE.value == "severe"
        assert InjurySeverity.SEASON_ENDING.value == "season_ending"

    def test_body_part_count(self):
        """Should have 15 body parts."""
        assert len(BodyPart) == 15

    def test_body_part_values(self):
        """All body parts have string values."""
        for body_part in BodyPart:
            assert isinstance(body_part.value, str)

    def test_injury_type_to_body_part_mapping(self):
        """Every injury type maps to a body part."""
        for injury_type in InjuryType:
            assert injury_type in INJURY_TYPE_TO_BODY_PART
            assert isinstance(INJURY_TYPE_TO_BODY_PART[injury_type], BodyPart)

    def test_severity_weeks_ranges(self):
        """Severity weeks are valid tuples."""
        for severity in InjurySeverity:
            assert severity in INJURY_SEVERITY_WEEKS
            min_weeks, max_weeks = INJURY_SEVERITY_WEEKS[severity]
            assert min_weeks <= max_weeks
            assert min_weeks >= 1

    def test_injury_type_severity_ranges(self):
        """Every injury type has valid severity range."""
        for injury_type in InjuryType:
            assert injury_type in INJURY_TYPE_SEVERITY_RANGE
            severities = INJURY_TYPE_SEVERITY_RANGE[injury_type]
            assert len(severities) >= 1
            for sev in severities:
                assert isinstance(sev, InjurySeverity)

    def test_acl_tear_always_season_ending(self):
        """ACL tear should always be season-ending."""
        severities = INJURY_TYPE_SEVERITY_RANGE[InjuryType.ACL_TEAR]
        assert severities == [InjurySeverity.SEASON_ENDING]

    def test_achilles_tear_always_season_ending(self):
        """Achilles tear should always be season-ending."""
        severities = INJURY_TYPE_SEVERITY_RANGE[InjuryType.ACHILLES_TEAR]
        assert severities == [InjurySeverity.SEASON_ENDING]


class TestInjuryDataclass:
    """Test Injury dataclass."""

    def test_create_injury(self):
        """Can create an injury instance."""
        injury = Injury(
            player_id=100,
            player_name="Test Player",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=2,
            week_occurred=5,
            season=2025,
            occurred_during='game',
        )
        assert injury.player_id == 100
        assert injury.injury_type == InjuryType.ANKLE_SPRAIN
        assert injury.is_active is True
        assert injury.on_ir is False

    def test_injury_display_name(self):
        """Display name is formatted correctly."""
        injury = Injury(
            player_id=100,
            player_name="Test",
            team_id=1,
            injury_type=InjuryType.HAMSTRING_STRAIN,
            body_part=BodyPart.THIGH,
            severity=InjurySeverity.MODERATE,
            weeks_out=3,
            week_occurred=1,
            season=2025,
            occurred_during='practice',
        )
        assert injury.display_name == "Hamstring Strain"

    def test_severity_display(self):
        """Severity display is formatted correctly."""
        injury = Injury(
            player_id=100,
            player_name="Test",
            team_id=1,
            injury_type=InjuryType.ACL_TEAR,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.SEASON_ENDING,
            weeks_out=12,
            week_occurred=3,
            season=2025,
            occurred_during='game',
        )
        assert injury.severity_display == "Season Ending"

    def test_estimated_return_week(self):
        """Return week calculation."""
        injury = Injury(
            player_id=100,
            player_name="Test",
            team_id=1,
            injury_type=InjuryType.KNEE_SPRAIN,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.MODERATE,
            weeks_out=4,
            week_occurred=10,
            season=2025,
            occurred_during='game',
        )
        assert injury.estimated_return_week == 14

    def test_to_db_dict(self):
        """Can convert to database dict."""
        injury = Injury(
            player_id=100,
            player_name="Test",
            team_id=1,
            injury_type=InjuryType.CONCUSSION,
            body_part=BodyPart.HEAD,
            severity=InjurySeverity.MINOR,
            weeks_out=1,
            week_occurred=3,
            season=2025,
            occurred_during='game',
            game_id='game_123',
        )
        db_dict = injury.to_db_dict()
        assert db_dict['injury_type'] == 'concussion'
        assert db_dict['body_part'] == 'head'
        assert db_dict['severity'] == 'minor'
        assert db_dict['game_id'] == 'game_123'
        assert db_dict['is_active'] == 1

    def test_from_db_row(self):
        """Can create from database row dict."""
        row = {
            'injury_id': 1,
            'player_id': 100,
            'player_name': 'John Doe',
            'team_id': 22,
            'injury_type': 'ankle_sprain',
            'body_part': 'ankle',
            'severity': 'moderate',
            'estimated_weeks_out': 3,
            'week_occurred': 5,
            'season': 2025,
            'occurred_during': 'game',
            'is_active': 1,
        }
        injury = Injury.from_db_row(row)
        assert injury.injury_id == 1
        assert injury.player_id == 100
        assert injury.injury_type == InjuryType.ANKLE_SPRAIN
        assert injury.body_part == BodyPart.ANKLE
        assert injury.severity == InjurySeverity.MODERATE

    def test_str_representation(self):
        """String representation is informative."""
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.HAMSTRING_STRAIN,
            body_part=BodyPart.THIGH,
            severity=InjurySeverity.MODERATE,
            weeks_out=3,
            week_occurred=5,
            season=2025,
            occurred_during='practice',
        )
        str_repr = str(injury)
        assert "John Doe" in str_repr
        assert "Hamstring Strain" in str_repr
        assert "3 weeks" in str_repr


class TestInjuryRisk:
    """Test InjuryRisk dataclass."""

    def test_create_injury_risk(self):
        """Can create injury risk profile."""
        risk = InjuryRisk(
            position='RB',
            base_injury_chance=0.08,
            high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE],
            common_injuries=[InjuryType.HAMSTRING_STRAIN],
        )
        assert risk.position == 'RB'
        assert risk.base_injury_chance == 0.08
        assert len(risk.high_risk_body_parts) == 2

    def test_injury_probability_high_durability(self):
        """High durability reduces injury probability."""
        risk = InjuryRisk(
            position='RB',
            base_injury_chance=0.10,  # 10% base
        )
        prob = risk.get_injury_probability(durability=90)
        # High durability (90) should reduce chance significantly
        assert prob < 0.10
        assert prob > 0

    def test_injury_probability_low_durability(self):
        """Low durability increases injury probability."""
        risk = InjuryRisk(
            position='RB',
            base_injury_chance=0.10,  # 10% base
        )
        prob = risk.get_injury_probability(durability=30)
        # Low durability (30) should increase chance
        assert prob > 0.10

    def test_injury_probability_average_durability(self):
        """Average durability (50) returns base probability."""
        risk = InjuryRisk(
            position='RB',
            base_injury_chance=0.10,
        )
        prob = risk.get_injury_probability(durability=50)
        # At 50 durability, modifier should be 1.0
        assert prob == pytest.approx(0.10, abs=0.001)

    def test_default_injury_risks_exist(self):
        """Default risk profiles exist for key positions."""
        assert 'RB' in DEFAULT_INJURY_RISKS
        assert 'WR' in DEFAULT_INJURY_RISKS
        assert 'QB' in DEFAULT_INJURY_RISKS

    def test_rb_highest_base_risk(self):
        """RBs should have highest base injury chance."""
        rb_risk = DEFAULT_INJURY_RISKS['RB']
        wr_risk = DEFAULT_INJURY_RISKS['WR']
        qb_risk = DEFAULT_INJURY_RISKS['QB']

        assert rb_risk.base_injury_chance > wr_risk.base_injury_chance
        assert rb_risk.base_injury_chance > qb_risk.base_injury_chance
