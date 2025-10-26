"""
Season Aggregator for Statistics Preservation System

Aggregates game-level statistics into season summaries for archival.
This is distinct from SeasonStatsAggregator which handles real-time updates.

Key Differences:
- Returns structured dataclasses (PlayerSeasonStats, SeasonArchive)
- Designed for end-of-season batch processing
- Includes award tracking and season metadata
- Pure data transformation (no database writes)
"""

from typing import List, Dict, Any, Optional
import logging
import sqlite3
from datetime import datetime

from statistics.models import PlayerSeasonStats, SeasonArchive
from stats_calculations.calculations import calculate_passer_rating


class SeasonAggregator:
    """
    Aggregate game-level statistics into season summaries for archival.

    This class is responsible for transforming player_game_stats data
    into PlayerSeasonStats objects that can be persisted to the
    player_season_stats table by the StatisticsArchiver.

    Design Philosophy:
    - Pure data transformation (no side effects)
    - Returns typed dataclasses (not raw dicts)
    - Independent of archival policy logic
    - Reusable for any season aggregation need
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        database_conn: Optional[sqlite3.Connection] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize season aggregator.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
            database_conn: Optional external database connection
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.external_conn = database_conn
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def aggregate_player_season_stats(
        self,
        season: int,
        season_type: str = "regular_season"
    ) -> List[PlayerSeasonStats]:
        """
        Aggregate all player stats for a season.

        Process:
        1. Query all player_game_stats for season
        2. Group by player_id
        3. Sum counting stats (yards, TDs, etc.)
        4. Calculate derived metrics (passer rating, YPC, catch rate)
        5. Return list of PlayerSeasonStats dataclasses

        Args:
            season: Season year to aggregate
            season_type: "regular_season" or "playoffs"

        Returns:
            List of PlayerSeasonStats dataclasses

        Raises:
            sqlite3.Error: If database query fails
        """
        conn = self._get_connection()

        try:
            query = """
            SELECT
                pgs.dynasty_id,
                pgs.player_id,
                MAX(pgs.player_name) as player_name,
                MAX(pgs.team_id) as team_id,
                MAX(pgs.position) as position,

                -- Game counts
                COUNT(DISTINCT g.game_id) as games_played,
                0 as games_started,  -- Not tracked in game stats

                -- Passing (counting)
                SUM(pgs.passing_attempts) as passing_attempts,
                SUM(pgs.passing_completions) as passing_completions,
                SUM(pgs.passing_yards) as passing_yards,
                SUM(pgs.passing_tds) as passing_tds,
                SUM(pgs.passing_interceptions) as passing_interceptions,

                -- Rushing (counting)
                SUM(pgs.rushing_attempts) as rushing_attempts,
                SUM(pgs.rushing_yards) as rushing_yards,
                SUM(pgs.rushing_tds) as rushing_tds,

                -- Receiving (counting)
                SUM(pgs.targets) as targets,
                SUM(pgs.receptions) as receptions,
                SUM(pgs.receiving_yards) as receiving_yards,
                SUM(pgs.receiving_tds) as receiving_tds,

                -- Defense (counting)
                SUM(pgs.tackles_total) as tackles_total,
                SUM(COALESCE(pgs.tackles_solo, 0)) as tackles_solo,
                SUM(COALESCE(pgs.tackles_assist, 0)) as tackles_assist,
                SUM(pgs.sacks) as sacks,
                SUM(pgs.interceptions) as interceptions_def,
                SUM(COALESCE(pgs.forced_fumbles, 0)) as forced_fumbles,
                0 as defensive_tds,

                -- Special teams (counting)
                SUM(pgs.field_goals_made) as field_goals_made,
                SUM(pgs.field_goals_attempted) as field_goals_attempted,
                SUM(pgs.extra_points_made) as extra_points_made,
                SUM(pgs.extra_points_attempted) as extra_points_attempted

            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
                AND g.season = ?
                AND g.season_type = ?
            GROUP BY pgs.player_id
            """

            cursor = conn.cursor()
            cursor.execute(query, (self.dynasty_id, season, season_type))
            rows = cursor.fetchall()

            player_stats_list = []

            for row in rows:
                # Calculate derived metrics
                passer_rating = None
                if row['passing_attempts'] > 0:
                    passer_rating = calculate_passer_rating(
                        attempts=row['passing_attempts'],
                        completions=row['passing_completions'],
                        yards=row['passing_yards'],
                        touchdowns=row['passing_tds'],
                        interceptions=row['passing_interceptions']
                    )

                yards_per_carry = None
                if row['rushing_attempts'] > 0:
                    yards_per_carry = round(
                        row['rushing_yards'] / row['rushing_attempts'], 2
                    )

                catch_rate = None
                if row['targets'] > 0:
                    catch_rate = round(
                        (row['receptions'] / row['targets']) * 100, 1
                    )

                yards_per_reception = None
                if row['receptions'] > 0:
                    yards_per_reception = round(
                        row['receiving_yards'] / row['receptions'], 2
                    )

                # Create PlayerSeasonStats dataclass
                player_stats = PlayerSeasonStats(
                    dynasty_id=row['dynasty_id'],
                    player_id=row['player_id'],
                    season=season,
                    team_id=row['team_id'],
                    position=row['position'],
                    games_played=row['games_played'],
                    games_started=row['games_started'],
                    passing_yards=row['passing_yards'],
                    passing_tds=row['passing_tds'],
                    passing_completions=row['passing_completions'],
                    passing_attempts=row['passing_attempts'],
                    interceptions=row['passing_interceptions'],
                    rushing_yards=row['rushing_yards'],
                    rushing_tds=row['rushing_tds'],
                    rushing_attempts=row['rushing_attempts'],
                    receiving_yards=row['receiving_yards'],
                    receiving_tds=row['receiving_tds'],
                    receptions=row['receptions'],
                    targets=row['targets'],
                    tackles_total=row['tackles_total'],
                    tackles_solo=row['tackles_solo'],
                    tackles_assist=row['tackles_assist'],
                    sacks=row['sacks'],
                    interceptions_def=row['interceptions_def'],
                    forced_fumbles=row['forced_fumbles'],
                    defensive_tds=row['defensive_tds'],
                    field_goals_made=row['field_goals_made'],
                    field_goals_attempted=row['field_goals_attempted'],
                    extra_points_made=row['extra_points_made'],
                    extra_points_attempted=row['extra_points_attempted'],
                    passer_rating=passer_rating,
                    yards_per_carry=yards_per_carry,
                    catch_rate=catch_rate,
                    yards_per_reception=yards_per_reception,
                    created_at=datetime.now()
                )

                player_stats_list.append(player_stats)

            self.logger.info(
                f"Aggregated {len(player_stats_list)} player season stats for "
                f"dynasty '{self.dynasty_id}', season {season}, type '{season_type}'"
            )

            return player_stats_list

        except sqlite3.Error as e:
            self.logger.error(
                f"Error aggregating player stats for season {season}: {e}",
                exc_info=True
            )
            raise

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

    def create_season_archive(
        self,
        season: int,
        super_bowl_champion: int,
        afc_champion: int,
        nfc_champion: int,
        awards: Optional[Dict[str, str]] = None
    ) -> SeasonArchive:
        """
        Create season archive record with champions and awards.

        Args:
            season: Season year
            super_bowl_champion: Team ID of Super Bowl champion
            afc_champion: Team ID of AFC champion
            nfc_champion: Team ID of NFC champion
            awards: Optional dict of award name → player_id

        Returns:
            SeasonArchive dataclass

        Example:
            awards = {
                "mvp": "QB_KC_001",
                "offensive_poy": "QB_KC_001",
                "defensive_poy": "LB_SF_042",
                "offensive_rookie": "QB_CAR_099",
                "defensive_rookie": "CB_DET_088",
                "comeback_player": "RB_DAL_024"
            }
        """
        awards = awards or {}

        # Extract award winners
        mvp = awards.get("mvp", "")
        opoy = awards.get("offensive_poy", "")
        dpoy = awards.get("defensive_poy", "")
        oroy = awards.get("offensive_rookie")
        droy = awards.get("defensive_rookie")
        comeback = awards.get("comeback_player")

        # Get best team record
        best_record = self._get_best_team_record(season)

        season_archive = SeasonArchive(
            dynasty_id=self.dynasty_id,
            season=season,
            super_bowl_champion=super_bowl_champion,
            afc_champion=afc_champion,
            nfc_champion=nfc_champion,
            mvp_player_id=mvp,
            offensive_poy=opoy,
            defensive_poy=dpoy,
            offensive_rookie_of_year=oroy,
            defensive_rookie_of_year=droy,
            comeback_player=comeback,
            best_record_team_id=best_record.get("team_id"),
            best_record_wins=best_record.get("wins"),
            best_record_losses=best_record.get("losses"),
            games_played=272,  # Standard NFL season
            archived_at=datetime.now()
        )

        self.logger.info(
            f"Created season archive for dynasty '{self.dynasty_id}', season {season}"
        )

        return season_archive

    def _get_best_team_record(self, season: int) -> Dict[str, Any]:
        """
        Get the team with the best record for a season.

        Args:
            season: Season year

        Returns:
            Dict with team_id, wins, losses
        """
        conn = self._get_connection()

        try:
            query = """
            SELECT team_id, wins, losses, ties
            FROM standings
            WHERE dynasty_id = ? AND season = ?
            ORDER BY wins DESC, losses ASC
            LIMIT 1
            """

            cursor = conn.cursor()
            cursor.execute(query, (self.dynasty_id, season))
            row = cursor.fetchone()

            if row:
                return {
                    "team_id": row['team_id'],
                    "wins": row['wins'],
                    "losses": row['losses']
                }

            # Return empty dict if no standings found
            return {}

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching best team record: {e}")
            return {}

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection (either external or create new).

        Returns:
            SQLite connection with row_factory set
        """
        if self.external_conn:
            return self.external_conn

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
