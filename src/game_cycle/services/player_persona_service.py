"""
Service for player persona generation and management.

Part of Tollgate 3: Persona Service.
Handles persona generation with weighted distribution, persistence, and display hints.
"""
import json
import logging
import random
import sqlite3
from typing import Dict, List, Optional, Tuple, Any

from src.player_management.player_persona import PlayerPersona, PersonaType
from src.game_cycle.database.persona_api import PersonaAPI, PersonaRecord
from src.utils.player_field_extractors import extract_overall_rating


# Base distribution weights (total = 100)
BASE_WEIGHTS: Dict[PersonaType, int] = {
    PersonaType.MONEY_FIRST: 25,
    PersonaType.COMPETITOR: 20,
    PersonaType.SYSTEM_FIT: 15,
    PersonaType.RING_CHASER: 12,
    PersonaType.LEGACY_BUILDER: 10,
    PersonaType.HOMETOWN_HERO: 8,
    PersonaType.BIG_MARKET: 5,
    PersonaType.SMALL_MARKET: 5,
}

# Preference templates: range (min, max) for each persona type
PERSONA_PREFERENCE_TEMPLATES: Dict[PersonaType, Dict[str, Tuple[int, int]]] = {
    PersonaType.RING_CHASER: {
        "winning_importance": (80, 95),
        "money_importance": (30, 50),
        "loyalty_importance": (20, 40),
    },
    PersonaType.MONEY_FIRST: {
        "money_importance": (85, 100),
        "winning_importance": (30, 50),
        "market_size_importance": (40, 60),
    },
    PersonaType.HOMETOWN_HERO: {
        "location_importance": (85, 100),
        "loyalty_importance": (70, 90),
        "money_importance": (30, 50),
    },
    PersonaType.BIG_MARKET: {
        "market_size_importance": (85, 100),
        "money_importance": (50, 70),
    },
    PersonaType.SMALL_MARKET: {
        "market_size_importance": (10, 30),  # Low = prefers small
        "location_importance": (60, 80),
    },
    PersonaType.LEGACY_BUILDER: {
        "loyalty_importance": (85, 100),
        "winning_importance": (50, 70),
        "money_importance": (30, 50),
    },
    PersonaType.COMPETITOR: {
        "playing_time_importance": (85, 100),
        "winning_importance": (60, 80),
    },
    PersonaType.SYSTEM_FIT: {
        "coaching_fit_importance": (85, 100),
        "playing_time_importance": (50, 70),
    },
}

# Own team hints (full details)
OWN_TEAM_HINTS: Dict[PersonaType, List[str]] = {
    PersonaType.RING_CHASER: [
        "Ring Chaser - Prioritizes winning championships",
        "May take discount for contenders",
        "Frustrated by losing seasons",
    ],
    PersonaType.MONEY_FIRST: [
        "Money First - Expects top dollar",
        "Will follow highest offer",
        "Unlikely to accept discounts",
    ],
    PersonaType.HOMETOWN_HERO: [
        "Hometown Hero - Strong location preference",
        "May discount to play near home",
        "Values family proximity",
    ],
    PersonaType.BIG_MARKET: [
        "Big Market - Wants major media exposure",
        "Prefers LA, NYC, Dallas markets",
        "Values endorsement opportunities",
    ],
    PersonaType.SMALL_MARKET: [
        "Small Market - Prefers quieter markets",
        "Avoids media spotlight",
        "Values privacy and community",
    ],
    PersonaType.LEGACY_BUILDER: [
        "Legacy Builder - Wants to be franchise icon",
        "Strong preference for current team",
        "Values long-term stability",
    ],
    PersonaType.COMPETITOR: [
        "Competitor - Wants significant playing time",
        "Will avoid bench roles",
        "Prioritizes starting opportunities",
    ],
    PersonaType.SYSTEM_FIT: [
        "System Fit - Values scheme compatibility",
        "Researches coaching staffs",
        "Prioritizes role clarity",
    ],
}

# Other team hints (vague)
OTHER_TEAM_HINTS: Dict[PersonaType, List[str]] = {
    PersonaType.RING_CHASER: ["Values winning over money"],
    PersonaType.MONEY_FIRST: ["Motivated by financial security"],
    PersonaType.HOMETOWN_HERO: ["Has strong geographic preferences"],
    PersonaType.BIG_MARKET: ["Prefers larger markets"],
    PersonaType.SMALL_MARKET: ["Prefers quieter markets"],
    PersonaType.LEGACY_BUILDER: ["Loyal to current team"],
    PersonaType.COMPETITOR: ["Wants significant playing time"],
    PersonaType.SYSTEM_FIT: ["Values scheme compatibility"],
}


class PlayerPersonaService:
    """Service for player persona generation and management.

    Follows the service pattern from training_camp_service.py.
    Uses lazy-loaded PersonaAPI for database operations.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """Initialize service.

        Args:
            db_path: Path to database file
            dynasty_id: Dynasty identifier for isolation
            season: Current season year (for age calculation)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)
        self._persona_api: Optional[PersonaAPI] = None

    def _get_persona_api(self) -> PersonaAPI:
        """Lazy-load PersonaAPI."""
        if self._persona_api is None:
            self._persona_api = PersonaAPI(self._db_path)
        return self._persona_api

    def generate_persona(
        self,
        player_id: int,
        age: int,
        overall: int,
        position: str,
        team_id: int,
        career_earnings: int = 0,
        championship_count: int = 0,
        birthplace_state: Optional[str] = None,
        college_state: Optional[str] = None,
    ) -> PlayerPersona:
        """Generate a persona for a player using weighted distribution.

        Args:
            player_id: Player ID
            age: Player age
            overall: Player overall rating
            position: Player position
            team_id: Current team ID (used as drafting team)
            career_earnings: Career earnings to date
            championship_count: Championships won
            birthplace_state: State of birth (optional)
            college_state: State of college (optional)

        Returns:
            Generated PlayerPersona
        """
        # Apply modifiers to base weights
        weights = self._apply_modifiers(
            BASE_WEIGHTS.copy(),
            age,
            overall,
            career_earnings,
            championship_count,
        )

        # Select persona type
        persona_type = self._select_persona_type(weights)

        # Generate preferences based on persona type
        preferences = self._generate_preferences(persona_type)

        return PlayerPersona(
            player_id=player_id,
            persona_type=persona_type,
            money_importance=preferences.get("money_importance", 50),
            winning_importance=preferences.get("winning_importance", 50),
            location_importance=preferences.get("location_importance", 50),
            playing_time_importance=preferences.get("playing_time_importance", 50),
            loyalty_importance=preferences.get("loyalty_importance", 50),
            market_size_importance=preferences.get("market_size_importance", 50),
            coaching_fit_importance=preferences.get("coaching_fit_importance", 50),
            relationships_importance=preferences.get("relationships_importance", 50),
            birthplace_state=birthplace_state,
            college_state=college_state,
            drafting_team_id=team_id,
            career_earnings=career_earnings,
            championship_count=championship_count,
            pro_bowl_count=0,
        )

    def _apply_modifiers(
        self,
        weights: Dict[PersonaType, int],
        age: int,
        overall: int,
        career_earnings: int,
        championship_count: int,
    ) -> Dict[PersonaType, int]:
        """Apply demographic modifiers to base weights.

        Args:
            weights: Base weights dict
            age: Player age
            overall: Player overall rating
            career_earnings: Career earnings
            championship_count: Championships won

        Returns:
            Modified weights dict
        """
        # Veterans (30+): +15% Ring Chaser
        if age >= 30:
            weights[PersonaType.RING_CHASER] += 15

        # High earners ($50M+ career): -10% Money First, +10% Ring Chaser
        if career_earnings >= 50_000_000:
            weights[PersonaType.MONEY_FIRST] -= 10
            weights[PersonaType.RING_CHASER] += 10

        # Ringless veterans (28+ with 0 championships): +20% Ring Chaser
        if age >= 28 and championship_count == 0:
            weights[PersonaType.RING_CHASER] += 20

        # High overall (85+): +10% Big Market (endorsement potential)
        if overall >= 85:
            weights[PersonaType.BIG_MARKET] += 10

        # Young players (< 26): +10% Money First (building wealth)
        if age < 26:
            weights[PersonaType.MONEY_FIRST] += 10

        # Normalize to prevent negatives
        for key in weights:
            weights[key] = max(0, weights[key])

        return weights

    def _select_persona_type(self, weights: Dict[PersonaType, int]) -> PersonaType:
        """Select persona type using weighted random choice.

        Args:
            weights: Dict mapping PersonaType to weight

        Returns:
            Selected PersonaType
        """
        total = sum(weights.values())
        if total == 0:
            return PersonaType.MONEY_FIRST  # Fallback

        r = random.randint(1, total)
        cumulative = 0
        for persona_type, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return persona_type

        return PersonaType.MONEY_FIRST  # Fallback

    def _generate_preferences(self, persona_type: PersonaType) -> Dict[str, int]:
        """Generate preference values based on persona type.

        Args:
            persona_type: The selected persona type

        Returns:
            Dict of preference name to value (0-100)
        """
        preferences: Dict[str, int] = {
            "money_importance": 50,
            "winning_importance": 50,
            "location_importance": 50,
            "playing_time_importance": 50,
            "loyalty_importance": 50,
            "market_size_importance": 50,
            "coaching_fit_importance": 50,
            "relationships_importance": 50,
        }

        template = PERSONA_PREFERENCE_TEMPLATES.get(persona_type, {})
        for pref_name, (min_val, max_val) in template.items():
            preferences[pref_name] = random.randint(min_val, max_val)

        return preferences

    def get_persona(self, player_id: int) -> Optional[PlayerPersona]:
        """Load a player's persona from the database.

        Args:
            player_id: Player ID

        Returns:
            PlayerPersona or None if not found
        """
        api = self._get_persona_api()
        data = api.get_persona(self._dynasty_id, player_id)
        if data:
            return PlayerPersona.from_db_row(data)
        return None

    def save_persona(self, persona: PlayerPersona) -> bool:
        """Persist a persona to the database.

        Args:
            persona: PlayerPersona to save

        Returns:
            True if successful
        """
        api = self._get_persona_api()
        record = PersonaRecord(
            player_id=persona.player_id,
            persona_type=persona.persona_type.value,
            money_importance=persona.money_importance,
            winning_importance=persona.winning_importance,
            location_importance=persona.location_importance,
            playing_time_importance=persona.playing_time_importance,
            loyalty_importance=persona.loyalty_importance,
            market_size_importance=persona.market_size_importance,
            coaching_fit_importance=persona.coaching_fit_importance,
            relationships_importance=persona.relationships_importance,
            birthplace_state=persona.birthplace_state,
            college_state=persona.college_state,
            drafting_team_id=persona.drafting_team_id,
            career_earnings=persona.career_earnings,
            championship_count=persona.championship_count,
            pro_bowl_count=persona.pro_bowl_count,
        )
        return api.insert_persona(self._dynasty_id, record)

    def update_career_context(
        self,
        player_id: int,
        earnings_added: int = 0,
        won_championship: bool = False,
        made_pro_bowl: bool = False,
    ) -> bool:
        """Update career stats for a player's persona.

        Args:
            player_id: Player ID
            earnings_added: Earnings to add to career total
            won_championship: Whether player won a championship
            made_pro_bowl: Whether player made Pro Bowl

        Returns:
            True if updated
        """
        # Get current persona
        persona = self.get_persona(player_id)
        if not persona:
            return False

        # Update values
        new_earnings = persona.career_earnings + earnings_added
        new_championships = persona.championship_count + (1 if won_championship else 0)
        new_pro_bowls = persona.pro_bowl_count + (1 if made_pro_bowl else 0)

        api = self._get_persona_api()
        return api.update_career_context(
            self._dynasty_id,
            player_id,
            new_earnings,
            new_championships,
            new_pro_bowls,
        )

    def get_display_hints(
        self, persona: PlayerPersona, is_own_team: bool
    ) -> List[str]:
        """Get UI display hints for a persona.

        Own team sees full details, other teams see vague hints.

        Args:
            persona: PlayerPersona to get hints for
            is_own_team: Whether viewing team owns this player

        Returns:
            List of hint strings
        """
        if is_own_team:
            hints = OWN_TEAM_HINTS.get(persona.persona_type, []).copy()
            # Add dynamic hints based on persona data
            if persona.birthplace_state and persona.persona_type == PersonaType.HOMETOWN_HERO:
                hints.append(f"Birthplace: {persona.birthplace_state}")
            if persona.college_state and persona.persona_type == PersonaType.HOMETOWN_HERO:
                hints.append(f"College State: {persona.college_state}")
            return hints
        else:
            return OTHER_TEAM_HINTS.get(persona.persona_type, ["Unknown preferences"])

    def persona_exists(self, player_id: int) -> bool:
        """Check if a persona exists for a player.

        Args:
            player_id: Player ID

        Returns:
            True if persona exists
        """
        api = self._get_persona_api()
        return api.persona_exists(self._dynasty_id, player_id)

    def generate_personas_for_team(self, team_id: int) -> List[PlayerPersona]:
        """Generate personas for all players on a team.

        Args:
            team_id: Team ID

        Returns:
            List of generated PlayerPersona objects
        """
        players = self._get_team_players(team_id)
        personas = []

        for player in players:
            # Skip if persona already exists
            if self.persona_exists(player["player_id"]):
                existing = self.get_persona(player["player_id"])
                if existing:
                    personas.append(existing)
                continue

            age, overall, position = self._parse_player_attributes(player)
            persona = self.generate_persona(
                player_id=player["player_id"],
                age=age,
                overall=overall,
                position=position,
                team_id=team_id,
            )
            self.save_persona(persona)
            personas.append(persona)

        return personas

    def generate_all_personas(self) -> Dict[str, Any]:
        """Generate personas for all players in the dynasty.

        Returns:
            Dict with stats: total, generated, existing
        """
        stats = {"total": 0, "generated": 0, "existing": 0}

        # Get all players
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT player_id, team_id, positions, attributes, birthdate
                FROM players
                WHERE dynasty_id = ?
            """,
                (self._dynasty_id,),
            )
            players = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

        for player in players:
            stats["total"] += 1

            if self.persona_exists(player["player_id"]):
                stats["existing"] += 1
                continue

            age, overall, position = self._parse_player_attributes(player)
            persona = self.generate_persona(
                player_id=player["player_id"],
                age=age,
                overall=overall,
                position=position,
                team_id=player.get("team_id") or 0,
            )
            self.save_persona(persona)
            stats["generated"] += 1

        return stats

    def _get_team_players(self, team_id: int) -> List[Dict[str, Any]]:
        """Get player data for a team.

        Args:
            team_id: Team ID

        Returns:
            List of player dicts with player_id, positions, attributes, birthdate
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT player_id, positions, attributes, birthdate
                FROM players
                WHERE dynasty_id = ? AND team_id = ?
            """,
                (self._dynasty_id, team_id),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _parse_player_attributes(self, player: Dict[str, Any]) -> Tuple[int, int, str]:
        """Extract age, overall, position from player data.

        Args:
            player: Dict with player data

        Returns:
            Tuple of (age, overall, position)
        """
        # Parse attributes JSON
        overall = extract_overall_rating(player, default=70)
        attributes = player.get("attributes", {})
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except json.JSONDecodeError:
                attributes = {}

        # Parse positions JSON
        positions = player.get("positions", [])
        if isinstance(positions, str):
            try:
                positions = json.loads(positions)
            except json.JSONDecodeError:
                positions = []
        position = positions[0] if positions else "unknown"

        # Calculate age from birthdate
        birthdate = player.get("birthdate")
        if birthdate:
            try:
                birth_year = int(birthdate.split("-")[0])
                age = self._season - birth_year
            except (ValueError, IndexError):
                age = 25  # Default
        else:
            age = 25  # Default

        return age, overall, position

    def get_persona_distribution(self) -> Dict[str, int]:
        """Get distribution of persona types in dynasty.

        Returns:
            Dict mapping persona type name to count
        """
        api = self._get_persona_api()
        all_personas = api.get_all_personas(self._dynasty_id)

        distribution: Dict[str, int] = {}
        for persona_data in all_personas:
            ptype = persona_data.get("persona_type", "unknown")
            distribution[ptype] = distribution.get(ptype, 0) + 1

        return distribution