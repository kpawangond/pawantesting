
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import SignupUser, StudyMaterial, Test

def admin_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        print(email, password)
        user = authenticate(request, username=email, password=password)
        request.session['is_logged_in'] = True
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            return render(request, 'skills/admin_login.html', {'error': 'Invalid credentials or not authorized.'})
    return render(request, 'skills/admin_login.html')


@login_required(login_url='/admin-login/')
def admin_dashboard_view(request):
    students = SignupUser.objects.all()
    study_materials = StudyMaterial.objects.all()
    practice_tests = Test.objects.all().prefetch_related('questions')

    context = {
        'students': students,
        'study_materials': study_materials,
        'practice_tests': practice_tests,
    }

    return render(request, 'skills/admin_dashboard.html', context)


@login_required(login_url='/admin-login/')
def student_detail_view(request, student_id):
    student = get_object_or_404(SignupUser, id=student_id)
    return render(request, 'skills/student_detail.html', {'student': student})


def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


def student_practice_view(request, student_id):
    student = get_object_or_404(SignupUser, id=student_id)
    return render(request, 'student_detail.html', {
        'student': student,
        'active_tab': 'practice'
    })