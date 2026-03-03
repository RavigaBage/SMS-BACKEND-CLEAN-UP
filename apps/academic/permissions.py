from rest_framework import permissions


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Permission to only allow teachers and admins to access resources
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return hasattr(request.user, 'teacher_profile') or request.user.is_staff


class IsTeacherOfClass(permissions.BasePermission):
    """
    Permission to only allow teachers of a specific class to modify it
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_superuser:
            return True
        
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
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_superuser or 
            request.user.is_staff or 
            hasattr(request.user, 'teacher_profile')
        )
    
    def has_object_permission(self, request, view, obj):
       
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_superuser:
            return True
        
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
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        if hasattr(request.user, 'student_profile'):
            return obj.id == request.user.student_profile.id
        
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

        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
            
        if hasattr(request.user, 'teacher_profile'):
            return True

        return False

    def has_object_permission(self, request, view, obj):
      
        if request.user.is_superuser or request.user.is_staff:
            return True

        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
           
            return obj.class_obj.teachers.filter(id=teacher.id).exists()

        return False