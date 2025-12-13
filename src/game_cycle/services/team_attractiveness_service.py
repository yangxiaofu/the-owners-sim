"""
Team Attractiveness Service for game_cycle.

Manages team attractiveness calculation by combining static team data
(market, taxes, weather) with dynamic 5-year history (wins, playoffs, Super Bowls).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.player_management.team_attractiveness import TeamAttractiveness
from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.team_history_api import TeamHistoryAPI, SeasonHistoryRecord
from src.game_cycle.database.standings_api import StandingsAPI
from src.game_cycle.database.playoff_bracket_api import PlayoffBracketAPI


class TeamAttractivenessService:
    """Service for team attractiveness calculation and history management.

    Responsibilities:
    - Load static team data from config
    - Query and manage 5-year history
    - Calculate contender scores
    - Record season results
    - Build TeamAttractiveness objects
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str, season: int):
        """
        Initialize the service.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier for isolation
            season: Current season year
        """
        self._db = db
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded dependencies
        self._history_api: Optional[TeamHistoryAPI] = None
        self._standings_api: Optional[StandingsAPI] = None
        self._playoff_api: Optional[PlayoffBracketAPI] = None
        self._static_data: Optional[Dict[str, Any]] = None

    # -------------------- Lazy Loading --------------------

    def _get_history_api(self) -> TeamHistoryAPI:
        """Lazy-load TeamHistoryAPI."""
        if self._history_api is None:
            self._history_api = TeamHistoryAPI(self._db)
        return self._history_api

    def _get_standings_api(self) -> StandingsAPI:
        """Lazy-load StandingsAPI."""
        if self._standings_api is None:
            self._standings_api = StandingsAPI(self._db)
        return self._standings_api

    def _get_playoff_api(self) -> PlayoffBracketAPI:
        """Lazy-load PlayoffBracketAPI."""
        if self._playoff_api is None:
            self._playoff_api = PlayoffBracketAPI(self._db)
        return self._playoff_api

    def _load_static_data(self) -> Dict[str, Any]:
        """Load static team data from config file."""
        if self._static_data is None:
            config_path = (
                Path(__file__).parent.parent.parent
                / "config"
                / "team_attractiveness_static.json"
            )
            with open(config_path) as f:
                self._static_data = json.load(f)
        return self._static_data

    # -------------------- Core Methods --------------------

    def get_team_attractiveness(self, team_id: int) -> TeamAttractiveness:
        """
        Build a complete TeamAttractiveness object.

        Combines static data (market, taxes, weather) with dynamic data
        (playoff history, current record, winning culture).

        Args:
            team_id: Team ID (1-32)

        Returns:
            TeamAttractiveness with all fields populated
        """
        # Load static data for this team
        static = self._load_static_data().get(str(team_id), {})

        # Get 5-year history
        history = self._get_history_api().get_team_history(
            self._dynasty_id, team_id, years=5
        )

        # Count playoff appearances and Super Bowl wins
        playoff_apps = sum(1 for h in history if h.made_playoffs)
        sb_wins = sum(1 for h in history if h.won_super_bowl)

        # Get current season record (if exists in history)
        current = next(
            (h for h in history if h.season == self._season),
            None
        )
        current_wins = current.wins if current else 0
        current_losses = current.losses if current else 0

        # Calculate winning culture score from 5-year average
        winning_culture = self._calculate_winning_culture(history)

        return TeamAttractiveness(
            team_id=team_id,
            # Static factors
            market_size=static.get("market_size", 50),
            state_income_tax_rate=static.get("state_income_tax_rate", 0.05),
            weather_score=static.get("weather_score", 50),
            state=static.get("state"),
            # Dynamic factors
            playoff_appearances_5yr=playoff_apps,
            super_bowl_wins_5yr=sb_wins,
            winning_culture_score=winning_culture,
            coaching_prestige=50,  # Default - future enhancement
            current_season_wins=current_wins,
            current_season_losses=current_losses,
        )

    def get_all_team_attractiveness(self) -> Dict[int, TeamAttractiveness]:
        """
        Get attractiveness for all 32 teams.

        Returns:
            Dict mapping team_id to TeamAttractiveness
        """
        return {
            team_id: self.get_team_attractiveness(team_id)
            for team_id in range(1, 33)
        }

    # -------------------- Score Calculations --------------------

    def calculate_contender_score(self, team_id: int) -> int:
        """
        Calculate team's contender score from 5-year history.

        Formula (0-100 scale):
        - Current record: 40%
        - Playoff appearances (5yr): 30%
        - Super Bowl wins (5yr): 20%
        - Winning culture (5yr avg): 10%

        Args:
            team_id: Team ID (1-32)

        Returns:
            Contender score 0-100
        """
        history = self._get_history_api().get_team_history(
            self._dynasty_id, team_id, years=5
        )

        if not history:
            return 50  # Default for new dynasty

        # Current season record weight: 40%
        current = next(
            (h for h in history if h.season == self._season),
            None
        )
        if current and (current.wins + current.losses) > 0:
            win_pct = current.wins / (current.wins + current.losses)
            current_score = win_pct * 100
        else:
            current_score = 50

        # Playoff appearances in 5 years: 30% (max 5 appearances = 100)
        playoff_apps = sum(1 for h in history if h.made_playoffs)
        playoff_score = (playoff_apps / 5) * 100

        # Super Bowl wins in 5 years: 20% (each SB = 50 points, max 100)
        sb_wins = sum(1 for h in history if h.won_super_bowl)
        sb_score = min(100, sb_wins * 50)

        # Winning culture (5-year avg win %): 10%
        culture_score = self._calculate_winning_culture(history)

        # Weighted sum
        contender = (
            current_score * 0.40
            + playoff_score * 0.30
            + sb_score * 0.20
            + culture_score * 0.10
        )

        return int(min(100, max(0, contender)))

    def _calculate_winning_culture(
        self,
        history: List[SeasonHistoryRecord]
    ) -> int:
        """
        Calculate winning culture score from history.

        Based on 5-year average win percentage.

        Args:
            history: List of SeasonHistoryRecord

        Returns:
            Score 0-100
        """
        if not history:
            return 50  # Default

        total_wins = sum(h.wins for h in history)
        total_games = sum(h.wins + h.losses for h in history)

        if total_games == 0:
            return 50

        win_pct = total_wins / total_games
        return int(min(100, max(0, win_pct * 100)))

    # -------------------- Season Recording --------------------

    def record_season_result(
        self,
        team_id: int,
        wins: int,
        losses: int,
        made_playoffs: bool = False,
        playoff_round_reached: Optional[str] = None,
        won_super_bowl: bool = False
    ) -> bool:
        """
        Record a single team's season result.

        Args:
            team_id: Team ID (1-32)
            wins: Total wins
            losses: Total losses
            made_playoffs: Whether team made playoffs
            playoff_round_reached: Highest round reached (wild_card, divisional, conference, super_bowl)
            won_super_bowl: Whether team won Super Bowl

        Returns:
            True if recorded successfully
        """
        record = SeasonHistoryRecord(
            team_id=team_id,
            season=self._season,
            wins=wins,
            losses=losses,
            made_playoffs=made_playoffs,
            playoff_round_reached=playoff_round_reached,
            won_super_bowl=won_super_bowl,
        )

        return self._get_history_api().record_season(self._dynasty_id, record)

    def record_all_season_results(self) -> Dict[str, int]:
        """
        Record season results for all 32 teams after Super Bowl.

        Queries standings table for W-L records and playoff_bracket
        table for playoff results.

        Returns:
            Dict with 'recorded' and 'errors' counts
        """
        stats = {"recorded": 0, "errors": 0}

        try:
            # Get final standings (W-L records)
            standings = self._get_standings_api().get_standings(
                self._dynasty_id, self._season
            )

            # Get playoff results for all teams
            playoff_results = self._get_playoff_results()

            for standing in standings:
                team_id = standing.team_id
                made_playoffs = standing.playoff_seed is not None
                result = playoff_results.get(team_id, {})
                round_reached = result.get("round_reached") if made_playoffs else None
                won_sb = result.get("won_super_bowl", False)

                try:
                    if self.record_season_result(
                        team_id=team_id,
                        wins=standing.wins,
                        losses=standing.losses,
                        made_playoffs=made_playoffs,
                        playoff_round_reached=round_reached,
                        won_super_bowl=won_sb,
                    ):
                        stats["recorded"] += 1
                    else:
                        stats["errors"] += 1
                except Exception as e:
                    self._logger.error(f"Error recording team {team_id}: {e}")
                    stats["errors"] += 1

            return stats

        except Exception as e:
            self._logger.error(f"Error recording season results: {e}")
            raise

    def _get_playoff_results(self) -> Dict[int, Dict[str, Any]]:
        """
        Get playoff advancement for all teams.

        Returns:
            Dict mapping team_id to {round_reached, won_super_bowl}
        """
        results: Dict[int, Dict[str, Any]] = {}

        # Get all playoff matchups for this season
        matchups = self._get_playoff_api().get_all_matchups(
            self._dynasty_id, self._season
        )

        # Round order for tracking highest reached
        round_order = {
            "wild_card": 1,
            "divisional": 2,
            "conference": 3,
            "super_bowl": 4,
        }

        for matchup in matchups:
            if matchup.winner is None:
                continue

            winner_id = matchup.winner
            round_name = matchup.round_name

            # Track highest round reached for winner
            if winner_id not in results:
                results[winner_id] = {
                    "round_reached": round_name,
                    "won_super_bowl": False
                }
            else:
                # Update to higher round if applicable
                current_order = round_order.get(
                    results[winner_id]["round_reached"], 0
                )
                new_order = round_order.get(round_name, 0)
                if new_order > current_order:
                    results[winner_id]["round_reached"] = round_name

            # Check for Super Bowl winner
            if round_name == "super_bowl":
                results[winner_id]["won_super_bowl"] = True

            # Also track losers who made it to each round
            # (they made the playoffs and reached at least that round)
            loser_id = (
                matchup.lower_seed
                if matchup.winner == matchup.higher_seed
                else matchup.higher_seed
            )
            if loser_id not in results:
                # Loser reached at least the round before
                results[loser_id] = {
                    "round_reached": round_name,
                    "won_super_bowl": False
                }
            else:
                current_order = round_order.get(
                    results[loser_id]["round_reached"], 0
                )
                new_order = round_order.get(round_name, 0)
                if new_order > current_order:
                    results[loser_id]["round_reached"] = round_name

        return results

    # -------------------- Database Persistence --------------------

    def update_attractiveness_table(self, team_id: int) -> bool:
        """
        Update team_attractiveness table with current computed values.

        Stores a snapshot of the team's attractiveness for the season.

        Args:
            team_id: Team ID (1-32)

        Returns:
            True if successful
        """
        ta = self.get_team_attractiveness(team_id)

        self._db.execute(
            """INSERT OR REPLACE INTO team_attractiveness
               (dynasty_id, team_id, season, playoff_appearances_5yr,
                super_bowl_wins_5yr, winning_culture_score, coaching_prestige)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                self._dynasty_id,
                team_id,
                self._season,
                ta.playoff_appearances_5yr,
                ta.super_bowl_wins_5yr,
                ta.winning_culture_score,
                ta.coaching_prestige,
            )
        )
        return True

    def update_all_attractiveness(self) -> int:
        """
        Update attractiveness table for all 32 teams.

        Returns:
            Number of teams updated
        """
        count = 0
        for team_id in range(1, 33):
            try:
                if self.update_attractiveness_table(team_id):
                    count += 1
            except Exception as e:
                self._logger.error(
                    f"Error updating attractiveness for team {team_id}: {e}"
                )
        return count
