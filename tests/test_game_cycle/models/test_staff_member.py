"""Unit tests for StaffMember and StaffCandidate models."""
import pytest
import uuid
from src.game_cycle.models.staff_member import (
    StaffType, StaffMember, StaffCandidate,
    create_default_gm, create_default_hc
)


class TestStaffType:
    """Tests for StaffType enum."""

    def test_staff_type_values(self):
        """Verify StaffType has GM and HEAD_COACH values."""
        assert StaffType.GM.value == "GM"
        assert StaffType.HEAD_COACH.value == "HC"

    def test_staff_type_from_string(self):
        """Verify StaffType can be created from string value."""
        assert StaffType("GM") == StaffType.GM
        assert StaffType("HC") == StaffType.HEAD_COACH


class TestStaffMemberSerialization:
    """Tests for StaffMember to_dict and from_dict."""

    def test_to_dict_converts_enum(self):
        """Verify to_dict converts enum to string value."""
        staff = StaffMember(
            staff_id="test-id",
            staff_type=StaffType.GM,
            name="John Smith",
            archetype_key="win_now",
        )
        result = staff.to_dict()
        assert result["staff_type"] == "GM"  # String, not enum
        assert result["name"] == "John Smith"
        assert result["archetype_key"] == "win_now"

    def test_from_dict_with_string_type(self):
        """Verify from_dict handles staff_type as string."""
        data = {
            "staff_id": "test-id",
            "staff_type": "HC",
            "name": "Bill Coach",
            "archetype_key": "balanced",
        }
        staff = StaffMember.from_dict(data)
        assert staff.staff_type == StaffType.HEAD_COACH
        assert staff.name == "Bill Coach"

    def test_from_dict_with_enum_type(self):
        """Verify from_dict handles staff_type as enum (edge case)."""
        data = {
            "staff_id": "test-id",
            "staff_type": StaffType.GM,  # Already enum
            "name": "Mike GM",
        }
        staff = StaffMember.from_dict(data)
        assert staff.staff_type == StaffType.GM

    def test_roundtrip_serialization(self):
        """Verify to_dict -> from_dict preserves data."""
        original = StaffMember(
            staff_id="unique-id",
            staff_type=StaffType.HEAD_COACH,
            name="Sean McVay Clone",
            archetype_key="sean_mcvay",
            custom_traits={"aggression": 0.8, "risk_tolerance": 0.7},
            history="Former offensive coordinator.",
            hire_season=2023,
        )
        restored = StaffMember.from_dict(original.to_dict())
        assert restored.staff_id == original.staff_id
        assert restored.staff_type == original.staff_type
        assert restored.name == original.name
        assert restored.custom_traits == original.custom_traits
        assert restored.hire_season == original.hire_season

    def test_uuid_auto_generation(self):
        """Verify staff_id auto-generates UUID if not provided."""
        data = {"staff_type": "GM", "name": "Auto ID Staff"}
        staff = StaffMember.from_dict(data)
        assert staff.staff_id is not None
        # Verify it's a valid UUID format
        uuid.UUID(staff.staff_id)  # Raises if invalid


class TestStaffMemberHelpers:
    """Tests for StaffMember helper methods."""

    def test_get_tenure_first_season(self):
        """Verify tenure is 1 for current hire season."""
        staff = StaffMember(hire_season=2025)
        assert staff.get_tenure(2025) == 1

    def test_get_tenure_multiple_seasons(self):
        """Verify tenure calculation across seasons."""
        staff = StaffMember(hire_season=2020)
        assert staff.get_tenure(2025) == 6  # 2020-2025 inclusive

    def test_get_archetype_display_name(self):
        """Verify 'win_now' -> 'Win Now' formatting."""
        staff = StaffMember(archetype_key="win_now")
        assert staff.get_archetype_display_name() == "Win Now"

    def test_get_archetype_display_name_single_word(self):
        """Verify 'balanced' -> 'Balanced' formatting."""
        staff = StaffMember(archetype_key="balanced")
        assert staff.get_archetype_display_name() == "Balanced"

    def test_get_effective_trait_with_override(self):
        """Verify custom trait overrides base value."""
        staff = StaffMember(custom_traits={"aggression": 0.9})
        result = staff.get_effective_trait("aggression", base_value=0.5)
        assert result == 0.9  # Custom value used

    def test_get_effective_trait_without_override(self):
        """Verify base value used when no custom trait."""
        staff = StaffMember(custom_traits={})
        result = staff.get_effective_trait("aggression", base_value=0.5)
        assert result == 0.5  # Base value used

    def test_str_representation(self):
        """Verify __str__ produces readable output."""
        staff = StaffMember(
            staff_type=StaffType.GM,
            name="John Smith",
            archetype_key="win_now",
            hire_season=2023,
        )
        result = str(staff)
        assert "GM" in result
        assert "John Smith" in result
        assert "Win Now" in result
        assert "2023" in result


class TestStaffCandidate:
    """Tests for StaffCandidate subclass."""

    def test_candidate_inherits_member_fields(self):
        """Verify StaffCandidate inherits StaffMember fields."""
        candidate = StaffCandidate(
            staff_type=StaffType.GM,
            name="Candidate Name",
            archetype_key="rebuilder",
        )
        assert candidate.staff_type == StaffType.GM
        assert candidate.name == "Candidate Name"
        assert candidate.archetype_key == "rebuilder"

    def test_candidate_has_selection_fields(self):
        """Verify StaffCandidate has candidate-specific fields."""
        candidate = StaffCandidate(is_selected=True, candidate_rank=2)
        assert candidate.is_selected is True
        assert candidate.candidate_rank == 2

    def test_candidate_to_dict_includes_extras(self):
        """Verify to_dict includes candidate-specific fields."""
        candidate = StaffCandidate(
            name="Test Candidate",
            is_selected=True,
            candidate_rank=1,
        )
        result = candidate.to_dict()
        assert result["is_selected"] is True
        assert result["candidate_rank"] == 1
        assert result["name"] == "Test Candidate"

    def test_candidate_from_dict(self):
        """Verify from_dict creates valid StaffCandidate."""
        data = {
            "staff_type": "HC",
            "name": "Coach Candidate",
            "is_selected": False,
            "candidate_rank": 3,
        }
        candidate = StaffCandidate.from_dict(data)
        assert candidate.staff_type == StaffType.HEAD_COACH
        assert candidate.is_selected is False
        assert candidate.candidate_rank == 3


class TestFactoryFunctions:
    """Tests for create_default_gm and create_default_hc."""

    def test_create_default_gm(self):
        """Verify create_default_gm returns GM type."""
        gm = create_default_gm("test-dynasty", 2025)
        assert gm.staff_type == StaffType.GM
        assert gm.archetype_key == "balanced"
        assert gm.hire_season == 2025
        assert gm.name == "Default GM"
        assert gm.staff_id is not None

    def test_create_default_hc(self):
        """Verify create_default_hc returns HC type."""
        hc = create_default_hc("test-dynasty", 2025)
        assert hc.staff_type == StaffType.HEAD_COACH
        assert hc.archetype_key == "balanced"
        assert hc.hire_season == 2025
        assert hc.name == "Default HC"

    def test_factory_generates_unique_ids(self):
        """Verify each call generates unique staff_id."""
        gm1 = create_default_gm("test", 2025)
        gm2 = create_default_gm("test", 2025)
        assert gm1.staff_id != gm2.staff_id
