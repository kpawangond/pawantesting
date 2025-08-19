from django.urls import path
from . import courses_page_views, sign_in_views, sign_up_views, views, admin_views, upload_study_material, practice_tests
from django.conf.urls import handler404

handler404 = 'skills.views.custom_404_view'

urlpatterns = [
    path('', views.home, name='home'),

    #### Demo Booking
    path('get_timezones/', views.get_timezones, name='get_timezones'),
    path('book-demo/', views.book_demo_view, name='book_demo'),
    path('api/get-available-slots/', views.get_available_slots, name='get_available_slots'),
    path('api/book-slot/', views.book_slot, name='book_slot'),
    path('confirmation/<int:booking_id>/', views.confirmation_view, name='confirmation'),

    #### Courses Page
    path('math/', courses_page_views.math_page_view, name='math'),
    path('public_speaking/', courses_page_views.public_speaking_page_view, name='public_speaking'),

    #### About Page
    path('about/', views.about, name='about'),

    #### Contact Page
    path('contact/', views.contact, name='contact'),

    #### Curriculum PDF
    path('download_pdf/<int:grade>/', courses_page_views.download_pdf, name='download_pdf'),

    #### Sign Up
    path('send-otp/', sign_up_views.send_signup_otp, name='send_signup_otp'),
    path('confirm-otp/', sign_up_views.confirm_otp_and_register, name='confirm_otp_and_register'),

    #### Sign IN
    path('signin/', sign_in_views.signin_view, name='signin'),
    path('dashboard/', sign_in_views.dashboard_view, name='dashboard'),

    #### Log out
    path('logout/', sign_in_views.logout_view, name='logout'),

    #### Admin Related
    path('signin/admin/', admin_views.admin_login_view, name='admin_login'),
    path('dashboard/admin/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('student/<int:student_id>/', admin_views.student_detail_view, name='student_detail'),
    path('admin/logout/', admin_views.admin_logout_view, name='admin_logout'),

    #### Study Material
    path('upload-study-material/', upload_study_material.upload_study_material, name='upload_study_material'),
    path('edit-study-material/<int:material_id>/', upload_study_material.edit_study_material, name='edit_study_material'),
    path('delete-study-material/<int:material_id>/', upload_study_material.delete_study_material, name='delete_study_material'),
    path('api/get-topics/', upload_study_material.get_topics, name='get_topics'),
    path('api/get-subtopics/', upload_study_material.get_subtopics, name='get_subtopics'),

    #### Student Material Management
    path('student/<int:student_id>/tab-change/<str:tab_name>/', upload_study_material.log_tab_change, name='log_tab_change'),
    path('student/<int:student_id>/assign-material/<int:material_id>/', upload_study_material.assign_student_material, name='assign_student_material'),
    path('student/<int:student_id>/remove-material/<int:assignment_id>/', upload_study_material.remove_student_material, name='remove_student_material'),
    path('student/<int:student_id>/event/create/', upload_study_material.create_event, name='create_event'),
    path('student/<int:student_id>/event/<int:event_id>/update/', upload_study_material.update_event, name='update_event'),
    path('student/<int:student_id>/event/<int:event_id>/delete/', upload_study_material.delete_event, name='delete_event'),

    #### Practice Test Admin Routes
    path('api/create-test/', practice_tests.create_test_view, name='create_test'),
    path('api/get-all-tests/', practice_tests.get_all_tests, name='get_all_tests'),
    path('api/get-test/<int:test_id>/', practice_tests.get_test_details, name='get_test_details'),
    path('api/edit-test/<int:test_id>/', practice_tests.edit_test_view, name='edit_test'),
    path('api/delete-test/<int:test_id>/', practice_tests.delete_test_view, name='delete_test'),
    path('api/assign-test/', practice_tests.assign_test_to_students, name='assign_test'),
    path('api/get-students-for-assignment/', practice_tests.get_students_for_assignment, name='get_students_for_assignment'),
    path('test/<int:test_id>/results/', practice_tests.test_results_view, name='test_results'),
    path('api/get-assigned-tests/<int:student_id>/', practice_tests.get_assigned_tests, name='get_assigned_tests'),
    path('api/revoke-test/<int:student_id>/<int:test_id>/', practice_tests.revoke_test_assignment, name='revoke_test_assignment'),
    path('api/extend-test/<int:student_id>/<int:test_id>/', practice_tests.extend_test_validity, name='extend_test_validity'),
    
    #### Student Test Routes
    path('student/<int:student_id>/tests/', practice_tests.student_test_list, name='student_test_list'),
    path('student/<int:student_id>/test/<int:test_id>/', practice_tests.take_test_view, name='take_test'),
    path('student/<int:student_id>/test/<int:test_id>/submit/', practice_tests.submit_test_view, name='submit_test'),
    path('student/<int:student_id>/test/<int:test_id>/results/', practice_tests.test_results_view, name='test_results'),
    path('student/<int:student_id>/test/<int:test_id>/feedback/', practice_tests.test_feedback_view, name='test_feedback'),

    #### Legacy Test Related (keeping for compatibility)
    path('student/<int:student_id>/practice/', admin_views.student_practice_view, name='student_practice'),
]