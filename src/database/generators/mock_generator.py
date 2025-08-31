import random
from typing import Dict, List, Tuple
from ..models.players.positions import (
    RunningBack, OffensiveLineman, DefensiveLineman, Linebacker,
    create_running_back, create_offensive_lineman, 
    create_defensive_lineman, create_linebacker
)
from ..models.players.player import Player, PlayerRole


class MockPlayerGenerator:
    """Generates realistic mock players based on team ratings"""
    
    # Name pools for generating realistic player names
    FIRST_NAMES = [
        "Aaron", "Adrian", "Antonio", "Brandon", "Calvin", "Darius", "DeAndre", 
        "Derek", "Devon", "Ezekiel", "Frank", "Garrett", "Isaiah", "Jalen", 
        "Jamal", "Jordan", "Justin", "Keion", "Lamar", "Marcus", "Marshawn",
        "Michael", "Nick", "Patrick", "Quentin", "Robert", "Saquon", "Terrell",
        "Tyler", "Victor", "Zach", "Alvin", "Carlos", "Damien", "Eddie", "Felix"
    ]
    
    LAST_NAMES = [
        "Adams", "Allen", "Anderson", "Brown", "Davis", "Garcia", "Harris", 
        "Jackson", "Johnson", "Jones", "Lewis", "Martin", "Miller", "Moore",
        "Robinson", "Smith", "Taylor", "Thomas", "Thompson", "Washington", 
        "White", "Williams", "Wilson", "Young", "Bell", "Cooper", "Green",
        "Hill", "King", "Lee", "Parker", "Reed", "Scott", "Turner", "Walker"
    ]
    
    @staticmethod
    def generate_name() -> str:
        """Generate a realistic player name"""
        first = random.choice(MockPlayerGenerator.FIRST_NAMES)
        last = random.choice(MockPlayerGenerator.LAST_NAMES)
        return f"{first} {last}"
    
    @staticmethod
    def apply_variance(base_rating: int, variance: int = 10, role: PlayerRole = PlayerRole.STARTER) -> int:
        """Apply realistic variance to base ratings based on player role"""
        # Role-based adjustments
        role_adjustments = {
            PlayerRole.STARTER: 0,      # No adjustment for starters
            PlayerRole.BACKUP: -8,      # Backups are typically 8 points lower
            PlayerRole.DEPTH: -15,      # Depth players are 15 points lower
            PlayerRole.PRACTICE_SQUAD: -25  # Practice squad much lower
        }
        
        # Apply role adjustment
        adjusted_base = base_rating + role_adjustments[role]
        
        # Apply random variance
        variance_adjustment = random.randint(-variance, variance)
        final_rating = max(30, min(99, adjusted_base + variance_adjustment))
        
        return final_rating
    
    @staticmethod
    def generate_running_backs(team_id: int, team_ratings: Dict[str, int]) -> List[RunningBack]:
        """Generate realistic RB depth chart (3 players: starter, backup, FB)"""
        rb_base = team_ratings['offense']['rb_rating']
        running_backs = []
        
        # Starter RB
        starter_ratings = {
            'speed': MockPlayerGenerator.apply_variance(rb_base + 5, 8, PlayerRole.STARTER),
            'strength': MockPlayerGenerator.apply_variance(rb_base, 8, PlayerRole.STARTER),
            'agility': MockPlayerGenerator.apply_variance(rb_base + 3, 8, PlayerRole.STARTER),
            'stamina': MockPlayerGenerator.apply_variance(80, 5, PlayerRole.STARTER),
            'awareness': MockPlayerGenerator.apply_variance(rb_base - 5, 8, PlayerRole.STARTER),
            'technique': MockPlayerGenerator.apply_variance(rb_base, 8, PlayerRole.STARTER),
            'vision': MockPlayerGenerator.apply_variance(rb_base + 2, 10, PlayerRole.STARTER),
            'power': MockPlayerGenerator.apply_variance(rb_base, 10, PlayerRole.STARTER),
            'elusiveness': MockPlayerGenerator.apply_variance(rb_base + 3, 10, PlayerRole.STARTER),
            'catching': MockPlayerGenerator.apply_variance(max(50, rb_base - 15), 8, PlayerRole.STARTER),
            'pass_blocking': MockPlayerGenerator.apply_variance(max(40, rb_base - 20), 8, PlayerRole.STARTER)
        }
        
        running_backs.append(create_running_back(
            MockPlayerGenerator.generate_name(), team_id, "RB", starter_ratings, PlayerRole.STARTER
        ))
        
        # Backup RB - typically more balanced, slightly lower overall
        backup_ratings = {
            'speed': MockPlayerGenerator.apply_variance(rb_base - 2, 8, PlayerRole.BACKUP),
            'strength': MockPlayerGenerator.apply_variance(rb_base, 8, PlayerRole.BACKUP),
            'agility': MockPlayerGenerator.apply_variance(rb_base, 8, PlayerRole.BACKUP),
            'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.BACKUP),
            'awareness': MockPlayerGenerator.apply_variance(rb_base - 3, 8, PlayerRole.BACKUP),
            'technique': MockPlayerGenerator.apply_variance(rb_base - 5, 8, PlayerRole.BACKUP),
            'vision': MockPlayerGenerator.apply_variance(rb_base - 3, 10, PlayerRole.BACKUP),
            'power': MockPlayerGenerator.apply_variance(rb_base - 2, 10, PlayerRole.BACKUP),
            'elusiveness': MockPlayerGenerator.apply_variance(rb_base, 10, PlayerRole.BACKUP),
            'catching': MockPlayerGenerator.apply_variance(max(45, rb_base - 20), 8, PlayerRole.BACKUP),
            'pass_blocking': MockPlayerGenerator.apply_variance(max(35, rb_base - 25), 8, PlayerRole.BACKUP)
        }
        
        running_backs.append(create_running_back(
            MockPlayerGenerator.generate_name(), team_id, "RB", backup_ratings, PlayerRole.BACKUP
        ))
        
        # Fullback - emphasize blocking and power over speed
        fb_ratings = {
            'speed': MockPlayerGenerator.apply_variance(rb_base - 15, 5, PlayerRole.STARTER),
            'strength': MockPlayerGenerator.apply_variance(rb_base + 10, 8, PlayerRole.STARTER),
            'agility': MockPlayerGenerator.apply_variance(rb_base - 10, 5, PlayerRole.STARTER),
            'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.STARTER),
            'awareness': MockPlayerGenerator.apply_variance(rb_base + 5, 5, PlayerRole.STARTER),
            'technique': MockPlayerGenerator.apply_variance(rb_base + 5, 5, PlayerRole.STARTER),
            'vision': MockPlayerGenerator.apply_variance(rb_base - 5, 8, PlayerRole.STARTER),
            'power': MockPlayerGenerator.apply_variance(rb_base + 15, 8, PlayerRole.STARTER),
            'elusiveness': MockPlayerGenerator.apply_variance(rb_base - 20, 8, PlayerRole.STARTER),
            'catching': MockPlayerGenerator.apply_variance(max(60, rb_base - 10), 5, PlayerRole.STARTER),
            'pass_blocking': MockPlayerGenerator.apply_variance(rb_base + 20, 8, PlayerRole.STARTER)
        }
        
        running_backs.append(create_running_back(
            MockPlayerGenerator.generate_name(), team_id, "FB", fb_ratings, PlayerRole.STARTER
        ))
        
        return running_backs
    
    @staticmethod
    def generate_offensive_line(team_id: int, team_ratings: Dict[str, int]) -> List[OffensiveLineman]:
        """Generate realistic OL depth chart (7 players: 5 starters + 2 backups)"""
        ol_base = team_ratings['offense']['ol_rating']
        offensive_line = []
        
        positions = ["LT", "LG", "C", "RG", "RT"]
        
        # Generate starters for each OL position
        for pos in positions:
            # Position-specific adjustments
            pos_adjustments = {
                "LT": {"pass_blocking": 5, "mobility": 3, "strength": 0},    # LT needs pass blocking
                "LG": {"run_blocking": 3, "strength": 2, "mobility": 2},     # Guards pull and drive
                "C": {"awareness": 5, "technique": 3, "anchor": 2},          # Center calls protections
                "RG": {"run_blocking": 3, "strength": 2, "mobility": 2},     # Guards pull and drive
                "RT": {"run_blocking": 2, "strength": 3, "anchor": 2}        # RT run blocking focused
            }
            
            adjustments = pos_adjustments[pos]
            
            starter_ratings = {
                'speed': MockPlayerGenerator.apply_variance(45, 5, PlayerRole.STARTER),
                'strength': MockPlayerGenerator.apply_variance(ol_base + adjustments.get('strength', 0), 8, PlayerRole.STARTER),
                'agility': MockPlayerGenerator.apply_variance(55, 8, PlayerRole.STARTER),
                'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.STARTER),
                'awareness': MockPlayerGenerator.apply_variance(ol_base + adjustments.get('awareness', 0), 8, PlayerRole.STARTER),
                'technique': MockPlayerGenerator.apply_variance(ol_base + adjustments.get('technique', 0), 8, PlayerRole.STARTER),
                'pass_blocking': MockPlayerGenerator.apply_variance(ol_base + adjustments.get('pass_blocking', 0), 10, PlayerRole.STARTER),
                'run_blocking': MockPlayerGenerator.apply_variance(ol_base + adjustments.get('run_blocking', 0), 10, PlayerRole.STARTER),
                'mobility': MockPlayerGenerator.apply_variance(60 + adjustments.get('mobility', 0), 10, PlayerRole.STARTER),
                'anchor': MockPlayerGenerator.apply_variance(80 + adjustments.get('anchor', 0), 8, PlayerRole.STARTER)
            }
            
            offensive_line.append(create_offensive_lineman(
                MockPlayerGenerator.generate_name(), team_id, pos, starter_ratings, PlayerRole.STARTER
            ))
        
        # Generate 2 backup OL (can play multiple positions)
        for i in range(2):
            backup_ratings = {
                'speed': MockPlayerGenerator.apply_variance(45, 5, PlayerRole.BACKUP),
                'strength': MockPlayerGenerator.apply_variance(ol_base, 8, PlayerRole.BACKUP),
                'agility': MockPlayerGenerator.apply_variance(55, 8, PlayerRole.BACKUP),
                'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.BACKUP),
                'awareness': MockPlayerGenerator.apply_variance(ol_base, 8, PlayerRole.BACKUP),
                'technique': MockPlayerGenerator.apply_variance(ol_base, 8, PlayerRole.BACKUP),
                'pass_blocking': MockPlayerGenerator.apply_variance(ol_base, 10, PlayerRole.BACKUP),
                'run_blocking': MockPlayerGenerator.apply_variance(ol_base, 10, PlayerRole.BACKUP),
                'mobility': MockPlayerGenerator.apply_variance(60, 10, PlayerRole.BACKUP),
                'anchor': MockPlayerGenerator.apply_variance(80, 8, PlayerRole.BACKUP)
            }
            
            offensive_line.append(create_offensive_lineman(
                MockPlayerGenerator.generate_name(), team_id, f"OL", backup_ratings, PlayerRole.BACKUP
            ))
        
        return offensive_line
    
    @staticmethod
    def generate_defensive_line(team_id: int, team_ratings: Dict[str, int]) -> List[DefensiveLineman]:
        """Generate realistic DL depth chart (6 players: 4 starters + 2 backups)"""
        dl_base = team_ratings['defense']['dl_rating']
        defensive_line = []
        
        positions_and_roles = [
            ("LE", "edge"),      # Left End - pass rush focus
            ("DT", "interior"),  # Defensive Tackle - run stop focus
            ("DT", "interior"),  # Defensive Tackle - run stop focus  
            ("RE", "edge")       # Right End - pass rush focus
        ]
        
        for pos, role in positions_and_roles:
            # Role-specific adjustments
            if role == "edge":
                # Edge rushers: more speed, finesse, pass rushing
                starter_ratings = {
                    'speed': MockPlayerGenerator.apply_variance(dl_base + 10, 8, PlayerRole.STARTER),
                    'strength': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.STARTER),
                    'agility': MockPlayerGenerator.apply_variance(dl_base + 5, 8, PlayerRole.STARTER),
                    'stamina': MockPlayerGenerator.apply_variance(80, 5, PlayerRole.STARTER),
                    'awareness': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.STARTER),
                    'technique': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.STARTER),
                    'pass_rushing': MockPlayerGenerator.apply_variance(dl_base + 8, 10, PlayerRole.STARTER),
                    'run_defense': MockPlayerGenerator.apply_variance(dl_base - 2, 8, PlayerRole.STARTER),
                    'power_moves': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.STARTER),
                    'finesse_moves': MockPlayerGenerator.apply_variance(dl_base + 10, 10, PlayerRole.STARTER),
                    'gap_discipline': MockPlayerGenerator.apply_variance(dl_base - 5, 8, PlayerRole.STARTER)
                }
            else:
                # Interior linemen: more strength, run defense, power
                starter_ratings = {
                    'speed': MockPlayerGenerator.apply_variance(dl_base - 10, 5, PlayerRole.STARTER),
                    'strength': MockPlayerGenerator.apply_variance(dl_base + 10, 8, PlayerRole.STARTER),
                    'agility': MockPlayerGenerator.apply_variance(dl_base - 5, 5, PlayerRole.STARTER),
                    'stamina': MockPlayerGenerator.apply_variance(80, 5, PlayerRole.STARTER),
                    'awareness': MockPlayerGenerator.apply_variance(dl_base + 5, 8, PlayerRole.STARTER),
                    'technique': MockPlayerGenerator.apply_variance(dl_base + 5, 8, PlayerRole.STARTER),
                    'pass_rushing': MockPlayerGenerator.apply_variance(dl_base - 5, 8, PlayerRole.STARTER),
                    'run_defense': MockPlayerGenerator.apply_variance(dl_base + 10, 10, PlayerRole.STARTER),
                    'power_moves': MockPlayerGenerator.apply_variance(dl_base + 10, 10, PlayerRole.STARTER),
                    'finesse_moves': MockPlayerGenerator.apply_variance(dl_base - 10, 8, PlayerRole.STARTER),
                    'gap_discipline': MockPlayerGenerator.apply_variance(dl_base + 8, 8, PlayerRole.STARTER)
                }
            
            defensive_line.append(create_defensive_lineman(
                MockPlayerGenerator.generate_name(), team_id, pos, starter_ratings, PlayerRole.STARTER
            ))
        
        # Generate 2 backup DL
        for i in range(2):
            backup_ratings = {
                'speed': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.BACKUP),
                'strength': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.BACKUP),
                'agility': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.BACKUP),
                'stamina': MockPlayerGenerator.apply_variance(80, 5, PlayerRole.BACKUP),
                'awareness': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.BACKUP),
                'technique': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.BACKUP),
                'pass_rushing': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.BACKUP),
                'run_defense': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.BACKUP),
                'power_moves': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.BACKUP),
                'finesse_moves': MockPlayerGenerator.apply_variance(dl_base, 10, PlayerRole.BACKUP),
                'gap_discipline': MockPlayerGenerator.apply_variance(dl_base, 8, PlayerRole.BACKUP)
            }
            
            defensive_line.append(create_defensive_lineman(
                MockPlayerGenerator.generate_name(), team_id, "DL", backup_ratings, PlayerRole.BACKUP
            ))
        
        return defensive_line
    
    @staticmethod  
    def generate_linebackers(team_id: int, team_ratings: Dict[str, int]) -> List[Linebacker]:
        """Generate realistic LB depth chart (5 players: 3 starters + 2 backups)"""
        lb_base = team_ratings['defense']['lb_rating']
        linebackers = []
        
        positions_and_roles = [
            ("LOLB", "edge"),     # Outside LB - pass rush and coverage
            ("MLB", "mike"),      # Middle LB - run defense and leadership
            ("ROLB", "edge")      # Outside LB - pass rush and coverage
        ]
        
        for pos, role in positions_and_roles:
            if role == "edge":
                # Outside LBs: more speed, coverage, blitzing
                starter_ratings = {
                    'speed': MockPlayerGenerator.apply_variance(lb_base + 8, 8, PlayerRole.STARTER),
                    'strength': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.STARTER),
                    'agility': MockPlayerGenerator.apply_variance(lb_base + 5, 8, PlayerRole.STARTER),
                    'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.STARTER),
                    'awareness': MockPlayerGenerator.apply_variance(lb_base + 3, 8, PlayerRole.STARTER),
                    'technique': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.STARTER),
                    'run_defense': MockPlayerGenerator.apply_variance(lb_base, 10, PlayerRole.STARTER),
                    'coverage': MockPlayerGenerator.apply_variance(lb_base + 8, 10, PlayerRole.STARTER),
                    'blitzing': MockPlayerGenerator.apply_variance(lb_base + 10, 10, PlayerRole.STARTER),
                    'pursuit': MockPlayerGenerator.apply_variance(lb_base + 8, 8, PlayerRole.STARTER),
                    'instincts': MockPlayerGenerator.apply_variance(lb_base + 3, 8, PlayerRole.STARTER)
                }
            else:
                # Middle LB: more run defense, instincts, awareness
                starter_ratings = {
                    'speed': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.STARTER),
                    'strength': MockPlayerGenerator.apply_variance(lb_base + 8, 8, PlayerRole.STARTER),
                    'agility': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.STARTER),
                    'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.STARTER),
                    'awareness': MockPlayerGenerator.apply_variance(lb_base + 10, 8, PlayerRole.STARTER),
                    'technique': MockPlayerGenerator.apply_variance(lb_base + 5, 8, PlayerRole.STARTER),
                    'run_defense': MockPlayerGenerator.apply_variance(lb_base + 10, 10, PlayerRole.STARTER),
                    'coverage': MockPlayerGenerator.apply_variance(lb_base - 5, 8, PlayerRole.STARTER),
                    'blitzing': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.STARTER),
                    'pursuit': MockPlayerGenerator.apply_variance(lb_base + 5, 8, PlayerRole.STARTER),
                    'instincts': MockPlayerGenerator.apply_variance(lb_base + 10, 8, PlayerRole.STARTER)
                }
            
            linebackers.append(create_linebacker(
                MockPlayerGenerator.generate_name(), team_id, pos, starter_ratings, PlayerRole.STARTER
            ))
        
        # Generate 2 backup LBs
        for i in range(2):
            backup_ratings = {
                'speed': MockPlayerGenerator.apply_variance(lb_base, 10, PlayerRole.BACKUP),
                'strength': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP),
                'agility': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP),
                'stamina': MockPlayerGenerator.apply_variance(85, 5, PlayerRole.BACKUP),
                'awareness': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP),
                'technique': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP),
                'run_defense': MockPlayerGenerator.apply_variance(lb_base, 10, PlayerRole.BACKUP),
                'coverage': MockPlayerGenerator.apply_variance(lb_base, 10, PlayerRole.BACKUP),
                'blitzing': MockPlayerGenerator.apply_variance(lb_base, 10, PlayerRole.BACKUP),
                'pursuit': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP),
                'instincts': MockPlayerGenerator.apply_variance(lb_base, 8, PlayerRole.BACKUP)
            }
            
            linebackers.append(create_linebacker(
                MockPlayerGenerator.generate_name(), team_id, "LB", backup_ratings, PlayerRole.BACKUP
            ))
        
        return linebackers
    
    @staticmethod
    def generate_team_roster(team_id: int, team_data: Dict) -> Dict[str, List[Player]]:
        """Generate a complete roster for a team focused on run game positions"""
        
        roster = {
            'running_backs': MockPlayerGenerator.generate_running_backs(team_id, team_data),
            'offensive_line': MockPlayerGenerator.generate_offensive_line(team_id, team_data),
            'defensive_line': MockPlayerGenerator.generate_defensive_line(team_id, team_data),
            'linebackers': MockPlayerGenerator.generate_linebackers(team_id, team_data)
        }
        
        return roster
    
    @staticmethod
    def generate_all_team_rosters(teams_data: Dict[int, Dict]) -> Dict[int, Dict[str, List[Player]]]:
        """Generate rosters for all teams"""
        all_rosters = {}
        
        for team_id, team_data in teams_data.items():
            all_rosters[team_id] = MockPlayerGenerator.generate_team_roster(team_id, team_data)
            
        return all_rosters