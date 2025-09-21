"""
Strength Calculator

Calculates strength of victory (SOV) and strength of schedule (SOS)
for NFL tiebreaker procedures.

- Strength of Victory: Combined winning percentage of teams that a team beat
- Strength of Schedule: Combined winning percentage of all teams a team played
"""

from typing import Dict, List, Set, Tuple
import logging
from collections import defaultdict

from .seeding_data_models import TeamRecord


class StrengthCalculator:
    """
    Calculates strength metrics for NFL tiebreaker procedures.

    Handles the complex calculations for Strength of Victory (SOV)
    and Strength of Schedule (SOS) based on opponent records.
    """

    def __init__(self):
        """Initialize the strength calculator."""
        self.logger = logging.getLogger(__name__)

    def calculate_strength_metrics(self,
                                 teams: Dict[int, TeamRecord],
                                 game_results: List[Dict]) -> Dict[int, Tuple[float, float]]:
        """
        Calculate strength of victory and strength of schedule for all teams.

        Args:
            teams: Dictionary of team_id -> TeamRecord
            game_results: List of game result dictionaries with keys:
                         ['home_team_id', 'away_team_id', 'home_score', 'away_score']

        Returns:
            Dictionary of team_id -> (strength_of_victory, strength_of_schedule)
        """
        self.logger.info(f"Calculating strength metrics for {len(teams)} teams")

        # Build opponent lists for each team
        opponents_faced = defaultdict(list)  # team_id -> [opponent_ids]
        opponents_beaten = defaultdict(list)  # team_id -> [beaten_opponent_ids]

        for game in game_results:
            home_id = game['home_team_id']
            away_id = game['away_team_id']
            home_score = game['home_score']
            away_score = game['away_score']

            # Skip if either team not in our teams dict
            if home_id not in teams or away_id not in teams:
                continue

            # Track opponents faced
            opponents_faced[home_id].append(away_id)
            opponents_faced[away_id].append(home_id)

            # Track opponents beaten
            if home_score > away_score:
                opponents_beaten[home_id].append(away_id)
            elif away_score > home_score:
                opponents_beaten[away_id].append(home_id)
            # Ties don't count as victories for SOV

        # Calculate metrics for each team
        strength_metrics = {}

        for team_id in teams.keys():
            sov = self._calculate_strength_of_victory(
                team_id, opponents_beaten[team_id], teams
            )
            sos = self._calculate_strength_of_schedule(
                team_id, opponents_faced[team_id], teams
            )

            strength_metrics[team_id] = (sov, sos)

            self.logger.debug(f"Team {team_id}: SOV={sov:.3f}, SOS={sos:.3f}")

        return strength_metrics

    def _calculate_strength_of_victory(self,
                                     team_id: int,
                                     beaten_opponents: List[int],
                                     teams: Dict[int, TeamRecord]) -> float:
        """
        Calculate strength of victory for a team.

        SOV = Combined winning percentage of teams that this team beat

        Args:
            team_id: Team to calculate SOV for
            beaten_opponents: List of opponent team IDs that this team beat
            teams: All team records

        Returns:
            Strength of victory as percentage (0.0 to 1.0)
        """
        if not beaten_opponents:
            return 0.0

        total_wins = 0
        total_games = 0

        for opponent_id in beaten_opponents:
            if opponent_id in teams:
                opponent = teams[opponent_id]
                total_wins += opponent.wins + (0.5 * opponent.ties)
                total_games += opponent.wins + opponent.losses + opponent.ties

        if total_games == 0:
            return 0.0

        sov = total_wins / total_games
        return sov

    def _calculate_strength_of_schedule(self,
                                      team_id: int,
                                      all_opponents: List[int],
                                      teams: Dict[int, TeamRecord]) -> float:
        """
        Calculate strength of schedule for a team.

        SOS = Combined winning percentage of all teams that this team played

        Args:
            team_id: Team to calculate SOS for
            all_opponents: List of all opponent team IDs that this team played
            teams: All team records

        Returns:
            Strength of schedule as percentage (0.0 to 1.0)
        """
        if not all_opponents:
            return 0.0

        total_wins = 0
        total_games = 0

        for opponent_id in all_opponents:
            if opponent_id in teams:
                opponent = teams[opponent_id]
                total_wins += opponent.wins + (0.5 * opponent.ties)
                total_games += opponent.wins + opponent.losses + opponent.ties

        if total_games == 0:
            return 0.0

        sos = total_wins / total_games
        return sos

    def calculate_team_rankings_for_combined_tiebreaker(self,
                                                      teams: Dict[int, TeamRecord],
                                                      scope: str = "conference") -> Dict[int, int]:
        """
        Calculate combined rankings for points scored and points allowed.

        Used for the "combined ranking" tiebreaker rule.

        Args:
            teams: Dictionary of team records
            scope: "conference" or "all" - determines ranking scope

        Returns:
            Dictionary of team_id -> combined_ranking (lower is better)
        """
        # Filter teams by scope if needed
        if scope == "conference":
            # Would need conference information to filter
            # For now, treat as all teams
            ranking_teams = teams
        else:
            ranking_teams = teams

        team_list = list(ranking_teams.values())

        # Rank teams by points scored (descending)
        teams_by_scoring = sorted(team_list, key=lambda t: t.points_for, reverse=True)
        scoring_ranks = {}
        for i, team in enumerate(teams_by_scoring):
            scoring_ranks[team.team_id] = i + 1

        # Rank teams by points allowed (ascending - fewer points allowed is better)
        teams_by_defense = sorted(team_list, key=lambda t: t.points_against)
        defense_ranks = {}
        for i, team in enumerate(teams_by_defense):
            defense_ranks[team.team_id] = i + 1

        # Combined ranking = scoring rank + defense rank (lower is better)
        combined_rankings = {}
        for team_id in ranking_teams.keys():
            combined_rankings[team_id] = scoring_ranks[team_id] + defense_ranks[team_id]

        self.logger.debug(f"Combined rankings calculated for {len(combined_rankings)} teams")
        return combined_rankings

    def update_team_strength_metrics(self,
                                   team: TeamRecord,
                                   sov: float,
                                   sos: float) -> None:
        """
        Update a team record with calculated strength metrics.

        Args:
            team: TeamRecord to update
            sov: Calculated strength of victory
            sos: Calculated strength of schedule
        """
        team.strength_of_victory = sov
        team.strength_of_schedule = sos

    def calculate_head_to_head_records(self,
                                     teams: List[int],
                                     game_results: List[Dict]) -> Dict[tuple, str]:
        """
        Calculate head-to-head records between specific teams.

        Args:
            teams: List of team IDs to calculate head-to-head for
            game_results: List of game result dictionaries

        Returns:
            Dictionary of (team1_id, team2_id) -> "wins1-wins2" record
        """
        head_to_head = defaultdict(lambda: [0, 0])  # [team1_wins, team2_wins]

        for game in game_results:
            home_id = game['home_team_id']
            away_id = game['away_team_id']
            home_score = game['home_score']
            away_score = game['away_score']

            # Only include games between our teams of interest
            if home_id not in teams or away_id not in teams:
                continue

            # Create consistent key (lower ID first)
            key = (min(home_id, away_id), max(home_id, away_id))

            if home_score > away_score:
                # Home team won
                if home_id == key[0]:
                    head_to_head[key][0] += 1  # First team won
                else:
                    head_to_head[key][1] += 1  # Second team won
            elif away_score > home_score:
                # Away team won
                if away_id == key[0]:
                    head_to_head[key][0] += 1  # First team won
                else:
                    head_to_head[key][1] += 1  # Second team won
            # Ties don't affect head-to-head record for tiebreaking

        # Convert to string format
        h2h_records = {}
        for key, wins in head_to_head.items():
            h2h_records[key] = f"{wins[0]}-{wins[1]}"

        return h2h_records