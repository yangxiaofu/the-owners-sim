"""
Transaction Service

Handles AI transaction evaluation and execution logic extracted from SeasonCycleController.

Responsibilities:
- Evaluate daily AI trade opportunities for all 32 teams
- Execute approved trade proposals
- Track team records for trade evaluation
- Manage transaction timing validation

This service was extracted to separate transaction concerns from the monolithic
SeasonCycleController (Phase 3: Service Extraction).
"""

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from database.unified_api import UnifiedDatabaseAPI
from src.season.season_constants import PhaseNames
from transactions.models import AssetType

if TYPE_CHECKING:
    # Import for type hints only, avoid runtime import conflicts
    from calendar.calendar_manager import CalendarManager


class TransactionService:
    """
    Service for managing AI-driven transaction evaluation and execution.

    Extracted from SeasonCycleController to improve separation of concerns
    and reduce God Object anti-pattern.
    """

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        calendar: 'CalendarManager',
        transaction_ai: 'TransactionAIManager',
        logger: logging.Logger,
        dynasty_id: str,
        database_path: str,
        season_year: int
    ):
        """
        Initialize Transaction Service.

        Args:
            db: Unified database API (shared connection pool)
            calendar: Calendar manager for date operations
            transaction_ai: AI manager for trade evaluation
            logger: Logger instance
            dynasty_id: Dynasty context for isolation
            database_path: Path to database file
            season_year: Current season year
        """
        self.db = db
        self.calendar = calendar
        self.transaction_ai = transaction_ai
        self.logger = logger
        self.dynasty_id = dynasty_id
        self.database_path = database_path
        self.season_year = season_year

    def evaluate_daily_for_all_teams(
        self,
        current_phase: str,
        current_week: int,
        verbose_logging: bool = False
    ) -> List[Dict]:
        """
        Run transaction AI for all 32 teams.

        Evaluates potential trades for each team and executes approved proposals.
        Trades are allowed during: PRESEASON, REGULAR_SEASON (before Week 9 Tuesday deadline).

        NFL Trading Rules:
        - Allowed: March 12 through Week 9 Tuesday
        - Includes: Offseason, Training Camp, Preseason, Regular Season Weeks 1-9
        - NOT allowed: After trade deadline through end of season/playoffs

        Args:
            current_phase: Current season phase value
            current_week: Current week number (phase-aware)
            verbose_logging: Enable verbose console output

        Returns:
            list: List of executed trade dicts
        """
        from transactions.transaction_timing_validator import TransactionTimingValidator
        from calendar.season_phase_tracker import SeasonPhase

        # Log entry point
        current_date = self.calendar.get_current_date().to_python_date()

        print(f"\n[AI_TRANSACTION_REQUEST] Starting AI transaction evaluation")
        print(f"[AI_TRANSACTION_REQUEST] Date: {current_date} | Phase: {current_phase} | Week: {current_week}")
        self.logger.info(
            f"[AI_TRANSACTION_REQUEST] Starting AI transaction evaluation | "
            f"Date: {current_date} | Phase: {current_phase} | Week: {current_week}"
        )

        # Convert string phase to SeasonPhase enum
        phase_enum = SeasonPhase(current_phase)

        # Check if trades are allowed based on NFL calendar
        validator = TransactionTimingValidator(self.season_year)

        is_allowed, reason = validator.is_trade_allowed(
            current_date=current_date,
            current_phase=current_phase,
            current_week=current_week
        )

        print(f"[AI_TRANSACTION_REQUEST] Trade window: {'ALLOWED' if is_allowed else 'BLOCKED'}")
        if not is_allowed:
            print(f"[AI_TRANSACTION_REQUEST] Reason: {reason}")
        self.logger.info(
            f"[AI_TRANSACTION_REQUEST] Trade window validation: "
            f"{'ALLOWED' if is_allowed else 'BLOCKED'} | Reason: {reason if not is_allowed else 'Within trading window'}"
        )

        if not is_allowed:
            print(f"[AI_TRANSACTION_REQUEST] Exiting - trades not allowed\n")
            return []

        executed_trades = []
        total_proposals = 0
        teams_evaluated = 0

        try:
            current_date = self.calendar.get_current_date()

            # Evaluate all 32 teams
            print("[AI_TRANSACTION_REQUEST] Evaluating all 32 teams for trade opportunities...")
            self.logger.info("[AI_TRANSACTION_REQUEST] Evaluating all 32 teams for trade opportunities")
            for team_id in range(1, 33):
                try:
                    teams_evaluated += 1

                    team_record = self._get_team_record(team_id)

                    # Get trade proposals for this team
                    proposals, _ = self.transaction_ai.evaluate_daily_transactions(
                        team_id=team_id,
                        current_date=str(current_date),
                        season_phase=phase_enum,  # Pass enum, not string
                        team_record=team_record,
                        current_week=current_week
                    )

                    if len(proposals) > 0:
                        print(f"[AI_TRANSACTION_REQUEST] Team {team_id}: {len(proposals)} proposal(s)")
                    self.logger.info(
                        f"[AI_TRANSACTION_REQUEST] Team {team_id} generated {len(proposals)} trade proposal(s)"
                    )
                    total_proposals += len(proposals)

                    # Execute approved proposals
                    # Track players already traded in this batch to prevent duplicate trades
                    traded_players = set()

                    for idx, proposal in enumerate(proposals, 1):
                        # Check if any player in this proposal was already traded
                        team1_player_ids = {asset.player_id for asset in proposal.team1_assets if asset.asset_type == AssetType.PLAYER}
                        team2_player_ids = {asset.player_id for asset in proposal.team2_assets if asset.asset_type == AssetType.PLAYER}
                        all_proposal_players = team1_player_ids | team2_player_ids

                        # Skip if any player already traded
                        if traded_players & all_proposal_players:
                            overlapping_players = traded_players & all_proposal_players
                            print(f"[AI_TRANSACTION_REQUEST] ⚠️  TRADE SKIPPED: Player(s) {overlapping_players} already traded in previous proposal")
                            self.logger.info(f"[AI_TRANSACTION_REQUEST] Skipping trade {idx}/{len(proposals)}: Player overlap with previous trade")
                            continue

                        print(f"[AI_TRANSACTION_REQUEST] Executing trade: Team {proposal.team1_id} ↔ Team {proposal.team2_id}")
                        self.logger.info(
                            f"[AI_TRANSACTION_REQUEST] Attempting to execute trade {idx}/{len(proposals)} for Team {team_id}: "
                            f"Team {proposal.team1_id} ↔ Team {proposal.team2_id}"
                        )

                        # Convert TradeProposal dataclass to dict format expected by execute_trade()
                        trade_dict = {
                            'team1_id': proposal.team1_id,
                            'team2_id': proposal.team2_id,
                            'team1_players': [asset.player_id for asset in proposal.team1_assets if asset.asset_type == AssetType.PLAYER],
                            'team2_players': [asset.player_id for asset in proposal.team2_assets if asset.asset_type == AssetType.PLAYER],
                            'fair_value': proposal.value_ratio
                        }
                        trade_result = self.execute_trade(trade_dict)

                        if trade_result['success']:
                            # Track these players as traded
                            traded_players.update(all_proposal_players)

                            executed_trades.append(trade_result['trade_details'])
                            print(f"[AI_TRANSACTION_REQUEST] ✅ TRADE EXECUTED: Team {proposal.team1_id} ↔ Team {proposal.team2_id}")
                            self.logger.info(
                                f"[AI_TRANSACTION_REQUEST] ✅ TRADE EXECUTED: Team {proposal.team1_id} ↔ Team {proposal.team2_id}"
                            )
                        else:
                            print(f"[AI_TRANSACTION_REQUEST] ❌ TRADE REJECTED: {trade_result.get('error_message', 'Unknown error')}")
                            self.logger.info(
                                f"[AI_TRANSACTION_REQUEST] ❌ TRADE REJECTED: {trade_result.get('error_message', 'Unknown error')}"
                            )

                except Exception as e:
                    print(f"[AI_TRANSACTION_REQUEST] Error evaluating Team {team_id}: {e}")
                    self.logger.error(f"[AI_TRANSACTION_REQUEST] Error evaluating Team {team_id}: {e}")
                    continue

        except Exception as e:
            print(f"[AI_TRANSACTION_REQUEST] FATAL ERROR: {e}")
            self.logger.error(f"[AI_TRANSACTION_REQUEST] FATAL ERROR in AI transaction evaluation: {e}")

        # Final summary
        print(f"\n[AI_TRANSACTION_REQUEST] ===== SUMMARY =====")
        print(f"[AI_TRANSACTION_REQUEST] Teams Evaluated: {teams_evaluated}/32")
        print(f"[AI_TRANSACTION_REQUEST] Total Proposals: {total_proposals}")
        print(f"[AI_TRANSACTION_REQUEST] Trades Executed: {len(executed_trades)}\n")
        self.logger.info(
            f"[AI_TRANSACTION_REQUEST] ===== SUMMARY ===== | "
            f"Teams Evaluated: {teams_evaluated}/32 | "
            f"Total Proposals: {total_proposals} | "
            f"Trades Executed: {len(executed_trades)}"
        )

        return executed_trades

    def execute_trade(self, proposal: dict) -> dict:
        """
        Execute a trade proposal by creating and simulating a PlayerForPlayerTradeEvent.

        Args:
            proposal: Trade proposal dict from TransactionAIManager
                {
                    'team1_id': int,
                    'team2_id': int,
                    'team1_players': [player_ids],
                    'team2_players': [player_ids],
                    'fair_value': float
                }

        Returns:
            dict: {'success': bool, 'error_message': str, 'trade_details': dict}
        """
        try:
            from events.trade_events import PlayerForPlayerTradeEvent
            from calendar.date_models import Date

            # Create trade event
            current_date = self.calendar.get_current_date()

            trade_event = PlayerForPlayerTradeEvent(
                team1_id=proposal['team1_id'],
                team2_id=proposal['team2_id'],
                team1_player_ids=proposal.get('team1_players', []),
                team2_player_ids=proposal.get('team2_players', []),
                season=self.season_year,
                event_date=current_date,
                dynasty_id=self.dynasty_id,
                database_path=self.database_path
            )

            # Execute trade
            result = trade_event.simulate()

            if result.success:
                return {
                    'success': True,
                    'error_message': None,
                    'trade_details': {
                        'team1_id': proposal['team1_id'],
                        'team2_id': proposal['team2_id'],
                        'team1_players': proposal.get('team1_players', []),
                        'team2_players': proposal.get('team2_players', []),
                        'team1_net_cap_change': result.data.get('team1_net_cap_change', 0),
                        'team2_net_cap_change': result.data.get('team2_net_cap_change', 0),
                        'date': str(current_date)
                    }
                }
            else:
                return {
                    'success': False,
                    'error_message': result.error_message,
                    'trade_details': None
                }

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return {
                'success': False,
                'error_message': str(e),
                'trade_details': None
            }

    def _get_team_record(self, team_id: int) -> dict:
        """
        Get current win-loss-tie record for a team.

        Uses existing DatabaseAPI.get_team_standing() method.

        Args:
            team_id: Team ID (1-32)

        Returns:
            dict: {'wins': int, 'losses': int, 'ties': int}
        """
        try:
            # Use existing, tested API method
            standing = self.db.standings_get_team(
                team_id=team_id,
                season=self.season_year,
                season_type=PhaseNames.DB_REGULAR_SEASON
            )

            if standing:
                return {
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'ties': standing.ties
                }
            else:
                # No record yet - return zeros (common during preseason)
                return {'wins': 0, 'losses': 0, 'ties': 0}

        except Exception as e:
            self.logger.error(f"Error getting record for team {team_id}: {e}")
            return {'wins': 0, 'losses': 0, 'ties': 0}
