"""Search-related tools for Canvas MCP."""

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from tools.utils import cached
from tools.api_client import make_canvas_request
from tools.courses import get_courses
from tools.assignments import get_course_assignments
from tools.content import get_course_pages, get_course_files, get_course_announcements

async def search_course(course_id: int, search_term: str):
    """Search for content within a specific course."""
    results = {"course_id": course_id, "results": {}}
    
    # Search assignments
    try:
        assignments = await get_course_assignments(course_id)
        matching_assignments = [a for a in assignments if 
                              search_term.lower() in a.get("name", "").lower() or 
                              (a.get("description") and search_term.lower() in a.get("description").lower())]
        if matching_assignments:
            results["results"]["assignments"] = matching_assignments
    except Exception:
        pass
    
    # Search pages
    try:
        pages = await get_course_pages(course_id)
        matching_pages = [p for p in pages if 
                        search_term.lower() in p.get("title", "").lower() or 
                        (p.get("body") and search_term.lower() in p.get("body").lower())]
        if matching_pages:
            results["results"]["pages"] = matching_pages
    except Exception:
        pass
    
    # Search files
    try:
        files = await get_course_files(course_id)
        matching_files = [f for f in files if 
                         search_term.lower() in f.get("display_name", "").lower()]
        if matching_files:
            results["results"]["files"] = matching_files
    except Exception:
        pass
    
    # Search announcements
    try:
        announcements = await get_course_announcements(course_id, False)
        matching_announcements = [a for a in announcements if 
                                search_term.lower() in a.get("title", "").lower() or
                                (a.get("message") and search_term.lower() in a.get("message").lower())]
        if matching_announcements:
            results["results"]["announcements"] = matching_announcements
    except Exception:
        pass
    
    return results

async def search_all_courses(search_term: str):
    """Search across all courses for the specified term."""
    courses = await get_courses()
    all_results = {}
    
    for course in courses:
        course_id = course["id"]
        course_results = await search_course(course_id, search_term)
        if course_results["results"]:
            all_results[course["name"]] = course_results["results"]
    
    return all_results 