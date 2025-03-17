"""Main MCP server for Canvas integration."""
import os
import asyncio
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initializing FastMCP server
mcp = FastMCP("canvas-student")

# Load environment variables
# Consider using python-dotenv for better env management
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "12523~84nXE3aWP9ZQDr8Zawttf2KWFzCvevmaRB3khzML6JBUYnBAJh6BVFt6AneKWVwX")
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.instructure.com")
CLIENT_ID = os.environ.get("CANVAS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVAS_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/oauth/callback")

# Rename this file to canvas_student.py (underscore instead of hyphen) for importability
# Change filename in imports for other modules
# For now we'll continue with the current name

# Import tools - these imports need to match our file structure
from tools.courses import get_courses, find_course_by_name, get_course_details
from tools.assignments import get_course_assignments, find_exams_in_course, get_upcoming_deadlines
from tools.content import get_course_files, get_course_modules, get_course_pages, get_course_announcements
from tools.search import search_course, search_all_courses
from tools.utils import format_course_summary, search_all_course_content, clear_cache

# Register course tools
mcp.tool(get_courses)
mcp.tool(find_course_by_name)
mcp.tool(get_course_details)

# Register assignment tools
mcp.tool(get_course_assignments)
mcp.tool(find_exams_in_course)
mcp.tool(get_upcoming_deadlines)

# Register content tools
mcp.tool(get_course_files)
mcp.tool(get_course_modules)
mcp.tool(get_course_pages)
mcp.tool(get_course_announcements)

# Register search tools
mcp.tool(search_course)
mcp.tool(search_all_courses)

# Register utility tools
mcp.tool(format_course_summary)
mcp.tool(search_all_course_content)
mcp.tool(clear_cache)

# Authentication tools
@mcp.tool
async def check_auth_status():
    """Check if the user's authentication token is valid and return expiration info."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CANVAS_BASE_URL}/api/v1/users/self",
                headers={"Authorization": f"Bearer {CANVAS_API_TOKEN}"}
            )
            response.raise_for_status()
            return {"status": "authenticated", "user": response.json()}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"status": "token_expired", "message": "Authentication token has expired"}
            return {"status": "error", "message": str(e)}

@mcp.tool
async def get_auth_url(redirect_uri: str = REDIRECT_URI):
    """Generate OAuth authorization URL for Canvas."""
    if not CLIENT_ID:
        return {"error": "CLIENT_ID not configured"}
    
    auth_url = (f"{CANVAS_BASE_URL}/login/oauth2/auth"
                f"?client_id={CLIENT_ID}&response_type=code"
                f"&redirect_uri={redirect_uri}&state=canvas-mcp")
    
    return {"auth_url": auth_url}

# The MCP server can be run both synchronously and asynchronously
# For compatibility with the MCP protocol, we'll use the synchronous version with stdio transport
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')

