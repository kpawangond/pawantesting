from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
import pytz
from datetime import datetime
from .models import DemoBooking, Skill
from .forms import DemoBookingForm
from .models import SignupUser


def custom_404_view(request, exception):
    return render(request, '404.html', status=404)



def home(request):
    skills = Skill.objects.all()
    user_email = request.session.get('user_email')

    user = None
    profile_picture_url = None

    if user_email:
        try:
            user = SignupUser.objects.get(email=user_email)
            profile_picture_url = user.get_profile_picture_url()
        except SignupUser.DoesNotExist:
            user = None
            profile_picture_url = None

    context = {
        'user': user,
        'profile_picture_url': profile_picture_url,
        'skills': skills
    }
    return render(request, 'skills/home.html', context)


def about(request):
    user_email = request.session.get('user_email')

    user = None
    profile_picture_url = None

    if user_email:
        try:
            user = SignupUser.objects.get(email=user_email)
            profile_picture_url = user.get_profile_picture_url()
        except SignupUser.DoesNotExist:
            user = None
            profile_picture_url = None

    context = {
        'user': user,
        'profile_picture_url': profile_picture_url,
    }
    return render(request, 'skills/about.html', context)


def contact(request):
    user_email = request.session.get('user_email')

    user = None
    profile_picture_url = None

    if user_email:
        try:
            user = SignupUser.objects.get(email=user_email)
            profile_picture_url = user.get_profile_picture_url()
        except SignupUser.DoesNotExist:
            user = None
            profile_picture_url = None

    context = {
        'user': user,
        'profile_picture_url': profile_picture_url,
    }
    return render(request, 'skills/contact.html', context)


def get_timezones(request):
    """Returns all timezones with GMT offsets for proper mapping"""
    timezones = []
    now = datetime.utcnow()

    for tz in pytz.all_timezones:
        timezone = pytz.timezone(tz)
        offset = timezone.utcoffset(now)

        hours, remainder = divmod(offset.total_seconds(), 3600)
        minutes = remainder // 60
        gmt_offset = f"GMT{int(hours):+03d}:{int(minutes):02d}"

        timezones.append({
            "value": tz,
            "label": f"({gmt_offset}) {tz.replace('_', ' ')}"
        })

    return JsonResponse({"timezones": timezones})


def book_demo_view(request):
    """Render the demo booking page"""
    return render(request, 'skills/book_demo.html')

@csrf_exempt
def get_available_slots(request):
    """API endpoint to get available time slots for a specific date"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))  # Decode JSON safely
            selected_date = data.get('date')
            selected_timezone = data.get('timezone')

            if not selected_date or not selected_timezone:
                return JsonResponse({'error': 'Missing required fields (date or timezone)'}, status=400)

            if selected_timezone not in pytz.all_timezones:
                return JsonResponse({'error': 'Invalid timezone'}, status=400)

            # Convert string date to datetime object
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()

            # Convert existing bookings to the selected timezone
            selected_tz = pytz.timezone(selected_timezone)
            ist_tz = pytz.timezone('Asia/Kolkata')

            # Fetch all bookings for this date
            booked_slots = DemoBooking.objects.filter(booking_date=date_obj).values_list('booking_time', 'timezone')

            booked_slots_converted = []
            for booking_time, booking_tz in booked_slots:
                try:
                    booking_tz_obj = pytz.timezone(booking_tz)
                    booking_dt = datetime.combine(date_obj, booking_time)
                    booking_dt = booking_tz_obj.localize(booking_dt)
                    converted_dt = booking_dt.astimezone(selected_tz)
                    booked_slots_converted.append(converted_dt.strftime('%H:%M'))
                except Exception as e:
                    print(f"Timezone conversion error: {e}")

            # Define all possible time slots
            all_slots = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']

            # Filter out booked slots
            available_slots = [slot for slot in all_slots if slot not in booked_slots_converted]

            return JsonResponse({'available_slots': available_slots})
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def book_slot(request):
    """API endpoint to book a demo slot"""
    if request.method == 'POST':
        try:
            # Parse request data
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
            
            form = DemoBookingForm(data)

            if form.is_valid():
                booking = form.save(commit=False)
                
                # Validate the timezone
                try:
                    user_tz = pytz.timezone(booking.timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    return JsonResponse({'status': 'error', 'message': 'Invalid timezone'}, status=400)
                
                ist_tz = pytz.timezone('Asia/Kolkata')

                if booking.booking_date and booking.booking_time:
                    user_dt = datetime.combine(booking.booking_date, booking.booking_time)
                    user_dt = user_tz.localize(user_dt)
                    ist_dt = user_dt.astimezone(ist_tz)
                    booking.booking_time_ist = ist_dt.time()

                existing_booking = DemoBooking.objects.filter(
                    booking_date=booking.booking_date,
                    booking_time=booking.booking_time,
                    timezone=booking.timezone
                ).exists()

                if existing_booking:
                    return JsonResponse({'status': 'error', 'message': 'Slot already booked'}, status=400)

                booking.save()

                return JsonResponse({
                    'status': 'success',
                    'message': 'Slot booked successfully!',
                    'booking_id': booking.id
                })
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def confirmation_view(request, booking_id):
    """View to display booking confirmation"""
    try:
        booking = DemoBooking.objects.get(id=booking_id)
        return render(request, 'skills/demo_confirmation.html', {'booking': booking})
    except DemoBooking.DoesNotExist:
        messages.error(request, "Booking not found")
        return redirect('book_demo')
    




def contact_form(request):
    if request.method == 'POST':
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact_form')
    else:
        form = ContactRequestForm()
    
    return render(request, 'contact_form.html', {'form': form})