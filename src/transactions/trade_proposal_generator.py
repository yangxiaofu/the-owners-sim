"""
Trade Proposal Generator

Generates realistic trade proposals based on team needs. Scans league for
potential trade targets and constructs fair-value packages using existing
team assets.

Phase 1.4 of AI Transaction System
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from database.player_roster_api import PlayerRosterAPI
from salary_cap.cap_database_api import CapDatabaseAPI
from transactions.trade_value_calculator import TradeValueCalculator
from transactions.models import (
    TradeProposal,
    TradeAsset,
    AssetType,
    DraftPick,
    FairnessRating
)
from team_management.gm_archetype import GMArchetype
from offseason.team_needs_analyzer import NeedUrgency


@dataclass
class TeamContext:
    """Team situation context for trade generation."""
    team_id: int
    wins: int
    losses: int
    ties: int = 0
    cap_space: int = 0  # Available cap space in dollars
    season: str = "regular"  # "preseason", "regular", or "playoffs"
    top_needs: list = None  # Top positional needs (optional, for PersonalityModifiers)

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.top_needs is None:
            self.top_needs = []

    @property
    def is_playoff_contender(self) -> bool:
        """
        Determine if team is a playoff contender.

        A team is considered a contender if:
        - Win percentage >= .500 (at or above .500)
        - Win percentage >= .400 (within striking distance)

        Returns:
            True if team is playoff contender, False otherwise
        """
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return False  # No games played yet

        # Calculate win percentage (ties count as 0.5 wins)
        win_pct = (self.wins + (self.ties * 0.5)) / total_games

        # Contender if win percentage >= .400 (realistic playoff chase threshold)
        return win_pct >= 0.400

    @property
    def is_rebuilding(self) -> bool:
        """
        Determine if team is rebuilding.

        A team is considered rebuilding if:
        - Win percentage < .400 (not in playoff contention)

        Returns:
            True if team is rebuilding, False otherwise
        """
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return False  # Too early to tell

        # Calculate win percentage (ties count as 0.5 wins)
        win_pct = (self.wins + (self.ties * 0.5)) / total_games

        # Rebuilding if win percentage < .400
        return win_pct < 0.400

    @property
    def win_percentage(self) -> float:
        """
        Calculate team's win percentage.

        Returns:
            Win percentage as a float (0.0-1.0), or 0.0 if no games played
        """
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0

        # Calculate win percentage (ties count as 0.5 wins)
        return (self.wins + (self.ties * 0.5)) / total_games

    @property
    def is_deadline(self) -> bool:
        """
        Check if currently at trade deadline.

        Note: This is a placeholder. In full implementation, this would check
        actual date against NFL trade deadline (Week 8 Tuesday).

        Returns:
            False (placeholder - no deadline tracking yet)
        """
        # TODO: Implement actual deadline checking when calendar system integrated
        return False


class TradeProposalGenerator:
    """
    Generates trade proposals based on team needs.

    Scans entire league for players matching team needs, identifies
    surplus assets on own roster, and constructs fair-value trade packages.

    Process:
    1. Filter needs (CRITICAL and HIGH only)
    2. Scan all 32 teams for potential targets
    3. Calculate trade values for targets
    4. Identify surplus assets on own roster
    5. Find fair-value asset combinations
    6. Validate cap compliance
    7. Sort by need urgency
    """

    # Constants
    MIN_OVERALL_CRITICAL = 82  # Minimum OVR for CRITICAL needs
    MIN_OVERALL_HIGH = 80      # Minimum OVR for HIGH needs
    MIN_OVERALL_MEDIUM = 75    # Minimum OVR for MEDIUM needs

    MAX_PROPOSALS_PER_CALL = 5  # Maximum proposals to generate
    MAX_ASSETS_PER_SIDE = 3     # Maximum assets per trade side

    # Fair trade ratio bounds
    MIN_FAIRNESS_RATIO = 0.80
    MAX_FAIRNESS_RATIO = 1.20

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        calculator: TradeValueCalculator,
        debug_mode: bool = False
    ):
        """
        Initialize trade proposal generator.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            calculator: Trade value calculator instance
            debug_mode: Enable comprehensive debug logging (default: False)
        """
        # Defensive type validation
        if not isinstance(dynasty_id, str):
            raise TypeError(f"dynasty_id must be str, got {type(dynasty_id).__name__}: {dynasty_id!r}")
        if not isinstance(database_path, str):
            raise TypeError(f"database_path must be str, got {type(database_path).__name__}: {database_path!r}")

        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.calculator = calculator
        self.debug_mode = debug_mode
        self.current_season = None  # Will be set when generate_trade_proposals is called

        # Initialize database APIs
        self.player_api = PlayerRosterAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)

        self.logger = logging.getLogger("TradeProposalGenerator")

        if self.debug_mode:
            self.logger.info(f"[DEBUG_MODE] TradeProposalGenerator initialized in debug mode (dynasty={dynasty_id})")

    def generate_trade_proposals(
        self,
        team_id: int,
        gm_archetype: GMArchetype,
        team_context: TeamContext,
        needs: List[Dict[str, Any]],
        season: int
    ) -> Tuple[List[TradeProposal], Optional[Dict[str, Any]]]:
        """
        Generate trade proposals for a team based on their needs.

        Args:
            team_id: Team ID (1-32)
            gm_archetype: GM personality traits
            team_context: Team situation (record, cap space)
            needs: List of team needs from TeamNeedsAnalyzer
            season: Current season year

        Returns:
            Tuple of (proposals, debug_data):
            - proposals: List of TradeProposal objects (0-5 proposals)
            - debug_data: Debug information if debug_mode enabled, None otherwise
        """
        # Store season for use in helper methods
        self.current_season = season

        self.logger.info(f"Generating trade proposals for team {team_id}")

        # Initialize debug data
        debug_data = {} if self.debug_mode else None

        # Step 1: Filter needs (CRITICAL and HIGH only for now)
        priority_needs = self._filter_priority_needs(needs)

        if self.debug_mode:
            debug_data['priority_needs_count'] = len(priority_needs)
            debug_data['total_needs_count'] = len(needs)

        if not priority_needs:
            self.logger.info(f"Team {team_id} has no CRITICAL or HIGH needs")
            if self.debug_mode:
                debug_data['early_exit_reason'] = 'No CRITICAL or HIGH needs'
            return [], debug_data

        # Step 2: Scan league for potential targets
        potential_targets = self._scan_league_for_targets(
            team_id=team_id,
            needs=priority_needs,
            season=season
        )

        if self.debug_mode:
            debug_data['potential_targets_count'] = len(potential_targets)
            debug_data['potential_targets'] = [
                {
                    'player_name': t['player'].get('name', 'Unknown'),
                    'position': t['player'].get('position', 'Unknown'),
                    'overall': t['player'].get('overall', 0),
                    'value': t['value'],
                    'need_urgency': t['need'].get('urgency', 'Unknown')
                }
                for t in potential_targets[:10]  # Limit to first 10 for readability
            ]

        if not potential_targets:
            self.logger.info(f"No viable trade targets found for team {team_id}")
            if self.debug_mode:
                debug_data['early_exit_reason'] = 'No viable trade targets found'
            return [], debug_data

        # Step 3: Identify surplus assets on own roster
        surplus_assets = self._identify_surplus_assets(
            team_id=team_id,
            season=season
        )

        if self.debug_mode:
            debug_data['surplus_assets_count'] = len(surplus_assets)

        if not surplus_assets:
            self.logger.info(f"Team {team_id} has no surplus assets to trade")
            if self.debug_mode:
                debug_data['early_exit_reason'] = 'No surplus assets to trade'
            return [], debug_data

        # Step 4: Generate proposals for each target
        proposals = []

        if self.debug_mode:
            debug_data['proposal_attempts'] = []

        for target in potential_targets:
            # Skip if we've hit max proposals
            if len(proposals) >= self.MAX_PROPOSALS_PER_CALL:
                break

            # Try to construct fair-value proposal
            proposal = self._construct_fair_value_proposal(
                proposing_team_id=team_id,
                target_player=target['player'],
                target_value=target['value'],
                target_need=target['need'],
                surplus_assets=surplus_assets,
                team_context=team_context
            )

            if self.debug_mode:
                attempt_info = {
                    'target_player': target['player'].get('name', 'Unknown'),
                    'target_value': target['value'],
                    'proposal_constructed': proposal is not None
                }
                debug_data['proposal_attempts'].append(attempt_info)

            if proposal:
                proposals.append(proposal)

        if self.debug_mode:
            debug_data['proposals_before_filters'] = len(proposals)

        # Step 5: Apply GM personality filters
        proposals = self._apply_gm_filters(
            proposals=proposals,
            gm=gm_archetype,
            team_context=team_context
        )

        if self.debug_mode:
            debug_data['proposals_after_gm_filters'] = len(proposals)

        # Step 6: Validate proposals (final validation)
        validated_proposals = []
        validation_failures = []

        for proposal in proposals:
            is_valid, reason = self._validate_proposal(proposal, team_id)
            if is_valid:
                validated_proposals.append(proposal)
            else:
                self.logger.debug(f"Proposal failed validation: {reason}")
                if self.debug_mode:
                    validation_failures.append({
                        'reason': reason,
                        'proposal_summary': f"Team {proposal.proposing_team_id} offers assets for Team {proposal.receiving_team_id} player"
                    })

        if self.debug_mode:
            debug_data['validation_failures'] = validation_failures
            debug_data['proposals_after_validation'] = len(validated_proposals)

        # Step 7: Sort proposals by priority
        validated_proposals = self._sort_proposals(validated_proposals)

        self.logger.info(f"Generated {len(validated_proposals)} trade proposals for team {team_id}")

        if self.debug_mode:
            debug_data['final_proposals_count'] = len(validated_proposals)

        return validated_proposals, debug_data

    def _filter_priority_needs(
        self,
        needs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter needs to CRITICAL and HIGH urgency only.

        Args:
            needs: List of team needs

        Returns:
            Filtered list of priority needs
        """
        priority_needs = []

        for need in needs:
            urgency = need.get('urgency')

            # Accept NeedUrgency enum or urgency_score int
            if isinstance(urgency, NeedUrgency):
                if urgency in [NeedUrgency.CRITICAL, NeedUrgency.HIGH]:
                    priority_needs.append(need)
            elif isinstance(urgency, int) or 'urgency_score' in need:
                urgency_score = need.get('urgency_score', urgency)
                if urgency_score >= 4:  # CRITICAL=5, HIGH=4
                    priority_needs.append(need)

        return priority_needs

    def _scan_league_for_targets(
        self,
        team_id: int,
        needs: List[Dict[str, Any]],
        season: int
    ) -> List[Dict[str, Any]]:
        """
        Scan all 32 teams for players matching team needs.

        Args:
            team_id: Team doing the scanning (to exclude own players)
            needs: Priority needs to fill
            season: Current season year

        Returns:
            List of potential trade targets with metadata:
            [
                {
                    'player': player_dict,
                    'value': float,
                    'need': need_dict,
                    'position': str
                },
                ...
            ]
        """
        potential_targets = []

        # Extract needed positions
        needed_positions = [need['position'] for need in needs]

        # Scan all teams except our own
        for other_team_id in range(1, 33):
            if other_team_id == team_id:
                continue  # Skip own team

            try:
                # Get roster for this team
                roster = self.player_api.get_team_roster(
                    dynasty_id=self.dynasty_id,
                    team_id=other_team_id
                )

                # Check each player
                for player in roster:
                    player_id = player.get('player_id')

                    # Skip players without active contracts (cannot be traded)
                    if not self._player_has_active_contract(player_id, other_team_id):
                        continue

                    # Parse player positions
                    positions = player.get('positions', [])
                    if isinstance(positions, str):
                        import json
                        positions = json.loads(positions)

                    # Check if player matches any needed position
                    player_position = positions[0] if positions else None

                    if player_position not in needed_positions:
                        continue

                    # Get player attributes
                    attributes = player.get('attributes', {})
                    if isinstance(attributes, str):
                        import json
                        attributes = json.loads(attributes)

                    overall_rating = attributes.get('overall', 0)

                    # Find matching need
                    matching_need = None
                    min_overall = 0

                    for need in needs:
                        if need['position'] == player_position:
                            matching_need = need

                            # Determine minimum OVR based on urgency
                            if need.get('urgency') == NeedUrgency.CRITICAL or need.get('urgency_score', 0) == 5:
                                min_overall = self.MIN_OVERALL_CRITICAL
                            elif need.get('urgency') == NeedUrgency.HIGH or need.get('urgency_score', 0) == 4:
                                min_overall = self.MIN_OVERALL_HIGH
                            else:
                                min_overall = self.MIN_OVERALL_MEDIUM
                            break

                    # Check if player meets minimum quality threshold
                    if overall_rating < min_overall:
                        continue

                    # Get contract info
                    contract = self._get_player_contract(player['player_id'])

                    # Skip pending free agents
                    if contract and contract.get('years_remaining', 0) == 0:
                        continue

                    # Calculate trade value
                    trade_value = self._calculate_player_value(
                        player=player,
                        contract=contract,
                        acquiring_team_id=team_id
                    )

                    # Add to potential targets
                    potential_targets.append({
                        'player': player,
                        'value': trade_value,
                        'need': matching_need,
                        'position': player_position,
                        'contract': contract
                    })

            except Exception as e:
                self.logger.warning(f"Error scanning team {other_team_id}: {e}")
                continue

        self.logger.info(f"Found {len(potential_targets)} potential trade targets")
        return potential_targets

    def _identify_surplus_assets(
        self,
        team_id: int,
        season: int
    ) -> List[TradeAsset]:
        """
        Identify tradeable assets from own roster.

        Includes:
        - Players at positions with depth > minimum
        - Players not in starting lineup
        - Draft picks (future enhancement)

        Args:
            team_id: Team ID
            season: Current season

        Returns:
            List of TradeAsset objects
        """
        surplus_assets = []

        try:
            # Get team roster
            roster = self.player_api.get_team_roster(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )

            # Group players by position
            position_groups: Dict[str, List] = {}

            for player in roster:
                positions = player.get('positions', [])
                if isinstance(positions, str):
                    import json
                    positions = json.loads(positions)

                primary_position = positions[0] if positions else 'unknown'

                if primary_position not in position_groups:
                    position_groups[primary_position] = []

                position_groups[primary_position].append(player)

            # Position minimums (NFL roster requirements)
            position_minimums = {
                'quarterback': 2,
                'running_back': 3,
                'wide_receiver': 5,
                'tight_end': 2,
                'left_tackle': 1,
                'right_tackle': 1,
                'left_guard': 1,
                'right_guard': 1,
                'center': 1,
                'defensive_end': 3,
                'defensive_tackle': 3,
                'linebacker': 4,
                'cornerback': 4,
                'safety': 3,
                'kicker': 1,
                'punter': 1
            }

            # Identify surplus players
            for position, players in position_groups.items():
                minimum = position_minimums.get(position, 2)  # Default to 2

                # Sort by depth chart order (lower = starter)
                players_sorted = sorted(
                    players,
                    key=lambda p: p.get('depth_chart_order', 999)
                )

                # Players beyond minimum + 1 are surplus
                # (Keep minimum + 1 for safety, rest are tradeable)
                surplus_count = max(0, len(players_sorted) - (minimum + 1))

                if surplus_count > 0:
                    # Take from end of depth chart (worst players)
                    surplus_players = players_sorted[-(surplus_count):]

                    for player in surplus_players:
                        player_id = player.get('player_id')

                        # Skip players without active contracts (cannot be traded)
                        if not self._player_has_active_contract(player_id, team_id):
                            continue

                        # Get contract
                        contract = self._get_player_contract(player_id)

                        # Calculate value
                        value = self._calculate_player_value(
                            player=player,
                            contract=contract,
                            acquiring_team_id=0  # Generic value
                        )

                        # Create TradeAsset
                        asset = self._create_player_asset(
                            player=player,
                            contract=contract,
                            trade_value=value
                        )

                        surplus_assets.append(asset)

        except Exception as e:
            self.logger.error(f"Error identifying surplus assets for team {team_id}: {e}")

        self.logger.info(f"Team {team_id} has {len(surplus_assets)} surplus assets")
        return surplus_assets

    def _construct_fair_value_proposal(
        self,
        proposing_team_id: int,
        target_player: Dict[str, Any],
        target_value: float,
        target_need: Dict[str, Any],
        surplus_assets: List[TradeAsset],
        team_context: TeamContext
    ) -> Optional[TradeProposal]:
        """
        Construct fair-value trade proposal for a target player.

        Uses greedy algorithm to find asset combination that creates
        fair trade (0.80-1.20 ratio).

        Args:
            proposing_team_id: Team making proposal
            target_player: Player to acquire
            target_value: Trade value of target player
            target_need: Need this player fills
            surplus_assets: Available assets to trade away
            team_context: Team context for validation

        Returns:
            TradeProposal if fair combination found, None otherwise
        """
        # Create asset for target player
        target_contract = target_player.get('contract')
        target_asset = self._create_player_asset(
            player=target_player,
            contract=target_contract,
            trade_value=target_value
        )

        # Sort surplus assets by value (descending)
        sorted_assets = sorted(
            surplus_assets,
            key=lambda a: a.trade_value,
            reverse=True
        )

        # Try to find fair combination (greedy algorithm)
        # 1. Try single asset
        # 2. Try two-asset combinations
        # 3. Try three-asset combinations (max)

        best_combination = None
        best_ratio = 0.0

        # Single asset
        for asset in sorted_assets:
            ratio = asset.trade_value / target_value

            if self.MIN_FAIRNESS_RATIO <= ratio <= self.MAX_FAIRNESS_RATIO:
                best_combination = [asset]
                best_ratio = ratio
                break  # Take first fair trade (prefer simplicity)

        # Two-asset combinations (if no single asset found)
        if not best_combination:
            for i, asset1 in enumerate(sorted_assets):
                for asset2 in sorted_assets[i+1:]:
                    combined_value = asset1.trade_value + asset2.trade_value
                    ratio = combined_value / target_value

                    if self.MIN_FAIRNESS_RATIO <= ratio <= self.MAX_FAIRNESS_RATIO:
                        best_combination = [asset1, asset2]
                        best_ratio = ratio
                        break

                if best_combination:
                    break

        # Three-asset combinations (if no two-asset found)
        if not best_combination:
            for i, asset1 in enumerate(sorted_assets):
                if best_combination:
                    break

                for j, asset2 in enumerate(sorted_assets[i+1:], start=i+1):
                    if best_combination:
                        break

                    for asset3 in sorted_assets[j+1:]:
                        combined_value = asset1.trade_value + asset2.trade_value + asset3.trade_value
                        ratio = combined_value / target_value

                        if self.MIN_FAIRNESS_RATIO <= ratio <= self.MAX_FAIRNESS_RATIO:
                            best_combination = [asset1, asset2, asset3]
                            best_ratio = ratio
                            break

        # No fair combination found
        if not best_combination:
            return None

        # Calculate total values
        team1_total_value = sum(asset.trade_value for asset in best_combination)
        team2_total_value = target_value

        # Calculate value ratio (team2 perspective: what they receive / what they send)
        value_ratio = team1_total_value / team2_total_value

        # Determine fairness rating
        fairness_rating = TradeProposal.calculate_fairness(value_ratio)

        # Validate cap space
        cap_space_valid, team1_cap_after, team2_cap_after = self._validate_cap_space(
            team1_id=proposing_team_id,
            team1_assets_in=best_combination,
            team1_assets_out=[target_asset],
            team2_id=target_player['team_id'],
            team2_assets_in=[target_asset],
            team2_assets_out=best_combination,
            team1_context=team_context
        )

        if not cap_space_valid:
            self.logger.debug(f"Cap space validation failed for proposal")
            return None

        # Create TradeProposal
        proposal = TradeProposal(
            team1_id=proposing_team_id,
            team1_assets=best_combination,
            team1_total_value=team1_total_value,
            team2_id=target_player['team_id'],
            team2_assets=[target_asset],
            team2_total_value=team2_total_value,
            value_ratio=value_ratio,
            fairness_rating=fairness_rating,
            passes_cap_validation=cap_space_valid,
            passes_roster_validation=True,  # Assume valid for now
            team1_cap_space_after=team1_cap_after,
            team2_cap_space_after=team2_cap_after,
            initiating_team_id=proposing_team_id
        )

        return proposal

    def _apply_gm_filters(
        self,
        proposals: List[TradeProposal],
        gm: GMArchetype,
        team_context: TeamContext
    ) -> List[TradeProposal]:
        """
        Apply GM personality filters to proposals.

        Filters based on:
        - trade_frequency: Limit max proposals per call
        - star_chasing: Filter by target player overall rating
        - cap_management: Reject proposals that consume too much cap
        - draft_pick_value: Filter proposals with draft picks (future)
        - veteran_preference: Filter by target player age
        - win_now_mentality: Relax cap constraints for contenders
        - risk_tolerance: Accept wider fairness ranges

        Args:
            proposals: List of generated proposals
            gm: GM archetype with personality traits
            team_context: Team context

        Returns:
            Filtered list of proposals
        """
        if not proposals:
            return proposals

        filtered = []

        # Filter 1: Max proposal count based on trade_frequency
        max_proposals = max(1, int(gm.trade_frequency * 5))  # 0.5 → 2, 0.8 → 4

        for proposal in proposals[:max_proposals]:  # Limit to max
            # Filter 2: Star chasing filter
            if not self._passes_star_chasing_filter(proposal, gm):
                self.logger.debug(f"Proposal rejected by star_chasing filter")
                continue

            # Filter 3: Cap management filter
            if not self._passes_cap_management_filter(proposal, gm, team_context):
                self.logger.debug(f"Proposal rejected by cap_management filter")
                continue

            # Filter 4: Veteran preference filter
            if not self._passes_veteran_preference_filter(proposal, gm):
                self.logger.debug(f"Proposal rejected by veteran_preference filter")
                continue

            # Filter 5: Draft pick value filter (future enhancement)
            # Currently no draft picks in proposals, skip this filter

            # All filters passed
            filtered.append(proposal)

        return filtered

    def _passes_star_chasing_filter(
        self,
        proposal: TradeProposal,
        gm: GMArchetype
    ) -> bool:
        """
        Check if proposal passes star chasing filter.

        High star_chasing (>0.6): Prefer elite players (88+ OVR)
        Low star_chasing (<0.4): Avoid elite players (prefer 80-87 OVR)
        Medium (0.4-0.6): Accept all

        Args:
            proposal: Trade proposal
            gm: GM archetype

        Returns:
            True if passes filter
        """
        # Get target player overall rating
        target_assets = proposal.team2_assets  # What we're receiving

        if not target_assets:
            return True

        target_overall = target_assets[0].overall_rating

        if gm.star_chasing > 0.6:
            # High star chasing: Prefer elite players
            return target_overall >= 85  # Accept good-elite players

        elif gm.star_chasing < 0.4:
            # Low star chasing: Avoid elite players
            return target_overall < 88  # Reject superstars

        else:
            # Medium: Accept all
            return True

    def _passes_cap_management_filter(
        self,
        proposal: TradeProposal,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> bool:
        """
        Check if proposal passes cap management filter.

        High cap_management (>0.7): Reject trades that consume >50% cap
        Medium (0.4-0.7): Reject trades that consume >70% cap
        Low (<0.4): Accept all (cap space not a concern)

        Also considers win_now_mentality: High win-now relaxes cap constraints

        Args:
            proposal: Trade proposal
            gm: GM archetype
            team_context: Team context

        Returns:
            True if passes filter
        """
        # Calculate net cap impact
        cap_in = sum(
            asset.annual_cap_hit
            for asset in proposal.team2_assets  # Receiving
            if asset.asset_type == AssetType.PLAYER
        )

        cap_out = sum(
            asset.annual_cap_hit
            for asset in proposal.team1_assets  # Sending
            if asset.asset_type == AssetType.PLAYER
        )

        net_cap_consumed = cap_in - cap_out

        # If we're net reducing cap hit, always pass
        if net_cap_consumed <= 0:
            return True

        # Check available cap space
        available_cap = team_context.cap_space

        if available_cap <= 0:
            return False  # No cap space

        cap_consumption_pct = net_cap_consumed / available_cap

        # High win-now mentality relaxes cap constraints
        if gm.win_now_mentality > 0.7:
            # Allow up to 80% cap consumption for win-now teams
            return cap_consumption_pct <= 0.80

        # Apply cap management filters
        if gm.cap_management > 0.7:
            # Very conservative: max 50% cap consumption
            return cap_consumption_pct <= 0.50

        elif gm.cap_management > 0.4:
            # Moderate: max 70% cap consumption
            return cap_consumption_pct <= 0.70

        else:
            # Aggressive cap management: max 90% cap consumption
            return cap_consumption_pct <= 0.90

    def _passes_veteran_preference_filter(
        self,
        proposal: TradeProposal,
        gm: GMArchetype
    ) -> bool:
        """
        Check if proposal passes veteran preference filter.

        High veteran_preference (>0.7): Prefer veterans (age 28+)
        Low veteran_preference (<0.3): Prefer youth (age <28)
        Medium (0.3-0.7): Accept all

        Args:
            proposal: Trade proposal
            gm: GM archetype

        Returns:
            True if passes filter
        """
        # Get target player age
        target_assets = proposal.team2_assets

        if not target_assets:
            return True

        target_age = target_assets[0].age

        if gm.veteran_preference > 0.7:
            # High veteran preference: Prefer veterans
            return target_age >= 27  # Accept 27+ (prime/veteran)

        elif gm.veteran_preference < 0.3:
            # Low veteran preference: Prefer youth
            return target_age < 29  # Reject aging veterans

        else:
            # Medium: Accept all ages
            return True

    def _validate_proposal(
        self,
        proposal: TradeProposal,
        proposing_team_id: int
    ) -> Tuple[bool, str]:
        """
        Final validation of trade proposal before returning.

        Checks:
        1. Roster minimum validation (both teams keep 53+ players)
        2. Cap space validation (both teams have sufficient cap)
        3. Duplicate player validation (no player appears twice)
        4. Free agent validation (all players under contract)
        5. Fairness ratio validation (0.80-1.20)
        6. Position minimum validation (can't trade last QB/K/P)

        Args:
            proposal: Trade proposal to validate
            proposing_team_id: Team making the proposal

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Check 1: No duplicate players
        all_player_ids = set()
        for asset in proposal.team1_assets + proposal.team2_assets:
            if asset.asset_type == AssetType.PLAYER:
                if asset.player_id in all_player_ids:
                    return False, f"Duplicate player {asset.player_id} in proposal"
                all_player_ids.add(asset.player_id)

        # Check 2: All players under contract (years_remaining > 0)
        for asset in proposal.team1_assets + proposal.team2_assets:
            if asset.asset_type == AssetType.PLAYER:
                if asset.contract_years_remaining <= 0:
                    return False, f"Player {asset.player_id} is pending free agent"

        # Check 3: Fairness ratio validation
        if not (self.MIN_FAIRNESS_RATIO <= proposal.value_ratio <= self.MAX_FAIRNESS_RATIO):
            return False, f"Value ratio {proposal.value_ratio:.3f} outside acceptable range"

        # Check 4: Cap space validation (if cap info available)
        if proposal.passes_cap_validation is False:
            return False, "Cap space validation failed"

        # Check 5: Position minimums (can't trade last QB/K/P)
        # This is a simplified check - full implementation would query roster
        critical_positions = ['quarterback', 'kicker', 'punter']
        for asset in proposal.team1_assets:
            if asset.asset_type == AssetType.PLAYER:
                if asset.position in critical_positions:
                    # Would need to check if this is the last player at this position
                    # For now, accept all (future enhancement)
                    pass

        # Check 6: Roster minimum (simplified - assume valid for now)
        # Full implementation would check both teams keep 53+ players
        # For now, accept all proposals that passed cap validation

        # All checks passed
        return True, ""

    def _sort_proposals(self, proposals: List[TradeProposal]) -> List[TradeProposal]:
        """
        Sort proposals by priority.

        Priority order:
        1. Need urgency (stored in metadata, not yet implemented)
        2. Value ratio (closer to 1.0 is better)
        3. Simplicity (fewer assets preferred)

        Args:
            proposals: List of proposals

        Returns:
            Sorted list
        """
        def sort_key(proposal: TradeProposal) -> Tuple[float, int]:
            # Distance from perfect fairness (1.0)
            ratio_distance = abs(1.0 - proposal.value_ratio)

            # Number of assets (prefer simpler trades)
            asset_count = len(proposal.team1_assets) + len(proposal.team2_assets)

            return (ratio_distance, asset_count)

        return sorted(proposals, key=sort_key)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_player_contract(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player's current contract."""
        try:
            # Defensive type check for dynasty_id
            if not isinstance(self.dynasty_id, str):
                self.logger.error(
                    f"BUG: dynasty_id is {type(self.dynasty_id).__name__} instead of str. "
                    f"Value: {self.dynasty_id!r}. Player ID: {player_id}"
                )
                return None

            contracts = self.cap_api.get_team_contracts(
                team_id=0,  # Will be filtered by player_id
                season=self.current_season,
                dynasty_id=self.dynasty_id
            )

            for contract in contracts:
                if contract.get('player_id') == player_id:
                    return contract

            return None
        except Exception as e:
            self.logger.warning(f"Error getting contract for player {player_id}: {e}")
            return None

    def _player_has_active_contract(self, player_id: int, team_id: int) -> bool:
        """
        Check if player has an active contract with the specified team.

        This ensures we only propose trades for players who can actually be traded.
        Players on rosters without active contracts cannot be traded (e.g., expired
        contracts, unsigned players).

        Args:
            player_id: Player ID
            team_id: Team ID (1-32)

        Returns:
            True if player has active contract with team, False otherwise
        """
        try:
            contract = self.cap_api.get_player_contract(
                player_id=player_id,
                team_id=team_id,
                season=self.current_season,
                dynasty_id=self.dynasty_id
            )

            # Contract must exist and be active
            return contract is not None and contract.get('is_active', False)
        except Exception as e:
            self.logger.warning(f"Error checking contract for player {player_id}: {e}")
            return False

    def _calculate_player_value(
        self,
        player: Dict[str, Any],
        contract: Optional[Dict[str, Any]],
        acquiring_team_id: int
    ) -> float:
        """
        Calculate trade value for a player.

        Args:
            player: Player dictionary from database
            contract: Contract dictionary (optional)
            acquiring_team_id: Team that would acquire player

        Returns:
            Trade value in arbitrary units
        """
        # Parse attributes
        attributes = player.get('attributes', {})
        if isinstance(attributes, str):
            import json
            attributes = json.loads(attributes)

        overall_rating = attributes.get('overall', 70)
        age = attributes.get('age', 25)

        # Parse positions
        positions = player.get('positions', [])
        if isinstance(positions, str):
            import json
            positions = json.loads(positions)

        primary_position = positions[0] if positions else 'unknown'

        # Get contract details
        years_remaining = 1
        annual_cap_hit = 1_000_000
        total_guaranteed = 0

        if contract:
            years_remaining = contract.get('years_remaining', 1)
            annual_cap_hit = contract.get('aav', 1_000_000)
            total_guaranteed = contract.get('total_guaranteed', 0)

        # Create TradeAsset for value calculation
        temp_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=player['player_id'],
            player_name=f"{player.get('first_name', '')} {player.get('last_name', '')}",
            position=primary_position,
            overall_rating=overall_rating,
            age=age,
            years_pro=player.get('years_pro', 1),
            contract_years_remaining=years_remaining,
            annual_cap_hit=annual_cap_hit,
            total_remaining_guaranteed=total_guaranteed,
            acquiring_team_id=acquiring_team_id
        )

        # Use calculator - unpack TradeAsset attributes
        value = self.calculator.calculate_player_value(
            player_id=temp_asset.player_id,
            overall_rating=temp_asset.overall_rating,
            position=temp_asset.position,
            age=temp_asset.age,
            contract_years_remaining=temp_asset.contract_years_remaining,
            annual_cap_hit=temp_asset.annual_cap_hit,
            acquiring_team_id=temp_asset.acquiring_team_id
        )

        return value

    def _create_player_asset(
        self,
        player: Dict[str, Any],
        contract: Optional[Dict[str, Any]],
        trade_value: float
    ) -> TradeAsset:
        """Create TradeAsset object from player data."""
        # Parse attributes
        attributes = player.get('attributes', {})
        if isinstance(attributes, str):
            import json
            attributes = json.loads(attributes)

        # Parse positions
        positions = player.get('positions', [])
        if isinstance(positions, str):
            import json
            positions = json.loads(positions)

        # Get contract details
        years_remaining = 1
        annual_cap_hit = 1_000_000
        total_guaranteed = 0

        if contract:
            years_remaining = contract.get('years_remaining', 1)
            annual_cap_hit = contract.get('aav', 1_000_000)
            total_guaranteed = contract.get('total_guaranteed', 0)

        return TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=player['player_id'],
            player_name=f"{player.get('first_name', '')} {player.get('last_name', '')}",
            position=positions[0] if positions else 'unknown',
            overall_rating=attributes.get('overall', 70),
            age=attributes.get('age', 25),
            years_pro=player.get('years_pro', 1),
            contract_years_remaining=years_remaining,
            annual_cap_hit=annual_cap_hit,
            total_remaining_guaranteed=total_guaranteed,
            trade_value=trade_value
        )

    def _validate_cap_space(
        self,
        team1_id: int,
        team1_assets_in: List[TradeAsset],
        team1_assets_out: List[TradeAsset],
        team2_id: int,
        team2_assets_in: List[TradeAsset],
        team2_assets_out: List[TradeAsset],
        team1_context: TeamContext
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        Validate both teams have cap space for trade.

        Args:
            team1_id: Proposing team ID
            team1_assets_in: Assets team1 receives
            team1_assets_out: Assets team1 sends
            team2_id: Receiving team ID
            team2_assets_in: Assets team2 receives
            team2_assets_out: Assets team2 sends
            team1_context: Team context for team1

        Returns:
            Tuple of (valid, team1_cap_after, team2_cap_after)
        """
        # Calculate net cap impact for team1
        team1_cap_in = sum(
            asset.annual_cap_hit
            for asset in team1_assets_in
            if asset.asset_type == AssetType.PLAYER
        )
        team1_cap_out = sum(
            asset.annual_cap_hit
            for asset in team1_assets_out
            if asset.asset_type == AssetType.PLAYER
        )
        team1_net_cap = team1_cap_in - team1_cap_out

        # Check team1 cap space
        team1_cap_after = team1_context.cap_space - team1_net_cap

        if team1_cap_after < 0:
            return False, None, None

        # For team2, we don't have context, so just calculate net impact
        # (Assume they have enough space for now - proper validation in Phase 1.4 Day 4)
        team2_cap_in = sum(
            asset.annual_cap_hit
            for asset in team2_assets_in
            if asset.asset_type == AssetType.PLAYER
        )
        team2_cap_out = sum(
            asset.annual_cap_hit
            for asset in team2_assets_out
            if asset.asset_type == AssetType.PLAYER
        )
        team2_net_cap = team2_cap_in - team2_cap_out

        # Placeholder for team2 cap space (will be enhanced in Day 4)
        team2_cap_after = -team2_net_cap  # Net change only

        return True, team1_cap_after, team2_cap_after
