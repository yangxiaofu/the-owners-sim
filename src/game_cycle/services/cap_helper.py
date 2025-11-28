"""
Cap Helper Service for Game Cycle.

Unified cap operations helper that all game cycle services use for:
- Getting cap summaries for UI display
- Validating signing transactions
- Calculating cap impacts

Uses the existing salary cap infrastructure from src/salary_cap/.
"""

from typing import Dict, Tuple, Optional
import logging

from salary_cap.cap_calculator import CapCalculator
from salary_cap.cap_database_api import CapDatabaseAPI


class CapHelper:
    """
    Unified cap operations for game cycle services.

    Provides:
    - get_cap_summary() - Full cap breakdown for UI display
    - validate_signing() - Check if transaction fits under cap
    - calculate_signing_cap_hit() - Calculate year-1 cap hit for new signing
    - calculate_release_savings() - Calculate cap savings/dead money for release
    """

    # Default NFL salary cap for 2025 season
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the cap helper.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Initialize cap APIs from existing infrastructure
        self._cap_calculator = CapCalculator(db_path)
        self._cap_db_api = CapDatabaseAPI(db_path, dynasty_id=dynasty_id)

    def get_cap_summary(self, team_id: int) -> Dict:
        """
        Get comprehensive cap summary for UI display.

        Always calculates dynamically from contract_year_details to ensure
        accuracy after any cap-affecting operation (signings, tags, cuts).

        Args:
            team_id: Team ID

        Returns:
            Dict with:
                - salary_cap_limit: int (e.g., 255400000)
                - total_spending: int
                - available_space: int (can be negative if over cap)
                - dead_money: int
                - is_compliant: bool
                - carryover: int (from previous season)
        """
        try:
            # Always use dynamic calculation from contract_year_details
            # This ensures franchise tags and other changes are immediately reflected
            reconciled = self.reconcile_team_cap(team_id)

            # Try to get dead_money from CapDatabaseAPI if available
            dead_money = 0
            carryover = 0
            try:
                cap_summary = self._cap_db_api.get_team_cap_summary(
                    team_id=team_id,
                    season=self._season,
                    dynasty_id=self._dynasty_id
                )
                if cap_summary:
                    dead_money = cap_summary.get("dead_money_total", 0)
                    carryover = cap_summary.get("carryover_from_previous", 0)
            except Exception as e:
                self._logger.debug(f"Could not get dead_money from CapDatabaseAPI: {e}")

            # Calculate total spending including dead money
            total_spending = reconciled["total_cap_hit"] + dead_money
            available_space = reconciled["salary_cap_limit"] - total_spending

            return {
                "salary_cap_limit": reconciled["salary_cap_limit"],
                "total_spending": total_spending,
                "available_space": available_space,
                "dead_money": dead_money,
                "is_compliant": available_space >= 0,
                "carryover": carryover
            }

        except Exception as e:
            self._logger.error(f"Error getting cap summary for team {team_id}: {e}")
            # Return safe defaults on error
            return {
                "salary_cap_limit": self.DEFAULT_CAP_LIMIT,
                "total_spending": 0,
                "available_space": self.DEFAULT_CAP_LIMIT,
                "dead_money": 0,
                "is_compliant": True,
                "carryover": 0
            }

    def validate_signing(self, team_id: int, cap_hit: int) -> Tuple[bool, str]:
        """
        Validate if team can sign a player with given cap hit.

        Args:
            team_id: Team ID
            cap_hit: Year-1 cap hit for the signing

        Returns:
            Tuple of (is_valid: bool, error_message: str)
            - If valid: (True, "")
            - If invalid: (False, "Over cap by $X. Need $Y, have $Z.")
        """
        try:
            # Use get_cap_summary which falls back to reconciliation
            cap_summary = self.get_cap_summary(team_id)
            cap_space = cap_summary.get("available_space", 0)

            if cap_hit > cap_space:
                shortfall = cap_hit - cap_space
                return (
                    False,
                    f"Insufficient cap space. Need ${cap_hit:,}, have ${cap_space:,}. "
                    f"Over cap by ${shortfall:,}."
                )

            return (True, "")

        except Exception as e:
            self._logger.error(f"Error validating signing for team {team_id}: {e}")
            # On error, allow the signing (fail open for now)
            return (True, "")

    def calculate_signing_cap_hit(
        self,
        total_value: int,
        signing_bonus: int,
        years: int
    ) -> int:
        """
        Calculate year-1 cap hit for a new contract.

        Uses NFL's 5-year maximum proration rule for signing bonuses.

        Args:
            total_value: Total contract value
            signing_bonus: Signing bonus amount
            years: Contract length in years

        Returns:
            Year-1 cap hit in dollars
        """
        if years <= 0:
            return 0

        # Proration is capped at 5 years per NFL rules
        proration_years = min(years, 5)

        # Signing bonus is spread evenly over proration years
        bonus_proration = signing_bonus // proration_years

        # Base salary for year 1 (simplified: even split of non-bonus value)
        non_bonus_value = total_value - signing_bonus
        year_1_base = non_bonus_value // years

        return year_1_base + bonus_proration

    def calculate_release_impact(
        self,
        player_id: int,
        team_id: int
    ) -> Dict:
        """
        Calculate cap impact of releasing a player.

        Args:
            player_id: Player ID
            team_id: Team ID

        Returns:
            Dict with:
                - cap_savings: int (immediate cap relief)
                - dead_money: int (accelerated guarantees)
                - net_cap_change: int (savings - dead_money)
                - can_release: bool
        """
        try:
            # Get player's current contract
            contract = self._cap_db_api.get_player_contract(
                player_id=player_id,
                dynasty_id=self._dynasty_id,
                season=self._season
            )

            if not contract:
                return {
                    "cap_savings": 0,
                    "dead_money": 0,
                    "net_cap_change": 0,
                    "can_release": False
                }

            # Get contract year details for current year
            contract_id = contract.get("contract_id")
            year_details = self._cap_db_api.get_contract_year_details(
                contract_id=contract_id,
                year=self._season
            )

            if not year_details:
                # No year details - estimate based on contract averages
                total_value = contract.get("total_value", 0)
                years = contract.get("contract_years", 1)
                signing_bonus = contract.get("signing_bonus", 0)

                avg_yearly = total_value // years if years > 0 else 0
                bonus_proration = signing_bonus // min(years, 5) if years > 0 else 0

                return {
                    "cap_savings": avg_yearly,
                    "dead_money": bonus_proration,
                    "net_cap_change": avg_yearly - bonus_proration,
                    "can_release": True
                }

            # Calculate from year details
            cap_hit = year_details.get("cap_hit", 0)
            base_salary = year_details.get("base_salary", 0)
            prorated_bonus = year_details.get("prorated_signing_bonus", 0)

            # Get remaining guaranteed money
            remaining_guaranteed = year_details.get("guaranteed_remaining", 0)

            # Calculate dead money (remaining prorated bonus + any remaining guarantees)
            dead_money = prorated_bonus + remaining_guaranteed

            # Cap savings = current cap hit - dead money
            cap_savings = cap_hit

            return {
                "cap_savings": cap_savings,
                "dead_money": dead_money,
                "net_cap_change": cap_savings - dead_money,
                "can_release": True
            }

        except Exception as e:
            self._logger.error(f"Error calculating release impact for player {player_id}: {e}")
            return {
                "cap_savings": 0,
                "dead_money": 0,
                "net_cap_change": 0,
                "can_release": False
            }

    def estimate_rookie_cap_hit(self, overall_pick: int) -> int:
        """
        Estimate year-1 cap hit for a rookie based on draft position.

        Uses approximate NFL rookie scale values.

        Args:
            overall_pick: Overall draft pick number (1-224)

        Returns:
            Estimated year-1 cap hit in dollars
        """
        # Approximate rookie cap hits based on 2024 values
        # Top picks get significantly more
        if overall_pick == 1:
            return 10_000_000  # ~$10M
        elif overall_pick <= 5:
            return 7_000_000 + (5 - overall_pick) * 500_000
        elif overall_pick <= 10:
            return 5_000_000 + (10 - overall_pick) * 200_000
        elif overall_pick <= 32:
            # First round (11-32)
            return 2_500_000 + (32 - overall_pick) * 50_000
        elif overall_pick <= 64:
            # Second round
            return 1_500_000 + (64 - overall_pick) * 20_000
        elif overall_pick <= 100:
            # Third round
            return 1_000_000 + (100 - overall_pick) * 10_000
        elif overall_pick <= 140:
            # Fourth round
            return 900_000 + (140 - overall_pick) * 5_000
        elif overall_pick <= 180:
            # Fifth-Sixth round
            return 800_000 + (180 - overall_pick) * 2_000
        else:
            # Seventh round - minimum salary range
            return 750_000

    def get_minimum_salary(self, years_pro: int = 0) -> int:
        """
        Get NFL minimum salary based on years of service.

        Args:
            years_pro: Years of NFL service

        Returns:
            Minimum salary in dollars (2024 values)
        """
        # 2024 NFL minimum salaries by years of service
        minimums = {
            0: 795_000,   # Rookies
            1: 915_000,
            2: 990_000,
            3: 1_065_000,
            4: 1_145_000,
            5: 1_215_000,
            6: 1_290_000,
        }
        return minimums.get(min(years_pro, 6), 1_290_000)

    def reconcile_team_cap(self, team_id: int) -> dict:
        """
        Calculate team's cap usage directly from player_contracts table.

        This method aggregates all active contracts for the team and returns
        the calculated cap values. Used when team_salary_cap table isn't
        populated or needs to be recalculated.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with:
                - total_cap_hit: int (sum of all contract cap hits)
                - active_contracts_count: int
                - salary_cap_limit: int (NFL cap for season)
                - available_space: int (cap limit - total_cap_hit)
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # First try contract_year_details for accurate cap hits
            cursor.execute('''
                SELECT COALESCE(SUM(cyd.total_cap_hit), 0) as total_cap_hit,
                       COUNT(DISTINCT pc.contract_id) as contract_count
                FROM player_contracts pc
                JOIN contract_year_details cyd ON pc.contract_id = cyd.contract_id
                WHERE pc.team_id = ?
                  AND pc.dynasty_id = ?
                  AND pc.is_active = 1
                  AND cyd.season_year = ?
            ''', (team_id, self._dynasty_id, self._season))

            row = cursor.fetchone()
            total_cap_hit = row[0] if row else 0
            contract_count = row[1] if row else 0

            # If no contract_year_details found, calculate from player_contracts
            if total_cap_hit == 0:
                cursor.execute('''
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN contract_years > 0
                            THEN (total_value - signing_bonus) / contract_years
                                 + signing_bonus / MIN(contract_years, 5)
                            ELSE 0
                        END
                    ), 0) as total_cap_hit,
                    COUNT(*) as contract_count
                    FROM player_contracts
                    WHERE team_id = ?
                      AND dynasty_id = ?
                      AND is_active = 1
                ''', (team_id, self._dynasty_id))

                row = cursor.fetchone()
                total_cap_hit = int(row[0]) if row and row[0] else 0
                contract_count = row[1] if row else 0

            conn.close()

            available_space = self.DEFAULT_CAP_LIMIT - total_cap_hit

            self._logger.info(
                f"Team {team_id} cap reconciled: ${total_cap_hit:,} used, "
                f"${available_space:,} available ({contract_count} contracts)"
            )

            return {
                "total_cap_hit": total_cap_hit,
                "active_contracts_count": contract_count,
                "salary_cap_limit": self.DEFAULT_CAP_LIMIT,
                "available_space": available_space
            }

        except Exception as e:
            self._logger.error(f"Error reconciling cap for team {team_id}: {e}")
            return {
                "total_cap_hit": 0,
                "active_contracts_count": 0,
                "salary_cap_limit": self.DEFAULT_CAP_LIMIT,
                "available_space": self.DEFAULT_CAP_LIMIT
            }

    def get_projected_cap_with_tag(
        self,
        team_id: int,
        pending_tag_cost: int = 0
    ) -> Dict:
        """
        Get projected cap space including a pending tag.

        Used by franchise tag UI to show impact of applying a tag.
        The tag counts against NEXT season's cap.

        Args:
            team_id: Team ID
            pending_tag_cost: Cost of tag being considered (0 if none selected)

        Returns:
            Dict with:
                - available_before_tag: Available cap space without the tag
                - available_after_tag: Available cap space after applying tag
                - tag_cost: The pending tag cost
                - can_afford_tag: bool - True if team can afford the tag
        """
        cap_summary = self.get_cap_summary(team_id)
        available_before = cap_summary.get("available_space", self.DEFAULT_CAP_LIMIT)

        available_after = available_before - pending_tag_cost
        can_afford = available_after >= 0

        return {
            "available_before_tag": available_before,
            "available_after_tag": available_after,
            "tag_cost": pending_tag_cost,
            "can_afford_tag": can_afford,
            "salary_cap_limit": cap_summary.get("salary_cap_limit", self.DEFAULT_CAP_LIMIT),
        }

    def validate_franchise_tag(
        self,
        team_id: int,
        tag_cost: int
    ) -> Tuple[bool, str]:
        """
        Validate if team can apply a franchise/transition tag.

        The tag counts against the cap for the season this CapHelper
        was initialized with. For franchise tags, this should be the
        NEXT season (since tags are applied before new league year).

        Args:
            team_id: Team ID
            tag_cost: Cost of the tag being applied

        Returns:
            Tuple of (is_valid: bool, error_message: str)
            - If valid: (True, "")
            - If invalid: (False, "Cannot apply tag: Over cap by $X...")
        """
        cap_summary = self.get_cap_summary(team_id)
        cap_space = cap_summary.get("available_space", 0)

        if tag_cost > cap_space:
            shortfall = tag_cost - cap_space
            return (
                False,
                f"Cannot apply tag: Over cap by ${shortfall:,}. "
                f"Tag costs ${tag_cost:,}, only ${cap_space:,} available."
            )

        return (True, "")

    # ========================================================================
    # SEASON ROLLOVER METHODS
    # ========================================================================

    def calculate_season_rollover(self, team_id: int) -> Dict:
        """
        Calculate cap rollover from completed season to next season.

        NFL Rule: Unlimited rollover - all unused cap carries over.

        Args:
            team_id: Team ID

        Returns:
            Dict with:
                - unused_cap: int (total unused cap space)
                - actual_rollover: int (same as unused - unlimited rollover)
        """
        # Get current season cap summary
        cap_summary = self.get_cap_summary(team_id)
        unused_cap = cap_summary.get("available_space", 0)

        # Unlimited rollover - all unused cap carries over (no negative rollover)
        actual_rollover = max(0, unused_cap)

        self._logger.debug(
            f"Team {team_id} rollover: ${unused_cap:,} unused, "
            f"${actual_rollover:,} rolling over"
        )

        return {
            "unused_cap": unused_cap,
            "actual_rollover": actual_rollover
        }

    def apply_rollover_to_new_season(
        self,
        team_id: int,
        from_season: int,
        to_season: int
    ) -> int:
        """
        Calculate rollover from completed season and store for new season.

        Args:
            team_id: Team ID
            from_season: Completed season year
            to_season: New season year (from_season + 1)

        Returns:
            Actual rollover amount applied
        """
        # Calculate rollover from completed season
        rollover_data = self.calculate_season_rollover(team_id)
        actual_rollover = rollover_data["actual_rollover"]

        # Update new season's cap record with carryover
        self._cap_db_api.update_team_carryover(
            team_id=team_id,
            season=to_season,
            dynasty_id=self._dynasty_id,
            carryover_amount=actual_rollover
        )

        self._logger.info(
            f"Applied ${actual_rollover:,} rollover for team {team_id} "
            f"from {from_season} to {to_season}"
        )

        return actual_rollover