"""Search-related tools for Canvas MCP."""
import logging
from typing import Dict, List, Any, Union
from canvasapi.exceptions import CanvasException

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached
from tools.canvas_client import get_canvas, get_object_data
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
        
        # Handle error case
        if isinstance(assignments, dict) and "error" in assignments:
            logger.error(f"Error getting assignments for search: {assignments['error']}")
        else:
            matching_assignments = []
            for a in assignments:
                # Get name and description safely regardless of type
                if isinstance(a, dict):
                    name = a.get("name", "").lower()
                    description = a.get("description", "")
                else:
                    name = getattr(a, "name", "").lower()
                    description = getattr(a, "description", "")
                
                # Convert description to string and lowercase
                description = str(description).lower() if description else ""
                
                # Check for matches
                if search_term.lower() in name or search_term.lower() in description:
                    # Convert to dict if needed
                    matching_assignments.append(a if isinstance(a, dict) else get_object_data(a))
                    
            if matching_assignments:
                results["results"]["assignments"] = matching_assignments
                logger.info(f"Found {len(matching_assignments)} matching assignments")
    except Exception as e:
        logger.error(f"Error searching assignments: {e}")
    
    # Search pages
    try:
        pages = await get_course_pages(course_id)
        
        # Handle error case
        if isinstance(pages, dict) and "error" in pages:
            logger.error(f"Error getting pages for search: {pages['error']}")
        else:
            matching_pages = []
            for p in pages:
                # Get title and body safely regardless of type
                if isinstance(p, dict):
                    title = p.get("title", "").lower()
                    body = p.get("body", "")
                else:
                    title = getattr(p, "title", "").lower()
                    body = getattr(p, "body", "")
                
                # Convert body to string and lowercase
                body = str(body).lower() if body else ""
                
                # Check for matches
                if search_term.lower() in title or search_term.lower() in body:
                    # Convert to dict if needed
                    matching_pages.append(p if isinstance(p, dict) else get_object_data(p))
                    
            if matching_pages:
                results["results"]["pages"] = matching_pages
                logger.info(f"Found {len(matching_pages)} matching pages")
    except Exception as e:
        logger.error(f"Error searching pages: {e}")
    
    # Search files
    try:
        files = await get_course_files(course_id)
        
        # Handle error case
        if isinstance(files, dict) and "error" in files:
            logger.error(f"Error getting files for search: {files['error']}")
        else:
            matching_files = []
            for f in files:
                # Get display_name safely regardless of type
                if isinstance(f, dict):
                    display_name = f.get("display_name", "").lower()
                else:
                    display_name = getattr(f, "display_name", "").lower()
                
                # Check for matches
                if search_term.lower() in display_name:
                    # Convert to dict if needed
                    matching_files.append(f if isinstance(f, dict) else get_object_data(f))
                    
            if matching_files:
                results["results"]["files"] = matching_files
                logger.info(f"Found {len(matching_files)} matching files")
    except Exception as e:
        logger.error(f"Error searching files: {e}")
    
    # Search announcements
    try:
        announcements = await get_course_announcements(course_id, False)
        
        # Handle error case
        if isinstance(announcements, dict) and "error" in announcements:
            logger.error(f"Error getting announcements for search: {announcements['error']}")
        else:
            matching_announcements = []
            for a in announcements:
                # Get title and message safely regardless of type
                if isinstance(a, dict):
                    title = a.get("title", "").lower()
                    message = a.get("message", "")
                else:
                    title = getattr(a, "title", "").lower()
                    message = getattr(a, "message", "")
                
                # Convert message to string and lowercase
                message = str(message).lower() if message else ""
                
                # Check for matches
                if search_term.lower() in title or search_term.lower() in message:
                    # Convert to dict if needed
                    matching_announcements.append(a if isinstance(a, dict) else get_object_data(a))
                    
            if matching_announcements:
                results["results"]["announcements"] = matching_announcements
                logger.info(f"Found {len(matching_announcements)} matching announcements")
    except Exception as e:
        logger.error(f"Error searching announcements: {e}")
    
    return results

async def search_all_courses(search_term: str) -> Dict[str, Dict[str, Any]]:
    """Search across all courses for the specified term."""
    logger.info(f"Searching all courses for '{search_term}'")
    try:
        courses = await get_courses()
        
        # Handle error case
        if isinstance(courses, dict) and "error" in courses:
            logger.error(f"Error getting courses for search: {courses['error']}")
            return {"error": courses["error"], "status": courses.get("status", "error")}
        
        all_results = {}
        
        for course in courses:
            # Get course id and name safely regardless of type
            if isinstance(course, dict):
                course_id = course["id"]
                course_name = course["name"]
            else:
                course_id = course.id
                course_name = course.name
                
            course_results = await search_course(course_id, search_term)
            if course_results["results"]:
                all_results[course_name] = course_results["results"]
        
        logger.info(f"Found matches in {len(all_results)} courses")
        return all_results
    except Exception as e:
        logger.error(f"Error searching all courses: {e}")
        return {"error": str(e), "status": "error"} 