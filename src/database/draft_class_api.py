"""
Draft Class Database API

Manages draft class generation, prospect storage, and draft execution in database.

Features:
- Dynasty-aware draft class generation
- Prospect storage and retrieval
- Draft execution (marking prospects as drafted)
- Prospect-to-player conversion
- Draft history tracking

Architecture:
- Integrates with PlayerRosterAPI for unified ID generation
- Uses player_generation system for draft class generation
- Respects dynasty isolation for all operations
- IMPORTANT: convert_prospect_to_player uses SAME player_id (no conversion)
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import date, datetime
from pathlib import Path
import logging


class DraftClassAPI:
    """
    Database API for draft class system.

    Handles all database operations for draft classes and prospects including
    generation, retrieval, draft execution, and prospect conversion.

    Features:
    - Dynasty isolation for all operations
    - Integration with player generation system
    - Unified player ID management via PlayerRosterAPI
    - Transaction support for draft execution
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Draft Class Database API.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Import PlayerRosterAPI for unified ID generation
        from database.player_roster_api import PlayerRosterAPI
        self.player_api = PlayerRosterAPI(database_path)

        # Ensure schema exists
        self._ensure_schema_exists()

    def _ensure_schema_exists(self) -> None:
        """Ensure draft class tables exist."""
        migration_path = Path(__file__).parent / "migrations" / "add_draft_tables.sql"

        if not migration_path.exists():
            self.logger.warning(f"Migration file not found: {migration_path}")
            return

        try:
            with sqlite3.connect(self.database_path, timeout=30.0) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Check if tables exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='draft_classes'"
                )
                if cursor.fetchone() is None:
                    # Run migration
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    conn.executescript(migration_sql)
                    conn.commit()
                    self.logger.info("Draft class schema initialized successfully")
        except Exception as e:
            self.logger.error(f"Error ensuring schema exists: {e}")
            raise

    # ========================================================================
    # GENERATION METHODS
    # ========================================================================

    def generate_draft_class(self, dynasty_id: str, season: int) -> int:
        """
        Generate a complete draft class using player generation system.

        Integrates with player_generation module to create 224 prospects
        (7 rounds × 32 picks) with realistic attributes and distributions.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year for draft class

        Returns:
            Total number of prospects generated

        Raises:
            ValueError: If draft class already exists for this dynasty/season
            RuntimeError: If generation fails
        """
        # Check if draft class already exists
        if self.dynasty_has_draft_class(dynasty_id, season):
            raise ValueError(
                f"Draft class already exists for dynasty '{dynasty_id}', season {season}. "
                f"Delete existing draft class first to regenerate."
            )

        self.logger.info(f"Generating draft class for dynasty '{dynasty_id}', season {season}...")

        try:
            # Import player generation system
            from player_generation.generators.player_generator import PlayerGenerator
            from player_generation.generators.draft_class_generator import DraftClassGenerator

            # Generate draft class
            player_gen = PlayerGenerator()
            draft_gen = DraftClassGenerator(player_gen)
            generated_prospects = draft_gen.generate_draft_class(year=season)

            # Pre-generate all player_ids BEFORE opening database connection
            # This avoids database locks from nested connections
            player_ids = []
            for _ in generated_prospects:
                player_id = self.player_api._get_next_player_id(dynasty_id)
                player_ids.append(player_id)

            # Create draft class record
            draft_class_id = f"DRAFT_{dynasty_id}_{season}"
            generation_date = datetime.now()

            with sqlite3.connect(self.database_path, timeout=30.0) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Insert draft class metadata
                conn.execute('''
                    INSERT INTO draft_classes (
                        draft_class_id, dynasty_id, season,
                        generation_date, total_prospects, status
                    ) VALUES (?, ?, ?, ?, ?, 'active')
                ''', (draft_class_id, dynasty_id, season, generation_date, len(generated_prospects)))

                # Insert all prospects using pre-generated player_ids
                for player_id, prospect in zip(player_ids, generated_prospects):
                    # Insert prospect
                    self._insert_prospect(player_id, prospect, draft_class_id, dynasty_id, conn)

                conn.commit()

            self.logger.info(
                f"✅ Draft class generation complete: {len(generated_prospects)} prospects created"
            )

            return len(generated_prospects)

        except Exception as e:
            self.logger.error(f"Draft class generation failed: {e}")
            raise RuntimeError(f"Failed to generate draft class: {e}")

    def dynasty_has_draft_class(self, dynasty_id: str, season: int) -> bool:
        """
        Check if dynasty has a draft class for given season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if draft class exists
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM draft_classes
                WHERE dynasty_id = ? AND season = ?
            ''', (dynasty_id, season))
            count = cursor.fetchone()[0]
            return count > 0

    def _insert_prospect(
        self,
        player_id: int,
        prospect: Any,  # GeneratedPlayer
        draft_class_id: str,
        dynasty_id: str,
        conn: Optional[sqlite3.Connection] = None
    ) -> None:
        """
        Insert prospect into database (private method).

        Args:
            player_id: Auto-generated unique player ID
            prospect: GeneratedPlayer instance from player_generation
            draft_class_id: Parent draft class ID
            dynasty_id: Dynasty identifier
            conn: Optional database connection (for transaction mode)
        """
        # Extract first name and last name from prospect.name
        name_parts = prospect.name.split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else "Unknown"
        last_name = name_parts[1] if len(name_parts) > 1 else "Prospect"

        # Serialize attributes
        attributes_json = json.dumps(prospect.true_ratings)

        # Extract background info (if available)
        college = prospect.background.college if prospect.background else "Unknown College"
        hometown = prospect.background.hometown if prospect.background else None
        home_state = prospect.background.home_state if prospect.background else None

        # Calculate projected pick range (based on draft position ± variance)
        draft_round = prospect.draft_round or 1
        draft_pick = prospect.draft_pick or 1
        overall_pick = (draft_round - 1) * 32 + draft_pick
        projected_pick_min = max(1, overall_pick - 15)
        projected_pick_max = min(224, overall_pick + 15)

        # Scouting data
        scouted_overall = prospect.scouted_overall if prospect.scouted_overall > 0 else None
        scouting_confidence = "medium"  # Default
        if prospect.scouting_report:
            scouting_confidence = prospect.scouting_report.confidence

        # Development curve
        development_curve = "normal"  # Default
        if prospect.development:
            development_curve = prospect.development.development_curve

        query = '''
            INSERT INTO draft_prospects (
                player_id, draft_class_id, dynasty_id,
                first_name, last_name, position, age,
                draft_round, draft_pick,
                projected_pick_min, projected_pick_max,
                overall, attributes,
                college, hometown, home_state,
                archetype_id,
                scouted_overall, scouting_confidence,
                development_curve
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        params = (
            player_id, draft_class_id, dynasty_id,
            first_name, last_name, prospect.position, prospect.age,
            draft_round, draft_pick,
            projected_pick_min, projected_pick_max,
            prospect.true_overall, attributes_json,
            college, hometown, home_state,
            prospect.archetype_id,
            scouted_overall, scouting_confidence,
            development_curve
        )

        if conn:
            conn.execute(query, params)
        else:
            with sqlite3.connect(self.database_path, timeout=30.0) as new_conn:
                new_conn.execute(query, params)
                new_conn.commit()

    # ========================================================================
    # RETRIEVAL METHODS
    # ========================================================================

    def get_draft_class_info(
        self,
        dynasty_id: str,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get draft class metadata.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Draft class info dict or None if not found
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM draft_classes
                WHERE dynasty_id = ? AND season = ?
            ''', (dynasty_id, season))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_prospects(
        self,
        dynasty_id: str,
        season: int,
        available_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all prospects in a draft class.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            available_only: Only return undrafted prospects (default True)

        Returns:
            List of prospect dicts sorted by projected overall pick
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM draft_prospects
                WHERE draft_class_id = ?
            '''
            params = [draft_class_id]

            if available_only:
                query += " AND is_drafted = FALSE"

            query += " ORDER BY overall DESC, draft_pick ASC"

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Parse JSON attributes
            for prospect in results:
                prospect['attributes'] = json.loads(prospect['attributes'])

            return results

    def get_prospects_by_position(
        self,
        dynasty_id: str,
        season: int,
        position: str,
        available_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get prospects filtered by position.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            position: Position filter (QB, RB, WR, etc.)
            available_only: Only return undrafted prospects (default True)

        Returns:
            List of prospect dicts sorted by overall rating
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM draft_prospects
                WHERE draft_class_id = ? AND position = ?
            '''
            params = [draft_class_id, position]

            if available_only:
                query += " AND is_drafted = FALSE"

            query += " ORDER BY overall DESC"

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Parse JSON attributes
            for prospect in results:
                prospect['attributes'] = json.loads(prospect['attributes'])

            return results

    def get_prospect_by_id(
        self,
        player_id: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single prospect by player ID.

        Args:
            player_id: Player ID
            dynasty_id: Dynasty identifier

        Returns:
            Prospect dict or None if not found
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM draft_prospects
                WHERE player_id = ? AND dynasty_id = ?
            ''', (player_id, dynasty_id))
            row = cursor.fetchone()

            if row:
                prospect = dict(row)
                prospect['attributes'] = json.loads(prospect['attributes'])
                return prospect

            return None

    def get_top_prospects(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 100,
        position: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top prospects by overall rating.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Maximum number of prospects to return (default 100)
            position: Optional position filter

        Returns:
            List of top prospect dicts sorted by overall rating
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            query = '''
                SELECT * FROM draft_prospects
                WHERE draft_class_id = ? AND is_drafted = FALSE
            '''
            params = [draft_class_id]

            if position:
                query += " AND position = ?"
                params.append(position)

            query += " ORDER BY overall DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Parse JSON attributes
            for prospect in results:
                prospect['attributes'] = json.loads(prospect['attributes'])

            return results

    def get_prospect_history(
        self,
        player_id: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get prospect's draft history (for drafted players).

        Returns prospect data including draft information, useful for
        tracking which team drafted a player and when.

        Args:
            player_id: Player ID
            dynasty_id: Dynasty identifier

        Returns:
            Prospect dict with draft history or None if not found
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT
                    dp.*,
                    dc.season,
                    dc.generation_date
                FROM draft_prospects dp
                JOIN draft_classes dc
                    ON dp.draft_class_id = dc.draft_class_id
                WHERE dp.player_id = ? AND dp.dynasty_id = ?
            ''', (player_id, dynasty_id))
            row = cursor.fetchone()

            if row:
                prospect = dict(row)
                prospect['attributes'] = json.loads(prospect['attributes'])
                return prospect

            return None

    # ========================================================================
    # DRAFT EXECUTION METHODS
    # ========================================================================

    def mark_prospect_drafted(
        self,
        player_id: int,
        team_id: int,
        actual_round: int,
        actual_pick: int,
        dynasty_id: str
    ) -> None:
        """
        Mark prospect as drafted (without converting to player yet).

        Updates prospect record with draft information. Call
        convert_prospect_to_player() to add player to team roster.

        Args:
            player_id: Player ID
            team_id: Team that drafted the player
            actual_round: Actual draft round (1-7)
            actual_pick: Actual pick number within round (1-32)
            dynasty_id: Dynasty identifier
        """
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.execute('''
                UPDATE draft_prospects
                SET
                    is_drafted = TRUE,
                    drafted_by_team_id = ?,
                    drafted_round = ?,
                    drafted_pick = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ? AND dynasty_id = ?
            ''', (team_id, actual_round, actual_pick, player_id, dynasty_id))
            conn.commit()

    def convert_prospect_to_player(
        self,
        player_id: int,
        team_id: int,
        dynasty_id: str,
        jersey_number: Optional[int] = None
    ) -> int:
        """
        Convert drafted prospect to active player on team roster.

        IMPORTANT: Uses SAME player_id (no ID conversion). The prospect's
        player_id becomes the player's player_id in the players table.

        Args:
            player_id: Player ID (same ID used in draft_prospects)
            team_id: Team ID (1-32)
            dynasty_id: Dynasty identifier
            jersey_number: Optional jersey number (auto-assigned if None)

        Returns:
            player_id of created player (same as input player_id)

        Raises:
            ValueError: If prospect not found or not drafted
        """
        # Get prospect data
        prospect = self.get_prospect_by_id(player_id, dynasty_id)

        if not prospect:
            raise ValueError(f"Prospect {player_id} not found in dynasty '{dynasty_id}'")

        if not prospect['is_drafted']:
            raise ValueError(f"Prospect {player_id} has not been drafted yet")

        # Auto-assign jersey number if not provided
        if jersey_number is None:
            # Simple auto-assignment based on position
            position = prospect['position']
            if position == 'QB':
                jersey_number = 10
            elif position in ['RB', 'FB']:
                jersey_number = 30
            elif position in ['WR', 'TE']:
                jersey_number = 80
            elif position in ['OT', 'OG', 'C']:
                jersey_number = 70
            elif position in ['DT', 'DE', 'EDGE']:
                jersey_number = 90
            elif position in ['LB']:
                jersey_number = 50
            elif position in ['CB', 'S']:
                jersey_number = 20
            else:
                jersey_number = 99

        # Parse positions (single position from draft becomes list)
        positions = [prospect['position']]

        # Create player record using PlayerRosterAPI
        # IMPORTANT: We pass player_id directly to maintain same ID
        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Insert player with SAME player_id
            self.player_api._insert_player(
                dynasty_id=dynasty_id,
                player_id=player_id,  # Use same ID!
                source_player_id=f"DRAFT_{prospect['draft_class_id']}_{player_id}",
                first_name=prospect['first_name'],
                last_name=prospect['last_name'],
                number=jersey_number,
                team_id=team_id,
                positions=positions,
                attributes=prospect['attributes'],
                birthdate=None  # Calculate from age if needed
            )

            # Add to roster
            self.player_api._add_to_roster(
                dynasty_id=dynasty_id,
                team_id=team_id,
                player_id=player_id,
                depth_order=99  # Rookies start at bottom of depth chart
            )

            conn.commit()

        self.logger.info(
            f"Converted prospect {player_id} to player for team {team_id} "
            f"(jersey #{jersey_number})"
        )

        return player_id

    def complete_draft_class(
        self,
        dynasty_id: str,
        season: int
    ) -> None:
        """
        Mark draft class as completed.

        Updates draft class status to 'completed' after all draft picks
        have been made.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.execute('''
                UPDATE draft_classes
                SET status = 'completed'
                WHERE draft_class_id = ?
            ''', (draft_class_id,))
            conn.commit()

        self.logger.info(f"Draft class {draft_class_id} marked as completed")

    def delete_draft_class(
        self,
        dynasty_id: str,
        season: int
    ) -> None:
        """
        Delete draft class and all prospects.

        Cascading delete removes all prospects associated with draft class.
        Use with caution - this cannot be undone.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with sqlite3.connect(self.database_path, timeout=30.0) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Delete draft class (cascades to prospects)
            conn.execute('''
                DELETE FROM draft_classes
                WHERE draft_class_id = ?
            ''', (draft_class_id,))

            conn.commit()

        self.logger.info(
            f"Deleted draft class {draft_class_id} and all associated prospects"
        )
