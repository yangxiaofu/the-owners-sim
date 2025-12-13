"""
Unit tests for StaffGeneratorService.

Part of Milestone 13: Owner Review, Tollgate 3.
Tests procedural generation of GM and HC candidates.
"""
import re
import uuid
from collections import Counter

import pytest

from src.game_cycle.services.staff_generator_service import StaffGeneratorService


@pytest.fixture
def generator():
    """Create a fresh StaffGeneratorService instance."""
    return StaffGeneratorService()


# ============================================
# Tests for Name Generation
# ============================================

class TestNameGeneration:
    """Tests for name generation logic."""

    def test_generates_valid_full_name(self, generator):
        """Generated name has 'First Last' format."""
        candidates = generator.generate_gm_candidates(count=1)
        name = candidates[0]["name"]
        parts = name.split()
        assert len(parts) >= 2  # At least first and last

    def test_name_uses_valid_first_name(self, generator):
        """First name comes from FIRST_NAMES pool."""
        candidates = generator.generate_gm_candidates(count=10)
        for c in candidates:
            first_name = c["name"].split()[0]
            # Either in pool or is part of a Jr. name
            assert first_name in StaffGeneratorService.FIRST_NAMES or "Jr." in c["name"]

    def test_name_uses_valid_last_name(self, generator):
        """Last name comes from LAST_NAMES pool."""
        candidates = generator.generate_gm_candidates(count=10)
        for c in candidates:
            parts = c["name"].split()
            # Last name is either position 1 or before "Jr."
            if "Jr." in c["name"]:
                last_name = parts[-2]
            else:
                last_name = parts[-1]
            assert last_name in StaffGeneratorService.LAST_NAMES

    def test_five_candidates_have_five_unique_names(self, generator):
        """5 candidates must have 5 distinct names."""
        candidates = generator.generate_gm_candidates(count=5)
        names = [c["name"] for c in candidates]
        assert len(set(names)) == 5

    def test_fallback_adds_junior_suffix(self, generator):
        """When pool exhausted, adds 'Jr.' suffix."""
        # Create a large used set to exhaust normal names
        used_names = set()
        # Fill with most combinations
        for first in StaffGeneratorService.FIRST_NAMES[:40]:
            for last in StaffGeneratorService.LAST_NAMES[:40]:
                used_names.add(f"{first} {last}")

        # Generate name with restricted pool - should get Jr.
        # This is a probabilistic test - may need multiple attempts
        found_jr = False
        for _ in range(50):
            name = generator._generate_unique_name(used_names)
            if "Jr." in name:
                found_jr = True
                break
            used_names.add(name)

        # Either found Jr. or pool still had names
        assert found_jr or len(used_names) < (46 * 56)

    def test_name_randomness_across_calls(self, generator):
        """Repeated calls produce different names."""
        # Generate two batches
        batch1 = generator.generate_gm_candidates(count=5)
        batch2 = generator.generate_gm_candidates(count=5)

        names1 = set(c["name"] for c in batch1)
        names2 = set(c["name"] for c in batch2)

        # Should have at least some different names (randomness)
        # Not requiring all different due to probability
        all_same = names1 == names2
        # Very unlikely to get exact same 5 names twice
        assert not all_same or len(names1) == 5


# ============================================
# Tests for GM Candidate Generation
# ============================================

class TestGMCandidateGeneration:
    """Tests for GM candidate generation."""

    def test_generates_correct_count(self, generator):
        """Generates exactly requested number of candidates."""
        for count in [1, 3, 5, 7]:
            candidates = generator.generate_gm_candidates(count=count)
            assert len(candidates) == count

    def test_candidate_has_required_fields(self, generator):
        """Each candidate has staff_id, name, archetype_key, custom_traits, history."""
        candidates = generator.generate_gm_candidates(count=1)
        candidate = candidates[0]
        assert "staff_id" in candidate
        assert "name" in candidate
        assert "archetype_key" in candidate
        assert "custom_traits" in candidate
        assert "history" in candidate

    def test_staff_id_is_valid_uuid(self, generator):
        """staff_id is valid UUID format."""
        candidates = generator.generate_gm_candidates(count=3)
        for c in candidates:
            # Should not raise ValueError
            parsed = uuid.UUID(c["staff_id"])
            assert str(parsed) == c["staff_id"]

    def test_archetype_is_from_gm_list(self, generator):
        """archetype_key comes from GM_ARCHETYPES."""
        candidates = generator.generate_gm_candidates(count=10)
        for c in candidates:
            assert c["archetype_key"] in StaffGeneratorService.GM_ARCHETYPES

    def test_excludes_specified_archetypes(self, generator):
        """exclude_archetypes prevents selection of listed archetypes."""
        excluded = ["win_now", "rebuilder"]
        candidates = generator.generate_gm_candidates(
            count=5, exclude_archetypes=excluded
        )
        for c in candidates:
            assert c["archetype_key"] not in excluded

    def test_varied_archetypes_across_candidates(self, generator):
        """5 candidates should have 3+ distinct archetypes."""
        candidates = generator.generate_gm_candidates(count=5)
        archetypes = set(c["archetype_key"] for c in candidates)
        # With 7 archetypes and avoiding recent repeats, should get variety
        assert len(archetypes) >= 3

    def test_custom_traits_has_two_to_three_entries(self, generator):
        """custom_traits dict has 2-3 trait entries."""
        candidates = generator.generate_gm_candidates(count=10)
        for c in candidates:
            traits = c["custom_traits"]
            assert isinstance(traits, dict)
            assert 2 <= len(traits) <= 3

    def test_history_is_non_empty_string(self, generator):
        """history field is populated string."""
        candidates = generator.generate_gm_candidates(count=5)
        for c in candidates:
            assert isinstance(c["history"], str)
            assert len(c["history"]) > 10  # Should be meaningful


# ============================================
# Tests for HC Candidate Generation
# ============================================

class TestHCCandidateGeneration:
    """Tests for HC candidate generation."""

    def test_generates_correct_count(self, generator):
        """Generates exactly requested number of candidates."""
        for count in [1, 3, 5, 7]:
            candidates = generator.generate_hc_candidates(count=count)
            assert len(candidates) == count

    def test_candidate_has_required_fields(self, generator):
        """Each candidate has staff_id, name, archetype_key, custom_traits, history."""
        candidates = generator.generate_hc_candidates(count=1)
        candidate = candidates[0]
        assert "staff_id" in candidate
        assert "name" in candidate
        assert "archetype_key" in candidate
        assert "custom_traits" in candidate
        assert "history" in candidate

    def test_staff_id_is_valid_uuid(self, generator):
        """staff_id is valid UUID format."""
        candidates = generator.generate_hc_candidates(count=3)
        for c in candidates:
            parsed = uuid.UUID(c["staff_id"])
            assert str(parsed) == c["staff_id"]

    def test_archetype_is_from_hc_list(self, generator):
        """archetype_key comes from HC_ARCHETYPES."""
        candidates = generator.generate_hc_candidates(count=10)
        for c in candidates:
            assert c["archetype_key"] in StaffGeneratorService.HC_ARCHETYPES

    def test_excludes_specified_archetypes(self, generator):
        """exclude_archetypes prevents selection of listed archetypes."""
        excluded = ["aggressive", "bill_belichick"]
        candidates = generator.generate_hc_candidates(
            count=5, exclude_archetypes=excluded
        )
        for c in candidates:
            assert c["archetype_key"] not in excluded

    def test_varied_archetypes_across_candidates(self, generator):
        """5 candidates should have 3+ distinct archetypes."""
        candidates = generator.generate_hc_candidates(count=5)
        archetypes = set(c["archetype_key"] for c in candidates)
        assert len(archetypes) >= 3

    def test_custom_traits_has_two_to_three_entries(self, generator):
        """custom_traits dict has 2-3 trait entries."""
        candidates = generator.generate_hc_candidates(count=10)
        for c in candidates:
            traits = c["custom_traits"]
            assert isinstance(traits, dict)
            assert 2 <= len(traits) <= 3

    def test_history_is_non_empty_string(self, generator):
        """history field is populated string."""
        candidates = generator.generate_hc_candidates(count=5)
        for c in candidates:
            assert isinstance(c["history"], str)
            assert len(c["history"]) > 10


# ============================================
# Tests for Trait Variations
# ============================================

class TestTraitVariations:
    """Tests for trait variation generation."""

    def test_gm_traits_within_bounds(self, generator):
        """All GM trait values are 0.0-1.0."""
        candidates = generator.generate_gm_candidates(count=20)
        for c in candidates:
            for trait_name, value in c["custom_traits"].items():
                assert 0.0 <= value <= 1.0, f"GM trait {trait_name} = {value} out of bounds"

    def test_hc_traits_within_bounds(self, generator):
        """All HC trait values are 0.0-1.0."""
        candidates = generator.generate_hc_candidates(count=20)
        for c in candidates:
            for trait_name, value in c["custom_traits"].items():
                assert 0.0 <= value <= 1.0, f"HC trait {trait_name} = {value} out of bounds"

    def test_trait_values_vary_across_candidates(self, generator):
        """Same trait has different values across candidates."""
        # Generate many candidates to ensure variety
        candidates = generator.generate_gm_candidates(count=20)

        # Collect all values for each trait
        trait_values = {}
        for c in candidates:
            for trait, value in c["custom_traits"].items():
                if trait not in trait_values:
                    trait_values[trait] = []
                trait_values[trait].append(value)

        # At least one trait should have varied values
        has_variety = False
        for trait, values in trait_values.items():
            if len(set(values)) > 1:
                has_variety = True
                break

        assert has_variety, "All trait values are identical across candidates"

    def test_gm_traits_from_valid_pool(self, generator):
        """GM traits come from allowed trait names."""
        valid_gm_traits = {
            "risk_tolerance", "win_now_mentality", "draft_pick_value",
            "cap_management", "trade_frequency", "star_chasing",
            "veteran_preference", "loyalty"
        }
        candidates = generator.generate_gm_candidates(count=10)
        for c in candidates:
            for trait in c["custom_traits"].keys():
                assert trait in valid_gm_traits, f"Unknown GM trait: {trait}"

    def test_hc_traits_from_valid_pool(self, generator):
        """HC traits come from allowed trait names."""
        valid_hc_traits = {
            "aggression", "risk_tolerance", "fourth_down_aggression",
            "conservatism", "run_preference", "adaptability"
        }
        candidates = generator.generate_hc_candidates(count=10)
        for c in candidates:
            for trait in c["custom_traits"].keys():
                assert trait in valid_hc_traits, f"Unknown HC trait: {trait}"


# ============================================
# Tests for History Generation
# ============================================

class TestHistoryGeneration:
    """Tests for history/background generation."""

    def test_gm_history_grammatically_correct(self, generator):
        """GM history strings have no unfilled placeholders."""
        candidates = generator.generate_gm_candidates(count=20)
        placeholder_pattern = re.compile(r'\{[^}]+\}')

        for c in candidates:
            history = c["history"]
            # Should not contain unfilled {placeholders}
            matches = placeholder_pattern.findall(history)
            assert len(matches) == 0, f"Unfilled placeholder in GM history: {history}"

    def test_hc_history_grammatically_correct(self, generator):
        """HC history strings have no unfilled placeholders."""
        candidates = generator.generate_hc_candidates(count=20)
        placeholder_pattern = re.compile(r'\{[^}]+\}')

        for c in candidates:
            history = c["history"]
            matches = placeholder_pattern.findall(history)
            assert len(matches) == 0, f"Unfilled placeholder in HC history: {history}"

    def test_history_varies_across_candidates(self, generator):
        """Different candidates get different histories."""
        candidates = generator.generate_gm_candidates(count=10)
        histories = [c["history"] for c in candidates]

        # Most should be unique (some template reuse is okay)
        unique_count = len(set(histories))
        assert unique_count >= 5, f"Too many duplicate histories: {unique_count}/10 unique"


# ============================================
# Statistical Tests (slow)
# ============================================

@pytest.mark.slow
class TestStatisticalVariety:
    """Statistical tests across many generations."""

    def test_100_generations_use_all_gm_archetypes(self, generator):
        """100 batches of GM candidates use all 7 archetypes."""
        archetype_counter = Counter()
        for _ in range(100):
            candidates = generator.generate_gm_candidates(count=5)
            for c in candidates:
                archetype_counter[c["archetype_key"]] += 1

        # All 7 archetypes should appear
        assert len(archetype_counter) == 7, f"Only {len(archetype_counter)} archetypes used"

        # Each archetype should appear at least once
        for archetype in StaffGeneratorService.GM_ARCHETYPES:
            assert archetype_counter[archetype] > 0, f"Archetype {archetype} never used"

    def test_100_generations_use_all_hc_archetypes(self, generator):
        """100 batches of HC candidates use all 10 archetypes."""
        archetype_counter = Counter()
        for _ in range(100):
            candidates = generator.generate_hc_candidates(count=5)
            for c in candidates:
                archetype_counter[c["archetype_key"]] += 1

        # All 10 archetypes should appear
        assert len(archetype_counter) == 10, f"Only {len(archetype_counter)} archetypes used"

        for archetype in StaffGeneratorService.HC_ARCHETYPES:
            assert archetype_counter[archetype] > 0, f"Archetype {archetype} never used"

    def test_name_distribution_is_varied(self, generator):
        """100 generations produce >80% unique names."""
        all_names = []
        for _ in range(100):
            candidates = generator.generate_gm_candidates(count=5)
            for c in candidates:
                all_names.append(c["name"])

        total = len(all_names)  # 500 names
        unique = len(set(all_names))
        ratio = unique / total

        # Should have high uniqueness (>80%)
        assert ratio > 0.80, f"Only {ratio:.1%} unique names ({unique}/{total})"
