#!/bin/bash
set -e

# Run either the HTTP API or MCP server based on SERVER_TYPE
if [ "$SERVER_TYPE" = "mcp" ]; then
    echo "Starting MCP server..."
    exec python mcp_server.py
else
    echo "Starting HTTP API server..."
    exec python server.py
fi