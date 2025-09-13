"""
Scouting Result Processor

Specialized processor for scouting results that handles prospect evaluations,
opponent intelligence, draft board updates, and strategic planning impacts.
"""

from typing import Dict, Any, List, Optional
from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult
from ..results.scouting_result import ScoutingResult
from .base_processor import BaseResultProcessor, ProcessingStrategy


class ScoutingResultProcessor(BaseResultProcessor):
    """
    Processes scouting results with focus on intelligence gathering and prospect evaluation.
    
    Handles:
    - Draft board updates and prospect rankings
    - Opponent intelligence and game planning
    - Scouting network expansion
    - Strategic advantage identification
    - Personnel evaluation insights
    """
    
    def can_process(self, result: AnySimulationResult) -> bool:
        """Check if this is a ScoutingResult"""
        return isinstance(result, ScoutingResult)
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process scouting result with intelligence and evaluation updates"""
        if not isinstance(result, ScoutingResult):
            return ProcessingResult(
                processed_successfully=False,
                processing_type="ScoutingResultProcessor",
                error_messages=["Expected ScoutingResult but received different type"]
            )
        
        scouting_result: ScoutingResult = result
        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="ScoutingResultProcessor"
        )
        
        # Process based on strategy
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(scouting_result, context, processing_result)
        elif self.config.strategy == ProcessingStrategy.INTELLIGENCE_GATHERING:
            self._process_intelligence_focus(scouting_result, context, processing_result)
        else:
            self._process_full_scouting_impact(scouting_result, context, processing_result)
        
        return processing_result
    
    def _process_full_scouting_impact(self, scouting_result: ScoutingResult, context: ProcessingContext,
                                    processing_result: ProcessingResult) -> None:
        """Process scouting with full intelligence and evaluation impact"""
        
        # 1. Update Draft Board
        if scouting_result.requires_draft_board_update():
            self._update_draft_board(scouting_result, context, processing_result)
        
        # 2. Process Opponent Intelligence  
        if scouting_result.requires_game_plan_update():
            self._process_opponent_intelligence(scouting_result, context, processing_result)
        
        # 3. Update Strategic Planning
        self._update_strategic_advantages(scouting_result, context, processing_result)
        
        # 4. Update Scouting Department Performance
        self._update_scouting_metrics(scouting_result, context, processing_result)
        
        # 5. Record Scouting History
        self._record_scouting_history(scouting_result, context, processing_result)
    
    def _process_statistics_only(self, scouting_result: ScoutingResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process scouting for statistics only"""
        
        processing_result.add_statistic("scouting_type", scouting_result.scouting_type)
        processing_result.add_statistic("prospects_evaluated", len(scouting_result.prospect_evaluations))
        processing_result.add_statistic("high_value_prospects", len(scouting_result.get_high_value_prospects()))
        processing_result.add_statistic("intelligence_pieces", len(scouting_result.opponent_intelligence))
        processing_result.add_statistic("actionable_insights", scouting_result.get_actionable_insights_count())
        
        processing_result.teams_updated = [scouting_result.team_id]
    
    def _process_intelligence_focus(self, scouting_result: ScoutingResult, context: ProcessingContext,
                                  processing_result: ProcessingResult) -> None:
        """Process with focus on intelligence gathering"""
        
        self._process_opponent_intelligence(scouting_result, context, processing_result)
        self._update_strategic_advantages(scouting_result, context, processing_result)
        
        # Enhanced intelligence analysis
        high_quality_intel = len(scouting_result.get_high_quality_intelligence())
        processing_result.add_statistic("high_quality_intelligence", high_quality_intel)
        
        if high_quality_intel >= 3:
            processing_result.add_side_effect("Exceptional intelligence gathering - significant strategic advantages gained")
    
    def _update_draft_board(self, scouting_result: ScoutingResult, context: ProcessingContext,
                          processing_result: ProcessingResult) -> None:
        """Update team's draft board based on prospect evaluations"""
        
        prospects_added = 0
        high_value_additions = 0
        
        for prospect in scouting_result.prospect_evaluations:
            prospect_key = f"prospect_{prospect.prospect_name.replace(' ', '_')}"
            
            # Add prospect to draft board
            processing_result.add_state_change(f"{prospect_key}_overall_rating", prospect.overall_rating)
            processing_result.add_state_change(f"{prospect_key}_potential_rating", prospect.potential_rating)
            processing_result.add_state_change(f"{prospect_key}_projected_round", prospect.projected_draft_round)
            processing_result.add_state_change(f"{prospect_key}_position", prospect.position)
            processing_result.add_state_change(f"{prospect_key}_school", prospect.school_or_team)
            
            # High-confidence evaluations get priority
            if prospect.is_high_confidence_evaluation():
                processing_result.add_state_change(f"{prospect_key}_evaluation_confidence", prospect.evaluation_confidence)
                processing_result.add_side_effect(f"High-confidence evaluation: {prospect.prospect_name} ({prospect.get_overall_grade()})")
            
            # Track red flag prospects
            if prospect.has_red_flags():
                processing_result.add_state_change(f"{prospect_key}_red_flags", prospect.character_concerns + prospect.injury_history)
                processing_result.add_side_effect(f"Red flags identified: {prospect.prospect_name}")
            
            # High-value prospects get special attention
            if prospect.overall_rating >= 80:
                high_value_additions += 1
                processing_result.add_side_effect(f"High-value prospect identified: {prospect.prospect_name} ({prospect.position}) - {prospect.get_overall_grade()}")
            
            prospects_added += 1
        
        # Update draft board changes
        for change in scouting_result.prospect_rankings_changes:
            processing_result.add_state_change("draft_board_ranking_change", change)
        
        processing_result.add_statistic("prospects_added_to_board", prospects_added)
        processing_result.add_statistic("high_value_prospects_found", high_value_additions)
        
        if prospects_added > 0:
            processing_result.add_side_effect(f"Draft board updated with {prospects_added} new prospects ({high_value_additions} high-value)")
    
    def _process_opponent_intelligence(self, scouting_result: ScoutingResult, context: ProcessingContext,
                                     processing_result: ProcessingResult) -> None:
        """Process opponent intelligence for game planning"""
        
        intelligence_pieces = 0
        high_quality_intel = 0
        
        for intel in scouting_result.opponent_intelligence:
            opponent_key = f"opponent_{intel.opponent_team_id}"
            
            # Store offensive intelligence
            if intel.offensive_tendencies:
                for situation, tendency in intel.offensive_tendencies.items():
                    processing_result.add_state_change(f"{opponent_key}_offense_{situation}", tendency)
            
            # Store defensive intelligence
            if intel.defensive_schemes:
                processing_result.add_state_change(f"{opponent_key}_defensive_schemes", intel.defensive_schemes)
            
            if intel.defensive_personnel_packages:
                for package, usage in intel.defensive_personnel_packages.items():
                    processing_result.add_state_change(f"{opponent_key}_defense_{package}_usage", usage)
            
            # Coaching patterns
            if intel.coaching_tendencies:
                for situation, tendency in intel.coaching_tendencies.items():
                    processing_result.add_state_change(f"{opponent_key}_coaching_{situation}", tendency)
            
            # Recent form and injury intel
            if intel.recent_form != "unknown":
                processing_result.add_state_change(f"{opponent_key}_recent_form", intel.recent_form)
            
            if intel.injury_report_intel:
                processing_result.add_state_change(f"{opponent_key}_injury_intel", intel.injury_report_intel)
            
            # Quality assessment
            if intel.is_high_quality_intel():
                high_quality_intel += 1
                processing_result.add_side_effect(f"High-quality intelligence on Team {intel.opponent_team_id} - {intel.intelligence_type}")
            
            # Exploitable weaknesses
            weaknesses = intel.get_exploitable_weaknesses()
            if weaknesses:
                processing_result.add_state_change(f"{opponent_key}_exploitable_weaknesses", weaknesses)
                processing_result.add_side_effect(f"Exploitable weaknesses identified: Team {intel.opponent_team_id}")
            
            intelligence_pieces += 1
        
        processing_result.add_statistic("opponent_intel_pieces", intelligence_pieces)
        processing_result.add_statistic("high_quality_intel_pieces", high_quality_intel)
    
    def _update_strategic_advantages(self, scouting_result: ScoutingResult, context: ProcessingContext,
                                   processing_result: ProcessingResult) -> None:
        """Update strategic advantages and game planning recommendations"""
        
        # Process game plan recommendations
        for recommendation in scouting_result.game_plan_recommendations:
            processing_result.add_state_change("game_plan_recommendation", recommendation)
            processing_result.add_side_effect(f"Game plan recommendation: {recommendation}")
        
        # Process strategic advantages
        for advantage in scouting_result.strategic_advantages_identified:
            processing_result.add_state_change("strategic_advantage", advantage)
        
        # Process competitive advantages
        for advantage in scouting_result.competitive_advantages_gained:
            processing_result.add_state_change("competitive_advantage", advantage)
            processing_result.add_side_effect(f"Competitive advantage gained: {advantage}")
        
        # Position needs identification
        for position_need in scouting_result.position_needs_identified:
            processing_result.add_state_change("position_need_identified", position_need)
        
        # Player comparisons
        for prospect, comparison in scouting_result.comparable_player_analysis.items():
            processing_result.add_state_change(f"prospect_comparison_{prospect}", comparison)
    
    def _update_scouting_metrics(self, scouting_result: ScoutingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Update scouting department performance metrics"""
        
        metrics = scouting_result.scouting_metrics
        
        # Efficiency metrics
        efficiency = metrics.get_efficiency_score()
        processing_result.add_state_change("scouting_efficiency", efficiency)
        
        if efficiency >= 0.8:
            processing_result.add_side_effect("Highly efficient scouting operation")
        elif efficiency <= 0.3:
            processing_result.add_side_effect("Scouting efficiency concerns - review needed")
        
        # Resource utilization
        processing_result.add_state_change("scouting_budget_spent", metrics.budget_spent)
        processing_result.add_state_change("scouting_time_invested", metrics.time_invested_hours)
        
        # Coverage metrics
        processing_result.add_state_change("scouting_games_attended", metrics.games_attended)
        processing_result.add_state_change("scouting_tape_reviewed", metrics.tape_reviewed_hours)
        
        if metrics.was_comprehensive_scouting():
            processing_result.add_side_effect("Comprehensive scouting coverage achieved")
        
        # Scout performance ratings
        for scout, rating in scouting_result.scout_performance_ratings.items():
            processing_result.add_state_change(f"scout_{scout}_performance", rating)
        
        # Network expansion
        for expansion in scouting_result.scouting_network_expansions:
            processing_result.add_state_change("scouting_network_expansion", expansion)
            processing_result.add_side_effect(f"Scouting network expanded: {expansion}")
    
    def _record_scouting_history(self, scouting_result: ScoutingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Record scouting operation in historical records"""
        
        scouting_summary = {
            "date": context.current_date.isoformat(),
            "scouting_type": scouting_result.scouting_type,
            "team_id": scouting_result.team_id,
            "target": scouting_result.target_description,
            "prospects_found": len(scouting_result.prospect_evaluations),
            "intelligence_gathered": len(scouting_result.opponent_intelligence),
            "success": scouting_result.was_successful_scouting(),
            "efficiency": scouting_result.scouting_metrics.get_efficiency_score()
        }
        
        processing_result.add_state_change("scouting_history_entry", scouting_summary)
        
        # Track scouting trends
        processing_result.add_state_change("scouting_operations_completed", 1)
        if scouting_result.was_successful_scouting():
            processing_result.add_state_change("successful_scouting_operations", 1)
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """ScoutingProcessor supports intelligence-focused strategies"""
        return strategy in [
            ProcessingStrategy.STATISTICS_ONLY,
            ProcessingStrategy.FULL_PROGRESSION,
            ProcessingStrategy.INTELLIGENCE_GATHERING,
            ProcessingStrategy.CUSTOM
        ]