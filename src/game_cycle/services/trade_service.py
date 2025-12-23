"""
Trade service for managing all trade-related operations in the game cycle.

Follows the established service pattern from DraftService, FreeAgencyService, etc.
"""

import json
import logging
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.persistence.transaction_logger import TransactionLogger
from src.utils.player_field_extractors import extract_overall_rating
from src.transactions.transaction_constants import TRADE_DEADLINE_WEEK
from src.transactions.models import (
    TradeAsset, TradeProposal, TradeDecision, AssetType, FairnessRating,
    NegotiationResult, DraftPick
)
from src.transactions.personality_modifiers import TeamContext


class TradeService:
    """Manages all trade-related operations for the game cycle."""

    TRADE_DEADLINE_WEEK = TRADE_DEADLINE_WEEK  # Week 9

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the trade service.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Current dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

        # Lazy-loaded dependencies (for Tollgate 2+)
        self._value_calculator = None
        self._trade_evaluator = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with Row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Trade Window Validation
    # =========================================================================

    def is_trade_window_open(self, week: int, phase: str) -> bool:
        """
        Check if trades are allowed in the current phase and week.

        Args:
            week: Current week number (1-18 for regular season)
            phase: Current season phase ('preseason', 'regular_season',
                   'playoffs', 'offseason', 'offseason_trading')

        Returns:
            True if trades are allowed, False otherwise
        """
        # Playoffs - no trades allowed
        if phase == "playoffs":
            return False

        # Regular season - trades allowed until Week 9
        if phase == "regular_season":
            return week <= self.TRADE_DEADLINE_WEEK

        # Preseason, offseason trading, and general offseason - trades allowed
        if phase in ("preseason", "offseason_trading", "offseason"):
            return True

        # Default to closed for unknown phases
        return False

    def get_weeks_until_deadline(self, current_week: int) -> Optional[int]:
        """
        Get weeks remaining until trade deadline (during regular season).

        Args:
            current_week: Current week number (1-18)

        Returns:
            Number of weeks until deadline, or None if deadline passed/not applicable
        """
        if current_week > self.TRADE_DEADLINE_WEEK:
            return None
        return self.TRADE_DEADLINE_WEEK - current_week + 1

    # =========================================================================
    # Asset Queries
    # =========================================================================

    def get_tradeable_players(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get players on a team's roster who are eligible for trade.

        Excludes players on IR or with trade restrictions.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dicts with trade-relevant info including:
            - player_id, name, position, overall_rating, age
            - contract_id, contract_years_remaining, cap_hit
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    p.player_id,
                    p.first_name,
                    p.last_name,
                    p.positions as position,
                    json_extract(p.attributes, '$.overall') as overall_rating,
                    ? - CAST(substr(p.birthdate, 1, 4) AS INTEGER) as age,
                    p.years_pro,
                    pc.contract_id,
                    pc.end_year - ? as years_remaining,
                    json_extract(cyd.base_salary, '$') as base_salary,
                    json_extract(cyd.total_cap_hit, '$') as cap_hit
                FROM players p
                LEFT JOIN player_contracts pc ON p.player_id = pc.player_id
                    AND pc.dynasty_id = p.dynasty_id
                    AND pc.is_active = 1
                LEFT JOIN contract_year_details cyd ON pc.contract_id = cyd.contract_id
                    AND cyd.season_year = ?
                WHERE p.dynasty_id = ?
                    AND p.team_id = ?
                    AND COALESCE(p.status, 'active') != 'IR'
                ORDER BY json_extract(p.attributes, '$.overall') DESC, p.positions
            """, (self._season, self._season, self._season, self._dynasty_id, team_id))

            players = []
            for row in cursor.fetchall():
                # Calculate age from years_pro if birthdate not available
                age = row["age"]
                if age is None:
                    age = 22 + (row["years_pro"] or 0)

                players.append({
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "name": f"{row['first_name']} {row['last_name']}",
                    "position": row["position"],
                    "overall_rating": row["overall_rating"] or 70,
                    "age": age,
                    "years_pro": row["years_pro"] or 0,
                    "contract_id": row["contract_id"],
                    "contract_years_remaining": row["years_remaining"],
                    "base_salary": row["base_salary"] or 0,
                    "cap_hit": row["cap_hit"] or 0,
                })

            return players

        finally:
            conn.close()

    def get_tradeable_picks(
        self,
        team_id: int,
        max_future_years: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get draft picks owned by a team (current season + future years).

        Args:
            team_id: Team ID (1-32)
            max_future_years: How many future years of picks to include (default 2)

        Returns:
            List of draft pick dicts with ownership info including:
            - id, season, round, original_team_id, current_team_id
            - was_traded, years_in_future
        """
        conn = self._get_connection()
        try:
            # Calculate year range
            min_season = self._season
            max_season = self._season + max_future_years

            cursor = conn.execute("""
                SELECT
                    id,
                    season,
                    round,
                    original_team_id,
                    current_team_id,
                    acquired_via_trade_id
                FROM draft_pick_ownership
                WHERE dynasty_id = ?
                    AND current_team_id = ?
                    AND season >= ?
                    AND season <= ?
                ORDER BY season, round
            """, (self._dynasty_id, team_id, min_season, max_season))

            picks = []
            for row in cursor.fetchall():
                picks.append({
                    "id": row["id"],
                    "season": row["season"],
                    "round": row["round"],
                    "original_team_id": row["original_team_id"],
                    "current_team_id": row["current_team_id"],
                    "was_traded": row["acquired_via_trade_id"] is not None,
                    "years_in_future": row["season"] - self._season,
                })

            return picks

        finally:
            conn.close()

    # =========================================================================
    # Pick Ownership Initialization
    # =========================================================================

    def initialize_pick_ownership(self, seasons_ahead: int = 3) -> int:
        """
        Initialize draft pick ownership for a dynasty.

        Creates ownership records for current season + future years.
        Each team starts owning their own picks for all 7 rounds.
        This method is idempotent - safe to call multiple times.

        Args:
            seasons_ahead: How many future seasons to initialize (default 3)

        Returns:
            Number of new pick ownership records created
        """
        conn = self._get_connection()
        try:
            records_created = 0

            for year_offset in range(seasons_ahead + 1):
                season = self._season + year_offset

                # Create picks for all 32 teams, rounds 1-7
                for team_id in range(1, 33):
                    for round_num in range(1, 8):
                        cursor = conn.execute("""
                            INSERT OR IGNORE INTO draft_pick_ownership
                            (dynasty_id, season, round, original_team_id, current_team_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (self._dynasty_id, season, round_num, team_id, team_id))
                        records_created += cursor.rowcount

            conn.commit()
            self._logger.info(
                f"Initialized {records_created} draft pick ownership records "
                f"for dynasty {self._dynasty_id}"
            )
            return records_created

        finally:
            conn.close()

    # =========================================================================
    # Trade History Queries
    # =========================================================================

    def get_trade_history(
        self,
        team_id: Optional[int] = None,
        season: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade history with optional filters.

        Args:
            team_id: Filter by team involvement (either side of trade)
            season: Filter by season (defaults to all seasons)
            status: Filter by status ('pending', 'accepted', 'rejected', 'countered')

        Returns:
            List of trade records sorted by most recent first
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT
                    trade_id,
                    season,
                    trade_date,
                    team1_id,
                    team2_id,
                    team1_assets,
                    team2_assets,
                    team1_total_value,
                    team2_total_value,
                    value_ratio,
                    fairness_rating,
                    status,
                    initiating_team_id,
                    rounds_negotiated,
                    created_at,
                    completed_at
                FROM trades
                WHERE dynasty_id = ?
            """
            params: List[Any] = [self._dynasty_id]

            if team_id is not None:
                query += " AND (team1_id = ? OR team2_id = ?)"
                params.extend([team_id, team_id])

            if season is not None:
                query += " AND season = ?"
                params.append(season)

            if status is not None:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)

            trades = []
            for row in cursor.fetchall():
                trades.append({
                    "trade_id": row["trade_id"],
                    "season": row["season"],
                    "trade_date": row["trade_date"],
                    "team1_id": row["team1_id"],
                    "team2_id": row["team2_id"],
                    "team1_assets": json.loads(row["team1_assets"]),
                    "team2_assets": json.loads(row["team2_assets"]),
                    "team1_total_value": row["team1_total_value"],
                    "team2_total_value": row["team2_total_value"],
                    "value_ratio": row["value_ratio"],
                    "fairness_rating": row["fairness_rating"],
                    "status": row["status"],
                    "initiating_team_id": row["initiating_team_id"],
                    "rounds_negotiated": row["rounds_negotiated"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"],
                })

            return trades

        finally:
            conn.close()

    # =========================================================================
    # Value Calculator (Tollgate 2)
    # =========================================================================

    @property
    def _get_value_calculator(self):
        """Lazy-load the trade value calculator."""
        if self._value_calculator is None:
            from src.transactions.trade_value_calculator import TradeValueCalculator
            self._value_calculator = TradeValueCalculator(
                current_year=self._season,
                dynasty_id=self._dynasty_id
            )
        return self._value_calculator

    # =========================================================================
    # Trade Proposal (Tollgate 2)
    # =========================================================================

    def propose_trade(
        self,
        team1_id: int,
        team1_player_ids: List[int],
        team2_id: int,
        team2_player_ids: List[int],
        trade_date: Optional[date] = None,
        team1_pick_ids: Optional[List[int]] = None,
        team2_pick_ids: Optional[List[int]] = None
    ) -> TradeProposal:
        """
        Create a trade proposal with value calculations.

        Args:
            team1_id: Proposing team ID (1-32)
            team1_player_ids: Players team1 is offering
            team2_id: Target team ID (1-32)
            team2_player_ids: Players team2 is offering
            trade_date: Optional trade date (defaults to today)
            team1_pick_ids: Draft pick IDs team1 is offering (from draft_pick_ownership.id)
            team2_pick_ids: Draft pick IDs team2 is offering (from draft_pick_ownership.id)

        Returns:
            TradeProposal with calculated values and fairness rating
        """
        # 1. Validate teams are different
        if team1_id == team2_id:
            raise ValueError("Cannot trade with same team")

        # Default empty lists for picks
        team1_pick_ids = team1_pick_ids or []
        team2_pick_ids = team2_pick_ids or []

        # 2. Build TradeAsset lists with calculated values
        team1_assets = self._build_player_assets(team1_player_ids, acquiring_team=team2_id)
        team2_assets = self._build_player_assets(team2_player_ids, acquiring_team=team1_id)

        # 3. Add pick assets if provided
        if team1_pick_ids:
            team1_assets.extend(self._build_pick_assets(team1_pick_ids, acquiring_team=team2_id))
        if team2_pick_ids:
            team2_assets.extend(self._build_pick_assets(team2_pick_ids, acquiring_team=team1_id))

        # 4. Calculate total values
        team1_total = sum(a.trade_value for a in team1_assets)
        team2_total = sum(a.trade_value for a in team2_assets)

        # 5. Calculate fairness
        value_ratio = team2_total / team1_total if team1_total > 0 else 0.0
        fairness_rating = TradeProposal.calculate_fairness(value_ratio)

        # 6. Create proposal
        proposal = TradeProposal(
            team1_id=team1_id,
            team1_assets=team1_assets,
            team1_total_value=team1_total,
            team2_id=team2_id,
            team2_assets=team2_assets,
            team2_total_value=team2_total,
            value_ratio=value_ratio,
            fairness_rating=fairness_rating,
            proposed_date=str(trade_date or date.today()),
            initiating_team_id=team1_id
        )

        return proposal

    def _build_player_assets(
        self,
        player_ids: List[int],
        acquiring_team: int
    ) -> List[TradeAsset]:
        """Build TradeAsset list from player IDs with calculated values."""
        assets = []
        calculator = self._get_value_calculator

        for player_id in player_ids:
            player = self._get_player_details(player_id)
            if not player:
                raise ValueError(f"Player {player_id} not found in dynasty")

            # Calculate trade value
            trade_value = calculator.calculate_player_value(
                overall_rating=player["overall_rating"],
                position=player["position"],
                age=player["age"],
                contract_years_remaining=player.get("contract_years_remaining"),
                annual_cap_hit=player.get("cap_hit"),
                acquiring_team_id=acquiring_team
            )

            asset = TradeAsset(
                asset_type=AssetType.PLAYER,
                player_id=player_id,
                player_name=player["name"],
                position=player["position"],
                overall_rating=player["overall_rating"],
                age=player["age"],
                years_pro=player.get("years_pro"),
                contract_years_remaining=player.get("contract_years_remaining"),
                annual_cap_hit=player.get("cap_hit"),
                trade_value=trade_value,
                acquiring_team_id=acquiring_team
            )
            assets.append(asset)

        return assets

    def _build_pick_assets(
        self,
        pick_ids: List[int],
        acquiring_team: int
    ) -> List[TradeAsset]:
        """
        Build TradeAsset list from draft pick IDs with calculated values.

        Args:
            pick_ids: List of draft_pick_ownership.id values
            acquiring_team: Team ID that will receive these picks

        Returns:
            List of TradeAsset objects with asset_type=DRAFT_PICK
        """
        assets = []
        calculator = self._get_value_calculator

        for pick_id in pick_ids:
            pick_info = self._get_pick_details(pick_id)
            if not pick_info:
                raise ValueError(f"Draft pick {pick_id} not found in dynasty")

            # Create DraftPick object for value calculation
            draft_pick = DraftPick(
                round=pick_info["round"],
                year=pick_info["season"],
                original_team_id=pick_info["original_team_id"],
                current_team_id=pick_info["current_team_id"]
            )

            # Get team record for pick value estimation
            team_wins = pick_info.get("team_wins", 8)  # Default mid-pack
            team_losses = pick_info.get("team_losses", 8)

            # Calculate trade value
            trade_value = calculator.calculate_pick_value(
                draft_pick=draft_pick,
                team_wins=team_wins,
                team_losses=team_losses
            )

            # Create TradeAsset with pick data
            asset = TradeAsset(
                asset_type=AssetType.DRAFT_PICK,
                draft_pick=draft_pick,
                trade_value=trade_value,
                acquiring_team_id=acquiring_team,
                # Store pick_id in player_id for backward compatibility
                player_id=pick_id,
                player_name=f"Round {pick_info['round']} Pick ({pick_info['season']})"
            )
            assets.append(asset)

        return assets

    def _get_pick_details(self, pick_id: int) -> Optional[Dict[str, Any]]:
        """
        Get draft pick details by pick ownership ID.

        Args:
            pick_id: The draft_pick_ownership.id value

        Returns:
            Dict with pick info or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    dpo.id,
                    dpo.season,
                    dpo.round,
                    dpo.original_team_id,
                    dpo.current_team_id,
                    dpo.acquired_via_trade_id
                FROM draft_pick_ownership dpo
                WHERE dpo.dynasty_id = ? AND dpo.id = ?
            """, (self._dynasty_id, pick_id))

            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Try to get team record for value estimation
                try:
                    from src.game_cycle.database.standings_api import StandingsAPI
                    from src.game_cycle.database.connection import GameCycleDatabase
                    db = GameCycleDatabase(self._db_path)
                    standings_api = StandingsAPI(db)
                    standing = standings_api.get_team_standing(
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        team_id=result["original_team_id"]
                    )
                    if standing:
                        result["team_wins"] = standing.wins
                        result["team_losses"] = standing.losses
                except Exception:
                    pass  # Use defaults if standings unavailable
                return result
            return None
        finally:
            conn.close()

    def _get_player_details(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player details for trade asset creation."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    p.player_id,
                    p.first_name || ' ' || p.last_name as name,
                    p.positions as position,
                    json_extract(p.attributes, '$.overall') as overall_rating,
                    ? - CAST(substr(p.birthdate, 1, 4) AS INTEGER) as age,
                    p.years_pro,
                    p.team_id,
                    pc.contract_id,
                    pc.end_year - ? as contract_years_remaining,
                    json_extract(cyd.total_cap_hit, '$') as cap_hit
                FROM players p
                LEFT JOIN player_contracts pc ON p.player_id = pc.player_id
                    AND pc.dynasty_id = p.dynasty_id AND pc.is_active = 1
                LEFT JOIN contract_year_details cyd ON pc.contract_id = cyd.contract_id
                    AND cyd.season_year = ?
                WHERE p.dynasty_id = ? AND p.player_id = ?
            """, (self._season, self._season, self._season, self._dynasty_id, player_id))

            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Calculate age from years_pro if birthdate not available
                if result["age"] is None:
                    result["age"] = 22 + (result["years_pro"] or 0)
                # Default overall rating if not set
                if result["overall_rating"] is None:
                    result["overall_rating"] = 70
                return result
            return None
        finally:
            conn.close()

    # =========================================================================
    # Trade Execution (Tollgate 2)
    # =========================================================================

    def execute_trade(
        self,
        proposal: TradeProposal,
        trade_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Execute an accepted trade.

        Args:
            proposal: The accepted TradeProposal
            trade_date: Date of trade (defaults to today)

        Returns:
            Dict with trade_id, status, and transferred player/pick info
        """
        actual_date = trade_date or date.today()

        # Collect transfer info for transaction logging (done after commit)
        transfers_to_log: List[Dict[str, Any]] = []
        pick_transfers: List[Dict[str, Any]] = []

        conn = self._get_connection()
        try:
            # 1. Validate trade is still valid (assets still owned by expected teams)
            self._validate_trade_assets(conn, proposal)

            # 2. Record trade in database FIRST (get trade_id)
            trade_id = self._record_trade(conn, proposal, actual_date)

            # 3. Transfer assets from team1 to team2
            for asset in proposal.team1_assets:
                if asset.asset_type == AssetType.PLAYER:
                    player_info = self._transfer_player_db(
                        conn=conn,
                        player_id=asset.player_id,
                        to_team_id=proposal.team2_id
                    )
                    transfers_to_log.append({
                        "player_id": asset.player_id,
                        "player_name": player_info["name"],
                        "position": player_info["position"],
                        "from_team_id": proposal.team1_id,
                        "to_team_id": proposal.team2_id,
                        "trade_id": trade_id
                    })
                elif asset.asset_type == AssetType.DRAFT_PICK:
                    # pick_id stored in player_id field for backward compatibility
                    pick_info = self._transfer_draft_pick(
                        conn=conn,
                        pick_id=asset.player_id,
                        to_team_id=proposal.team2_id,
                        trade_id=trade_id
                    )
                    pick_transfers.append(pick_info)

            # 4. Transfer assets from team2 to team1
            for asset in proposal.team2_assets:
                if asset.asset_type == AssetType.PLAYER:
                    player_info = self._transfer_player_db(
                        conn=conn,
                        player_id=asset.player_id,
                        to_team_id=proposal.team1_id
                    )
                    transfers_to_log.append({
                        "player_id": asset.player_id,
                        "player_name": player_info["name"],
                        "position": player_info["position"],
                        "from_team_id": proposal.team2_id,
                        "to_team_id": proposal.team1_id,
                        "trade_id": trade_id
                    })
                elif asset.asset_type == AssetType.DRAFT_PICK:
                    pick_info = self._transfer_draft_pick(
                        conn=conn,
                        pick_id=asset.player_id,
                        to_team_id=proposal.team1_id,
                        trade_id=trade_id
                    )
                    pick_transfers.append(pick_info)

            # 5. Update trade status to accepted
            conn.execute("""
                UPDATE trades
                SET status = 'accepted', completed_at = CURRENT_TIMESTAMP
                WHERE trade_id = ?
            """, (trade_id,))

            conn.commit()

        except Exception as e:
            conn.rollback()
            self._logger.error(f"Trade execution failed: {e}")
            raise
        finally:
            conn.close()

        # 6. Log player transactions AFTER main transaction commits (avoids DB lock)
        for transfer in transfers_to_log:
            try:
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    transaction_type="TRADE",
                    player_id=transfer["player_id"],
                    player_name=transfer["player_name"],
                    position=transfer["position"],
                    from_team_id=transfer["from_team_id"],
                    to_team_id=transfer["to_team_id"],
                    transaction_date=actual_date,
                    details={
                        "trade_id": transfer["trade_id"],
                        "direction": "outgoing"
                    }
                )
            except Exception as log_error:
                # Log failure shouldn't block trade execution
                self._logger.warning(f"Transaction logging failed: {log_error}")

        # 7. Log pick transactions
        for pick in pick_transfers:
            try:
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    transaction_type="TRADE",
                    player_id=pick["pick_id"],  # Use pick_id as player_id
                    player_name=f"Round {pick['round']} Pick ({pick['season']})",
                    position="PICK",
                    from_team_id=pick["from_team_id"],
                    to_team_id=pick["to_team_id"],
                    transaction_date=actual_date,
                    details={
                        "trade_id": trade_id,
                        "pick_round": pick["round"],
                        "pick_season": pick["season"],
                        "original_team_id": pick["original_team_id"]
                    }
                )
            except Exception as log_error:
                self._logger.warning(f"Pick transaction logging failed: {log_error}")

        self._logger.info(
            f"Trade #{trade_id} executed: Team {proposal.team1_id} <-> Team {proposal.team2_id}"
        )

        # Update player popularity for traded players (Milestone 16)
        # Apply 4-week market adjustment process
        try:
            self._adjust_traded_player_popularity(proposal, transfers_to_log)
        except Exception as pop_error:
            # Don't fail trade execution for popularity calculation errors
            self._logger.warning(f"Failed to adjust popularity for traded players: {pop_error}")

        return {
            "trade_id": trade_id,
            "status": "accepted",
            "team1_players_sent": [a.player_id for a in proposal.team1_assets if a.asset_type == AssetType.PLAYER],
            "team2_players_sent": [a.player_id for a in proposal.team2_assets if a.asset_type == AssetType.PLAYER],
            "team1_picks_sent": [a.player_id for a in proposal.team1_assets if a.asset_type == AssetType.DRAFT_PICK],
            "team2_picks_sent": [a.player_id for a in proposal.team2_assets if a.asset_type == AssetType.DRAFT_PICK],
            "trade_date": str(actual_date)
        }

    def _transfer_player_db(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        to_team_id: int
    ) -> Dict[str, Any]:
        """
        Transfer a player to a new team (database update only).

        Returns player info for transaction logging.
        """
        # 1. Get player name for logging
        cursor = conn.execute("""
            SELECT first_name, last_name, positions
            FROM players WHERE dynasty_id = ? AND player_id = ?
        """, (self._dynasty_id, player_id))
        player = cursor.fetchone()

        # 2. Update player's team_id in players table
        conn.execute("""
            UPDATE players
            SET team_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE dynasty_id = ? AND player_id = ?
        """, (to_team_id, self._dynasty_id, player_id))

        # 3. Update team_rosters table to maintain consistency
        conn.execute("""
            UPDATE team_rosters
            SET team_id = ?
            WHERE dynasty_id = ? AND player_id = ?
        """, (to_team_id, self._dynasty_id, player_id))

        return {
            "name": f"{player['first_name']} {player['last_name']}",
            "position": player['positions']
        }

    def _transfer_draft_pick(
        self,
        conn: sqlite3.Connection,
        pick_id: int,
        to_team_id: int,
        trade_id: int
    ) -> Dict[str, Any]:
        """
        Transfer a draft pick to a new team (database update only).

        Updates draft_pick_ownership.current_team_id and records the trade_id.

        Args:
            conn: Database connection
            pick_id: The draft_pick_ownership.id value
            to_team_id: Team receiving the pick
            trade_id: ID of the trade for audit trail

        Returns:
            Dict with pick info for logging
        """
        # 1. Get pick details for logging
        cursor = conn.execute("""
            SELECT season, round, original_team_id, current_team_id
            FROM draft_pick_ownership
            WHERE dynasty_id = ? AND id = ?
        """, (self._dynasty_id, pick_id))
        pick = cursor.fetchone()

        if not pick:
            raise ValueError(f"Draft pick {pick_id} not found")

        from_team_id = pick["current_team_id"]

        # 2. Update pick ownership
        conn.execute("""
            UPDATE draft_pick_ownership
            SET current_team_id = ?,
                acquired_via_trade_id = ?
            WHERE dynasty_id = ? AND id = ?
        """, (to_team_id, trade_id, self._dynasty_id, pick_id))

        return {
            "pick_id": pick_id,
            "season": pick["season"],
            "round": pick["round"],
            "original_team_id": pick["original_team_id"],
            "from_team_id": from_team_id,
            "to_team_id": to_team_id
        }

    def _validate_trade_assets(
        self,
        conn: sqlite3.Connection,
        proposal: TradeProposal
    ) -> None:
        """Validate all assets are still owned by their expected teams."""
        # Check team1 assets
        for asset in proposal.team1_assets:
            if asset.asset_type == AssetType.PLAYER:
                cursor = conn.execute("""
                    SELECT team_id FROM players
                    WHERE dynasty_id = ? AND player_id = ?
                """, (self._dynasty_id, asset.player_id))
                row = cursor.fetchone()
                if not row or row["team_id"] != proposal.team1_id:
                    raise ValueError(
                        f"Player {asset.player_id} is no longer on team {proposal.team1_id}"
                    )
            elif asset.asset_type == AssetType.DRAFT_PICK:
                # pick_id stored in player_id field
                cursor = conn.execute("""
                    SELECT current_team_id FROM draft_pick_ownership
                    WHERE dynasty_id = ? AND id = ?
                """, (self._dynasty_id, asset.player_id))
                row = cursor.fetchone()
                if not row or row["current_team_id"] != proposal.team1_id:
                    raise ValueError(
                        f"Draft pick {asset.player_id} is no longer owned by team {proposal.team1_id}"
                    )

        # Check team2 assets
        for asset in proposal.team2_assets:
            if asset.asset_type == AssetType.PLAYER:
                cursor = conn.execute("""
                    SELECT team_id FROM players
                    WHERE dynasty_id = ? AND player_id = ?
                """, (self._dynasty_id, asset.player_id))
                row = cursor.fetchone()
                if not row or row["team_id"] != proposal.team2_id:
                    raise ValueError(
                        f"Player {asset.player_id} is no longer on team {proposal.team2_id}"
                    )
            elif asset.asset_type == AssetType.DRAFT_PICK:
                cursor = conn.execute("""
                    SELECT current_team_id FROM draft_pick_ownership
                    WHERE dynasty_id = ? AND id = ?
                """, (self._dynasty_id, asset.player_id))
                row = cursor.fetchone()
                if not row or row["current_team_id"] != proposal.team2_id:
                    raise ValueError(
                        f"Draft pick {asset.player_id} is no longer owned by team {proposal.team2_id}"
                    )

    def _record_trade(
        self,
        conn: sqlite3.Connection,
        proposal: TradeProposal,
        trade_date: date
    ) -> int:
        """Record trade in database and return trade_id."""
        cursor = conn.execute("""
            INSERT INTO trades (
                dynasty_id, season, trade_date,
                team1_id, team2_id,
                team1_assets, team2_assets,
                team1_total_value, team2_total_value,
                value_ratio, fairness_rating,
                status, initiating_team_id, rounds_negotiated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, 0)
        """, (
            self._dynasty_id,
            self._season,
            str(trade_date),
            proposal.team1_id,
            proposal.team2_id,
            json.dumps([self._asset_to_dict(a) for a in proposal.team1_assets]),
            json.dumps([self._asset_to_dict(a) for a in proposal.team2_assets]),
            proposal.team1_total_value,
            proposal.team2_total_value,
            proposal.value_ratio,
            proposal.fairness_rating.value,
            proposal.initiating_team_id or proposal.team1_id
        ))
        return cursor.lastrowid

    def _asset_to_dict(self, asset: TradeAsset) -> Dict[str, Any]:
        """Convert TradeAsset to JSON-serializable dict."""
        base_dict = {
            "asset_type": asset.asset_type.value,
            "player_id": asset.player_id,  # pick_id for draft picks
            "player_name": asset.player_name,
            "trade_value": asset.trade_value
        }

        if asset.asset_type == AssetType.PLAYER:
            base_dict.update({
                "position": asset.position,
                "overall_rating": asset.overall_rating,
                "age": asset.age
            })
        elif asset.asset_type == AssetType.DRAFT_PICK and asset.draft_pick:
            base_dict.update({
                "pick_round": asset.draft_pick.round,
                "pick_year": asset.draft_pick.year,
                "original_team_id": asset.draft_pick.original_team_id
            })

        return base_dict

    # =========================================================================
    # AI Trade Evaluation (Tollgate 3)
    # =========================================================================

    # Untouchable player thresholds (v1.2 - trade realism)
    UNTOUCHABLE_ELITE_MIN_OVR = 90  # Elite players at this OVR are untouchable
    UNTOUCHABLE_ELITE_MAX_AGE = 29  # Under 30 for elite untouchable
    UNTOUCHABLE_QB_MIN_OVR = 85  # Franchise QBs at this OVR are untouchable
    UNTOUCHABLE_QB_MAX_AGE = 31  # Under 32 for franchise QB untouchable

    def _is_untouchable_player(self, player_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if a player should be considered untouchable by AI teams.

        Untouchable criteria (v1.2 - trade realism):
        1. Franchise QB: 85+ OVR and under 32 years old
        2. Elite player: 90+ OVR and under 30 years old

        This prevents AI teams from accepting unrealistic trades like
        "Trade away Lamar Jackson for a 1st round pick."

        Args:
            player_data: Dict with overall_rating, age, position fields

        Returns:
            Tuple of (is_untouchable: bool, reason: str)
        """
        overall = player_data.get("overall_rating") or player_data.get("overall") or 0
        age = player_data.get("age", 99)
        position = str(player_data.get("position", "")).upper()

        # Normalize position (handle JSON array format)
        if position.startswith("["):
            import json as json_lib
            try:
                positions = json_lib.loads(position)
                position = positions[0].upper() if positions else ""
            except (json.JSONDecodeError, IndexError):
                pass

        name = player_data.get("player_name") or player_data.get("name", "Unknown")

        # 1. Franchise QB under 32 is untouchable
        if position == "QB":
            if overall >= self.UNTOUCHABLE_QB_MIN_OVR and age <= self.UNTOUCHABLE_QB_MAX_AGE:
                return True, f"{name} is a franchise quarterback and is not available"

        # 2. Elite players (90+) under 30 are untouchable
        if overall >= self.UNTOUCHABLE_ELITE_MIN_OVR and age <= self.UNTOUCHABLE_ELITE_MAX_AGE:
            return True, f"{name} is a cornerstone player and is not available"

        return False, ""

    def _check_untouchable_in_proposal(
        self,
        proposal: TradeProposal,
        evaluating_team_id: int
    ) -> Tuple[bool, str]:
        """
        Check if the proposal asks an AI team to give up untouchable players.

        Args:
            proposal: The trade proposal
            evaluating_team_id: Team ID making the evaluation

        Returns:
            Tuple of (has_untouchable: bool, rejection_reason: str)
        """
        from src.transactions.models import AssetType

        # Determine which assets the evaluating team would give up
        if evaluating_team_id == proposal.team1_id:
            giving_up = proposal.team1_assets
        else:
            giving_up = proposal.team2_assets

        # Check each player asset
        for asset in giving_up:
            if asset.asset_type == AssetType.PLAYER:
                player_data = {
                    "overall_rating": asset.overall_rating,
                    "age": asset.age,
                    "position": asset.position,
                    "player_name": asset.player_name
                }
                is_untouchable, reason = self._is_untouchable_player(player_data)
                if is_untouchable:
                    return True, reason

        return False, ""

    def _build_team_context(self, team_id: int) -> TeamContext:
        """
        Build TeamContext from database for AI evaluation.

        Uses StandingsAPI for database access (Separation of Concerns).

        Args:
            team_id: Team ID (1-32)

        Returns:
            TeamContext with team's current situation
        """
        from src.game_cycle.database.standings_api import StandingsAPI
        from src.game_cycle.database.connection import GameCycleDatabase

        # Default values
        wins = 0
        losses = 0
        playoff_position = None

        # Use StandingsAPI for standings data
        try:
            db = GameCycleDatabase(self._db_path)
            standings_api = StandingsAPI(db)
            standing = standings_api.get_team_standing(
                dynasty_id=self._dynasty_id,
                season=self._season,
                team_id=team_id
            )
            if standing:
                wins = standing.wins
                losses = standing.losses
                playoff_position = standing.playoff_seed
        except Exception:
            # Standings not available (early season or schema mismatch)
            pass

        # Cap space calculation (simplified - could use a CapAPI in future)
        cap_ceiling = 255_000_000  # Approximate NFL salary cap
        cap_space = cap_ceiling  # Default to full cap space

        return TeamContext(
            team_id=team_id,
            season=self._season,
            wins=wins,
            losses=losses,
            playoff_position=playoff_position,
            cap_space=int(cap_space),
            cap_percentage=cap_space / cap_ceiling if cap_ceiling > 0 else 0.0,
            is_deadline=False,  # Set by caller if needed
            is_offseason=False  # Set by caller if needed
        )

    def _get_gm_archetype(self, team_id: int) -> "GMArchetype":
        """
        Get GMArchetype for a team.

        Currently returns a default balanced GM. Future: load from gm_profiles table.

        Args:
            team_id: Team ID (1-32)

        Returns:
            GMArchetype with personality traits
        """
        from src.team_management.gm_archetype import GMArchetype
        # Default balanced GM archetype
        return GMArchetype(
            name=f"GM Team {team_id}",
            description="Default balanced general manager"
        )

    def evaluate_ai_trade(
        self,
        proposal: TradeProposal,
        ai_team_id: int,
        is_deadline: bool = False,
        is_offseason: bool = False
    ) -> TradeDecision:
        """
        Have an AI team evaluate a trade proposal.

        Uses TradeEvaluator with GM personality traits to determine
        whether to accept, reject, or counter the proposal.

        Args:
            proposal: The trade proposal to evaluate
            ai_team_id: Team ID making the evaluation (must be team1_id or team2_id)
            is_deadline: True if at trade deadline (affects urgency)
            is_offseason: True if in offseason trading period

        Returns:
            TradeDecision with decision type, reasoning, and confidence

        Raises:
            ValueError: If ai_team_id is not part of the proposal
        """
        from src.transactions.trade_evaluator import TradeEvaluator
        from src.transactions.models import TradeDecisionType

        # Validate AI team is part of the proposal
        if ai_team_id not in (proposal.team1_id, proposal.team2_id):
            raise ValueError(
                f"Team {ai_team_id} is not part of this trade proposal "
                f"(teams: {proposal.team1_id}, {proposal.team2_id})"
            )

        # v1.2 Trade Realism: Check for untouchable players first
        # AI teams will never trade away franchise QBs or elite young players
        has_untouchable, rejection_reason = self._check_untouchable_in_proposal(
            proposal, ai_team_id
        )
        if has_untouchable:
            self._logger.info(
                f"Team {ai_team_id} rejected trade: untouchable player "
                f"({rejection_reason})"
            )
            return TradeDecision(
                decision=TradeDecisionType.REJECT,
                reasoning=rejection_reason,
                confidence=1.0  # 100% confident in rejection
            )

        # Build context and archetype for evaluating team
        gm_archetype = self._get_gm_archetype(ai_team_id)
        team_context = self._build_team_context(ai_team_id)
        team_context.is_deadline = is_deadline
        team_context.is_offseason = is_offseason

        # Create evaluator and evaluate (with player veto support - Milestone 6)
        evaluator = TradeEvaluator(
            gm_archetype=gm_archetype,
            team_context=team_context,
            trade_value_calculator=self._get_value_calculator,
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._season
        )

        decision = evaluator.evaluate_proposal(
            proposal=proposal,
            from_perspective_of=ai_team_id
        )

        self._logger.info(
            f"Team {ai_team_id} evaluated trade: {decision.decision.value} "
            f"(confidence: {decision.confidence:.2f})"
        )

        return decision

    # =========================================================================
    # AI Trade Negotiation (Tollgate 3)
    # =========================================================================

    def negotiate_trade(
        self,
        initial_proposal: TradeProposal,
        max_rounds: int = 3,
        is_deadline: bool = False,
        is_offseason: bool = False
    ) -> NegotiationResult:
        """
        Conduct multi-round trade negotiation between two AI teams.

        Uses NegotiatorEngine to alternate evaluations and generate counter-offers
        until one of: acceptance, rejection, max rounds reached, or stalemate.

        Args:
            initial_proposal: Starting proposal from team1
            max_rounds: Maximum negotiation rounds (default 3, plus initial)
            is_deadline: True if at trade deadline
            is_offseason: True if in offseason trading period

        Returns:
            NegotiationResult with success status, final proposal, and history
        """
        from src.transactions.negotiator_engine import NegotiatorEngine

        team1_id = initial_proposal.team1_id
        team2_id = initial_proposal.team2_id

        # Build contexts for both teams
        team1_context = self._build_team_context(team1_id)
        team2_context = self._build_team_context(team2_id)
        team1_context.is_deadline = is_deadline
        team2_context.is_deadline = is_deadline
        team1_context.is_offseason = is_offseason
        team2_context.is_offseason = is_offseason

        # Get GM archetypes
        team1_gm = self._get_gm_archetype(team1_id)
        team2_gm = self._get_gm_archetype(team2_id)

        # Get tradeable assets for counter-offers
        team1_assets = self._get_tradeable_assets_for_negotiation(team1_id)
        team2_assets = self._get_tradeable_assets_for_negotiation(team2_id)

        # Create negotiator engine (uses team1's context as base)
        negotiator = NegotiatorEngine(
            gm_archetype=team1_gm,
            team_context=team1_context,
            trade_value_calculator=self._get_value_calculator,
            asset_pool=team1_assets
        )

        # Run negotiation - negotiate_until_convergence takes both teams' info
        result = negotiator.negotiate_until_convergence(
            initial_proposal=initial_proposal,
            team1_gm=team1_gm,
            team1_context=team1_context,
            team1_asset_pool=team1_assets,
            team2_gm=team2_gm,
            team2_context=team2_context,
            team2_asset_pool=team2_assets
        )

        self._logger.info(
            f"Negotiation complete: {result.termination_reason} "
            f"after {result.rounds_taken} rounds"
        )

        return result

    def _get_tradeable_assets_for_negotiation(
        self,
        team_id: int,
        include_picks: bool = True
    ) -> List[TradeAsset]:
        """
        Get team's tradeable assets (players and picks) for counter-offers.

        Converts player dicts from get_tradeable_players() and pick dicts
        from get_tradeable_picks() into TradeAsset objects with calculated
        trade values.

        Args:
            team_id: Team ID (1-32)
            include_picks: Whether to include draft picks (default True)

        Returns:
            List of TradeAsset objects for negotiation asset pool
        """
        assets = []

        # Get tradeable players
        players = self.get_tradeable_players(team_id)
        for player in players:
            # Calculate trade value
            trade_value = self._get_value_calculator.calculate_player_value(
                overall_rating=extract_overall_rating(player, default=70),
                position=player.get("position", ""),
                age=player.get("age", 25),
                contract_years_remaining=player.get("contract_years_remaining"),
                annual_cap_hit=player.get("cap_hit")
            )

            asset = TradeAsset(
                asset_type=AssetType.PLAYER,
                player_id=player["player_id"],
                player_name=player.get("name", "Unknown"),
                position=player.get("position"),
                overall_rating=extract_overall_rating(player, default=0),
                age=player.get("age"),
                years_pro=player.get("years_pro"),
                contract_years_remaining=player.get("contract_years_remaining"),
                annual_cap_hit=player.get("cap_hit"),
                trade_value=trade_value
            )
            assets.append(asset)

        # Get tradeable draft picks
        if include_picks:
            picks = self.get_tradeable_picks(team_id)
            for pick in picks:
                draft_pick = DraftPick(
                    round=pick["round"],
                    year=pick["season"],
                    original_team_id=pick["original_team_id"],
                    current_team_id=pick["current_team_id"]
                )

                trade_value = self._get_value_calculator.calculate_pick_value(
                    draft_pick=draft_pick,
                    team_wins=8,  # Default mid-pack
                    team_losses=8
                )

                asset = TradeAsset(
                    asset_type=AssetType.DRAFT_PICK,
                    draft_pick=draft_pick,
                    trade_value=trade_value,
                    player_id=pick["id"],  # Store pick_id for reference
                    player_name=f"Round {pick['round']} Pick ({pick['season']})"
                )
                assets.append(asset)

        return assets

    # =========================================================================
    # Player Popularity Integration (Milestone 16)
    # =========================================================================

    def _adjust_traded_player_popularity(
        self,
        proposal: TradeProposal,
        transfers: List[Dict[str, Any]]
    ) -> None:
        """
        Adjust popularity for traded players (Milestone 16).

        Applies 4-week market adjustment process:
        - Week 0: -20% disruption (trade shock)
        - Weeks 1-4: Linear interpolation to new market multiplier
        - Week 5+: Full new market multiplier applied

        Args:
            proposal: The executed trade proposal
            transfers: List of player transfer dicts with player_id, from_team_id, to_team_id

        Note:
            This method catches ImportError gracefully if PopularityCalculator
            is not yet implemented, allowing trades to execute without popularity.
        """
        try:
            from ..services.popularity_calculator import PopularityCalculator
            from ..database.standings_api import StandingsAPI
            from ..database.connection import GameCycleDatabase

            # Create database connection for PopularityCalculator
            gc_db = GameCycleDatabase(self._db_path)
            calculator = PopularityCalculator(gc_db, self._dynasty_id)

            # Get current week from season context
            # During regular season: use actual week
            # During offseason: use week 0 (trade deadline is week 9, offseason trading is week 0)
            current_week = 0  # Default to offseason

            # Attempt to get current week from standings/season state
            try:
                standings_api = StandingsAPI(gc_db)
                standings = standings_api.get_standings(self._dynasty_id, self._season)
                # If standings exist, we're in regular season - estimate week from games played
                if standings and len(standings) > 0:
                    # Rough estimate: use average games played / 32 teams as week indicator
                    # More precise: could check schedule or game results
                    pass  # Keep week 0 for now - can be enhanced later
            except Exception:
                pass  # Use week 0 default

            # Process each transferred player
            for transfer in transfers:
                player_id = transfer.get("player_id")
                old_team_id = transfer.get("from_team_id")
                new_team_id = transfer.get("to_team_id")

                if player_id and old_team_id and new_team_id:
                    calculator.adjust_for_trade(
                        player_id=player_id,
                        old_team_id=old_team_id,
                        new_team_id=new_team_id,
                        current_week=current_week
                    )
                    self._logger.debug(
                        f"Adjusted popularity for player {player_id} "
                        f"traded from team {old_team_id} to team {new_team_id}"
                    )

        except ImportError:
            # PopularityCalculator not yet implemented - silently skip
            self._logger.debug("PopularityCalculator not available - skipping trade popularity adjustment")
        except Exception as e:
            # Log error but don't fail trade execution
            self._logger.warning(f"Failed to adjust popularity for traded players: {e}", exc_info=True)
