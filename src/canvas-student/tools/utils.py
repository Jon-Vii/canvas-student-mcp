"""Utility tools for Canvas MCP."""
from datetime import datetime
import time
from functools import wraps

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.api_client import make_canvas_request

# Cache management
cache = {}
cache_ttl = {}

def cached(ttl=300):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if cached and not expired
            if key in cache and time.time() < cache_ttl.get(key, 0):
                return cache[key]
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[key] = result
            cache_ttl[key] = time.time() + ttl
            return result
        return wrapper
    return decorator

async def clear_cache():
    """Clear the API response cache."""
    cache.clear()
    cache_ttl.clear()
    return {"status": "success", "message": "Cache cleared"}

async def format_course_summary(course_id: int):
    """Generate a comprehensive summary of a course with assignments, modules, etc."""
    try:
        # Get basic course info
        course = await make_canvas_request(f"courses/{course_id}", params={"include[]": ["term", "total_students"]})
            
        # Get assignments
        assignments = await make_canvas_request(f"courses/{course_id}/assignments")
        
        # Get modules
        modules = await make_canvas_request(f"courses/{course_id}/modules")
            
        # Format summary
        now = datetime.now()
        upcoming_assignments = 0
        
        for a in assignments:
            if a.get("due_at") and datetime.fromisoformat(a["due_at"].replace("Z", "+00:00")) > now:
                upcoming_assignments += 1
                
        summary = {
            "course_name": course["name"],
            "code": course.get("course_code"),
            "term": course.get("term", {}).get("name") if "term" in course else None,
            "students": course.get("total_students"),
            "assignments": {
                "total": len(assignments),
                "upcoming": upcoming_assignments
            },
            "modules": len(modules)
        }
        
        return summary
    except Exception as e:
        return {"error": str(e)}

async def search_all_course_content(search_term: str):
    """Search across all courses for content matching the search term."""
    # Get all courses
    courses = await make_canvas_request("courses", params={"enrollment_state": "active"})
    results = {}
    
    for course in courses:
        course_id = course["id"]
        
        # Search assignments
        try:
            assignments = await make_canvas_request(f"courses/{course_id}/assignments")
            matching_assignments = [a for a in assignments if 
                                   search_term.lower() in a.get("name", "").lower() or 
                                   (a.get("description") and search_term.lower() in a.get("description").lower())]
            if matching_assignments:
                if course["name"] not in results:
                    results[course["name"]] = {}
                results[course["name"]]["assignments"] = matching_assignments
        except Exception:
            pass
            
        # Additional searches could be added for announcements, pages, discussions, etc.
            
    return results 