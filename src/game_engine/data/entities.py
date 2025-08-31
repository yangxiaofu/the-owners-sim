from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Team:
    """
    Team entity representing a football team.
    
    Contains team metadata, ratings, and organizational information.
    """
    id: int
    name: str
    city: str
    founded: Optional[int] = None
    stadium_id: Optional[int] = None
    division: Optional[str] = None
    conference: Optional[str] = None
    
    # Team ratings
    ratings: Dict[str, Any] = None
    
    # Financial information
    salary_cap: Optional[int] = None
    cap_space: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default ratings if not provided."""
        if self.ratings is None:
            self.ratings = {
                "offense": {"rb_rating": 50, "ol_rating": 50, "qb_rating": 50, "wr_rating": 50, "te_rating": 50},
                "defense": {"dl_rating": 50, "lb_rating": 50, "db_rating": 50},
                "special_teams": 50,
                "coaching": {"offensive": 50, "defensive": 50},
                "overall_rating": 50
            }
    
    @property
    def full_name(self) -> str:
        """Get full team name (city + name)."""
        return f"{self.city} {self.name}"
    
    def get_rating(self, category: str, subcategory: str = None) -> int:
        """
        Get a specific rating value.
        
        Args:
            category: Main category ("offense", "defense", etc.)
            subcategory: Optional subcategory ("rb_rating", "qb_rating", etc.)
            
        Returns:
            Rating value or 50 if not found
        """
        if category not in self.ratings:
            return 50
            
        rating_data = self.ratings[category]
        
        if subcategory is None:
            return rating_data if isinstance(rating_data, int) else 50
        
        return rating_data.get(subcategory, 50) if isinstance(rating_data, dict) else 50
    
    def __str__(self) -> str:
        return self.full_name
    
    def __repr__(self) -> str:
        return f"Team(id={self.id}, name='{self.full_name}', overall={self.get_rating('overall_rating')})"


@dataclass
class Stadium:
    """
    Stadium entity representing a football stadium.
    """
    id: int
    name: str
    city: str
    capacity: int
    surface: str = "grass"  # grass, turf, dome, etc.
    opened: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.city})"
    
    def __repr__(self) -> str:
        return f"Stadium(id={self.id}, name='{self.name}', capacity={self.capacity})"


@dataclass 
class MediaAsset:
    """
    Media asset entity for logos, photos, etc.
    """
    id: str
    entity_type: str  # "team", "player", "stadium"
    entity_id: Any    # ID of associated entity
    asset_type: str   # "logo", "photo", "video"
    url: str
    alt_text: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.asset_type} for {self.entity_type} {self.entity_id}"
    
    def __repr__(self) -> str:
        return f"MediaAsset(id='{self.id}', type='{self.asset_type}', url='{self.url}')"