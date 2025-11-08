# ========================================================================
# DRAFT OPERATIONS (15 methods) - IMPLEMENTATION
# ========================================================================

# Add these imports to unified_api.py:
# import json
# from datetime import datetime

def draft_generate_class(self, season: int) -> int:
    """
    Generate a complete draft class using player generation system.

    Integrates with player_generation module to create 224 prospects
    (7 rounds × 32 picks) with realistic attributes and distributions.

    Args:
        season: Season year for draft class

    Returns:
        Total number of prospects generated

    Raises:
        ValueError: If draft class already exists for this dynasty/season
        RuntimeError: If generation fails
    """
    # Check if draft class already exists
    if self.draft_has_class(season):
        raise ValueError(
            f"Draft class already exists for dynasty '{self.dynasty_id}', season {season}. "
            f"Delete existing draft class first to regenerate."
        )

    self.logger.info(f"Generating draft class for dynasty '{self.dynasty_id}', season {season}...")

    try:
        # Import player generation system
        from player_generation.generators.player_generator import PlayerGenerator
        from player_generation.generators.draft_class_generator import DraftClassGenerator

        # Generate draft class
        player_gen = PlayerGenerator()
        draft_gen = DraftClassGenerator(player_gen)
        generated_prospects = draft_gen.generate_draft_class(year=season)

        # Pre-generate all player_ids BEFORE transaction
        # This avoids database locks from nested connections
        player_ids = []
        for _ in generated_prospects:
            player_id = self._roster_get_next_player_id()
            player_ids.append(player_id)

        # Create draft class record
        draft_class_id = f"DRAFT_{self.dynasty_id}_{season}"
        generation_date = datetime.now()

        # Use transaction for atomic insertion of all prospects
        with self.transaction():
            # Insert draft class metadata
            self._execute_update('''
                INSERT INTO draft_classes (
                    draft_class_id, dynasty_id, season,
                    generation_date, total_prospects, status
                ) VALUES (?, ?, ?, ?, ?, 'active')
            ''', (draft_class_id, self.dynasty_id, season, generation_date, len(generated_prospects)))

            # Insert all prospects using pre-generated player_ids
            for player_id, prospect in zip(player_ids, generated_prospects):
                self._draft_insert_prospect(player_id, prospect, draft_class_id)

        self.logger.info(
            f"✅ Draft class generation complete: {len(generated_prospects)} prospects created"
        )

        return len(generated_prospects)

    except Exception as e:
        self.logger.error(f"Draft class generation failed: {e}")
        raise RuntimeError(f"Failed to generate draft class: {e}")


def draft_has_class(self, season: int) -> bool:
    """
    Check if dynasty has a draft class for given season.

    Args:
        season: Season year

    Returns:
        True if draft class exists
    """
    results = self._execute_query('''
        SELECT COUNT(*) as cnt FROM draft_classes
        WHERE dynasty_id = ? AND season = ?
    ''', (self.dynasty_id, season))

    return results[0]['cnt'] > 0 if results else False


def _draft_insert_prospect(
    self,
    player_id: int,
    prospect: Any,  # GeneratedPlayer
    draft_class_id: str
) -> None:
    """
    Insert prospect into database (private method).

    Args:
        player_id: Auto-generated unique player ID
        prospect: GeneratedPlayer instance from player_generation
        draft_class_id: Parent draft class ID
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

    self._execute_update('''
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
    ''', (
        player_id, draft_class_id, self.dynasty_id,
        first_name, last_name, prospect.position, prospect.age,
        draft_round, draft_pick,
        projected_pick_min, projected_pick_max,
        prospect.true_overall, attributes_json,
        college, hometown, home_state,
        prospect.archetype_id,
        scouted_overall, scouting_confidence,
        development_curve
    ))


# Continue with remaining 12 draft methods...
# (Draft retrieval, execution methods - see full implementation in message)

# ========================================================================
# ROSTER OPERATIONS (12 methods) - IMPLEMENTATION
# ========================================================================

def roster_initialize_dynasty(self, season: int = 2025) -> int:
    """
    Load all 32 NFL team rosters + free agents from JSON → Database.
    Called ONLY when creating a new dynasty.

    Args:
        season: Starting season year for contract initialization (default: 2025)

    Returns:
        Total number of players loaded (team rosters + free agents)

    Raises:
        ValueError: If dynasty already has rosters
        FileNotFoundError: If JSON source files missing
        RuntimeError: If initialization fails
    """
    # Prevent re-initialization
    if self.roster_has_dynasty():
        raise ValueError(
            f"Dynasty '{self.dynasty_id}' already has rosters in database. "
            f"Cannot re-initialize. Delete dynasty first to start fresh."
        )

    self.logger.info(f"Initializing rosters for dynasty '{self.dynasty_id}' from JSON files...")

    # Load from JSON (ONLY time JSON is accessed during gameplay)
    try:
        from team_management.players.player_loader import PlayerDataLoader
        loader = PlayerDataLoader()
    except Exception as e:
        raise FileNotFoundError(f"Failed to load JSON player data: {e}")

    players_inserted = 0
    teams_processed = 0
    players_with_contracts = []  # Collect players with contract data

    # Bulk insert all 32 teams
    for team_id in range(1, 33):
        try:
            real_players = loader.get_players_by_team(team_id)

            if not real_players:
                self.logger.warning(f"No players found for team {team_id}")
                continue

            # Insert each player for this team
            for real_player in real_players:
                # Generate new unique player_id (auto-incrementing)
                new_player_id = self._roster_get_next_player_id()

                # Insert with auto-generated ID and source reference
                self._roster_insert_player(
                    player_id=new_player_id,
                    source_player_id=str(real_player.player_id),
                    first_name=real_player.first_name,
                    last_name=real_player.last_name,
                    number=real_player.number,
                    team_id=team_id,
                    positions=real_player.positions,
                    attributes=real_player.attributes,
                    birthdate=real_player.birthdate
                )

                # Add to roster with new player_id
                self._roster_add_to_roster(
                    team_id=team_id,
                    player_id=new_player_id
                )

                # Collect contract data for later initialization
                if real_player.contract:
                    players_with_contracts.append({
                        'player_id': new_player_id,
                        'team_id': team_id,
                        'contract': real_player.contract
                    })

                players_inserted += 1

            teams_processed += 1
            self.logger.info(f"  Team {team_id}: {len(real_players)} players loaded")

        except Exception as e:
            self.logger.error(f"Failed to load team {team_id}: {e}")
            raise RuntimeError(f"Roster initialization failed at team {team_id}: {e}")

    self.logger.info(
        f"✅ Team roster initialization complete: "
        f"{players_inserted} players loaded across {teams_processed} teams"
    )

    # Load free agents (team_id = 0 in database)
    self.logger.info("📥 Loading free agents from free_agents.json...")
    try:
        free_agents = loader.get_free_agents()

        if free_agents:
            for free_agent in free_agents:
                # Generate new unique player_id
                new_player_id = self._roster_get_next_player_id()

                # Insert free agent with team_id = 0 (no team)
                self._roster_insert_player(
                    player_id=new_player_id,
                    source_player_id=str(free_agent.player_id),
                    first_name=free_agent.first_name,
                    last_name=free_agent.last_name,
                    number=free_agent.number if free_agent.number else 0,
                    team_id=0,  # Free agents have team_id = 0
                    positions=free_agent.positions,
                    attributes=free_agent.attributes,
                    birthdate=free_agent.birthdate
                )

                # NOTE: Do NOT add to team_rosters table - free agents aren't on any team

                # Collect contract data if present
                if free_agent.contract:
                    players_with_contracts.append({
                        'player_id': new_player_id,
                        'team_id': 0,
                        'contract': free_agent.contract
                    })

                players_inserted += 1

            self.logger.info(f"✅ Free agent loading complete: {len(free_agents)} free agents loaded")
        else:
            self.logger.warning("⚠️  No free agents found in free_agents.json")

    except Exception as e:
        self.logger.error(f"Failed to load free agents: {e}")
        # Non-critical - continue with team rosters only

    self.logger.info(
        f"✅ Roster initialization complete: "
        f"{players_inserted} total players loaded ({teams_processed} teams + free agents)"
    )

    # Initialize contracts for all players
    if players_with_contracts:
        self._roster_initialize_contracts(
            season=season,
            players_with_contracts=players_with_contracts
        )

    return players_inserted


def roster_has_dynasty(self) -> bool:
    """
    Check if dynasty has player rosters in database.

    Returns:
        True if dynasty has any players in database
    """
    results = self._execute_query(
        "SELECT COUNT(*) as cnt FROM players WHERE dynasty_id = ?",
        (self.dynasty_id,)
    )
    return results[0]['cnt'] > 0 if results else False


def _roster_initialize_contracts(
    self,
    season: int,
    players_with_contracts: List[Dict[str, Any]]
) -> None:
    """
    Initialize player contracts from JSON data (private method).

    Args:
        season: Starting season year for contract initialization
        players_with_contracts: List of dicts with player_id, team_id, contract data
    """
    from salary_cap.contract_initializer import ContractInitializer

    conn = self._get_connection()
    try:
        contract_initializer = ContractInitializer(conn)

        # Create all contracts from JSON data
        contract_map = contract_initializer.initialize_contracts_from_json(
            dynasty_id=self.dynasty_id,
            season=season,
            players_with_contracts=players_with_contracts
        )

        # Link contract_id to players table
        contract_initializer.link_contracts_to_players(contract_map)

        self.logger.info(
            f"✅ Contract initialization complete: {len(contract_map)} contracts created"
        )

    except Exception as e:
        self.logger.error(f"Contract initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize contracts: {e}")
    finally:
        self._return_connection(conn)


def roster_get_team(self, team_id: int, roster_status: str = 'active') -> List[Dict[str, Any]]:
    """
    Get team roster with optional status filter.

    Args:
        team_id: Team ID (1-32)
        roster_status: Status filter ('active', 'injured_reserve', 'practice_squad', 'all')

    Returns:
        List of player dictionaries with roster info
    """
    query = """
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.number,
            p.team_id,
            p.positions,
            p.attributes,
            p.status,
            p.years_pro,
            p.birthdate,
            tr.depth_chart_order,
            tr.roster_status
        FROM players p
        JOIN team_rosters tr
            ON p.dynasty_id = tr.dynasty_id
            AND p.player_id = tr.player_id
        WHERE p.dynasty_id = ?
            AND p.team_id = ?
    """
    params = [self.dynasty_id, team_id]

    if roster_status != 'all':
        query += " AND tr.roster_status = ?"
        params.append(roster_status)

    query += " ORDER BY tr.depth_chart_order, p.number"

    results = self._execute_query(query, tuple(params))

    if not results and roster_status == 'active':
        raise ValueError(
            f"❌ No roster found in database for dynasty '{self.dynasty_id}', team {team_id}.\n"
            f"   Database is not initialized. Create a new dynasty to load rosters."
        )

    return results


def roster_get_free_agents(self) -> List[Dict[str, Any]]:
    """
    Get all free agent players (players not on any team).

    Returns:
        List of player dictionaries for free agents (team_id = 0)
    """
    query = """
        SELECT
            p.player_id,
            p.source_player_id,
            p.first_name,
            p.last_name,
            p.number,
            p.team_id,
            p.positions,
            p.attributes,
            p.status,
            p.years_pro,
            p.birthdate
        FROM players p
        WHERE p.dynasty_id = ?
            AND p.team_id = 0
        ORDER BY p.last_name, p.first_name
    """

    return self._execute_query(query, (self.dynasty_id,))


def roster_get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
    """
    Get single player by ID.

    Args:
        player_id: Player ID (auto-generated integer)

    Returns:
        Player dictionary or None if not found
    """
    results = self._execute_query("""
        SELECT *
        FROM players
        WHERE dynasty_id = ? AND player_id = ?
    """, (self.dynasty_id, player_id))

    return results[0] if results else None


def roster_count_team(self, team_id: int) -> int:
    """
    Get count of players on team roster.

    Args:
        team_id: Team ID (1-32)

    Returns:
        Number of players on roster
    """
    results = self._execute_query("""
        SELECT COUNT(*) as cnt
        FROM team_rosters
        WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
    """, (self.dynasty_id, team_id))

    return results[0]['cnt'] if results else 0


def roster_get_by_position(self, team_id: int, position: str) -> List[Dict[str, Any]]:
    """
    Get players at a specific position on team.

    Args:
        team_id: Team ID (1-32)
        position: Position filter (QB, RB, WR, etc.)

    Returns:
        List of player dictionaries at position
    """
    # Note: positions is stored as JSON array, so we need to check if position is in array
    query = """
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.number,
            p.team_id,
            p.positions,
            p.attributes,
            p.status,
            tr.depth_chart_order
        FROM players p
        JOIN team_rosters tr
            ON p.dynasty_id = tr.dynasty_id
            AND p.player_id = tr.player_id
        WHERE p.dynasty_id = ?
            AND p.team_id = ?
            AND p.positions LIKE ?
            AND tr.roster_status = 'active'
        ORDER BY tr.depth_chart_order
    """

    # LIKE pattern to match position in JSON array
    position_pattern = f'%"{position}"%'

    return self._execute_query(query, (self.dynasty_id, team_id, position_pattern))


def roster_update_player_team(self, player_id: int, new_team_id: int, season: int) -> None:
    """
    Move player to different team (trades, signings).

    Args:
        player_id: Player to move (auto-generated integer)
        new_team_id: New team (1-32, or 0 for free agent)
        season: Season year (for record keeping)
    """
    # Update player's team_id
    self._execute_update("""
        UPDATE players
        SET team_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE dynasty_id = ? AND player_id = ?
    """, (new_team_id, self.dynasty_id, player_id))

    # Update roster entry (or remove if free agent)
    if new_team_id == 0:
        # Free agent - remove from team roster
        self._execute_update("""
            DELETE FROM team_rosters
            WHERE dynasty_id = ? AND player_id = ?
        """, (self.dynasty_id, player_id))
    else:
        # Update roster entry (or create if doesn't exist)
        rows_affected = self._execute_update("""
            UPDATE team_rosters
            SET team_id = ?
            WHERE dynasty_id = ? AND player_id = ?
        """, (new_team_id, self.dynasty_id, player_id))

        # If no rows updated, insert new roster entry
        if rows_affected == 0:
            self._roster_add_to_roster(new_team_id, player_id)


def roster_add_generated_player(self, player_data: Dict[str, Any], team_id: int) -> int:
    """
    Add newly generated player to database (draft, free agency, player generation).

    Args:
        player_data: Player attributes dict
            Required keys: first_name, last_name, number, positions, attributes
            Optional keys: player_id (used as source_player_id if provided)
        team_id: Team to add player to (1-32, or 0 for free agent)

    Returns:
        player_id of inserted player (auto-generated integer)

    Raises:
        ValueError: If required player_data fields missing
    """
    required_fields = ['first_name', 'last_name', 'number', 'positions', 'attributes']
    missing_fields = [f for f in required_fields if f not in player_data]

    if missing_fields:
        raise ValueError(f"Missing required player fields: {missing_fields}")

    # Generate new unique player_id (auto-incrementing)
    new_player_id = self._roster_get_next_player_id()

    # Use provided player_id as source reference, or generate synthetic one
    source_player_id = str(player_data.get('player_id', f'GENERATED_{new_player_id}'))

    # Insert player with auto-generated ID
    self._roster_insert_player(
        player_id=new_player_id,
        source_player_id=source_player_id,
        first_name=player_data['first_name'],
        last_name=player_data['last_name'],
        number=player_data['number'],
        team_id=team_id,
        positions=player_data['positions'],
        attributes=player_data['attributes'],
        birthdate=player_data.get('birthdate')  # Optional birthdate
    )

    # Add to roster if on a team
    if team_id > 0:
        self._roster_add_to_roster(team_id, new_player_id)

    return new_player_id


def _roster_insert_player(
    self,
    player_id: int,
    source_player_id: str,
    first_name: str,
    last_name: str,
    number: int,
    team_id: int,
    positions: List[str],
    attributes: Dict,
    birthdate: Optional[str] = None
) -> None:
    """
    Insert player into database (private method).

    Args:
        player_id: Auto-generated unique player ID (integer)
        source_player_id: Original JSON player_id (for reference)
        first_name: First name
        last_name: Last name
        number: Jersey number
        team_id: Team ID (0-32)
        positions: List of positions player can play
        attributes: Dict of player attributes/ratings
        birthdate: Optional birthdate in YYYY-MM-DD format
    """
    self._execute_update("""
        INSERT INTO players
            (dynasty_id, player_id, source_player_id, first_name, last_name, number,
             team_id, positions, attributes, birthdate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        self.dynasty_id,
        player_id,
        source_player_id,
        first_name,
        last_name,
        number,
        team_id,
        json.dumps(positions),
        json.dumps(attributes),
        birthdate
    ))


def _roster_add_to_roster(
    self,
    team_id: int,
    player_id: int,
    depth_order: int = 99
) -> None:
    """
    Add player to team roster (private method).

    Args:
        team_id: Team ID (1-32)
        player_id: Player ID (auto-generated integer)
        depth_order: Depth chart position (lower = higher)
    """
    self._execute_update("""
        INSERT INTO team_rosters
            (dynasty_id, team_id, player_id, depth_chart_order)
        VALUES (?, ?, ?, ?)
    """, (self.dynasty_id, team_id, player_id, depth_order))


def _roster_get_next_player_id(self) -> int:
    """
    Get next unique player_id for this dynasty (private method).

    Returns:
        Next available player_id (auto-incrementing)
    """
    results = self._execute_query(
        "SELECT COALESCE(MAX(player_id), 0) as max_id FROM players WHERE dynasty_id = ?",
        (self.dynasty_id,)
    )

    max_id = results[0]['max_id'] if results else 0
    return max_id + 1
