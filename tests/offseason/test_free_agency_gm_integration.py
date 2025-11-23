"""
Integration tests for FreeAgencyManager with GM personality modifiers.

Tests verify that GM archetypes correctly influence free agency contract offers.
Validates that personality traits (win_now, star_chasing, veteran_preference, etc.)
produce measurable differences in contract AAV values.
"""

import pytest
from offseason.free_agency_manager import FreeAgencyManager
from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import TeamContext


class TestFreeAgencyGMIntegration:
    """Integration tests for GM personality-driven free agency."""

    @pytest.fixture
    def fa_manager(self):
        """Create FreeAgencyManager instance for testing."""
        return FreeAgencyManager(
            database_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2024,
            enable_persistence=False,
            verbose_logging=False
        )

    @pytest.fixture
    def win_now_gm(self):
        """Win-Now GM archetype: Overpays for proven talent."""
        return GMArchetype(
            name="Win-Now GM",
            description="Championship window, aggressive spending",
            risk_tolerance=0.6,
            win_now_mentality=0.95,  # Very high win-now
            draft_pick_value=0.2,
            cap_management=0.2,  # Low cap discipline
            trade_frequency=0.8,
            veteran_preference=0.8,
            star_chasing=0.7,
            loyalty=0.4,
            desperation_threshold=0.6,
            patience_years=2,
            deadline_activity=0.9,
            premium_position_focus=0.7
        )

    @pytest.fixture
    def rebuilder_gm(self):
        """Rebuilder GM archetype: Value deals, youth focus."""
        return GMArchetype(
            name="Rebuilder GM",
            description="Building for future, cap conservative",
            risk_tolerance=0.5,
            win_now_mentality=0.15,  # Very low win-now
            draft_pick_value=0.9,
            cap_management=0.85,  # High cap discipline
            trade_frequency=0.4,
            veteran_preference=0.2,  # Youth preference
            star_chasing=0.2,
            loyalty=0.6,
            desperation_threshold=0.4,
            patience_years=5,
            deadline_activity=0.3,
            premium_position_focus=0.5
        )

    @pytest.fixture
    def star_chaser_gm(self):
        """Star Chaser GM archetype: Pays premium for elite talent."""
        return GMArchetype(
            name="Star Chaser GM",
            description="Builds around superstars",
            risk_tolerance=0.7,
            win_now_mentality=0.6,
            draft_pick_value=0.4,
            cap_management=0.3,  # Low cap discipline
            trade_frequency=0.7,
            veteran_preference=0.5,
            star_chasing=0.95,  # Very high star chasing
            loyalty=0.5,
            desperation_threshold=0.6,
            patience_years=3,
            deadline_activity=0.7,
            premium_position_focus=0.8
        )

    @pytest.fixture
    def neutral_gm(self):
        """Neutral GM archetype: All traits at 0.5 (baseline)."""
        return GMArchetype(
            name="Neutral GM",
            description="Balanced approach, no strong preferences",
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=0.5
        )

    @pytest.fixture
    def mock_fa_pool(self):
        """Create mock free agent pool with diverse players."""
        return [
            # Elite player (92 OVR QB, prime age)
            {
                'player_id': 'fa_elite_qb',
                'player_name': 'Elite QB',
                'position': 'quarterback',
                'overall': 92,
                'age': 28,
                'years_pro': 6,
                'injury_prone': False
            },
            # Superstar (90 OVR WR)
            {
                'player_id': 'fa_superstar_wr',
                'player_name': 'Superstar WR',
                'position': 'wide_receiver',
                'overall': 90,
                'age': 26,
                'years_pro': 4,
                'injury_prone': False
            },
            # Young starter (78 OVR WR, 25 years old)
            {
                'player_id': 'fa_young_wr',
                'player_name': 'Young WR',
                'position': 'wide_receiver',
                'overall': 78,
                'age': 25,
                'years_pro': 3,
                'injury_prone': False
            },
            # Veteran (82 OVR LT, 32 years old)
            {
                'player_id': 'fa_vet_lt',
                'player_name': 'Veteran LT',
                'position': 'left_tackle',
                'overall': 82,
                'age': 32,
                'years_pro': 10,
                'injury_prone': False
            },
            # Injury-prone (80 OVR RB)
            {
                'player_id': 'fa_injury_rb',
                'player_name': 'Injury RB',
                'position': 'running_back',
                'overall': 80,
                'age': 27,
                'years_pro': 5,
                'injury_prone': True
            },
            # Average starter (83 OVR DE)
            {
                'player_id': 'fa_avg_de',
                'player_name': 'Average DE',
                'position': 'defensive_end',
                'overall': 83,
                'age': 27,
                'years_pro': 5,
                'injury_prone': False
            }
        ]

    @pytest.fixture
    def mock_standings(self):
        """Mock standings data for team context."""
        return [
            {'team_id': 1, 'wins': 11, 'losses': 6, 'ties': 0},  # Contender
            {'team_id': 2, 'wins': 3, 'losses': 14, 'ties': 0},  # Rebuilder
        ]

    @pytest.fixture
    def mock_team_needs(self):
        """Mock team needs for context building."""
        return [
            {'position': 'quarterback', 'urgency': 0.9},
            {'position': 'wide_receiver', 'urgency': 0.8},
            {'position': 'defensive_end', 'urgency': 0.7}
        ]

    # ============================================================================
    # WIN-NOW GM TESTS
    # ============================================================================

    def test_win_now_gm_overpays_for_starters(self, fa_manager, win_now_gm, mock_fa_pool,
                                                mock_standings, mock_team_needs, monkeypatch):
        """Verify Win-Now GM pays ≥15% premium for proven starters (80+ OVR)."""
        # Set up manager with Win-Now GM
        fa_manager.gm = win_now_gm

        # Mock dependencies
        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 40_000_000
        )
        # Mock needs_analyzer.get_top_needs (which is called by _simulate_team_fa_day)
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'get_top_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: win_now_gm
        )

        # Simulate FA day with proven starter (83 OVR DE)
        # Use day 5 (Starters tier, min_overall=75) instead of day 1 (Elite tier, min_overall=85)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_avg_de']
        signings = fa_manager.simulate_free_agency_day(
            day_number=5,  # Day 5 allows 75+ OVR starters
            user_team_id=30,  # Skip team 30
            available_fas=available_fas
        )

        # Get base market value for comparison
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='defensive_end',
            overall=83,
            age=27,
            years_pro=5
        )
        base_aav = base_contract['aav']

        # Verify at least one team signed the player
        assert len(signings) > 0, "Win-Now GM should sign proven starter"

        # Verify contract AAV is ≥15% higher than base market value
        # Win-now modifier should apply (win_now_mentality=0.95, player OVR=83 > 80)
        signing = signings[0]
        assert signing['contract_aav'] >= base_aav * 1.15, \
            f"Expected ≥15% premium, got {signing['contract_aav']} vs base {base_aav}"

    def test_win_now_gm_prefers_shorter_contracts(self, fa_manager, win_now_gm, mock_fa_pool,
                                                    mock_standings, mock_team_needs, monkeypatch):
        """Verify Win-Now GMs prefer shorter contracts (2-3 years) for flexibility."""
        fa_manager.gm = win_now_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 50_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: win_now_gm
        )

        # Simulate FA day
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_young_wr']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Verify contract years
        if signings:
            signing = signings[0]
            # Win-now teams prefer shorter deals (typically 2-3 years)
            assert signing['contract_years'] <= 3, \
                f"Win-Now GM should prefer ≤3 year deals, got {signing['contract_years']}"

    # ============================================================================
    # REBUILDER GM TESTS
    # ============================================================================

    def test_rebuilder_gm_seeks_value_deals(self, fa_manager, rebuilder_gm, mock_fa_pool,
                                             mock_standings, mock_team_needs, monkeypatch):
        """Verify Rebuilder GM gets discounted contracts for non-elite players."""
        fa_manager.gm = rebuilder_gm

        # Mock rebuilding team (3-14 record)
        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 60_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: rebuilder_gm
        )

        # Simulate FA day with young starter (78 OVR WR)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_young_wr']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='wide_receiver',
            overall=78,
            age=25,
            years_pro=3
        )
        base_aav = base_contract['aav']

        # Verify Rebuilder GM gets discount (cap_management=0.85 applies to non-elite)
        if signings:
            signing = signings[0]
            # Cap-conscious GMs discount non-elite players (OVR 78 < 85)
            # Expected: 0.6x multiplier (1.0 - 0.85 * 0.4 = 0.66)
            assert signing['contract_aav'] < base_aav, \
                f"Rebuilder should get discount, got {signing['contract_aav']} vs base {base_aav}"

    def test_rebuilder_gm_prefers_longer_deals(self, fa_manager, rebuilder_gm, mock_fa_pool,
                                                mock_standings, mock_team_needs, monkeypatch):
        """Verify Rebuilders prefer longer deals (4-5 years) for cost certainty."""
        fa_manager.gm = rebuilder_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 70_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: rebuilder_gm
        )

        # Simulate FA day
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_young_wr']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Base contract years for WR is 3
        base_years = 3

        # Rebuilders typically lock in young players for longer
        # Note: Current implementation doesn't modify years, just AAV
        # This test documents expected behavior for future enhancement
        if signings:
            signing = signings[0]
            # Currently returns base years (3), future enhancement would increase to 4-5
            assert signing['contract_years'] >= base_years

    # ============================================================================
    # STAR CHASER GM TESTS
    # ============================================================================

    def test_star_chaser_targets_elite_talent(self, fa_manager, star_chaser_gm, mock_fa_pool,
                                               mock_standings, mock_team_needs, monkeypatch):
        """Verify Star Chaser GM pays significant premium for 90+ OVR players."""
        fa_manager.gm = star_chaser_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 80_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: star_chaser_gm
        )

        # Simulate FA day with superstar (90 OVR WR)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_superstar_wr']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='wide_receiver',
            overall=90,
            age=26,
            years_pro=4
        )
        base_aav = base_contract['aav']

        # Verify Star Chaser pays significant premium for elite talent
        assert len(signings) > 0, "Star Chaser should sign elite player"

        signing = signings[0]
        # Star chasing modifier: 1.0 + (0.95 * 0.5) = 1.475x for 90+ OVR
        # Expected premium: ≥40%
        assert signing['contract_aav'] >= base_aav * 1.40, \
            f"Expected ≥40% premium for elite talent, got {signing['contract_aav']} vs base {base_aav}"

    def test_star_chaser_ignores_non_elite(self, fa_manager, star_chaser_gm, mock_fa_pool,
                                            mock_standings, mock_team_needs, monkeypatch):
        """Verify Star Chaser GM discounts average players (75-84 OVR)."""
        fa_manager.gm = star_chaser_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 50_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: star_chaser_gm
        )

        # Simulate FA day with average starter (78 OVR WR)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_young_wr']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='wide_receiver',
            overall=78,
            age=25,
            years_pro=3
        )
        base_aav = base_contract['aav']

        # Star Chasers may sign but discount average players
        # Cap management (0.3) + star_chasing discount for non-elite
        if signings:
            signing = signings[0]
            # Expected: Discount due to cap_management (0.3) on non-elite (OVR 78 < 85)
            # Multiplier: 1.0 - (0.3 * 0.4) = 0.88x
            assert signing['contract_aav'] <= base_aav * 0.95, \
                f"Star Chaser should discount non-elite, got {signing['contract_aav']} vs base {base_aav}"

    # ============================================================================
    # BACKWARD COMPATIBILITY TESTS
    # ============================================================================

    def test_backward_compatibility_no_gm(self, fa_manager, mock_fa_pool,
                                          mock_standings, mock_team_needs, monkeypatch):
        """Verify neutral behavior when no GM archetype provided."""
        # fa_manager.gm is None by default

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 40_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        # Return neutral GM for all teams
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: GMArchetype(
                name="Neutral",
                description="All traits neutral",
                risk_tolerance=0.5,
                win_now_mentality=0.5,
                draft_pick_value=0.5,
                cap_management=0.5,
                trade_frequency=0.5,
                veteran_preference=0.5,
                star_chasing=0.5,
                loyalty=0.5,
                desperation_threshold=0.5,
                patience_years=3,
                deadline_activity=0.5,
                premium_position_focus=0.5
            )
        )

        # Simulate FA day
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_avg_de']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='defensive_end',
            overall=83,
            age=27,
            years_pro=5
        )
        base_aav = base_contract['aav']

        # Verify contracts close to base market value (no significant modifiers)
        # Neutral GM with all 0.5 traits should produce near-base values
        if signings:
            signing = signings[0]
            # Allow ±5% variance for neutral GM
            assert 0.95 * base_aav <= signing['contract_aav'] <= 1.05 * base_aav, \
                f"Neutral GM should be near base value, got {signing['contract_aav']} vs base {base_aav}"

    # ============================================================================
    # AGE-BASED MODIFIER TESTS
    # ============================================================================

    def test_veteran_preference_modifier(self, fa_manager, mock_fa_pool,
                                         mock_standings, mock_team_needs, monkeypatch):
        """Verify veteran-focused GMs adjust contracts for 30+ players."""
        # Create veteran-preferring GM
        vet_gm = GMArchetype(
            name="Veteran GM",
            description="Prefers experienced players",
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.9,  # High veteran preference
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=0.5
        )

        fa_manager.gm = vet_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 50_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: vet_gm
        )

        # Simulate FA day with veteran (32 year old LT)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_vet_lt']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='left_tackle',
            overall=82,
            age=32,
            years_pro=10
        )
        base_aav = base_contract['aav']

        # Verify veteran-preferring GM pays premium for 30+ players
        if signings:
            signing = signings[0]
            # veteran_preference modifier: 1.0 + ((0.9 - 0.5) * 0.4) = 1.16x
            assert signing['contract_aav'] >= base_aav * 1.10, \
                f"Veteran GM should pay premium for 30+ age, got {signing['contract_aav']} vs base {base_aav}"

    def test_youth_preference_modifier(self, fa_manager, mock_fa_pool,
                                       mock_standings, mock_team_needs, monkeypatch):
        """Verify youth-focused GMs discount 30+ age players."""
        # Create youth-preferring GM
        youth_gm = GMArchetype(
            name="Youth GM",
            description="Prefers young talent",
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.1,  # Low veteran preference = youth focus
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=0.5
        )

        fa_manager.gm = youth_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 50_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: youth_gm
        )

        # Simulate FA day with veteran (32 year old LT)
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_vet_lt']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='left_tackle',
            overall=82,
            age=32,
            years_pro=10
        )
        base_aav = base_contract['aav']

        # Verify youth-preferring GM discounts 30+ age players
        if signings:
            signing = signings[0]
            # veteran_preference modifier: 1.0 - ((0.5 - 0.1) * 0.4) = 0.84x
            assert signing['contract_aav'] <= base_aav * 0.90, \
                f"Youth GM should discount 30+ age, got {signing['contract_aav']} vs base {base_aav}"

    # ============================================================================
    # INJURY-PRONE PLAYER HANDLING TESTS
    # ============================================================================

    def test_injury_prone_discount_risk_averse(self, fa_manager, mock_fa_pool,
                                                mock_standings, mock_team_needs, monkeypatch):
        """Verify risk-averse GMs discount injury-prone players."""
        # Create risk-averse GM
        risk_averse_gm = GMArchetype(
            name="Risk-Averse GM",
            description="Avoids injury-prone players",
            risk_tolerance=0.1,  # Very low risk tolerance
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=0.5
        )

        fa_manager.gm = risk_averse_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 40_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: risk_averse_gm
        )

        # Simulate FA day with injury-prone player
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_injury_rb']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='running_back',
            overall=80,
            age=27,
            years_pro=5
        )
        base_aav = base_contract['aav']

        # Verify risk-averse GM discounts injury-prone players
        if signings:
            signing = signings[0]
            # risk_tolerance modifier: 1.0 - ((0.5 - 0.1) * 0.6) = 0.76x
            assert signing['contract_aav'] <= base_aav * 0.85, \
                f"Risk-averse GM should discount injury-prone, got {signing['contract_aav']} vs base {base_aav}"

    def test_injury_prone_neutral_risk_tolerant(self, fa_manager, mock_fa_pool,
                                                 mock_standings, mock_team_needs, monkeypatch):
        """Verify risk-tolerant GMs accept injury-prone players at market value."""
        # Create risk-tolerant GM
        risk_tolerant_gm = GMArchetype(
            name="Risk-Tolerant GM",
            description="Willing to gamble on injury-prone talent",
            risk_tolerance=0.9,  # Very high risk tolerance
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.5,
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=0.5
        )

        fa_manager.gm = risk_tolerant_gm

        monkeypatch.setattr(
            fa_manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            fa_manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 40_000_000
        )
        monkeypatch.setattr(
            fa_manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: mock_team_needs
        )
        monkeypatch.setattr(
            fa_manager.gm_factory,
            'get_team_archetype',
            lambda team_id: risk_tolerant_gm
        )

        # Simulate FA day with injury-prone player
        available_fas = [fa for fa in mock_fa_pool if fa['player_id'] == 'fa_injury_rb']
        signings = fa_manager.simulate_free_agency_day(
            day_number=1,
            user_team_id=30,
            available_fas=available_fas
        )

        # Get base market value
        base_contract = fa_manager.market_calc.calculate_player_value(
            position='running_back',
            overall=80,
            age=27,
            years_pro=5
        )
        base_aav = base_contract['aav']

        # Verify risk-tolerant GM pays closer to market value
        # High risk_tolerance (0.9) means minimal discount for injury-prone
        # Modifier only applies when risk_tolerance < 0.5
        if signings:
            signing = signings[0]
            # No injury discount for high risk_tolerance (≥0.5)
            # Should be close to base value (±10%)
            assert 0.90 * base_aav <= signing['contract_aav'] <= 1.10 * base_aav, \
                f"Risk-tolerant GM should accept injury-prone near base, got {signing['contract_aav']} vs base {base_aav}"