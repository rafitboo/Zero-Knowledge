from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_active = models.BooleanField(default=True)
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('USER', 'Regular User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    encrypted_rsa_private_key = models.TextField(blank=True, null=True)
    rsa_public_key = models.TextField(blank=True, null=True)


    encrypted_contact_info = models.TextField(blank=True, null=True)
    encrypted_email = models.TextField(blank=True, null=True)
    

    pending_email = models.EmailField(blank=True, null=True)  # Temp storage for new email
    pending_email_otp = models.CharField(max_length=6, blank=True, null=True)  # OTP for email verification
    pending_encrypted_email = models.TextField(blank=True, null=True)
    password_salt = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.role}"