"""Course-related tools for Canvas MCP."""
import logging
from canvasapi.exceptions import CanvasException, Unauthorized, ResourceDoesNotExist
from typing import List, Dict, Any, Union, Optional

# Get logger from __init__.py
logger = logging.getLogger(__name__)

# Import from utils and canvas client
from tools.utils import cached, format_for_claude
from tools.canvas_client import get_canvas, get_object_data

@cached()
async def get_courses():
    """Retrieve all courses the user is enrolled in."""
    logger.info("Fetching user courses")
    
    try:
        canvas = get_canvas()
        courses = list(canvas.get_courses(enrollment_state='active'))
        
        # Convert to dictionary for JSON serialization
        course_data = [get_object_data(course) for course in courses]
        
        logger.info(f"Successfully retrieved {len(course_data)} courses")
        return course_data
    except CanvasException as e:
        logger.error(f"Error retrieving courses: {e}")
        return {"error": str(e), "status": "error"}
    except Exception as e:
        logger.error(f"Unexpected error retrieving courses: {e}")
        return {"error": str(e), "status": "unknown_error"}

# DEPRECATED: Use get_courses instead and filter the results client-side
async def find_course_by_name(course_name: str):
    """
    DEPRECATED: Find a course by name or partial name match.
    
    This function is deprecated and will be removed in a future version.
    Use get_courses() instead and filter the results client-side.
    """
    logger.warning("find_course_by_name is deprecated. Use get_courses instead and filter results client-side.")
    try:
        courses = await get_courses()
        
        # If we got an error response from get_courses
        if isinstance(courses, dict) and "error" in courses:
            return courses
        
        matches = []
        for course in courses:
            # Access name using dictionary syntax or object attribute depending on what's available
            course_name_value = course.get("name") if isinstance(course, dict) else getattr(course, "name", "")
            if course_name.lower() in course_name_value.lower():
                # Convert to dictionary if it's not already
                matches.append(course if isinstance(course, dict) else get_object_data(course))
        
        if not matches:
            return {"matches": [], "message": f"No courses found matching '{course_name}'", "deprecated": True}
        
        return {"matches": matches, "deprecated": True, "message": "This tool is deprecated. Use get_courses instead."}
    except Exception as e:
        logger.error(f"Error finding course: {e}")
        return {"error": str(e), "status": "error"}

@cached()
async def get_course_details(course_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific course.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        dict: Detailed course information
    """
    logger.info(f"Getting details for course ID {course_id}")
    
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        
        # Get course details
        course_data = get_object_data(course)
        
        # Get teacher information
        teachers = []
        try:
            for teacher in course.get_users(enrollment_type=['teacher']):
                teachers.append({
                    'id': teacher.id,
                    'name': teacher.name
                })
        except Exception as e:
            logger.warning(f"Could not get teachers for course {course_id}: {e}")
            teachers = [{'name': 'Unable to retrieve teacher information'}]
        
        # Format for Claude
        course_info = {
            **course_data,
            'teachers': teachers
        }
        
        # Create a summary of the course
        summary = f"Course {course_data.get('name')} (ID: {course_id})"
        
        # Create Claude-friendly formatted output
        formatted_output = format_for_claude(
            data=course_info,
            type_name="COURSE_DETAILS",
            title=course_data.get('name'),
            summary=summary,
            items=None
        )
        
        return {
            "success": True,
            "course": course_data,
            "teachers": teachers,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving course {course_id}: {e}")
        if isinstance(e, Unauthorized):
            return {
                "error": f"You don't have permission to access this course. This might be because you are not enrolled in it.",
                "status": "unauthorized",
                "original_error": str(e)
            }
        elif isinstance(e, ResourceDoesNotExist):
            return {
                "error": f"Course with ID {course_id} not found. It might have been deleted or you might not have access to it.",
                "status": "not_found",
                "original_error": str(e)
            }
        else:
            return {
                "error": str(e),
                "status": "canvas_error",
                "original_error": str(e)
            }
    except Exception as e:
        logger.error(f"Unexpected error retrieving course {course_id}: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        } 