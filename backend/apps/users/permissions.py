from rest_framework.permissions import BasePermission, IsAdminUser


class IsAdminOrSelf(BasePermission):
    """Allow access to admins or the user accessing their own record."""
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or request.user.role == 'admin' or obj == request.user
