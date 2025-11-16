"""
Draft Order Utility Functions

Converter functions for transforming data between different formats used
by draft-related APIs and services.

These utilities bridge the gap between:
- DatabaseAPI standings format → DraftOrderService TeamRecord format
- DraftOrderService DraftPickOrder → DraftOrderDatabaseAPI DraftPick format
"""

from typing import Dict, List, Any
from dataclasses import dataclass

# Import types from draft order service
from offseason.draft_order_service import TeamRecord

# Import types from draft order database API
from database.draft_order_database_api import DraftPick


def convert_standings_to_team_records(standings_dict: Dict[str, Any]) -> List[TeamRecord]:
    """
    Convert DatabaseAPI standings format to DraftOrderService TeamRecord format.

    The DatabaseAPI returns standings in a complex nested structure organized
    by divisions and conferences. DraftOrderService needs a simple flat list
    of TeamRecord objects for all 32 teams.

    Args:
        standings_dict: Result from DatabaseAPI.get_standings()
            Structure:
            {
                'divisions': {
                    'AFC East': [
                        {
                            'team': Team(...),
                            'standing': EnhancedTeamStanding(team_id=1, wins=11, losses=6, ...)
                        },
                        ...
                    ],
                    ...
                },
                'conferences': {...},
                'playoff_picture': {...}
            }

    Returns:
        List of TeamRecord objects, one for each of the 32 NFL teams.
        Each TeamRecord contains: team_id, wins, losses, ties, win_percentage

    Raises:
        ValueError: If standings_dict is invalid or missing required data

    Example:
        >>> from database.api import DatabaseAPI
        >>> db_api = DatabaseAPI("nfl.db")
        >>> standings = db_api.get_standings("my_dynasty", 2024, "regular_season")
        >>> team_records = convert_standings_to_team_records(standings)
        >>> print(f"Converted {len(team_records)} teams")
        Converted 32 teams
    """
    if not standings_dict or 'divisions' not in standings_dict:
        raise ValueError("Invalid standings_dict: missing 'divisions' key")

    team_records = []

    # Extract team records from divisions structure
    divisions = standings_dict['divisions']

    for division_name, division_teams in divisions.items():
        # division_teams is a list of dicts with 'team' and 'standing' keys
        for team_dict in division_teams:
            if 'standing' not in team_dict:
                raise ValueError(f"Missing 'standing' in team_dict for division {division_name}")

            standing = team_dict['standing']

            # Calculate win percentage
            total_games = standing.wins + standing.losses + standing.ties
            if total_games == 0:
                win_percentage = 0.0
            else:
                win_percentage = (standing.wins + 0.5 * standing.ties) / total_games

            # Create TeamRecord
            team_record = TeamRecord(
                team_id=standing.team_id,
                wins=standing.wins,
                losses=standing.losses,
                ties=standing.ties,
                win_percentage=win_percentage
            )

            team_records.append(team_record)

    # Validate we got all 32 teams
    if len(team_records) != 32:
        raise ValueError(
            f"Expected 32 team records, got {len(team_records)}. "
            f"Standings data may be incomplete."
        )

    return team_records


def convert_draft_pick_order_to_draft_pick(
    pick_order: 'DraftPickOrder',
    dynasty_id: str,
    season: int
) -> DraftPick:
    """
    Convert DraftOrderService output to DraftOrderDatabaseAPI input format.

    DraftOrderService calculates draft order and returns DraftPickOrder objects
    with draft position and team info. DraftOrderDatabaseAPI needs DraftPick
    objects with database-specific fields like dynasty_id, season, and trade info.

    Args:
        pick_order: DraftPickOrder from DraftOrderService.calculate_draft_order()
        dynasty_id: Dynasty identifier for database isolation
        season: Season year (e.g., 2025 for 2024 season draft)

    Returns:
        DraftPick ready to be saved to database

    Example:
        >>> from offseason.draft_order_service import DraftOrderService, TeamRecord
        >>> service = DraftOrderService("my_dynasty", 2025)
        >>> # ... calculate draft order ...
        >>> pick_orders = service.calculate_draft_order(standings, playoff_results)
        >>> db_picks = [
        ...     convert_draft_pick_order_to_draft_pick(po, "my_dynasty", 2025)
        ...     for po in pick_orders
        ... ]
        >>> # Now save db_picks to database
    """
    # DraftPickOrder has: round_number, pick_in_round, overall_pick, team_id,
    #                     original_team_id, reason, team_record, strength_of_schedule
    #
    # DraftPick needs: pick_id (auto), dynasty_id, season, round_number, pick_in_round,
    #                  overall_pick, original_team_id, current_team_id, player_id (None),
    #                  draft_class_id (None), is_executed (False), is_compensatory (False),
    #                  comp_round_end (False), acquired_via_trade (False), trade_date (None),
    #                  original_trade_id (None)

    return DraftPick(
        pick_id=None,  # Auto-generated by database
        dynasty_id=dynasty_id,
        season=season,
        round_number=pick_order.round_number,
        pick_in_round=pick_order.pick_in_round,
        overall_pick=pick_order.overall_pick,
        original_team_id=pick_order.original_team_id,
        current_team_id=pick_order.team_id,  # Same as original initially (no trades yet)
        player_id=None,  # Not yet drafted
        draft_class_id=None,  # Will be set when draft class is generated
        is_executed=False,  # Pick not yet made
        is_compensatory=False,  # Base picks only (compensatory picks not implemented yet)
        comp_round_end=False,  # N/A for base picks
        acquired_via_trade=False,  # Original pick (no trades yet)
        trade_date=None,  # N/A
        original_trade_id=None  # N/A
    )


def convert_all_draft_picks(
    pick_orders: List['DraftPickOrder'],
    dynasty_id: str,
    season: int
) -> List[DraftPick]:
    """
    Batch convert all draft picks from service format to database format.

    Convenience function that calls convert_draft_pick_order_to_draft_pick()
    for each pick in a list.

    Args:
        pick_orders: List of DraftPickOrder from DraftOrderService
        dynasty_id: Dynasty identifier
        season: Season year

    Returns:
        List of DraftPick ready to save to database (224 picks for 7 rounds)

    Example:
        >>> pick_orders = service.calculate_draft_order(standings, playoff_results)
        >>> db_picks = convert_all_draft_picks(pick_orders, "my_dynasty", 2025)
        >>> draft_api.save_draft_order(db_picks)  # Save to database
    """
    return [
        convert_draft_pick_order_to_draft_pick(pick_order, dynasty_id, season)
        for pick_order in pick_orders
    ]
