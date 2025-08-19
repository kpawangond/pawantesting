from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from .models import SignupUser, StudentMaterial, StudentEvent, AssignedTest
from django.utils import timezone
import json
from datetime import datetime, timedelta

@csrf_exempt
def signin_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            custom_user = SignupUser.objects.get(email=email)
            
            if check_password(password, custom_user.password):
                try:
                    django_user = User.objects.get(username=email)
                except User.DoesNotExist:
                    django_user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=None
                    )
                    django_user.set_unusable_password()
                    django_user.save()
                
                django_user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, django_user)

                request.session['user_email'] = custom_user.email
                request.session['is_logged_in'] = True

                # Redirect to dashboard
                return JsonResponse({'status': 'success', 'redirect_url': '/dashboard/'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid email or password'})
                
        except SignupUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid email or password'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


def dashboard_view(request):
    if not request.session.get('is_logged_in'):
        return render(request, 'skills/home.html', {'error': 'Please login to continue.'})

    user_email = request.session.get('user_email')

    try:
        user = SignupUser.objects.get(email=user_email)
    except SignupUser.DoesNotExist:
        return render(request, 'skills/home.html', {'error': 'User not found. Please log in again.'})
    
    # Get student materials
    student_materials = StudentMaterial.objects.filter(student=user).select_related('material')

    # Get unique topics for filtering
    unique_topics = set()
    for sm in student_materials:
        if sm.material.topic:
            unique_topics.add(sm.material.topic)
    
    # Check validity of materials
    for sm in student_materials:
        sm.is_valid = timezone.now().date() <= sm.valid_until
    
    # Get student events
    student_events = StudentEvent.objects.filter(student=user).order_by('event_date', 'start_time')
    
    # Get upcoming events (next 30 days)
    today = timezone.now().date()
    upcoming_events = student_events.filter(
        event_date__gte=today,
        event_date__lte=today + timedelta(days=30)
    )[:10]  # Limit to 10 upcoming events
    
    # Get assigned tests and practice materials
    assigned_tests = AssignedTest.objects.filter(
        student=user, 
        test__is_practice=False
    ).select_related('test').order_by('-assigned_date')
    
    practice_tests = AssignedTest.objects.filter(
        student=user, 
        test__is_practice=True
    ).select_related('test').order_by('-assigned_date')
    
    # Prepare test data for templates
    def prepare_test_data(assignments):
        test_data = []
        for assignment in assignments:
            test = assignment.test
            test_data.append({
                'id': test.id,
                'name': test.name,
                'subject': test.subject,
                'duration_minutes': test.duration_minutes,
                'questions_count': test.questions.count(),
                'completed': assignment.completed,
                'score': assignment.score,
                'assigned_date': assignment.assigned_date.strftime('%Y-%m-%d %H:%M'),
                'completed_date': assignment.completed_date.strftime('%Y-%m-%d %H:%M') if assignment.completed_date else None,
                'valid_until': assignment.valid_until.strftime('%Y-%m-%d') if assignment.valid_until else 'No expiry',
                'is_expired': assignment.valid_until and timezone.now().date() > assignment.valid_until
            })
        return test_data
    
    assigned_tests_data = prepare_test_data(assigned_tests)
    practice_tests_data = prepare_test_data(practice_tests)
    
    # Prepare events data for JavaScript calendar
    events_data = []
    for event in student_events:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'class_link': event.class_link,
            'description': event.description or '',
            'event_type': event.event_type,
            'event_date': event.event_date.strftime('%Y-%m-%d'),
            'start_time': event.start_time.strftime('%H:%M'),
            'end_time': event.end_time.strftime('%H:%M'),
            'timezone': event.timezone,
            'is_completed': event.is_completed,
            'notes': event.notes or ''
        })
    
    context = {
        'user': user,
        'student_materials': student_materials,
        'profile_picture_url': user.get_profile_picture_url(),
        'unique_topics': sorted(unique_topics),
        'student_events': student_events,
        'upcoming_events': upcoming_events,
        'events_data_json': json.dumps(events_data),
        'assigned_tests': assigned_tests_data,
        'practice_tests': practice_tests_data,
    }

    return render(request, 'skills/dashboard.html', context)


def logout_view(request):
    logout(request)
    request.session.flush() 
    return redirect('home')  


def logout_view(request):
    request.session.flush()
    return render(request, 'skills/home.html')