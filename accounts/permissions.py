from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):

    def has_permission(self, request, view):

        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')

class IsModeratorRole(BasePermission):
    
    def has_permission(self, request, view):
        allowed_roles = ['ADMIN', 'MODERATOR']
        return bool(request.user and request.user.is_authenticated and request.user.role in allowed_roles)