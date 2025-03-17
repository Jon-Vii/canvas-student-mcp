"""Main MCP server for Canvas integration."""
import os
import asyncio
import logging
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initializing FastMCP server
mcp = FastMCP("canvas-student")

# Load environment variables
# Consider using python-dotenv for better env management
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "12523~84nXE3aWP9ZQDr8Zawttf2KWFzCvevmaRB3khzML6JBUYnBAJh6BVFt6AneKWVwX")
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.instructure.com")

# Remove OAuth variables - we're only using API token authentication
# CLIENT_ID = os.environ.get("CANVAS_CLIENT_ID")
# CLIENT_SECRET = os.environ.get("CANVAS_CLIENT_SECRET")
# REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/oauth/callback")

# Import tools - these imports need to match our file structure
from tools.courses import get_courses, find_course_by_name, get_course_details
from tools.assignments import get_course_assignments, find_exams_in_course, get_upcoming_deadlines
from tools.content import get_course_files, get_course_modules, get_course_pages, get_course_announcements
from tools.search import search_course, search_all_courses
from tools.utils import format_course_summary, search_all_course_content, clear_cache

# Register course tools
mcp.tool()(get_courses)
mcp.tool()(find_course_by_name)
mcp.tool()(get_course_details)

# Register assignment tools
mcp.tool()(get_course_assignments)
mcp.tool()(find_exams_in_course)
mcp.tool()(get_upcoming_deadlines)

# Register content tools
mcp.tool()(get_course_files)
mcp.tool()(get_course_modules)
mcp.tool()(get_course_pages)
mcp.tool()(get_course_announcements)

# Register search tools
mcp.tool()(search_course)
mcp.tool()(search_all_courses)

# Register utility tools
mcp.tool()(format_course_summary)
mcp.tool()(search_all_course_content)
mcp.tool()(clear_cache)

# Authentication status tool
@mcp.tool()
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

# Add a diagnostic authentication test tool
@mcp.tool()
async def test_auth():
    """Test Canvas API authentication and return detailed diagnostic information."""
    logger.info("Running authentication test...")
    
    # 1. Check if the token is present
    if not CANVAS_API_TOKEN:
        return {
            "status": "error",
            "message": "No API token provided",
            "diagnostics": {
                "token_present": False,
                "token_format_valid": False
            }
        }
    
    # 2. Check token format
    token_format_valid = CANVAS_API_TOKEN.startswith("12523~")
    
    diagnostics = {
        "token_present": True,
        "token_format_valid": token_format_valid,
        "token_value": f"{CANVAS_API_TOKEN[:8]}...{CANVAS_API_TOKEN[-4:]}",  # Show partial token for security
        "base_url": CANVAS_BASE_URL
    }
    
    # 3. Test the API connection
    async with httpx.AsyncClient() as client:
        try:
            # First test /api/v1/users/self endpoint
            logger.info("Testing /api/v1/users/self endpoint...")
            response = await client.get(
                f"{CANVAS_BASE_URL}/api/v1/users/self",
                headers={"Authorization": f"Bearer {CANVAS_API_TOKEN}"}
            )
            
            diagnostics["users_self_status"] = response.status_code
            
            if response.status_code == 200:
                user_data = response.json()
                diagnostics["user_id"] = user_data.get("id")
                diagnostics["user_name"] = user_data.get("name")
                
                # Now test courses endpoint
                logger.info("Testing /api/v1/courses endpoint...")
                courses_response = await client.get(
                    f"{CANVAS_BASE_URL}/api/v1/courses",
                    headers={"Authorization": f"Bearer {CANVAS_API_TOKEN}"}
                )
                
                diagnostics["courses_status"] = courses_response.status_code
                
                if courses_response.status_code == 200:
                    courses_data = courses_response.json()
                    diagnostics["courses_count"] = len(courses_data)
                    diagnostics["courses_response"] = (
                        courses_data if courses_data == {} else 
                        [{"id": c.get("id"), "name": c.get("name")} for c in courses_data[:3]]
                    )
                    
                    return {
                        "status": "success" if courses_data else "warning",
                        "message": "Authentication successful" if courses_data else "Authentication successful but no courses found",
                        "diagnostics": diagnostics
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Courses API error: {courses_response.status_code}",
                        "diagnostics": diagnostics
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Authentication failed with status code: {response.status_code}",
                    "diagnostics": diagnostics
                }
                
        except Exception as e:
            logger.error(f"Error during authentication test: {e}")
            diagnostics["exception"] = str(e)
            return {
                "status": "error",
                "message": f"Error during authentication test: {e}",
                "diagnostics": diagnostics
            }

# Removed OAuth-specific tool
# @mcp.tool()
# async def get_auth_url(redirect_uri: str = REDIRECT_URI):
#    """Generate OAuth authorization URL for Canvas."""
#    if not CLIENT_ID:
#        return {"error": "CLIENT_ID not configured"}
#    
#    auth_url = (f"{CANVAS_BASE_URL}/login/oauth2/auth"
#                f"?client_id={CLIENT_ID}&response_type=code"
#                f"&redirect_uri={redirect_uri}&state=canvas-mcp")
#    
#    return {"auth_url": auth_url}

# The MCP server can be run both synchronously and asynchronously
# For compatibility with the MCP protocol, we'll use the synchronous version with stdio transport
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')

