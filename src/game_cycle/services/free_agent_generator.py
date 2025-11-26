"""
Free Agent Generator for Game Cycle.

Generates low-tier free agents to replenish the free agent pool each season.
"""

from typing import Dict, List, Any, Optional
import logging
import random


class FreeAgentGenerator:
    """
    Generator for low-tier free agents.

    Creates free agents per season with:
    - Overall ratings: 55-70 (backups/depth players)
    - Ages: 26-35 (veterans, not rookies)
    - Realistic position distribution
    - Inserted as team_id=0 (free agent pool)
    """

    # Position distribution for free agent generation
    POSITION_DISTRIBUTION = {
        "QB": 0.04,    # ~2 QBs
        "RB": 0.08,    # ~4 RBs
        "WR": 0.12,    # ~6 WRs
        "TE": 0.06,    # ~3 TEs
        "OT": 0.08,    # ~4 OTs
        "OG": 0.08,    # ~4 OGs
        "C": 0.04,     # ~2 Centers
        "EDGE": 0.08,  # ~4 Edge
        "DT": 0.08,    # ~4 DTs
        "LB": 0.10,    # ~5 LBs
        "CB": 0.10,    # ~5 CBs
        "S": 0.08,     # ~4 Safeties
        "K": 0.02,     # ~1 Kicker
        "P": 0.02,     # ~1 Punter
    }

    MIN_OVERALL = 55
    MAX_OVERALL = 70
    MIN_AGE = 26
    MAX_AGE = 35
    DEFAULT_COUNT = 50

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the free agent generator.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded components
        self._player_generator = None
        self._archetype_registry = None
        self._roster_api = None

    def generate_free_agents(
        self,
        count: int = DEFAULT_COUNT,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate free agents and insert into database.

        Args:
            count: Number of free agents to generate (default 50)
            min_overall: Optional minimum overall (default 55)
            max_overall: Optional maximum overall (default 70)

        Returns:
            Dict with success status and generation results
        """
        from player_generation.core.generation_context import GenerationConfig, GenerationContext

        min_ovr = min_overall or self.MIN_OVERALL
        max_ovr = max_overall or self.MAX_OVERALL

        generator = self._get_player_generator()
        registry = self._get_archetype_registry()

        # Get position counts
        position_counts = self._get_position_counts(count)

        players = []
        by_position = {}

        for position, pos_count in position_counts.items():
            by_position[position] = 0

            for _ in range(pos_count):
                # Get random archetype for position
                archetype = registry.select_random_archetype(position)
                if archetype is None:
                    self._logger.warning(f"No archetype found for position {position}")
                    continue

                # Generate random age (veterans)
                age = random.randint(self.MIN_AGE, self.MAX_AGE)

                # Create generation config
                config = GenerationConfig(
                    context=GenerationContext.CUSTOM,
                    position=position,
                    archetype_id=archetype.archetype_id,
                    overall_min=min_ovr,
                    overall_max=max_ovr,
                    age=age,
                    dynasty_id=self._dynasty_id,
                    enable_scouting_error=False,  # No scouting for FAs
                )

                # Generate player
                try:
                    player = generator.generate_player(config, archetype)
                    player_id = self._insert_free_agent(player)

                    players.append({
                        "player_id": player_id,
                        "name": player.name,
                        "position": player.position,
                        "overall": player.true_overall,
                        "age": age,
                    })
                    by_position[position] += 1

                except Exception as e:
                    self._logger.error(f"Failed to generate {position}: {e}")

        self._logger.info(f"Generated {len(players)} free agents")

        return {
            "success": True,
            "count": len(players),
            "players": players,
            "by_position": by_position,
        }

    def get_existing_free_agent_count(self) -> int:
        """Get count of existing free agents in the pool."""
        roster_api = self._get_roster_api()
        free_agents = roster_api.get_free_agents(self._dynasty_id)
        return len(free_agents)

    def _get_position_counts(self, total: int) -> Dict[str, int]:
        """Calculate position counts based on distribution."""
        counts = {}
        remaining = total

        for position, percentage in self.POSITION_DISTRIBUTION.items():
            count = int(total * percentage)
            counts[position] = count
            remaining -= count

        # Distribute remaining to common positions
        common_positions = ["WR", "LB", "CB", "RB"]
        idx = 0
        while remaining > 0:
            pos = common_positions[idx % len(common_positions)]
            counts[pos] += 1
            remaining -= 1
            idx += 1

        return counts

    def _insert_free_agent(self, player) -> int:
        """
        Insert generated free agent into database.

        Args:
            player: GeneratedPlayer instance

        Returns:
            Assigned player_id
        """
        roster_api = self._get_roster_api()

        # Split name
        name_parts = player.name.split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else "Generated"
        last_name = name_parts[1] if len(name_parts) > 1 else "Player"

        # Build attributes dict with overall
        attributes = dict(player.true_ratings)
        attributes["overall"] = player.true_overall

        # Generate jersey number
        jersey_number = self._get_jersey_number(player.position)

        # Generate birthdate from age
        birthdate = self._generate_birthdate(player.age)

        # Build player data
        player_data = {
            "first_name": first_name,
            "last_name": last_name,
            "number": jersey_number,
            "positions": [player.position],
            "attributes": attributes,
            "birthdate": birthdate,
        }

        # Insert with team_id=0 (free agent)
        player_id = roster_api.add_generated_player(
            dynasty_id=self._dynasty_id,
            player_data=player_data,
            team_id=0  # Free agent
        )

        return player_id

    def _generate_birthdate(self, age: int) -> str:
        """Generate birthdate string from age."""
        birth_year = self._season - age
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        return f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

    def _get_jersey_number(self, position: str) -> int:
        """Get appropriate jersey number for position."""
        ranges = {
            "QB": (1, 19),
            "RB": (20, 49),
            "WR": (10, 19),
            "TE": (80, 89),
            "OT": (70, 79),
            "OG": (60, 79),
            "C": (50, 79),
            "DT": (90, 99),
            "DE": (90, 99),
            "EDGE": (90, 99),
            "LB": (50, 59),
            "CB": (20, 39),
            "S": (20, 49),
            "K": (1, 19),
            "P": (1, 19),
        }
        min_num, max_num = ranges.get(position, (1, 99))
        return random.randint(min_num, max_num)

    # ========================================================================
    # LAZY-LOADED HELPERS
    # ========================================================================

    def _get_player_generator(self):
        """Lazy-load PlayerGenerator."""
        if self._player_generator is None:
            from player_generation.generators.player_generator import PlayerGenerator
            self._player_generator = PlayerGenerator()
        return self._player_generator

    def _get_archetype_registry(self):
        """Lazy-load ArchetypeRegistry."""
        if self._archetype_registry is None:
            from player_generation.archetypes.archetype_registry import ArchetypeRegistry
            self._archetype_registry = ArchetypeRegistry()
        return self._archetype_registry

    def _get_roster_api(self):
        """Lazy-load PlayerRosterAPI."""
        if self._roster_api is None:
            from database.player_roster_api import PlayerRosterAPI
            self._roster_api = PlayerRosterAPI(self._db_path)
        return self._roster_api