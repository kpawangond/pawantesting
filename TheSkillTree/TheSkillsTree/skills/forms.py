from django import forms
from .models import DemoBooking, SignupUser
import re

class DemoBookingForm(forms.ModelForm):
    class Meta:
        model = DemoBooking
        fields = [
            'parent_name', 
            'phone_number', 
            'email', 
            'student_name', 
            'grade', 
            'booking_date', 
            'booking_time', 
            'timezone'
        ]
        
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        phone = ''.join(filter(str.isdigit, phone))
        
        if len(phone) < 10:
            raise forms.ValidationError("Please enter a valid phone number")
        
        return phone


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), min_length=8)
    otp = forms.CharField(max_length=4, required=False)

    class Meta:
        model = SignupUser
        fields = ['parent_name', 'student_name', 'grade', 'email', 'password']

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("Password must contain at least one digit.")
        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError("Password must contain at least one special character.")

        return password