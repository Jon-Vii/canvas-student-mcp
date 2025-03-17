"""Utility tools for Canvas MCP."""
from datetime import datetime
import time
from functools import wraps
import logging
from typing import Any, Callable, Dict

# Get logger
logger = logging.getLogger(__name__)

from tools.api_client import make_canvas_request

# Cache management
cache: Dict[str, Any] = {}
cache_ttl: Dict[str, float] = {}

def cached(ttl: int = 300):
    """Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds for cached entries
        
    Returns:
        Decorated function that uses caching
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if cached and not expired
            if key in cache and time.time() < cache_ttl.get(key, 0):
                logger.debug(f"Cache hit for {key}")
                return cache[key]
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {key}, executing function")
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
        logger.error(f"Error formatting course summary: {e}")
        return {"error": str(e)} 