from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from .models import Timetable, Syllabus
from .serializers import TimetableSerializer, SyllabusSerializer, SyllabusListSerializer
from apps.accounts.permissions import IsAdminOrHeadmaster
import logging

logger = logging.getLogger(__name__)


class TimetableViewSet(viewsets.ModelViewSet):
    """ViewSet for Timetable management"""
    
    queryset = Timetable.objects.select_related('class_obj', 'subject', 'teacher').all()
    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        
        teacher_id = self.request.query_params.get('teacher_id', None)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        day = self.request.query_params.get('day', None)
        if day:
            queryset = queryset.filter(day_of_week=day)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create timetable entry with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating timetable entry: {str(e)}")
            
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
            logger.error(f"Integrity error creating timetable entry: {str(e)}")
            error_detail = 'Timetable entry conflicts with existing schedule or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating timetable entry: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the timetable entry.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update timetable entry with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating timetable entry: {str(e)}")
            
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
            logger.error(f"Integrity error updating timetable entry: {str(e)}")
            error_detail = 'Timetable entry conflicts with existing schedule or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating timetable entry: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the timetable entry.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def class_schedule(self, request):
        """Get full weekly schedule for a class with exception handling"""
        try:
            class_id = request.query_params.get('class_id')
            
            if not class_id:
                error_detail = 'class_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            timetable_entries = Timetable.objects.filter(
                class_obj_id=class_id
            ).select_related('subject', 'teacher').order_by('day_of_week', 'start_time')
            
            # Group by day
            schedule = {}
            for entry in timetable_entries:
                day = entry.get_day_of_week_display()
                if day not in schedule:
                    schedule[day] = []
                
                schedule[day].append(TimetableSerializer(entry).data)
            
            return Response(schedule)
            
        except Exception as e:
            logger.error(f"Error retrieving class schedule: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving the class schedule.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def teacher_schedule(self, request):
        """Get full weekly schedule for a teacher with exception handling"""
        try:
            teacher_id = request.query_params.get('teacher_id')
            
            if not teacher_id:
                error_detail = 'teacher_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            timetable_entries = Timetable.objects.filter(
                teacher_id=teacher_id
            ).select_related('class_obj', 'subject').order_by('day_of_week', 'start_time')
            
            # Group by day
            schedule = {}
            for entry in timetable_entries:
                day = entry.get_day_of_week_display()
                if day not in schedule:
                    schedule[day] = []
                
                schedule[day].append(TimetableSerializer(entry).data)
            
            return Response(schedule)
            
        except Exception as e:
            logger.error(f"Error retrieving teacher schedule: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving the teacher schedule.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def check_conflicts(self, request):
        """Check for scheduling conflicts with exception handling"""
        try:
            class_id = request.data.get('class_id')
            teacher_id = request.data.get('teacher_id')
            day_of_week = request.data.get('day_of_week')
            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            exclude_id = request.data.get('exclude_id')
            
            if not all([day_of_week, start_time, end_time]):
                error_detail = 'day_of_week, start_time, and end_time are required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conflicts = []
            
            # Check class conflicts
            if class_id:
                class_conflicts = Timetable.objects.filter(
                    class_obj_id=class_id,
                    day_of_week=day_of_week,
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
                
                if exclude_id:
                    class_conflicts = class_conflicts.exclude(id=exclude_id)
                
                if class_conflicts.exists():
                    conflicts.append({
                        'type': 'class',
                        'message': 'Class already has a session at this time',
                        'entries': TimetableSerializer(class_conflicts, many=True).data
                    })
            
            # Check teacher conflicts
            if teacher_id:
                teacher_conflicts = Timetable.objects.filter(
                    teacher_id=teacher_id,
                    day_of_week=day_of_week,
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
                
                if exclude_id:
                    teacher_conflicts = teacher_conflicts.exclude(id=exclude_id)
                
                if teacher_conflicts.exists():
                    conflicts.append({
                        'type': 'teacher',
                        'message': 'Teacher already has a session at this time',
                        'entries': TimetableSerializer(teacher_conflicts, many=True).data
                    })
            
            return Response({
                'has_conflicts': len(conflicts) > 0,
                'conflicts': conflicts
            })
            
        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while checking for conflicts.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyllabusViewSet(viewsets.ModelViewSet):
    """ViewSet for Syllabus management"""
    
    queryset = Syllabus.objects.all().select_related('subject', 'teacher', 'class_obj')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'teacher', 'class_obj', 'week_number']
    search_fields = ['topic_title', 'content_summary', 'learning_objectives']
    ordering_fields = ['week_number', 'topic_title']
    ordering = ['week_number']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return SyllabusListSerializer
        return SyllabusSerializer
    
    def create(self, request, *args, **kwargs):
        """Create syllabus with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating syllabus: {str(e)}")
            
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
            logger.error(f"Integrity error creating syllabus: {str(e)}")
            error_detail = 'Syllabus already exists for this subject and week or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating syllabus: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the syllabus.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update syllabus with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating syllabus: {str(e)}")
            
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
            logger.error(f"Integrity error updating syllabus: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating syllabus: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the syllabus.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='by-subject/(?P<subject_id>[^/.]+)')
    def by_subject(self, request, subject_id=None):
        """Get all syllabi for a specific subject with exception handling"""
        try:
            syllabi = self.queryset.filter(subject_id=subject_id)
            serializer = self.get_serializer(syllabi, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving syllabi by subject {subject_id}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving syllabi.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='by-teacher/(?P<teacher_id>[^/.]+)')
    def by_teacher(self, request, teacher_id=None):
        """Get all syllabi for a specific teacher with exception handling"""
        try:
            syllabi = self.queryset.filter(teacher_id=teacher_id)
            serializer = self.get_serializer(syllabi, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving syllabi by teacher {teacher_id}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving syllabi.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='by-class/(?P<class_id>[^/.]+)')
    def by_class(self, request, class_id=None):
        """Get all syllabi for a specific class with exception handling"""
        try:
            syllabi = self.queryset.filter(class_obj_id=class_id)
            serializer = self.get_serializer(syllabi, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving syllabi by class {class_id}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving syllabi.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def weekly_overview(self, request):
        """Get syllabi grouped by week number with exception handling"""
        try:
            queryset = self.queryset
            
            # Apply filters from query params
            subject_id = request.query_params.get('subject_id')
            teacher_id = request.query_params.get('teacher_id')
            class_id = request.query_params.get('class_id')
            
            if subject_id:
                queryset = queryset.filter(subject_id=subject_id)
            if teacher_id:
                queryset = queryset.filter(teacher_id=teacher_id)
            if class_id:
                queryset = queryset.filter(class_obj_id=class_id)
            
            # Group by week
            weeks = {}
            for syllabus in queryset:
                week = syllabus.week_number
                if week not in weeks:
                    weeks[week] = []
                weeks[week].append(SyllabusSerializer(syllabus).data)
            
            return Response({
                'weeks': weeks,
                'total_weeks': len(weeks),
            })
            
        except Exception as e:
            logger.error(f"Error retrieving weekly overview: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving weekly overview.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Function-based view with exception handling
@api_view(['GET'])
def get_syllabus_by_params(request):
    """
    Get syllabus filtered by query parameters with exception handling
    Example: /api/syllabus/filter/?subject=1&teacher=2&week_number=3
    """
    try:
        subject_id = request.query_params.get('subject')
        teacher_id = request.query_params.get('teacher')
        class_id = request.query_params.get('class')
        week_number = request.query_params.get('week_number')
        
        queryset = Syllabus.objects.all()
        
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        if week_number:
            queryset = queryset.filter(week_number=week_number)
        
        serializer = SyllabusSerializer(queryset, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error in get_syllabus_by_params: {str(e)}", exc_info=True)
        error_detail = 'An unexpected error occurred while retrieving syllabi.'
        return Response(
            {
                'error': f'Server Error: {error_detail}',
                'detail': error_detail
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )