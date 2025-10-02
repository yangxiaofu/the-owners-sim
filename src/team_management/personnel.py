import random
from typing import List, Dict, Any
from .players.player import Player, Position
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation, FormationMapper
from .teams.team_loader import get_team_by_id, Team
from .players.player_loader import get_real_roster_for_team, has_real_roster_data, RealPlayer


class PersonnelPackageManager:
    """Manages player selection for specific play types and formations"""
    
    def __init__(self, team_roster: List[Player]):
        self.roster = team_roster
        self.position_groups = self._organize_by_position()
    
    def _organize_by_position(self) -> Dict[str, List[Player]]:
        """Organize roster by position for quick lookup"""
        position_groups = {}
        
        for player in self.roster:
            position = player.primary_position
            if position not in position_groups:
                position_groups[position] = []
            position_groups[position].append(player)
        
        # Sort players by overall rating (best first)
        for position in position_groups:
            position_groups[position].sort(key=lambda p: p.get_rating('overall'), reverse=True)
        
        return position_groups
    
    def get_offensive_personnel(self, formation: str) -> List[Player]:
        """Get 11 offensive players for a specific formation"""
        requirements = OffensiveFormation.get_personnel_requirements(formation)
        return self._select_players_for_requirements(requirements)
    
    def get_defensive_personnel(self, formation: str) -> List[Player]:
        """Get 11 defensive players for a specific formation"""
        requirements = DefensiveFormation.get_personnel_requirements(formation)
        return self._select_players_for_requirements(requirements)
    
    # Backward compatibility methods that use play type to formation mapping
    def get_offensive_personnel_for_play(self, play_type: str) -> List[Player]:
        """Get 11 offensive players for a specific play type (uses formation mapping)"""
        formation = FormationMapper.get_offensive_formation_for_play(play_type)
        return self.get_offensive_personnel(formation)
    
    def get_defensive_personnel_for_play(self, play_type: str) -> List[Player]:
        """Get 11 defensive players for a specific play type (uses formation mapping)"""
        formation = FormationMapper.get_defensive_formation_for_play(play_type)
        return self.get_defensive_personnel(formation)
    
    def _select_players_for_requirements(self, requirements: Dict[str, int]) -> List[Player]:
        """Select players based on position requirements"""
        selected_players = []
        used_players = set()
        
        # First pass: Select required players for each position
        for position, count in requirements.items():
            available_players = [p for p in self.position_groups.get(position, []) 
                               if p not in used_players]
            
            # Select best available players for this position
            for i in range(min(count, len(available_players))):
                player = available_players[i]
                selected_players.append(player)
                used_players.add(player)
        
        # If we don't have enough players, fill with versatile players or create generic ones
        while len(selected_players) < 11:
            # Try to find unused players from any position
            unused_players = [p for p in self.roster if p not in used_players]
            
            if unused_players:
                # Pick the best unused player
                best_unused = max(unused_players, key=lambda p: p.get_rating('overall'))
                selected_players.append(best_unused)
                used_players.add(best_unused)
            else:
                # Create a generic player if we're somehow short
                generic_player = self._create_generic_player(len(selected_players))
                selected_players.append(generic_player)
        
        return selected_players[:11]  # Ensure exactly 11 players
    
    def _create_generic_player(self, index: int, team_id: int = None) -> Player:
        """Create a generic player as fallback"""
        return Player(
            name=f"Generic Player {index + 1}",
            number=90 + index,
            primary_position=Position.WR,  # Default to WR
            ratings={"overall": 60},  # Below average rating
            team_id=team_id
        )
    
    def get_formation_for_play(self, play_type: str, side: str) -> str:
        """Get the formation being used for a play type"""
        if side == 'offense':
            return FormationMapper.get_offensive_formation_for_play(play_type)
        else:
            return FormationMapper.get_defensive_formation_for_play(play_type)
    
    def validate_personnel_package(self, players: List[Player]) -> bool:
        """Validate that a personnel package is legal (exactly 11 players)"""
        return len(players) == 11 and len(set(players)) == 11  # No duplicates
    
    def get_personnel_summary(self, players: List[Player]) -> Dict[str, int]:
        """Get a summary of positions in a personnel package"""
        summary = {}
        for player in players:
            position = player.primary_position
            summary[position] = summary.get(position, 0) + 1
        return summary
    
    def __str__(self):
        return f"PersonnelPackageManager with {len(self.roster)} players across {len(self.position_groups)} positions"


class TeamRosterGenerator:
    """Utility class to generate sample team rosters for testing"""
    
    @classmethod
    def load_team_roster(cls, team_id: int) -> List[Player]:
        """
        Load complete team roster from available data sources
        
        First attempts to load real NFL player data from JSON configuration,
        falls back to synthetic roster generation if real data unavailable.
        
        Args:
            team_id: Numerical team ID (1-32) to load roster for
            
        Returns:
            List of Player objects representing the team's complete roster
        """
        # Check if real roster data exists for this team
        if has_real_roster_data(team_id):
            return cls.generate_real_roster(team_id)
        
        # Fall back to synthetic roster generation
        return cls.generate_synthetic_roster(team_id)
    
    @classmethod
    def generate_real_roster(cls, team_id: int) -> List[Player]:
        """
        Generate roster using real NFL player data
        
        Args:
            team_id: Numerical team ID (must have real data available)
            
        Returns:
            List of Player objects created from real player data
        """
        if not has_real_roster_data(team_id):
            raise ValueError(f"No real roster data available for team_id: {team_id}")
        
        # Get real players for this team
        real_players = get_real_roster_for_team(team_id)
        
        # Convert RealPlayer objects to Player objects
        roster = []
        for real_player in real_players:
            # Create Player object with real data
            player = Player(
                name=real_player.full_name,
                number=real_player.number,
                primary_position=real_player.primary_position,
                ratings=real_player.attributes.copy(),  # Use real attributes
                team_id=team_id  # Pass team_id to preserve team assignment
            )
            roster.append(player)
        
        return roster
    
    @classmethod
    def generate_synthetic_roster(cls, team_id: int = 1) -> List[Player]:
        """
        Generate a complete 53-man roster with synthetic/generated ratings
        
        Args:
            team_id: Numerical team ID (1-32) to generate roster for
            
        Returns:
            List of Player objects representing the team's roster
        """
        # Get team data
        team = get_team_by_id(team_id)
        if not team:
            raise ValueError(f"Invalid team_id: {team_id}. Must be between 1 and 32.")
        
        roster = []
        
        # Offensive players
        roster.extend(cls._generate_quarterbacks(team))
        roster.extend(cls._generate_running_backs(team))
        roster.extend(cls._generate_wide_receivers(team))
        roster.extend(cls._generate_tight_ends(team))
        roster.extend(cls._generate_offensive_line(team))
        
        # Defensive players
        roster.extend(cls._generate_defensive_line(team))
        roster.extend(cls._generate_linebackers(team))
        roster.extend(cls._generate_defensive_backs(team))
        
        # Special teams
        roster.extend(cls._generate_specialists(team))
        
        return roster
    
    @classmethod
    def _generate_quarterbacks(cls, team: Team) -> List[Player]:
        """Generate QB depth chart"""
        return [
            Player(f"{team.city} Starting QB", 1, Position.QB, {"overall": random.randint(75, 95)}, team.team_id),
            Player(f"{team.city} Backup QB", 12, Position.QB, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} 3rd String QB", 15, Position.QB, {"overall": random.randint(55, 70)}, team.team_id)
        ]
    
    @classmethod
    def _generate_running_backs(cls, team: Team) -> List[Player]:
        """Generate RB depth chart"""
        return [
            Player(f"{team.city} Starting RB", 21, Position.RB, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} Backup RB", 32, Position.RB, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} 3rd Down RB", 28, Position.RB, {"overall": random.randint(60, 75)}, team.team_id),
            Player(f"{team.city} Fullback", 44, Position.FB, {"overall": random.randint(65, 80)}, team.team_id)
        ]
    
    @classmethod
    def _generate_wide_receivers(cls, team: Team) -> List[Player]:
        """Generate WR depth chart"""
        return [
            Player(f"{team.city} WR1", 11, Position.WR, {"overall": random.randint(80, 95)}, team.team_id),
            Player(f"{team.city} WR2", 13, Position.WR, {"overall": random.randint(75, 85)}, team.team_id),
            Player(f"{team.city} WR3", 17, Position.WR, {"overall": random.randint(70, 82)}, team.team_id),
            Player(f"{team.city} WR4", 19, Position.WR, {"overall": random.randint(65, 75)}, team.team_id),
            Player(f"{team.city} WR5", 16, Position.WR, {"overall": random.randint(60, 70)}, team.team_id),
            Player(f"{team.city} WR6", 14, Position.WR, {"overall": random.randint(55, 65)}, team.team_id)
        ]
    
    @classmethod
    def _generate_tight_ends(cls, team: Team) -> List[Player]:
        """Generate TE depth chart"""
        return [
            Player(f"{team.city} Starting TE", 87, Position.TE, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} TE2", 85, Position.TE, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} TE3", 81, Position.TE, {"overall": random.randint(60, 75)}, team.team_id)
        ]
    
    @classmethod
    def _generate_offensive_line(cls, team: Team) -> List[Player]:
        """Generate O-Line depth chart"""
        return [
            Player(f"{team.city} LT", 73, Position.LT, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} LG", 67, Position.LG, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} Center", 55, Position.C, {"overall": random.randint(75, 88)}, team.team_id),
            Player(f"{team.city} RG", 65, Position.RG, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} RT", 71, Position.RT, {"overall": random.randint(75, 90)}, team.team_id),
            # Backup linemen
            Player(f"{team.city} OL6", 74, Position.LT, {"overall": random.randint(60, 75)}, team.team_id),
            Player(f"{team.city} OL7", 68, Position.LG, {"overall": random.randint(60, 75)}, team.team_id),
            Player(f"{team.city} OL8", 63, Position.C, {"overall": random.randint(60, 75)}, team.team_id)
        ]
    
    @classmethod
    def _generate_defensive_line(cls, team: Team) -> List[Player]:
        """Generate D-Line depth chart"""
        return [
            Player(f"{team.city} LE", 91, Position.DE, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} RE", 94, Position.DE, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} DT1", 93, Position.DT, {"overall": random.randint(75, 88)}, team.team_id),
            Player(f"{team.city} NT", 98, Position.NT, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} DT2", 95, Position.DT, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} DE3", 92, Position.DE, {"overall": random.randint(60, 75)}, team.team_id)
        ]
    
    @classmethod
    def _generate_linebackers(cls, team: Team) -> List[Player]:
        """Generate LB depth chart with accurate position names"""
        return [
            # 4-3 Linebackers
            Player(f"{team.city} Mike LB", 54, Position.MIKE, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} Sam LB", 52, Position.SAM, {"overall": random.randint(75, 88)}, team.team_id),
            Player(f"{team.city} Will LB", 58, Position.WILL, {"overall": random.randint(75, 88)}, team.team_id),
            
            # 3-4 Linebackers  
            Player(f"{team.city} ILB1", 56, Position.ILB, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} ILB2", 57, Position.ILB, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} OLB1", 51, Position.OLB, {"overall": random.randint(75, 85)}, team.team_id),
            Player(f"{team.city} OLB2", 59, Position.OLB, {"overall": random.randint(70, 80)}, team.team_id)
        ]
    
    @classmethod
    def _generate_defensive_backs(cls, team: Team) -> List[Player]:
        """Generate DB depth chart with nickel/slot coverage"""
        return [
            Player(f"{team.city} CB1", 24, Position.CB, {"overall": random.randint(80, 92)}, team.team_id),
            Player(f"{team.city} CB2", 22, Position.CB, {"overall": random.randint(75, 88)}, team.team_id),
            Player(f"{team.city} Nickel CB", 26, Position.NCB, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} Dime CB", 25, Position.NCB, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} FS", 31, Position.FS, {"overall": random.randint(75, 90)}, team.team_id),
            Player(f"{team.city} SS", 33, Position.SS, {"overall": random.randint(75, 88)}, team.team_id),
            Player(f"{team.city} CB3", 29, Position.CB, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} CB4", 27, Position.CB, {"overall": random.randint(60, 75)}, team.team_id),
            Player(f"{team.city} S3", 37, Position.FS, {"overall": random.randint(60, 75)}, team.team_id)
        ]
    
    @classmethod
    def _generate_specialists(cls, team: Team) -> List[Player]:
        """Generate special teams specialists"""
        return [
            Player(f"{team.city} Kicker", 4, Position.K, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} Punter", 8, Position.P, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} Long Snapper", 46, Position.LS, {"overall": random.randint(65, 80)}, team.team_id),
            Player(f"{team.city} Holder", 18, Position.H, {"overall": random.randint(60, 75)}, team.team_id),  # Usually backup QB/P
            Player(f"{team.city} Kick Returner", 23, Position.KR, {"overall": random.randint(70, 85)}, team.team_id),
            Player(f"{team.city} Punt Returner", 10, Position.PR, {"overall": random.randint(70, 85)}, team.team_id)
        ]