"""API client functions for Canvas interactions."""
import httpx
import os
import logging
from typing import Dict, Any, Optional, Union, List

# Get logger from __init__.py
logger = logging.getLogger(__name__)

# Import canvas_student module
from canvas_student import CANVAS_API_TOKEN, CANVAS_BASE_URL

async def make_canvas_request(
    endpoint: str, 
    method: str = "GET", 
    params: Optional[Dict[str, Any]] = None, 
    data: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Make a request to the Canvas API.
    
    Args:
        endpoint: The API endpoint (without the /api/v1 prefix)
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        data: JSON body data
        
    Returns:
        The response as JSON, or an error dict
    """
    url = f"{CANVAS_BASE_URL}/api/v1/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {CANVAS_API_TOKEN}"}
    
    logger.info(f"Making {method} request to {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data
            )
            
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            # Handle different response statuses
            if response.status_code == 401:
                logger.error("Authentication failed: Invalid API token or insufficient permissions")
                return {"error": "Authentication failed", "status": 401}
            elif response.status_code == 404:
                logger.error(f"Resource not found: {url}")
                return {"error": "Resource not found", "status": 404}
                
            # For successful responses
            response.raise_for_status()
            
            # Return empty list instead of empty dict for certain endpoints
            json_response = response.json()
            if json_response == {} and endpoint == "courses":
                logger.info("No courses found, returning empty list")
                return []
                
            return json_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            return {"error": str(e), "status": e.response.status_code}
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            return {"error": str(e), "status": "connection_error"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e), "status": "unknown_error"} 