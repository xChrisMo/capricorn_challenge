#!/usr/bin/env python3
"""
Manual test script for the MCP server.
Tests the server by sending JSON-RPC requests and checking responses.
"""
import json
import subprocess
import sys

def send_request(server, request):
    """Send a request and get response."""
    request_json = json.dumps(request)
    request_bytes = request_json.encode('utf-8')
    header = f"Content-Length: {len(request_bytes)}\r\n\r\n".encode('utf-8')

    server.stdin.write(header + request_bytes)
    server.stdin.flush()

    # Read response
    header_line = server.stdout.readline().decode('utf-8')
    content_length = int(header_line.split(':')[1].strip())
    server.stdout.readline()  # Empty line
    response_bytes = server.stdout.read(content_length)
    return json.loads(response_bytes.decode('utf-8'))

def main():
    print("=" * 60)
    print("Manual MCP Server Test")
    print("=" * 60)
    print()

    # Start server
    print("Starting MCP server...")
    server = subprocess.Popen(
        ['python', '-m', 'mcp.release_notes_server'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    try:
        # Test 1: Initialize
        print("1. Testing initialize...")
        response = send_request(server, {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {}
        })
        assert response['result']['serverInfo']['name'] == 'release-notes-server'
        print("   ✓ Server initialized")

        # Test 2: List tools
        print("2. Testing tools/list...")
        response = send_request(server, {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'tools/list',
            'params': {}
        })
        tools = response['result']['tools']
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"     - {tool['name']}: {tool['description'][:50]}...")

        # Test 3: Call get_git_history
        print("3. Testing get_git_history...")
        response = send_request(server, {
            'jsonrpc': '2.0',
            'id': 3,
            'method': 'tools/call',
            'params': {
                'name': 'get_git_history',
                'arguments': {
                    'from_ref': 'HEAD~2',
                    'to_ref': 'HEAD',
                    'max_commits': 10
                }
            }
        })

        result_text = response['result']['content'][0]['text']
        result = json.loads(result_text)
        print(f"   ✓ Got {len(result['commits'])} commits")
        print(f"     From: {result['from_ref']} ({result['from_sha'][:8]})")
        print(f"     To: {result['to_ref']} ({result['to_sha'][:8]})")

        print()
        print("=" * 60)
        print("✅ All manual tests passed!")
        print("=" * 60)

    finally:
        server.terminate()
        server.wait()

if __name__ == '__main__':
    main()
