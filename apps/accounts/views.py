from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .models import User
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    ChangePasswordSerializer
)
from .permissions import IsAdminOrHeadmaster


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
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
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
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


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
        
        return queryset
    
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
    
    @extend_schema(
        responses={200: OpenApiResponse(description="User deactivated successfully")},
        description="Deactivate a user account"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def deactivate(self, request, pk=None):
        """Deactivate a user account"""
        user = self.get_object()
        
        # Cannot deactivate yourself
        if user == request.user:
            return Response(
                {'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = False
        user.save()
        
        return Response({'message': 'User deactivated successfully'})
    
    @extend_schema(
        responses={200: OpenApiResponse(description="User activated successfully")},
        description="Activate a user account"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def activate(self, request, pk=None):
        """Activate a user account"""
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({'message': 'User activated successfully'})


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
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)