"""Assignment-related tools for Canvas MCP."""
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Union, Optional
from canvasapi.exceptions import CanvasException

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached, format_for_claude
from tools.canvas_client import get_canvas, get_object_data

@cached()
async def get_course_assignments(course_id: int) -> List[Dict[str, Any]]:
    """Get all assignments for a specific course."""
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        assignments = list(course.get_assignments())
        return [get_object_data(assignment) for assignment in assignments]
    except CanvasException as e:
        logger.error(f"Error getting assignments for course {course_id}: {e}")
        return {"error": str(e), "status": "error"}
    except Exception as e:
        logger.error(f"Unexpected error retrieving assignments: {e}")
        return {"error": str(e), "status": "unknown_error"}

async def find_exams_in_course(course_id: int) -> List[Dict[str, Any]]:
    """Find assignments that are likely exams in a course."""
    try:
        assignments = await get_course_assignments(course_id)
        
        # Handle error case
        if isinstance(assignments, dict) and "error" in assignments:
            return assignments
            
        exam_keywords = ["exam", "test", "quiz", "midterm", "final", "assessment"]
        exams = []
        
        for assignment in assignments:
            # Check if any exam keywords are in the name or description
            is_exam = False
            
            # Safely get name and description accounting for both dict and object
            if isinstance(assignment, dict):
                name = assignment.get("name", "").lower()
                description = assignment.get("description", "") or ""
            else:
                name = getattr(assignment, "name", "").lower()
                description = getattr(assignment, "description", "") or ""
                
            description = description.lower()
            
            if any(keyword in name for keyword in exam_keywords) or any(keyword in description for keyword in exam_keywords):
                if not isinstance(assignment, dict):
                    assignment = get_object_data(assignment)
                exams.append(assignment)
                
        return exams
    except Exception as e:
        logger.error(f"Error finding exams in course {course_id}: {e}")
        return {"error": str(e), "status": "error"}

@cached()
async def get_upcoming_deadlines(days: int = 7, include_past_due: bool = True) -> Dict[str, Any]:
    """
    Get upcoming assignment deadlines across all courses.
    
    Args:
        days: Number of days to look ahead (default: 7)
        include_past_due: Whether to include past due assignments (default: True)
        
    Returns:
        dict: List of upcoming deadlines grouped by course
    """
    logger.info(f"Getting upcoming deadlines for next {days} days (include_past_due={include_past_due})")
    
    try:
        canvas = get_canvas()
        courses = list(canvas.get_courses(enrollment_state='active'))
        
        now = datetime.now()
        cutoff_date = now + timedelta(days=days)
        
        # For past due items, look back up to 30 days
        past_due_cutoff = now - timedelta(days=30) if include_past_due else now
        
        upcoming_deadlines = []
        course_map = {}
        
        for course in courses:
            course_map[course.id] = {
                'id': course.id,
                'name': course.name
            }
            try:
                assignments = course.get_assignments()
                for assignment in assignments:
                    # Skip assignments without due dates
                    if not assignment.due_at:
                        continue
                    
                    # Parse the due date
                    due_date = datetime.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                    
                    # Include if it's in our time window
                    if past_due_cutoff <= due_date <= cutoff_date:
                        deadline_info = get_object_data(assignment)
                        deadline_info['course_id'] = course.id
                        deadline_info['course_name'] = course.name
                        upcoming_deadlines.append(deadline_info)
            except Exception as course_error:
                logger.warning(f"Error getting assignments for course {course.id}: {course_error}")
        
        # Sort by due date
        upcoming_deadlines.sort(key=lambda x: x.get('due_at', ''))
        
        # Group by course
        deadlines_by_course = {}
        for deadline in upcoming_deadlines:
            course_id = deadline['course_id']
            if course_id not in deadlines_by_course:
                deadlines_by_course[course_id] = {
                    'course_name': deadline['course_name'],
                    'deadlines': []
                }
            deadlines_by_course[course_id]['deadlines'].append(deadline)
        
        # Format for Claude
        formatted_courses = []
        for course_id, course_data in deadlines_by_course.items():
            course_name = course_data['course_name']
            course_deadlines = course_data['deadlines']
            
            # Format each deadline within this course
            formatted_deadlines = []
            for deadline in course_deadlines:
                due_at = deadline.get('due_at', 'No due date')
                name = deadline.get('name', 'Unnamed assignment')
                points = deadline.get('points_possible', 'N/A')
                
                formatted_deadline = f"{name} - Due: {due_at} - Points: {points}"
                formatted_deadlines.append(formatted_deadline)
            
            # Add to the list of formatted courses
            formatted_courses.append({
                'name': course_name,
                'deadlines': formatted_deadlines
            })
        
        # Create the final Claude-friendly output
        formatted_output = format_for_claude(
            data={'days_ahead': days, 'total_deadlines': len(upcoming_deadlines)},
            type_name="UPCOMING_DEADLINES",
            title=f"Upcoming Deadlines (Next {days} days)",
            summary=f"Found {len(upcoming_deadlines)} upcoming deadlines across {len(deadlines_by_course)} courses",
            items=[f"{course['name']}: {len(course['deadlines'])} deadlines" for course in formatted_courses]
        )
        
        # For each course, add its deadlines in Claude-friendly format
        course_details = []
        for course in formatted_courses:
            course_output = format_for_claude(
                data={'course_name': course['name'], 'deadline_count': len(course['deadlines'])},
                type_name="COURSE_DEADLINES",
                title=course['name'],
                summary=f"{len(course['deadlines'])} upcoming deadlines",
                items=course['deadlines']
            )
            course_details.append(course_output)
        
        # Combine all outputs
        combined_output = formatted_output + "\n\n" + "\n".join(course_details)
        
        return {
            "success": True,
            "deadlines": upcoming_deadlines,
            "deadlines_by_course": deadlines_by_course,
            "formatted_output": combined_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving upcoming deadlines: {e}")
        return {
            "error": str(e),
            "status": "canvas_error",
            "original_error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error retrieving upcoming deadlines: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        } 