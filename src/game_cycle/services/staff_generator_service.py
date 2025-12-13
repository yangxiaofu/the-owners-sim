"""
Staff Generator Service - Procedural generation of GM and HC candidates.

Part of Milestone 13: Owner Review.
Generates realistic names, trait variations, and backgrounds for
staff candidates when user fires their GM or HC.
"""

import random
import uuid
from typing import List, Dict, Any, Optional


class StaffGeneratorService:
    """
    Service for procedurally generating GM and HC candidates.

    Features:
    - Random American name generation
    - Trait variation around archetype baselines
    - Background/history generation

    Usage:
        generator = StaffGeneratorService()
        candidates = generator.generate_gm_candidates(count=5)
    """

    # Name pools for procedural generation
    FIRST_NAMES = [
        "John", "Mike", "Tom", "Bill", "Dave", "Steve", "Chris", "Dan",
        "Jim", "Bob", "Mark", "Kevin", "Brian", "Jeff", "Scott", "Matt",
        "Eric", "Ryan", "Jason", "Patrick", "Andrew", "Sean", "Nick",
        "Brandon", "Kyle", "Adam", "Aaron", "Josh", "Tim", "Joe",
        "Greg", "Rob", "Pete", "Rich", "Doug", "Gary", "Paul", "Terry",
        "Don", "Ray", "Tony", "Frank", "Lou", "Ed", "Ron", "Larry"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
        "Wilson", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
        "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez",
        "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "King", "Wright",
        "Scott", "Green", "Adams", "Baker", "Nelson", "Carter", "Mitchell",
        "Perez", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans",
        "Collins", "Edwards", "Stewart", "Flores", "Morris", "Murphy", "Cook",
        "Rogers", "Morgan", "Peterson", "Cooper", "Reed", "Bailey", "Bell"
    ]

    # GM archetype keys (from base_archetypes.json)
    GM_ARCHETYPES = [
        "win_now", "rebuilder", "balanced", "aggressive_trader",
        "conservative", "draft_hoarder", "star_chaser"
    ]

    # HC archetype keys (from head_coaches/*.json)
    HC_ARCHETYPES = [
        "balanced", "aggressive", "conservative", "ultra_aggressive",
        "ultra_conservative", "andy_reid", "bill_belichick", "sean_mcvay",
        "kyle_shanahan", "kevin_stefanski"
    ]

    # Background templates
    GM_BACKGROUNDS = [
        "Former scout who rose through the ranks with the {team}. Known for {trait}.",
        "Spent {years} years in the {team} front office. Reputation for {trait}.",
        "Previously worked as Director of Player Personnel. Values {trait}.",
        "Former agent turned executive. Unique perspective on {trait}.",
        "Analytics pioneer who helped build {team}'s scouting department. Focuses on {trait}.",
        "Long-time football operations executive with experience at multiple clubs. Excels at {trait}.",
        "Rose from intern to GM candidate through {years} years of hard work. Prioritizes {trait}.",
        "Former college football coach who transitioned to the front office. Emphasizes {trait}.",
    ]

    HC_BACKGROUNDS = [
        "Former {position} coach who served as coordinator for the {team}. Known for {style} approach.",
        "Developed under {mentor}, bringing a {style} philosophy to head coaching.",
        "Spent {years} years as offensive coordinator. Philosophy emphasizes {style} football.",
        "First-time head coach with innovative ideas about {style} gameplay.",
        "Veteran coach with {years} years of NFL experience. Trusted for {style} leadership.",
        "Former player turned coach, brings real-world experience and {style} mentality.",
        "Offensive mastermind who engineered multiple top-10 offenses. Prefers {style} schemes.",
        "Defensive coordinator who built championship-caliber units. Believes in {style} play.",
    ]

    TRAITS = [
        "building through the draft", "cap management", "player development",
        "making bold trades", "finding undervalued talent", "developing young players",
        "veteran leadership", "roster construction", "analytics-based decisions",
        "culture building", "winning mentality", "patience in rebuilds",
        "identifying talent", "contract negotiations", "long-term planning"
    ]

    STYLES = [
        "aggressive", "balanced", "innovative", "old-school",
        "player-friendly", "disciplined", "risk-taking", "conservative",
        "analytics-driven", "fundamentals-focused", "adaptable", "creative"
    ]

    TEAMS = [
        "Patriots", "Chiefs", "Ravens", "49ers", "Cowboys", "Packers",
        "Steelers", "Eagles", "Bills", "Rams", "Seahawks", "Broncos",
        "Giants", "Bears", "Saints", "Colts", "Dolphins", "Vikings"
    ]

    MENTORS = [
        "Bill Belichick", "Andy Reid", "Sean McVay", "Kyle Shanahan",
        "Mike Tomlin", "John Harbaugh", "Pete Carroll", "Mike McCarthy",
        "Sean Payton", "Jon Gruden", "Tony Dungy", "Bill Walsh"
    ]

    POSITIONS = [
        "offensive line", "quarterback", "wide receiver", "defensive back",
        "linebacker", "running back", "tight end", "defensive line"
    ]

    def __init__(self):
        """Initialize the service."""
        pass

    def generate_gm_candidates(
        self,
        count: int = 5,
        exclude_archetypes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate GM candidates with varied archetypes.

        Args:
            count: Number of candidates (3-5 recommended)
            exclude_archetypes: Archetypes to skip (e.g., current GM's)

        Returns:
            List of candidate dictionaries with staff fields
        """
        exclude = exclude_archetypes or []
        available = [a for a in self.GM_ARCHETYPES if a not in exclude]

        # Ensure we have enough archetypes
        if len(available) < count:
            available = self.GM_ARCHETYPES.copy()

        candidates = []
        used_names = set()
        used_archetypes = []

        for i in range(count):
            # Generate unique name
            name = self._generate_unique_name(used_names)
            used_names.add(name)

            # Select archetype (cycle through available, avoid recent repeats)
            remaining = [a for a in available if a not in used_archetypes[-2:]]
            if not remaining:
                remaining = available
            archetype = random.choice(remaining)
            used_archetypes.append(archetype)

            # Generate trait variations
            custom_traits = self._generate_gm_trait_variations(archetype)

            # Generate history
            history = self._generate_gm_history(archetype)

            candidates.append({
                "staff_id": str(uuid.uuid4()),
                "name": name,
                "archetype_key": archetype,
                "custom_traits": custom_traits,
                "history": history,
            })

        return candidates

    def generate_hc_candidates(
        self,
        count: int = 5,
        exclude_archetypes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate Head Coach candidates with varied archetypes.

        Args:
            count: Number of candidates (3-5 recommended)
            exclude_archetypes: Archetypes to skip

        Returns:
            List of candidate dictionaries
        """
        exclude = exclude_archetypes or []
        available = [a for a in self.HC_ARCHETYPES if a not in exclude]

        # Ensure we have enough archetypes
        if len(available) < count:
            available = self.HC_ARCHETYPES.copy()

        candidates = []
        used_names = set()
        used_archetypes = []

        for i in range(count):
            # Generate unique name
            name = self._generate_unique_name(used_names)
            used_names.add(name)

            # Select archetype
            remaining = [a for a in available if a not in used_archetypes[-2:]]
            if not remaining:
                remaining = available
            archetype = random.choice(remaining)
            used_archetypes.append(archetype)

            # Generate trait variations
            custom_traits = self._generate_hc_trait_variations(archetype)

            # Generate history
            history = self._generate_hc_history(archetype)

            candidates.append({
                "staff_id": str(uuid.uuid4()),
                "name": name,
                "archetype_key": archetype,
                "custom_traits": custom_traits,
                "history": history,
            })

        return candidates

    def _generate_unique_name(self, used: set) -> str:
        """Generate a unique full name."""
        for _ in range(100):  # Max attempts
            first = random.choice(self.FIRST_NAMES)
            last = random.choice(self.LAST_NAMES)
            full = f"{first} {last}"
            if full not in used:
                return full
        # Fallback with suffix
        return f"{random.choice(self.FIRST_NAMES)} {random.choice(self.LAST_NAMES)} Jr."

    def _generate_gm_trait_variations(self, archetype: str) -> Dict[str, float]:
        """
        Generate random variations around GM archetype baseline.

        Adds +/- 0.1 noise to 2-3 traits for personality.

        Args:
            archetype: GM archetype key

        Returns:
            Dict of trait name to variation value
        """
        variations = {}
        all_traits = [
            "risk_tolerance", "win_now_mentality", "draft_pick_value",
            "cap_management", "trade_frequency", "star_chasing",
            "veteran_preference", "loyalty"
        ]

        traits_to_vary = random.sample(all_traits, k=random.randint(2, 3))

        for trait in traits_to_vary:
            # Generate variation value (not delta, but final value offset)
            base_approx = 0.5  # Approximate base
            noise = random.uniform(-0.15, 0.15)
            variations[trait] = max(0.0, min(1.0, base_approx + noise))

        return variations

    def _generate_hc_trait_variations(self, archetype: str) -> Dict[str, float]:
        """
        Generate random variations around HC archetype baseline.

        Args:
            archetype: HC archetype key

        Returns:
            Dict of trait variations
        """
        variations = {}
        all_traits = [
            "aggression", "risk_tolerance", "fourth_down_aggression",
            "conservatism", "run_preference", "adaptability"
        ]

        traits_to_vary = random.sample(all_traits, k=random.randint(2, 3))

        for trait in traits_to_vary:
            base_approx = 0.5
            noise = random.uniform(-0.15, 0.15)
            variations[trait] = max(0.0, min(1.0, base_approx + noise))

        return variations

    def _generate_gm_history(self, archetype: str) -> str:
        """
        Generate a background story for GM candidate.

        Args:
            archetype: GM archetype key

        Returns:
            Generated history string
        """
        template = random.choice(self.GM_BACKGROUNDS)
        return template.format(
            team=random.choice(self.TEAMS),
            years=random.randint(5, 15),
            trait=random.choice(self.TRAITS)
        )

    def _generate_hc_history(self, archetype: str) -> str:
        """
        Generate a background story for HC candidate.

        Args:
            archetype: HC archetype key

        Returns:
            Generated history string
        """
        template = random.choice(self.HC_BACKGROUNDS)
        return template.format(
            team=random.choice(self.TEAMS),
            years=random.randint(5, 20),
            style=random.choice(self.STYLES),
            mentor=random.choice(self.MENTORS),
            position=random.choice(self.POSITIONS)
        )
