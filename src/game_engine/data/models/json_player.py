"""
JSON Player Model - Simple Player Data Structure for JSON Data Sources

This module provides a lightweight Player dataclass that works with JSON data
without any database dependencies. It's designed to be a fallback when the
full database models aren't available.

Key features:
- No external dependencies (database, SQLAlchemy, etc.)
- Compatible with existing players.json structure
- Simple dataclass with all essential player attributes
- Easy serialization/deserialization from JSON
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class JsonPlayer:
    """
    Simple player representation for JSON data sources.
    
    This class represents a player with all the essential attributes
    needed for game simulation, without database dependencies.
    """
    
    # Core Identity
    id: str
    name: str
    team_id: int
    position: str
    role: str = "depth"  # starter, backup, depth
    
    # Basic Info
    jersey_number: Optional[int] = None
    
    # Player Attributes (0-100 scale)
    attributes: Dict[str, int] = field(default_factory=dict)
    
    # Contract Information
    contract: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    injury_status: str = "healthy"
    fatigue: int = 100
    
    # Computed Properties
    @property
    def overall_rating(self) -> int:
        """Calculate overall rating from attributes."""
        if not self.attributes:
            return 50  # Default rating
            
        # Simple average of all attributes
        total = sum(self.attributes.values())
        count = len(self.attributes)
        return total // count if count > 0 else 50
    
    @property
    def position_group(self) -> str:
        """Get position group for this player."""
        position_groups = {
            # Offense
            'QB': 'Offense',
            'RB': 'Offense', 'FB': 'Offense',
            'WR': 'Offense', 'TE': 'Offense',
            'LT': 'Offense', 'LG': 'Offense', 'C': 'Offense', 
            'RG': 'Offense', 'RT': 'Offense',
            
            # Defense  
            'DE': 'Defense', 'DT': 'Defense', 'NT': 'Defense',
            'OLB': 'Defense', 'MLB': 'Defense', 'ILB': 'Defense',
            'CB': 'Defense', 'FS': 'Defense', 'SS': 'Defense',
            
            # Special Teams
            'K': 'Special Teams', 'P': 'Special Teams', 'LS': 'Special Teams',
            'KR': 'Special Teams', 'PR': 'Special Teams'
        }
        
        return position_groups.get(self.position, 'Unknown')
    
    @property
    def is_starter(self) -> bool:
        """Check if this player is a starter."""
        return self.role.lower() == "starter"
    
    @property
    def is_healthy(self) -> bool:
        """Check if player is healthy and available."""
        return self.injury_status.lower() in ["healthy", "active"]
    
    @property
    def salary(self) -> int:
        """Get player salary from contract."""
        if isinstance(self.contract, dict):
            return self.contract.get('salary', 0)
        return 0
    
    @property
    def years_remaining(self) -> int:
        """Get contract years remaining."""
        if isinstance(self.contract, dict):
            return self.contract.get('years_remaining', 0)
        return 0
    
    def get_attribute(self, attr_name: str, default: int = 50) -> int:
        """Get a specific attribute value."""
        return self.attributes.get(attr_name, default)
    
    def get_key_attributes(self) -> Dict[str, int]:
        """Get the most important attributes for this position."""
        position_key_attrs = {
            'QB': ['arm_strength', 'accuracy', 'awareness', 'mobility'],
            'RB': ['speed', 'agility', 'power', 'vision', 'elusiveness'],
            'WR': ['speed', 'catching', 'route_running', 'agility'],
            'TE': ['catching', 'strength', 'pass_blocking', 'route_running'],
            'LT': ['pass_blocking', 'strength', 'technique', 'awareness'],
            'LG': ['pass_blocking', 'run_blocking', 'strength', 'technique'],
            'C': ['pass_blocking', 'run_blocking', 'awareness', 'technique'],
            'RG': ['pass_blocking', 'run_blocking', 'strength', 'technique'],
            'RT': ['pass_blocking', 'strength', 'technique', 'awareness'],
            'DE': ['pass_rush', 'strength', 'technique', 'awareness'],
            'DT': ['strength', 'pass_rush', 'run_defense', 'technique'],
            'OLB': ['coverage', 'pass_rush', 'run_defense', 'awareness'],
            'MLB': ['run_defense', 'coverage', 'awareness', 'technique'],
            'CB': ['coverage', 'speed', 'agility', 'awareness'],
            'FS': ['coverage', 'awareness', 'speed', 'tackling'],
            'SS': ['run_defense', 'coverage', 'tackling', 'awareness'],
            'K': ['accuracy', 'power', 'clutch'],
            'P': ['accuracy', 'power', 'consistency']
        }
        
        key_attrs = position_key_attrs.get(self.position, [])
        return {attr: self.get_attribute(attr) for attr in key_attrs}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'team_id': self.team_id,
            'position': self.position,
            'role': self.role,
            'jersey_number': self.jersey_number,
            'attributes': dict(self.attributes),
            'contract': dict(self.contract),
            'injury_status': self.injury_status,
            'fatigue': self.fatigue,
            'overall_rating': self.overall_rating,
            'position_group': self.position_group
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonPlayer':
        """Create JsonPlayer from dictionary data."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', 'Unknown'),
            team_id=data.get('team_id', 0),
            position=data.get('position', 'Unknown'),
            role=data.get('role', 'depth'),
            jersey_number=data.get('jersey_number'),
            attributes=data.get('attributes', {}),
            contract=data.get('contract', {}),
            injury_status=data.get('injury_status', 'healthy'),
            fatigue=data.get('fatigue', 100)
        )
    
    def __str__(self) -> str:
        """String representation of player."""
        status = "🟢" if self.is_healthy else "🔴"
        role_icon = "⭐" if self.is_starter else "🔹"
        return f"{status}{role_icon} #{self.jersey_number or '??'} {self.name} ({self.position}) - {self.overall_rating} OVR"
    
    def get_summary(self) -> str:
        """Get detailed player summary."""
        lines = [
            f"📋 {self.name} (#{self.jersey_number or '??'})",
            f"   Position: {self.position} ({self.position_group})",
            f"   Role: {self.role.title()}",
            f"   Overall: {self.overall_rating}",
            f"   Status: {self.injury_status.title()} ({self.fatigue}% energy)"
        ]
        
        if self.salary > 0:
            lines.append(f"   Contract: ${self.salary:,} ({self.years_remaining} years)")
            
        key_attrs = self.get_key_attributes()
        if key_attrs:
            attr_str = ", ".join([f"{k}: {v}" for k, v in key_attrs.items()])
            lines.append(f"   Key Attributes: {attr_str}")
            
        return "\n".join(lines)