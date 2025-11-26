# MCP Server Example

MCP (Model Context Protocol) servers allow Claude to access external data and services.

## What is an MCP Server?

An MCP server provides:
- Tools that Claude can call
- Resources (data, files, APIs)
- Prompts and context

## Example Use Cases

- Connect to project management tools (Jira, ADO)
- Query databases
- Access internal APIs
- Fetch real-time data (CI/CD status, monitoring)
- Integration with external services

## Basic Structure

```json
// In plugin.json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["examples/mcp-server-example/server.js"]
    }
  }
}
```

## Example Server

See `server.js` for a minimal working example that provides:
- A simple tool Claude can call
- A resource Claude can read
- A prompt template

## Your Task

Build an MCP server that provides real value:
- What external system would help development?
- What data does Claude need access to?
- What operations should be possible?

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)
