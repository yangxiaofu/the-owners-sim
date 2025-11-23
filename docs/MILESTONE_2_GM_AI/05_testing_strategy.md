# Testing Strategy: GM AI Integration

**Purpose**: Comprehensive testing and validation approach for unified GM decision-making system

---

## Testing Pyramid

```
                   ┌─────────────────┐
                   │  E2E Validation │  (4 tests)
                   │   32-team sims  │
                   └─────────────────┘
                  ┌───────────────────┐
                  │ Integration Tests │  (20 tests)
                  │  Manager + GM     │
                  └───────────────────┘
               ┌──────────────────────────┐
               │      Unit Tests          │  (34 tests)
               │  PersonalityModifiers    │
               └──────────────────────────┘
```

**Total Test Count**: 58 tests
- **34 Unit Tests** (PersonalityModifiers in isolation)
- **20 Integration Tests** (Managers with GM integration)
- **4 End-to-End Tests** (Full offseason simulation)

**Test Coverage Goal**: ≥90% for all modified files

---

## Unit Tests (Component Level)

### PersonalityModifiers Tests

**Location**: `tests/transactions/test_personality_modifiers.py`

**Total**: 34 unit tests (18 FA + 12 draft + 4 cuts)

#### Free Agency Modifiers (18 tests)

**Test Class**: `TestFreeAgencyModifiers`

```python
class TestFreeAgencyModifiers:
    """Unit tests for free agency personality modifiers."""

    # ===== Win-Now Premium Tests (5 tests) =====

    def test_win_now_premium_for_proven_starter(self):
        """Win-Now GM should overpay for 80+ OVR players."""
        gm = GMArchetype(win_now_mentality=0.9)
        player = Player(overall=85, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # win_now=0.9 → 1.32x multiplier
        assert result['aav'] > 15_000_000
        assert result['aav'] <= 15_000_000 * 1.4  # Max multiplier

    def test_win_now_no_premium_for_rebuilder(self):
        """Rebuilder GM should not overpay."""
        gm = GMArchetype(win_now_mentality=0.2)
        player = Player(overall=85, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # win_now=0.2 → no modifier (below 0.5 threshold)
        assert result['aav'] == 15_000_000

    def test_win_now_no_premium_for_low_ovr(self):
        """Win-Now premium should not apply to <80 OVR players."""
        gm = GMArchetype(win_now_mentality=0.9)
        player = Player(overall=75, age=27)
        market_value = {'aav': 8_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # No win-now modifier for 75 OVR (but cap management might apply)
        # This test isolates win-now logic only

    def test_win_now_edge_case_threshold(self):
        """Test win_now_mentality=0.5 (threshold)."""
        gm = GMArchetype(win_now_mentality=0.5)
        player = Player(overall=85, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # win_now=0.5 → 1.0x multiplier (no premium)
        assert result['aav'] == 15_000_000

    def test_win_now_maximum_multiplier(self):
        """Test win_now_mentality=1.0 (max)."""
        gm = GMArchetype(win_now_mentality=1.0)
        player = Player(overall=85, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # win_now=1.0 → 1.4x multiplier
        expected_aav = 15_000_000 * 1.4
        assert abs(result['aav'] - expected_aav) < 100_000  # Allow rounding

    # ===== Cap Management Tests (3 tests) =====

    def test_cap_management_discount_expensive_player(self):
        """Cap-Conscious GM should discount non-elite players."""
        gm = GMArchetype(cap_management=0.9)
        player = Player(overall=82, age=27)  # Non-elite
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # cap_management=0.9 → 0.64x multiplier
        assert result['aav'] < 15_000_000

    def test_cap_management_no_discount_for_elite(self):
        """Cap modifier should not apply to 90+ OVR players."""
        gm = GMArchetype(cap_management=0.9)
        player = Player(overall=92, age=27)  # Elite
        market_value = {'aav': 22_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # No cap management discount for elite players

    def test_cap_management_no_discount_for_flexible_gm(self):
        """Cap-flexible GM should not discount."""
        gm = GMArchetype(cap_management=0.0)
        player = Player(overall=82, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # cap_management=0.0 → 1.0x multiplier (no discount)

    # ===== Veteran Preference Tests (4 tests) =====

    def test_veteran_preference_boost_for_veteran(self):
        """Veteran-preferring GM should boost 30+ age players."""
        gm = GMArchetype(veteran_preference=0.9)
        player = Player(overall=85, age=32)
        market_value = {'aav': 12_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # veteran_preference=0.9 → 1.16x multiplier
        assert result['aav'] > 12_000_000

    def test_veteran_preference_discount_for_youth_focused(self):
        """Youth-focused GM should discount 30+ age players."""
        gm = GMArchetype(veteran_preference=0.2)
        player = Player(overall=85, age=32)
        market_value = {'aav': 12_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # veteran_preference=0.2 → 0.88x multiplier
        assert result['aav'] < 12_000_000

    def test_veteran_preference_no_modifier_for_young_player(self):
        """Veteran preference should not apply to <30 age players."""
        gm = GMArchetype(veteran_preference=0.9)
        player = Player(overall=85, age=25)
        market_value = {'aav': 12_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # No veteran modifier for 25-year-old

    def test_veteran_preference_threshold(self):
        """Test veteran_preference=0.5 (threshold)."""
        gm = GMArchetype(veteran_preference=0.5)
        player = Player(overall=85, age=32)
        market_value = {'aav': 12_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # veteran_preference=0.5 → 1.0x multiplier (no change)
        assert result['aav'] == 12_000_000

    # ===== Star Chasing Tests (3 tests) =====

    def test_star_chasing_premium_for_elite(self):
        """Star-chasing GM should overpay for 90+ OVR players."""
        gm = GMArchetype(star_chasing=1.0)
        player = Player(overall=92, age=27)
        market_value = {'aav': 22_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # star_chasing=1.0 → 1.5x multiplier
        expected_aav = 22_000_000 * 1.5
        assert abs(result['aav'] - expected_aav) < 100_000

    def test_star_chasing_no_premium_for_non_elite(self):
        """Star-chasing modifier should not apply to <90 OVR players."""
        gm = GMArchetype(star_chasing=1.0)
        player = Player(overall=85, age=27)
        market_value = {'aav': 15_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # No star-chasing modifier for 85 OVR

    def test_star_chasing_zero_trait(self):
        """Non-star-chasing GM should not overpay."""
        gm = GMArchetype(star_chasing=0.0)
        player = Player(overall=92, age=27)
        market_value = {'aav': 22_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # star_chasing=0.0 → 1.0x multiplier

    # ===== Risk Tolerance Tests (3 tests) =====

    def test_risk_tolerance_discount_for_injury_prone(self):
        """Risk-averse GM should discount injury-prone players."""
        gm = GMArchetype(risk_tolerance=0.2)
        player = Player(overall=86, age=27, injury_prone=True)
        market_value = {'aav': 14_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # risk_tolerance=0.2 → 0.82x multiplier
        assert result['aav'] < 14_000_000

    def test_risk_tolerance_no_discount_for_risk_tolerant(self):
        """Risk-tolerant GM should not discount injury-prone players."""
        gm = GMArchetype(risk_tolerance=0.8)
        player = Player(overall=86, age=27, injury_prone=True)
        market_value = {'aav': 14_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # risk_tolerance=0.8 → 1.0x (no discount for high risk tolerance)

    def test_risk_tolerance_no_modifier_for_healthy_player(self):
        """Risk modifier should not apply to non-injury-prone players."""
        gm = GMArchetype(risk_tolerance=0.2)
        player = Player(overall=86, age=27, injury_prone=False)
        market_value = {'aav': 14_000_000}

        result = PersonalityModifiers.apply_free_agency_modifier(
            player, market_value, gm, team_context
        )

        # No risk modifier for healthy players
```

#### Draft Modifiers (12 tests)

**Test Class**: `TestDraftModifiers`

```python
class TestDraftModifiers:
    """Unit tests for draft personality modifiers."""

    # ===== Risk Tolerance Tests (4 tests) =====

    def test_risk_tolerance_boost_high_ceiling_prospect(self):
        """Risk-tolerant GM should value high-ceiling prospects."""
        gm = GMArchetype(risk_tolerance=0.9)
        prospect = Player(overall=70, potential=90)  # upside=20
        base_value = 70

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=15, gm=gm, team_context=team_context
        )

        # risk_tolerance=0.9, upside=20 → 1.16x multiplier
        assert result > base_value

    def test_risk_tolerance_discount_for_conservative(self):
        """Risk-averse GM should discount high-ceiling prospects."""
        gm = GMArchetype(risk_tolerance=0.1)
        prospect = Player(overall=70, potential=90)  # upside=20
        base_value = 70

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=15, gm=gm, team_context=team_context
        )

        # risk_tolerance=0.1, upside=20 → 0.92x multiplier
        assert result < base_value

    def test_risk_tolerance_no_modifier_for_safe_pick(self):
        """Risk modifier should not apply to high-floor prospects."""
        gm = GMArchetype(risk_tolerance=0.9)
        prospect = Player(overall=78, potential=82)  # upside=4
        base_value = 78

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=15, gm=gm, team_context=team_context
        )

        # upside=4 (not >10), no risk modifier

    def test_risk_tolerance_threshold(self):
        """Test risk_tolerance=0.5 (threshold)."""
        gm = GMArchetype(risk_tolerance=0.5)
        prospect = Player(overall=70, potential=90)  # upside=20
        base_value = 70

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=15, gm=gm, team_context=team_context
        )

        # risk_tolerance=0.5 → 1.0x multiplier (no change)
        assert result == base_value

    # ===== Win-Now Mentality Tests (3 tests) =====

    def test_win_now_boost_polished_prospect(self):
        """Win-Now GM should value polished prospects."""
        gm = GMArchetype(win_now_mentality=0.9)
        prospect = Player(overall=76, age=24)  # Polished
        base_value = 76

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=45, gm=gm, team_context=team_context
        )

        # win_now=0.9, age=24 → 1.27x multiplier
        assert result > base_value

    def test_win_now_no_boost_for_young_prospect(self):
        """Win-Now modifier should not apply to young prospects."""
        gm = GMArchetype(win_now_mentality=0.9)
        prospect = Player(overall=76, age=20)  # Raw
        base_value = 76

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=45, gm=gm, team_context=team_context
        )

        # age=20 (not >=23), no win-now modifier

    def test_win_now_rebuilder_minimal_boost(self):
        """Rebuilder GM should have minimal polished prospect boost."""
        gm = GMArchetype(win_now_mentality=0.2)
        prospect = Player(overall=76, age=24)
        base_value = 76

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=45, gm=gm, team_context=team_context
        )

        # win_now=0.2, age=24 → 1.06x multiplier (small boost)
        assert result > base_value
        assert result < base_value * 1.15  # Less than mid-range GM

    # ===== Premium Position Focus Tests (2 tests) =====

    def test_premium_position_focus_qb(self):
        """Premium position focus GM should boost QB value."""
        gm = GMArchetype(premium_position_focus=1.0)
        prospect = Player(overall=80, position='QB')
        base_value = 80

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=5, gm=gm, team_context=team_context
        )

        # premium_position_focus=1.0, QB → 1.3x multiplier
        expected_value = 80 * 1.3
        assert abs(result - expected_value) < 1.0

    def test_premium_position_no_boost_for_non_premium(self):
        """Premium position modifier should not apply to RB/WR/etc."""
        gm = GMArchetype(premium_position_focus=1.0)
        prospect = Player(overall=80, position='RB')
        base_value = 80

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=25, gm=gm, team_context=team_context
        )

        # position='RB' (not QB/Edge/LT), no premium modifier

    # ===== Veteran Preference Tests (2 tests) =====

    def test_veteran_preference_boost_older_prospect(self):
        """Veteran preference GM should boost older prospects."""
        gm = GMArchetype(veteran_preference=0.9)
        prospect = Player(overall=74, age=25)
        base_value = 74

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=100, gm=gm, team_context=team_context
        )

        # veteran_preference=0.9, age=25 → 1.18x multiplier
        assert result > base_value

    def test_veteran_preference_no_boost_for_young_prospect(self):
        """Veteran preference should not apply to young prospects."""
        gm = GMArchetype(veteran_preference=0.9)
        prospect = Player(overall=74, age=21)
        base_value = 74

        result = PersonalityModifiers.apply_draft_modifier(
            prospect, draft_position=100, gm=gm, team_context=team_context
        )

        # age=21 (not >=24), no veteran modifier

    # ===== Draft Pick Value Tests (1 test) =====

    def test_draft_pick_value_bpa_vs_need(self):
        """Draft pick value affects BPA vs need-based drafting."""
        # This is tested in integration tests (complex selection logic)
        # Unit test just verifies trait exists and is accessible
        gm = GMArchetype(draft_pick_value=0.9)
        assert gm.draft_pick_value == 0.9
```

#### Roster Cut Modifiers (4 tests)

**Test Class**: `TestRosterCutModifiers`

```python
class TestRosterCutModifiers:
    """Unit tests for roster cut personality modifiers."""

    # ===== Loyalty Tests (2 tests) =====

    def test_loyalty_boost_for_long_tenured_player(self):
        """Loyal GM should boost long-tenured player value."""
        gm = GMArchetype(loyalty=0.9)
        player = Player(overall=75, years_with_team=8)
        objective_value = 60

        result = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, team_context
        )

        # loyalty=0.9, 8 years → 1.36x multiplier
        assert result > objective_value

    def test_loyalty_no_boost_for_new_player(self):
        """Loyalty should not apply to <5 year players."""
        gm = GMArchetype(loyalty=0.9)
        player = Player(overall=75, years_with_team=2)
        objective_value = 60

        result = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, team_context
        )

        # years_with_team=2 (not >=5), no loyalty modifier

    # ===== Cap Management Tests (1 test) =====

    def test_cap_management_discount_expensive_player(self):
        """Cap-conscious GM should discount expensive players."""
        gm = GMArchetype(cap_management=0.9)
        player = Player(overall=78, cap_hit=8_000_000)
        objective_value = 70

        result = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, team_context
        )

        # cap_management=0.9, $8M cap hit → 0.8x multiplier
        assert result < objective_value

    # ===== Veteran Preference Tests (1 test) =====

    def test_veteran_preference_boost_for_veteran(self):
        """Veteran preference GM should boost 30+ age players."""
        gm = GMArchetype(veteran_preference=0.9)
        player = Player(overall=76, age=32, years_with_team=3)
        objective_value = 72

        result = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, team_context
        )

        # veteran_preference=0.9, age=32 → 1.16x multiplier
        assert result > objective_value
```

---

## Integration Tests (Manager Level)

### Free Agency Integration Tests

**Location**: `tests/offseason/test_free_agency_gm_integration.py`

**Total**: 5 tests

```python
class TestFreeAgencyGMIntegration:
    """Integration tests for free agency with GM personalities."""

    def test_win_now_gm_overpays_for_veterans(self):
        """Win-Now GM should sign more expensive veteran free agents."""
        # Setup: Same FA market, Win-Now GM
        gm = GMArchetype(win_now_mentality=0.9, cap_management=0.3)
        fa_manager = FreeAgencyManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        # Run 30-day FA simulation
        signings = fa_manager.simulate_free_agency()

        # Assertions:
        avg_aav = sum(s['contract']['aav'] for s in signings) / len(signings)
        avg_age = sum(s['player'].age for s in signings) / len(signings)

        assert avg_aav > 15_000_000  # Overpays (baseline ~$12M)
        assert avg_age > 28  # Signs veterans

    def test_rebuilder_gm_signs_value_deals(self):
        """Rebuilder GM should only sign value free agents."""
        gm = GMArchetype(win_now_mentality=0.2, cap_management=0.9)
        fa_manager = FreeAgencyManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        signings = fa_manager.simulate_free_agency()

        # Count "overpay" signings (AAV > 120% of objective market value)
        overpays = [s for s in signings if s['contract']['aav'] > s['market_value']['aav'] * 1.2]

        assert len(overpays) == 0  # No overpays
        assert len(signings) <= 5  # Selective signings

    def test_cap_conscious_gm_avoids_expensive_contracts(self):
        """Cap-conscious GM should avoid $15M+ AAV contracts."""
        gm = GMArchetype(cap_management=0.9, win_now_mentality=0.5)
        fa_manager = FreeAgencyManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        signings = fa_manager.simulate_free_agency()

        expensive_signings = [s for s in signings if s['contract']['aav'] > 15_000_000]

        assert len(expensive_signings) <= 1  # Very few expensive contracts

    def test_star_chaser_prioritizes_elite_free_agents(self):
        """Star chaser GM should sign more 90+ OVR free agents."""
        gm = GMArchetype(star_chasing=1.0, cap_management=0.3)
        fa_manager = FreeAgencyManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        signings = fa_manager.simulate_free_agency()

        elite_signings = [s for s in signings if s['player'].overall >= 90]

        assert len(elite_signings) >= 2  # Signs multiple elite FAs

    def test_backward_compatibility_no_gm(self):
        """FA manager should work without GM archetype (backward compat)."""
        fa_manager = FreeAgencyManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=None  # No GM
        )

        signings = fa_manager.simulate_free_agency()

        # Should use objective logic (no personality modifiers)
        assert len(signings) > 0  # Still signs free agents
```

### Draft Integration Tests

**Location**: `tests/offseason/test_draft_gm_integration.py`

**Total**: 6 tests

```python
class TestDraftGMIntegration:
    """Integration tests for draft with GM personalities."""

    def test_risk_tolerant_gm_drafts_high_ceiling_prospects(self):
        """Risk-tolerant GM should draft more high-ceiling prospects."""
        gm = GMArchetype(risk_tolerance=0.9)
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        # Simulate Round 1 (32 picks)
        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        # Count high-ceiling picks (upside >10)
        high_ceiling_picks = [p for p in picks if (p.prospect.potential - p.prospect.overall) > 10]

        # Risk-tolerant GM should draft ≥30% high-ceiling prospects
        assert len(high_ceiling_picks) >= 10  # ≥10/32 picks

    def test_conservative_gm_drafts_safe_picks(self):
        """Conservative GM should draft more high-floor prospects."""
        gm = GMArchetype(risk_tolerance=0.2)
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        # Count safe picks (upside ≤5)
        safe_picks = [p for p in picks if (p.prospect.potential - p.prospect.overall) <= 5]

        assert len(safe_picks) >= 15  # ≥15/32 picks (mostly safe)

    def test_win_now_gm_drafts_polished_rookies(self):
        """Win-Now GM should draft older, pro-ready prospects."""
        gm = GMArchetype(win_now_mentality=0.9)
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        avg_age = sum(p.prospect.age for p in picks) / len(picks)

        assert avg_age >= 22.5  # Older prospects

    def test_rebuilder_gm_drafts_developmental_projects(self):
        """Rebuilder GM should draft younger prospects."""
        gm = GMArchetype(win_now_mentality=0.2)
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        avg_age = sum(p.prospect.age for p in picks) / len(picks)

        assert avg_age <= 21.5  # Younger prospects

    def test_premium_position_focus_gm_prioritizes_qb_edge_lt(self):
        """Premium position focus GM should draft more QB/Edge/LT."""
        gm = GMArchetype(premium_position_focus=1.0)
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        premium_picks = [p for p in picks if p.prospect.position in ['QB', 'EDGE', 'LT']]

        assert len(premium_picks) >= 12  # ≥40% of Round 1 picks

    def test_backward_compatibility_no_gm(self):
        """Draft manager should work without GM archetype."""
        draft_manager = DraftManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=None
        )

        picks = draft_manager.simulate_draft_round(round_number=1, draft_order=list(range(1, 33)))

        assert len(picks) == 32  # Completes round
```

### Roster Cuts Integration Tests

**Location**: `tests/offseason/test_roster_cuts_gm_integration.py`

**Total**: 5 tests

```python
class TestRosterCutsGMIntegration:
    """Integration tests for roster cuts with GM personalities."""

    def test_loyal_gm_keeps_long_tenured_veterans(self):
        """Loyal GM should keep more long-tenured players."""
        gm = GMArchetype(loyalty=0.9)
        roster_manager = RosterManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        # 90-man roster with mix of tenure
        cuts = roster_manager.execute_roster_cuts(team_id=9)

        # Count long-tenured players (5+ years) in cuts
        long_tenured_cuts = [c for c in cuts if c['player'].years_with_team >= 5]

        assert len(long_tenured_cuts) <= 3  # Keeps most long-tenured players

    def test_cap_conscious_gm_cuts_expensive_backups(self):
        """Cap-conscious GM should cut more expensive players."""
        gm = GMArchetype(cap_management=0.9)
        roster_manager = RosterManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        cuts = roster_manager.execute_roster_cuts(team_id=9)

        # Count expensive players (>$5M cap hit) in cuts
        expensive_cuts = [c for c in cuts if c['player'].cap_hit > 5_000_000]

        assert len(expensive_cuts) >= 5  # Cuts expensive backups

    def test_veteran_preference_gm_keeps_older_players(self):
        """Veteran preference GM should keep more 30+ age players."""
        gm = GMArchetype(veteran_preference=0.9)
        roster_manager = RosterManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        cuts = roster_manager.execute_roster_cuts(team_id=9)

        # Count 30+ age players in cuts
        veteran_cuts = [c for c in cuts if c['player'].age >= 30]

        assert len(veteran_cuts) <= 5  # Keeps most veterans

    def test_youth_focused_gm_gives_opportunities_to_young_players(self):
        """Youth-focused GM should cut more 30+ age players."""
        gm = GMArchetype(veteran_preference=0.2)
        roster_manager = RosterManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=gm
        )

        cuts = roster_manager.execute_roster_cuts(team_id=9)

        veteran_cuts = [c for c in cuts if c['player'].age >= 30]

        assert len(veteran_cuts) >= 10  # Cuts many veterans

    def test_backward_compatibility_no_gm(self):
        """Roster manager should work without GM archetype."""
        roster_manager = RosterManager(
            database_path=test_db,
            dynasty_id='test',
            gm_archetype=None
        )

        cuts = roster_manager.execute_roster_cuts(team_id=9)

        assert len(cuts) == 37  # 90→53 (37 cuts)
```

### Cross-Context Consistency Tests

**Location**: `tests/integration/test_gm_cross_context_consistency.py`

**Total**: 4 tests

```python
class TestGMCrossContextConsistency:
    """Integration tests for GM consistency across trades, FA, draft, cuts."""

    def test_win_now_gm_consistency_across_contexts(self):
        """Win-Now GM should behave consistently in FA and trades."""
        gm = GMArchetype(win_now_mentality=0.9)

        # Free Agency: Should overpay for veterans
        fa_manager = FreeAgencyManager(..., gm_archetype=gm)
        fa_signings = fa_manager.simulate_free_agency()
        fa_avg_aav = sum(s['contract']['aav'] for s in fa_signings) / len(fa_signings)

        # Trades: Should value proven players highly (via PersonalityModifiers)
        # (This would use trade system, but just verify multiplier consistency)

        # Assertion: Both contexts should show similar overpay behavior
        # FA overpay ~1.3x, Trade modifier for proven players ~1.3x (consistent)

    def test_rebuilder_gm_consistency_across_contexts(self):
        """Rebuilder GM should behave consistently in draft and FA."""
        gm = GMArchetype(win_now_mentality=0.2)

        # Draft: Should draft young prospects
        draft_manager = DraftManager(..., gm_archetype=gm)
        picks = draft_manager.simulate_draft_round(1, list(range(1, 33)))
        avg_pick_age = sum(p.prospect.age for p in picks) / len(picks)

        # Free Agency: Should avoid expensive veterans
        fa_manager = FreeAgencyManager(..., gm_archetype=gm)
        signings = fa_manager.simulate_free_agency()
        avg_fa_age = sum(s['player'].age for s in signings) / len(signings)

        # Assertion: Both contexts should show youth preference
        assert avg_pick_age <= 21.5  # Draft young
        assert avg_fa_age <= 26  # Sign young FAs

    def test_loyal_gm_consistency_across_contexts(self):
        """Loyal GM should behave consistently in trades and roster cuts."""
        gm = GMArchetype(loyalty=0.9)

        # Roster Cuts: Should keep long-tenured players
        roster_manager = RosterManager(..., gm_archetype=gm)
        cuts = roster_manager.execute_roster_cuts(team_id=9)
        long_tenured_cuts = [c for c in cuts if c['player'].years_with_team >= 5]

        # Trades: Should value own players highly (via PersonalityModifiers)
        # (Trade modifier for own players ~1.4x when loyalty=0.9)

        # Assertion: Both contexts should show loyalty
        assert len(long_tenured_cuts) <= 3  # Keeps most long-tenured

    def test_multiplier_range_consistency(self):
        """Verify multiplier ranges are similar across contexts."""
        gm = GMArchetype(win_now_mentality=0.9, veteran_preference=0.9)

        # FA veteran preference: 1.16x for 30+ age
        # Draft veteran preference: 1.18x for 24+ age
        # Roster cut veteran preference: 1.16x for 30+ age

        # All should be within ±0.1x of each other (1.16-1.18x range is consistent)
```

---

## End-to-End Validation (Full Simulation)

### 32-Team Offseason Validation

**Location**: `scripts/validate_full_offseason_gm.py`

**Purpose**: Run complete offseason for all 32 teams, analyze GM behaviors

**Metrics Collected**:

1. **Free Agency**:
   - Average AAV by GM archetype
   - Age distribution by GM archetype
   - Position distribution by GM archetype
   - Overpay percentage (AAV > 120% of market value)
   - Elite free agent signings (90+ OVR)

2. **Draft**:
   - Average prospect ceiling (potential) by GM archetype
   - Average prospect age by GM archetype
   - Position distribution (QB/Edge/LT vs others)
   - High-ceiling vs safe picks ratio

3. **Roster Cuts**:
   - Average tenure of cut players by GM archetype
   - Average cap hit of cut players by GM archetype
   - Age distribution of cut players by GM archetype

**Success Criteria**:

| Metric | Measurement | Target Variance |
|--------|-------------|----------------|
| FA AAV | Win-Now vs Rebuilder | ≥20% |
| Draft Ceiling | Risk-Tolerant vs Conservative | ≥30% |
| Cut Tenure | Loyal vs Ruthless | ≥20% |
| FA Age | Veteran Preference vs Youth | ≥2 years |
| Draft Age | Win-Now vs Rebuilder | ≥1.5 years |
| Cut Cap Hit | Cap-Conscious vs Flexible | ≥$2M avg |

**Validation Script**:

```python
def validate_full_offseason():
    """Run 32-team offseason simulation and validate GM behaviors."""

    results = {
        'free_agency': {},
        'draft': {},
        'roster_cuts': {}
    }

    for team_id in range(1, 33):
        gm = GMArchetypeFactory.create_for_team(team_id)

        # Run offseason
        controller = OffseasonController(database_path, dynasty_id)
        team_results = controller.simulate_ai_full_offseason_for_team(team_id, gm)

        # Collect metrics
        results['free_agency'][team_id] = {
            'avg_aav': calculate_avg_aav(team_results['fa_signings']),
            'avg_age': calculate_avg_age(team_results['fa_signings']),
            'elite_count': count_elite_signings(team_results['fa_signings'])
        }

        results['draft'][team_id] = {
            'avg_ceiling': calculate_avg_ceiling(team_results['draft_picks']),
            'avg_age': calculate_avg_age(team_results['draft_picks'])
        }

        results['roster_cuts'][team_id] = {
            'avg_tenure': calculate_avg_tenure(team_results['cuts']),
            'avg_cap_hit': calculate_avg_cap_hit(team_results['cuts'])
        }

    # Analyze results by archetype
    analyze_by_archetype(results)

    # Generate report
    generate_validation_report(results)
```

---

## Performance Testing

### Load Testing

**Goal**: Ensure GM integration doesn't significantly degrade performance

**Test**: Time 100 iterations of full offseason simulation

**Acceptance Criteria**: <10% performance degradation vs no-GM baseline

**Script**:

```python
import time

def performance_test():
    """Measure performance impact of GM integration."""

    # Baseline (no GM)
    start = time.time()
    for i in range(100):
        controller = OffseasonController(..., gm_archetype=None)
        controller.simulate_ai_full_offseason(user_team_id=1)
    baseline_time = time.time() - start

    # With GM integration
    start = time.time()
    for i in range(100):
        gm = GMArchetypeFactory.create_for_team(9)
        controller = OffseasonController(..., gm_archetype=gm)
        controller.simulate_ai_full_offseason(user_team_id=1)
    gm_time = time.time() - start

    overhead = ((gm_time - baseline_time) / baseline_time) * 100

    print(f"Baseline: {baseline_time:.2f}s")
    print(f"With GM: {gm_time:.2f}s")
    print(f"Overhead: {overhead:.1f}%")

    assert overhead < 10  # <10% overhead acceptable
```

---

## Test Coverage

### Coverage Goals

| Module | Target Coverage |
|--------|----------------|
| `personality_modifiers.py` | 100% |
| `free_agency_manager.py` | 85% |
| `draft_manager.py` | 80% |
| `roster_manager.py` | 85% |
| `offseason_controller.py` | 75% |

### Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=src/transactions --cov=src/offseason --cov-report=html

# View report
open htmlcov/index.html
```

---

## Continuous Integration

### GitHub Actions Workflow (if applicable)

```yaml
name: GM AI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python 3.13
      uses: actions/setup-python@v2
      with:
        python-version: 3.13

    - name: Install dependencies
      run: pip install -r requirements-ui.txt pytest pytest-cov

    - name: Run unit tests
      run: pytest tests/ -v --cov=src/transactions --cov=src/offseason

    - name: Run integration tests
      run: pytest tests/offseason/ tests/integration/ -v

    - name: Run validation scripts
      run: |
        python scripts/validate_fa_gm_behavior.py
        python scripts/validate_draft_gm_behavior.py
        python scripts/validate_roster_cuts_gm_behavior.py

    - name: Generate coverage report
      run: pytest --cov=src --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
```

---

## Regression Testing

### Existing Test Suites

**CRITICAL**: All existing tests MUST continue to pass

**Test Suites**:
- `tests/calendar/` - Calendar system tests
- `tests/playoff_system/` - Playoff system tests
- `tests/salary_cap/` - Salary cap tests
- `tests/player_generation/` - Player generation tests
- `tests/statistics/` - Statistics system tests
- `tests/services/` - Service layer tests (20/30 expected to pass)
- `tests/database/` - Database layer tests

**Regression Check**:

```bash
# Run all existing tests BEFORE making any changes
pytest tests/ -v > baseline_results.txt

# After GM integration, run all tests again
pytest tests/ -v > gm_integration_results.txt

# Diff the results
diff baseline_results.txt gm_integration_results.txt

# Assertion: No new failures (only new tests added)
```

---

## Documentation

**MILESTONE 2: Unified GM AI Infrastructure** is now fully documented. All 5 planning documents created:

1. ✅ `README.md` - Executive summary and roadmap
2. ✅ `01_current_state.md` - Comprehensive audit findings
3. ✅ `02_architecture.md` - Unified GM brain design
4. ✅ `03_implementation_plan.md` - 4-phase rollout with detailed tasks
5. ✅ `05_testing_strategy.md` - This file (complete validation approach)

The plan is ready for implementation. Next steps:
- Review and approve milestone plan
- Create feature branch: `feature/milestone-2-gm-ai`
- Begin Phase 1: Free Agency GM Integration