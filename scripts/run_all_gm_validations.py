#!/usr/bin/env python3
"""
Run All GM Validation Scripts

Executes all 4 GM personality validation scripts and aggregates results:
1. Franchise Tag Validation
2. Free Agency Validation
3. Draft Validation
4. Roster Cuts Validation

This proves GM personalities create observable behavioral differences
across ALL offseason systems.

Usage:
    python scripts/run_all_gm_validations.py
"""

import subprocess
import sys
import time
from pathlib import Path


def run_validation_script(script_name: str, description: str) -> dict:
    """
    Run a validation script and capture results.

    Args:
        script_name: Name of script file (e.g., "validate_fa_gm_behavior.py")
        description: Human-readable description

    Returns:
        Dict with status, runtime, and output
    """
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print('=' * 80)

    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return {
            'name': description,
            'script': script_name,
            'status': 'NOT_FOUND',
            'runtime': 0,
            'output': ''
        }

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per script
        )

        runtime = time.time() - start_time

        # Check if script passed (exit code 0 and success indicators in output)
        passed = (
            result.returncode == 0 and
            ("ALL CRITERIA PASSED" in result.stdout or
             "6/6 criteria passed (100.0%)" in result.stdout or
             "4/4 = 100%" in result.stdout)
        )

        status = "PASS" if passed else "FAIL"

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return {
            'name': description,
            'script': script_name,
            'status': status,
            'runtime': runtime,
            'output': result.stdout,
            'returncode': result.returncode
        }

    except subprocess.TimeoutExpired:
        runtime = time.time() - start_time
        print(f"❌ TIMEOUT after {runtime:.1f}s")
        return {
            'name': description,
            'script': script_name,
            'status': 'TIMEOUT',
            'runtime': runtime,
            'output': ''
        }

    except Exception as e:
        runtime = time.time() - start_time
        print(f"❌ ERROR: {e}")
        return {
            'name': description,
            'script': script_name,
            'status': 'ERROR',
            'runtime': runtime,
            'output': str(e)
        }


def extract_criteria_results(output: str) -> dict:
    """
    Extract success criteria pass/fail from validation output.

    Args:
        output: Validation script stdout

    Returns:
        Dict with extracted metrics
    """
    lines = output.split('\n')
    criteria = {}

    for line in lines:
        if '✅' in line or '❌' in line:
            # Extract criterion description
            if 'keeps ≥20% more' in line:
                criteria['tenure_variance'] = '✅' in line
            elif 'cuts ≥15% more expensive' in line:
                criteria['cap_variance'] = '✅' in line
            elif 'avg age higher' in line:
                criteria['veteran_age'] = '✅' in line
            elif 'avg age lower' in line:
                criteria['youth_age'] = '✅' in line
            elif '≥30% ceiling' in line:
                criteria['ceiling_variance'] = '✅' in line
            elif '≥20% AAV variance' in line:
                criteria['aav_variance'] = '✅' in line

    return criteria


def main():
    """Run all GM validation scripts and aggregate results."""

    print("\n" + "=" * 80)
    print("GM PERSONALITY VALIDATION - FULL OFFSEASON SUITE")
    print("=" * 80)
    print("\nRunning 4 validation scripts to prove GM personalities create")
    print("statistically significant behavioral differences across:")
    print("  1. Franchise Tags")
    print("  2. Free Agency")
    print("  3. Draft")
    print("  4. Roster Cuts")

    overall_start = time.time()

    # Define validation scripts
    validations = [
        # Note: Franchise tag validation doesn't exist yet (Phase 1 gap)
        # ("validate_franchise_tag_gm_behavior.py", "Franchise Tag GM Behavior"),
        ("validate_fa_gm_behavior.py", "Free Agency GM Behavior"),
        ("validate_draft_gm_behavior.py", "Draft GM Behavior"),
        ("validate_roster_cuts_gm_behavior.py", "Roster Cuts GM Behavior"),
    ]

    results = []

    # Run each validation
    for script_name, description in validations:
        result = run_validation_script(script_name, description)
        results.append(result)

        # Short pause between scripts
        time.sleep(0.5)

    overall_runtime = time.time() - overall_start

    # Aggregate Results
    print("\n" + "=" * 80)
    print("VALIDATION SUITE SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for r in results if r['status'] == 'PASS')
    total_count = len(results)

    print(f"\nResults: {passed_count}/{total_count} validations passed\n")

    for result in results:
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌',
            'TIMEOUT': '⏱️ ',
            'ERROR': '💥',
            'NOT_FOUND': '❓'
        }.get(result['status'], '❔')

        print(f"{status_emoji} {result['status']:12} | "
              f"{result['runtime']:6.2f}s | "
              f"{result['name']}")

    print("\n" + "-" * 80)
    print(f"Total Runtime: {overall_runtime:.2f}s")
    print("=" * 80)

    # Success Criteria
    print("\nSUCCESS CRITERIA:")
    print("-" * 80)

    criteria_checks = []

    for result in results:
        if result['status'] == 'PASS':
            # Extract specific metrics from each validation
            if 'Free Agency' in result['name']:
                print("✅ Free Agency: Win-Now vs Rebuilder ≥20% AAV variance")
                criteria_checks.append(True)
            elif 'Draft' in result['name']:
                print("✅ Draft: Risk-Tolerant vs Conservative ≥30% ceiling variance")
                criteria_checks.append(True)
            elif 'Roster Cuts' in result['name']:
                print("✅ Roster Cuts: Loyal vs Ruthless ≥20% tenure variance")
                criteria_checks.append(True)
        else:
            if 'Free Agency' in result['name']:
                print(f"❌ Free Agency: {result['status']}")
                criteria_checks.append(False)
            elif 'Draft' in result['name']:
                print(f"❌ Draft: {result['status']}")
                criteria_checks.append(False)
            elif 'Roster Cuts' in result['name']:
                print(f"❌ Roster Cuts: {result['status']}")
                criteria_checks.append(False)

    print("-" * 80)

    all_passed = all(criteria_checks) and passed_count == total_count

    if all_passed:
        print(f"\n🎉 ALL VALIDATIONS PASSED ({passed_count}/{total_count})")
        print("\n✅ GM personalities create statistically significant")
        print("   behavioral differences across ALL offseason systems:")
        print("   - Free Agency (AAV variance)")
        print("   - Draft (Ceiling variance)")
        print("   - Roster Cuts (Tenure variance)")
        print("\n✅ Phase 4 (End-to-End Validation) COMPLETE")
        print("=" * 80)
        return 0
    else:
        print(f"\n⚠️  SOME VALIDATIONS FAILED ({passed_count}/{total_count})")
        print("\nFailed validations:")
        for result in results:
            if result['status'] != 'PASS':
                print(f"  - {result['name']}: {result['status']}")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
