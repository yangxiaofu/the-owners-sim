"""
Flex Scheduler - NFL-style late-season schedule adjustments.

Part of Milestone 11: Schedule & Rivalries, Tollgate 8.
Implements flex scheduling for weeks 12-17 based on playoff implications.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.standings_api import StandingsAPI, TeamStanding
from src.game_cycle.database.rivalry_api import RivalryAPI, Rivalry
from src.game_cycle.models.game_slot import GameSlot, PrimetimeAssignment, get_market_score
from team_management.teams.team_loader import get_team_by_id


# Flex scheduling constants
FLEX_THRESHOLD = 15  # Minimum appeal delta to trigger flex
MAX_GAMES_PER_SEASON = 4  # Don't flex more than 4 games per season


@dataclass
class PlayoffImplications:
    """What's at stake for a team in a given game."""
    team_id: int
    can_clinch_playoff: bool = False      # Win = playoff berth
    can_clinch_division: bool = False     # Win = division title
    can_clinch_bye: bool = False          # Win = first-round bye (seed 1)
    elimination_game: bool = False        # Loss = mathematically eliminated
    wild_card_race: bool = False          # In tight wild card race
    division_title_game: bool = False     # Division title on the line

    @property
    def implication_score(self) -> int:
        """
        Calculate composite implication score (0-50).

        Used to boost flex appeal for high-stakes games.
        """
        score = 0
        if self.can_clinch_playoff:
            score += 15
        if self.can_clinch_division:
            score += 12
        if self.can_clinch_bye:
            score += 10
        if self.elimination_game:
            score += 12
        if self.wild_card_race:
            score += 5
        if self.division_title_game:
            score += 10
        return min(score, 50)  # Cap at 50


@dataclass
class FlexRecommendation:
    """Recommendation to flex a game into/out of primetime."""
    game_to_flex_in: str           # game_id to move TO primetime
    game_to_flex_out: str          # game_id to move OUT of primetime
    target_slot: GameSlot          # SNF, MNF, or TNF
    reason: str                    # "playoff_implications", "division_race", etc.
    appeal_delta: int              # How much better the new game is
    flex_in_appeal: int            # Appeal score of game being flexed in
    flex_out_appeal: int           # Appeal score of game being flexed out


class FlexScheduler:
    """
    NFL flex scheduling for weeks 12-17.

    Rules:
    - Weeks 12-17: SNF games can be flexed
    - Weeks 15-17: TNF and MNF can also be flexed
    - 12-day notice required (we auto-flex after week completion)
    - Protected games NEVER flex: Kickoff, Thanksgiving, already-flexed games

    Usage:
        flex_scheduler = FlexScheduler(db, dynasty_id)
        recommendations = flex_scheduler.evaluate_flex_opportunities(
            season=2025, current_week=10, target_week=12
        )
        for rec in recommendations:
            if rec.appeal_delta >= FLEX_THRESHOLD:
                flex_scheduler.execute_flex(season, rec)
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        self._db = db
        self._dynasty_id = dynasty_id
        self._standings_api = StandingsAPI(db)
        self._rivalry_api = RivalryAPI(db)

    def evaluate_flex_opportunities(
        self,
        season: int,
        current_week: int,
        target_week: int,
    ) -> List[FlexRecommendation]:
        """
        Identify games that should be flexed for target_week.

        Called after current_week completes to evaluate target_week games.

        Args:
            season: Season year
            current_week: Week that just completed
            target_week: Week to potentially flex (usually current_week + 2)

        Returns:
            List of FlexRecommendation objects, sorted by appeal_delta descending
        """
        # Validate flex window
        if target_week < 12 or target_week > 17:
            return []

        # Determine which slots can be flexed this week
        flexable_slots = self._get_flexable_slots(target_week)
        if not flexable_slots:
            return []

        # Get current standings
        standings = self._standings_api.get_standings(self._dynasty_id, season)
        if not standings:
            return []

        # Get all games for target week
        week_games = self._get_week_games(season, target_week)
        if not week_games:
            return []

        # Load rivalries for appeal calculation
        rivalries = self._rivalry_api.get_all_rivalries(self._dynasty_id)
        rivalry_map = self._build_rivalry_map(rivalries)

        # Calculate appeal for all games
        game_appeals: Dict[str, int] = {}
        for game in week_games:
            appeal = self.calculate_game_flex_appeal(
                season, target_week,
                game['home_team_id'], game['away_team_id'],
                standings, rivalry_map
            )
            game_appeals[game['game_id']] = appeal

        # Find current primetime games and their appeals
        recommendations = []

        for slot in flexable_slots:
            # Get current game in this primetime slot
            current_primetime = self._get_game_in_slot(season, target_week, slot)
            if not current_primetime:
                continue

            current_appeal = game_appeals.get(current_primetime['game_id'], 0)

            # Find best non-primetime game to swap in
            for game in week_games:
                game_id = game['game_id']

                # Skip if already in primetime or already flexed
                if self._is_primetime_slot(game.get('slot', 'SUN_EARLY')):
                    continue
                if game.get('flexed_from'):
                    continue

                candidate_appeal = game_appeals.get(game_id, 0)
                appeal_delta = candidate_appeal - current_appeal

                if appeal_delta >= FLEX_THRESHOLD:
                    reason = self._determine_flex_reason(
                        game['home_team_id'], game['away_team_id'],
                        standings, rivalry_map
                    )

                    recommendations.append(FlexRecommendation(
                        game_to_flex_in=game_id,
                        game_to_flex_out=current_primetime['game_id'],
                        target_slot=slot,
                        reason=reason,
                        appeal_delta=appeal_delta,
                        flex_in_appeal=candidate_appeal,
                        flex_out_appeal=current_appeal,
                    ))

        # Sort by appeal delta (highest first)
        recommendations.sort(key=lambda r: r.appeal_delta, reverse=True)

        return recommendations

    def execute_flex(
        self,
        season: int,
        recommendation: FlexRecommendation,
    ) -> bool:
        """
        Execute a flex schedule change.

        Updates game_slots table:
        - game_to_flex_in: slot = target_slot, flexed_from = old_slot
        - game_to_flex_out: slot = old_slot of flex_in game

        Args:
            season: Season year
            recommendation: FlexRecommendation to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get original slots
            orig_in_slot = self._get_game_slot(season, recommendation.game_to_flex_in)
            orig_out_slot = recommendation.target_slot.value

            if not orig_in_slot:
                return False

            # Get connection for atomic transaction
            conn = self._db.get_connection()

            # Update game being flexed IN to primetime
            conn.execute(
                """UPDATE game_slots
                   SET slot = ?, flexed_from = ?, appeal_score = ?
                   WHERE dynasty_id = ? AND season = ? AND game_id = ?""",
                (recommendation.target_slot.value, orig_in_slot,
                 recommendation.flex_in_appeal,
                 self._dynasty_id, season, recommendation.game_to_flex_in)
            )

            # Update game being flexed OUT of primetime
            conn.execute(
                """UPDATE game_slots
                   SET slot = ?, flexed_from = ?
                   WHERE dynasty_id = ? AND season = ? AND game_id = ?""",
                (orig_in_slot, orig_out_slot,
                 self._dynasty_id, season, recommendation.game_to_flex_out)
            )

            conn.commit()
            return True

        except Exception as e:
            conn = self._db.get_connection()
            conn.rollback()
            return False

    def calculate_game_flex_appeal(
        self,
        season: int,
        week: int,
        home_team_id: int,
        away_team_id: int,
        standings: Optional[List[TeamStanding]] = None,
        rivalry_map: Optional[Dict[Tuple[int, int], Rivalry]] = None,
    ) -> int:
        """
        Calculate flex appeal score (0-100) using CURRENT standings.

        Different from initial appeal calculation which uses prior year standings.

        Score components:
        - Playoff implications: +40 max
        - Current win total: +25 max
        - Rivalry intensity: +20 max
        - Market size: +15 max

        Args:
            season: Season year
            week: Week number
            home_team_id: Home team ID
            away_team_id: Away team ID
            standings: Optional pre-loaded standings (for efficiency)
            rivalry_map: Optional pre-loaded rivalry map

        Returns:
            Appeal score 0-100
        """
        # Load standings if not provided
        if standings is None:
            standings = self._standings_api.get_standings(self._dynasty_id, season)

        # Load rivalries if not provided
        if rivalry_map is None:
            rivalries = self._rivalry_api.get_all_rivalries(self._dynasty_id)
            rivalry_map = self._build_rivalry_map(rivalries)

        total_appeal = 0

        # 1. Playoff implications (0-40)
        home_implications = self.calculate_playoff_implications(
            season, week, home_team_id, away_team_id, standings
        )
        away_implications = self.calculate_playoff_implications(
            season, week, away_team_id, home_team_id, standings
        )
        implications_appeal = min(
            home_implications.implication_score + away_implications.implication_score,
            40
        )
        total_appeal += implications_appeal

        # 2. Current win total (0-25)
        win_total_appeal = self._get_current_win_appeal(
            home_team_id, away_team_id, standings
        )
        total_appeal += win_total_appeal

        # 3. Rivalry intensity (0-20)
        rivalry_appeal = self._get_rivalry_appeal(
            home_team_id, away_team_id, rivalry_map
        )
        total_appeal += rivalry_appeal

        # 4. Market size (0-15)
        market_appeal = self._get_market_appeal(home_team_id, away_team_id)
        total_appeal += market_appeal

        return min(total_appeal, 100)

    def calculate_playoff_implications(
        self,
        season: int,
        week: int,
        team_id: int,
        opponent_id: int,
        standings: Optional[List[TeamStanding]] = None,
    ) -> PlayoffImplications:
        """
        Calculate what's at stake for a team in upcoming games.

        Args:
            season: Season year
            week: Week number
            team_id: Team to evaluate
            opponent_id: Opponent team ID
            standings: Optional pre-loaded standings

        Returns:
            PlayoffImplications for the team
        """
        if standings is None:
            standings = self._standings_api.get_standings(self._dynasty_id, season)

        implications = PlayoffImplications(team_id=team_id)

        if not standings:
            return implications

        # Get team's standing
        team_standing = next(
            (s for s in standings if s.team_id == team_id), None
        )
        if not team_standing:
            return implications

        # Get team info for conference/division
        team_info = get_team_by_id(team_id)
        opponent_info = get_team_by_id(opponent_id)

        if not team_info:
            return implications

        # Filter standings by conference
        conference_standings = [
            s for s in standings
            if self._get_team_conference(s.team_id) == team_info.conference
        ]
        conference_standings.sort(key=lambda s: s.win_percentage, reverse=True)

        # Get team's conference rank
        conference_rank = next(
            (i + 1 for i, s in enumerate(conference_standings) if s.team_id == team_id),
            16
        )

        # Calculate remaining games (17 - games played)
        games_played = team_standing.wins + team_standing.losses + team_standing.ties
        remaining_games = 17 - games_played

        # Check clinching scenarios
        implications.can_clinch_playoff = self._can_clinch_playoff(
            team_standing, conference_standings, conference_rank, remaining_games
        )

        implications.can_clinch_division = self._can_clinch_division(
            team_id, team_standing, standings, remaining_games
        )

        implications.can_clinch_bye = self._can_clinch_bye(
            team_standing, conference_standings, conference_rank, remaining_games
        )

        # Check elimination scenario
        implications.elimination_game = self._is_elimination_game(
            team_standing, conference_standings, conference_rank, remaining_games
        )

        # Check wild card race
        implications.wild_card_race = self._in_wild_card_race(
            conference_rank, conference_standings
        )

        # Check if division title game
        if opponent_info and team_info.division == opponent_info.division:
            implications.division_title_game = self._is_division_title_game(
                team_id, opponent_id, standings
            )

        return implications

    # -------------------- Private Helper Methods --------------------

    def _get_flexable_slots(self, week: int) -> List[GameSlot]:
        """Get which primetime slots can be flexed for a given week."""
        if week < 12:
            return []
        elif week <= 14:
            # Weeks 12-14: Only SNF
            return [GameSlot.SUNDAY_NIGHT]
        else:
            # Weeks 15-17: SNF, TNF, MNF
            return [GameSlot.SUNDAY_NIGHT, GameSlot.THURSDAY_NIGHT, GameSlot.MONDAY_NIGHT]

    def _get_week_games(self, season: int, week: int) -> List[Dict]:
        """Get all games for a given week from game_slots table."""
        rows = self._db.query_all(
            """SELECT game_id, slot, home_team_id, away_team_id,
                      appeal_score, is_flex_eligible, flexed_from
               FROM game_slots
               WHERE dynasty_id = ? AND season = ? AND week = ?""",
            (self._dynasty_id, season, week)
        )
        return [dict(row) for row in rows] if rows else []

    def _get_game_in_slot(
        self, season: int, week: int, slot: GameSlot
    ) -> Optional[Dict]:
        """Get the game currently in a specific slot."""
        row = self._db.query_one(
            """SELECT game_id, slot, home_team_id, away_team_id, appeal_score
               FROM game_slots
               WHERE dynasty_id = ? AND season = ? AND week = ? AND slot = ?""",
            (self._dynasty_id, season, week, slot.value)
        )
        return dict(row) if row else None

    def _get_game_slot(self, season: int, game_id: str) -> Optional[str]:
        """Get the current slot for a game."""
        row = self._db.query_one(
            """SELECT slot FROM game_slots
               WHERE dynasty_id = ? AND season = ? AND game_id = ?""",
            (self._dynasty_id, season, game_id)
        )
        return row['slot'] if row else None

    def _is_primetime_slot(self, slot: str) -> bool:
        """Check if a slot is a primetime slot."""
        primetime_slots = {'TNF', 'SNF', 'MNF', 'KICKOFF',
                          'TG_EARLY', 'TG_LATE', 'TG_NIGHT', 'XMAS'}
        return slot in primetime_slots

    def _build_rivalry_map(
        self, rivalries: List[Rivalry]
    ) -> Dict[Tuple[int, int], Rivalry]:
        """Build lookup map for rivalries."""
        rivalry_map = {}
        for r in rivalries:
            key = (min(r.team_a_id, r.team_b_id), max(r.team_a_id, r.team_b_id))
            rivalry_map[key] = r
        return rivalry_map

    def _get_rivalry(
        self, team_a: int, team_b: int,
        rivalry_map: Dict[Tuple[int, int], Rivalry]
    ) -> Optional[Rivalry]:
        """Get rivalry between two teams."""
        key = (min(team_a, team_b), max(team_a, team_b))
        return rivalry_map.get(key)

    def _get_team_conference(self, team_id: int) -> Optional[str]:
        """Get team's conference."""
        team = get_team_by_id(team_id)
        return team.conference if team else None

    def _get_team_division(self, team_id: int) -> Optional[str]:
        """Get team's division."""
        team = get_team_by_id(team_id)
        return team.division if team else None

    # -------------------- Appeal Component Calculations --------------------

    def _get_current_win_appeal(
        self, home_team_id: int, away_team_id: int,
        standings: List[TeamStanding]
    ) -> int:
        """
        Calculate appeal from current win totals (0-25).

        Formula: combined_wins * 1.5, capped at 25
        """
        home_standing = next(
            (s for s in standings if s.team_id == home_team_id), None
        )
        away_standing = next(
            (s for s in standings if s.team_id == away_team_id), None
        )

        home_wins = home_standing.wins if home_standing else 0
        away_wins = away_standing.wins if away_standing else 0

        combined_wins = home_wins + away_wins
        return min(int(combined_wins * 1.5), 25)

    def _get_rivalry_appeal(
        self, home_team_id: int, away_team_id: int,
        rivalry_map: Dict[Tuple[int, int], Rivalry]
    ) -> int:
        """
        Calculate appeal from rivalry intensity (0-20).

        Formula: rivalry.intensity * 0.2
        """
        rivalry = self._get_rivalry(home_team_id, away_team_id, rivalry_map)
        if rivalry:
            return min(int(rivalry.intensity * 0.2), 20)
        return 0

    def _get_market_appeal(self, home_team_id: int, away_team_id: int) -> int:
        """
        Calculate appeal from market size (0-15).

        Uses get_market_score from game_slot.py (returns 0-20).
        Formula: average of both teams' market scores, scaled to 0-15
        """
        # get_market_score returns 0-20, scale to 0-15
        home_score = int(get_market_score(home_team_id) * 0.75)
        away_score = int(get_market_score(away_team_id) * 0.75)
        return min((home_score + away_score) // 2, 15)

    # -------------------- Clinching/Elimination Logic --------------------

    def _can_clinch_playoff(
        self,
        team_standing: TeamStanding,
        conference_standings: List[TeamStanding],
        conference_rank: int,
        remaining_games: int,
    ) -> bool:
        """
        Determine if team can clinch playoff berth with a win.

        Simplified logic:
        - Team is in top 7 of conference
        - Win would give them enough wins that 8th place can't catch them
        """
        if conference_rank > 7:
            return False

        # Get 8th place team's potential max wins
        if len(conference_standings) >= 8:
            eighth_place = conference_standings[7]
            eighth_max_wins = eighth_place.wins + remaining_games

            # If team wins, can 8th place still catch them?
            team_wins_after = team_standing.wins + 1
            return team_wins_after > eighth_max_wins

        return False

    def _can_clinch_division(
        self,
        team_id: int,
        team_standing: TeamStanding,
        standings: List[TeamStanding],
        remaining_games: int,
    ) -> bool:
        """
        Determine if team can clinch division with a win.

        Simplified logic:
        - Team is 1st in division
        - Win would put them out of reach of 2nd place
        """
        division = self._get_team_division(team_id)
        if not division:
            return False

        # Get division standings
        division_standings = [
            s for s in standings
            if self._get_team_division(s.team_id) == division
        ]
        division_standings.sort(key=lambda s: s.win_percentage, reverse=True)

        if not division_standings or division_standings[0].team_id != team_id:
            return False

        if len(division_standings) >= 2:
            second_place = division_standings[1]
            second_max_wins = second_place.wins + remaining_games
            team_wins_after = team_standing.wins + 1
            return team_wins_after > second_max_wins

        return False

    def _can_clinch_bye(
        self,
        team_standing: TeamStanding,
        conference_standings: List[TeamStanding],
        conference_rank: int,
        remaining_games: int,
    ) -> bool:
        """
        Determine if team can clinch first-round bye (seed 1) with a win.

        Simplified logic:
        - Team is 1st in conference
        - Win would put them out of reach of 2nd place
        """
        if conference_rank != 1:
            return False

        if len(conference_standings) >= 2:
            second_place = conference_standings[1]
            second_max_wins = second_place.wins + remaining_games
            team_wins_after = team_standing.wins + 1
            return team_wins_after > second_max_wins

        return False

    def _is_elimination_game(
        self,
        team_standing: TeamStanding,
        conference_standings: List[TeamStanding],
        conference_rank: int,
        remaining_games: int,
    ) -> bool:
        """
        Determine if loss would mathematically eliminate team.

        Simplified logic:
        - Team is outside top 7
        - Loss would put them too far behind to catch 7th place
        """
        if conference_rank <= 7:
            return False

        if len(conference_standings) >= 7:
            seventh_place = conference_standings[6]
            seventh_current_wins = seventh_place.wins

            # If team loses, can they still catch 7th place?
            team_max_wins_after_loss = team_standing.wins + (remaining_games - 1)
            return team_max_wins_after_loss < seventh_current_wins

        return False

    def _in_wild_card_race(
        self,
        conference_rank: int,
        conference_standings: List[TeamStanding],
    ) -> bool:
        """
        Check if team is in tight wild card race.

        True if team is ranked 5-9 and within 2 games of 7th place.
        """
        if conference_rank < 5 or conference_rank > 9:
            return False

        if len(conference_standings) >= 7:
            seventh_place = conference_standings[6]
            team_standing = conference_standings[conference_rank - 1]

            games_back = seventh_place.wins - team_standing.wins
            return abs(games_back) <= 2

        return False

    def _is_division_title_game(
        self,
        team_id: int,
        opponent_id: int,
        standings: List[TeamStanding],
    ) -> bool:
        """
        Check if this game decides the division title.

        True if:
        - Both teams are in same division
        - Teams are 1st and 2nd in division
        - Difference is 1 game or less
        """
        division = self._get_team_division(team_id)
        opponent_division = self._get_team_division(opponent_id)

        if not division or division != opponent_division:
            return False

        # Get division standings
        division_standings = [
            s for s in standings
            if self._get_team_division(s.team_id) == division
        ]
        division_standings.sort(key=lambda s: s.win_percentage, reverse=True)

        if len(division_standings) < 2:
            return False

        # Check if these two teams are 1st and 2nd
        top_two_ids = {division_standings[0].team_id, division_standings[1].team_id}
        if team_id not in top_two_ids or opponent_id not in top_two_ids:
            return False

        # Check if within 1 game
        first = division_standings[0]
        second = division_standings[1]
        games_diff = first.wins - second.wins

        return games_diff <= 1

    def _determine_flex_reason(
        self,
        home_team_id: int,
        away_team_id: int,
        standings: List[TeamStanding],
        rivalry_map: Dict[Tuple[int, int], Rivalry],
    ) -> str:
        """Determine primary reason for flexing this game."""
        # Check playoff implications first
        home_impl = self.calculate_playoff_implications(
            0, 0, home_team_id, away_team_id, standings
        )
        away_impl = self.calculate_playoff_implications(
            0, 0, away_team_id, home_team_id, standings
        )

        if home_impl.division_title_game or away_impl.division_title_game:
            return "division_title"
        if home_impl.can_clinch_playoff or away_impl.can_clinch_playoff:
            return "playoff_clinch"
        if home_impl.elimination_game or away_impl.elimination_game:
            return "elimination_game"
        if home_impl.wild_card_race or away_impl.wild_card_race:
            return "wild_card_race"

        # Check rivalry
        rivalry = self._get_rivalry(home_team_id, away_team_id, rivalry_map)
        if rivalry and rivalry.intensity >= 75:
            return "rivalry_matchup"

        # Default
        return "high_appeal_matchup"
