"""
Benchmark test case definitions for Contract Valuation Engine.

Defines 30+ test cases across 6 categories to validate that the
valuation engine produces realistic contract offers matching NFL market rates.

Categories:
1. Elite Players (90+ rating) - Top-tier AAVs
2. Average Starters (75-79 rating) - Mid-tier AAVs
3. Backups (60-69 rating) - Backup-level AAVs
4. Age Extremes - Young prospects and aging veterans
5. GM Style Variance - Same player, different GM styles
6. Pressure Scenarios - Hot seat vs secure GM effects
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


# Category constants
CATEGORY_ELITE = "elite"
CATEGORY_STARTER = "starter"
CATEGORY_BACKUP = "backup"
CATEGORY_AGE_EXTREME = "age_extreme"
CATEGORY_GM_VARIANCE = "gm_variance"
CATEGORY_PRESSURE = "pressure"


@dataclass
class BenchmarkCase:
    """
    A single benchmark test case.

    Attributes:
        name: Human-readable name for the test case
        player_data: Player information dictionary for valuation
        expected_aav_min: Minimum acceptable AAV in dollars
        expected_aav_max: Maximum acceptable AAV in dollars
        category: Test category (elite, starter, backup, etc.)
        notes: Explanation of expected outcome
        gm_style: Optional GM style to use (for variance tests)
        pressure_level: Optional pressure level name (for pressure tests)
    """

    name: str
    player_data: Dict[str, Any]
    expected_aav_min: int
    expected_aav_max: int
    category: str
    notes: str
    gm_style: Optional[str] = None
    pressure_level: Optional[str] = None

    @property
    def expected_midpoint(self) -> int:
        """Calculate expected AAV midpoint."""
        return (self.expected_aav_min + self.expected_aav_max) // 2


@dataclass
class BenchmarkResult:
    """
    Result of running a single benchmark case.

    Attributes:
        case: The benchmark case that was run
        actual_aav: The AAV produced by the engine
        in_range: Whether actual_aav is within expected range
        deviation_pct: Percentage deviation from expected midpoint
        valuation_result: Full ValuationResult for debugging
    """

    case: BenchmarkCase
    actual_aav: int
    in_range: bool
    deviation_pct: float
    valuation_result: Optional[Any] = None

    @property
    def passed(self) -> bool:
        """Whether this case passed (AAV in expected range)."""
        return self.in_range


@dataclass
class BenchmarkReport:
    """
    Aggregate report of all benchmark results.

    Attributes:
        results: List of individual BenchmarkResult objects
        total_cases: Total number of cases run
        passed_cases: Number of cases that passed
        failed_cases: Number of cases that failed
        average_deviation: Average deviation percentage across all cases
    """

    results: List[BenchmarkResult] = field(default_factory=list)

    @property
    def total_cases(self) -> int:
        """Total number of cases in this report."""
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        """Number of cases that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_cases(self) -> int:
        """Number of cases that failed."""
        return self.total_cases - self.passed_cases

    @property
    def pass_rate(self) -> float:
        """Pass rate as a percentage (0.0-1.0)."""
        if self.total_cases == 0:
            return 0.0
        return self.passed_cases / self.total_cases

    @property
    def average_deviation(self) -> float:
        """Average deviation percentage across all cases."""
        if not self.results:
            return 0.0
        return sum(abs(r.deviation_pct) for r in self.results) / len(self.results)

    def get_results_by_category(self, category: str) -> List[BenchmarkResult]:
        """Get results filtered by category."""
        return [r for r in self.results if r.case.category == category]

    def get_category_pass_rate(self, category: str) -> float:
        """Get pass rate for a specific category."""
        cat_results = self.get_results_by_category(category)
        if not cat_results:
            return 0.0
        passed = sum(1 for r in cat_results if r.passed)
        return passed / len(cat_results)

    def get_failed_results(self) -> List[BenchmarkResult]:
        """Get all failed results."""
        return [r for r in self.results if not r.passed]


def _create_player_data(
    player_id: int,
    name: str,
    position: str,
    overall_rating: int,
    age: int,
    stats: Optional[Dict[str, Any]] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper to create player data dictionaries."""
    data = {
        "player_id": player_id,
        "name": name,
        "position": position,
        "overall_rating": overall_rating,
        "age": age,
    }
    if stats:
        data["stats"] = stats
    if attributes:
        data["attributes"] = attributes
    return data


# =============================================================================
# CATEGORY 1: ELITE PLAYERS (90+ rating)
# =============================================================================

ELITE_CASES = [
    BenchmarkCase(
        name="Elite QB (Patrick Mahomes tier)",
        player_data=_create_player_data(
            player_id=1,
            name="John Elite",
            position="QB",
            overall_rating=99,
            age=28,
            stats={
                "pass_yards": 4800,
                "pass_tds": 40,
                "passer_rating": 110.0,
                "games_played": 17,
            },
        ),
        expected_aav_min=50_000_000,
        expected_aav_max=60_000_000,
        category=CATEGORY_ELITE,
        notes="Top 3 QB should get $50-60M AAV (Mahomes/Burrow tier, 2024 calibration)",
    ),
    BenchmarkCase(
        name="Elite EDGE Rusher (Myles Garrett tier)",
        player_data=_create_player_data(
            player_id=2,
            name="Mike Rusher",
            position="EDGE",
            overall_rating=96,
            age=27,
            stats={
                "sacks": 14.0,
                "tackles": 52,
                "forced_fumbles": 3,
                "games_played": 17,
            },
        ),
        expected_aav_min=24_000_000,
        expected_aav_max=32_000_000,
        category=CATEGORY_ELITE,
        notes="Elite pass rusher should get $24-32M AAV",
    ),
    BenchmarkCase(
        name="Elite WR (Ja'Marr Chase tier)",
        player_data=_create_player_data(
            player_id=3,
            name="DeVon Star",
            position="WR",
            overall_rating=95,
            age=24,
            stats={
                "rec_yards": 1500,
                "receptions": 105,
                "rec_tds": 13,
                "games_played": 17,
            },
        ),
        expected_aav_min=24_000_000,
        expected_aav_max=32_000_000,
        category=CATEGORY_ELITE,
        notes="Elite WR should get $24-32M AAV (young superstar)",
    ),
    BenchmarkCase(
        name="Elite CB (Jalen Ramsey tier)",
        player_data=_create_player_data(
            player_id=4,
            name="Marcus Lockdown",
            position="CB",
            overall_rating=94,
            age=28,
            stats={
                "interceptions": 5,
                "passes_defended": 18,
                "tackles": 65,
                "games_played": 16,
            },
        ),
        expected_aav_min=18_000_000,
        expected_aav_max=25_000_000,
        category=CATEGORY_ELITE,
        notes="Elite CB should get $18-25M AAV",
    ),
    BenchmarkCase(
        name="Elite LT (Trent Williams tier)",
        player_data=_create_player_data(
            player_id=5,
            name="Anthony Anchor",
            position="LT",
            overall_rating=95,
            age=29,
            stats={
                "sacks_allowed": 1,
                "pressures_allowed": 12,
                "games_played": 17,
            },
        ),
        expected_aav_min=22_000_000,
        expected_aav_max=30_000_000,
        category=CATEGORY_ELITE,
        notes="Elite LT should get $22-30M AAV",
    ),
]


# =============================================================================
# CATEGORY 2: AVERAGE STARTERS (75-79 rating)
# =============================================================================

STARTER_CASES = [
    BenchmarkCase(
        name="Average Starting QB",
        player_data=_create_player_data(
            player_id=10,
            name="Tom Adequate",
            position="QB",
            overall_rating=78,
            age=29,
            stats={
                "pass_yards": 3500,
                "pass_tds": 22,
                "passer_rating": 90.0,
                "games_played": 17,
            },
        ),
        expected_aav_min=18_000_000,
        expected_aav_max=28_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter QB should get $18-28M AAV (2024 QB market)",
    ),
    BenchmarkCase(
        name="Average Starting RB",
        player_data=_create_player_data(
            player_id=11,
            name="Jason Runner",
            position="RB",
            overall_rating=77,
            age=26,
            stats={
                "rush_yards": 900,
                "rush_tds": 7,
                "receptions": 35,
                "games_played": 17,
            },
        ),
        expected_aav_min=3_500_000,
        expected_aav_max=7_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter RB should get $3.5-7M AAV (RB devaluation)",
    ),
    BenchmarkCase(
        name="Average Starting WR",
        player_data=_create_player_data(
            player_id=12,
            name="Kevin Hands",
            position="WR",
            overall_rating=79,
            age=27,
            stats={
                "rec_yards": 850,
                "receptions": 65,
                "rec_tds": 5,
                "games_played": 16,
            },
        ),
        expected_aav_min=7_000_000,
        expected_aav_max=12_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter WR should get $7-12M AAV",
    ),
    BenchmarkCase(
        name="Average Starting TE",
        player_data=_create_player_data(
            player_id=13,
            name="Brian Block",
            position="TE",
            overall_rating=76,
            age=28,
            stats={
                "rec_yards": 550,
                "receptions": 50,
                "rec_tds": 4,
                "games_played": 17,
            },
        ),
        expected_aav_min=5_000_000,
        expected_aav_max=9_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter TE should get $5-9M AAV",
    ),
    BenchmarkCase(
        name="Average Starting DT",
        player_data=_create_player_data(
            player_id=14,
            name="Derek Interior",
            position="DT",
            overall_rating=78,
            age=27,
            stats={
                "sacks": 3.5,
                "tackles": 45,
                "games_played": 17,
            },
        ),
        expected_aav_min=7_000_000,
        expected_aav_max=12_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter DT should get $7-12M AAV",
    ),
    BenchmarkCase(
        name="Average Starting Safety",
        player_data=_create_player_data(
            player_id=15,
            name="Marcus Safety",
            position="S",
            overall_rating=77,
            age=27,
            stats={
                "interceptions": 2,
                "tackles": 80,
                "passes_defended": 8,
                "games_played": 17,
            },
        ),
        expected_aav_min=5_000_000,
        expected_aav_max=9_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter S should get $5-9M AAV",
    ),
    BenchmarkCase(
        name="Average Starting Guard",
        player_data=_create_player_data(
            player_id=16,
            name="Paul Puller",
            position="OG",
            overall_rating=76,
            age=28,
            stats={
                "sacks_allowed": 2,
                "games_played": 17,
            },
        ),
        expected_aav_min=5_000_000,
        expected_aav_max=10_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter OG should get $5-10M AAV",
    ),
    BenchmarkCase(
        name="Average Starting LB",
        player_data=_create_player_data(
            player_id=17,
            name="Larry Linebacker",
            position="LB",
            overall_rating=78,
            age=27,
            stats={
                "tackles": 95,
                "sacks": 2.0,
                "interceptions": 1,
                "games_played": 17,
            },
        ),
        expected_aav_min=7_000_000,
        expected_aav_max=12_000_000,
        category=CATEGORY_STARTER,
        notes="Average starter LB should get $7-12M AAV",
    ),
]


# =============================================================================
# CATEGORY 3: BACKUPS (60-69 rating)
# =============================================================================

BACKUP_CASES = [
    BenchmarkCase(
        name="Backup QB",
        player_data=_create_player_data(
            player_id=20,
            name="Steve Clipboard",
            position="QB",
            overall_rating=65,
            age=30,
            stats={
                "pass_yards": 200,
                "pass_tds": 1,
                "games_played": 3,
            },
        ),
        expected_aav_min=2_000_000,
        expected_aav_max=5_000_000,
        category=CATEGORY_BACKUP,
        notes="Backup QB should get $2-5M AAV",
    ),
    BenchmarkCase(
        name="Backup RB",
        player_data=_create_player_data(
            player_id=21,
            name="Chad Change",
            position="RB",
            overall_rating=68,
            age=27,
            stats={
                "rush_yards": 350,
                "rush_tds": 2,
                "games_played": 14,
            },
        ),
        expected_aav_min=1_000_000,
        expected_aav_max=2_500_000,
        category=CATEGORY_BACKUP,
        notes="Backup RB should get $1-2.5M AAV",
    ),
    BenchmarkCase(
        name="Backup WR (WR4/5)",
        player_data=_create_player_data(
            player_id=22,
            name="Danny Depth",
            position="WR",
            overall_rating=67,
            age=26,
            stats={
                "rec_yards": 250,
                "receptions": 20,
                "rec_tds": 1,
                "games_played": 17,
            },
        ),
        expected_aav_min=1_500_000,
        expected_aav_max=3_500_000,
        category=CATEGORY_BACKUP,
        notes="Depth WR should get $1.5-3.5M AAV",
    ),
    BenchmarkCase(
        name="Backup CB",
        player_data=_create_player_data(
            player_id=23,
            name="Nick Nickel",
            position="CB",
            overall_rating=66,
            age=25,
            stats={
                "tackles": 35,
                "passes_defended": 4,
                "games_played": 16,
            },
        ),
        expected_aav_min=1_500_000,
        expected_aav_max=3_500_000,
        category=CATEGORY_BACKUP,
        notes="Backup CB should get $1.5-3.5M AAV",
    ),
    BenchmarkCase(
        name="Backup EDGE",
        player_data=_create_player_data(
            player_id=24,
            name="Robert Rotation",
            position="EDGE",
            overall_rating=68,
            age=28,
            stats={
                "sacks": 3.0,
                "tackles": 28,
                "games_played": 17,
            },
        ),
        expected_aav_min=2_500_000,
        expected_aav_max=5_000_000,
        category=CATEGORY_BACKUP,
        notes="Rotational EDGE should get $2.5-5M AAV",
    ),
    BenchmarkCase(
        name="Backup Kicker",
        player_data=_create_player_data(
            player_id=25,
            name="Kyle Kickoff",
            position="K",
            overall_rating=65,
            age=29,
            stats={
                "fg_made": 10,
                "fg_attempted": 12,
                "games_played": 8,
            },
        ),
        expected_aav_min=800_000,
        expected_aav_max=2_000_000,
        category=CATEGORY_BACKUP,
        notes="Backup K should get $800K-2M AAV",
    ),
]


# =============================================================================
# CATEGORY 4: AGE EXTREMES
# =============================================================================

AGE_EXTREME_CASES = [
    BenchmarkCase(
        name="Young Breakout WR (22 years old)",
        player_data=_create_player_data(
            player_id=30,
            name="Jayden Promising",
            position="WR",
            overall_rating=88,
            age=22,
            stats={
                "rec_yards": 1200,
                "receptions": 85,
                "rec_tds": 10,
                "games_played": 17,
            },
            attributes={
                "potential": 98,
                "technique": 82,
                "football_iq": 78,
            },
        ),
        expected_aav_min=18_000_000,
        expected_aav_max=28_000_000,
        category=CATEGORY_AGE_EXTREME,
        notes="Young breakout star with high potential should get premium (5-year deal)",
    ),
    BenchmarkCase(
        name="Aging Elite QB (36 years old)",
        player_data=_create_player_data(
            player_id=31,
            name="Tom Legend",
            position="QB",
            overall_rating=92,
            age=36,
            stats={
                "pass_yards": 4000,
                "pass_tds": 28,
                "passer_rating": 100.0,
                "games_played": 17,
            },
        ),
        expected_aav_min=25_000_000,
        expected_aav_max=40_000_000,
        category=CATEGORY_AGE_EXTREME,
        notes="Elite but aging QB should get high AAV but shorter term (2-3 years)",
    ),
    BenchmarkCase(
        name="Aging RB (30 years old)",
        player_data=_create_player_data(
            player_id=32,
            name="Adrian Veteran",
            position="RB",
            overall_rating=85,
            age=30,
            stats={
                "rush_yards": 1100,
                "rush_tds": 9,
                "games_played": 17,
            },
        ),
        expected_aav_min=5_000_000,
        expected_aav_max=10_000_000,
        category=CATEGORY_AGE_EXTREME,
        notes="30-year-old RB with production should get short-term deal (1-2 years)",
    ),
    BenchmarkCase(
        name="Young Rookie CB Extension (23 years old)",
        player_data=_create_player_data(
            player_id=33,
            name="Sauce Cornerback",
            position="CB",
            overall_rating=90,
            age=23,
            stats={
                "interceptions": 6,
                "passes_defended": 20,
                "tackles": 55,
                "games_played": 17,
            },
            attributes={
                "potential": 95,
            },
        ),
        expected_aav_min=16_000_000,
        expected_aav_max=24_000_000,
        category=CATEGORY_AGE_EXTREME,
        notes="Young elite CB on extension should get long-term premium (5 years)",
    ),
    BenchmarkCase(
        name="Veteran EDGE (34 years old)",
        player_data=_create_player_data(
            player_id=34,
            name="Dwight Decline",
            position="EDGE",
            overall_rating=82,
            age=34,
            stats={
                "sacks": 8.0,
                "tackles": 40,
                "games_played": 16,
            },
        ),
        expected_aav_min=8_000_000,
        expected_aav_max=15_000_000,
        category=CATEGORY_AGE_EXTREME,
        notes="34-year-old quality EDGE should get value deal (1-2 years)",
    ),
]


# =============================================================================
# CATEGORY 5: GM STYLE VARIANCE
# These use the same player but expect different outcomes per GM style
# =============================================================================

# Base player for variance testing
_VARIANCE_TEST_PLAYER = _create_player_data(
    player_id=40,
    name="Test Variance",
    position="WR",
    overall_rating=86,
    age=26,
    stats={
        "rec_yards": 1100,
        "receptions": 80,
        "rec_tds": 8,
        "games_played": 17,
    },
    attributes={
        "technique": 85,
        "football_iq": 80,
        "athleticism": 88,
        "potential": 82,
    },
)

GM_VARIANCE_CASES = [
    BenchmarkCase(
        name="Quality WR - Analytics GM",
        player_data=_VARIANCE_TEST_PLAYER.copy(),
        expected_aav_min=14_000_000,
        expected_aav_max=20_000_000,
        category=CATEGORY_GM_VARIANCE,
        notes="Analytics GM weighs stats heavily - should value based on production",
        gm_style="analytics_heavy",
    ),
    BenchmarkCase(
        name="Quality WR - Scout GM",
        player_data=_VARIANCE_TEST_PLAYER.copy(),
        expected_aav_min=15_000_000,
        expected_aav_max=22_000_000,
        category=CATEGORY_GM_VARIANCE,
        notes="Scout GM may see upside in attributes - could pay slightly more",
        gm_style="scout_focused",
    ),
    BenchmarkCase(
        name="Quality WR - Market GM",
        player_data=_VARIANCE_TEST_PLAYER.copy(),
        expected_aav_min=14_000_000,
        expected_aav_max=20_000_000,
        category=CATEGORY_GM_VARIANCE,
        notes="Market GM follows market rates closely - should be near average",
        gm_style="market_driven",
    ),
]


# =============================================================================
# CATEGORY 6: PRESSURE SCENARIOS
# =============================================================================

_PRESSURE_TEST_PLAYER = _create_player_data(
    player_id=50,
    name="Test Pressure",
    position="EDGE",
    overall_rating=84,
    age=27,
    stats={
        "sacks": 10.0,
        "tackles": 48,
        "games_played": 17,
    },
)

PRESSURE_CASES = [
    BenchmarkCase(
        name="Quality EDGE - Secure GM",
        player_data=_PRESSURE_TEST_PLAYER.copy(),
        expected_aav_min=14_000_000,
        expected_aav_max=20_000_000,
        category=CATEGORY_PRESSURE,
        notes="Secure GM gets value deal - no overpay pressure",
        pressure_level="secure",
    ),
    BenchmarkCase(
        name="Quality EDGE - Hot Seat GM",
        player_data=_PRESSURE_TEST_PLAYER.copy(),
        expected_aav_min=17_000_000,
        expected_aav_max=25_000_000,
        category=CATEGORY_PRESSURE,
        notes="Hot seat GM overpays by 10-15% to win now",
        pressure_level="hot_seat",
    ),
    BenchmarkCase(
        name="Quality EDGE - New Hire GM",
        player_data=_PRESSURE_TEST_PLAYER.copy(),
        expected_aav_min=15_000_000,
        expected_aav_max=22_000_000,
        category=CATEGORY_PRESSURE,
        notes="New hire has moderate pressure - slight overpay",
        pressure_level="new_hire",
    ),
]


# =============================================================================
# COMBINED BENCHMARK CASES
# =============================================================================

BENCHMARK_CASES: List[BenchmarkCase] = (
    ELITE_CASES
    + STARTER_CASES
    + BACKUP_CASES
    + AGE_EXTREME_CASES
    + GM_VARIANCE_CASES
    + PRESSURE_CASES
)


def get_cases_by_category(category: str) -> List[BenchmarkCase]:
    """
    Get benchmark cases filtered by category.

    Args:
        category: Category constant (CATEGORY_ELITE, etc.)

    Returns:
        List of BenchmarkCase objects for that category
    """
    return [c for c in BENCHMARK_CASES if c.category == category]


def get_all_categories() -> List[str]:
    """Get list of all categories."""
    return [
        CATEGORY_ELITE,
        CATEGORY_STARTER,
        CATEGORY_BACKUP,
        CATEGORY_AGE_EXTREME,
        CATEGORY_GM_VARIANCE,
        CATEGORY_PRESSURE,
    ]
