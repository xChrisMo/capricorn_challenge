# MCP Server Testing Guide

## Quick Manual Tests

### Test 1: Initialize

```bash
python -c "
import json
req = {
    'jsonrpc': '2.0',
    'method': 'initialize',
    'params': {},
    'id': 1
}
body = json.dumps(req)
msg = f'Content-Length: {len(body)}\r\n\r\n{body}'
print(msg, end='')
" | python -m mcp.release_notes_server 2>/dev/null
```

Expected output:
```
Content-Length: ...

{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", ...}}
```

### Test 2: List Tools

```bash
python -c "
import json
req = {
    'jsonrpc': '2.0',
    'method': 'tools/list',
    'id': 2
}
body = json.dumps(req)
msg = f'Content-Length: {len(body)}\r\n\r\n{body}'
print(msg, end='')
" | python -m mcp.release_notes_server 2>/dev/null
```

Expected output shows 3 tools: `get_git_history`, `get_ci_report`, `get_customer_watchlist`

### Test 3: Call Tool

```bash
python -c "
import json
req = {
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'get_git_history',
        'arguments': {
            'from_ref': 'HEAD~5',
            'to_ref': 'HEAD'
        }
    },
    'id': 3
}
body = json.dumps(req)
msg = f'Content-Length: {len(body)}\r\n\r\n{body}'
print(msg, end='')
" | python -m mcp.release_notes_server 2>/dev/null
```

Expected output shows stub commit data.

## Automated Test Suite

Run the comprehensive test suite:

```bash
python mcp/test_server.py
```

This tests:
- ✓ Initialize method
- ✓ Tools list method
- ✓ Tool call with valid params
- ✓ Error handling for invalid method
- ✓ Error handling for invalid params

## Viewing Server Logs

To see debug logs while testing:

```bash
# Run server and capture stderr to file
echo '...' | python -m mcp.release_notes_server 2>server.log

# View logs
cat server.log
```

Log output includes:
```
[2024-01-15 10:30:00] INFO: ReleaseNotesServer initialized
[2024-01-15 10:30:00] INFO: Registered tool: get_git_history
[2024-01-15 10:30:00] INFO: Registered tool: get_ci_report
[2024-01-15 10:30:00] INFO: Registered tool: get_customer_watchlist
[2024-01-15 10:30:00] INFO: All tools registered successfully
[2024-01-15 10:30:00] INFO: Server starting...
[2024-01-15 10:30:00] INFO: Received initialize request
```

## Debugging Protocol Issues

### Check Content-Length Calculation

```python
import json

# Your request
req = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

# Serialize
body = json.dumps(req)
body_bytes = body.encode('utf-8')

# Calculate length
content_length = len(body_bytes)

print(f"Body: {body}")
print(f"Length: {content_length}")
print(f"Header: Content-Length: {content_length}\\r\\n\\r\\n")
```

### Validate JSON-RPC Format

All requests must have:
- `jsonrpc: "2.0"` (required)
- `method: "..."` (required)
- `id: ...` (required for requests, omit for notifications)
- `params: {...}` (optional)

All responses have:
- `jsonrpc: "2.0"` (required)
- `id: ...` (same as request)
- Either:
  - `result: {...}` (success)
  - `error: {...}` (error)

## Common Issues

### Server hangs / no output

**Cause**: Missing or incorrect Content-Length header

**Fix**: Ensure header format is exact:
```
Content-Length: 123\r\n
\r\n
{...json...}
```

### "Parse error" response

**Cause**: Invalid JSON in request body

**Fix**: Validate JSON with:
```bash
echo '{"your": "json"}' | python -m json.tool
```

### "Invalid Request" error

**Cause**: Missing required JSON-RPC fields

**Fix**: Ensure `jsonrpc` and `method` are present:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

### "Method not found" error

**Cause**: Typo in method name or calling wrong method

**Fix**: Use exact method names:
- `initialize`
- `tools/list`
- `tools/call`

### "Invalid params" error

**Cause**: Missing required parameter or wrong type

**Fix**: Check tool schema with `tools/list` and provide all required params

## Testing with Real Git Repos

Once git integration is implemented, test with:

```bash
cd /path/to/git/repo

python -c "
import json
req = {
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'get_git_history',
        'arguments': {
            'from_ref': 'v1.0.0',
            'to_ref': 'HEAD',
            'max_commits': 50
        }
    },
    'id': 1
}
body = json.dumps(req)
msg = f'Content-Length: {len(body)}\r\n\r\n{body}'
print(msg, end='')
" | python -m mcp.release_notes_server
```

## Next Steps

After git integration is implemented:

1. Test with various git refs (tags, branches, SHAs)
2. Test error cases (invalid refs, empty ranges)
3. Test with large commit ranges (100+ commits)
4. Test CI report and watchlist file loading
5. Test with missing/malformed JSON files

## Performance Testing

Test server performance with:

```bash
# Time a single request
time python mcp/test_server.py

# Test multiple sequential requests
for i in {1..10}; do
  python -c "..." | python -m mcp.release_notes_server 2>/dev/null
done
```

Expected performance:
- Initialize: <100ms
- Tools list: <50ms
- Simple tool call: <100ms
- Git history (when impl): <1s for 100 commits
