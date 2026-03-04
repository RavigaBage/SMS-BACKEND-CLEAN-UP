from rest_framework.permissions import BasePermission

class CanManageProgression(BasePermission):
    """
    Allow access only to:
    - Headmaster
    - Admin
    - Teacher assigned to the class in the request
    """
    message = "You do not have permission to manage student progressions."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role in ('headmaster', 'admin'):
            return True

        # for teachers — check later in has_object_permission
        if user.role == 'teacher':
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role in ('headmaster', 'admin'):
            return True

        if user.role == 'teacher':
            return user.staff_profile.assigned_classes.filter(
                class_name=obj.from_class
            ).exists()

        return False