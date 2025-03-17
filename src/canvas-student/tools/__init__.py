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
from . import canvas_client, courses, assignments, content, search, utils, file_content, todos, quizzes

# For backward compatibility - avoid importing directly
from .courses import get_courses, find_course_by_name, get_course_details
from .assignments import get_course_assignments, find_exams_in_course, get_upcoming_deadlines
from .content import get_course_files, get_course_modules, get_module_items, get_course_pages, get_course_announcements, get_files_from_content
from .search import search_course, search_all_courses
from .utils import format_course_summary, clear_cache
from .canvas_client import check_auth
from .file_content import get_file_content
from .todos import get_todo_items, get_upcoming_todo_items
from .quizzes import get_course_quizzes, get_all_quizzes, get_quiz_details 