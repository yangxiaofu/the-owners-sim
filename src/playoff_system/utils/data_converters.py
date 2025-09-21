"""
Data Model Converters

Utilities for converting between different team record representations to avoid
duplication while allowing each component to use the model that best fits its needs.

Key Conversions:
- StandingsStore.EnhancedTeamStanding ↔ playoff_system.TeamRecord
- Extract playoff data from various sources
"""

from typing import Dict, List, Optional, Any
import logging

# Import with fallback handling
try:
    from stores.standings_store import EnhancedTeamStanding, TeamStanding
    STANDINGS_STORE_AVAILABLE = True
except ImportError:
    STANDINGS_STORE_AVAILABLE = False

try:
    from ..seeding.seeding_data_models import TeamRecord
    TEAM_RECORD_AVAILABLE = True
except ImportError:
    TEAM_RECORD_AVAILABLE = False


logger = logging.getLogger(__name__)


def convert_standing_to_team_record(standing: Any) -> Optional[Any]:
    """
    Convert a StandingsStore team standing to a playoff system TeamRecord.

    Args:
        standing: EnhancedTeamStanding or TeamStanding instance

    Returns:
        TeamRecord instance with all available data, or None if conversion fails
    """
    if not TEAM_RECORD_AVAILABLE:
        logger.error("TeamRecord not available - cannot convert")
        return None

    try:
        # Handle both TeamStanding and EnhancedTeamStanding
        if hasattr(standing, 'division_wins'):
            # EnhancedTeamStanding - has all the fields we need
            return TeamRecord(
                team_id=standing.team_id,
                wins=standing.wins,
                losses=standing.losses,
                ties=getattr(standing, 'ties', 0),

                # Division records
                division_wins=getattr(standing, 'division_wins', 0),
                division_losses=getattr(standing, 'division_losses', 0),
                division_ties=0,  # EnhancedTeamStanding doesn't track ties separately

                # Conference records
                conference_wins=getattr(standing, 'conference_wins', 0),
                conference_losses=getattr(standing, 'conference_losses', 0),
                conference_ties=0,  # EnhancedTeamStanding doesn't track ties separately

                # Home/away records
                home_wins=getattr(standing, 'home_wins', 0),
                home_losses=getattr(standing, 'home_losses', 0),
                home_ties=0,
                away_wins=getattr(standing, 'away_wins', 0),
                away_losses=getattr(standing, 'away_losses', 0),
                away_ties=0,

                # Scoring
                points_for=getattr(standing, 'points_for', 0),
                points_against=getattr(standing, 'points_against', 0),

                # Strength calculations (will be filled by StrengthCalculator)
                strength_of_victory=0.0,
                strength_of_schedule=0.0,

                # These will be populated during tiebreaker calculations
                head_to_head_records={},
                common_games_record=None
            )
        else:
            # Basic TeamStanding - limited data available
            return TeamRecord(
                team_id=standing.team_id,
                wins=standing.wins,
                losses=standing.losses,
                ties=getattr(standing, 'ties', 0),

                # All other fields default to 0 since not available
                division_wins=0,
                division_losses=0,
                conference_wins=0,
                conference_losses=0,
                points_for=0,
                points_against=0
            )

    except Exception as e:
        logger.error(f"Failed to convert standing to TeamRecord: {e}")
        return None


def convert_team_record_to_standing(team_record: Any, enhanced: bool = True) -> Optional[Any]:
    """
    Convert a playoff system TeamRecord to a StandingsStore team standing.

    Args:
        team_record: TeamRecord instance
        enhanced: If True, create EnhancedTeamStanding; if False, basic TeamStanding

    Returns:
        EnhancedTeamStanding or TeamStanding instance, or None if conversion fails
    """
    if not STANDINGS_STORE_AVAILABLE:
        logger.error("StandingsStore not available - cannot convert")
        return None

    try:
        if enhanced:
            # Create EnhancedTeamStanding with all available data
            return EnhancedTeamStanding(
                team_id=team_record.team_id,
                wins=team_record.wins,
                losses=team_record.losses,
                ties=team_record.ties,
                division_place=1,  # Will be calculated by standings store

                # Enhanced fields
                division_wins=team_record.division_wins,
                division_losses=team_record.division_losses,
                conference_wins=team_record.conference_wins,
                conference_losses=team_record.conference_losses,
                home_wins=team_record.home_wins,
                home_losses=team_record.home_losses,
                away_wins=team_record.away_wins,
                away_losses=team_record.away_losses,
                points_for=team_record.points_for,
                points_against=team_record.points_against,

                # These would need to be calculated separately
                streak="",
                last_5=""
            )
        else:
            # Create basic TeamStanding
            return TeamStanding(
                team_id=team_record.team_id,
                wins=team_record.wins,
                losses=team_record.losses,
                ties=team_record.ties,
                division_place=1  # Will be calculated by standings store
            )

    except Exception as e:
        logger.error(f"Failed to convert TeamRecord to standing: {e}")
        return None


def extract_team_records_from_standings_store(standings_store: Any) -> Dict[int, Any]:
    """
    Extract playoff-ready TeamRecord objects from a StandingsStore.

    Args:
        standings_store: StandingsStore instance

    Returns:
        Dictionary mapping team_id -> TeamRecord for all teams
    """
    team_records = {}

    if not TEAM_RECORD_AVAILABLE:
        logger.error("TeamRecord not available - cannot extract")
        return team_records

    try:
        # Iterate through all teams in the standings store
        for team_id_str, standing in standings_store.data.items():
            team_id = int(team_id_str)

            team_record = convert_standing_to_team_record(standing)
            if team_record:
                team_records[team_id] = team_record
            else:
                logger.warning(f"Failed to convert standing for team {team_id}")

    except Exception as e:
        logger.error(f"Failed to extract team records from standings store: {e}")

    return team_records


def create_playoff_seeding_input_from_standings_store(standings_store: Any,
                                                     dynasty_id: str,
                                                     season: int,
                                                     head_to_head_results: Optional[Dict] = None) -> Optional[Any]:
    """
    Create a complete PlayoffSeedingInput from a StandingsStore.

    Args:
        standings_store: StandingsStore instance with current season data
        dynasty_id: Dynasty identifier
        season: Season year
        head_to_head_results: Optional head-to-head results dict

    Returns:
        PlayoffSeedingInput ready for seeding calculation, or None if failed
    """
    try:
        from ..seeding.seeding_data_models import PlayoffSeedingInput
        from datetime import datetime

        # Extract team records
        final_standings = extract_team_records_from_standings_store(standings_store)

        if not final_standings:
            logger.error("No team records extracted from standings store")
            return None

        # Create seeding input
        return PlayoffSeedingInput(
            final_standings=final_standings,
            head_to_head_results=head_to_head_results or {},
            dynasty_id=dynasty_id,
            season=season,
            calculation_date=datetime.now()
        )

    except ImportError:
        logger.error("PlayoffSeedingInput not available")
        return None
    except Exception as e:
        logger.error(f"Failed to create PlayoffSeedingInput: {e}")
        return None


def validate_team_record_completeness(team_record: Any) -> Dict[str, bool]:
    """
    Validate that a TeamRecord has all necessary data for playoff calculations.

    Args:
        team_record: TeamRecord instance to validate

    Returns:
        Dictionary of validation results for different aspects
    """
    validation = {
        'basic_record': False,
        'division_record': False,
        'conference_record': False,
        'home_away_record': False,
        'scoring_data': False,
        'overall_complete': False
    }

    try:
        # Basic record validation
        if hasattr(team_record, 'wins') and hasattr(team_record, 'losses'):
            validation['basic_record'] = True

        # Division record validation
        if (hasattr(team_record, 'division_wins') and
            hasattr(team_record, 'division_losses')):
            validation['division_record'] = True

        # Conference record validation
        if (hasattr(team_record, 'conference_wins') and
            hasattr(team_record, 'conference_losses')):
            validation['conference_record'] = True

        # Home/away record validation
        if (hasattr(team_record, 'home_wins') and hasattr(team_record, 'away_wins') and
            hasattr(team_record, 'home_losses') and hasattr(team_record, 'away_losses')):
            validation['home_away_record'] = True

        # Scoring data validation
        if (hasattr(team_record, 'points_for') and
            hasattr(team_record, 'points_against')):
            validation['scoring_data'] = True

        # Overall completeness
        validation['overall_complete'] = all([
            validation['basic_record'],
            validation['division_record'],
            validation['conference_record'],
            validation['scoring_data']
        ])

    except Exception as e:
        logger.error(f"Failed to validate TeamRecord: {e}")

    return validation


def get_missing_data_summary(team_records: Dict[int, Any]) -> Dict[str, Any]:
    """
    Analyze a collection of team records to identify missing data.

    Args:
        team_records: Dictionary of team_id -> TeamRecord

    Returns:
        Summary of missing data across all teams
    """
    summary = {
        'total_teams': len(team_records),
        'teams_with_issues': [],
        'common_missing_fields': [],
        'overall_completeness': 0.0
    }

    if not team_records:
        return summary

    field_counts = {
        'basic_record': 0,
        'division_record': 0,
        'conference_record': 0,
        'home_away_record': 0,
        'scoring_data': 0,
        'overall_complete': 0
    }

    for team_id, team_record in team_records.items():
        validation = validate_team_record_completeness(team_record)

        # Count completeness
        for field, is_complete in validation.items():
            if is_complete:
                field_counts[field] += 1

        # Track teams with issues
        if not validation['overall_complete']:
            missing_fields = [field for field, complete in validation.items() if not complete]
            summary['teams_with_issues'].append({
                'team_id': team_id,
                'missing_fields': missing_fields
            })

    # Calculate percentages
    total_teams = summary['total_teams']
    summary['field_completeness'] = {
        field: (count / total_teams) * 100
        for field, count in field_counts.items()
    }

    summary['overall_completeness'] = field_counts['overall_complete'] / total_teams * 100

    return summary