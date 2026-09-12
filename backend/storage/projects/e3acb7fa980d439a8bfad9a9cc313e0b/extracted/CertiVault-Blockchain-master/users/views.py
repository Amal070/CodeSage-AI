import hashlib
from django.shortcuts import render
from blockchain.utils import verify_hash_from_blockchain
from institute.models import Certificate
from students.models import Enrollment
from .models import VerificationHistory


def home(request):
    return render(request, 'home.html')



# @login_required
# def user_dashboard(request):

#     result = None

#     if request.method == "POST":

#         cert_id = request.POST.get("certificate_id")
#         uploaded_file = request.FILES.get("certificate")

#         if not cert_id or not uploaded_file:
#             result = "Please provide Certificate ID and file ❌"

#         else:
#             generated_hash = generate_file_hash(uploaded_file)

#             web3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_URL))

#             contract = web3.eth.contract(
#                 address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
#                 abi=settings.CONTRACT_ABI
#             )

#             try:
#                 stored_hash = contract.functions.getCertificateHash(cert_id).call()
#             except Exception:
#                 result = "Blockchain connection failed ❌"
#                 return render(request, "users/dashboard.html", {"result": result})

#             if stored_hash == "":
#                 result = "Certificate not found on Blockchain ❌"
#             elif generated_hash == stored_hash:
#                 result = "Certificate is VALID ✅"
#             else:
#                 result = "Certificate is TAMPERED ❌"

#             VerificationHistory.objects.create(
#                 user=request.user,
#                 certificate_id=cert_id,
#                 result=result
#             )

#     history = VerificationHistory.objects.filter(
#         user=request.user
#     ).order_by("-verified_at")

#     return render(request, "users/dashboard.html", {
#         "result": result,
#         "history": history
#     })




def user_dashboard(request):
    return render(request, "users/user_dashboard.html")


def verify_certificate(request):

    result = None
    certificate_data = None
    certificate_type = None

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

                    # Try to find certificate in InstituteCertificate model
                    from institute.models import InstituteCertificate
                    certificate_data = InstituteCertificate.objects.filter(
                        certificate_hash=hash_value
                    ).first()
                    
                    if certificate_data:
                        certificate_type = "institute"
                    else:
                        # Try to find certificate in Enrollment model using certificate_hash (efficient lookup)
                        enrollment = Enrollment.objects.filter(
                            certificate_hash=hash_value,
                            certificate_generated=True
                        ).first()
                        
                        if enrollment:
                            certificate_data = enrollment
                            certificate_type = "student"

                else:
                    result = "INVALID"

                # Save verification history
                if request.user.is_authenticated:
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

    return render(request, "users/verify_certificate.html", {
        "result": result,
        "certificate": certificate_data,
        "certificate_type": certificate_type
    })
