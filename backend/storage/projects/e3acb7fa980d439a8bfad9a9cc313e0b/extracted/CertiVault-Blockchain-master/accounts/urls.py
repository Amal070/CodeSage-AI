from django.urls import path
from . import views

urlpatterns = [
    path('institution/register/', views.institute_register, name='institution_register'),
    path('institution/login/', views.institution_login, name='institution_login'),
    path('institution/dashboard/', views.institution_dashboard, name='institution_dashboard'),
    path('user/register/', views.user_register, name='user_register'),
    path('user/login/', views.user_login, name='user_login'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('student/register/', views.student_register, name='student_register'),
    path('student/verify-register-otp/', views.verify_student_register_otp, name='verify_student_register_otp'),
    path('logout/', views.user_logout, name='logout'),
    
    # Admin URLs (using 'manage' prefix to avoid conflict with Django admin)
    path('manage/login/', views.admin_login, name='admin_login'),
    path('manage/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/approve-institute/<int:institute_id>/<str:action>/', views.approve_institute, name='approve_institute'),
]
