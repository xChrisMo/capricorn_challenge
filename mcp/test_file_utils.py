#!/usr/bin/env python3
"""
Tests for file I/O utilities.
"""
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.release_notes_server import file_utils
from mcp.release_notes_server.errors import InvalidJSONFileError


def test_load_json_file_success():
    """Test loading a valid JSON file."""
    print("Testing load_json_file with valid JSON...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = {"key": "value", "number": 42}
        json.dump(test_data, f)
        temp_path = f.name

    try:
        result = file_utils.load_json_file(temp_path)
        assert result == test_data
        print("  ✓ Valid JSON file loaded successfully")
    finally:
        Path(temp_path).unlink()

    print("✓ load_json_file success test passed\n")


def test_load_json_file_not_found():
    """Test loading a non-existent file."""
    print("Testing load_json_file with non-existent file...")

    result = file_utils.load_json_file("/nonexistent/path/file.json")
    assert result is None
    print("  ✓ Non-existent file returns None")

    print("✓ load_json_file not found test passed\n")


def test_load_json_file_invalid():
    """Test loading an invalid JSON file."""
    print("Testing load_json_file with invalid JSON...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name

    try:
        try:
            file_utils.load_json_file(temp_path)
            assert False, "Should have raised InvalidJSONFileError"
        except InvalidJSONFileError as e:
            assert "Invalid JSON" in str(e)
            print("  ✓ Invalid JSON raises InvalidJSONFileError")
    finally:
        Path(temp_path).unlink()

    print("✓ load_json_file invalid test passed\n")


def test_load_ci_report_valid():
    """Test loading a valid CI report."""
    print("Testing load_ci_report with valid report...")

    ci_data = {
        "test_summary": {
            "total": 100,
            "passed": 95,
            "failed": 5,
            "skipped": 0
        },
        "coverage": {
            "line_percent": 85.0,
            "branch_percent": 78.0
        },
        "build_status": "unstable",
        "duration_seconds": 120
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(ci_data, f)
        temp_path = f.name

    try:
        result = file_utils.load_ci_report(temp_path)
        assert result == ci_data
        assert result['test_summary']['total'] == 100
        assert result['coverage']['line_percent'] == 85.0
        print("  ✓ Valid CI report loaded successfully")
    finally:
        Path(temp_path).unlink()

    print("✓ load_ci_report valid test passed\n")


def test_load_ci_report_missing():
    """Test loading missing CI report (should return None)."""
    print("Testing load_ci_report with missing file...")

    result = file_utils.load_ci_report("/nonexistent/ci_report.json")
    assert result is None
    print("  ✓ Missing CI report returns None")

    print("✓ load_ci_report missing test passed\n")


def test_load_ci_report_incomplete():
    """Test loading incomplete CI report (should warn but succeed)."""
    print("Testing load_ci_report with incomplete data...")

    # Missing some expected keys
    incomplete_data = {
        "test_summary": {
            "total": 50,
            "passed": 50
            # Missing 'failed' field
        }
        # Missing 'coverage' and 'build_status'
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(incomplete_data, f)
        temp_path = f.name

    try:
        result = file_utils.load_ci_report(temp_path)
        assert result is not None
        assert result['test_summary']['total'] == 50
        print("  ✓ Incomplete CI report loaded with warnings")
    finally:
        Path(temp_path).unlink()

    print("✓ load_ci_report incomplete test passed\n")


def test_load_customer_watchlist_valid():
    """Test loading a valid customer watchlist."""
    print("Testing load_customer_watchlist with valid data...")

    watchlist_data = {
        "critical_customers": ["acme-corp", "globex"],
        "watched_features": ["authentication", "payments"],
        "high_risk_paths": ["src/auth/", "src/payment/"]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(watchlist_data, f)
        temp_path = f.name

    try:
        result = file_utils.load_customer_watchlist(temp_path)
        assert "acme-corp" in result['critical_customers']
        assert "authentication" in result['watched_features']
        assert "src/auth/" in result['high_risk_paths']
        # Should have defaults merged
        assert 'breaking_change_keywords' in result
        assert 'migration_patterns' in result
        print("  ✓ Valid watchlist loaded and merged with defaults")
    finally:
        Path(temp_path).unlink()

    print("✓ load_customer_watchlist valid test passed\n")


def test_load_customer_watchlist_missing():
    """Test loading missing customer watchlist (should return defaults)."""
    print("Testing load_customer_watchlist with missing file...")

    result = file_utils.load_customer_watchlist("/nonexistent/watchlist.json")
    assert result is not None
    assert 'critical_customers' in result
    assert 'watched_features' in result
    assert 'breaking_change_keywords' in result
    assert 'high_risk_paths' in result
    assert 'migration_patterns' in result
    # Should be empty or defaults
    assert isinstance(result['critical_customers'], list)
    print("  ✓ Missing watchlist returns defaults")

    print("✓ load_customer_watchlist missing test passed\n")


def test_load_customer_watchlist_invalid_types():
    """Test loading watchlist with invalid field types."""
    print("Testing load_customer_watchlist with invalid field types...")

    # critical_customers should be list, not string
    invalid_data = {
        "critical_customers": "should-be-a-list",
        "watched_features": ["valid-list"]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        temp_path = f.name

    try:
        result = file_utils.load_customer_watchlist(temp_path)
        assert result is not None
        # Should convert invalid field to empty list
        assert isinstance(result['critical_customers'], list)
        assert len(result['critical_customers']) == 0
        # Valid field should be preserved
        assert "valid-list" in result['watched_features']
        print("  ✓ Invalid field types corrected with warnings")
    finally:
        Path(temp_path).unlink()

    print("✓ load_customer_watchlist invalid types test passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("File Utilities Tests")
    print("=" * 60)
    print()

    tests = [
        test_load_json_file_success,
        test_load_json_file_not_found,
        test_load_json_file_invalid,
        test_load_ci_report_valid,
        test_load_ci_report_missing,
        test_load_ci_report_incomplete,
        test_load_customer_watchlist_valid,
        test_load_customer_watchlist_missing,
        test_load_customer_watchlist_invalid_types,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
