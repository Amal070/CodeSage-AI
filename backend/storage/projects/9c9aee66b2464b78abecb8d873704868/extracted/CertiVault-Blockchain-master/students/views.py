from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse


# ==========================
# STUDENT DASHBOARD
# ==========================
@login_required
def student_dashboard(request):

    if request.user.user_type != "student":
        return redirect("students:student_login")

    # Import models
    from students.models import Student, Enrollment, CertificateRequest
    from institute.models import Institute, Course
    
    # Get or create student profile
    student, created = Student.objects.get_or_create(
        user=request.user,
        defaults={
            'student_id': f"STU{request.user.id}",
            'full_name': request.user.username,
            'email': request.user.email,
            'phone': "",
            'address': ""
        }
    )
    
    # Check if profile is incomplete
    profile_incomplete = not student.phone or not student.address
    
    # Get all institutes with their courses (show all for visibility)
    institutes = Institute.objects.all().prefetch_related('courses')
    
    # Get student's enrollments
    enrollments = Enrollment.objects.filter(student=student).select_related('institute', 'course').order_by('-created_at')
    
    # Get pending course requests
    pending_requests = enrollments.filter(status='Pending')
    
    # Get approved/completed courses
    active_courses = enrollments.filter(status='Approved')
    completed_courses = enrollments.filter(status='Completed')
    
    # Get active enrollments per institute (to restrict multiple enrollments)
    active_enrollments_by_institute = {}
    for enrollment in enrollments.exclude(status__in=['Rejected', 'Completed']):
        active_enrollments_by_institute[enrollment.institute.id] = enrollment
    
    # Get certificate requests for this student
    cert_requests = CertificateRequest.objects.filter(
        enrollment__student=student
    ).select_related('enrollment', 'enrollment__course').order_by('-request_date')
    
    return render(request, "student/dashboard.html", {
        'student': student,
        'profile_incomplete': profile_incomplete,
        'institutes': institutes,
        'enrollments': enrollments,
        'pending_requests': pending_requests,
        'active_courses': active_courses,
        'completed_courses': completed_courses,
        'active_enrollments_by_institute': active_enrollments_by_institute,
        'cert_requests': cert_requests,
    })


# ==========================
# STUDENT PROFILE UPDATE
# ==========================
@login_required
def student_profile_update(request):
    if request.user.user_type != "student":
        return redirect("students:student_login")
    
    from students.models import Student
    
    student = Student.objects.get(user=request.user)
    
    if request.method == "POST":
        student.full_name = request.POST.get("full_name")
        student.phone = request.POST.get("phone")
        student.address = request.POST.get("address")
        student.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("students:student_dashboard")
    
    return render(request, "student/profile_update.html", {"student": student})


# ==========================
# COURSE ENROLLMENT REQUEST
# ==========================
@login_required
def enroll_course(request):
    if request.user.user_type != "student":
        return redirect("students:student_login")
    
    if request.method == "POST":
        from students.models import Student, Enrollment
        from institute.models import Course
        
        course_id = request.POST.get("course_id")
        
        try:
            student = Student.objects.get(user=request.user)
            course = Course.objects.get(id=course_id)
            
            # Check if already enrolled in the SAME course
            if Enrollment.objects.filter(student=student, course=course).exists():
                messages.error(request, "You have already enrolled in this course!")
                return redirect("students:student_dashboard")
            
            # NEW: Check if student already has an active enrollment under the same institute
            # Student can only have ONE active enrollment per institute at a time
            active_enrollment = Enrollment.objects.filter(
                student=student,
                institute=course.institute
            ).exclude(status__in=['Rejected', 'Completed']).first()
            
            if active_enrollment:
                messages.error(request, f"You already have an active enrollment in '{active_enrollment.course.course_name}' at {course.institute.institute_name}. You can only enroll in one course per institute at a time.")
                return redirect("students:student_dashboard")
            
            # Create enrollment request
            Enrollment.objects.create(
                student=student,
                institute=course.institute,
                course=course,
                status="Pending"
            )
            
            messages.success(request, "Course enrollment request submitted! Wait for institute approval.")
            return redirect("students:student_dashboard")
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect("students:student_dashboard")
    
    return redirect("students:student_dashboard")


# ==========================
# REQUEST CERTIFICATE
# ==========================
@login_required
def request_certificate(request):
    if request.user.user_type != "student":
        return redirect("students:student_login")
    
    if request.method == "POST":
        from students.models import Student, Enrollment, CertificateRequest
        
        enrollment_id = request.POST.get("enrollment_id")
        
        try:
            student = Student.objects.get(user=request.user)
            enrollment = Enrollment.objects.get(id=enrollment_id, student=student)
            
            # Check if enrollment is completed
            if enrollment.status != 'Completed':
                messages.error(request, "You can only request a certificate for completed courses.")
                return redirect("students:student_dashboard")
            
            # Check if certificate already generated
            if enrollment.certificate_generated:
                messages.error(request, "Certificate has already been issued for this course.")
                return redirect("students:student_dashboard")
            
            # Check if there's already a pending request
            if CertificateRequest.objects.filter(enrollment=enrollment, status='Pending').exists():
                messages.error(request, "You already have a pending certificate request for this course.")
                return redirect("students:student_dashboard")
            
            # Create certificate request (no need for name/birthdate - using student data)
            CertificateRequest.objects.create(
                enrollment=enrollment,
                status='Pending'
            )
            
            messages.success(request, "Certificate request submitted! The institute will review and issue your certificate.")
            return redirect("students:student_dashboard")
            
        except Enrollment.DoesNotExist:
            messages.error(request, "Enrollment not found.")
            return redirect("students:student_dashboard")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect("students:student_dashboard")
    
    return redirect("students:student_dashboard")


# ==========================
# STUDENT LOGIN
# ==========================
def student_login(request):
    from django.contrib.auth import login, authenticate
    from accounts.models import CustomUser
    
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            student = CustomUser.objects.get(email=email, user_type='student')
            
            # Authenticate with username and password
            user = authenticate(request, username=student.username, password=password)

            if user is not None:
                login(request, user)
                return redirect("students:student_dashboard")
            else:
                return render(request, "student/login.html", {
                    "error": "Invalid password"
                })

        except CustomUser.DoesNotExist:

            return render(request,"student/login.html",
                          {"error":"Student account not found"})

    return render(request,"student/login.html")

