"""Generates realistic player names."""

import random
from typing import List


class NameGenerator:
    """Generates realistic player names."""

    # Position-appropriate name pools
    FIRST_NAMES = [
        "Michael", "Chris", "David", "James", "Robert", "John", "Daniel", "Matthew",
        "Brandon", "Justin", "Tyler", "Ryan", "Josh", "Andrew", "Kevin", "Brian",
        "Marcus", "Darius", "DeAndre", "Jamal", "Lamar", "Antonio", "Terrell",
        "Cameron", "Jordan", "Taylor", "Mason", "Logan", "Ethan", "Noah",
        "Jalen", "Kyler", "Caleb", "Drake", "Garrett", "Hunter", "Isaiah", "Jaylen",
        "Keenan", "Malik", "Nathaniel", "Patrick", "Quentin", "Rashad", "Stefon",
        "Trevon", "Xavier", "Zach", "Aaron", "Ben", "Carson", "Devin", "Eric",
        "Frank", "George", "Henry", "Ian", "Jacob", "Kyle"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
        "Harris", "Clark", "Lewis", "Robinson", "Walker", "Allen", "Young", "King",
        "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Carter", "Mitchell",
        "Perez", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans",
        "Edwards", "Collins", "Stewart", "Sanchez", "Morris", "Rogers", "Reed",
        "Cook", "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper", "Richardson"
    ]

    @staticmethod
    def generate_name() -> str:
        """Generate random player name.

        Returns:
            Full player name in "First Last" format
        """
        first = random.choice(NameGenerator.FIRST_NAMES)
        last = random.choice(NameGenerator.LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def generate_unique_names(count: int) -> List[str]:
        """Generate list of unique names.

        Args:
            count: Number of unique names to generate

        Returns:
            List of unique player names
        """
        names = set()
        attempts = 0
        max_attempts = count * 10

        while len(names) < count and attempts < max_attempts:
            names.add(NameGenerator.generate_name())
            attempts += 1

        return list(names)