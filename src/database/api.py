"""
Database API

Lean API for retrieving data from the SQLite database.
Provides single source of truth for all data access.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import json

from .connection import DatabaseConnection
from stores.standings_store import EnhancedTeamStanding, NFL_DIVISIONS, NFL_CONFERENCES
from team_management.players.player import Position


class DatabaseAPI:
    """
    Clean API for database retrieval operations.
    
    This class provides all data retrieval methods and serves as the
    single source of truth. Stores should never be used for retrieval.
    """
    
    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize database API.
        
        Args:
            database_path: Path to SQLite database
        """
        self.db_connection = DatabaseConnection(database_path)
        self.logger = logging.getLogger("DatabaseAPI")
    
    def get_standings(self, dynasty_id: str, season: int) -> Dict[str, Any]:
        """
        Get current standings from database.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Formatted standings data matching StandingsStore structure
        """
        query = '''
            SELECT team_id, wins, losses, ties, division_wins, division_losses,
                   conference_wins, conference_losses, home_wins, home_losses,
                   away_wins, away_losses, points_for, points_against,
                   current_streak, division_rank
            FROM standings
            WHERE dynasty_id = ? AND season = ?
            ORDER BY team_id
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, season))

        if not results:
            self.logger.warning(f"No standings found for dynasty {dynasty_id}, season {season}")
            return self._get_empty_standings()
        
        # Convert to standings format
        standings_data = {}
        
        # Group by divisions
        for division, team_ids in NFL_DIVISIONS.items():
            division_teams = []
            
            for team_id in team_ids:
                # Find this team in results
                team_record = None
                for row in results:
                    if row['team_id'] == team_id:
                        team_record = row
                        break
                
                if team_record:
                    # Create EnhancedTeamStanding object
                    standing = EnhancedTeamStanding(
                        team_id=team_id,
                        wins=team_record['wins'],
                        losses=team_record['losses'],
                        ties=team_record['ties'],
                        division_wins=team_record['division_wins'],
                        division_losses=team_record['division_losses'],
                        conference_wins=team_record['conference_wins'],
                        conference_losses=team_record['conference_losses'],
                        home_wins=team_record['home_wins'],
                        home_losses=team_record['home_losses'],
                        away_wins=team_record['away_wins'],
                        away_losses=team_record['away_losses'],
                        points_for=team_record['points_for'],
                        points_against=team_record['points_against'],
                        streak=team_record['current_streak'] or "",
                        division_place=team_record['division_rank'] or 1
                    )
                else:
                    # Create empty standing for missing team
                    standing = EnhancedTeamStanding(team_id=team_id)
                
                division_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })
            
            # Sort by record (wins desc, then win percentage desc)
            division_teams.sort(key=lambda x: (
                x['standing'].wins,
                x['standing'].win_percentage,
                -x['standing'].losses
            ), reverse=True)
            
            standings_data[division] = division_teams
        
        # Group by conferences for conference standings
        conferences_data = {}
        for conference, team_ids in NFL_CONFERENCES.items():
            conference_teams = []
            
            for team_id in team_ids:
                # Find this team in results
                for row in results:
                    if row['team_id'] == team_id:
                        standing = EnhancedTeamStanding(
                            team_id=team_id,
                            wins=row['wins'],
                            losses=row['losses'],
                            ties=row['ties'],
                            conference_wins=row['conference_wins'],
                            conference_losses=row['conference_losses'],
                            points_for=row['points_for'],
                            points_against=row['points_against']
                        )
                        conference_teams.append({
                            'team_id': team_id,
                            'standing': standing
                        })
                        break
            
            # Sort conference teams
            conference_teams.sort(key=lambda x: (
                x['standing'].wins,
                x['standing'].win_percentage,
                x['standing'].conference_wins,
                -x['standing'].losses
            ), reverse=True)
            
            conferences_data[conference] = conference_teams
        
        # Create overall standings
        overall_teams = []
        for row in results:
            standing = EnhancedTeamStanding(
                team_id=row['team_id'],
                wins=row['wins'],
                losses=row['losses'],
                ties=row['ties'],
                points_for=row['points_for'],
                points_against=row['points_against']
            )
            overall_teams.append({
                'team_id': row['team_id'],
                'standing': standing
            })
        
        overall_teams.sort(key=lambda x: (
            x['standing'].wins,
            x['standing'].win_percentage,
            -x['standing'].losses
        ), reverse=True)

        return {
            'divisions': standings_data,
            'conferences': conferences_data,
            'overall': overall_teams,
            'playoff_picture': {}  # TODO: Add playoff calculation if needed
        }
    
    def get_game_results(self, dynasty_id: str, week: int, season: int) -> List[Dict[str, Any]]:
        """
        Get game results for a specific week.
        
        Args:
            dynasty_id: Dynasty identifier
            week: Week number
            season: Season year
            
        Returns:
            List of game result dictionaries
        """
        query = '''
            SELECT game_id, home_team_id, away_team_id, home_score, away_score,
                   total_plays, game_duration_minutes, overtime_periods,
                   created_at
            FROM games
            WHERE dynasty_id = ? AND week = ? AND season = ?
            ORDER BY created_at
        '''
        
        results = self.db_connection.execute_query(query, (dynasty_id, week, season))
        
        game_list = []
        for row in results:
            game_data = {
                'game_id': row['game_id'],
                'home_team_id': row['home_team_id'],
                'away_team_id': row['away_team_id'],
                'home_score': row['home_score'],
                'away_score': row['away_score'],
                'total_plays': row['total_plays'],
                'game_duration_minutes': row['game_duration_minutes'],
                'overtime_periods': row['overtime_periods'],
                'week': week,
                'date': row['created_at']
            }
            game_list.append(game_data)
        
        return game_list

    def get_games_by_date_range(
        self,
        dynasty_id: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Get all completed games within a date range (for calendar display).

        Args:
            dynasty_id: Dynasty identifier
            start_timestamp_ms: Start of range (milliseconds since epoch)
            end_timestamp_ms: End of range (milliseconds since epoch)

        Returns:
            List of game dictionaries with date, teams, scores, etc.
        """
        query = '''
            SELECT
                game_id,
                game_date,
                season,
                week,
                season_type,
                game_type,
                home_team_id,
                away_team_id,
                home_score,
                away_score,
                total_plays,
                game_duration_minutes,
                overtime_periods
            FROM games
            WHERE dynasty_id = ?
            AND game_date >= ?
            AND game_date <= ?
            ORDER BY game_date ASC
        '''

        results = self.db_connection.execute_query(
            query,
            (dynasty_id, start_timestamp_ms, end_timestamp_ms)
        )
        return results if results else []

    def get_team_standing(self, dynasty_id: str, team_id: int, season: int) -> Optional[EnhancedTeamStanding]:
        """
        Get standing for a specific team.
        
        Args:
            dynasty_id: Dynasty identifier
            team_id: Team identifier
            season: Season year
            
        Returns:
            Team standing or None if not found
        """
        query = '''
            SELECT team_id, wins, losses, ties, division_wins, division_losses,
                   conference_wins, conference_losses, home_wins, home_losses,
                   away_wins, away_losses, points_for, points_against,
                   current_streak, division_rank
            FROM standings 
            WHERE dynasty_id = ? AND team_id = ? AND season = ?
        '''
        
        results = self.db_connection.execute_query(query, (dynasty_id, team_id, season))
        
        if not results:
            return None
        
        row = results[0]
        return EnhancedTeamStanding(
            team_id=row['team_id'],
            wins=row['wins'],
            losses=row['losses'],
            ties=row['ties'],
            division_wins=row['division_wins'],
            division_losses=row['division_losses'],
            conference_wins=row['conference_wins'],
            conference_losses=row['conference_losses'],
            home_wins=row['home_wins'],
            home_losses=row['home_losses'],
            away_wins=row['away_wins'],
            away_losses=row['away_losses'],
            points_for=row['points_for'],
            points_against=row['points_against'],
            streak=row['current_streak'] or "",
            division_place=row['division_rank'] or 1
        )
    
    def _get_empty_standings(self) -> Dict[str, Any]:
        """
        Get empty standings structure for new seasons.
        
        Returns:
            Empty standings with all teams at 0-0
        """
        standings_data = {}
        
        # Initialize all divisions with 0-0 records
        for division, team_ids in NFL_DIVISIONS.items():
            division_teams = []
            for team_id in team_ids:
                standing = EnhancedTeamStanding(team_id=team_id)
                division_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })
            standings_data[division] = division_teams
        
        # Initialize conferences
        conferences_data = {}
        for conference, team_ids in NFL_CONFERENCES.items():
            conference_teams = []
            for team_id in team_ids:
                standing = EnhancedTeamStanding(team_id=team_id)
                conference_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })
            conferences_data[conference] = conference_teams
        
        # Initialize overall
        overall_teams = []
        for team_id in range(1, 33):
            standing = EnhancedTeamStanding(team_id=team_id)
            overall_teams.append({
                'team_id': team_id,
                'standing': standing
            })
        
        return {
            'divisions': standings_data,
            'conferences': conferences_data,
            'overall': overall_teams,
            'playoff_picture': {}
        }

    def get_passing_leaders(self, dynasty_id: str, season: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get passing statistics leaders for the season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of top players to return

        Returns:
            List of passing leaders with aggregated stats
        """
        query = '''
            SELECT
                player_name,
                player_id,
                team_id,
                position,
                SUM(passing_yards) as total_passing_yards,
                SUM(passing_tds) as total_passing_tds,
                SUM(passing_completions) as total_completions,
                SUM(passing_attempts) as total_attempts,
                COUNT(*) as games_played,
                ROUND(AVG(CAST(passing_yards AS FLOAT)), 1) as avg_yards_per_game,
                CASE
                    WHEN SUM(passing_attempts) > 0
                    THEN ROUND((CAST(SUM(passing_completions) AS FLOAT) / SUM(passing_attempts)) * 100, 1)
                    ELSE 0.0
                END as completion_percentage
            FROM player_game_stats
            WHERE dynasty_id = ?
                AND position = ?
                AND (passing_attempts > 0 OR passing_yards > 0)
            GROUP BY player_id, player_name, team_id, position
            ORDER BY total_passing_yards DESC
            LIMIT ?
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, Position.QB, limit))

        return [dict(row) for row in results]

    def get_rushing_leaders(self, dynasty_id: str, season: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get rushing statistics leaders for the season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of top players to return

        Returns:
            List of rushing leaders with aggregated stats
        """
        query = '''
            SELECT
                player_name,
                player_id,
                team_id,
                position,
                SUM(rushing_yards) as total_rushing_yards,
                SUM(rushing_tds) as total_rushing_tds,
                SUM(rushing_attempts) as total_attempts,
                COUNT(*) as games_played,
                ROUND(AVG(CAST(rushing_yards AS FLOAT)), 1) as avg_yards_per_game,
                CASE
                    WHEN SUM(rushing_attempts) > 0
                    THEN ROUND(CAST(SUM(rushing_yards) AS FLOAT) / SUM(rushing_attempts), 2)
                    ELSE 0.0
                END as yards_per_carry
            FROM player_game_stats
            WHERE dynasty_id = ?
                AND (rushing_attempts > 0 OR rushing_yards > 0)
            GROUP BY player_id, player_name, team_id, position
            ORDER BY total_rushing_yards DESC
            LIMIT ?
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, limit))

        return [dict(row) for row in results]

    def get_receiving_leaders(self, dynasty_id: str, season: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get receiving statistics leaders for the season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of top players to return

        Returns:
            List of receiving leaders with aggregated stats
        """
        query = '''
            SELECT
                player_name,
                player_id,
                team_id,
                position,
                SUM(receiving_yards) as total_receiving_yards,
                SUM(receiving_tds) as total_receiving_tds,
                SUM(receptions) as total_receptions,
                SUM(targets) as total_targets,
                COUNT(*) as games_played,
                ROUND(AVG(CAST(receiving_yards AS FLOAT)), 1) as avg_yards_per_game,
                CASE
                    WHEN SUM(receptions) > 0
                    THEN ROUND(CAST(SUM(receiving_yards) AS FLOAT) / SUM(receptions), 2)
                    ELSE 0.0
                END as yards_per_reception,
                CASE
                    WHEN SUM(targets) > 0
                    THEN ROUND((CAST(SUM(receptions) AS FLOAT) / SUM(targets)) * 100, 1)
                    ELSE 0.0
                END as catch_percentage
            FROM player_game_stats
            WHERE dynasty_id = ?
                AND (receptions > 0 OR receiving_yards > 0 OR targets > 0)
            GROUP BY player_id, player_name, team_id, position
            ORDER BY total_receiving_yards DESC
            LIMIT ?
        '''

        results = self.db_connection.execute_query(query, (dynasty_id, limit))

        return [dict(row) for row in results]

    def get_upcoming_games(self, start_date_str: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get games scheduled in the next N days from events table.

        This method queries the events table to find scheduled games within
        a date range, providing a reusable way to view upcoming matchups.

        Args:
            start_date_str: Starting date in YYYY-MM-DD format
            days: Number of days ahead to look (default: 7)

        Returns:
            List of upcoming game dictionaries with matchup information
        """
        # Parse date manually to avoid calendar module conflict
        year, month, day = map(int, start_date_str.split('-'))
        start_date = datetime(year, month, day)
        end_date = start_date + timedelta(days=days)
        end_date_str = f"{end_date.year:04d}-{end_date.month:02d}-{end_date.day:02d}"

        query = '''
            SELECT event_id, game_id, data, timestamp
            FROM events
            WHERE event_type = 'GAME'
            ORDER BY timestamp
        '''

        results = self.db_connection.execute_query(query)

        upcoming_games = []
        for row in results:
            data = json.loads(row['data'])
            params = data.get('parameters', data)

            game_date_str = params.get('game_date', '')
            if 'T' in game_date_str:
                game_date_part = game_date_str.split('T')[0]
            else:
                game_date_part = game_date_str[:10] if len(game_date_str) >= 10 else game_date_str

            if start_date_str <= game_date_part < end_date_str:
                upcoming_games.append({
                    'event_id': row['event_id'],
                    'game_id': row['game_id'],
                    'game_date': game_date_part,
                    'away_team_id': params.get('away_team_id'),
                    'home_team_id': params.get('home_team_id'),
                    'week': params.get('week'),
                    'season': params.get('season', 2024),
                    'timestamp': row['timestamp']
                })

        return upcoming_games

    def get_player_leaders_unified(
        self,
        dynasty_id: str,
        season: int,
        stat_category: str,
        limit: int = 10,
        position_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Unified method to get player stat leaders across any category.

        Provides flexible querying for any statistical category without
        requiring separate methods for each stat type.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stat_category: Stat category ('passing_yards', 'rushing_yards', 'receiving_yards', etc.)
            limit: Number of top players to return
            position_filter: Optional position filter (e.g., 'QB', 'RB', 'WR')

        Returns:
            List of player leaders with aggregated stats for the requested category
        """
        # Validate stat category
        valid_categories = {
            'passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts',
            'rushing_yards', 'rushing_tds', 'rushing_attempts',
            'receiving_yards', 'receiving_tds', 'receptions', 'targets',
            'tackles_total', 'sacks', 'interceptions',
            'field_goals_made', 'field_goals_attempted'
        }

        if stat_category not in valid_categories:
            raise ValueError(f"Invalid stat category: {stat_category}. Must be one of {valid_categories}")

        # Build dynamic query based on category
        position_clause = "AND position = ?" if position_filter else ""
        position_params = (position_filter,) if position_filter else ()

        query = f'''
            SELECT
                player_name,
                player_id,
                team_id,
                position,
                SUM({stat_category}) as total_{stat_category},
                COUNT(*) as games_played,
                ROUND(AVG(CAST({stat_category} AS FLOAT)), 1) as avg_per_game
            FROM player_game_stats
            WHERE dynasty_id = ?
                {position_clause}
                AND {stat_category} > 0
            GROUP BY player_id, player_name, team_id, position
            ORDER BY total_{stat_category} DESC
            LIMIT ?
        '''

        params = (dynasty_id,) + position_params + (limit,)
        results = self.db_connection.execute_query(query, params)

        return [dict(row) for row in results]