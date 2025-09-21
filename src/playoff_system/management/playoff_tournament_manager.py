"""
Playoff Tournament Manager

High-level coordinator for complete NFL playoff tournament management.
Orchestrates playoff seeding, bracket progression, game scheduling, and
tournament state tracking from Wild Card through Super Bowl.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Import shared constants
from ..constants import (
    PlayoffRound, PLAYOFF_ROUNDS, TEAMS_ADVANCING_PER_CONFERENCE,
    WILD_CARD_MATCHUPS, PLAYOFF_SCHEDULE_TIMING, GAMES_PER_ROUND,
    HOME_FIELD_RULES, get_next_round, is_final_round
)

# Import seeding components
from ..seeding.playoff_seeding_calculator import PlayoffSeedingCalculator
from ..seeding.seeding_data_models import PlayoffSeeding, PlayoffSeed

# Import utilities
from ..utils.data_converters import create_playoff_seeding_input_from_standings_store


class TournamentState(Enum):
    """Current state of the playoff tournament"""
    NOT_STARTED = "not_started"
    SEEDING_COMPLETE = "seeding_complete"
    WILD_CARD_IN_PROGRESS = "wild_card_in_progress"
    WILD_CARD_COMPLETE = "wild_card_complete"
    DIVISIONAL_IN_PROGRESS = "divisional_in_progress"
    DIVISIONAL_COMPLETE = "divisional_complete"
    CONFERENCE_IN_PROGRESS = "conference_in_progress"
    CONFERENCE_COMPLETE = "conference_complete"
    SUPER_BOWL_SCHEDULED = "super_bowl_scheduled"
    TOURNAMENT_COMPLETE = "tournament_complete"


@dataclass
class TournamentProgress:
    """Track overall tournament progress and statistics"""
    current_state: TournamentState = TournamentState.NOT_STARTED
    current_round: Optional[PlayoffRound] = None
    games_completed: int = 0
    games_remaining: int = 0
    tournament_start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None

    # Round-specific progress
    wild_card_complete: bool = False
    divisional_complete: bool = False
    conference_complete: bool = False
    super_bowl_complete: bool = False

    # Tournament results tracking
    afc_champion: Optional[int] = None  # Team ID
    nfc_champion: Optional[int] = None  # Team ID
    super_bowl_winner: Optional[int] = None  # Team ID


@dataclass
class TournamentContext:
    """Context information for the tournament"""
    dynasty_id: str
    season: int
    seeding_date: date
    tournament_start_date: date

    # Tournament configuration
    neutral_site_super_bowl: bool = True
    bye_week_between_rounds: bool = True

    # External integrations
    calendar_manager: Optional[Any] = None
    standings_store: Optional[Any] = None


class PlayoffTournamentManager:
    """
    High-level coordinator for complete NFL playoff tournament management.

    Orchestrates the entire playoff process from seeding calculation through
    Super Bowl completion, managing bracket progression, game scheduling,
    and integration with the simulation calendar system.
    """

    def __init__(self, tournament_context: TournamentContext):
        """
        Initialize playoff tournament manager.

        Args:
            tournament_context: Configuration and context for this tournament
        """
        self.context = tournament_context
        self.logger = logging.getLogger(__name__)

        # Core components
        self.seeding_calculator = PlayoffSeedingCalculator()

        # Tournament state
        self.progress = TournamentProgress()
        self.playoff_seeding: Optional[PlayoffSeeding] = None

        # Tournament bracket tracking
        self.bracket_state: Dict[PlayoffRound, Dict[str, Any]] = {}
        self.game_results: Dict[str, Any] = {}  # game_id -> result

        # Round managers (to be initialized)
        self.round_managers: Dict[PlayoffRound, Any] = {}

        self.logger.info(f"Tournament manager initialized for {self.context.season} season")

    def initialize_tournament(self, standings_store: Optional[Any] = None) -> bool:
        """
        Initialize the complete playoff tournament.

        Args:
            standings_store: Optional standings store with final regular season data

        Returns:
            True if initialization successful, False otherwise
        """
        self.logger.info("Initializing playoff tournament...")

        try:
            # Step 1: Calculate playoff seeding
            if not self._calculate_playoff_seeding(standings_store):
                return False

            # Step 2: Initialize tournament bracket
            if not self._initialize_tournament_bracket():
                return False

            # Step 3: Set up round managers
            if not self._initialize_round_managers():
                return False

            # Step 4: Update tournament state
            self.progress.current_state = TournamentState.SEEDING_COMPLETE
            self.progress.tournament_start_date = self.context.tournament_start_date
            self._calculate_tournament_timeline()

            self.logger.info("✅ Tournament initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"Tournament initialization failed: {e}")
            return False

    def schedule_tournament_games(self, calendar_manager: Any) -> bool:
        """
        Schedule all playoff games on the calendar system.

        Args:
            calendar_manager: Calendar manager for scheduling games

        Returns:
            True if scheduling successful, False otherwise
        """
        if self.progress.current_state != TournamentState.SEEDING_COMPLETE:
            self.logger.error("Cannot schedule games - tournament not properly initialized")
            return False

        self.logger.info("Scheduling playoff tournament games...")

        try:
            # Schedule Wild Card round
            if not self._schedule_round_games(PlayoffRound.WILD_CARD, calendar_manager):
                return False

            # Set up automatic round advancement triggers
            if not self._setup_round_advancement_triggers(calendar_manager):
                return False

            self.progress.current_state = TournamentState.WILD_CARD_IN_PROGRESS
            self.context.calendar_manager = calendar_manager

            self.logger.info("✅ Tournament games scheduled successfully")
            return True

        except Exception as e:
            self.logger.error(f"Game scheduling failed: {e}")
            return False

    def _calculate_tournament_timeline(self) -> None:
        """Calculate estimated tournament completion timeline."""
        if not self.progress.tournament_start_date:
            return

        # Use shared constants for timeline calculation (DRY compliance)
        super_bowl_offset = PLAYOFF_SCHEDULE_TIMING[PlayoffRound.SUPER_BOWL]
        super_bowl_date = self.progress.tournament_start_date + timedelta(days=super_bowl_offset)
        self.progress.estimated_completion_date = super_bowl_date

        # Calculate total games using shared constants
        total_games = sum(GAMES_PER_ROUND.values())
        self.progress.games_remaining = total_games

    def advance_to_next_round(self, completed_round: PlayoffRound,
                            round_results: List[Any]) -> bool:
        """
        Advance tournament to the next round based on completed round results.

        Args:
            completed_round: Round that just completed
            round_results: Results from the completed round

        Returns:
            True if advancement successful, False otherwise
        """
        self.logger.info(f"Advancing from {completed_round.value} round...")

        try:
            # Validate round completion
            if not self._validate_round_completion(completed_round, round_results):
                return False

            # Extract winners and update bracket
            winners = self._extract_round_winners(round_results)
            if not self._update_bracket_with_winners(completed_round, winners):
                return False

            # Determine next round
            next_round = self._get_next_round(completed_round)
            if not next_round:
                # Tournament complete
                return self._finalize_tournament(round_results)

            # Schedule next round games
            if self.context.calendar_manager:
                if not self._schedule_round_games(next_round, self.context.calendar_manager):
                    return False

            # Update tournament state
            self._update_tournament_state(completed_round, next_round)

            self.logger.info(f"✅ Advanced to {next_round.value} round")
            return True

        except Exception as e:
            self.logger.error(f"Round advancement failed: {e}")
            return False

    def get_tournament_status(self) -> Dict[str, Any]:
        """
        Get current tournament status and progress.

        Returns:
            Dictionary with comprehensive tournament status
        """
        status = {
            'tournament_initialized': self.playoff_seeding is not None,
            'current_state': self.progress.current_state.value,
            'current_round': self.progress.current_round.value if self.progress.current_round else None,
            'games_completed': self.progress.games_completed,
            'games_remaining': self.progress.games_remaining,
            'tournament_start_date': self.progress.tournament_start_date.isoformat() if self.progress.tournament_start_date else None,
            'estimated_completion': self.progress.estimated_completion_date.isoformat() if self.progress.estimated_completion_date else None,

            # Round completion status
            'rounds_complete': {
                'wild_card': self.progress.wild_card_complete,
                'divisional': self.progress.divisional_complete,
                'conference': self.progress.conference_complete,
                'super_bowl': self.progress.super_bowl_complete
            },

            # Championship tracking
            'afc_champion': self.progress.afc_champion,
            'nfc_champion': self.progress.nfc_champion,
            'super_bowl_winner': self.progress.super_bowl_winner,

            # Context
            'dynasty_id': self.context.dynasty_id,
            'season': self.context.season
        }

        # Add seeding information if available
        if self.playoff_seeding:
            status['playoff_seeding'] = {
                'afc_seeds': [(seed.seed_number, seed.team_id, seed.record) for seed in self.playoff_seeding.afc_seeds],
                'nfc_seeds': [(seed.seed_number, seed.team_id, seed.record) for seed in self.playoff_seeding.nfc_seeds],
                'teams_with_byes': [seed.team_id for seed in self.playoff_seeding.teams_with_byes]
            }

        return status

    def get_current_round_matchups(self) -> List[Dict[str, Any]]:
        """
        Get matchups for the current active round.

        Returns:
            List of matchup dictionaries with game details
        """
        if not self.progress.current_round or not self.playoff_seeding:
            return []

        try:
            current_round = self.progress.current_round

            if current_round == PlayoffRound.WILD_CARD:
                return self._get_wild_card_matchups()
            elif current_round == PlayoffRound.DIVISIONAL:
                return self._get_divisional_matchups()
            elif current_round == PlayoffRound.CONFERENCE_CHAMPIONSHIP:
                return self._get_conference_championship_matchups()
            elif current_round == PlayoffRound.SUPER_BOWL:
                return self._get_super_bowl_matchup()
            else:
                return []

        except Exception as e:
            self.logger.error(f"Failed to get current round matchups: {e}")
            return []

    # Private helper methods

    def _calculate_playoff_seeding(self, standings_store: Optional[Any] = None) -> bool:
        """Calculate playoff seeding from available data."""
        try:
            if standings_store:
                # Create seeding input from standings store
                seeding_input = create_playoff_seeding_input_from_standings_store(
                    standings_store, self.context.dynasty_id, self.context.season
                )
            else:
                # Would need to get data from another source
                self.logger.warning("No standings store provided - cannot calculate seeding")
                return False

            if not seeding_input:
                self.logger.error("Failed to create seeding input")
                return False

            # Calculate seeding
            self.playoff_seeding = self.seeding_calculator.calculate_playoff_seeding(seeding_input)

            self.logger.info(f"Playoff seeding calculated: {len(self.playoff_seeding.afc_seeds)} AFC, {len(self.playoff_seeding.nfc_seeds)} NFC teams")
            return True

        except Exception as e:
            self.logger.error(f"Seeding calculation failed: {e}")
            return False

    def _initialize_tournament_bracket(self) -> bool:
        """Initialize empty tournament bracket structure."""
        try:
            for round_enum in PLAYOFF_ROUNDS:
                self.bracket_state[round_enum] = {
                    'scheduled_games': [],
                    'completed_games': [],
                    'advancing_teams': []
                }

            return True

        except Exception as e:
            self.logger.error(f"Bracket initialization failed: {e}")
            return False

    def _initialize_round_managers(self) -> bool:
        """Initialize round-specific managers."""
        # This would initialize specific round managers
        # For now, just placeholder
        self.logger.info("Round managers initialized")
        return True


    def _schedule_round_games(self, round_enum: PlayoffRound, calendar_manager: Any) -> bool:
        """Schedule games for a specific round."""
        try:
            # Get round matchups
            if round_enum == PlayoffRound.WILD_CARD:
                matchups = self._get_wild_card_matchups()
            elif round_enum == PlayoffRound.DIVISIONAL:
                matchups = self._get_divisional_matchups()
            elif round_enum == PlayoffRound.CONFERENCE_CHAMPIONSHIP:
                matchups = self._get_conference_championship_matchups()
            elif round_enum == PlayoffRound.SUPER_BOWL:
                matchups = self._get_super_bowl_matchup()
            else:
                self.logger.error(f"Unknown round: {round_enum}")
                return False

            if not matchups:
                self.logger.warning(f"No matchups generated for {round_enum.value}")
                return True  # May be valid for some rounds

            # Calculate game date based on round timing
            round_start_date = self.context.tournament_start_date + timedelta(
                days=PLAYOFF_SCHEDULE_TIMING[round_enum]
            )

            # Schedule each game
            scheduled_games = []
            for i, matchup in enumerate(matchups):
                game_id = f"{round_enum.value.lower().replace(' ', '_')}_{i+1}"

                # Create game event (placeholder - would integrate with actual event system)
                game_event = {
                    'event_type': 'playoff_game',
                    'game_id': game_id,
                    'round': round_enum.value,
                    'home_team_id': matchup['home_team'],
                    'away_team_id': matchup['away_team'],
                    'game_date': round_start_date,
                    'neutral_site': HOME_FIELD_RULES[round_enum] == 'neutral_site'
                }

                scheduled_games.append(game_event)
                self.logger.info(f"Scheduled {round_enum.value} game: {matchup['description']}")

            # Store scheduled games in bracket state
            self.bracket_state[round_enum]['scheduled_games'] = scheduled_games

            self.logger.info(f"✅ Scheduled {len(scheduled_games)} {round_enum.value} games")
            return True

        except Exception as e:
            self.logger.error(f"Failed to schedule {round_enum.value} games: {e}")
            return False

    def _setup_round_advancement_triggers(self, calendar_manager: Any) -> bool:
        """Set up automatic triggers for round advancement."""
        # This would set up event triggers to automatically advance rounds
        self.logger.info("Round advancement triggers set up")
        return True

    def _validate_round_completion(self, completed_round: PlayoffRound, results: List[Any]) -> bool:
        """Validate that a round is properly completed."""
        try:
            # Check if we have the expected number of game results
            expected_games = GAMES_PER_ROUND[completed_round]

            if len(results) != expected_games:
                self.logger.error(
                    f"{completed_round.value} round validation failed: "
                    f"Expected {expected_games} results, got {len(results)}"
                )
                return False

            # Validate each result has required fields
            for i, result in enumerate(results):
                if not self._validate_game_result(result, completed_round, i):
                    return False

            # Validate advancing teams count
            winners = self._extract_round_winners(results)
            if not is_final_round(completed_round):
                expected_advancing = TEAMS_ADVANCING_PER_CONFERENCE[completed_round] * 2  # AFC + NFC
                if len(winners) != expected_advancing:
                    self.logger.error(
                        f"{completed_round.value} round validation failed: "
                        f"Expected {expected_advancing} advancing teams, got {len(winners)}"
                    )
                    return False

            self.logger.info(f"✅ {completed_round.value} round validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Round validation failed: {e}")
            return False

    def _extract_round_winners(self, round_results: List[Any]) -> List[int]:
        """Extract winning team IDs from round results."""
        winners = []

        try:
            for result in round_results:
                # Handle different possible result formats
                if hasattr(result, 'winning_team_id'):
                    winners.append(result.winning_team_id)
                elif hasattr(result, 'winner_team_id'):
                    winners.append(result.winner_team_id)
                elif isinstance(result, dict):
                    if 'winning_team_id' in result:
                        winners.append(result['winning_team_id'])
                    elif 'winner_team_id' in result:
                        winners.append(result['winner_team_id'])
                    elif 'winner' in result:
                        winners.append(result['winner'])
                    else:
                        self.logger.warning(f"Could not extract winner from result: {result}")
                else:
                    self.logger.warning(f"Unrecognized result format: {type(result)}")

            self.logger.info(f"Extracted {len(winners)} winners from round results")
            return winners

        except Exception as e:
            self.logger.error(f"Failed to extract round winners: {e}")
            return []

    def _update_bracket_with_winners(self, completed_round: PlayoffRound, winners: List[int]) -> bool:
        """Update bracket state with round winners."""
        self.bracket_state[completed_round]['advancing_teams'] = winners
        return True

    def _get_next_round(self, current_round: PlayoffRound) -> Optional[PlayoffRound]:
        """Get the next round after current round."""
        try:
            # Use shared constant function for DRY compliance
            return get_next_round(current_round)
        except ValueError:
            # Super Bowl is final round
            return None

    def _finalize_tournament(self, final_results: List[Any]) -> bool:
        """Finalize tournament with Super Bowl results."""
        self.progress.current_state = TournamentState.TOURNAMENT_COMPLETE
        self.progress.super_bowl_complete = True
        # Extract Super Bowl winner
        # self.progress.super_bowl_winner = winner_team_id
        self.logger.info("🏆 Tournament completed!")
        return True

    def _update_tournament_state(self, completed_round: PlayoffRound, next_round: PlayoffRound) -> None:
        """Update tournament state after round advancement."""
        # Mark completed round
        if completed_round == PlayoffRound.WILD_CARD:
            self.progress.wild_card_complete = True
            self.progress.current_state = TournamentState.DIVISIONAL_IN_PROGRESS
        elif completed_round == PlayoffRound.DIVISIONAL:
            self.progress.divisional_complete = True
            self.progress.current_state = TournamentState.CONFERENCE_IN_PROGRESS
        elif completed_round == PlayoffRound.CONFERENCE_CHAMPIONSHIP:
            self.progress.conference_complete = True
            self.progress.current_state = TournamentState.SUPER_BOWL_SCHEDULED

        self.progress.current_round = next_round

    def _get_wild_card_matchups(self) -> List[Dict[str, Any]]:
        """Get Wild Card round matchups."""
        if not self.playoff_seeding:
            return []

        matchups = []
        for matchup in self.playoff_seeding.wild_card_matchups:
            matchups.append({
                'round': 'Wild Card',
                'conference': matchup.conference,
                'higher_seed': matchup.higher_seed.seed_number,
                'lower_seed': matchup.lower_seed.seed_number,
                'home_team': matchup.home_team_id,
                'away_team': matchup.away_team_id,
                'description': matchup.game_description
            })

        return matchups

    def _get_divisional_matchups(self) -> List[Dict[str, Any]]:
        """Get Divisional round matchups."""
        if not self.playoff_seeding:
            return []

        try:
            matchups = []
            wild_card_winners = self.bracket_state.get(PlayoffRound.WILD_CARD, {}).get('advancing_teams', [])

            if len(wild_card_winners) < 6:  # 3 AFC + 3 NFC
                self.logger.warning(f"Insufficient wild card winners: {len(wild_card_winners)}")
                return []

            # Split winners by conference
            afc_winners = [team_id for team_id in wild_card_winners if team_id <= 16]
            nfc_winners = [team_id for team_id in wild_card_winners if team_id > 16]

            if len(afc_winners) != 3 or len(nfc_winners) != 3:
                self.logger.warning(f"Invalid conference split: AFC={len(afc_winners)}, NFC={len(nfc_winners)}")
                return []

            # Generate AFC divisional matchups
            afc_matchups = self._generate_divisional_conference_matchups(
                afc_winners, 'AFC', self.playoff_seeding.afc_seeds
            )
            matchups.extend(afc_matchups)

            # Generate NFC divisional matchups
            nfc_matchups = self._generate_divisional_conference_matchups(
                nfc_winners, 'NFC', self.playoff_seeding.nfc_seeds
            )
            matchups.extend(nfc_matchups)

            return matchups

        except Exception as e:
            self.logger.error(f"Failed to generate divisional matchups: {e}")
            return []

    def _get_conference_championship_matchups(self) -> List[Dict[str, Any]]:
        """Get Conference Championship matchups."""
        try:
            matchups = []
            divisional_winners = self.bracket_state.get(PlayoffRound.DIVISIONAL, {}).get('advancing_teams', [])

            if len(divisional_winners) < 4:  # 2 AFC + 2 NFC
                self.logger.warning(f"Insufficient divisional winners: {len(divisional_winners)}")
                return []

            # Split winners by conference
            afc_winners = [team_id for team_id in divisional_winners if team_id <= 16]
            nfc_winners = [team_id for team_id in divisional_winners if team_id > 16]

            if len(afc_winners) != 2 or len(nfc_winners) != 2:
                self.logger.warning(f"Invalid conference split: AFC={len(afc_winners)}, NFC={len(nfc_winners)}")
                return []

            # AFC Championship
            afc_matchup = self._generate_conference_championship_matchup(afc_winners, 'AFC')
            if afc_matchup:
                matchups.append(afc_matchup)

            # NFC Championship
            nfc_matchup = self._generate_conference_championship_matchup(nfc_winners, 'NFC')
            if nfc_matchup:
                matchups.append(nfc_matchup)

            return matchups

        except Exception as e:
            self.logger.error(f"Failed to generate conference championship matchups: {e}")
            return []

    def _validate_game_result(self, result: Any, round_enum: PlayoffRound, game_index: int) -> bool:
        """Validate a single game result has required fields."""
        try:
            # Check for winner identification
            has_winner = (
                hasattr(result, 'winning_team_id') or
                hasattr(result, 'winner_team_id') or
                (isinstance(result, dict) and (
                    'winning_team_id' in result or
                    'winner_team_id' in result or
                    'winner' in result
                ))
            )

            if not has_winner:
                self.logger.error(
                    f"{round_enum.value} game {game_index + 1} missing winner information"
                )
                return False

            # Additional validation could be added here
            # (e.g., score validation, team ID validation)

            return True

        except Exception as e:
            self.logger.error(f"Game result validation failed: {e}")
            return False

    def _generate_divisional_conference_matchups(self, wild_card_winners: List[int],
                                                conference: str, conference_seeds: List[Any]) -> List[Dict[str, Any]]:
        """Generate divisional round matchups for a specific conference."""
        try:
            matchups = []

            # Create seed mapping for wild card winners
            seed_map = {seed.team_id: seed.seed_number for seed in conference_seeds}

            # Sort wild card winners by seed (lowest seed number = higher seed)
            sorted_winners = sorted(wild_card_winners, key=lambda team_id: seed_map.get(team_id, 99))

            # #1 seed (bye) plays lowest remaining seed
            one_seed = next((seed.team_id for seed in conference_seeds if seed.seed_number == 1), None)
            if not one_seed:
                self.logger.error(f"{conference} #1 seed not found")
                return []

            lowest_seed_winner = sorted_winners[-1] if sorted_winners else None
            if not lowest_seed_winner:
                self.logger.error(f"No wild card winners for {conference}")
                return []

            # Game 1: #1 seed vs lowest wild card winner
            matchups.append({
                'round': 'Divisional',
                'conference': conference,
                'higher_seed': 1,
                'lower_seed': seed_map.get(lowest_seed_winner, 99),
                'home_team': one_seed,
                'away_team': lowest_seed_winner,
                'description': f"{conference} Divisional: #{seed_map.get(lowest_seed_winner, '?')} vs #1"
            })

            # Game 2: Remaining two wild card winners
            remaining_winners = [w for w in sorted_winners if w != lowest_seed_winner]
            if len(remaining_winners) >= 2:
                higher_seed_team = remaining_winners[0]  # Higher seeded team
                lower_seed_team = remaining_winners[1]   # Lower seeded team

                matchups.append({
                    'round': 'Divisional',
                    'conference': conference,
                    'higher_seed': seed_map.get(higher_seed_team, 99),
                    'lower_seed': seed_map.get(lower_seed_team, 99),
                    'home_team': higher_seed_team,
                    'away_team': lower_seed_team,
                    'description': f"{conference} Divisional: #{seed_map.get(lower_seed_team, '?')} vs #{seed_map.get(higher_seed_team, '?')}"
                })

            return matchups

        except Exception as e:
            self.logger.error(f"Failed to generate {conference} divisional matchups: {e}")
            return []

    def _generate_conference_championship_matchup(self, divisional_winners: List[int],
                                                 conference: str) -> Optional[Dict[str, Any]]:
        """Generate conference championship matchup."""
        try:
            if len(divisional_winners) != 2:
                self.logger.error(f"{conference} championship needs exactly 2 teams, got {len(divisional_winners)}")
                return None

            # Get original seeding to determine home field
            conference_seeds = self.playoff_seeding.afc_seeds if conference == 'AFC' else self.playoff_seeding.nfc_seeds
            seed_map = {seed.team_id: seed.seed_number for seed in conference_seeds}

            # Sort by seed (lower number = higher seed = home field advantage)
            sorted_winners = sorted(divisional_winners, key=lambda team_id: seed_map.get(team_id, 99))
            higher_seed_team = sorted_winners[0]
            lower_seed_team = sorted_winners[1]

            return {
                'round': 'Conference Championship',
                'conference': conference,
                'higher_seed': seed_map.get(higher_seed_team, 99),
                'lower_seed': seed_map.get(lower_seed_team, 99),
                'home_team': higher_seed_team,  # Higher seed hosts
                'away_team': lower_seed_team,
                'description': f"{conference} Championship: #{seed_map.get(lower_seed_team, '?')} vs #{seed_map.get(higher_seed_team, '?')}"
            }

        except Exception as e:
            self.logger.error(f"Failed to generate {conference} championship matchup: {e}")
            return None

    def _get_super_bowl_matchup(self) -> List[Dict[str, Any]]:
        """Get Super Bowl matchup."""
        try:
            conference_winners = self.bracket_state.get(PlayoffRound.CONFERENCE_CHAMPIONSHIP, {}).get('advancing_teams', [])

            if len(conference_winners) != 2:
                self.logger.warning(f"Need exactly 2 conference champions, got {len(conference_winners)}")
                return []

            # Split by conference
            afc_champion = None
            nfc_champion = None

            for team_id in conference_winners:
                if team_id <= 16:
                    afc_champion = team_id
                else:
                    nfc_champion = team_id

            if not afc_champion or not nfc_champion:
                self.logger.error(f"Missing conference champion: AFC={afc_champion}, NFC={nfc_champion}")
                return []

            # Update tournament progress
            self.progress.afc_champion = afc_champion
            self.progress.nfc_champion = nfc_champion

            # Super Bowl is always neutral site
            super_bowl_matchup = {
                'round': 'Super Bowl',
                'conference': 'NEUTRAL',
                'afc_champion': afc_champion,
                'nfc_champion': nfc_champion,
                'home_team': afc_champion,  # Convention: AFC champion listed as home
                'away_team': nfc_champion,
                'description': f"Super Bowl: AFC Champion vs NFC Champion",
                'neutral_site': True
            }

            return [super_bowl_matchup]

        except Exception as e:
            self.logger.error(f"Failed to generate Super Bowl matchup: {e}")
            return []