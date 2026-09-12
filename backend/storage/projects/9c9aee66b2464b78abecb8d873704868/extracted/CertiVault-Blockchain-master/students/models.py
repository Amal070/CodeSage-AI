from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from institute.models import Institute, Course


# function to automatically store the current year during enrollment
def current_year():
    return timezone.now().year


class Student(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE
    )

    student_id = models.CharField(
        max_length=50,
        unique=True
    )

    full_name = models.CharField(
        max_length=150
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True
    )

    phone = models.CharField(
        max_length=15
    )

    address = models.TextField()

    profile_photo = models.ImageField(
        upload_to="student_photos/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.full_name


class Enrollment(models.Model):

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    institute = models.ForeignKey(
        Institute,
        on_delete=models.CASCADE
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    # automatically stores the year of enrollment
    course_year = models.IntegerField(
        default=current_year
    )

    request_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    completion_date = models.DateField(
        null=True,
        blank=True
    )

    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Marks obtained in the course"
    )

    certificate_generated = models.BooleanField(
        default=False,
        help_text="Whether certificate has been generated"
    )

    certificate_file = models.FileField(
        upload_to='student_certificates/',
        null=True,
        blank=True
    )

    blockchain_tx_hash = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Blockchain transaction hash for certificate verification"
    )

    certificate_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA256 hash of the certificate file for blockchain verification"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.full_name} - {self.course.course_name}"


class CertificateRequest(models.Model):

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="certificate_requests"
    )

    request_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    def __str__(self):
        return f"Certificate Request - {self.enrollment.course.course_name} ({self.status})"
