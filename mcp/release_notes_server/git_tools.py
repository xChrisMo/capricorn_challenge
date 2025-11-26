"""
Git operations and commit parsing for release notes.

This module provides low-level git operations using subprocess (stdlib only).
All functions assume they're running in a git repository context.
"""
import subprocess
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from .errors import (
    GitRepoNotFoundError,
    InvalidRefError,
    EmptyCommitRangeError,
    CommitLimitExceededError,
    GitOperationTimeoutError,
    InternalError,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_COMMITS = 200
GIT_TIMEOUT_SECONDS = 30
COMMIT_DELIMITER = "|||END_COMMIT|||"
FIELD_DELIMITER = "|||"


def is_git_repository(path: str = ".") -> bool:
    """
    Check if the given path is inside a git repository.

    Args:
        path: Path to check (default: current directory)

    Returns:
        True if inside a git repository, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            timeout=5,
            check=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def resolve_ref(ref: str, cwd: str = ".") -> str:
    """
    Resolve a git ref (tag, branch, SHA) to a full SHA.

    Args:
        ref: Git reference (tag, branch, or SHA)
        cwd: Working directory (default: current directory)

    Returns:
        Full SHA hash

    Raises:
        InvalidRefError: If ref doesn't exist
        GitRepoNotFoundError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=cwd,
            capture_output=True,
            timeout=5,
            check=True,
            text=True
        )
        sha = result.stdout.strip()
        logger.debug(f"Resolved {ref} -> {sha}")
        return sha

    except subprocess.TimeoutExpired:
        raise GitOperationTimeoutError(5)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip().lower()

        if "not a git repository" in stderr:
            raise GitRepoNotFoundError(cwd)
        elif "unknown revision" in stderr or "bad revision" in stderr:
            raise InvalidRefError(ref)
        else:
            raise InvalidRefError(ref)

    except FileNotFoundError:
        raise InternalError("git command not found. Is git installed?")


def get_commit_count(from_ref: str, to_ref: str, cwd: str = ".") -> int:
    """
    Count commits between two refs.

    Args:
        from_ref: Starting ref
        to_ref: Ending ref
        cwd: Working directory

    Returns:
        Number of commits in range from_ref..to_ref

    Raises:
        InvalidRefError: If refs don't exist
        GitOperationTimeoutError: If operation times out
    """
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "--no-merges", f"{from_ref}..{to_ref}"],
            cwd=cwd,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=True,
            text=True
        )
        count = int(result.stdout.strip())
        logger.debug(f"Commit count {from_ref}..{to_ref}: {count}")
        return count

    except subprocess.TimeoutExpired:
        raise GitOperationTimeoutError(GIT_TIMEOUT_SECONDS)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip().lower()

        if "unknown revision" in stderr or "bad revision" in stderr:
            # Try to determine which ref is invalid
            try:
                resolve_ref(from_ref, cwd)
                raise InvalidRefError(to_ref)
            except InvalidRefError:
                raise InvalidRefError(from_ref)
        else:
            raise InternalError(f"git rev-list failed: {e.stderr}")

    except ValueError as e:
        raise InternalError(f"Failed to parse commit count: {e}")


def run_git_log(
    from_ref: str,
    to_ref: str,
    include_diffs: bool = False,
    max_commits: int = DEFAULT_MAX_COMMITS,
    cwd: str = ".",
    timeout: int = GIT_TIMEOUT_SECONDS
) -> str:
    """
    Run git log with custom format to get commit history.

    Args:
        from_ref: Starting ref
        to_ref: Ending ref
        include_diffs: Include full patch diffs (expensive)
        max_commits: Maximum commits to return
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        Raw git log output

    Raises:
        InvalidRefError: If refs don't exist
        GitOperationTimeoutError: If operation times out
        InternalError: If git command fails
    """
    # Build git log command
    # Format: SHA|||author|||email|||timestamp|||subject|||body|||END_COMMIT
    log_format = f"%H{FIELD_DELIMITER}%an{FIELD_DELIMITER}%ae{FIELD_DELIMITER}%at{FIELD_DELIMITER}%s{FIELD_DELIMITER}%b{FIELD_DELIMITER}{COMMIT_DELIMITER}"

    cmd = [
        "git", "log",
        "--no-merges",
        f"--format={log_format}",
        "--numstat",  # Show file stats
        f"-{max_commits}",  # Limit commits
        f"{from_ref}..{to_ref}"
    ]

    # Add patch diffs if requested
    if include_diffs:
        cmd.insert(2, "-p")  # Add patch output

    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=True,
            text=True,
            encoding='utf-8',
            errors='replace'  # Replace invalid UTF-8 with replacement char
        )

        return result.stdout

    except subprocess.TimeoutExpired:
        raise GitOperationTimeoutError(timeout)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip().lower()

        if "unknown revision" in stderr or "bad revision" in stderr:
            # Try to determine which ref is invalid
            try:
                resolve_ref(from_ref, cwd)
                raise InvalidRefError(to_ref)
            except InvalidRefError:
                raise InvalidRefError(from_ref)
        else:
            raise InternalError(f"git log failed: {e.stderr}")

    except FileNotFoundError:
        raise InternalError("git command not found. Is git installed?")


def parse_git_log_output(raw_output: str, from_ref: str, to_ref: str) -> Dict[str, Any]:
    """
    Parse git log output into structured JSON.

    Args:
        raw_output: Raw output from git log
        from_ref: Original from_ref (for metadata)
        to_ref: Original to_ref (for metadata)

    Returns:
        Dictionary with commits, stats, and warnings

    Format:
        {
            "commits": [
                {
                    "sha": "...",
                    "author": "...",
                    "email": "...",
                    "timestamp": 1234567890,
                    "date": "2024-01-15T10:30:00Z",
                    "subject": "...",
                    "body": "...",
                    "files_changed": [
                        {
                            "path": "src/file.py",
                            "insertions": 50,
                            "deletions": 10,
                            "status": "modified"
                        }
                    ]
                }
            ],
            "stats": {
                "total_commits": 15,
                "total_files_changed": 42,
                "total_insertions": 1200,
                "total_deletions": 300,
                "authors": ["Jane", "John"],
                "date_range": {...}
            }
        }
    """
    if not raw_output.strip():
        # No commits in range
        return {
            "commits": [],
            "stats": {
                "total_commits": 0,
                "total_files_changed": 0,
                "total_insertions": 0,
                "total_deletions": 0,
                "authors": [],
                "date_range": None
            }
        }

    commits = []
    authors_set = set()
    total_insertions = 0
    total_deletions = 0
    files_set = set()
    timestamps = []

    # Split by commit delimiter
    commit_blocks = raw_output.split(COMMIT_DELIMITER)

    # First pass: extract all commit metadata
    commit_metadata_list = []

    for block_idx, block in enumerate(commit_blocks):
        block = block.strip()
        if not block:
            continue

        # Split block into lines
        lines = block.split('\n')

        # Find commit metadata line (contains FIELD_DELIMITER)
        metadata_line = None
        for line in lines:
            if line.strip() and FIELD_DELIMITER in line and line.count(FIELD_DELIMITER) >= 5:
                metadata_line = line
                break

        if metadata_line is None:
            # No metadata in this block
            continue

        # Parse metadata
        parts = metadata_line.split(FIELD_DELIMITER)
        if len(parts) < 6:
            logger.warning(f"Invalid commit metadata: {metadata_line[:100]}")
            continue

        sha = parts[0].strip()
        author = parts[1].strip()
        email = parts[2].strip()
        timestamp_str = parts[3].strip()
        subject = parts[4].strip()
        body = parts[5].strip() if len(parts) > 5 else ""

        # Convert timestamp
        try:
            timestamp = int(timestamp_str)
            date_iso = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')
            timestamps.append(timestamp)
        except (ValueError, OSError):
            logger.warning(f"Invalid timestamp: {timestamp_str}")
            timestamp = 0
            date_iso = "1970-01-01T00:00:00Z"

        # Track author
        authors_set.add(author)

        commit_metadata_list.append({
            "sha": sha,
            "author": author,
            "email": email,
            "timestamp": timestamp,
            "date": date_iso,
            "subject": subject,
            "body": body,
            "block_idx": block_idx
        })

    # Second pass: extract numstat data and associate with commits
    for i, commit_meta in enumerate(commit_metadata_list):
        files_changed = []
        commit_insertions = 0
        commit_deletions = 0

        # Numstat for commit i is in block i+1 (after the delimiter)
        # It appears before the next commit's metadata
        numstat_block_idx = commit_meta["block_idx"] + 1

        if numstat_block_idx < len(commit_blocks):
            block = commit_blocks[numstat_block_idx].strip()
            lines = block.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Stop if we hit the next commit's metadata
                if FIELD_DELIMITER in line and line.count(FIELD_DELIMITER) >= 5:
                    break

                # numstat format: insertions\tdeletions\tfilename
                # Note: Binary files show as "-\t-\tfilename"
                match = re.match(r'^(\d+|-)\s+(\d+|-)\s+(.+)$', line)
                if not match:
                    continue

                insertions_str, deletions_str, filepath = match.groups()

                # Handle binary files (show as "-")
                insertions = 0 if insertions_str == '-' else int(insertions_str)
                deletions = 0 if deletions_str == '-' else int(deletions_str)

                # Determine file status (simplified)
                status = "modified"  # Default
                if insertions > 0 and deletions == 0:
                    status = "added"
                elif insertions == 0 and deletions > 0:
                    status = "deleted"

                files_changed.append({
                    "path": filepath,
                    "insertions": insertions,
                    "deletions": deletions,
                    "status": status
                })

                commit_insertions += insertions
                commit_deletions += deletions
                files_set.add(filepath)

        total_insertions += commit_insertions
        total_deletions += commit_deletions

        # Build complete commit object
        commit = {
            "sha": commit_meta["sha"],
            "author": commit_meta["author"],
            "email": commit_meta["email"],
            "timestamp": commit_meta["timestamp"],
            "date": commit_meta["date"],
            "subject": commit_meta["subject"],
            "body": commit_meta["body"],
            "files_changed": files_changed
        }

        commits.append(commit)

    # Calculate date range
    date_range = None
    if timestamps:
        first_timestamp = min(timestamps)
        last_timestamp = max(timestamps)
        date_range = {
            "first_commit_date": datetime.utcfromtimestamp(first_timestamp).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "last_commit_date": datetime.utcfromtimestamp(last_timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    # Build stats
    stats = {
        "total_commits": len(commits),
        "total_files_changed": len(files_set),
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "authors": sorted(list(authors_set)),
        "date_range": date_range
    }

    return {
        "commits": commits,
        "stats": stats
    }


def get_git_history_data(
    from_ref: str,
    to_ref: str,
    include_diffs: bool = False,
    max_commits: int = DEFAULT_MAX_COMMITS,
    cwd: str = "."
) -> Dict[str, Any]:
    """
    High-level function to get git history between two refs.

    This is the main entry point that coordinates all git operations.

    Args:
        from_ref: Starting ref
        to_ref: Ending ref
        include_diffs: Include full patch diffs
        max_commits: Maximum commits to return
        cwd: Working directory

    Returns:
        Complete git history data with commits, stats, and warnings

    Raises:
        GitRepoNotFoundError: If not in a git repository
        InvalidRefError: If refs don't exist
        EmptyCommitRangeError: If no commits between refs
        CommitLimitExceededError: If too many commits (and strict mode)
        GitOperationTimeoutError: If operations timeout
    """
    warnings = []

    # Check if we're in a git repository
    if not is_git_repository(cwd):
        raise GitRepoNotFoundError(cwd)

    # Resolve refs to SHAs
    from_sha = resolve_ref(from_ref, cwd)
    to_sha = resolve_ref(to_ref, cwd)

    # Check if refs are identical
    if from_sha == to_sha:
        raise EmptyCommitRangeError(from_ref, to_ref)

    # Get commit count
    count = get_commit_count(from_ref, to_ref, cwd)

    if count == 0:
        raise EmptyCommitRangeError(from_ref, to_ref)

    # Warn if limit reached
    if count > max_commits:
        warnings.append(
            f"⚠️  Commit limit reached: showing first {max_commits} of {count} commits. "
            f"Use --max-commits to increase limit."
        )
        logger.warning(f"Commit count {count} exceeds max_commits {max_commits}")

    # Warn about large diffs
    if include_diffs and count > 50:
        warnings.append(
            f"⚠️  Including diffs for {min(count, max_commits)} commits may be slow."
        )

    # Run git log
    raw_output = run_git_log(
        from_ref=from_ref,
        to_ref=to_ref,
        include_diffs=include_diffs,
        max_commits=max_commits,
        cwd=cwd
    )

    # Parse output
    parsed = parse_git_log_output(raw_output, from_ref, to_ref)

    # Build final result
    result = {
        "from_ref": from_ref,
        "to_ref": to_ref,
        "from_sha": from_sha,
        "to_sha": to_sha,
        "commits": parsed["commits"],
        "stats": parsed["stats"],
        "warnings": warnings
    }

    logger.info(
        f"Retrieved {result['stats']['total_commits']} commits "
        f"from {from_ref}..{to_ref}"
    )

    return result
