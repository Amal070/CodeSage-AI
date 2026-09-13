from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, default='')
    is_verified = models.BooleanField(default=False)

    def get_display_name(self):
        return self.username or self.email
