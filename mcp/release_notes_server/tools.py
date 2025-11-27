"""
Tool implementations for Release Notes MCP server.

This module contains implementations for the three main tools:
- get_git_history: Fetch git commit history between refs
- get_ci_report: Load CI/CD test report from JSON
- get_customer_watchlist: Load customer watchlist from JSON
"""
import logging
from typing import Any, Dict, List, Optional

from . import git_tools
from . import file_utils

logger = logging.getLogger(__name__)


def get_git_history(
    from_ref: str,
    to_ref: str,
    include_diffs: bool = False,
    max_commits: int = 200
) -> Dict[str, Any]:
    """
    Fetch git commit history between two refs.

    This function uses real git operations to:
    - Validate git repository exists
    - Resolve refs to SHAs
    - Check commit count and enforce max_commits
    - Run git log with appropriate format
    - Parse output into structured JSON
    - Handle errors (invalid refs, timeouts, etc.)

    Args:
        from_ref: Starting git ref (tag, branch, SHA)
        to_ref: Ending git ref (tag, branch, SHA)
        include_diffs: Include full patch diffs (default: False)
        max_commits: Maximum commits to return (default: 200)

    Returns:
        Dictionary containing:
        - from_ref, to_ref: Original inputs
        - from_sha, to_sha: Resolved SHAs
        - commits: List of commit objects with metadata and file changes
        - stats: Aggregate statistics
        - warnings: List of warnings (e.g., commit limit reached)

    Raises:
        GitRepoNotFoundError: If not in a git repository
        InvalidRefError: If ref doesn't exist
        EmptyCommitRangeError: If no commits between refs
        CommitLimitExceededError: If commits > max_commits and not allowed
        GitOperationTimeoutError: If git operation times out
    """
    logger.info(
        f"get_git_history called: {from_ref}..{to_ref} "
        f"(include_diffs={include_diffs}, max_commits={max_commits})"
    )

    # Use real git operations
    return git_tools.get_git_history_data(
        from_ref=from_ref,
        to_ref=to_ref,
        include_diffs=include_diffs,
        max_commits=max_commits,
        cwd="."
    )


def get_ci_report(report_path: str = "./ci_report.json") -> Optional[Dict[str, Any]]:
    """
    Load and parse CI/CD test report from JSON file.

    Args:
        report_path: Path to CI report JSON file (default: ./ci_report.json)

    Returns:
        Dictionary containing:
        - test_summary: Total, passed, failed, skipped counts
        - coverage: Line and branch coverage percentages
        - failed_tests: List of failed test details
        - build_status: success/failed/unstable/unknown
        - duration_seconds: Test execution time
        - metadata: Optional build info

        Returns None if file doesn't exist (graceful degradation).

    Raises:
        InvalidJSONFileError: If file exists but contains invalid JSON
    """
    logger.info(f"get_ci_report called: {report_path}")

    return file_utils.load_ci_report(report_path)


def get_customer_watchlist(
    watchlist_path: str = "./customer_watchlist.json"
) -> Dict[str, Any]:
    """
    Load customer watchlist with critical accounts and features.

    Args:
        watchlist_path: Path to watchlist JSON file (default: ./customer_watchlist.json)

    Returns:
        Dictionary containing:
        - critical_customers: List of important customer IDs
        - watched_features: List of high-visibility features
        - breaking_change_keywords: Keywords that signal breaking changes
        - high_risk_paths: File paths that are high-risk
        - migration_patterns: Patterns for database migrations

        Always returns valid structure (uses defaults if file missing).

    Raises:
        InvalidJSONFileError: If file exists but contains invalid JSON
    """
    logger.info(f"get_customer_watchlist called: {watchlist_path}")

    return file_utils.load_customer_watchlist(watchlist_path)


def register_tools(server: Any) -> None:
    """
    Register all tools with the MCP server.

    Args:
        server: ReleaseNotesServer instance
    """
    # Tool 1: get_git_history
    server.register_tool(
        name="get_git_history",
        description="Fetch git commit history between two refs with file change statistics",
        input_schema={
            "type": "object",
            "properties": {
                "from_ref": {
                    "type": "string",
                    "description": "Starting git ref (tag, branch, SHA)"
                },
                "to_ref": {
                    "type": "string",
                    "description": "Ending git ref (tag, branch, SHA)"
                },
                "include_diffs": {
                    "type": "boolean",
                    "description": "Include full patch diffs (warning: expensive for large ranges)",
                    "default": False
                },
                "max_commits": {
                    "type": "integer",
                    "description": "Maximum commits to return (default 200, prevents runaway queries)",
                    "default": 200
                }
            },
            "required": ["from_ref", "to_ref"]
        },
        handler=get_git_history
    )

    # Tool 2: get_ci_report
    server.register_tool(
        name="get_ci_report",
        description="Load and parse CI/CD test report from JSON file",
        input_schema={
            "type": "object",
            "properties": {
                "report_path": {
                    "type": "string",
                    "description": "Path to CI report JSON file",
                    "default": "./ci_report.json"
                }
            },
            "required": []
        },
        handler=get_ci_report
    )

    # Tool 3: get_customer_watchlist
    server.register_tool(
        name="get_customer_watchlist",
        description="Load customer watchlist with critical accounts and features",
        input_schema={
            "type": "object",
            "properties": {
                "watchlist_path": {
                    "type": "string",
                    "description": "Path to customer watchlist JSON file",
                    "default": "./customer_watchlist.json"
                }
            },
            "required": []
        },
        handler=get_customer_watchlist
    )

    logger.info("All tools registered successfully")
