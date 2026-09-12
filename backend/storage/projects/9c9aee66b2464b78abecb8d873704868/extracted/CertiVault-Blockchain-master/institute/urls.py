from django.urls import path
from . import views

app_name = 'institute'

urlpatterns = [
    path('issue-certificate/', views.issue_certificate, name='issue_certificate'),
    path('manage-enrollments/', views.manage_enrollments, name='manage_enrollments'),
    path('update-enrollment/<int:enrollment_id>/<str:action>/', views.update_enrollment, name='update_enrollment'),
    path('generate-certificate/<int:enrollment_id>/', views.generate_student_certificate, name='generate_certificate'),
    path('save-certificate/', views.save_certificate, name='save_certificate'),
]
