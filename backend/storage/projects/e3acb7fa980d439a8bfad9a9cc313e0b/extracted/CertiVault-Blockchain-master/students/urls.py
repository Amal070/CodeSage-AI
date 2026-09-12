from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('login/', views.student_login, name='student_login'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('profile-update/', views.student_profile_update, name='student_profile_update'),
    path('enroll-course/', views.enroll_course, name='enroll_course'),
    path('request-certificate/', views.request_certificate, name='request_certificate'),
]

