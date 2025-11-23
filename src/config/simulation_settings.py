"""
Centralized Simulation Speed Settings

Simple True/False toggles to skip expensive operations.
Change these settings to speed up simulations for testing.
"""
from operator import truediv


class SimulationSettings:
    """
    Simulation speed controls.

    True  = SKIP (faster, for testing)
    False = RUN NORMALLY (realistic, for gameplay)
    """

    # ================================================================
    # CHANGE THESE TO SPEED UP SIMULATIONS
    # ================================================================

    SKIP_GAME_SIMULATION = True
    # True:  Use fake game scores (instant, ~0.001s per game)
    # False: Run full play-by-play simulation (realistic, ~2-5s per game)

    SKIP_TRANSACTION_AI = True
    # True:  Skip AI trade evaluation (no CPU-intensive trade analysis)
    # False: Run full transaction AI (evaluates trades for all 32 teams)

    SKIP_OFFSEASON_EVENTS = True
    # True:  Skip offseason event processing (faster offseason)
    # False: Run all offseason events (franchise tags, free agency, etc.)