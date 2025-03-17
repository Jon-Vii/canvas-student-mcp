#!/usr/bin/env python
"""
Canvas Student MCP - Server launcher

This script starts the Canvas Student MCP server with Claude-optimized tools.
"""
import sys
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("canvas-mcp-launcher")

def main():
    """Start the MCP server with Claude-optimized tools."""
    # Import and run the MCP server
    logger.info("Starting Canvas Student MCP server with Claude-optimized tools...")
    try:
        # Add the current directory to the path if needed
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Import and run the MCP server
        from canvas_student import mcp
        
        # Log information about the optimizations
        logger.info("Tool output is formatted for optimal Claude integration")
        logger.info("Tools provide rich context for files and Canvas content")
        logger.info("Redundant tools have been consolidated for better performance")
        
        # Start the server
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 