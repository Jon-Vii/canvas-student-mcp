"""Course-related tools for Canvas MCP."""
import time
import logging

# Get logger from __init__.py
logger = logging.getLogger(__name__)

# Import cache from utils and API client functions
from tools.utils import cached
from tools.api_client import make_canvas_request

@cached()
async def get_courses():
    """Retrieve all courses the user is enrolled in."""
    logger.info("Fetching user courses")
    
    result = await make_canvas_request(
        "courses",
        params={"enrollment_state": "active"}
    )
    
    # Check if the result is an error
    if isinstance(result, dict) and "error" in result:
        logger.error(f"Error retrieving courses: {result}")
        return {"error": result["error"], "status": result.get("status")}
    
    # Check if we got an empty list
    if result == []:
        logger.info("No active courses found")
        return {"courses": [], "message": "No active courses found"}
    
    # For successful responses with courses
    logger.info(f"Successfully retrieved {len(result)} courses")
    return result

async def find_course_by_name(course_name: str):
    """Find a course by name or partial name match."""
    courses = await get_courses()
    
    # Handle error responses from get_courses
    if isinstance(courses, dict) and "error" in courses:
        return courses
    
    # Check if courses is a dict with 'courses' key (our custom empty result)
    if isinstance(courses, dict) and "courses" in courses:
        courses = courses["courses"]
    
    matches = []
    for course in courses:
        if "name" in course and course_name.lower() in course["name"].lower():
            matches.append(course)
    
    if not matches:
        return {"matches": [], "message": f"No courses found matching '{course_name}'"}
    
    return matches

@cached()
async def get_course_details(course_id: int):
    """Get detailed information about a course."""
    logger.info(f"Fetching details for course ID: {course_id}")
    
    result = await make_canvas_request(
        f"courses/{course_id}",
        params={"include[]": ["term", "total_students"]}
    )
    
    # Check if the result is an error
    if isinstance(result, dict) and "error" in result:
        logger.error(f"Error retrieving course details: {result}")
        return {"error": result["error"], "status": result.get("status")}
    
    return result 