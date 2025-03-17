"""Content-related tools for Canvas MCP."""
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached
from tools.api_client import make_canvas_request

@cached()
async def get_course_files(course_id: int) -> List[Dict[str, Any]]:
    """Get all files for a specific course."""
    logger.info(f"Fetching files for course {course_id}")
    return await make_canvas_request(f"courses/{course_id}/files")

@cached()
async def get_course_modules(course_id: int) -> List[Dict[str, Any]]:
    """Get all modules for a specific course."""
    logger.info(f"Fetching modules for course {course_id}")
    return await make_canvas_request(f"courses/{course_id}/modules")

@cached()
async def get_module_items(course_id: int, module_id: int) -> List[Dict[str, Any]]:
    """Get all items in a specific module."""
    logger.info(f"Fetching items for module {module_id} in course {course_id}")
    return await make_canvas_request(f"courses/{course_id}/modules/{module_id}/items")

@cached()
async def get_course_pages(course_id: int) -> List[Dict[str, Any]]:
    """Get all pages for a specific course."""
    logger.info(f"Fetching pages for course {course_id}")
    return await make_canvas_request(f"courses/{course_id}/pages")

@cached()
async def get_course_announcements(course_id: int, recent_only: bool = True) -> List[Dict[str, Any]]:
    """Get announcements for a specific course."""
    logger.info(f"Fetching announcements for course {course_id}, recent_only={recent_only}")
    
    params = {}
    if recent_only:
        # Get announcements from the last 14 days
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        params = {"start_date": start_date}
        
    return await make_canvas_request(
        f"courses/{course_id}/announcements",
        params=params
    ) 