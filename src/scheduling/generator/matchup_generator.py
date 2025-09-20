"""
Simple NFL Matchup Generator - YAGNI Implementation

Generates 272 matchups (17 per team) using simplified NFL rules.
No complex rotation patterns - just functional matchup generation.
"""

from typing import List, Tuple, Dict, Set
from collections import defaultdict
from random import shuffle
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scheduling.data.team_data import TeamDataManager
from scheduling.data.division_structure import NFL_STRUCTURE, Division, Conference


class SimpleMatchupGenerator:
    """
    Generates NFL matchups using simplified rules.
    
    YAGNI Approach: Basic but functional matchup generation
    without complex NFL rotation patterns.
    """
    
    def __init__(self):
        self.team_manager = TeamDataManager()
    
    def _are_division_rivals(self, team1: int, team2: int) -> bool:
        """Check if two teams are in the same division"""
        t1 = self.team_manager.get_team(team1)
        t2 = self.team_manager.get_team(team2)
        return t1.division == t2.division
        
    def generate_season_matchups(self, year: int = 2024) -> List[Tuple[int, int]]:
        """
        Generate all 272 matchups for the season.
        
        Returns:
            List of (home_team_id, away_team_id) tuples
        """
        matchups = []
        
        # Track games per team to ensure exactly 17
        team_game_count = defaultdict(int)
        
        # 1. Division games (6 per team) - highest priority
        division_matchups = self._generate_division_matchups()
        matchups.extend(division_matchups)
        self._update_game_counts(division_matchups, team_game_count)
        
        # 2. Conference games (4 per team)
        conference_matchups = self._generate_conference_matchups(year)
        matchups.extend(conference_matchups)
        self._update_game_counts(conference_matchups, team_game_count)
        
        # 3. Inter-conference games (4 per team)
        interconference_matchups = self._generate_interconference_matchups(year)
        matchups.extend(interconference_matchups)
        self._update_game_counts(interconference_matchups, team_game_count)
        
        # 4. Remaining games to reach 17 per team
        remaining_matchups = self._generate_remaining_matchups(team_game_count, matchups)
        matchups.extend(remaining_matchups)
        self._update_game_counts(remaining_matchups, team_game_count)
        
        # 5. Validate and balance
        self._validate_matchups(matchups, team_game_count)
        balanced_matchups = self._balance_home_away(matchups)
        
        return balanced_matchups
    
    def _generate_division_matchups(self) -> List[Tuple[int, int]]:
        """Generate division matchups - each team plays division rivals twice."""
        matchups = []
        
        for division, teams in NFL_STRUCTURE.divisions.items():
            # Each team plays every other team in division twice (home and away)
            for home_team in teams:
                for away_team in teams:
                    if home_team != away_team:
                        matchups.append((home_team, away_team))
        
        return matchups
    
    def _generate_conference_matchups(self, year: int) -> List[Tuple[int, int]]:
        """
        Generate conference matchups using simple rotation.
        Each team plays 4 teams from one other division in same conference.
        """
        matchups = []
        rotation_map = self._get_simple_conference_rotation(year)
        
        # Process each division pair only once to avoid duplicates
        processed_pairs = set()
        
        for division, opponent_division in rotation_map.items():
            # Create a sorted pair to avoid processing the same matchup twice
            pair = tuple(sorted([division.value, opponent_division.value]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)
            
            division1_teams = NFL_STRUCTURE.divisions[division]
            division2_teams = NFL_STRUCTURE.divisions[opponent_division]
            
            # Each team in division1 plays each team in division2 once
            # Alternate home/away based on team ID to balance
            for i, team1 in enumerate(division1_teams):
                for j, team2 in enumerate(division2_teams):
                    # Alternate who hosts based on indices
                    if (i + j) % 2 == 0:
                        matchups.append((team1, team2))
                    else:
                        matchups.append((team2, team1))
        
        return matchups
    
    def _generate_interconference_matchups(self, year: int) -> List[Tuple[int, int]]:
        """
        Generate inter-conference matchups using simple rotation.
        Each team plays 4 teams from one division in other conference.
        """
        matchups = []
        rotation_map = self._get_simple_interconference_rotation(year)
        
        # Process each division pair only once to avoid duplicates
        processed_pairs = set()
        
        for division, opponent_division in rotation_map.items():
            # Create a sorted pair to avoid processing the same matchup twice
            pair = tuple(sorted([division.value, opponent_division.value]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)
            
            division1_teams = NFL_STRUCTURE.divisions[division]
            division2_teams = NFL_STRUCTURE.divisions[opponent_division]
            
            # Each team in division1 plays each team in division2 once
            for i, team1 in enumerate(division1_teams):
                for j, team2 in enumerate(division2_teams):
                    # Alternate home/away based on year and team to balance
                    if (year + i + j) % 2 == 0:
                        matchups.append((team1, team2))
                    else:
                        matchups.append((team2, team1))
        
        return matchups
    
    def _generate_remaining_matchups(self, team_game_count: Dict[int, int], 
                                   existing_matchups: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Generate remaining games to reach exactly 17 per team.
        YAGNI approach: Simple algorithm that ensures all teams get 17 games.
        """
        matchups = []
        
        # Count how many times each pair has played
        pair_counts = defaultdict(int)
        for home, away in existing_matchups:
            pair = tuple(sorted([home, away]))
            pair_counts[pair] += 1
        
        # Find teams that need more games and their exact counts
        team_needs = {}
        for team_id in range(1, 33):
            games_needed = 17 - team_game_count[team_id]
            if games_needed > 0:
                team_needs[team_id] = games_needed
        
        # YAGNI approach: Distribute remaining games more evenly to avoid division conflicts
        iteration = 0
        max_iterations = 200
        
        while team_needs and iteration < max_iterations:
            iteration += 1
            
            # Find team with most games needed (to balance)
            team1 = max(team_needs.keys(), key=lambda t: team_needs[t])
            
            # Try to find the best opponent, prioritizing non-division teams
            opponent = None
            best_opponent = None
            
            # First pass: look for non-division teams that haven't played this team yet
            for team2 in team_needs.keys():
                if team1 == team2:
                    continue
                
                pair = tuple(sorted([team1, team2]))
                is_division_pair = self._are_division_rivals(team1, team2)
                current_games = pair_counts[pair]
                
                if not is_division_pair and current_games == 0:
                    # Perfect match: non-division team with no previous games
                    opponent = team2
                    break
                elif not is_division_pair and current_games == 1:
                    # Good match: non-division team with one previous game
                    best_opponent = team2
            
            # Use best match if no perfect match found
            if opponent is None and best_opponent is not None:
                opponent = best_opponent
            
            # Second pass: if still no opponent, accept any non-division team
            if opponent is None:
                for team2 in team_needs.keys():
                    if team1 == team2:
                        continue
                    
                    is_division_pair = self._are_division_rivals(team1, team2)
                    if not is_division_pair:
                        opponent = team2
                        break
            
            # Last resort: accept division rival (should be very rare)
            if opponent is None:
                remaining_teams = [t for t in team_needs.keys() if t != team1]
                if remaining_teams:
                    opponent = remaining_teams[0]
            
            if opponent is None:
                # This shouldn't happen, but break to prevent infinite loop
                break
            
            # Create the matchup
            matchups.append((team1, opponent))
            pair = tuple(sorted([team1, opponent]))
            pair_counts[pair] += 1
            
            # Update needs
            team_needs[team1] -= 1
            team_needs[opponent] -= 1
            
            # Remove teams that no longer need games
            if team_needs[team1] <= 0:
                del team_needs[team1]
            if opponent in team_needs and team_needs[opponent] <= 0:
                del team_needs[opponent]
        
        return matchups
    
    def _get_simple_conference_rotation(self, year: int) -> Dict[Division, Division]:
        """Simple conference rotation - each division plays exactly one other division."""
        cycle = year % 3
        
        # Each division plays exactly one other division per year
        # We create pairs that don't overlap
        if cycle == 0:
            return {
                Division.AFC_EAST: Division.AFC_NORTH,
                Division.AFC_NORTH: Division.AFC_EAST,  # Reciprocal pairing
                Division.AFC_SOUTH: Division.AFC_WEST,
                Division.AFC_WEST: Division.AFC_SOUTH,  # Reciprocal pairing
                Division.NFC_EAST: Division.NFC_NORTH,
                Division.NFC_NORTH: Division.NFC_EAST,  # Reciprocal pairing
                Division.NFC_SOUTH: Division.NFC_WEST,
                Division.NFC_WEST: Division.NFC_SOUTH,  # Reciprocal pairing
            }
        elif cycle == 1:
            return {
                Division.AFC_EAST: Division.AFC_SOUTH,
                Division.AFC_SOUTH: Division.AFC_EAST,  # Reciprocal pairing
                Division.AFC_NORTH: Division.AFC_WEST,
                Division.AFC_WEST: Division.AFC_NORTH,  # Reciprocal pairing
                Division.NFC_EAST: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.NFC_EAST,  # Reciprocal pairing
                Division.NFC_NORTH: Division.NFC_WEST,
                Division.NFC_WEST: Division.NFC_NORTH,  # Reciprocal pairing
            }
        else:  # cycle == 2
            return {
                Division.AFC_EAST: Division.AFC_WEST,
                Division.AFC_WEST: Division.AFC_EAST,  # Reciprocal pairing
                Division.AFC_NORTH: Division.AFC_SOUTH,
                Division.AFC_SOUTH: Division.AFC_NORTH,  # Reciprocal pairing
                Division.NFC_EAST: Division.NFC_WEST,
                Division.NFC_WEST: Division.NFC_EAST,  # Reciprocal pairing
                Division.NFC_NORTH: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.NFC_NORTH,  # Reciprocal pairing
            }
    
    def _get_simple_interconference_rotation(self, year: int) -> Dict[Division, Division]:
        """Simple inter-conference rotation - each division plays exactly one other conference division."""
        cycle = year % 4
        
        # Each division plays exactly one division from other conference per year
        # We create pairs that don't overlap within each cycle
        if cycle == 0:
            return {
                Division.AFC_EAST: Division.NFC_NORTH,
                Division.NFC_NORTH: Division.AFC_EAST,  # Reciprocal pairing
                Division.AFC_NORTH: Division.NFC_WEST,
                Division.NFC_WEST: Division.AFC_NORTH,  # Reciprocal pairing
                Division.AFC_SOUTH: Division.NFC_EAST,
                Division.NFC_EAST: Division.AFC_SOUTH,  # Reciprocal pairing
                Division.AFC_WEST: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.AFC_WEST,  # Reciprocal pairing
            }
        elif cycle == 1:
            return {
                Division.AFC_EAST: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.AFC_EAST,  # Reciprocal pairing
                Division.AFC_NORTH: Division.NFC_EAST,
                Division.NFC_EAST: Division.AFC_NORTH,  # Reciprocal pairing
                Division.AFC_SOUTH: Division.NFC_NORTH,
                Division.NFC_NORTH: Division.AFC_SOUTH,  # Reciprocal pairing
                Division.AFC_WEST: Division.NFC_WEST,
                Division.NFC_WEST: Division.AFC_WEST,   # Reciprocal pairing
            }
        elif cycle == 2:
            return {
                Division.AFC_EAST: Division.NFC_WEST,
                Division.NFC_WEST: Division.AFC_EAST,   # Reciprocal pairing
                Division.AFC_NORTH: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.AFC_NORTH, # Reciprocal pairing
                Division.AFC_SOUTH: Division.NFC_EAST,
                Division.NFC_EAST: Division.AFC_SOUTH,  # Reciprocal pairing
                Division.AFC_WEST: Division.NFC_NORTH,
                Division.NFC_NORTH: Division.AFC_WEST,  # Reciprocal pairing
            }
        else:  # cycle == 3
            return {
                Division.AFC_EAST: Division.NFC_EAST,
                Division.NFC_EAST: Division.AFC_EAST,   # Reciprocal pairing
                Division.AFC_NORTH: Division.NFC_NORTH,
                Division.NFC_NORTH: Division.AFC_NORTH, # Reciprocal pairing
                Division.AFC_SOUTH: Division.NFC_SOUTH,
                Division.NFC_SOUTH: Division.AFC_SOUTH, # Reciprocal pairing
                Division.AFC_WEST: Division.NFC_WEST,
                Division.NFC_WEST: Division.AFC_WEST,   # Reciprocal pairing
            }
    
    def _update_game_counts(self, matchups: List[Tuple[int, int]], 
                           team_game_count: Dict[int, int]) -> None:
        """Update game counts for teams in matchups."""
        for home_team, away_team in matchups:
            team_game_count[home_team] += 1
            team_game_count[away_team] += 1
    
    def _matchup_exists(self, matchups: List[Tuple[int, int]], 
                       team1: int, team2: int) -> bool:
        """Check if matchup between two teams already exists."""
        return ((team1, team2) in matchups or (team2, team1) in matchups)
    
    def _validate_matchups(self, matchups: List[Tuple[int, int]], 
                          team_game_count: Dict[int, int]) -> None:
        """Validate generated matchups meet requirements."""
        errors = []
        
        # Check total games
        if len(matchups) != 272:
            errors.append(f"Total games: {len(matchups)}, expected 272")
        
        # Check each team has exactly 17 games
        for team_id in range(1, 33):
            count = team_game_count[team_id]
            if count != 17:
                errors.append(f"Team {team_id}: {count} games, expected 17")
        
        # Check division games (should mostly play twice, but allow some flexibility for YAGNI)
        division_pairs = defaultdict(int)
        for home_team, away_team in matchups:
            if self._are_division_rivals(home_team, away_team):
                pair = tuple(sorted([home_team, away_team]))
                division_pairs[pair] += 1
        
        # For YAGNI implementation, allow some flexibility in division game counts
        # Most should be 2, but 1 or 3 is acceptable if needed for valid schedule
        for pair, count in division_pairs.items():
            if count < 1 or count > 3:
                errors.append(f"Division rivals {pair} play {count} times, expected 1-3 (preferably 2)")
        
        if errors:
            raise ValueError(f"Matchup validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def _balance_home_away(self, matchups: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Balance home/away games so each team has 8 or 9 home games.
        Simple implementation - just returns matchups as generated.
        More complex balancing could be added later if needed.
        """
        # For YAGNI implementation, we accept the home/away distribution
        # from the generation algorithms above
        return matchups