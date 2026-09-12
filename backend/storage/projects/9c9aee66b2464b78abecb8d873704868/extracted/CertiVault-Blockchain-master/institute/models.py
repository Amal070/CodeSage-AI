import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

from django.conf import settings
from django.db import models


class Institute(models.Model):

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    institute_name = models.CharField(max_length=200)
    institute_code = models.CharField(max_length=50, unique=True)

    affiliation = models.CharField(max_length=200)
    type = models.CharField(max_length=100)

    established_year = models.IntegerField()

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    website = models.URLField(blank=True, null=True)
    address = models.TextField()

    admin_name = models.CharField(max_length=150)
    designation = models.CharField(max_length=100)

    govt_reg_no = models.CharField(max_length=100, unique=True)
    accreditation = models.CharField(max_length=100)

    # Courses provided by institute
    provided_courses = models.TextField(
        help_text="Example: Python, Data Science, 3 Month Diploma, 1 Year Course"
    )

    # Signature used for certificate generation
    signature = models.ImageField(upload_to='signatures/')

    # Institute logo
    logo = models.ImageField(upload_to='logos/')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.institute_name


class Course(models.Model):

    institute = models.ForeignKey(
        Institute,
        on_delete=models.CASCADE,
        related_name="courses"
    )

    course_name = models.CharField(max_length=200)
    duration_months = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.course_name


class Certificate(models.Model):

    student_name = models.CharField(max_length=200)
    register_number = models.CharField(max_length=100, null=True, blank=True)

    course = models.CharField(max_length=200)
    year_of_passing = models.IntegerField(null=True, blank=True)

    certificate_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        null=True,
        blank=True
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    certificate_file = models.FileField(upload_to='certificates/')

    certificate_hash = models.CharField(max_length=256)

    blockchain_tx_hash = models.CharField(
        max_length=256,
        null=True,
        blank=True
    )

    issue_date = models.DateField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = "CERT-" + str(uuid.uuid4()).split("-")[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.certificate_id


class InstituteCertificate(models.Model):

    institute = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='institute_certificates'
    )

    student_name = models.CharField(max_length=200)
    register_number = models.CharField(max_length=100, null=True, blank=True)

    student_email = models.EmailField(null=True, blank=True)

    course = models.CharField(max_length=200)
    year_of_passing = models.IntegerField(null=True, blank=True)

    certificate_file = models.FileField(upload_to='institute_certificates/')

    certificate_hash = models.CharField(max_length=64, unique=True)

    blockchain_tx_hash = models.CharField(
        max_length=256,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.institute.username} - {self.student_name} ({self.certificate_hash})"