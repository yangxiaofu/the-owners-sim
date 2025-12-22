"""
Mock Stats Generator for Game Cycle

Generates realistic-looking player stats for simulated games based on final scores
and player ratings. Stats are internally consistent (e.g., receiving yards sum to
passing yards) and align with scoring (TDs, FGs, XPs match final score).

This is used during the regular season simulation when we need player stats
without running the full play-by-play engine.

Usage:
    generator = MockStatsGenerator(db_path, dynasty_id)
    mock_stats = generator.generate(
        game_id="game_123",
        home_team_id=22,  # Detroit Lions
        away_team_id=15,  # Kansas City Chiefs
        home_score=28,
        away_score=24
    )

    # Insert into database
    for player_stat in mock_stats.player_stats:
        db.execute("INSERT INTO player_game_stats ...", player_stat)
"""

import json
import logging
import random
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.constants.position_abbreviations import get_position_abbreviation
from src.game_cycle.models.injury_models import Injury
from src.utils.player_field_extractors import extract_overall_rating

logger = logging.getLogger(__name__)


@dataclass
class MockGameStats:
    """Container for generated mock game statistics."""
    game_id: str
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    player_stats: List[Dict[str, Any]]  # Ready for DB insert into player_game_stats
    injuries: List[Injury] = field(default_factory=list)  # Injuries generated during game
    # Team-level stats for box scores (first_downs, 3rd/4th down, TOP, penalties)
    home_team_stats: Dict[str, Any] = field(default_factory=dict)
    away_team_stats: Dict[str, Any] = field(default_factory=dict)


class MockStatsGenerator:
    """
    Generates realistic mock player statistics for simulated games.

    Key Features:
    - Rating-weighted stats (elite players get better numbers)
    - Full stat coverage (all 40+ columns from player_game_stats)
    - Internal consistency (passing_yards == sum of receiving_yards)
    - Score alignment (TDs*6 + FGs*3 + XPs ≈ final score)
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int = 2025,
        season_type: str = "regular_season"
    ):
        """
        Initialize mock stats generator.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty context for roster lookups
            season: Current season year for injury tracking
            season_type: Type of season ('regular_season' or 'playoffs')
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season
        self.season_type = season_type

    def generate(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        week: int = 1
    ) -> MockGameStats:
        """
        Generate mock stats for both teams in a game.

        Args:
            game_id: Unique game identifier
            home_team_id: Home team ID (1-32)
            away_team_id: Away team ID (1-32)
            home_score: Final home team score
            away_score: Final away team score
            week: Game week number (for injury tracking)

        Returns:
            MockGameStats with player_stats and team_stats ready for database insertion
        """
        all_stats = []

        # Generate stats for home team
        home_stats = self._generate_team_stats(
            team_id=home_team_id,
            score=home_score,
            opponent_score=away_score,
            is_home=True,
            game_id=game_id
        )
        all_stats.extend(home_stats)

        # Generate stats for away team
        away_stats = self._generate_team_stats(
            team_id=away_team_id,
            score=away_score,
            opponent_score=home_score,
            is_home=False,
            game_id=game_id
        )
        all_stats.extend(away_stats)

        # Check for injuries among players who participated
        injuries = self._check_game_injuries(
            game_id=game_id,
            player_stats=all_stats,
            week=week
        )

        # Generate team-level stats for box scores (first_downs, 3rd/4th down, TOP, penalties)
        # Calculate yards using same logic as _generate_team_stats
        def calc_yards(score: int) -> tuple:
            base_yards = 350
            score_factor = max(0.5, min(2.0, score / 21))
            total_yards = int(base_yards * score_factor)
            passing_yards = int(total_yards * 0.60)
            rushing_yards = int(total_yards * 0.40)
            return total_yards, passing_yards, rushing_yards

        home_total, home_pass, home_rush = calc_yards(home_score)
        away_total, away_pass, away_rush = calc_yards(away_score)

        home_team_stats = self._generate_mock_team_stats(
            home_score, home_total, home_pass, home_rush
        )
        away_team_stats = self._generate_mock_team_stats(
            away_score, away_total, away_pass, away_rush
        )

        return MockGameStats(
            game_id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            player_stats=all_stats,
            injuries=injuries,
            home_team_stats=home_team_stats,
            away_team_stats=away_team_stats
        )

    def _generate_team_stats(
        self,
        team_id: int,
        score: int,
        opponent_score: int,
        is_home: bool,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Generate stats for one team.

        Args:
            team_id: Team ID (1-32)
            score: Team's final score
            opponent_score: Opponent's final score
            is_home: Whether this team is home
            game_id: Game identifier

        Returns:
            List of player stat dictionaries ready for DB insertion
        """
        # Get roster with positions and ratings
        roster = self._get_team_roster(team_id)

        # Decompose score into scoring plays
        tds, fgs, xps = self._estimate_scoring_plays(score)

        # Estimate total yards (NFL average ~350 yards/game, scale by score)
        base_yards = 350
        score_factor = max(0.5, min(2.0, score / 21))  # 21 = 3 TDs
        total_yards = int(base_yards * score_factor)

        # Allocate yards between passing and rushing (NFL avg: 60% pass, 40% rush)
        passing_yards = int(total_yards * 0.60)
        rushing_yards = int(total_yards * 0.40)

        # Allocate TDs between passing and rushing (NFL avg: 65% pass TDs, 35% rush TDs)
        passing_tds = int(tds * 0.65)
        rushing_tds = tds - passing_tds
        receiving_tds = passing_tds  # Receiving TDs = Passing TDs

        # Estimate total plays for defensive stats
        # NFL average: 60-70 plays per game
        total_plays = random.randint(58, 72)

        player_stats = []

        # Allocate QB stats
        qb_stats = self._allocate_passing_stats(
            roster, passing_tds, passing_yards, game_id
        )
        player_stats.extend(qb_stats)

        # Allocate rushing stats (RBs + QB scrambles)
        rush_stats = self._allocate_rushing_stats(
            roster, rushing_tds, rushing_yards, game_id
        )
        player_stats.extend(rush_stats)

        # Allocate receiving stats (must sum to passing yards)
        recv_stats = self._allocate_receiving_stats(
            roster, receiving_tds, passing_yards, game_id
        )
        player_stats.extend(recv_stats)

        # Allocate defensive stats
        def_stats = self._allocate_defensive_stats(
            roster, total_plays, game_id
        )
        player_stats.extend(def_stats)

        # Allocate kicker stats
        kicker_stats = self._allocate_kicker_stats(
            roster, fgs, xps, game_id
        )
        player_stats.extend(kicker_stats)

        # Allocate punter stats
        punter_stats = self._allocate_punter_stats(roster, game_id)
        player_stats.extend(punter_stats)

        # Allocate OL stats (basic placeholders)
        ol_stats = self._allocate_ol_stats(roster, game_id)
        player_stats.extend(ol_stats)

        # Merge duplicate player entries (e.g., RBs with both rushing and receiving)
        merged_stats = self._merge_player_stats(player_stats)

        return merged_stats

    def _merge_player_stats(
        self, stats_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple stat entries for the same player.

        This fixes the issue where RBs could appear twice: once for rushing stats
        and once for receiving stats. The merge combines numeric values additively.

        Args:
            stats_list: List of player stat dictionaries

        Returns:
            Merged list with one entry per player
        """
        player_stats_by_id = {}

        for stats in stats_list:
            player_id = stats.get('player_id')
            if player_id is None:
                continue

            if player_id in player_stats_by_id:
                # Merge: add numeric values, keep non-numeric from first entry
                existing = player_stats_by_id[player_id]
                for key, value in stats.items():
                    if key == 'player_id':
                        continue
                    if isinstance(value, (int, float)):
                        # Additive merge for numeric stats
                        existing[key] = existing.get(key, 0) + value
                    elif key not in existing or existing[key] is None:
                        # Keep first non-None value for non-numeric fields
                        existing[key] = value
            else:
                player_stats_by_id[player_id] = stats.copy()

        return list(player_stats_by_id.values())

    def _estimate_scoring_plays(self, score: int) -> Tuple[int, int, int]:
        """
        Estimate TDs, FGs, and XPs from final score.

        NFL averages per game:
        - 2.5-3.0 TDs (with XP = 7 points each)
        - 1.5-2.0 FGs (3 points each)

        Args:
            score: Final team score

        Returns:
            Tuple of (touchdowns, field_goals, xp_attempts)
        """
        if score == 0:
            return (0, 0, 0)

        if score <= 3:
            return (0, 1, 0)  # Single FG

        if score == 4:
            # Rare: 1 FG made + 1 missed (or safety + missed FG)
            return (0, 1, 0)

        if score == 5:
            # Extremely rare: Safety (2) + FG (3)
            return (0, 1, 0)

        if score == 6:
            return (0, 2, 0)  # Two FGs

        # For scores 7+: TD-first decomposition
        estimated_tds = score // 7
        remaining = score - (estimated_tds * 7)

        # Convert clean remaining points to FGs (0, 3, or 6 points)
        fgs = remaining // 3

        # Handle 1-2 point remainders (missed XPs or safeties)
        # DO NOT add extra FGs for these - they represent missed XPs or safeties
        leftover = remaining % 3
        # leftover of 1-2 points = missed XP or safety, not another FG

        # XP attempts = TDs (one attempt per touchdown)
        xp_attempts = estimated_tds

        # Sanity check: Cap FGs at 3 per game (NFL 99th percentile)
        # Prevents unrealistic scenarios from score estimation errors
        if fgs > 3:
            fgs = 3

        return (estimated_tds, fgs, xp_attempts)

    def _get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team roster with positions and ratings.

        Excludes players who are currently injured.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries with positions and attributes
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get active players excluding those with active injuries
            # Use team_rosters.team_id as source of truth (players.team_id may be stale after trades)
            query = """
                SELECT
                    p.player_id,
                    p.first_name,
                    p.last_name,
                    p.positions,
                    p.attributes,
                    tr.team_id
                FROM players p
                JOIN team_rosters tr
                    ON p.dynasty_id = tr.dynasty_id
                    AND p.player_id = tr.player_id
                LEFT JOIN player_injuries pi
                    ON p.dynasty_id = pi.dynasty_id
                    AND p.player_id = pi.player_id
                    AND pi.is_active = 1
                WHERE p.dynasty_id = ?
                    AND tr.team_id = ?
                    AND tr.roster_status = 'active'
                    AND pi.injury_id IS NULL
                ORDER BY tr.depth_chart_order
            """

            cursor.execute(query, (self.dynasty_id, team_id))
            rows = cursor.fetchall()

            if not rows:
                logger.warning(
                    "[MockStatsGenerator] Empty roster for team_id=%d, dynasty_id=%s. "
                    "Stats will not be generated. Check team_rosters table.",
                    team_id, self.dynasty_id
                )
                return []

            roster = []
            for row in rows:
                positions = json.loads(row['positions'])
                attributes = json.loads(row['attributes'])

                player_dict = {
                    'player_id': row['player_id'],
                    'player_name': f"{row['first_name']} {row['last_name']}",
                    'team_id': row['team_id'],
                    'positions': positions,
                    'primary_position': positions[0] if positions else 'unknown',
                    'attributes': attributes,
                }
                player_dict['overall'] = extract_overall_rating(player_dict, default=50)
                roster.append(player_dict)

            return roster

    def _allocate_passing_stats(
        self,
        roster: List[Dict],
        passing_tds: int,
        total_yards: int,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate passing stats to QB(s).

        Args:
            roster: Team roster
            passing_tds: Total passing TDs
            total_yards: Total passing yards
            game_id: Game identifier

        Returns:
            List of QB stat dictionaries
        """
        qbs = [p for p in roster if p['primary_position'] == 'quarterback']

        if not qbs:
            return []

        # Primary QB gets 95% of stats, backup gets 5%
        primary_qb = qbs[0]
        qb_rating = primary_qb['overall']

        # Generate attempts based on rating (20-45 attempts)
        attempts = self._rating_weighted_value(25, 42, qb_rating)

        # Completion percentage based on rating (55%-70%)
        comp_pct_min = 0.55 + (qb_rating - 40) / 100 * 0.10  # 55%-65%
        comp_pct = min(0.72, max(0.50, comp_pct_min + random.uniform(-0.03, 0.03)))
        completions = int(attempts * comp_pct)

        # Interceptions (0-3, fewer for high-rated QBs)
        # NFL average is ~2.5% INT rate, elite QBs ~1.5%, bad QBs ~3.5%
        base_int_rate = 0.025  # 2.5% base
        rating_modifier = (qb_rating - 70) / 100 * 0.015  # +/- 1.5% based on rating
        int_rate = max(0.01, min(0.04, base_int_rate - rating_modifier))
        expected_ints = attempts * int_rate
        # Use random to determine actual INTs (0-3 range based on expected)
        interceptions = min(3, max(0, int(expected_ints + random.uniform(-0.5, 1.0))))

        # Sacks (1-4, based on rating and randomness)
        sacks = random.randint(1, 4)
        sack_yards = sacks * random.randint(5, 9)

        # Passer rating (simple approximation: 70-120)
        passer_rating = self._calculate_passer_rating(
            attempts, completions, total_yards, passing_tds, interceptions
        )

        qb_stats = {
            'dynasty_id': self.dynasty_id,
            'game_id': game_id,
            'player_id': primary_qb['player_id'],
            'player_name': primary_qb['player_name'],
            'team_id': primary_qb['team_id'],
            'position': 'QB',
            'season_type': self.season_type,

            # Passing stats
            'passing_yards': total_yards,
            'passing_tds': passing_tds,
            'passing_attempts': attempts,
            'passing_completions': completions,
            'passing_interceptions': interceptions,
            'passing_sacks': sacks,
            'passing_sack_yards': sack_yards,
            'passing_rating': round(passer_rating, 1),

            # QB rushing (scrambles)
            'rushing_yards': random.randint(5, 25),
            'rushing_tds': 0,
            'rushing_attempts': random.randint(2, 5),
            'rushing_long': random.randint(8, 18),
            'rushing_fumbles': random.choices([0, 1, 2], weights=[70, 25, 5])[0],
            'fumbles_lost': random.choices([0, 1], weights=[80, 20])[0],
            'rushing_20_plus': random.randint(0, 1),

            # No receiving stats for QB
            'receiving_yards': 0,
            'receiving_tds': 0,
            'receptions': 0,
            'targets': 0,
            'receiving_long': 0,
            'receiving_drops': 0,

            # No defensive stats
            'tackles_total': 0,
            'tackles_solo': 0,
            'tackles_assist': 0,
            'sacks': 0.0,
            'interceptions': 0,
            'forced_fumbles': 0,
            'fumbles_recovered': 0,
            'passes_defended': 0,

            # No kicking stats
            'field_goals_made': 0,
            'field_goals_attempted': 0,
            'extra_points_made': 0,
            'extra_points_attempted': 0,
            'punts': 0,
            'punt_yards': 0,

            # OL stats (not applicable for QB)
            'pancakes': 0,
            'sacks_allowed': 0,
            'hurries_allowed': 0,
            'pressures_allowed': 0,
            'run_blocking_grade': 0.0,
            'pass_blocking_efficiency': 0.0,
            'missed_assignments': 0,
            'holding_penalties': 0,
            'false_start_penalties': 0,
            'downfield_blocks': 0,
            'double_team_blocks': 0,
            'chip_blocks': 0,

            # Snap counts
            'snap_counts_offense': random.randint(55, 68),
            'snap_counts_defense': 0,
            'snap_counts_special_teams': 0,

            'fantasy_points': self._calculate_fantasy_points(
                passing_yards=total_yards,
                passing_tds=passing_tds,
                interceptions=interceptions,
                rushing_yards=random.randint(5, 25),
                rushing_tds=0
            )
        }

        return [qb_stats]

    def _allocate_rushing_stats(
        self,
        roster: List[Dict],
        rushing_tds: int,
        total_yards: int,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate rushing stats to RBs (and FB if present).

        Args:
            roster: Team roster
            rushing_tds: Total rushing TDs
            total_yards: Total rushing yards
            game_id: Game identifier

        Returns:
            List of RB stat dictionaries
        """
        rbs = [p for p in roster if p['primary_position'] in ['running_back', 'fullback']]

        if not rbs:
            return []

        # Top 2 RBs split the work
        rb_stats_list = []

        for i, rb in enumerate(rbs[:2]):
            # RB1 gets ~70% of carries, RB2 gets ~30%
            split = 0.70 if i == 0 else 0.30

            yards = int(total_yards * split)
            attempts = self._rating_weighted_value(10, 25, rb['overall'])

            # TDs go to RB1 primarily
            tds = rushing_tds if i == 0 else 0

            # Long run (10-40 yards based on rating)
            long_run = self._rating_weighted_value(12, 35, rb['overall'])

            # Fumbles (rare: 0-1)
            fumbles = 1 if random.random() < 0.08 else 0

            rb_stats = {
                'dynasty_id': self.dynasty_id,
                'game_id': game_id,
                'player_id': rb['player_id'],
                'player_name': rb['player_name'],
                'team_id': rb['team_id'],
                'position': get_position_abbreviation(rb['primary_position']),
                'season_type': self.season_type,

                # No passing
                'passing_yards': 0,
                'passing_tds': 0,
                'passing_attempts': 0,
                'passing_completions': 0,
                'passing_interceptions': 0,
                'passing_sacks': 0,
                'passing_sack_yards': 0,
                'passing_rating': 0.0,

                # Rushing stats
                'rushing_yards': yards,
                'rushing_tds': tds,
                'rushing_attempts': attempts,
                'rushing_long': long_run,
                'rushing_fumbles': random.choices([0, 1, 2], weights=[70, 25, 5])[0],
                'fumbles_lost': random.choices([0, 1], weights=[80, 20])[0],
                'rushing_20_plus': random.randint(0, 3),

                # RBs can catch passes (handled in receiving allocation)
                'receiving_yards': 0,  # Will be filled by _allocate_receiving_stats
                'receiving_tds': 0,
                'receptions': 0,
                'targets': 0,
                'receiving_long': 0,
                'receiving_drops': 0,

                # No defensive stats
                'tackles_total': 0,
                'tackles_solo': 0,
                'tackles_assist': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'forced_fumbles': 0,
                'fumbles_recovered': 0,
                'passes_defended': 0,

                # No kicking
                'field_goals_made': 0,
                'field_goals_attempted': 0,
                'extra_points_made': 0,
                'extra_points_attempted': 0,
                'punts': 0,
                'punt_yards': 0,

                # OL stats
                'pancakes': 0,
                'sacks_allowed': 0,
                'hurries_allowed': 0,
                'pressures_allowed': 0,
                'run_blocking_grade': 0.0,
                'pass_blocking_efficiency': 0.0,
                'missed_assignments': 0,
                'holding_penalties': 0,
                'false_start_penalties': 0,
                'downfield_blocks': 0,
                'double_team_blocks': 0,
                'chip_blocks': 0,

                # Snap counts
                'snap_counts_offense': random.randint(30, 55) if i == 0 else random.randint(10, 25),
                'snap_counts_defense': 0,
                'snap_counts_special_teams': 0,

                'fantasy_points': self._calculate_fantasy_points(
                    rushing_yards=yards,
                    rushing_tds=tds,
                    receiving_yards=0,  # Updated later
                    receiving_tds=0
                )
            }

            rb_stats_list.append(rb_stats)

        return rb_stats_list

    def _allocate_receiving_stats(
        self,
        roster: List[Dict],
        receiving_tds: int,
        passing_yards: int,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate receiving stats to WRs, TEs, and RBs.

        CRITICAL: receiving_yards must sum to passing_yards for consistency.

        Args:
            roster: Team roster
            receiving_tds: Total receiving TDs (should equal passing TDs)
            passing_yards: Total passing yards to distribute
            game_id: Game identifier

        Returns:
            List of receiver stat dictionaries
        """
        wrs = [p for p in roster if p['primary_position'] == 'wide_receiver'][:3]
        tes = [p for p in roster if p['primary_position'] == 'tight_end'][:1]
        rbs = [p for p in roster if p['primary_position'] == 'running_back'][:2]

        receivers = wrs + tes + rbs

        if not receivers:
            return []

        # Allocation percentages (must sum to 1.0)
        # WR1: 30%, WR2: 25%, WR3: 15%, TE: 20%, RB: 10%
        allocations = []

        for i, wr in enumerate(wrs):
            if i == 0:
                allocations.append((wr, 0.30))
            elif i == 1:
                allocations.append((wr, 0.25))
            else:
                allocations.append((wr, 0.15))

        for te in tes:
            allocations.append((te, 0.20))

        for rb in rbs:
            allocations.append((rb, 0.05))

        # Normalize allocations to sum to 1.0
        total_alloc = sum(alloc for _, alloc in allocations)
        allocations = [(p, alloc / total_alloc) for p, alloc in allocations]

        receiver_stats_list = []
        yards_allocated = 0

        # Allocate TDs (give to top receivers)
        td_distribution = [1] * receiving_tds + [0] * (len(allocations) - receiving_tds)
        random.shuffle(td_distribution)

        for i, (player, alloc) in enumerate(allocations):
            yards = int(passing_yards * alloc)
            yards_allocated += yards

            # Adjust last receiver to ensure exact match
            if i == len(allocations) - 1:
                yards = passing_yards - (yards_allocated - yards)

            # Receptions based on yards and rating
            receptions = self._rating_weighted_value(3, 10, player['overall'])
            targets = int(receptions * random.uniform(1.3, 1.6))

            tds = td_distribution[i] if i < len(td_distribution) else 0

            # Long reception
            long_rec = self._rating_weighted_value(15, 45, player['overall'])

            # Drops (0-2)
            drops = random.randint(0, 2) if random.random() < 0.3 else 0

            # Yards after catch (YAC) - typically 30-60% of receiving yards
            yac_pct = random.uniform(0.35, 0.55)
            yac = int(yards * yac_pct)

            # Receiving fumbles (rare: about 1 in every 80-100 receptions)
            recv_fumbles = 1 if receptions > 0 and random.random() < 0.012 else 0

            recv_stats = {
                'dynasty_id': self.dynasty_id,
                'game_id': game_id,
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'team_id': player['team_id'],
                'position': get_position_abbreviation(player['primary_position']),
                'season_type': self.season_type,

                # No passing
                'passing_yards': 0,
                'passing_tds': 0,
                'passing_attempts': 0,
                'passing_completions': 0,
                'passing_interceptions': 0,
                'passing_sacks': 0,
                'passing_sack_yards': 0,
                'passing_rating': 0.0,

                # No rushing (RBs handled separately)
                'rushing_yards': 0,
                'rushing_tds': 0,
                'rushing_attempts': 0,
                'rushing_long': 0,
                'rushing_fumbles': 0,
                'fumbles_lost': 0,
                'rushing_20_plus': 0,

                # Receiving stats
                'receiving_yards': yards,
                'receiving_tds': tds,
                'receptions': receptions,
                'targets': targets,
                'receiving_long': long_rec,
                'receiving_drops': drops,
                'yards_after_catch': yac,
                'receiving_fumbles': recv_fumbles,

                # No defensive stats
                'tackles_total': 0,
                'tackles_solo': 0,
                'tackles_assist': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'forced_fumbles': 0,
                'fumbles_recovered': 0,
                'passes_defended': 0,

                # No kicking
                'field_goals_made': 0,
                'field_goals_attempted': 0,
                'extra_points_made': 0,
                'extra_points_attempted': 0,
                'punts': 0,
                'punt_yards': 0,

                # OL stats
                'pancakes': 0,
                'sacks_allowed': 0,
                'hurries_allowed': 0,
                'pressures_allowed': 0,
                'run_blocking_grade': 0.0,
                'pass_blocking_efficiency': 0.0,
                'missed_assignments': 0,
                'holding_penalties': 0,
                'false_start_penalties': 0,
                'downfield_blocks': 0,
                'double_team_blocks': 0,
                'chip_blocks': 0,

                # Snap counts
                'snap_counts_offense': random.randint(25, 60),
                'snap_counts_defense': 0,
                'snap_counts_special_teams': 0,

                'fantasy_points': self._calculate_fantasy_points(
                    receiving_yards=yards,
                    receiving_tds=tds,
                    receptions=receptions
                )
            }

            receiver_stats_list.append(recv_stats)

        return receiver_stats_list

    def _allocate_defensive_stats(
        self,
        roster: List[Dict],
        total_plays: int,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate defensive stats (tackles, sacks, INTs) across defense.

        Args:
            roster: Team roster
            total_plays: Estimated opponent plays (for tackle distribution)
            game_id: Game identifier

        Returns:
            List of defensive player stat dictionaries
        """
        # Get defensive players
        lbs = [p for p in roster if 'linebacker' in p['primary_position']][:3]
        dbs = [p for p in roster if p['primary_position'] in ['cornerback', 'safety', 'free_safety', 'strong_safety']][:4]
        dline = [p for p in roster if p['primary_position'] in ['defensive_end', 'defensive_tackle', 'nose_tackle']][:4]

        defenders = lbs + dbs + dline

        if not defenders:
            return []

        # Total tackles ≈ total plays (each play has ~1-2 tackles)
        total_tackles = int(total_plays * random.uniform(1.1, 1.3))

        # Distribute sacks (2-5 total team sacks)
        total_sacks = random.randint(2, 5)
        sack_pool = [0.5] * (total_sacks * 2)  # Split into half sacks

        # Distribute INTs (0-2 per game)
        total_ints = random.randint(0, 2)
        int_pool = [1] * total_ints

        def_stats_list = []
        tackles_allocated = 0

        for i, player in enumerate(defenders):
            pos = player['primary_position']

            # Tackle distribution by position
            if 'linebacker' in pos:
                tackle_share = 0.15  # LBs get most tackles
            elif pos in ['safety', 'strong_safety', 'free_safety']:
                tackle_share = 0.10
            elif pos == 'cornerback':
                tackle_share = 0.05
            else:  # D-line
                tackle_share = 0.08

            tackles = int(total_tackles * tackle_share)
            tackles_allocated += tackles

            # Solo vs assist (roughly 60/40 split)
            solo_tackles = int(tackles * 0.60)
            assist_tackles = tackles - solo_tackles

            # Sacks (DL and edge rushers get priority)
            sacks = 0.0
            if pos in ['defensive_end', 'outside_linebacker'] and sack_pool:
                num_sacks = min(random.randint(0, 2), len(sack_pool))
                for _ in range(num_sacks):
                    if sack_pool:
                        sacks += sack_pool.pop()

            # Interceptions (DBs get priority)
            ints = 0
            if pos in ['cornerback', 'safety', 'free_safety', 'strong_safety'] and int_pool:
                if random.random() < 0.3 and int_pool:
                    ints = int_pool.pop()

            # Other defensive stats
            forced_fumbles = 1 if random.random() < 0.05 else 0
            fumbles_recovered = 1 if random.random() < 0.03 else 0
            passes_defended = random.randint(0, 3) if 'cornerback' in pos or 'safety' in pos else 0

            def_stats = {
                'dynasty_id': self.dynasty_id,
                'game_id': game_id,
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'team_id': player['team_id'],
                'position': get_position_abbreviation(player['primary_position']),
                'season_type': self.season_type,

                # No offensive stats
                'passing_yards': 0,
                'passing_tds': 0,
                'passing_attempts': 0,
                'passing_completions': 0,
                'passing_interceptions': 0,
                'passing_sacks': 0,
                'passing_sack_yards': 0,
                'passing_rating': 0.0,

                'rushing_yards': 0,
                'rushing_tds': 0,
                'rushing_attempts': 0,
                'rushing_long': 0,
                'rushing_fumbles': 0,
                'fumbles_lost': 0,
                'rushing_20_plus': 0,

                'receiving_yards': 0,
                'receiving_tds': 0,
                'receptions': 0,
                'targets': 0,
                'receiving_long': 0,
                'receiving_drops': 0,

                # Defensive stats
                'tackles_total': tackles,
                'tackles_solo': solo_tackles,
                'tackles_assist': assist_tackles,
                'sacks': sacks,
                'interceptions': ints,
                'forced_fumbles': forced_fumbles,
                'fumbles_recovered': fumbles_recovered,
                'passes_defended': passes_defended,

                # No kicking
                'field_goals_made': 0,
                'field_goals_attempted': 0,
                'extra_points_made': 0,
                'extra_points_attempted': 0,
                'punts': 0,
                'punt_yards': 0,

                # OL stats
                'pancakes': 0,
                'sacks_allowed': 0,
                'hurries_allowed': 0,
                'pressures_allowed': 0,
                'run_blocking_grade': 0.0,
                'pass_blocking_efficiency': 0.0,
                'missed_assignments': 0,
                'holding_penalties': 0,
                'false_start_penalties': 0,
                'downfield_blocks': 0,
                'double_team_blocks': 0,
                'chip_blocks': 0,

                # Snap counts
                'snap_counts_offense': 0,
                'snap_counts_defense': random.randint(45, 65),
                'snap_counts_special_teams': random.randint(5, 12),

                'fantasy_points': self._calculate_fantasy_points(
                    tackles=tackles,
                    sacks=sacks,
                    interceptions=ints
                )
            }

            def_stats_list.append(def_stats)

        return def_stats_list

    def _allocate_kicker_stats(
        self,
        roster: List[Dict],
        fgs: int,
        xp_attempts: int,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate FG and XP stats to kicker.

        Args:
            roster: Team roster
            fgs: Field goals made
            xp_attempts: Extra point attempts (one per TD)
            game_id: Game identifier

        Returns:
            List with single kicker stat dictionary
        """
        kickers = [p for p in roster if p['primary_position'] == 'kicker']

        if not kickers:
            return []

        kicker = kickers[0]

        # FG attempts based on NFL weighted average 88% accuracy
        # Use probabilistic rounding to avoid inflating misses
        if fgs > 0:
            # NFL weighted average: 88% success rate (95% at 0-39, 85% at 40-49, 65% at 50+)
            # Working backward: made / 0.88 = attempts
            # Example: 3 made → 3/0.88 = 3.41 → round to 3 or 4 (59% chance 3/3, 41% chance 3/4)
            # Better: 3 made → round to 3 or 4 probabilistically
            base_attempts = fgs / 0.88
            fg_attempts = int(base_attempts)  # Floor value

            # Probabilistically add 1 more attempt based on remainder
            # This gives correct average: 3 made → 3.41 attempts avg
            remainder = base_attempts - fg_attempts
            if random.random() < remainder:
                fg_attempts += 1
        else:
            # No FGs made - very rarely attempt and miss
            # Assume 0-1 attempts when no FGs were made (10% chance)
            fg_attempts = 1 if random.random() < 0.10 else 0

        # XP made based on NFL average 98% accuracy
        # Logic: Start with all XP attempts, then apply 2% miss rate probabilistically
        if xp_attempts > 0:
            # Calculate expected misses (2% miss rate)
            # Example: 3 attempts → 3 * 0.02 = 0.06 misses → 94% chance 0 misses, 6% chance 1 miss
            expected_misses = xp_attempts * 0.02
            actual_misses = int(expected_misses)

            # Probabilistically add 1 more miss based on remainder
            remainder = expected_misses - actual_misses
            if random.random() < remainder:
                actual_misses += 1

            # XP made = attempts - misses
            xp_made = xp_attempts - actual_misses
        else:
            xp_made = 0

        kicker_stats = {
            'dynasty_id': self.dynasty_id,
            'game_id': game_id,
            'player_id': kicker['player_id'],
            'player_name': kicker['player_name'],
            'team_id': kicker['team_id'],
            'position': 'K',
            'season_type': self.season_type,

            # No offensive stats
            'passing_yards': 0,
            'passing_tds': 0,
            'passing_attempts': 0,
            'passing_completions': 0,
            'passing_interceptions': 0,
            'passing_sacks': 0,
            'passing_sack_yards': 0,
            'passing_rating': 0.0,

            'rushing_yards': 0,
            'rushing_tds': 0,
            'rushing_attempts': 0,
            'rushing_long': 0,
            'rushing_fumbles': 0,
            'fumbles_lost': 0,
            'rushing_20_plus': 0,

            'receiving_yards': 0,
            'receiving_tds': 0,
            'receptions': 0,
            'targets': 0,
            'receiving_long': 0,
            'receiving_drops': 0,

            # No defensive stats
            'tackles_total': 0,
            'tackles_solo': 0,
            'tackles_assist': 0,
            'sacks': 0.0,
            'interceptions': 0,
            'forced_fumbles': 0,
            'fumbles_recovered': 0,
            'passes_defended': 0,

            # Kicking stats
            'field_goals_made': fgs,
            'field_goals_attempted': fg_attempts,
            'extra_points_made': xp_made,
            'extra_points_attempted': xp_attempts,
            'punts': 0,
            'punt_yards': 0,

            # OL stats
            'pancakes': 0,
            'sacks_allowed': 0,
            'hurries_allowed': 0,
            'pressures_allowed': 0,
            'run_blocking_grade': 0.0,
            'pass_blocking_efficiency': 0.0,
            'missed_assignments': 0,
            'holding_penalties': 0,
            'false_start_penalties': 0,
            'downfield_blocks': 0,
            'double_team_blocks': 0,
            'chip_blocks': 0,

            # Snap counts - include kickoffs (typically 5-8 per game)
            'snap_counts_offense': 0,
            'snap_counts_defense': 0,
            'snap_counts_special_teams': fg_attempts + xp_attempts + random.randint(4, 8),

            'fantasy_points': fgs * 3  # Simple: 3 pts per FG
        }

        return [kicker_stats]

    def _allocate_punter_stats(
        self,
        roster: List[Dict],
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate punting stats to punter.

        Args:
            roster: Team roster
            game_id: Game identifier

        Returns:
            List with single punter stat dictionary
        """
        punters = [p for p in roster if p['primary_position'] == 'punter']

        if not punters:
            return []

        punter = punters[0]

        # NFL average: 4-6 punts per game
        punts = random.randint(3, 7)

        # Punt yards: NFL average 45-48 yards per punt
        avg_punt_distance = random.randint(42, 50)
        punt_yards = punts * avg_punt_distance

        # Punt long: best punt of the game
        punt_long = avg_punt_distance + random.randint(5, 15)

        # Inside 20: roughly 40% of punts
        punts_inside_20 = int(punts * random.uniform(0.3, 0.5))

        # Touchbacks: roughly 10% of punts
        touchbacks = int(punts * random.uniform(0.05, 0.15))

        punter_stats = {
            'dynasty_id': self.dynasty_id,
            'game_id': game_id,
            'player_id': punter['player_id'],
            'player_name': punter['player_name'],
            'team_id': punter['team_id'],
            'position': 'P',
            'season_type': self.season_type,

            # No offensive stats
            'passing_yards': 0,
            'passing_tds': 0,
            'passing_attempts': 0,
            'passing_completions': 0,
            'passing_interceptions': 0,
            'passing_sacks': 0,
            'passing_sack_yards': 0,
            'passing_rating': 0.0,

            'rushing_yards': 0,
            'rushing_tds': 0,
            'rushing_attempts': 0,
            'rushing_long': 0,
            'rushing_fumbles': 0,
            'fumbles_lost': 0,
            'rushing_20_plus': 0,

            'receiving_yards': 0,
            'receiving_tds': 0,
            'receptions': 0,
            'targets': 0,
            'receiving_long': 0,
            'receiving_drops': 0,

            # No defensive stats
            'tackles_total': 0,
            'tackles_solo': 0,
            'tackles_assist': 0,
            'sacks': 0.0,
            'interceptions': 0,
            'forced_fumbles': 0,
            'fumbles_recovered': 0,
            'passes_defended': 0,

            # Kicking stats - punting only
            'field_goals_made': 0,
            'field_goals_attempted': 0,
            'extra_points_made': 0,
            'extra_points_attempted': 0,
            'punts': punts,
            'punt_yards': punt_yards,
            'punt_long': punt_long,
            'punts_inside_20': punts_inside_20,
            'punt_touchbacks': touchbacks,

            # OL stats
            'pancakes': 0,
            'sacks_allowed': 0,
            'hurries_allowed': 0,
            'pressures_allowed': 0,
            'run_blocking_grade': 0.0,
            'pass_blocking_efficiency': 0.0,
            'missed_assignments': 0,
            'holding_penalties': 0,
            'false_start_penalties': 0,
            'downfield_blocks': 0,
            'double_team_blocks': 0,
            'chip_blocks': 0,

            # Snap counts
            'snap_counts_offense': 0,
            'snap_counts_defense': 0,
            'snap_counts_special_teams': punts,

            'fantasy_points': 0.0  # Punters don't get fantasy points in standard scoring
        }

        return [punter_stats]

    def _allocate_ol_stats(
        self,
        roster: List[Dict],
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate basic OL stats (pancakes, sacks allowed, etc.).

        Args:
            roster: Team roster
            game_id: Game identifier

        Returns:
            List of OL stat dictionaries
        """
        ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']
        ol_players = [p for p in roster if p['primary_position'] in ol_positions][:5]

        if not ol_players:
            return []

        # Position-specific grade modifiers (tackles = pass blocking, guards = run blocking)
        POSITION_MODIFIERS = {
            'left_tackle': {'run_blocking': -3, 'pass_blocking': +5},   # Pass protection focus
            'right_tackle': {'run_blocking': -2, 'pass_blocking': +4},
            'left_guard': {'run_blocking': +4, 'pass_blocking': -2},    # Run blocking focus
            'right_guard': {'run_blocking': +3, 'pass_blocking': -1},
            'center': {'run_blocking': +2, 'pass_blocking': +2},        # Balanced + snapping
        }

        ol_stats_list = []

        for player in ol_players:
            rating = player['overall']
            position = player['primary_position']
            modifiers = POSITION_MODIFIERS.get(position, {'run_blocking': 0, 'pass_blocking': 0})

            # Individual variance unique to each player (creates differentiation)
            individual_variance = random.randint(-5, 5)

            # Pancakes (crushing blocks): 0-3 per game
            pancakes = random.randint(0, 3) if rating > 75 else random.randint(0, 1)

            # Sacks allowed (inverse of rating)
            sacks_allowed = 1 if random.random() < (90 - rating) / 100 else 0

            # Hurries/pressures
            hurries = random.randint(0, 2)
            pressures = random.randint(0, 3)

            # Grades (0-100 scale) - now with position-specific modifiers and larger variance
            run_grade = min(100, max(50, rating + modifiers['run_blocking'] + random.randint(-15, 15) + individual_variance))
            pass_eff = min(100, max(50, rating + modifiers['pass_blocking'] + random.randint(-15, 15) + individual_variance))

            # Penalties
            holding = 1 if random.random() < 0.08 else 0
            false_start = 1 if random.random() < 0.05 else 0

            ol_stats = {
                'dynasty_id': self.dynasty_id,
                'game_id': game_id,
                'player_id': player['player_id'],
                'player_name': player['player_name'],
                'team_id': player['team_id'],
                'position': get_position_abbreviation(player['primary_position']),
                'season_type': self.season_type,

                # No offensive skill stats
                'passing_yards': 0,
                'passing_tds': 0,
                'passing_attempts': 0,
                'passing_completions': 0,
                'passing_interceptions': 0,
                'passing_sacks': 0,
                'passing_sack_yards': 0,
                'passing_rating': 0.0,

                'rushing_yards': 0,
                'rushing_tds': 0,
                'rushing_attempts': 0,
                'rushing_long': 0,
                'rushing_fumbles': 0,
                'fumbles_lost': 0,
                'rushing_20_plus': 0,

                'receiving_yards': 0,
                'receiving_tds': 0,
                'receptions': 0,
                'targets': 0,
                'receiving_long': 0,
                'receiving_drops': 0,

                # No defensive stats
                'tackles_total': 0,
                'tackles_solo': 0,
                'tackles_assist': 0,
                'sacks': 0.0,
                'interceptions': 0,
                'forced_fumbles': 0,
                'fumbles_recovered': 0,
                'passes_defended': 0,

                # No kicking
                'field_goals_made': 0,
                'field_goals_attempted': 0,
                'extra_points_made': 0,
                'extra_points_attempted': 0,
                'punts': 0,
                'punt_yards': 0,

                # OL stats
                'pancakes': pancakes,
                'sacks_allowed': sacks_allowed,
                'hurries_allowed': hurries,
                'pressures_allowed': pressures,
                'run_blocking_grade': float(run_grade),
                'pass_blocking_efficiency': float(pass_eff),
                'missed_assignments': random.randint(0, 1),
                'holding_penalties': holding,
                'false_start_penalties': false_start,
                'downfield_blocks': random.randint(0, 2),
                'double_team_blocks': random.randint(1, 4),
                'chip_blocks': random.randint(0, 2),

                # Snap counts
                'snap_counts_offense': random.randint(55, 68),
                'snap_counts_defense': 0,
                'snap_counts_special_teams': 0,

                'fantasy_points': 0.0  # OL doesn't get fantasy points
            }

            ol_stats_list.append(ol_stats)

        return ol_stats_list

    def _rating_weighted_value(self, base_min: int, base_max: int, rating: int) -> int:
        """
        Generate a value weighted by player rating.

        Rating 99 = max of range, Rating 40 = min of range

        Args:
            base_min: Minimum value for low-rated players
            base_max: Maximum value for high-rated players
            rating: Player overall rating (0-99)

        Returns:
            Value in range [base_min, base_max] scaled by rating
        """
        # Clamp rating to 40-99 range
        rating = max(40, min(99, rating))

        # Scale rating to 0-1
        rating_factor = (rating - 40) / 59.0

        # Calculate base value
        range_size = base_max - base_min
        base_value = base_min + int(range_size * rating_factor)

        # Add small random variance
        variance = random.randint(-3, 3)

        return max(base_min, min(base_max, base_value + variance))

    def _calculate_passer_rating(
        self,
        attempts: int,
        completions: int,
        yards: int,
        tds: int,
        ints: int
    ) -> float:
        """
        Calculate NFL passer rating using official formula.

        The NFL passer rating formula uses 4 components (a, b, c, d),
        each capped between 0 and 2.375. The final rating is the
        average of these components multiplied by 100/6.

        Args:
            attempts: Pass attempts
            completions: Completions
            yards: Passing yards
            tds: Passing TDs
            ints: Interceptions

        Returns:
            Passer rating (0-158.3 scale)
        """
        if attempts == 0:
            return 0.0

        # Component a: Completion percentage
        a = ((completions / attempts) - 0.3) * 5
        a = max(0, min(2.375, a))

        # Component b: Yards per attempt
        b = ((yards / attempts) - 3) * 0.25
        b = max(0, min(2.375, b))

        # Component c: Touchdown percentage
        c = (tds / attempts) * 20
        c = max(0, min(2.375, c))

        # Component d: Interception percentage (inverse)
        d = 2.375 - ((ints / attempts) * 25)
        d = max(0, min(2.375, d))

        # Final rating
        rating = ((a + b + c + d) / 6) * 100

        return round(rating, 1)

    def _check_game_injuries(
        self,
        game_id: str,
        player_stats: List[Dict[str, Any]],
        week: int
    ) -> List[Injury]:
        """
        Check for injuries among players who participated in the game.

        Uses snap count data to weight injury probability - players who
        play more snaps have higher chance of injury.

        Args:
            game_id: Game identifier
            player_stats: List of player stat dictionaries with snap counts
            week: Game week number

        Returns:
            List of injuries that occurred during the game
        """
        from src.game_cycle.services.injury_service import InjuryService

        injuries = []
        injury_service = InjuryService(self.db_path, self.dynasty_id, self.season)

        for player_stat in player_stats:
            # Calculate total snaps played
            total_snaps = (
                player_stat.get('snap_counts_offense', 0) +
                player_stat.get('snap_counts_defense', 0) +
                player_stat.get('snap_counts_special_teams', 0)
            )

            # Skip players who didn't play
            if total_snaps == 0:
                continue

            # Build player dict for injury generation
            player_data = self._build_player_data_for_injury(player_stat)

            if not player_data:
                continue

            # Generate injury (returns None if no injury)
            injury = injury_service.generate_injury(
                player=player_data,
                week=week,
                occurred_during='game',
                game_id=game_id
            )

            if injury:
                injuries.append(injury)

        return injuries

    def _build_player_data_for_injury(
        self,
        player_stat: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Build player data dictionary needed for injury generation.

        Fetches additional player info from database (attributes, birthdate)
        that isn't included in the basic stat dictionary.

        Args:
            player_stat: Player stat dictionary from game stats

        Returns:
            Player data dict with all fields needed for injury generation,
            or None if player not found
        """
        player_id = player_stat.get('player_id')
        if not player_id:
            return None

        # Fetch player details from database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    player_id,
                    first_name,
                    last_name,
                    team_id,
                    positions,
                    attributes,
                    birthdate
                FROM players
                WHERE dynasty_id = ? AND player_id = ?
            """, (self.dynasty_id, player_id))

            row = cursor.fetchone()

            if not row:
                return None

            # Parse JSON fields
            positions = json.loads(row['positions']) if row['positions'] else []
            attributes = json.loads(row['attributes']) if row['attributes'] else {}

            return {
                'player_id': row['player_id'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'team_id': row['team_id'],
                'positions': positions,
                'attributes': attributes,
                'birthdate': row['birthdate']
            }

    def _calculate_fantasy_points(
        self,
        passing_yards: int = 0,
        passing_tds: int = 0,
        interceptions: int = 0,
        rushing_yards: int = 0,
        rushing_tds: int = 0,
        receiving_yards: int = 0,
        receiving_tds: int = 0,
        receptions: int = 0,
        tackles: int = 0,
        sacks: float = 0.0,
        **kwargs
    ) -> float:
        """
        Calculate fantasy points (standard scoring).

        Args:
            passing_yards: Passing yards (0.04 pts/yd)
            passing_tds: Passing TDs (4 pts)
            interceptions: Interceptions thrown (-2 pts)
            rushing_yards: Rushing yards (0.1 pts/yd)
            rushing_tds: Rushing TDs (6 pts)
            receiving_yards: Receiving yards (0.1 pts/yd)
            receiving_tds: Receiving TDs (6 pts)
            receptions: Receptions (0.5 pts PPR)
            tackles: Tackles (1 pt)
            sacks: Sacks (2 pts)

        Returns:
            Total fantasy points
        """
        points = 0.0

        # Passing
        points += passing_yards * 0.04
        points += passing_tds * 4
        points -= interceptions * 2

        # Rushing
        points += rushing_yards * 0.1
        points += rushing_tds * 6

        # Receiving
        points += receiving_yards * 0.1
        points += receiving_tds * 6
        points += receptions * 0.5  # PPR

        # Defense (IDP scoring)
        points += tackles * 1
        points += sacks * 2

        return round(points, 1)

    def _generate_mock_team_stats(
        self,
        score: int,
        total_yards: int,
        passing_yards: int,
        rushing_yards: int
    ) -> Dict[str, Any]:
        """
        Generate realistic mock team-level stats for box scores.

        These stats cannot be derived from player stats alone - they track
        team-level events like first downs, 3rd/4th down conversions,
        time of possession, and penalties.

        Args:
            score: Team's final score
            total_yards: Total yards (passing + rushing)
            passing_yards: Passing yards
            rushing_yards: Rushing yards

        Returns:
            Dict with team stats ready for box_scores table
        """
        # First downs: ~1 per 15 yards gained (NFL average ~20-25 per game)
        first_downs = max(8, int(total_yards / 15) + random.randint(-3, 3))

        # 3rd down: NFL average ~40% conversion rate, 10-18 attempts per game
        third_down_att = random.randint(10, 18)
        third_down_conv = int(third_down_att * random.uniform(0.30, 0.50))

        # 4th down: 0-4 attempts per game, ~50% conversion rate
        fourth_down_att = random.randint(0, 4)
        fourth_down_conv = int(fourth_down_att * random.uniform(0.40, 0.60))

        # Time of possession: 25-35 minutes per team (in seconds: 1500-2100)
        # Winning teams often have more TOP, but not always
        base_top = 1800  # 30 min in seconds
        score_modifier = (score - 21) * 15  # +/- 15 sec per point from average
        time_of_possession = max(1500, min(2100, base_top + score_modifier + random.randint(-120, 120)))

        # Penalties: NFL average ~5-7 per game, 40-60 yards
        penalties = random.randint(3, 10)
        penalty_yards = penalties * random.randint(6, 10)

        return {
            'first_downs': first_downs,
            'third_down_attempts': third_down_att,
            'third_down_conversions': third_down_conv,
            'fourth_down_attempts': fourth_down_att,
            'fourth_down_conversions': fourth_down_conv,
            'time_of_possession_seconds': time_of_possession,
            'penalties': penalties,
            'penalty_yards': penalty_yards,
            'total_yards': total_yards,
            'passing_yards': passing_yards,
            'rushing_yards': rushing_yards,
        }
