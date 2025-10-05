"""Generates complete NFL draft classes."""

import random
from typing import List
from ..models.generated_player import GeneratedPlayer
from ..core.generation_context import GenerationConfig, GenerationContext
from .player_generator import PlayerGenerator


class DraftClassGenerator:
    """Generates complete NFL draft classes."""

    # NFL draft structure
    ROUNDS = 7
    PICKS_PER_ROUND = 32
    TOTAL_PICKS = ROUNDS * PICKS_PER_ROUND  # 224 picks

    # Position distribution (percentage of each round)
    POSITION_DISTRIBUTION = {
        1: {  # Round 1: Premium positions
            "QB": 0.15, "EDGE": 0.20, "OT": 0.20, "WR": 0.15, "CB": 0.15, "DT": 0.10, "S": 0.05
        },
        2: {  # Round 2
            "QB": 0.10, "RB": 0.10, "WR": 0.15, "OT": 0.15, "EDGE": 0.15, "CB": 0.15, "S": 0.10, "LB": 0.10
        },
        3: {  # Round 3
            "RB": 0.12, "WR": 0.15, "TE": 0.10, "OG": 0.12, "OT": 0.10, "DT": 0.12, "EDGE": 0.10, "LB": 0.12, "CB": 0.07
        },
        4: {  # Round 4
            "RB": 0.10, "WR": 0.13, "TE": 0.10, "OG": 0.13, "OT": 0.10, "C": 0.06,
            "DT": 0.10, "EDGE": 0.10, "LB": 0.10, "CB": 0.10, "S": 0.08
        },
        5: {  # Round 5
            "RB": 0.09, "WR": 0.12, "TE": 0.09, "OG": 0.12, "OT": 0.09, "C": 0.07,
            "DT": 0.10, "EDGE": 0.09, "LB": 0.10, "CB": 0.08, "S": 0.05
        },
        6: {  # Round 6
            "RB": 0.08, "WR": 0.10, "TE": 0.09, "OG": 0.11, "OT": 0.08, "C": 0.08,
            "DT": 0.10, "EDGE": 0.08, "LB": 0.11, "CB": 0.08, "S": 0.09
        },
        7: {  # Round 7
            "RB": 0.08, "WR": 0.10, "TE": 0.09, "OG": 0.10, "OT": 0.08, "C": 0.08,
            "DT": 0.09, "EDGE": 0.08, "LB": 0.10, "CB": 0.10, "S": 0.10
        }
    }

    def __init__(self, generator: PlayerGenerator):
        """Initialize draft class generator.

        Args:
            generator: Player generator instance
        """
        self.generator = generator

    def generate_draft_class(
        self,
        year: int
    ) -> List[GeneratedPlayer]:
        """Generate complete draft class.

        Args:
            year: Draft year

        Returns:
            List of 224 generated players (7 rounds × 32 picks)
        """
        draft_class = []

        pick_number = 1
        for round_num in range(1, self.ROUNDS + 1):
            round_players = self._generate_round(
                round_num=round_num,
                year=year,
                start_pick=pick_number
            )
            draft_class.extend(round_players)
            pick_number += len(round_players)

        return draft_class

    def _generate_round(
        self,
        round_num: int,
        year: int,
        start_pick: int
    ) -> List[GeneratedPlayer]:
        """Generate all players for a single round.

        Args:
            round_num: Round number (1-7)
            year: Draft year
            start_pick: Starting pick number for this round

        Returns:
            List of 32 generated players for the round
        """
        players = []
        positions = self._get_round_positions(round_num)

        for i, position in enumerate(positions):
            pick_number = start_pick + i

            config = GenerationConfig(
                context=GenerationContext.NFL_DRAFT,
                position=position,
                draft_round=round_num,
                draft_pick=pick_number,
                draft_year=year
            )

            player = self.generator.generate_player(config)
            players.append(player)

        return players

    def _get_round_positions(self, round_num: int) -> List[str]:
        """Get position distribution for a round.

        Args:
            round_num: Round number (1-7)

        Returns:
            List of 32 positions for the round
        """
        distribution = self.POSITION_DISTRIBUTION.get(round_num, {})
        if not distribution:
            # Default distribution for later rounds
            distribution = {
                "RB": 0.10, "WR": 0.12, "TE": 0.08, "OG": 0.12, "OT": 0.08,
                "DT": 0.12, "EDGE": 0.10, "LB": 0.12, "CB": 0.10, "S": 0.06
            }

        positions = []
        for position, percentage in distribution.items():
            count = int(self.PICKS_PER_ROUND * percentage)
            positions.extend([position] * count)

        # Fill remaining slots randomly
        while len(positions) < self.PICKS_PER_ROUND:
            positions.append(random.choice(list(distribution.keys())))

        # Shuffle to randomize pick order
        random.shuffle(positions)
        return positions[:self.PICKS_PER_ROUND]