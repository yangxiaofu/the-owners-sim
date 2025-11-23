"""
Draft Commentary Generator

Generates contextual draft pick commentary based on GM archetype personalities.
Used in draft demo to illustrate how GM traits influence draft decisions.
"""

import random
from typing import Dict, List, Optional, Any

from constants.team_ids import get_team_name


class DraftCommentaryGenerator:
    """
    Generates realistic draft commentary based on GM archetype and pick context.

    Commentary adapts to:
    - GM archetype (win_now, rebuilder, star_chaser, conservative, balanced, aggressive_trader)
    - Prospect attributes (floor, ceiling, age, position)
    - Draft context (reach, value, BPA vs need)
    """

    # Commentary template library
    COMMENTARY_TEMPLATES = {
        "win_now": {
            "high_floor_pick": [
                "{team} targets polished {position} {player} for immediate impact",
                "Championship window drives {team}'s selection of NFL-ready {player}",
                "{team} prioritizes proven production with {player} ({overall} OVR, high floor)",
                "With title aspirations, {team} selects safe, high-floor {player}",
            ],
            "avoid_project": [
                "With title aspirations, {team} passes on project {alt_player}, selects safe {player}",
                "{team}'s win-now approach avoids raw prospects, targets polished {player}",
            ],
            "premium_position": [
                "{team} addresses championship need at {position} with {player}",
                "Elite {position} {player} fits {team}'s contention timeline perfectly",
                "{team} invests in premium {position} for playoff push",
            ],
        },

        "rebuilder": {
            "high_ceiling_pick": [
                "Rebuilding {team} swings for upside with {player} ({ceiling} ceiling)",
                "{team} prioritizes long-term potential over polish with raw {player}",
                "Patient {team} invests in developmental {position} {player}",
                "{team}'s multi-year timeline allows gamble on high-ceiling {player}",
            ],
            "youth_bonus": [
                "{team}'s rebuild allows gamble on {age}-year-old {player}",
                "Young {player} ({age}) fits {team}'s long-term foundation plan",
                "{team} builds for future with youthful {position} {player}",
            ],
            "premium_foundation": [
                "Building foundation: {team} secures premium {position} {player}",
                "{team} prioritizes cornerstone talent at {position} with {player}",
                "Franchise-building pick: {team} lands {position} {player}",
            ],
        },

        "star_chaser": {
            "boom_or_bust": [
                "Risk-tolerant {team} bets on explosive upside of {player}",
                "{team} chases superstar potential with boom-or-bust {player}",
                "High-risk, high-reward: {team} targets {player}'s {ceiling} ceiling",
                "{team} gambles on All-Pro upside of volatile {player}",
            ],
            "elite_traits": [
                "{team} willing to gamble on elite physical traits of raw {player}",
                "Elite athleticism drives {team}'s selection of {player}",
                "{team} prioritizes star potential over floor with {player}",
            ],
            "reach": [
                "{team} reaches for {player} due to elite ceiling potential",
                "Aggressive {team} moves ahead of market on boom prospect {player}",
                "{team} willing to overpay for superstar upside of {player}",
            ],
        },

        "conservative": {
            "safe_pick": [
                "Conservative {team} sticks to high-floor prospect {player}",
                "{team} avoids risk with proven college producer {player}",
                "No gambles for {team}: {player} offers NFL-ready skills",
                "Risk-averse {team} targets low-variance {player}",
            ],
            "production_focus": [
                "{team} values {player}'s extensive college production",
                "Proven performer {player} fits {team}'s conservative approach",
                "{team} trusts {player}'s consistent college track record",
            ],
            "avoid_boom_bust": [
                "{team} passes on volatile prospects, selects safe {player}",
                "Risk-averse {team} avoids boom-or-bust players, takes {player}",
            ],
        },

        "balanced": {
            "bpa": [
                "BPA philosophy: {team} selects top-graded {player}",
                "{team} ignores positional need, targets best available {player}",
                "Value-driven pick: {team} capitalizes on {player}'s slide",
                "{team} trusts their board, drafts {player} as top player",
            ],
            "position_depth": [
                "{team} trusts their board, drafts {player} despite depth at {position}",
                "Talent over need: {team} adds {position} {player}",
                "{team} prioritizes value over roster construction with {player}",
            ],
            "grade_drop": [
                "{team} refuses to reach, selects top remaining player {player}",
                "Strict to their board, {team} takes {player} ({overall} OVR)",
                "{team} follows their grades, drafts {player}",
            ],
        },

        "aggressive_trader": {
            "versatility": [
                "Active trader {team} targets versatile {player}",
                "{team} values {player}'s multi-position flexibility",
                "Positional flexibility key: {team} selects {player}",
            ],
            "scheme_fit": [
                "{team}'s aggressive GM secures scheme-perfect {player}",
                "Scheme match drives {team}'s selection of {player}",
                "{team} prioritizes scheme fit with {player} pick",
            ],
            "trade_activity": [
                "Trade-happy {team} moves up for priority target {player}",
                "{team} executes trade to secure {player}",
                "Aggressive {team} trades assets for {player}",
            ],
        },
    }

    def __init__(self):
        """Initialize commentary generator"""
        pass

    def generate_commentary(
        self,
        team_id: int,
        archetype: str,
        selected_prospect: Dict[str, Any],
        team_needs: Optional[List[Dict[str, Any]]] = None,
        pick_position: Optional[int] = None,
    ) -> str:
        """
        Generate contextual draft commentary based on GM archetype and pick context.

        Args:
            team_id: Team making selection (1-32)
            archetype: GM archetype key (win_now, rebuilder, star_chaser, etc.)
            selected_prospect: Dict with prospect data
                Required: first_name, last_name, position, overall
                Optional: ceiling, floor, age, projected_pick_min, projected_pick_max
            team_needs: Optional list of team need dicts with urgency_score and position
            pick_position: Optional current pick number

        Returns:
            Formatted commentary string

        Example:
            >>> gen = DraftCommentaryGenerator()
            >>> prospect = {
            ...     'first_name': 'Caleb',
            ...     'last_name': 'Williams',
            ...     'position': 'quarterback',
            ...     'overall': 92,
            ...     'ceiling': 95,
            ...     'floor': 88,
            ...     'age': 21
            ... }
            >>> commentary = gen.generate_commentary(
            ...     team_id=1,
            ...     archetype='rebuilder',
            ...     selected_prospect=prospect
            ... )
            >>> print(commentary)
            "Rebuilding Arizona Cardinals swing for upside with Caleb Williams (95 ceiling)"
        """
        # Get team name
        team_name = get_team_name(team_id)

        # Extract prospect data
        player_name = f"{selected_prospect['first_name']} {selected_prospect['last_name']}"
        position = selected_prospect['position']
        overall = selected_prospect['overall']
        ceiling = selected_prospect.get('ceiling', overall + 5)
        floor = selected_prospect.get('floor', overall - 5)
        age = selected_prospect.get('age', 21)
        projected_min = selected_prospect.get('projected_pick_min', pick_position or 15)
        projected_max = selected_prospect.get('projected_pick_max', (pick_position or 15) + 10)

        # Determine pick context
        is_high_floor = (overall - floor) <= 5
        is_high_ceiling = (ceiling - overall) >= 10
        is_reach = pick_position and pick_position < (projected_min - 5)
        is_value = pick_position and pick_position > (projected_max + 10)
        is_premium_pos = position in ['quarterback', 'left_tackle', 'defensive_end', 'cornerback']
        is_critical_need = False

        if team_needs:
            is_critical_need = any(
                n['urgency_score'] >= 5 and n['position'] == position
                for n in team_needs
            )

        # Select template category based on archetype and context
        category = self._select_category(
            archetype=archetype,
            is_high_floor=is_high_floor,
            is_high_ceiling=is_high_ceiling,
            is_reach=is_reach,
            is_value=is_value,
            is_premium_pos=is_premium_pos,
            is_critical_need=is_critical_need,
            age=age,
        )

        # Get templates for archetype
        archetype_key = self._normalize_archetype_key(archetype)
        templates = self.COMMENTARY_TEMPLATES.get(
            archetype_key,
            self.COMMENTARY_TEMPLATES['balanced']
        )

        # Select random template from category
        if category not in templates:
            # Fallback to first available category
            category = list(templates.keys())[0]

        template = random.choice(templates[category])

        # Format template
        commentary = template.format(
            team=team_name,
            player=player_name,
            position=self._format_position(position),
            overall=overall,
            ceiling=ceiling,
            floor=floor,
            age=age,
            projected_pick=f"{projected_min}-{projected_max}",
            alt_player="[alternative prospect]",  # Placeholder for future enhancement
            alt_overall="XX",  # Placeholder
        )

        return commentary

    def _normalize_archetype_key(self, archetype: str) -> str:
        """
        Normalize archetype string to template key.

        Handles variations like:
        - "Win-Now" -> "win_now"
        - "Star Chaser" -> "star_chaser"
        - "aggressive_trader" -> "aggressive_trader"
        """
        normalized = archetype.lower().replace('-', '_').replace(' ', '_')

        # Map special cases
        archetype_map = {
            'draft_hoarder': 'rebuilder',  # Draft hoarders behave like rebuilders in draft
            'bpa': 'balanced',  # BPA is balanced archetype
        }

        return archetype_map.get(normalized, normalized)

    def _select_category(
        self,
        archetype: str,
        is_high_floor: bool,
        is_high_ceiling: bool,
        is_reach: bool,
        is_value: bool,
        is_premium_pos: bool,
        is_critical_need: bool,
        age: int,
    ) -> str:
        """
        Select commentary category based on archetype and pick context.

        Args:
            archetype: GM archetype string
            is_high_floor: Prospect has high floor (overall - floor <= 5)
            is_high_ceiling: Prospect has high ceiling (ceiling - overall >= 10)
            is_reach: Pick is reach (pick < projected_min - 5)
            is_value: Pick is value (pick > projected_max + 10)
            is_premium_pos: Position is premium (QB, LT, Edge, CB)
            is_critical_need: Position matches critical team need
            age: Prospect age

        Returns:
            Category key for template selection
        """
        normalized = self._normalize_archetype_key(archetype)

        if normalized == 'win_now':
            if is_high_floor:
                return 'high_floor_pick'
            elif is_premium_pos:
                return 'premium_position'
            else:
                return 'avoid_project'

        elif normalized == 'rebuilder':
            if is_high_ceiling:
                return 'high_ceiling_pick'
            elif age <= 21:
                return 'youth_bonus'
            elif is_premium_pos:
                return 'premium_foundation'
            else:
                return 'high_ceiling_pick'

        elif normalized == 'star_chaser':
            if is_high_ceiling:
                return 'boom_or_bust'
            elif is_reach:
                return 'reach'
            else:
                return 'elite_traits'

        elif normalized == 'conservative':
            if is_high_floor:
                return 'safe_pick'
            else:
                return 'production_focus'

        elif normalized == 'balanced':
            if is_value:
                return 'bpa'
            elif not is_critical_need:
                return 'position_depth'
            else:
                return 'grade_drop'

        elif normalized == 'aggressive_trader':
            # Check for versatility flag in future
            return 'scheme_fit'

        else:
            # Default to balanced BPA
            return 'bpa'

    def _format_position(self, position: str) -> str:
        """
        Format position string for display.

        Args:
            position: Position string (e.g., 'quarterback', 'defensive_end')

        Returns:
            Formatted position string (e.g., 'Quarterback', 'Defensive End')
        """
        return position.replace('_', ' ').title()

    def generate_archetype_summary(
        self,
        team_id: int,
        archetype_name: str,
        risk_tolerance: float,
        win_now_mentality: float,
        draft_pick_value: float,
    ) -> str:
        """
        Generate summary of GM archetype traits for display.

        Args:
            team_id: Team ID
            archetype_name: Archetype name (e.g., "Win-Now", "Rebuilder")
            risk_tolerance: Risk tolerance trait (0.0-1.0)
            win_now_mentality: Win-now mentality trait (0.0-1.0)
            draft_pick_value: Draft pick value trait (0.0-1.0)

        Returns:
            Formatted archetype summary string

        Example:
            "Arizona Cardinals GM: Rebuilder (Risk: 0.35 | Win-Now: 0.20 | Draft Value: 0.85)"
        """
        team_name = get_team_name(team_id)

        summary = (
            f"{team_name} GM: {archetype_name} "
            f"(Risk: {risk_tolerance:.2f} | "
            f"Win-Now: {win_now_mentality:.2f} | "
            f"Draft Value: {draft_pick_value:.2f})"
        )

        return summary
