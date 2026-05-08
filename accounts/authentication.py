import jwt
import datetime
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import User

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Your session token has expired.')
        except (jwt.DecodeError, User.DoesNotExist):
            raise AuthenticationFailed('Invalid authentication token.')
        except Exception as e:
            raise AuthenticationFailed(f'Token rejected. {str(e)}')