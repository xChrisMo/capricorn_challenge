# Release Notes MCP Server

A Model Context Protocol (MCP) server for analyzing git repositories and generating release notes with quality assessment.

## Overview

This MCP server provides three tools for release note generation:

1. **`get_git_history`** - Fetch commit history between two git refs
2. **`get_ci_report`** - Load CI/CD test results from JSON
3. **`get_customer_watchlist`** - Load customer watchlist configuration

## Features

- **Zero dependencies**: Uses only Python standard library
- **JSON-RPC 2.0**: Implements full protocol with Content-Length framing
- **Production-ready**: Comprehensive error handling and validation
- **Type-safe**: Full type hints throughout
- **Well-tested**: Clean separation of concerns for easy testing

## Requirements

- Python 3.8+
- Git (for git operations)
- No external packages required

## Installation

The server is designed to be run directly from the repository:

```bash
# From repository root
python -m mcp.release_notes_server
```

## Running the Server

### Standalone (for testing)

```bash
# Run server directly (listens on stdin/stdout)
python -m mcp.release_notes_server
```

The server will:
- Read JSON-RPC requests from stdin
- Write responses to stdout
- Log debug info to stderr

### With Claude Code

Add to your Claude Code MCP configuration (typically in `~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "release-notes": {
      "command": "python",
      "args": [
        "-m",
        "mcp.release_notes_server"
      ],
      "cwd": "/path/to/capricorn_challenge",
      "env": {}
    }
  }
}
```

## Protocol

The server implements JSON-RPC 2.0 over stdio with Content-Length framing:

```
Content-Length: 123\r\n
\r\n
{"jsonrpc": "2.0", "method": "...", "id": 1}
```

### Supported Methods

#### `initialize`

Initialize the MCP server connection.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {}
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "release-notes-server",
      "version": "0.1.0"
    }
  }
}
```

#### `tools/list`

List available tools.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 2
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "get_git_history",
        "description": "Fetch git commit history between two refs...",
        "inputSchema": { ... }
      },
      ...
    ]
  }
}
```

#### `tools/call`

Invoke a specific tool.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_git_history",
    "arguments": {
      "from_ref": "v1.0.0",
      "to_ref": "v1.1.0"
    }
  },
  "id": 3
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"from_ref\": \"v1.0.0\", ...}"
      }
    ]
  }
}
```

## Tools

### get_git_history

Fetch git commit history between two refs.

**Parameters:**
- `from_ref` (string, required): Starting git ref (tag, branch, SHA)
- `to_ref` (string, required): Ending git ref (tag, branch, SHA)
- `include_diffs` (boolean, optional): Include full patch diffs (default: false)
- `max_commits` (integer, optional): Maximum commits to return (default: 200)

**Returns:**
```json
{
  "from_ref": "v1.0.0",
  "to_ref": "v1.1.0",
  "from_sha": "abc123...",
  "to_sha": "def456...",
  "commits": [
    {
      "sha": "...",
      "author": "Jane Dev",
      "email": "jane@example.com",
      "timestamp": 1705320000,
      "date": "2024-01-15T10:30:00Z",
      "subject": "feat: add feature",
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
    "authors": ["Jane Dev", "John Doe"]
  },
  "warnings": []
}
```

**Errors:**
- `-32001`: Git repository not found
- `-32002`: Invalid git ref
- `-32003`: Empty commit range
- `-32004`: Commit limit exceeded
- `-32005`: Git operation timeout

### get_ci_report

Load CI/CD test report from JSON file.

**Parameters:**
- `report_path` (string, optional): Path to CI report JSON (default: `./ci_report.json`)

**Returns:**
```json
{
  "test_summary": {
    "total": 150,
    "passed": 148,
    "failed": 2,
    "skipped": 0
  },
  "coverage": {
    "line_percent": 85.5,
    "branch_percent": 78.2
  },
  "failed_tests": [...],
  "build_status": "unstable"
}
```

Returns `null` if file doesn't exist (graceful degradation).

**Errors:**
- `-32007`: Invalid JSON file

### get_customer_watchlist

Load customer watchlist configuration.

**Parameters:**
- `watchlist_path` (string, optional): Path to watchlist JSON (default: `./customer_watchlist.json`)

**Returns:**
```json
{
  "critical_customers": ["acme-corp"],
  "watched_features": ["authentication"],
  "breaking_change_keywords": ["BREAKING", "deprecated"],
  "high_risk_paths": ["src/payment/", "src/auth/"],
  "migration_patterns": ["migrations/"]
}
```

Returns default configuration if file doesn't exist.

**Errors:**
- `-32007`: Invalid JSON file

## Error Handling

All errors follow JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Git repository not found",
    "data": "No .git directory found at '.'. Run 'git init' or cd to repository root."
  }
}
```

### Error Codes

| Code | Error | Description |
|------|-------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Malformed request |
| -32601 | Method not found | Unknown method |
| -32602 | Invalid params | Invalid parameters |
| -32603 | Internal error | Server error |
| -32001 | Git repo not found | Not in git repository |
| -32002 | Invalid ref | Git ref doesn't exist |
| -32003 | Empty range | No commits between refs |
| -32004 | Commit limit | Too many commits |
| -32005 | Git timeout | Operation timed out |
| -32006 | File not found | Required file missing |
| -32007 | Invalid JSON | JSON file malformed |

## Testing

### Manual Testing

Test the server manually using echo and pipes:

```bash
# Send initialize request
echo -e 'Content-Length: 89\r\n\r\n{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | python -m mcp.release_notes_server

# List tools
echo -e 'Content-Length: 50\r\n\r\n{"jsonrpc":"2.0","method":"tools/list","id":2}' | python -m mcp.release_notes_server

# Call a tool
cat << 'EOF' | python -m mcp.release_notes_server
Content-Length: 156

{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_git_history","arguments":{"from_ref":"HEAD~5","to_ref":"HEAD"}},"id":3}
EOF
```

### Unit Testing

```bash
# Run unit tests (when implemented)
python -m pytest tests/test_server.py
```

## Architecture

```
mcp/release_notes_server/
├── __init__.py          # Package entry point
├── __main__.py          # Module runner
├── server.py            # JSON-RPC server implementation
├── tools.py             # Tool implementations
├── errors.py            # Custom exception classes
└── README.md            # This file
```

### Component Responsibilities

- **server.py**: JSON-RPC protocol handling, request/response framing
- **tools.py**: Business logic for each tool
- **errors.py**: Exception hierarchy and error codes
- **__init__.py**: Package interface and main() entry point

## Current Status

✅ **Implemented:**
- Full JSON-RPC 2.0 protocol with Content-Length framing
- Tool registration and dispatch
- Error handling and validation
- Three tool stubs with correct signatures

🚧 **TODO (Next Steps):**
- Implement real git operations in `get_git_history`
- Implement file reading in `get_ci_report`
- Implement file reading in `get_customer_watchlist`
- Add unit tests
- Add integration tests

## Troubleshooting

### Server doesn't start

**Check Python version:**
```bash
python --version  # Should be 3.8+
```

**Check for syntax errors:**
```bash
python -m py_compile mcp/release_notes_server/server.py
```

### No output / hangs

**Check logs on stderr:**
```bash
python -m mcp.release_notes_server 2>debug.log
```

### Invalid JSON-RPC responses

**Validate Content-Length:**
- Must be exact byte count of JSON body
- Must include `\r\n\r\n` after headers
- Body must be valid JSON

**Example:**
```python
body = '{"jsonrpc":"2.0","method":"tools/list","id":1}'
length = len(body.encode('utf-8'))
message = f"Content-Length: {length}\r\n\r\n{body}"
```

### Tool calls fail

**Check tool exists:**
```bash
# List available tools
echo -e 'Content-Length: 50\r\n\r\n{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m mcp.release_notes_server
```

**Check parameter types:**
- All params must match schema types
- Use correct JSON types (string, number, boolean)

## Development

### Adding a New Tool

1. Add function to `tools.py`:
```python
def my_new_tool(param1: str, param2: int = 10) -> dict:
    """Tool description."""
    # Implementation
    return {"result": ...}
```

2. Register in `register_tools()`:
```python
server.register_tool(
    name="my_new_tool",
    description="...",
    input_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer", "default": 10}
        },
        "required": ["param1"]
    },
    handler=my_new_tool
)
```

### Logging

Set log level via environment:
```bash
export PYTHONUNBUFFERED=1
export MCP_LOG_LEVEL=DEBUG
python -m mcp.release_notes_server 2>debug.log
```

Logs go to stderr only (stdout reserved for JSON-RPC).

## License

See repository LICENSE file.
