"""
Playoff Seeding Calculator

Main orchestrator for calculating NFL playoff seeding using official rules.
Coordinates between the tiebreaker engine, strength calculator, and data models
to produce the final playoff seeding for both conferences.
"""

from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import time

from .seeding_data_models import (
    TeamRecord, PlayoffSeed, PlayoffSeeding, WildCardMatchup,
    PlayoffSeedingInput, TiebreakerResult
)
from .nfl_tiebreaker_engine import NFLTiebreakerEngine
from .strength_calculator import StrengthCalculator
from ..constants import NFL_DIVISIONS


class PlayoffSeedingCalculator:
    """
    Orchestrates the complete NFL playoff seeding calculation.

    This is the main class that coordinates all components to calculate
    playoff seeding according to official NFL rules and procedures.
    """

    def __init__(self):
        """Initialize the playoff seeding calculator."""
        self.logger = logging.getLogger(__name__)
        self.tiebreaker_engine = NFLTiebreakerEngine()
        self.strength_calculator = StrengthCalculator()

    def calculate_playoff_seeding(self, seeding_input: PlayoffSeedingInput) -> PlayoffSeeding:
        """
        Calculate complete playoff seeding for both conferences.

        Args:
            seeding_input: All data needed for seeding calculation

        Returns:
            Complete playoff seeding with all teams and matchups
        """
        start_time = time.time()
        self.logger.info(f"Starting playoff seeding calculation for season {seeding_input.season}")

        try:
            # Step 1: Calculate strength metrics for all teams
            self._calculate_strength_metrics(seeding_input)

            # Step 2: Determine division winners (8 total)
            division_winners = self._determine_division_winners(seeding_input)

            # Step 3: Seed division winners 1-4 in each conference
            afc_division_seeds, nfc_division_seeds = self._seed_division_winners(
                division_winners, seeding_input
            )

            # Step 4: Determine wild card teams (6 total)
            afc_wildcard_seeds, nfc_wildcard_seeds = self._determine_wildcard_teams(
                seeding_input, division_winners
            )

            # Step 5: Combine for final seeding
            afc_seeds = afc_division_seeds + afc_wildcard_seeds
            nfc_seeds = nfc_division_seeds + nfc_wildcard_seeds

            # Step 6: Generate wild card matchups
            wild_card_matchups = self._generate_wildcard_matchups(afc_seeds, nfc_seeds)

            # Step 7: Create final result
            calculation_time = time.time() - start_time

            playoff_seeding = PlayoffSeeding(
                afc_seeds=afc_seeds,
                nfc_seeds=nfc_seeds,
                wild_card_matchups=wild_card_matchups,
                dynasty_id=seeding_input.dynasty_id,
                season=seeding_input.season,
                seeding_date=seeding_input.calculation_date,
                tiebreaker_applications=[],  # Will be populated by tiebreaker engine
                regular_season_complete=True,
                calculation_time_seconds=calculation_time
            )

            self.logger.info(f"Playoff seeding calculation completed in {calculation_time:.2f}s")
            return playoff_seeding

        except Exception as e:
            self.logger.error(f"Error calculating playoff seeding: {e}")
            raise

    def _calculate_strength_metrics(self, seeding_input: PlayoffSeedingInput) -> None:
        """Calculate strength of victory and strength of schedule for all teams."""
        self.logger.info("Calculating strength metrics")

        # This would require game results to calculate properly
        # For now, we'll set placeholder values
        # TODO: Implement proper strength calculation when game results are available

        for team_record in seeding_input.final_standings.values():
            # Placeholder calculations - replace with actual game data analysis
            team_record.strength_of_victory = 0.500  # 50% placeholder
            team_record.strength_of_schedule = 0.500  # 50% placeholder

    def _determine_division_winners(self, seeding_input: PlayoffSeedingInput) -> Dict[str, TeamRecord]:
        """
        Determine the winner of each division.

        Returns:
            Dictionary mapping division name to winning team record
        """
        self.logger.info("Determining division winners")
        division_winners = {}

        for division_name, team_ids in NFL_DIVISIONS.items():
            # Get teams in this division
            division_teams = []
            for team_id in team_ids:
                if team_id in seeding_input.final_standings:
                    division_teams.append(seeding_input.final_standings[team_id])

            if not division_teams:
                continue

            # Sort by win percentage first
            division_teams.sort(key=lambda t: t.win_percentage, reverse=True)

            # Check for ties at the top
            best_percentage = division_teams[0].win_percentage
            tied_teams = [team for team in division_teams if team.win_percentage == best_percentage]

            if len(tied_teams) == 1:
                # Clear division winner
                winner = tied_teams[0]
            else:
                # Need tiebreaker
                self.logger.info(f"Division tiebreaker needed in {division_name}: "
                               f"{[team.team_id for team in tied_teams]}")

                ordered_teams = self.tiebreaker_engine.break_division_tie(
                    tied_teams, seeding_input.head_to_head_results
                )
                winner = ordered_teams[0]

            division_winners[division_name] = winner
            self.logger.info(f"{division_name} winner: Team {winner.team_id} ({winner.overall_record})")

        return division_winners

    def _seed_division_winners(self, division_winners: Dict[str, TeamRecord],
                             seeding_input: PlayoffSeedingInput) -> Tuple[List[PlayoffSeed], List[PlayoffSeed]]:
        """
        Seed division winners 1-4 in each conference.

        Returns:
            Tuple of (AFC division seeds 1-4, NFC division seeds 1-4)
        """
        self.logger.info("Seeding division winners")

        # Separate by conference
        afc_division_winners = []
        nfc_division_winners = []

        for division_name, winner in division_winners.items():
            if division_name.startswith('AFC'):
                afc_division_winners.append(winner)
            else:
                nfc_division_winners.append(winner)

        # Sort each conference by record (handle ties)
        afc_seeds = self._create_division_seeds(afc_division_winners, "AFC", seeding_input)
        nfc_seeds = self._create_division_seeds(nfc_division_winners, "NFC", seeding_input)

        return afc_seeds, nfc_seeds

    def _create_division_seeds(self, division_winners: List[TeamRecord],
                              conference: str, seeding_input: PlayoffSeedingInput) -> List[PlayoffSeed]:
        """Create playoff seeds for division winners in a conference."""
        # Sort by win percentage first
        sorted_winners = sorted(division_winners, key=lambda t: t.win_percentage, reverse=True)

        # Handle potential ties between division winners
        seeds = []
        current_seed = 1

        i = 0
        while i < len(sorted_winners) and current_seed <= 4:
            current_team = sorted_winners[i]
            tied_teams = [current_team]

            # Find all teams tied with current team
            j = i + 1
            while j < len(sorted_winners) and sorted_winners[j].win_percentage == current_team.win_percentage:
                tied_teams.append(sorted_winners[j])
                j += 1

            if len(tied_teams) == 1:
                # No tie
                seed = self._create_playoff_seed(current_team, current_seed, conference, True)
                seeds.append(seed)
                current_seed += 1
                i += 1
            else:
                # Tie among division winners
                ordered_teams = self.tiebreaker_engine.break_division_tie(
                    tied_teams, seeding_input.head_to_head_results
                )

                for team in ordered_teams:
                    if current_seed <= 4:
                        seed = self._create_playoff_seed(team, current_seed, conference, True)
                        seeds.append(seed)
                        current_seed += 1

                i = j

        return seeds

    def _determine_wildcard_teams(self, seeding_input: PlayoffSeedingInput,
                                 division_winners: Dict[str, TeamRecord]) -> Tuple[List[PlayoffSeed], List[PlayoffSeed]]:
        """
        Determine wild card teams (3 per conference).

        Returns:
            Tuple of (AFC wild card seeds 5-7, NFC wild card seeds 5-7)
        """
        self.logger.info("Determining wild card teams")

        # Get division winner team IDs
        division_winner_ids = {winner.team_id for winner in division_winners.values()}

        # Separate remaining teams by conference
        afc_candidates = []
        nfc_candidates = []

        for team_id, team_record in seeding_input.final_standings.items():
            if team_id not in division_winner_ids:
                if 1 <= team_id <= 16:  # AFC
                    afc_candidates.append(team_record)
                else:  # NFC
                    nfc_candidates.append(team_record)

        # Select top 3 from each conference
        afc_wildcards = self._select_wildcard_teams(afc_candidates, "AFC", seeding_input)
        nfc_wildcards = self._select_wildcard_teams(nfc_candidates, "NFC", seeding_input)

        return afc_wildcards, nfc_wildcards

    def _select_wildcard_teams(self, candidates: List[TeamRecord],
                              conference: str, seeding_input: PlayoffSeedingInput) -> List[PlayoffSeed]:
        """Select 3 wild card teams from conference candidates."""
        # Sort by win percentage
        sorted_candidates = sorted(candidates, key=lambda t: t.win_percentage, reverse=True)

        wildcard_seeds = []
        selected_teams = []
        current_seed = 5

        # Select teams one by one, handling ties
        while len(selected_teams) < 3 and len(selected_teams) < len(sorted_candidates):
            remaining_candidates = [team for team in sorted_candidates if team not in selected_teams]

            if not remaining_candidates:
                break

            # Find best remaining win percentage
            best_percentage = remaining_candidates[0].win_percentage
            tied_teams = [team for team in remaining_candidates if team.win_percentage == best_percentage]

            if len(tied_teams) == 1:
                # No tie
                selected_team = tied_teams[0]
                selected_teams.append(selected_team)
                seed = self._create_playoff_seed(selected_team, current_seed, conference, False)
                wildcard_seeds.append(seed)
                current_seed += 1
            else:
                # Wild card tiebreaker
                ordered_teams = self.tiebreaker_engine.break_wildcard_tie(
                    tied_teams, seeding_input.head_to_head_results
                )

                # Take as many as we need
                for team in ordered_teams:
                    if len(selected_teams) < 3:
                        selected_teams.append(team)
                        seed = self._create_playoff_seed(team, current_seed, conference, False)
                        wildcard_seeds.append(seed)
                        current_seed += 1

        return wildcard_seeds

    def _create_playoff_seed(self, team: TeamRecord, seed_number: int,
                           conference: str, is_division_winner: bool) -> PlayoffSeed:
        """Create a PlayoffSeed object from team data."""
        # Determine division
        division = self._get_team_division(team.team_id)

        return PlayoffSeed(
            seed_number=seed_number,
            team_id=team.team_id,
            record=team.overall_record,
            win_percentage=team.win_percentage,
            division_winner=is_division_winner,
            conference=conference,
            division=division,
            points_for=team.points_for,
            points_against=team.points_against,
            strength_of_victory=team.strength_of_victory,
            strength_of_schedule=team.strength_of_schedule
        )

    def _get_team_division(self, team_id: int) -> str:
        """Get division name for a team ID."""
        for division_name, team_ids in NFL_DIVISIONS.items():
            if team_id in team_ids:
                return division_name.replace('_', ' ')  # "AFC_EAST" -> "AFC EAST"
        return "Unknown"

    def _generate_wildcard_matchups(self, afc_seeds: List[PlayoffSeed],
                                  nfc_seeds: List[PlayoffSeed]) -> List[WildCardMatchup]:
        """Generate wild card round matchups from seeding."""
        matchups = []

        # AFC matchups: 2v7, 3v6, 4v5
        afc_matchups = [
            (afc_seeds[1], afc_seeds[6]),  # 2 vs 7
            (afc_seeds[2], afc_seeds[5]),  # 3 vs 6
            (afc_seeds[3], afc_seeds[4])   # 4 vs 5
        ]

        # NFC matchups: 2v7, 3v6, 4v5
        nfc_matchups = [
            (nfc_seeds[1], nfc_seeds[6]),  # 2 vs 7
            (nfc_seeds[2], nfc_seeds[5]),  # 3 vs 6
            (nfc_seeds[3], nfc_seeds[4])   # 4 vs 5
        ]

        # Create matchup objects
        for higher_seed, lower_seed in afc_matchups:
            matchup = WildCardMatchup(
                higher_seed=higher_seed,
                lower_seed=lower_seed,
                home_team_id=higher_seed.team_id,
                away_team_id=lower_seed.team_id,
                conference="AFC",
                game_description=f"AFC Wild Card: ({higher_seed.seed_number}) vs ({lower_seed.seed_number})"
            )
            matchups.append(matchup)

        for higher_seed, lower_seed in nfc_matchups:
            matchup = WildCardMatchup(
                higher_seed=higher_seed,
                lower_seed=lower_seed,
                home_team_id=higher_seed.team_id,
                away_team_id=lower_seed.team_id,
                conference="NFC",
                game_description=f"NFC Wild Card: ({higher_seed.seed_number}) vs ({lower_seed.seed_number})"
            )
            matchups.append(matchup)

        return matchups