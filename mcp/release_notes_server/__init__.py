"""
Release Notes MCP Server Package.

A Model Context Protocol (MCP) server for analyzing git repositories
and generating release notes with quality assessment.
"""
from .server import ReleaseNotesServer
from .tools import register_tools
from .errors import (
    JSONRPCError,
    GitRepoNotFoundError,
    InvalidRefError,
    EmptyCommitRangeError,
)

__version__ = "0.1.0"
__all__ = [
    "ReleaseNotesServer",
    "register_tools",
    "JSONRPCError",
    "GitRepoNotFoundError",
    "InvalidRefError",
    "EmptyCommitRangeError",
]


def main() -> None:
    """Main entry point for the MCP server."""
    import sys
    import logging

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        stream=sys.stderr
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Release Notes MCP Server")

    try:
        # Create and configure server
        server = ReleaseNotesServer()
        register_tools(server)

        # Run server loop
        server.run()

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error in server")
        sys.exit(1)


if __name__ == "__main__":
    main()
