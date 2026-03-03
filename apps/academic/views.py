from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import AcademicYear, Class, Subject, Enrollment, SubjectAssignment
from django.db.models import Q
from .serializers import (
    AcademicYearSerializer, ClassSerializer, SubjectSerializer,
    EnrollmentSerializer, SubjectAssignmentSerializer, ClassDetailSerializer
)
from apps.accounts.permissions import CanManageStudents, IsAdminOrHeadmaster
from apps.permissions.mixins import SchoolWriteMixin, handle_viewset_exception
import logging
from apps.studentManager.services import ProgressionService

logger = logging.getLogger(__name__)


class AcademicYearViewSet(SchoolWriteMixin, viewsets.ModelViewSet):
    queryset         = AcademicYear.objects.all().order_by("-start_date")
    serializer_class = AcademicYearSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Return the current academic year."""
        try:
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_year:
                return Response(
                    {"error": "Not Found: No current academic year set."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(self.get_serializer(current_year).data)
        except Exception as e:
            return handle_viewset_exception(e, "retrieving current academic year")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def set_as_current(self, request, pk=None):
        """Mark this academic year as the active one."""
        try:
            academic_year = self.get_object()
            AcademicYear.objects.update(is_current=False)
            academic_year.is_current = True
            academic_year.save()
            return Response(self.get_serializer(academic_year).data)
        except Exception as e:
            return handle_viewset_exception(e, "setting academic year as current")


class SubjectViewSet(SchoolWriteMixin, viewsets.ModelViewSet):
    queryset         = Subject.objects.all().order_by("subject_code")
    serializer_class = SubjectSerializer
    requires_teacher  = False

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset     = super().get_queryset()
        grade_level  = self.request.query_params.get("grade_level")
        search       = self.request.query_params.get("search")

        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if search:
            queryset = queryset.filter(
                Q(subject_name__icontains=search) | Q(subject_code__icontains=search)
            )
        return queryset


class ClassViewSet(SchoolWriteMixin, viewsets.ModelViewSet):
    queryset = Class.objects.select_related("class_teacher").prefetch_related("subjects").all()
    serializer_teacher_field = "class_teacher"
    ownership_teacher_field  = "class_teacher"

    def get_serializer_class(self):
        return ClassDetailSerializer if self.action == "retrieve" else ClassSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Class.objects.select_related("class_teacher").prefetch_related("subjects").all()
        academic_year = self.request.query_params.get("academic_year")
        grade_level  = self.request.query_params.get("grade_level")
        teacher_id   = self.request.query_params.get("teacher_id")

        if academic_year:
            qs = qs.filter(academic_year=academic_year)
        if grade_level:
            qs = qs.filter(grade_level=grade_level)
        if teacher_id:
            qs = qs.filter(class_teacher_id=teacher_id)
        return qs

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        """Return active students enrolled in this class."""
        try:
            class_obj   = self.get_object()
            enrollments = class_obj.enrollments.filter(status="active").select_related("student")
            from apps.students.serializers import StudentSerializer
            return Response(StudentSerializer([e.student for e in enrollments], many=True).data)
        except Exception as e:
            return handle_viewset_exception(e, f"retrieving students for class {pk}")

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Return headcount and seat availability for this class."""
        try:
            class_obj      = self.get_object()
            total_students = class_obj.enrollments.filter(status="active").count()
            gender_breakdown = (
                class_obj.enrollments.filter(status="active")
                .values("student__gender")
                .annotate(count=Count("id"))
            )
            return Response({
                "total_students":   total_students,
                "capacity":         class_obj.capacity,
                "available_seats":  class_obj.capacity - total_students,
                "gender_breakdown": list(gender_breakdown),
            })
        except Exception as e:
            return handle_viewset_exception(e, f"retrieving statistics for class {pk}")


class EnrollmentViewSet(SchoolWriteMixin, viewsets.ModelViewSet):
    queryset         = Enrollment.objects.select_related("student", "class_obj").all()
    serializer_class = EnrollmentSerializer
    requires_teacher  = False
    permission_classes = [IsAuthenticated, CanManageStudents]
    filter_backends  = [filters.SearchFilter]
    search_fields    = ["student__first_name", "student__last_name", "student__middle_name"]

    def get_queryset(self):
        queryset      = super().get_queryset()
        student_id    = self.request.query_params.get("student_id")
        class_id      = self.request.query_params.get("class_id")
        status_filter = self.request.query_params.get("status")
        academic_year = self.request.query_params.get("academic_year")

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if academic_year:
            queryset = queryset.filter(
                Q(academic_year=academic_year) |
                Q(academic_year="", class_obj__academic_year=academic_year)
            )
        return queryset

    def perform_create(self, serializer):
        enrollment = serializer.save()
        ProgressionService.handle_new_enrollment(enrollment)

class SubjectAssignmentViewSet(SchoolWriteMixin, viewsets.ModelViewSet):
    queryset         = SubjectAssignment.objects.select_related("class_obj", "subject", "teacher").all()
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]

    def get_queryset(self):
        queryset   = super().get_queryset()
        class_id   = self.request.query_params.get("class_id")
        teacher_id = self.request.query_params.get("teacher_id")
        subject_id = self.request.query_params.get("subject_id")

        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        return queryset
