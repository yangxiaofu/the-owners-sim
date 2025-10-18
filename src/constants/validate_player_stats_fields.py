#!/usr/bin/env python3
"""
Validation Script for PlayerStatField Phase 1

Tests the new database persistence metadata system to ensure:
1. All enum fields have proper metadata
2. Generate INSERT statement works correctly
3. Extract params works with PlayerStats objects
4. Schema validation detects mismatches
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants.player_stats_fields import PlayerStatField, StatFieldMetadata


def test_metadata_structure():
    """Test that all enum fields have proper StatFieldMetadata"""
    print("=" * 80)
    print("TEST 1: Metadata Structure Validation")
    print("=" * 80)

    errors = []
    for field in PlayerStatField:
        # Check that value is StatFieldMetadata
        if not isinstance(field.value, StatFieldMetadata):
            errors.append(f"{field.name}: value is not StatFieldMetadata (got {type(field.value)})")
            continue

        # Check that field_name exists
        if not field.value.field_name:
            errors.append(f"{field.name}: missing field_name")

        # Check that db_column exists
        if not field.value.db_column:
            errors.append(f"{field.name}: missing db_column")

        # Check that data_type is valid
        if field.value.data_type not in [int, float, str]:
            errors.append(f"{field.name}: invalid data_type {field.value.data_type}")

    if errors:
        print("❌ FAILED: Found errors in metadata structure:\n")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ PASSED: All {len(list(PlayerStatField))} fields have valid metadata")
        return True


def test_persistable_fields():
    """Test that persistable field extraction works"""
    print("\n" + "=" * 80)
    print("TEST 2: Persistable Fields Extraction")
    print("=" * 80)

    persistable = PlayerStatField.get_persistable_fields()
    non_persistable = [f for f in PlayerStatField if not f.persistable]

    print(f"\nPersistable fields: {len(persistable)}")
    print(f"Non-persistable fields: {len(non_persistable)}")

    # Print first 10 persistable fields as sample
    print("\nSample persistable fields (first 10):")
    for field in persistable[:10]:
        print(f"  {field.name:30s} -> {field.db_column:30s} (default={field.default_value})")

    # Verify critical fields are persistable
    critical_fields = [
        PlayerStatField.PLAYER_ID,
        PlayerStatField.PLAYER_NAME,
        PlayerStatField.PASSING_YARDS,
        PlayerStatField.INTERCEPTIONS_THROWN,
        PlayerStatField.RUSHING_YARDS,
        PlayerStatField.RECEIVING_YARDS,
        PlayerStatField.TACKLES,
        PlayerStatField.SACKS,
    ]

    errors = []
    for field in critical_fields:
        if not field.persistable:
            errors.append(f"{field.name} should be persistable but is not")

    if errors:
        print("\n❌ FAILED: Critical fields not marked as persistable:\n")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ PASSED: All critical fields are persistable")
        return True


def test_insert_statement_generation():
    """Test auto-generation of INSERT statements"""
    print("\n" + "=" * 80)
    print("TEST 3: INSERT Statement Generation")
    print("=" * 80)

    # Generate INSERT statement with additional columns
    stmt = PlayerStatField.generate_insert_statement(
        table_name="player_game_stats",
        additional_columns=["dynasty_id", "game_id"]
    )

    print("\nGenerated INSERT statement:")
    print(stmt)

    # Verify statement structure
    errors = []
    if "INSERT INTO player_game_stats" not in stmt:
        errors.append("Missing table name in INSERT statement")

    if "dynasty_id" not in stmt:
        errors.append("Missing dynasty_id in column list")

    if "game_id" not in stmt:
        errors.append("Missing game_id in column list")

    if "player_id" not in stmt:
        errors.append("Missing player_id in column list")

    if "passing_interceptions" not in stmt:
        errors.append("Missing passing_interceptions in column list (critical field!)")

    if "VALUES" not in stmt:
        errors.append("Missing VALUES clause")

    # Count placeholders (should match number of columns)
    persistable_count = len(PlayerStatField.get_persistable_fields())
    additional_count = 2  # dynasty_id, game_id
    expected_placeholders = persistable_count + additional_count

    placeholder_count = stmt.count("?")
    if placeholder_count != expected_placeholders:
        errors.append(
            f"Placeholder count mismatch: expected {expected_placeholders}, got {placeholder_count}"
        )

    if errors:
        print("\n❌ FAILED: INSERT statement generation has errors:\n")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n✅ PASSED: INSERT statement has {placeholder_count} placeholders for {expected_placeholders} columns")
        return True


def test_param_extraction():
    """Test parameter extraction from mock PlayerStats object"""
    print("\n" + "=" * 80)
    print("TEST 4: Parameter Extraction")
    print("=" * 80)

    # Create a mock PlayerStats object (simple object with attributes)
    class MockPlayerStats:
        def __init__(self):
            self.player_id = "player_123"
            self.player_name = "Test Player"
            self.team_id = 7
            self.position = "QB"
            self.passing_yards = 350
            self.passing_tds = 3
            self.passing_completions = 25
            self.passing_attempts = 35
            self.interceptions_thrown = 1  # The critical field we fixed!
            self.rushing_yards = 15
            self.rushing_tds = 0
            self.rushing_attempts = 3

    mock_stats = MockPlayerStats()

    # Extract params
    params = PlayerStatField.extract_params_from_stats(
        mock_stats,
        additional_params=("dynasty_test", "game_456")
    )

    print(f"\nExtracted {len(params)} parameters from PlayerStats")
    print("\nFirst 15 parameters:")
    for i, param in enumerate(params[:15]):
        print(f"  [{i}] {param}")

    # Verify critical values
    errors = []
    if params[0] != "dynasty_test":
        errors.append(f"First param should be dynasty_id='dynasty_test', got {params[0]}")

    if params[1] != "game_456":
        errors.append(f"Second param should be game_id='game_456', got {params[1]}")

    # Find interceptions_thrown in params
    persistable_fields = PlayerStatField.get_persistable_fields()
    field_names = [f.field_name for f in persistable_fields]

    try:
        int_index = field_names.index("interceptions_thrown")
        # Add 2 to account for dynasty_id and game_id
        actual_int_value = params[int_index + 2]
        if actual_int_value != 1:
            errors.append(
                f"interceptions_thrown should be 1, got {actual_int_value} at index {int_index + 2}"
            )
        else:
            print(f"\n✅ Found interceptions_thrown=1 at index {int_index + 2}")
    except ValueError:
        errors.append("interceptions_thrown not found in persistable fields!")

    if errors:
        print("\n❌ FAILED: Parameter extraction has errors:\n")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ PASSED: All parameters extracted correctly")
        return True


def test_schema_validation():
    """Test schema consistency validation"""
    print("\n" + "=" * 80)
    print("TEST 5: Schema Consistency Validation")
    print("=" * 80)

    # Test with correct schema
    correct_schema = PlayerStatField.get_persistable_db_columns()
    result = PlayerStatField.validate_schema_consistency(correct_schema)

    print("\nTest 5a: Validating against correct schema")
    if result["valid"]:
        print("✅ PASSED: Schema validation works with correct schema")
    else:
        print("❌ FAILED: Schema validation should pass with correct schema")
        print(f"  Errors: {result['errors']}")
        return False

    # Test with missing column
    incomplete_schema = [col for col in correct_schema if col != "passing_interceptions"]
    result = PlayerStatField.validate_schema_consistency(incomplete_schema)

    print("\nTest 5b: Validating against schema missing 'passing_interceptions'")
    if not result["valid"]:
        print(f"✅ PASSED: Detected missing column")
        print(f"  Missing: {result['missing_in_db']}")
    else:
        print("❌ FAILED: Should have detected missing passing_interceptions column")
        return False

    # Test with extra column
    schema_with_extra = correct_schema + ["fake_column"]
    result = PlayerStatField.validate_schema_consistency(schema_with_extra)

    print("\nTest 5c: Validating against schema with extra 'fake_column'")
    if not result["valid"]:
        print(f"✅ PASSED: Detected extra column")
        print(f"  Extra: {result['extra_in_db']}")
    else:
        print("❌ FAILED: Should have detected extra fake_column")
        return False

    return True


def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("PlayerStatField Phase 1 Validation")
    print("=" * 80)

    tests = [
        ("Metadata Structure", test_metadata_structure),
        ("Persistable Fields", test_persistable_fields),
        ("INSERT Generation", test_insert_statement_generation),
        ("Param Extraction", test_param_extraction),
        ("Schema Validation", test_schema_validation),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ FAILED: {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")

    print("\n" + "=" * 80)
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("=" * 80)
        print("\nPhase 1 Complete! Ready for Phase 2 (schema_generator.py)")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
