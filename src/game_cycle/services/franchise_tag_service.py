"""
Franchise Tag Service

Wrapper service for TagManager integration with the game cycle.
Provides methods for:
- Getting taggable players (expiring contracts)
- Calculating tag salaries
- Applying franchise/transition tags
- AI team tag decisions
"""

import json
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from salary_cap.tag_manager import TagManager
from salary_cap.cap_database_api import CapDatabaseAPI
from database.player_roster_api import PlayerRosterAPI


class FranchiseTagService:
    """
    Service for franchise tag operations in the game cycle.

    Wraps the TagManager and provides game-cycle-specific operations.
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the service.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Initialize underlying services
        self._tag_manager = TagManager(db_path)
        self._cap_api = CapDatabaseAPI(db_path)
        self._roster_api = PlayerRosterAPI(db_path)

    def get_taggable_players(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get list of players eligible for franchise/transition tag.

        A player is taggable if:
        - They have an expiring contract (end_year = current season)
        - They belong to the specified team
        - They haven't already been tagged this season

        Args:
            team_id: Team ID to get taggable players for

        Returns:
            List of player dicts with tag cost calculations
        """
        taggable_players = []

        try:
            # Get all active contracts for this team that expire this season
            contracts = self._cap_api.get_team_contracts(
                team_id=team_id,
                dynasty_id=self._dynasty_id,
                season=self._season,
                active_only=True
            )

            for contract in contracts:
                player_id = contract.get("player_id")
                end_year = contract.get("end_year", self._season)

                # Only include expiring contracts
                if end_year > self._season:
                    continue

                # Check if already tagged
                if self._is_player_tagged(player_id):
                    continue

                # Get player info
                player_info = self._roster_api.get_player_by_id(
                    self._dynasty_id, player_id
                )

                if not player_info:
                    continue

                # Parse position
                positions = player_info.get("positions", [])
                if isinstance(positions, str):
                    positions = json.loads(positions)
                position = positions[0] if positions else "unknown"

                # Parse attributes
                attributes = player_info.get("attributes", {})
                if isinstance(attributes, str):
                    attributes = json.loads(attributes)
                overall = attributes.get("overall", 0)

                # Calculate age
                age = 0
                birthdate = player_info.get("birthdate")
                if birthdate:
                    try:
                        birth_year = int(birthdate.split("-")[0])
                        age = self._season - birth_year
                    except (ValueError, IndexError):
                        pass

                # Calculate tag costs
                tag_category = self._tag_manager._get_tag_category(position)

                franchise_tag_cost = self._tag_manager.calculate_franchise_tag_salary(
                    position=position,
                    season=self._season + 1,  # Tag is for next season
                    dynasty_id=self._dynasty_id
                )

                transition_tag_cost = self._tag_manager.calculate_transition_tag_salary(
                    position=position,
                    season=self._season + 1,
                    dynasty_id=self._dynasty_id
                )

                # Current cap hit for reference
                current_cap_hit = contract.get("cap_hit", 0)

                taggable_players.append({
                    "player_id": player_id,
                    "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                    "position": position,
                    "tag_category": tag_category,
                    "age": age,
                    "overall": overall,
                    "current_cap_hit": current_cap_hit,
                    "franchise_tag_cost": franchise_tag_cost,
                    "transition_tag_cost": transition_tag_cost,
                    "contract_id": contract.get("contract_id"),
                })

            # Sort by overall rating (highest first)
            taggable_players.sort(key=lambda x: x.get("overall", 0), reverse=True)

        except Exception as e:
            import traceback
            print(f"[FranchiseTagService] Error getting taggable players: {e}")
            traceback.print_exc()

        return taggable_players

    def apply_franchise_tag(
        self,
        player_id: int,
        team_id: int,
        tag_type: str = "NON_EXCLUSIVE"
    ) -> Dict[str, Any]:
        """
        Apply franchise tag to a player.

        Args:
            player_id: Player ID to tag
            team_id: Team applying the tag
            tag_type: "EXCLUSIVE" or "NON_EXCLUSIVE"

        Returns:
            Result dict with success status and details
        """
        try:
            # Check if team already used a tag this season
            tag_count = self._tag_manager.get_team_tag_count(
                team_id, self._season + 1, self._dynasty_id
            )
            if tag_count["total"] > 0:
                return {
                    "success": False,
                    "error": "Team has already used franchise or transition tag this season"
                }

            # Get player info for position
            player_info = self._roster_api.get_player_by_id(
                self._dynasty_id, player_id
            )
            if not player_info:
                return {
                    "success": False,
                    "error": f"Player {player_id} not found"
                }

            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else "unknown"

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Use February 25 of the tag season as canonical tag date
            tag_date = date(self._season + 1, 2, 25)

            # Apply the tag
            tag_salary = self._tag_manager.apply_franchise_tag(
                player_id=player_id,
                team_id=team_id,
                season=self._season + 1,  # Tag is for next season
                dynasty_id=self._dynasty_id,
                position=position,
                tag_type=tag_type,
                tag_date=tag_date,
                player_name=player_name
            )

            return {
                "success": True,
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "tag_type": f"FRANCHISE_{tag_type}",
                "tag_salary": tag_salary,
                "team_id": team_id,
            }

        except Exception as e:
            import traceback
            print(f"[FranchiseTagService] Error applying franchise tag: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def apply_transition_tag(
        self,
        player_id: int,
        team_id: int
    ) -> Dict[str, Any]:
        """
        Apply transition tag to a player.

        Args:
            player_id: Player ID to tag
            team_id: Team applying the tag

        Returns:
            Result dict with success status and details
        """
        try:
            # Check if team already used a tag this season
            tag_count = self._tag_manager.get_team_tag_count(
                team_id, self._season + 1, self._dynasty_id
            )
            if tag_count["total"] > 0:
                return {
                    "success": False,
                    "error": "Team has already used franchise or transition tag this season"
                }

            # Get player info for position
            player_info = self._roster_api.get_player_by_id(
                self._dynasty_id, player_id
            )
            if not player_info:
                return {
                    "success": False,
                    "error": f"Player {player_id} not found"
                }

            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else "unknown"

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Use February 25 of the tag season as canonical tag date
            tag_date = date(self._season + 1, 2, 25)

            # Apply the tag
            tag_salary = self._tag_manager.apply_transition_tag(
                player_id=player_id,
                team_id=team_id,
                season=self._season + 1,  # Tag is for next season
                dynasty_id=self._dynasty_id,
                position=position,
                tag_date=tag_date,
                player_name=player_name
            )

            return {
                "success": True,
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "tag_type": "TRANSITION",
                "tag_salary": tag_salary,
                "team_id": team_id,
            }

        except Exception as e:
            import traceback
            print(f"[FranchiseTagService] Error applying transition tag: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def has_team_used_tag(self, team_id: int) -> bool:
        """Check if team has already used a tag this season."""
        tag_count = self._tag_manager.get_team_tag_count(
            team_id, self._season + 1, self._dynasty_id
        )
        return tag_count["total"] > 0

    def process_ai_tags(self, user_team_id: int) -> Dict[str, Any]:
        """
        Process franchise tag decisions for all AI teams.

        OPTIMIZED: Uses batch queries to load all data upfront instead of
        making individual queries per team (fixes N+1 query problem).

        AI teams will tag their best expiring player if:
        - Overall >= 80
        - Age <= 30
        - Position value is high enough to warrant tagging

        Args:
            user_team_id: User's team ID (skip this team)

        Returns:
            Result dict with tags applied and events
        """
        tags_applied = []
        events = []

        # Premium positions for AI to prioritize
        premium_positions = ['QB', 'DE', 'CB', 'WR', 'LB', 'OL']

        try:
            # BATCH LOAD: Get all data upfront with minimal queries
            all_expiring = self._get_all_expiring_contracts_batch()
            existing_tags = self._get_teams_with_tags_batch()

            # Group expiring contracts by team
            expiring_by_team: Dict[int, List[Dict]] = {}
            for contract in all_expiring:
                team_id = contract["team_id"]
                if team_id not in expiring_by_team:
                    expiring_by_team[team_id] = []
                expiring_by_team[team_id].append(contract)

            # Process each AI team using pre-loaded data
            for team_id in range(1, 33):
                if team_id == user_team_id:
                    continue

                # Skip if team already used tag (from batch data)
                if team_id in existing_tags:
                    continue

                # Get this team's expiring contracts (from batch data)
                team_expiring = expiring_by_team.get(team_id, [])
                if not team_expiring:
                    continue

                # Find best candidate from pre-loaded data
                best_candidate = None
                for player in team_expiring:
                    overall = player.get("overall", 0)
                    age = player.get("age", 35)
                    tag_category = player.get("tag_category", "")

                    # AI criteria: 80+ OVR, age <= 30, premium position
                    if overall >= 80 and age <= 30:
                        if tag_category in premium_positions:
                            if best_candidate is None or overall > best_candidate.get("overall", 0):
                                best_candidate = player

                # Apply tag to best candidate if found
                if best_candidate:
                    result = self.apply_franchise_tag(
                        player_id=best_candidate["player_id"],
                        team_id=team_id,
                        tag_type="NON_EXCLUSIVE"
                    )

                    if result["success"]:
                        tags_applied.append(result)
                        events.append(
                            f"Team {team_id} applied franchise tag to {result['player_name']} "
                            f"({result['position']}) - ${result['tag_salary']:,}"
                        )

        except Exception as e:
            import traceback
            print(f"[FranchiseTagService] Error in process_ai_tags: {e}")
            traceback.print_exc()

        return {
            "tags_applied": tags_applied,
            "events": events,
            "total_tags": len(tags_applied),
        }

    def _get_all_expiring_contracts_batch(self) -> List[Dict[str, Any]]:
        """
        Batch load ALL expiring contracts across ALL teams in ONE query.

        Returns list of dicts with player info, team_id, and tag eligibility.
        """
        results = []

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Single query: Get all expiring contracts with player info joined
                cursor.execute(
                    """
                    SELECT
                        pc.player_id,
                        pc.team_id,
                        pc.contract_id,
                        pc.end_year,
                        p.first_name,
                        p.last_name,
                        p.positions,
                        p.attributes,
                        p.birthdate
                    FROM player_contracts pc
                    JOIN players p ON pc.player_id = p.player_id AND pc.dynasty_id = p.dynasty_id
                    WHERE pc.dynasty_id = ?
                      AND pc.is_active = 1
                      AND pc.end_year <= ?
                      AND pc.team_id BETWEEN 1 AND 32
                    """,
                    (self._dynasty_id, self._season)
                )

                rows = cursor.fetchall()

                # Get all player IDs that are already tagged (single query)
                cursor.execute(
                    """
                    SELECT player_id FROM franchise_tags
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (self._dynasty_id, self._season + 1)
                )
                tagged_player_ids = {row[0] for row in cursor.fetchall()}

                for row in rows:
                    player_id = row["player_id"]

                    # Skip already tagged players
                    if player_id in tagged_player_ids:
                        continue

                    # Parse position
                    positions = row["positions"]
                    if isinstance(positions, str):
                        positions = json.loads(positions)
                    position = positions[0] if positions else "unknown"

                    # Parse attributes
                    attributes = row["attributes"]
                    if isinstance(attributes, str):
                        attributes = json.loads(attributes)
                    overall = attributes.get("overall", 0)

                    # Calculate age
                    age = 0
                    birthdate = row["birthdate"]
                    if birthdate:
                        try:
                            birth_year = int(birthdate.split("-")[0])
                            age = self._season - birth_year
                        except (ValueError, IndexError):
                            pass

                    # Get tag category
                    tag_category = self._tag_manager._get_tag_category(position)

                    results.append({
                        "player_id": player_id,
                        "team_id": row["team_id"],
                        "contract_id": row["contract_id"],
                        "name": f"{row['first_name'] or ''} {row['last_name'] or ''}".strip(),
                        "position": position,
                        "tag_category": tag_category,
                        "overall": overall,
                        "age": age,
                    })

        except Exception as e:
            import traceback
            print(f"[FranchiseTagService] Error in batch expiring contracts: {e}")
            traceback.print_exc()

        return results

    def _get_teams_with_tags_batch(self) -> set:
        """
        Batch load all team IDs that have already used their tag.

        Returns set of team_ids that have already tagged a player.
        """
        teams_with_tags = set()

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT team_id FROM franchise_tags
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (self._dynasty_id, self._season + 1)
                )
                teams_with_tags = {row[0] for row in cursor.fetchall()}

        except Exception as e:
            print(f"[FranchiseTagService] Error getting teams with tags: {e}")

        return teams_with_tags

    def _is_player_tagged(self, player_id: int) -> bool:
        """Check if player is already tagged for next season."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM franchise_tags
                    WHERE player_id = ?
                      AND dynasty_id = ?
                      AND season = ?
                    """,
                    (player_id, self._dynasty_id, self._season + 1)
                )
                result = cursor.fetchone()
                return result[0] > 0 if result else False
        except Exception:
            return False