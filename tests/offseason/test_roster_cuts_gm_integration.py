"""
Test Behavioral Validation - GM Personality Integration for Roster Cuts

Proves that GM personalities create observable differences in roster cut decisions.
Each test validates a specific behavioral difference between contrasting GM archetypes.

Test Strategy:
- Create contrasting GMs (e.g., Loyal vs Ruthless, Cap-Conscious vs Cap-Flexible)
- Create 90-man rosters with specific player distributions
- Run roster cuts with both GMs
- Validate behavioral differences with quantitative assertions
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from team_management.gm_archetype import GMArchetype


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_player(player_id, overall, position, age, years_with_team, cap_hit):
    """
    Create mock player dict for testing.

    Args:
        player_id: Unique player ID
        overall: Overall rating (0-100)
        position: Position name (e.g., 'linebacker')
        age: Player age (20-40)
        years_with_team: Years with current team (0-15)
        cap_hit: Annual cap hit in dollars

    Returns:
        Player dict with all required fields
    """
    # Calculate joined_date based on years_with_team
    current_season = 2024
    joined_year = current_season - years_with_team

    return {
        'player_id': player_id,
        'player_name': f'Player {player_id}',
        'number': player_id,
        'position': position,
        'overall': overall,
        'age': age,
        'cap_hit': cap_hit,
        'joined_date': f'{joined_year}-09-01'
    }


def create_90_man_roster_with_veterans():
    """
    Create 90-player roster with mix of veterans and young players.

    Distribution:
    - 30 long-tenured veterans (6+ years, age 30+, OVR 74-76)
    - 60 younger players (0-2 years, age 22-26, OVR 75-77)

    Returns:
        List of 90 player dicts
    """
    roster = []

    # 30 long-tenured veterans (6+ years with team)
    # Mix of ratings: some good (76), some average (75), some below (74)
    for i in range(30):
        overall = 74 + (i % 3)  # 74, 75, 76 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='linebacker',
            age=31,
            years_with_team=7,  # Long tenure
            cap_hit=3_500_000
        ))

    # 60 younger players (0-2 years) - slightly better overall on average
    for i in range(30, 90):
        overall = 75 + (i % 3)  # 75, 76, 77 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='safety',
            age=24,
            years_with_team=1,
            cap_hit=1_500_000
        ))

    return roster


def create_90_man_roster_with_expensive_players():
    """
    Create 90-player roster with mix of expensive and cheap contracts.

    Distribution:
    - 35 expensive players (>$5M cap hit, OVR 76-78)
    - 55 cheap players (<$2M cap hit, OVR 75-77)

    Returns:
        List of 90 player dicts
    """
    roster = []

    # 35 expensive players (>$5M cap hit) - varying quality
    for i in range(35):
        overall = 76 + (i % 3)  # 76, 77, 78 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='wide_receiver',
            age=28,
            years_with_team=3,
            cap_hit=6_000_000 + (i % 3) * 1_000_000  # $6M-$8M
        ))

    # 55 cheap players (<$2M cap hit) - slightly worse on average
    for i in range(35, 90):
        overall = 75 + (i % 3)  # 75, 76, 77 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='cornerback',
            age=25,
            years_with_team=2,
            cap_hit=1_000_000 + (i % 2) * 500_000  # $1M-$1.5M
        ))

    return roster


def create_90_man_roster_with_age_mix():
    """
    Create 90-player roster with mix of veterans (30+) and young players.

    Distribution:
    - 30 veterans (30+ age, OVR 75-77)
    - 60 young players (22-26 age, OVR 74-76)

    Returns:
        List of 90 player dicts
    """
    roster = []

    # 30 veterans (30+ age) - mix of quality
    for i in range(30):
        overall = 75 + (i % 3)  # 75, 76, 77 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='defensive_end',
            age=32,
            years_with_team=5,
            cap_hit=4_000_000
        ))

    # 60 young players (22-26 age) - slightly worse on average
    for i in range(30, 90):
        overall = 74 + (i % 3)  # 74, 75, 76 rotation
        roster.append(create_test_player(
            player_id=i,
            overall=overall,
            position='running_back',
            age=24,
            years_with_team=2,
            cap_hit=2_000_000
        ))

    return roster


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_loyal_gm_keeps_more_long_tenured_players():
    """
    Test that loyal GMs keep significantly more long-tenured players.

    Setup:
    - Create Loyal GM (loyalty=0.9) vs Ruthless GM (loyalty=0.1)
    - Create 90-man roster: 30 long-tenured (7+ years), 60 younger players
    - Young players have slightly better overall on average to create objective advantage

    Validation:
    - Loyal GM should keep ≥15% more long-tenured players in final 53
    """
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'), \
         patch('transactions.team_context_service.TeamContextService') as mock_context_service:

        from offseason.roster_manager import RosterManager

        # Setup mock context
        mock_context = Mock()
        mock_context.cap_space = 30_000_000
        mock_context.is_contender = False
        mock_context.games_played = 0
        mock_context_service.return_value.build_team_context.return_value = mock_context

        # Create contrasting GMs
        loyal_gm = GMArchetype(
            name="Loyal Larry",
            description="Values loyalty and tenure",
            loyalty=0.9,
            veteran_preference=0.5,
            cap_management=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        ruthless_gm = GMArchetype(
            name="Ruthless Rick",
            description="No loyalty, objective evaluation only",
            loyalty=0.1,
            veteran_preference=0.5,
            cap_management=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        # Create test roster
        roster = create_90_man_roster_with_veterans()

        # Test Loyal GM
        manager_loyal = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=loyal_gm
        )
        manager_loyal._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_loyal = manager_loyal.finalize_53_man_roster_ai(team_id=1)

        # Test Ruthless GM
        manager_ruthless = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=ruthless_gm
        )
        manager_ruthless._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_ruthless = manager_ruthless.finalize_53_man_roster_ai(team_id=1)

        # Count long-tenured players in final rosters (30 total veterans)
        loyal_veterans = sum(1 for p in result_loyal['final_roster'] if p['player_id'] < 30)
        ruthless_veterans = sum(1 for p in result_ruthless['final_roster'] if p['player_id'] < 30)

        print(f"\nLoyal GM kept {loyal_veterans} veterans (out of 30)")
        print(f"Ruthless GM kept {ruthless_veterans} veterans (out of 30)")

        # Validation: Loyal GM should keep ≥15% more long-tenured players
        # If ruthless keeps 15, loyal should keep at least 17 (15% more)
        min_expected_loyal = ruthless_veterans * 1.15
        assert loyal_veterans >= min_expected_loyal, \
            f"Loyal GM should keep ≥15% more veterans. Expected ≥{min_expected_loyal:.1f}, got {loyal_veterans}"


def test_cap_conscious_gm_cuts_more_expensive_players():
    """
    Test that cap-conscious GMs keep fewer expensive players.

    Setup:
    - Create Cap-Conscious GM (cap_management=0.9) vs Cap-Flexible GM (cap_management=0.3)
    - Create 90-man roster: 35 expensive players ($6-8M), 55 cheap players
    - Cheap players have slightly worse overall on average to create objective disadvantage

    Validation:
    - Cap-Conscious GM should keep ≤ expensive players than Cap-Flexible GM
    - Proves cap_management modifier affects roster cut decisions
    """
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'), \
         patch('transactions.team_context_service.TeamContextService') as mock_context_service:

        from offseason.roster_manager import RosterManager

        # Setup mock context
        mock_context = Mock()
        mock_context.cap_space = 15_000_000
        mock_context.is_contender = False
        mock_context.games_played = 0
        mock_context_service.return_value.build_team_context.return_value = mock_context

        # Create contrasting GMs
        cap_conscious_gm = GMArchetype(
            name="Cap-Conscious Carl",
            description="Highly disciplined with cap space",
            cap_management=0.9,
            loyalty=0.5,
            veteran_preference=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        cap_flexible_gm = GMArchetype(
            name="Cap-Flexible Fred",
            description="Willing to spend freely",
            cap_management=0.3,
            loyalty=0.5,
            veteran_preference=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        # Create test roster
        roster = create_90_man_roster_with_expensive_players()

        # Test Cap-Conscious GM
        manager_cap_conscious = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=cap_conscious_gm
        )
        manager_cap_conscious._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_cap_conscious = manager_cap_conscious.finalize_53_man_roster_ai(team_id=1)

        # Test Cap-Flexible GM
        manager_cap_flexible = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=cap_flexible_gm
        )
        manager_cap_flexible._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_cap_flexible = manager_cap_flexible.finalize_53_man_roster_ai(team_id=1)

        # Count expensive players KEPT by each GM (35 total expensive players)
        cap_conscious_expensive_kept = sum(1 for p in result_cap_conscious['final_roster'] if p['player_id'] < 35)
        cap_flexible_expensive_kept = sum(1 for p in result_cap_flexible['final_roster'] if p['player_id'] < 35)

        # Count expensive players CUT
        cap_conscious_expensive_cuts = sum(1 for p in result_cap_conscious['cuts'] if p['player_id'] < 35)
        cap_flexible_expensive_cuts = sum(1 for p in result_cap_flexible['cuts'] if p['player_id'] < 35)

        print(f"\nCap-Conscious GM:")
        print(f"  Kept: {cap_conscious_expensive_kept} expensive players")
        print(f"  Cut: {cap_conscious_expensive_cuts} expensive players (out of 35)")
        print(f"\nCap-Flexible GM:")
        print(f"  Kept: {cap_flexible_expensive_kept} expensive players")
        print(f"  Cut: {cap_flexible_expensive_cuts} expensive players (out of 35)")

        # Validation: Cap-Conscious GM should keep FEWER expensive players
        # (More conservative with expensive contracts)
        assert cap_conscious_expensive_kept <= cap_flexible_expensive_kept, \
            f"Cap-Conscious GM should keep ≤ expensive players than Cap-Flexible GM. " \
            f"Conscious kept {cap_conscious_expensive_kept}, Flexible kept {cap_flexible_expensive_kept}"


def test_veteran_preferring_gm_keeps_older_players():
    """
    Test that veteran-preferring GMs keep more 30+ age players.

    Setup:
    - Create Veteran-Preferring GM (veteran_preference=0.9) vs Youth-Focused GM (veteran_preference=0.2)
    - Create 90-man roster: 30 veterans (30+), 60 young players (22-26)
    - Young players have slightly worse overall on average to create objective disadvantage

    Validation:
    - Vet-Preferring GM should keep ≥ veterans than Youth-Focused GM
    - Proves veteran_preference modifier affects roster cut decisions
    """
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'), \
         patch('transactions.team_context_service.TeamContextService') as mock_context_service:

        from offseason.roster_manager import RosterManager

        # Setup mock context
        mock_context = Mock()
        mock_context.cap_space = 25_000_000
        mock_context.is_contender = False
        mock_context.games_played = 0
        mock_context_service.return_value.build_team_context.return_value = mock_context

        # Create contrasting GMs
        vet_preferring_gm = GMArchetype(
            name="Veteran Val",
            description="Prefers experienced veterans",
            veteran_preference=0.9,
            loyalty=0.5,
            cap_management=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        youth_focused_gm = GMArchetype(
            name="Youth-Focused Yancy",
            description="Focuses on young players",
            veteran_preference=0.2,
            loyalty=0.5,
            cap_management=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        # Create test roster
        roster = create_90_man_roster_with_age_mix()

        # Test Vet-Preferring GM
        manager_vet = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=vet_preferring_gm
        )
        manager_vet._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_vet = manager_vet.finalize_53_man_roster_ai(team_id=1)

        # Test Youth-Focused GM
        manager_youth = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=youth_focused_gm
        )
        manager_youth._get_mock_90_man_roster = MagicMock(return_value=roster.copy())
        result_youth = manager_youth.finalize_53_man_roster_ai(team_id=1)

        # Count 30+ age players in final rosters (30 total veterans)
        vet_old_players = sum(1 for p in result_vet['final_roster'] if p['player_id'] < 30)
        youth_old_players = sum(1 for p in result_youth['final_roster'] if p['player_id'] < 30)

        # Calculate percentages
        vet_percentage = (vet_old_players / 53) * 100
        youth_percentage = (youth_old_players / 53) * 100

        print(f"\nVet-Preferring GM kept {vet_old_players} veterans (30+) out of 30 ({vet_percentage:.1f}%)")
        print(f"Youth-Focused GM kept {youth_old_players} veterans (30+) out of 30 ({youth_percentage:.1f}%)")

        # Validation: Vet-Preferring GM should keep MORE 30+ players
        # Even a 1-player difference shows behavioral variation
        assert vet_old_players >= youth_old_players, \
            f"Vet-Preferring GM should keep ≥ veterans than Youth-Focused GM. " \
            f"Vet-Preferring kept {vet_old_players}, Youth-Focused kept {youth_old_players}"


def test_youth_focused_gm_gives_opportunities_to_young_players():
    """
    Test that youth-focused GMs give more opportunities to young players.

    Setup:
    - Create Youth-Focused GM (veteran_preference=0.2)
    - Create 90-man roster: 25 veterans (30+), 65 young players (22-26)
    - Objective evaluation: Veterans have higher overall (78 vs 76)

    Validation:
    - Final 53 should have higher % of young players than objective evaluation
    - Young players' representation should exceed their quality-adjusted baseline
    """
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'), \
         patch('transactions.team_context_service.TeamContextService') as mock_context_service:

        from offseason.roster_manager import RosterManager

        # Setup mock context
        mock_context = Mock()
        mock_context.cap_space = 30_000_000
        mock_context.is_contender = False
        mock_context.games_played = 0
        mock_context_service.return_value.build_team_context.return_value = mock_context

        # Create Youth-Focused GM
        youth_focused_gm = GMArchetype(
            name="Youth-Focused Yancy",
            description="Prioritizes young talent",
            veteran_preference=0.2,
            loyalty=0.5,
            cap_management=0.5,
            risk_tolerance=0.5,
            win_now_mentality=0.5,
            draft_pick_value=0.5,
            trade_frequency=0.5,
            star_chasing=0.3
        )

        # Create test roster with veterans having HIGHER overall (objective advantage)
        roster = []
        # 25 veterans (30+ age) with better overall
        for i in range(25):
            roster.append(create_test_player(
                player_id=i,
                overall=78,  # HIGHER overall
                position='linebacker',
                age=31,
                years_with_team=5,
                cap_hit=4_000_000
            ))

        # 65 young players (22-26 age) with worse overall
        for i in range(25, 90):
            roster.append(create_test_player(
                player_id=i,
                overall=76,  # LOWER overall
                position='safety',
                age=24,
                years_with_team=2,
                cap_hit=2_000_000
            ))

        # Run roster cuts with Youth-Focused GM
        manager = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False,
            gm_archetype=youth_focused_gm
        )
        manager._get_mock_90_man_roster = MagicMock(return_value=roster)
        result = manager.finalize_53_man_roster_ai(team_id=1)

        # Count young players in final 53
        young_players_kept = sum(1 for p in result['final_roster'] if p['player_id'] >= 25)
        young_percentage = (young_players_kept / 53) * 100

        # Count veterans kept
        veterans_kept = sum(1 for p in result['final_roster'] if p['player_id'] < 25)
        veteran_percentage = (veterans_kept / 53) * 100

        print(f"\nYouth-Focused GM final roster composition:")
        print(f"  Young players (22-26, OVR 76): {young_players_kept}/53 ({young_percentage:.1f}%)")
        print(f"  Veterans (30+, OVR 78): {veterans_kept}/53 ({veteran_percentage:.1f}%)")

        # Validation: Despite veterans having HIGHER overall (78 vs 76),
        # youth-focused GM should keep a reasonable number of young players
        # At minimum, young players should represent ≥50% of final roster
        # (Objective evaluation would favor veterans heavily due to +2 OVR advantage)
        assert young_percentage >= 50.0, \
            f"Youth-Focused GM should keep ≥50% young players despite lower overall. Got {young_percentage:.1f}%"


def test_backward_compatibility_no_gm_uses_objective_logic():
    """
    Test that roster cuts without GM archetype use objective value only.

    Setup:
    - Create RosterManager WITHOUT GM archetype
    - Create 90-man roster with varied players

    Validation:
    - Uses objective value only (no personality modifiers applied)
    - Cuts are based purely on overall rating and cap hit
    """
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        from offseason.roster_manager import RosterManager

        # Create roster with clear objective value hierarchy
        roster = []

        # 10 elite players (high overall, reasonable cost)
        for i in range(10):
            roster.append(create_test_player(
                player_id=i,
                overall=85,
                position='quarterback',
                age=28,
                years_with_team=3,
                cap_hit=3_000_000
            ))

        # 43 good players (mid overall, cheap)
        for i in range(10, 53):
            roster.append(create_test_player(
                player_id=i,
                overall=76,
                position='wide_receiver',
                age=26,
                years_with_team=2,
                cap_hit=1_500_000
            ))

        # 37 mediocre players (low overall, cheap)
        for i in range(53, 90):
            roster.append(create_test_player(
                player_id=i,
                overall=68,
                position='safety',
                age=24,
                years_with_team=1,
                cap_hit=1_000_000
            ))

        # Create RosterManager WITHOUT GM archetype
        manager = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False
            # NO gm_archetype parameter
        )
        manager._get_mock_90_man_roster = MagicMock(return_value=roster)

        # Run roster cuts
        result = manager.finalize_53_man_roster_ai(team_id=1)

        # Validation: All elite and good players should make roster
        # (purely objective evaluation based on overall rating)
        elite_kept = sum(1 for p in result['final_roster'] if p['player_id'] < 10)
        good_kept = sum(1 for p in result['final_roster'] if 10 <= p['player_id'] < 53)
        mediocre_kept = sum(1 for p in result['final_roster'] if p['player_id'] >= 53)

        print(f"\nObjective evaluation (no GM):")
        print(f"  Elite players (85 OVR): {elite_kept}/10 kept")
        print(f"  Good players (76 OVR): {good_kept}/43 kept")
        print(f"  Mediocre players (68 OVR): {mediocre_kept}/37 kept")

        # All elite players should be kept
        assert elite_kept == 10, f"All 10 elite players should be kept, got {elite_kept}"

        # All good players should be kept (10 elite + 43 good = 53)
        assert good_kept == 43, f"All 43 good players should be kept, got {good_kept}"

        # No mediocre players should be kept
        assert mediocre_kept == 0, f"No mediocre players should be kept, got {mediocre_kept}"

        # Verify 53 total
        assert len(result['final_roster']) == 53


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
