#!/usr/bin/env python3
"""
Integration tests for git operations.

Tests the real git integration using the current repository.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.release_notes_server import git_tools
from mcp.release_notes_server.errors import (
    GitRepoNotFoundError,
    InvalidRefError,
    EmptyCommitRangeError,
)


def test_is_git_repository():
    """Test git repository detection."""
    print("Testing is_git_repository...")

    # Current directory should be a git repo
    assert git_tools.is_git_repository("."), "Current directory should be a git repo"

    # /tmp should not be a git repo
    assert not git_tools.is_git_repository("/tmp"), "/tmp should not be a git repo"

    print("✓ is_git_repository test passed")


def test_resolve_ref():
    """Test ref resolution."""
    print("Testing resolve_ref...")

    # Resolve HEAD
    sha = git_tools.resolve_ref("HEAD")
    assert len(sha) == 40, f"SHA should be 40 chars, got {len(sha)}"
    assert sha.isalnum(), "SHA should be alphanumeric"
    print(f"  HEAD -> {sha[:8]}...")

    # Test invalid ref
    try:
        git_tools.resolve_ref("nonexistent-ref-12345")
        assert False, "Should have raised InvalidRefError"
    except InvalidRefError as e:
        print(f"  Invalid ref correctly raised: {e.message}")

    print("✓ resolve_ref test passed")


def test_get_commit_count():
    """Test commit counting."""
    print("Testing get_commit_count...")

    # Count commits from HEAD~2 to HEAD
    try:
        count = git_tools.get_commit_count("HEAD~2", "HEAD")
        print(f"  HEAD~2..HEAD: {count} commits")
        assert count >= 0 and count <= 2, f"Expected 0-2 commits, got {count}"
    except (EmptyCommitRangeError, InvalidRefError):
        print("  HEAD~2..HEAD: empty range or invalid ref (repo might have < 2 commits)")

    # get_commit_count returns 0 for empty ranges (not an error at this level)
    count = git_tools.get_commit_count("HEAD", "HEAD")
    assert count == 0, f"Empty range should have 0 commits, got {count}"
    print("  HEAD..HEAD: 0 commits (as expected)")

    print("✓ get_commit_count test passed")


def test_run_git_log():
    """Test git log execution."""
    print("Testing run_git_log...")

    # Get log from HEAD~2 to HEAD
    try:
        output = git_tools.run_git_log("HEAD~2", "HEAD", include_diffs=False, max_commits=10)
        assert isinstance(output, str), "Output should be string"
        assert len(output) > 0, "Output should not be empty"
        print(f"  Got {len(output)} bytes of output")
    except (EmptyCommitRangeError, InvalidRefError):
        print("  HEAD~2..HEAD: empty range or invalid ref (repo might have < 2 commits)")

    print("✓ run_git_log test passed")


def test_parse_git_log_output():
    """Test git log parsing."""
    print("Testing parse_git_log_output...")

    # Get real git log output and parse it
    try:
        raw_output = git_tools.run_git_log("HEAD~2", "HEAD", include_diffs=False, max_commits=10)
        parsed = git_tools.parse_git_log_output(raw_output, "HEAD~2", "HEAD")

        assert "commits" in parsed, "Should have commits key"
        assert "stats" in parsed, "Should have stats key"

        commits = parsed["commits"]
        stats = parsed["stats"]

        print(f"  Parsed {len(commits)} commits")

        if commits:
            # Check first commit structure
            commit = commits[0]
            assert "sha" in commit, "Commit should have sha"
            assert "author" in commit, "Commit should have author"
            assert "email" in commit, "Commit should have email"
            assert "timestamp" in commit, "Commit should have timestamp"
            assert "date" in commit, "Commit should have date"
            assert "subject" in commit, "Commit should have subject"
            assert "files_changed" in commit, "Commit should have files_changed"

            print(f"  First commit: {commit['sha'][:8]} - {commit['subject'][:50]}")
            print(f"  Author: {commit['author']} <{commit['email']}>")
            print(f"  Files changed: {len(commit['files_changed'])}")

        # Check stats
        assert stats["total_commits"] == len(commits), "Stats should match commit count"
        print(f"  Total insertions: {stats['total_insertions']}")
        print(f"  Total deletions: {stats['total_deletions']}")
        print(f"  Authors: {', '.join(stats['authors'])}")

    except (EmptyCommitRangeError, InvalidRefError):
        print("  HEAD~2..HEAD: empty range or invalid ref (repo might have < 2 commits)")

    print("✓ parse_git_log_output test passed")


def test_get_git_history_data():
    """Test complete git history retrieval."""
    print("Testing get_git_history_data...")

    try:
        # Get history from HEAD~2 to HEAD
        data = git_tools.get_git_history_data(
            from_ref="HEAD~2",
            to_ref="HEAD",
            include_diffs=False,
            max_commits=10
        )

        # Validate structure
        assert "from_ref" in data
        assert "to_ref" in data
        assert "from_sha" in data
        assert "to_sha" in data
        assert "commits" in data
        assert "stats" in data
        assert "warnings" in data

        print(f"  Range: {data['from_ref']}..{data['to_ref']}")
        print(f"  From SHA: {data['from_sha'][:8]}...")
        print(f"  To SHA: {data['to_sha'][:8]}...")
        print(f"  Commits: {data['stats']['total_commits']}")
        print(f"  Warnings: {len(data['warnings'])}")

        if data["warnings"]:
            for warning in data["warnings"]:
                print(f"    - {warning}")

        # Print JSON summary
        print(f"\n  Summary JSON:")
        summary = {
            "commits": data["stats"]["total_commits"],
            "files_changed": data["stats"]["total_files_changed"],
            "insertions": data["stats"]["total_insertions"],
            "deletions": data["stats"]["total_deletions"],
            "authors": data["stats"]["authors"]
        }
        print(f"  {json.dumps(summary, indent=2)}")

    except (EmptyCommitRangeError, InvalidRefError):
        print("  HEAD~2..HEAD: empty range or invalid ref (repo might have < 2 commits)")

    print("✓ get_git_history_data test passed")


def test_error_handling():
    """Test error handling."""
    print("Testing error handling...")

    # Test invalid ref
    try:
        git_tools.get_git_history_data("invalid-ref-xyz", "HEAD")
        assert False, "Should raise InvalidRefError"
    except InvalidRefError as e:
        print(f"  ✓ Invalid ref error: {e.data}")

    # Test empty range
    try:
        git_tools.get_git_history_data("HEAD", "HEAD")
        assert False, "Should raise EmptyCommitRangeError"
    except EmptyCommitRangeError as e:
        print(f"  ✓ Empty range error: {e.data}")

    # Test not a git repo (in /tmp)
    try:
        git_tools.get_git_history_data("HEAD~5", "HEAD", cwd="/tmp")
        assert False, "Should raise GitRepoNotFoundError"
    except GitRepoNotFoundError as e:
        print(f"  ✓ Not a git repo error: {e.data}")

    print("✓ error_handling test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Git Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_is_git_repository,
        test_resolve_ref,
        test_get_commit_count,
        test_run_git_log,
        test_parse_git_log_output,
        test_get_git_history_data,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
