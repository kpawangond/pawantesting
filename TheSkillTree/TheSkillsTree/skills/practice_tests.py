from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from .models import StudentAnswer, Test, Question, Option, SignupUser, AssignedTest
from django.conf import settings
import json
import uuid
import os
from PIL import Image
from io import BytesIO
import base64
from django.db.models import Avg

@login_required(login_url='/signin/admin/')
def create_test_view(request):
    """Create a new practice test"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # Create the test
                test = Test.objects.create(
                    name=data['name'],
                    subject=data['subject'],
                    duration_minutes = int(data.get('duration') or 0),
                    grade=data.get('grade', ''),
                    is_practice=data.get('is_practice', False),
                    created_by=request.user
                )
                
                # Create questions and options
                for i, question_data in enumerate(data['questions']):
                    # Handle question image if present
                    question_image = None
                    if 'questionImage' in question_data and question_data['questionImage']:
                        question_image = save_base64_image(question_data['questionImage'], 'question_images')
                    
                    question = Question.objects.create(
                        test=test,
                        question_text=question_data['text'],
                        question_image=question_image,
                        points=int(question_data['points']),
                        order=i + 1
                    )
                    
                    # Create options
                    for j, option_data in enumerate(question_data['options']):
                        # Handle option image if present
                        option_image = None
                        if 'optionImage' in option_data and option_data['optionImage']:
                            option_image = save_base64_image(option_data['optionImage'], 'option_images')
                        
                        Option.objects.create(
                            question=question,
                            option_text=option_data['text'],
                            option_image=option_image,
                            is_correct=option_data['isCorrect'],
                            order=j + 1
                        )
            
            return JsonResponse({
                'success': True,
                'message': 'Test created successfully',
                'test_id': test.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error creating test: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='/signin/admin/')
def get_all_tests(request):
    """Get all practice tests for admin dashboard"""
    try:
        tests = Test.objects.all().prefetch_related('questions', 'assigned_to').order_by('-created_at')
        tests_data = []
        
        for test in tests:
            assigned_count = test.assigned_to.count()
            completed_count = AssignedTest.objects.filter(test=test, completed=True).count()
            
            tests_data.append({
                'id': test.id,
                'name': test.name,
                'grade': test.grade,
                'subject': test.subject,
                'duration_minutes': test.duration_minutes or 0,
                'questions_count': test.questions.count(),
                'assigned_count': assigned_count,
                'completed_count': completed_count,
                'created_at': test.created_at.strftime('%Y-%m-%d %H:%M'),
                'created_by': test.created_by.username
            })
        
        return JsonResponse({
            'success': True,
            'tests': tests_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error loading tests: {str(e)}',
            'tests': []
        })


@login_required(login_url='/signin/admin/')
def get_test_details(request, test_id):
    """Get detailed test information including questions and options"""
    try:
        test = get_object_or_404(Test, id=test_id)
        questions = []
        
        for question in test.questions.all().order_by('order'):
            options = []
            for option in question.options.all().order_by('order'):
                options.append({
                    'id': option.id,
                    'text': option.option_text,
                    'image_url': option.option_image.url if option.option_image else None,
                    'is_correct': option.is_correct,
                    'order': option.order
                })
            
            questions.append({
                'id': question.id,
                'text': question.question_text,
                'image_url': question.question_image.url if question.question_image else None,
                'points': question.points,
                'order': question.order,
                'options': options
            })
        
        # Get assignment statistics
        total_assigned = test.assigned_to.count()
        completed_assignments = AssignedTest.objects.filter(test=test, completed=True)
        completed_count = completed_assignments.count()
        average_score = completed_assignments.aggregate(avg_score=Avg('score'))['avg_score'] or 0
        
        test_data = {
            'id': test.id,
            'name': test.name,
            'subject': test.subject,
            'duration_minutes': test.duration_minutes,
            'grade': test.grade,
            'created_at': test.created_at.strftime('%Y-%m-%d %H:%M'),
            'created_by': test.created_by.username,
            'questions': questions,
            'stats': {
                'total_assigned': total_assigned,
                'completed_count': completed_count,
                'average_score': round(average_score, 2)
            }
        }
        
        return JsonResponse({'success': True, 'test': test_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required(login_url='/signin/admin/')
def edit_test_view(request, test_id):
    """Edit an existing test"""
    if request.method == 'POST':
        try:
            test = get_object_or_404(Test, id=test_id)
            data = json.loads(request.body)
            
            with transaction.atomic():
                # Update test basic info
                test.name = data['name']
                test.subject = data['subject']
                test.duration_minutes = int(data['duration'])
                test.save()
                
                # Delete existing questions and options (cascade delete will handle options)
                test.questions.all().delete()
                
                # Create new questions and options
                for i, question_data in enumerate(data['questions']):
                    # Handle question image if present
                    question_image = None
                    if 'questionImage' in question_data and question_data['questionImage']:
                        if question_data['questionImage'].startswith('data:'):
                            question_image = save_base64_image(question_data['questionImage'], 'question_images')
                        else:
                            # Keep existing image URL
                            question_image = question_data['questionImage']
                    
                    question = Question.objects.create(
                        test=test,
                        question_text=question_data['text'],
                        question_image=question_image,
                        points=int(question_data['points']),
                        order=i + 1
                    )
                    
                    # Create options
                    for j, option_data in enumerate(question_data['options']):
                        # Handle option image if present
                        option_image = None
                        if 'optionImage' in option_data and option_data['optionImage']:
                            if option_data['optionImage'].startswith('data:'):
                                option_image = save_base64_image(option_data['optionImage'], 'option_images')
                            else:
                                # Keep existing image URL
                                option_image = option_data['optionImage']
                        
                        Option.objects.create(
                            question=question,
                            option_text=option_data['text'],
                            option_image=option_image,
                            is_correct=option_data['isCorrect'],
                            order=j + 1
                        )
            
            return JsonResponse({
                'success': True,
                'message': 'Test updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating test: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='/signin/admin/')
def delete_test_view(request, test_id):
    """Delete a test"""
    if request.method == 'POST':
        try:
            test = get_object_or_404(Test, id=test_id)
            test_name = test.name
            
            # Delete associated images
            for question in test.questions.all():
                if question.question_image:
                    
                    delete_file_safely(question.question_image.path)
                for option in question.options.all():
                    if option.option_image:
                        delete_file_safely(option.option_image.path)
            
            test.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Test "{test_name}" deleted successfully'
            })
            
        except Exception as e:
            print( ":::::::::::::::::::::")
            return JsonResponse({
                'success': False,
                'message': f'Error deleting test: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='/signin/admin/')
def assign_test_to_students(request):
    """Assign a test to multiple students"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            test_id = data['test_id']
            student_ids = data['student_ids']
            expiration_date = data.get('expiration_date')
            
            test = get_object_or_404(Test, id=test_id)
            students = SignupUser.objects.filter(id__in=student_ids)
            
            assigned_count = 0
            for student in students:
                assigned_test, created = AssignedTest.objects.get_or_create(
                    test=test,
                    student=student,
                    defaults={
                        'assigned_date': timezone.now(),
                        'valid_until': expiration_date
                    }
                )
                if created:
                    assigned_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Test assigned to {assigned_count} new students (Total: {len(students)} students)'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error assigning test: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required(login_url='/signin/admin/')
def get_students_for_assignment(request):
    """Get list of students for test assignment"""
    grade = request.GET.get('grade', '')
    
    students = SignupUser.objects.filter(is_verified=True)
    if grade:
        students = students.filter(grade__regex=fr"\b{grade}\b")
    
    students = students.order_by('student_name')
    students_data = []
    
    for student in students:
        students_data.append({
            'id': student.id,
            'student_name': student.student_name,
            'parent_name': student.parent_name,
            'grade': student.grade,
            'email': student.email
        })
    
    return JsonResponse({'students': students_data})


@login_required(login_url='/signin/admin/')
def get_assigned_tests(request, student_id):
    """Get all tests assigned to a specific student"""
    try:
        student = get_object_or_404(SignupUser, id=student_id)
        assigned_tests = AssignedTest.objects.filter(student=student).select_related('test')
        
        tests_data = []
        for assignment in assigned_tests:
            test = assignment.test
            tests_data.append({
                'id': test.id,
                'name': test.name,
                'subject': test.subject,
                'duration': test.duration_minutes,
                'completed': assignment.completed,
                'score': assignment.score,
                'valid_until': assignment.valid_until.strftime('%Y-%m-%d') if assignment.valid_until else 'N/A',
                'assigned_date': assignment.assigned_date.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse({
            'success': True,
            'tests': tests_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required(login_url='/signin/admin/')
def revoke_test_assignment(request, student_id, test_id):
    """Revoke a test assignment from a student"""
    if request.method == 'POST':
        try:
            assignment = get_object_or_404(AssignedTest, student_id=student_id, test_id=test_id)
            assignment.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Test assignment revoked successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required(login_url='/signin/admin/')
def extend_test_validity(request, student_id, test_id):
    """Extend the validity of a test assignment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_date = data.get('valid_until')
            
            if not new_date:
                return JsonResponse({
                    'success': False,
                    'message': 'Valid until date is required'
                }, status=400)
            
            assignment = get_object_or_404(AssignedTest, student_id=student_id, test_id=test_id)
            assignment.valid_until = new_date
            assignment.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Test validity extended successfully',
                'new_date': new_date
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


# Student-facing views for taking tests

def student_test_list(request, student_id):
    """List all tests assigned to a student"""
    student = get_object_or_404(SignupUser, id=student_id)
    
    # Get assigned tests with their assignment details
    assigned_tests = AssignedTest.objects.filter(student=student).select_related('test').order_by('-assigned_date')
    
    tests_data = []
    for assignment in assigned_tests:
        test = assignment.test
        tests_data.append({
            'id': test.id,
            'name': test.name,
            'subject': test.subject,
            'duration_minutes': test.duration_minutes,
            'questions_count': test.questions.count(),
            'completed': assignment.completed,
            'score': assignment.score,
            'assigned_date': assignment.assigned_date.strftime('%Y-%m-%d %H:%M'),
            'completed_date': assignment.completed_date.strftime('%Y-%m-%d %H:%M') if assignment.completed_date else None
        })
    
    return render(request, 'skills/student_tests.html', {
        'student': student,
        'tests': tests_data
    })


def take_test_view(request, student_id, test_id):
    """Student interface for taking a test"""
    student = get_object_or_404(SignupUser, id=student_id)
    test = get_object_or_404(Test, id=test_id)
    
    # Check if student is assigned to this test
    try:
        assignment = AssignedTest.objects.get(test=test, student=student)
    except AssignedTest.DoesNotExist:
        return render(request, 'skills/error.html', {
            'message': 'You are not assigned to this test.'
        })
    
    # Check if test is already completed
    if assignment.completed:
        return render(request, 'skills/test_completed.html', {
            'test': test,
            'assignment': assignment,
            'student': student
        })
    
    questions = []
    for question in test.questions.all().order_by('order'):
        options = []
        for option in question.options.all().order_by('order'):
            options.append({
                'id': option.id,
                'text': option.option_text,
                'image_url': option.option_image.url if option.option_image else None
            })
        
        questions.append({
            'id': question.id,
            'text': question.question_text,
            'image_url': question.question_image.url if question.question_image else None,
            'points': question.points,
            'options': options
        })
    
    return render(request, 'skills/take_test.html', {
        'student': student,
        'test': test,
        'questions': questions
    })


@csrf_exempt
def submit_test_view(request, student_id, test_id):
    """Handle test submission and calculate score"""
    if request.method == 'POST':
        try:
            student = get_object_or_404(SignupUser, id=student_id)
            test = get_object_or_404(Test, id=test_id)
            
            # Get assignment
            assignment = get_object_or_404(AssignedTest, test=test, student=student)
            
            # Check if already completed
            if assignment.completed:
                return JsonResponse({
                    'success': False,
                    'message': 'Test already completed'
                })
            
            data = json.loads(request.body)
            answers = data.get('answers', {})
            feedback = data.get('feedback', {})
            
            # Calculate score
            total_points = 0
            earned_points = 0
            results = []
            
            for question in test.questions.all():
                total_points += question.points
                
                # Check if answer is correct
                question_id = str(question.id)
                selected_option_id = answers.get(question_id)
                question_feedback = feedback.get(question_id, '')
                correct_option = question.options.filter(is_correct=True).first()
                
                is_correct = False
                selected_option = None
                
                if correct_option and selected_option_id:
                    try:
                        selected_option = Option.objects.get(id=selected_option_id)
                        is_correct = str(correct_option.id) == str(selected_option_id)
                    except Option.DoesNotExist:
                        pass
                
                if selected_option:
                    # Save student answer
                    StudentAnswer.objects.create(
                        assignment=assignment,
                        question=question,
                        selected_option=selected_option,
                        is_correct=is_correct,
                        feedback=question_feedback
                    )
                
                if is_correct:
                    earned_points += question.points
                
                results.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'selected_option_id': selected_option_id,
                    'correct_option_id': correct_option.id if correct_option else None,
                    'is_correct': is_correct,
                    'points': question.points
                })
            
            # Calculate percentage score
            score_percentage = (earned_points / total_points) * 100 if total_points > 0 else 0
            
            # Update assignment
            assignment.completed = True
            assignment.completed_date = timezone.now()
            assignment.score = score_percentage
            assignment.student_feedback = data.get('general_feedback', '')
            assignment.save()
            
            return JsonResponse({
                'success': True,
                'score': round(score_percentage, 2),
                'earned_points': earned_points,
                'total_points': total_points,
                'results': results
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error submitting test: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def get_student_answer(assignment, question):
    try:
        student_answer = StudentAnswer.objects.get(
            assignment=assignment,
            question=question
        )
        
        return {
            'option_id': student_answer.selected_option.id,
            'option_text': student_answer.selected_option.option_text,
            'option_image': student_answer.selected_option.option_image.url if student_answer.selected_option.option_image else None,
            'is_correct': student_answer.is_correct,
            'answered_at': student_answer.created_at,
            'feedback': student_answer.feedback
        }
    except StudentAnswer.DoesNotExist:
        return None


def test_results_view(request, student_id, test_id):
    """Return JSON data with test results"""
    student = get_object_or_404(SignupUser, id=student_id)
    test = get_object_or_404(Test, id=test_id)
    assignment = get_object_or_404(AssignedTest, test=test, student=student)
    
    if not assignment.completed:
        return JsonResponse({'error': 'Test not completed'}, status=400)
    
    # Get all questions with student answers
    questions = []
    for question in test.questions.all().order_by('order'):
        student_answer = get_student_answer(assignment, question)
        correct_option = question.options.filter(is_correct=True).first()
        
        questions.append({
            'question_id': question.id,
            'text': question.question_text,
            'image_url': question.question_image.url if question.question_image else None,
            'selected_answer': student_answer['option_text'] if student_answer else None,
            'selected_answer_id': student_answer['option_id'] if student_answer else None,
            'selected_answer_image': student_answer['option_image'] if student_answer and 'option_image' in student_answer else None,
            'correct_answer': correct_option.option_text if correct_option else None,
            'correct_answer_id': correct_option.id if correct_option else None,
            'correct_answer_image': correct_option.option_image.url if correct_option and correct_option.option_image else None,
            'is_correct': student_answer['is_correct'] if student_answer else False,
            'points': question.points,
            'feedback': student_answer['feedback'] if student_answer and 'feedback' in student_answer else None
        })
    
    return JsonResponse({
        'test_name': test.name,
        'score': assignment.score,
        'completed_date': assignment.completed_date.strftime('%Y-%m-%d %H:%M'),
        'questions': questions,
        'student_feedback': assignment.student_feedback or ""
    })


@csrf_exempt
def test_feedback_view(request, student_id, test_id):
    """Handle test feedback submission"""
    if request.method == 'POST':
        try:
            student = get_object_or_404(SignupUser, id=student_id)
            test = get_object_or_404(Test, id=test_id)
            assignment = get_object_or_404(AssignedTest, test=test, student=student)
            
            data = json.loads(request.body)
            feedback = data.get('feedback', '').strip()
            
            if feedback:
                # Save feedback - you'll need to add a feedback field to your AssignedTest model
                assignment.feedback = feedback
                assignment.save()
                
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False, 'message': 'Feedback cannot be empty'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# Utility functions

def save_base64_image(base64_string, subfolder='question_img'):
    try:
        # Strip base64 header if present
        if base64_string.startswith('data:'):
            _, base64_string = base64_string.split(',', 1)

        # Decode base64 and open image
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))

        # Convert image mode if needed
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Resize large images
        max_size = (1200, 1200)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Generate unique filename
        filename = f"{uuid.uuid4()}.jpg"

        # Create target folder: static/question_img/ or static/option_img/
        static_target_dir = os.path.join(settings.BASE_DIR, 'skills', 'static', subfolder)
        os.makedirs(static_target_dir, exist_ok=True)

        # Save image
        file_path = os.path.join(static_target_dir, filename)
        image.save(file_path, format='JPEG', quality=85, optimize=True)

        # Return relative static path for browser use
        return f"{settings.STATIC_URL}{subfolder}/{filename}"

    except Exception as e:
        raise Exception(f"Error saving image: {str(e)}")


def validate_image(image_file):
    """Validate uploaded image"""
    # Check file size (5MB limit)
    if image_file.size > 5 * 1024 * 1024:
        return False
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in allowed_extensions:
        return False
    
    try:
        # Try to open with PIL to validate
        image = Image.open(image_file)
        image.verify()
        return True
    except:
        return False


def process_image(image_file):
    """Process uploaded image (resize, optimize)"""
    image = Image.open(image_file)
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    # Resize if too large
    max_size = (1200, 1200)
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save to BytesIO
    output = BytesIO()
    image.save(output, format='JPEG', quality=85, optimize=True)
    output.seek(0)
    
    return ContentFile(output.read())


def delete_file_safely(file_path):
    try:
        base_static_path = os.path.join(settings.BASE_DIR, 'skills', 'static')
        relative_path = file_path.replace('/static/', '')
        full_path = os.path.join(base_static_path, relative_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
    except:
        pass  # Ignore errors when deleting files