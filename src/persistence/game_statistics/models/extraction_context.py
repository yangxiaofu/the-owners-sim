"""
Extraction Context Models

Context information and metadata for statistics extraction operations.
Provides structured context that guides extraction logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import date


@dataclass
class ExtractionContext:
    """
    Context information for statistics extraction operations.

    Provides game metadata, team information, and extraction
    configuration to guide the extraction process.
    """

    # Game identification
    game_id: str
    dynasty_id: str
    game_date: date

    # Team information
    away_team_id: int
    home_team_id: int

    # Game context
    week: int
    season_type: str
    season_year: int = 2024

    # Extraction configuration
    extract_player_stats: bool = True
    extract_team_stats: bool = True
    extract_o_line_stats: bool = True
    extract_special_teams_stats: bool = True

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the extraction context.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata from the extraction context.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def get_team_ids(self) -> List[int]:
        """
        Get all team IDs involved in this game.

        Returns:
            List of team IDs
        """
        return [self.away_team_id, self.home_team_id]

    def is_team_involved(self, team_id: int) -> bool:
        """
        Check if a team is involved in this game.

        Args:
            team_id: Team ID to check

        Returns:
            True if team is involved in this game
        """
        return team_id in [self.away_team_id, self.home_team_id]

    def get_opposing_team(self, team_id: int) -> Optional[int]:
        """
        Get the opposing team ID for a given team.

        Args:
            team_id: Team ID to get opponent for

        Returns:
            Opposing team ID or None if team not involved
        """
        if team_id == self.away_team_id:
            return self.home_team_id
        elif team_id == self.home_team_id:
            return self.away_team_id
        else:
            return None

    def is_playoff_game(self) -> bool:
        """
        Check if this is a playoff game.

        Returns:
            True if this is a playoff game
        """
        return self.season_type.lower() in ['playoffs', 'wildcard', 'divisional', 'conference', 'superbowl']

    def is_regular_season_game(self) -> bool:
        """
        Check if this is a regular season game.

        Returns:
            True if this is a regular season game
        """
        return self.season_type.lower() == 'regular_season'

    def should_extract_comprehensive_stats(self) -> bool:
        """
        Check if comprehensive statistics should be extracted.

        Returns:
            True if comprehensive stats should be extracted
        """
        return (self.extract_player_stats and
                self.extract_o_line_stats and
                self.extract_special_teams_stats)

    def __str__(self) -> str:
        """String representation of extraction context."""
        return (f"ExtractionContext(game_id={self.game_id}, "
                f"teams={self.away_team_id}@{self.home_team_id}, "
                f"week={self.week}, season_type={self.season_type})")


@dataclass
class PlayerExtractionContext:
    """
    Player-specific context for statistics extraction.

    Provides player metadata and context to guide
    player-specific extraction logic.
    """

    player_id: str
    player_name: str
    team_id: int
    position: str

    # Context from game
    game_context: ExtractionContext

    # Player-specific extraction flags
    extract_offensive_stats: bool = True
    extract_defensive_stats: bool = True
    extract_special_teams_stats: bool = True
    extract_o_line_stats: bool = True

    def is_offensive_lineman(self) -> bool:
        """Check if this player is an offensive lineman."""
        o_line_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']
        return self.position.lower() in o_line_positions

    def is_quarterback(self) -> bool:
        """Check if this player is a quarterback."""
        return self.position.lower() == 'quarterback'

    def is_skill_position(self) -> bool:
        """Check if this player is a skill position player."""
        skill_positions = ['quarterback', 'running_back', 'wide_receiver', 'tight_end']
        return self.position.lower() in skill_positions

    def is_defensive_player(self) -> bool:
        """Check if this player is a defensive player."""
        defensive_positions = [
            'defensive_end', 'defensive_tackle', 'nose_tackle',
            'linebacker', 'outside_linebacker', 'inside_linebacker',
            'cornerback', 'safety', 'strong_safety', 'free_safety'
        ]
        return self.position.lower() in defensive_positions

    def is_special_teams_player(self) -> bool:
        """Check if this player is a special teams player."""
        st_positions = ['kicker', 'punter', 'long_snapper']
        return self.position.lower() in st_positions

    def should_extract_o_line_stats(self) -> bool:
        """
        Check if O-line statistics should be extracted for this player.

        Returns:
            True if O-line stats should be extracted
        """
        return (self.extract_o_line_stats and
                self.game_context.extract_o_line_stats and
                (self.is_offensive_lineman() or self.is_skill_position()))

    def __str__(self) -> str:
        """String representation of player extraction context."""
        return (f"PlayerExtractionContext(player={self.player_name}, "
                f"position={self.position}, team={self.team_id})")