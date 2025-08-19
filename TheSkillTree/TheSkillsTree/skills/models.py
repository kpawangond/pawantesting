import uuid
from django.db import models
from datetime import datetime
from pytz import timezone
import pytz, os
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Skill(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class DemoBooking(models.Model):
    
    GRADE_CHOICES = [(str(i), f'Grade {i}') for i in range(1, 13)]
    
    parent_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, null=True)
    email = models.EmailField()
    student_name = models.CharField(max_length=100)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    
    booking_date = models.DateField(null=True)
    booking_time = models.TimeField(null=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    booking_time_ist = models.TimeField(null=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        """Convert booking_time to IST before saving"""
        if self.booking_time and self.timezone:
            try:
                user_tz = pytz.timezone(self.timezone)
                ist_tz = pytz.timezone('Asia/Kolkata')

                if self.booking_date:
                    user_dt = datetime.combine(self.booking_date, self.booking_time)
                    user_dt = user_tz.localize(user_dt)
                    ist_dt = user_dt.astimezone(ist_tz)
                    self.booking_time_ist = ist_dt.time()
            except pytz.exceptions.UnknownTimeZoneError:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_name} - {self.booking_date} {self.booking_time} ({self.timezone})"

    class Meta:
        ordering = ['-booking_date', 'booking_time']




def student_profile_pic_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    new_filename = f"profile_{uuid.uuid4().hex}{ext}"
    return os.path.join('student_images', new_filename)

class SignupUser(models.Model):
    parent_name = models.CharField(max_length=100)
    student_name = models.CharField(max_length=100)
    grade = models.CharField(max_length=10)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=4, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_picture = models.ImageField(
        upload_to=student_profile_pic_path,
        null=True,
        blank=True,
        storage=FileSystemStorage(location=os.path.join(settings.BASE_DIR, 'skills', 'static')),
        help_text='Student profile picture (saved in static/student_images/)'
    )

    def save(self, *args, **kwargs):
        if self.profile_picture:
            target_dir = os.path.join(settings.BASE_DIR, 'skills', 'static', 'student_images')
            os.makedirs(target_dir, exist_ok=True)
            
            old_file = None
            if self.pk:
                try:
                    old_file = SignupUser.objects.get(pk=self.pk).profile_picture
                except SignupUser.DoesNotExist:
                    pass
            
            super().save(*args, **kwargs)
            
            if old_file and old_file != self.profile_picture:
                old_file_path = os.path.join(settings.BASE_DIR, 'skills', 'static', old_file.name)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

    def get_profile_picture_url(self):
        if self.profile_picture:
            return f"{settings.STATIC_URL}student_images/{os.path.basename(self.profile_picture.name)}"
        return f"{settings.STATIC_URL}skills/images/default_profile.png"

    def __str__(self):
        return self.email
    



class StudyMaterial(models.Model):
    SUBJECT_CHOICES = [
        ('Maths', 'Maths'),
        ('Public Speaking', 'Public Speaking'),
        ('ELA', 'ELA'),
        ('Personalized Courses', 'Personalized Courses'),
    ]
    
    file_link = models.URLField(max_length=500)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    grades = models.CharField(max_length=100) 
    topic = models.CharField(max_length=200, blank=True, null=True)
    sub_topic = models.CharField(max_length=200, blank=True, null=True)
    short_video_link = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.subject} - {self.grades}"
    
    def get_grades_list(self):
        """Return grades as a list of integers"""
        if not self.grades:
            return []
        return [int(grade) for grade in self.grades.split(',')]
    
    def set_grades_list(self, grades_list):
        """Set grades from a list of values"""
        self.grades = ','.join(str(grade) for grade in grades_list)
    
    class Meta:
        ordering = ['-created_at']



class StudentEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('Study Session', 'Study Session'),
        ('Test/Practice', 'Test/Practice'),
    ]
    
    student = models.ForeignKey('SignupUser', on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='Study Session')
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    class_link = models.URLField(blank=True, null=True, help_text="Add Zoom/Google Meet/Class link")
    
    # IST conversion fields
    event_date_ist = models.DateField(null=True, editable=False)
    start_time_ist = models.TimeField(null=True, editable=False)
    end_time_ist = models.TimeField(null=True, editable=False)
    
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        """Convert event times to IST before saving"""
        if self.start_time and self.end_time and self.event_date and self.timezone:
            try:
                user_tz = pytz.timezone(self.timezone)
                ist_tz = pytz.timezone('Asia/Kolkata')
                
                # Convert start time
                start_dt = datetime.combine(self.event_date, self.start_time)
                start_dt = user_tz.localize(start_dt)
                start_ist = start_dt.astimezone(ist_tz)
                
                # Convert end time
                end_dt = datetime.combine(self.event_date, self.end_time)
                end_dt = user_tz.localize(end_dt)
                end_ist = end_dt.astimezone(ist_tz)
                
                self.event_date_ist = start_ist.date()
                self.start_time_ist = start_ist.time()
                self.end_time_ist = end_ist.time()
                
            except pytz.exceptions.UnknownTimeZoneError:
                # If timezone is invalid, use the original values
                self.event_date_ist = self.event_date
                self.start_time_ist = self.start_time
                self.end_time_ist = self.end_time
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student.student_name} - {self.title} ({self.event_date})"
    
    class Meta:
        ordering = ['event_date', 'start_time']




class StudentMaterial(models.Model):
    """Model to track materials assigned to students"""
    student = models.ForeignKey('SignupUser', on_delete=models.CASCADE, related_name='assigned_materials')
    material = models.ForeignKey('StudyMaterial', on_delete=models.CASCADE, related_name='student_assignments')
    assigned_date = models.DateTimeField(auto_now_add=True) 
    topic = models.CharField(max_length=200, blank=True, null=True)
    valid_until = models.DateField()
    
    def __str__(self):
        return f"{self.student.student_name} - {self.material.subject}"
    
    def is_valid(self):
        """Check if the assignment is still valid"""
        return timezone.now().date() <= self.valid_until
    
    class Meta:
        unique_together = ('student', 'material')
        ordering = ['-assigned_date']



class Test(models.Model):
    SUBJECT_CHOICES = [
        ('Maths', 'Maths'),
        ('Public Speaking', 'Public Speaking'),
        ('ELA', 'ELA'),
        ('Personalized Courses', 'Personalized Courses'),
    ]
    
    name = models.CharField(max_length=200)
    duration_minutes = models.PositiveIntegerField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ManyToManyField('SignupUser', through='AssignedTest', related_name='assigned_tests')
    grade = models.CharField(max_length=20, blank=True, null=True)
    is_practice = models.BooleanField(default=False) 
    
    def __str__(self):
        return f"{self.name} ({self.subject})"

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_text = CKEditor5Field('Question Text', config_name='extends')
    question_image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Question {self.order} for {self.test.name}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = CKEditor5Field('Option Text', config_name='extends')
    option_image = models.ImageField(upload_to='option_images/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Option {self.order} for Question {self.question.order}"

class AssignedTest(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey('SignupUser', on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    student_feedback = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('test', 'student')

class StudentAnswer(models.Model):
    assignment = models.ForeignKey(AssignedTest, on_delete=models.CASCADE, related_name='student_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('assignment', 'question')
        verbose_name = "Student Answer"
        verbose_name_plural = "Student Answers"

    def __str__(self):
        return f"{self.assignment.student.student_name} - Q{self.question.order}"