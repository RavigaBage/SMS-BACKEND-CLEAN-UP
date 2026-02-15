from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .models import User
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    ChangePasswordSerializer
)
from .permissions import IsAdminOrHeadmaster
import logging

logger = logging.getLogger(__name__)


class LoginView(TokenObtainPairView):
    """
    Login endpoint - returns access and refresh tokens
    
    POST /api/v1/auth/login/
    {
        "email": "admin@school.com",
        "password": "password"
    }
    
    Returns:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@school.com",
            "role": "admin",
            "role_display": "Admin"
        }
    }
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Login with exception handling"""
        try:
            return super().post(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error during login: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except InvalidToken as e:
            logger.error(f"Invalid token during login: {str(e)}")
            error_detail = 'Invalid credentials provided.'
            return Response(
                {
                    'error': f'Authentication Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred during login.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefreshTokenView(TokenRefreshView):
    """
    Refresh access token using refresh token
    
    POST /api/v1/auth/refresh/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Returns:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // New refresh token (token rotation)
    }
    """
    serializer_class = CustomTokenRefreshSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Refresh token with exception handling"""
        try:
            return super().post(request, *args, **kwargs)
            
        except TokenError as e:
            logger.error(f"Token error during refresh: {str(e)}")
            error_detail = 'Invalid or expired refresh token.'
            return Response(
                {
                    'error': f'Token Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except InvalidToken as e:
            logger.error(f"Invalid token during refresh: {str(e)}")
            error_detail = 'Invalid refresh token provided.'
            return Response(
                {
                    'error': f'Authentication Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while refreshing token.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(GenericAPIView):
    """
    Logout endpoint - blacklists the refresh token
    
    POST /api/v1/auth/logout/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
        responses={
            200: OpenApiResponse(description="Successfully logged out"),
            400: OpenApiResponse(description="Invalid token")
        },
        description="Logout user and blacklist refresh token"
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                error_detail = 'Refresh token is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
            
        except TokenError as e:
            logger.error(f"Token error during logout: {str(e)}")
            error_detail = 'Invalid or expired token'
            return Response(
                {
                    'error': f'Token Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during logout: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred during logout.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class CurrentUserView(GenericAPIView):
    """
    Get current logged-in user details
    
    GET /api/v1/auth/me/
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: UserSerializer},
        description="Get current authenticated user information"
    )
    def get(self, request):
        try:
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving current user: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving user information.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User management"""
    
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    
    # Disable unused actions
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by role if specified
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by username, email, first_name, or last_name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new user with exception handling"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Set password and created_by
            user = serializer.save()
            user.set_password(request.data.get('password'))
            user.created_by = request.user
            user.save()
            
            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
            
        except ValidationError as e:
            logger.error(f"Validation error creating user: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating user: {str(e)}")
            error_detail = 'Username or email already exists.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the user.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update user with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating user: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error updating user: {str(e)}")
            error_detail = 'Username or email already exists.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the user.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
        description="Change user password (Admin/Headmaster only)"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def change_password(self, request, pk=None):
        """
        Admin/Headmaster changes user password
        No old password required - admin override
        """
        try:
            user = self.get_object()
            
            serializer = ChangePasswordSerializer(data=request.data)
            if serializer.is_valid():
                # Admin can change any password without knowing old password
                new_password = serializer.validated_data['new_password']
                user.set_password(new_password)
                user.save()
                
                return Response({
                    'message': f'Password changed successfully for {user.username}. User must login with new password.'
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except ValidationError as e:
            logger.error(f"Validation error changing password for user {pk}: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error changing password for user {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while changing the password.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        responses={200: OpenApiResponse(description="User deactivated successfully")},
        description="Deactivate a user account"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def deactivate(self, request, pk=None):
        """Deactivate a user account"""
        try:
            user = self.get_object()
            
            # Cannot deactivate yourself
            if user == request.user:
                error_detail = 'You cannot deactivate your own account'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.is_active = False
            user.save()
            
            return Response({'message': 'User deactivated successfully'})
            
        except ValidationError as e:
            logger.error(f"Validation error deactivating user {pk}: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error deactivating user {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while deactivating the user.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        responses={200: OpenApiResponse(description="User activated successfully")},
        description="Activate a user account"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def activate(self, request, pk=None):
        """Activate a user account"""
        try:
            user = self.get_object()
            user.is_active = True
            user.save()
            
            return Response({'message': 'User activated successfully'})
            
        except ValidationError as e:
            logger.error(f"Validation error activating user {pk}: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error activating user {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while activating the user.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Health check
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        connection.ensure_connection()
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'service': 'school-management-api'
        }, status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)