from django.contrib.auth.hashers import make_password
from django.shortcuts import render
from django.http import JsonResponse
from .models import SignupUser
from .forms import SignupForm
from .utils import generate_otp, send_otp_email


def send_signup_otp(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data['email']
            print("Triggered")
            otp = generate_otp()

            request.session['signup_data'] = form.cleaned_data
            request.session['signup_otp'] = otp

            send_otp_email(email, otp)
            return JsonResponse({'status': 'otp_sent'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})


def confirm_otp_and_register(request):
    if request.method == 'POST':
        input_otp = request.POST.get('otp')
        session_otp = request.session.get('signup_otp')
        signup_data = request.session.get('signup_data')

        if input_otp == session_otp:
            hashed_password = make_password(signup_data['password'])

            profile_picture = request.FILES.get('profile_picture')

            user = SignupUser.objects.create(
                parent_name=signup_data['parent_name'],
                student_name=signup_data['student_name'],
                grade=signup_data['grade'],
                email=signup_data['email'],
                password=hashed_password,
                is_verified=True,
                otp=None,
                profile_picture=profile_picture
            )
            
            del request.session['signup_data']
            del request.session['signup_otp']
            
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'invalid_otp'})
