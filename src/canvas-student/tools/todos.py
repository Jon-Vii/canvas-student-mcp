"""Todo and missing assignments tools for Canvas MCP."""
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
from canvasapi.exceptions import CanvasException, Unauthorized, ResourceDoesNotExist

# Get logger
logger = logging.getLogger(__name__)

# Import utilities
from tools.utils import cached, format_for_claude
from tools.canvas_client import get_canvas, get_object_data

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
            "error": f"The requested resource was not found. This could be because the resource doesn't exist or you don't have access to it.",
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

@cached(ttl=300)
async def get_todo_items():
    """
    Get the current user's todo items and missing assignments, formatted for Claude.
    
    Returns:
        dict: Information about todo items and missing assignments
    """
    logger.info("Getting todo items and missing assignments")
    
    try:
        canvas = get_canvas()
        user = canvas.get_current_user()
        
        # Get todo items
        try:
            todo_items = list(user.get_todo_items())
            todo_data = [get_object_data(item) for item in todo_items]
        except Exception as e:
            logger.warning(f"Error getting todo items: {e}")
            todo_data = []
        
        # Get missing assignments
        try:
            # Get courses first, so we can add course names to assignments
            courses = {c.id: c.name for c in canvas.get_courses(enrollment_state='active')}
            
            # Get missing assignments
            missing_items = list(user.get_missing_submissions())
            missing_data = []
            
            for item in missing_items:
                item_data = get_object_data(item)
                
                # Add course name if available
                if 'course_id' in item_data and item_data['course_id'] in courses:
                    item_data['course_name'] = courses[item_data['course_id']]
                
                missing_data.append(item_data)
        except Exception as e:
            logger.warning(f"Error getting missing assignments: {e}")
            missing_data = []
        
        # Process todo items
        now = datetime.now()
        formatted_todos = []
        
        for item in todo_data:
            # Get basic info
            item_type = item.get('type', 'Unknown')
            title = item.get('assignment', {}).get('name', 'Unknown Assignment')
            course_id = item.get('course_id')
            course_name = None
            
            # Get course name if available
            if course_id and course_id in courses:
                course_name = courses[course_id]
            else:
                context_name = item.get('context_name', 'Unknown Course')
                if context_name != 'Unknown Course':
                    course_name = context_name
            
            # Get date info
            date_info = ""
            if 'assignment' in item and 'due_at' in item['assignment'] and item['assignment']['due_at']:
                due_at = item['assignment']['due_at']
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    days_until = (due_date - now).days
                    hours_until = ((due_date - now).seconds // 3600)
                    
                    if days_until < 0:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (PAST DUE)"
                    elif days_until == 0:
                        if hours_until <= 1:
                            date_info = f" - Due: {due_date.strftime('%b %d')} (DUE VERY SOON)"
                        else:
                            date_info = f" - Due: {due_date.strftime('%b %d')} (DUE TODAY in {hours_until} hours)"
                    elif days_until == 1:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (DUE TOMORROW)"
                    elif days_until < 7:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (Due in {days_until} days)"
                    else:
                        date_info = f" - Due: {due_date.strftime('%b %d')}"
                except (ValueError, TypeError):
                    date_info = f" - Due: {due_at}"
            
            # Format for display
            if course_name:
                todo_text = f"📋 {title} - Course: {course_name}{date_info}"
            else:
                todo_text = f"📋 {title}{date_info}"
            
            formatted_todos.append(todo_text)
        
        # Process missing assignments
        formatted_missing = []
        
        for item in missing_data:
            # Get basic info
            name = item.get('name', 'Unknown Assignment')
            points_possible = item.get('points_possible', 'Unknown')
            course_name = item.get('course_name', 'Unknown Course')
            
            # Get date info
            date_info = ""
            if 'due_at' in item and item['due_at']:
                due_at = item['due_at']
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    days_since = (now - due_date).days
                    
                    if days_since < 1:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (DUE TODAY)"
                    elif days_since == 1:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (1 day past due)"
                    else:
                        date_info = f" - Due: {due_date.strftime('%b %d')} ({days_since} days past due)"
                except (ValueError, TypeError):
                    date_info = f" - Due: {due_at}"
            
            # Format for display
            missing_text = f"⚠️ {name} - Course: {course_name}{date_info} - Points: {points_possible}"
            formatted_missing.append(missing_text)
        
        # Create items for Claude output
        all_items = []
        
        # Add todo items
        if formatted_todos:
            all_items.append("📋 TO-DO ITEMS:")
            all_items.extend(formatted_todos)
            all_items.append("")
        
        # Add missing assignments
        if formatted_missing:
            all_items.append("⚠️ MISSING ASSIGNMENTS:")
            all_items.extend(formatted_missing)
        
        # If nothing found, add a message
        if not formatted_todos and not formatted_missing:
            all_items.append("🎉 No to-do items or missing assignments found. You're all caught up!")
        
        # Create summary for output
        summary = f"Found {len(formatted_todos)} to-do items and {len(formatted_missing)} missing assignments"
        
        # Format for Claude
        formatted_output = format_for_claude(
            data={
                'todo_count': len(todo_data),
                'missing_count': len(missing_data)
            },
            type_name="TODO_ITEMS",
            title="To-Do Items and Missing Assignments",
            summary=summary,
            items=all_items
        )
        
        return {
            "success": True,
            "todo_items": todo_data,
            "missing_assignments": missing_data,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving todo items: {e}")
        return _handle_canvas_error(e, "retrieve todo items")
    except Exception as e:
        logger.error(f"Unexpected error retrieving todo items: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        }

@cached(ttl=300)
async def get_upcoming_todo_items(days: int = 7):
    """
    Get upcoming todo items and assignments due within X days.
    
    Args:
        days: Number of days to look ahead for assignments
        
    Returns:
        dict: Information about upcoming todo items and assignments
    """
    logger.info(f"Getting upcoming items due in the next {days} days")
    
    try:
        canvas = get_canvas()
        user = canvas.get_current_user()
        
        # Get courses
        courses = list(canvas.get_courses(enrollment_state='active'))
        course_dict = {c.id: c for c in courses}
        
        # Calculate date range
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        # Collect upcoming assignments
        upcoming_assignments = []
        
        for course_id, course in course_dict.items():
            try:
                # Get assignments for the course
                assignments = list(course.get_assignments())
                
                for assignment in assignments:
                    assignment_data = get_object_data(assignment)
                    
                    # Check if the assignment is published
                    if assignment_data.get('published') is False:
                        continue
                    
                    # Check if there's a due date
                    due_at = assignment_data.get('due_at')
                    if not due_at:
                        continue
                    
                    # Parse the due date
                    try:
                        due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        
                        # Check if it's in our date range and not past due
                        if now <= due_date <= end_date:
                            # Add course name for display
                            assignment_data['course_name'] = course.name
                            upcoming_assignments.append(assignment_data)
                    except (ValueError, TypeError):
                        # Skip if we can't parse the date
                        continue
            except Exception as e:
                logger.warning(f"Could not get assignments for course {course_id}: {e}")
        
        # Sort by due date
        upcoming_assignments.sort(key=lambda x: x.get('due_at', ''))
        
        # Format upcoming assignments for Claude
        formatted_assignments = []
        
        for assignment in upcoming_assignments:
            # Get basic info
            name = assignment.get('name', 'Unknown Assignment')
            course_name = assignment.get('course_name', 'Unknown Course')
            points_possible = assignment.get('points_possible', 'Unknown')
            due_at = assignment.get('due_at')
            
            # Get date info
            date_info = ""
            if due_at:
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    days_until = (due_date - now).days
                    hours_until = ((due_date - now).seconds // 3600)
                    
                    if days_until == 0:
                        if hours_until <= 1:
                            date_info = f" - Due: {due_date.strftime('%b %d')} (DUE VERY SOON)"
                        else:
                            date_info = f" - Due: {due_date.strftime('%b %d')} (DUE TODAY in {hours_until} hours)"
                    elif days_until == 1:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (DUE TOMORROW)"
                    else:
                        date_info = f" - Due: {due_date.strftime('%b %d')} (Due in {days_until} days)"
                except (ValueError, TypeError):
                    date_info = f" - Due: {due_at}"
            
            # Format for display
            assignment_text = f"📝 {name} - Course: {course_name}{date_info} - Points: {points_possible}"
            formatted_assignments.append(assignment_text)
        
        # Create items for Claude output
        all_items = []
        
        # Add upcoming assignments
        if formatted_assignments:
            all_items.append(f"📅 ASSIGNMENTS DUE IN THE NEXT {days} DAYS:")
            all_items.extend(formatted_assignments)
        else:
            all_items.append(f"🎉 No assignments due in the next {days} days.")
        
        # Create summary for output
        summary = f"Found {len(formatted_assignments)} assignments due in the next {days} days"
        
        # Format for Claude
        formatted_output = format_for_claude(
            data={
                'days_ahead': days,
                'assignment_count': len(upcoming_assignments)
            },
            type_name="UPCOMING_ASSIGNMENTS",
            title=f"Assignments Due in the Next {days} Days",
            summary=summary,
            items=all_items
        )
        
        return {
            "success": True,
            "upcoming_assignments": upcoming_assignments,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving upcoming assignments: {e}")
        return _handle_canvas_error(e, "retrieve upcoming assignments")
    except Exception as e:
        logger.error(f"Unexpected error retrieving upcoming assignments: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        } 