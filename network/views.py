import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.db.models import Q 


from .models import Post, DirectMessage, Conversation
from .serializers import PostSerializer, DirectMessageSerializer
from accounts.models import User
from accounts.authentication import JWTAuthentication
from accounts.permissions import IsAdminRole
from accounts.serializers import UserSerializer

# Cryptographic Math Engines
from crypto_engine.ecc_core import generate_ecc_keypair, encrypt_post, decrypt_post 
from crypto_engine.rsa_core import encrypt, decrypt, generate_keypair
from crypto_engine.server_keyring import _load_server_keys_from_env, wrap_user_private_key, unwrap_user_private_key
from crypto_engine.mac_core import generate_mac, verify_mac


def _get_dm_mac_secret():
    # Returns MAC secret for DM integrity
    return getattr(settings, 'DM_MAC_SECRET', settings.SECRET_KEY)


def _decrypt_posts_queryset(posts, server_priv):
    decrypted_posts = []

    for post in posts:
        try:
            wrapped_ecc_priv = json.loads(post.encrypted_ecc_private_key)
            ecc_priv_key_str = decrypt(server_priv, wrapped_ecc_priv)
            ciphertext_array = json.loads(post.encrypted_content)
            formatted_cipher = [(c[0], c[1]) for c in ciphertext_array]
            plaintext = decrypt_post(int(ecc_priv_key_str), formatted_cipher)

            decrypted_posts.append({
                "id": post.id,
                "author": post.author.username,
                "content": plaintext,
                "created_at": post.created_at,
            })
        except Exception:
            continue

    return decrypted_posts


class AdminConsoleView(TemplateView):
    template_name = 'admin_console.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all().order_by('id')
        return context


class AdminUserPostsPageView(TemplateView):
    template_name = 'admin_user_posts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = get_object_or_404(User, id=self.kwargs['user_id'])
        return context


class PostListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch all posts by unwrapping ECC private key with server RSA private key
        # Server private key is used to unwrap each post's ECC private key
        _, server_priv = _load_server_keys_from_env()
        if not server_priv:
            return Response({"error": "Server decryption key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        posts = Post.objects.all().order_by('-created_at')
        return Response(_decrypt_posts_queryset(posts, server_priv))

    def post(self, request):
        # Create a post with ECC encryption
        raw_content = request.data.get('content')
        if not raw_content:
            return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Server public key wraps ECC private key 
        server_pub, _ = _load_server_keys_from_env()
        if not server_pub:
            return Response({"error": "Server encryption key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # 1. Generate ECC keypair and encrypt content
            ecc_pub_key, ecc_priv_key = generate_ecc_keypair()
            encrypted_content = encrypt_post(ecc_pub_key, raw_content)
            # 2. Wrap ECC private key with server RSA public key
            wrapped_ecc_priv = encrypt(server_pub, str(ecc_priv_key))
            
            # 3. Store ECC ciphertext and wrapped ECC private key
            Post.objects.create(
            author=request.user,
            encrypted_content=json.dumps(encrypted_content),
            ecc_public_key=json.dumps(ecc_pub_key),
                encrypted_ecc_private_key=json.dumps(wrapped_ecc_priv)
        )
            return Response({"message": "Post created successfully."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Encryption failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class DecryptPostView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
        except Post.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        provided_private_key = request.data.get('ecc_private_key')
        if not provided_private_key:
            return Response({"error": "ECC Private Key required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ciphertext_array = json.loads(post.encrypted_content)
            formatted_cipher = [(c[0], c[1]) for c in ciphertext_array]
            plaintext = decrypt_post(int(provided_private_key), formatted_cipher)
            return Response({"decrypted_content": plaintext}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Decryption failed."}, status=status.HTTP_400_BAD_REQUEST)




class AdminUserPostsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)

        _, server_priv = _load_server_keys_from_env()
        if not server_priv:
            return Response({"error": "Server decryption key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        posts = Post.objects.filter(author=target_user).order_by('-created_at')
        return Response({
            "user": {
                "id": target_user.id,
                "username": target_user.username,
            },
            "posts": _decrypt_posts_queryset(posts, server_priv),
        }, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        post_ids = request.data.get('post_ids', [])

        if not isinstance(post_ids, list) or not post_ids:
            return Response({"error": "Select at least one post to delete."}, status=status.HTTP_400_BAD_REQUEST)

        normalized_ids = []
        for post_id in post_ids:
            try:
                normalized_ids.append(int(post_id))
            except (TypeError, ValueError):
                continue

        if not normalized_ids:
            return Response({"error": "No valid post IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = Post.objects.filter(author=target_user, id__in=normalized_ids).delete()
        return Response({
            "message": f"Deleted {deleted_count} post(s).",
            "deleted_count": deleted_count,
        }, status=status.HTTP_200_OK)


class DMPageView(TemplateView):
    template_name = 'dm.html'


 
class DirectMessageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, target_username=None):
        if not target_username:
            return Response({"error": "Target username required."}, status=status.HTTP_400_BAD_REQUEST)

        # Load server RSA private key for simple decryption
        _, server_priv = _load_server_keys_from_env()
        if not server_priv:
            return Response({"error": "Server decryption key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        after_id_raw = request.query_params.get('after_id')
        after_id = None
        if after_id_raw:
            try:
                after_id = int(after_id_raw)
            except (TypeError, ValueError):
                return Response({"error": "Invalid after_id value."}, status=status.HTTP_400_BAD_REQUEST)

        messages = DirectMessage.objects.filter(
            Q(sender=request.user, receiver__username=target_username) |
            Q(sender__username=target_username, receiver=request.user)
        ).order_by('id')

        if after_id is not None:
            messages = messages.filter(id__gt=after_id)
        
        decrypted_history = []

        for msg in messages:
            plaintext = "[MESSAGE CORRUPTED]"
            is_compromised = True
            try:
                # unwrap per-message private key and decrypt
                if msg.encrypted_rsa_private_key:
                    try:
                        wrapped = json.loads(msg.encrypted_rsa_private_key)
                        per_priv = unwrap_user_private_key(wrapped)
                        encrypted_data = json.loads(msg.encrypted_content)
                        plaintext = decrypt(per_priv, encrypted_data)
                    except Exception:
                        # Fallback to legacy server-RSA decryption below
                        encrypted_data = json.loads(msg.encrypted_content)
                        plaintext = decrypt(server_priv, encrypted_data)
                else:
                    # Legacy messages encrypted with server RSA key
                    encrypted_data = json.loads(msg.encrypted_content)
                    plaintext = decrypt(server_priv, encrypted_data)

                expected_ok = verify_mac(_get_dm_mac_secret(), plaintext, msg.mac_tag)
                is_compromised = not expected_ok
                if not expected_ok:
                    plaintext = "[MESSAGE CORRUPTED]"
            except Exception:
                plaintext = "[MESSAGE CORRUPTED]"
                is_compromised = True

            decrypted_history.append({
                "id": msg.id,
                "sender": msg.sender.username,
                "content": plaintext,
                "timestamp": msg.timestamp,
                "is_compromised": is_compromised,
            })

        return Response(decrypted_history, status=status.HTTP_200_OK)

    def post(self, request):
        receiver_username = request.data.get('receiver')
        raw_content = request.data.get('content')
        
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return Response({"error": "Receiver not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Load server RSA public key for simple encryption
        server_pub, _ = _load_server_keys_from_env()
        if not server_pub:
            return Response({"error": "Server encryption key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Simple RSA encryption with server public key
            # Create a per-message RSA keypair and wrap the private key with the server RSA
            per_pub, per_priv = generate_keypair(keysize=256)
            encrypted_content = encrypt(per_pub, raw_content)
            wrapped_priv = wrap_user_private_key(per_priv)
            mac_tag = generate_mac(_get_dm_mac_secret(), raw_content)

            msg = DirectMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                encrypted_content=json.dumps(encrypted_content),
                rsa_public_key=json.dumps(list(per_pub)),
                encrypted_rsa_private_key=json.dumps(wrapped_priv),
                mac_tag=mac_tag
            )
            return Response({
                "message": "Secure P2P message dispatched.",
                "id": msg.id,
                "timestamp": msg.timestamp,
                "sender": request.user.username,
                "receiver": receiver.username,
                "content": raw_content,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": "Encryption failed."}, status=status.HTTP_400_BAD_REQUEST)

class OperativeDirectoryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Returns a safe list of all active operatives for the DM directory
        # Fetch all active users EXCEPT the user making the request
        users = User.objects.filter(is_active=True).exclude(id=request.user.id).values('id', 'username')
        serialized = [{'id': u['id'], 'username': u['username']} for u in users]
        return Response(serialized, status=status.HTTP_200_OK)
    

class SystemAuditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole] 

    def get(self, request):
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


class AdminUserManagementView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = User.objects.all().order_by('id')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class AdminPromoteUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request, user_id):
        new_role = request.data.get('role')
        if new_role not in ['ADMIN', 'USER', 'MODERATOR']:
            return Response({"error": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_user = User.objects.get(id=user_id)
            target_user.role = new_role
            target_user.save()
            return Response({"message": "Role updated."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


class AdminUserActionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request, user_id):
        action = request.data.get('action')
        try:
            target_user = User.objects.get(id=user_id)
            
            if action == 'toggle_ban':
                target_user.is_active = not target_user.is_active
                target_user.save()
                return Response({"message": "User active state toggled."}, status=status.HTTP_200_OK)
            elif action == 'change_role':
                target_user.role = request.data.get('role')
                target_user.save()
                return Response({"message": "Role updated."}, status=status.HTTP_200_OK)

            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
