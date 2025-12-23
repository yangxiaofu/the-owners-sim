"""
Benchmark Harness for Contract Valuation Engine.

Runs benchmark cases against the valuation engine and compares results
to expected AAV ranges to validate realism.

Usage:
    from contract_valuation.engine import ContractValuationEngine
    from contract_valuation.testing import BenchmarkHarness, BENCHMARK_CASES

    harness = BenchmarkHarness()
    report = harness.run_all_cases(BENCHMARK_CASES)
    print(f"Pass rate: {report.pass_rate:.0%}")
    print(f"Average deviation: {report.average_deviation:.1%}")
"""

from typing import List, Optional, TYPE_CHECKING

from contract_valuation.testing.benchmark_cases import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkReport,
    CATEGORY_GM_VARIANCE,
    CATEGORY_PRESSURE,
)
from contract_valuation.context import (
    ValuationContext,
    OwnerContext,
    JobSecurityContext,
)
from contract_valuation.gm_influence.styles import GMStyle

if TYPE_CHECKING:
    from contract_valuation.engine import ContractValuationEngine
    from team_management.gm_archetype import GMArchetype


class BenchmarkHarness:
    """
    Runs benchmark cases and compares results to expectations.

    The harness creates default contexts for valuation but allows
    overrides for testing specific scenarios (GM style, pressure level).

    Attributes:
        engine: ContractValuationEngine instance to test
        default_context: Default ValuationContext for cases
        default_owner_context: Default OwnerContext for cases
    """

    # Default 2025 salary cap
    DEFAULT_SALARY_CAP = 255_000_000
    DEFAULT_SEASON = 2025

    def __init__(
        self,
        engine: Optional["ContractValuationEngine"] = None,
        valuation_context: Optional[ValuationContext] = None,
    ):
        """
        Initialize the benchmark harness.

        Args:
            engine: ContractValuationEngine to test. If None, creates new instance.
            valuation_context: Default context. If None, uses 2025 defaults.
        """
        if engine is None:
            from contract_valuation.engine import ContractValuationEngine
            engine = ContractValuationEngine()

        self._engine = engine
        self._default_context = valuation_context or self._create_default_context()

    def run_all_cases(
        self,
        cases: List[BenchmarkCase],
    ) -> BenchmarkReport:
        """
        Run all benchmark cases and generate report.

        Args:
            cases: List of BenchmarkCase objects to run

        Returns:
            BenchmarkReport with all results
        """
        results: List[BenchmarkResult] = []

        for case in cases:
            try:
                result = self._run_case(case)
                results.append(result)
            except Exception as e:
                # Create failed result for error cases
                results.append(self._create_error_result(case, str(e)))

        return BenchmarkReport(results=results)

    def run_category(
        self,
        cases: List[BenchmarkCase],
        category: str,
    ) -> BenchmarkReport:
        """
        Run benchmark cases for a specific category only.

        Args:
            cases: Full list of BenchmarkCase objects
            category: Category to filter by

        Returns:
            BenchmarkReport for that category only
        """
        filtered = [c for c in cases if c.category == category]
        return self.run_all_cases(filtered)

    def _run_case(self, case: BenchmarkCase) -> BenchmarkResult:
        """
        Run a single benchmark case.

        Args:
            case: BenchmarkCase to run

        Returns:
            BenchmarkResult with actual AAV and comparison
        """
        # Build context based on case type
        owner_context = self._build_owner_context_for_case(case)
        gm_archetype = self._build_gm_archetype_for_case(case)

        # Run valuation
        valuation_result = self._engine.valuate(
            player_data=case.player_data,
            valuation_context=self._default_context,
            owner_context=owner_context,
            gm_archetype=gm_archetype,
        )

        actual_aav = valuation_result.offer.aav

        # Calculate if in range
        in_range = case.expected_aav_min <= actual_aav <= case.expected_aav_max

        # Calculate deviation from midpoint
        deviation_pct = self._calculate_deviation(actual_aav, case)

        return BenchmarkResult(
            case=case,
            actual_aav=actual_aav,
            in_range=in_range,
            deviation_pct=deviation_pct,
            valuation_result=valuation_result,
        )

    def _create_error_result(self, case: BenchmarkCase, error: str) -> BenchmarkResult:
        """Create a failed result for cases that threw errors."""
        return BenchmarkResult(
            case=case,
            actual_aav=0,
            in_range=False,
            deviation_pct=1.0,  # 100% deviation
            valuation_result=None,
        )

    def _calculate_deviation(self, actual_aav: int, case: BenchmarkCase) -> float:
        """
        Calculate percentage deviation from expected midpoint.

        Args:
            actual_aav: Actual AAV from engine
            case: BenchmarkCase with expected range

        Returns:
            Deviation as percentage (e.g., 0.15 for 15%)
        """
        midpoint = case.expected_midpoint
        if midpoint == 0:
            return 1.0  # 100% deviation if expected is 0

        deviation = abs(actual_aav - midpoint) / midpoint
        return deviation

    def _create_default_context(self) -> ValuationContext:
        """Create default 2025 valuation context."""
        return ValuationContext.create_default_2025()

    def _build_owner_context_for_case(self, case: BenchmarkCase) -> OwnerContext:
        """
        Build appropriate OwnerContext based on case properties.

        Pressure cases get specific pressure levels, others get balanced.
        """
        if case.category == CATEGORY_PRESSURE and case.pressure_level:
            return self._create_pressure_context(case.pressure_level)

        # Default balanced context
        return OwnerContext.create_default(
            dynasty_id="benchmark_test",
            team_id=1,
        )

    def _create_pressure_context(self, pressure_level: str) -> OwnerContext:
        """
        Create OwnerContext for specific pressure scenarios.

        Args:
            pressure_level: One of "secure", "hot_seat", "new_hire"

        Returns:
            OwnerContext with appropriate job security
        """
        if pressure_level == "secure":
            job_security = JobSecurityContext.create_secure()
        elif pressure_level == "hot_seat":
            job_security = JobSecurityContext.create_hot_seat()
        elif pressure_level == "new_hire":
            job_security = JobSecurityContext.create_new_hire()
        else:
            job_security = JobSecurityContext.create_secure()

        return OwnerContext(
            dynasty_id="benchmark_test",
            team_id=1,
            job_security=job_security,
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=(pressure_level == "hot_seat"),
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

    def _build_gm_archetype_for_case(
        self,
        case: BenchmarkCase,
    ) -> Optional["GMArchetype"]:
        """
        Build GMArchetype based on case properties.

        GM variance cases get specific archetypes, others get default.
        """
        if case.category == CATEGORY_GM_VARIANCE and case.gm_style:
            return self._create_gm_for_style(case.gm_style)

        # Return None to use engine's default (BALANCED)
        return None

    def _create_gm_for_style(self, style_name: str) -> "GMArchetype":
        """
        Create a GMArchetype with specific valuation preferences.

        Args:
            style_name: One of "analytics_heavy", "scout_focused", "market_driven"

        Returns:
            GMArchetype configured for that style
        """
        from team_management.gm_archetype import GMArchetype

        # Base archetype with style-specific preferences
        if style_name == "analytics_heavy":
            return GMArchetype(
                archetype_key="analytics_heavy",
                analytics_preference=0.90,  # Heavy stats weight
                scouting_preference=0.30,
                market_awareness=0.50,
                risk_tolerance=0.50,
                star_chasing=0.40,
                youth_focus=0.60,
                position_value_bias=0.50,
                loyalty_tendency=0.40,
                patience_level=0.60,
                cap_management_style=0.50,
                draft_priority=0.60,
            )
        elif style_name == "scout_focused":
            return GMArchetype(
                archetype_key="scout_focused",
                analytics_preference=0.30,
                scouting_preference=0.90,  # Heavy scouting weight
                market_awareness=0.50,
                risk_tolerance=0.60,
                star_chasing=0.50,
                youth_focus=0.70,
                position_value_bias=0.50,
                loyalty_tendency=0.50,
                patience_level=0.50,
                cap_management_style=0.50,
                draft_priority=0.70,
            )
        elif style_name == "market_driven":
            return GMArchetype(
                archetype_key="market_driven",
                analytics_preference=0.40,
                scouting_preference=0.40,
                market_awareness=0.90,  # Heavy market weight
                risk_tolerance=0.40,
                star_chasing=0.50,
                youth_focus=0.50,
                position_value_bias=0.50,
                loyalty_tendency=0.50,
                patience_level=0.50,
                cap_management_style=0.60,
                draft_priority=0.50,
            )
        else:
            # Default balanced
            return GMArchetype(
                archetype_key="balanced",
                analytics_preference=0.50,
                scouting_preference=0.50,
                market_awareness=0.50,
                risk_tolerance=0.50,
                star_chasing=0.50,
                youth_focus=0.50,
                position_value_bias=0.50,
                loyalty_tendency=0.50,
                patience_level=0.50,
                cap_management_style=0.50,
                draft_priority=0.50,
            )


def run_quick_benchmark() -> BenchmarkReport:
    """
    Quick benchmark runner for command-line testing.

    Returns:
        BenchmarkReport with all results
    """
    from contract_valuation.testing.benchmark_cases import BENCHMARK_CASES

    harness = BenchmarkHarness()
    return harness.run_all_cases(BENCHMARK_CASES)


if __name__ == "__main__":
    # Quick test run
    report = run_quick_benchmark()
    print(f"Total cases: {report.total_cases}")
    print(f"Passed: {report.passed_cases}")
    print(f"Failed: {report.failed_cases}")
    print(f"Pass rate: {report.pass_rate:.0%}")
    print(f"Average deviation: {report.average_deviation:.1%}")
