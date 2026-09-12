from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    USER_TYPE_CHOICES = (
        ('institution', 'Institution'),
        ('student', 'Student'),
        ('user', 'User'),   # Public verifier
        ('admin', 'Admin'),  # Admin dashboard
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    otp = models.CharField(max_length=6, null=True, blank=True)
