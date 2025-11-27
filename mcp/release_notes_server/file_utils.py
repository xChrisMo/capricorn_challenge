"""
File I/O utilities for loading JSON configuration files.

Implements graceful degradation:
- Returns None or defaults if files don't exist
- Validates JSON structure
- Provides helpful error messages
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import InvalidJSONFileError

logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load and parse a JSON file with error handling.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON dict, or None if file doesn't exist

    Raises:
        InvalidJSONFileError: If file exists but contains invalid JSON
    """
    path = Path(file_path)

    # Graceful degradation: return None if file doesn't exist
    if not path.exists():
        logger.info(f"JSON file not found: {file_path} (will use defaults)")
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded JSON file: {file_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise InvalidJSONFileError(file_path, str(e))
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise InvalidJSONFileError(file_path, str(e))


def load_ci_report(report_path: str) -> Optional[Dict[str, Any]]:
    """
    Load and validate CI report JSON file.

    Expected structure:
    {
        "test_summary": {"total", "passed", "failed", "skipped"},
        "coverage": {"line_percent", "branch_percent"},
        "build_status": "success|failed|unstable",
        ...
    }

    Args:
        report_path: Path to CI report JSON file

    Returns:
        CI report dict, or None if file doesn't exist

    Raises:
        InvalidJSONFileError: If file exists but is invalid
    """
    data = load_json_file(report_path)

    if data is None:
        return None

    # Basic validation - check for expected top-level keys
    expected_keys = {'test_summary', 'coverage', 'build_status'}
    missing_keys = expected_keys - set(data.keys())

    if missing_keys:
        logger.warning(
            f"CI report missing recommended keys: {missing_keys}. "
            f"Report may be incomplete."
        )

    # Validate test_summary structure
    if 'test_summary' in data:
        test_summary = data['test_summary']
        required_fields = {'total', 'passed', 'failed'}
        missing_fields = required_fields - set(test_summary.keys())
        if missing_fields:
            logger.warning(f"test_summary missing fields: {missing_fields}")

    # Validate coverage structure
    if 'coverage' in data:
        coverage = data['coverage']
        if 'line_percent' not in coverage:
            logger.warning("coverage missing line_percent")

    return data


def load_customer_watchlist(watchlist_path: str) -> Dict[str, Any]:
    """
    Load customer watchlist JSON file with defaults.

    Expected structure:
    {
        "critical_customers": ["customer-id", ...],
        "watched_features": ["feature-name", ...],
        "high_risk_paths": ["path/prefix/", ...],
        ...
    }

    Args:
        watchlist_path: Path to watchlist JSON file

    Returns:
        Watchlist dict (uses defaults if file doesn't exist)

    Raises:
        InvalidJSONFileError: If file exists but is invalid
    """
    # Default watchlist structure
    defaults = {
        "critical_customers": [],
        "watched_features": [],
        "breaking_change_keywords": [
            "BREAKING",
            "BREAKING CHANGE",
            "deprecated",
            "removed",
            "drop support",
            "incompatible"
        ],
        "high_risk_paths": [],
        "migration_patterns": [
            "migrations/",
            "alembic/versions/",
            "db/migrate/"
        ]
    }

    data = load_json_file(watchlist_path)

    if data is None:
        logger.info("Using default customer watchlist (no file found)")
        return defaults

    # Merge with defaults (file values override defaults)
    merged = defaults.copy()
    merged.update(data)

    # Validate list fields
    list_fields = [
        'critical_customers',
        'watched_features',
        'breaking_change_keywords',
        'high_risk_paths',
        'migration_patterns'
    ]

    for field in list_fields:
        if field in merged and not isinstance(merged[field], list):
            logger.warning(f"watchlist.{field} should be a list, got {type(merged[field])}")
            merged[field] = []

    return merged
