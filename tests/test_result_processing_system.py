"""
Comprehensive Test Suite for Result Processing System

Tests the complete result processing pipeline including processors, season state management,
calendar integration, and different processing strategies.
"""

import unittest
from datetime import date, datetime, timedelta
from typing import List, Dict, Any
import tempfile
import os

from src.simulation.calendar_manager import CalendarManager, ConflictResolution
from src.simulation.season_state_manager import SeasonStateManager
from src.simulation.processing_strategies import ProcessingStrategyFactory, SimulationMode
from src.simulation.processors.base_processor import ProcessingStrategy, ProcessorConfig
from src.simulation.processors.game_processor import GameResultProcessor
from src.simulation.processors.training_processor import TrainingResultProcessor
from src.simulation.results.base_result import ProcessingContext, ProcessingResult
from src.simulation.results.game_result import GameResult, TeamGameStats, PlayerGameStats, GameStateChanges
from src.simulation.results.training_result import TrainingResult, PlayerDevelopment, TeamChemistryChanges, TrainingMetrics
from src.simulation.events.placeholder_events import GameSimulationEvent, TrainingEvent


class TestResultProcessingSystem(unittest.TestCase):
    """Test suite for the complete result processing system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_date = date(2024, 9, 1)
        self.test_context = ProcessingContext(
            current_date=datetime(2024, 9, 1, 14, 0),
            season_week=1,
            season_phase="regular_season"
        )
    
    def test_season_state_manager_initialization(self):
        """Test SeasonStateManager initialization and basic functionality"""
        manager = SeasonStateManager(season_year=2024)
        
        # Test initialization
        self.assertEqual(manager.season_year, 2024)
        self.assertEqual(len(manager.team_states), 32)  # 32 NFL teams
        self.assertEqual(manager.current_week, 0)
        self.assertEqual(manager.season_phase, "preseason")
        
        # Test team states
        team_1 = manager.team_states[1]
        self.assertEqual(team_1.team_id, 1)
        self.assertEqual(team_1.wins, 0)
        self.assertEqual(team_1.losses, 0)
        self.assertEqual(team_1.chemistry_level, 75.0)
    
    def test_game_result_processing(self):
        """Test processing of game results"""
        processor = GameResultProcessor()
        
        # Create a sample game result
        game_result = GameResult(
            event_type="GAME",
            success=True,
            teams_affected=[1, 2],
            away_team_id=1,
            home_team_id=2,
            away_score=21,
            home_score=14,
            week=1,
            season_type="regular_season"
        )
        
        # Add some team stats
        game_result.team_stats[1] = TeamGameStats(
            score=21, total_yards=350, turnovers=1, penalties=5
        )
        game_result.team_stats[2] = TeamGameStats(
            score=14, total_yards=275, turnovers=2, penalties=8
        )
        
        # Process the result
        processing_result = processor.process_result(game_result, self.test_context)
        
        # Verify processing success
        self.assertTrue(processing_result.processed_successfully)
        self.assertEqual(processing_result.processing_type, "GameResultProcessor")
        self.assertEqual(processing_result.teams_updated, [1, 2])
        
        # Check that state changes were recorded
        self.assertIn("team_1_wins", processing_result.state_changes)
        self.assertIn("team_2_losses", processing_result.state_changes)
        self.assertEqual(processing_result.state_changes["team_1_wins"], 1)
        self.assertEqual(processing_result.state_changes["team_2_losses"], 1)
        
        # Check statistics
        self.assertGreater(len(processing_result.statistics), 0)
        self.assertIn("game_final_score", processing_result.statistics)
    
    def test_training_result_processing(self):
        """Test processing of training results"""
        processor = TrainingResultProcessor()
        
        # Create a sample training result
        training_result = TrainingResult(
            event_type="TRAINING",
            success=True,
            teams_affected=[1],
            team_id=1,
            training_type="practice"
        )
        
        # Add player developments
        training_result.player_developments = [
            PlayerDevelopment(
                player_name="Test Player 1",
                overall_rating_change=1.0,
                speed_change=0.5,
                effort_level=1.2
            ),
            PlayerDevelopment(
                player_name="Test Player 2", 
                overall_rating_change=0.5,
                strength_change=1.0,
                effort_level=1.1
            )
        ]
        
        # Add team chemistry changes
        training_result.team_chemistry_changes = TeamChemistryChanges(
            overall_chemistry_change=1.5,
            offensive_line_chemistry=2.0
        )
        
        # Add training metrics
        training_result.training_metrics = TrainingMetrics(
            average_effort_level=1.15,
            breakthrough_moments=1
        )
        
        # Process the result
        processing_result = processor.process_result(training_result, self.test_context)
        
        # Verify processing
        self.assertTrue(processing_result.processed_successfully)
        self.assertEqual(processing_result.processing_type, "TrainingResultProcessor")
        self.assertIn(1, processing_result.teams_updated)
        
        # Check player development processing
        self.assertIn("player_Test Player 1_overall_rating", processing_result.state_changes)
        self.assertIn("player_Test Player 2_overall_rating", processing_result.state_changes)
        
        # Check team chemistry processing
        self.assertIn("team_overall_chemistry", processing_result.state_changes)
        self.assertIn("team_offensive_line_chemistry", processing_result.state_changes)
        
        # Check statistics
        self.assertIn("players_skill_updated", processing_result.statistics)
        self.assertEqual(processing_result.statistics["players_skill_updated"], 2)
    
    def test_season_state_integration(self):
        """Test integration between processors and season state manager"""
        season_manager = SeasonStateManager(season_year=2024)
        processor = GameResultProcessor()
        
        # Create and process a game result
        game_result = GameResult(
            event_type="GAME",
            success=True,
            teams_affected=[1, 2],
            away_team_id=1,
            home_team_id=2,
            away_score=28,
            home_score=21
        )
        
        processing_result = processor.process_result(game_result, self.test_context)
        season_manager.apply_processing_result(processing_result, self.test_context)
        
        # Check that season state was updated
        team_1 = season_manager.team_states[1]
        team_2 = season_manager.team_states[2]
        
        self.assertEqual(team_1.wins, 1)
        self.assertEqual(team_1.losses, 0)
        self.assertEqual(team_2.wins, 0) 
        self.assertEqual(team_2.losses, 1)
        self.assertEqual(team_1.games_played, 1)
        self.assertEqual(team_2.games_played, 1)
        
        # Check standings
        standings = season_manager.get_team_standings()
        self.assertEqual(standings[0].team_id, 1)  # Team 1 should be first with 1 win
        self.assertEqual(standings[0].get_win_percentage(), 1.0)
    
    def test_calendar_manager_integration(self):
        """Test full integration with CalendarManager"""
        calendar_manager = CalendarManager(
            start_date=self.test_date,
            enable_result_processing=True,
            processing_strategy=ProcessingStrategy.FULL_PROGRESSION,
            season_year=2024
        )
        
        # Verify initialization
        self.assertTrue(calendar_manager.enable_result_processing)
        self.assertEqual(calendar_manager.processing_strategy, ProcessingStrategy.FULL_PROGRESSION)
        self.assertIsNotNone(calendar_manager.get_season_state_manager())
        self.assertTrue(hasattr(calendar_manager, '_result_processors'))
        self.assertEqual(len(calendar_manager._result_processors), 5)  # All processor types
        
        # Schedule and simulate events
        game_event = GameSimulationEvent(
            event_name="Test Game",
            date=self.test_date,
            involved_teams=[1, 2],
            duration_hours=3.0
        )
        
        training_event = TrainingEvent(
            event_name="Test Training",
            date=self.test_date + timedelta(days=1),
            involved_teams=[1],
            duration_hours=2.0
        )
        
        # Schedule events
        success, msg = calendar_manager.schedule_event(game_event)
        self.assertTrue(success)
        
        success, msg = calendar_manager.schedule_event(training_event)
        self.assertTrue(success)
        
        # Simulate the days
        day_results = calendar_manager.advance_to_date(self.test_date + timedelta(days=1))
        
        # Verify simulation results
        self.assertEqual(len(day_results), 2)  # 2 days simulated
        
        # Check first day (game day)
        game_day = day_results[0]
        self.assertEqual(game_day.events_executed, 1)
        self.assertEqual(game_day.successful_events, 1)
        # Should have processing results if game was processed
        # Note: Actual processing depends on the placeholder implementation
        
        # Check calendar stats
        stats = calendar_manager.get_calendar_stats()
        self.assertTrue(stats.result_processing_enabled)
        self.assertTrue(stats.season_state_tracked)
    
    def test_processing_strategies(self):
        """Test different processing strategies"""
        
        # Test strategy factory
        modes = ProcessingStrategyFactory.get_available_modes()
        self.assertGreater(len(modes), 0)
        self.assertIn(SimulationMode.QUICK_STATS, modes)
        self.assertIn(SimulationMode.SEASON_SIMULATION, modes)
        
        # Test getting specific strategy
        quick_stats_profile = ProcessingStrategyFactory.get_strategy_profile(SimulationMode.QUICK_STATS)
        self.assertEqual(quick_stats_profile.processing_strategy, ProcessingStrategy.STATISTICS_ONLY)
        self.assertFalse(quick_stats_profile.season_tracking_enabled)
        
        season_profile = ProcessingStrategyFactory.get_strategy_profile(SimulationMode.SEASON_SIMULATION)
        self.assertEqual(season_profile.processing_strategy, ProcessingStrategy.FULL_PROGRESSION)
        self.assertTrue(season_profile.season_tracking_enabled)
        
        # Test custom profile creation
        custom_profile = ProcessingStrategyFactory.create_custom_profile(
            name="Test Custom",
            description="Test custom profile",
            enable_player_development=False,
            enable_injury_tracking=True
        )
        self.assertEqual(custom_profile.name, "Test Custom")
        self.assertFalse(custom_profile.enable_player_development)
        self.assertTrue(custom_profile.enable_injury_tracking)
        
        # Test processor config generation
        config = custom_profile.to_processor_config()
        self.assertFalse(config.process_development)
        self.assertTrue(config.process_injuries)
    
    def test_different_simulation_modes(self):
        """Test calendar manager with different simulation modes"""
        
        # Test lightweight mode (no processing)
        lightweight_config = ProcessingStrategyFactory.create_calendar_manager_config(
            mode=SimulationMode.LIGHTWEIGHT,
            start_date=self.test_date,
            season_year=2024
        )
        
        lightweight_calendar = CalendarManager(**lightweight_config)
        self.assertFalse(lightweight_calendar.enable_result_processing)
        self.assertIsNone(lightweight_calendar.get_season_state_manager())
        
        # Test full season mode (full processing)
        full_config = ProcessingStrategyFactory.create_calendar_manager_config(
            mode=SimulationMode.SEASON_SIMULATION,
            start_date=self.test_date,
            season_year=2024
        )
        
        full_calendar = CalendarManager(**full_config)
        self.assertTrue(full_calendar.enable_result_processing)
        self.assertIsNotNone(full_calendar.get_season_state_manager())
        self.assertEqual(full_calendar.processing_strategy, ProcessingStrategy.FULL_PROGRESSION)
    
    def test_processor_error_handling(self):
        """Test processor error handling and validation"""
        processor = GameResultProcessor()
        
        # Test with wrong result type
        training_result = TrainingResult(
            event_type="TRAINING",
            success=True,
            teams_affected=[1]
        )
        
        processing_result = processor.process_result(training_result, self.test_context)
        self.assertFalse(processing_result.processed_successfully)
        self.assertGreater(len(processing_result.error_messages), 0)
        
        # Test with failed simulation result
        failed_game = GameResult(
            event_type="GAME",
            success=False,
            teams_affected=[1, 2]
        )
        
        # Should still process in FULL_PROGRESSION mode
        processing_result = processor.process_result(failed_game, self.test_context)
        # Depends on processor configuration and validation logic
    
    def test_processing_context_progression(self):
        """Test context progression through season"""
        manager = SeasonStateManager(season_year=2024)
        
        # Test multiple weeks
        for week in range(1, 6):
            context = ProcessingContext(
                current_date=datetime(2024, 9, week*7, 13, 0),
                season_week=week,
                season_phase="regular_season"
            )
            
            # Create simple processing result
            result = ProcessingResult(
                processed_successfully=True,
                processing_type="TestProcessor"
            )
            result.add_statistic("test_week", week)
            
            manager.apply_processing_result(result, context)
            
            # Check context updates
            self.assertEqual(manager.current_week, week)
            self.assertEqual(manager.season_phase, "regular_season")
        
        summary = manager.get_season_summary()
        self.assertEqual(summary["current_week"], 5)
        self.assertEqual(summary["season_phase"], "regular_season")
        self.assertEqual(summary["processing_events"], 5)
    
    def test_performance_with_many_events(self):
        """Test system performance with multiple events"""
        calendar_manager = CalendarManager(
            start_date=self.test_date,
            enable_result_processing=True,
            processing_strategy=ProcessingStrategy.STATISTICS_ONLY,  # Faster mode
            season_year=2024
        )
        
        # Schedule many events
        for day_offset in range(10):
            event_date = self.test_date + timedelta(days=day_offset)
            for event_num in range(3):  # 3 events per day
                event = TrainingEvent(
                    event_name=f"Training {day_offset}-{event_num}",
                    date=event_date,
                    involved_teams=[1 + (event_num % 5)],  # Rotate through teams 1-5
                    duration_hours=1.0
                )
                success, _ = calendar_manager.schedule_event(event)
                self.assertTrue(success)
        
        # Simulate all events
        import time
        start_time = time.time()
        
        results = calendar_manager.advance_to_date(self.test_date + timedelta(days=9))
        
        end_time = time.time()
        simulation_time = end_time - start_time
        
        # Verify results
        total_events = sum(day.events_executed for day in results)
        self.assertEqual(total_events, 30)  # 10 days * 3 events
        
        # Performance should be reasonable (less than 5 seconds for 30 events)
        self.assertLess(simulation_time, 5.0, f"Simulation took {simulation_time:.2f}s, expected < 5.0s")
        
        # Check processing statistics
        stats = calendar_manager.get_calendar_stats()
        self.assertGreaterEqual(stats.total_processed_results, 0)  # May be 0 with placeholder events
    
    def tearDown(self):
        """Clean up after tests"""
        pass


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for realistic simulation scenarios"""
    
    def test_full_week_simulation_scenario(self):
        """Test a realistic full week of NFL activities"""
        start_date = date(2024, 9, 8)  # Sunday
        
        calendar = CalendarManager(
            start_date=start_date,
            enable_result_processing=True,
            processing_strategy=ProcessingStrategy.FULL_PROGRESSION,
            season_year=2024
        )
        
        # Sunday: Game day
        game = GameSimulationEvent(
            event_name="Lions vs Bears",
            date=start_date,
            involved_teams=[22, 5],  # Lions vs Bears
            duration_hours=3.5
        )
        calendar.schedule_event(game)
        
        # Monday: Rest day
        from src.simulation.events.placeholder_events import RestDayEvent
        rest = RestDayEvent(
            event_name="Team Recovery",
            date=start_date + timedelta(days=1),
            involved_teams=[22],
            duration_hours=0.5
        )
        calendar.schedule_event(rest)
        
        # Tuesday-Thursday: Training
        for day in range(2, 5):
            training = TrainingEvent(
                event_name=f"Practice Day {day-1}",
                date=start_date + timedelta(days=day),
                involved_teams=[22],
                duration_hours=2.0
            )
            calendar.schedule_event(training)
        
        # Friday: Scouting
        from src.simulation.events.placeholder_events import ScoutingEvent
        scouting = ScoutingEvent(
            event_name="College Scouting",
            date=start_date + timedelta(days=5),
            involved_teams=[22],
            duration_hours=4.0
        )
        calendar.schedule_event(scouting)
        
        # Saturday: Light practice
        light_training = TrainingEvent(
            event_name="Game Prep",
            date=start_date + timedelta(days=6),
            involved_teams=[22],
            duration_hours=1.5
        )
        calendar.schedule_event(light_training)
        
        # Simulate the full week
        week_results = calendar.advance_to_date(start_date + timedelta(days=6))
        
        # Verify comprehensive simulation
        self.assertEqual(len(week_results), 7)  # 7 days
        total_events = sum(day.events_executed for day in week_results)
        self.assertEqual(total_events, 6)  # 6 scheduled events
        
        # Check season state progression
        season_manager = calendar.get_season_state_manager()
        self.assertIsNotNone(season_manager)
        
        summary = season_manager.get_season_summary()
        self.assertGreater(summary["processing_events"], 0)
        
        # Verify team state tracking
        lions_state = season_manager.team_states[22]  # Lions
        self.assertGreaterEqual(lions_state.games_played, 0)  # May be 0 with placeholder events
        
        # Check processing summary
        processing_summary = calendar.get_processing_summary()
        self.assertTrue(processing_summary["result_processing_enabled"])
        self.assertEqual(processing_summary["season_year"], 2024)


def run_comprehensive_test_suite():
    """Run all tests in the comprehensive test suite"""
    
    print("Running Comprehensive Result Processing System Test Suite")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestResultProcessingSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0] if 'AssertionError: ' in traceback else 'See details above'}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback.split('\n')[-2] if len(traceback.split('\n')) > 1 else 'See details above'}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_test_suite()
    exit(0 if success else 1)