"""Canvas MCP tools collection."""
# Add parent directory to path so we can import from canvas_student module
import sys
import os
import logging

# Configure logging once for all tools
logging.basicConfig(level=logging.INFO)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all tools to make them available through the package
from . import api_client, courses, assignments, content, search, utils 