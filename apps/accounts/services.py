from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from .models import User
import secrets
import string


class UserService:
    """Service layer for User operations"""
    
    @staticmethod
    def generate_password(length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password
    
    @staticmethod
    def generate_username(first_name, last_name, role):
        """Generate username from name and role"""
        base_username = f"{first_name.lower()}.{last_name.lower()}"
        
        counter = 1
        username = base_username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    @staticmethod
    def validate_email_unique(email):
        """Check if email is already in use"""
        if User.objects.filter(email=email).exists():
            raise ValidationError(f"Email {email} is already in use")
    
    @staticmethod
    def validate_role_permissions(created_by_user, target_role):
        """Check if user has permission to create this role"""
        if not created_by_user:
            return True 
        
        if created_by_user.role not in [User.Role.ADMIN, User.Role.HEADMASTER]:
            raise ValidationError("You don't have permission to create users")
        
        if created_by_user.role == User.Role.BURSAR:
            if target_role in [User.Role.ADMIN, User.Role.HEADMASTER]:
                raise ValidationError("You don't have permission to create this role")
        
        return True