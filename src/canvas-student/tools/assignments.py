"""Assignment-related tools for Canvas MCP."""
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Union

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached
from tools.api_client import make_canvas_request

@cached()
async def get_course_assignments(course_id: int) -> List[Dict[str, Any]]:
    """Get all assignments for a specific course."""
    return await make_canvas_request(f"courses/{course_id}/assignments")

async def find_exams_in_course(course_id: int) -> List[Dict[str, Any]]:
    """Find assignments that are likely exams in a course."""
    assignments = await get_course_assignments(course_id)
    
    # Look for assignments with exam-related keywords
    exam_keywords = ["exam", "test", "quiz", "midterm", "final", "assessment"]
    exams = []
    
    for assignment in assignments:
        # Check if any exam keywords are in the name or description
        is_exam = False
        if "name" in assignment:
            if any(keyword in assignment["name"].lower() for keyword in exam_keywords):
                is_exam = True
        
        if "description" in assignment and assignment["description"]:
            if any(keyword in assignment["description"].lower() for keyword in exam_keywords):
                is_exam = True
                
        if is_exam:
            exams.append(assignment)
            
    return exams

async def get_upcoming_deadlines(days: int = 7) -> List[Dict[str, Any]]:
    """Get all assignments due in the next X days across all courses."""
    from tools.courses import get_courses
    
    courses = await get_courses()
    upcoming = []
    now = datetime.now()
    future = now + timedelta(days=days)
    
    for course in courses:
        course_id = course["id"]
        try:
            assignments = await get_course_assignments(course_id)
            for assignment in assignments:
                if assignment.get("due_at"):
                    due_date = datetime.fromisoformat(assignment["due_at"].replace("Z", "+00:00"))
                    if now <= due_date <= future:
                        upcoming.append({
                            "course_name": course["name"],
                            "assignment_name": assignment["name"],
                            "due_date": assignment["due_at"],
                            "points_possible": assignment.get("points_possible")
                        })
        except Exception as e:
            logger.error(f"Error processing assignments for course {course_id}: {e}")
            pass
            
    return sorted(upcoming, key=lambda x: x["due_date"]) 