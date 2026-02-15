from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import AcademicYear, Class, Subject, Enrollment, SubjectAssignment
from .serializers import (
    AcademicYearSerializer, ClassSerializer, SubjectSerializer,
    EnrollmentSerializer, SubjectAssignmentSerializer, ClassDetailSerializer
)
from apps.accounts.permissions import CanManageStudents, IsAdminOrHeadmaster
import logging

logger = logging.getLogger(__name__)


class AcademicYearViewSet(viewsets.ModelViewSet):
    """ViewSet for AcademicYear management"""
    
    queryset = AcademicYear.objects.all().order_by('-start_date')
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """Create academic year with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating academic year: {str(e)}")
            
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
            logger.error(f"Integrity error creating academic year: {str(e)}")
            error_detail = 'A database constraint was violated. This may be due to duplicate data.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating academic year: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the academic year.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update academic year with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating academic year: {str(e)}")
            
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
            logger.error(f"Integrity error updating academic year: {str(e)}")
            error_detail = 'A database constraint was violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating academic year: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the academic year.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current academic year"""
        try:
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                serializer = self.get_serializer(current_year)
                return Response(serializer.data)
            
            error_detail = 'No current academic year set'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Error retrieving current academic year: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving the current academic year.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def set_as_current(self, request, pk=None):
        """Set this academic year as current"""
        try:
            academic_year = self.get_object()

            # Unset current from all others
            AcademicYear.objects.update(is_current=False)

            # Set this as current
            academic_year.is_current = True
            academic_year.save()

            serializer = self.get_serializer(academic_year)
            return Response(serializer.data)
            
        except ValidationError as e:
            logger.error(f"Validation error setting academic year as current: {str(e)}")
            
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
            logger.error(f"Unexpected error setting academic year as current: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while setting the academic year as current.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Subject management"""
    queryset = Subject.objects.all().order_by('subject_code')
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by grade level
        grade_level = self.request.query_params.get('grade_level', None)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)

        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(subject_name__icontains=search) |
                Q(subject_code__icontains=search)
            )

        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create subject with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating subject: {str(e)}")
            
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
            logger.error(f"Integrity error creating subject: {str(e)}")
            error_detail = 'Subject code already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating subject: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the subject.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update subject with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating subject: {str(e)}")
            
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
            logger.error(f"Integrity error updating subject: {str(e)}")
            error_detail = 'Subject code already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating subject: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the subject.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class ClassViewSet(viewsets.ModelViewSet):
    """ViewSet for Class management"""
    queryset = Class.objects.select_related('academic_year', 'class_teacher').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClassDetailSerializer
        return ClassSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by academic year
        academic_year_id = self.request.query_params.get('academic_year_id', None)
        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)

        # Filter by grade level
        grade_level = self.request.query_params.get('grade_level', None)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)

        # Filter by teacher
        teacher_id = self.request.query_params.get('teacher_id', None)
        if teacher_id:
            queryset = queryset.filter(class_teacher_id=teacher_id)

        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create class with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating class: {str(e)}")
            
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
            logger.error(f"Integrity error creating class: {str(e)}")
            error_detail = 'Class name already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating class: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the class.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update class with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating class: {str(e)}")
            
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
            logger.error(f"Integrity error updating class: {str(e)}")
            error_detail = 'Class name already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating class: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the class.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get all students in a class"""
        try:
            class_obj = self.get_object()
            enrollments = class_obj.enrollments.filter(status='active').select_related('student')

            from apps.students.serializers import StudentSerializer
            students = [enrollment.student for enrollment in enrollments]
            serializer = StudentSerializer(students, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving students for class {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving students.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get class statistics"""
        try:
            class_obj = self.get_object()

            total_students = class_obj.enrollments.filter(status='active').count()
            gender_breakdown = class_obj.enrollments.filter(status='active').values('student__gender').annotate(count=Count('id'))

            return Response({
                'total_students': total_students,
                'capacity': class_obj.capacity,
                'available_seats': class_obj.capacity - total_students,
                'gender_breakdown': list(gender_breakdown)
            })
            
        except Exception as e:
            logger.error(f"Error retrieving statistics for class {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving class statistics.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Enrollment management"""
    queryset = Enrollment.objects.select_related('student', 'class_obj').all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, CanManageStudents]
    filter_backends = [filters.SearchFilter]
    search_fields = ['student__first_name', 'student__last_name', 'student__middle_name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # Filter by class
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create enrollment with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating enrollment: {str(e)}")
            
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
            logger.error(f"Integrity error creating enrollment: {str(e)}")
            error_detail = 'Student is already enrolled in this class or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating enrollment: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the enrollment.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update enrollment with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating enrollment: {str(e)}")
            
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
            logger.error(f"Integrity error updating enrollment: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating enrollment: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the enrollment.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class SubjectAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for SubjectAssignment management"""
    queryset = SubjectAssignment.objects.select_related('class_obj', 'subject', 'teacher').all()
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by class
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)

        # Filter by teacher
        teacher_id = self.request.query_params.get('teacher_id', None)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        # Filter by subject
        subject_id = self.request.query_params.get('subject_id', None)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create subject assignment with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating subject assignment: {str(e)}")
            
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
            logger.error(f"Integrity error creating subject assignment: {str(e)}")
            error_detail = 'Subject is already assigned to this class or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating subject assignment: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the subject assignment.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update subject assignment with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating subject assignment: {str(e)}")
            
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
            logger.error(f"Integrity error updating subject assignment: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating subject assignment: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the subject assignment.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )