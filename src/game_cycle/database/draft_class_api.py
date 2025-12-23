"""
Game Cycle Draft Class Database API.

Manages draft prospects and draft execution for the game_cycle.db database.
Uses the game_cycle draft_prospects schema (prospect_id, drafted_team_id, draft_round, draft_pick).

This is the SINGLE SOURCE OF TRUTH for game cycle draft class database operations.
"""

import sqlite3
import json
import random
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from pathlib import Path
import logging

from constants.position_abbreviations import get_full_position_name


class DraftClassAPI:
    """
    Game cycle draft class database API.

    Handles draft prospects storage, retrieval, and conversion to players
    for the game_cycle.db database.

    Key differences from legacy API:
    - Uses prospect_id (not player_id) as primary key
    - Uses drafted_team_id (not drafted_by_team_id)
    - Uses draft_round (not drafted_round)
    - Uses draft_pick (not drafted_pick)
    """

    def __init__(self, database_path: str):
        """
        Initialize Draft Class API.

        Args:
            database_path: Path to SQLite database file (game_cycle.db)
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.database_path, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_prospect_by_id(
        self,
        prospect_id: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single prospect by prospect ID.

        Args:
            prospect_id: Prospect ID (from draft_prospects.prospect_id)
            dynasty_id: Dynasty identifier

        Returns:
            Prospect dict or None if not found

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> prospect = api.get_prospect_by_id(12345, "my_dynasty")
            >>> if prospect:
            ...     print(f"{prospect['first_name']} {prospect['last_name']}")
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM draft_prospects
                WHERE prospect_id = ? AND dynasty_id = ?
            ''', (prospect_id, dynasty_id))
            row = cursor.fetchone()

            if row:
                prospect = dict(row)
                # Parse JSON attributes if present
                if prospect.get('attributes'):
                    try:
                        prospect['attributes'] = json.loads(prospect['attributes'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return prospect

            return None

    def mark_prospect_drafted(
        self,
        player_id: int,  # Note: This is prospect_id, but parameter name kept for compatibility
        team_id: int,
        actual_round: int,
        actual_pick: int,
        dynasty_id: str
    ) -> None:
        """
        Mark prospect as drafted.

        Updates prospect record with draft information. Call
        convert_prospect_to_player() to add player to team roster.

        Args:
            player_id: Prospect ID (note: parameter name is player_id for compatibility)
            team_id: Team that drafted the prospect (1-32)
            actual_round: Actual draft round (1-7)
            actual_pick: Actual pick number within round (1-32)
            dynasty_id: Dynasty identifier

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> api.mark_prospect_drafted(
            ...     player_id=12345,
            ...     team_id=22,
            ...     actual_round=1,
            ...     actual_pick=15,
            ...     dynasty_id="my_dynasty"
            ... )
        """
        with self._get_connection() as conn:
            # Calculate overall pick number
            overall_pick = (actual_round - 1) * 32 + actual_pick

            # Use game_cycle schema column names
            conn.execute('''
                UPDATE draft_prospects
                SET
                    is_drafted = TRUE,
                    drafted_team_id = ?,
                    draft_round = ?,
                    draft_pick = ?,
                    draft_overall_pick = ?
                WHERE prospect_id = ? AND dynasty_id = ?
            ''', (team_id, actual_round, actual_pick, overall_pick, player_id, dynasty_id))
            conn.commit()

            self.logger.info(
                f"Marked prospect {player_id} as drafted by team {team_id} "
                f"(Round {actual_round}, Pick {actual_pick}, Overall {overall_pick})"
            )

    def convert_prospect_to_player(
        self,
        player_id: int,  # Note: This is prospect_id, but parameter name kept for compatibility
        team_id: int,
        dynasty_id: str,
        jersey_number: Optional[int] = None
    ) -> int:
        """
        Convert drafted prospect to active player on team roster.

        IMPORTANT: This method generates a NEW player_id for the players table.
        The prospect_id is temporary and is NOT used in the players table.

        Args:
            player_id: Prospect ID (note: parameter name is player_id for compatibility)
            team_id: Team that drafted the prospect (1-32)
            dynasty_id: Dynasty identifier
            jersey_number: Optional jersey number (auto-assigned if None)

        Returns:
            int: NEW player_id assigned from players table (different from prospect_id)

        Raises:
            ValueError: If prospect not found or not drafted

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> new_player_id = api.convert_prospect_to_player(
            ...     player_id=12345,
            ...     team_id=22,
            ...     dynasty_id="my_dynasty"
            ... )
            >>> print(f"Prospect 12345 is now player {new_player_id}")
        """
        # Get prospect data
        prospect = self.get_prospect_by_id(player_id, dynasty_id)

        if not prospect:
            raise ValueError(f"Prospect {player_id} not found in dynasty '{dynasty_id}'")

        if not prospect['is_drafted']:
            raise ValueError(f"Prospect {player_id} has not been drafted yet")

        # Generate NEW player_id from players table sequence
        # This prevents ID collisions with existing roster players
        new_player_id = self._get_next_player_id(dynasty_id)

        self.logger.info(
            f"Converting prospect {player_id} → new player {new_player_id} "
            f"for team {team_id} in dynasty '{dynasty_id}'"
        )

        # Auto-assign jersey number if not provided
        if jersey_number is None:
            jersey_number = self._auto_assign_jersey(prospect['position'])

        # Parse attributes
        attributes = prospect.get('attributes', {})
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except (json.JSONDecodeError, TypeError):
                attributes = {}

        # Calculate birthdate from prospect age
        birthdate = self._calculate_birthdate(prospect)

        # Prepare positions as JSON array (game_cycle schema uses JSON array)
        # Convert abbreviated position (e.g., "QB") to full name (e.g., "quarterback")
        # to match the format used by existing roster players and depth chart system
        full_position = get_full_position_name(prospect['position'])
        positions_json = json.dumps([full_position])  # ["quarterback"] not ["QB"]

        # Prepare complete attributes JSON including physical stats
        # (game_cycle stores age, overall, potential, height, weight in attributes)
        full_attributes = {
            'overall': prospect.get('overall', 50),
            'potential': prospect.get('potential', prospect.get('overall', 50)),
            'age': prospect.get('age', 21),
            'height_inches': prospect.get('height_inches'),
            'weight_lbs': prospect.get('weight_lbs'),
        }

        # Merge with existing attributes from prospect
        if isinstance(attributes, dict):
            full_attributes.update(attributes)

        attributes_json = json.dumps(full_attributes)

        # Insert into players table with game_cycle schema
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO players (
                    dynasty_id, player_id, source_player_id,
                    first_name, last_name, number, team_id,
                    positions, attributes, contract_id,
                    status, years_pro, birthdate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dynasty_id,
                new_player_id,
                None,  # source_player_id (NULL for drafted rookies)
                prospect['first_name'],
                prospect['last_name'],
                jersey_number,  # game_cycle uses 'number' not 'jersey_number'
                team_id,
                positions_json,  # JSON array: ["QB"]
                attributes_json,  # All physical stats in JSON
                None,  # contract_id (contracts created separately)
                'active',  # status
                0,  # years_pro (rookie)
                birthdate
            ))

            # Insert into team_rosters to make player visible on roster
            # Use INSERT OR IGNORE to prevent duplicates if method called multiple times
            conn.execute('''
                INSERT OR IGNORE INTO team_rosters (
                    dynasty_id, team_id, player_id, roster_status, depth_chart_order
                ) VALUES (?, ?, ?, 'active', 99)
            ''', (dynasty_id, team_id, new_player_id))

            # Update prospect with roster_player_id and player_id links
            conn.execute('''
                UPDATE draft_prospects
                SET roster_player_id = ?, player_id = ?
                WHERE prospect_id = ? AND dynasty_id = ?
            ''', (new_player_id, new_player_id, player_id, dynasty_id))

            conn.commit()

        self.logger.info(
            f"Added player {new_player_id} ({prospect['first_name']} {prospect['last_name']}) "
            f"to team {team_id} roster"
        )

        return new_player_id

    def _get_next_player_id(self, dynasty_id: str) -> int:
        """
        Generate next available player_id for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Next available player_id
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT COALESCE(MAX(player_id), 0) + 1 AS next_id
                FROM players
                WHERE dynasty_id = ?
            ''', (dynasty_id,))
            row = cursor.fetchone()
            return row[0] if row else 1

    def _auto_assign_jersey(self, position: str) -> int:
        """
        Auto-assign jersey number based on position.

        Args:
            position: Player position

        Returns:
            Jersey number (0-99)
        """
        # Simple auto-assignment based on position
        if position == 'QB':
            return 10
        elif position in ['RB', 'FB']:
            return 30
        elif position in ['WR', 'TE']:
            return 80
        elif position in ['OT', 'OG', 'C', 'LT', 'LG', 'RT', 'RG']:
            return 70
        elif position in ['DT', 'DE', 'EDGE', 'LE', 'RE']:
            return 90
        elif position in ['LB', 'MLB', 'LOLB', 'ROLB']:
            return 50
        elif position in ['CB', 'S', 'FS', 'SS']:
            return 20
        elif position in ['K', 'P']:
            return 4
        else:
            return 99

    def _calculate_birthdate(self, prospect: Dict[str, Any]) -> str:
        """
        Calculate birthdate from prospect age and draft year.

        Args:
            prospect: Prospect dict with age and draft_class_id

        Returns:
            Birthdate string in YYYY-MM-DD format

        Raises:
            ValueError: If age or draft year cannot be determined
        """
        prospect_age = prospect.get('age')
        if prospect_age is None:
            raise ValueError(
                f"Prospect {prospect.get('prospect_id')} has no age set. Cannot calculate birthdate."
            )

        draft_class_id = prospect.get('draft_class_id')
        if not draft_class_id:
            raise ValueError(
                f"Prospect {prospect.get('prospect_id')} has no draft_class_id. "
                "Cannot determine draft year."
            )

        try:
            # draft_class_id format: "DRAFT_{dynasty_id}_{season}"
            draft_year = int(draft_class_id.split('_')[-1])
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Cannot parse draft year from draft_class_id '{draft_class_id}': {e}"
            )

        # Birth year = draft year - age
        # Example: 22-year-old drafted in 2025 was born in 2003
        birth_year = draft_year - prospect_age

        # Randomize month/day for realism
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)  # Use 28 to avoid invalid dates
        birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

        self.logger.debug(
            f"Calculated birthdate for {prospect['first_name']} {prospect['last_name']}: "
            f"age {prospect_age} in {draft_year} → born {birthdate}"
        )

        return birthdate

    def find_prospect_by_name(
        self,
        dynasty_id: str,
        season: int,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a prospect by name (for resolving owner wishlists).

        Performs fuzzy matching: searches first_name + last_name or last_name only.
        Returns first matching prospect (best match by overall if multiple).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year (draft class year)
            name: Full name ("John Doe") or last name ("Doe")

        Returns:
            Prospect dict or None if not found

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> prospect = api.find_prospect_by_name("my_dynasty", 2025, "John Smith")
            >>> if prospect:
            ...     print(f"Found: {prospect['first_name']} {prospect['last_name']}")
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        # Parse name into parts
        name_parts = name.strip().split()

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row

            # Try exact full name match first (first + last)
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])  # Handle multi-word last names

                cursor = conn.execute('''
                    SELECT * FROM draft_prospects
                    WHERE draft_class_id = ?
                    AND LOWER(first_name) = LOWER(?)
                    AND LOWER(last_name) = LOWER(?)
                    AND is_drafted = FALSE
                    ORDER BY overall DESC
                    LIMIT 1
                ''', (draft_class_id, first_name, last_name))

                row = cursor.fetchone()
                if row:
                    prospect = dict(row)
                    # Parse JSON attributes if present
                    if prospect.get('attributes'):
                        try:
                            prospect['attributes'] = json.loads(prospect['attributes'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    return prospect

            # Try last name only match (single word or full string)
            last_name_search = name_parts[-1] if name_parts else name
            cursor = conn.execute('''
                SELECT * FROM draft_prospects
                WHERE draft_class_id = ?
                AND LOWER(last_name) = LOWER(?)
                AND is_drafted = FALSE
                ORDER BY overall DESC
                LIMIT 1
            ''', (draft_class_id, last_name_search))

            row = cursor.fetchone()
            if row:
                prospect = dict(row)
                # Parse JSON attributes if present
                if prospect.get('attributes'):
                    try:
                        prospect['attributes'] = json.loads(prospect['attributes'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return prospect

            # Try partial match on last name (LIKE search)
            cursor = conn.execute('''
                SELECT * FROM draft_prospects
                WHERE draft_class_id = ?
                AND LOWER(last_name) LIKE LOWER(?)
                AND is_drafted = FALSE
                ORDER BY overall DESC
                LIMIT 1
            ''', (draft_class_id, f"%{last_name_search}%"))

            row = cursor.fetchone()
            if row:
                prospect = dict(row)
                # Parse JSON attributes if present
                if prospect.get('attributes'):
                    try:
                        prospect['attributes'] = json.loads(prospect['attributes'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return prospect

            return None

    def dynasty_has_draft_class(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Check if dynasty has a draft class for given season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional shared connection for transaction participation

        Returns:
            True if draft class exists

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> if api.dynasty_has_draft_class("my_dynasty", 2025):
            ...     print("Draft class exists!")
        """
        should_close = connection is None
        if connection is None:
            connection = self._get_connection()

        try:
            cursor = connection.execute('''
                SELECT COUNT(*) FROM draft_classes
                WHERE dynasty_id = ? AND season = ?
            ''', (dynasty_id, season))
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            if should_close and connection:
                connection.close()

    def get_draft_prospects_count(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Get total count of draft prospects in a draft class.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional shared connection for transaction participation

        Returns:
            Number of prospects in draft class (0 if draft class doesn't exist)

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> count = api.get_draft_prospects_count("my_dynasty", 2025)
            >>> print(f"Draft class has {count} prospects")
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        query = '''
            SELECT COUNT(*) as count
            FROM draft_prospects
            WHERE draft_class_id = ?
        '''

        if connection:
            cursor = connection.execute(query, (draft_class_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        else:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (draft_class_id,))
                result = cursor.fetchone()
                return result[0] if result else 0

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

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> prospects = api.get_all_prospects("my_dynasty", 2025)
            >>> for p in prospects[:10]:
            ...     print(f"{p['first_name']} {p['last_name']} - {p['position']} ({p['overall']} OVR)")
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with self._get_connection() as conn:
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
                if prospect.get('attributes'):
                    try:
                        prospect['attributes'] = json.loads(prospect['attributes'])
                    except (json.JSONDecodeError, TypeError):
                        pass

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

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> qbs = api.get_prospects_by_position("my_dynasty", 2025, "QB")
            >>> print(f"Top QB: {qbs[0]['first_name']} {qbs[0]['last_name']}")
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        with self._get_connection() as conn:
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
                if prospect.get('attributes'):
                    try:
                        prospect['attributes'] = json.loads(prospect['attributes'])
                    except (json.JSONDecodeError, TypeError):
                        pass

            return results

    def generate_draft_class(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Generate a complete draft class using player generation system.

        Integrates with player_generation module to create 224 prospects
        (7 rounds × 32 picks) with realistic attributes and distributions.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year for draft class
            connection: Optional shared connection for transaction participation.
                       If provided, uses shared connection (caller manages commit).
                       If None, creates own connection and auto-commits.

        Returns:
            Total number of prospects generated

        Raises:
            ValueError: If draft class already exists for this dynasty/season
            RuntimeError: If generation fails

        Examples:
            >>> api = DraftClassAPI("data/database/game_cycle/game_cycle.db")
            >>> count = api.generate_draft_class("my_dynasty", 2025)
            >>> print(f"Generated {count} prospects")
        """
        # Check if draft class already exists
        if self.dynasty_has_draft_class(dynasty_id, season, connection=connection):
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

            # Create draft class record
            draft_class_id = f"DRAFT_{dynasty_id}_{season}"
            generation_date = datetime.now()

            # Use provided connection OR create own
            should_close = connection is None
            if connection is None:
                connection = self._get_connection()
                self.logger.debug("Using auto-commit mode (own connection)")
            else:
                self.logger.debug("Using transaction mode (shared connection)")

            try:
                # Insert draft class metadata
                connection.execute('''
                    INSERT INTO draft_classes (
                        draft_class_id, dynasty_id, season,
                        generation_date, total_prospects, status
                    ) VALUES (?, ?, ?, ?, ?, 'active')
                ''', (draft_class_id, dynasty_id, season, generation_date, len(generated_prospects)))

                # Insert all prospects
                for prospect in generated_prospects:
                    self._insert_prospect(prospect, draft_class_id, dynasty_id, connection)

                # Only commit if we created the connection (auto-commit mode)
                if should_close:
                    connection.commit()
                    self.logger.debug("Auto-committed transaction")

                self.logger.info(
                    f"✅ Draft class generation complete: {len(generated_prospects)} prospects created"
                )

                return len(generated_prospects)

            finally:
                if should_close and connection:
                    connection.close()

        except Exception as e:
            self.logger.error(f"Draft class generation failed: {e}")
            raise RuntimeError(f"Failed to generate draft class: {e}")

    def _insert_prospect(
        self,
        prospect: Any,  # GeneratedPlayer from player_generation
        draft_class_id: str,
        dynasty_id: str,
        conn: sqlite3.Connection
    ) -> None:
        """
        Insert prospect into database (private helper method).

        Args:
            prospect: GeneratedPlayer instance from player_generation
            draft_class_id: Parent draft class ID
            dynasty_id: Dynasty identifier
            conn: Database connection (transaction mode)
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

        # Calculate projected pick range
        draft_round = prospect.draft_round or 1
        draft_pick = prospect.draft_pick or 1
        overall_pick = (draft_round - 1) * 32 + draft_pick
        projected_pick_min = max(1, overall_pick - 15)
        projected_pick_max = min(224, overall_pick + 15)

        # Scouting data
        scouted_overall = prospect.scouted_overall if prospect.scouted_overall > 0 else None
        scouting_confidence = "medium"
        if prospect.scouting_report:
            scouting_confidence = prospect.scouting_report.confidence

        # Development curve
        development_curve = "normal"
        if prospect.development:
            development_curve = prospect.development.development_curve

        query = '''
            INSERT INTO draft_prospects (
                draft_class_id, dynasty_id,
                first_name, last_name, position, age,
                draft_round, draft_pick,
                projected_pick_min, projected_pick_max,
                overall, attributes,
                college, hometown, home_state,
                archetype_id,
                scouted_overall, scouting_confidence,
                development_curve
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        params = (
            draft_class_id, dynasty_id,
            first_name, last_name, prospect.position, prospect.age,
            draft_round, draft_pick,
            projected_pick_min, projected_pick_max,
            prospect.true_overall, attributes_json,
            college, hometown, home_state,
            prospect.archetype_id,
            scouted_overall, scouting_confidence,
            development_curve
        )

        conn.execute(query, params)

    def generate_udfa_prospects(
        self,
        dynasty_id: str,
        season: int,
        count: int = 300
    ) -> int:
        """
        Generate additional undrafted free agent prospects.

        Creates lower-rated prospects that weren't selected in the draft.
        These become the UDFA pool for teams to sign to fill 90-man rosters.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            count: Number of UDFA prospects to generate (default 300)

        Returns:
            Number of UDFA prospects created

        Note:
            - UDFAs have overall ratings typically 50-70 (lower than drafted players)
            - UDFAs have draft_round=0 and draft_pick=0 to distinguish them
            - Should be called after the draft is complete
        """
        draft_class_id = f"DRAFT_{dynasty_id}_{season}"

        # Verify draft class exists
        if not self.dynasty_has_draft_class(dynasty_id, season):
            self.logger.warning(f"No draft class found for {dynasty_id}/{season}")
            return 0

        self.logger.info(f"Generating {count} UDFA prospects for {dynasty_id}/{season}...")

        try:
            import random
            from player_generation.generators.player_generator import PlayerGenerator
            from player_generation.core.generation_context import GenerationConfig, GenerationContext

            player_gen = PlayerGenerator()

            # UDFA position distribution (more depth positions)
            udfa_positions = [
                "QB", "RB", "WR", "WR", "WR", "TE", "TE",
                "OT", "OG", "OG", "C",
                "EDGE", "DT", "DT", "LB", "LB", "LB",
                "CB", "CB", "S", "S",
                "K", "P", "LS"
            ]

            conn = self._get_connection()
            try:
                created = 0
                for i in range(count):
                    # Pick random position
                    position = udfa_positions[i % len(udfa_positions)]

                    # Generate UDFA-caliber prospect (lower ratings)
                    # Random age between 21-24 for UDFAs
                    udfa_age = random.randint(21, 24)

                    config = GenerationConfig(
                        context=GenerationContext.UDFA,
                        position=position,
                        overall_min=50,  # UDFA caliber - lower floor
                        overall_max=70,  # UDFA caliber - lower ceiling
                        age=udfa_age,
                    )

                    try:
                        prospect = player_gen.generate_player(config)
                    except Exception as gen_err:
                        self.logger.debug(f"Failed to generate UDFA prospect: {gen_err}")
                        continue

                    # Insert UDFA prospect with round=0, pick=0
                    name_parts = prospect.name.split(maxsplit=1)
                    first_name = name_parts[0] if len(name_parts) > 0 else "Unknown"
                    last_name = name_parts[1] if len(name_parts) > 1 else "Prospect"

                    attributes_json = json.dumps(prospect.true_ratings)
                    college = prospect.background.college if prospect.background else "Unknown College"
                    hometown = prospect.background.hometown if prospect.background else None
                    home_state = prospect.background.home_state if prospect.background else None

                    development_curve = "normal"
                    if prospect.development:
                        development_curve = prospect.development.development_curve

                    conn.execute('''
                        INSERT INTO draft_prospects (
                            draft_class_id, dynasty_id,
                            first_name, last_name, position, age,
                            draft_round, draft_pick,
                            projected_pick_min, projected_pick_max,
                            overall, attributes,
                            college, hometown, home_state,
                            archetype_id,
                            scouted_overall, scouting_confidence,
                            development_curve
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        draft_class_id, dynasty_id,
                        first_name, last_name, position, prospect.age,
                        0, 0,  # draft_round=0, draft_pick=0 marks as UDFA
                        225, 999,  # projected pick range (undrafted)
                        prospect.true_overall, attributes_json,
                        college, hometown, home_state,
                        prospect.archetype_id,
                        None, "low",  # scouted_overall, confidence
                        development_curve
                    ))
                    created += 1

                conn.commit()
                self.logger.info(f"✅ Generated {created} UDFA prospects")
                return created

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"UDFA generation failed: {e}")
            return 0
