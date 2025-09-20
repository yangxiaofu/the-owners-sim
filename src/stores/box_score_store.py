"""
Box Score Store

Store for game box scores with formatted statistical displays.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .base_store import BaseStore
from game_management.box_score_generator import TeamBoxScore, BoxScoreSection


@dataclass
class GameBoxScore:
    """Complete box score for a game with both teams"""
    game_id: str
    date: datetime
    home_box_score: TeamBoxScore
    away_box_score: TeamBoxScore
    game_summary: Dict[str, Any]  # Final score, total plays, etc.


class BoxScoreStore(BaseStore[GameBoxScore]):
    """
    Store for game box scores.

    Maintains formatted box scores for display and reporting,
    separate from raw statistical data.
    """

    def __init__(self):
        """Initialize box score store."""
        super().__init__("box_scores")

        # Additional indices
        self.by_team: Dict[int, List[str]] = {}  # team_id -> [game_ids]
        self.by_date: Dict[str, List[str]] = {}  # date_str -> [game_ids]

    def add(self, key: str, item: GameBoxScore) -> None:
        """
        Add a game box score.

        Args:
            key: Game identifier
            item: Complete game box score
        """
        if self.is_locked():
            self.logger.warning(f"Cannot add to locked store {self.store_name}")
            return

        # Store the box score
        self.data[key] = item

        # Update indices
        self._index_box_score(key, item)

        self._update_metadata()
        self._log_transaction('add', key, True, {
            'home_team': item.home_box_score.team.team_id if item.home_box_score.team else None,
            'away_team': item.away_box_score.team.team_id if item.away_box_score.team else None
        })

    def add_game_box_scores(self, game_id: str, home_box: TeamBoxScore,
                           away_box: TeamBoxScore, game_summary: Dict[str, Any]) -> None:
        """
        Convenience method to add box scores for both teams.

        Args:
            game_id: Game identifier
            home_box: Home team box score
            away_box: Away team box score
            game_summary: Game summary information
        """
        game_box = GameBoxScore(
            game_id=game_id,
            date=datetime.now(),  # Should be actual game date
            home_box_score=home_box,
            away_box_score=away_box,
            game_summary=game_summary
        )
        self.add(game_id, game_box)

    def get(self, key: str) -> Optional[GameBoxScore]:
        """
        Get a game's box score.

        Args:
            key: Game identifier

        Returns:
            GameBoxScore if found, None otherwise
        """
        return self.data.get(key)

    def get_all(self) -> Dict[str, GameBoxScore]:
        """Get all box scores."""
        return self.data.copy()

    def clear(self) -> None:
        """Clear all box scores."""
        if self.is_locked():
            self.logger.warning(f"Cannot clear locked store {self.store_name}")
            return

        self.data.clear()
        self.by_team.clear()
        self.by_date.clear()

        self.metadata.last_cleared = datetime.now()
        self._update_metadata()
        self._log_transaction('clear', None, True)

    def validate(self) -> bool:
        """
        Validate box score consistency.

        Returns:
            True if all data is valid, False otherwise
        """
        try:
            for game_id, box_score in self.data.items():
                # Verify both teams have box scores
                if not box_score.home_box_score or not box_score.away_box_score:
                    self.logger.error(f"Missing team box score for game {game_id}")
                    return False

                # Verify box scores have sections
                if not box_score.home_box_score.sections:
                    self.logger.error(f"Home team has no box score sections for game {game_id}")
                    return False

                if not box_score.away_box_score.sections:
                    self.logger.error(f"Away team has no box score sections for game {game_id}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def get_game_box_score(self, game_id: str) -> Optional[Tuple[TeamBoxScore, TeamBoxScore]]:
        """
        Get both team box scores for a game.

        Args:
            game_id: Game identifier

        Returns:
            Tuple of (home_box, away_box) if found, None otherwise
        """
        game_box = self.get(game_id)
        if game_box:
            return (game_box.home_box_score, game_box.away_box_score)
        return None

    def get_team_box_scores(self, team_id: int) -> List[TeamBoxScore]:
        """
        Get all box scores for a specific team.

        Args:
            team_id: Team identifier

        Returns:
            List of team box scores
        """
        box_scores = []
        game_ids = self.by_team.get(team_id, [])

        for game_id in game_ids:
            game_box = self.data.get(game_id)
            if game_box:
                # Check if team was home or away
                if game_box.home_box_score.team and game_box.home_box_score.team.team_id == team_id:
                    box_scores.append(game_box.home_box_score)
                elif game_box.away_box_score.team and game_box.away_box_score.team.team_id == team_id:
                    box_scores.append(game_box.away_box_score)

        return box_scores

    def get_by_date(self, date: datetime) -> List[GameBoxScore]:
        """
        Get all box scores for a specific date.

        Args:
            date: Date to query

        Returns:
            List of game box scores from that date
        """
        date_str = date.date().isoformat()
        game_ids = self.by_date.get(date_str, [])
        return [self.data[gid] for gid in game_ids if gid in self.data]

    def get_formatted_box_score(self, game_id: str) -> Optional[str]:
        """
        Get a formatted string representation of a box score.

        Args:
            game_id: Game identifier

        Returns:
            Formatted box score string if found
        """
        game_box = self.get(game_id)
        if not game_box:
            return None

        lines = []
        lines.append("=" * 80)
        lines.append(f"GAME BOX SCORE: {game_id}")
        lines.append("=" * 80)

        # Game summary
        if game_box.game_summary:
            lines.append("\nGAME SUMMARY:")
            for key, value in game_box.game_summary.items():
                lines.append(f"  {key}: {value}")

        # Format each team's box score
        for label, team_box in [("AWAY", game_box.away_box_score),
                                ("HOME", game_box.home_box_score)]:
            lines.append(f"\n{label} TEAM: {team_box.team.full_name if team_box.team else 'Unknown'}")
            lines.append("-" * 40)

            for section in team_box.sections:
                lines.append(f"\n{section.title}:")

                # Format headers
                if section.headers:
                    header_line = "  " + " | ".join(f"{h:>10}" for h in section.headers)
                    lines.append(header_line)
                    lines.append("  " + "-" * (len(header_line) - 2))

                # Format rows
                for row in section.rows:
                    row_line = "  " + " | ".join(f"{v:>10}" for v in row)
                    lines.append(row_line)

                # Add footnotes
                if section.footnotes:
                    for footnote in section.footnotes:
                        lines.append(f"  * {footnote}")

            # Team totals
            if team_box.team_totals:
                lines.append("\nTEAM TOTALS:")
                for stat, value in team_box.team_totals.items():
                    lines.append(f"  {stat}: {value}")

        return "\n".join(lines)

    def get_section_leaders(self, section_title: str,
                           stat_column: int) -> List[Tuple[str, str, Any]]:
        """
        Get leaders for a specific box score section statistic.

        Args:
            section_title: Title of the section (e.g., "Passing", "Rushing")
            stat_column: Column index of the statistic to rank by

        Returns:
            List of (player_name, team_name, stat_value) tuples
        """
        leaders = []

        for game_box in self.data.values():
            for team_box in [game_box.home_box_score, game_box.away_box_score]:
                for section in team_box.sections:
                    if section.title == section_title:
                        for row in section.rows:
                            if len(row) > stat_column:
                                try:
                                    # Assume first column is player name
                                    player_name = row[0]
                                    stat_value = float(row[stat_column])
                                    team_name = team_box.team.full_name if team_box.team else "Unknown"
                                    leaders.append((player_name, team_name, stat_value))
                                except (ValueError, IndexError):
                                    continue

        # Sort by stat value
        leaders.sort(key=lambda x: x[2], reverse=True)
        return leaders

    def _index_box_score(self, game_id: str, box_score: GameBoxScore) -> None:
        """
        Update indices for a box score.

        Args:
            game_id: Game identifier
            box_score: Box score to index
        """
        # Index by team
        if box_score.home_box_score.team:
            team_id = box_score.home_box_score.team.team_id
            if team_id not in self.by_team:
                self.by_team[team_id] = []
            self.by_team[team_id].append(game_id)

        if box_score.away_box_score.team:
            team_id = box_score.away_box_score.team.team_id
            if team_id not in self.by_team:
                self.by_team[team_id] = []
            self.by_team[team_id].append(game_id)

        # Index by date
        date_str = box_score.date.date().isoformat()
        if date_str not in self.by_date:
            self.by_date[date_str] = []
        self.by_date[date_str].append(game_id)

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize box scores for persistence.

        Returns:
            Serializable dictionary
        """
        serialized = {}

        for game_id, box_score in self.data.items():
            serialized[game_id] = {
                'date': box_score.date.isoformat(),
                'game_summary': box_score.game_summary,
                'home_team': {
                    'team_id': box_score.home_box_score.team.team_id if box_score.home_box_score.team else None,
                    'team_name': box_score.home_box_score.team.full_name if box_score.home_box_score.team else None,
                    'sections': [
                        {
                            'title': section.title,
                            'headers': section.headers,
                            'rows': section.rows,
                            'footnotes': section.footnotes
                        }
                        for section in box_score.home_box_score.sections
                    ],
                    'totals': box_score.home_box_score.team_totals
                },
                'away_team': {
                    'team_id': box_score.away_box_score.team.team_id if box_score.away_box_score.team else None,
                    'team_name': box_score.away_box_score.team.full_name if box_score.away_box_score.team else None,
                    'sections': [
                        {
                            'title': section.title,
                            'headers': section.headers,
                            'rows': section.rows,
                            'footnotes': section.footnotes
                        }
                        for section in box_score.away_box_score.sections
                    ],
                    'totals': box_score.away_box_score.team_totals
                }
            }

        return serialized

    def get_daily_summary(self, date: datetime) -> Dict[str, Any]:
        """
        Get a summary of all games on a specific date.

        Args:
            date: Date to summarize

        Returns:
            Summary statistics for the day
        """
        day_games = self.get_by_date(date)

        if not day_games:
            return {'date': date.isoformat(), 'games_played': 0}

        total_games = len(day_games)
        total_points = 0
        highest_scoring_game = None
        highest_score = 0

        for game_box in day_games:
            if game_box.game_summary:
                home_score = game_box.game_summary.get('home_score', 0)
                away_score = game_box.game_summary.get('away_score', 0)
                game_total = home_score + away_score

                total_points += game_total

                if game_total > highest_score:
                    highest_score = game_total
                    highest_scoring_game = game_box.game_id

        return {
            'date': date.isoformat(),
            'games_played': total_games,
            'total_points': total_points,
            'avg_points_per_game': total_points / total_games if total_games > 0 else 0,
            'highest_scoring_game': highest_scoring_game,
            'highest_score': highest_score
        }