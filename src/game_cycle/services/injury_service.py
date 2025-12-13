"""
Injury Service - Core injury management for game cycle.

Handles:
- Recording new injuries
- Querying active/historical injuries
- Recovery processing
- IR placement/activation (NFL rules)
- Player availability tracking
"""

import json
import logging
import random
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from src.game_cycle.models.injury_models import (
    INJURY_SEVERITY_WEEKS,
    INJURY_TYPE_SEVERITY_RANGE,
    INJURY_TYPE_TO_BODY_PART,
    BodyPart,
    Injury,
    InjurySeverity,
    InjuryType,
)
from src.persistence.transaction_logger import TransactionLogger

from .injury_risk_profiles import POSITION_INJURY_RISKS, get_risk_profile


class InjuryService:
    """Manages all injury-related operations."""

    # NFL IR Rules
    IR_MINIMUM_GAMES = 4
    IR_RETURN_SLOTS_PER_SEASON = 8

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize InjuryService.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)
        self._transaction_logger = TransactionLogger(db_path)

    # =========================================================================
    # Core CRUD Methods
    # =========================================================================

    def record_injury(self, injury: Injury) -> int:
        """
        Record a new injury to database.

        Args:
            injury: Injury dataclass instance

        Returns:
            injury_id of created record

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        try:
            db_dict = injury.to_db_dict()
            cursor = conn.execute("""
                INSERT INTO player_injuries (
                    dynasty_id, player_id, season, week_occurred,
                    injury_type, body_part, severity,
                    estimated_weeks_out, occurred_during, game_id,
                    play_description, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self._dynasty_id,
                db_dict['player_id'],
                db_dict['season'],
                db_dict['week_occurred'],
                db_dict['injury_type'],
                db_dict['body_part'],
                db_dict['severity'],
                db_dict['estimated_weeks_out'],
                db_dict['occurred_during'],
                db_dict.get('game_id'),
                db_dict.get('play_description'),
                1  # is_active = True
            ))
            conn.commit()
            injury_id = cursor.lastrowid

            # Log transaction (optional - may fail if using separate database)
            try:
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    transaction_type="INJURY",
                    player_id=injury.player_id,
                    player_name=injury.player_name,
                    position=None,
                    from_team_id=injury.team_id,
                    to_team_id=injury.team_id,
                    transaction_date=date.today(),
                    details={
                        'injury_type': injury.injury_type.value,
                        'body_part': injury.body_part.value,
                        'severity': injury.severity.value,
                        'weeks_out': injury.weeks_out,
                        'occurred_during': injury.occurred_during
                    }
                )
            except Exception as tx_error:
                # Transaction logging is optional - don't fail core functionality
                self._logger.warning(f"Could not log injury transaction: {tx_error}")

            self._logger.info(
                f"Recorded injury: {injury.player_name} - "
                f"{injury.display_name} ({injury.severity.value}), "
                f"{injury.weeks_out} weeks"
            )
            return injury_id

        except Exception as e:
            conn.rollback()
            self._logger.error(f"Failed to record injury: {e}")
            raise
        finally:
            conn.close()

    def get_active_injuries(self, team_id: Optional[int] = None) -> List[Injury]:
        """
        Get all active injuries, optionally filtered by team.

        Args:
            team_id: Optional team ID to filter results

        Returns:
            List of active Injury instances
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            if team_id:
                rows = conn.execute("""
                    SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                           p.team_id
                    FROM player_injuries pi
                    JOIN players p ON pi.dynasty_id = p.dynasty_id
                                   AND pi.player_id = p.player_id
                    WHERE pi.dynasty_id = ?
                      AND pi.is_active = 1
                      AND p.team_id = ?
                    ORDER BY pi.week_occurred DESC
                """, (self._dynasty_id, team_id)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                           p.team_id
                    FROM player_injuries pi
                    JOIN players p ON pi.dynasty_id = p.dynasty_id
                                   AND pi.player_id = p.player_id
                    WHERE pi.dynasty_id = ? AND pi.is_active = 1
                    ORDER BY pi.week_occurred DESC
                """, (self._dynasty_id,)).fetchall()

            return [Injury.from_db_row(dict(row)) for row in rows]
        finally:
            conn.close()

    def get_player_injury_history(self, player_id: int) -> List[Injury]:
        """
        Get all injuries (active and healed) for a player.

        Args:
            player_id: Player ID to query

        Returns:
            List of all Injury instances for the player
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                       p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ? AND pi.player_id = ?
                ORDER BY pi.season DESC, pi.week_occurred DESC
            """, (self._dynasty_id, player_id)).fetchall()

            return [Injury.from_db_row(dict(row)) for row in rows]
        finally:
            conn.close()

    def check_injury_recovery(self, current_week: int) -> List[Injury]:
        """
        Check which players are ready to return from injury.

        Args:
            current_week: Current week number in season

        Returns:
            List of injuries where player should be healed
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                       p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ?
                  AND pi.season = ?
                  AND pi.is_active = 1
                  AND pi.ir_placement_date IS NULL
                  AND (pi.week_occurred + pi.estimated_weeks_out) <= ?
            """, (self._dynasty_id, self._season, current_week)).fetchall()

            return [Injury.from_db_row(dict(row)) for row in rows]
        finally:
            conn.close()

    def clear_injury(self, injury_id: int, actual_weeks: Optional[int] = None) -> None:
        """
        Mark injury as healed.

        Args:
            injury_id: ID of injury to clear
            actual_weeks: Optional actual weeks missed (defaults to estimated)

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        try:
            if actual_weeks is not None:
                conn.execute("""
                    UPDATE player_injuries
                    SET is_active = 0, actual_weeks_out = ?
                    WHERE injury_id = ? AND dynasty_id = ?
                """, (actual_weeks, injury_id, self._dynasty_id))
            else:
                conn.execute("""
                    UPDATE player_injuries
                    SET is_active = 0, actual_weeks_out = estimated_weeks_out
                    WHERE injury_id = ? AND dynasty_id = ?
                """, (injury_id, self._dynasty_id))
            conn.commit()
            self._logger.info(f"Cleared injury {injury_id}")
        except Exception as e:
            conn.rollback()
            self._logger.error(f"Failed to clear injury: {e}")
            raise
        finally:
            conn.close()

    # =========================================================================
    # Injury Generation Methods
    # =========================================================================

    def generate_injury(
        self,
        player: Dict[str, Any],
        week: int,
        occurred_during: str,
        game_id: Optional[str] = None
    ) -> Optional[Injury]:
        """
        Generate an injury for a player based on risk factors.

        Rolls for injury occurrence and generates type/severity if injured.

        Args:
            player: Player dict with id, name, position, attributes
            week: Current week number
            occurred_during: 'game' or 'practice'
            game_id: Optional game ID if game injury

        Returns:
            Injury instance if injury occurred, None otherwise
        """
        position = self._get_position(player)
        durability = self._get_durability(player)
        age = self._calculate_age(player)
        injury_history = len(self.get_player_injury_history(player['player_id']))

        # Calculate injury probability
        probability = self.calculate_injury_probability(
            position=position,
            durability=durability,
            age=age,
            injury_history_count=injury_history,
            context=occurred_during
        )

        # Roll for injury
        if random.random() > probability:
            return None  # No injury

        # Generate injury details
        risk_profile = get_risk_profile(position)
        injury_type = self._select_injury_type(risk_profile)
        severity = self._select_severity(injury_type)
        weeks_out = self._calculate_weeks_out(severity)
        body_part = INJURY_TYPE_TO_BODY_PART[injury_type]

        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        player_name = f"{first_name} {last_name}".strip() or f"Player {player['player_id']}"

        return Injury(
            player_id=player['player_id'],
            player_name=player_name,
            team_id=player.get('team_id', 0),
            injury_type=injury_type,
            body_part=body_part,
            severity=severity,
            weeks_out=weeks_out,
            week_occurred=week,
            season=self._season,
            occurred_during=occurred_during,
            game_id=game_id
        )

    def calculate_injury_probability(
        self,
        position: str,
        durability: int,
        age: int,
        injury_history_count: int,
        context: str
    ) -> float:
        """
        Calculate injury probability for a player.

        Formula:
        P = base_chance * durability_mod * age_mod * history_mod * context_mod

        Args:
            position: Player's position
            durability: Durability rating (0-100)
            age: Player's age
            injury_history_count: Number of previous injuries
            context: 'game' or 'practice'

        Returns:
            Injury probability (0.0 - 1.0)
        """
        risk_profile = get_risk_profile(position)
        base = risk_profile.base_injury_chance

        # Durability modifier: 100 durability = 0.5x, 50 = 1.0x, 0 = 1.5x
        durability_mod = 1.5 - (durability / 100)

        # Age modifier: Under 26 = 0.9x, 26-30 = 1.0x, over 30 = +3% per year
        if age < 26:
            age_mod = 0.9
        elif age <= 30:
            age_mod = 1.0
        else:
            age_mod = 1.0 + (age - 30) * 0.03

        # History modifier: Each past injury adds 5%
        history_mod = 1.0 + (injury_history_count * 0.05)

        # Context modifier: Practice injuries are less common
        context_mod = 0.3 if context == 'practice' else 1.0

        return base * durability_mod * age_mod * history_mod * context_mod

    def _select_injury_type(self, risk_profile) -> InjuryType:
        """
        Select injury type weighted toward common injuries.

        Args:
            risk_profile: InjuryRisk profile for position

        Returns:
            Selected InjuryType
        """
        # 70% chance of common injury, 30% any injury
        if random.random() < 0.7 and risk_profile.common_injuries:
            return random.choice(risk_profile.common_injuries)
        return random.choice(list(InjuryType))

    def _select_severity(self, injury_type: InjuryType) -> InjurySeverity:
        """
        Select severity based on injury type's valid range.

        Args:
            injury_type: Type of injury

        Returns:
            Selected severity level
        """
        valid_severities = INJURY_TYPE_SEVERITY_RANGE.get(
            injury_type,
            list(InjurySeverity)
        )
        # Weight toward less severe (60% first option, 30% second, etc.)
        weights = [0.6, 0.3, 0.08, 0.02][:len(valid_severities)]
        return random.choices(valid_severities, weights=weights)[0]

    def _calculate_weeks_out(self, severity: InjurySeverity) -> int:
        """
        Calculate weeks out based on severity.

        Args:
            severity: Injury severity level

        Returns:
            Number of weeks player will miss
        """
        min_weeks, max_weeks = INJURY_SEVERITY_WEEKS[severity]
        return random.randint(min_weeks, max_weeks)

    # =========================================================================
    # Availability Methods
    # =========================================================================

    def get_unavailable_players(self, team_id: int) -> List[int]:
        """
        Get player_ids who cannot play (injured or on IR).

        Args:
            team_id: Team ID to check

        Returns:
            List of unavailable player IDs
        """
        injuries = self.get_active_injuries(team_id)
        return [injury.player_id for injury in injuries]

    def is_player_available(self, player_id: int) -> bool:
        """
        Check if a specific player is available to play.

        Args:
            player_id: Player ID to check

        Returns:
            True if player has no active injuries
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            result = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM player_injuries
                WHERE dynasty_id = ? AND player_id = ? AND is_active = 1
            """, (self._dynasty_id, player_id)).fetchone()
            return result['cnt'] == 0
        finally:
            conn.close()

    def get_injury_by_id(self, injury_id: int) -> Optional[Injury]:
        """
        Get a specific injury by ID.

        Args:
            injury_id: ID of injury to retrieve

        Returns:
            Injury instance or None if not found
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("""
                SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                       p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.injury_id = ? AND pi.dynasty_id = ?
            """, (injury_id, self._dynasty_id)).fetchone()

            if row:
                return Injury.from_db_row(dict(row))
            return None
        finally:
            conn.close()

    # =========================================================================
    # IR Methods (Tollgate 5 - Full NFL IR Compliance)
    # =========================================================================

    def place_on_ir(self, player_id: int, injury_id: int) -> bool:
        """
        Place player on Injured Reserve.

        NFL Rules Enforced:
        - Injury must be estimated >= 4 weeks (IR_MINIMUM_GAMES)
        - Updates roster_status to 'injured_reserve'
        - Records IR placement date

        Args:
            player_id: Player to place on IR
            injury_id: Associated injury ID

        Returns:
            True if successful, False if validation fails

        Raises:
            sqlite3.Error: If database operation fails
        """
        # 1. Validate injury exists and meets minimum
        injury = self.get_injury_by_id(injury_id)
        if not injury:
            self._logger.warning(f"Injury {injury_id} not found")
            return False

        if injury.weeks_out < self.IR_MINIMUM_GAMES:
            self._logger.info(
                f"Injury {injury_id} does not meet IR minimum "
                f"({injury.weeks_out} < {self.IR_MINIMUM_GAMES} weeks)"
            )
            return False

        if injury.on_ir:
            self._logger.info(f"Player {player_id} already on IR")
            return False

        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # 2. Update injury record with IR placement
            conn.execute("""
                UPDATE player_injuries
                SET ir_placement_date = date('now')
                WHERE injury_id = ? AND dynasty_id = ?
            """, (injury_id, self._dynasty_id))

            # 3. Update roster status to injured_reserve
            conn.execute("""
                UPDATE team_rosters
                SET roster_status = 'injured_reserve'
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))

            conn.commit()

            # 4. Log transaction
            try:
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    transaction_type="IR_PLACEMENT",
                    player_id=player_id,
                    player_name=injury.player_name,
                    position=None,
                    from_team_id=injury.team_id,
                    to_team_id=injury.team_id,
                    transaction_date=date.today(),
                    details={
                        'injury_type': injury.injury_type.value,
                        'severity': injury.severity.value,
                        'weeks_out': injury.weeks_out,
                    }
                )
            except Exception as tx_error:
                self._logger.warning(f"Could not log IR placement transaction: {tx_error}")

            self._logger.info(f"Placed player {player_id} on IR for injury {injury_id}")
            return True

        except Exception as e:
            conn.rollback()
            self._logger.error(f"Failed to place player on IR: {e}")
            raise
        finally:
            conn.close()

    def activate_from_ir(self, player_id: int, current_week: Optional[int] = None) -> bool:
        """
        Activate player from Injured Reserve.

        NFL Rules Enforced:
        - Must have been on IR for minimum 4 games
        - Uses one of 8 season IR-return slots
        - Fails if no slots remaining

        Args:
            player_id: Player to activate
            current_week: Current week number (optional, fetched if not provided)

        Returns:
            True if successful, False if validation fails

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # 1. Get the player's active IR injury
            row = conn.execute("""
                SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                       p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ? AND pi.player_id = ?
                  AND pi.ir_placement_date IS NOT NULL
                  AND pi.ir_return_date IS NULL
                  AND pi.is_active = 1
                ORDER BY pi.ir_placement_date DESC
                LIMIT 1
            """, (self._dynasty_id, player_id)).fetchone()

            if not row:
                self._logger.warning(f"No active IR injury found for player {player_id}")
                return False

            team_id = row['team_id']
            injury_id = row['injury_id']
            player_name = row['player_name']
            placement_week = row['week_occurred']

            # 2. Check minimum IR time (4 games)
            if current_week is None:
                current_week = self._get_current_week()
            weeks_on_ir = current_week - placement_week

            if weeks_on_ir < self.IR_MINIMUM_GAMES:
                self._logger.info(
                    f"Player {player_id} has not been on IR long enough "
                    f"({weeks_on_ir} < {self.IR_MINIMUM_GAMES} weeks)"
                )
                return False

            # 3. Check IR return slots available
            slots_remaining = self.get_ir_return_slots_remaining(team_id)
            if slots_remaining <= 0:
                self._logger.warning(
                    f"Team {team_id} has no IR return slots remaining"
                )
                return False

            # 3.5 Check if team has roster space (53-man limit)
            active_roster_count = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
            """, (self._dynasty_id, team_id)).fetchone()[0]

            ROSTER_LIMIT = 53
            if active_roster_count >= ROSTER_LIMIT:
                self._logger.warning(
                    f"Cannot activate player {player_id} from IR: "
                    f"Team {team_id} has {active_roster_count} active players (limit: {ROSTER_LIMIT}). "
                    f"Must cut a player first."
                )
                return False

            # 4. Update injury record
            conn.execute("""
                UPDATE player_injuries
                SET ir_return_date = date('now'), is_active = 0
                WHERE injury_id = ? AND dynasty_id = ?
            """, (injury_id, self._dynasty_id))

            # 5. Update roster status back to active
            conn.execute("""
                UPDATE team_rosters
                SET roster_status = 'active'
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))

            # 6. Increment IR return slots used
            conn.execute("""
                INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(dynasty_id, team_id, season)
                DO UPDATE SET ir_return_slots_used = ir_return_slots_used + 1
            """, (self._dynasty_id, team_id, self._season))

            conn.commit()

            # 7. Log transaction
            try:
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    transaction_type="IR_ACTIVATION",
                    player_id=player_id,
                    player_name=player_name,
                    position=None,
                    from_team_id=team_id,
                    to_team_id=team_id,
                    transaction_date=date.today(),
                    details={
                        'weeks_on_ir': weeks_on_ir,
                        'slots_remaining': slots_remaining - 1,
                    }
                )
            except Exception as tx_error:
                self._logger.warning(f"Could not log IR activation transaction: {tx_error}")

            self._logger.info(
                f"Activated player {player_id} from IR "
                f"(team {team_id} has {slots_remaining - 1} slots remaining)"
            )
            return True

        except Exception as e:
            conn.rollback()
            self._logger.error(f"Failed to activate player from IR: {e}")
            raise
        finally:
            conn.close()

    def can_activate_from_ir(self, player_id: int, current_week: Optional[int] = None) -> Dict[str, Any]:
        """
        Check if player can be activated from IR (without executing).

        Useful for UI pre-validation to show appropriate status/messaging.

        Args:
            player_id: Player ID to check
            current_week: Current week number (optional, fetched if not provided)

        Returns:
            Dict with:
                - can_activate: bool
                - reason: str (if cannot activate)
                - roster_count: int
                - slots_remaining: int
                - weeks_on_ir: int
        """
        result = {
            "can_activate": False,
            "reason": None,
            "roster_count": 0,
            "slots_remaining": 0,
            "weeks_on_ir": 0,
        }

        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # Get player's active IR injury
            row = conn.execute("""
                SELECT pi.*, p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ? AND pi.player_id = ?
                  AND pi.ir_placement_date IS NOT NULL
                  AND pi.ir_return_date IS NULL
                  AND pi.is_active = 1
                LIMIT 1
            """, (self._dynasty_id, player_id)).fetchone()

            if not row:
                result["reason"] = "Player not found on IR"
                return result

            team_id = row['team_id']
            placement_week = row['week_occurred']

            if current_week is None:
                current_week = self._get_current_week()

            weeks_on_ir = current_week - placement_week
            result["weeks_on_ir"] = weeks_on_ir

            # Check minimum IR time
            if weeks_on_ir < self.IR_MINIMUM_GAMES:
                result["reason"] = f"Must be on IR for {self.IR_MINIMUM_GAMES} weeks (currently {weeks_on_ir})"
                return result

            # Check IR slots
            slots_remaining = self.get_ir_return_slots_remaining(team_id)
            result["slots_remaining"] = slots_remaining
            if slots_remaining <= 0:
                result["reason"] = "No IR return slots remaining (0/8)"
                return result

            # Check roster space
            roster_count = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
            """, (self._dynasty_id, team_id)).fetchone()[0]
            result["roster_count"] = roster_count

            ROSTER_LIMIT = 53
            if roster_count >= ROSTER_LIMIT:
                result["reason"] = f"Roster full ({roster_count}/53). Must cut a player first."
                return result

            result["can_activate"] = True
            return result
        finally:
            conn.close()

    def get_ir_return_slots_remaining(self, team_id: int) -> int:
        """
        Get remaining IR-return slots for team this season.

        Args:
            team_id: Team ID to check

        Returns:
            Number of remaining IR activation slots (0-8)
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            result = conn.execute("""
                SELECT ir_return_slots_used
                FROM ir_tracking
                WHERE dynasty_id = ? AND team_id = ? AND season = ?
            """, (self._dynasty_id, team_id, self._season)).fetchone()

            if result:
                return self.IR_RETURN_SLOTS_PER_SEASON - result['ir_return_slots_used']
            return self.IR_RETURN_SLOTS_PER_SEASON
        finally:
            conn.close()

    def get_players_on_ir(self, team_id: int) -> List[Injury]:
        """
        Get all players currently on IR for a team.

        Args:
            team_id: Team ID to check

        Returns:
            List of injuries for players on IR
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT pi.*, p.first_name || ' ' || p.last_name as player_name,
                       p.team_id
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ?
                  AND pi.is_active = 1
                  AND pi.ir_placement_date IS NOT NULL
                  AND pi.ir_return_date IS NULL
                  AND p.team_id = ?
                ORDER BY pi.ir_placement_date DESC
            """, (self._dynasty_id, team_id)).fetchall()

            return [Injury.from_db_row(dict(row)) for row in rows]
        finally:
            conn.close()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_position(self, player: Dict) -> str:
        """Extract primary position from player dict."""
        positions = player.get('positions', [])
        if isinstance(positions, str):
            try:
                positions = json.loads(positions)
            except json.JSONDecodeError:
                positions = [positions]
        if isinstance(positions, list) and positions:
            return positions[0]
        return 'WR'  # Default

    def _get_durability(self, player: Dict) -> int:
        """Extract durability from player attributes."""
        attrs = player.get('attributes', {})
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except json.JSONDecodeError:
                attrs = {}
        return attrs.get('durability', 75)

    def _calculate_age(self, player: Dict) -> int:
        """Calculate player age from birthdate."""
        birthdate = player.get('birthdate')
        if not birthdate:
            return 25  # Default
        try:
            birth_year = int(str(birthdate).split('-')[0])
            return self._season - birth_year
        except (ValueError, IndexError):
            return 25

    def _get_current_week(self) -> int:
        """Get current week from dynasty_state table."""
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("""
                SELECT current_week FROM dynasty_state
                WHERE dynasty_id = ?
            """, (self._dynasty_id,)).fetchone()

            return row['current_week'] if row else 1
        finally:
            conn.close()

    # =========================================================================
    # AI GM IR Management
    # =========================================================================

    def process_ai_ir_management(
        self,
        user_team_id: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        Process IR placements and activations for all AI teams.

        Called weekly during regular season. AI teams will:
        1. Place severely injured players on IR (4+ weeks out)
        2. Activate recovered players from IR if slots available

        Args:
            user_team_id: Team to skip (user controls their own IR)
            current_week: Current week number (1-18)

        Returns:
            Dict with ir_placements, ir_activations, events lists
        """
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        all_placements = []
        all_activations = []
        events = []

        for team in all_teams:
            team_id = team.team_id

            # Skip user's team - they manage their own IR
            if team_id == user_team_id:
                continue

            # Process IR placements for this team
            placements = self._process_team_ir_placements(team_id)
            if placements:
                all_placements.extend(placements)
                events.append(
                    f"{team.abbreviation} placed {len(placements)} player(s) on IR"
                )

            # Process IR activations for this team
            activations = self._process_team_ir_activations(team_id, current_week)
            if activations:
                all_activations.extend(activations)
                events.append(
                    f"{team.abbreviation} activated {len(activations)} player(s) from IR"
                )

        self._logger.info(
            f"AI IR management complete: "
            f"{len(all_placements)} placements, "
            f"{len(all_activations)} activations"
        )

        return {
            "ir_placements": all_placements,
            "ir_activations": all_activations,
            "events": events,
            "total_placements": len(all_placements),
            "total_activations": len(all_activations),
        }

    def _process_team_ir_placements(self, team_id: int) -> List[Dict[str, Any]]:
        """
        AI logic: Place eligible injured players on IR.

        Criteria for IR placement:
        - Not already on IR
        - Injury severity is SEVERE or SEASON_ENDING
        - OR estimated_weeks_out >= IR_MINIMUM_GAMES (4)
        """
        placements = []
        active_injuries = self.get_active_injuries(team_id)

        for injury in active_injuries:
            # Skip if already on IR
            if injury.on_ir:
                continue

            # Check if eligible for IR (severe enough or long enough)
            should_place = (
                injury.severity in [InjurySeverity.SEVERE, InjurySeverity.SEASON_ENDING]
                or injury.weeks_out >= self.IR_MINIMUM_GAMES
            )

            if should_place:
                success = self.place_on_ir(injury.player_id, injury.injury_id)
                if success:
                    placements.append({
                        "player_id": injury.player_id,
                        "player_name": injury.player_name,
                        "team_id": team_id,
                        "injury_type": injury.injury_type.value,
                        "severity": injury.severity.value,
                        "weeks_out": injury.weeks_out,
                    })

        return placements

    def _process_team_ir_activations(
        self,
        team_id: int,
        current_week: int
    ) -> List[Dict[str, Any]]:
        """
        AI logic: Activate recovered players from IR.

        Criteria for activation:
        - Currently on IR
        - Estimated return week has passed
        - Team has IR return slots remaining
        - Team has roster space (< 53 active players)
        """
        activations = []

        # Check slots first
        slots_remaining = self.get_ir_return_slots_remaining(team_id)
        if slots_remaining <= 0:
            return []

        # Check roster space
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        try:
            roster_count = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
            """, (self._dynasty_id, team_id)).fetchone()[0]
        finally:
            conn.close()

        ROSTER_LIMIT = 53
        if roster_count >= ROSTER_LIMIT:
            self._logger.info(
                f"Team {team_id} cannot activate from IR: roster full ({roster_count}/53)"
            )
            return []

        # Get players on IR
        ir_players = self.get_players_on_ir(team_id)

        for injury in ir_players:
            if slots_remaining <= 0:
                break

            # Check if player should be healthy (return week passed)
            if injury.estimated_return_week <= current_week:
                success = self.activate_from_ir(injury.player_id, current_week)
                if success:
                    activations.append({
                        "player_id": injury.player_id,
                        "player_name": injury.player_name,
                        "team_id": team_id,
                        "injury_type": injury.injury_type.value,
                        "weeks_missed": current_week - injury.week_occurred,
                    })
                    slots_remaining -= 1

        return activations

    # =========================================================================
    # IR Activation Roster Management (Milestone 5 Enhancement)
    # =========================================================================

    def get_weekly_ir_eligible_players(
        self,
        team_id: int,
        current_week: int
    ) -> List[Dict[str, Any]]:
        """
        Get all players eligible to return from IR this week.

        This method is used for the weekly IR activation UI to show which players
        can potentially be activated. It checks all IR eligibility criteria except
        roster space (that's handled separately in the activation flow).

        Eligibility criteria:
        - On IR for 4+ weeks (NFL minimum)
        - IR return slots available for the team (8 per season max)
        - Injury recovery timeline suggests readiness

        Args:
            team_id: Team ID to check
            current_week: Current week number

        Returns:
            List of dicts with player info:
            {
                "player_id": int,
                "player_name": str,
                "position": str,
                "overall": int,
                "weeks_on_ir": int,
                "injury_type": str,
                "injury_id": int,
                "estimated_return_week": int,
                "body_part": str
            }
        """
        # Check IR return slots first
        slots_remaining = self.get_ir_return_slots_remaining(team_id)
        if slots_remaining <= 0:
            self._logger.info(
                f"Team {team_id} has no IR return slots remaining (0/{self.IR_RETURN_SLOTS_PER_SEASON})"
            )
            return []

        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT
                    pi.injury_id,
                    pi.player_id,
                    p.first_name || ' ' || p.last_name as player_name,
                    p.position,
                    p.overall,
                    pi.week_occurred,
                    pi.injury_type,
                    pi.body_part,
                    pi.estimated_weeks_out,
                    pi.ir_placement_date
                FROM player_injuries pi
                JOIN players p ON pi.dynasty_id = p.dynasty_id
                               AND pi.player_id = p.player_id
                WHERE pi.dynasty_id = ?
                  AND p.team_id = ?
                  AND pi.ir_placement_date IS NOT NULL
                  AND pi.ir_return_date IS NULL
                  AND pi.is_active = 1
                ORDER BY pi.week_occurred ASC
            """, (self._dynasty_id, team_id)).fetchall()

            eligible = []
            for row in rows:
                weeks_on_ir = current_week - row['week_occurred']

                # Must meet minimum IR time (4 games)
                if weeks_on_ir < self.IR_MINIMUM_GAMES:
                    continue

                estimated_return_week = row['week_occurred'] + row['estimated_weeks_out']

                eligible.append({
                    "injury_id": row['injury_id'],
                    "player_id": row['player_id'],
                    "player_name": row['player_name'],
                    "position": row['position'],
                    "overall": row['overall'],
                    "weeks_on_ir": weeks_on_ir,
                    "injury_type": row['injury_type'],
                    "body_part": row['body_part'],
                    "estimated_return_week": estimated_return_week
                })

            return eligible

        finally:
            conn.close()

    def get_cut_candidates_for_activation(
        self,
        team_id: int,
        num_activations: int
    ) -> List[Dict[str, Any]]:
        """
        Get roster players who could be cut to make room for IR activations.

        Uses the same player value calculation as RosterCutsService:
        - value_score = (position_multiplier × overall) - (cap_hit / 1_000_000)
        - Excludes protected players (position minimums)
        - Sorts by value (lowest first = best cut candidates)

        Args:
            team_id: Team ID to check
            num_activations: Number of activations needed (determines how many candidates to return)

        Returns:
            List of dicts with player info:
            {
                "player_id": int,
                "player_name": str,
                "position": str,
                "age": int,
                "overall": int,
                "cap_hit": int,
                "value_score": float,
                "protected": bool,
                "protection_reason": str (if protected)
            }
        """
        # Lazy import to avoid circular dependency
        from .roster_cuts_service import RosterCutsService

        # Use RosterCutsService to get full roster with value calculations
        roster_cuts_service = RosterCutsService(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._season
        )

        # Get full roster with value scores (already sorted by value)
        roster_with_values = roster_cuts_service.get_team_roster_for_cuts(team_id)

        # Get protected players (position minimums)
        protected_player_ids = roster_cuts_service._get_protected_players(roster_with_values)

        # Mark protected status and add to results
        candidates = []
        for player in roster_with_values:
            is_protected = player['player_id'] in protected_player_ids

            candidate = {
                "player_id": player['player_id'],
                "player_name": player['name'],
                "position": player['position'],
                "age": player['age'],
                "overall": player['overall'],
                "cap_hit": player['cap_hit'],
                "value_score": player['value_score'],
                "protected": is_protected,
            }

            if is_protected:
                candidate["protection_reason"] = "Position minimum requirement"

            candidates.append(candidate)

        # Return more candidates than activations needed (give user options)
        # Return at least 10 candidates or 2x num_activations, whichever is larger
        num_to_return = max(10, num_activations * 2)
        return candidates[:num_to_return]

    def execute_batch_ir_activations(
        self,
        team_id: int,
        activations: List[Dict[str, int]],
        current_week: int
    ) -> Dict[str, Any]:
        """
        Execute batch IR activations with roster cuts (atomic operation).

        This method ensures atomicity - either all activations succeed or all fail.
        Uses a database transaction to prevent partial completion.

        Args:
            team_id: Team ID executing activations
            activations: List of {
                "player_to_activate": int (player_id),
                "player_to_cut": int (player_id)
            }
            current_week: Current week number

        Returns:
            {
                "success": bool,
                "activations": List[str] (player names activated),
                "cuts": List[str] (player names cut),
                "errors": List[str] (any errors that occurred)
            }

        Raises:
            sqlite3.Error: If transaction fails and cannot be rolled back
        """
        from .roster_cuts_service import RosterCutsService

        # Initialize roster cuts service for cut operations
        roster_cuts_service = RosterCutsService(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._season
        )

        activated_players = []
        cut_players = []
        errors = []

        # Begin atomic transaction
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        try:
            # Start immediate transaction (locks database)
            conn.execute("BEGIN IMMEDIATE")

            for activation in activations:
                player_to_activate = activation["player_to_activate"]
                player_to_cut = activation["player_to_cut"]

                # 1. Cut the designated player to make room
                try:
                    cut_result = roster_cuts_service.cut_player(
                        player_id=player_to_cut,
                        team_id=team_id,
                        add_to_waivers=True,
                        use_june_1=False
                    )

                    if cut_result["success"]:
                        cut_players.append(cut_result["player_name"])
                    else:
                        errors.append(f"Failed to cut player {player_to_cut}")
                        raise Exception(f"Cut failed for player {player_to_cut}")

                except Exception as e:
                    self._logger.error(f"Error cutting player {player_to_cut}: {e}")
                    errors.append(str(e))
                    raise  # Rollback transaction

                # 2. Activate the IR player
                try:
                    success = self.activate_from_ir(player_to_activate, current_week)
                    if success:
                        # Get player name for reporting
                        player_row = conn.execute("""
                            SELECT first_name || ' ' || last_name as name
                            FROM players
                            WHERE dynasty_id = ? AND player_id = ?
                        """, (self._dynasty_id, player_to_activate)).fetchone()

                        if player_row:
                            activated_players.append(player_row['name'])
                    else:
                        errors.append(f"Failed to activate player {player_to_activate} from IR")
                        raise Exception(f"IR activation failed for player {player_to_activate}")

                except Exception as e:
                    self._logger.error(f"Error activating player {player_to_activate}: {e}")
                    errors.append(str(e))
                    raise  # Rollback transaction

            # If we got here, all operations succeeded
            conn.commit()

            self._logger.info(
                f"Batch IR activations successful for team {team_id}: "
                f"{len(activated_players)} activated, {len(cut_players)} cut"
            )

            return {
                "success": True,
                "activations": activated_players,
                "cuts": cut_players,
                "errors": []
            }

        except Exception as e:
            # Rollback all operations
            conn.rollback()
            self._logger.error(f"Batch IR activation failed for team {team_id}, rolled back: {e}")

            return {
                "success": False,
                "activations": [],
                "cuts": [],
                "errors": errors if errors else [str(e)]
            }

        finally:
            conn.close()

    def should_ai_activate_player(
        self,
        ir_player: Dict[str, Any],
        team_roster: List[Dict[str, Any]],
        weeks_remaining: int
    ) -> bool:
        """
        AI decision logic for conservative IR activation strategy.

        This implements the conservative strategy chosen by the user:
        - Only activate starter-quality players (75+ OVR)
        - Focus on critical position needs
        - Avoid roster churn for backups

        Activation criteria:
        1. Player OVR >= 75 (starter quality) AND
        2. One of:
           - Position depth < 3 players (critical need)
           - Position has other injuries (dire need)
           - Player OVR >= 80 (high-value) AND weeks_remaining >= 6

        Do NOT activate if:
        - Weeks remaining in season < 4 (not worth roster churn)
        - Player OVR < 75 (backup quality)
        - Position has 4+ healthy players (sufficient depth)

        Args:
            ir_player: Player dict with keys: player_id, position, overall, etc.
            team_roster: Full roster list (active players)
            weeks_remaining: Weeks left in regular season

        Returns:
            True if AI should activate this player, False otherwise
        """
        # Filter 1: Don't activate late in season (< 4 weeks left)
        if weeks_remaining < 4:
            self._logger.debug(
                f"AI skip IR activation: Not enough weeks remaining ({weeks_remaining} < 4)"
            )
            return False

        # Filter 2: Only activate starter-quality players (75+ OVR)
        player_overall = ir_player.get('overall', 0)
        if player_overall < 75:
            self._logger.debug(
                f"AI skip IR activation: Player OVR too low ({player_overall} < 75)"
            )
            return False

        # Filter 3: Check position depth
        position = ir_player.get('position', '')
        healthy_at_position = [
            p for p in team_roster
            if p.get('position') == position and not p.get('injured', False)
        ]
        position_depth = len(healthy_at_position)

        # Activate if critical need (< 3 at position)
        if position_depth < 3:
            self._logger.info(
                f"AI activating from IR: Critical position need "
                f"({position} depth = {position_depth})"
            )
            return True

        # Activate if high-value (80+ OVR) and significant time left
        if player_overall >= 80 and weeks_remaining >= 6:
            self._logger.info(
                f"AI activating from IR: High-value player "
                f"(OVR {player_overall}, {weeks_remaining} weeks left)"
            )
            return True

        # Activate if other injuries at same position (dire need)
        injured_at_position = [
            p for p in team_roster
            if p.get('position') == position and p.get('injured', False)
        ]
        if len(injured_at_position) >= 2:
            self._logger.info(
                f"AI activating from IR: Multiple injuries at position "
                f"({position}: {len(injured_at_position)} injured)"
            )
            return True

        # Default: Keep on IR (don't churn roster for backups)
        self._logger.debug(
            f"AI skip IR activation: Not worth roster churn "
            f"(OVR {player_overall}, depth {position_depth}, weeks {weeks_remaining})"
        )
        return False

    def process_ai_ir_activations(
        self,
        ai_team_ids: List[int],
        current_week: int
    ) -> Dict[str, Any]:
        """
        Process IR activations for all AI teams (conservative strategy).

        For each AI team:
        1. Get eligible IR players
        2. Evaluate each using should_ai_activate_player()
        3. If activating, get cut candidates
        4. Pick lowest value cut (avoid protected players)
        5. Execute activation + cut atomically

        Args:
            ai_team_ids: List of team IDs to process (all AI teams)
            current_week: Current week number

        Returns:
            {
                "teams_processed": int,
                "total_activations": int,
                "total_cuts": int,
                "events": List[str]  # Human-readable event log
            }
        """
        teams_processed = 0
        total_activations = 0
        total_cuts = 0
        events = []

        # Calculate weeks remaining in season (18 total regular season weeks)
        REGULAR_SEASON_WEEKS = 18
        weeks_remaining = REGULAR_SEASON_WEEKS - current_week

        for team_id in ai_team_ids:
            teams_processed += 1

            # Get eligible IR players for this team
            eligible_players = self.get_weekly_ir_eligible_players(team_id, current_week)

            if not eligible_players:
                continue  # No eligible players

            # Get current roster for decision-making
            conn = sqlite3.connect(self._db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                roster_rows = conn.execute("""
                    SELECT player_id, position, overall
                    FROM players
                    WHERE dynasty_id = ? AND team_id = ?
                """, (self._dynasty_id, team_id)).fetchall()

                team_roster = [dict(row) for row in roster_rows]
            finally:
                conn.close()

            # Evaluate each eligible player
            activations_to_execute = []
            for ir_player in eligible_players:
                should_activate = self.should_ai_activate_player(
                    ir_player, team_roster, weeks_remaining
                )

                if not should_activate:
                    continue

                # Get cut candidates (sorted by value, lowest first)
                cut_candidates = self.get_cut_candidates_for_activation(team_id, 1)

                # Filter out protected players
                eligible_cuts = [c for c in cut_candidates if not c.get('protected', False)]

                if not eligible_cuts:
                    self._logger.warning(
                        f"Team {team_id} cannot activate player {ir_player['player_id']} from IR: "
                        f"no unprotected players to cut"
                    )
                    events.append(
                        f"Team {team_id} blocked: No unprotected players to cut for IR activation"
                    )
                    continue

                # Pick lowest value player to cut
                player_to_cut = eligible_cuts[0]['player_id']

                activations_to_execute.append({
                    "player_to_activate": ir_player['player_id'],
                    "player_to_cut": player_to_cut
                })

            # Execute all activations for this team atomically
            if activations_to_execute:
                result = self.execute_batch_ir_activations(
                    team_id, activations_to_execute, current_week
                )

                if result["success"]:
                    total_activations += len(result["activations"])
                    total_cuts += len(result["cuts"])

                    # Create event log entries
                    for i, activation in enumerate(result["activations"]):
                        cut = result["cuts"][i] if i < len(result["cuts"]) else "unknown"
                        events.append(
                            f"Team {team_id} activated {activation} from IR (cut {cut})"
                        )
                else:
                    events.append(
                        f"Team {team_id} IR activation failed: {result['errors']}"
                    )

        self._logger.info(
            f"AI IR activations complete: {total_activations} activated, "
            f"{total_cuts} cut across {teams_processed} teams"
        )

        return {
            "teams_processed": teams_processed,
            "total_activations": total_activations,
            "total_cuts": total_cuts,
            "events": events
        }
