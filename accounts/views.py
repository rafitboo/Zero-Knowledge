import json
import logging
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    ProfileSerializer,
    decrypt_user_email,
    encrypt_user_email,
)
from .utils import generate_jwt_token, generate_otp, generate_password_salt, combine_password_and_salt
from django.utils import timezone
from accounts.permissions import IsAdminRole
from accounts.authentication import JWTAuthentication
from network.models import Post


from rest_framework.permissions import AllowAny, IsAuthenticated
from crypto_engine.rsa_core import encrypt

logger = logging.getLogger(__name__)


def _get_user_email(user):
    # Return decrypted email
    try:
        return decrypt_user_email(user)
    except Exception:
        return user.email or ""


def _email_exists(candidate_email, exclude_user_id=None):
    # Check email uniqueness against encrypted values.
    normalized = (candidate_email or "").strip().lower()
    if not normalized:
        return False

    queryset = User.objects.all()
    if exclude_user_id is not None:
        queryset = queryset.exclude(id=exclude_user_id)

    for other in queryset:
        try:
            other_email = _get_user_email(other)
        except Exception:
            continue
        if other_email and other_email.strip().lower() == normalized:
            return True
    return False


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            
            # 1. Generate keys and encrypts contact info
            user = serializer.save()
            
            # 2. Generate and save OTP
            otp = generate_otp()
            user.otp_code = otp
            user.otp_created_at = timezone.now()
            user.save()
            # print OTP in terminal for testing
            try:
                print(f"🔐 REGISTRATION OTP for user {user.username}: {otp}")
                print(f"📧 Sent to: {_get_user_email(user)}")
            except Exception:
               
                logger.exception("Failed to print OTP to console")
            logger.info("Registration OTP generated for %s (email=%s)", user.username, _get_user_email(user))
            # 3. Send OTP to user's email 
            try:
                recipient_email = _get_user_email(user)
                send_mail(
                    subject="Your ZK Login OTP",
                    message=f"Your one-time login code is: {otp}\nThis code expires in 10 minutes.",
                    from_email="noreply@zk.local",
                    recipient_list=[recipient_email] if recipient_email else [],
                    fail_silently=True,
                )
            except Exception:
                logger.exception("Failed to send login OTP email")
            
            return Response({
                "message": "User registered successfully.",
                "warning": "Verify your email with the OTP to activate your account."
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp_code')
        
        try:
            user = User.objects.get(username=username)
            
            # Check expiry (10 minutes)
            if not user.otp_code or user.otp_code != otp:
                return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

            if user.otp_created_at and timezone.now() - user.otp_created_at > timedelta(minutes=10):

                # Expired OTP
                user.otp_code = None
                user.otp_created_at = None
                user.save()
                return Response({"error": "OTP expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

            # Valid OTP for registration/email verification
            user.is_email_verified = True
            user.otp_code = None 
            user.otp_created_at = None
            user.save()
            return Response({"message": "Email verified successfully. You can now login."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = User.objects.filter(username=username).first()
        if user and not user.is_active:
            return Response(
                {"error": "Your account is banned. Please contact an administrator."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_valid = False
        if user is not None:
            if user.password_salt:
                salted_password = combine_password_and_salt(password, user.password_salt)
                is_valid = check_password(salted_password, user.password)
            else:
                is_valid = check_password(password, user.password)

        if user is not None and is_valid:
            # Enforce two-factor
            otp = generate_otp()
            user.otp_code = otp
            user.otp_created_at = timezone.now()
            user.save()

            # Print OTP to terminal
            try:
                print(f"🔐 LOGIN OTP for user {user.username}: {otp}")
                print(f"📧 Sent to: {_get_user_email(user)}")
            except Exception:
                logger.exception("Failed to print OTP to console")

            # Send OTP to user's email
            try:
                recipient_email = _get_user_email(user)
                send_mail(
                    subject="Your ZK Login OTP",
                    message=f"Your one-time login code is: {otp}\nThis code expires in 10 minutes.",
                    from_email="noreply@zk.local",
                    recipient_list=[recipient_email] if recipient_email else [],
                    fail_silently=True,
                )
            except Exception:
                logger.exception("Failed to send login OTP email")

            return Response({
                "message": "OTP sent to your email. Verify OTP to complete login.",
                "username": user.username
            }, status=status.HTTP_200_OK)
            
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)


@method_decorator(csrf_exempt, name='dispatch')
class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        # Fetch profile
        user = User.objects.get(id=request.user.id)
        serializer = ProfileSerializer(user, context={'request': request})
        profile_data = dict(serializer.data)
        profile_data['email'] = decrypt_user_email(user) or user.email or profile_data.get('email', '')
        return Response(profile_data, status=status.HTTP_200_OK)

    def patch(self, request):
        # Update profile 
        user = User.objects.get(id=request.user.id)
        email = request.data.get('email', '').strip() if request.data.get('email') else None
        new_contact_raw = request.data.get('contact_info')
        password = request.data.get('password')

        updated_fields = []

        # 1. Handle Email Change (requires OTP verification)
        if email:
            if _email_exists(email, exclude_user_id=user.id):
                return Response({"error": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)

            current_email = _get_user_email(user)
            if email != current_email:
                
                # Generate OTP for email verification
                otp = generate_otp()
                user.pending_email = None
                user.pending_encrypted_email = encrypt_user_email(user, email)
                user.pending_email_otp = otp
                
                # Print OTP 
                print(f"🔐 EMAIL VERIFICATION OTP: {otp}")
                print(f"📧 Sent to: {email}")
                
                # Send email 
                try:
                    send_mail(
                        subject="Verify Your New Email - ZK",
                        message=f"Your OTP to verify email change is: {otp}\n\nThis OTP will expire in 10 minutes.",
                        from_email="noreply@zk.local",
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"⚠️  Email sending failed (this is OK for testing): {str(e)}")
                
                updated_fields.append('email_verification_pending')
            
        # 2. Handle Contact Info Encryption
        if new_contact_raw is not None and new_contact_raw.strip():
            try:
                pub_key = tuple(json.loads(user.rsa_public_key))
                encrypted_array = encrypt(pub_key, new_contact_raw.strip())
                user.encrypted_contact_info = json.dumps(encrypted_array)
                updated_fields.append('contact_info')
                print(f"📱 Contact info encrypted and saved for user {user.username}")
            except Exception as e:
                return Response({"error": f"Encryption failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Update password if provided
        if password:
            password_salt = generate_password_salt()
            user.password_salt = password_salt
            user.set_password(combine_password_and_salt(password, password_salt))
            updated_fields.append('password')

        # 4. Save all changes
        if updated_fields:
            user.save()
            
            # If email is pending, return special response
            if 'email_verification_pending' in updated_fields:
                return Response({
                    "message": "OTP sent to new email. Verify it to complete email change.",
                    "updated_fields": updated_fields,
                    "pending_email": email
                }, status=status.HTTP_200_OK)
            
            return Response({
                "message": "Profile updated successfully.",
                "updated_fields": updated_fields
            }, status=status.HTTP_200_OK)
        
        return Response({
            "message": "No changes provided.",
            "updated_fields": []
        }, status=status.HTTP_200_OK)
    

class VerifyEmailChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Verify OTP for email change
        user = User.objects.get(id=request.user.id)
        otp = request.data.get('otp')
        
        if not user.pending_email:
            if not user.pending_encrypted_email:
                return Response({"error": "No pending email change."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not otp:
            return Response({"error": "OTP is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.pending_email_otp != otp:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        
        # OTP is valid - update email
        if user.pending_encrypted_email:
            user.encrypted_email = user.pending_encrypted_email
        elif user.pending_email:
            user.encrypted_email = encrypt_user_email(user, user.pending_email)
        user.email = ""
        user.pending_email = None
        user.pending_encrypted_email = None
        user.pending_email_otp = None
        user.save()
        
        return Response({
            "message": "Email verified and updated successfully.",
            "new_email": _get_user_email(user)
        }, status=status.HTTP_200_OK)


class LoginVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if not otp or not user.otp_code:
            return Response({"error": "OTP required or not requested."}, status=status.HTTP_400_BAD_REQUEST)

        if user.otp_code != otp:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if user.otp_created_at and timezone.now() - user.otp_created_at > timedelta(minutes=10):
            user.otp_code = None
            user.otp_created_at = None
            user.save()
            return Response({"error": "OTP expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        token = generate_jwt_token(user)
        user.otp_code = None
        user.otp_created_at = None
        user.save()

        return Response({
            "message": "Login successful",
            "token": token,
            "role": user.role
        }, status=status.HTTP_200_OK)
    
    
class SystemAuditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole] 

    def get(self, request):
        
        # Only ADMIN can access this. 
        
        total_users = User.objects.count()
        total_posts = Post.objects.count()
        
        return Response({
            "status": "CLASSIFIED_AUDIT_GRANTED",
            "admin_user": request.user.username,
            "metrics": {
                "total_operatives": total_users,
                "total_encrypted_broadcasts": total_posts
            }
        }, status=status.HTTP_200_OK)