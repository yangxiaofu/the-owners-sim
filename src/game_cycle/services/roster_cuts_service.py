"""
Roster Cuts Service for Game Cycle.

Handles roster cut operations during the offseason roster cuts stage.
Implements AI auto-cut suggestions and dead money calculations.
"""

from typing import Dict, List, Any, Optional, Set
import logging
import sqlite3
import json


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

    # NFL minimum position requirements
    POSITION_MINIMUMS = {
        'quarterback': 1,
        'offensive_line': 5,  # Any OL position
        'defensive_line': 4,  # Any DL position
        'linebacker': 3,
        'defensive_back': 3,  # Any DB position
        'kicker': 1,
        'punter': 1
    }

    # Position groupings
    OL_POSITIONS = {'left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'center'}
    DL_POSITIONS = {'defensive_end', 'defensive_tackle'}
    DB_POSITIONS = {'cornerback', 'safety'}

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

            # Extract overall from JSON attributes
            attributes = player.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 0)

            # Calculate age from birthdate if available
            age = 0
            birthdate = player.get("birthdate")
            if birthdate:
                try:
                    birth_year = int(birthdate.split("-")[0])
                    age = self._season - birth_year
                except (ValueError, IndexError):
                    pass

            # Get contract info
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

            # Calculate dead money and cap savings if cut
            dead_money, cap_savings = self._calculate_cut_cap_impact(
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

            roster_data.append({
                "player_id": player_id,
                "name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                "position": position,
                "age": age,
                "overall": overall,
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

    def get_cuts_needed(self, team_id: int) -> int:
        """
        Get number of players that need to be cut to reach 53.

        Args:
            team_id: Team ID

        Returns:
            Number of cuts needed (0 if already at/below 53)
        """
        roster_count = self.get_roster_count(team_id)
        return max(0, roster_count - self.ROSTER_LIMIT)

    def get_ai_cut_suggestions(self, team_id: int, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get AI suggestions for which players to cut.

        Uses player value score (overall * position_value - cap_hit_penalty)
        to suggest cutting lowest-value players while respecting position minimums.

        Args:
            team_id: Team ID
            count: Number of suggestions needed (defaults to cuts_needed)

        Returns:
            List of player dicts to suggest cutting, sorted by priority
        """
        if count is None:
            count = self.get_cuts_needed(team_id)

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
        add_to_waivers: bool = True
    ) -> Dict[str, Any]:
        """
        Cut a player from the roster with dead money calculation.

        Args:
            player_id: Player ID to cut
            team_id: Team ID
            add_to_waivers: Whether to add player to waiver wire (default True)

        Returns:
            Dict with:
                - success: bool
                - player_name: str
                - dead_money: int
                - cap_savings: int
                - error_message: str (if failed)
        """
        from database.player_roster_api import PlayerRosterAPI
        from salary_cap.cap_database_api import CapDatabaseAPI

        try:
            roster_api = PlayerRosterAPI(self._db_path)
            cap_api = CapDatabaseAPI(self._db_path)

            # Get player info
            player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not found",
                }

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Get contract info
            contract = cap_api.get_player_contract(
                player_id=player_id,
                team_id=team_id,
                season=self._season,
                dynasty_id=self._dynasty_id
            )

            dead_money = 0
            cap_savings = 0

            if contract:
                contract_years = contract.get("contract_years", 1)
                years_remaining = max(0, contract.get("end_year", self._season) - self._season + 1)
                signing_bonus = contract.get("signing_bonus", 0)
                annual_salary = contract.get("total_value", 0) // max(contract_years, 1)

                dead_money, cap_savings = self._calculate_cut_cap_impact(
                    signing_bonus=signing_bonus,
                    contract_years=contract_years,
                    years_remaining=years_remaining,
                    annual_salary=annual_salary
                )

                # Void the contract
                cap_api.void_contract(contract["contract_id"])

            # Add to waiver wire if requested
            if add_to_waivers:
                self._add_to_waiver_wire(
                    player_id=player_id,
                    former_team_id=team_id,
                    dead_money=dead_money,
                    cap_savings=cap_savings
                )

            # Move player to "waiver" status (not free agent yet)
            # We'll set team_id to 0 but they're on waivers until cleared
            roster_api.update_player_team(
                dynasty_id=self._dynasty_id,
                player_id=player_id,
                new_team_id=0  # Will be on waiver wire
            )

            self._logger.info(
                f"Cut {player_name} from team {team_id}. Dead money: ${dead_money:,}, Savings: ${cap_savings:,}"
            )

            return {
                "success": True,
                "player_name": player_name,
                "player_id": player_id,
                "dead_money": dead_money,
                "cap_savings": cap_savings,
            }

        except Exception as e:
            self._logger.error(f"Failed to cut player {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def process_ai_cuts(self, user_team_id: int) -> Dict[str, Any]:
        """
        Process roster cuts for all AI teams.

        For each AI team (not user_team_id):
        1. Get cuts needed
        2. Get AI suggestions
        3. Execute cuts
        4. Add to waiver wire

        Args:
            user_team_id: User's team ID (to skip)

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

            cuts_needed = self.get_cuts_needed(team_id)

            if cuts_needed <= 0:
                continue

            # Get AI suggestions
            suggestions = self.get_ai_cut_suggestions(team_id, cuts_needed)

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
        annual_salary: int
    ) -> tuple:
        """
        Calculate dead money and cap savings when cutting a player.

        NFL Rules (simplified):
        - Dead money = remaining signing bonus proration
        - Cap savings = annual salary - dead money accelerated

        Args:
            signing_bonus: Total signing bonus
            contract_years: Total years on contract
            years_remaining: Years left on contract
            annual_salary: Annual base salary

        Returns:
            Tuple of (dead_money, cap_savings)
        """
        if contract_years <= 0:
            return 0, annual_salary

        # Proration per year
        proration = signing_bonus // contract_years

        # Dead money = remaining prorated bonus accelerated
        dead_money = proration * years_remaining

        # Cap savings = this year's salary (contract is voided)
        # If dead_money > salary, team actually loses cap space
        cap_savings = max(0, annual_salary - dead_money)

        return dead_money, cap_savings

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
            elif pos in self.OL_POSITIONS:
                position_groups['offensive_line'].append((player_id, value))
            elif pos in self.DL_POSITIONS:
                position_groups['defensive_line'].append((player_id, value))
            elif pos == 'linebacker':
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

    def _add_to_waiver_wire(
        self,
        player_id: int,
        former_team_id: int,
        dead_money: int,
        cap_savings: int
    ) -> int:
        """
        Add a cut player to the waiver wire.

        Args:
            player_id: Player ID
            former_team_id: Team that cut the player
            dead_money: Dead money cap hit
            cap_savings: Cap savings from cut

        Returns:
            Waiver wire entry ID
        """
        conn = sqlite3.connect(self._db_path)
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
            conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            # Player already on waivers (shouldn't happen but handle gracefully)
            self._logger.warning(f"Player {player_id} already on waiver wire")
            return -1
        finally:
            conn.close()

    def get_waiver_wire_players(self) -> List[Dict[str, Any]]:
        """
        Get all players currently on the waiver wire.

        Returns:
            List of player dicts with waiver info
        """
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(self._db_path)
        conn = sqlite3.connect(self._db_path)
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

                    attributes = player_info.get("attributes", {})
                    if isinstance(attributes, str):
                        attributes = json.loads(attributes)
                    overall = attributes.get("overall", 0)

                    waiver_players.append({
                        "waiver_id": waiver_id,
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": position,
                        "overall": overall,
                        "former_team_id": former_team_id,
                        "waiver_order": order,
                        "dead_money": dead_money,
                        "cap_savings": cap_savings,
                        "created_at": created,
                    })

            return waiver_players

        finally:
            conn.close()