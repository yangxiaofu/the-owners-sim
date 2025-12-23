"""
Roster Cuts Service for Game Cycle.

Handles roster cut operations during the offseason roster cuts stage.
Implements AI auto-cut suggestions and dead money calculations.
"""

from datetime import date
from typing import Dict, List, Any, Optional, Set
import logging
import sqlite3
import json

from src.persistence.transaction_logger import TransactionLogger
from src.utils.player_field_extractors import extract_overall_rating


class RosterCutsService:
    """
    Service for roster cuts stage operations.

    Manages:
    - Getting team roster with player values
    - AI cut suggestions based on player value
    - Cutting players with dead money calculation
    - Adding cut players to waiver wire
    - Processing AI team roster cuts
    """

    # Position value multipliers (premium positions = higher value)
    POSITION_VALUES = {
        # Tier 1: Premium positions
        'quarterback': 2.0,
        'defensive_end': 1.8,
        'left_tackle': 1.8,
        'right_tackle': 1.8,

        # Tier 2: High-value positions
        'wide_receiver': 1.5,
        'cornerback': 1.5,
        'center': 1.4,

        # Tier 3: Standard positions
        'running_back': 1.0,
        'tight_end': 1.2,
        'linebacker': 1.3,
        'safety': 1.3,
        'left_guard': 1.2,
        'right_guard': 1.2,

        # Tier 4: Lower-value positions
        'defensive_tackle': 1.1,
        'kicker': 0.8,
        'punter': 0.8,
    }

    # NFL minimum position requirements (per team)
    POSITION_MINIMUMS = {
        'quarterback': 2,
        'running_back': 2,       # RBs are essential for run plays
        'wide_receiver': 3,      # Need depth at WR
        'tight_end': 1,          # At least one TE
        'offensive_line': 5,     # Any OL position
        'defensive_line': 4,     # Any DL position
        'linebacker': 3,
        'defensive_back': 4,     # Need DB depth
        'kicker': 1,
        'punter': 1
    }

    # Position groupings - include all variants from database
    OL_POSITIONS = {
        'left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'center',
        'offensive_tackle', 'offensive_guard', 'tackle', 'guard'
    }
    DL_POSITIONS = {'defensive_end', 'defensive_tackle', 'edge', 'nose_tackle'}
    DB_POSITIONS = {'cornerback', 'safety', 'free_safety', 'strong_safety'}
    LB_POSITIONS = {
        'linebacker', 'outside_linebacker', 'inside_linebacker',
        'mike_linebacker', 'will_linebacker', 'middle_linebacker'
    }
    RB_POSITIONS = {'running_back', 'fullback'}
    WR_POSITIONS = {'wide_receiver'}
    TE_POSITIONS = {'tight_end'}

    ROSTER_LIMIT = 53

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the roster cuts service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded cap helper
        self._cap_helper = None

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

        # Ensure waiver tables exist (migration for existing databases)
        self._ensure_tables()

    def _get_cap_helper(self):
        """Get or create cap helper instance.

        Uses season + 1 because during offseason roster cuts,
        cap calculations are for the NEXT league year.
        """
        if self._cap_helper is None:
            from .cap_helper import CapHelper
            # Offseason cap calculations are for NEXT season
            self._cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
        return self._cap_helper

    def _ensure_tables(self):
        """Create waiver tables if they don't exist (handles schema migration)."""
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        try:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS waiver_wire (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    former_team_id INTEGER NOT NULL,
                    waiver_status TEXT DEFAULT 'on_waivers',
                    waiver_order INTEGER,
                    claiming_team_id INTEGER,
                    dead_money INTEGER DEFAULT 0,
                    cap_savings INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cleared_at TIMESTAMP,
                    season INTEGER NOT NULL,
                    UNIQUE(dynasty_id, player_id, season)
                );

                CREATE TABLE IF NOT EXISTS waiver_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    waiver_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    claiming_team_id INTEGER NOT NULL,
                    claim_priority INTEGER NOT NULL,
                    claim_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    UNIQUE(dynasty_id, season, player_id, claiming_team_id)
                );

                CREATE INDEX IF NOT EXISTS idx_waiver_wire_dynasty ON waiver_wire(dynasty_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_wire_status ON waiver_wire(dynasty_id, waiver_status);
                CREATE INDEX IF NOT EXISTS idx_waiver_wire_season ON waiver_wire(dynasty_id, season);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_dynasty ON waiver_claims(dynasty_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_player ON waiver_claims(dynasty_id, player_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_pending ON waiver_claims(dynasty_id, season, claim_status);
            ''')
            conn.commit()
        finally:
            conn.close()

    def get_cap_summary(self, team_id: int) -> dict:
        """
        Get salary cap summary for a team.

        Args:
            team_id: Team ID

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant
        """
        return self._get_cap_helper().get_cap_summary(team_id)

    def get_team_roster_for_cuts(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get full roster for a team with all data needed for cut decisions.

        Args:
            team_id: Team ID to get roster for

        Returns:
            List of player dictionaries with ratings, contract info, and value scores
        """
        from database.player_roster_api import PlayerRosterAPI
        from salary_cap.cap_database_api import CapDatabaseAPI

        roster_api = PlayerRosterAPI(self._db_path)
        cap_api = CapDatabaseAPI(self._db_path)

        # Get all players for this team
        players = roster_api.get_team_roster(self._dynasty_id, team_id)

        roster_data = []
        for player in players:
            player_id = player.get("player_id")

            # Extract position from JSON array
            positions = player.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else ""

            # Extract overall and potential from JSON attributes
            overall = extract_overall_rating(player, default=0)
            attributes = player.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            potential = attributes.get("potential", 0)

            # Calculate age from birthdate if available
            age = 0
            birthdate = player.get("birthdate")
            if birthdate:
                try:
                    birth_year = int(birthdate.split("-")[0])
                    age = self._season - birth_year
                except (ValueError, IndexError):
                    pass

            # Get contract info for current season (players on expiring contracts are still on roster)
            contract = cap_api.get_player_contract(
                player_id=player_id,
                team_id=team_id,
                season=self._season,
                dynasty_id=self._dynasty_id
            )

            salary = 0
            signing_bonus = 0
            contract_years = 1
            years_remaining = 0
            cap_hit = 0

            if contract:
                salary = contract.get("total_value", 0) // max(contract.get("contract_years", 1), 1)
                signing_bonus = contract.get("signing_bonus", 0)
                contract_years = contract.get("contract_years", 1)
                years_remaining = max(0, contract.get("end_year", self._season) - self._season + 1)
                cap_hit = salary + (signing_bonus // max(contract_years, 1))

            # Calculate dead money and cap savings if cut (immediate, no June 1)
            dead_money, cap_savings, _ = self._calculate_cut_cap_impact(
                signing_bonus=signing_bonus,
                contract_years=contract_years,
                years_remaining=years_remaining,
                annual_salary=salary
            )

            # Calculate value score for ranking
            value_score = self._calculate_player_value(
                overall=overall,
                position=position,
                cap_hit=cap_hit
            )

            # Get development type from archetype
            archetype_id = player.get("archetype_id")
            dev_type = self._get_dev_type(archetype_id)

            roster_data.append({
                "player_id": player_id,
                "name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                "position": position,
                "age": age,
                "overall": overall,
                "potential": potential,
                "dev_type": dev_type,
                "years_pro": player.get("years_pro", 0),
                "salary": salary,
                "cap_hit": cap_hit,
                "dead_money": dead_money,
                "cap_savings": cap_savings,
                "value_score": value_score,
                "contract_id": contract.get("contract_id") if contract else None,
            })

        # Sort by value score (highest first)
        roster_data.sort(key=lambda x: x.get("value_score", 0), reverse=True)

        return roster_data

    def get_roster_count(self, team_id: int) -> int:
        """
        Get count of active roster players for a team.

        Args:
            team_id: Team ID

        Returns:
            Number of players on roster
        """
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(self._db_path)
        return roster_api.get_roster_count(self._dynasty_id, team_id)

    def get_cuts_needed(self, team_id: int, target_size: int = 53) -> int:
        """
        Get number of players that need to be cut to reach target roster size.

        Args:
            team_id: Team ID
            target_size: Target roster size (default 53 for regular roster limit)

        Returns:
            Number of cuts needed (0 if already at/below target)
        """
        roster_count = self.get_roster_count(team_id)
        return max(0, roster_count - target_size)

    def get_ai_cut_suggestions(self, team_id: int, count: Optional[int] = None, target_size: int = 53) -> List[Dict[str, Any]]:
        """
        Get AI suggestions for which players to cut.

        Uses player value score (overall * position_value - cap_hit_penalty)
        to suggest cutting lowest-value players while respecting position minimums.

        Args:
            team_id: Team ID
            count: Number of suggestions needed (defaults to cuts_needed based on target_size)
            target_size: Target roster size (default 53 for regular roster limit)

        Returns:
            List of player dicts to suggest cutting, sorted by priority
        """
        if count is None:
            count = self.get_cuts_needed(team_id, target_size)

        if count <= 0:
            return []

        roster = self.get_team_roster_for_cuts(team_id)

        # Identify players that cannot be cut (position minimums)
        protected_ids = self._get_protected_players(roster)

        # Filter out protected players and reverse sort (lowest value first)
        cuttable = [p for p in roster if p["player_id"] not in protected_ids]
        cuttable.sort(key=lambda x: x.get("value_score", 0))

        # Return bottom N players
        suggestions = cuttable[:count]

        return suggestions

    def cut_player(
        self,
        player_id: int,
        team_id: int,
        add_to_waivers: bool = True,
        use_june_1: bool = False,
        conn: Optional[sqlite3.Connection] = None
    ) -> Dict[str, Any]:
        """
        Cut a player from the roster with dead money calculation.

        Args:
            player_id: Player ID to cut
            team_id: Team ID
            add_to_waivers: Whether to add player to waiver wire (default True)
            use_june_1: If True, use Post-June 1 designation to spread dead money over 2 years
            conn: Optional shared database connection for transaction mode.
                  If provided, all operations use this connection (for avoiding lock conflicts).
                  If None, operations create their own connections.

        Returns:
            Dict with:
                - success: bool
                - player_name: str
                - dead_money: int (current year dead money)
                - dead_money_next_year: int (next year dead money, if June 1)
                - cap_savings: int
                - use_june_1: bool
                - error_message: str (if failed)
        """
        from database.player_roster_api import PlayerRosterAPI
        from salary_cap.cap_database_api import CapDatabaseAPI
        from datetime import date as date_type

        try:
            # Use shared connection if provided to avoid lock conflicts
            roster_api = PlayerRosterAPI(self._db_path, connection=conn)
            cap_api = CapDatabaseAPI(self._db_path)

            # Get player info
            player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not found",
                }

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
            player_position = player_info.get('position', '')

            # Get contract info for current season (players on expiring contracts are still on roster)
            contract = cap_api.get_player_contract(
                player_id=player_id,
                team_id=team_id,
                season=self._season,
                dynasty_id=self._dynasty_id
            )

            dead_money = 0
            cap_savings = 0
            dead_money_next_year = 0

            if contract:
                contract_years = contract.get("contract_years", 1)
                years_remaining = max(0, contract.get("end_year", self._season) - self._season + 1)
                signing_bonus = contract.get("signing_bonus", 0)
                annual_salary = contract.get("total_value", 0) // max(contract_years, 1)

                dead_money, cap_savings, dead_money_next_year = self._calculate_cut_cap_impact(
                    signing_bonus=signing_bonus,
                    contract_years=contract_years,
                    years_remaining=years_remaining,
                    annual_salary=annual_salary,
                    use_june_1=use_june_1
                )

                # Void the contract - use shared connection if provided to avoid locks
                if conn is not None:
                    conn.execute('''
                        UPDATE player_contracts
                        SET is_active = FALSE,
                            voided_date = ?,
                            modified_at = CURRENT_TIMESTAMP
                        WHERE contract_id = ?
                    ''', (date_type.today(), contract["contract_id"]))
                else:
                    cap_api.void_contract(contract["contract_id"])

            # Add to waiver wire if requested
            if add_to_waivers:
                self._add_to_waiver_wire(
                    player_id=player_id,
                    former_team_id=team_id,
                    dead_money=dead_money,
                    cap_savings=cap_savings,
                    conn=conn
                )

            # Move player to "waiver" status (not free agent yet)
            # We'll set team_id to 0 but they're on waivers until cleared
            roster_api.update_player_team(
                dynasty_id=self._dynasty_id,
                player_id=player_id,
                new_team_id=0  # Will be on waiver wire
            )

            june_1_str = " (June 1)" if use_june_1 else ""
            next_yr_str = f", Next year: ${dead_money_next_year:,}" if dead_money_next_year else ""
            self._logger.info(
                f"Cut {player_name} from team {team_id}{june_1_str}. Dead money: ${dead_money:,}{next_yr_str}, Savings: ${cap_savings:,}"
            )

            # Prepare transaction log data
            transaction_log_data = {
                "dynasty_id": self._dynasty_id,
                "season": self._season + 1,  # Cut is during next season's preseason
                "transaction_type": "ROSTER_CUT",
                "player_id": player_id,
                "player_name": player_name,
                "position": player_position,
                "from_team_id": team_id,
                "to_team_id": None,  # To waivers/free agency
                "transaction_date": date(self._season + 1, 8, 27),  # Roster cut deadline (next year)
                "details": {
                    "dead_money": dead_money,
                    "dead_money_next_year": dead_money_next_year,
                    "cap_savings": cap_savings,
                    "use_june_1": use_june_1,
                    "reason": "roster_limit",
                }
            }

            # Log transaction for audit trail
            # If conn is provided (batch mode), defer logging to caller to avoid lock conflicts
            if conn is None:
                self._transaction_logger.log_transaction(**transaction_log_data)

            return {
                "success": True,
                "player_name": player_name,
                "player_id": player_id,
                "dead_money": dead_money,
                "dead_money_next_year": dead_money_next_year,
                "cap_savings": cap_savings,
                "use_june_1": use_june_1,
                "transaction_log_data": transaction_log_data,  # Caller logs after commit
            }

        except Exception as e:
            self._logger.error(f"Failed to cut player {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def process_ai_cuts(self, user_team_id: int, target_size: int = 53) -> Dict[str, Any]:
        """
        Process roster cuts for all AI teams.

        For each AI team (not user_team_id):
        1. Get cuts needed
        2. Get AI suggestions
        3. Execute cuts
        4. Add to waiver wire

        Args:
            user_team_id: User's team ID (to skip)
            target_size: Target roster size (default 53 for regular roster limit)

        Returns:
            Dict with:
                - cuts: List of cut player info
                - events: List of event strings for UI
                - total_cuts: int
        """
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        all_cuts = []
        events = []

        for team in all_teams:
            team_id = team.team_id

            # Skip user's team
            if team_id == user_team_id:
                continue

            cuts_needed = self.get_cuts_needed(team_id, target_size)

            if cuts_needed <= 0:
                continue

            # Get AI suggestions
            suggestions = self.get_ai_cut_suggestions(team_id, cuts_needed, target_size)

            team_cuts = []
            for player in suggestions:
                result = self.cut_player(
                    player_id=player["player_id"],
                    team_id=team_id,
                    add_to_waivers=True
                )

                if result["success"]:
                    team_cuts.append({
                        "player_id": player["player_id"],
                        "player_name": result["player_name"],
                        "position": player.get("position", ""),
                        "overall": player.get("overall", 0),
                        "team_id": team_id,
                        "team_name": team.full_name,
                        "team_abbr": team.abbreviation,
                        "dead_money": result["dead_money"],
                        "cap_savings": result["cap_savings"],
                    })

            if team_cuts:
                all_cuts.extend(team_cuts)
                events.append(
                    f"{team.abbreviation} cut {len(team_cuts)} players"
                )

        self._logger.info(f"AI roster cuts complete: {len(all_cuts)} total cuts across {len(events)} teams")

        return {
            "cuts": all_cuts,
            "events": events,
            "total_cuts": len(all_cuts),
        }

    def _calculate_cut_cap_impact(
        self,
        signing_bonus: int,
        contract_years: int,
        years_remaining: int,
        annual_salary: int,
        use_june_1: bool = False
    ) -> tuple:
        """
        Calculate dead money and cap savings when cutting a player.

        NFL Rules (simplified):
        - Dead money = remaining signing bonus proration
        - Cap savings = annual salary - dead money accelerated

        Post-June 1 designation:
        - Current year dead money = 1 year of proration only
        - Next year dead money = remaining prorated bonus
        - More immediate cap relief, but dead money spreads to next year

        Args:
            signing_bonus: Total signing bonus
            contract_years: Total years on contract
            years_remaining: Years left on contract
            annual_salary: Annual base salary
            use_june_1: If True, use Post-June 1 designation (spread dead money)

        Returns:
            Tuple of (dead_money, cap_savings, dead_money_next_year)
            dead_money_next_year is 0 for immediate cuts
        """
        if contract_years <= 0:
            return 0, annual_salary, 0

        # Proration per year
        proration = signing_bonus // contract_years

        if use_june_1 and years_remaining > 1:
            # Post-June 1: Split dead money over 2 years
            # Current year: 1 year of proration
            dead_money = proration
            # Next year: remaining prorated bonus
            dead_money_next_year = proration * (years_remaining - 1)
        else:
            # Immediate cut: All dead money accelerates to current year
            dead_money = proration * years_remaining
            dead_money_next_year = 0

        # Cap savings = this year's salary (contract is voided)
        # If dead_money > salary, team actually loses cap space
        cap_savings = max(0, annual_salary - dead_money)

        return dead_money, cap_savings, dead_money_next_year

    def _calculate_player_value(
        self,
        overall: int,
        position: str,
        cap_hit: int
    ) -> float:
        """
        Calculate player value score for cut decisions.

        Higher score = more valuable, less likely to cut.

        Args:
            overall: Player overall rating
            position: Player position
            cap_hit: Annual cap hit

        Returns:
            Value score (higher is better)
        """
        pos_multiplier = self.POSITION_VALUES.get(position, 1.0)
        cap_penalty = cap_hit / 1_000_000  # Convert to millions

        value = (pos_multiplier * overall) - cap_penalty

        return value

    def _get_protected_players(self, roster: List[Dict[str, Any]]) -> Set[int]:
        """
        Get player IDs that cannot be cut due to position minimums.

        Args:
            roster: Full roster with position info

        Returns:
            Set of protected player IDs
        """
        protected = set()

        # Count players by position group
        position_groups = {
            'quarterback': [],
            'running_back': [],
            'wide_receiver': [],
            'tight_end': [],
            'offensive_line': [],
            'defensive_line': [],
            'linebacker': [],
            'defensive_back': [],
            'kicker': [],
            'punter': [],
        }

        for player in roster:
            pos = player.get("position", "")
            player_id = player["player_id"]
            value = player.get("value_score", 0)

            if pos == 'quarterback':
                position_groups['quarterback'].append((player_id, value))
            elif pos in self.RB_POSITIONS:
                position_groups['running_back'].append((player_id, value))
            elif pos in self.WR_POSITIONS:
                position_groups['wide_receiver'].append((player_id, value))
            elif pos in self.TE_POSITIONS:
                position_groups['tight_end'].append((player_id, value))
            elif pos in self.OL_POSITIONS:
                position_groups['offensive_line'].append((player_id, value))
            elif pos in self.DL_POSITIONS:
                position_groups['defensive_line'].append((player_id, value))
            elif pos in self.LB_POSITIONS:
                position_groups['linebacker'].append((player_id, value))
            elif pos in self.DB_POSITIONS:
                position_groups['defensive_back'].append((player_id, value))
            elif pos == 'kicker':
                position_groups['kicker'].append((player_id, value))
            elif pos == 'punter':
                position_groups['punter'].append((player_id, value))

        # Protect top N players at each position to meet minimums
        for group, min_count in self.POSITION_MINIMUMS.items():
            players = position_groups.get(group, [])
            # Sort by value (highest first) and protect top min_count
            players.sort(key=lambda x: x[1], reverse=True)
            for player_id, _ in players[:min_count]:
                protected.add(player_id)

        return protected

    def _get_dev_type(self, archetype_id: Optional[str]) -> str:
        """
        Get development type from archetype.

        Args:
            archetype_id: Player's archetype ID

        Returns:
            Development type: "E" (early), "N" (normal), "L" (late)
        """
        if not archetype_id:
            return "N"
        try:
            from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry
            registry = ArchetypeRegistry()
            archetype = registry.get_archetype(archetype_id)
            if archetype and archetype.development_curve:
                return {"early": "E", "normal": "N", "late": "L"}.get(archetype.development_curve, "N")
        except Exception:
            pass
        return "N"

    def _add_to_waiver_wire(
        self,
        player_id: int,
        former_team_id: int,
        dead_money: int,
        cap_savings: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Add a cut player to the waiver wire.

        Args:
            player_id: Player ID
            former_team_id: Team that cut the player
            dead_money: Dead money cap hit
            cap_savings: Cap savings from cut
            conn: Optional shared database connection for transaction mode.
                  If provided, uses this connection (caller manages commit/close).
                  If None, creates own connection with auto-commit.

        Returns:
            Waiver wire entry ID
        """
        # Use shared connection if provided, otherwise create new one
        owns_connection = conn is None
        if owns_connection:
            conn = sqlite3.connect(self._db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            # Get next waiver order
            cursor.execute(
                """
                SELECT COALESCE(MAX(waiver_order), 0) + 1
                FROM waiver_wire
                WHERE dynasty_id = ? AND season = ?
                """,
                (self._dynasty_id, self._season)
            )
            waiver_order = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO waiver_wire (
                    dynasty_id, player_id, former_team_id, waiver_status,
                    waiver_order, dead_money, cap_savings, season
                )
                VALUES (?, ?, ?, 'on_waivers', ?, ?, ?, ?)
                """,
                (
                    self._dynasty_id,
                    player_id,
                    former_team_id,
                    waiver_order,
                    dead_money,
                    cap_savings,
                    self._season
                )
            )
            # Only commit if we own the connection
            if owns_connection:
                conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            # Player already on waivers (shouldn't happen but handle gracefully)
            self._logger.warning(f"Player {player_id} already on waiver wire")
            return -1
        finally:
            # Only close if we created the connection
            if owns_connection:
                conn.close()

    def get_waiver_wire_players(self) -> List[Dict[str, Any]]:
        """
        Get all players currently on the waiver wire.

        Returns:
            List of player dicts with waiver info
        """
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(self._db_path)
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT w.id, w.player_id, w.former_team_id, w.waiver_order,
                       w.dead_money, w.cap_savings, w.created_at
                FROM waiver_wire w
                WHERE w.dynasty_id = ? AND w.season = ? AND w.waiver_status = 'on_waivers'
                ORDER BY w.waiver_order ASC
                """,
                (self._dynasty_id, self._season)
            )

            waiver_players = []
            for row in cursor.fetchall():
                waiver_id, player_id, former_team_id, order, dead_money, cap_savings, created = row

                # Get player details
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

                if player_info:
                    positions = player_info.get("positions", [])
                    if isinstance(positions, str):
                        positions = json.loads(positions)
                    position = positions[0] if positions else ""

                    overall = extract_overall_rating(player_info, default=0)
                    attributes = player_info.get("attributes", {})
                    if isinstance(attributes, str):
                        attributes = json.loads(attributes)
                    potential = attributes.get("potential", 0)

                    # Get development type from archetype
                    archetype_id = player_info.get("archetype_id")
                    dev_type = self._get_dev_type(archetype_id)

                    waiver_players.append({
                        "waiver_id": waiver_id,
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": position,
                        "overall": overall,
                        "potential": potential,
                        "dev_type": dev_type,
                        "former_team_id": former_team_id,
                        "waiver_order": order,
                        "dead_money": dead_money,
                        "cap_savings": cap_savings,
                        "created_at": created,
                    })

            return waiver_players

        finally:
            conn.close()