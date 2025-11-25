-- Migration: Fix vw_team_cap_summary view to include cap_id column
-- Date: 2025-11-23
-- Purpose: Add missing cap_id column to view for proper initialization error handling
-- Related: Draft initialization requires cap_id for duplicate detection
-- Root Cause: initialize_team_cap() returns existing.get('cap_id', 0) which was always 0

-- Drop existing view
DROP VIEW IF EXISTS vw_team_cap_summary;

-- Recreate view with cap_id column
CREATE VIEW vw_team_cap_summary AS
SELECT
    tsc.cap_id,                     -- PRIMARY KEY (was missing!)
    tsc.team_id,
    tsc.season,
    tsc.dynasty_id,
    tsc.salary_cap_limit,
    tsc.carryover_from_previous,
    (tsc.salary_cap_limit + tsc.carryover_from_previous) as total_cap_available,
    tsc.active_contracts_total,
    tsc.dead_money_total,
    tsc.ltbe_incentives_total,
    tsc.practice_squad_total,
    tsc.top_51_total,
    (tsc.active_contracts_total + tsc.dead_money_total + tsc.ltbe_incentives_total + tsc.practice_squad_total) as total_cap_used,
    (tsc.salary_cap_limit + tsc.carryover_from_previous - tsc.active_contracts_total - tsc.dead_money_total - tsc.ltbe_incentives_total - tsc.practice_squad_total) as cap_space_available,
    tsc.is_top_51_active,
    tsc.cash_spent_this_year
FROM team_salary_cap tsc;

-- Verification query:
-- SELECT cap_id, team_id, season, dynasty_id, cap_space_available FROM vw_team_cap_summary WHERE dynasty_id='your_dynasty' ORDER BY team_id;
