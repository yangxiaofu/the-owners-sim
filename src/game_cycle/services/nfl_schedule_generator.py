"""
NFL Schedule Generator - Generates NFL-compliant 17-game schedules.

Implements the NFL's scheduling formula with proper opponent rotation:
- 6 division games (2x each rival)
- 4 in-conference rotation games (3-year cycle)
- 4 cross-conference rotation games (4-year cycle)
- 2 same-place finisher games (based on prior standings)
- 1 17th game (cross-conference, based on standings)

Total: 17 games per team = 272 games per season (32 teams * 17 / 2)

Architecture:
    NFLScheduleGenerator → ScheduleRotationAPI (rotation state)
                        → TeamHistoryAPI (prior standings)
                        → StandingsAPI (divisional rankings)
"""

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Callable

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.schedule_rotation_api import ScheduleRotationAPI
from src.game_cycle.database.standings_api import StandingsAPI


@dataclass
class Matchup:
    """Represents a single game matchup before week assignment."""
    home_team_id: int
    away_team_id: int
    is_divisional: bool
    is_conference: bool
    week: int = 0  # Assigned during week distribution

    def __hash__(self):
        return hash((self.home_team_id, self.away_team_id))


@dataclass
class NFLScheduleGenerator:
    """
    Generates NFL-compliant 17-game schedules using deterministic rotation.

    Tracks rotation state across seasons to ensure proper opponent cycling.

    Architecture:
        - Generates 272 total games (32 teams * 17 games / 2)
        - Uses rotation state from schedule_rotation table
        - Deterministic opponent selection based on NFL formula
        - Home/away balancing ensures 8-9 or 9-8 split per team

    Usage:
        generator = NFLScheduleGenerator(db_path, dynasty_id)
        games = generator.generate_schedule(season=2025)
        # Returns list of game event dicts ready for events_insert_batch()

    Division IDs:
        1: AFC East (Teams 1-4: Bills, Dolphins, Patriots, Jets)
        2: AFC North (Teams 5-8: Ravens, Bengals, Browns, Steelers)
        3: AFC South (Teams 9-12: Texans, Colts, Jaguars, Titans)
        4: AFC West (Teams 13-16: Broncos, Chiefs, Raiders, Chargers)
        5: NFC East (Teams 17-20: Cowboys, Giants, Eagles, Commanders)
        6: NFC North (Teams 21-24: Bears, Lions, Packers, Vikings)
        7: NFC South (Teams 25-28: Falcons, Panthers, Saints, Buccaneers)
        8: NFC West (Teams 29-32: Cardinals, Rams, 49ers, Seahawks)
    """

    db_path: str
    dynasty_id: str

    # Division structure - maps division_id to team_ids
    DIVISIONS: Dict[int, List[int]] = field(default_factory=lambda: {
        1: [1, 2, 3, 4],       # AFC East
        2: [5, 6, 7, 8],       # AFC North
        3: [9, 10, 11, 12],    # AFC South
        4: [13, 14, 15, 16],   # AFC West
        5: [17, 18, 19, 20],   # NFC East
        6: [21, 22, 23, 24],   # NFC North
        7: [25, 26, 27, 28],   # NFC South
        8: [29, 30, 31, 32],   # NFC West
    })

    # In-conference rotation pairings (3-year cycle)
    IN_CONFERENCE_PAIRINGS: Dict[str, List[Dict[int, int]]] = field(default_factory=lambda: {
        'AFC': [
            {1: 2, 2: 1, 3: 4, 4: 3},  # Year 0: East-North, South-West
            {1: 3, 3: 1, 2: 4, 4: 2},  # Year 1: East-South, North-West
            {1: 4, 4: 1, 2: 3, 3: 2},  # Year 2: East-West, North-South
        ],
        'NFC': [
            {5: 6, 6: 5, 7: 8, 8: 7},  # Year 0: East-North, South-West
            {5: 7, 7: 5, 6: 8, 8: 6},  # Year 1: East-South, North-West
            {5: 8, 8: 5, 6: 7, 7: 6},  # Year 2: East-West, North-South
        ]
    })

    # Cross-conference pairings (4-year cycle)
    CROSS_CONFERENCE_PAIRINGS: List[Dict[int, int]] = field(default_factory=lambda: [
        {1: 5, 2: 6, 3: 7, 4: 8, 5: 1, 6: 2, 7: 3, 8: 4},  # Year 0
        {1: 6, 2: 7, 3: 8, 4: 5, 5: 4, 6: 1, 7: 2, 8: 3},  # Year 1
        {1: 7, 2: 8, 3: 5, 4: 6, 5: 3, 6: 4, 7: 1, 8: 2},  # Year 2
        {1: 8, 2: 5, 3: 6, 4: 7, 5: 2, 6: 3, 7: 4, 8: 1},  # Year 3
    ])

    # Constants
    TOTAL_WEEKS: int = 18  # 17 games + 1 bye per team
    TOTAL_TEAMS: int = 32
    TOTAL_GAMES: int = 272  # 17 games per team * 32 teams / 2
    GAMES_PER_WEEK: int = 16  # 32 teams / 2 (when no bye weeks)

    # Bye week constants (Milestone 11, Tollgate 3)
    BYE_WEEK_START: int = 5
    BYE_WEEK_END: int = 14
    MAX_TEAMS_PER_BYE: int = 4
    MAX_DIVISION_PER_BYE: int = 2  # Soft constraint: spread division byes

    # Internal tracking
    home_counts: Dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(1, 33)})
    away_counts: Dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(1, 33)})
    _teams_data: Dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize database connections and load team data."""
        self._db = GameCycleDatabase(self.db_path)
        self._rotation_api = ScheduleRotationAPI(self._db)
        self._standings_api = StandingsAPI(self._db)
        self._load_teams_data()
        self._load_static_schedules()

    def _load_teams_data(self) -> None:
        """Load team data from JSON file."""
        teams_path = Path(__file__).parent.parent.parent / "data" / "teams.json"
        with open(teams_path, 'r') as f:
            self._teams_data = json.load(f).get("teams", {})

    def _load_static_schedules(self) -> None:
        """Load pre-defined static schedules (like the real 2025 NFL schedule)."""
        self._static_schedules: Dict[int, dict] = {}
        schedules_dir = Path(__file__).parent.parent.parent / "config" / "schedules"
        if schedules_dir.exists():
            for schedule_file in schedules_dir.glob("nfl_*_schedule.json"):
                with open(schedule_file, 'r') as f:
                    schedule_data = json.load(f)
                    season = schedule_data.get("season")
                    if season:
                        self._static_schedules[season] = schedule_data

    def _generate_from_static_schedule(self, season: int) -> List[Dict]:
        """
        Generate schedule from pre-defined static data (e.g., real 2025 NFL schedule).

        Args:
            season: Year of the season

        Returns:
            List of game event dicts ready for events_insert_batch()
        """
        schedule_data = self._static_schedules[season]
        team_abbr_to_id = schedule_data["teams"]
        games = schedule_data["games"]
        bye_weeks_raw = schedule_data.get("bye_weeks", {})

        # Convert bye weeks from abbr to team_id
        bye_assignments: Dict[int, int] = {}
        for week_str, teams in bye_weeks_raw.items():
            week = int(week_str)
            for abbr in teams:
                team_id = team_abbr_to_id.get(abbr)
                if team_id:
                    bye_assignments[team_id] = week

        # Save bye weeks to database (skip validation for static schedules since they're official)
        self._save_bye_weeks(season, bye_assignments, validate=False)

        # Group games by week and create Matchup objects
        weekly_schedule: Dict[int, List[Matchup]] = {w: [] for w in range(1, self.TOTAL_WEEKS + 1)}

        for game in games:
            week = game["week"]
            away_id = team_abbr_to_id[game["away"]]
            home_id = team_abbr_to_id[game["home"]]

            # Determine if this is a divisional/conference game
            away_div = self._get_division_id(away_id)
            home_div = self._get_division_id(home_id)
            is_divisional = away_div == home_div
            is_conference = self._same_conference(away_div, home_div)

            matchup = Matchup(
                home_team_id=home_id,
                away_team_id=away_id,
                is_divisional=is_divisional,
                is_conference=is_conference,
                week=week
            )
            weekly_schedule[week].append(matchup)

        # Convert to game events
        print(f"[NFLScheduleGenerator] Converting {len(games)} games to events...")
        game_events = self._convert_to_events(weekly_schedule, season)

        print(f"[NFLScheduleGenerator] Generated {len(game_events)} games for season {season}")
        return game_events

    def _get_division_id(self, team_id: int) -> int:
        """Get the division ID for a team."""
        for div_id, teams in self.DIVISIONS.items():
            if team_id in teams:
                return div_id
        return 0

    def _same_conference(self, div1: int, div2: int) -> bool:
        """Check if two divisions are in the same conference."""
        # AFC: divisions 1-4, NFC: divisions 5-8
        return (div1 <= 4 and div2 <= 4) or (div1 >= 5 and div2 >= 5)

    def generate_schedule(self, season: int) -> List[Dict]:
        """
        Generate complete NFL-compliant schedule for a season.

        Uses static schedule data if available (e.g., the real 2025 NFL schedule),
        otherwise falls back to algorithmic generation.

        Args:
            season: Year of the season (e.g., 2025)

        Returns:
            List of game event dicts ready for events_insert_batch()
        """
        print(f"[NFLScheduleGenerator] Generating schedule for season {season}")

        # Check if we have a static schedule for this season
        if season in self._static_schedules:
            print(f"[NFLScheduleGenerator] Using static {season} NFL schedule")
            return self._generate_from_static_schedule(season)

        print(f"[NFLScheduleGenerator] No static schedule found, generating algorithmically")

        # Retry loop - if bye week assignment creates unschedulable config, retry
        max_schedule_attempts = 10
        last_error = None

        for schedule_attempt in range(max_schedule_attempts):
            # Reset counters
            self.home_counts = {i: 0 for i in range(1, 33)}
            self.away_counts = {i: 0 for i in range(1, 33)}

            # Step 0: Assign bye weeks FIRST (Milestone 11, Tollgate 3)
            print(f"[NFLScheduleGenerator] Assigning bye weeks...")
            bye_assignments = self._assign_bye_weeks()
            print(f"[NFLScheduleGenerator]   Bye weeks assigned for all 32 teams")

            matchups: List[Matchup] = []

            # Step 1: Generate all matchups
            print(f"[NFLScheduleGenerator] Assigning division games...")
            division_matchups = self._assign_division_games()
            matchups.extend(division_matchups)
            print(f"[NFLScheduleGenerator]   Created {len(division_matchups)} division games")

            print(f"[NFLScheduleGenerator] Assigning in-conference rotation games...")
            conference_matchups = self._assign_conference_rotation(season)
            matchups.extend(conference_matchups)
            print(f"[NFLScheduleGenerator]   Created {len(conference_matchups)} conference rotation games")

            print(f"[NFLScheduleGenerator] Assigning cross-conference rotation games...")
            cross_conf_matchups = self._assign_cross_conference_rotation(season)
            matchups.extend(cross_conf_matchups)
            print(f"[NFLScheduleGenerator]   Created {len(cross_conf_matchups)} cross-conference games")

            print(f"[NFLScheduleGenerator] Assigning same-place finisher games...")
            same_place_matchups = self._assign_same_place_finishers(season)
            matchups.extend(same_place_matchups)
            print(f"[NFLScheduleGenerator]   Created {len(same_place_matchups)} same-place finisher games")

            print(f"[NFLScheduleGenerator] Assigning 17th game matchups...")
            game_17_matchups = self._assign_17th_game(season)
            matchups.extend(game_17_matchups)
            print(f"[NFLScheduleGenerator]   Created {len(game_17_matchups)} 17th game matchups")

            # Validate total matchups
            if len(matchups) != self.TOTAL_GAMES:
                raise ValueError(f"Expected {self.TOTAL_GAMES} games, got {len(matchups)}")

            # Step 2: Balance home/away
            print(f"[NFLScheduleGenerator] Balancing home/away assignments...")
            matchups = self._balance_home_away(matchups)

            # Step 3: Distribute to weeks (with bye week consideration)
            print(f"[NFLScheduleGenerator] Distributing games to weeks (with byes)...")
            try:
                weekly_schedule = self._distribute_to_weeks_with_byes(matchups, bye_assignments)
                # Success! Save bye weeks and break out of retry loop
                self._save_bye_weeks(season, bye_assignments)
                break
            except ValueError as e:
                last_error = e
                if schedule_attempt < max_schedule_attempts - 1:
                    print(f"[NFLScheduleGenerator] Distribution failed (attempt {schedule_attempt + 1}/{max_schedule_attempts}), retrying with new bye assignments...")
                    continue
                else:
                    raise ValueError(
                        f"Cannot generate schedule after {max_schedule_attempts} attempts. "
                        f"Last error: {last_error}"
                    )

        # Step 4: Convert to game events
        print(f"[NFLScheduleGenerator] Converting to game events...")
        game_events = self._convert_to_events(weekly_schedule, season)

        # Step 5: Save rotation state
        print(f"[NFLScheduleGenerator] Saving rotation state...")
        self._save_rotation_state(season)

        print(f"[NFLScheduleGenerator] Generated {len(game_events)} games for season {season}")
        return game_events

    # -------------------- Matchup Generation --------------------

    def _assign_division_games(self) -> List[Matchup]:
        """
        Generate division games (6 per team, 96 total).

        Each team plays division rivals twice (home + away).

        Returns:
            List of 96 Matchup objects
        """
        matchups = []

        for division_id, teams in self.DIVISIONS.items():
            # For each division, generate round-robin (home + away)
            for i, team_a in enumerate(teams):
                for team_b in teams[i + 1:]:
                    # Home game for team_a
                    matchups.append(Matchup(
                        home_team_id=team_a,
                        away_team_id=team_b,
                        is_divisional=True,
                        is_conference=True
                    ))

                    # Away game for team_a (home for team_b)
                    matchups.append(Matchup(
                        home_team_id=team_b,
                        away_team_id=team_a,
                        is_divisional=True,
                        is_conference=True
                    ))

        if len(matchups) != 96:
            raise ValueError(f"Expected 96 division games, got {len(matchups)}")

        return matchups

    def _generate_cross_division_matchups(
        self,
        own_division_id: int,
        opponent_division_id: int,
        season: int,
        is_conference: bool
    ) -> List[Matchup]:
        """Generate all matchups between two divisions (4 per team, 16 total)."""
        matchups = []
        own_teams = self.DIVISIONS[own_division_id]
        opponent_teams = self.DIVISIONS[opponent_division_id]

        for own_team in own_teams:
            for opp_team in opponent_teams:
                if (season + own_team) % 2 == 0:
                    home, away = own_team, opp_team
                else:
                    home, away = opp_team, own_team

                matchups.append(Matchup(
                    home_team_id=home,
                    away_team_id=away,
                    is_divisional=False,
                    is_conference=is_conference
                ))

        return matchups

    def _assign_conference_rotation(self, season: int) -> List[Matchup]:
        """
        Generate in-conference rotation games (4 per team, 64 total).

        Each division plays one other in-conference division on 3-year rotation.

        Args:
            season: Current season year

        Returns:
            List of 64 Matchup objects
        """
        matchups = []
        processed_pairs: Set[Tuple[int, int]] = set()

        for division_id in self.DIVISIONS.keys():
            # Get opponent division from rotation
            opponent_div = self._get_in_conference_opponent_div(division_id, season)

            # Skip if already processed this pair
            pair = tuple(sorted([division_id, opponent_div]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            # Generate all matchups between divisions
            matchups.extend(
                self._generate_cross_division_matchups(
                    division_id, opponent_div, season, is_conference=True
                )
            )

        if len(matchups) != 64:
            raise ValueError(f"Expected 64 conference rotation games, got {len(matchups)}")

        return matchups

    def _assign_cross_conference_rotation(self, season: int) -> List[Matchup]:
        """
        Generate cross-conference rotation games (4 per team, 64 total).

        Each division plays one opposite-conference division on 4-year rotation.

        Args:
            season: Current season year

        Returns:
            List of 64 Matchup objects
        """
        matchups = []
        processed_pairs: Set[Tuple[int, int]] = set()

        for division_id in self.DIVISIONS.keys():
            # Get opponent division from rotation
            opponent_div = self._get_cross_conference_opponent_div(division_id, season)

            # Skip if already processed this pair
            pair = tuple(sorted([division_id, opponent_div]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            # Generate all matchups between divisions
            matchups.extend(
                self._generate_cross_division_matchups(
                    division_id, opponent_div, season, is_conference=False
                )
            )

        if len(matchups) != 64:
            raise ValueError(f"Expected 64 cross-conference games, got {len(matchups)}")

        return matchups

    def _assign_same_place_finishers(self, season: int) -> List[Matchup]:
        """
        Generate same-place finisher games (2 per team, 32 total).

        Teams play 2 opponents from remaining in-conference divisions
        based on prior year divisional finish.

        Args:
            season: Current season year

        Returns:
            List of 32 Matchup objects

        Note:
            For first season (no prior standings), uses default ordering (team_id).
        """
        matchups = []
        processed_pairs: Set[Tuple[int, int]] = set()

        # Get prior season standings
        standings = self._get_divisional_standings(season - 1)

        for division_id in self.DIVISIONS.keys():
            # Get the 2 in-conference divisions NOT played in rotation
            rotation_opponent = self._get_in_conference_opponent_div(division_id, season)
            conference_divs = self._get_conference_divisions(division_id)
            conference_divs.remove(division_id)  # Remove own
            conference_divs.remove(rotation_opponent)  # Remove rotation opponent

            # Now have 2 remaining divisions
            if len(conference_divs) != 2:
                raise ValueError(f"Expected 2 remaining divisions, got {len(conference_divs)}")

            # Get this division's teams ranked by prior year finish
            own_teams_ranked = standings.get(division_id, self.DIVISIONS[division_id])

            # Match teams by divisional finish (1st vs 1st, 2nd vs 2nd, etc.)
            for rank in range(4):  # 4 teams per division
                own_team = own_teams_ranked[rank]

                # Play rank-matched team from each of the 2 divisions
                for other_div in conference_divs:
                    other_teams_ranked = standings.get(other_div, self.DIVISIONS[other_div])
                    other_team = other_teams_ranked[rank]

                    # Skip if already processed
                    pair = tuple(sorted([own_team, other_team]))
                    if pair in processed_pairs:
                        continue
                    processed_pairs.add(pair)

                    # Determine home/away (alternates by season)
                    if (season + own_team) % 2 == 0:
                        home, away = own_team, other_team
                    else:
                        home, away = other_team, own_team

                    matchups.append(Matchup(
                        home_team_id=home,
                        away_team_id=away,
                        is_divisional=False,
                        is_conference=True
                    ))

        if len(matchups) != 32:
            raise ValueError(f"Expected 32 same-place finisher games, got {len(matchups)}")

        return matchups

    def _assign_17th_game(self, season: int) -> List[Matchup]:
        """
        Generate 17th game matchups (1 per team, 16 total).

        Each team plays one cross-conference opponent based on divisional finish.
        Uses proper pairing to ensure symmetric matchups.

        The 17th game pairs divisions NOT involved in cross-conference rotation:
        If cross-conf rotation year is Year N (0-3), then 17th game uses Year (N+1) % 4 pairing

        Args:
            season: Current season year

        Returns:
            List of 16 Matchup objects
        """
        matchups = []

        # Get prior season standings
        standings = self._get_divisional_standings(season - 1)

        # Get the 17th game pairings (different from cross-conference rotation)
        # Use the next cross-conference pairing cycle
        game17_pairings = self._get_17th_game_pairings(season)

        # Only process AFC divisions (1-4) to avoid double-counting
        for afc_div in range(1, 5):
            nfc_div = game17_pairings[afc_div]

            # Match teams by divisional finish
            afc_teams_ranked = standings.get(afc_div, self.DIVISIONS[afc_div])
            nfc_teams_ranked = standings.get(nfc_div, self.DIVISIONS[nfc_div])

            for rank in range(4):
                afc_team = afc_teams_ranked[rank]
                nfc_team = nfc_teams_ranked[rank]

                # Determine home/away (AFC home in even years)
                if season % 2 == 0:
                    home, away = afc_team, nfc_team
                else:
                    home, away = nfc_team, afc_team

                matchups.append(Matchup(
                    home_team_id=home,
                    away_team_id=away,
                    is_divisional=False,
                    is_conference=False
                ))

        if len(matchups) != 16:
            raise ValueError(f"Expected 16 17th games, got {len(matchups)}")

        return matchups

    def _get_17th_game_pairings(self, season: int) -> Dict[int, int]:
        """
        Get the AFC-NFC division pairings for the 17th game.

        The 17th game uses a pairing that's offset from the cross-conference rotation.
        This ensures teams play an opponent from a different NFC division than their
        cross-conference rotation opponent.

        Args:
            season: Season year

        Returns:
            Dict mapping AFC division (1-4) to NFC division (5-8)
        """
        # Cross-conference rotation index
        cross_conf_index = season % 4

        # 17th game uses a different rotation (offset by 1 or 2)
        # This ensures the 17th game opponent is from a different division
        # than the cross-conference rotation opponent
        game17_index = (cross_conf_index + 1) % 4

        # Same pairing structure as cross-conference but with different offset
        game17_pairings = [
            {1: 5, 2: 6, 3: 7, 4: 8},  # Year 0: East-East, North-North, etc.
            {1: 6, 2: 7, 3: 8, 4: 5},  # Year 1
            {1: 7, 2: 8, 3: 5, 4: 6},  # Year 2
            {1: 8, 2: 5, 3: 6, 4: 7},  # Year 3
        ]

        return game17_pairings[game17_index]

    # -------------------- Rotation Helpers --------------------

    def _get_in_conference_opponent_div(self, division_id: int, season: int) -> int:
        """Get in-conference opponent division (3-year rotation)."""
        conference = 'AFC' if division_id <= 4 else 'NFC'
        rotation_index = season % 3
        return self.IN_CONFERENCE_PAIRINGS[conference][rotation_index][division_id]

    def _get_cross_conference_opponent_div(self, division_id: int, season: int) -> int:
        """Get cross-conference opponent division (4-year rotation)."""
        rotation_index = season % 4
        return self.CROSS_CONFERENCE_PAIRINGS[rotation_index][division_id]

    def _get_conference_divisions(self, division_id: int) -> List[int]:
        """Get all divisions in same conference."""
        if division_id <= 4:
            return [1, 2, 3, 4]  # AFC
        else:
            return [5, 6, 7, 8]  # NFC

    def _get_opposite_conference_divisions(self, division_id: int) -> List[int]:
        """Get all divisions in opposite conference."""
        if division_id <= 4:
            return [5, 6, 7, 8]  # NFC
        else:
            return [1, 2, 3, 4]  # AFC

    def _get_divisional_standings(self, season: int) -> Dict[int, List[int]]:
        """
        Get prior season divisional standings.

        Args:
            season: Season year to get standings for

        Returns:
            Dict mapping division_id -> list of team_ids (ranked 1st to 4th)
        """
        standings: Dict[int, List[int]] = {}

        for division_id, teams in self.DIVISIONS.items():
            # Query standings for these teams
            team_records = []
            for team_id in teams:
                standing = self._standings_api.get_team_standing(
                    self.dynasty_id, season, team_id
                )
                if standing:
                    team_records.append((team_id, standing.win_percentage, standing.wins))
                else:
                    # No record found - use default (0 wins)
                    team_records.append((team_id, 0.0, 0))

            # Sort by win percentage, then wins, then team_id for stability
            team_records.sort(key=lambda x: (-x[1], -x[2], x[0]))

            # Extract team IDs in ranked order
            standings[division_id] = [t[0] for t in team_records]

        return standings

    def _get_team_division(self, team_id: int) -> int:
        """Get division ID for a team."""
        for div_id, teams in self.DIVISIONS.items():
            if team_id in teams:
                return div_id
        raise ValueError(f"Team {team_id} not found in any division")

    # -------------------- Balancing & Distribution --------------------

    def _balance_home_away(self, matchups: List[Matchup]) -> List[Matchup]:
        """
        Balance home/away games to ensure 8-9 or 9-8 split per team.

        Iteratively flips matchups to achieve balance.

        Args:
            matchups: List of all matchups

        Returns:
            Balanced list of matchups
        """
        # Count current home/away
        for m in matchups:
            self.home_counts[m.home_team_id] += 1
            self.away_counts[m.away_team_id] += 1

        # Identify teams needing adjustment and perform swaps
        max_iterations = 1000
        iteration = 0

        while iteration < max_iterations:
            needs_adjustment = False

            for team_id in range(1, 33):
                home_count = self.home_counts[team_id]
                away_count = self.away_counts[team_id]

                # Should be 8-9 or 9-8
                if home_count > 9:
                    needs_adjustment = True
                    # Find a matchup to flip (this team is home, needs to be away)
                    for m in matchups:
                        if m.home_team_id == team_id and not m.is_divisional:
                            other_team = m.away_team_id
                            # Check if other team can accept being away
                            if self.home_counts[other_team] < 9:
                                # Flip
                                m.home_team_id, m.away_team_id = m.away_team_id, m.home_team_id
                                self.home_counts[team_id] -= 1
                                self.away_counts[team_id] += 1
                                self.home_counts[other_team] += 1
                                self.away_counts[other_team] -= 1
                                break

                elif away_count > 9:
                    needs_adjustment = True
                    # Find a matchup to flip (this team is away, needs to be home)
                    for m in matchups:
                        if m.away_team_id == team_id and not m.is_divisional:
                            other_team = m.home_team_id
                            # Check if other team can accept being home
                            if self.away_counts[other_team] < 9:
                                # Flip
                                m.home_team_id, m.away_team_id = m.away_team_id, m.home_team_id
                                self.home_counts[team_id] += 1
                                self.away_counts[team_id] -= 1
                                self.home_counts[other_team] -= 1
                                self.away_counts[other_team] += 1
                                break

            if not needs_adjustment:
                break

            iteration += 1

        # Verify all teams have valid split
        for team_id in range(1, 33):
            home = self.home_counts[team_id]
            away = self.away_counts[team_id]
            if (home, away) not in [(8, 9), (9, 8)]:
                print(f"[NFLScheduleGenerator] Warning: Team {team_id} has {home} home, {away} away (expected 8-9 or 9-8)")

        return matchups

    def _distribute_to_weeks(self, matchups: List[Matchup]) -> Dict[int, List[Matchup]]:
        """
        Distribute 272 matchups across 17 weeks (16 games/week).

        Uses retry-based algorithm with different random orderings.

        Constraints:
        - No team plays multiple games in same week
        - Each week has exactly 16 games

        Args:
            matchups: List of all 272 matchups

        Returns:
            Dict mapping week -> list of matchups
        """
        max_attempts = 100

        for attempt in range(max_attempts):
            result = self._try_distribute(matchups, attempt)
            if result is not None:
                return result

            # Reset matchup weeks for next attempt
            for m in matchups:
                m.week = 0

        raise ValueError(
            f"Cannot distribute matchups to weeks after {max_attempts} attempts"
        )

    def _try_distribute(
        self,
        matchups: List[Matchup],
        attempt: int
    ) -> Optional[Dict[int, List[Matchup]]]:
        """
        Single attempt to distribute matchups to weeks.

        Uses constraint-based ordering: most-constrained matchups first.
        """
        # Track team availability per week
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}
        week_games: Dict[int, List[Matchup]] = {w: [] for w in range(1, 18)}

        def can_assign(m: Matchup, week: int) -> bool:
            if len(week_games[week]) >= self.GAMES_PER_WEEK:
                return False
            if week in team_week[m.home_team_id]:
                return False
            if week in team_week[m.away_team_id]:
                return False
            return True

        def assign(m: Matchup, week: int) -> None:
            m.week = week
            week_games[week].append(m)
            team_week[m.home_team_id].add(week)
            team_week[m.away_team_id].add(week)

        def unassign(m: Matchup) -> None:
            if m.week == 0:
                return
            week = m.week
            m.week = 0
            week_games[week].remove(m)
            team_week[m.home_team_id].discard(week)
            team_week[m.away_team_id].discard(week)

        def count_available_weeks(m: Matchup) -> int:
            return sum(1 for w in range(1, 18) if can_assign(m, w))

        # Shuffle matchups with variation based on attempt
        random.seed(attempt * 12345)  # Deterministic but varied
        shuffled = list(matchups)
        random.shuffle(shuffled)

        # Sort by constraint level (most constrained first)
        # Division games are most constrained, then by team "busyness"
        def constraint_key(m: Matchup) -> Tuple[int, int, int]:
            # Priority: division games, then fewest available weeks
            div_priority = 0 if m.is_divisional else 1
            available = count_available_weeks(m)
            # Add small random factor to break ties differently each attempt
            rand_factor = hash((m.home_team_id, m.away_team_id, attempt)) % 100
            return (div_priority, available, rand_factor)

        # Re-sort periodically during assignment to update constraints
        remaining = sorted(shuffled, key=constraint_key)

        while remaining:
            # Take most constrained matchup
            game = remaining.pop(0)

            available_weeks = [w for w in range(1, 18) if can_assign(game, w)]

            if available_weeks:
                # Choose week that keeps schedule balanced
                week = min(available_weeks, key=lambda w: len(week_games[w]))
                assign(game, week)

                # Re-sort remaining every 50 games to update constraint ordering
                if len(remaining) % 50 == 0 and remaining:
                    remaining.sort(key=constraint_key)
            else:
                # Can't place this game - try swapping
                placed = self._try_swap_placement(
                    game, week_games, team_week,
                    assign, unassign, can_assign
                )

                if not placed:
                    return None  # This attempt failed

        # Verify completeness
        for week in range(1, 18):
            if len(week_games[week]) != 16:
                return None

        return week_games

    def _try_swap_placement(
        self,
        game: Matchup,
        week_games: Dict[int, List[Matchup]],
        team_week: Dict[int, Set[int]],
        assign: Callable[[Matchup, int], None],
        unassign: Callable[[Matchup], None],
        can_assign: Callable[[Matchup, int], bool]
    ) -> bool:
        """
        Try to place a game by swapping with existing games.

        Uses 2-level chain swapping.
        """
        for target_week in range(1, 18):
            if len(week_games[target_week]) >= self.GAMES_PER_WEEK:
                continue

            # Find games blocking this matchup in target_week
            blockers = []
            if target_week in team_week[game.home_team_id]:
                for m in week_games[target_week]:
                    if game.home_team_id in (m.home_team_id, m.away_team_id):
                        blockers.append(m)
                        break

            if target_week in team_week[game.away_team_id]:
                for m in week_games[target_week]:
                    if game.away_team_id in (m.home_team_id, m.away_team_id):
                        if m not in blockers:
                            blockers.append(m)
                        break

            # Try moving blockers to make room
            for blocker in blockers:
                orig_week = blocker.week
                unassign(blocker)

                if can_assign(game, target_week):
                    # Find new spot for blocker
                    for alt_week in range(1, 18):
                        if can_assign(blocker, alt_week):
                            assign(game, target_week)
                            assign(blocker, alt_week)
                            return True

                    # Try 2-level chain: move blocker by displacing another game
                    for alt_week in range(1, 18):
                        if len(week_games[alt_week]) >= self.GAMES_PER_WEEK:
                            continue

                        for displaced in list(week_games[alt_week]):
                            unassign(displaced)

                            if can_assign(blocker, alt_week):
                                for final_week in range(1, 18):
                                    if can_assign(displaced, final_week):
                                        assign(game, target_week)
                                        assign(blocker, alt_week)
                                        assign(displaced, final_week)
                                        return True

                            assign(displaced, alt_week)

                # Revert if couldn't place
                assign(blocker, orig_week)

        return False

    # -------------------- Event Conversion --------------------

    def _convert_to_events(
        self,
        weekly_schedule: Dict[int, List[Matchup]],
        season: int
    ) -> List[Dict]:
        """
        Convert matchups to game event dicts.

        Args:
            weekly_schedule: Dict mapping week -> list of matchups
            season: Season year

        Returns:
            List of game event dicts ready for events_insert_batch()
        """
        events = []

        # Calculate season start date (first Thursday after Labor Day)
        season_start = self._calculate_season_start(season)

        # Build team info for conference/division lookup
        team_info = self._build_team_info()

        for week in range(1, self.TOTAL_WEEKS + 1):
            week_matchups = weekly_schedule.get(week, [])

            # Calculate week start date
            week_start = season_start + timedelta(days=(week - 1) * 7)

            for game_num, matchup in enumerate(week_matchups, 1):
                game_id = f"regular_{season}_{week}_{game_num}"
                event_id = str(uuid.uuid4())

                # Calculate game datetime (Sunday 1pm for simplicity)
                game_date = week_start + timedelta(days=3)  # Thursday + 3 = Sunday
                game_date = game_date.replace(hour=13, minute=0, second=0, microsecond=0)

                # Get team info for metadata
                home_conf = team_info.get(matchup.home_team_id, {}).get("conference", "Unknown")
                away_conf = team_info.get(matchup.away_team_id, {}).get("conference", "Unknown")

                event = {
                    "event_id": event_id,
                    "event_type": "GAME",
                    "timestamp": int(game_date.timestamp() * 1000),
                    "game_id": game_id,
                    "data": {
                        "parameters": {
                            "away_team_id": matchup.away_team_id,
                            "home_team_id": matchup.home_team_id,
                            "week": week,
                            "season": season,
                            "season_type": "regular_season",
                            "game_type": "regular",
                            "game_date": game_date.isoformat(),
                            "overtime_type": "regular_season"
                        },
                        "results": None,
                        "metadata": {
                            "matchup_description": f"Week {week}: Team {matchup.away_team_id} @ Team {matchup.home_team_id}",
                            "is_playoff_game": False,
                            "is_divisional": matchup.is_divisional,
                            "is_conference": matchup.is_conference
                        }
                    }
                }

                events.append(event)

        return events

    def _calculate_season_start(self, season: int) -> datetime:
        """
        Calculate NFL regular season start date.

        The NFL season starts the Thursday after Labor Day.
        Labor Day is the first Monday in September.

        Args:
            season: Season year

        Returns:
            datetime of first regular season game
        """
        # Start with September 1st of the season year
        sept_1 = datetime(season, 9, 1)

        # Find Labor Day (first Monday in September)
        weekday = sept_1.weekday()
        if weekday == 0:  # Sept 1 is Monday
            days_until_monday = 0
        else:
            days_until_monday = (7 - weekday) % 7

        labor_day = sept_1 + timedelta(days=days_until_monday)

        # Season starts Thursday after Labor Day
        season_start = labor_day + timedelta(days=3)
        return season_start.replace(hour=20, minute=0, second=0, microsecond=0)

    def _build_team_info(self) -> Dict[int, Dict[str, str]]:
        """Build team conference/division lookup."""
        team_info = {}
        for team_id_str, team in self._teams_data.items():
            team_info[team["team_id"]] = {
                "conference": team["conference"],
                "division": team["division"]
            }
        return team_info

    def _save_rotation_state(self, season: int) -> None:
        """
        Save rotation state to database for record keeping.

        Args:
            season: Season year
        """
        for division_id in self.DIVISIONS.keys():
            in_conf = self._get_in_conference_opponent_div(division_id, season)
            cross_conf = self._get_cross_conference_opponent_div(division_id, season)

            self._rotation_api.save_rotation_state(
                dynasty_id=self.dynasty_id,
                season=season,
                division_id=division_id,
                in_conference_opponent_div=in_conf,
                cross_conference_opponent_div=cross_conf
            )

    # -------------------- Bye Week Assignment (Milestone 11, Tollgate 3) --------------------

    def _assign_bye_weeks(self) -> Dict[int, int]:
        """
        Assign bye weeks for all 32 teams.

        Algorithm:
            1. Process divisions in random order to avoid bias
            2. For each team, find optimal bye week using scoring
            3. Constraints: max 4 per week, max 2 per division per week

        Returns:
            Dict mapping team_id -> bye_week (5-14)
        """
        bye_assignments: Dict[int, int] = {}
        week_counts: Dict[int, int] = {w: 0 for w in range(self.BYE_WEEK_START, self.BYE_WEEK_END + 1)}
        division_week_counts: Dict[int, Dict[int, int]] = {
            d: {w: 0 for w in range(self.BYE_WEEK_START, self.BYE_WEEK_END + 1)}
            for d in self.DIVISIONS.keys()
        }

        # Process divisions in random order to avoid bias
        divisions = list(self.DIVISIONS.items())
        random.shuffle(divisions)

        for div_id, teams in divisions:
            # Shuffle teams within division
            team_list = list(teams)
            random.shuffle(team_list)

            for team_id in team_list:
                # Find best bye week for this team
                bye_week = self._find_best_bye_week(
                    team_id, div_id, week_counts, division_week_counts
                )

                bye_assignments[team_id] = bye_week
                week_counts[bye_week] += 1
                division_week_counts[div_id][bye_week] += 1

        return bye_assignments

    def _calculate_bye_week_score(
        self,
        week: int,
        current_count: int,
        division_id: int,
        division_week_counts: Dict[int, Dict[int, int]],
        weeks_at_two: int
    ) -> float:
        """Calculate score for assigning a bye to a specific week (lower = better)."""
        score = 0.0
        new_count = current_count + 1

        if new_count > self.MAX_TEAMS_PER_BYE:
            score += 1000
        if division_week_counts[division_id][week] >= self.MAX_DIVISION_PER_BYE:
            score += 500
        if new_count in (1, 3):
            score += 100
        if current_count == 2 and weeks_at_two >= 4:
            score += 80
        score += current_count * 15
        score += random.uniform(0, 5)

        return score

    def _find_best_bye_week(
        self,
        team_id: int,
        division_id: int,
        week_counts: Dict[int, int],
        division_week_counts: Dict[int, Dict[int, int]]
    ) -> int:
        """
        Find optimal bye week for a team using scoring.

        CRITICAL: We need EVEN numbers of byes per week to get integer games.
        - 2 byes → 30 teams → 15 games
        - 4 byes → 28 teams → 14 games
        - 3 byes → 29 teams → 14 games (loses 1 team slot!)

        Target distribution: 4 weeks with 2 byes + 6 weeks with 4 byes = 144 bye week games

        Scoring criteria (lower = better):
        - Week at capacity (4 teams): +1000 (hard constraint)
        - Division already has 2+ teams on this bye: +500 (soft constraint)
        - Odd bye count (1 or 3): +100 (prefer even counts for optimal scheduling)
        - Balance: prefer weeks with fewer teams

        Args:
            team_id: Team to assign
            division_id: Team's division
            week_counts: Current teams per bye week
            division_week_counts: Current division teams per bye week

        Returns:
            Best bye week (5-14)
        """
        best_week = self.BYE_WEEK_START
        best_score = float('inf')

        # Count how many weeks already have 2 byes (those should stay at 2)
        weeks_at_two = sum(1 for c in week_counts.values() if c == 2)

        for week in range(self.BYE_WEEK_START, self.BYE_WEEK_END + 1):
            score = self._calculate_bye_week_score(
                week, week_counts[week], division_id, division_week_counts, weeks_at_two
            )

            if score < best_score:
                best_score = score
                best_week = week

        return best_week

    def _save_bye_weeks(
        self,
        season: int,
        bye_assignments: Dict[int, int],
        validate: bool = True
    ) -> None:
        """
        Persist bye week assignments to database.

        Args:
            season: Season year
            bye_assignments: Dict mapping team_id -> bye_week
            validate: Whether to validate constraints (skip for official NFL schedules)
        """
        from ..database.bye_week_api import ByeWeekAPI

        bye_api = ByeWeekAPI(self._db)
        bye_api.save_bye_weeks(self.dynasty_id, season, bye_assignments, validate=validate)

    def _distribute_to_weeks_with_byes(
        self,
        matchups: List[Matchup],
        bye_assignments: Dict[int, int]
    ) -> Dict[int, List[Matchup]]:
        """
        Distribute 272 matchups across 18 weeks respecting bye weeks.

        Key changes from _distribute_to_weeks:
        - Teams cannot play during their bye week
        - Games per week varies (14-16 depending on byes)
        - Week capacity = (32 - teams_on_bye) / 2
        - Uses MCV greedy first, then full backtracking as fallback

        Args:
            matchups: List of all 272 matchups
            bye_assignments: Dict mapping team_id -> bye_week

        Returns:
            Dict mapping week -> list of matchups
        """
        # Try MCV greedy first (fast path)
        for attempt in range(50):
            for m in matchups:
                m.week = 0

            result, unassigned = self._greedy_with_unassigned(
                matchups, bye_assignments, attempt
            )

            if not unassigned and self._verify_no_conflicts(result):
                return result

        # Greedy failed, use full recursive backtracking (guaranteed to work)
        print("[NFLScheduleGenerator] Greedy failed, using full backtracking...")
        for attempt in range(10):
            for m in matchups:
                m.week = 0
            random.seed(attempt * 54321)

            result = self._full_backtracking(matchups, bye_assignments)
            if result is not None:
                return result

        raise ValueError(
            "Cannot distribute matchups with byes after greedy + backtracking attempts"
        )

    def _greedy_with_unassigned(
        self,
        matchups: List[Matchup],
        bye_assignments: Dict[int, int],
        attempt: int
    ) -> Tuple[Dict[int, List[Matchup]], List[Matchup]]:
        """
        Greedy assignment that always picks the most constrained game.

        Uses most-constrained-variable (MCV) heuristic: always place the game
        with the fewest available weeks first. This minimizes dead ends.

        Returns:
            Tuple of (week_games dict, list of unassigned games)
        """
        # Track team availability (includes bye weeks)
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}

        # Pre-mark bye weeks as unavailable
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)

        # Calculate week capacities
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            teams_on_bye = sum(1 for t, w in bye_assignments.items() if w == week)
            week_capacity[week] = (self.TOTAL_TEAMS - teams_on_bye) // 2

        week_games: Dict[int, List[Matchup]] = {w: [] for w in range(1, self.TOTAL_WEEKS + 1)}
        unassigned: List[Matchup] = []

        def can_assign(m: Matchup, week: int) -> bool:
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[m.home_team_id]:
                return False
            if week in team_week[m.away_team_id]:
                return False
            return True

        def assign(m: Matchup, week: int) -> None:
            m.week = week
            week_games[week].append(m)
            team_week[m.home_team_id].add(week)
            team_week[m.away_team_id].add(week)

        def count_available(m: Matchup) -> int:
            return sum(1 for w in range(1, self.TOTAL_WEEKS + 1) if can_assign(m, w))

        # Shuffle for variety on different attempts
        random.seed(attempt * 12345)
        remaining = list(matchups)
        random.shuffle(remaining)

        # MCV greedy: always pick the most constrained game
        while remaining:
            # Find game with fewest available weeks
            best_idx = 0
            best_count = count_available(remaining[0])
            for i in range(1, len(remaining)):
                count = count_available(remaining[i])
                if count < best_count:
                    best_count = count
                    best_idx = i

            game = remaining.pop(best_idx)

            if best_count == 0:
                unassigned.append(game)
                continue

            # Place in least-full available week
            available_weeks = [w for w in range(1, self.TOTAL_WEEKS + 1) if can_assign(game, w)]
            week = min(available_weeks, key=lambda w: len(week_games[w]))
            assign(game, week)

        return week_games, unassigned

    def _full_backtracking(
        self,
        matchups: List[Matchup],
        bye_assignments: Dict[int, int],
        max_iterations: int = 500000
    ) -> Optional[Dict[int, List[Matchup]]]:
        """
        Full recursive backtracking to place all 272 games.

        This is the reliable fallback when greedy fails. It guarantees
        finding a valid schedule if one exists by exploring the full
        search space with pruning.

        Args:
            matchups: All 272 matchups to place
            bye_assignments: Dict mapping team_id -> bye_week
            max_iterations: Max iterations before giving up

        Returns:
            Dict mapping week -> list of matchups, or None if failed
        """
        # Track team availability (includes bye weeks)
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)

        # Calculate week capacities
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            teams_on_bye = sum(1 for t, w in bye_assignments.items() if w == week)
            week_capacity[week] = (self.TOTAL_TEAMS - teams_on_bye) // 2

        week_games: Dict[int, List[Matchup]] = {w: [] for w in range(1, self.TOTAL_WEEKS + 1)}

        def can_place(game: Matchup, week: int) -> bool:
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[game.home_team_id]:
                return False
            if week in team_week[game.away_team_id]:
                return False
            return True

        def place(game: Matchup, week: int) -> None:
            game.week = week
            week_games[week].append(game)
            team_week[game.home_team_id].add(week)
            team_week[game.away_team_id].add(week)

        def unplace(game: Matchup) -> None:
            week = game.week
            game.week = 0
            week_games[week].remove(game)
            team_week[game.home_team_id].discard(week)
            team_week[game.away_team_id].discard(week)

        def count_available(game: Matchup) -> int:
            return sum(1 for w in range(1, self.TOTAL_WEEKS + 1) if can_place(game, w))

        # Sort games by constraint level (most constrained first - MCV heuristic)
        sorted_games = sorted(matchups, key=lambda g: count_available(g))

        iterations = [0]

        def backtrack(idx: int) -> bool:
            if iterations[0] >= max_iterations:
                return False
            iterations[0] += 1

            if idx >= len(sorted_games):
                return True  # All games placed!

            game = sorted_games[idx]

            # Try weeks in order (could optimize with least-constraining-value)
            for week in range(1, self.TOTAL_WEEKS + 1):
                if can_place(game, week):
                    place(game, week)
                    if backtrack(idx + 1):
                        return True
                    unplace(game)

            return False

        if backtrack(0):
            return week_games
        return None

    def _place_remaining_backtracking(
        self,
        games: List[Matchup],
        week_games: Dict[int, List[Matchup]],
        bye_assignments: Dict[int, int],
        max_iterations: int = 100000
    ) -> bool:
        """
        Use backtracking to place remaining unassigned games.

        Args:
            games: List of games to place
            week_games: Current week assignment (will be modified)
            bye_assignments: Bye week assignments
            max_iterations: Max iterations before giving up

        Returns:
            True if all games placed, False otherwise
        """
        if not games:
            return True

        # Build tracking from current state
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)
        for week, gms in week_games.items():
            for g in gms:
                team_week[g.home_team_id].add(week)
                team_week[g.away_team_id].add(week)

        # Calculate capacities
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            byes = sum(1 for t, w in bye_assignments.items() if w == week)
            week_capacity[week] = (self.TOTAL_TEAMS - byes) // 2

        def can_place(game: Matchup, week: int) -> bool:
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[game.home_team_id]:
                return False
            if week in team_week[game.away_team_id]:
                return False
            return True

        def place(game: Matchup, week: int) -> None:
            game.week = week
            week_games[week].append(game)
            team_week[game.home_team_id].add(week)
            team_week[game.away_team_id].add(week)

        def unplace(game: Matchup) -> None:
            week = game.week
            game.week = 0
            week_games[week].remove(game)
            team_week[game.home_team_id].discard(week)
            team_week[game.away_team_id].discard(week)

        # Iterative backtracking with stack
        stack: List[Tuple[int, int, Optional[int]]] = [(0, 1, None)]
        iterations = 0

        while stack and iterations < max_iterations:
            iterations += 1
            game_idx, next_week, placed_week = stack.pop()

            if placed_week is not None:
                unplace(games[game_idx])

            if game_idx >= len(games):
                return True

            game = games[game_idx]
            found_week = None
            for week in range(next_week, self.TOTAL_WEEKS + 1):
                if can_place(game, week):
                    found_week = week
                    break

            if found_week is not None:
                place(game, found_week)
                stack.append((game_idx, found_week + 1, found_week))
                stack.append((game_idx + 1, 1, None))

        return False

    def _repair_conflicts(
        self,
        week_games: Dict[int, List[Matchup]],
        bye_assignments: Dict[int, int]
    ) -> Optional[Dict[int, List[Matchup]]]:
        """
        Repair any team conflicts in a schedule by swapping games.

        Args:
            week_games: Dict mapping week -> list of matchups
            bye_assignments: Dict mapping team_id -> bye_week

        Returns:
            Repaired schedule dict, or None if repair failed
        """
        # Build tracking structures
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}

        # Pre-mark bye weeks
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)

        # Calculate week capacities
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            byes = sum(1 for t, w in bye_assignments.items() if w == week)
            week_capacity[week] = (self.TOTAL_TEAMS - byes) // 2

        # Build team_week from current schedule
        for week, games in week_games.items():
            for game in games:
                team_week[game.home_team_id].add(week)
                team_week[game.away_team_id].add(week)

        def can_place(game: Matchup, week: int) -> bool:
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[game.home_team_id]:
                return False
            if week in team_week[game.away_team_id]:
                return False
            return True

        def move_game(game: Matchup, from_week: int, to_week: int) -> None:
            week_games[from_week].remove(game)
            week_games[to_week].append(game)
            team_week[game.home_team_id].discard(from_week)
            team_week[game.away_team_id].discard(from_week)
            team_week[game.home_team_id].add(to_week)
            team_week[game.away_team_id].add(to_week)
            game.week = to_week

        # Find and fix conflicts (limit iterations to prevent infinite loops)
        max_repair_iterations = 1000
        for iteration in range(max_repair_iterations):
            # Find a conflict
            conflict_found = False
            for week in range(1, self.TOTAL_WEEKS + 1):
                teams_seen: Dict[int, Matchup] = {}
                for game in list(week_games[week]):
                    for team_id in [game.home_team_id, game.away_team_id]:
                        if team_id in teams_seen:
                            # Conflict found! Try to move this game
                            conflict_found = True

                            # Find alternative week for this game
                            original_week = week
                            # Temporarily remove game from tracking
                            week_games[week].remove(game)
                            team_week[game.home_team_id].discard(week)
                            team_week[game.away_team_id].discard(week)

                            moved = False
                            for alt_week in range(1, self.TOTAL_WEEKS + 1):
                                if alt_week == week:
                                    continue
                                if can_place(game, alt_week):
                                    # Move game to alternative week
                                    week_games[alt_week].append(game)
                                    team_week[game.home_team_id].add(alt_week)
                                    team_week[game.away_team_id].add(alt_week)
                                    game.week = alt_week
                                    moved = True
                                    break

                            if not moved:
                                # Try swapping with a game from another week
                                for alt_week in range(1, self.TOTAL_WEEKS + 1):
                                    if alt_week == week:
                                        continue
                                    for swap_game in list(week_games[alt_week]):
                                        # Can we swap?
                                        # Temporarily remove swap_game
                                        week_games[alt_week].remove(swap_game)
                                        team_week[swap_game.home_team_id].discard(alt_week)
                                        team_week[swap_game.away_team_id].discard(alt_week)

                                        if can_place(game, alt_week):
                                            # Put game in alt_week
                                            week_games[alt_week].append(game)
                                            team_week[game.home_team_id].add(alt_week)
                                            team_week[game.away_team_id].add(alt_week)
                                            game.week = alt_week

                                            # Try to place swap_game in original week
                                            # Re-add to tracking to check
                                            week_games[original_week].append(swap_game)
                                            team_week[swap_game.home_team_id].add(original_week)
                                            team_week[swap_game.away_team_id].add(original_week)
                                            swap_game.week = original_week
                                            moved = True
                                            break
                                        else:
                                            # Restore swap_game
                                            week_games[alt_week].append(swap_game)
                                            team_week[swap_game.home_team_id].add(alt_week)
                                            team_week[swap_game.away_team_id].add(alt_week)

                                    if moved:
                                        break

                            if not moved:
                                # Could not repair - restore and fail
                                week_games[week].append(game)
                                team_week[game.home_team_id].add(week)
                                team_week[game.away_team_id].add(week)
                                return None

                            break  # Restart conflict search after a move
                        teams_seen[team_id] = game

                    if conflict_found:
                        break
                if conflict_found:
                    break

            if not conflict_found:
                # No more conflicts - verify and return
                if self._verify_no_conflicts(week_games):
                    return week_games
                else:
                    # Should not happen, but safety check
                    return None

        # Max iterations reached
        return None

    def _verify_no_conflicts(self, week_games: Dict[int, List[Matchup]]) -> bool:
        """
        Verify no team plays twice in any week.

        Args:
            week_games: Dict mapping week -> list of matchups

        Returns:
            True if no conflicts, False otherwise
        """
        for week, games in week_games.items():
            teams = set()
            for game in games:
                if game.home_team_id in teams or game.away_team_id in teams:
                    return False
                teams.add(game.home_team_id)
                teams.add(game.away_team_id)
        return True

    def _distribute_backtracking(
        self,
        matchups: List[Matchup],
        bye_assignments: Dict[int, int],
        max_iterations: int = 500000
    ) -> Optional[Dict[int, List[Matchup]]]:
        """
        Distribute matchups using iterative backtracking - simpler and more reliable.

        Algorithm:
        1. Pre-compute week capacity and blocked weeks
        2. Use iterative stack-based approach (no recursion limit issues)
        3. Prioritize divisional games and most-constrained matchups dynamically
        4. Return first valid complete assignment

        Args:
            matchups: List of all 272 matchups
            bye_assignments: Dict mapping team_id -> bye_week
            max_iterations: Maximum iterations to prevent infinite loops

        Returns:
            Dict mapping week -> list of matchups, or None if failed
        """
        # Initialize tracking
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}
        week_games: Dict[int, List[Matchup]] = {w: [] for w in range(1, self.TOTAL_WEEKS + 1)}

        # Pre-mark bye weeks
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)

        # Calculate week capacities
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            byes = sum(1 for t, w in bye_assignments.items() if w == week)
            week_capacity[week] = (self.TOTAL_TEAMS - byes) // 2

        def can_place(game: Matchup, week: int) -> bool:
            """Check if game can be placed in week."""
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[game.home_team_id]:
                return False
            if week in team_week[game.away_team_id]:
                return False
            return True

        def place(game: Matchup, week: int) -> None:
            """Place game in week."""
            game.week = week
            week_games[week].append(game)
            team_week[game.home_team_id].add(week)
            team_week[game.away_team_id].add(week)

        def unplace(game: Matchup) -> None:
            """Remove game from its week."""
            week = game.week
            game.week = 0
            week_games[week].remove(game)
            team_week[game.home_team_id].discard(week)
            team_week[game.away_team_id].discard(week)

        def count_available(game: Matchup) -> int:
            """Count available weeks for a game."""
            return sum(1 for w in range(1, self.TOTAL_WEEKS + 1) if can_place(game, w))

        # Shuffle games first for variety, then sort by static priority
        # (divisional first, then other conference, then non-conference)
        game_list = list(matchups)
        random.shuffle(game_list)

        # Sort: divisional > conference > non-conference
        def static_priority(g: Matchup) -> int:
            if g.is_divisional:
                return 0
            elif g.is_conference:
                return 1
            else:
                return 2

        game_list.sort(key=static_priority)

        # Use iterative approach with explicit stack
        # Stack contains: (game_index, week_to_try_next, placed_week_or_none)
        stack: List[Tuple[int, int, Optional[int]]] = [(0, 1, None)]
        iterations = 0

        while stack and iterations < max_iterations:
            iterations += 1
            game_idx, next_week, placed_week = stack.pop()

            # If we placed a game, unplace it before trying next week
            if placed_week is not None:
                unplace(game_list[game_idx])

            # All games placed successfully
            if game_idx >= len(game_list):
                return week_games

            game = game_list[game_idx]

            # Find next valid week to try
            found_week = None
            for week in range(next_week, self.TOTAL_WEEKS + 2):
                if week > self.TOTAL_WEEKS:
                    break
                if can_place(game, week):
                    found_week = week
                    break

            if found_week is not None:
                # Place this game and push state for backtracking
                place(game, found_week)
                # Push backtrack state (try next week if we fail later)
                stack.append((game_idx, found_week + 1, found_week))
                # Push next game
                stack.append((game_idx + 1, 1, None))
            # If no week found, backtracking will happen naturally (pop to previous state)

        return None

    def _try_distribute_with_byes(
        self,
        matchups: List[Matchup],
        bye_assignments: Dict[int, int],
        attempt: int
    ) -> Optional[Dict[int, List[Matchup]]]:
        """
        Single attempt to distribute matchups respecting bye weeks.

        Uses constraint-based ordering: most-constrained matchups first.
        Teams are pre-marked unavailable during their bye weeks.
        """
        # Track team availability (includes bye weeks)
        team_week: Dict[int, Set[int]] = {t: set() for t in range(1, 33)}

        # Pre-mark bye weeks as unavailable
        for team_id, bye_week in bye_assignments.items():
            team_week[team_id].add(bye_week)

        # Calculate week capacities (accounting for byes)
        week_capacity: Dict[int, int] = {}
        for week in range(1, self.TOTAL_WEEKS + 1):
            teams_on_bye = sum(1 for t, w in bye_assignments.items() if w == week)
            teams_playing = self.TOTAL_TEAMS - teams_on_bye
            week_capacity[week] = teams_playing // 2  # 14-16 games

        week_games: Dict[int, List[Matchup]] = {w: [] for w in range(1, self.TOTAL_WEEKS + 1)}

        def can_assign(m: Matchup, week: int) -> bool:
            if len(week_games[week]) >= week_capacity[week]:
                return False
            if week in team_week[m.home_team_id]:
                return False
            if week in team_week[m.away_team_id]:
                return False
            return True

        def assign(m: Matchup, week: int) -> None:
            m.week = week
            week_games[week].append(m)
            team_week[m.home_team_id].add(week)
            team_week[m.away_team_id].add(week)

        def unassign(m: Matchup) -> None:
            if m.week == 0:
                return
            week = m.week
            m.week = 0
            week_games[week].remove(m)
            team_week[m.home_team_id].discard(week)
            team_week[m.away_team_id].discard(week)

        def count_available_weeks(m: Matchup) -> int:
            return sum(1 for w in range(1, self.TOTAL_WEEKS + 1) if can_assign(m, w))

        # Shuffle matchups with variation based on attempt
        random.seed(attempt * 12345)  # Deterministic but varied
        shuffled = list(matchups)
        random.shuffle(shuffled)

        # Sort by constraint level (most constrained first)
        def constraint_key(m: Matchup) -> Tuple[int, int, int]:
            div_priority = 0 if m.is_divisional else 1
            available = count_available_weeks(m)
            rand_factor = hash((m.home_team_id, m.away_team_id, attempt)) % 100
            return (div_priority, available, rand_factor)

        remaining = sorted(shuffled, key=constraint_key)

        while remaining:
            game = remaining.pop(0)
            available_weeks = [w for w in range(1, self.TOTAL_WEEKS + 1) if can_assign(game, w)]

            if available_weeks:
                week = min(available_weeks, key=lambda w: len(week_games[w]))
                assign(game, week)

                if len(remaining) % 50 == 0 and remaining:
                    remaining.sort(key=constraint_key)
            else:
                placed = self._try_swap_placement_with_byes(
                    game, week_games, team_week, week_capacity,
                    assign, unassign, can_assign
                )
                if not placed:
                    return None

        # Verify completeness (variable games per week)
        for week in range(1, self.TOTAL_WEEKS + 1):
            if len(week_games[week]) != week_capacity[week]:
                return None

        return week_games

    def _try_swap_placement_with_byes(
        self,
        game: Matchup,
        week_games: Dict[int, List[Matchup]],
        team_week: Dict[int, Set[int]],
        week_capacity: Dict[int, int],
        assign: Callable[[Matchup, int], None],
        unassign: Callable[[Matchup], None],
        can_assign: Callable[[Matchup, int], bool]
    ) -> bool:
        """
        Try to place a game by swapping with existing games.

        Uses 2-level chain swapping for bye-aware scheduling.
        Adapted from _try_swap_placement for variable week capacity.
        """
        for target_week in range(1, self.TOTAL_WEEKS + 1):
            if len(week_games[target_week]) >= week_capacity[target_week]:
                continue

            # Find games blocking this matchup in target_week
            blockers = []
            if target_week in team_week[game.home_team_id]:
                for m in week_games[target_week]:
                    if game.home_team_id in (m.home_team_id, m.away_team_id):
                        blockers.append(m)
                        break

            if target_week in team_week[game.away_team_id]:
                for m in week_games[target_week]:
                    if game.away_team_id in (m.home_team_id, m.away_team_id):
                        if m not in blockers:
                            blockers.append(m)
                        break

            # If no blockers AND week is valid for both teams, assign directly
            # CRITICAL: Must check can_assign to respect bye weeks!
            if not blockers and can_assign(game, target_week):
                assign(game, target_week)
                return True

            # Try moving blockers to make room
            for blocker in blockers:
                orig_week = blocker.week
                unassign(blocker)

                if can_assign(game, target_week):
                    # Level 1: Find new spot for blocker
                    for alt_week in range(1, self.TOTAL_WEEKS + 1):
                        if can_assign(blocker, alt_week):
                            assign(game, target_week)
                            assign(blocker, alt_week)
                            return True

                    # Level 2: Move blocker by displacing another game
                    for alt_week in range(1, self.TOTAL_WEEKS + 1):
                        if len(week_games[alt_week]) >= week_capacity[alt_week]:
                            continue

                        for displaced in list(week_games[alt_week]):
                            unassign(displaced)

                            if can_assign(blocker, alt_week):
                                for final_week in range(1, self.TOTAL_WEEKS + 1):
                                    if can_assign(displaced, final_week):
                                        assign(game, target_week)
                                        assign(blocker, alt_week)
                                        assign(displaced, final_week)
                                        return True

                            assign(displaced, alt_week)

                # Revert if couldn't place
                assign(blocker, orig_week)

        return False

    def close(self):
        """Close database connection."""
        if hasattr(self, '_db') and self._db:
            self._db.close()
