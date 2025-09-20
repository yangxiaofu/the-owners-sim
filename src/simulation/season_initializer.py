"""
Season Initializer

Orchestrates the complete initialization of an NFL season, including:
- Dynasty creation
- Schedule generation
- Calendar setup
- Database initialization
"""

import sys
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation.dynasty_context import DynastyContext, get_dynasty_context

# Try to import real components, fall back to mocks for testing
try:
    from simulation.calendar_manager import CalendarManager
except ImportError:
    CalendarManager = None

# Import real StoreManager for Phase 2
from stores.store_manager import StoreManager

try:
    from database.connection import DatabaseConnection
except ImportError:
    DatabaseConnection = None

try:
    from persistence.daily_persister import DailyDataPersister
except ImportError:
    DailyDataPersister = None

try:
    from simulation.events.game_simulation_event import GameSimulationEvent
except ImportError:
    GameSimulationEvent = None

from scheduling.generator.simple_scheduler import CompleteScheduler
from scheduling.utils.date_calculator import WeekToDateCalculator
from scheduling.template.schedule_template import SeasonSchedule
from scheduling.converters.schedule_to_event_converter import ScheduleToEventConverter

try:
    from team_management.personnel import TeamRosterGenerator
except ImportError:
    TeamRosterGenerator = None


class SeasonInitializer:
    """
    Main orchestrator for NFL season initialization.
    
    This class brings together all components needed to start a new season:
    - Dynasty management
    - Schedule generation
    - Calendar setup with game events
    - Database persistence
    - Team roster initialization
    """
    
    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize the season initializer.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.dynasty_context = get_dynasty_context()
        self.store_manager: Optional[StoreManager] = None
        self.calendar_manager: Optional[CalendarManager] = None
        self.db_connection: Optional[DatabaseConnection] = None
        self.daily_persister: Optional[DailyDataPersister] = None
        self.schedule: Optional[SeasonSchedule] = None
        self.date_calculator: Optional[WeekToDateCalculator] = None
    
    def initialize_season(
        self,
        season_year: int,
        dynasty_name: str,
        start_date: Optional[date] = None,
        existing_dynasty_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize a complete NFL season.
        
        Args:
            season_year: Year the season starts (e.g., 2025)
            dynasty_name: Name for this dynasty/franchise
            start_date: Optional custom start date (defaults to Sept 1)
            existing_dynasty_id: Optional existing dynasty to continue
            
        Returns:
            Dictionary with initialization results
        """
        print(f"\n🏈 Initializing {season_year} NFL Season")
        print("=" * 50)
        
        try:
            # Step 1: Initialize Dynasty
            dynasty_id = self._initialize_dynasty(dynasty_name, season_year, existing_dynasty_id)
            print(f"✅ Dynasty initialized: {dynasty_id[:8]}...")
            
            # Step 1.5: Initialize Team Registry
            self._initialize_team_registry(dynasty_name, season_year)
            print("✅ Team registry initialized")
            
            # Step 2: Set up Database
            self._setup_database(dynasty_id)
            print("✅ Database connected and initialized")
            
            # Step 3: Generate Schedule
            self.schedule = self._generate_schedule(season_year)
            print(f"✅ Generated schedule: {len(self.schedule.get_assigned_games())} games")
            
            # Step 4: Initialize Date Calculator
            # Let WeekToDateCalculator calculate the proper NFL season start
            # (first Thursday of September)
            self.date_calculator = WeekToDateCalculator(season_year)
            print(f"✅ Date calculator initialized (season starts {self.date_calculator.season_start})")
            
            # Step 5: Initialize Team Rosters
            self._initialize_rosters()
            print("✅ Team rosters initialized")
            
            # Step 6: Set up Store Manager with database path
            self.store_manager = StoreManager(self.database_path)
            print("✅ Store manager created")
            
            # Set dynasty context for stores that support persistence
            dynasty_id = self.dynasty_context.dynasty_id
            self.store_manager.set_dynasty_context(dynasty_id, season_year)
            print("✅ Dynasty context set for stores")
            
            # Step 7: Set up Calendar Manager
            # Use the actual NFL season start date from the date calculator
            calendar_start = self.date_calculator.season_start if self.date_calculator else date(season_year, 9, 1)
            self.calendar_manager = self._setup_calendar(calendar_start)
            print("✅ Calendar manager initialized")
            
            # Step 8: Schedule Games in Calendar
            games_scheduled = self._schedule_games_in_calendar()
            print(f"✅ Scheduled {games_scheduled} games in calendar")
            
            # Step 9: Persist initial state
            self._persist_initial_state()
            print("✅ Initial state persisted to database")
            
            # Return summary
            return self._get_initialization_summary()
            
        except Exception as e:
            error_msg = f"Season initialization failed: {str(e)}"
            print(f"\n❌ {error_msg}")
            raise RuntimeError(error_msg) from e
    
    def _initialize_dynasty(self, name: str, year: int, existing_id: Optional[str]) -> str:
        """
        Initialize or load dynasty context.
        
        Args:
            name: Dynasty name
            year: Season year
            existing_id: Optional existing dynasty ID
            
        Returns:
            Dynasty ID
        """
        dynasty_id = self.dynasty_context.initialize_dynasty(
            dynasty_name=name,
            season_year=year,
            dynasty_id=existing_id
        )
        
        # Set additional metadata
        self.dynasty_context.set_metadata('initialized_at', datetime.now().isoformat())
        self.dynasty_context.set_metadata('season_type', 'regular')
        
        return dynasty_id
    
    def _initialize_team_registry(self, dynasty_name: str, season_year: int) -> None:
        """
        Initialize the Dynasty Team Registry for consistent team data.
        
        Args:
            dynasty_name: Name of the dynasty
            season_year: Season year
        """
        try:
            # Import registry here to handle cases where it's not available
            from team_registry import initialize_dynasty_teams
            
            # Initialize registry with standard NFL team configuration
            # TODO: Could be made configurable for custom dynasties
            registry = initialize_dynasty_teams(dynasty_name, season_year, "standard_nfl")
            
            # Store reference for potential future use
            self.team_registry = registry
            
        except ImportError:
            # Team registry not available - continue without it
            # GameSimulationEvent will fall back to its backup mapping
            print("⚠️  Team registry not available - using fallback team mappings")
            self.team_registry = None
        except Exception as e:
            # Registry initialization failed - continue with fallback
            print(f"⚠️  Team registry initialization failed: {e}")
            self.team_registry = None
    
    def _setup_database(self, dynasty_id: str) -> None:
        """
        Set up database connection and create dynasty.
        
        Args:
            dynasty_id: Dynasty ID to use
        """
        if DatabaseConnection is None or DailyDataPersister is None:
            # Database components not available in Phase 1
            self.db_connection = None
            self.daily_persister = None
            return
        
        # Create database connection
        self.db_connection = DatabaseConnection(self.database_path)
        
        # Ensure dynasty exists in database
        conn = self.db_connection.get_connection()
        cursor = conn.cursor()
        
        # Check if dynasty exists
        cursor.execute(
            "SELECT dynasty_id FROM dynasties WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        
        if not cursor.fetchone():
            # Create new dynasty in database
            cursor.execute(
                """
                INSERT INTO dynasties (dynasty_id, dynasty_name, team_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (dynasty_id, self.dynasty_context.dynasty_name, 22, datetime.now())  # Default to Lions (22)
            )
            conn.commit()
        
        conn.close()
        
        # Create daily persister (with correct parameter name)
        self.daily_persister = DailyDataPersister(
            store_manager=None,  # Will be set later
            database_connection=self.db_connection,  # Correct parameter name
            dynasty_id=dynasty_id
        )
    
    def _generate_schedule(self, year: int) -> SeasonSchedule:
        """
        Generate complete NFL schedule.
        
        Args:
            year: Season year
            
        Returns:
            Complete season schedule
        """
        scheduler = CompleteScheduler()
        return scheduler.generate_full_schedule(year)
    
    def _initialize_rosters(self) -> None:
        """
        Initialize rosters for all 32 teams.
        """
        if TeamRosterGenerator is None:
            # Mock roster initialization for Phase 1 testing
            rosters = {}
            for team_id in range(1, 33):
                rosters[f"team_{team_id}_roster"] = 53  # Standard NFL roster size
            
            self.dynasty_context.set_metadata('rosters_initialized', True)
            self.dynasty_context.set_metadata('roster_counts', rosters)
            self.dynasty_context.set_metadata('roster_type', 'mock')
        else:
            roster_generator = TeamRosterGenerator()
            
            # Store rosters in dynasty context metadata
            rosters = {}
            for team_id in range(1, 33):
                roster = roster_generator.generate_sample_roster(team_id)
                rosters[f"team_{team_id}_roster"] = len(roster)
            
            self.dynasty_context.set_metadata('rosters_initialized', True)
            self.dynasty_context.set_metadata('roster_counts', rosters)
            self.dynasty_context.set_metadata('roster_type', 'generated')
    
    def _setup_calendar(self, start_date: date) -> Optional[CalendarManager]:
        """
        Set up calendar manager with persistence.
        
        Args:
            start_date: Season start date
            
        Returns:
            Configured CalendarManager or None if not available
        """
        if CalendarManager is None:
            # Calendar manager not available in Phase 1
            return None
        
        # Update persister with store manager
        if self.daily_persister:
            self.daily_persister.store_manager = self.store_manager
        
        # Create calendar with CORRECT parameters
        calendar = CalendarManager(
            start_date=start_date,  # Required first parameter
            season_year=self.dynasty_context.get_season_year(),
            daily_persister=self.daily_persister,
            enable_result_processing=True,  # Enable to update standings!
            store_manager=self.store_manager  # Pass store manager for standings updates
        )
        
        return calendar
    
    def _schedule_games_in_calendar(self) -> int:
        """
        Convert schedule to calendar events and schedule them.
        
        Returns:
            Number of games successfully scheduled
        """
        if not self.schedule or not self.calendar_manager or not self.date_calculator:
            print("⚠️  Prerequisites not initialized for scheduling")
            return 0
        
        # Use the new ScheduleToEventConverter with team registry and store manager
        converter = ScheduleToEventConverter(
            self.date_calculator, 
            team_registry=self.team_registry,
            store_manager=self.store_manager
        )
        
        # Validate registry is available for event creation
        if self.team_registry and hasattr(self.team_registry, 'is_initialized') and self.team_registry.is_initialized():
            print(f"✅ ScheduleToEventConverter using registry with {len(self.team_registry)} teams")
        else:
            print("⚠️  ScheduleToEventConverter proceeding without registry - may cause Week 5+ standings issues")
        
        # Convert all games to events
        print(f"\n📅 Converting schedule to events...")
        events = converter.convert_schedule(self.schedule)
        
        if not events:
            print("⚠️  No events created from schedule")
            return 0
        
        # Get summary of converted events
        summary = converter.get_event_summary(events)
        print(f"✅ Converted {summary['total_events']} games to events")
        print(f"   - Thursday games: {summary['thursday_games']}")
        print(f"   - Sunday games: {summary['sunday_games']}")
        print(f"   - Monday games: {summary['monday_games']}")
        print(f"   - Primetime games: {summary['primetime_games']}")
        
        # Schedule events in calendar
        games_scheduled = 0
        games_failed = 0
        
        print(f"\n📅 Scheduling {len(events)} games in calendar...")
        
        for event in events:
            try:
                # Schedule the event in calendar
                success, msg = self.calendar_manager.schedule_event(event)
                
                if success:
                    games_scheduled += 1
                    if games_scheduled <= 5:  # Show first 5 for confirmation
                        # Handle both dict and GameSimulationEvent
                        if isinstance(event, dict):
                            week = event['week']
                            away_id = event['away_team_id']
                            home_id = event['home_team_id']
                            event_date = event['date']
                        else:
                            week = event.week
                            away_id = event.away_team_id
                            home_id = event.home_team_id
                            event_date = event.date
                        
                        print(f"   ✓ Week {week} {event_date.strftime('%a %I:%M %p')}: Team {away_id} @ Team {home_id}")
                else:
                    games_failed += 1
                    if games_failed <= 3:  # Show first 3 failures
                        print(f"   ✗ Failed to schedule: {msg}")
                    
            except Exception as e:
                games_failed += 1
                print(f"   ✗ Error scheduling event: {e}")
                if games_failed >= 10:  # Stop if too many failures
                    print("   ⚠️  Too many failures, stopping scheduling")
                    break
        
        if games_scheduled > 5:
            print(f"   ... and {games_scheduled - 5} more games")
        
        if games_failed > 0:
            print(f"\n⚠️  Failed to schedule {games_failed} games")
        
        print(f"\n✅ Successfully scheduled {games_scheduled}/{len(events)} games in calendar")
        
        return games_scheduled
    
    def _persist_initial_state(self) -> None:
        """
        Persist initial season state to database.
        """
        if not self.db_connection or not self.schedule:
            return
        
        conn = self.db_connection.get_connection()
        cursor = conn.cursor()
        
        # Save season metadata (only columns that exist)
        cursor.execute(
            """
            INSERT OR REPLACE INTO dynasty_seasons 
            (dynasty_id, season)
            VALUES (?, ?)
            """,
            (
                self.dynasty_context.get_dynasty_id(),
                self.dynasty_context.get_season_year()
            )
        )
        
        # Note: schedules table is for individual games, not full schedule summary
        # We'll skip this for now as it needs proper game-by-game insertion
        # This would be better handled when we persist actual game schedules
        
        conn.commit()
        conn.close()
    
    def _get_initialization_summary(self) -> Dict[str, Any]:
        """
        Get summary of initialization results.
        
        Returns:
            Dictionary with initialization details
        """
        dynasty_summary = self.dynasty_context.get_summary()
        
        schedule_summary = {}
        if self.schedule:
            schedule_summary = {
                'total_games': len(self.schedule.get_assigned_games()),
                'total_weeks': 18,
                'primetime_games': len(self.schedule.get_primetime_games())
            }
        
        date_summary = {}
        if self.date_calculator:
            season_info = self.date_calculator.get_season_summary()
            date_summary = {
                'season_start': season_info['season_start'].isoformat(),
                'first_game': season_info['first_game'].isoformat(),
                'last_regular_game': season_info['last_regular_season_game'].isoformat()
            }
        
        return {
            'success': True,
            'dynasty': dynasty_summary,
            'schedule': schedule_summary,
            'dates': date_summary,
            'database': {
                'path': self.database_path,
                'connected': self.db_connection is not None,
                'persister_ready': self.daily_persister is not None
            },
            'components': {
                'store_manager': self.store_manager is not None,
                'calendar_manager': self.calendar_manager is not None,
                'date_calculator': self.date_calculator is not None
            }
        }
    
    def get_calendar_manager(self) -> Optional[CalendarManager]:
        """
        Get the initialized calendar manager.
        
        Returns:
            CalendarManager instance or None
        """
        return self.calendar_manager
    
    def get_dynasty_id(self) -> str:
        """
        Get the current dynasty ID.
        
        Returns:
            Dynasty ID string
        """
        return self.dynasty_context.get_dynasty_id()
    
    def simulate_day(self, target_date: date) -> Dict[str, Any]:
        """
        Simulate a specific day (convenience method).
        
        Args:
            target_date: Date to simulate
            
        Returns:
            Day simulation results
        """
        if not self.calendar_manager:
            raise RuntimeError("Calendar manager not initialized")
        
        # Use the correct method name
        result = self.calendar_manager.simulate_day(target_date)
        
        # Convert DaySimulationResult to dict for consistency
        return {
            'date': result.date,
            'events_executed': result.events_executed,
            'successful_events': result.successful_events,
            'failed_events': result.failed_events,
            'success_rate': result.success_rate,
            'teams_involved': list(result.teams_involved)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current season status.
        
        Returns:
            Status dictionary
        """
        return {
            'dynasty_id': self.dynasty_context.get_dynasty_id() if self.dynasty_context.is_initialized() else None,
            'season_year': self.dynasty_context.get_season_year() if self.dynasty_context.is_initialized() else None,
            'current_date': self.calendar_manager.current_date.isoformat() if self.calendar_manager else None,
            'games_scheduled': len(self.schedule.get_assigned_games()) if self.schedule else 0,
            'components_ready': {
                'dynasty': self.dynasty_context.is_initialized(),
                'database': self.db_connection is not None,
                'calendar': self.calendar_manager is not None,
                'schedule': self.schedule is not None
            }
        }
