from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser
from institute.models import Institute
import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib.auth import login
from .models import CustomUser

# ==========================
# STUDENT REGISTER - OTP VERIFICATION
# ==========================

def student_register(request):
    """Step 1: Show registration form to enter email for OTP"""
    if request.method == "POST":
        email = request.POST.get("email")
        
        if CustomUser.objects.filter(email=email).exists():
            return render(request, "student/register.html", {
                "error": "Email already exists"
            })
        
        # Generate OTP and send to email
        otp = str(random.randint(100000, 999999))
        
        # Store temporarily in session
        request.session['student_reg_email'] = email
        request.session['student_reg_otp'] = otp
        
        try:
            send_mail(
                "CertiVault Registration OTP",
                f"Your registration OTP is: {otp}",
                "certivault@gmail.com",
                [email],
                fail_silently=False
            )
        except:
            # For testing, show OTP in console
            print(f"OTP for {email}: {otp}")
        
        return redirect("verify_student_register_otp")
    
    return render(request, "student/register.html")


def verify_student_register_otp(request):
    """Step 2: Verify OTP and set password"""
    if request.method == "POST":
        otp = request.POST.get("otp")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        
        stored_otp = request.session.get('student_reg_otp')
        email = request.session.get('student_reg_email')
        
        if otp != stored_otp:
            return render(request, "student/verify_register_otp.html", {
                "error": "Invalid OTP"
            })
        
        if password != confirm_password:
            return render(request, "student/verify_register_otp.html", {
                "error": "Passwords do not match"
            })
        
        if len(password) < 6:
            return render(request, "student/verify_register_otp.html", {
                "error": "Password must be at least 6 characters"
            })
        
        # Create username from email
        username = email.split('@')[0]
        
        # Create student user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type="student"
        )
        
        # Create Student record with email
        from students.models import Student
        Student.objects.create(
            user=user,
            student_id=f"STU{user.id}",  # Generate student ID based on user ID
            full_name=username,  # Use username as temporary full name
            email=email,
            phone="",  # Placeholder - to be updated later
            address=""  # Placeholder - to be updated later
        )
        
        # Clear session
        del request.session['student_reg_email']
        del request.session['student_reg_otp']
        
        messages.success(request, "Registration successful! Please login.")
        return redirect("students:student_login")
    
    return render(request, "student/verify_register_otp.html")


# ==========================
# INSTITUTION REGISTER
# ==========================
def institute_register(request):

    if request.method == "POST":

        try:
            username = request.POST.get("username")
            password = request.POST.get("password")

            institute_name = request.POST.get("institute_name")
            institute_code = request.POST.get("institute_code")
            affiliation = request.POST.get("affiliation")
            type_inst = request.POST.get("type")
            established_year = request.POST.get("established_year")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            website = request.POST.get("website")
            address = request.POST.get("address")
            admin_name = request.POST.get("admin_name")
            designation = request.POST.get("designation")
            govt_reg_no = request.POST.get("govt_reg_no")
            accreditation = request.POST.get("accreditation")

            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return render(request, "accounts/institution_register.html")

            # Create login account
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                user_type="institution"
            )

            # Create institute profile
            institute = Institute.objects.create(
                user=user,
                institute_name=institute_name,
                institute_code=institute_code,
                affiliation=affiliation,
                type=type_inst,
                established_year=int(established_year) if established_year else None,
                email=email,
                phone=phone,
                website=website,
                address=address,
                admin_name=admin_name,
                designation=designation,
                govt_reg_no=govt_reg_no,
                accreditation=accreditation,
                logo=request.FILES.get("logo"),
                signature=request.FILES.get("signature"),
                provided_courses=request.POST.get("provided_courses", ""),
            )

            # Handle course entries
            from institute.models import Course
            course_count = int(request.POST.get("course_count", 0))
            
            for i in range(1, course_count + 1):
                course_name = request.POST.get(f"course_name_{i}")
                duration = request.POST.get(f"duration_{i}")
                
                if course_name and duration:
                    Course.objects.create(
                        institute=institute,
                        course_name=course_name,
                        duration_months=int(duration)
                    )

            messages.success(request, "Registration submitted. Wait for approval.")
            return redirect("/accounts/institution/login/")
            
        except Exception as e:
            # Print error for debugging
            print(f"Registration Error: {str(e)}")
            messages.error(request, f"Registration error: {str(e)}")
            return render(request, "accounts/institution_register.html")

    return render(request, "accounts/institution_register.html")

# ==========================
# INSTITUTION LOGIN
# ==========================
def institution_login(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.user_type == "institution":
            login(request, user)
            return redirect("institution_dashboard")
        else:
            return render(request, "accounts/institution_login.html", {
                "error": "Invalid credentials or not an Institution"
            })

    return render(request, "accounts/institution_login.html")


# ==========================
# INSTITUTION DASHBOARD
# ==========================
@login_required
def institution_dashboard(request):

    if request.user.user_type != "institution":
        return redirect("institution_login")

    # import inside to avoid circular at module load
    from institute.forms import InstituteCertificateForm
    from institute.models import InstituteCertificate
    from blockchain.utils import store_hash_on_blockchain, verify_hash_from_blockchain
    import hashlib
    from django.db import IntegrityError

    # statistics
    total_issued = InstituteCertificate.objects.filter(institute=request.user).count()
    # placeholder values for pending/verified; adjust if you add status fields later
    pending = 0
    verified = 0

    # Get all certificates for this institute
    certificates = InstituteCertificate.objects.filter(institute=request.user).order_by('-created_at')

    form = InstituteCertificateForm()

    if request.method == "POST":
        form = InstituteCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert_file = form.cleaned_data['certificate_file']
            sha = hashlib.sha256()
            for chunk in cert_file.chunks():
                sha.update(chunk)
            hash_value = sha.hexdigest()
            try:
                cert_file.seek(0)
            except Exception:
                pass

            if InstituteCertificate.objects.filter(certificate_hash=hash_value).exists():
                messages.error(request, "Certificate with same content already issued.")
                return redirect("institution_dashboard")

            try:
                tx_hash = store_hash_on_blockchain(hash_value)
            except Exception as e:
                messages.error(request, f"Blockchain error: {str(e)}")
                return redirect("institution_dashboard")

            # verify immediately after sending
            verified = False
            try:
                verified = verify_hash_from_blockchain(hash_value)
            except Exception:
                # if verify call fails we'll still record but mark unverified
                verified = False

            try:
                inst_cert = form.save(commit=False)
                inst_cert.institute = request.user
                inst_cert.certificate_hash = hash_value
                inst_cert.blockchain_tx_hash = tx_hash
                inst_cert.save()
            except IntegrityError:
                messages.error(request, "Duplicate certificate hash detected.")
                return redirect("institution_dashboard")

            request.session['last_tx_hash'] = tx_hash
            request.session['last_verified'] = verified
            messages.success(request, "Certificate issued and stored on blockchain.")
            return redirect("institution_dashboard")

    # pull tx hash and verification status from session if available
    last_tx = request.session.pop('last_tx_hash', None)
    last_verified = request.session.pop('last_verified', None)
    return render(request, "institute/institution_dashboard.html", {
        "form": form,
        "total_issued": total_issued,
        "pending": pending,
        "verified": verified,
        "last_tx_hash": last_tx,
        "last_verified": last_verified,
        "certificates": certificates,
    })


# ==========================
# USER REGISTER
# ==========================
def user_register(request):

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if CustomUser.objects.filter(username=username).exists():
            return render(request, "accounts/user_register.html", {
                "error": "Username already exists"
            })

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type="user"
        )

        login(request, user)
        return redirect("user_dashboard")

    return render(request, "accounts/user_register.html")


# ==========================
# USER LOGIN
# ==========================
def user_login(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.user_type == "user":
            login(request, user)
            return redirect("user_dashboard")
        else:
            return render(request, "accounts/user_login.html", {
                "error": "Invalid credentials or not a User"
            })

    return render(request, "accounts/user_login.html")


# ==========================
# USER DASHBOARD
# ==========================
@login_required
def user_dashboard(request):

    if request.user.user_type != "user":
        return redirect("user_login")

    # Import blockchain functions here to avoid import errors
    from blockchain.utils import verify_hash_from_blockchain
    from institute.models import Certificate
    from users.models import VerificationHistory
    import hashlib

    result = None
    certificate_data = None

    if request.method == "POST":

        certificate_file = request.FILES.get("certificate")

        if certificate_file:

            # Generate SHA256 hash
            file_data = certificate_file.read()
            hash_value = hashlib.sha256(file_data).hexdigest()
            certificate_file.seek(0)

            try:
                # Verify from blockchain
                is_valid = verify_hash_from_blockchain(hash_value)

                if is_valid:
                    result = "VALID"

                    # Fetch certificate details
                    certificate_data = Certificate.objects.filter(
                        certificate_hash=hash_value
                    ).first()

                else:
                    result = "INVALID"

                # Save verification history
                VerificationHistory.objects.create(
                    user=request.user,
                    certificate_id=hash_value,
                    result=result
                )

            except Exception as e:
                error_msg = str(e)
                # Check if it's a connection error
                if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                    result = "⚠️ Blockchain not connected. Please start Ganache to verify certificates."
                else:
                    result = f"Blockchain Error: {error_msg}"

    return render(request, "users/user_dashboard.html", {
        "result": result,
        "certificate": certificate_data
    })


# ==========================
# LOGOUT
# ==========================
def user_logout(request):
    logout(request)
    return redirect("/")


# ==========================
# ADMIN LOGIN
# ==========================
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.user_type == "admin":
            login(request, user)
            return redirect("admin_dashboard")
        else:
            return render(request, "accounts/admin_login.html", {
                "error": "Invalid credentials or not an Admin"
            })

    return render(request, "accounts/admin_login.html")


# ==========================
# ADMIN DASHBOARD
# ==========================
@login_required
def admin_dashboard(request):
    if request.user.user_type != "admin":
        return redirect("admin_login")

    # Import models
    from institute.models import Institute
    from students.models import Student, Enrollment, CertificateRequest
    from accounts.models import CustomUser

    # Get statistics
    # Institutes
    total_institutes = Institute.objects.count()
    pending_institutes = Institute.objects.filter(status='Pending').count()
    approved_institutes = Institute.objects.filter(status='Approved').count()
    rejected_institutes = Institute.objects.filter(status='Rejected').count()

    # Students
    total_students = Student.objects.count()

    # Enrollments
    total_enrollments = Enrollment.objects.count()
    pending_enrollments = Enrollment.objects.filter(status='Pending').count()
    approved_enrollments = Enrollment.objects.filter(status='Approved').count()
    completed_enrollments = Enrollment.objects.filter(status='Completed').count()

    # Certificate Requests
    pending_cert_requests = CertificateRequest.objects.filter(status='Pending').count()

    # Recent institute registrations
    recent_institutes = Institute.objects.order_by('-created_at')[:10]

    # Recent enrollments
    recent_enrollments = Enrollment.objects.select_related('student', 'course', 'institute').order_by('-created_at')[:10]

    # Recent certificate requests
    recent_cert_requests = CertificateRequest.objects.select_related(
        'enrollment', 'enrollment__student', 'enrollment__course', 'enrollment__institute'
    ).order_by('-request_date')[:10]

    context = {
        # Institute stats
        'total_institutes': total_institutes,
        'pending_institutes': pending_institutes,
        'approved_institutes': approved_institutes,
        'rejected_institutes': rejected_institutes,

        # Student stats
        'total_students': total_students,

        # Enrollment stats
        'total_enrollments': total_enrollments,
        'pending_enrollments': pending_enrollments,
        'approved_enrollments': approved_enrollments,
        'completed_enrollments': completed_enrollments,

        # Certificate stats
        'pending_cert_requests': pending_cert_requests,

        # Recent data
        'recent_institutes': recent_institutes,
        'recent_enrollments': recent_enrollments,
        'recent_cert_requests': recent_cert_requests,
    }

    return render(request, "accounts/admin_dashboard.html", context)


# ==========================
# APPROVE/REJECT INSTITUTE
# ==========================
@login_required
def approve_institute(request, institute_id, action):
    if request.user.user_type != "admin":
        return redirect("admin_login")

    try:
        institute = Institute.objects.get(id=institute_id)

        if action == 'approve':
            institute.status = 'Approved'
            institute.save()
            messages.success(request, f"Institute '{institute.institute_name}' has been approved.")
        elif action == 'reject':
            institute.status = 'Rejected'
            institute.save()
            messages.error(request, f"Institute '{institute.institute_name}' has been rejected.")

        return redirect("admin_dashboard")

    except Institute.DoesNotExist:
        messages.error(request, "Institute not found.")
        return redirect("admin_dashboard")
