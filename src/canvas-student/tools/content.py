"""Content-related tools for Canvas MCP."""

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from tools.utils import cached
from tools.api_client import make_canvas_request

@cached()
async def get_course_files(course_id: int):
    """Get all files for a specific course."""
    return await make_canvas_request(f"courses/{course_id}/files")

@cached()
async def get_course_modules(course_id: int):
    """Get all modules for a specific course."""
    return await make_canvas_request(f"courses/{course_id}/modules")

@cached()
async def get_module_items(course_id: int, module_id: int):
    """Get all items in a specific module."""
    return await make_canvas_request(f"courses/{course_id}/modules/{module_id}/items")

@cached()
async def get_course_pages(course_id: int):
    """Get all pages for a specific course."""
    return await make_canvas_request(f"courses/{course_id}/pages")

@cached()
async def get_course_announcements(course_id: int, recent_only: bool = True):
    """Get announcements for a specific course."""
    params = {}
    if recent_only:
        # Get announcements from the last 14 days
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        params = {"start_date": start_date}
        
    return await make_canvas_request(
        f"courses/{course_id}/announcements",
        params=params
    ) 