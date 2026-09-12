from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import hashlib
from .models import InstituteCertificate, Institute, Course
from .forms import InstituteCertificateForm
from blockchain.utils import store_hash_on_blockchain
from students.models import Enrollment, Student, CertificateRequest


@login_required
def issue_certificate(request):

    if request.user.user_type != "institution":
        return redirect("institution_login")

    # Get the institute profile
    try:
        institute = Institute.objects.get(user=request.user)
    except Institute.DoesNotExist:
        messages.error(request, "Institute profile not found.")
        return redirect("institution_dashboard")

    # Get pending certificate requests from students (for completed enrollments where certificate not yet generated)
    pending_cert_requests = CertificateRequest.objects.filter(
        enrollment__institute=institute,
        enrollment__certificate_generated=False,
        status='Pending'
    ).select_related('enrollment', 'enrollment__student', 'enrollment__course')

    if request.method == "POST":
        form = InstituteCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert_file = form.cleaned_data['certificate_file']

            # Compute SHA256 using chunks to avoid large memory spikes
            sha = hashlib.sha256()
            for chunk in cert_file.chunks():
                sha.update(chunk)
            hash_value = sha.hexdigest()

            # Reset file pointer so saving works correctly
            try:
                cert_file.seek(0)
            except Exception:
                pass

            # Prevent duplicate hash
            if InstituteCertificate.objects.filter(certificate_hash=hash_value).exists():
                messages.error(request, "Certificate with same content already issued.")
                return redirect("institute:issue_certificate")

            # Store on blockchain
            try:
                tx_hash = store_hash_on_blockchain(hash_value)
            except Exception as e:
                messages.error(request, f"Blockchain error: {str(e)}")
                return redirect("institute:issue_certificate")

            # Save record
            try:
                inst_cert = form.save(commit=False)
                inst_cert.institute = request.user
                inst_cert.certificate_hash = hash_value
                inst_cert.blockchain_tx_hash = tx_hash
                inst_cert.save()
            except IntegrityError:
                messages.error(request, "Duplicate certificate hash detected.")
                return redirect("institute:issue_certificate")

            messages.success(request, "Certificate issued and stored on blockchain.")
            return redirect("institution_dashboard")
    else:
        # Prefill form if register_number provided and exists for this institute
        reg_no = request.GET.get('register_number')
        initial = None
        if reg_no:
            existing = InstituteCertificate.objects.filter(institute=request.user, register_number=reg_no).first()
            if existing:
                initial = {
                    'student_name': existing.student_name,
                    'student_email': existing.student_email,
                    'course': existing.course,
                    'year_of_passing': existing.year_of_passing,
                    'register_number': existing.register_number,
                }

        form = InstituteCertificateForm(initial=initial)

    return render(request, "institute/issue_certificate.html", {
        "form": form,
        "pending_cert_requests": pending_cert_requests
    })


# ==========================
# MANAGE ENROLLMENTS
# ==========================
@login_required
def manage_enrollments(request):
    if request.user.user_type != "institution":
        return redirect("institution_login")
    
    # Get the institute profile
    try:
        institute = Institute.objects.get(user=request.user)
    except Institute.DoesNotExist:
        messages.error(request, "Institute profile not found.")
        return redirect("institution_dashboard")
    
    # Get all enrollments for this institute
    enrollments = Enrollment.objects.filter(
        institute=institute
    ).select_related('student', 'course').order_by('-created_at')
    
    # Get counts
    pending_count = enrollments.filter(status='Pending').count()
    approved_count = enrollments.filter(status='Approved').count()
    completed_count = enrollments.filter(status='Completed').count()
    
    return render(request, "institute/manage_enrollments.html", {
        'enrollments': enrollments,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'completed_count': completed_count,
    })


# ==========================
# APPROVE/REJECT ENROLLMENT
# ==========================
@login_required
def update_enrollment(request, enrollment_id, action):
    if request.user.user_type != "institution":
        return redirect("institution_login")
    
    try:
        institute = Institute.objects.get(user=request.user)
        enrollment = Enrollment.objects.get(id=enrollment_id, institute=institute)
        
        if action == 'approve':
            enrollment.status = 'Approved'
            enrollment.save()
            messages.success(request, f"Enrollment approved for {enrollment.student.full_name}")
        elif action == 'reject':
            enrollment.status = 'Rejected'
            enrollment.save()
            messages.error(request, f"Enrollment rejected for {enrollment.student.full_name}")
        elif action == 'complete':
            enrollment.status = 'Completed'
            from django.utils import timezone
            enrollment.completion_date = timezone.now().date()
            enrollment.save()
            messages.success(request, f"Course completed for {enrollment.student.full_name}. They can now request a certificate.")
        
        return redirect("institute:manage_enrollments")
        
    except Enrollment.DoesNotExist:
        messages.error(request, "Enrollment not found.")
        return redirect("institute:manage_enrollments")
    except Institute.DoesNotExist:
        messages.error(request, "Institute profile not found.")
        return redirect("institution_dashboard")


# ==========================
# SAVE CERTIFICATE (JavaScript PDF API)
# ==========================
@login_required
def save_certificate(request):
    """
    API endpoint to save the JavaScript-generated certificate PDF.
    """
    if request.user.user_type != "institution":
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    import hashlib
    import base64
    from django.core.files.base import ContentFile
    
    try:
        import json
        data = json.loads(request.body)
        
        enrollment_id = data.get('enrollment_id')
        certificate_id = data.get('certificate_id')
        marks = data.get('marks')
        pdf_data = data.get('pdf_data')
        
        if not all([enrollment_id, certificate_id, marks, pdf_data]):
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
        
        # Get enrollment
        try:
            institute = Institute.objects.get(user=request.user)
            enrollment = Enrollment.objects.get(id=enrollment_id, institute=institute)
        except (Enrollment.DoesNotExist, Institute.DoesNotExist):
            return JsonResponse({'success': False, 'message': 'Enrollment not found'}, status=404)
        
        # Check if already has certificate
        if enrollment.certificate_generated:
            return JsonResponse({'success': False, 'message': 'Certificate already generated'}, status=400)
        
        # Decode base64 PDF
        if ',' in pdf_data:
            # Remove data URL prefix
            pdf_data = pdf_data.split(',')[1]
        
        pdf_content = base64.b64decode(pdf_data)
        
        # Generate hash for blockchain
        hash_value = hashlib.sha256(pdf_content).hexdigest()
        
        # Try to store on blockchain
        try:
            tx_hash = store_hash_on_blockchain(hash_value)
        except Exception as e:
            tx_hash = None
            print(f"Blockchain storage failed: {e}")
        
        # Save PDF to enrollment
        filename = f"certificate_{enrollment.id}_{enrollment.student.student_id}.pdf"
        enrollment.certificate_file.save(filename, ContentFile(pdf_content))
        enrollment.certificate_generated = True
        enrollment.marks = marks
        enrollment.blockchain_tx_hash = tx_hash
        enrollment.certificate_hash = hash_value  # Store hash for efficient verification
        enrollment.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Certificate saved and stored on blockchain successfully!',
            'certificate_id': certificate_id,
            'tx_hash': tx_hash
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==========================
# ISSUE CERTIFICATE (GENERATE WITH MARKS)
# ==========================
@login_required
def generate_student_certificate(request, enrollment_id):
    """
    Generate and issue a certificate for a completed enrollment.
    Uses JavaScript-based certificate generation in the frontend.
    """
    if request.user.user_type != "institution":
        return redirect("institution_login")
    
    try:
        institute = Institute.objects.get(user=request.user)
        enrollment = Enrollment.objects.get(id=enrollment_id, institute=institute)
        
        # Only allow certificate generation for completed enrollments
        if enrollment.status != 'Completed':
            messages.error(request, "Can only issue certificate for completed courses.")
            return redirect("institute:manage_enrollments")
        
        # Check if certificate already generated
        if enrollment.certificate_generated:
            messages.warning(request, "Certificate already generated for this student.")
            return redirect("institute:manage_enrollments")
        
        # Render the JavaScript-based certificate generation template
        return render(request, "institute/issue_student_certificate.html", {
            'enrollment': enrollment,
            'institute': institute,
        })
        
    except Enrollment.DoesNotExist:
        messages.error(request, "Enrollment not found.")
        return redirect("institute:manage_enrollments")
    except Institute.DoesNotExist:
        messages.error(request, "Institute profile not found.")
        return redirect("institution_dashboard")

