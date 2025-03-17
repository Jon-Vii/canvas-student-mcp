#!/usr/bin/env python
"""
Canvas Student MCP - Main entry point

This file provides a simple entry point to run the Canvas MCP server.
"""
from canvas_student import mcp

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
