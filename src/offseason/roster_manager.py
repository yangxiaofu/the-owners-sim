"""
Roster Manager

Handles NFL roster management operations including:
- Roster expansion (53 → 90 players)
- Final roster cuts (90 → 53 players)
- Practice squad management (16 players)
- Roster validation and compliance
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime

from database.player_roster_api import PlayerRosterAPI
from salary_cap.cap_database_api import CapDatabaseAPI
from src.persistence.transaction_logger import TransactionLogger
from team_management.gm_archetype import GMArchetype


class RosterManager:
    """
    Manages roster expansion and cuts throughout the offseason.

    Responsibilities:
    - Expand rosters to 90 players (post-draft)
    - Fill open roster spots with UDFAs
    - Execute roster cuts (90 → 53)
    - Manage practice squad (16 players)
    - Validate roster composition and size
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        enable_persistence: bool = True,
        gm_archetype: Optional[GMArchetype] = None
    ):
        """
        Initialize roster manager.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            enable_persistence: Whether to save roster actions to database
            gm_archetype: Optional GM archetype for personality-based decisions
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.enable_persistence = enable_persistence
        self.gm = gm_archetype  # Store GM archetype

        # Initialize database APIs
        self.player_api = PlayerRosterAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)
        self.transaction_logger = TransactionLogger(database_path)

        # Initialize TeamContextService if GM archetype provided
        self.context_service = None
        if self.gm:
            from transactions.team_context_service import TeamContextService
            self.context_service = TeamContextService(database_path, dynasty_id)

        # Will be initialized when needed
        self.roster_limits = {
            'offseason': 90,
            'regular_season': 53,
            'practice_squad': 16
        }

    def get_roster(
        self,
        team_id: int,
        include_practice_squad: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get current roster for a team.

        Args:
            team_id: Team ID (1-32)
            include_practice_squad: Include practice squad players

        Returns:
            List of player dictionaries
        """
        # TODO: Implement roster retrieval
        # - Get all active roster players from database
        # - Optionally include practice squad
        # - Return sorted by depth chart position
        raise NotImplementedError("Roster retrieval not yet implemented")

    def expand_roster(self, team_id: int) -> Dict[str, Any]:
        """
        Expand roster from 53 to 90 players (post-draft).

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with expansion results
        """
        # TODO: Implement roster expansion
        # - Increase roster limit to 90
        # - Sign UDFAs to fill open spots
        # - Return summary of signings
        raise NotImplementedError("Roster expansion not yet implemented")

    def cut_player(
        self,
        team_id: int,
        player_id: str,
        june_1_designation: bool = False
    ) -> Dict[str, Any]:
        """
        Cut a player from the roster.

        Args:
            team_id: Team ID (1-32)
            player_id: Player to cut
            june_1_designation: Whether to designate as June 1 cut

        Returns:
            Dictionary with cut results and cap impact
        """
        # TODO: Implement player cut
        # - Remove player from roster
        # - Calculate dead money and cap savings
        # - Handle June 1 designation if specified
        # - Trigger player release event
        raise NotImplementedError("Player cut not yet implemented")

    def finalize_53_man_roster(self, team_id: int) -> Dict[str, Any]:
        """
        Finalize 53-man roster (August 26 deadline).

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with finalization results
        """
        # TODO: Implement roster finalization
        # - Validate roster has exactly 53 players
        # - Validate position requirements (e.g., min 2 QBs)
        # - Move cut players to waiver wire
        # - Return validation results
        raise NotImplementedError("Roster finalization not yet implemented")

    def finalize_53_man_roster_ai(self, team_id: int, gm_archetype: Optional[GMArchetype] = None) -> Dict[str, Any]:
        """
        AI logic to cut 90-man roster down to 53.

        Ultra-thin orchestrator delegating to helper methods.

        Algorithm:
        1. Rank all 90 players by value score
        2. Select top 53 meeting position minimums
        3. Cut bottom 37

        Args:
            team_id: Team ID (1-32)
            gm_archetype: Optional GM archetype for personality-based decisions (overrides constructor param)

        Returns:
            Dict with final_roster and cuts lists
        """
        # Use method parameter if provided, otherwise fall back to constructor parameter
        active_gm = gm_archetype if gm_archetype is not None else self.gm

        # Temporarily set GM for this operation
        original_gm = self.gm
        original_context_service = self.context_service

        try:
            # Set active GM for this operation
            self.gm = active_gm

            # Initialize context service if needed
            if self.gm and not self.context_service:
                from transactions.team_context_service import TeamContextService
                self.context_service = TeamContextService(self.database_path, self.dynasty_id)
            # Step 1: Get current 90-man roster (mock for now)
            roster_90 = self._get_mock_90_man_roster(team_id)

            if len(roster_90) <= 53:
                return {'final_roster': roster_90, 'cuts': [], 'message': 'Roster already at 53 or below'}

            # Step 2: Rank players by value (with optional GM personality modifiers)
            ranked_players = self._rank_players_by_value(roster_90, team_id=team_id)

            # Step 3: Select top 53 with position minimums
            final_53 = self._select_53_with_position_mins(ranked_players)

            # Step 4: Identify cuts
            final_53_ids = {p['player_id'] for p in final_53}
            cuts = [p for p in roster_90 if p['player_id'] not in final_53_ids]

            # Step 5: Log roster cut transactions
            if self.enable_persistence:
                for player in cuts:
                    try:
                        self.transaction_logger.log_transaction(
                            dynasty_id=self.dynasty_id,
                            season=self.season_year,
                            transaction_type="ROSTER_CUT",
                            player_id=player['player_id'],
                            player_name=player.get('player_name', f"Player {player['player_id']}"),
                            transaction_date=date.today(),
                            position=player.get('position'),
                            from_team_id=team_id,
                            to_team_id=None,
                            details={
                                "cut_type": "53_MAN_ROSTER_FINALIZATION",
                                "reason": "Did not make final 53-man roster",
                                "value_score": player.get('value_score', 0)
                            }
                        )
                    except Exception as e:
                        # Don't fail the whole operation if logging fails
                        pass

            return {
                'final_roster': final_53,
                'cuts': cuts,
                'total_cut': len(cuts)
            }

        finally:
            # Restore original GM and context service
            self.gm = original_gm
            self.context_service = original_context_service

    def _get_mock_90_man_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get mock 90-man roster for testing.

        TODO: Replace with actual database query.

        Returns:
            List of 90 player dicts
        """
        # Mock roster - in real implementation, query database
        return []

    def _rank_players_by_value(self, roster: List[Dict[str, Any]], team_id: int = None) -> List[Dict[str, Any]]:
        """
        Rank players by value score.

        If GM archetype provided: Uses GM personality modifiers (Phase 3)
        If not provided: Uses objective value only (backward compatible)

        Value score = (position_value * overall) - cap_hit_penalty

        Args:
            roster: List of player dicts
            team_id: Team ID for team context (required if GM archetype provided)

        Returns:
            Sorted list (highest value first)
        """
        # Build team context once if GM archetype provided
        team_context = None
        if self.gm and self.context_service and team_id:
            team_context = self.context_service.build_team_context(
                team_id=team_id,
                season=self.season_year,
                needs_analyzer=None,  # Not needed for roster cuts
                is_offseason=True,
                roster_mode="offseason"
            )

        for player in roster:
            # Get position value multiplier
            pos_value = self._get_position_value_multiplier(player['position'])

            # Get cap hit (default to league min if not available)
            cap_hit = player.get('cap_hit', 1_000_000)

            # Calculate objective value score
            # Higher overall and cheaper players score better
            objective_value = (pos_value * player['overall']) - (cap_hit / 1_000_000)

            # Apply GM personality modifiers if available
            if self.gm and team_context:
                # Convert player dict to Player object
                player_obj = self._create_player_from_dict(player)

                # Apply GM personality modifiers
                from transactions.personality_modifiers import PersonalityModifiers
                player['value_score'] = PersonalityModifiers.apply_roster_cut_modifier(
                    player=player_obj,
                    objective_value=objective_value,
                    gm=self.gm,
                    team_context=team_context
                )
            else:
                # No GM modifiers - use objective value only
                player['value_score'] = objective_value

        # Sort by value score (highest first)
        return sorted(roster, key=lambda p: p['value_score'], reverse=True)

    def _get_position_value_multiplier(self, position: str) -> float:
        """
        Get position value multiplier.

        Pure data - no logic.
        Premium positions get higher multipliers.

        Args:
            position: Position name

        Returns:
            Value multiplier (1.0-2.0)
        """
        position_values = {
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

        return position_values.get(position, 1.0)

    def _select_53_with_position_mins(self, ranked_players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select top 53 players while meeting NFL position minimums.

        NFL roster requirements:
        - At least 1 QB
        - At least 5 OL
        - At least 4 DL
        - At least 3 LB
        - At least 3 DB
        - At least 1 K
        - At least 1 P

        Args:
            ranked_players: Players sorted by value

        Returns:
            List of 53 selected players
        """
        position_minimums = {
            'quarterback': 1,
            'offensive_line': 5,  # Any OL position
            'defensive_line': 4,  # Any DL position
            'linebacker': 3,
            'defensive_back': 3,  # Any DB position
            'kicker': 1,
            'punter': 1
        }

        # Position groupings
        ol_positions = {'left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'center'}
        dl_positions = {'defensive_end', 'defensive_tackle'}
        db_positions = {'cornerback', 'safety'}

        selected = []
        position_counts = {
            'quarterback': 0,
            'offensive_line': 0,
            'defensive_line': 0,
            'linebacker': 0,
            'defensive_back': 0,
            'kicker': 0,
            'punter': 0
        }

        # First pass: Take top players to meet minimums
        for player in ranked_players:
            if len(selected) >= 53:
                break

            pos = player['position']

            # Map to position group
            if pos == 'quarterback':
                group = 'quarterback'
            elif pos in ol_positions:
                group = 'offensive_line'
            elif pos in dl_positions:
                group = 'defensive_line'
            elif pos == 'linebacker':
                group = 'linebacker'
            elif pos in db_positions:
                group = 'defensive_back'
            elif pos == 'kicker':
                group = 'kicker'
            elif pos == 'punter':
                group = 'punter'
            else:
                group = 'other'

            # Check if we need this position
            if group in position_counts:
                min_needed = position_minimums.get(group, 0)
                if position_counts[group] < min_needed or len(selected) < 53:
                    selected.append(player)
                    position_counts[group] += 1
            elif len(selected) < 53:
                selected.append(player)

        return selected[:53]

    def _create_player_from_dict(self, player_dict: Dict[str, Any]) -> 'Player':
        """
        Convert player dict to Player object for modifier evaluation.

        Args:
            player_dict: Player data dict with fields like overall, age, cap_hit, joined_date

        Returns:
            Player object with necessary attributes for roster cut evaluation
        """
        from team_management.players.player import Player

        # Create minimal Player object with required fields
        player_obj = Player(
            name=player_dict.get('player_name', f"Player {player_dict['player_id']}"),
            number=player_dict.get('number', 99),
            primary_position=player_dict['position'],
            player_id=player_dict['player_id']
        )

        # Add roster cut-specific attributes
        player_obj.age = player_dict.get('age', 25)
        player_obj.cap_hit = player_dict.get('cap_hit', 1_000_000)

        # Calculate years_with_team from joined_date
        player_obj.years_with_team = self._calculate_years_with_team(
            player_dict.get('joined_date'),
            self.season_year
        )

        # Add overall rating (used in modifier calculations)
        if 'overall' in player_dict:
            player_obj.ratings = player_obj.ratings or {}
            player_obj.ratings['overall'] = player_dict['overall']

        return player_obj

    def _calculate_years_with_team(self, joined_date: Optional[str], current_season: int) -> int:
        """
        Calculate how many years a player has been with current team.

        Args:
            joined_date: Date player joined team (YYYY-MM-DD format) or None
            current_season: Current season year (e.g., 2024)

        Returns:
            Years with team (0 if joined_date unavailable)
        """
        if not joined_date:
            return 0

        try:
            # Parse joined_date (format: YYYY-MM-DD)
            joined_dt = datetime.strptime(joined_date, '%Y-%m-%d')
            joined_year = joined_dt.year

            # Calculate years with team
            years_with_team = current_season - joined_year

            # Minimum 0 years (in case of future dates or errors)
            return max(0, years_with_team)

        except (ValueError, TypeError):
            # If parsing fails, default to 0
            return 0

    def create_practice_squad(self, team_id: int) -> Dict[str, Any]:
        """
        Create practice squad (up to 16 players).

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with practice squad composition
        """
        # TODO: Implement practice squad creation
        # - Sign eligible players from waiver wire
        # - Validate practice squad eligibility rules
        # - Return practice squad roster
        raise NotImplementedError("Practice squad creation not yet implemented")

    def validate_roster(self, team_id: int) -> Dict[str, Any]:
        """
        Validate roster composition and compliance.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with validation results and any violations
        """
        # TODO: Implement roster validation
        # - Check roster size limits
        # - Check position requirements
        # - Check salary cap compliance
        # - Return list of violations if any
        raise NotImplementedError("Roster validation not yet implemented")
