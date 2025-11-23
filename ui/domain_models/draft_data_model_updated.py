"""
Draft Data Model - Domain Model for Draft UI (WITH EDGE CASE HANDLING)

This is an updated version with comprehensive edge case handling.
Replace the get_draft_order() method in draft_data_model.py with this implementation.
"""

def get_draft_order(self, round_number: Optional[int] = None) -> Dict[str, Any]:
    """
    Get draft order for specific round or all rounds WITH EDGE CASE HANDLING.

    EDGE CASES HANDLED:
    -------------------
    1. Missing standings: Returns empty picks with error message
    2. Incomplete playoffs: Returns partial draft order (non-playoff teams only)
    3. Missing schedule data: Uses SOS = 0.500 for all teams as default
    4. Database errors: Returns empty picks with error message logged
    5. Invalid playoff results: Gracefully handles inconsistent data

    Args:
        round_number: Round to filter (1-7), or None for all rounds

    Returns:
        Dict with:
        {
            'picks': List[Dict],  # Draft pick dicts
            'playoffs_complete': bool,  # True if playoffs finished, False if in progress
            'errors': List[str],  # Error messages (empty if successful)
            'warnings': List[str]  # Warning messages (non-fatal issues)
        }
    """
    result = {
        'picks': [],
        'playoffs_complete': True,
        'errors': [],
        'warnings': []
    }

    try:
        # Step 1: Get standings from database
        logger.debug(f"Fetching standings for dynasty={self.dynasty_id}, season={self.season-1}")

        try:
            standings = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season - 1,  # Draft 2025 is based on 2024 season
                season_type="regular_season"
            )
        except Exception as e:
            logger.error(f"Failed to fetch standings: {e}")
            result['errors'].append(f"Failed to fetch standings: {str(e)}")
            return result

        # Validate standings exist
        if not standings or 'divisions' not in standings:
            logger.warning("No standings data found for draft order calculation")
            result['errors'].append("No standings data found. Please complete a regular season first.")
            return result

        # Step 2: Convert standings to TeamRecord format
        try:
            team_records = convert_standings_to_team_records(standings)
        except ValueError as e:
            logger.error(f"Failed to convert standings: {e}")
            result['errors'].append(f"Invalid standings data: {str(e)}")
            return result

        # Validate we have all 32 teams
        if len(team_records) != 32:
            logger.error(f"Expected 32 teams in standings, got {len(team_records)}")
            result['errors'].append(
                f"Incomplete standings: expected 32 teams, got {len(team_records)}"
            )
            return result

        # Step 3: Get playoff results (handle incomplete playoffs gracefully)
        playoff_api = PlayoffResultsAPI(self.db_path)
        playoff_results = None
        playoffs_complete = False

        try:
            logger.debug(f"Fetching playoff results for dynasty={self.dynasty_id}, season={self.season-1}")
            playoff_results = playoff_api.get_playoff_results(
                dynasty_id=self.dynasty_id,
                season=self.season - 1  # Draft 2025 is based on 2024 season playoffs
            )
            playoffs_complete = True
            logger.info("Playoffs complete - full draft order available")

        except ValueError as e:
            # Playoffs incomplete or not started
            logger.warning(f"Playoffs incomplete: {e}")
            result['playoffs_complete'] = False
            result['warnings'].append(
                "Playoffs not complete. Draft order will include non-playoff teams only."
            )

            # Use empty playoff results for partial draft order
            playoff_results = {
                'wild_card_losers': [],
                'divisional_losers': [],
                'conference_losers': [],
                'super_bowl_loser': None,
                'super_bowl_winner': None
            }

        except Exception as e:
            # Unexpected error fetching playoff data
            logger.error(f"Error fetching playoff results: {e}")
            result['errors'].append(f"Error fetching playoff results: {str(e)}")
            return result

        # Update result with playoff status
        result['playoffs_complete'] = playoffs_complete

        # Step 4: Get team schedules for SOS calculation (handle missing schedules)
        sos_dict = {}
        try:
            logger.debug("Fetching team schedules for SOS calculation")
            schedules = self.database_api.get_all_team_schedules(
                dynasty_id=self.dynasty_id,
                season=self.season - 1,
                season_type="regular_season"
            )

            # Calculate SOS for all teams
            sos_dict = self._calculate_strength_of_schedule(schedules, team_records)

        except Exception as e:
            # Schedule data missing - use default SOS
            logger.warning(f"Failed to fetch schedules for SOS: {e}")
            result['warnings'].append(
                "Schedule data unavailable. Using default SOS (0.500) for all teams."
            )

            # Use default SOS = 0.500 for all teams
            sos_dict = {rec.team_id: 0.500 for rec in team_records}

        # Step 5: Calculate draft order (service validates inputs)
        try:
            logger.debug("Calculating draft order")
            draft_picks = self.draft_order_service.calculate_draft_order(
                team_records=team_records,
                playoff_results=playoff_results,
                strength_of_schedule=sos_dict
            )

        except ValueError as e:
            # Service validation failed
            logger.error(f"Draft order calculation failed: {e}")
            result['errors'].append(f"Draft order calculation failed: {str(e)}")
            return result

        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error calculating draft order: {e}")
            result['errors'].append(f"Unexpected error: {str(e)}")
            return result

        # Step 6: Convert to dict format and enrich with team data
        picks = []
        all_teams = {team.team_id: team for team in self.team_loader.get_all_teams()}

        for pick in draft_picks:
            try:
                # Get team metadata (handle missing team gracefully)
                team = all_teams.get(pick.team_id)
                if team:
                    team_name = team.full_name
                    team_abbrev = team.abbreviation
                    primary_color = team.primary_color
                    secondary_color = team.secondary_color
                else:
                    # Team data missing - use defaults
                    logger.warning(f"Team {pick.team_id} not found in team loader")
                    team_name = f"Team {pick.team_id}"
                    team_abbrev = f"T{pick.team_id}"
                    primary_color = "#000000"
                    secondary_color = "#FFFFFF"

                # Convert to dict with enriched data
                pick_dict = {
                    'overall_pick': pick.overall_pick,
                    'round_number': pick.round_number,
                    'pick_in_round': pick.pick_in_round,
                    'team_id': pick.team_id,
                    'team_name': team_name,
                    'team_abbrev': team_abbrev,
                    'team_record': pick.team_record,
                    'reason': pick.reason,
                    'sos': pick.strength_of_schedule,
                    'primary_color': primary_color,
                    'secondary_color': secondary_color,
                    'player': None,  # TODO: Query draft_class_api for executed picks
                }

                picks.append(pick_dict)

            except Exception as e:
                # Error processing single pick - log and continue
                logger.error(f"Error processing pick {pick.overall_pick}: {e}")
                result['warnings'].append(
                    f"Error processing pick #{pick.overall_pick}: {str(e)}"
                )

        # Step 7: Filter by round if specified
        if round_number is not None:
            if not (1 <= round_number <= 7):
                result['errors'].append(f"Invalid round number: {round_number} (must be 1-7)")
                return result

            picks = [p for p in picks if p['round_number'] == round_number]

        # Step 8: Set result picks
        result['picks'] = picks

        # Log success
        logger.info(
            f"Draft order calculated successfully: {len(picks)} picks "
            f"(playoffs_complete={playoffs_complete}, {len(result['errors'])} errors, "
            f"{len(result['warnings'])} warnings)"
        )

        return result

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in get_draft_order: {e}")
        result['errors'].append(f"Unexpected error: {str(e)}")
        return result


def _calculate_strength_of_schedule(
    self,
    schedules: Dict[int, List[int]],
    team_records: List[TeamRecord]
) -> Dict[int, float]:
    """
    Calculate strength of schedule for all teams.

    EDGE CASE HANDLING:
    - Missing schedule for team: Use SOS = 0.500
    - Empty schedule: Use SOS = 0.500
    - Missing opponent records: Skip opponent in SOS calculation

    Args:
        schedules: Dict mapping team_id → list of opponent team_ids
        team_records: List of all team records

    Returns:
        Dict mapping team_id → SOS (float between 0.0 and 1.0)
    """
    sos_dict = {}

    # Build lookup for team records
    team_record_lookup = {rec.team_id: rec for rec in team_records}

    # Calculate SOS for each team
    for team_id in range(1, 33):  # All 32 NFL teams
        # Get team's schedule
        schedule = schedules.get(team_id, [])

        if not schedule:
            # No schedule data - use default
            logger.warning(f"No schedule found for team {team_id}, using SOS=0.500")
            sos_dict[team_id] = 0.500
            continue

        # Calculate average opponent win percentage
        opponent_win_pcts = []
        for opponent_id in schedule:
            opponent_record = team_record_lookup.get(opponent_id)
            if opponent_record:
                opponent_win_pcts.append(opponent_record.win_percentage)
            else:
                logger.warning(
                    f"Opponent {opponent_id} not found in team records for team {team_id}"
                )

        if not opponent_win_pcts:
            # No valid opponents - use default
            logger.warning(
                f"No valid opponents found for team {team_id}, using SOS=0.500"
            )
            sos_dict[team_id] = 0.500
        else:
            # Calculate average
            sos = sum(opponent_win_pcts) / len(opponent_win_pcts)
            sos_dict[team_id] = sos

    return sos_dict
