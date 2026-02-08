from rest_framework import permissions


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Permission to only allow teachers and admins to access resources
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user is a teacher or staff
        return hasattr(request.user, 'teacher_profile') or request.user.is_staff


class IsTeacherOfClass(permissions.BasePermission):
    """
    Permission to only allow teachers of a specific class to modify it
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user is a teacher of this class
        if hasattr(request.user, 'teacher_profile'):
            return obj.teachers.filter(id=request.user.teacher_profile.id).exists()
        
        return False


class CanManageGrades(permissions.BasePermission):
    """
    Permission to manage grades - only teachers and admins
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read-only for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for teachers and admins
        return (
            request.user.is_superuser or 
            request.user.is_staff or 
            hasattr(request.user, 'teacher_profile')
        )
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user is a teacher of the class this grade belongs to
        if hasattr(request.user, 'teacher_profile'):
            if obj.class_obj:
                return obj.class_obj.teachers.filter(
                    id=request.user.teacher_profile.id
                ).exists()
        
        return False


class IsStudentOwnerOrTeacher(permissions.BasePermission):
    """
    Students can only view their own transcripts
    Teachers can view transcripts of students in their classes
    """
    def has_object_permission(self, request, view, obj):
        # Allow superusers and staff
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Students can view their own data
        if hasattr(request.user, 'student_profile'):
            return obj.id == request.user.student_profile.id
        
        # Teachers can view data of students in their classes
        if hasattr(request.user, 'teacher_profile'):
            teacher_class_ids = request.user.teacher_profile.classes.values_list('id', flat=True)
            student_class_ids = obj.enrollments.values_list('class_obj_id', flat=True)
            return bool(set(teacher_class_ids) & set(student_class_ids))
        
        return False


class CanManageStudents(permissions.BasePermission):
    """
    Permission to manage student enrollments.
    Allows Superusers, Staff, and Teachers.
    """
    def has_permission(self, request, view):
        # Deny if not logged in
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 1. Superusers and Staff always have access
        if request.user.is_superuser or request.user.is_staff:
            return True
            
        # 2. Teachers have access
        if hasattr(request.user, 'teacher_profile'):
            return True

        return False

    def has_object_permission(self, request, view, obj):
        # Superusers and Staff can touch any enrollment object
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Teachers can only manage enrollments for their own classes
        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            # Check if this teacher is assigned to the class associated with this enrollment
            return obj.class_obj.teachers.filter(id=teacher.id).exists()

        return False