"""
Custom exception classes for MCP server error handling.

Maps Python exceptions to JSON-RPC 2.0 error codes.
"""
from typing import Any, Optional


class JSONRPCError(Exception):
    """Base class for JSON-RPC errors."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to JSON-RPC error object."""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            error["data"] = self.data
        return error


class ParseError(JSONRPCError):
    """Invalid JSON was received (-32700)."""

    def __init__(self, details: str = "Invalid JSON"):
        super().__init__(-32700, "Parse error", details)


class InvalidRequest(JSONRPCError):
    """The JSON sent is not a valid Request object (-32600)."""

    def __init__(self, details: str = "Invalid Request"):
        super().__init__(-32600, "Invalid Request", details)


class MethodNotFound(JSONRPCError):
    """The method does not exist / is not available (-32601)."""

    def __init__(self, method: str):
        super().__init__(-32601, "Method not found", f"Method '{method}' not found")


class InvalidParams(JSONRPCError):
    """Invalid method parameter(s) (-32602)."""

    def __init__(self, details: str):
        super().__init__(-32602, "Invalid params", details)


class InternalError(JSONRPCError):
    """Internal JSON-RPC error (-32603)."""

    def __init__(self, details: str = "Internal error"):
        super().__init__(-32603, "Internal error", details)


# Business logic exceptions (map to -32000 to -32099 range)
class ReleaseNotesError(JSONRPCError):
    """Base class for release notes business logic errors."""

    def __init__(self, code: int, message: str, details: Optional[str] = None):
        super().__init__(code, message, details)


class GitRepoNotFoundError(ReleaseNotesError):
    """Not in a git repository."""

    def __init__(self, path: str = "."):
        super().__init__(
            -32001,
            "Git repository not found",
            f"No .git directory found at '{path}'. Run 'git init' or cd to repository root."
        )


class InvalidRefError(ReleaseNotesError):
    """Git ref does not exist."""

    def __init__(self, ref: str):
        super().__init__(
            -32002,
            "Invalid git ref",
            f"Ref '{ref}' not found. Run 'git tag --list' or 'git branch -a' to see available refs."
        )


class EmptyCommitRangeError(ReleaseNotesError):
    """No commits between refs."""

    def __init__(self, from_ref: str, to_ref: str):
        super().__init__(
            -32003,
            "Empty commit range",
            f"No commits between '{from_ref}' and '{to_ref}'."
        )


class CommitLimitExceededError(ReleaseNotesError):
    """Too many commits in range."""

    def __init__(self, count: int, max_commits: int):
        super().__init__(
            -32004,
            "Commit limit exceeded",
            f"Found {count} commits, but limit is {max_commits}. Use a smaller range or increase --max-commits."
        )


class GitOperationTimeoutError(ReleaseNotesError):
    """Git operation timed out."""

    def __init__(self, timeout: int = 30):
        super().__init__(
            -32005,
            "Git operation timeout",
            f"Git operation exceeded {timeout} second timeout. Try a smaller commit range."
        )


class FileNotFoundError(ReleaseNotesError):
    """Required file not found."""

    def __init__(self, path: str):
        super().__init__(
            -32006,
            "File not found",
            f"File '{path}' does not exist."
        )


class InvalidJSONFileError(ReleaseNotesError):
    """JSON file is malformed."""

    def __init__(self, path: str, details: str):
        super().__init__(
            -32007,
            "Invalid JSON file",
            f"File '{path}' contains invalid JSON: {details}"
        )
