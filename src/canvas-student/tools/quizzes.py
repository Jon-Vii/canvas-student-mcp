"""Quiz-related tools for Canvas MCP."""
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
async def get_course_quizzes(course_id: int):
    """
    Get information about quizzes in a specific course.
    
    Args:
        course_id: The Canvas course ID
        
    Returns:
        dict: Information about quizzes with Claude-friendly formatting
    """
    logger.info(f"Getting quizzes for course {course_id}")
    
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        quizzes = list(course.get_quizzes())
        
        # Convert to dictionary for JSON serialization
        quiz_data = [get_object_data(quiz) for quiz in quizzes]
        
        # Categorize quizzes
        now = datetime.now()
        upcoming_quizzes = []
        available_quizzes = []
        past_quizzes = []
        
        for quiz in quiz_data:
            # Check quiz status
            if quiz.get('published') is False:
                # Skip unpublished quizzes
                continue
                
            due_at = quiz.get('due_at')
            unlock_at = quiz.get('unlock_at')
            lock_at = quiz.get('lock_at')
            
            # Determine if quiz is available now
            is_available_now = True
            
            if unlock_at:
                try:
                    unlock_date = datetime.fromisoformat(unlock_at.replace('Z', '+00:00'))
                    if unlock_date > now:
                        is_available_now = False
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse unlock date for quiz {quiz.get('id')}: {e}")
            
            if lock_at and is_available_now:
                try:
                    lock_date = datetime.fromisoformat(lock_at.replace('Z', '+00:00'))
                    if lock_date < now:
                        is_available_now = False
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse lock date for quiz {quiz.get('id')}: {e}")
            
            # Check due date to categorize as upcoming or past
            if due_at:
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    if due_date > now:
                        upcoming_quizzes.append(quiz)
                    else:
                        past_quizzes.append(quiz)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse due date for quiz {quiz.get('id')}: {e}")
                    
                    # If we can't parse the date, consider it as an available quiz
                    if is_available_now:
                        available_quizzes.append(quiz)
            else:
                # If no due date, consider it as an available quiz
                if is_available_now:
                    available_quizzes.append(quiz)
        
        # Sort upcoming quizzes by due date
        upcoming_quizzes.sort(key=lambda x: x.get('due_at', ''))
        
        # Format quiz information for Claude
        upcoming_items = []
        for quiz in upcoming_quizzes:
            title = quiz.get('title', 'Unnamed quiz')
            due_at = quiz.get('due_at')
            points = quiz.get('points_possible', 'No points')
            time_limit = quiz.get('time_limit')
            allowed_attempts = quiz.get('allowed_attempts')
            question_count = quiz.get('question_count', 'Unknown')
            
            # Format date to be more readable
            date_info = ""
            if due_at:
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    days_until = (due_date - now).days
                    hours_until = ((due_date - now).seconds // 3600)
                    
                    if days_until == 0:
                        if hours_until == 0:
                            time_until = "Due today (in less than an hour)"
                        elif hours_until == 1:
                            time_until = "Due today (in 1 hour)"
                        else:
                            time_until = f"Due today (in {hours_until} hours)"
                    elif days_until == 1:
                        time_until = "Due tomorrow"
                    else:
                        time_until = f"Due in {days_until} days"
                    
                    date_info = f" - Due: {due_date.strftime('%b %d, %Y at %I:%M %p')} ({time_until})"
                except (ValueError, TypeError):
                    date_info = f" - Due: {due_at}"
            
            # Format quiz details
            quiz_info = f"📝 {title}{date_info} - Points: {points}"
            
            # Add time limit if available
            if time_limit:
                quiz_info += f" - Time Limit: {time_limit} minutes"
                
            # Add attempts info if available
            if allowed_attempts:
                if allowed_attempts == -1:
                    quiz_info += f" - Unlimited attempts"
                else:
                    quiz_info += f" - {allowed_attempts} attempt(s)"
                    
            # Add question count if available
            if question_count != 'Unknown':
                quiz_info += f" - {question_count} questions"
                
            upcoming_items.append(quiz_info)
        
        # Format available quizzes
        available_items = []
        for quiz in available_quizzes:
            title = quiz.get('title', 'Unnamed quiz')
            points = quiz.get('points_possible', 'No points')
            time_limit = quiz.get('time_limit')
            allowed_attempts = quiz.get('allowed_attempts')
            
            # Format quiz details
            quiz_info = f"✅ {title} - Available now - Points: {points}"
            
            # Add time limit if available
            if time_limit:
                quiz_info += f" - Time Limit: {time_limit} minutes"
                
            # Add attempts info if available
            if allowed_attempts:
                if allowed_attempts == -1:
                    quiz_info += f" - Unlimited attempts"
                else:
                    quiz_info += f" - {allowed_attempts} attempt(s)"
                    
            available_items.append(quiz_info)
        
        # Create items for Claude output
        all_items = []
        
        # Add upcoming quizzes if any
        if upcoming_items:
            all_items.append("🔜 UPCOMING QUIZZES:")
            all_items.extend(upcoming_items)
            all_items.append("")
        
        # Add available quizzes if any
        if available_items:
            all_items.append("✅ AVAILABLE NOW:")
            all_items.extend(available_items)
        
        # If no quizzes, add a message
        if not upcoming_items and not available_items:
            all_items.append("No upcoming or available quizzes found in this course.")
        
        # Create summary for output
        summary = f"Found {len(upcoming_quizzes)} upcoming and {len(available_quizzes)} available quizzes in {course.name}"
        
        # Format for Claude
        formatted_output = format_for_claude(
            data={
                'course_id': course_id, 
                'total_quizzes': len(quiz_data),
                'upcoming_quizzes': len(upcoming_quizzes),
                'available_quizzes': len(available_quizzes),
                'past_quizzes': len(past_quizzes)
            },
            type_name="COURSE_QUIZZES",
            title=f"Quizzes for {course.name}",
            summary=summary,
            items=all_items
        )
        
        return {
            "success": True,
            "quizzes": quiz_data,
            "upcoming_quizzes": upcoming_quizzes,
            "available_quizzes": available_quizzes,
            "past_quizzes": past_quizzes,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving quizzes for course {course_id}: {e}")
        return _handle_canvas_error(e, f"retrieve quizzes for course {course_id}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving quizzes for course {course_id}: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        }

@cached(ttl=300)
async def get_all_quizzes():
    """
    Get information about quizzes across all courses.
    
    Returns:
        dict: Information about quizzes from all courses with Claude-friendly formatting
    """
    logger.info("Getting quizzes across all courses")
    
    try:
        canvas = get_canvas()
        courses = list(canvas.get_courses(enrollment_state='active'))
        
        now = datetime.now()
        upcoming_quizzes = []
        available_quizzes = []
        
        for course in courses:
            try:
                quizzes = list(course.get_quizzes())
                
                for quiz in quizzes:
                    quiz_data = get_object_data(quiz)
                    quiz_data['course_name'] = course.name
                    quiz_data['course_id'] = course.id
                    
                    # Skip unpublished quizzes
                    if quiz_data.get('published') is False:
                        continue
                        
                    # Check availability
                    due_at = quiz_data.get('due_at')
                    unlock_at = quiz_data.get('unlock_at')
                    lock_at = quiz_data.get('lock_at')
                    
                    # Determine if quiz is available now
                    is_available_now = True
                    
                    if unlock_at:
                        try:
                            unlock_date = datetime.fromisoformat(unlock_at.replace('Z', '+00:00'))
                            if unlock_date > now:
                                is_available_now = False
                        except (ValueError, TypeError):
                            pass
                    
                    if lock_at and is_available_now:
                        try:
                            lock_date = datetime.fromisoformat(lock_at.replace('Z', '+00:00'))
                            if lock_date < now:
                                is_available_now = False
                        except (ValueError, TypeError):
                            pass
                    
                    # Check due date to categorize
                    if due_at:
                        try:
                            due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                            if due_date > now:
                                # Upcoming quiz
                                upcoming_quizzes.append(quiz_data)
                            elif is_available_now:
                                # Past due but still available
                                available_quizzes.append(quiz_data)
                        except (ValueError, TypeError):
                            # If we can't parse the date and it's available, add to available
                            if is_available_now:
                                available_quizzes.append(quiz_data)
                    else:
                        # No due date but available
                        if is_available_now:
                            available_quizzes.append(quiz_data)
            except Exception as e:
                logger.warning(f"Could not get quizzes for course {course.id}: {e}")
        
        # Sort upcoming quizzes by due date
        upcoming_quizzes.sort(key=lambda x: x.get('due_at', ''))
        
        # Format upcoming quizzes for Claude
        upcoming_items = []
        for quiz in upcoming_quizzes:
            title = quiz.get('title', 'Unnamed quiz')
            course_name = quiz.get('course_name', 'Unknown course')
            due_at = quiz.get('due_at')
            points = quiz.get('points_possible', 'No points')
            time_limit = quiz.get('time_limit')
            
            # Format date to be more readable
            date_info = ""
            if due_at:
                try:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    days_until = (due_date - now).days
                    
                    if days_until == 0:
                        time_until = "Due today"
                    elif days_until == 1:
                        time_until = "Due tomorrow"
                    else:
                        time_until = f"Due in {days_until} days"
                    
                    date_info = f" - Due: {due_date.strftime('%b %d')} ({time_until})"
                except (ValueError, TypeError):
                    date_info = f" - Due: {due_at}"
            
            # Format quiz details
            quiz_info = f"📝 {title} - Course: {course_name}{date_info} - Points: {points}"
            
            # Add time limit if available
            if time_limit:
                quiz_info += f" - Time Limit: {time_limit} minutes"
                
            upcoming_items.append(quiz_info)
        
        # Format available quizzes
        available_items = []
        for quiz in available_quizzes:
            title = quiz.get('title', 'Unnamed quiz')
            course_name = quiz.get('course_name', 'Unknown course')
            points = quiz.get('points_possible', 'No points')
            time_limit = quiz.get('time_limit')
            
            # Format quiz details
            quiz_info = f"✅ {title} - Course: {course_name} - Available now - Points: {points}"
            
            # Add time limit if available
            if time_limit:
                quiz_info += f" - Time Limit: {time_limit} minutes"
                
            available_items.append(quiz_info)
        
        # Create items for Claude output
        all_items = []
        
        # Add upcoming quizzes if any
        if upcoming_items:
            all_items.append("🔜 UPCOMING QUIZZES:")
            all_items.extend(upcoming_items)
            all_items.append("")
        
        # Add available quizzes if any
        if available_items:
            all_items.append("✅ AVAILABLE NOW:")
            all_items.extend(available_items)
        
        # If no quizzes, add a message
        if not upcoming_items and not available_items:
            all_items.append("No upcoming or available quizzes found in any course.")
        
        # Create summary for output
        summary = f"Found {len(upcoming_quizzes)} upcoming and {len(available_quizzes)} available quizzes across {len(courses)} courses"
        
        # Format for Claude
        formatted_output = format_for_claude(
            data={
                'total_courses': len(courses),
                'upcoming_quizzes': len(upcoming_quizzes),
                'available_quizzes': len(available_quizzes)
            },
            type_name="ALL_QUIZZES",
            title="Quizzes Across All Courses",
            summary=summary,
            items=all_items
        )
        
        return {
            "success": True,
            "upcoming_quizzes": upcoming_quizzes,
            "available_quizzes": available_quizzes,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving quizzes: {e}")
        return _handle_canvas_error(e, "retrieve quizzes across all courses")
    except Exception as e:
        logger.error(f"Unexpected error retrieving quizzes: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        }

@cached(ttl=300)
async def get_quiz_details(course_id: int, quiz_id: int):
    """
    Get detailed information about a specific quiz.
    
    Args:
        course_id: The Canvas course ID
        quiz_id: The Canvas quiz ID
        
    Returns:
        dict: Detailed information about the quiz with Claude-friendly formatting
    """
    logger.info(f"Getting details for quiz {quiz_id} in course {course_id}")
    
    try:
        canvas = get_canvas()
        course = canvas.get_course(course_id)
        quiz = course.get_quiz(quiz_id)
        
        # Get quiz data
        quiz_data = get_object_data(quiz)
        
        # Try to get questions if available
        try:
            questions = list(quiz.get_questions())
            question_data = [get_object_data(question) for question in questions]
            quiz_data['questions'] = question_data
        except Exception as e:
            logger.warning(f"Could not get questions for quiz {quiz_id}: {e}")
            quiz_data['questions'] = []
        
        # Try to get submission data if available
        try:
            user = canvas.get_current_user()
            submissions = list(quiz.get_submissions(user_id=user.id))
            submission_data = [get_object_data(submission) for submission in submissions]
            quiz_data['submissions'] = submission_data
        except Exception as e:
            logger.warning(f"Could not get submissions for quiz {quiz_id}: {e}")
            quiz_data['submissions'] = []
        
        # Format quiz information for Claude
        now = datetime.now()
        
        # Get basic quiz info
        title = quiz_data.get('title', 'Unnamed quiz')
        description = quiz_data.get('description', 'No description available')
        points_possible = quiz_data.get('points_possible', 'No points')
        question_count = quiz_data.get('question_count', 'Unknown')
        time_limit = quiz_data.get('time_limit')
        allowed_attempts = quiz_data.get('allowed_attempts')
        due_at = quiz_data.get('due_at')
        unlock_at = quiz_data.get('unlock_at')
        lock_at = quiz_data.get('lock_at')
        quiz_type = quiz_data.get('quiz_type', 'Unknown')
        scoring_policy = quiz_data.get('scoring_policy', 'Unknown')
        
        # Format date information
        date_info = []
        if due_at:
            try:
                due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                if due_date > now:
                    days_until = (due_date - now).days
                    if days_until == 0:
                        time_until = "Due today"
                    elif days_until == 1:
                        time_until = "Due tomorrow"
                    else:
                        time_until = f"Due in {days_until} days"
                else:
                    time_until = "Past due"
                    
                date_info.append(f"Due: {due_date.strftime('%b %d, %Y at %I:%M %p')} ({time_until})")
            except (ValueError, TypeError):
                date_info.append(f"Due: {due_at}")
        
        if unlock_at:
            try:
                unlock_date = datetime.fromisoformat(unlock_at.replace('Z', '+00:00'))
                date_info.append(f"Available from: {unlock_date.strftime('%b %d, %Y at %I:%M %p')}")
            except (ValueError, TypeError):
                date_info.append(f"Available from: {unlock_at}")
        
        if lock_at:
            try:
                lock_date = datetime.fromisoformat(lock_at.replace('Z', '+00:00'))
                date_info.append(f"Available until: {lock_date.strftime('%b %d, %Y at %I:%M %p')}")
            except (ValueError, TypeError):
                date_info.append(f"Available until: {lock_at}")
        
        # Format submission information
        submission_info = []
        if quiz_data.get('submissions'):
            latest_submission = quiz_data['submissions'][0] if quiz_data['submissions'] else None
            if latest_submission:
                submission_info.append(f"Latest submission: {latest_submission.get('workflow_state', 'Unknown status')}")
                if 'score' in latest_submission:
                    submission_info.append(f"Score: {latest_submission.get('score')} / {points_possible}")
                if 'attempt' in latest_submission:
                    submission_info.append(f"Attempt: {latest_submission.get('attempt')}")
        
        # Format attempt policy
        attempt_info = "Attempts allowed: "
        if allowed_attempts is None or allowed_attempts == 0:
            attempt_info += "1"
        elif allowed_attempts == -1:
            attempt_info += "Unlimited"
        else:
            attempt_info += str(allowed_attempts)
        
        # Format quiz type and scoring policy
        type_info = f"Quiz type: {quiz_type}"
        if scoring_policy != 'Unknown':
            type_info += f" - Scoring policy: {scoring_policy}"
        
        # Create items for Claude output
        all_items = [
            f"📊 Points: {points_possible}",
            f"❓ Questions: {question_count}",
        ]
        
        # Add time limit if available
        if time_limit:
            all_items.append(f"⏱️ Time limit: {time_limit} minutes")
        
        # Add attempt information
        all_items.append(f"🔄 {attempt_info}")
        
        # Add type information
        all_items.append(f"ℹ️ {type_info}")
        
        # Add date information
        all_items.append("")
        all_items.append("📅 DATES:")
        all_items.extend(date_info if date_info else ["No date information available"])
        
        # Add submission information if available
        if submission_info:
            all_items.append("")
            all_items.append("📝 YOUR SUBMISSIONS:")
            all_items.extend(submission_info)
        
        # Add description if available
        if description and description != 'No description available':
            all_items.append("")
            all_items.append("📄 DESCRIPTION:")
            all_items.append(description)
        
        # Create summary for output
        if quiz_data.get('submissions'):
            summary = f"Quiz with {question_count} questions worth {points_possible} points - You have submitted {len(quiz_data['submissions'])} attempt(s)"
        else:
            summary = f"Quiz with {question_count} questions worth {points_possible} points"
        
        # Format for Claude
        formatted_output = format_for_claude(
            data={
                'course_id': course_id,
                'quiz_id': quiz_id,
                'questions': len(quiz_data.get('questions', [])),
                'submissions': len(quiz_data.get('submissions', []))
            },
            type_name="QUIZ_DETAILS",
            title=title,
            summary=summary,
            items=all_items
        )
        
        return {
            "success": True,
            "quiz": quiz_data,
            "formatted_output": formatted_output
        }
    except CanvasException as e:
        logger.error(f"Canvas API error retrieving quiz {quiz_id}: {e}")
        return _handle_canvas_error(e, f"retrieve quiz {quiz_id}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving quiz {quiz_id}: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "unknown_error",
            "original_error": str(e)
        } 