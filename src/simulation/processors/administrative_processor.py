"""
Administrative Result Processor

Specialized processor for administrative activities like contract negotiations,
free agency moves, roster adjustments, and front office decisions.
"""

from typing import Dict, Any, List, Optional
from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult
from ..results.administrative_result import AdministrativeResult
from .base_processor import BaseResultProcessor, ProcessingStrategy


class AdministrativeResultProcessor(BaseResultProcessor):
    """
    Processes administrative results with focus on roster management and business operations.
    
    Handles:
    - Contract negotiations and signings
    - Free agency acquisitions and losses
    - Roster moves and depth chart updates
    - Salary cap management
    - Front office decision tracking
    - Trade processing and validation
    """
    
    def can_process(self, result: AnySimulationResult) -> bool:
        """Check if this is an AdministrativeResult"""
        return isinstance(result, AdministrativeResult)
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process administrative result with roster and business impact"""
        if not isinstance(result, AdministrativeResult):
            return ProcessingResult(
                processed_successfully=False,
                processing_type="AdministrativeResultProcessor",
                error_messages=["Expected AdministrativeResult but received different type"]
            )
        
        admin_result: AdministrativeResult = result
        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="AdministrativeResultProcessor"
        )
        
        # Process based on strategy
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(admin_result, context, processing_result)
        else:
            self._process_full_administrative_impact(admin_result, context, processing_result)
        
        return processing_result
    
    def _process_full_administrative_impact(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                         processing_result: ProcessingResult) -> None:
        """Process administrative activities with full roster and business impact"""
        
        # 1. Process Contract Activities
        if admin_result.contract_negotiations:
            self._process_contract_activities(admin_result, context, processing_result)
        
        # 2. Process Roster Moves
        if admin_result.players_signed or admin_result.players_released or admin_result.practice_squad_moves:
            self._process_roster_changes(admin_result, context, processing_result)
        
        # 3. Process Trade Activities
        if admin_result.trade_discussions:
            self._process_trade_activities(admin_result, context, processing_result)
        
        # 4. Update Salary Cap Status
        self._update_salary_cap_metrics(admin_result, context, processing_result)
        
        # 5. Record Administrative History
        self._record_administrative_history(admin_result, context, processing_result)
    
    def _process_statistics_only(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process administrative activities for statistics only"""
        
        processing_result.add_statistic("administrative_type", admin_result.admin_type)
        processing_result.add_statistic("contracts_negotiated", len(admin_result.contract_negotiations))
        processing_result.add_statistic("players_signed", len(admin_result.players_signed))
        processing_result.add_statistic("players_released", len(admin_result.players_released))
        processing_result.add_statistic("trade_discussions", len(admin_result.trade_discussions))
        processing_result.add_statistic("salary_cap_impact", admin_result.salary_cap_changes)
        
        processing_result.teams_updated = [admin_result.team_id]
    
    def _process_contract_activities(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                   processing_result: ProcessingResult) -> None:
        """Process contract negotiations and signings"""
        
        negotiations_processed = 0
        completed_contracts = 0
        
        for negotiation in admin_result.contract_negotiations:
            player_key = f"player_{negotiation.player_name}"
            
            # Update negotiation status
            processing_result.add_state_change(f"{player_key}_negotiation_status", negotiation.current_status)
            processing_result.add_state_change(f"{player_key}_negotiation_progress", negotiation.negotiation_progress)
            
            if negotiation.current_status == "completed":
                completed_contracts += 1
                processing_result.add_side_effect(f"Contract completed: {negotiation.player_name} - {negotiation.negotiation_type}")
                
                # Process contract details if available
                if negotiation.contract_details:
                    contract_value = negotiation.contract_details.get('value', 0)
                    if contract_value >= 10000000:  # $10M+ contracts
                        processing_result.add_side_effect(f"Major contract: {negotiation.player_name} - ${contract_value:,}")
            
            elif negotiation.current_status == "stalled":
                processing_result.add_side_effect(f"Negotiation stalled: {negotiation.player_name} - {', '.join(negotiation.sticking_points)}")
            
            # Track breakthrough moments
            if negotiation.breakthrough_moments:
                for breakthrough in negotiation.breakthrough_moments:
                    processing_result.add_side_effect(f"Breakthrough: {negotiation.player_name} - {breakthrough}")
            
            negotiations_processed += 1
        
        processing_result.add_statistic("negotiations_processed", negotiations_processed)
        processing_result.add_statistic("completed_contracts", completed_contracts)
    
    def _process_roster_changes(self, admin_result: AdministrativeResult, context: ProcessingContext,
                              processing_result: ProcessingResult) -> None:
        """Process roster moves and depth chart updates"""
        
        total_moves = 0
        
        # Process signings
        for player_name in admin_result.players_signed:
            player_key = f"player_{player_name}"
            processing_result.add_state_change(f"{player_key}_roster_status", "signed")
            processing_result.add_state_change(f"{player_key}_signing_date", context.current_date.isoformat())
            processing_result.add_side_effect(f"Player signed: {player_name}")
            total_moves += 1
        
        # Process releases
        for player_name in admin_result.players_released:
            player_key = f"player_{player_name}"
            processing_result.add_state_change(f"{player_key}_roster_status", "released")
            processing_result.add_state_change(f"{player_key}_release_date", context.current_date.isoformat())
            processing_result.add_side_effect(f"Player released: {player_name}")
            total_moves += 1
        
        # Process practice squad moves
        for move in admin_result.practice_squad_moves:
            processing_result.add_side_effect(f"Practice squad move: {move}")
            total_moves += 1
        
        processing_result.add_statistic("total_roster_moves", total_moves)
        processing_result.add_statistic("players_signed_count", len(admin_result.players_signed))
        processing_result.add_statistic("players_released_count", len(admin_result.players_released))
    
    def _process_trade_activities(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process trade activities and player exchanges"""
        
        trades_processed = 0
        serious_discussions = 0
        
        for trade in admin_result.trade_discussions:
            # Track trade discussion progress
            processing_result.add_state_change(f"trade_discussion_{trade.partner_team_id}", trade.discussion_type)
            processing_result.add_state_change(f"trade_likelihood_{trade.partner_team_id}", trade.likelihood_of_completion)
            
            if trade.discussion_type == "finalized":
                processing_result.add_side_effect(f"Trade finalized with Team {trade.partner_team_id}")
                # Record players involved
                if trade.players_offered:
                    processing_result.add_side_effect(f"Players offered: {', '.join(trade.players_offered)}")
                if trade.players_requested:
                    processing_result.add_side_effect(f"Players requested: {', '.join(trade.players_requested)}")
            
            elif trade.discussion_type == "serious" and trade.likelihood_of_completion >= 0.7:
                serious_discussions += 1
                processing_result.add_side_effect(f"Serious trade talks with Team {trade.partner_team_id} - high likelihood")
            
            trades_processed += 1
        
        processing_result.add_statistic("trade_discussions_processed", trades_processed)
        processing_result.add_statistic("serious_trade_discussions", serious_discussions)
    
    def _update_salary_cap_metrics(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                 processing_result: ProcessingResult) -> None:
        """Update salary cap status and spending"""
        
        # Process salary cap changes
        if admin_result.salary_cap_changes != 0:
            processing_result.add_state_change("salary_cap_change", admin_result.salary_cap_changes)
            
            if admin_result.salary_cap_changes > 0:
                processing_result.add_side_effect(f"Salary cap increased by ${admin_result.salary_cap_changes:,.0f}")
            else:
                processing_result.add_side_effect(f"Salary cap reduced by ${abs(admin_result.salary_cap_changes):,.0f}")
        
        # Process cap space created
        if admin_result.cap_space_created > 0:
            processing_result.add_state_change("cap_space_created", admin_result.cap_space_created)
            processing_result.add_side_effect(f"Created ${admin_result.cap_space_created:,.0f} in cap space")
        
        # Process contract values negotiated
        if admin_result.contract_values_negotiated > 0:
            processing_result.add_state_change("contract_values_negotiated", admin_result.contract_values_negotiated)
            processing_result.add_statistic("total_contract_value", admin_result.contract_values_negotiated)
    
    
    def _record_administrative_history(self, admin_result: AdministrativeResult, context: ProcessingContext,
                                     processing_result: ProcessingResult) -> None:
        """Record administrative activities in historical records"""
        
        admin_summary = {
            "date": context.current_date.isoformat(),
            "administrative_type": admin_result.admin_type,
            "team_id": admin_result.team_id,
            "contracts_negotiated": len(admin_result.contract_negotiations),
            "players_signed": len(admin_result.players_signed),
            "players_released": len(admin_result.players_released),
            "trade_discussions": len(admin_result.trade_discussions),
            "salary_cap_impact": admin_result.salary_cap_changes
        }
        
        processing_result.add_state_change("administrative_history_entry", admin_summary)
        
        # Track administrative activities
        processing_result.add_state_change("administrative_activities_completed", 1)
        if admin_result.success:
            processing_result.add_state_change("successful_administrative_periods", 1)
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """AdministrativeProcessor supports business-focused strategies"""
        return strategy in [
            ProcessingStrategy.STATISTICS_ONLY,
            ProcessingStrategy.FULL_PROGRESSION,
            ProcessingStrategy.CUSTOM
        ]