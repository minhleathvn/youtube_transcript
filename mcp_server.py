"""
Main entry point for YouTube Transcript MCP server
"""
import logging
from app.mcp_server import mcp

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting YouTube Transcript MCP Server...")
    mcp.run()