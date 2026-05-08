import jwt
import datetime
import random
import secrets
from django.conf import settings

def generate_jwt_token(user):
    
    #Generate JWT token
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role, # Baking RBAC into the token
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), # Expires in 1 day
        'iat': datetime.datetime.utcnow(),
    }
    
    # Encode using HS256 (HMAC with SHA-256)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

def generate_otp():
    # Generate 6-digit random OTP.
    
    return str(random.randint(100000, 999999))


def generate_password_salt():
    
    # Generate secure random salt for password
    return secrets.token_hex(16)


def combine_password_and_salt(raw_password, salt):
    # Combines raw password and salt before hashing
    return f"{raw_password}{salt}"