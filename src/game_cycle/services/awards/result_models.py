"""
Result Models for Awards Service.

Dataclasses for service return types that encapsulate award calculation results.
Part of Milestone 10: Awards System, Tollgate 4.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .voting_engine import VotingResult


@dataclass
class AwardResult:
    """
    Result of calculating a major award (MVP, OPOY, etc.).

    Contains the winner, finalists, and all voting results.

    Attributes:
        award_id: Award identifier ('mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy')
        season: Season year the award is for
        winner: VotingResult for the winner (None if no candidates)
        finalists: VotingResults for positions 2-5
        all_votes: All candidates who received votes
        candidates_evaluated: Total number of eligible candidates
    """
    award_id: str
    season: int
    winner: Optional[VotingResult] = None
    finalists: List[VotingResult] = field(default_factory=list)
    all_votes: List[VotingResult] = field(default_factory=list)
    candidates_evaluated: int = 0

    @property
    def has_winner(self) -> bool:
        """Check if a winner was selected."""
        return self.winner is not None

    @property
    def top_5(self) -> List[VotingResult]:
        """Get the top 5 finalists including winner."""
        if self.winner is None:
            return []
        return [self.winner] + self.finalists[:4]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'award_id': self.award_id,
            'season': self.season,
            'winner': self.winner.to_dict() if self.winner else None,
            'finalists': [f.to_dict() for f in self.finalists],
            'all_votes': [v.to_dict() for v in self.all_votes],
            'candidates_evaluated': self.candidates_evaluated,
        }

    def __repr__(self) -> str:
        winner_name = self.winner.player_name if self.winner else "None"
        return (
            f"AwardResult(award={self.award_id}, season={self.season}, "
            f"winner={winner_name}, candidates={self.candidates_evaluated})"
        )


@dataclass
class AllProSelection:
    """
    A single All-Pro selection.

    Represents one player selected to either First Team or Second Team All-Pro.
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    team_type: str  # 'FIRST_TEAM' or 'SECOND_TEAM'
    overall_grade: float = 0.0
    position_rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'team_type': self.team_type,
            'overall_grade': self.overall_grade,
            'position_rank': self.position_rank,
        }


@dataclass
class AllProTeam:
    """
    Result of All-Pro team selection.

    Contains 44 total players: 22 First Team + 22 Second Team.

    Attributes:
        season: Season year
        first_team: Dict mapping position to list of First Team selections
        second_team: Dict mapping position to list of Second Team selections
        total_selections: Total number of players selected (should be 44)
    """
    season: int
    first_team: Dict[str, List[AllProSelection]] = field(default_factory=dict)
    second_team: Dict[str, List[AllProSelection]] = field(default_factory=dict)
    total_selections: int = 0

    @property
    def first_team_count(self) -> int:
        """Count of first team selections."""
        return sum(len(players) for players in self.first_team.values())

    @property
    def second_team_count(self) -> int:
        """Count of second team selections."""
        return sum(len(players) for players in self.second_team.values())

    def get_position_selections(self, position: str) -> Dict[str, List[AllProSelection]]:
        """Get both first and second team selections for a position."""
        return {
            'first_team': self.first_team.get(position, []),
            'second_team': self.second_team.get(position, []),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'first_team': {
                pos: [p.to_dict() for p in players]
                for pos, players in self.first_team.items()
            },
            'second_team': {
                pos: [p.to_dict() for p in players]
                for pos, players in self.second_team.items()
            },
            'total_selections': self.total_selections,
            'first_team_count': self.first_team_count,
            'second_team_count': self.second_team_count,
        }

    def __repr__(self) -> str:
        return (
            f"AllProTeam(season={self.season}, "
            f"first={self.first_team_count}, "
            f"second={self.second_team_count})"
        )


@dataclass
class ProBowlSelection:
    """
    A single Pro Bowl selection.

    Represents one player selected to the Pro Bowl for their conference.
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    conference: str  # 'AFC' or 'NFC'
    selection_type: str  # 'STARTER', 'RESERVE', 'ALTERNATE'
    overall_grade: float = 0.0
    combined_score: float = 0.0  # Fan + Coach + Player voting

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'conference': self.conference,
            'selection_type': self.selection_type,
            'overall_grade': self.overall_grade,
            'combined_score': self.combined_score,
        }


@dataclass
class ProBowlRoster:
    """
    Result of Pro Bowl roster selection.

    Contains AFC and NFC rosters with starters and reserves.

    Attributes:
        season: Season year
        afc_roster: Dict mapping position to list of AFC selections
        nfc_roster: Dict mapping position to list of NFC selections
        total_selections: Total number of players selected
    """
    season: int
    afc_roster: Dict[str, List[ProBowlSelection]] = field(default_factory=dict)
    nfc_roster: Dict[str, List[ProBowlSelection]] = field(default_factory=dict)
    total_selections: int = 0

    @property
    def afc_count(self) -> int:
        """Count of AFC selections."""
        return sum(len(players) for players in self.afc_roster.values())

    @property
    def nfc_count(self) -> int:
        """Count of NFC selections."""
        return sum(len(players) for players in self.nfc_roster.values())

    def get_conference_roster(self, conference: str) -> Dict[str, List[ProBowlSelection]]:
        """Get roster for a specific conference."""
        if conference.upper() == 'AFC':
            return self.afc_roster
        elif conference.upper() == 'NFC':
            return self.nfc_roster
        else:
            return {}

    def get_starters(self, conference: str) -> List[ProBowlSelection]:
        """Get all starters for a conference."""
        roster = self.get_conference_roster(conference)
        starters = []
        for players in roster.values():
            starters.extend([p for p in players if p.selection_type == 'STARTER'])
        return starters

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'afc_roster': {
                pos: [p.to_dict() for p in players]
                for pos, players in self.afc_roster.items()
            },
            'nfc_roster': {
                pos: [p.to_dict() for p in players]
                for pos, players in self.nfc_roster.items()
            },
            'total_selections': self.total_selections,
            'afc_count': self.afc_count,
            'nfc_count': self.nfc_count,
        }

    def __repr__(self) -> str:
        return (
            f"ProBowlRoster(season={self.season}, "
            f"afc={self.afc_count}, nfc={self.nfc_count})"
        )


@dataclass
class StatisticalLeaderEntry:
    """
    A single statistical leader entry.

    Represents one player's ranking in a statistical category.
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    stat_category: str
    stat_value: float
    league_rank: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'stat_category': self.stat_category,
            'stat_value': self.stat_value,
            'league_rank': self.league_rank,
        }


@dataclass
class StatisticalLeadersResult:
    """
    Result of recording statistical leaders.

    Contains leaders for all statistical categories.

    Attributes:
        season: Season year
        leaders_by_category: Dict mapping category name to list of top 10 leaders
        total_recorded: Total number of entries recorded
    """
    season: int
    leaders_by_category: Dict[str, List[StatisticalLeaderEntry]] = field(default_factory=dict)
    total_recorded: int = 0

    def get_category_leader(self, category: str) -> Optional[StatisticalLeaderEntry]:
        """Get the #1 leader for a category."""
        leaders = self.leaders_by_category.get(category, [])
        return leaders[0] if leaders else None

    def get_category_top_10(self, category: str) -> List[StatisticalLeaderEntry]:
        """Get top 10 for a category."""
        return self.leaders_by_category.get(category, [])[:10]

    @property
    def categories_recorded(self) -> List[str]:
        """List of all categories with recorded leaders."""
        return list(self.leaders_by_category.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'leaders_by_category': {
                cat: [e.to_dict() for e in entries]
                for cat, entries in self.leaders_by_category.items()
            },
            'total_recorded': self.total_recorded,
            'categories_recorded': self.categories_recorded,
        }

    def __repr__(self) -> str:
        return (
            f"StatisticalLeadersResult(season={self.season}, "
            f"categories={len(self.categories_recorded)}, "
            f"total={self.total_recorded})"
        )


@dataclass
class SuperBowlMVPResult:
    """
    Result of Super Bowl MVP calculation.

    Contains the MVP player and their game performance stats.

    Attributes:
        season: Season year
        game_id: Super Bowl game ID
        player_id: MVP player ID
        player_name: MVP player name
        team_id: MVP player's team ID
        position: Player's position
        winning_team: True if MVP was on winning team
        stat_line: Dict of key stats from the game
        mvp_score: Calculated MVP score (for internal use)
    """
    season: int
    game_id: str
    player_id: int
    player_name: str
    team_id: int
    position: str
    winning_team: bool = True
    stat_line: Dict[str, Any] = field(default_factory=dict)
    mvp_score: float = 0.0

    def get_stat_summary(self) -> str:
        """Get a formatted summary of key stats."""
        parts = []
        stats = self.stat_line

        # Passing stats
        if stats.get('passing_yards', 0) > 0:
            parts.append(f"{stats.get('passing_yards', 0)} pass yds")
            if stats.get('passing_tds', 0) > 0:
                parts.append(f"{stats.get('passing_tds', 0)} pass TD")

        # Rushing stats
        if stats.get('rushing_yards', 0) > 0:
            parts.append(f"{stats.get('rushing_yards', 0)} rush yds")
            if stats.get('rushing_tds', 0) > 0:
                parts.append(f"{stats.get('rushing_tds', 0)} rush TD")

        # Receiving stats
        if stats.get('receiving_yards', 0) > 0:
            parts.append(f"{stats.get('receptions', 0)} rec")
            parts.append(f"{stats.get('receiving_yards', 0)} rec yds")
            if stats.get('receiving_tds', 0) > 0:
                parts.append(f"{stats.get('receiving_tds', 0)} rec TD")

        # Defensive stats
        if stats.get('sacks', 0) > 0:
            parts.append(f"{stats.get('sacks', 0)} sack")
        if stats.get('interceptions', 0) > 0:
            parts.append(f"{stats.get('interceptions', 0)} INT")

        return ", ".join(parts) if parts else "N/A"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'game_id': self.game_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'winning_team': self.winning_team,
            'stat_line': self.stat_line,
            'stat_summary': self.get_stat_summary(),
            'mvp_score': self.mvp_score,
        }

    def __repr__(self) -> str:
        return (
            f"SuperBowlMVPResult(season={self.season}, "
            f"player={self.player_name}, team={self.team_id})"
        )