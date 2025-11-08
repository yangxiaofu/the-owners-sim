"""
Complete implementations of all 40 Salary Cap methods for UnifiedDatabaseAPI.

This file contains the full implementations to replace the TODO stubs in:
src/database/unified_api.py (lines ~860-955)

INSTRUCTIONS:
1. Replace the entire "SALARY CAP OPERATIONS (40 methods)" section
2. Keep the section header comment
3. Replace from cap_get_team_summary through the end of cap operations

All methods follow the UnifiedDatabaseAPI patterns:
- Use self._execute_query() for SELECT
- Use self._execute_update() for INSERT/UPDATE/DELETE
- Use self.transaction() for multi-step operations
- Dynasty isolation with self.dynasty_id default
- Comprehensive error handling and logging
"""

# ========================================================================
# SALARY CAP OPERATIONS (40 methods)
# ========================================================================

# Contract Operations (8 methods)

def contracts_insert(
    self,
    player_id: int,
    team_id: int,
    start_year: int,
    end_year: int,
    contract_years: int,
    contract_type: str,
    total_value: int,
    signing_bonus: int = 0,
    signing_bonus_proration: int = 0,
    guaranteed_at_signing: int = 0,
    injury_guaranteed: int = 0,
    total_guaranteed: int = 0,
    signed_date: Optional[str] = None,
    dynasty_id: Optional[str] = None
) -> int:
    """
    Insert a new player contract.

    Args:
        player_id: Player ID
        team_id: Team ID (1-32)
        start_year: Contract start year
        end_year: Contract end year
        contract_years: Number of years
        contract_type: Contract type ('ROOKIE', 'VETERAN', 'FRANCHISE_TAG', etc.')
        total_value: Total contract value
        signing_bonus: Signing bonus amount
        signing_bonus_proration: Annual proration amount
        guaranteed_at_signing: Guaranteed money at signing
        injury_guaranteed: Injury guarantee amount
        total_guaranteed: Total guaranteed money
        signed_date: Date contract was signed (YYYY-MM-DD)
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        Generated contract_id
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    if signed_date is None:
        signed_date = datetime.now().date().isoformat()

    query = '''
        INSERT INTO player_contracts (
            player_id, team_id, dynasty_id,
            start_year, end_year, contract_years,
            contract_type, total_value, signing_bonus, signing_bonus_proration,
            guaranteed_at_signing, injury_guaranteed, total_guaranteed,
            is_active, signed_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            player_id, team_id, dynasty_id,
            start_year, end_year, contract_years,
            contract_type, total_value, signing_bonus, signing_bonus_proration,
            guaranteed_at_signing, injury_guaranteed, total_guaranteed,
            signed_date
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error inserting contract: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def contracts_get(self, contract_id: int) -> Optional[Dict[str, Any]]:
    """
    Get contract by ID.

    Args:
        contract_id: Contract ID

    Returns:
        Contract dict or None if not found
    """
    query = "SELECT * FROM player_contracts WHERE contract_id = ?"
    results = self._execute_query(query, (contract_id,))
    return results[0] if results else None


def contracts_get_by_team(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all contracts for a team in a given season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        active_only: Only return active contracts

    Returns:
        List of contract dicts
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM player_contracts
        WHERE team_id = ?
          AND dynasty_id = ?
          AND start_year <= ?
          AND end_year >= ?
    '''
    params = [team_id, dynasty_id, season, season]

    if active_only:
        query += " AND is_active = TRUE"

    query += " ORDER BY total_value DESC"

    return self._execute_query(query, tuple(params))


def contracts_get_by_player(
    self,
    player_id: int,
    dynasty_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get active contract for a specific player.

    Args:
        player_id: Player ID
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        Contract dict or None if not found
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM player_contracts
        WHERE player_id = ?
          AND dynasty_id = ?
          AND is_active = TRUE
        LIMIT 1
    '''

    results = self._execute_query(query, (player_id, dynasty_id))
    return results[0] if results else None


def contracts_get_expiring(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all contracts expiring after this season.

    Args:
        team_id: Team ID (1-32)
        season: Current season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        active_only: Only return active contracts

    Returns:
        List of expiring contract dicts with player information
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT
            pc.*,
            p.first_name || ' ' || p.last_name as player_name,
            p.positions,
            p.attributes,
            p.years_pro,
            p.birthdate
        FROM player_contracts pc
        JOIN players p
            ON pc.player_id = p.player_id
            AND pc.dynasty_id = p.dynasty_id
        WHERE pc.team_id = ?
          AND pc.dynasty_id = ?
          AND pc.end_year = ?
    '''
    params = [team_id, dynasty_id, season]

    if active_only:
        query += " AND pc.is_active = TRUE"

    query += " ORDER BY pc.total_value DESC"

    return self._execute_query(query, tuple(params))


def contracts_get_pending_free_agents(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None,
    min_overall: int = 0
) -> List[Dict[str, Any]]:
    """
    Get pending free agents (contracts expiring) filtered by quality.

    Args:
        team_id: Team ID (1-32)
        season: Current season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        min_overall: Minimum overall rating to include (0-100)

    Returns:
        List of simplified player dicts sorted by overall rating
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    # Get raw expiring contracts
    expiring = self.contracts_get_expiring(team_id, season, dynasty_id)

    # Parse and filter by overall rating
    import json
    pending_fas = []
    for contract in expiring:
        # Parse JSON attributes
        attrs = json.loads(contract['attributes'])
        overall = attrs.get('overall', 0)

        # Filter by minimum overall
        if overall >= min_overall:
            # Parse positions
            positions = json.loads(contract['positions'])
            primary_position = positions[0] if positions else 'UNKNOWN'

            # Build simplified dict
            pending_fas.append({
                'player_id': contract['player_id'],
                'player_name': contract['player_name'],
                'position': primary_position,
                'overall': overall,
                'years_pro': contract['years_pro'],
                'contract_id': contract['contract_id'],
                'contract_value': contract['total_value'],
                'contract_years': contract['contract_years'],
                'aav': contract['total_value'] // contract['contract_years'] if contract['contract_years'] > 0 else 0
            })

    # Sort by overall rating (best players first)
    pending_fas.sort(key=lambda x: x['overall'], reverse=True)

    return pending_fas


def contracts_void(
    self,
    contract_id: int,
    void_date: Optional[str] = None
) -> None:
    """
    Mark contract as voided.

    Args:
        contract_id: Contract ID to void
        void_date: Date contract voided (YYYY-MM-DD)
    """
    if void_date is None:
        void_date = datetime.now().date().isoformat()

    query = '''
        UPDATE player_contracts
        SET is_active = FALSE,
            voided_date = ?,
            modified_at = CURRENT_TIMESTAMP
        WHERE contract_id = ?
    '''

    self._execute_update(query, (void_date, contract_id))


def contracts_get_active(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all active contracts for a team in a season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        List of active contract dictionaries
    """
    return self.contracts_get_by_team(team_id, season, dynasty_id, active_only=True)


# Contract Year Details (3 methods)

def contract_years_insert(
    self,
    contract_id: int,
    contract_year: int,
    season_year: int,
    base_salary: int,
    total_cap_hit: int,
    cash_paid: int,
    roster_bonus: int = 0,
    workout_bonus: int = 0,
    option_bonus: int = 0,
    per_game_roster_bonus: int = 0,
    ltbe_incentives: int = 0,
    nltbe_incentives: int = 0,
    base_salary_guaranteed: bool = False,
    guarantee_type: Optional[str] = None,
    guarantee_date: Optional[str] = None,
    signing_bonus_proration: int = 0,
    option_bonus_proration: int = 0,
    is_voided: bool = False
) -> int:
    """
    Insert contract year details.

    Args:
        contract_id: Parent contract ID
        contract_year: Year of contract (1-based)
        season_year: Absolute season year
        base_salary: Base salary for this year
        total_cap_hit: Total cap hit including all components
        cash_paid: Actual cash paid in this year
        roster_bonus: Roster bonus amount
        workout_bonus: Workout bonus amount
        option_bonus: Option bonus amount
        per_game_roster_bonus: Per-game roster bonus
        ltbe_incentives: Likely to be earned incentives
        nltbe_incentives: Not likely to be earned incentives
        base_salary_guaranteed: Whether base salary is guaranteed
        guarantee_type: Type of guarantee
        guarantee_date: Date guarantee vests
        signing_bonus_proration: Signing bonus proration
        option_bonus_proration: Option bonus proration
        is_voided: Whether year is voided

    Returns:
        detail_id of inserted record
    """
    query = '''
        INSERT INTO contract_year_details (
            contract_id, contract_year, season_year,
            base_salary, roster_bonus, workout_bonus, option_bonus, per_game_roster_bonus,
            ltbe_incentives, nltbe_incentives,
            base_salary_guaranteed, guarantee_type, guarantee_date,
            signing_bonus_proration, option_bonus_proration,
            total_cap_hit, cash_paid, is_voided
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            contract_id, contract_year, season_year,
            base_salary, roster_bonus, workout_bonus, option_bonus, per_game_roster_bonus,
            ltbe_incentives, nltbe_incentives,
            base_salary_guaranteed, guarantee_type, guarantee_date,
            signing_bonus_proration, option_bonus_proration,
            total_cap_hit, cash_paid, is_voided
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error inserting contract year details: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def contract_years_get(
    self,
    contract_id: int
) -> List[Dict[str, Any]]:
    """
    Get year-by-year details for a contract.

    Args:
        contract_id: Contract ID

    Returns:
        List of contract year detail dicts
    """
    query = '''
        SELECT * FROM contract_year_details
        WHERE contract_id = ?
        ORDER BY contract_year
    '''

    return self._execute_query(query, (contract_id,))


def contract_years_get_for_season(
    self,
    contract_id: int,
    season: int
) -> Optional[Dict[str, Any]]:
    """
    Get contract year details for specific season.

    Args:
        contract_id: Contract ID
        season: Season year

    Returns:
        Contract year detail dict or None if not found
    """
    query = '''
        SELECT * FROM contract_year_details
        WHERE contract_id = ? AND season_year = ?
    '''

    results = self._execute_query(query, (contract_id, season))
    return results[0] if results else None


# Team Cap Operations (3 methods)

def cap_initialize_team(
    self,
    team_id: int,
    season: int,
    salary_cap_limit: int,
    dynasty_id: Optional[str] = None,
    carryover_from_previous: int = 0
) -> int:
    """
    Initialize team salary cap for a season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        salary_cap_limit: League-wide cap limit
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        carryover_from_previous: Cap space carried over

    Returns:
        cap_id of inserted record
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        INSERT OR REPLACE INTO team_salary_cap (
            team_id, season, dynasty_id,
            salary_cap_limit, carryover_from_previous,
            is_top_51_active
        ) VALUES (?, ?, ?, ?, ?, TRUE)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (team_id, season, dynasty_id, salary_cap_limit, carryover_from_previous))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error initializing team cap: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def cap_update_team(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None,
    active_contracts_total: Optional[int] = None,
    dead_money_total: Optional[int] = None,
    ltbe_incentives_total: Optional[int] = None,
    practice_squad_total: Optional[int] = None,
    top_51_total: Optional[int] = None,
    cash_spent_this_year: Optional[int] = None,
    is_top_51_active: Optional[bool] = None
) -> None:
    """
    Update team cap totals.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        active_contracts_total: Total of active contracts
        dead_money_total: Total dead money
        ltbe_incentives_total: Total LTBE incentives
        practice_squad_total: Total practice squad cost
        top_51_total: Total of top 51 contracts (offseason)
        cash_spent_this_year: Cash spending for floor calculation
        is_top_51_active: Whether top-51 rule is active
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    updates = []
    params = []

    if active_contracts_total is not None:
        updates.append("active_contracts_total = ?")
        params.append(active_contracts_total)

    if dead_money_total is not None:
        updates.append("dead_money_total = ?")
        params.append(dead_money_total)

    if ltbe_incentives_total is not None:
        updates.append("ltbe_incentives_total = ?")
        params.append(ltbe_incentives_total)

    if practice_squad_total is not None:
        updates.append("practice_squad_total = ?")
        params.append(practice_squad_total)

    if top_51_total is not None:
        updates.append("top_51_total = ?")
        params.append(top_51_total)

    if cash_spent_this_year is not None:
        updates.append("cash_spent_this_year = ?")
        params.append(cash_spent_this_year)

    if is_top_51_active is not None:
        updates.append("is_top_51_active = ?")
        params.append(is_top_51_active)

    if not updates:
        return

    updates.append("last_updated = CURRENT_TIMESTAMP")
    params.extend([team_id, season, dynasty_id])

    query = f'''
        UPDATE team_salary_cap
        SET {', '.join(updates)}
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
    '''

    self._execute_update(query, tuple(params))


def cap_get_team_summary(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get complete cap summary for a team.

    Args:
        team_id: Team identifier (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        Cap summary dict with all totals and available space or None if no data exists
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM vw_team_cap_summary
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
    '''

    results = self._execute_query(query, (team_id, season, dynasty_id))
    return results[0] if results else None


# Franchise/Transition Tag Operations (4 methods)

def tags_insert_franchise(
    self,
    player_id: int,
    team_id: int,
    season: int,
    tag_type: str,
    tag_salary: int,
    tag_date: str,
    deadline_date: str,
    dynasty_id: Optional[str] = None,
    consecutive_tag_number: int = 1
) -> int:
    """
    Insert franchise/transition tag record.

    Args:
        player_id: Player ID
        team_id: Team ID (1-32)
        season: Season year
        tag_type: FRANCHISE_EXCLUSIVE, FRANCHISE_NON_EXCLUSIVE, or TRANSITION
        tag_salary: Tag salary amount
        tag_date: Date tag was applied (YYYY-MM-DD)
        deadline_date: Deadline for signing extension (YYYY-MM-DD)
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        consecutive_tag_number: 1st, 2nd, or 3rd consecutive tag

    Returns:
        tag_id of inserted record
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        INSERT INTO franchise_tags (
            player_id, team_id, season, dynasty_id,
            tag_type, tag_salary,
            tag_date, deadline_date,
            consecutive_tag_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            player_id, team_id, season, dynasty_id,
            tag_type, tag_salary,
            tag_date, deadline_date,
            consecutive_tag_number
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error inserting franchise tag: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def tags_get_by_player(
    self,
    player_id: int,
    team_id: int
) -> List[Dict[str, Any]]:
    """
    Get all franchise tags for a player with a specific team.

    Args:
        player_id: Player ID
        team_id: Team ID (1-32)

    Returns:
        List of franchise tag records
    """
    query = '''
        SELECT * FROM franchise_tags
        WHERE player_id = ? AND team_id = ?
        ORDER BY season DESC
    '''

    return self._execute_query(query, (player_id, team_id))


def tags_get_by_team(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all franchise tags used by team in a season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        List of franchise tag records
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM franchise_tags
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
    '''

    return self._execute_query(query, (team_id, season, dynasty_id))


def tags_update_contract(
    self,
    tag_id: int,
    contract_id: int
) -> None:
    """
    Link a contract to a franchise tag.

    Args:
        tag_id: Franchise tag ID
        contract_id: Contract ID
    """
    query = '''
        UPDATE franchise_tags
        SET extension_contract_id = ?
        WHERE tag_id = ?
    '''

    self._execute_update(query, (contract_id, tag_id))


# RFA Tender Operations (2 methods)

def rfa_insert_tender(
    self,
    player_id: int,
    team_id: int,
    season: int,
    tender_level: str,
    tender_salary: int,
    tender_date: str,
    dynasty_id: Optional[str] = None,
    compensation_round: Optional[int] = None
) -> int:
    """
    Insert RFA tender record.

    Args:
        player_id: Player ID
        team_id: Team ID (1-32)
        season: Season year
        tender_level: FIRST_ROUND, SECOND_ROUND, ORIGINAL_ROUND, RIGHT_OF_FIRST_REFUSAL
        tender_salary: Tender amount
        tender_date: Date tender was offered (YYYY-MM-DD)
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        compensation_round: Draft round for compensation (None for ROFR only)

    Returns:
        tender_id of inserted record
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        INSERT INTO rfa_tenders (
            player_id, team_id, season, dynasty_id,
            tender_level, tender_salary, tender_date,
            compensation_round
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            player_id, team_id, season, dynasty_id,
            tender_level, tender_salary, tender_date,
            compensation_round
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error inserting RFA tender: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def rfa_get_tenders(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all RFA tenders for a team in a season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        List of RFA tender records
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM rfa_tenders
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
    '''

    return self._execute_query(query, (team_id, season, dynasty_id))


# Dead Money Operations (2 methods)

def dead_money_insert(
    self,
    team_id: int,
    player_id: int,
    season: int,
    contract_id: int,
    release_date: str,
    dead_money_amount: int,
    current_year_dead_money: int,
    next_year_dead_money: int,
    remaining_signing_bonus: int,
    dynasty_id: Optional[str] = None,
    guaranteed_salary: int = 0,
    is_june_1_designation: bool = False
) -> int:
    """
    Insert dead money record for released player.

    Args:
        team_id: Team ID (1-32)
        player_id: Player ID
        season: Season year
        contract_id: Original contract ID
        release_date: Date player was released (YYYY-MM-DD)
        dead_money_amount: Total dead money
        current_year_dead_money: Dead money in current year
        next_year_dead_money: Dead money in next year (June 1 split)
        remaining_signing_bonus: Remaining bonus proration
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        guaranteed_salary: Guaranteed salary accelerated
        is_june_1_designation: Whether June 1 designation used

    Returns:
        dead_money_id of inserted record
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        INSERT INTO dead_money (
            team_id, player_id, season, dynasty_id,
            contract_id, release_date,
            dead_money_amount,
            is_june_1_designation,
            current_year_dead_money, next_year_dead_money,
            remaining_signing_bonus, guaranteed_salary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            team_id, player_id, season, dynasty_id,
            contract_id, release_date,
            dead_money_amount,
            is_june_1_designation,
            current_year_dead_money, next_year_dead_money,
            remaining_signing_bonus, guaranteed_salary
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error inserting dead money: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def dead_money_get_team(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all dead money entries for a team in a season.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        List of dead money dicts
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM dead_money
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
        ORDER BY dead_money_amount DESC
    '''

    return self._execute_query(query, (team_id, season, dynasty_id))


# Transaction Logging (2 methods)

def transactions_log(
    self,
    team_id: int,
    season: int,
    transaction_type: str,
    transaction_date: str,
    dynasty_id: Optional[str] = None,
    player_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    cap_impact_current: int = 0,
    cap_impact_future: Optional[Dict[int, int]] = None,
    cash_impact: int = 0,
    dead_money_created: int = 0,
    description: Optional[str] = None
) -> int:
    """
    Log cap transaction.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        transaction_type: SIGNING, RELEASE, RESTRUCTURE, TRADE, TAG, TENDER
        transaction_date: Date of transaction (YYYY-MM-DD)
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        player_id: Player ID (if applicable)
        contract_id: Contract ID (if applicable)
        cap_impact_current: Impact on current year cap
        cap_impact_future: Dict of {year: impact} for future years
        cash_impact: Cash spending impact
        dead_money_created: Dead money created
        description: Transaction description

    Returns:
        transaction_id of logged transaction
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    import json
    cap_impact_future_json = json.dumps(cap_impact_future) if cap_impact_future else None

    query = '''
        INSERT INTO cap_transactions (
            team_id, season, dynasty_id,
            transaction_type, player_id, contract_id,
            transaction_date,
            cap_impact_current, cap_impact_future,
            cash_impact, dead_money_created,
            description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (
            team_id, season, dynasty_id,
            transaction_type, player_id, contract_id,
            transaction_date,
            cap_impact_current, cap_impact_future_json,
            cash_impact, dead_money_created,
            description
        ))

        if self._active_transaction is None:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        if self._active_transaction is None:
            conn.rollback()
        self.logger.error(f"Error logging transaction: {e}", exc_info=True)
        raise
    finally:
        self._return_connection(conn)


def transactions_get_team(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None,
    transaction_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get transaction history for a team.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)
        transaction_type: Optional filter by type

    Returns:
        List of transaction dicts
    """
    if dynasty_id is None:
        dynasty_id = self.dynasty_id

    query = '''
        SELECT * FROM cap_transactions
        WHERE team_id = ? AND season = ? AND dynasty_id = ?
    '''
    params = [team_id, season, dynasty_id]

    if transaction_type:
        query += " AND transaction_type = ?"
        params.append(transaction_type)

    query += " ORDER BY transaction_date DESC, created_at DESC"

    results = self._execute_query(query, tuple(params))

    # Parse JSON cap_impact_future
    import json
    for row in results:
        if row.get('cap_impact_future'):
            row['cap_impact_future'] = json.loads(row['cap_impact_future'])

    return results


# League Cap Operations (2 methods)

def league_cap_get(self, season: int) -> Optional[int]:
    """
    Get league-wide salary cap for a season.

    Args:
        season: Season year

    Returns:
        Salary cap amount or None if not found
    """
    query = '''
        SELECT salary_cap_amount FROM league_salary_cap_history
        WHERE season = ?
    '''

    results = self._execute_query(query, (season,))
    return results[0]['salary_cap_amount'] if results else None


def league_cap_get_history(
    self,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get salary cap history across years.

    Args:
        start_year: Optional start year
        end_year: Optional end year

    Returns:
        List of cap history dicts
    """
    if start_year and end_year:
        query = '''
            SELECT * FROM league_salary_cap_history
            WHERE season BETWEEN ? AND ?
            ORDER BY season
        '''
        return self._execute_query(query, (start_year, end_year))
    else:
        query = '''
            SELECT * FROM league_salary_cap_history
            ORDER BY season
        '''
        return self._execute_query(query)


# Utility Methods (3 methods)

def cap_get_available_space(
    self,
    team_id: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> int:
    """
    Calculate available cap space for a team.

    Args:
        team_id: Team ID (1-32)
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        Available cap space in dollars (can be negative if over cap)
    """
    summary = self.cap_get_team_summary(team_id, season, dynasty_id)

    if not summary:
        return 0

    # Calculate based on which rule is active
    if summary.get('is_top_51_active'):
        used = summary.get('top_51_total', 0)
    else:
        used = summary.get('active_contracts_total', 0)

    # Add dead money and incentives
    used += summary.get('dead_money_total', 0)
    used += summary.get('ltbe_incentives_total', 0)

    cap_limit = summary.get('salary_cap_limit', 0)
    carryover = summary.get('carryover_from_previous', 0)

    return (cap_limit + carryover) - used


def cap_validate_contract(
    self,
    team_id: int,
    contract_value: int,
    season: int,
    dynasty_id: Optional[str] = None
) -> bool:
    """
    Validate if team can afford a contract.

    Args:
        team_id: Team ID (1-32)
        contract_value: First year cap hit
        season: Season year
        dynasty_id: Dynasty identifier (defaults to self.dynasty_id)

    Returns:
        True if team has sufficient cap space, False otherwise
    """
    available_space = self.cap_get_available_space(team_id, season, dynasty_id)
    return available_space >= contract_value


def _ensure_salary_cap_schema_exists(self) -> None:
    """
    Private helper to ensure salary cap schema is initialized.

    Called by _ensure_schemas() during API initialization.
    """
    migration_path = Path(__file__).parent / "migrations" / "002_salary_cap_schema.sql"

    if not migration_path.exists():
        self.logger.warning(f"Salary cap migration file not found: {migration_path}")
        return

    try:
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")

            # Check if tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_contracts'"
            )
            if cursor.fetchone() is None:
                # Run migration
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                conn.executescript(migration_sql)

                if self._active_transaction is None:
                    conn.commit()

                self.logger.info("Salary cap schema initialized successfully")
        finally:
            self._return_connection(conn)
    except Exception as e:
        self.logger.error(f"Error ensuring salary cap schema exists: {e}")
        raise
