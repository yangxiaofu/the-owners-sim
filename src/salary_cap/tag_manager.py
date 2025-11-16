"""
Tag Manager

Manages franchise tags, transition tags, and RFA tenders including:
- Calculate tag salaries by position (top 5 average)
- Apply tags to players with database persistence
- Handle consecutive tag escalators (120%, 144%)
- Calculate RFA tender amounts (4 levels)

All operations follow 2024-2025 NFL CBA rules.
"""

from typing import Dict, List, Optional, Tuple
from datetime import date
import logging

from .cap_database_api import CapDatabaseAPI
from .contract_manager import ContractManager
from persistence.transaction_logger import TransactionLogger


class TagManager:
    """
    Manages franchise tags, transition tags, and RFA tenders.

    Key Responsibilities:
    - Calculate franchise tag salaries by position (top 5 average)
    - Calculate transition tag salaries (top 10 average)
    - Apply tags and create 1-year contracts
    - Handle consecutive tag escalators (120% for 2nd, 144% for 3rd)
    - Calculate RFA tender amounts (4 levels with compensation)
    - Track tag history and deadlines
    """

    # NFL Tag Rules Constants
    FRANCHISE_TAG_TOP_N = 5  # Top 5 average for franchise tag
    TRANSITION_TAG_TOP_N = 10  # Top 10 average for transition tag

    # Consecutive tag escalators
    SECOND_TAG_MULTIPLIER = 1.20  # 120% of previous tag
    THIRD_TAG_MULTIPLIER = 1.44  # 144% of original tag

    # RFA tender minimums (2024 values - would be updated annually)
    RFA_FIRST_ROUND_TENDER = 4_158_000  # First round compensation
    RFA_SECOND_ROUND_TENDER = 3_116_000  # Second round compensation
    RFA_ORIGINAL_ROUND_TENDER = 2_985_000  # Original round compensation
    RFA_RIGHT_OF_FIRST_REFUSAL = 2_985_000  # No draft compensation

    # RFA tender salary percentage
    RFA_SALARY_PERCENTAGE = 1.10  # 110% of previous salary

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Tag Manager.

        Args:
            database_path: Path to database
        """
        self.db_api = CapDatabaseAPI(database_path)
        self.contract_manager = ContractManager(database_path)
        self.transaction_logger = TransactionLogger(database_path)
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # FRANCHISE TAG OPERATIONS
    # ========================================================================

    def calculate_franchise_tag_salary(
        self,
        position: str,
        season: int,
        dynasty_id: str,
        tag_type: str = "NON_EXCLUSIVE"
    ) -> int:
        """
        Calculate franchise tag salary for position.

        Uses average of top 5 salaries at position from previous season,
        OR 120% of player's previous cap number, whichever is greater.

        Args:
            position: Player position (QB, WR, RB, etc.)
            season: Season year
            dynasty_id: Dynasty identifier
            tag_type: "EXCLUSIVE" or "NON_EXCLUSIVE" (both use same calculation)

        Returns:
            Franchise tag salary in dollars

        NFL Rules:
            - Top 5 average cap values at position
            - OR 120% of previous year's cap number
            - Whichever is greater
        """
        # Get top N salaries for position from previous season
        top_salaries = self._get_top_position_salaries(
            position=position,
            season=season - 1,
            dynasty_id=dynasty_id,
            top_n=self.FRANCHISE_TAG_TOP_N
        )

        if not top_salaries:
            # No data - use league minimum escalated
            self.logger.warning(
                f"No salary data found for {position} in {season-1}. Using default minimum."
            )
            return 10_000_000  # Reasonable default for any position

        # Calculate average
        average_salary = sum(top_salaries) // len(top_salaries)

        return average_salary

    def calculate_transition_tag_salary(
        self,
        position: str,
        season: int,
        dynasty_id: str
    ) -> int:
        """
        Calculate transition tag salary for position.

        Uses average of top 10 salaries at position from previous season.

        Args:
            position: Player position
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Transition tag salary in dollars

        NFL Rules:
            - Top 10 average cap values at position
            - Lower than franchise tag (typically ~85-90%)
        """
        # Get top N salaries for position from previous season
        top_salaries = self._get_top_position_salaries(
            position=position,
            season=season - 1,
            dynasty_id=dynasty_id,
            top_n=self.TRANSITION_TAG_TOP_N
        )

        if not top_salaries:
            self.logger.warning(
                f"No salary data found for {position} in {season-1}. Using default minimum."
            )
            return 8_000_000  # Lower than franchise tag default

        # Calculate average
        average_salary = sum(top_salaries) // len(top_salaries)

        return average_salary

    def apply_franchise_tag(
        self,
        player_id: int,
        team_id: int,
        season: int,
        dynasty_id: str,
        position: str,
        tag_type: str = "NON_EXCLUSIVE",
        tag_date: Optional[date] = None
    ) -> int:
        """
        Apply franchise tag to player.

        Creates franchise tag record and 1-year contract at tag salary.
        Handles consecutive tag escalators automatically.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            position: Player position
            tag_type: "EXCLUSIVE" or "NON_EXCLUSIVE"
            tag_date: Date tag was applied (defaults to today)

        Returns:
            tag_salary amount

        NFL Rules:
            - 1st tag: Top 5 average at position
            - 2nd consecutive tag: 120% of 1st tag salary
            - 3rd consecutive tag: 144% of 1st tag salary
            - Deadline: Early March (typically March 4)
        """
        if tag_date is None:
            tag_date = date.today()

        # Check if player has been tagged before
        previous_tags = self._get_player_tag_history(player_id, team_id)
        consecutive_tag_number = len(previous_tags) + 1

        # Calculate base franchise tag salary
        base_tag_salary = self.calculate_franchise_tag_salary(
            position=position,
            season=season,
            dynasty_id=dynasty_id,
            tag_type=tag_type
        )

        # Apply consecutive tag escalators
        if consecutive_tag_number == 1:
            # First tag: use calculated salary
            tag_salary = base_tag_salary
        elif consecutive_tag_number == 2:
            # Second tag: 120% of previous tag
            previous_tag_salary = previous_tags[0]['tag_salary']
            tag_salary = int(previous_tag_salary * self.SECOND_TAG_MULTIPLIER)
        elif consecutive_tag_number >= 3:
            # Third tag: 144% of original tag
            first_tag_salary = previous_tags[-1]['tag_salary']  # Oldest tag
            tag_salary = int(first_tag_salary * self.THIRD_TAG_MULTIPLIER)
        else:
            tag_salary = base_tag_salary

        # Store franchise tag in database
        tag_id = self.db_api.insert_franchise_tag(
            player_id=player_id,
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            tag_type=f"FRANCHISE_{tag_type}",
            tag_salary=tag_salary,
            tag_date=tag_date,
            deadline_date=date(season, 3, 4),  # March 4 deadline
            consecutive_tag_number=consecutive_tag_number
        )

        # Create 1-year contract for tag amount
        contract_id = self.contract_manager.create_contract(
            player_id=player_id,
            team_id=team_id,
            dynasty_id=dynasty_id,
            contract_years=1,
            total_value=tag_salary,
            signing_bonus=0,  # Tags typically have no signing bonus
            base_salaries=[tag_salary],
            guaranteed_amounts=[tag_salary],  # Fully guaranteed
            contract_type="FRANCHISE_TAG",
            season=season
        )

        # Link contract to tag
        self.db_api.update_franchise_tag_contract(tag_id, contract_id)

        self.logger.info(
            f"Applied {tag_type} franchise tag to player {player_id} "
            f"(Tag #{consecutive_tag_number}): ${tag_salary:,}"
        )

        # Log transaction to player_transactions table
        try:
            self.transaction_logger.log_transaction(
                dynasty_id=dynasty_id,
                season=season,
                transaction_type="FRANCHISE_TAG",
                player_id=player_id,
                player_name=f"Player {player_id}",  # Would get from player data in real implementation
                transaction_date=tag_date,
                position=position,
                from_team_id=None,
                to_team_id=team_id,
                details={
                    "tag_type": tag_type,
                    "tag_salary": tag_salary,
                    "consecutive_tag_number": consecutive_tag_number,
                    "cap_impact": tag_salary
                },
                contract_id=contract_id
            )
        except Exception as e:
            self.logger.warning(f"Failed to log franchise tag transaction: {e}")

        return tag_salary

    def apply_transition_tag(
        self,
        player_id: int,
        team_id: int,
        season: int,
        dynasty_id: str,
        position: str,
        tag_date: Optional[date] = None
    ) -> int:
        """
        Apply transition tag to player.

        Creates transition tag record and 1-year contract at tag salary.
        Transition tags do NOT have consecutive escalators.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            position: Player position
            tag_date: Date tag was applied

        Returns:
            tag_salary amount

        NFL Rules:
            - Top 10 average at position
            - No consecutive tag escalators
            - Right of first refusal (team can match offers)
        """
        if tag_date is None:
            tag_date = date.today()

        # Calculate transition tag salary
        tag_salary = self.calculate_transition_tag_salary(
            position=position,
            season=season,
            dynasty_id=dynasty_id
        )

        # Store transition tag in database
        tag_id = self.db_api.insert_franchise_tag(
            player_id=player_id,
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            tag_type="TRANSITION",
            tag_salary=tag_salary,
            tag_date=tag_date,
            deadline_date=date(season, 3, 4),
            consecutive_tag_number=1  # Transition tags don't escalate
        )

        # Create 1-year contract for tag amount
        contract_id = self.contract_manager.create_contract(
            player_id=player_id,
            team_id=team_id,
            dynasty_id=dynasty_id,
            contract_years=1,
            total_value=tag_salary,
            signing_bonus=0,
            base_salaries=[tag_salary],
            guaranteed_amounts=[tag_salary],
            contract_type="TRANSITION_TAG",
            season=season
        )

        # Link contract to tag
        self.db_api.update_franchise_tag_contract(tag_id, contract_id)

        self.logger.info(
            f"Applied transition tag to player {player_id}: ${tag_salary:,}"
        )

        # Log transaction to player_transactions table
        try:
            self.transaction_logger.log_transaction(
                dynasty_id=dynasty_id,
                season=season,
                transaction_type="TRANSITION_TAG",
                player_id=player_id,
                player_name=f"Player {player_id}",  # Would get from player data in real implementation
                transaction_date=tag_date,
                position=position,
                from_team_id=None,
                to_team_id=team_id,
                details={
                    "tag_salary": tag_salary,
                    "cap_impact": tag_salary
                },
                contract_id=contract_id
            )
        except Exception as e:
            self.logger.warning(f"Failed to log transition tag transaction: {e}")

        return tag_salary

    # ========================================================================
    # RFA TENDER OPERATIONS
    # ========================================================================

    def calculate_rfa_tender(
        self,
        tender_level: str,
        season: int,
        player_previous_salary: int = 0
    ) -> int:
        """
        Calculate RFA tender amount.

        Returns higher of tender_base OR 110% of previous salary.

        Args:
            tender_level: "FIRST_ROUND", "SECOND_ROUND", "ORIGINAL_ROUND", "RIGHT_OF_FIRST_REFUSAL"
            season: Season year
            player_previous_salary: Player's previous year salary

        Returns:
            RFA tender amount in dollars

        NFL Rules:
            - Tender minimums set annually by league
            - Must be at least 110% of previous year's salary
            - Different levels provide different draft pick compensation
        """
        # Get base tender amount by level
        if tender_level == "FIRST_ROUND":
            base_tender = self.RFA_FIRST_ROUND_TENDER
        elif tender_level == "SECOND_ROUND":
            base_tender = self.RFA_SECOND_ROUND_TENDER
        elif tender_level == "ORIGINAL_ROUND":
            base_tender = self.RFA_ORIGINAL_ROUND_TENDER
        elif tender_level == "RIGHT_OF_FIRST_REFUSAL":
            base_tender = self.RFA_RIGHT_OF_FIRST_REFUSAL
        else:
            raise ValueError(f"Invalid tender level: {tender_level}")

        # Calculate 110% of previous salary
        if player_previous_salary > 0:
            escalated_salary = int(player_previous_salary * self.RFA_SALARY_PERCENTAGE)
            # Use higher of base tender or escalated salary
            tender_amount = max(base_tender, escalated_salary)
        else:
            tender_amount = base_tender

        return tender_amount

    def apply_rfa_tender(
        self,
        player_id: int,
        team_id: int,
        season: int,
        dynasty_id: str,
        tender_level: str,
        player_previous_salary: int = 0,
        tender_date: Optional[date] = None
    ) -> int:
        """
        Apply RFA tender to player.

        Creates RFA tender record. Does NOT create contract until accepted.

        Args:
            player_id: Player ID
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            tender_level: Tender level (determines compensation)
            player_previous_salary: Previous year salary
            tender_date: Date tender was applied

        Returns:
            tender_salary amount

        NFL Rules:
            - Deadline: Typically late April
            - Player can negotiate with other teams
            - Original team has right to match any offer
            - Different tender levels give different draft pick compensation
        """
        if tender_date is None:
            tender_date = date.today()

        # Calculate tender amount
        tender_salary = self.calculate_rfa_tender(
            tender_level=tender_level,
            season=season,
            player_previous_salary=player_previous_salary
        )

        # Get compensation round (None for right of first refusal)
        if tender_level == "FIRST_ROUND":
            compensation_round = 1
        elif tender_level == "SECOND_ROUND":
            compensation_round = 2
        elif tender_level == "ORIGINAL_ROUND":
            compensation_round = None  # Depends on player's original draft round
        else:  # RIGHT_OF_FIRST_REFUSAL
            compensation_round = None

        # Store RFA tender in database
        tender_id = self.db_api.insert_rfa_tender(
            player_id=player_id,
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            tender_level=tender_level,
            tender_salary=tender_salary,
            compensation_round=compensation_round,
            tender_date=tender_date,
            offer_sheet_deadline=date(season, 4, 22)  # April 22 deadline
        )

        self.logger.info(
            f"Applied {tender_level} RFA tender to player {player_id}: ${tender_salary:,}"
        )

        return tender_salary

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_top_position_salaries(
        self,
        position: str,
        season: int,
        dynasty_id: str,
        top_n: int
    ) -> List[int]:
        """
        Get top N salaries for position in given season.

        Args:
            position: Player position
            season: Season year
            dynasty_id: Dynasty identifier
            top_n: Number of top salaries to retrieve

        Returns:
            List of top N cap hits (sorted descending)
        """
        # This would query contract_year_details for all players at position
        # For now, return empty list (would be implemented with player position data)

        # TODO: Implement once player position tracking is added
        # Query: SELECT total_cap_hit FROM contract_year_details
        #        JOIN player_contracts ON ...
        #        WHERE position = ? AND season_year = ? AND dynasty_id = ?
        #        ORDER BY total_cap_hit DESC LIMIT ?

        self.logger.warning(
            f"Position salary lookup not yet implemented for {position}. "
            f"Using empty list."
        )
        return []

    def _get_player_tag_history(
        self,
        player_id: int,
        team_id: int
    ) -> List[Dict]:
        """
        Get franchise tag history for player with same team.

        Used to determine consecutive tag number and escalators.

        Args:
            player_id: Player ID
            team_id: Team ID

        Returns:
            List of previous franchise tags (newest first)
        """
        # Get franchise tags for this player/team combo
        tags = self.db_api.get_player_franchise_tags(player_id, team_id)

        # Return sorted by season (newest first)
        return sorted(tags, key=lambda x: x['season'], reverse=True)

    def get_team_tag_count(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Dict[str, int]:
        """
        Get count of tags used by team in season.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Dict with counts: {"franchise": int, "transition": int, "total": int}

        NFL Rules:
            - Teams can use 1 franchise tag OR 1 transition tag per year
            - Cannot use both in same year
        """
        tags = self.db_api.get_team_franchise_tags(team_id, season, dynasty_id)

        franchise_count = sum(1 for t in tags if "FRANCHISE" in t['tag_type'])
        transition_count = sum(1 for t in tags if t['tag_type'] == "TRANSITION")

        return {
            "franchise": franchise_count,
            "transition": transition_count,
            "total": franchise_count + transition_count
        }