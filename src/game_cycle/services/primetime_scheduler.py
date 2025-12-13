"""
Primetime game scheduling service (Milestone 11, Tollgate 4).

Assigns games to primetime slots (TNF, SNF, MNF) and special games
(Thanksgiving, Christmas, Week 1 Kickoff) based on matchup appeal.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random

from ..database.connection import GameCycleDatabase
from ..database.rivalry_api import RivalryAPI
from ..database.standings_api import StandingsAPI
from ..models.game_slot import GameSlot, PrimetimeAssignment, get_market_score
from ..models.rivalry import Rivalry


@dataclass
class WeeklySlotDistribution:
    """Primetime slot distribution for a week."""
    thursday_night: int = 1      # 1 TNF game (except Week 1 which has Kickoff)
    sunday_night: int = 1        # 1 SNF game
    monday_night: int = 1        # 1 MNF game (some weeks have 2)
    sunday_late: int = 3         # 3-4 late afternoon games
    # Remaining games are Sunday Early


# Teams that traditionally host Thanksgiving games
THANKSGIVING_HOME_TEAMS = {
    22: "THANKSGIVING_EARLY",   # Lions - early game
    17: "THANKSGIVING_LATE",    # Cowboys - late game
}

# Team ID constants
LIONS_TEAM_ID = 22
COWBOYS_TEAM_ID = 17

# Slot ordering for SQL queries
SLOT_ORDER: Dict[str, int] = {
    'KICKOFF': 1,
    'TNF': 2,
    'TG_EARLY': 3,
    'TG_LATE': 4,
    'SUN_EARLY': 5,
    'SUN_LATE': 6,
    'SNF': 7,
    'TG_NIGHT': 8,
    'MNF': 9,
}


class PrimetimeScheduler:
    """
    Assign games to primetime slots based on matchup quality.

    Primetime priorities:
    1. Historic rivalries (Bears-Packers)
    2. Division games between contenders
    3. Super Bowl rematch
    4. Star player matchups (approximated by team record)
    5. Games with playoff implications (late season)
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize primetime scheduler.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty ID for data isolation
        """
        self._db = db
        self._dynasty_id = dynasty_id
        self._rivalry_api = RivalryAPI(db)
        self._standings_api = StandingsAPI(db)

    def _get_slot_order_sql(self, include_week: bool = False) -> str:
        """Generate SQL CASE statement for slot ordering."""
        cases = " ".join(f"WHEN '{slot}' THEN {order}"
                         for slot, order in SLOT_ORDER.items())
        order_clause = f"CASE slot {cases} ELSE 10 END"
        return f"week, {order_clause}" if include_week else order_clause

    def assign_primetime_games(
        self,
        season: int,
        games: List[Dict],
        super_bowl_winner_id: Optional[int] = None,
    ) -> List[PrimetimeAssignment]:
        """
        Assign primetime slots for all games in a season.

        Args:
            season: Season year
            games: List of game event dicts from schedule generator
            super_bowl_winner_id: Optional ID of defending Super Bowl champion

        Returns:
            List of PrimetimeAssignment for all games
        """
        # Get prior year standings for appeal calculation
        standings_list = self._standings_api.get_standings(
            self._dynasty_id, season - 1
        )
        # Convert list of TeamStanding to dict format for appeal calculation
        prior_standings = {
            s.team_id: {"wins": s.wins, "losses": s.losses}
            for s in standings_list
        } if standings_list else {}

        # Get rivalries
        rivalries = self._rivalry_api.get_all_rivalries(self._dynasty_id)
        rivalry_map = self._build_rivalry_map(rivalries)

        # Organize games by week
        games_by_week: Dict[int, List[Dict]] = {}
        for game in games:
            week = game["data"]["parameters"]["week"]
            if week not in games_by_week:
                games_by_week[week] = []
            games_by_week[week].append(game)

        # Calculate Thanksgiving week (Week 12 or 13 typically)
        thanksgiving_week = self._calculate_thanksgiving_week(season)

        # Assign slots week by week
        assignments = []
        for week in range(1, 19):
            if week not in games_by_week:
                continue

            week_games = games_by_week[week]
            week_assignments = self._assign_week_slots(
                week=week,
                games=week_games,
                prior_standings=prior_standings,
                rivalry_map=rivalry_map,
                super_bowl_winner_id=super_bowl_winner_id,
                is_thanksgiving=(week == thanksgiving_week),
            )
            assignments.extend(week_assignments)

        return assignments

    def _assign_week_slots(
        self,
        week: int,
        games: List[Dict],
        prior_standings: Dict[int, Dict],
        rivalry_map: Dict[Tuple[int, int], Rivalry],
        super_bowl_winner_id: Optional[int],
        is_thanksgiving: bool = False,
    ) -> List[PrimetimeAssignment]:
        """
        Assign primetime slots for a single week.

        Args:
            week: Week number (1-18)
            games: List of games for this week
            prior_standings: Prior year standings for appeal calc
            rivalry_map: Map of team pairs to rivalries
            super_bowl_winner_id: Defending champion team ID
            is_thanksgiving: True if this is Thanksgiving week

        Returns:
            List of PrimetimeAssignment for the week
        """
        # Calculate appeal scores for all games
        scored_games = []
        for game in games:
            params = game["data"]["parameters"]
            home_id = params["home_team_id"]
            away_id = params["away_team_id"]
            game_id = game["game_id"]

            rivalry = rivalry_map.get(
                (min(home_id, away_id), max(home_id, away_id))
            )

            appeal = self._calculate_matchup_appeal(
                home_team=home_id,
                away_team=away_id,
                rivalry=rivalry,
                prior_standings=prior_standings,
                super_bowl_winner_id=super_bowl_winner_id,
                week=week,
            )

            scored_games.append({
                "game": game,
                "game_id": game_id,
                "home_id": home_id,
                "away_id": away_id,
                "appeal": appeal,
                "is_divisional": game["data"]["metadata"].get("is_divisional", False),
            })

        # Sort by appeal score (highest first)
        scored_games.sort(key=lambda x: x["appeal"], reverse=True)

        assignments = []
        assigned_game_ids = set()

        # Handle special cases
        if week == 1:
            # Week 1 Kickoff: Defending champion hosts Thursday night
            kickoff_game = self._find_kickoff_game(
                scored_games, super_bowl_winner_id, assigned_game_ids
            )
            if kickoff_game:
                assignments.append(kickoff_game)
                assigned_game_ids.add(kickoff_game.game_id)

        if is_thanksgiving:
            # Thanksgiving: Lions early, Cowboys late, prime matchup night
            thanksgiving_games = self._assign_thanksgiving_games(
                scored_games, assigned_game_ids, week
            )
            assignments.extend(thanksgiving_games)
            for g in thanksgiving_games:
                assigned_game_ids.add(g.game_id)

        # Assign regular primetime slots
        # TNF (if not Week 1 or not already assigned)
        if week != 1 or not any(a.slot == GameSlot.KICKOFF for a in assignments):
            tnf = self._assign_slot(
                scored_games, GameSlot.THURSDAY_NIGHT, assigned_game_ids, week
            )
            if tnf:
                assignments.append(tnf)
                assigned_game_ids.add(tnf.game_id)

        # SNF
        snf = self._assign_slot(
            scored_games, GameSlot.SUNDAY_NIGHT, assigned_game_ids, week
        )
        if snf:
            assignments.append(snf)
            assigned_game_ids.add(snf.game_id)

        # MNF
        mnf = self._assign_slot(
            scored_games, GameSlot.MONDAY_NIGHT, assigned_game_ids, week
        )
        if mnf:
            assignments.append(mnf)
            assigned_game_ids.add(mnf.game_id)

        # Sunday Late (3-4 games)
        for _ in range(3):
            late = self._assign_slot(
                scored_games, GameSlot.SUNDAY_LATE, assigned_game_ids, week
            )
            if late:
                assignments.append(late)
                assigned_game_ids.add(late.game_id)

        # Remaining games are Sunday Early
        for sg in scored_games:
            if sg["game_id"] not in assigned_game_ids:
                assignments.append(PrimetimeAssignment(
                    game_id=sg["game_id"],
                    week=week,
                    slot=GameSlot.SUNDAY_EARLY,
                    home_team_id=sg["home_id"],
                    away_team_id=sg["away_id"],
                    appeal_score=sg["appeal"],
                    broadcast_network=GameSlot.SUNDAY_EARLY.broadcast_network,
                    is_flex_eligible=(week >= 12 and week <= 17),
                ))

        return assignments

    def _get_rivalry_appeal(self, rivalry: Optional[Rivalry]) -> int:
        """Rivalry contribution to appeal (0-30)."""
        return int(rivalry.intensity * 0.30) if rivalry else 0

    def _get_win_total_appeal(
        self,
        prior_standings: Dict[int, Dict],
        home_team: int,
        away_team: int
    ) -> int:
        """Combined win total contribution (0-25)."""
        home_wins = prior_standings.get(home_team, {}).get("wins", 8)
        away_wins = prior_standings.get(away_team, {}).get("wins", 8)
        combined_wins = home_wins + away_wins
        return min(25, int(combined_wins * 25 / 34))

    def _get_market_appeal(self, home_team: int, away_team: int) -> int:
        """Market size contribution (0-20)."""
        home_market = get_market_score(home_team)
        away_market = get_market_score(away_team)
        return (home_market + away_market) // 2

    def _get_super_bowl_appeal(
        self,
        home_team: int,
        away_team: int,
        super_bowl_winner_id: Optional[int]
    ) -> int:
        """Super Bowl participant bonus (0-15)."""
        if super_bowl_winner_id and (home_team == super_bowl_winner_id or away_team == super_bowl_winner_id):
            return 15
        return 0

    def _get_late_season_division_appeal(
        self,
        week: int,
        rivalry: Optional[Rivalry]
    ) -> int:
        """Late season division game bonus (0-10)."""
        if week >= 14 and rivalry and rivalry.rivalry_type.value == "division":
            return 10
        return 0

    def _calculate_matchup_appeal(
        self,
        home_team: int,
        away_team: int,
        rivalry: Optional[Rivalry],
        prior_standings: Dict[int, Dict],
        super_bowl_winner_id: Optional[int],
        week: int,
    ) -> int:
        """
        Calculate matchup appeal score (0-100).

        Factors:
        - Rivalry intensity (+30 max)
        - Combined win total from prior year (+25 max)
        - Market size of teams (+20 max)
        - Super Bowl participant (+15 max)
        - Division game late season (+10 max)

        Args:
            home_team: Home team ID
            away_team: Away team ID
            rivalry: Optional rivalry between teams
            prior_standings: Prior year standings
            super_bowl_winner_id: Defending champion
            week: Week number

        Returns:
            Appeal score 0-100
        """
        score = 0
        score += self._get_rivalry_appeal(rivalry)
        score += self._get_win_total_appeal(prior_standings, home_team, away_team)
        score += self._get_market_appeal(home_team, away_team)
        score += self._get_super_bowl_appeal(home_team, away_team, super_bowl_winner_id)
        score += self._get_late_season_division_appeal(week, rivalry)
        return min(100, score)

    def _find_kickoff_game(
        self,
        scored_games: List[Dict],
        super_bowl_winner_id: Optional[int],
        assigned: set,
    ) -> Optional[PrimetimeAssignment]:
        """
        Find the Week 1 Kickoff game (defending champion hosts).

        If no clear champion, pick highest appeal game.
        """
        # First, look for a game where the champion is home
        if super_bowl_winner_id:
            for sg in scored_games:
                if sg["game_id"] in assigned:
                    continue
                if sg["home_id"] == super_bowl_winner_id:
                    return PrimetimeAssignment(
                        game_id=sg["game_id"],
                        week=1,
                        slot=GameSlot.KICKOFF,
                        home_team_id=sg["home_id"],
                        away_team_id=sg["away_id"],
                        appeal_score=sg["appeal"] + 10,  # Bonus for kickoff
                        broadcast_network=GameSlot.KICKOFF.broadcast_network,
                        is_flex_eligible=False,  # Kickoff never flexed
                    )

        # Fall back to highest appeal game
        for sg in scored_games:
            if sg["game_id"] not in assigned:
                return PrimetimeAssignment(
                    game_id=sg["game_id"],
                    week=1,
                    slot=GameSlot.KICKOFF,
                    home_team_id=sg["home_id"],
                    away_team_id=sg["away_id"],
                    appeal_score=sg["appeal"],
                    broadcast_network=GameSlot.KICKOFF.broadcast_network,
                    is_flex_eligible=False,
                )

        return None

    def _find_team_home_game(
        self,
        scored_games: List[Dict],
        assigned: set,
        home_team_id: int
    ) -> Optional[Dict]:
        """Find first unassigned game where specified team is home."""
        for sg in scored_games:
            if sg["game_id"] not in assigned and sg["home_id"] == home_team_id:
                return sg
        return None

    def _find_highest_appeal_game(
        self,
        scored_games: List[Dict],
        assigned: set
    ) -> Optional[Dict]:
        """Find highest appeal unassigned game."""
        for sg in scored_games:
            if sg["game_id"] not in assigned:
                return sg
        return None

    def _create_assignment(
        self,
        game: Dict,
        week: int,
        slot: GameSlot,
        flex_eligible: bool = False
    ) -> PrimetimeAssignment:
        """Create a PrimetimeAssignment from a scored game dict."""
        return PrimetimeAssignment(
            game_id=game["game_id"],
            week=week,
            slot=slot,
            home_team_id=game["home_id"],
            away_team_id=game["away_id"],
            appeal_score=game["appeal"],
            broadcast_network=slot.broadcast_network,
            is_flex_eligible=flex_eligible,
        )

    def _assign_thanksgiving_games(
        self,
        scored_games: List[Dict],
        assigned: set,
        week: int,
    ) -> List[PrimetimeAssignment]:
        """
        Assign Thanksgiving games (Lions early, Cowboys late, prime night).
        """
        assignments = []

        # Lions home game (early slot)
        lions_game = self._find_team_home_game(scored_games, assigned, LIONS_TEAM_ID)
        if lions_game:
            assignments.append(self._create_assignment(
                lions_game, week, GameSlot.THANKSGIVING_EARLY, flex_eligible=False
            ))
            assigned.add(lions_game["game_id"])

        # Cowboys home game (late slot)
        cowboys_game = self._find_team_home_game(scored_games, assigned, COWBOYS_TEAM_ID)
        if cowboys_game:
            assignments.append(self._create_assignment(
                cowboys_game, week, GameSlot.THANKSGIVING_LATE, flex_eligible=False
            ))
            assigned.add(cowboys_game["game_id"])

        # Prime matchup for night game (highest remaining appeal)
        night_game = self._find_highest_appeal_game(scored_games, assigned)
        if night_game:
            assignments.append(self._create_assignment(
                night_game, week, GameSlot.THANKSGIVING_NIGHT, flex_eligible=False
            ))
            assigned.add(night_game["game_id"])

        return assignments

    def _assign_slot(
        self,
        scored_games: List[Dict],
        slot: GameSlot,
        assigned: set,
        week: int,
    ) -> Optional[PrimetimeAssignment]:
        """
        Assign the next best game to a slot.
        """
        for sg in scored_games:
            if sg["game_id"] in assigned:
                continue

            return PrimetimeAssignment(
                game_id=sg["game_id"],
                week=week,
                slot=slot,
                home_team_id=sg["home_id"],
                away_team_id=sg["away_id"],
                appeal_score=sg["appeal"],
                broadcast_network=slot.broadcast_network,
                is_flex_eligible=(week >= 12 and week <= 17),
            )

        return None

    def _build_rivalry_map(
        self, rivalries: List[Rivalry]
    ) -> Dict[Tuple[int, int], Rivalry]:
        """Build a map of team pairs to rivalries."""
        rivalry_map = {}
        for rivalry in rivalries:
            key = (min(rivalry.team_a_id, rivalry.team_b_id),
                   max(rivalry.team_a_id, rivalry.team_b_id))
            rivalry_map[key] = rivalry
        return rivalry_map

    def _calculate_thanksgiving_week(self, season: int) -> int:
        """
        Calculate which week contains Thanksgiving.

        Thanksgiving is the 4th Thursday of November.
        NFL Week 12 or 13 typically contains Thanksgiving.
        """
        # Simplified: assume Week 12 for most seasons
        # In reality, depends on when the season started
        return 12

    def save_assignments(
        self,
        season: int,
        assignments: List[PrimetimeAssignment],
    ) -> int:
        """
        Save primetime assignments to database.

        Args:
            season: Season year
            assignments: List of PrimetimeAssignment

        Returns:
            Number of assignments saved
        """
        conn = self._db.get_connection()

        # Clear existing assignments for this season
        conn.execute(
            "DELETE FROM game_slots WHERE dynasty_id = ? AND season = ?",
            (self._dynasty_id, season)
        )

        # Insert new assignments
        for assignment in assignments:
            conn.execute(
                """
                INSERT INTO game_slots (
                    dynasty_id, season, game_id, week, slot,
                    home_team_id, away_team_id, appeal_score,
                    broadcast_network, is_flex_eligible, flexed_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._dynasty_id,
                    season,
                    assignment.game_id,
                    assignment.week,
                    assignment.slot.value,
                    assignment.home_team_id,
                    assignment.away_team_id,
                    assignment.appeal_score,
                    assignment.broadcast_network,
                    1 if assignment.is_flex_eligible else 0,
                    assignment.flexed_from.value if assignment.flexed_from else None,
                )
            )

        conn.commit()
        return len(assignments)

    def get_week_schedule(
        self,
        season: int,
        week: int,
    ) -> List[PrimetimeAssignment]:
        """
        Get primetime assignments for a specific week.

        Args:
            season: Season year
            week: Week number

        Returns:
            List of PrimetimeAssignment for the week
        """
        conn = self._db.get_connection()
        order_clause = self._get_slot_order_sql()
        cursor = conn.execute(
            f"""
            SELECT game_id, week, slot, home_team_id, away_team_id,
                   appeal_score, broadcast_network, is_flex_eligible, flexed_from
            FROM game_slots
            WHERE dynasty_id = ? AND season = ? AND week = ?
            ORDER BY {order_clause}
            """,
            (self._dynasty_id, season, week)
        )

        assignments = []
        for row in cursor.fetchall():
            assignments.append(PrimetimeAssignment(
                game_id=row[0],
                week=row[1],
                slot=GameSlot(row[2]),
                home_team_id=row[3],
                away_team_id=row[4],
                appeal_score=row[5],
                broadcast_network=row[6],
                is_flex_eligible=bool(row[7]),
                flexed_from=GameSlot(row[8]) if row[8] else None,
            ))

        return assignments

    def get_primetime_games(
        self,
        season: int,
    ) -> List[PrimetimeAssignment]:
        """
        Get all primetime games for a season.

        Args:
            season: Season year

        Returns:
            List of PrimetimeAssignment for primetime slots only
        """
        conn = self._db.get_connection()
        order_clause = self._get_slot_order_sql(include_week=True)
        cursor = conn.execute(
            f"""
            SELECT game_id, week, slot, home_team_id, away_team_id,
                   appeal_score, broadcast_network, is_flex_eligible, flexed_from
            FROM game_slots
            WHERE dynasty_id = ? AND season = ?
              AND slot IN ('TNF', 'SNF', 'MNF', 'KICKOFF',
                           'TG_EARLY', 'TG_LATE', 'TG_NIGHT', 'XMAS', 'INTL')
            ORDER BY {order_clause}
            """,
            (self._dynasty_id, season)
        )

        assignments = []
        for row in cursor.fetchall():
            assignments.append(PrimetimeAssignment(
                game_id=row[0],
                week=row[1],
                slot=GameSlot(row[2]),
                home_team_id=row[3],
                away_team_id=row[4],
                appeal_score=row[5],
                broadcast_network=row[6],
                is_flex_eligible=bool(row[7]),
                flexed_from=GameSlot(row[8]) if row[8] else None,
            ))

        return assignments
