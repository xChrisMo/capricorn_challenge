"""
MCP Server for Release Notes Plugin.

Implements JSON-RPC 2.0 protocol over stdio with Content-Length framing.
Uses only Python standard library (no external dependencies).
"""
import json
import sys
import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass

from .errors import (
    JSONRPCError,
    ParseError,
    InvalidRequest,
    MethodNotFound,
    InvalidParams,
    InternalError,
)


# Configure logging to stderr only (stdout is for JSON-RPC protocol)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema definition for an MCP tool."""
    name: str
    description: str
    input_schema: dict
    handler: Callable


class ReleaseNotesServer:
    """
    MCP server that handles JSON-RPC 2.0 requests over stdio.

    Responsibilities:
    - Read JSON-RPC messages from stdin with Content-Length framing
    - Parse and validate requests
    - Dispatch to registered tool handlers
    - Format and write JSON-RPC responses to stdout
    - Handle errors and map to JSON-RPC error codes
    """

    def __init__(self):
        """Initialize the server with empty tool registry."""
        self.tools: Dict[str, ToolSchema] = {}
        self.running = False
        logger.info("ReleaseNotesServer initialized")

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable
    ) -> None:
        """
        Register a tool with the server.

        Args:
            name: Tool name (e.g., "get_git_history")
            description: Human-readable description
            input_schema: JSON Schema for tool parameters
            handler: Function to call when tool is invoked
        """
        schema = ToolSchema(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
        self.tools[name] = schema
        logger.info(f"Registered tool: {name}")

    def tool(self, name: str, description: str, input_schema: dict):
        """
        Decorator for registering tool functions.

        Usage:
            @server.tool(name="my_tool", description="...", input_schema={...})
            def my_tool(param1: str, param2: int = 10) -> dict:
                return {"result": ...}
        """
        def decorator(func: Callable) -> Callable:
            self.register_tool(name, description, input_schema, func)
            return func
        return decorator

    def read_message(self) -> Optional[dict]:
        """
        Read a JSON-RPC message from stdin using Content-Length framing.

        Protocol:
            Content-Length: 123\r\n
            \r\n
            {"jsonrpc": "2.0", ...}

        Returns:
            Parsed JSON object, or None on EOF

        Raises:
            ParseError: If JSON is malformed
            InvalidRequest: If framing is incorrect
        """
        # Read headers until empty line
        content_length = None
        while True:
            line = sys.stdin.buffer.readline()

            if not line:
                # EOF
                return None

            # Decode header line
            try:
                header = line.decode('utf-8').strip()
            except UnicodeDecodeError as e:
                raise InvalidRequest(f"Invalid header encoding: {e}")

            if not header:
                # Empty line signals end of headers
                break

            # Parse Content-Length header
            if header.lower().startswith('content-length:'):
                try:
                    content_length = int(header.split(':', 1)[1].strip())
                except (ValueError, IndexError) as e:
                    raise InvalidRequest(f"Invalid Content-Length header: {e}")

        if content_length is None:
            raise InvalidRequest("Missing Content-Length header")

        if content_length <= 0:
            raise InvalidRequest(f"Invalid Content-Length: {content_length}")

        # Read exactly content_length bytes
        try:
            body = sys.stdin.buffer.read(content_length)
        except Exception as e:
            raise InvalidRequest(f"Failed to read message body: {e}")

        if len(body) != content_length:
            raise InvalidRequest(
                f"Incomplete message: expected {content_length} bytes, got {len(body)}"
            )

        # Parse JSON
        try:
            message = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")
        except UnicodeDecodeError as e:
            raise ParseError(f"Invalid UTF-8: {e}")

        return message

    def write_message(self, message: dict) -> None:
        """
        Write a JSON-RPC message to stdout with Content-Length framing.

        Args:
            message: JSON-RPC response or notification
        """
        # Serialize to JSON
        body = json.dumps(message, ensure_ascii=False).encode('utf-8')

        # Write headers
        header = f"Content-Length: {len(body)}\r\n\r\n".encode('utf-8')

        # Write to stdout (binary mode)
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()

        logger.debug(f"Sent message: {message.get('method', message.get('result', 'response'))}")

    def validate_request(self, request: dict) -> None:
        """
        Validate JSON-RPC request structure.

        Args:
            request: Parsed JSON request

        Raises:
            InvalidRequest: If request is malformed
        """
        if not isinstance(request, dict):
            raise InvalidRequest("Request must be a JSON object")

        if request.get('jsonrpc') != '2.0':
            raise InvalidRequest("Must specify 'jsonrpc': '2.0'")

        if 'method' not in request:
            raise InvalidRequest("Missing 'method' field")

        if not isinstance(request['method'], str):
            raise InvalidRequest("Method must be a string")

        # id can be string, number, or null (notifications have no id)
        if 'id' in request:
            if not isinstance(request['id'], (str, int, type(None))):
                raise InvalidRequest("Request 'id' must be string, number, or null")

    def validate_params(self, method: str, params: dict) -> None:
        """
        Validate parameters against tool's input schema.

        Args:
            method: Tool name
            params: Parameters passed to tool

        Raises:
            MethodNotFound: If tool doesn't exist
            InvalidParams: If params don't match schema
        """
        if method not in self.tools:
            raise MethodNotFound(method)

        schema = self.tools[method].input_schema

        # Basic validation: check required fields
        required = schema.get('required', [])
        for field in required:
            if field not in params:
                raise InvalidParams(f"Missing required parameter: '{field}'")

        # Type validation for provided params
        properties = schema.get('properties', {})
        for key, value in params.items():
            if key not in properties:
                raise InvalidParams(f"Unknown parameter: '{key}'")

            # Basic type checking (extend as needed)
            expected_type = properties[key].get('type')
            if expected_type:
                if not self._check_type(value, expected_type):
                    raise InvalidParams(
                        f"Parameter '{key}' must be type '{expected_type}', got {type(value).__name__}"
                    )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON Schema type."""
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'object': dict,
            'array': list,
            'null': type(None),
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, skip validation

        return isinstance(value, expected_python_type)

    def dispatch(self, method: str, params: dict) -> Any:
        """
        Dispatch request to appropriate tool handler.

        Args:
            method: Tool name
            params: Tool parameters

        Returns:
            Tool result (must be JSON-serializable)

        Raises:
            MethodNotFound: If tool doesn't exist
            JSONRPCError: If tool execution fails
        """
        if method not in self.tools:
            raise MethodNotFound(method)

        handler = self.tools[method].handler

        try:
            # Call handler with params as keyword arguments
            result = handler(**params)
            return result
        except JSONRPCError:
            # Re-raise JSON-RPC errors as-is
            raise
        except TypeError as e:
            # Usually means wrong arguments
            raise InvalidParams(f"Invalid arguments: {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Error in tool '{method}'")
            raise InternalError(f"Tool '{method}' failed: {str(e)}")

    def handle_request(self, request: dict) -> Optional[dict]:
        """
        Handle a single JSON-RPC request.

        Args:
            request: Parsed JSON-RPC request

        Returns:
            JSON-RPC response, or None for notifications
        """
        request_id = request.get('id')

        try:
            # Validate request structure
            self.validate_request(request)

            method = request['method']
            params = request.get('params', {})

            # Handle special methods
            if method == 'initialize':
                return self._handle_initialize(request_id, params)
            elif method == 'tools/list':
                return self._handle_tools_list(request_id)
            elif method == 'tools/call':
                return self._handle_tools_call(request_id, params)
            else:
                raise MethodNotFound(method)

        except JSONRPCError as e:
            # Known error, return error response
            if request_id is not None:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': e.to_dict()
                }
            else:
                # Notification - don't send error response
                logger.error(f"Error in notification: {e.message}")
                return None

        except Exception as e:
            # Unexpected error
            logger.exception("Unexpected error handling request")
            if request_id is not None:
                error = InternalError(str(e))
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': error.to_dict()
                }
            return None

    def _handle_initialize(self, request_id: Any, params: dict) -> dict:
        """Handle MCP initialize request."""
        logger.info("Received initialize request")
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'protocolVersion': '2024-11-05',
                'capabilities': {
                    'tools': {}
                },
                'serverInfo': {
                    'name': 'release-notes-server',
                    'version': '0.1.0'
                }
            }
        }

    def _handle_tools_list(self, request_id: Any) -> dict:
        """Handle tools/list request - return available tools."""
        logger.info("Received tools/list request")
        tools = [
            {
                'name': tool.name,
                'description': tool.description,
                'inputSchema': tool.input_schema
            }
            for tool in self.tools.values()
        ]

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'tools': tools
            }
        }

    def _handle_tools_call(self, request_id: Any, params: dict) -> dict:
        """Handle tools/call request - invoke a tool."""
        if 'name' not in params:
            raise InvalidParams("Missing 'name' parameter")

        tool_name = params['name']
        tool_params = params.get('arguments', {})

        logger.info(f"Calling tool: {tool_name}")

        # Validate and dispatch
        self.validate_params(tool_name, tool_params)
        result = self.dispatch(tool_name, tool_params)

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(result, indent=2)
                    }
                ]
            }
        }

    def run(self) -> None:
        """
        Main server loop.

        Reads JSON-RPC requests from stdin, processes them, and writes
        responses to stdout. Runs until EOF or fatal error.
        """
        self.running = True
        logger.info("Server starting...")

        try:
            while self.running:
                # Read request
                try:
                    request = self.read_message()
                except JSONRPCError as e:
                    # Protocol error - send error response with null id
                    logger.error(f"Protocol error: {e.message}")
                    error_response = {
                        'jsonrpc': '2.0',
                        'id': None,
                        'error': e.to_dict()
                    }
                    self.write_message(error_response)
                    continue

                if request is None:
                    # EOF - clean shutdown
                    logger.info("EOF received, shutting down")
                    break

                logger.debug(f"Received request: {request.get('method', 'unknown')}")

                # Handle request
                response = self.handle_request(request)

                # Send response (if not a notification)
                if response is not None:
                    self.write_message(response)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.exception("Fatal error in server loop")
            raise
        finally:
            self.running = False
            logger.info("Server stopped")

    def shutdown(self) -> None:
        """Gracefully shutdown the server."""
        logger.info("Shutting down...")
        self.running = False
