"""Utility tools for Canvas MCP."""
from datetime import datetime
import time
from functools import wraps
import logging
from typing import Any, Callable, Dict
from canvasapi.exceptions import CanvasException

# Get logger
logger = logging.getLogger(__name__)

from tools.canvas_client import get_canvas, get_object_data

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
        canvas = get_canvas()
        course = canvas.get_course(course_id, include=["term", "total_students"])
        course_data = get_object_data(course)
        
        # Get assignments using canvasapi
        assignments = list(course.get_assignments())
        assignments_data = [get_object_data(a) for a in assignments]
        
        # Get modules using canvasapi
        modules = list(course.get_modules())
        
        # Format summary
        now = datetime.now()
        upcoming_assignments = 0
        
        for a in assignments_data:
            due_at = a.get("due_at")
            if due_at and due_at:
                try:
                    due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
                    if due_date > now:
                        upcoming_assignments += 1
                except (ValueError, TypeError):
                    pass
                
        # Get course properties safely
        course_name = course_data.get("name", "Unknown Course")
        course_code = course_data.get("course_code")
        
        # Get term information 
        if isinstance(course_data.get("term"), dict):
            term_name = course_data.get("term", {}).get("name")
        else:
            term_name = None
            
        students = course_data.get("total_students")
        
        summary = {
            "course_name": course_name,
            "code": course_code,
            "term": term_name,
            "students": students,
            "assignments": {
                "total": len(assignments_data),
                "upcoming": upcoming_assignments
            },
            "modules": len(modules)
        }
        
        return summary
    except CanvasException as e:
        logger.error(f"Canvas API error formatting course summary: {e}")
        return {"error": str(e), "status": "error"}
    except Exception as e:
        logger.error(f"Error formatting course summary: {e}")
        return {"error": str(e), "status": "unknown_error"}

def format_for_claude(data, type_name, title=None, summary=None, items=None):
    """
    Format data in a Claude-friendly way for better understanding and parsing.
    
    Args:
        data: The data to format (could be a dict, list, or other structure)
        type_name: Type of the data (e.g., 'COURSE', 'ASSIGNMENT', 'MODULE')
        title: Optional title for the data
        summary: Optional summary of the data
        items: Optional list of items (for collections)
        
    Returns:
        str: Claude-friendly formatted string
    """
    output = [f"<{type_name}>"]
    
    # Add title if provided
    if title:
        output.append(f"TITLE: {title}")
    
    # Add summary if provided 
    if summary:
        output.append(f"SUMMARY: {summary}")
    
    # Add items if provided
    if items:
        output.append("\nITEMS:")
        for i, item in enumerate(items, 1):
            if isinstance(item, dict) and 'name' in item:
                item_line = f"{i}. {item['name']}"
                if 'due_at' in item and item['due_at']:
                    item_line += f" (Due: {item['due_at']})"
                output.append(item_line)
            elif isinstance(item, str):
                output.append(f"{i}. {item}")
    
    # Add main data in a structured way
    if isinstance(data, dict):
        output.append("\nDETAILS:")
        # Format dictionary for readability
        for key, value in data.items():
            # Skip complex nested structures
            if isinstance(value, (dict, list)) and key not in ['name', 'title', 'id']:
                continue
            output.append(f"- {key}: {value}")
    
    output.append(f"</{type_name}>\n")
    
    return "\n".join(output) 