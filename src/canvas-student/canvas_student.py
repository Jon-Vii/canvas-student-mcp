"""Main MCP server for Canvas integration."""
import os
import asyncio
import logging
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
import dotenv

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
from tools.courses import get_courses, get_course_details
from tools.assignments import get_course_assignments, find_exams_in_course, get_upcoming_deadlines
from tools.content import get_course_files, get_course_modules, get_course_pages, get_course_announcements
from tools.search import search_course, search_all_courses
from tools.utils import format_course_summary, clear_cache
from tools.canvas_client import check_auth
from tools.file_content import get_file_content
from tools.todos import get_todo_items, get_upcoming_todo_items
from tools.quizzes import get_course_quizzes, get_all_quizzes, get_quiz_details

# Register course tools
mcp.tool()(get_courses)
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
mcp.tool()(clear_cache)

# Register file content tool
mcp.tool()(get_file_content)

# Register todo and quiz tools
mcp.tool()(get_todo_items)
mcp.tool()(get_upcoming_todo_items)
mcp.tool()(get_course_quizzes)
mcp.tool()(get_all_quizzes)
mcp.tool()(get_quiz_details)

# Authentication tools
mcp.tool()(check_auth)  # Using check_auth from canvas_client

@mcp.tool()
async def get_auth_url(redirect_uri: str = REDIRECT_URI) -> Dict[str, Any]:
    """Generate OAuth authorization URL for Canvas."""
    # If API token is being used, notify the user
    if CANVAS_API_TOKEN:
        logger.info("Currently using API token authentication")
        return {
            "status": "info", 
            "message": "You are already configured to use an API token for authentication. OAuth flow is not necessary.",
            "using_api_token": True,
            "url": None
        }
    
    # If OAuth is being used but CLIENT_ID is missing
    if not CLIENT_ID:
        logger.error("CLIENT_ID not configured for OAuth authentication")
        return {
            "error": "CLIENT_ID not configured", 
            "message": "To use OAuth authentication, you must set CANVAS_CLIENT_ID in your environment or .env file.",
            "using_api_token": False
        }
    
    # Generate OAuth URL
    auth_url = (f"{CANVAS_BASE_URL}/login/oauth2/auth"
                f"?client_id={CLIENT_ID}&response_type=code"
                f"&redirect_uri={redirect_uri}&state=canvas-mcp")
    
    logger.info(f"Generated OAuth auth URL for redirect_uri: {redirect_uri}")
    return {
        "status": "success",
        "auth_url": auth_url,
        "using_api_token": False,
        "message": "Use this URL to authorize Canvas access through OAuth"
    }

# For backwards compatibility with scripts that use this module directly
if __name__ == "__main__":
    # Print deprecation warning
    print("WARNING: Running canvas_student.py directly is deprecated. Use main.py instead.")
    # Initialize and run the server
    mcp.run(transport='stdio')

