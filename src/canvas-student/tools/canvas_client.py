"""Canvas API client using canvasapi."""
import logging
import os
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

logger = logging.getLogger(__name__)

# Get credentials from environment (fixing variable names and default values)
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "12523~84nXE3aWP9ZQDr8Zawttf2KWFzCvevmaRB3khzML6JBUYnBAJh6BVFt6AneKWVwX")
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://chalmers.instructure.com")

# Global canvas instance
_canvas = None

def get_canvas():
    """Get or create the Canvas client instance."""
    global _canvas
    if _canvas is None:
        logger.info(f"Initializing Canvas client for {CANVAS_BASE_URL}")
        _canvas = Canvas(CANVAS_BASE_URL, CANVAS_API_TOKEN)
    return _canvas

async def check_auth():
    """Check if authentication is valid."""
    try:
        canvas = get_canvas()
        # Add debugging information
        logger.info(f"Checking authentication with URL: {CANVAS_BASE_URL} and token: {CANVAS_API_TOKEN[:5]}...")
        
        user = canvas.get_current_user()
        
        # Check if user is None before trying to access properties
        if user is None:
            logger.error("Authentication failed: get_current_user returned None")
            return {"status": "error", "message": "Failed to retrieve user information"}
        
        # Convert the user object to a dictionary with the properties we need
        user_dict = {
            "id": user.id,
            "name": user.name,
            "email": getattr(user, "email", ""),
            "login_id": getattr(user, "login_id", "")
        }
        
        return {"status": "authenticated", "user": user_dict}
    except CanvasException as e:
        logger.error(f"Canvas API authentication error: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

def get_object_data(obj):
    """
    Safely extract data from a canvasapi object.
    
    This handles the case where we need to serialize the object
    for JSON responses in the MCP tools.
    """
    # If the object is None, return None
    if obj is None:
        return None
        
    # If the object is a list, process each item
    if isinstance(obj, list):
        return [get_object_data(item) for item in obj]
        
    # If the object has __dict__, it's likely a Canvas object
    if hasattr(obj, '__dict__'):
        # Extract the internal dict but skip private attributes
        result = {}
        # Try to get all attributes that don't start with underscore
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):
                result[key] = get_object_data(value)
        return result
        
    # For primitive types, dictionaries, or other JSON-serializable items
    return obj 