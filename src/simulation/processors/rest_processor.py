"""
Rest Result Processor

Specialized processor for rest day activities that handles player recovery,
injury healing, fatigue management, and passive team development.
"""

from typing import Dict, Any, List, Optional
from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult
from ..results.rest_result import RestResult
from .base_processor import BaseResultProcessor, ProcessingStrategy


class RestResultProcessor(BaseResultProcessor):
    """
    Processes rest day results with focus on recovery and passive development.
    
    Handles:
    - Player fatigue recovery and rest benefits
    - Injury healing progression
    - Mental recovery and stress reduction
    - Passive skill maintenance and retention
    - Team bonding during downtime
    - Recovery efficiency optimization
    """
    
    def can_process(self, result: AnySimulationResult) -> bool:
        """Check if this is a RestResult"""
        return isinstance(result, RestResult)
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process rest day result with recovery and passive development impact"""
        if not isinstance(result, RestResult):
            return ProcessingResult(
                processed_successfully=False,
                processing_type="RestResultProcessor",
                error_messages=["Expected RestResult but received different type"]
            )
        
        rest_result: RestResult = result
        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="RestResultProcessor"
        )
        
        # Process based on strategy
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(rest_result, context, processing_result)
        else:
            self._process_full_rest_impact(rest_result, context, processing_result)
        
        return processing_result
    
    def _process_full_rest_impact(self, rest_result: RestResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process rest day with full recovery and passive development impact"""
        
        # 1. Process Injury Healing
        if rest_result.injury_recoveries:
            self._process_injury_healing(rest_result, context, processing_result)
        
        # 2. Process Fatigue Recovery
        self._process_fatigue_recovery(rest_result, context, processing_result)
        
        # 3. Process Mental and Morale Changes
        self._process_mental_recovery(rest_result, context, processing_result)
        
        # 4. Record Rest History
        self._record_rest_history(rest_result, context, processing_result)
    
    def _process_statistics_only(self, rest_result: RestResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process rest day for statistics collection only"""
        
        processing_result.add_statistic("rest_type", rest_result.rest_type)
        processing_result.add_statistic("injury_recoveries", len(rest_result.injury_recoveries))
        processing_result.add_statistic("team_fatigue_reduction", rest_result.fatigue_recovery.team_fatigue_reduction)
        processing_result.add_statistic("individual_recoveries", len(rest_result.fatigue_recovery.individual_recoveries))
        processing_result.add_statistic("team_morale_change", rest_result.team_morale_change)
        processing_result.add_statistic("stress_reduction", rest_result.stress_reduction)
        
        processing_result.teams_updated = [rest_result.team_id]
    
    def _process_fatigue_recovery(self, rest_result: RestResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process team and individual fatigue recovery"""
        
        fatigue_recovery = rest_result.fatigue_recovery
        
        # Process team-wide fatigue reduction
        if fatigue_recovery.team_fatigue_reduction > 0:
            processing_result.add_state_change("team_fatigue_reduction", fatigue_recovery.team_fatigue_reduction)
            processing_result.add_side_effect(f"Team fatigue reduced by {fatigue_recovery.team_fatigue_reduction:.1f}")
        
        # Process individual player recoveries
        individual_recoveries = 0
        significant_recoveries = 0
        
        for player_name, recovery_amount in fatigue_recovery.individual_recoveries.items():
            player_key = f"player_{player_name}"
            processing_result.add_state_change(f"{player_key}_fatigue_recovery", recovery_amount)
            
            if recovery_amount >= 2.0:
                significant_recoveries += 1
                processing_result.add_side_effect(f"Significant recovery: {player_name} - {recovery_amount:.1f} fatigue reduction")
            
            individual_recoveries += 1
        
        # Track complete recoveries
        if fatigue_recovery.complete_recovery_count > 0:
            processing_result.add_state_change("complete_recoveries", fatigue_recovery.complete_recovery_count)
            processing_result.add_side_effect(f"{fatigue_recovery.complete_recovery_count} players achieved complete recovery")
        
        processing_result.add_statistic("individual_recoveries_processed", individual_recoveries)
        processing_result.add_statistic("significant_recoveries", significant_recoveries)
    
    def _process_injury_healing(self, rest_result: RestResult, context: ProcessingContext,
                              processing_result: ProcessingResult) -> None:
        """Process injury healing progression during rest"""
        
        healing_progressions = 0
        significant_healing = 0
        
        for injury_recovery in rest_result.injury_recoveries:
            player_key = f"player_{injury_recovery.player_name}"
            
            # Update injury recovery progress
            processing_result.add_state_change(f"{player_key}_injury_recovery_progress", injury_recovery.recovery_progress)
            processing_result.add_state_change(f"{player_key}_expected_return_weeks", injury_recovery.expected_return_weeks)
            
            # Track significant recovery progress
            if injury_recovery.recovery_progress >= 0.5:
                significant_healing += 1
                processing_result.add_side_effect(f"Good healing progress: {injury_recovery.player_name} - {injury_recovery.injury_type} at {injury_recovery.recovery_progress*100:.0f}% recovery")
            
            # Handle setbacks if any
            if injury_recovery.setbacks:
                for setback in injury_recovery.setbacks:
                    processing_result.add_side_effect(f"Injury setback: {injury_recovery.player_name} - {setback}")
            
            # Track treatment effectiveness
            processing_result.add_state_change(f"{player_key}_treatment_effectiveness", injury_recovery.treatment_effectiveness)
            
            healing_progressions += 1
        
        processing_result.add_statistic("healing_progressions", healing_progressions)
        processing_result.add_statistic("significant_healing_progress", significant_healing)
    
    def _process_mental_recovery(self, rest_result: RestResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Process mental recovery and morale changes"""
        
        # Process team morale changes
        if rest_result.team_morale_change != 0:
            processing_result.add_state_change("team_morale_change", rest_result.team_morale_change)
            
            if rest_result.team_morale_change > 0:
                processing_result.add_side_effect(f"Team morale improved by {rest_result.team_morale_change:.1f} from rest")
            else:
                processing_result.add_side_effect(f"Team morale declined by {abs(rest_result.team_morale_change):.1f} during rest")
        
        # Process stress reduction
        if rest_result.stress_reduction > 0:
            processing_result.add_state_change("team_stress_reduction", rest_result.stress_reduction)
            processing_result.add_side_effect(f"Team stress reduced by {rest_result.stress_reduction:.1f}")
        
        # Process mental freshness gains
        if rest_result.mental_freshness_gain > 0:
            processing_result.add_state_change("mental_freshness_gain", rest_result.mental_freshness_gain)
            processing_result.add_side_effect(f"Mental freshness improved by {rest_result.mental_freshness_gain:.1f}")
    
    
    
    
    def _record_rest_history(self, rest_result: RestResult, context: ProcessingContext,
                           processing_result: ProcessingResult) -> None:
        """Record rest period in historical records"""
        
        rest_summary = {
            "date": context.current_date.isoformat(),
            "rest_type": rest_result.rest_type,
            "team_id": rest_result.team_id,
            "injury_recoveries": len(rest_result.injury_recoveries),
            "team_fatigue_reduction": rest_result.fatigue_recovery.team_fatigue_reduction,
            "individual_recoveries": len(rest_result.fatigue_recovery.individual_recoveries),
            "morale_change": rest_result.team_morale_change,
            "stress_reduction": rest_result.stress_reduction
        }
        
        processing_result.add_state_change("rest_history_entry", rest_summary)
        
        # Track rest period trends
        processing_result.add_state_change("rest_periods_completed", 1)
        if rest_result.success:
            processing_result.add_state_change("successful_rest_periods", 1)
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """RestProcessor supports recovery-focused strategies"""
        return strategy in [
            ProcessingStrategy.STATISTICS_ONLY,
            ProcessingStrategy.FULL_PROGRESSION,
            ProcessingStrategy.DEVELOPMENT_FOCUS,
            ProcessingStrategy.CUSTOM
        ]