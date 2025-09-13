"""
Training Result Processor

Specialized processor for training/practice results that handles player skill development,
team chemistry changes, injury processing, and coaching effectiveness tracking.
"""

from typing import Dict, Any, List, Optional
from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult
from ..results.training_result import TrainingResult
from .base_processor import BaseResultProcessor, ProcessingStrategy


class TrainingResultProcessor(BaseResultProcessor):
    """
    Processes training/practice results with focus on player development and team building.
    
    Handles:
    - Player skill progression and development
    - Team chemistry and cohesion changes  
    - Training-related injury processing
    - Coaching effectiveness and rapport
    - Playbook mastery improvements
    - Fatigue and conditioning impacts
    """
    
    def can_process(self, result: AnySimulationResult) -> bool:
        """Check if this is a TrainingResult"""
        return isinstance(result, TrainingResult)
    
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """Process training result with comprehensive player/team development"""
        if not isinstance(result, TrainingResult):
            return ProcessingResult(
                processed_successfully=False,
                processing_type="TrainingResultProcessor",
                error_messages=["Expected TrainingResult but received different type"]
            )
        
        training_result: TrainingResult = result
        processing_result = ProcessingResult(
            processed_successfully=True,
            processing_type="TrainingResultProcessor"
        )
        
        # Process based on configured strategy
        if self.config.strategy == ProcessingStrategy.STATISTICS_ONLY:
            self._process_statistics_only(training_result, context, processing_result)
        elif self.config.strategy == ProcessingStrategy.DEVELOPMENT_FOCUS:
            self._process_development_focus(training_result, context, processing_result)
        else:
            self._process_full_training_impact(training_result, context, processing_result)
        
        return processing_result
    
    def _process_full_training_impact(self, training_result: TrainingResult, context: ProcessingContext,
                                    processing_result: ProcessingResult) -> None:
        """Process training with full season progression impact"""
        
        # 1. Update Player Skills and Development
        if self.config.process_development and training_result.requires_skill_updates():
            self._update_player_skills(training_result, context, processing_result)
        
        # 2. Process Team Chemistry Changes
        if self.config.update_chemistry and training_result.requires_chemistry_updates():
            self._update_team_chemistry(training_result, context, processing_result)
        
        # 3. Process Training Injuries
        if self.config.process_injuries and training_result.requires_injury_processing():
            self._process_training_injuries(training_result, context, processing_result)
        
        # 4. Update Coaching Effectiveness
        self._update_coaching_metrics(training_result, context, processing_result)
        
        # 5. Process Playbook Mastery
        self._update_playbook_mastery(training_result, context, processing_result)
        
        # 6. Handle Fatigue and Conditioning
        self._process_fatigue_impacts(training_result, context, processing_result)
        
        # 7. Record Training History and Trends
        self._record_training_history(training_result, context, processing_result)
    
    def _process_statistics_only(self, training_result: TrainingResult, context: ProcessingContext,
                                processing_result: ProcessingResult) -> None:
        """Process training for statistics collection only"""
        
        # Basic training statistics
        processing_result.add_statistic("training_type", training_result.training_type)
        processing_result.add_statistic("players_developed", training_result.get_total_player_developments())
        processing_result.add_statistic("training_injuries", training_result.get_injury_count())
        processing_result.add_statistic("serious_injuries", training_result.get_serious_injury_count())
        
        # Training effectiveness metrics
        if training_result.training_metrics:
            processing_result.add_statistic("drill_success_rate", training_result.training_metrics.get_drill_success_rate())
            processing_result.add_statistic("average_effort", training_result.training_metrics.average_effort_level)
            processing_result.add_statistic("breakthrough_moments", training_result.training_metrics.breakthrough_moments)
        
        # Chemistry impact summary
        chemistry_change = training_result.team_chemistry_changes.get_net_chemistry_change()
        processing_result.add_statistic("net_chemistry_change", chemistry_change)
        
        processing_result.teams_updated = [training_result.team_id]
    
    def _process_development_focus(self, training_result: TrainingResult, context: ProcessingContext,
                                 processing_result: ProcessingResult) -> None:
        """Process training with emphasis on player and team development"""
        
        # Focus heavily on development aspects
        self._update_player_skills(training_result, context, processing_result)
        self._update_team_chemistry(training_result, context, processing_result)
        self._update_playbook_mastery(training_result, context, processing_result)
        
        # Track development trends over time
        self._analyze_development_trends(training_result, context, processing_result)
        
        # Less emphasis on injuries and fatigue in development-focused mode
        if training_result.get_serious_injury_count() > 0:
            processing_result.add_side_effect(f"Development impacted by {training_result.get_serious_injury_count()} serious injuries")
    
    def _update_player_skills(self, training_result: TrainingResult, context: ProcessingContext,
                            processing_result: ProcessingResult) -> None:
        """Update individual player skill ratings and development"""
        
        players_developed = 0
        significant_developments = 0
        
        for development in training_result.player_developments:
            player_key = f"player_{development.player_name}"
            
            # Apply skill changes
            if development.overall_rating_change != 0:
                processing_result.add_state_change(f"{player_key}_overall_rating", development.overall_rating_change)
            
            if development.potential_change != 0:
                processing_result.add_state_change(f"{player_key}_potential", development.potential_change)
            
            # Position-specific skill updates
            position_skills = {
                "speed": development.speed_change,
                "strength": development.strength_change,
                "agility": development.agility_change,
                "awareness": development.awareness_change,
                "throwing_accuracy": development.throwing_accuracy_change,
                "catching": development.catching_change,
                "tackling": development.tackling_change
            }
            
            for skill, change in position_skills.items():
                if change != 0:
                    processing_result.add_state_change(f"{player_key}_{skill}", change)
            
            # Track development trait improvements
            if development.development_trait_improvement:
                processing_result.add_state_change(f"{player_key}_development_trait", "improved")
                processing_result.add_side_effect(f"Development breakthrough: {development.player_name} improved development trait")
            
            # Performance-based updates
            effort_bonus = max(0, development.effort_level - 1.0) * 0.5  # Bonus for high effort
            processing_result.add_state_change(f"{player_key}_effort_rating", development.effort_level)
            
            if development.practice_performance == "excellent":
                processing_result.add_state_change(f"{player_key}_confidence", 2.0)
                processing_result.add_side_effect(f"Excellent practice: {development.player_name} gained confidence")
            elif development.practice_performance == "poor":
                processing_result.add_state_change(f"{player_key}_confidence", -1.0)
            
            players_developed += 1
            if development.has_significant_development():
                significant_developments += 1
        
        processing_result.add_statistic("players_skill_updated", players_developed)
        processing_result.add_statistic("significant_skill_developments", significant_developments)
        
        if significant_developments > 0:
            processing_result.add_side_effect(f"Training produced {significant_developments} significant player developments")
    
    def _update_team_chemistry(self, training_result: TrainingResult, context: ProcessingContext,
                             processing_result: ProcessingResult) -> None:
        """Update team chemistry and cohesion metrics"""
        
        chemistry = training_result.team_chemistry_changes
        
        # Update overall team chemistry
        if chemistry.overall_chemistry_change != 0:
            processing_result.add_state_change("team_overall_chemistry", chemistry.overall_chemistry_change)
        
        # Update unit-specific chemistry
        unit_changes = {
            "offensive_line": chemistry.offensive_line_chemistry,
            "receiving_corps": chemistry.receiving_corps_chemistry,
            "defensive_secondary": chemistry.defensive_secondary_chemistry,
            "linebacker_corps": chemistry.linebacker_corps_chemistry,
            "special_teams": chemistry.special_teams_chemistry
        }
        
        significant_changes = 0
        for unit, change in unit_changes.items():
            if abs(change) >= 1.0:
                processing_result.add_state_change(f"team_{unit}_chemistry", change)
                significant_changes += 1
                
                if change >= 2.0:
                    processing_result.add_side_effect(f"Strong chemistry improvement in {unit}: +{change:.1f}")
                elif change <= -2.0:
                    processing_result.add_side_effect(f"Chemistry concerns in {unit}: {change:.1f}")
        
        # Leadership and culture impacts
        if chemistry.veteran_leadership_influence != 0:
            processing_result.add_state_change("team_veteran_leadership", chemistry.veteran_leadership_influence)
        
        if chemistry.rookie_integration_success != 0:
            processing_result.add_state_change("team_rookie_integration", chemistry.rookie_integration_success)
        
        if chemistry.coaching_rapport_change != 0:
            processing_result.add_state_change("team_coaching_rapport", chemistry.coaching_rapport_change)
        
        # Process chemistry events
        for event in chemistry.chemistry_events:
            processing_result.add_side_effect(f"Chemistry event: {event}")
        
        # Overall chemistry assessment
        net_change = chemistry.get_net_chemistry_change()
        if net_change >= 2.0:
            processing_result.add_side_effect("Training significantly improved team chemistry")
        elif net_change <= -2.0:
            processing_result.add_side_effect("Training revealed team chemistry issues")
        
        processing_result.add_statistic("unit_chemistry_changes", significant_changes)
        processing_result.add_statistic("net_chemistry_change", net_change)
    
    def _process_training_injuries(self, training_result: TrainingResult, context: ProcessingContext,
                                 processing_result: ProcessingResult) -> None:
        """Process injuries that occurred during training"""
        
        injuries_processed = 0
        serious_injuries = 0
        
        for injury in training_result.training_injuries:
            player_key = f"player_{injury.player_name}"
            
            # Update player injury status
            processing_result.add_state_change(f"{player_key}_injury_type", injury.injury_type)
            processing_result.add_state_change(f"{player_key}_injury_severity", injury.severity)
            processing_result.add_state_change(f"{player_key}_weeks_out", injury.weeks_out)
            processing_result.add_state_change(f"{player_key}_injury_context", f"Training - {injury.occurred_during}")
            
            # Track injury trends
            processing_result.add_state_change(f"team_training_injury_count", 1)
            
            # Categorize injury impact
            if injury.is_serious_injury():
                serious_injuries += 1
                processing_result.add_side_effect(f"Serious training injury: {injury.player_name} - {injury.injury_type} ({injury.severity}) - {injury.weeks_out} weeks")
                
                # Serious injuries might affect team confidence
                processing_result.add_state_change("team_injury_concern", 1.0)
            else:
                processing_result.add_side_effect(f"Minor training injury: {injury.player_name} - {injury.injury_type}")
            
            injuries_processed += 1
        
        # Update training safety metrics
        if injuries_processed > 0:
            injury_rate = injuries_processed / len(training_result.player_developments) if training_result.player_developments else 0
            processing_result.add_state_change("training_injury_rate", injury_rate)
            
            if injury_rate > 0.1:  # More than 10% injury rate
                processing_result.add_side_effect("High training injury rate - consider training intensity review")
        
        processing_result.add_statistic("training_injuries_processed", injuries_processed)
        processing_result.add_statistic("serious_training_injuries", serious_injuries)
    
    def _update_coaching_metrics(self, training_result: TrainingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Update coaching effectiveness and rapport metrics"""
        
        # Training effectiveness metrics
        if training_result.training_metrics.was_highly_effective():
            processing_result.add_state_change("coaching_effectiveness", 1.0)
            processing_result.add_side_effect("Highly effective training session - coaching staff performing well")
        elif training_result.training_metrics.get_drill_success_rate() < 60:
            processing_result.add_state_change("coaching_effectiveness", -0.5)
            processing_result.add_side_effect("Training effectiveness concerns - low drill success rate")
        
        # Coaching rapport changes
        for coach_type, rapport_change in training_result.coaching_rapport_changes.items():
            processing_result.add_state_change(f"coaching_rapport_{coach_type}", rapport_change)
            
            if abs(rapport_change) >= 2.0:
                direction = "improved" if rapport_change > 0 else "declined"
                processing_result.add_side_effect(f"Player-coach rapport {direction}: {coach_type} ({rapport_change:+.1f})")
        
        # Training innovation and adaptation
        processing_result.add_state_change("coaching_training_sessions_run", 1)
        if training_result.training_metrics.breakthrough_moments > 0:
            processing_result.add_state_change("coaching_breakthrough_sessions", 1)
    
    def _update_playbook_mastery(self, training_result: TrainingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Update team's mastery of playbook systems"""
        
        mastery_improvements = 0
        
        for system, improvement in training_result.playbook_mastery_improvements.items():
            if improvement > 0:
                processing_result.add_state_change(f"playbook_mastery_{system}", improvement)
                mastery_improvements += 1
                
                if improvement >= 2.0:
                    processing_result.add_side_effect(f"Significant playbook improvement: {system} (+{improvement:.1f})")
        
        # Overall playbook progress
        if mastery_improvements > 0:
            processing_result.add_state_change("team_playbook_sessions", 1)
            processing_result.add_statistic("playbook_systems_improved", mastery_improvements)
    
    def _process_fatigue_impacts(self, training_result: TrainingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Process fatigue and conditioning impacts from training"""
        
        # Team-wide fatigue impact
        if training_result.team_fatigue_change != 0:
            processing_result.add_state_change("team_fatigue_level", training_result.team_fatigue_change)
            
            if training_result.team_fatigue_change > 2.0:
                processing_result.add_side_effect("High-intensity training increased team fatigue")
            elif training_result.team_fatigue_change < -2.0:
                processing_result.add_side_effect("Recovery-focused training reduced team fatigue")
        
        # Individual fatigue changes
        significant_fatigue_changes = 0
        for player_name, fatigue_change in training_result.individual_fatigue_changes.items():
            if abs(fatigue_change) >= 1.0:
                processing_result.add_state_change(f"player_{player_name}_fatigue", fatigue_change)
                significant_fatigue_changes += 1
        
        processing_result.add_statistic("players_fatigue_affected", significant_fatigue_changes)
    
    def _record_training_history(self, training_result: TrainingResult, context: ProcessingContext,
                               processing_result: ProcessingResult) -> None:
        """Record training session in historical records"""
        
        training_summary = {
            "date": context.current_date.isoformat(),
            "training_type": training_result.training_type,
            "team_id": training_result.team_id,
            "players_developed": training_result.get_total_player_developments(),
            "injuries": training_result.get_injury_count(),
            "success": training_result.had_successful_training(),
            "chemistry_change": training_result.team_chemistry_changes.get_net_chemistry_change()
        }
        
        processing_result.add_state_change("training_history_entry", training_summary)
        
        # Record notable events
        for highlight in training_result.practice_highlights:
            processing_result.add_side_effect(f"Practice highlight: {highlight}")
        
        for breakthrough in training_result.breakthrough_performances:
            processing_result.add_side_effect(f"Breakthrough performance: {breakthrough}")
        
        for incident in training_result.discipline_incidents:
            processing_result.add_side_effect(f"Discipline incident: {incident}")
    
    def _analyze_development_trends(self, training_result: TrainingResult, context: ProcessingContext,
                                  processing_result: ProcessingResult) -> None:
        """Analyze development trends over time (development-focused strategy)"""
        
        # This would typically look at historical data to identify trends
        total_development = sum(dev.get_total_development_points() for dev in training_result.player_developments)
        avg_development = total_development / max(1, len(training_result.player_developments))
        
        processing_result.add_statistic("average_development_per_player", avg_development)
        
        if avg_development >= 2.0:
            processing_result.add_side_effect("Exceptional development session - players making rapid progress")
        elif avg_development <= 0.5:
            processing_result.add_side_effect("Limited development this session - may need training adjustments")
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """TrainingProcessor supports development-focused strategies"""
        return strategy in [
            ProcessingStrategy.STATISTICS_ONLY,
            ProcessingStrategy.FULL_PROGRESSION,
            ProcessingStrategy.DEVELOPMENT_FOCUS,
            ProcessingStrategy.CUSTOM
        ]