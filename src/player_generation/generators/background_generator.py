"""Generates player background including college and hometown."""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from ..models.generated_player import PlayerBackground
from ..core.generation_context import GenerationConfig, GenerationContext


class BackgroundGenerator:
    """Generates player background including college, hometown, and combine stats."""

    # US cities by state for hometown generation
    CITIES_BY_STATE = {
        "AL": ["Birmingham", "Mobile", "Huntsville", "Montgomery", "Tuscaloosa"],
        "AK": ["Anchorage", "Fairbanks", "Juneau"],
        "AZ": ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale"],
        "AR": ["Little Rock", "Fort Smith", "Fayetteville", "Springdale"],
        "CA": ["Los Angeles", "San Diego", "San Francisco", "Oakland", "Fresno", "Sacramento", "Long Beach", "Bakersfield"],
        "CO": ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Boulder"],
        "CT": ["Hartford", "New Haven", "Bridgeport", "Stamford"],
        "DE": ["Wilmington", "Dover", "Newark"],
        "FL": ["Miami", "Jacksonville", "Tampa", "Orlando", "Fort Lauderdale", "Tallahassee", "Gainesville"],
        "GA": ["Atlanta", "Augusta", "Savannah", "Columbus", "Macon"],
        "HI": ["Honolulu", "Pearl City", "Hilo"],
        "ID": ["Boise", "Meridian", "Nampa", "Idaho Falls"],
        "IL": ["Chicago", "Aurora", "Naperville", "Rockford", "Peoria"],
        "IN": ["Indianapolis", "Fort Wayne", "Evansville", "South Bend"],
        "IA": ["Des Moines", "Cedar Rapids", "Davenport", "Iowa City"],
        "KS": ["Wichita", "Kansas City", "Topeka", "Overland Park"],
        "KY": ["Louisville", "Lexington", "Bowling Green", "Covington"],
        "LA": ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette"],
        "ME": ["Portland", "Bangor", "Lewiston"],
        "MD": ["Baltimore", "Rockville", "Silver Spring", "Annapolis"],
        "MA": ["Boston", "Worcester", "Springfield", "Cambridge"],
        "MI": ["Detroit", "Grand Rapids", "Ann Arbor", "Lansing", "Flint"],
        "MN": ["Minneapolis", "St. Paul", "Rochester", "Duluth"],
        "MS": ["Jackson", "Gulfport", "Biloxi", "Hattiesburg"],
        "MO": ["Kansas City", "St. Louis", "Springfield", "Columbia"],
        "MT": ["Billings", "Missoula", "Great Falls", "Bozeman"],
        "NE": ["Omaha", "Lincoln", "Bellevue"],
        "NV": ["Las Vegas", "Henderson", "Reno"],
        "NH": ["Manchester", "Nashua", "Concord"],
        "NJ": ["Newark", "Jersey City", "Paterson", "Elizabeth", "Trenton"],
        "NM": ["Albuquerque", "Santa Fe", "Las Cruces"],
        "NY": ["New York", "Buffalo", "Rochester", "Syracuse", "Albany"],
        "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Fayetteville"],
        "ND": ["Fargo", "Bismarck", "Grand Forks"],
        "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton"],
        "OK": ["Oklahoma City", "Tulsa", "Norman", "Edmond"],
        "OR": ["Portland", "Salem", "Eugene", "Bend"],
        "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Harrisburg"],
        "RI": ["Providence", "Warwick", "Cranston"],
        "SC": ["Charleston", "Columbia", "Greenville", "Rock Hill"],
        "SD": ["Sioux Falls", "Rapid City", "Aberdeen"],
        "TN": ["Nashville", "Memphis", "Knoxville", "Chattanooga"],
        "TX": ["Houston", "Dallas", "San Antonio", "Austin", "Fort Worth", "El Paso", "Arlington", "Plano"],
        "UT": ["Salt Lake City", "Provo", "Ogden", "St. George"],
        "VT": ["Burlington", "Montpelier", "Rutland"],
        "VA": ["Virginia Beach", "Norfolk", "Richmond", "Chesapeake", "Newport News"],
        "WA": ["Seattle", "Spokane", "Tacoma", "Vancouver", "Bellevue"],
        "WV": ["Charleston", "Huntington", "Morgantown"],
        "WI": ["Milwaukee", "Madison", "Green Bay", "Kenosha"],
        "WY": ["Cheyenne", "Casper", "Laramie"],
    }

    # Tier weights by draft round (higher = more likely)
    # Format: {round: {tier: weight}}
    TIER_WEIGHTS_BY_ROUND = {
        1: {1: 50, 2: 35, 3: 12, 4: 3},   # Round 1: Heavily favor elite schools
        2: {1: 35, 2: 40, 3: 20, 4: 5},   # Round 2: Still favor top schools
        3: {1: 20, 2: 35, 3: 35, 4: 10},  # Round 3: More balanced
        4: {1: 10, 2: 25, 3: 40, 4: 25},  # Round 4: Mid-tier focus
        5: {1: 5, 2: 20, 3: 40, 4: 35},   # Round 5: More small schools
        6: {1: 3, 2: 12, 3: 35, 4: 50},   # Round 6: Small school focus
        7: {1: 2, 2: 8, 3: 30, 4: 60},    # Round 7: Heavily favor small schools
    }

    # Default weights for non-draft contexts (UDFA, etc.)
    DEFAULT_TIER_WEIGHTS = {1: 5, 2: 15, 3: 35, 4: 45}

    def __init__(self):
        """Initialize background generator with college data."""
        self._colleges: List[Dict] = []
        self._colleges_by_tier: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: []}
        self._load_colleges()

    def _load_colleges(self) -> None:
        """Load colleges from JSON file."""
        colleges_path = Path(__file__).parent.parent.parent / "data" / "colleges.json"

        try:
            with open(colleges_path, 'r') as f:
                data = json.load(f)
                self._colleges = data.get("colleges", [])

                # Organize by tier
                for college in self._colleges:
                    tier = college.get("tier", 4)
                    if tier in self._colleges_by_tier:
                        self._colleges_by_tier[tier].append(college)
        except FileNotFoundError:
            # Fallback if file not found
            self._colleges = [
                {"name": "Alabama", "state": "AL", "tier": 1},
                {"name": "Ohio State", "state": "OH", "tier": 1},
                {"name": "Georgia", "state": "GA", "tier": 1},
            ]
            self._colleges_by_tier[1] = self._colleges

    def generate_background(self, config: GenerationConfig) -> PlayerBackground:
        """Generate player background based on draft position.

        Args:
            config: Generation configuration with draft round info

        Returns:
            PlayerBackground with college, hometown, and optional combine stats
        """
        # Select college based on draft round
        college = self._select_college(config.draft_round, config.context)

        # Generate hometown (biased toward college state, but can be anywhere)
        hometown, home_state = self._generate_hometown(college["state"])

        return PlayerBackground(
            college=college["name"],
            hometown=hometown,
            home_state=home_state
        )

    def _select_college(
        self,
        draft_round: Optional[int],
        context: GenerationContext
    ) -> Dict:
        """Select college weighted by draft round and tier.

        Args:
            draft_round: Draft round (1-7) or None
            context: Generation context (NFL_DRAFT, UDFA, etc.)

        Returns:
            College dict with name, state, tier
        """
        # Get tier weights based on round
        if draft_round and draft_round in self.TIER_WEIGHTS_BY_ROUND:
            tier_weights = self.TIER_WEIGHTS_BY_ROUND[draft_round]
        else:
            tier_weights = self.DEFAULT_TIER_WEIGHTS

        # Build weighted selection pool
        weighted_pool = []
        for tier, weight in tier_weights.items():
            colleges_in_tier = self._colleges_by_tier.get(tier, [])
            for college in colleges_in_tier:
                weighted_pool.extend([college] * weight)

        if not weighted_pool:
            # Fallback
            return {"name": "Unknown College", "state": "CA", "tier": 4}

        return random.choice(weighted_pool)

    def _generate_hometown(self, college_state: str) -> tuple:
        """Generate hometown, biased toward college state.

        Args:
            college_state: State abbreviation of the player's college

        Returns:
            Tuple of (city, state)
        """
        # 60% chance hometown is in same state as college
        # 40% chance hometown is elsewhere (recruited from another state)
        if random.random() < 0.60 and college_state in self.CITIES_BY_STATE:
            state = college_state
        else:
            # Pick any state, weighted toward football hotbeds
            football_states = ["TX", "FL", "CA", "GA", "OH", "PA", "LA", "AL"]
            all_states = list(self.CITIES_BY_STATE.keys())

            if random.random() < 0.50:
                state = random.choice(football_states)
            else:
                state = random.choice(all_states)

        cities = self.CITIES_BY_STATE.get(state, ["Unknown City"])
        city = random.choice(cities)

        return city, state
