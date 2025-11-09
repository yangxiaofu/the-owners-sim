"""
Playoff Manager

Pure logic for NFL playoff bracket generation and progression.
Implements NFL playoff rules including re-seeding after each round.
"""

from typing import List, Dict, Tuple, Optional
from datetime import timedelta

from .seeding_models import PlayoffSeeding, PlayoffSeed, ConferenceSeeding
from .bracket_models import PlayoffGame, PlayoffBracket

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date

from shared.game_result import GameResult


class PlayoffManager:
    """
    Manages NFL playoff bracket generation and progression.

    This is pure business logic - no side effects, no database access,
    no event creation. Takes seeding/results as input, returns brackets as output.

    Implements NFL playoff rules:
    - Wild Card: (2)v(7), (3)v(6), (4)v(5), #1 gets bye
    - Divisional: #1 plays LOWEST remaining seed (re-seeding)
    - Conference: Winners of divisional games
    - Super Bowl: AFC Champion vs NFC Champion
    """

    # NFL Playoff scheduling constants
    WILD_CARD_WEEK = 1
    DIVISIONAL_WEEK = 2
    CONFERENCE_WEEK = 3
    SUPER_BOWL_WEEK = 4

    def __init__(self):
        """Initialize playoff manager (no dependencies needed)."""
        pass

    def generate_wild_card_bracket(
        self,
        seeding: PlayoffSeeding,
        start_date: Date,
        season: int
    ) -> PlayoffBracket:
        """
        Generate wild card round from playoff seeding.

        Wild Card matchups:
        - AFC: (2)v(7), (3)v(6), (4)v(5)
        - NFC: (2)v(7), (3)v(6), (4)v(5)
        - #1 seeds get bye week (not in bracket)

        Args:
            seeding: Complete playoff seeding from PlayoffSeeder
            start_date: First wild card game date
            season: Season year (e.g., 2024)

        Returns:
            PlayoffBracket with 6 wild card games
        """
        games = []

        # AFC Wild Card games
        afc_games = self._create_wild_card_conference_games(
            seeding.afc,
            'AFC',
            start_date,
            season,
            game_offset=0
        )
        games.extend(afc_games)

        # NFC Wild Card games
        nfc_games = self._create_wild_card_conference_games(
            seeding.nfc,
            'NFC',
            start_date,
            season,
            game_offset=3  # NFC games start at game 4
        )
        games.extend(nfc_games)

        bracket = PlayoffBracket(
            round_name='wild_card',
            season=season,
            games=games,
            start_date=start_date
        )

        # Validate bracket structure
        bracket.validate()

        return bracket

    def generate_divisional_bracket(
        self,
        wild_card_results: List[GameResult],
        original_seeding: PlayoffSeeding,
        start_date: Date,
        season: int
    ) -> PlayoffBracket:
        """
        Generate divisional round with NFL re-seeding.

        Re-seeding rule:
        - #1 seed plays LOWEST remaining seed
        - Other two winners play each other (higher seed hosts)

        Args:
            wild_card_results: Results from wild card games
            original_seeding: Original playoff seeding (needed for #1 seed and re-seeding)
            start_date: Divisional round start date
            season: Season year

        Returns:
            PlayoffBracket with 4 divisional games
        """
        games = []

        # AFC Divisional Round
        afc_winners = self._extract_winners(wild_card_results, 'AFC')
        afc_one_seed = original_seeding.afc.seeds[0]  # #1 seed (had bye)

        afc_games = self._create_divisional_matchups(
            afc_winners,
            afc_one_seed,
            'AFC',
            start_date,
            season,
            game_offset=0
        )
        games.extend(afc_games)

        # NFC Divisional Round
        nfc_winners = self._extract_winners(wild_card_results, 'NFC')
        nfc_one_seed = original_seeding.nfc.seeds[0]  # #1 seed (had bye)

        nfc_games = self._create_divisional_matchups(
            nfc_winners,
            nfc_one_seed,
            'NFC',
            start_date,
            season,
            game_offset=2  # NFC games start at game 3
        )
        games.extend(nfc_games)

        bracket = PlayoffBracket(
            round_name='divisional',
            season=season,
            games=games,
            start_date=start_date
        )

        bracket.validate()
        return bracket

    def generate_conference_championship_bracket(
        self,
        divisional_results: List[GameResult],
        start_date: Date,
        season: int
    ) -> PlayoffBracket:
        """
        Generate conference championships from divisional results.

        Args:
            divisional_results: Results from divisional round
            start_date: Conference championship start date
            season: Season year

        Returns:
            PlayoffBracket with 2 conference championship games
        """
        games = []

        # AFC Championship
        afc_winners = self._extract_winners(divisional_results, 'AFC')
        if len(afc_winners) != 2:
            raise ValueError(f"Expected 2 AFC divisional winners, got {len(afc_winners)}")

        afc_game = self._create_championship_game(
            afc_winners,
            'AFC',
            start_date,
            season,
            game_number=1
        )
        games.append(afc_game)

        # NFC Championship
        nfc_winners = self._extract_winners(divisional_results, 'NFC')
        if len(nfc_winners) != 2:
            raise ValueError(f"Expected 2 NFC divisional winners, got {len(nfc_winners)}")

        nfc_game = self._create_championship_game(
            nfc_winners,
            'NFC',
            start_date,
            season,
            game_number=2
        )
        games.append(nfc_game)

        bracket = PlayoffBracket(
            round_name='conference',
            season=season,
            games=games,
            start_date=start_date
        )

        bracket.validate()
        return bracket

    def generate_super_bowl_bracket(
        self,
        conference_results: List[GameResult],
        start_date: Date,
        season: int
    ) -> PlayoffBracket:
        """
        Generate Super Bowl from conference championship results.

        Args:
            conference_results: Results from conference championships
            start_date: Super Bowl date
            season: Season year

        Returns:
            PlayoffBracket with 1 Super Bowl game
        """
        # Extract champions
        afc_champion = self._extract_champion(conference_results, 'AFC')
        nfc_champion = self._extract_champion(conference_results, 'NFC')

        # Super Bowl: AFC champion is visitor, NFC champion is home
        # (In reality this alternates, but for simplicity we use this convention)
        super_bowl_game = PlayoffGame(
            away_team_id=afc_champion['team_id'],
            home_team_id=nfc_champion['team_id'],
            away_seed=afc_champion['seed'],
            home_seed=nfc_champion['seed'],
            game_date=start_date,
            round_name='super_bowl',
            conference=None,  # Super Bowl has no conference
            game_number=1,
            week=self.SUPER_BOWL_WEEK,
            season=season
        )

        bracket = PlayoffBracket(
            round_name='super_bowl',
            season=season,
            games=[super_bowl_game],
            start_date=start_date
        )

        bracket.validate()
        return bracket

    # ========== Helper Methods ==========

    def _create_wild_card_conference_games(
        self,
        conference_seeding: ConferenceSeeding,
        conference: str,
        start_date: Date,
        season: int,
        game_offset: int
    ) -> List[PlayoffGame]:
        """
        Create wild card games for one conference.

        Matchups: (2)v(7), (3)v(6), (4)v(5)

        Args:
            conference_seeding: Seeding for one conference
            conference: 'AFC' or 'NFC'
            start_date: First game date
            season: Season year
            game_offset: Game number offset (0 for AFC, 3 for NFC)

        Returns:
            List of 3 PlayoffGame objects
        """
        games = []
        seeds = conference_seeding.seeds

        # Wild card matchups: (2)v(7), (3)v(6), (4)v(5)
        matchups = [
            (seeds[1], seeds[6]),  # (2) vs (7)
            (seeds[2], seeds[5]),  # (3) vs (6)
            (seeds[3], seeds[4]),  # (4) vs (5)
        ]

        # Calculate game dates (spread across weekend)
        game_dates = self._calculate_game_dates(start_date, 'wild_card', 3)

        for idx, (home_seed, away_seed) in enumerate(matchups):
            game = PlayoffGame(
                away_team_id=away_seed.team_id,
                home_team_id=home_seed.team_id,
                away_seed=away_seed.seed,
                home_seed=home_seed.seed,
                game_date=game_dates[idx],
                round_name='wild_card',
                conference=conference,
                game_number=game_offset + idx + 1,
                week=self.WILD_CARD_WEEK,
                season=season
            )
            games.append(game)

        return games

    def _create_divisional_matchups(
        self,
        winners: List[PlayoffSeed],
        one_seed: PlayoffSeed,
        conference: str,
        start_date: Date,
        season: int,
        game_offset: int
    ) -> List[PlayoffGame]:
        """
        Create divisional matchups with NFL re-seeding.

        Rule: #1 seed plays LOWEST remaining seed, other two play each other.

        Args:
            winners: Wild card winners (3 teams)
            one_seed: Conference #1 seed (had bye)
            conference: 'AFC' or 'NFC'
            start_date: Divisional round start date
            season: Season year
            game_offset: Game number offset (0 for AFC, 2 for NFC)

        Returns:
            List of 2 PlayoffGame objects
        """
        if len(winners) != 3:
            raise ValueError(f"Expected 3 wild card winners, got {len(winners)}")

        # Sort winners by seed (ascending = highest to lowest seed)
        sorted_winners = sorted(winners, key=lambda w: w.seed)

        # #1 seed plays LOWEST seed (highest seed number)
        lowest_seed = sorted_winners[-1]

        # Other two winners play each other
        middle_seed = sorted_winners[1]
        highest_seed = sorted_winners[0]

        # Calculate game dates
        game_dates = self._calculate_game_dates(start_date, 'divisional', 2)

        # Game 1: #1 seed vs lowest remaining seed
        game1 = PlayoffGame(
            away_team_id=lowest_seed.team_id,
            home_team_id=one_seed.team_id,
            away_seed=lowest_seed.seed,
            home_seed=one_seed.seed,
            game_date=game_dates[0],
            round_name='divisional',
            conference=conference,
            game_number=game_offset + 1,
            week=self.DIVISIONAL_WEEK,
            season=season
        )

        # Game 2: Other two winners (higher seed hosts)
        game2 = PlayoffGame(
            away_team_id=middle_seed.team_id,
            home_team_id=highest_seed.team_id,
            away_seed=middle_seed.seed,
            home_seed=highest_seed.seed,
            game_date=game_dates[1],
            round_name='divisional',
            conference=conference,
            game_number=game_offset + 2,
            week=self.DIVISIONAL_WEEK,
            season=season
        )

        return [game1, game2]

    def _create_championship_game(
        self,
        winners: List[PlayoffSeed],
        conference: str,
        start_date: Date,
        season: int,
        game_number: int
    ) -> PlayoffGame:
        """
        Create conference championship game.

        Args:
            winners: Divisional round winners (2 teams)
            conference: 'AFC' or 'NFC'
            start_date: Conference championship date
            season: Season year
            game_number: Game number (1 for AFC, 2 for NFC)

        Returns:
            PlayoffGame object
        """
        if len(winners) != 2:
            raise ValueError(f"Expected 2 divisional winners, got {len(winners)}")

        # Higher seed hosts
        sorted_winners = sorted(winners, key=lambda w: w.seed)
        home_team = sorted_winners[0]  # Lower seed number = higher seed
        away_team = sorted_winners[1]

        game_date = start_date if game_number == 1 else start_date.add_days(1)

        return PlayoffGame(
            away_team_id=away_team.team_id,
            home_team_id=home_team.team_id,
            away_seed=away_team.seed,
            home_seed=home_team.seed,
            game_date=game_date,
            round_name='conference',
            conference=conference,
            game_number=game_number,
            week=self.CONFERENCE_WEEK,
            season=season
        )

    def _extract_winners(
        self,
        results: List[GameResult],
        conference: str
    ) -> List[PlayoffSeed]:
        """
        Extract winning teams from game results for a conference.

        Args:
            results: Game results
            conference: 'AFC' or 'NFC'

        Returns:
            List of PlayoffSeed objects for winners
        """
        winners = []

        for result in results:
            # Determine winner
            if result.final_score[result.home_team.team_id] > result.final_score[result.away_team.team_id]:
                winner_team = result.home_team
            else:
                winner_team = result.away_team

            # Check if winner is from this conference
            # AFC: teams 1-16, NFC: teams 17-32
            is_afc = 1 <= winner_team.team_id <= 16
            team_conference = 'AFC' if is_afc else 'NFC'

            if team_conference == conference:
                # Extract seed from result metadata (should be stored)
                # For now, we need to infer seed from team_id
                # In practice, this would come from game metadata
                winner_seed = self._infer_seed_from_result(result, winner_team.team_id)
                winners.append(winner_seed)

        return winners

    def _extract_champion(
        self,
        results: List[GameResult],
        conference: str
    ) -> Dict:
        """
        Extract conference champion from conference championship results.

        Args:
            results: Conference championship results
            conference: 'AFC' or 'NFC'

        Returns:
            Dict with 'team_id' and 'seed'
        """
        for result in results:
            # Determine winner
            if result.final_score[result.home_team.team_id] > result.final_score[result.away_team.team_id]:
                winner_team = result.home_team
            else:
                winner_team = result.away_team

            # Check if winner is from this conference
            is_afc = 1 <= winner_team.team_id <= 16
            team_conference = 'AFC' if is_afc else 'NFC'

            if team_conference == conference:
                winner_seed = self._infer_seed_from_result(result, winner_team.team_id)
                return {
                    'team_id': winner_team.team_id,
                    'seed': winner_seed.seed
                }

        raise ValueError(f"No {conference} champion found in results")

    def _infer_seed_from_result(self, result: GameResult, team_id: int) -> PlayoffSeed:
        """
        Infer playoff seed from game result.

        This is a placeholder - in practice, seed info should be stored
        in the GameResult metadata.

        Args:
            result: Game result
            team_id: Team ID to get seed for

        Returns:
            PlayoffSeed object with basic info
        """
        # TODO: Get actual seed from result metadata
        # For now, return a minimal PlayoffSeed
        # This will be replaced when GameResult includes playoff metadata

        return PlayoffSeed(
            seed=1,  # Placeholder
            team_id=team_id,
            wins=0,
            losses=0,
            ties=0,
            win_percentage=0.0,
            division_winner=False,
            division_name="Unknown",
            conference="AFC" if team_id <= 16 else "NFC",
            points_for=0,
            points_against=0,
            point_differential=0,
            division_record="0-0",
            conference_record="0-0"
        )

    def _calculate_game_dates(
        self,
        start_date: Date,
        round_name: str,
        num_games: int
    ) -> List[Date]:
        """
        Calculate game dates for a round.

        Wild card: Spread across Sat/Sun/Mon
        Divisional: Sat/Sun
        Conference: Sunday (both games same day)
        Super Bowl: One game

        Args:
            start_date: First game date
            round_name: Round name
            num_games: Number of games

        Returns:
            List of Date objects
        """
        dates = []

        if round_name == 'wild_card':
            # Wild card: Saturday, Sunday, Sunday, Monday, Monday, Monday
            # Simplified: spread across 3 days
            for i in range(num_games):
                if i < 2:
                    dates.append(start_date)  # Saturday games
                elif i < 4:
                    dates.append(start_date.add_days(1))  # Sunday games
                else:
                    dates.append(start_date.add_days(2))  # Monday games

        elif round_name == 'divisional':
            # Divisional: Saturday, Sunday
            for i in range(num_games):
                if i < 1:
                    dates.append(start_date)
                else:
                    dates.append(start_date.add_days(1))

        elif round_name == 'conference':
            # Conference championships: Both on Sunday
            for _ in range(num_games):
                dates.append(start_date)

        else:  # super_bowl
            dates.append(start_date)

        return dates
