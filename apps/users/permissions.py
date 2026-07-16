from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrAdmin(BasePermission):
    """Allow access only to the object owner or admin staff."""

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        user_field = getattr(obj, "user", None)
        return user_field == request.user


class IsAdminUser(BasePermission):
    """Allow access only to admin/staff users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAuthenticatedOrReadOnly(BasePermission):
    """Read-only for anonymous, full access for authenticated."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)