from rest_framework import permissions


class IsBusinessAdmin(permissions.BasePermission):
    """
    Permission to check if user is the admin of the business
    """
    def has_object_permission(self, request, view, obj):
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        # Check if obj is Business
        if hasattr(obj, 'admin_user'):
            return obj.admin_user == request.user
        
        # Check if obj has business attribute (Camera, Alert, etc.)
        if hasattr(obj, 'business'):
            return obj.business.admin_user == request.user
        
        # Check if obj is related to camera (Alert)
        if hasattr(obj, 'camera'):
            return obj.camera.business.admin_user == request.user
        
        return False


class IsBusinessMember(permissions.BasePermission):
    """
    Permission to check if user belongs to the business
    (Can be extended to support multiple users per business in future)
    """
    def has_object_permission(self, request, view, obj):
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        # For now, same as IsBusinessAdmin
        # In future, check if user is in business.members
        
        if hasattr(obj, 'admin_user'):
            return obj.admin_user == request.user
        
        if hasattr(obj, 'business'):
            return obj.business.admin_user == request.user
        
        if hasattr(obj, 'camera'):
            return obj.camera.business.admin_user == request.user
        
        return False


class ReadOnly(permissions.BasePermission):
    """
    Permission to allow only read operations
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
