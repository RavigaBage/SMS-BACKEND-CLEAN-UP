from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.http import JsonResponse
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.db.models import Q
import os
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from apps.settings.models import EmailConfiguration
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import User
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    ChangePasswordSerializer
)
from .permissions import IsAdminOrHeadmaster
import logging
from django.core.mail import send_mail, get_connection
logger = logging.getLogger(__name__)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)

        except (DRFValidationError, ValidationError) as e:

            if hasattr(e, "detail"):

                if isinstance(e.detail, dict):
                    first_key = next(iter(e.detail))
                    error_detail = e.detail[first_key][0]

                elif isinstance(e.detail, list):
                    error_detail = e.detail[0]

                else:
                    error_detail = str(e.detail)

            else:
                error_detail = str(e)

            return Response(
                {
                    "error": False,
                    "detail": str(error_detail),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except InvalidToken:
            return Response(
                {
                    "error": False,
                    "detail": "Invalid credentials provided.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except Exception:
            return Response(
                {
                    "error": False,
                    "detail": "An unexpected error occurred during login.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
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
            
            user = serializer.save()
            user.set_password(request.data.get('password'))
            user.created_by = request.user
            user.save()
            
            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
            
        except (DRFValidationError, ValidationError) as e:
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
        

    def get_email_connection(self):
        """Build an email connection from the DB email config model."""
        config = EmailConfiguration.objects.first()
        if not config:
            raise ValueError("No email configuration found. Please set up email settings in the admin panel.")

        if config.backend == "console":
            return ConsoleBackend()

        return SMTPBackend(
            host=config.host,
            port=config.port,
            username=config.host_user,
            password=config.host_password,
            use_tls=config.use_tls,
            fail_silently=False,
        )


    def update(self, request, *args, **kwargs):
        """Update user with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
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
                new_password = serializer.validated_data['new_password']
                user.set_password(new_password)
                user.save()
                
                return Response({
                    'message': f'Password changed successfully for {user.username}. User must login with new password.'
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except (DRFValidationError, ValidationError) as e:
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
            
        except (DRFValidationError, ValidationError) as e:
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
            
        except (DRFValidationError, ValidationError) as e:
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
    @extend_schema(
    responses={200: OpenApiResponse(description="Invite email sent successfully")},
    description="Send platform invite email to a user"
    )
        
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def send_invite(self, request, pk=None):
        try:
            user = self.get_object()
            config = EmailConfiguration.objects.first()
            if not config:
                return Response(
                    {'error': 'Email not configured. Please set up email settings first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            login_url    = f"{frontend_url}/login"
            school_name  = config.school_name or "School Administration"
            from_email   = config.default_from_email or config.host_user

            html_body = render_to_string('emails/platform_invite.html', {
                'username':    user.username,
                'email':       user.email,
                'role_display': user.role,
                'school_name': school_name,
                'platform_url': frontend_url,
                'login_url':   login_url,
                'invited_by':  request.user.username,
                'invited_on':  timezone.now().strftime('%d %B %Y'),
            })

            connection = self.get_email_connection()

            email = EmailMessage(
                subject=f"You've been invited to {school_name}'s Management Platform",
                body=html_body,
                from_email=from_email,
                to=[user.email],
                connection=connection,
            )
            email.content_subtype = 'html' 
            email.send()

            logger.info(f"Invite sent to {user.email} by {request.user.username}")
            return Response({'message': f'Invite sent successfully to {user.email}'})

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Failed to send invite to user {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to send invite: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
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
