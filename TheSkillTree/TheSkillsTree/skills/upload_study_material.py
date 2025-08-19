from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .models import StudyMaterial, StudentMaterial, SignupUser, StudentEvent
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.db.models import Count


def upload_study_material(request):
    if request.method == 'POST':
        file_link = request.POST.get('file_link')
        subject = request.POST.get('subject')
        grades = request.POST.getlist('grades')
        short_video_link = request.POST.getlist('short_video_link')
        topic = request.POST.get('topic', '').strip()
        
        if not file_link or not subject or not grades:
            messages.error(request, 'Please fill all required fields')
            return redirect('admin_dashboard')
            
        study_material = StudyMaterial(
            file_link=file_link,
            subject=subject,
            topic=topic if topic else None,
            short_video_link=short_video_link if short_video_link else None
        )
        study_material.set_grades_list(grades)
        study_material.save()
        
        messages.success(request, 'Study material uploaded successfully!')
        return redirect('admin_dashboard')
    
    return redirect('admin_dashboard')


def edit_study_material(request, material_id):
    try:
        material = StudyMaterial.objects.get(id=material_id)
    except StudyMaterial.DoesNotExist:
        messages.error(request, 'Study material not found')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        file_link = request.POST.get('file_link')
        subject = request.POST.get('subject')
        grades = request.POST.getlist('grades')
        
        if not file_link or not subject or not grades:
            messages.error(request, 'Please fill all required fields')
            return redirect('edit_study_material', material_id=material_id)
        
        material.file_link = file_link
        material.subject = subject
        material.set_grades_list(grades)
        material.save()
        
        messages.success(request, 'Study material updated successfully!')
        return redirect('admin_dashboard')
    
    grades_list = material.get_grades_list()
    
    context = {
        'material': material,
        'grades_list': grades_list,
    }
    
    return render(request, 'skills/edit_study_material.html', context)


def delete_study_material(request, material_id):
    try:
        material = StudyMaterial.objects.get(id=material_id)
    except StudyMaterial.DoesNotExist:
        messages.error(request, 'Study material not found')
        return redirect('admin_dashboard')
    
    material.delete()
    messages.success(request, 'Study material deleted successfully!')
    return redirect('admin_dashboard')


@require_POST
def log_tab_change(request, student_id, tab_name):
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        
        # Get student information
        student = get_object_or_404(SignupUser, id=student_id)
        
        response_data = {
            'status': 'success',
        }
        
        # If tab is 'event', fetch student events
        if tab_name == 'event':
            # Get current month and year from request or use current date
            current_date = datetime.now()
            month = data.get('month', current_date.month)
            year = data.get('year', current_date.year)
            
            # Get events for the current month
            events = StudentEvent.objects.filter(
                student=student,
                event_date__year=year,
                event_date__month=month
            ).order_by('event_date', 'start_time')
            
            events_data = []
            for event in events:
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'class_link': event.class_link,
                    'event_type': event.event_type,
                    'event_type_display': event.get_event_type_display(),
                    'event_date': event.event_date.strftime('%Y-%m-%d'),
                    'start_time': event.start_time.strftime('%H:%M'),
                    'end_time': event.end_time.strftime('%H:%M'),
                    'is_completed': event.is_completed,
                    'notes': event.notes,
                })
            
            response_data['events'] = events_data
            response_data['month'] = month
            response_data['year'] = year
        
        # If tab is 'assigned', fetch assigned materials
        elif tab_name == 'assigned':
            student_materials = StudentMaterial.objects.filter(student=student).select_related('material')
            assigned_materials = []
            
            for sm in student_materials:
                is_valid = timezone.now().date() <= sm.valid_until
                assigned_materials.append({
                    'subject': sm.material.subject,
                    'file_link': sm.material.file_link,
                    'valid_until': sm.valid_until.strftime('%b %d, %Y'),
                    'is_expired': not is_valid,
                    'assignment_id': sm.id,
                    'topic': sm.material.topic,
                    'sub_topic': sm.material.sub_topic,
                    'short_video_link': sm.material.short_video_link,
                })
            
            # Group materials by subject
            subject_materials = {}
            for material in assigned_materials:
                if material['subject'] not in subject_materials:
                    subject_materials[material['subject']] = []
                subject_materials[material['subject']].append(material)
            
            response_data['assigned_materials'] = subject_materials
        
        # If tab is 'assign', fetch available materials
        elif tab_name == 'assign':
            # Extract numeric part from grade string (e.g., "Grade 1" -> 1)
            try:
                if student.grade.startswith('Grade '):
                    student_grade = int(student.grade.split('Grade ')[1])
                else:
                    student_grade = int(student.grade)
            except (ValueError, AttributeError):
                student_grade = 0
            
            # Get all materials appropriate for this student's grade level that haven't been assigned
            available_materials = []
            all_materials = StudyMaterial.objects.all()
            
            for material in all_materials:
                try:
                    # Safely get grades list with error handling
                    grade_list = material.get_grades_list()
                    if student_grade in grade_list:
                        # Check if material is already assigned
                        if not StudentMaterial.objects.filter(student=student, material=material).exists():
                            # Handle grades display safely
                            try:
                                grades_list = [f"Grade {g}" for g in material.grades.split(',') if g.strip()]
                                grades_display = ", ".join(grades_list) if grades_list else "No grades specified"
                            except (AttributeError, ValueError):
                                grades_display = "Grades format error"
                                
                            available_materials.append({
                                'id': material.id,
                                'subject': material.subject,
                                'file_link': material.file_link,
                                'topic': material.topic,
                                'sub_topic': material.sub_topic,
                                'short_video_link': material.short_video_link,
                                'grades': grades_display
                            })
                except Exception as e:
                    continue
            
            # Group by subject
            subject_materials = {}
            for material in available_materials:
                if material['subject'] not in subject_materials:
                    subject_materials[material['subject']] = []
                subject_materials[material['subject']].append(material)
            
            response_data['available_materials'] = subject_materials
        
        return JsonResponse(response_data)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        import traceback
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_POST
def create_event(request, student_id):
    """Create a new event for a student"""
    try:
        data = json.loads(request.body)
        student = get_object_or_404(SignupUser, id=student_id)
        
        event = StudentEvent.objects.create(
            student=student,
            title=data.get('title'),
            description=data.get('description', ''),
            event_type=data.get('event_type', 'session'),
            event_date=datetime.strptime(data.get('event_date'), '%Y-%m-%d').date(),
            start_time=datetime.strptime(data.get('start_time'), '%H:%M').time(),
            end_time=datetime.strptime(data.get('end_time'), '%H:%M').time(),
            timezone=data.get('timezone', 'Asia/Kolkata'),
            class_link=data.get('class_link', ''),
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Event created successfully',
            'event_id': event.id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_POST
def update_event(request, student_id, event_id):
    """Update an existing event"""
    try:
        data = json.loads(request.body)
        student = get_object_or_404(SignupUser, id=student_id)
        event = get_object_or_404(StudentEvent, id=event_id, student=student)
        
        # Update event fields
        event.title = data.get('title', event.title)
        event.description = data.get('description', event.description)
        event.event_type = data.get('event_type', event.event_type)
        event.event_date = datetime.strptime(data.get('event_date'), '%Y-%m-%d').date()
        event.start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
        event.end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
        event.is_completed = data.get('is_completed', event.is_completed)
        event.notes = data.get('notes', event.notes)
        event.class_link = data.get('class_link', event.class_link)
        
        event.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Event updated successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_POST
def delete_event(request, student_id, event_id):
    """Delete an event"""
    try:
        student = get_object_or_404(SignupUser, id=student_id)
        event = get_object_or_404(StudentEvent, id=event_id, student=student)
        event.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Event deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


def student_detail(request, student_id):
    # Get student information
    student = get_object_or_404(SignupUser, id=student_id)
    
    # Get assigned materials for this student with validity information
    student_materials = StudentMaterial.objects.filter(student=student).select_related('material')
    
    assigned_materials = []
    for sm in student_materials:
        assigned_materials.append({
            'subject': sm.material.subject,
            'file_link': sm.material.file_link,
            'valid_until': sm.valid_until,
            'is_expired': not sm.is_valid(),
            'assignment_id': sm.id
        })
    
    # Get materials available for this student's grade that haven't been assigned yet
    student_grade = int(student.grade)
    
    # Get all materials appropriate for this student's grade level
    available_materials = []
    all_materials = StudyMaterial.objects.all()
    
    for material in all_materials:
        # Check if material is appropriate for student's grade
        grade_list = material.get_grades_list()
        if student_grade in grade_list:
            # Check if material is already assigned
            if not StudentMaterial.objects.filter(student=student, material=material).exists():
                available_materials.append({
                    'id': material.id,
                    'subject': material.subject,
                    'file_link': material.file_link,
                    'grades': material.grades
                })
    
    # Group by subject
    for material in available_materials:
        grades_list = [f"Grade {g}" for g in material['grades'].split(',')]
        material['grades'] = ", ".join(grades_list)
    
    context = {
        'student': student,
        'assigned_materials': assigned_materials,
        'available_materials': available_materials,
        'today_date': timezone.now()
    }
    
    return render(request, 'skills/student_detail.html', context)


def get_topics(request):
    subject = request.GET.get('subject', '')
    if not subject:
        return JsonResponse([], safe=False)
    
    # Get unique topics for the selected subject, ordered by most used
    topics = StudyMaterial.objects.filter(subject=subject)\
        .exclude(topic__isnull=True)\
        .exclude(topic__exact='')\
        .values('topic')\
        .annotate(count=Count('topic'))\
        .order_by('-count', 'topic')
    
    # Extract just the topic names
    topic_list = [item['topic'] for item in topics]
    return JsonResponse(topic_list, safe=False)

def get_subtopics(request):
    subject = request.GET.get('subject', '')
    if not subject:
        return JsonResponse([], safe=False)
    
    # Get unique topics for the selected subject, ordered by most used
    sub_topics = StudyMaterial.objects.filter(subject=subject)\
        .exclude(topic__isnull=True)\
        .exclude(topic__exact='')\
        .values('sub_topic')\
        .annotate(count=Count('sub_topic'))\
        .order_by('-count', 'sub_topic')
    
    # Extract just the topic names
    subtopic_list = [item['sub_topic'] for item in sub_topics]
    return JsonResponse(subtopic_list, safe=False)


def assign_student_material(request, student_id, material_id):
    if request.method == 'POST':
        student = get_object_or_404(SignupUser, id=student_id)
        material = get_object_or_404(StudyMaterial, id=material_id)
        
        valid_until = request.POST.get('valid_until')
        try:
            valid_until_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
            
            if valid_until_date < timezone.now().date():
                messages.error(request, 'Validity date must be today or in the future')
                return redirect('student_detail', student_id=student_id)
                
            # Assign the selected material
            StudentMaterial.objects.create(
                student=student,
                material=material,
                valid_until=valid_until_date
            )
            
            messages.success(request, f'Study material assigned to {student.student_name} successfully!')
            
        except ValueError:
            messages.error(request, 'Invalid date format')
        except Exception as e:
            messages.error(request, f'Error assigning material: {str(e)}')
    
    return redirect('student_detail', student_id=student_id)


def remove_student_material(request, student_id, assignment_id):
    if request.method == 'POST':
        try:
            assignment = StudentMaterial.objects.get(id=assignment_id, student_id=student_id)
            assignment.delete()
            messages.success(request, 'Study material removed successfully!')
        except StudentMaterial.DoesNotExist:
            messages.error(request, 'Assignment not found')
        except Exception as e:
            messages.error(request, f'Error removing assignment: {str(e)}')
    
    return redirect('student_detail', student_id=student_id)