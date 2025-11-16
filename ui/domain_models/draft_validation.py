"""
Draft Validation Helpers

Provides validation utilities for draft order calculation and playoff results.
These helpers ensure data consistency and completeness before draft order display.
"""

from typing import Dict, List, Tuple, Any


def validate_playoff_results(playoff_results: Dict) -> Tuple[bool, List[str]]:
    """
    Validate playoff results are complete and consistent.

    Checks:
    - All required keys present (wild_card_losers, divisional_losers, etc.)
    - Correct team counts in each category
    - No duplicate teams across categories
    - Team IDs are valid integers

    Args:
        playoff_results: Dict with playoff results structure

    Returns:
        Tuple of (is_complete, errors)
        - is_complete: True if all validations pass
        - errors: List of error messages (empty if valid)

    Example:
        >>> playoff_results = {
        ...     'wild_card_losers': [1, 2, 3, 4, 5, 6],
        ...     'divisional_losers': [7, 8, 9, 10],
        ...     'conference_losers': [11, 12],
        ...     'super_bowl_loser': 13,
        ...     'super_bowl_winner': 14
        ... }
        >>> is_complete, errors = validate_playoff_results(playoff_results)
        >>> print(is_complete)  # True
        >>> print(errors)  # []
    """
    errors = []

    # Check required keys
    required_keys = [
        'wild_card_losers',
        'divisional_losers',
        'conference_losers',
        'super_bowl_loser',
        'super_bowl_winner'
    ]
    missing_keys = [key for key in required_keys if key not in playoff_results]
    if missing_keys:
        errors.append(f"Missing required playoff result keys: {', '.join(missing_keys)}")
        return False, errors  # Can't validate further without required keys

    # Check wild card losers
    wc_losers = playoff_results.get('wild_card_losers', [])
    if len(wc_losers) != 6:
        errors.append(f"Expected 6 wild card losers, got {len(wc_losers)}")

    # Check divisional losers
    div_losers = playoff_results.get('divisional_losers', [])
    if len(div_losers) != 4:
        errors.append(f"Expected 4 divisional losers, got {len(div_losers)}")

    # Check conference losers
    conf_losers = playoff_results.get('conference_losers', [])
    if len(conf_losers) != 2:
        errors.append(f"Expected 2 conference losers, got {len(conf_losers)}")

    # Check Super Bowl teams are integers
    sb_loser = playoff_results.get('super_bowl_loser')
    if not isinstance(sb_loser, int):
        errors.append(f"super_bowl_loser must be an integer, got {type(sb_loser).__name__}")

    sb_winner = playoff_results.get('super_bowl_winner')
    if not isinstance(sb_winner, int):
        errors.append(f"super_bowl_winner must be an integer, got {type(sb_winner).__name__}")

    # Check for duplicate teams
    all_playoff_teams = (
        wc_losers +
        div_losers +
        conf_losers +
        ([sb_loser] if isinstance(sb_loser, int) else []) +
        ([sb_winner] if isinstance(sb_winner, int) else [])
    )

    if len(all_playoff_teams) != len(set(all_playoff_teams)):
        errors.append("Duplicate teams found in playoff results")

    # Check total playoff team count
    if len(all_playoff_teams) != 14:
        errors.append(f"Expected 14 total playoff teams, got {len(all_playoff_teams)}")

    is_complete = len(errors) == 0
    return is_complete, errors


def validate_draft_order(picks: List[Dict]) -> List[str]:
    """
    Validate draft order is complete and correct.

    Checks:
    - Total pick count (224 for 7 rounds)
    - Overall pick sequence (1, 2, 3, ..., 224)
    - Round numbers (1-7)
    - Picks per round (32)
    - All teams represented (32 unique team_ids)
    - Required fields present

    Args:
        picks: List of pick dicts from DraftDataModel.get_draft_order()

    Returns:
        List of validation errors (empty if valid)

    Example:
        >>> picks = model.get_draft_order()
        >>> errors = validate_draft_order(picks)
        >>> if errors:
        ...     print(f"Draft order has {len(errors)} errors:")
        ...     for error in errors:
        ...         print(f"  - {error}")
    """
    errors = []

    # Check total pick count
    if len(picks) != 224:
        errors.append(f"Expected 224 picks (7 rounds × 32 picks), got {len(picks)}")
        # If pick count is wrong, many other validations will fail
        # Still run them to provide comprehensive feedback

    # Check overall pick sequence
    for i, pick in enumerate(picks):
        expected_overall = i + 1
        actual_overall = pick.get('overall_pick')
        if actual_overall != expected_overall:
            errors.append(
                f"Pick {i+1}: Expected overall_pick={expected_overall}, "
                f"got {actual_overall}"
            )

    # Check round numbers and picks per round
    picks_by_round = {}
    for pick in picks:
        round_num = pick.get('round_number')
        if round_num is None:
            errors.append(f"Pick {pick.get('overall_pick')}: Missing round_number")
            continue

        if round_num < 1 or round_num > 7:
            errors.append(
                f"Pick {pick.get('overall_pick')}: Invalid round_number={round_num} "
                f"(must be 1-7)"
            )

        # Track picks per round
        if round_num not in picks_by_round:
            picks_by_round[round_num] = []
        picks_by_round[round_num].append(pick)

    # Validate picks per round
    for round_num in range(1, 8):
        round_picks = picks_by_round.get(round_num, [])
        if len(round_picks) != 32:
            errors.append(
                f"Round {round_num}: Expected 32 picks, got {len(round_picks)}"
            )

    # Check all teams represented
    team_ids = set()
    for pick in picks:
        team_id = pick.get('team_id')
        if team_id is None:
            errors.append(f"Pick {pick.get('overall_pick')}: Missing team_id")
        elif not isinstance(team_id, int):
            errors.append(
                f"Pick {pick.get('overall_pick')}: team_id must be integer, "
                f"got {type(team_id).__name__}"
            )
        else:
            team_ids.add(team_id)

    if len(team_ids) != 32:
        errors.append(
            f"Expected 32 unique teams, got {len(team_ids)} teams"
        )

    # Check required fields
    required_fields = [
        'overall_pick',
        'round_number',
        'pick_in_round',
        'team_id',
        'team_record',
        'reason',
        'sos'
    ]

    for i, pick in enumerate(picks):
        missing_fields = [field for field in required_fields if field not in pick]
        if missing_fields:
            errors.append(
                f"Pick {i+1}: Missing required fields: {', '.join(missing_fields)}"
            )
            # Only report first 5 picks with missing fields to avoid spam
            if i >= 5:
                errors.append(f"... (suppressing further missing field errors)")
                break

    return errors


def validate_standings(standings: List[Dict]) -> List[str]:
    """
    Validate standings data structure.

    Checks:
    - Team count (32 teams)
    - Required fields present
    - Win percentage calculations
    - No duplicate teams

    Args:
        standings: List of team standing dicts

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check team count
    if len(standings) != 32:
        errors.append(f"Expected 32 teams in standings, got {len(standings)}")

    # Check for duplicates
    team_ids = [s.get('team_id') for s in standings]
    if len(team_ids) != len(set(team_ids)):
        errors.append("Duplicate teams found in standings")

    # Check required fields
    required_fields = ['team_id', 'wins', 'losses', 'ties', 'win_percentage']
    for i, standing in enumerate(standings):
        missing_fields = [field for field in required_fields if field not in standing]
        if missing_fields:
            errors.append(
                f"Team {standing.get('team_id', 'unknown')}: "
                f"Missing fields: {', '.join(missing_fields)}"
            )

        # Validate win percentage calculation (if all fields present)
        if not missing_fields:
            wins = standing.get('wins', 0)
            losses = standing.get('losses', 0)
            ties = standing.get('ties', 0)
            win_pct = standing.get('win_percentage', 0.0)

            total_games = wins + losses + ties
            if total_games > 0:
                expected_pct = (wins + 0.5 * ties) / total_games
                if abs(win_pct - expected_pct) > 0.001:  # Allow small floating point error
                    errors.append(
                        f"Team {standing.get('team_id')}: Win percentage mismatch. "
                        f"Expected {expected_pct:.3f}, got {win_pct:.3f}"
                    )

    return errors
