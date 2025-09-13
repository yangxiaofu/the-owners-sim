"""
Date utilities for NFL scheduling

Provides functions for calculating NFL season dates, converting between
week numbers and actual dates, and handling time zones.
"""

from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import calendar


class GameDay(Enum):
    """Days of the week for NFL games"""
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2


def get_labor_day(year: int) -> date:
    """
    Get Labor Day for a given year (first Monday in September).
    
    Args:
        year: Year to get Labor Day for
        
    Returns:
        Date of Labor Day
    """
    # Find first Monday in September
    sept_first = date(year, 9, 1)
    
    # Calculate days until Monday (0 = Monday)
    days_until_monday = (7 - sept_first.weekday()) % 7
    
    # If September 1st is Monday, Labor Day is September 1st
    # Otherwise, it's the first Monday after
    if days_until_monday == 0 and sept_first.weekday() == 0:
        return sept_first
    else:
        return sept_first + timedelta(days=days_until_monday or 7)


def get_season_start(year: int) -> date:
    """
    Get NFL season start date (Thursday after Labor Day).
    
    Args:
        year: Year of the season
        
    Returns:
        Date of season start (Thursday)
    """
    labor_day = get_labor_day(year)
    # Season starts Thursday after Labor Day (3 days later)
    return labor_day + timedelta(days=3)


def get_thanksgiving(year: int) -> date:
    """
    Get Thanksgiving Day (fourth Thursday in November).
    
    Args:
        year: Year to get Thanksgiving for
        
    Returns:
        Date of Thanksgiving
    """
    # Find first Thursday in November
    nov_first = date(year, 11, 1)
    days_until_thursday = (3 - nov_first.weekday()) % 7  # Thursday is 3
    first_thursday = nov_first + timedelta(days=days_until_thursday)
    
    # Fourth Thursday is 3 weeks later
    return first_thursday + timedelta(weeks=3)


def get_christmas(year: int) -> date:
    """Get Christmas Day for a given year"""
    return date(year, 12, 25)


def week_to_date(year: int, week: int, day: GameDay = GameDay.SUNDAY) -> date:
    """
    Convert NFL week number to actual date.
    
    Args:
        year: Season year
        week: Week number (1-18)
        day: Day of week for the game
        
    Returns:
        Date for that week and day
    """
    if week < 1 or week > 18:
        raise ValueError(f"Invalid week number: {week}. Must be 1-18.")
    
    season_start = get_season_start(year)
    
    # Calculate the start of the given week
    # Week 1 starts on the season start date (Thursday)
    week_start = season_start + timedelta(weeks=week - 1)
    
    # Find the Thursday of this week
    days_since_thursday = week_start.weekday() - 3  # Thursday is 3
    week_thursday = week_start - timedelta(days=days_since_thursday)
    
    # Calculate the target day
    if day == GameDay.THURSDAY:
        target_date = week_thursday
    elif day == GameDay.FRIDAY:
        target_date = week_thursday + timedelta(days=1)
    elif day == GameDay.SATURDAY:
        target_date = week_thursday + timedelta(days=2)
    elif day == GameDay.SUNDAY:
        target_date = week_thursday + timedelta(days=3)
    elif day == GameDay.MONDAY:
        target_date = week_thursday + timedelta(days=4)
    else:
        # Tuesday or Wednesday (rare but possible)
        days_offset = (day.value - 3) % 7
        target_date = week_thursday + timedelta(days=days_offset)
    
    return target_date


def get_game_datetime(year: int, week: int, time_slot: str) -> datetime:
    """
    Get full datetime for a game based on week and time slot.
    
    Args:
        year: Season year
        week: Week number
        time_slot: Time slot string (e.g., "TNF", "Sunday_1PM", etc.)
        
    Returns:
        Full datetime with appropriate time
    """
    # Map time slots to days and times (Eastern Time)
    slot_map = {
        'TNF': (GameDay.THURSDAY, time(20, 15)),      # 8:15 PM ET
        'Sunday_1PM': (GameDay.SUNDAY, time(13, 0)),   # 1:00 PM ET
        'Sunday_4PM': (GameDay.SUNDAY, time(16, 25)),  # 4:25 PM ET
        'Sunday_425PM': (GameDay.SUNDAY, time(16, 25)), # 4:25 PM ET
        'SNF': (GameDay.SUNDAY, time(20, 20)),         # 8:20 PM ET
        'MNF': (GameDay.MONDAY, time(20, 15)),         # 8:15 PM ET
        'Saturday': (GameDay.SATURDAY, time(16, 30)),  # 4:30 PM ET
        'International': (GameDay.SUNDAY, time(9, 30)), # 9:30 AM ET (London)
    }
    
    if time_slot not in slot_map:
        # Default to Sunday 1PM
        day, game_time = GameDay.SUNDAY, time(13, 0)
    else:
        day, game_time = slot_map[time_slot]
    
    game_date = week_to_date(year, week, day)
    return datetime.combine(game_date, game_time)


def get_week_date_range(year: int, week: int) -> Tuple[date, date]:
    """
    Get the date range for an NFL week (Thursday to Monday).
    
    Args:
        year: Season year
        week: Week number
        
    Returns:
        Tuple of (start_date, end_date) for the week
    """
    thursday = week_to_date(year, week, GameDay.THURSDAY)
    monday = week_to_date(year, week, GameDay.MONDAY)
    return (thursday, monday)


def date_to_week(game_date: date, season_year: int) -> Optional[int]:
    """
    Convert a date to its NFL week number.
    
    Args:
        game_date: Date to convert
        season_year: Season year
        
    Returns:
        Week number (1-18) or None if outside season
    """
    season_start = get_season_start(season_year)
    
    # Check if date is before season
    if game_date < season_start:
        return None
    
    # Calculate weeks since season start
    days_since_start = (game_date - season_start).days
    week = (days_since_start // 7) + 1
    
    # Check if within valid range
    if 1 <= week <= 18:
        return week
    else:
        return None


def get_season_dates(year: int) -> Dict[str, date]:
    """
    Get all important dates for an NFL season.
    
    Args:
        year: Season year
        
    Returns:
        Dictionary of important dates
    """
    season_start = get_season_start(year)
    
    return {
        'preseason_start': season_start - timedelta(weeks=4),
        'season_start': season_start,
        'week_1_sunday': week_to_date(year, 1, GameDay.SUNDAY),
        'thanksgiving': get_thanksgiving(year),
        'christmas': get_christmas(year),
        'week_18_end': week_to_date(year, 18, GameDay.MONDAY),
        'playoffs_start': week_to_date(year + 1, 18, GameDay.SATURDAY) + timedelta(days=6),
        'super_bowl': get_super_bowl_date(year)
    }


def get_super_bowl_date(season_year: int) -> date:
    """
    Get Super Bowl date (second Sunday in February of following year).
    
    Args:
        season_year: NFL season year (Super Bowl is in following calendar year)
        
    Returns:
        Date of Super Bowl
    """
    # Super Bowl is in February of the following year
    feb_first = date(season_year + 1, 2, 1)
    
    # Find first Sunday
    days_until_sunday = (6 - feb_first.weekday()) % 7
    if days_until_sunday == 0 and feb_first.weekday() == 6:
        first_sunday = feb_first
    else:
        first_sunday = feb_first + timedelta(days=days_until_sunday or 7)
    
    # Second Sunday
    return first_sunday + timedelta(weeks=1)


def is_primetime_slot(time_slot: str) -> bool:
    """Check if a time slot is considered primetime"""
    primetime_slots = {'TNF', 'SNF', 'MNF'}
    return time_slot in primetime_slots


def calculate_days_rest(game1_date: date, game2_date: date) -> int:
    """
    Calculate days of rest between two games.
    
    Args:
        game1_date: Date of first game
        game2_date: Date of second game
        
    Returns:
        Number of days rest (excluding game days)
    """
    return (game2_date - game1_date).days - 1


def get_bye_week_dates(year: int, week: int) -> Tuple[date, date]:
    """
    Get the date range for a team's bye week.
    
    Args:
        year: Season year
        week: Bye week number
        
    Returns:
        Tuple of (last_game_before, first_game_after) dates
    """
    # Last game would be in the previous week (likely Sunday)
    last_game = week_to_date(year, week - 1, GameDay.SUNDAY)
    
    # First game after would be in the following week
    first_game_after = week_to_date(year, week + 1, GameDay.SUNDAY)
    
    return (last_game, first_game_after)


def format_game_time(dt: datetime, include_timezone: bool = True) -> str:
    """
    Format a game datetime for display.
    
    Args:
        dt: Game datetime
        include_timezone: Whether to include timezone designation
        
    Returns:
        Formatted string like "Sun 09/08 1:00 PM ET"
    """
    day_names = {
        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
        4: 'Fri', 5: 'Sat', 6: 'Sun'
    }
    
    day = day_names[dt.weekday()]
    date_str = dt.strftime('%m/%d')
    time_str = dt.strftime('%-I:%M %p')
    
    if include_timezone:
        return f"{day} {date_str} {time_str} ET"
    else:
        return f"{day} {date_str} {time_str}"