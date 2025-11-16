"""
Draft Order Service

Calculates NFL draft order after the Super Bowl based on regular season records,
playoff results, and strength of schedule tiebreakers.

NFL Draft Order Rules:
1. Picks 1-18: Non-playoff teams (worst → best by record, SOS tiebreaker)
2. Picks 19-24: Wild Card Round losers (worst → best by record, SOS tiebreaker)
3. Picks 25-28: Divisional Round losers (worst → best by record, SOS tiebreaker)
4. Picks 29-30: Conference Championship losers (worst → best by record, SOS tiebreaker)
5. Pick 31: Super Bowl loser
6. Pick 32: Super Bowl winner
7. Rounds 2-7: Same order as Round 1 (224 base picks total, compensatory picks not yet implemented)
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class TeamRecord:
    """Team's regular season record"""
    team_id: int
    wins: int
    losses: int
    ties: int
    win_percentage: float

    def __str__(self) -> str:
        """String representation of record (e.g., '11-6-0')"""
        return f"{self.wins}-{self.losses}-{self.ties}"


@dataclass
class DraftPickOrder:
    """Single draft pick in order"""
    round_number: int
    pick_in_round: int
    overall_pick: int
    team_id: int
    original_team_id: int  # Same as team_id initially (for trades)
    reason: str  # e.g., "non_playoff", "wild_card_loss", "super_bowl_winner"
    team_record: str  # e.g., "4-13-0"
    strength_of_schedule: float

    def __str__(self) -> str:
        """String representation of draft pick"""
        return (f"Round {self.round_number}, Pick {self.pick_in_round} "
                f"(#{self.overall_pick} overall): Team {self.team_id} - "
                f"{self.reason} ({self.team_record}, SOS: {self.strength_of_schedule:.3f})")


class DraftOrderService:
    """
    Service for calculating NFL draft order based on regular season records
    and playoff results.
    """

    # NFL draft has 7 rounds with 32 picks each
    NUM_ROUNDS = 7
    PICKS_PER_ROUND = 32
    TOTAL_PICKS = NUM_ROUNDS * PICKS_PER_ROUND  # 224 (base picks only, compensatory picks not yet implemented)

    # Playoff team counts
    NON_PLAYOFF_TEAMS = 18
    WILD_CARD_LOSERS = 6
    DIVISIONAL_LOSERS = 4
    CONFERENCE_LOSERS = 2
    SUPER_BOWL_LOSER = 1
    SUPER_BOWL_WINNER = 1

    def __init__(self, dynasty_id: str, season_year: int):
        """
        Initialize draft order service.

        Args:
            dynasty_id: Dynasty identifier for database queries
            season_year: Draft year (e.g., 2025 for 2024 season)
        """
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self._sos_cache: Dict[int, float] = {}  # Cache SOS calculations

        logger.info(f"Initialized DraftOrderService for dynasty '{dynasty_id}', "
                   f"draft year {season_year}")

    def calculate_draft_order(
        self,
        standings: List[TeamRecord],
        playoff_results: Dict[str, Any]
    ) -> List[DraftPickOrder]:
        """
        Calculate complete 7-round draft order (262 picks).

        Args:
            standings: All 32 teams' regular season records
            playoff_results: Dict with keys:
                - 'wild_card_losers': List[team_id] (6 teams)
                - 'divisional_losers': List[team_id] (4 teams)
                - 'conference_losers': List[team_id] (2 teams)
                - 'super_bowl_loser': int (team_id)
                - 'super_bowl_winner': int (team_id)

        Returns:
            List of 224 DraftPickOrder objects (7 rounds × 32 base picks, compensatory picks not yet implemented)

        Raises:
            ValueError: If inputs are invalid (wrong team counts, missing data)
        """
        logger.info("Calculating draft order...")

        # Validate inputs
        self._validate_inputs(standings, playoff_results)

        # Calculate Round 1 order (this determines all subsequent rounds)
        round_1_order = self._calculate_round_1_order(standings, playoff_results)

        # Generate all 7 rounds using Round 1 order
        all_picks = self._generate_all_rounds(round_1_order)

        logger.info(f"Draft order calculation complete: {len(all_picks)} total picks")
        return all_picks

    def calculate_strength_of_schedule(
        self,
        team_id: int,
        all_standings: List[TeamRecord],
        schedule: Optional[List[int]] = None
    ) -> float:
        """
        Calculate strength of schedule for a team.

        SOS = average win% of all opponents faced in regular season

        Args:
            team_id: Team to calculate SOS for
            all_standings: All teams' records (to look up opponent win%)
            schedule: Optional list of opponent team_ids. If None, must be provided
                     via external call (database query would go here in production)

        Returns:
            Float between 0.0 and 1.0 (average opponent win%)

        Raises:
            ValueError: If schedule is None or empty
        """
        # Check cache first
        if team_id in self._sos_cache:
            return self._sos_cache[team_id]

        if schedule is None or len(schedule) == 0:
            raise ValueError(f"Schedule required for team {team_id} to calculate SOS")

        # Build lookup dict for team records
        team_records = {rec.team_id: rec for rec in all_standings}

        # Calculate average opponent win percentage
        opponent_win_percentages = []
        for opponent_id in schedule:
            if opponent_id in team_records:
                opponent_win_percentages.append(team_records[opponent_id].win_percentage)
            else:
                logger.warning(f"Opponent {opponent_id} not found in standings for team {team_id}")

        if not opponent_win_percentages:
            logger.warning(f"No valid opponents found for team {team_id}, defaulting SOS to 0.500")
            sos = 0.500
        else:
            sos = sum(opponent_win_percentages) / len(opponent_win_percentages)

        # Cache the result
        self._sos_cache[team_id] = sos

        logger.debug(f"Team {team_id} SOS: {sos:.3f} (based on {len(opponent_win_percentages)} opponents)")
        return sos

    def _validate_inputs(
        self,
        standings: List[TeamRecord],
        playoff_results: Dict[str, Any]
    ) -> None:
        """
        Validate inputs for draft order calculation.

        Args:
            standings: All team records
            playoff_results: Playoff results dict

        Raises:
            ValueError: If inputs are invalid
        """
        # Check standings
        if len(standings) != 32:
            raise ValueError(f"Expected 32 team records, got {len(standings)}")

        # Check playoff results structure
        required_keys = ['wild_card_losers', 'divisional_losers', 'conference_losers',
                        'super_bowl_loser', 'super_bowl_winner']
        missing_keys = [key for key in required_keys if key not in playoff_results]
        if missing_keys:
            raise ValueError(f"Missing required playoff result keys: {missing_keys}")

        # Validate playoff team counts
        if len(playoff_results['wild_card_losers']) != self.WILD_CARD_LOSERS:
            raise ValueError(f"Expected {self.WILD_CARD_LOSERS} wild card losers, "
                           f"got {len(playoff_results['wild_card_losers'])}")

        if len(playoff_results['divisional_losers']) != self.DIVISIONAL_LOSERS:
            raise ValueError(f"Expected {self.DIVISIONAL_LOSERS} divisional losers, "
                           f"got {len(playoff_results['divisional_losers'])}")

        if len(playoff_results['conference_losers']) != self.CONFERENCE_LOSERS:
            raise ValueError(f"Expected {self.CONFERENCE_LOSERS} conference losers, "
                           f"got {len(playoff_results['conference_losers'])}")

        # Validate Super Bowl teams are integers
        if not isinstance(playoff_results['super_bowl_loser'], int):
            raise ValueError("super_bowl_loser must be an integer team_id")

        if not isinstance(playoff_results['super_bowl_winner'], int):
            raise ValueError("super_bowl_winner must be an integer team_id")

        # Check for duplicate teams across playoff categories
        all_playoff_teams = (
            playoff_results['wild_card_losers'] +
            playoff_results['divisional_losers'] +
            playoff_results['conference_losers'] +
            [playoff_results['super_bowl_loser']] +
            [playoff_results['super_bowl_winner']]
        )

        if len(all_playoff_teams) != len(set(all_playoff_teams)):
            raise ValueError("Duplicate teams found in playoff results")

        # Should have exactly 14 playoff teams total
        if len(all_playoff_teams) != 14:
            raise ValueError(f"Expected 14 playoff teams total, got {len(all_playoff_teams)}")

        logger.debug("Input validation passed")

    def _calculate_round_1_order(
        self,
        standings: List[TeamRecord],
        playoff_results: Dict[str, Any]
    ) -> List[DraftPickOrder]:
        """
        Calculate Round 1 draft order (picks 1-32).

        Args:
            standings: All team records
            playoff_results: Playoff results dict

        Returns:
            List of 32 DraftPickOrder objects for Round 1
        """
        round_1_picks = []
        pick_number = 1

        # Identify playoff teams
        playoff_team_ids = set(
            playoff_results['wild_card_losers'] +
            playoff_results['divisional_losers'] +
            playoff_results['conference_losers'] +
            [playoff_results['super_bowl_loser']] +
            [playoff_results['super_bowl_winner']]
        )

        # 1. Picks 1-18: Non-playoff teams (worst → best)
        non_playoff_teams = [rec.team_id for rec in standings if rec.team_id not in playoff_team_ids]
        non_playoff_sorted = self._sort_teams_by_record(non_playoff_teams, standings, reverse=False)

        for team_id in non_playoff_sorted:
            team_record = self._get_team_record(team_id, standings)
            round_1_picks.append(DraftPickOrder(
                round_number=1,
                pick_in_round=pick_number,
                overall_pick=pick_number,
                team_id=team_id,
                original_team_id=team_id,
                reason="non_playoff",
                team_record=str(team_record),
                strength_of_schedule=self._sos_cache.get(team_id, 0.500)
            ))
            pick_number += 1

        # 2. Picks 19-24: Wild Card Round losers (worst → best)
        wc_sorted = self._sort_teams_by_record(playoff_results['wild_card_losers'], standings, reverse=False)
        for team_id in wc_sorted:
            team_record = self._get_team_record(team_id, standings)
            round_1_picks.append(DraftPickOrder(
                round_number=1,
                pick_in_round=pick_number,
                overall_pick=pick_number,
                team_id=team_id,
                original_team_id=team_id,
                reason="wild_card_loss",
                team_record=str(team_record),
                strength_of_schedule=self._sos_cache.get(team_id, 0.500)
            ))
            pick_number += 1

        # 3. Picks 25-28: Divisional Round losers (worst → best)
        div_sorted = self._sort_teams_by_record(playoff_results['divisional_losers'], standings, reverse=False)
        for team_id in div_sorted:
            team_record = self._get_team_record(team_id, standings)
            round_1_picks.append(DraftPickOrder(
                round_number=1,
                pick_in_round=pick_number,
                overall_pick=pick_number,
                team_id=team_id,
                original_team_id=team_id,
                reason="divisional_loss",
                team_record=str(team_record),
                strength_of_schedule=self._sos_cache.get(team_id, 0.500)
            ))
            pick_number += 1

        # 4. Picks 29-30: Conference Championship losers (worst → best)
        conf_sorted = self._sort_teams_by_record(playoff_results['conference_losers'], standings, reverse=False)
        for team_id in conf_sorted:
            team_record = self._get_team_record(team_id, standings)
            round_1_picks.append(DraftPickOrder(
                round_number=1,
                pick_in_round=pick_number,
                overall_pick=pick_number,
                team_id=team_id,
                original_team_id=team_id,
                reason="conference_loss",
                team_record=str(team_record),
                strength_of_schedule=self._sos_cache.get(team_id, 0.500)
            ))
            pick_number += 1

        # 5. Pick 31: Super Bowl loser
        sb_loser_id = playoff_results['super_bowl_loser']
        sb_loser_record = self._get_team_record(sb_loser_id, standings)
        round_1_picks.append(DraftPickOrder(
            round_number=1,
            pick_in_round=31,
            overall_pick=31,
            team_id=sb_loser_id,
            original_team_id=sb_loser_id,
            reason="super_bowl_loss",
            team_record=str(sb_loser_record),
            strength_of_schedule=self._sos_cache.get(sb_loser_id, 0.500)
        ))

        # 6. Pick 32: Super Bowl winner
        sb_winner_id = playoff_results['super_bowl_winner']
        sb_winner_record = self._get_team_record(sb_winner_id, standings)
        round_1_picks.append(DraftPickOrder(
            round_number=1,
            pick_in_round=32,
            overall_pick=32,
            team_id=sb_winner_id,
            original_team_id=sb_winner_id,
            reason="super_bowl_win",
            team_record=str(sb_winner_record),
            strength_of_schedule=self._sos_cache.get(sb_winner_id, 0.500)
        ))

        logger.info(f"Round 1 order calculated: {len(round_1_picks)} picks")
        return round_1_picks

    def _generate_all_rounds(self, round_1_order: List[DraftPickOrder]) -> List[DraftPickOrder]:
        """
        Generate all 7 rounds using Round 1 order.

        Args:
            round_1_order: The 32 picks from Round 1

        Returns:
            List of 262 DraftPickOrder objects (7 rounds × 32 picks)
        """
        all_picks = []
        overall_pick = 1

        for round_num in range(1, self.NUM_ROUNDS + 1):
            for pick_in_round in range(1, self.PICKS_PER_ROUND + 1):
                # Use Round 1 order to determine team for this pick
                round_1_pick = round_1_order[pick_in_round - 1]

                pick = DraftPickOrder(
                    round_number=round_num,
                    pick_in_round=pick_in_round,
                    overall_pick=overall_pick,
                    team_id=round_1_pick.team_id,
                    original_team_id=round_1_pick.original_team_id,
                    reason=round_1_pick.reason,
                    team_record=round_1_pick.team_record,
                    strength_of_schedule=round_1_pick.strength_of_schedule
                )
                all_picks.append(pick)
                overall_pick += 1

        logger.debug(f"Generated {len(all_picks)} total picks across {self.NUM_ROUNDS} rounds")
        return all_picks

    def _sort_teams_by_record(
        self,
        team_ids: List[int],
        standings: List[TeamRecord],
        reverse: bool = False
    ) -> List[int]:
        """
        Sort teams by record, using SOS for tiebreakers.

        Sorting logic:
        - Primary: Win percentage (lower/higher depending on reverse)
        - Tiebreaker: Strength of schedule (easier schedule drafts first for non-reverse)

        Args:
            team_ids: Teams to sort
            standings: All team records
            reverse: If True, sort best → worst. If False, sort worst → best.

        Returns:
            Sorted list of team_ids
        """
        # Build lookup dicts
        team_records = {rec.team_id: rec for rec in standings}

        # Sort teams
        def sort_key(team_id: int):
            record = team_records[team_id]
            sos = self._sos_cache.get(team_id, 0.500)

            if reverse:
                # Best → worst: higher win% first, then harder SOS breaks ties
                return (-record.win_percentage, -sos)
            else:
                # Worst → best: lower win% first, then easier SOS breaks ties
                return (record.win_percentage, sos)

        sorted_teams = sorted(team_ids, key=sort_key)

        logger.debug(f"Sorted {len(sorted_teams)} teams by record "
                    f"({'best→worst' if reverse else 'worst→best'})")
        return sorted_teams

    def _get_team_record(self, team_id: int, standings: List[TeamRecord]) -> TeamRecord:
        """
        Get team record from standings list.

        Args:
            team_id: Team to find
            standings: All team records

        Returns:
            TeamRecord for the team

        Raises:
            ValueError: If team not found
        """
        for record in standings:
            if record.team_id == team_id:
                return record
        raise ValueError(f"Team {team_id} not found in standings")
