"""
Event System Integration for Salary Cap.

This module provides middleware and bridge classes to integrate the salary cap
system with the event system, enabling validation and execution of cap-related
events.
"""

from typing import Optional, Tuple

from salary_cap.cap_calculator import CapCalculator
from salary_cap.cap_validator import CapValidator
from salary_cap.tag_manager import TagManager
from salary_cap.cap_database_api import CapDatabaseAPI


class ValidationMiddleware:
    """
    Validates cap transactions before execution.

    Provides pre-execution validation for all cap operations to prevent
    invalid transactions and provide helpful error messages.
    """

    def __init__(self, cap_calculator, cap_validator, tag_manager, cap_db):
        self.cap_calculator = cap_calculator
        self.cap_validator = cap_validator
        self.tag_manager = tag_manager
        self.cap_db = cap_db

    def validate_franchise_tag(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate franchise tag can be applied.

        Checks:
        - Team hasn't used tag this season
        - Team not over cap

        Returns:
            (is_valid, error_message)
        """
        # Check if team has already used franchise tag this season
        existing_tag = self.tag_manager.get_franchise_tag(team_id, season, dynasty_id)
        if existing_tag is not None:
            return False, "Team has already used franchise tag this season"

        # Check if team is over cap (they need space for the tag)
        cap_status = self.cap_calculator.get_team_cap_status(team_id, season, dynasty_id)
        if cap_status['is_over_cap']:
            return False, f"Team is over cap by ${abs(cap_status['cap_space']):,} and cannot apply franchise tag"

        return True, None

    def validate_ufa_signing(
        self,
        team_id: int,
        contract_value: int,
        season: int,
        dynasty_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate UFA signing.

        Checks:
        - Team has cap space for contract
        - Contract value is positive

        Returns:
            (is_valid, error_message)
        """
        # Validate contract value is positive
        if contract_value <= 0:
            return False, f"Contract value must be positive (received ${contract_value:,})"

        # Check if team has enough cap space
        cap_status = self.cap_calculator.get_team_cap_status(team_id, season, dynasty_id)
        cap_space = cap_status['cap_space']

        if contract_value > cap_space:
            shortfall = contract_value - cap_space
            return False, f"Insufficient cap space: need ${contract_value:,}, have ${cap_space:,} (short ${shortfall:,})"

        return True, None

    def validate_player_release(
        self,
        team_id: int,
        player_id: str,
        season: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate player release.

        Checks:
        - Player has active contract

        Returns:
            (is_valid, error_message)
        """
        # Check if player has an active contract
        contract = self.cap_db.get_player_contract(player_id, team_id, season)

        if contract is None:
            return False, f"Player {player_id} does not have an active contract with team {team_id}"

        if contract.get('status') != 'active':
            return False, f"Player {player_id} contract is not active (status: {contract.get('status')})"

        return True, None

    def validate_contract_restructure(
        self,
        contract_id: int,
        amount_to_convert: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate contract restructure.

        Checks:
        - Contract exists and is active
        - Amount to convert is reasonable

        Returns:
            (is_valid, error_message)
        """
        # Check if contract exists
        contract = self.cap_db.get_contract_by_id(contract_id)

        if contract is None:
            return False, f"Contract {contract_id} does not exist"

        # Check if contract is active
        if contract.get('status') != 'active':
            return False, f"Contract {contract_id} is not active (status: {contract.get('status')})"

        # Validate amount to convert is positive
        if amount_to_convert <= 0:
            return False, f"Amount to convert must be positive (received ${amount_to_convert:,})"

        # Check if amount is reasonable (not more than current year cap hit)
        current_year_hit = contract.get('current_year_cap_hit', 0)
        if amount_to_convert > current_year_hit:
            return False, f"Cannot convert ${amount_to_convert:,} when current year cap hit is only ${current_year_hit:,}"

        return True, None

    def validate_rfa_tender(
        self,
        team_id: int,
        player_id: str,
        season: int,
        dynasty_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate RFA tender can be applied.

        Returns:
            (is_valid, error_message)
        """
        # Check if player already has an active tender this season
        existing_tender = self.tag_manager.get_rfa_tender(team_id, player_id, season, dynasty_id)
        if existing_tender is not None:
            return False, f"Player {player_id} already has an active RFA tender for season {season}"

        # Check if team has cap space (RFA tenders require cap space)
        cap_status = self.cap_calculator.get_team_cap_status(team_id, season, dynasty_id)
        if cap_status['is_over_cap']:
            return False, f"Team is over cap by ${abs(cap_status['cap_space']):,} and cannot apply RFA tender"

        return True, None


class EventCapBridge:
    """
    Bridge between event system and salary cap system.

    Wraps all cap components (CapCalculator, ContractManager, TagManager)
    and provides execution methods for cap-related events.

    Used by specialized event handlers to execute cap operations.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize event-cap bridge.

        Args:
            database_path: Path to database
        """
        from salary_cap.contract_manager import ContractManager
        import logging

        self.calculator = CapCalculator(database_path)
        self.contract_mgr = ContractManager(database_path)
        self.tag_mgr = TagManager(database_path)
        self.cap_db = CapDatabaseAPI(database_path)
        self.validator = CapValidator(database_path)
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # FRANCHISE TAG OPERATIONS
    # ========================================================================

    def execute_franchise_tag(
        self,
        team_id: int,
        player_id: str,
        player_position: str,
        season: int,
        tag_type: str,
        tag_date,
        dynasty_id: str = "default"
    ):
        """
        Execute franchise tag application.

        Args:
            team_id: Team applying the tag
            player_id: Player being tagged
            player_position: Player's position (QB, WR, etc.)
            season: Season year
            tag_type: FRANCHISE_EXCLUSIVE or FRANCHISE_NON_EXCLUSIVE
            tag_date: Date tag was applied
            dynasty_id: Dynasty context

        Returns:
            Dict with tag_salary, contract_id, cap_impact, success status
        """
        try:
            # TagManager expects "EXCLUSIVE" or "NON_EXCLUSIVE" (without FRANCHISE_ prefix)
            # Strip "FRANCHISE_" if present
            tag_type_for_manager = tag_type.replace("FRANCHISE_", "") if tag_type.startswith("FRANCHISE_") else tag_type

            # Apply franchise tag (creates 1-year contract)
            tag_salary = self.tag_mgr.apply_franchise_tag(
                player_id=player_id,
                team_id=team_id,
                season=season,
                dynasty_id=dynasty_id,
                position=player_position,
                tag_type=tag_type_for_manager,
                tag_date=tag_date
            )

            # Get the created contract
            tag_record = self.tag_mgr.get_player_franchise_tags(
                player_id=player_id,
                dynasty_id=dynasty_id
            )

            contract_id = None
            if tag_record:
                latest_tag = tag_record[-1]
                contract_id = latest_tag.get('contract_id')

            return {
                "success": True,
                "tag_salary": tag_salary,
                "contract_id": contract_id,
                "cap_impact": tag_salary,
                "tag_type": tag_type,
                "player_position": player_position
            }

        except Exception as e:
            self.logger.error(f"Failed to execute franchise tag: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    def execute_transition_tag(
        self,
        team_id: int,
        player_id: str,
        player_position: str,
        season: int,
        tag_date,
        dynasty_id: str = "default"
    ):
        """
        Execute transition tag application.

        Args:
            team_id: Team applying the tag
            player_id: Player being tagged
            player_position: Player's position
            season: Season year
            tag_date: Date tag was applied
            dynasty_id: Dynasty context

        Returns:
            Dict with tag_salary, contract_id, cap_impact, success status
        """
        try:
            # Apply transition tag (creates 1-year contract)
            tag_salary = self.tag_mgr.apply_transition_tag(
                player_id=player_id,
                team_id=team_id,
                season=season,
                dynasty_id=dynasty_id,
                position=player_position,
                tag_date=tag_date
            )

            # Get the created contract
            tag_record = self.tag_mgr.get_player_franchise_tags(
                player_id=player_id,
                dynasty_id=dynasty_id
            )

            contract_id = None
            if tag_record:
                latest_tag = tag_record[-1]
                contract_id = latest_tag.get('contract_id')

            return {
                "success": True,
                "tag_salary": tag_salary,
                "contract_id": contract_id,
                "cap_impact": tag_salary,
                "tag_type": "TRANSITION",
                "player_position": player_position
            }

        except Exception as e:
            self.logger.error(f"Failed to execute transition tag: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    # ========================================================================
    # RFA TENDER OPERATIONS
    # ========================================================================

    def execute_rfa_tender(
        self,
        team_id: int,
        player_id: str,
        tender_level: str,
        season: int,
        tender_date,
        player_previous_salary: int,
        dynasty_id: str = "default"
    ):
        """
        Execute RFA tender application.

        Args:
            team_id: Team tendering the player
            player_id: Player being tendered
            tender_level: FIRST_ROUND, SECOND_ROUND, ORIGINAL_ROUND, RIGHT_OF_FIRST_REFUSAL
            season: Season year
            tender_date: Date tender was applied
            player_previous_salary: Player's previous year salary
            dynasty_id: Dynasty context

        Returns:
            Dict with tender_salary, contract_id, cap_impact, success status
        """
        try:
            # Apply RFA tender (creates 1-year contract)
            tender_salary = self.tag_mgr.apply_rfa_tender(
                player_id=player_id,
                team_id=team_id,
                tender_level=tender_level,
                season=season,
                tender_date=tender_date,
                player_previous_salary=player_previous_salary,
                dynasty_id=dynasty_id
            )

            # Get the created contract
            tender_record = self.cap_db.get_rfa_tender(
                player_id=player_id,
                season=season,
                dynasty_id=dynasty_id
            )

            contract_id = None
            if tender_record:
                # RFA tender doesn't create contract until accepted
                # Store tender_id for now
                contract_id = tender_record.get('tender_id')

            return {
                "success": True,
                "tender_salary": tender_salary,
                "tender_level": tender_level,
                "contract_id": contract_id,
                "cap_impact": tender_salary
            }

        except Exception as e:
            self.logger.error(f"Failed to execute RFA tender: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    def execute_offer_sheet(
        self,
        player_id: str,
        offering_team_id: int,
        original_team_id: int,
        contract_years: int,
        total_value: int,
        signing_bonus: int,
        base_salaries: list,
        season: int,
        is_matched: bool,
        dynasty_id: str = "default"
    ):
        """
        Execute RFA offer sheet (matched or unmatched).

        Args:
            player_id: Player receiving offer sheet
            offering_team_id: Team making the offer
            original_team_id: Original team with RFA rights
            contract_years: Years in offer
            total_value: Total contract value
            signing_bonus: Signing bonus amount
            base_salaries: Year-by-year base salaries
            season: Season year
            is_matched: Whether original team matched
            dynasty_id: Dynasty context

        Returns:
            Dict with contract_id, signing_team_id, cap_impact, success status
        """
        try:
            # Determine which team gets the player
            signing_team_id = original_team_id if is_matched else offering_team_id

            # Validate cap space for signing team
            is_valid, error_msg = self.calculator.validate_transaction(
                team_id=signing_team_id,
                season=season,
                cap_impact=base_salaries[0] if base_salaries else 0,
                dynasty_id=dynasty_id
            )

            if not is_valid:
                return {
                    "success": False,
                    "error_message": f"Cap validation failed: {error_msg}"
                }

            # Create contract
            contract_id = self.contract_mgr.create_contract(
                player_id=player_id,
                team_id=signing_team_id,
                contract_years=contract_years,
                total_value=total_value,
                signing_bonus=signing_bonus,
                base_salaries=base_salaries,
                guaranteed_amounts=[0] * contract_years,  # Offer sheets typically not guaranteed
                contract_type="VETERAN",
                season=season,
                dynasty_id=dynasty_id
            )

            return {
                "success": True,
                "contract_id": contract_id,
                "signing_team_id": signing_team_id,
                "cap_impact": base_salaries[0] if base_salaries else 0,
                "is_matched": is_matched
            }

        except Exception as e:
            self.logger.error(f"Failed to execute offer sheet: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    # ========================================================================
    # CONTRACT OPERATIONS
    # ========================================================================

    def execute_ufa_signing(
        self,
        player_id: str,
        team_id: int,
        contract_years: int,
        total_value: int,
        signing_bonus: int,
        base_salaries: list,
        guaranteed_amounts: list,
        season: int,
        dynasty_id: str = "default"
    ):
        """
        Execute UFA signing with cap validation.

        Args:
            player_id: Player being signed
            team_id: Team signing the player
            contract_years: Years in contract
            total_value: Total contract value
            signing_bonus: Signing bonus amount
            base_salaries: Year-by-year base salaries
            guaranteed_amounts: Year-by-year guaranteed amounts
            season: Season year
            dynasty_id: Dynasty context

        Returns:
            Dict with contract_id, cap_impact, cap_space_remaining, success status
        """
        try:
            # Validate cap space
            first_year_cap_hit = base_salaries[0] if base_salaries else 0
            is_valid, error_msg = self.calculator.validate_transaction(
                team_id=team_id,
                season=season,
                cap_impact=first_year_cap_hit,
                dynasty_id=dynasty_id
            )

            if not is_valid:
                return {
                    "success": False,
                    "error_message": f"Insufficient cap space: {error_msg}"
                }

            # Create contract
            contract_id = self.contract_mgr.create_contract(
                player_id=player_id,
                team_id=team_id,
                contract_years=contract_years,
                total_value=total_value,
                signing_bonus=signing_bonus,
                base_salaries=base_salaries,
                guaranteed_amounts=guaranteed_amounts,
                contract_type="VETERAN",
                season=season,
                dynasty_id=dynasty_id
            )

            # Get remaining cap space
            cap_space = self.calculator.calculate_team_cap_space(
                team_id=team_id,
                season=season,
                dynasty_id=dynasty_id
            )

            return {
                "success": True,
                "contract_id": contract_id,
                "cap_impact": first_year_cap_hit,
                "cap_space_remaining": cap_space
            }

        except Exception as e:
            self.logger.error(f"Failed to execute UFA signing: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    def execute_contract_restructure(
        self,
        contract_id: int,
        year_to_restructure: int,
        amount_to_convert: int,
        dynasty_id: str = "default"
    ):
        """
        Execute contract restructure.

        Args:
            contract_id: Contract to restructure
            year_to_restructure: Which year to restructure
            amount_to_convert: Base salary amount to convert to bonus
            dynasty_id: Dynasty context

        Returns:
            Dict with cap_savings, new_cap_hits, dead_money_increase, success status
        """
        try:
            # Execute restructure
            result = self.contract_mgr.restructure_contract(
                contract_id=contract_id,
                year_to_restructure=year_to_restructure,
                amount_to_convert=amount_to_convert,
                dynasty_id=dynasty_id
            )

            return {
                "success": True,
                "cap_savings": result.get('cap_savings', 0),
                "new_cap_hits": result.get('new_cap_hits', {}),
                "dead_money_increase": result.get('dead_money_increase', 0)
            }

        except Exception as e:
            self.logger.error(f"Failed to execute contract restructure: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    # ========================================================================
    # PLAYER RELEASE OPERATIONS
    # ========================================================================

    def execute_player_release(
        self,
        contract_id: int,
        release_date,
        june_1_designation: bool = False,
        dynasty_id: str = "default"
    ):
        """
        Execute player release.

        Args:
            contract_id: Contract to terminate
            release_date: Date of release
            june_1_designation: Whether to use June 1 designation
            dynasty_id: Dynasty context

        Returns:
            Dict with dead_money, cap_savings, cap_space_available, success status
        """
        try:
            # Execute release
            result = self.contract_mgr.release_player(
                contract_id=contract_id,
                release_date=release_date,
                june_1_designation=june_1_designation,
                dynasty_id=dynasty_id
            )

            return {
                "success": True,
                "dead_money": result.get('dead_money', 0),
                "cap_savings": result.get('cap_savings', 0),
                "cap_space_available": result.get('cap_space_available', 0),
                "june_1_designation": june_1_designation
            }

        except Exception as e:
            self.logger.error(f"Failed to execute player release: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }


# ============================================================================
# SPECIALIZED EVENT HANDLERS
# ============================================================================

class TagEventHandler:
    """
    Specialized handler for franchise and transition tag events.

    Thin wrapper that extracts event data and delegates to EventCapBridge.
    """

    def __init__(self, bridge: EventCapBridge):
        """
        Initialize tag event handler.

        Args:
            bridge: EventCapBridge instance to delegate to
        """
        self.bridge = bridge

    def handle_franchise_tag(self, event_data: dict):
        """
        Process franchise tag event data.

        Expected event_data structure:
        {
            "team_id": int,
            "player_id": str,
            "player_position": str,
            "season": int,
            "tag_type": str,  # FRANCHISE_EXCLUSIVE or FRANCHISE_NON_EXCLUSIVE
            "tag_date": date,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_franchise_tag()
        """
        return self.bridge.execute_franchise_tag(
            team_id=event_data["team_id"],
            player_id=event_data["player_id"],
            player_position=event_data["player_position"],
            season=event_data["season"],
            tag_type=event_data["tag_type"],
            tag_date=event_data["tag_date"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )

    def handle_transition_tag(self, event_data: dict):
        """
        Process transition tag event data.

        Expected event_data structure:
        {
            "team_id": int,
            "player_id": str,
            "player_position": str,
            "season": int,
            "tag_date": date,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_transition_tag()
        """
        return self.bridge.execute_transition_tag(
            team_id=event_data["team_id"],
            player_id=event_data["player_id"],
            player_position=event_data["player_position"],
            season=event_data["season"],
            tag_date=event_data["tag_date"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )


class ContractEventHandler:
    """
    Specialized handler for contract-related events.

    Handles UFA signings and contract restructures.
    """

    def __init__(self, bridge: EventCapBridge):
        """
        Initialize contract event handler.

        Args:
            bridge: EventCapBridge instance to delegate to
        """
        self.bridge = bridge

    def handle_ufa_signing(self, event_data: dict):
        """
        Process UFA signing event.

        Expected event_data structure:
        {
            "player_id": str,
            "team_id": int,
            "contract_years": int,
            "total_value": int,
            "signing_bonus": int,
            "base_salaries": list[int],
            "guaranteed_amounts": list[int],
            "season": int,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_ufa_signing()
        """
        return self.bridge.execute_ufa_signing(
            player_id=event_data["player_id"],
            team_id=event_data["team_id"],
            contract_years=event_data["contract_years"],
            total_value=event_data["total_value"],
            signing_bonus=event_data["signing_bonus"],
            base_salaries=event_data["base_salaries"],
            guaranteed_amounts=event_data["guaranteed_amounts"],
            season=event_data["season"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )

    def handle_contract_restructure(self, event_data: dict):
        """
        Process contract restructure event.

        Expected event_data structure:
        {
            "contract_id": int,
            "year_to_restructure": int,
            "amount_to_convert": int,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_contract_restructure()
        """
        return self.bridge.execute_contract_restructure(
            contract_id=event_data["contract_id"],
            year_to_restructure=event_data["year_to_restructure"],
            amount_to_convert=event_data["amount_to_convert"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )


class ReleaseEventHandler:
    """
    Specialized handler for player release events.

    Handles standard releases and June 1 designated releases.
    """

    def __init__(self, bridge: EventCapBridge):
        """
        Initialize release event handler.

        Args:
            bridge: EventCapBridge instance to delegate to
        """
        self.bridge = bridge

    def handle_player_release(self, event_data: dict):
        """
        Process player release event.

        Expected event_data structure:
        {
            "contract_id": int,
            "release_date": date,
            "june_1_designation": bool (optional, default False),
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_player_release()
        """
        return self.bridge.execute_player_release(
            contract_id=event_data["contract_id"],
            release_date=event_data["release_date"],
            june_1_designation=event_data.get("june_1_designation", False),
            dynasty_id=event_data.get("dynasty_id", "default")
        )


class RFAEventHandler:
    """
    Specialized handler for RFA tender and offer sheet events.

    Handles RFA tenders and RFA offer sheets (matched/unmatched).
    """

    def __init__(self, bridge: EventCapBridge):
        """
        Initialize RFA event handler.

        Args:
            bridge: EventCapBridge instance to delegate to
        """
        self.bridge = bridge

    def handle_rfa_tender(self, event_data: dict):
        """
        Process RFA tender event.

        Expected event_data structure:
        {
            "team_id": int,
            "player_id": str,
            "tender_level": str,  # FIRST_ROUND, SECOND_ROUND, ORIGINAL_ROUND, RIGHT_OF_FIRST_REFUSAL
            "season": int,
            "tender_date": date,
            "player_previous_salary": int,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_rfa_tender()
        """
        return self.bridge.execute_rfa_tender(
            team_id=event_data["team_id"],
            player_id=event_data["player_id"],
            tender_level=event_data["tender_level"],
            season=event_data["season"],
            tender_date=event_data["tender_date"],
            player_previous_salary=event_data["player_previous_salary"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )

    def handle_offer_sheet(self, event_data: dict):
        """
        Process RFA offer sheet event (matched/unmatched).

        Expected event_data structure:
        {
            "player_id": str,
            "offering_team_id": int,
            "original_team_id": int,
            "contract_years": int,
            "total_value": int,
            "signing_bonus": int,
            "base_salaries": list[int],
            "season": int,
            "is_matched": bool,
            "dynasty_id": str (optional)
        }

        Args:
            event_data: Event data dictionary

        Returns:
            Result dict from bridge.execute_offer_sheet()
        """
        return self.bridge.execute_offer_sheet(
            player_id=event_data["player_id"],
            offering_team_id=event_data["offering_team_id"],
            original_team_id=event_data["original_team_id"],
            contract_years=event_data["contract_years"],
            total_value=event_data["total_value"],
            signing_bonus=event_data["signing_bonus"],
            base_salaries=event_data["base_salaries"],
            season=event_data["season"],
            is_matched=event_data["is_matched"],
            dynasty_id=event_data.get("dynasty_id", "default")
        )
