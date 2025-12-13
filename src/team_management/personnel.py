import random
import json
from typing import List, Dict, Any, Optional
from .players.player import Player, Position
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation, FormationMapper
from .teams.team_loader import get_team_by_id, Team


class PersonnelPackageManager:
    """Manages player selection for specific play types and formations"""

    def __init__(self, team_roster: List[Player], strict_depth_chart: bool = True):
        self.roster = team_roster
        self.strict_depth_chart = strict_depth_chart
        self.position_groups = self._organize_by_position()
    
    def _organize_by_position(self) -> Dict[str, List[Player]]:
        """Organize roster by position and validate/sort by depth chart order"""
        position_groups = {}

        for player in self.roster:
            position = player.primary_position
            if position not in position_groups:
                position_groups[position] = []
            position_groups[position].append(player)

        # Validate depth charts and sort
        for position in position_groups:
            if self.strict_depth_chart:
                # STRICT MODE: Validate all players have valid depth chart assignments
                self._validate_depth_chart(position, position_groups[position])

                # Sort by depth chart order (lower = higher priority), then overall as tiebreaker
                position_groups[position].sort(
                    key=lambda p: (
                        p.depth_chart_order,      # Primary: depth chart order (1, 2, 3...)
                        -p.get_rating('overall')  # Secondary: overall rating (descending)
                    )
                )
            else:
                # PERMISSIVE MODE: Fall back to overall sorting with default depth_chart_order=99
                position_groups[position].sort(
                    key=lambda p: (
                        getattr(p, 'depth_chart_order', 99),  # Default to 99 if missing
                        -p.get_rating('overall')              # Overall as tiebreaker
                    )
                )

        return position_groups

    def _validate_depth_chart(self, position: str, players: List[Player]) -> None:
        """
        Validate that all players have valid depth chart assignments (strict mode only).

        Args:
            position: Position to validate (e.g., 'QB', 'RB')
            players: List of players at this position

        Raises:
            ValueError: If any player missing depth_chart_order or has depth_chart_order=99
        """
        # Check for missing depth_chart_order attribute
        players_without_depth = [
            p for p in players
            if not hasattr(p, 'depth_chart_order') or p.depth_chart_order is None
        ]

        if players_without_depth:
            player_details = [
                f"  - {p.name} (#{p.number})"
                for p in players_without_depth
            ]
            raise ValueError(
                f"❌ DEPTH CHART ERROR: Position {position} has {len(players_without_depth)} "
                f"player(s) without depth chart assignment:\n" +
                "\n".join(player_details) +
                f"\n\nAll players must have a depth_chart_order assigned before game simulation.\n"
                f"Use the Depth Chart tab to set starters and backups for {position}."
            )

        # Check for unassigned players (depth_chart_order = 99)
        unassigned_players = [
            p for p in players
            if p.depth_chart_order == 99
        ]

        if unassigned_players:
            player_details = [
                f"  - {p.name} (#{p.number})"
                for p in unassigned_players
            ]
            raise ValueError(
                f"❌ DEPTH CHART ERROR: Position {position} has {len(unassigned_players)} "
                f"unassigned player(s) (depth_chart_order=99):\n" +
                "\n".join(player_details) +
                f"\n\nAll players must be assigned a depth chart position before game simulation.\n"
                f"Use the Depth Chart tab to assign {position} depth positions."
            )
    
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
    """Utility class for team roster management (database-backed)."""

    @classmethod
    def load_team_roster(cls, team_id: int,
                        dynasty_id: Optional[str] = None,
                        db_path: Optional[str] = None) -> List[Player]:
        """
        Load team roster from DATABASE ONLY.

        Args:
            team_id: Team ID (1-32)
            dynasty_id: Dynasty context (REQUIRED for database loading)
            db_path: Database path (REQUIRED for database loading)

        Returns:
            List of Player objects from database

        Raises:
            ValueError: If dynasty_id or db_path missing (no fallbacks)
            ValueError: If no roster found in database

        Note:
            For standalone demos without dynasties, use generate_synthetic_roster()
        """
        # Database loading is now REQUIRED
        if dynasty_id and db_path:
            return cls._load_from_database(team_id, dynasty_id, db_path)

        # No fallback - fail with clear error message
        raise ValueError(
            f"❌ dynasty_id and db_path are REQUIRED to load rosters.\n"
            f"   Player rosters are stored in database only.\n"
            f"   For standalone testing, use TeamRosterGenerator.generate_synthetic_roster({team_id})"
        )

    @classmethod
    def _load_from_database(cls, team_id: int, dynasty_id: str,
                           db_path: str) -> List[Player]:
        """
        Load roster from database (private method).

        Args:
            team_id: Team ID (1-32)
            dynasty_id: Dynasty context
            db_path: Database path

        Returns:
            List of Player objects from database

        Raises:
            ValueError: If no roster found
        """
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(db_path)
        roster_data = roster_api.get_team_roster(dynasty_id, team_id)

        # Convert database records to Player objects
        roster = []
        for row in roster_data:
            # Parse JSON fields
            positions = json.loads(row['positions'])
            attributes = json.loads(row['attributes'])

            # Create Player object with database player_id preserved
            player = Player(
                name=f"{row['first_name']} {row['last_name']}",
                number=row['number'],
                primary_position=positions[0] if positions else Position.WR,
                ratings=attributes,
                team_id=row['team_id'],
                player_id=row['player_id']  # Preserve stable database player_id
            )

            # Add depth_chart_order attribute (loaded from database)
            # sqlite3.Row doesn't have .get() method, use try/except for column access
            try:
                player.depth_chart_order = row['depth_chart_order']
            except (KeyError, IndexError):
                player.depth_chart_order = 99  # Default if column doesn't exist

            roster.append(player)

        # Sort roster by depth_chart_order so starters are processed first
        # This ensures snap tracking assigns snaps to starters, not backups
        roster.sort(key=lambda p: (getattr(p, 'depth_chart_order', 99), -getattr(p, 'overall', 0)))

        return roster
    
    @classmethod
    def generate_synthetic_roster(cls, team_id: int = 1) -> List[Player]:
        """
        Generate synthetic roster for standalone testing/demos.

        Use this ONLY for:
        - Unit tests
        - Standalone demos without dynasties
        - Development/debugging

        Production code should use load_team_roster() with database.

        Args:
            team_id: Numerical team ID (1-32) to generate roster for

        Returns:
            List of Player objects with synthetic ratings
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