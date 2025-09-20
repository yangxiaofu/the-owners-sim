"""
NFL Week to Date Calculator

Calculates actual dates for NFL weeks based on the season year.
NFL seasons start on the first Thursday of September.
"""

from datetime import date, timedelta
from typing import Dict


class WeekToDateCalculator:
    """
    Calculates NFL game dates based on week numbers.
    
    NFL Schedule Rules:
    - Season starts first Thursday of September
    - Most games on Sunday
    - Thursday Night Football (TNF)
    - Monday Night Football (MNF)
    - 18 weeks total (17 games + 1 bye per team)
    """
    
    def __init__(self, season_year: int):
        """
        Initialize the date calculator for a specific season.
        
        Args:
            season_year: Year the season starts (e.g., 2025)
        """
        self.season_year = season_year
        self.season_start = self._calculate_season_start()
        
    def _calculate_season_start(self) -> date:
        """
        Calculate the first Thursday of September for the season.
        
        Returns:
            Date of season kickoff (first Thursday of September)
        """
        # Start with September 1st
        sept_first = date(self.season_year, 9, 1)
        
        # Find the first Thursday
        # weekday() returns 0=Monday, 3=Thursday
        days_until_thursday = (3 - sept_first.weekday()) % 7
        if days_until_thursday == 0 and sept_first.weekday() != 3:
            days_until_thursday = 7
            
        first_thursday = sept_first + timedelta(days=days_until_thursday)
        return first_thursday
    
    def get_game_dates_for_week(self, week: int) -> Dict[str, date]:
        """
        Get the game dates for a specific week.
        
        Args:
            week: NFL week number (1-18)
            
        Returns:
            Dictionary with 'thursday', 'sunday', 'monday' dates
        """
        if week < 1 or week > 18:
            raise ValueError(f"Week must be between 1 and 18, got {week}")
        
        # Calculate the Thursday of the requested week
        # Week 1 starts on the first Thursday
        weeks_offset = week - 1
        week_thursday = self.season_start + timedelta(weeks=weeks_offset)
        
        # Calculate Sunday and Monday of the same week
        # Sunday is 3 days after Thursday
        week_sunday = week_thursday + timedelta(days=3)
        # Monday is 4 days after Thursday  
        week_monday = week_thursday + timedelta(days=4)
        
        return {
            'thursday': week_thursday,
            'sunday': week_sunday,
            'monday': week_monday
        }
    
    def get_season_summary(self) -> Dict[str, date]:
        """
        Get summary of key season dates.
        
        Returns:
            Dictionary with season milestone dates
        """
        # Calculate key dates
        week_1 = self.get_game_dates_for_week(1)
        week_18 = self.get_game_dates_for_week(18)
        
        return {
            'season_start': self.season_start,
            'first_game': week_1['thursday'],
            'last_regular_season_game': week_18['sunday'],
            'regular_season_end': week_18['monday']
        }
    
    def get_date_for_game(self, week: int, day_of_week: str) -> date:
        """
        Get the specific date for a game.
        
        Args:
            week: NFL week number (1-18)
            day_of_week: 'thursday', 'sunday', or 'monday'
            
        Returns:
            Date for the specified game
        """
        week_dates = self.get_game_dates_for_week(week)
        
        if day_of_week.lower() not in week_dates:
            raise ValueError(f"Invalid day_of_week: {day_of_week}. Must be 'thursday', 'sunday', or 'monday'")
        
        return week_dates[day_of_week.lower()]