#!/usr/bin/env python3
"""
Simple test script for the MCP server.

Tests the JSON-RPC protocol by sending requests and validating responses.
"""
import json
import subprocess
import sys
from typing import Any, Dict, Optional


class MCPClient:
    """Simple MCP client for testing."""

    def __init__(self, server_cmd: list):
        """
        Initialize client and start server process.

        Args:
            server_cmd: Command to start server (e.g., ["python", "-m", "mcp.release_notes_server"])
        """
        self.process = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        self.request_id = 0

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> dict:
        """
        Send a JSON-RPC request and return the response.

        Args:
            method: JSON-RPC method name
            params: Optional parameters dict

        Returns:
            Parsed JSON response
        """
        self.request_id += 1

        # Build request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id
        }
        if params is not None:
            request["params"] = params

        # Serialize to JSON
        body = json.dumps(request).encode('utf-8')

        # Build message with Content-Length framing
        message = f"Content-Length: {len(body)}\r\n\r\n".encode('utf-8') + body

        # Send request
        self.process.stdin.write(message)
        self.process.stdin.flush()

        # Read response
        response = self._read_response()
        return response

    def _read_response(self) -> dict:
        """Read a JSON-RPC response with Content-Length framing."""
        # Read headers
        content_length = None
        while True:
            line = self.process.stdout.readline().decode('utf-8').strip()
            if not line:
                break

            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())

        if content_length is None:
            raise ValueError("No Content-Length header in response")

        # Read body
        body = self.process.stdout.read(content_length).decode('utf-8')
        return json.loads(body)

    def close(self):
        """Close the server process."""
        self.process.stdin.close()
        self.process.wait(timeout=2)


def test_initialize():
    """Test initialize method."""
    print("Testing initialize...")
    client = MCPClient(["python", "-m", "mcp.release_notes_server"])

    try:
        response = client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "release-notes-server"
        print("✓ Initialize test passed")

    finally:
        client.close()


def test_tools_list():
    """Test tools/list method."""
    print("Testing tools/list...")
    client = MCPClient(["python", "-m", "mcp.release_notes_server"])

    try:
        # Initialize first
        client.send_request("initialize", {})

        # List tools
        response = client.send_request("tools/list")

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "tools" in response["result"]

        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "get_git_history" in tool_names
        assert "get_ci_report" in tool_names
        assert "get_customer_watchlist" in tool_names

        print(f"✓ Tools list test passed - found {len(tools)} tools")

    finally:
        client.close()


def test_tool_call():
    """Test tools/call method with get_git_history."""
    print("Testing tools/call (get_git_history)...")
    client = MCPClient(["python", "-m", "mcp.release_notes_server"])

    try:
        # Initialize first
        client.send_request("initialize", {})

        # Call tool
        response = client.send_request("tools/call", {
            "name": "get_git_history",
            "arguments": {
                "from_ref": "v1.0.0",
                "to_ref": "v1.1.0"
            }
        })

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "content" in response["result"]

        # Parse tool result from content
        content_text = response["result"]["content"][0]["text"]
        result = json.loads(content_text)

        assert result["from_ref"] == "v1.0.0"
        assert result["to_ref"] == "v1.1.0"
        assert "commits" in result
        assert "stats" in result

        print(f"✓ Tool call test passed - got {result['stats']['total_commits']} commits")

    finally:
        client.close()


def test_invalid_method():
    """Test error handling for invalid method."""
    print("Testing invalid method error handling...")
    client = MCPClient(["python", "-m", "mcp.release_notes_server"])

    try:
        # Initialize first
        client.send_request("initialize", {})

        # Call non-existent method
        response = client.send_request("nonexistent_method")

        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
        assert "not found" in response["error"]["message"].lower()

        print("✓ Invalid method test passed")

    finally:
        client.close()


def test_invalid_params():
    """Test error handling for invalid parameters."""
    print("Testing invalid params error handling...")
    client = MCPClient(["python", "-m", "mcp.release_notes_server"])

    try:
        # Initialize first
        client.send_request("initialize", {})

        # Call tool with missing required param
        response = client.send_request("tools/call", {
            "name": "get_git_history",
            "arguments": {
                "from_ref": "v1.0.0"
                # Missing to_ref
            }
        })

        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params

        print("✓ Invalid params test passed")

    finally:
        client.close()


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Server Protocol Tests")
    print("=" * 60)
    print()

    tests = [
        test_initialize,
        test_tools_list,
        test_tool_call,
        test_invalid_method,
        test_invalid_params,
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
            failed += 1
            print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
