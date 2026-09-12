from django.db import models
from django.conf import settings


class VerificationHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    certificate_id = models.CharField(max_length=200)
    result = models.CharField(max_length=100)
    verified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.certificate_id}"