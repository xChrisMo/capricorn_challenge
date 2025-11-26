#!/usr/bin/env node

/**
 * Minimal MCP Server Example
 *
 * This is a simplified example showing the basic structure.
 * Real implementations would be more sophisticated.
 */

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');

// Create server instance
const server = new Server({
  name: 'example-server',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
    resources: {},
  },
});

// Register a simple tool
server.setRequestHandler('tools/list', async () => {
  return {
    tools: [
      {
        name: 'get_example_data',
        description: 'Gets example data from the system',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'What to query for',
            },
          },
          required: ['query'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'get_example_data') {
    // Your implementation here
    return {
      content: [
        {
          type: 'text',
          text: `Example data for query: ${args.query}`,
        },
      ],
    };
  }

  throw new Error(`Unknown tool: ${name}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Example Server running on stdio');
}

main().catch(console.error);
