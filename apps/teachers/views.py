from rest_framework import viewsets, status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Teacher
from apps.accounts.models import User
from .serializers import (
    TeacherSerializer,
    TeacherCreateSerializer,
    TeacherUpdateSerializer,
    TeacherDetailSerializer,
    TeacherAssignSubjectsSerializer
)
from .services import TeacherService
from apps.accounts.permissions import IsAdminOrHeadmaster,IsAdminHeadmasterOrTeacher
import logging

logger = logging.getLogger(__name__)



class TeacherProfileViewSet(viewsets.ModelViewSet):

    queryset = Teacher.objects.select_related(
        'user',
        'assigned_by'
    ).prefetch_related(
        'subjects'
    ).all()

    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]


    def get_object(self):


        user_id = self.kwargs.get('pk')
        teacher = get_object_or_404(
            Teacher,
            id=user_id
        )

        return teacher

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]

        return [IsAuthenticated(), IsAdminOrHeadmaster()]


    def get_serializer_class(self):
        if self.action == 'create':
            return TeacherCreateSerializer

        elif self.action in ['update', 'partial_update']:
            return TeacherUpdateSerializer

        elif self.action == 'retrieve':
            return TeacherDetailSerializer

        return TeacherSerializer


    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if hasattr(user, 'role') and user.role == 'teacher':
            queryset = queryset.filter(user=user)
            return queryset

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == 'true'
            )

        specialization = self.request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(
                specialization__icontains=specialization
            )

        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            queryset = queryset.filter(
                subjects__id=subject_id
            )

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(
                user__id=user_id
            )

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(user__username__icontains=search)
            )

        return queryset.order_by('id')


    def create(self, request, *args, **kwargs):
        """Create a teacher profile"""

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)

            service = TeacherService()

            teacher = service.create_teacher_profile(
                teacher_data=serializer.validated_data,
                assigned_by=request.user
            )

            response_serializer = TeacherSerializer(teacher)

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except (DRFValidationError, ValidationError) as e:

            logger.error(
                f"Validation error creating teacher: {str(e)}"
            )

            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict

            elif hasattr(e, 'messages'):
                error_detail = (
                    e.messages[0]
                    if e.messages
                    else str(e)
                )

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

            logger.error(
                f"Integrity error creating teacher: {str(e)}"
            )

            error_detail = (
                'Teacher profile already exists for this user '
                'or database constraint violated.'
            )

            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:

            logger.error(
                f"Unexpected error creating teacher: {str(e)}",
                exc_info=True
            )

            error_detail = (
                'An unexpected error occurred while '
                'creating the teacher profile.'
            )

            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TeacherViewSet(viewsets.ModelViewSet):
    """ViewSet for Teacher management"""
    
    queryset = Teacher.objects.select_related('user', 'assigned_by').prefetch_related('subjects').all()
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrHeadmaster()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TeacherCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TeacherUpdateSerializer
        elif self.action == 'retrieve':
            return TeacherDetailSerializer
        return TeacherSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if hasattr(user, 'role') and user.role == 'teacher':
            queryset = queryset.filter(user=user)
            return queryset

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        specialization = self.request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)

        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subjects__id=subject_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user__id=user_id)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(user__username__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a teacher profile"""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            service = TeacherService()
            teacher = service.create_teacher_profile(
                teacher_data=serializer.validated_data,
                assigned_by=request.user
            )
            
            response_serializer = TeacherSerializer(teacher)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating teacher: {str(e)}")
            
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
            logger.error(f"Integrity error creating teacher: {str(e)}")
            error_detail = 'Teacher profile already exists for this user or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating teacher: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the teacher profile.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update teacher profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            service = TeacherService()
            teacher = service.update_teacher_profile(
                teacher_id=instance.id,
                teacher_data=serializer.validated_data
            )
            
            response_serializer = TeacherSerializer(teacher)
            return Response(response_serializer.data)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error updating teacher {instance.id}: {str(e)}")
            
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
            logger.error(f"Integrity error updating teacher {instance.id}: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating teacher {instance.id}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the teacher profile.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def assign_subjects(self, request, pk=None):
        """Assign subjects to a teacher"""
        teacher = self.get_object()
        serializer = TeacherAssignSubjectsSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            service = TeacherService()
            teacher = service.assign_subjects(
                teacher_id=teacher.id,
                subject_ids=serializer.validated_data['subject_ids']
            )
            
            response_serializer = TeacherSerializer(teacher)
            return Response(
                {
                    'message': 'Subjects assigned successfully',
                    'teacher': response_serializer.data
                }
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error assigning subjects to teacher {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error assigning subjects to teacher {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while assigning subjects.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def remove_subjects(self, request, pk=None):
        """Remove subjects from a teacher"""
        teacher = self.get_object()
        serializer = TeacherAssignSubjectsSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            service = TeacherService()
            teacher = service.remove_subjects(
                teacher_id=teacher.id,
                subject_ids=serializer.validated_data['subject_ids']
            )
            
            response_serializer = TeacherSerializer(teacher)
            return Response(
                {
                    'message': 'Subjects removed successfully',
                    'teacher': response_serializer.data
                }
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error removing subjects from teacher {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error removing subjects from teacher {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while removing subjects.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a teacher"""
        teacher = self.get_object()
        
        try:
            service = TeacherService()
            teacher = service.deactivate_teacher(
                teacher_id=teacher.id,
                deactivated_by=request.user
            )
            
            return Response(
                {
                    'message': f'{teacher.full_name} has been deactivated',
                    'teacher': TeacherSerializer(teacher).data
                }
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error deactivating teacher {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error deactivating teacher {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while deactivating the teacher.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def workload(self, request, pk=None):
        """Get teacher's workload"""
        teacher = self.get_object()
        
        try:
            service = TeacherService()
            workload_data = service.get_teacher_workload(teacher.id)
            
            from apps.academic.serializers import ClassSerializer, SubjectAssignmentSerializer
            
            return Response({
                'teacher': TeacherSerializer(workload_data['teacher']).data,
                'assigned_classes': ClassSerializer(workload_data['assigned_classes'], many=True).data,
                'assigned_classes_count': workload_data['assigned_classes_count'],
                'subject_assignments': SubjectAssignmentSerializer(workload_data['subject_assignments'], many=True).data,
                'subject_assignments_count': workload_data['subject_assignments_count'],
                'total_workload': workload_data['total_workload']
            })
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error retrieving teacher workload {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error retrieving teacher workload {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving teacher workload.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active teachers"""
        try:
            service = TeacherService()
            teachers = service.get_active_teachers()
            serializer = TeacherSerializer(teachers, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving active teachers: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving active teachers.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def by_subject(self, request):
        """Get teachers by subject"""
        subject_id = request.query_params.get('subject_id')
        
        if not subject_id:
            error_detail = 'subject_id query parameter is required'
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = TeacherService()
            teachers = service.get_teachers_by_subject(subject_id)
            serializer = TeacherSerializer(teachers, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving teachers by subject {subject_id}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving teachers.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
