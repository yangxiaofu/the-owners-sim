"""
Player Stats Store

Store for player statistics with game-by-game tracking and season aggregation.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

from .base_store import BaseStore
from simulation.results.game_result import PlayerGameStats


@dataclass
class PlayerSeasonStats:
    """Aggregated season statistics for a player"""
    player_name: str
    position: str
    team_id: int
    games_played: int = 0

    # Offensive stats
    passing_yards: int = 0
    passing_tds: int = 0
    passing_attempts: int = 0
    passing_completions: int = 0
    passing_interceptions: int = 0

    rushing_yards: int = 0
    rushing_tds: int = 0
    rushing_attempts: int = 0

    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    targets: int = 0

    # Defensive stats
    tackles: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    pass_deflections: int = 0
    forced_fumbles: int = 0

    # Special teams
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    extra_points_made: int = 0
    extra_points_attempted: int = 0

    # Performance
    total_touchdowns: int = 0
    total_fantasy_points: float = 0.0

    def add_game_stats(self, game_stats: PlayerGameStats) -> None:
        """Add a game's statistics to season totals"""
        self.games_played += 1

        # Offensive
        self.passing_yards += game_stats.passing_yards
        self.passing_tds += game_stats.passing_tds
        self.passing_interceptions += game_stats.passing_interceptions
        self.rushing_yards += game_stats.rushing_yards
        self.rushing_tds += game_stats.rushing_tds
        self.receiving_yards += game_stats.receiving_yards
        self.receiving_tds += game_stats.receiving_tds
        self.receptions += game_stats.receptions

        # Defensive
        self.tackles += game_stats.tackles
        self.sacks += game_stats.sacks
        self.interceptions += game_stats.interceptions
        self.pass_deflections += game_stats.pass_deflections

        # Special teams
        self.field_goals_made += game_stats.field_goals_made
        self.field_goals_attempted += game_stats.field_goals_attempted
        self.extra_points_made += game_stats.extra_points_made
        self.extra_points_attempted += game_stats.extra_points_attempted

        # Total TDs
        self.total_touchdowns = (self.passing_tds + self.rushing_tds +
                                self.receiving_tds)

    def get_passing_rating(self) -> float:
        """Calculate NFL passer rating"""
        if self.passing_attempts == 0:
            return 0.0

        # NFL passer rating formula components
        a = min(((self.passing_completions / self.passing_attempts) - 0.3) * 5, 2.375)
        b = min(((self.passing_yards / self.passing_attempts) - 3) * 0.25, 2.375)
        c = min((self.passing_tds / self.passing_attempts) * 20, 2.375)
        d = max(2.375 - ((self.passing_interceptions / self.passing_attempts) * 25), 0)

        return ((a + b + c + d) / 6) * 100

    def get_yards_per_carry(self) -> float:
        """Calculate rushing yards per attempt"""
        if self.rushing_attempts == 0:
            return 0.0
        return self.rushing_yards / self.rushing_attempts

    def get_yards_per_reception(self) -> float:
        """Calculate receiving yards per reception"""
        if self.receptions == 0:
            return 0.0
        return self.receiving_yards / self.receptions


class PlayerStatsStore(BaseStore[Dict[str, PlayerGameStats]]):
    """
    Store for player statistics with game logs and season aggregation.
    Tracks individual game performances and maintains season totals
    for statistical analysis and reporting.
    """

    def __init__(self):
        """Initialize player stats store."""
        super().__init__("player_stats")

        # Season totals for each player
        self.season_totals: Dict[str, PlayerSeasonStats] = {}

        # Game logs for each player (player_name -> list of game stats)
        self.game_logs: Dict[str, List[Tuple[str, PlayerGameStats]]] = defaultdict(list)

        # Position group indices for quick lookups
        self.by_position: Dict[str, List[str]] = defaultdict(list)  # position -> [player_names]
        self.by_team: Dict[int, List[str]] = defaultdict(list)  # team_id -> [player_names]

    def add(self, key: str, item: Dict[str, PlayerGameStats]) -> None:
        """
        Add game statistics for multiple players.

        Args:
            key: Game identifier (e.g., "2024_week1_DAL_NYG")
            item: Dictionary of player stats keyed by player name
        """
        if self.is_locked():
            self.logger.warning(f"Cannot add to locked store {self.store_name}")
            return

        # Store the game stats
        self.data[key] = item

        # Process each player's stats
        for player_name, stats in item.items():
            self._process_player_game_stats(key, player_name, stats)

        self._update_metadata()
        self._log_transaction('add', key, True, {'player_count': len(item)})

    def add_game_stats(self, game_id: str, stats_list: List[PlayerGameStats]) -> None:
        """
        Add game statistics from a list of PlayerGameStats.

        Args:
            game_id: Unique game identifier
            stats_list: List of player statistics from the game
        """
        # Convert list to dictionary
        stats_dict = {stats.player_name: stats for stats in stats_list}
        self.add(game_id, stats_dict)

    def get(self, key: str) -> Optional[Dict[str, PlayerGameStats]]:
        """
        Get all player stats for a specific game.

        Args:
            key: Game identifier

        Returns:
            Dictionary of player stats if found, None otherwise
        """
        return self.data.get(key)

    def get_all(self) -> Dict[str, Dict[str, PlayerGameStats]]:
        """Get all stored game statistics."""
        return self.data.copy()

    def clear(self) -> None:
        """Clear all player statistics."""
        if self.is_locked():
            self.logger.warning(f"Cannot clear locked store {self.store_name}")
            return

        self.data.clear()
        self.season_totals.clear()
        self.game_logs.clear()
        self.by_position.clear()
        self.by_team.clear()

        self.metadata.last_cleared = datetime.now()
        self._update_metadata()
        self._log_transaction('clear', None, True)

    def validate(self) -> bool:
        """
        Validate player statistics consistency.

        Returns:
            True if all data is valid, False otherwise
        """
        try:
            # Verify season totals match game logs
            for player_name, season_stats in self.season_totals.items():
                if player_name not in self.game_logs:
                    self.logger.error(f"Player {player_name} has season stats but no game logs")
                    return False

                # Recalculate and compare
                recalculated = self._recalculate_season_stats(player_name)
                if recalculated and recalculated.games_played != season_stats.games_played:
                    self.logger.error(f"Game count mismatch for {player_name}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def get_player_season_stats(self, player_name: str) -> Optional[PlayerSeasonStats]:
        """
        Get aggregated season statistics for a player.

        Args:
            player_name: Name of the player

        Returns:
            Season statistics if player exists, None otherwise
        """
        return self.season_totals.get(player_name)

    def get_player_game_log(self, player_name: str) -> List[Tuple[str, PlayerGameStats]]:
        """
        Get all game statistics for a player.

        Args:
            player_name: Name of the player

        Returns:
            List of (game_id, stats) tuples
        """
        return self.game_logs.get(player_name, [])

    def get_top_performers(self, stat: str, limit: int = 10,
                          position: Optional[str] = None) -> List[Tuple[str, Any]]:
        """
        Get top performers for a specific statistic.

        Args:
            stat: Statistic to rank by (e.g., 'passing_yards', 'rushing_tds')
            limit: Number of players to return
            position: Optional position filter

        Returns:
            List of (player_name, stat_value) tuples
        """
        eligible_players = self.season_totals.values()

        if position:
            eligible_players = [p for p in eligible_players if p.position == position]

        # Sort by the requested stat
        if hasattr(PlayerSeasonStats, stat):
            sorted_players = sorted(
                eligible_players,
                key=lambda p: getattr(p, stat, 0),
                reverse=True
            )
            return [(p.player_name, getattr(p, stat)) for p in sorted_players[:limit]]

        return []

    def get_team_players(self, team_id: int) -> List[PlayerSeasonStats]:
        """
        Get all players for a specific team.

        Args:
            team_id: Team identifier

        Returns:
            List of player season statistics
        """
        player_names = self.by_team.get(team_id, [])
        return [self.season_totals[name] for name in player_names
                if name in self.season_totals]

    def get_position_leaders(self, position: str) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Get statistical leaders for a specific position.

        Args:
            position: Position to analyze (e.g., 'QB', 'RB', 'WR')

        Returns:
            Dictionary of stat categories to leader lists
        """
        leaders = {}

        if position == 'QB':
            leaders['passing_yards'] = self.get_top_performers('passing_yards', 5, 'QB')
            leaders['passing_tds'] = self.get_top_performers('passing_tds', 5, 'QB')
            leaders['passer_rating'] = self._get_top_passer_ratings(5)
        elif position == 'RB':
            leaders['rushing_yards'] = self.get_top_performers('rushing_yards', 5, 'RB')
            leaders['rushing_tds'] = self.get_top_performers('rushing_tds', 5, 'RB')
            leaders['yards_per_carry'] = self._get_top_yards_per_carry(5)
        elif position == 'WR' or position == 'TE':
            leaders['receiving_yards'] = self.get_top_performers('receiving_yards', 5, position)
            leaders['receptions'] = self.get_top_performers('receptions', 5, position)
            leaders['receiving_tds'] = self.get_top_performers('receiving_tds', 5, position)

        return leaders

    def _process_player_game_stats(self, game_id: str, player_name: str,
                                  stats: PlayerGameStats) -> None:
        """
        Process a player's game statistics.

        Args:
            game_id: Game identifier
            player_name: Player's name
            stats: Game statistics
        """
        # Add to game log
        self.game_logs[player_name].append((game_id, stats))

        # Update or create season totals
        if player_name not in self.season_totals:
            self.season_totals[player_name] = PlayerSeasonStats(
                player_name=player_name,
                position=stats.position,
                team_id=stats.team_id
            )

            # Update indices
            self.by_position[stats.position].append(player_name)
            self.by_team[stats.team_id].append(player_name)

        # Add game stats to season totals
        self.season_totals[player_name].add_game_stats(stats)

    def _recalculate_season_stats(self, player_name: str) -> Optional[PlayerSeasonStats]:
        """
        Recalculate season statistics from game logs.

        Args:
            player_name: Player's name

        Returns:
            Recalculated season stats if player exists
        """
        if player_name not in self.game_logs:
            return None

        game_log = self.game_logs[player_name]
        if not game_log:
            return None

        # Start with first game's basic info
        first_stats = game_log[0][1]
        season_stats = PlayerSeasonStats(
            player_name=player_name,
            position=first_stats.position,
            team_id=first_stats.team_id
        )

        # Add all game stats
        for _, game_stats in game_log:
            season_stats.add_game_stats(game_stats)

        return season_stats

    def _get_top_passer_ratings(self, limit: int) -> List[Tuple[str, float]]:
        """Get top QBs by passer rating."""
        qbs = [p for p in self.season_totals.values() if p.position == 'QB']
        rated_qbs = [(qb.player_name, qb.get_passing_rating()) for qb in qbs
                     if qb.passing_attempts >= 100]  # Min attempts for qualification
        return sorted(rated_qbs, key=lambda x: x[1], reverse=True)[:limit]

    def _get_top_yards_per_carry(self, limit: int) -> List[Tuple[str, float]]:
        """Get top RBs by yards per carry."""
        rbs = [p for p in self.season_totals.values() if p.position == 'RB']
        ypc_rbs = [(rb.player_name, rb.get_yards_per_carry()) for rb in rbs
                   if rb.rushing_attempts >= 50]  # Min attempts for qualification
        return sorted(ypc_rbs, key=lambda x: x[1], reverse=True)[:limit]

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize player statistics for persistence.

        Returns:
            Serializable dictionary
        """
        return {
            'game_stats': {
                game_id: {
                    player_name: {
                        'position': stats.position,
                        'team_id': stats.team_id,
                        'passing_yards': stats.passing_yards,
                        'passing_tds': stats.passing_tds,
                        'rushing_yards': stats.rushing_yards,
                        'rushing_tds': stats.rushing_tds,
                        'receiving_yards': stats.receiving_yards,
                        'receiving_tds': stats.receiving_tds,
                        'receptions': stats.receptions,
                        # Add more fields as needed
                    }
                    for player_name, stats in players.items()
                }
                for game_id, players in self.data.items()
            },
            'season_totals': {
                player_name: {
                    'games_played': stats.games_played,
                    'total_touchdowns': stats.total_touchdowns,
                    'passing_yards': stats.passing_yards,
                    'rushing_yards': stats.rushing_yards,
                    'receiving_yards': stats.receiving_yards,
                    # Add more season total fields
                }
                for player_name, stats in self.season_totals.items()
            }
        }