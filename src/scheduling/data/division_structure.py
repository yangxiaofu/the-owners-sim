"""
NFL Division Structure and Constants

Defines the structure of the NFL including conferences, divisions,
and team assignments. Integrates with existing TeamIDs system.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from constants.team_ids import TeamIDs


class Conference(Enum):
    """NFL Conference enumeration"""
    AFC = "AFC"
    NFC = "NFC"


class Division(Enum):
    """NFL Division enumeration"""
    # AFC Divisions
    AFC_EAST = "AFC_East"
    AFC_NORTH = "AFC_North"
    AFC_SOUTH = "AFC_South"
    AFC_WEST = "AFC_West"
    
    # NFC Divisions
    NFC_EAST = "NFC_East"
    NFC_NORTH = "NFC_North"
    NFC_SOUTH = "NFC_South"
    NFC_WEST = "NFC_West"


@dataclass
class DivisionRotation:
    """Represents division rotation matchups for a season"""
    year: int
    afc_rotations: Dict[Division, Division] = field(default_factory=dict)
    nfc_rotations: Dict[Division, Division] = field(default_factory=dict)
    inter_conference: Dict[Division, Division] = field(default_factory=dict)


@dataclass
class NFLStructure:
    """Complete NFL organizational structure with scheduling utilities"""
    
    def __init__(self):
        """Initialize NFL structure with team mappings"""
        # Map divisions to team IDs using existing TeamIDs constants
        self.divisions: Dict[Division, List[int]] = {
            Division.AFC_EAST: [
                TeamIDs.BUFFALO_BILLS,        # 1
                TeamIDs.MIAMI_DOLPHINS,        # 2
                TeamIDs.NEW_ENGLAND_PATRIOTS, # 3
                TeamIDs.NEW_YORK_JETS         # 4
            ],
            Division.AFC_NORTH: [
                TeamIDs.BALTIMORE_RAVENS,     # 5
                TeamIDs.CINCINNATI_BENGALS,   # 6
                TeamIDs.CLEVELAND_BROWNS,     # 7
                TeamIDs.PITTSBURGH_STEELERS   # 8
            ],
            Division.AFC_SOUTH: [
                TeamIDs.HOUSTON_TEXANS,       # 9
                TeamIDs.INDIANAPOLIS_COLTS,   # 10
                TeamIDs.JACKSONVILLE_JAGUARS, # 11
                TeamIDs.TENNESSEE_TITANS      # 12
            ],
            Division.AFC_WEST: [
                TeamIDs.DENVER_BRONCOS,       # 13
                TeamIDs.KANSAS_CITY_CHIEFS,   # 14
                TeamIDs.LAS_VEGAS_RAIDERS,    # 15
                TeamIDs.LOS_ANGELES_CHARGERS  # 16
            ],
            Division.NFC_EAST: [
                TeamIDs.DALLAS_COWBOYS,       # 17
                TeamIDs.NEW_YORK_GIANTS,      # 18
                TeamIDs.PHILADELPHIA_EAGLES,  # 19
                TeamIDs.WASHINGTON_COMMANDERS # 20
            ],
            Division.NFC_NORTH: [
                TeamIDs.CHICAGO_BEARS,        # 21
                TeamIDs.DETROIT_LIONS,        # 22
                TeamIDs.GREEN_BAY_PACKERS,    # 23
                TeamIDs.MINNESOTA_VIKINGS     # 24
            ],
            Division.NFC_SOUTH: [
                TeamIDs.ATLANTA_FALCONS,      # 25
                TeamIDs.CAROLINA_PANTHERS,    # 26
                TeamIDs.NEW_ORLEANS_SAINTS,   # 27
                TeamIDs.TAMPA_BAY_BUCCANEERS  # 28
            ],
            Division.NFC_WEST: [
                TeamIDs.ARIZONA_CARDINALS,    # 29
                TeamIDs.LOS_ANGELES_RAMS,     # 30
                TeamIDs.SAN_FRANCISCO_49ERS,  # 31
                TeamIDs.SEATTLE_SEAHAWKS      # 32
            ]
        }
        
        # Build reverse lookup maps
        self._build_lookup_maps()
        
        # Initialize rotation patterns
        self._build_rotation_map()
    
    def _build_lookup_maps(self):
        """Build reverse lookup maps for efficient queries"""
        self.team_to_division: Dict[int, Division] = {}
        self.team_to_conference: Dict[int, Conference] = {}
        
        for division, teams in self.divisions.items():
            conference = Conference.AFC if "AFC" in division.value else Conference.NFC
            for team_id in teams:
                self.team_to_division[team_id] = division
                self.team_to_conference[team_id] = conference
    
    def _build_rotation_map(self):
        """
        Pre-compute division rotation patterns.
        
        NFL uses a 4-year inter-conference rotation and 
        3-year intra-conference rotation cycle.
        """
        self.rotation_patterns: Dict[int, DivisionRotation] = {}
        
        # 2024 rotations (example - would load from configuration in production)
        self.rotation_patterns[2024] = DivisionRotation(
            year=2024,
            # Intra-conference rotations (play entire division)
            afc_rotations={
                Division.AFC_EAST: Division.AFC_WEST,
                Division.AFC_NORTH: Division.AFC_SOUTH,
                Division.AFC_SOUTH: Division.AFC_NORTH,
                Division.AFC_WEST: Division.AFC_EAST
            },
            nfc_rotations={
                Division.NFC_EAST: Division.NFC_SOUTH,
                Division.NFC_NORTH: Division.NFC_WEST,
                Division.NFC_SOUTH: Division.NFC_EAST,
                Division.NFC_WEST: Division.NFC_NORTH
            },
            # Inter-conference rotations
            inter_conference={
                Division.AFC_EAST: Division.NFC_WEST,
                Division.AFC_NORTH: Division.NFC_EAST,
                Division.AFC_SOUTH: Division.NFC_NORTH,
                Division.AFC_WEST: Division.NFC_SOUTH,
                Division.NFC_EAST: Division.AFC_NORTH,
                Division.NFC_NORTH: Division.AFC_SOUTH,
                Division.NFC_SOUTH: Division.AFC_WEST,
                Division.NFC_WEST: Division.AFC_EAST
            }
        )
        
        # Additional years would be added based on the rotation cycle
        self._generate_future_rotations()
    
    def _generate_future_rotations(self):
        """Generate rotation patterns for future years based on NFL cycle"""
        # This would implement the full rotation logic
        # For now, just copy 2024 as placeholder
        for year in range(2025, 2030):
            self.rotation_patterns[year] = self.rotation_patterns[2024]
    
    def get_division_for_team(self, team_id: int) -> Division:
        """Get division for a specific team"""
        if team_id not in self.team_to_division:
            raise ValueError(f"Team {team_id} not found in any division")
        return self.team_to_division[team_id]
    
    def get_conference_for_team(self, team_id: int) -> Conference:
        """Get conference for a specific team"""
        if team_id not in self.team_to_conference:
            raise ValueError(f"Team {team_id} not found in any conference")
        return self.team_to_conference[team_id]
    
    def get_division_opponents(self, team_id: int) -> List[int]:
        """Get division opponents for a team"""
        division = self.get_division_for_team(team_id)
        return [t for t in self.divisions[division] if t != team_id]
    
    def get_conference_teams(self, conference: Conference) -> List[int]:
        """Get all teams in a conference"""
        teams = []
        for division in self.divisions:
            if conference.value in division.value:
                teams.extend(self.divisions[division])
        return teams
    
    def get_division_teams(self, division: Division) -> List[int]:
        """Get all teams in a division"""
        return self.divisions.get(division, [])
    
    def get_rotating_opponents(self, team_id: int, year: int) -> Dict[str, List[int]]:
        """
        Get rotating opponents for a team in a given year.
        
        Returns:
            Dictionary with 'intra_conference' and 'inter_conference' opponent lists
        """
        if year not in self.rotation_patterns:
            raise ValueError(f"No rotation pattern defined for year {year}")
        
        division = self.get_division_for_team(team_id)
        rotation = self.rotation_patterns[year]
        
        result = {
            'intra_conference': [],
            'inter_conference': []
        }
        
        # Get intra-conference rotation
        if division in Division.__members__.values():
            if "AFC" in division.value:
                rotating_div = rotation.afc_rotations.get(division)
            else:
                rotating_div = rotation.nfc_rotations.get(division)
            
            if rotating_div:
                result['intra_conference'] = self.get_division_teams(rotating_div)
        
        # Get inter-conference rotation
        rotating_div = rotation.inter_conference.get(division)
        if rotating_div:
            result['inter_conference'] = self.get_division_teams(rotating_div)
        
        return result
    
    def get_all_teams(self) -> List[int]:
        """Get all NFL team IDs"""
        return list(range(1, 33))
    
    def validate_structure(self) -> Tuple[bool, List[str]]:
        """
        Validate the NFL structure is correctly configured.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check all teams are present
        all_teams = set()
        for teams in self.divisions.values():
            all_teams.update(teams)
        
        if len(all_teams) != 32:
            errors.append(f"Expected 32 teams, found {len(all_teams)}")
        
        # Check for duplicates
        team_list = []
        for teams in self.divisions.values():
            team_list.extend(teams)
        
        if len(team_list) != len(set(team_list)):
            errors.append("Duplicate team assignments found")
        
        # Check each division has 4 teams
        for division, teams in self.divisions.items():
            if len(teams) != 4:
                errors.append(f"{division.value} has {len(teams)} teams, expected 4")
        
        # Check team IDs are in valid range
        for team_id in all_teams:
            if not 1 <= team_id <= 32:
                errors.append(f"Invalid team ID: {team_id}")
        
        return len(errors) == 0, errors


# Global instance for easy access
NFL_STRUCTURE = NFLStructure()