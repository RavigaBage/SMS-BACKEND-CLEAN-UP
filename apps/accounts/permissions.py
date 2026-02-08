from rest_framework import permissions
from .models import User


class IsAdminOrHeadmaster(permissions.BasePermission):
    """Permission for admin and headmaster only"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.Role.ADMIN, User.Role.HEADMASTER]
        )


class IsBursar(permissions.BasePermission):
    """Permission for bursar only"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.BURSAR
        )


class IsTeacher(permissions.BasePermission):
    """Permission for teachers"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.TEACHER
        )


class CanManageStaff(permissions.BasePermission):
    """Permission to manage staff (admin and headmaster)"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.Role.ADMIN, User.Role.HEADMASTER]
        )


class CanManageFinance(permissions.BasePermission):
    """Permission to manage finance (admin, headmaster, bursar)"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.Role.ADMIN, User.Role.HEADMASTER, User.Role.BURSAR]
        )


class CanManageStudents(permissions.BasePermission):
    """Permission to manage students (superuser, admin, headmaster, teacher)"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        return (
            request.user.is_superuser or 
            request.user.role in [
                User.Role.ADMIN, 
                User.Role.HEADMASTER, 
                User.Role.TEACHER
            ]
        )
class CanManageGrades(permissions.BasePermission):
    """Permission to manage grades (admin, headmaster, teacher)"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Admin and headmaster have full access
        if request.user.role in [User.Role.ADMIN, User.Role.HEADMASTER]:
            return True
        
        # Teachers can manage grades
        if request.user.role == User.Role.TEACHER:
            return True
        
        return False