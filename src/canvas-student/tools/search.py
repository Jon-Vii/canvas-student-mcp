"""Search-related tools for Canvas MCP."""
import logging
from typing import Dict, List, Any, Union

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached
from tools.api_client import make_canvas_request
from tools.courses import get_courses
from tools.assignments import get_course_assignments
from tools.content import get_course_pages, get_course_files, get_course_announcements

async def search_course(course_id: int, search_term: str) -> Dict[str, Any]:
    """Search for content within a specific course."""
    logger.info(f"Searching course {course_id} for '{search_term}'")
    results = {"course_id": course_id, "results": {}}
    
    # Search assignments
    try:
        assignments = await get_course_assignments(course_id)
        matching_assignments = [a for a in assignments if 
                              search_term.lower() in a.get("name", "").lower() or 
                              (a.get("description") and search_term.lower() in a.get("description").lower())]
        if matching_assignments:
            results["results"]["assignments"] = matching_assignments
            logger.info(f"Found {len(matching_assignments)} matching assignments")
    except Exception as e:
        logger.error(f"Error searching assignments: {e}")
        pass
    
    # Search pages
    try:
        pages = await get_course_pages(course_id)
        matching_pages = [p for p in pages if 
                        search_term.lower() in p.get("title", "").lower() or 
                        (p.get("body") and search_term.lower() in p.get("body").lower())]
        if matching_pages:
            results["results"]["pages"] = matching_pages
            logger.info(f"Found {len(matching_pages)} matching pages")
    except Exception as e:
        logger.error(f"Error searching pages: {e}")
        pass
    
    # Search files
    try:
        files = await get_course_files(course_id)
        matching_files = [f for f in files if 
                         search_term.lower() in f.get("display_name", "").lower()]
        if matching_files:
            results["results"]["files"] = matching_files
            logger.info(f"Found {len(matching_files)} matching files")
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        pass
    
    # Search announcements
    try:
        announcements = await get_course_announcements(course_id, False)
        matching_announcements = [a for a in announcements if 
                                search_term.lower() in a.get("title", "").lower() or
                                (a.get("message") and search_term.lower() in a.get("message").lower())]
        if matching_announcements:
            results["results"]["announcements"] = matching_announcements
            logger.info(f"Found {len(matching_announcements)} matching announcements")
    except Exception as e:
        logger.error(f"Error searching announcements: {e}")
        pass
    
    return results

async def search_all_courses(search_term: str) -> Dict[str, Dict[str, Any]]:
    """Search across all courses for the specified term."""
    logger.info(f"Searching all courses for '{search_term}'")
    courses = await get_courses()
    all_results = {}
    
    for course in courses:
        course_id = course["id"]
        course_results = await search_course(course_id, search_term)
        if course_results["results"]:
            all_results[course["name"]] = course_results["results"]
    
    logger.info(f"Found matches in {len(all_results)} courses")
    return all_results 