"""File content extraction tools for Canvas MCP."""
import logging
import io
import re
import json
from typing import Dict, Any, Union, Optional
import requests

from canvasapi.exceptions import CanvasException, Unauthorized, ResourceDoesNotExist

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from .canvas_client import get_canvas, get_object_data

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
            "error": f"The requested resource was not found. This could be because the file doesn't exist or you don't have access to it.",
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

def _extract_text_from_pdf_preview(preview_content: str) -> str:
    """
    Extract readable text from Canvas PDF preview content.
    
    Args:
        preview_content: Raw preview content from Canvas
        
    Returns:
        str: Extracted text, cleaned up for readability
    """
    # First check if it's JSON-formatted
    try:
        # If the content is JSON, it might have the PDF content inside it
        data = json.loads(preview_content)
        if isinstance(data, dict) and "content" in data:
            preview_content = data["content"]
    except (json.JSONDecodeError, TypeError):
        # Not JSON, continue with raw content
        pass
    
    # Find potential text content in the PDF data
    extracted_text = []
    
    # Remove PDF structural elements and binary markers
    cleaned = re.sub(r'\\u[0-9a-fA-F]{4}', ' ', preview_content)  # Replace Unicode escapes
    cleaned = re.sub(r'<</[^>]+>>', '', cleaned)  # Remove PDF dictionary objects
    cleaned = re.sub(r'endobj|endstream|startxref|trailer|xref', '\n', cleaned)  # Replace PDF markers with newlines
    
    # Extract lines that have a good ratio of printable characters
    lines = cleaned.split('\\n')
    for line in lines:
        # Skip PDF header, binary data indicators and very short lines
        if line.startswith('%PDF') or len(line.strip()) < 5:
            continue
            
        # Clean up the line
        clean_line = re.sub(r'\\[^a-zA-Z0-9]', ' ', line)  # Replace escape sequences
        
        # Only keep lines with a good proportion of alphanumeric characters
        if sum(c.isalnum() or c.isspace() for c in clean_line) > len(clean_line) * 0.3:
            # Further clean up for readability
            clean_line = re.sub(r'[^\w\s.,?!;:()\-\'"]', ' ', clean_line)
            clean_line = re.sub(r'\s+', ' ', clean_line).strip()
            
            if clean_line and len(clean_line) > 10:  # Only meaningful content
                extracted_text.append(clean_line)
    
    if not extracted_text:
        return "Could not extract readable text from this PDF. Please use the source URL to view the original file."
    
    return "\n".join(extracted_text)

def get_file_content(file_id=None, file_url=None, max_length=10000):
    """
    Get file content from Canvas with Claude-optimized output formatting.
    
    Args:
        file_id: The Canvas file ID
        file_url: Direct file URL including verifier
        max_length: Maximum length of content to return
        
    Returns:
        dict: Information about the file with Claude-friendly formatting
    """
    logger.info(f"Getting file content for file ID {file_id} or URL {file_url}")
    
    if not file_id and not file_url:
        return {"error": "Either file_id or file_url must be provided", "status": "error"}
    
    try:
        canvas = get_canvas()
        # Get the underlying session for direct requests
        session = canvas._Canvas__requester._session
        
        # Get file metadata if only ID is provided
        if file_id and not file_url:
            try:
                file = canvas.get_file(file_id)
                file_url = file.url
                file_name = file.display_name
                mime_type = getattr(file, 'content-type', None)
                
                # Generate a direct preview URL
                preview_url = f"{file.url}&preview=1" if '?' in file.url else f"{file.url}?preview=1"
                
            except Exception as e:
                logger.error(f"Could not get file with ID {file_id}: {str(e)}")
                return _handle_canvas_error(e, f"access file with ID {file_id}")
        else:
            # Try to extract file name from URL
            file_name = file_url.split('/')[-1].split('?')[0]
            mime_type = None
        
        # Stream the file directly to memory
        response = session.get(file_url, stream=True)
        response.raise_for_status()
        
        # Set mime type from response headers if not already available
        if not mime_type:
            mime_type = response.headers.get('Content-Type', 'application/octet-stream')
        
        # Simplified file type handling - Claude-optimized approach
        is_pdf = 'pdf' in mime_type.lower() or file_name.lower().endswith('.pdf')
        is_text = ('text/' in mime_type.lower() or 
                   any(file_name.lower().endswith(ext) for ext in ['.txt', '.md', '.csv', '.json']))
        is_image = 'image/' in mime_type.lower()
        
        # Create Claude-friendly content formatting
        if is_text:
            # For text files, simply return the content
            try:
                text_content = response.text[:max_length]
                truncated = len(response.text) > max_length
                
                # Format nicely for Claude with metadata header
                formatted_content = (
                    f"<file name=\"{file_name}\" type=\"{mime_type}\">\n"
                    f"{text_content}\n"
                    f"</file>"
                )
                
                if truncated:
                    formatted_content += f"\n\n[Note: This file has been truncated to {max_length} characters. The original is {len(response.text)} characters long.]"
                
                return {
                    "success": True,
                    "content": formatted_content,
                    "truncated": truncated,
                    "content_length": len(response.text),
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "source": file_url,
                    "is_text": True
                }
            except Exception as content_error:
                logger.warning(f"Error extracting text content: {content_error}")
                # Fall through to the general case
        
        # For PDF files, try to give better context
        if is_pdf:
            # Try to extract some preview information if possible
            try:
                # Request the preview version
                preview_url = f"{file_url}&preview=1" if '?' in file_url else f"{file_url}?preview=1"
                preview_response = session.get(preview_url, stream=True)
                
                if preview_response.ok:
                    # Try to extract text from the preview
                    extracted_text = _extract_text_from_pdf_preview(preview_response.text)
                    if extracted_text and len(extracted_text) > 50:  # Only if we got something meaningful
                        # Format for Claude as a PDF document with extracted text
                        formatted_content = (
                            f"<PDF_DOCUMENT name=\"{file_name}\">\n"
                            f"EXTRACTED_TEXT:\n{extracted_text[:max_length]}\n\n"
                            f"[This is an extracted preview of the PDF content. For the full document, use the URL: {file_url}]\n"
                            f"</PDF_DOCUMENT>"
                        )
                        
                        return {
                            "success": True,
                            "content": formatted_content,
                            "file_name": file_name,
                            "mime_type": mime_type,
                            "source": file_url,
                            "extracted_text": True,
                            "is_pdf": True
                        }
            except Exception as pdf_error:
                logger.warning(f"Error extracting PDF preview: {pdf_error}")
            
            # If extraction failed or wasn't possible, return a helpful message
            formatted_content = (
                f"<PDF_DOCUMENT name=\"{file_name}\">\n"
                f"This is a PDF document available in Canvas.\n\n"
                f"URL: {file_url}\n\n"
                f"I cannot display the full contents directly, but I can help you with questions about this document if you've reviewed it.\n"
                f"</PDF_DOCUMENT>"
            )
            
            return {
                "success": True,
                "content": formatted_content,
                "file_name": file_name,
                "mime_type": mime_type,
                "source": file_url,
                "is_pdf": True
            }
        
        # For images, provide a descriptive message
        if is_image:
            formatted_content = (
                f"<IMAGE name=\"{file_name}\" type=\"{mime_type}\">\n"
                f"[This is an image file available in Canvas.]\n\n"
                f"URL: {file_url}\n\n"
                f"I cannot display this image directly, but you can view it by following the URL above.\n"
                f"</IMAGE>"
            )
            
            return {
                "success": True,
                "content": formatted_content,
                "file_name": file_name,
                "mime_type": mime_type,
                "source": file_url,
                "is_image": True
            }
        
        # For other file types, provide a general message
        formatted_content = (
            f"<FILE name=\"{file_name}\" type=\"{mime_type}\">\n"
            f"This file is available in Canvas, but I cannot display its contents directly.\n\n"
            f"URL: {file_url}\n\n"
            f"You can download or view this file by following the URL above.\n"
            f"</FILE>"
        )
        
        return {
            "success": True,
            "content": formatted_content,
            "file_name": file_name,
            "mime_type": mime_type,
            "source": file_url
        }
        
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return _handle_canvas_error(e, f"extract content from file") 