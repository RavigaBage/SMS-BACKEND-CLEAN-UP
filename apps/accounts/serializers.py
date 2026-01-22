from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from django.contrib.auth import authenticate
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'is_active', 'date_joined', 'last_login',
            'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to use email instead of username for login
    and include user data in response
    """
    
    username_field = 'email'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace username field with email
        self.fields['email'] = serializers.EmailField(required=True)
        self.fields.pop('username', None)
    
    def validate(self, attrs):
        # Get email and password from request
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password')
        
        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError('Account is deactivated')
        
        # Authenticate using username (Django's authenticate requires username)
        user = authenticate(username=user.username, password=password)
        
        if user is None:
            raise serializers.ValidationError('Invalid email or password')
        
        # Get tokens
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
            }
        }
        
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Custom token refresh serializer"""
    pass


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for admin to change user password
    No old password required - admin override
    """
    
    new_password = serializers.CharField(required=True, write_only=True, min_length=10)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return data