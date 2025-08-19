import random
from django.core.mail import send_mail

def generate_otp():
    return str(random.randint(1000, 9999))

def send_otp_email(to_email, otp):
    subject = 'Your OTP Code'
    message = f'Your OTP code is: {otp}'
    from_email = 'youremail@example.com'
    send_mail(subject, message, from_email, [to_email])
