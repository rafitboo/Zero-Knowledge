import json
import logging
from rest_framework import serializers
from .models import User
from crypto_engine.rsa_core import generate_keypair, encrypt, decrypt
from crypto_engine.server_keyring import wrap_user_private_key, unwrap_user_private_key
from network.models import Post
from .utils import generate_password_salt, combine_password_and_salt

logger = logging.getLogger(__name__)

def decrypt_user_email(user):
    if not user.encrypted_email:
        return user.email or ""

    if not user.encrypted_rsa_private_key:
        return ""

    user_priv = unwrap_user_private_key(user.encrypted_rsa_private_key)
    ciphertext = json.loads(user.encrypted_email)
    return decrypt(user_priv, ciphertext)


def encrypt_user_email(user, email_plaintext):
    public_key = tuple(json.loads(user.rsa_public_key))
    encrypted_array = encrypt(public_key, email_plaintext)
    return json.dumps(encrypted_array)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    contact_info = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role', 'contact_info')

    def create(self, validated_data):
        contact_info = validated_data.pop('contact_info', 'No contact info provided.')
        raw_email = validated_data.pop('email')
        raw_password = validated_data.pop('password')
        
        # 1. Generate the RSA Key Pair 
        public_key, private_key = generate_keypair(keysize=256)
        
        # 2. Encrypt user's contact info
        encrypted_info_array = encrypt(public_key, contact_info)
        
        # 3. Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email='',
            password=None,
            role=validated_data.get('role', 'USER')
        )

        # Salt and hash pass
        password_salt = generate_password_salt()
        user.password_salt = password_salt
        user.set_password(combine_password_and_salt(raw_password, password_salt))
        
        # 4. Save encrypted data 
        user.rsa_public_key = json.dumps(public_key)
        user.encrypted_contact_info = json.dumps(encrypted_info_array)
        user.encrypted_email = encrypt_user_email(user, raw_email)
        
        # 5. Wrap the user's RSA private key with server public key 
        try:
            wrapped = wrap_user_private_key(private_key)
            user.encrypted_rsa_private_key = json.dumps(wrapped)
        except Exception:
            logger.error(f"Failed to wrap RSA private key for user {user.id}")
            user.encrypted_rsa_private_key = None
        user.save()
        
   
        user.temporary_private_key = private_key
        
        return user




class UserSerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_active', 'post_count', 'is_email_verified']

    def get_post_count(self, obj):
        return Post.objects.filter(author=obj).count()

    def get_email(self, obj):
        try:
            return decrypt_user_email(obj)
        except Exception as e:
            logger.warning(f"Failed to decrypt email for user {obj.id}: {str(e)}")
            return "[ENCRYPTED]"


class ProfileSerializer(serializers.ModelSerializer):
    """
    Handles profile serialization with encrypted contact info.
    On GET: Shows decrypted contact info if private key is provided in request headers
    On PATCH: Accepts decrypted contact info and encrypts it before saving
    """
    contact_info = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_email_verified', 'contact_info']
        read_only_fields = ['id', 'role', 'is_email_verified']

    def get_contact_info(self, obj):
        """
        Attempts to decrypt contact info if private key is provided.
        Returns decrypted string or "[ENCRYPTED]" if key not available.
        """
        request = self.context.get('request')
        if not request or not obj.encrypted_contact_info:
            return "[NO_DATA]"
        
        # First try: client-supplied private key via header
        priv_key_raw = request.headers.get('X-RSA-Private-Key')
        if priv_key_raw:
            try:
                private_key = tuple(json.loads(priv_key_raw))
                ciphertext = json.loads(obj.encrypted_contact_info)
                decrypted = decrypt(private_key, ciphertext)
                return decrypted
            except Exception as e:
                logger.warning(f"Failed to decrypt contact info with header key for user {obj.id}: {str(e)}")

        # Second try: server-unwrapping (transparent) using wrapped private key stored in DB
        if obj.encrypted_rsa_private_key:
            try:
                user_priv = unwrap_user_private_key(obj.encrypted_rsa_private_key)
                ciphertext = json.loads(obj.encrypted_contact_info)
                decrypted = decrypt(user_priv, ciphertext)
                return decrypted
            except Exception as e:
                logger.warning(f"Server unwrap/decrypt failed for user {obj.id}: {str(e)}")

        return "[ENCRYPTED]"

    def get_email(self, obj):
        try:
            decrypted_email = decrypt_user_email(obj)
            if decrypted_email:
                return decrypted_email
            return obj.email or ""
        except Exception as e:
            logger.warning(f"Failed to decrypt email for profile user {obj.id}: {str(e)}")
            return obj.email or "[ENCRYPTED]"

    def update(self, instance, validated_data):
        """
        Update profile fields. Handles email and contact_info specially.
        Contact info is encrypted before saving.
        """
        email = validated_data.get('email', instance.email)
        contact_info_raw = self.initial_data.get('contact_info')
        
        # Update email if provided
        if email:
            try:
                current_email = decrypt_user_email(instance)
            except Exception:
                current_email = ''
            if email != current_email:
                # Email update is handled separately in views with OTP verification
                instance.encrypted_email = encrypt_user_email(instance, email)
        
        # Handle contact info encryption if provided
        if contact_info_raw is not None and contact_info_raw.strip():
            try:
                public_key = tuple(json.loads(instance.rsa_public_key))
                encrypted_array = encrypt(public_key, contact_info_raw.strip())
                instance.encrypted_contact_info = json.dumps(encrypted_array)
            except Exception as e:
                raise serializers.ValidationError(f"Failed to encrypt contact info: {str(e)}")
        
        instance.save()
        return instance