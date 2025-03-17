"""Course-related tools for Canvas MCP."""
import time
import httpx
from functools import wraps

# Import from parent directory - adjust as needed
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canvas_student import CANVAS_API_TOKEN, CANVAS_BASE_URL, cache, cache_ttl

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

async def make_canvas_request(endpoint, method="GET", params=None, data=None):
    """Make a request to the Canvas API."""
    url = f"{CANVAS_BASE_URL}/api/v1/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {CANVAS_API_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data
        )
        response.raise_for_status()
        return response.json()

@cached()
async def get_courses():
    """Retrieve all courses the user is enrolled in."""
    return await make_canvas_request(
        "courses",
        params={"enrollment_state": "active"}
    )

async def find_course_by_name(course_name: str):
    """Find a course by name or partial name match."""
    courses = await get_courses()
    matches = []
    for course in courses:
        if "name" in course and course_name.lower() in course["name"].lower():
            matches.append(course)
    return matches

@cached()
async def get_course_details(course_id: int):
    """Get detailed information about a course."""
    return await make_canvas_request(
        f"courses/{course_id}",
        params={"include[]": ["term", "total_students"]}
    ) 