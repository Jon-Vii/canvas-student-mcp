"""Content-related tools for Canvas MCP."""
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
from canvasapi.exceptions import CanvasException, Unauthorized, ResourceDoesNotExist

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached
from tools.canvas_client import get_canvas, get_object_data

def _handle_canvas_error(e: Exception, action: str) -> Dict[str, Any]:
    """Helper function to provide better error messages for Canvas API errors.
    
    Args:
        e: The exception that was raised
        action: Description of what was being attempted
        
    Returns:
        A dictionary with error information
    """
    if isinstance(e, Unauthorized):
        # This is specifically a permissions issue
        return {
            "error": f"You don't have permission to {action}. This might be because you are a student and this action requires instructor privileges.",
            "status": "unauthorized",
            "original_error": str(e)
        }
    elif isinstance(e, ResourceDoesNotExist):
        return {
            "error": f"The requested resource was not found. This could be because the course doesn't exist or you don't have access to it.",
            "status": "not_found",
            "original_error": str(e)
        }
    elif isinstance(e, CanvasException):
        return {
            "error": str(e),
            "status": "canvas_error",
            "original_error": str(e)
        }
    else:
        return {
            "error": f"Unexpected error while {action}: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        }

@cached()
async def get_course_files(course_id: int) -> List[Dict[str, Any]]:
    """Get all files for a specific course that the student can access.
    
    This comprehensive approach examines multiple Canvas locations where files might be:
    1. Files referenced in modules
    2. Files in course folders (if accessible)
    3. Files embedded in assignment descriptions
    4. Files embedded in course pages
    5. Files in announcements
    """
    logger.info(f"Fetching files for course {course_id}")
    all_files = []
    file_ids = set()  # Track discovered file IDs to avoid duplicates
    
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        
        # Method 1: Get files through modules (often works for students)
        try:
            logger.info("Attempting to get files via course modules")
            modules = list(course.get_modules())
            
            for module in modules:
                module_items = list(module.get_module_items())
                for item in module_items:
                    # Find file type items
                    if item.type == 'File':
                        try:
                            file_id = item.content_id
                            if file_id not in file_ids:
                                file_ids.add(file_id)
                                file = course.get_file(file_id)
                                all_files.append(file)
                        except Exception as file_err:
                            logger.warning(f"Could not retrieve file {item.title}: {file_err}")
        except Exception as e:
            logger.warning(f"Module-based file access failed: {e}")
            
        # Method 2: Get files through folders (sometimes works for students)
        try:
            logger.info("Attempting to get files via course folders")
            folders = list(course.get_folders())
            
            for folder in folders:
                try:
                    folder_files = list(folder.get_files())
                    for file in folder_files:
                        if file.id not in file_ids:
                            file_ids.add(file.id)
                            all_files.append(file)
                except Exception as folder_err:
                    logger.warning(f"Error getting files from folder {folder.name}: {folder_err}")
        except Exception as e:
            logger.warning(f"Folder-based file access failed: {e}")
        
        # Method 3: Extract file links from assignments
        try:
            logger.info("Extracting file links from assignments")
            assignments = list(course.get_assignments())
            file_ids_from_html = await extract_file_ids_from_html(course_id, 
                                                                [a.description for a in assignments if hasattr(a, 'description') and a.description])
            
            for file_id in file_ids_from_html:
                if file_id not in file_ids:
                    try:
                        file_ids.add(file_id)
                        file = course.get_file(file_id)
                        all_files.append(file)
                    except Exception as file_err:
                        logger.warning(f"Could not retrieve file {file_id} from assignment: {file_err}")
        except Exception as e:
            logger.warning(f"Assignment-based file extraction failed: {e}")
        
        # Method 4: Extract file links from pages
        try:
            logger.info("Extracting file links from pages")
            pages = list(course.get_pages())
            page_bodies = []
            
            for page in pages:
                try:
                    # Need to get the full page to access body content
                    full_page = course.get_page(page.url)
                    if hasattr(full_page, 'body') and full_page.body:
                        page_bodies.append(full_page.body)
                except Exception as page_err:
                    logger.warning(f"Error getting page content: {page_err}")
            
            file_ids_from_pages = await extract_file_ids_from_html(course_id, page_bodies)
            
            for file_id in file_ids_from_pages:
                if file_id not in file_ids:
                    try:
                        file_ids.add(file_id)
                        file = course.get_file(file_id)
                        all_files.append(file)
                    except Exception as file_err:
                        logger.warning(f"Could not retrieve file {file_id} from page: {file_err}")
        except Exception as e:
            logger.warning(f"Page-based file extraction failed: {e}")
            
        # If we got here with empty all_files, we couldn't retrieve any files
        if not all_files:
            logger.error("Could not retrieve any files using available methods")
            return {
                "error": "No accessible files found for this course. This may be because you don't have permission or there are no files available.",
                "status": "not_found"
            }
            
        return [get_object_data(file) for file in all_files]
    except Unauthorized as e:
        logger.error(f"Unauthorized access to course {course_id}: {e}")
        return _handle_canvas_error(e, f"access files for course {course_id}")
    except ResourceDoesNotExist as e:
        logger.error(f"Course {course_id} not found: {e}")
        return _handle_canvas_error(e, f"find course {course_id}")
    except CanvasException as e:
        logger.error(f"Canvas API error fetching files for course {course_id}: {e}")
        return _handle_canvas_error(e, f"get files for course {course_id}")
    except Exception as e:
        logger.error(f"Unexpected error fetching files: {e}")
        return _handle_canvas_error(e, f"retrieve files for course {course_id}")

async def extract_file_ids_from_html(course_id: int, html_contents: List[str]) -> List[int]:
    """
    Extract file IDs from HTML content by looking for Canvas file URLs.
    
    Args:
        course_id: The Canvas course ID 
        html_contents: List of HTML strings to parse
    
    Returns:
        List of file IDs extracted from the HTML
    """
    import re
    file_ids = []
    
    # Pattern to match Canvas file URLs like:
    # https://chalmers.instructure.com/courses/27849/files/3025924
    pattern = rf'https?://[^/]+/courses/{course_id}/files/(\d+)'
    
    for html in html_contents:
        if not html:
            continue
            
        # Find all matches in the current HTML content
        matches = re.findall(pattern, html)
        for match in matches:
            try:
                file_id = int(match)
                file_ids.append(file_id)
            except ValueError:
                logger.warning(f"Invalid file ID extracted: {match}")
    
    return file_ids

@cached()
async def get_course_modules(course_id: int) -> List[Dict[str, Any]]:
    """Get all modules for a specific course."""
    logger.info(f"Fetching modules for course {course_id}")
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        modules = list(course.get_modules())
        return [get_object_data(module) for module in modules]
    except Unauthorized as e:
        logger.error(f"Unauthorized access to course modules {course_id}: {e}")
        return _handle_canvas_error(e, f"access modules for course {course_id}")
    except ResourceDoesNotExist as e:
        logger.error(f"Course {course_id} not found: {e}")
        return _handle_canvas_error(e, f"find course {course_id}")
    except CanvasException as e:
        logger.error(f"Canvas API error fetching modules for course {course_id}: {e}")
        return _handle_canvas_error(e, f"get modules for course {course_id}")
    except Exception as e:
        logger.error(f"Unexpected error fetching modules: {e}")
        return _handle_canvas_error(e, f"retrieve modules for course {course_id}")

@cached()
async def get_module_items(course_id: int, module_id: int) -> List[Dict[str, Any]]:
    """Get all items in a specific module."""
    logger.info(f"Fetching items for module {module_id} in course {course_id}")
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        module = course.get_module(module_id)
        items = list(module.get_module_items())
        return [get_object_data(item) for item in items]
    except Unauthorized as e:
        logger.error(f"Unauthorized access to module items for course {course_id}, module {module_id}: {e}")
        return _handle_canvas_error(e, f"access items in module {module_id}")
    except ResourceDoesNotExist as e:
        logger.error(f"Module {module_id} or course {course_id} not found: {e}")
        return _handle_canvas_error(e, f"find module {module_id} in course {course_id}")
    except CanvasException as e:
        logger.error(f"Canvas API error fetching module items for course {course_id}, module {module_id}: {e}")
        return _handle_canvas_error(e, f"get items for module {module_id}")
    except Exception as e:
        logger.error(f"Unexpected error fetching module items: {e}")
        return _handle_canvas_error(e, f"retrieve items from module {module_id}")

@cached()
async def get_course_pages(course_id: int) -> List[Dict[str, Any]]:
    """Get all pages for a specific course."""
    logger.info(f"Fetching pages for course {course_id}")
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        pages = list(course.get_pages())
        return [get_object_data(page) for page in pages]
    except Unauthorized as e:
        logger.error(f"Unauthorized access to course pages {course_id}: {e}")
        return _handle_canvas_error(e, f"access pages for course {course_id}")
    except ResourceDoesNotExist as e:
        logger.error(f"Course {course_id} not found: {e}")
        return _handle_canvas_error(e, f"find course {course_id}")
    except CanvasException as e:
        logger.error(f"Canvas API error fetching pages for course {course_id}: {e}")
        return _handle_canvas_error(e, f"get pages for course {course_id}")
    except Exception as e:
        logger.error(f"Unexpected error fetching pages: {e}")
        return _handle_canvas_error(e, f"retrieve pages for course {course_id}")

@cached()
async def get_course_announcements(course_id: int, recent_only: bool = True) -> List[Dict[str, Any]]:
    """Get announcements for a specific course."""
    logger.info(f"Fetching announcements for course {course_id}, recent_only={recent_only}")
    
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        
        params = {}
        if recent_only:
            # Get announcements from the last 14 days
            start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
            params = {"start_date": start_date}
        
        # Get announcements and convert them to dictionaries
        announcements = list(course.get_discussion_topics(only_announcements=True, **params))
        return [get_object_data(announcement) for announcement in announcements]
    except Unauthorized as e:
        logger.error(f"Unauthorized access to course announcements {course_id}: {e}")
        return _handle_canvas_error(e, f"access announcements for course {course_id}")
    except ResourceDoesNotExist as e:
        logger.error(f"Course {course_id} not found: {e}")
        return _handle_canvas_error(e, f"find course {course_id}")
    except CanvasException as e:
        logger.error(f"Canvas API error fetching announcements for course {course_id}: {e}")
        return _handle_canvas_error(e, f"get announcements for course {course_id}")
    except Exception as e:
        logger.error(f"Unexpected error fetching announcements: {e}")
        return _handle_canvas_error(e, f"retrieve announcements for course {course_id}")

async def get_files_from_content(course_id: int) -> List[Dict[str, Any]]:
    """
    Find all files embedded in course content (assignments, pages, announcements).
    This is particularly useful for students who can access files through content
    but not directly.
    """
    logger.info(f"Scanning course {course_id} content for embedded files")
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        all_file_ids = set()
        all_files = []
        
        # Scan assignments
        assignments = list(course.get_assignments())
        assignment_html = [a.description for a in assignments if hasattr(a, 'description') and a.description]
        
        # Scan pages
        pages = list(course.get_pages())
        page_html = []
        for page in pages:
            try:
                full_page = course.get_page(page.url)
                if hasattr(full_page, 'body') and full_page.body:
                    page_html.append(full_page.body)
            except Exception as e:
                logger.warning(f"Error getting page content: {e}")
        
        # Scan announcements
        announcements = list(course.get_discussion_topics(only_announcements=True))
        announcement_html = [a.message for a in announcements if hasattr(a, 'message') and a.message]
        
        # Combine all HTML content
        all_html = assignment_html + page_html + announcement_html
        
        # Extract file IDs
        file_ids = await extract_file_ids_from_html(course_id, all_html)
        
        # Retrieve files
        for file_id in file_ids:
            if file_id not in all_file_ids:
                try:
                    all_file_ids.add(file_id)
                    file = course.get_file(file_id)
                    all_files.append(file)
                except Exception as e:
                    logger.warning(f"Could not retrieve file {file_id}: {e}")
        
        return [get_object_data(file) for file in all_files]
    except Exception as e:
        logger.error(f"Error scanning course content for files: {e}")
        return {"error": str(e), "status": "error"} 