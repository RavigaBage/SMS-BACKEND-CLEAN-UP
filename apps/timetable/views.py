from django.forms import ValidationError
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Timetable, Syllabus
from apps.accounts.models import User
from .serializers import TimetableSerializer, SyllabusSerializer, SyllabusListSerializer
from apps.accounts.permissions import IsAdminOrHeadmaster
import logging

logger = logging.getLogger(__name__)


class TimetableViewSet(viewsets.ModelViewSet):
    """
    Enterprise-grade timetable viewset.

    Features:
    - Safe filtering
    - Conflict detection
    - Clean validation
    - Role-based permissions
    """

    queryset = Timetable.objects.select_related(
        "class_obj",
        "subject",
        "teacher"
    ).all()

    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]

   
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]


    def _get_int_param(self, param_name):
        value = self.request.query_params.get(param_name)
        if value is None:
            return None

        if not str(value).isdigit():
            raise DjangoValidationError(
                {param_name: "Must be a numeric ID."}
            )

        return int(value)

    def _apply_filters(self, queryset):
        class_id = self._get_int_param("class_id")
        teacher_id = self._get_int_param("teacher_id")
        day = self._get_int_param("day")

        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)

        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        if day:
            queryset = queryset.filter(day_of_week=day)

        return queryset

    def _stringify_error(self, err):
        if hasattr(err, "detail"):
            return str(err.detail)
        if hasattr(err, "message_dict"):
            return str(err.message_dict)
        if hasattr(err, "messages"):
            return str(err.messages[0] if err.messages else err)
        return str(err)

    def _is_duplicate_integrity_error(self, err):
        msg = str(err).lower()
        duplicate_tokens = [
            "unique",
            "duplicate",
            "already exists",
            "unique constraint",
            "duplicate key",
        ]
        return any(token in msg for token in duplicate_tokens)

    def _error_response(self, message, status_code):
        msg = str(message)
        return Response(msg, status=status_code)

 
    def get_queryset(self):
        queryset = super().get_queryset()
        
        term = self.request.query_params.get("term")
        academic_year = self.request.query_params.get("academic_year")

        if term:
            queryset = queryset.filter(term=term)

        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)
            
        return self._apply_filters(queryset)

    def _check_conflicts(
        self,
        class_id,
        teacher_id,
        day,
        start_time,
        end_time,
        term="",
        academic_year="",
        instance_id=None
    ):
        """
        Prevent:
        - Teacher double booking
        - Class double booking
        """
        overlapping_filter = Q(
            day_of_week=day,
            start_time__lt=end_time,
            end_time__gt=start_time,
            term=term,
            academic_year=academic_year,
        )

        conflicts = Timetable.objects.filter(overlapping_filter)

        if instance_id:
            conflicts = conflicts.exclude(id=instance_id)

        class_conflict = conflicts.filter(class_obj_id=class_id).exists()
        teacher_conflict = conflicts.filter(teacher_id=teacher_id).exists()

        if class_conflict:
            raise DjangoValidationError(
                {"This class already has a lesson at this time."}
            )

        if teacher_conflict:
            raise DjangoValidationError(
                {"This teacher is already booked at this time."}
            )

   
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            self._check_conflicts(
                class_id=data["class_obj"].id,
                teacher_id=(data.get("teacher").id if data.get("teacher") else None),
                day=data["day_of_week"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                term=data.get("term", ""),
                academic_year=data.get("academic_year", ""),
            )

            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (DRFValidationError, DjangoValidationError) as e:
            logger.error(f"Validation error creating timetable entry: {str(e)}")
            return self._error_response(self._stringify_error(e), status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            logger.error(f"Integrity error creating timetable entry: {str(e)}")
            if self._is_duplicate_integrity_error(e):
                return self._error_response(
                    "Duplicate timetable entry detected. This schedule already exists.",
                    status.HTTP_400_BAD_REQUEST,
                )
            return self._error_response(
                "Database integrity error while creating timetable entry.",
                status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Unexpected error creating timetable entry: {str(e)}", exc_info=True)
            return self._error_response(
                "An unexpected server error occurred while creating timetable entry.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()

            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial
            )

            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            self._check_conflicts(
                class_id=data.get("class_obj", instance.class_obj).id,
                teacher_id=(data.get("teacher", instance.teacher).id if data.get("teacher", instance.teacher) else None),
                day=data.get("day_of_week", instance.day_of_week),
                start_time=data.get("start_time", instance.start_time),
                end_time=data.get("end_time", instance.end_time),
                term=data.get("term", instance.term),
                academic_year=data.get("academic_year", instance.academic_year),
                instance_id=instance.id
            )

            self.perform_update(serializer)
            return Response(serializer.data)

        except (DRFValidationError, DjangoValidationError) as e:
            logger.error(f"Validation error updating timetable entry: {str(e)}")
            return self._error_response(self._stringify_error(e), status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            logger.error(f"Integrity error updating timetable entry: {str(e)}")
            if self._is_duplicate_integrity_error(e):
                return self._error_response(
                    "Duplicate timetable entry detected. This schedule already exists.",
                    status.HTTP_400_BAD_REQUEST,
                )
            return self._error_response(
                "Database integrity error while updating timetable entry.",
                status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Unexpected error updating timetable entry: {str(e)}", exc_info=True)
            return self._error_response(
                "An unexpected server error occurred while updating timetable entry.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def class_schedule(self, request):
        class_id = self._get_int_param("class_id")

        if not class_id:
            raise DjangoValidationError(
                {"class_id query parameter is required."}
            )

        queryset = Timetable.objects.filter(class_obj_id=class_id)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def teacher_schedule(self, request):
        teacher_id = self._get_int_param("teacher_id")

        if not teacher_id:
            raise DjangoValidationError(
                {"teacher_id query parameter is required."}
            )

        queryset = Timetable.objects.filter(teacher_id=teacher_id)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def check_conflicts(self, request):
        """
        API endpoint to manually check scheduling conflicts.
        """

        class_id = self._get_int_param("class_id")
        teacher_id = self._get_int_param("teacher_id")
        day = self._get_int_param("day")

        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        if not all([class_id, teacher_id, day, start_time, end_time]):
            raise DjangoValidationError(
                "class_id, teacher_id, day, start_time, end_time are required."
            )

        overlapping_filter = Q(
            day_of_week=day,
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        conflicts = Timetable.objects.filter(overlapping_filter)

        return Response({
            "class_conflict": conflicts.filter(
                class_obj_id=class_id
            ).exists(),
            "teacher_conflict": conflicts.filter(
                teacher_id=teacher_id
            ).exists(),
        })
    
class SyllabusViewSet(viewsets.ModelViewSet):
    """ViewSet for Syllabus management"""
    
    queryset = Syllabus.objects.all().select_related('subject', 'teacher', 'class_obj')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'teacher', 'class_obj', 'week_number']
    search_fields = ['topic_title', 'content_summary', 'learning_objectives']
    ordering_fields = ['week_number', 'topic_title']
    ordering = ['week_number']

    def get_serializer_class(self):
        if self.action == 'list':
            return SyllabusListSerializer
        return SyllabusSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]  
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    def _assert_ownership(self, request, teacher_id, class_obj_id):
        user = request.user

        if user.role in [User.Role.ADMIN, User.Role.HEADMASTER]:
            return

        if user.role == User.Role.TEACHER:
            try:
                teacher_profile = user.teacher_profile 
            except Exception:
                raise PermissionDenied("No teacher profile found for this account.")

            if teacher_id and int(teacher_id) != teacher_profile.id:
                raise PermissionDenied(
                    "You can only upload a syllabus assigned to yourself as the teacher."
                )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            teacher_id = data.get('teacher').id if data.get('teacher') else None
            class_obj_id = data.get('class_obj').id if data.get('class_obj') else None
            
            self._assert_ownership(request, teacher_id, class_obj_id)
            
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except DRFValidationError as e:
            logger.warning(f"Validation error creating syllabus: {str(e)}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except PermissionDenied as e:
            logger.warning(f"Permission denied: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        except IntegrityError as e:
            logger.error(f"Integrity error creating syllabus: {str(e)}")
            return Response(
                {'error': 'Syllabus already exists for this subject, teacher, and week.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error creating syllabus: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An unexpected server error occurred.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def update(self, request, *args, **kwargs):
        try:
            teacher_id   = request.data.get('teacher')
            class_obj_id = request.data.get('class_obj')
            self._assert_ownership(request, teacher_id, class_obj_id)

            return super().update(request, *args, **kwargs)

        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        except ValidationError as e:
            logger.error(f"Validation error updating syllabus: {str(e)}")
            error_detail = (
                e.message_dict if hasattr(e, 'message_dict')
                else e.messages[0] if hasattr(e, 'messages') and e.messages
                else str(e)
            )
            return Response({'Validation Error': str(error_detail)}, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError as e:
            logger.error(f"Integrity error updating syllabus: {str(e)}")
            return Response(
                {'Database Error': 'Database constraint violated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error updating syllabus: {str(e)}", exc_info=True)
            return Response(
                {'Server Error': 'An unexpected error occurred while updating the syllabus.'},
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
                {f'Server Error: {error_detail}'},
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
                { f'Server Error: {error_detail}'},
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
                { f'Server Error: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def weekly_overview(self, request):
        """Get syllabi grouped by week number with exception handling"""
        try:
            queryset = self.queryset
            
            subject_id = request.query_params.get('subject_id')
            teacher_id = request.query_params.get('teacher_id')
            class_id = request.query_params.get('class_id')
            
            if subject_id:
                queryset = queryset.filter(subject_id=subject_id)
            if teacher_id:
                queryset = queryset.filter(teacher_id=teacher_id)
            if class_id:
                queryset = queryset.filter(class_obj_id=class_id)
            
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
                { f'Server Error: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            {f'Server Error: {error_detail}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
