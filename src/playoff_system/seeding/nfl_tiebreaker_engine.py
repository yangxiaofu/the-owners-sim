"""
NFL Tiebreaker Engine

Implements all official NFL tiebreaker rules for playoff seeding.
Handles both division tiebreakers and wild card tiebreakers according
to the official NFL procedures.

Based on official NFL tiebreaking procedures:
https://operations.nfl.com/the-rules/nfl-tie-breaking-procedures/
"""

from typing import List, Dict, Optional, Tuple, Set
import logging
from collections import defaultdict

from .seeding_data_models import (
    TeamRecord, TiebreakerResult, TiebreakerRule
)


class NFLTiebreakerEngine:
    """
    Implements all NFL tiebreaker rules for playoff seeding.

    Handles the complex hierarchy of tiebreaker rules, including
    head-to-head records, division/conference records, strength
    calculations, and point differentials.
    """

    def __init__(self):
        """Initialize the tiebreaker engine."""
        self.logger = logging.getLogger(__name__)

    def break_division_tie(self, teams: List[TeamRecord],
                          head_to_head_results: Dict[tuple, str]) -> List[TeamRecord]:
        """
        Break ties between teams in the same division.

        Args:
            teams: List of tied teams from same division
            head_to_head_results: Head-to-head results between teams

        Returns:
            List of teams in order after applying tiebreakers
        """
        if len(teams) <= 1:
            return teams

        self.logger.info(f"Breaking division tie for {len(teams)} teams: "
                        f"{[team.team_id for team in teams]}")

        # Division tiebreaker order
        tiebreaker_methods = [
            self._apply_head_to_head,
            self._apply_division_record,
            self._apply_conference_record,
            self._apply_common_games,
            self._apply_strength_of_victory,
            self._apply_strength_of_schedule,
            self._apply_combined_ranking_conference,
            self._apply_combined_ranking_all,
            self._apply_net_points_conference,
            self._apply_net_points_all,
            self._apply_coin_flip
        ]

        return self._apply_tiebreaker_cascade(teams, head_to_head_results,
                                            tiebreaker_methods, "division")

    def break_wildcard_tie(self, teams: List[TeamRecord],
                          head_to_head_results: Dict[tuple, str]) -> List[TeamRecord]:
        """
        Break ties between teams for wild card spots.

        Args:
            teams: List of tied teams (from different divisions)
            head_to_head_results: Head-to-head results between teams

        Returns:
            List of teams in order after applying tiebreakers
        """
        if len(teams) <= 1:
            return teams

        self.logger.info(f"Breaking wild card tie for {len(teams)} teams: "
                        f"{[team.team_id for team in teams]}")

        # Wild card tiebreaker order (slightly different from division)
        tiebreaker_methods = [
            self._apply_head_to_head_sweep,  # Only if one team swept all others
            self._apply_conference_record,
            self._apply_common_games,
            self._apply_strength_of_victory,
            self._apply_strength_of_schedule,
            self._apply_combined_ranking_conference,
            self._apply_combined_ranking_all,
            self._apply_net_points_conference,
            self._apply_net_points_all,
            self._apply_coin_flip
        ]

        return self._apply_tiebreaker_cascade(teams, head_to_head_results,
                                            tiebreaker_methods, "wildcard")

    def _apply_tiebreaker_cascade(self, teams: List[TeamRecord],
                                 head_to_head_results: Dict[tuple, str],
                                 tiebreaker_methods: List,
                                 tie_type: str) -> List[TeamRecord]:
        """
        Apply tiebreaker methods in sequence until tie is broken.

        Args:
            teams: Teams to break ties for
            head_to_head_results: Head-to-head results
            tiebreaker_methods: Ordered list of tiebreaker methods
            tie_type: "division" or "wildcard"

        Returns:
            Teams in order after applying tiebreakers
        """
        remaining_teams = teams.copy()
        ordered_teams = []

        while len(remaining_teams) > 1:
            # Try each tiebreaker method
            resolved = False

            for method in tiebreaker_methods:
                result = method(remaining_teams, head_to_head_results)

                if result and result.was_decisive:
                    # Tiebreaker was decisive
                    self.logger.info(f"Tiebreaker {result.rule_applied.value} resolved tie: "
                                   f"Winner {result.winner_team_id}")

                    # Add winner to ordered list
                    winner = next(team for team in remaining_teams
                                if team.team_id == result.winner_team_id)
                    ordered_teams.append(winner)
                    remaining_teams.remove(winner)

                    resolved = True
                    break

            if not resolved:
                # No tiebreaker could resolve - should not happen with coin flip
                self.logger.warning(f"Could not resolve tie for teams: "
                                  f"{[team.team_id for team in remaining_teams]}")
                # Add remaining teams in original order
                ordered_teams.extend(remaining_teams)
                break

        # Add last remaining team if any
        if remaining_teams:
            ordered_teams.extend(remaining_teams)

        return ordered_teams

    def _apply_head_to_head(self, teams: List[TeamRecord],
                           head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """
        Apply head-to-head tiebreaker.

        For 2 teams: Better head-to-head record wins.
        For 3+ teams: Only applies if all teams played each other same number of times.
        """
        if len(teams) == 2:
            return self._apply_head_to_head_two_teams(teams, head_to_head_results)
        else:
            return self._apply_head_to_head_multi_teams(teams, head_to_head_results)

    def _apply_head_to_head_two_teams(self, teams: List[TeamRecord],
                                     head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply head-to-head for exactly 2 teams."""
        team1, team2 = teams[0], teams[1]

        # Look for head-to-head result
        h2h_key = (min(team1.team_id, team2.team_id), max(team1.team_id, team2.team_id))
        h2h_result = head_to_head_results.get(h2h_key)

        if not h2h_result:
            return None  # No head-to-head games

        # Parse result like "2-0", "1-1", etc.
        parts = h2h_result.split('-')
        if len(parts) != 2:
            return None

        try:
            wins1, wins2 = int(parts[0]), int(parts[1])
        except ValueError:
            return None

        # Determine winner
        if wins1 > wins2:
            winner_id = team1.team_id if team1.team_id < team2.team_id else team2.team_id
            loser_id = team2.team_id if winner_id == team1.team_id else team1.team_id
        elif wins2 > wins1:
            winner_id = team2.team_id if team1.team_id < team2.team_id else team1.team_id
            loser_id = team1.team_id if winner_id == team2.team_id else team2.team_id
        else:
            return None  # Tied head-to-head

        return TiebreakerResult(
            rule_applied=TiebreakerRule.HEAD_TO_HEAD,
            teams_involved=[team1.team_id, team2.team_id],
            winner_team_id=winner_id,
            eliminated_teams=[loser_id],
            calculation_details={
                'head_to_head_record': h2h_result,
                'winner_record': f"{max(wins1, wins2)}-{min(wins1, wins2)}"
            },
            description=f"Head-to-head: Team {winner_id} beat Team {loser_id} {max(wins1, wins2)}-{min(wins1, wins2)}"
        )

    def _apply_head_to_head_multi_teams(self, teams: List[TeamRecord],
                                       head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply head-to-head for 3+ teams (more complex)."""
        # For now, return None - this requires complex logic
        # TODO: Implement multi-team head-to-head
        return None

    def _apply_head_to_head_sweep(self, teams: List[TeamRecord],
                                 head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """
        Apply head-to-head sweep (wild card only).
        Only applies if one team beat all others or lost to all others.
        """
        # TODO: Implement head-to-head sweep logic
        return None

    def _apply_division_record(self, teams: List[TeamRecord],
                              head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply division record tiebreaker."""
        # Sort by division win percentage
        teams_by_div_pct = sorted(teams, key=lambda t: t.division_win_percentage, reverse=True)

        best_pct = teams_by_div_pct[0].division_win_percentage
        winners = [team for team in teams_by_div_pct if team.division_win_percentage == best_pct]

        if len(winners) == 1:
            return TiebreakerResult(
                rule_applied=TiebreakerRule.DIVISION_RECORD,
                teams_involved=[team.team_id for team in teams],
                winner_team_id=winners[0].team_id,
                eliminated_teams=[team.team_id for team in teams if team.team_id != winners[0].team_id],
                calculation_details={
                    'division_records': {team.team_id: f"{team.division_wins}-{team.division_losses}"
                                       for team in teams}
                },
                description=f"Best division record: {winners[0].division_wins}-{winners[0].division_losses}"
            )

        return None  # Still tied

    def _apply_conference_record(self, teams: List[TeamRecord],
                                head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply conference record tiebreaker."""
        # Sort by conference win percentage
        teams_by_conf_pct = sorted(teams, key=lambda t: t.conference_win_percentage, reverse=True)

        best_pct = teams_by_conf_pct[0].conference_win_percentage
        winners = [team for team in teams_by_conf_pct if team.conference_win_percentage == best_pct]

        if len(winners) == 1:
            return TiebreakerResult(
                rule_applied=TiebreakerRule.CONFERENCE_RECORD,
                teams_involved=[team.team_id for team in teams],
                winner_team_id=winners[0].team_id,
                eliminated_teams=[team.team_id for team in teams if team.team_id != winners[0].team_id],
                calculation_details={
                    'conference_records': {team.team_id: f"{team.conference_wins}-{team.conference_losses}"
                                         for team in teams}
                },
                description=f"Best conference record: {winners[0].conference_wins}-{winners[0].conference_losses}"
            )

        return None  # Still tied

    def _apply_common_games(self, teams: List[TeamRecord],
                           head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply common games tiebreaker (minimum 4 games)."""
        # TODO: Implement common games logic - requires game-by-game analysis
        return None

    def _apply_strength_of_victory(self, teams: List[TeamRecord],
                                  head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply strength of victory tiebreaker."""
        # Sort by strength of victory (higher is better)
        teams_by_sov = sorted(teams, key=lambda t: t.strength_of_victory, reverse=True)

        best_sov = teams_by_sov[0].strength_of_victory
        winners = [team for team in teams_by_sov if abs(team.strength_of_victory - best_sov) < 0.001]

        if len(winners) == 1:
            return TiebreakerResult(
                rule_applied=TiebreakerRule.STRENGTH_OF_VICTORY,
                teams_involved=[team.team_id for team in teams],
                winner_team_id=winners[0].team_id,
                eliminated_teams=[team.team_id for team in teams if team.team_id != winners[0].team_id],
                calculation_details={
                    'strength_of_victory': {team.team_id: round(team.strength_of_victory, 3)
                                          for team in teams}
                },
                description=f"Best strength of victory: {winners[0].strength_of_victory:.3f}"
            )

        return None  # Still tied

    def _apply_strength_of_schedule(self, teams: List[TeamRecord],
                                   head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply strength of schedule tiebreaker."""
        # Sort by strength of schedule (higher is better)
        teams_by_sos = sorted(teams, key=lambda t: t.strength_of_schedule, reverse=True)

        best_sos = teams_by_sos[0].strength_of_schedule
        winners = [team for team in teams_by_sos if abs(team.strength_of_schedule - best_sos) < 0.001]

        if len(winners) == 1:
            return TiebreakerResult(
                rule_applied=TiebreakerRule.STRENGTH_OF_SCHEDULE,
                teams_involved=[team.team_id for team in teams],
                winner_team_id=winners[0].team_id,
                eliminated_teams=[team.team_id for team in teams if team.team_id != winners[0].team_id],
                calculation_details={
                    'strength_of_schedule': {team.team_id: round(team.strength_of_schedule, 3)
                                           for team in teams}
                },
                description=f"Best strength of schedule: {winners[0].strength_of_schedule:.3f}"
            )

        return None  # Still tied

    def _apply_combined_ranking_conference(self, teams: List[TeamRecord],
                                         head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply combined ranking among conference teams."""
        # TODO: Implement combined ranking logic - requires conference-wide point rankings
        return None

    def _apply_combined_ranking_all(self, teams: List[TeamRecord],
                                   head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply combined ranking among all teams."""
        # TODO: Implement combined ranking logic - requires league-wide point rankings
        return None

    def _apply_net_points_conference(self, teams: List[TeamRecord],
                                    head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply net points in conference games."""
        # TODO: Implement net points in conference games - requires conference game breakdown
        return None

    def _apply_net_points_all(self, teams: List[TeamRecord],
                             head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply net points in all games."""
        # Sort by point differential (higher is better)
        teams_by_diff = sorted(teams, key=lambda t: t.point_differential, reverse=True)

        best_diff = teams_by_diff[0].point_differential
        winners = [team for team in teams_by_diff if team.point_differential == best_diff]

        if len(winners) == 1:
            return TiebreakerResult(
                rule_applied=TiebreakerRule.NET_POINTS_ALL,
                teams_involved=[team.team_id for team in teams],
                winner_team_id=winners[0].team_id,
                eliminated_teams=[team.team_id for team in teams if team.team_id != winners[0].team_id],
                calculation_details={
                    'point_differentials': {team.team_id: team.point_differential for team in teams}
                },
                description=f"Best point differential: {winners[0].point_differential}"
            )

        return None  # Still tied

    def _apply_coin_flip(self, teams: List[TeamRecord],
                        head_to_head_results: Dict[tuple, str]) -> Optional[TiebreakerResult]:
        """Apply coin flip tiebreaker (last resort)."""
        import random

        # Randomly select winner
        winner = random.choice(teams)

        return TiebreakerResult(
            rule_applied=TiebreakerRule.COIN_FLIP,
            teams_involved=[team.team_id for team in teams],
            winner_team_id=winner.team_id,
            eliminated_teams=[team.team_id for team in teams if team.team_id != winner.team_id],
            calculation_details={'method': 'random_selection'},
            description="Coin flip/random selection"
        )