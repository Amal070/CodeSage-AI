from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('dashboard/', views.user_dashboard, name='user_dashboard'),  # User dashboard
    path('verify/', views.verify_certificate, name='verify_certificate'),  # Verify certificate page
]
