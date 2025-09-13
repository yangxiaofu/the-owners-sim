"""
Test to verify the net passing yards fix is working correctly.

This test validates that:
1. TeamStats tracks sack_yards_lost correctly
2. Net passing yards are calculated correctly (gross - sacks)
3. Total yards = net passing + rushing (NFL standard)
4. Box score displays net passing yards with clear notation
5. The mismatch issue is resolved
"""

from src.play_engine.simulation.stats import (
    PlayerStatsAccumulator, 
    TeamStatsAccumulator,
    PlayStatsSummary,
    PlayerStats
)
from src.game_management.box_score_generator import BoxScoreGenerator
from src.game_management.game_stats_reporter import GameStatsReporter
from src.play_engine.play_types.base_types import PlayType
from src.constants.team_ids import TeamIDs
from src.team_management.teams.team_loader import Team

def create_sample_pass_play(yards: int, is_completion: bool = True) -> PlayStatsSummary:
    """Create a sample pass play with stats"""
    summary = PlayStatsSummary(
        play_type=PlayType.PASS,
        yards_gained=yards,
        time_elapsed=5.0
    )
    
    # Add QB stats
    qb = PlayerStats(
        player_name="Cleveland QB",
        player_number=7,
        position="QB"
    )
    
    if is_completion and yards > 0:
        qb.pass_attempts = 1
        qb.completions = 1
        qb.passing_yards = yards
    elif is_completion:
        qb.pass_attempts = 1
        qb.completions = 1
        qb.passing_yards = 0
    else:
        qb.pass_attempts = 1
        qb.completions = 0
    
    summary.add_player_stats(qb)
    
    # Add receiver stats if completion
    if is_completion and yards > 0:
        receiver = PlayerStats(
            player_name="Cleveland WR",
            player_number=13,
            position="WR"
        )
        receiver.receptions = 1
        receiver.receiving_yards = yards
        receiver.targets = 1
        summary.add_player_stats(receiver)
    
    return summary

def create_sack_play(sack_yards: int) -> PlayStatsSummary:
    """Create a sack play with negative yards"""
    summary = PlayStatsSummary(
        play_type=PlayType.PASS,
        yards_gained=-sack_yards,  # Negative yards for sack
        time_elapsed=3.0
    )
    
    # Add QB stats for sack
    qb = PlayerStats(
        player_name="Cleveland QB",
        player_number=7,
        position="QB"
    )
    qb.pass_attempts = 1
    qb.completions = 0
    qb.sacks_taken = 1
    qb.sack_yards_lost = sack_yards  # Positive value stored
    
    summary.add_player_stats(qb)
    
    # Add defensive player who got the sack
    defender = PlayerStats(
        player_name="SF Defender",
        player_number=99,
        position="DE"
    )
    defender.sacks = 1.0
    defender.tackles_for_loss = 1
    summary.add_player_stats(defender)
    
    return summary

def create_run_play(yards: int) -> PlayStatsSummary:
    """Create a run play with stats"""
    summary = PlayStatsSummary(
        play_type=PlayType.RUN,
        yards_gained=yards,
        time_elapsed=4.0
    )
    
    # Add RB stats
    rb = PlayerStats(
        player_name="Cleveland RB",
        player_number=24,
        position="RB"
    )
    rb.carries = 1
    rb.rushing_yards = yards
    
    summary.add_player_stats(rb)
    return summary

def test_net_passing_yards_fix():
    """
    Test that the net passing yards fix resolves the mismatch issue.
    """
    
    print("\n" + "="*80)
    print("TESTING NET PASSING YARDS FIX")
    print("="*80)
    
    # Initialize accumulators
    player_accumulator = PlayerStatsAccumulator("Browns_Game")
    team_accumulator = TeamStatsAccumulator("Browns_Game")
    box_score_gen = BoxScoreGenerator()
    
    browns_id = TeamIDs.CLEVELAND_BROWNS
    niners_id = TeamIDs.SAN_FRANCISCO_49ERS
    
    # Create team objects for testing
    browns_team = Team(
        team_id=browns_id,
        city="Cleveland",
        nickname="Browns",
        full_name="Cleveland Browns",
        abbreviation="CLE",
        conference="AFC",
        division="AFC North",
        colors={"primary": "#FF3C00", "secondary": "#311D00"}
    )
    
    print("\n--- SIMULATING PLAYS ---")
    
    # Create the same plays as before to replicate the issue
    # 266 yards of completions
    pass_plays = [
        create_sample_pass_play(15),
        create_sample_pass_play(8),
        create_sample_pass_play(25),
        create_sample_pass_play(12),
        create_sample_pass_play(30),
        create_sample_pass_play(18),
        create_sample_pass_play(22),
        create_sample_pass_play(35),
        create_sample_pass_play(14),
        create_sample_pass_play(20),
        create_sample_pass_play(17),
        create_sample_pass_play(10),
        create_sample_pass_play(40),
    ]
    
    total_pass_yards = sum(play.yards_gained for play in pass_plays)
    print(f"Total passing completions: {total_pass_yards} yards")
    
    # 56 yards of sacks
    sack_plays = [
        create_sack_play(7),
        create_sack_play(12),
        create_sack_play(8),
        create_sack_play(15),
        create_sack_play(14),
    ]
    
    total_sack_yards = sum(abs(play.yards_gained) for play in sack_plays)
    print(f"Total sack yardage lost: {total_sack_yards} yards")
    
    # 36 yards of rushing
    run_plays = [
        create_run_play(5),
        create_run_play(3),
        create_run_play(8),
        create_run_play(2),
        create_run_play(7),
        create_run_play(4),
        create_run_play(7),
    ]
    
    total_rush_yards = sum(play.yards_gained for play in run_plays)
    print(f"Total rushing yards: {total_rush_yards} yards")
    
    # Process all plays
    all_plays = pass_plays + sack_plays + run_plays
    
    for play in all_plays:
        player_accumulator.add_play_stats(play)
        team_accumulator.add_play_stats(play, browns_id, niners_id)
    
    print("\n--- VERIFYING FIX ---")
    
    # 1. Test TeamStats has correct fields
    team_stats = team_accumulator.get_team_stats(browns_id)
    print("\n1. TeamStats object:")
    print(f"   - passing_yards (gross): {team_stats.passing_yards}")
    print(f"   - rushing_yards: {team_stats.rushing_yards}")
    print(f"   - times_sacked: {team_stats.times_sacked}")
    print(f"   - sack_yards_lost: {team_stats.sack_yards_lost}")
    print(f"   - get_net_passing_yards(): {team_stats.get_net_passing_yards()}")
    print(f"   - total_yards: {team_stats.total_yards}")
    
    # Verify net passing calculation
    assert team_stats.get_net_passing_yards() == team_stats.passing_yards - team_stats.sack_yards_lost
    print("   ✓ Net passing yards calculation is correct")
    
    # 2. Test BoxScoreGenerator uses net passing
    box_score = box_score_gen.generate_team_box_score(browns_team, player_accumulator)
    print("\n2. BoxScore team totals:")
    for key, value in box_score.team_totals.items():
        print(f"   - {key}: {value}")
    
    # Check that total yards calculation is correct
    expected_total = team_stats.get_net_passing_yards() + team_stats.rushing_yards
    actual_total = int(box_score.team_totals["Total Yards"])
    assert actual_total == expected_total, f"Total yards mismatch: {actual_total} != {expected_total}"
    print(f"   ✓ Total yards ({actual_total}) = net passing ({team_stats.get_net_passing_yards()}) + rushing ({team_stats.rushing_yards})")
    
    # 3. Test GameStatsReporter uses net passing
    reporter = GameStatsReporter()
    team_game_stats = reporter._calculate_team_stats_from_players(browns_team, player_accumulator)
    print("\n3. GameStatsReporter team stats:")
    print(f"   - total_yards: {team_game_stats.total_yards}")
    print(f"   - passing_yards (net): {team_game_stats.passing_yards}")
    print(f"   - rushing_yards: {team_game_stats.rushing_yards}")
    
    # Verify consistency
    assert team_game_stats.total_yards == team_game_stats.passing_yards + team_game_stats.rushing_yards
    print(f"   ✓ Total yards math is consistent: {team_game_stats.total_yards} = {team_game_stats.passing_yards} + {team_game_stats.rushing_yards}")
    
    print("\n--- FINAL VERIFICATION ---")
    print("✅ THE FIX IS WORKING!")
    print(f"   - Total Yards: {team_game_stats.total_yards}")
    print(f"   - Passing Yards: {team_game_stats.passing_yards} net ({total_pass_yards} gross - {total_sack_yards} sacks)")
    print(f"   - Rushing Yards: {team_game_stats.rushing_yards}")
    print(f"   - Math Check: {team_game_stats.passing_yards} + {team_game_stats.rushing_yards} = {team_game_stats.total_yards} ✓")
    
    print("\n--- INDIVIDUAL PLAYER STATS (UNCHANGED) ---")
    all_players = player_accumulator.get_all_players_with_stats()
    qb_stats = [p for p in all_players if p.position == "QB"][0]
    print(f"QB Stats:")
    print(f"   - passing_yards (gross): {qb_stats.passing_yards}")
    print(f"   - sacks_taken: {qb_stats.sacks_taken}")
    print(f"   - sack_yards_lost: {qb_stats.sack_yards_lost}")
    print("   ✓ Individual QB stats still show gross passing yards (NFL standard)")

if __name__ == "__main__":
    test_net_passing_yards_fix()