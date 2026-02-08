from rest_framework import viewsets, status,filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import AcademicYear, Class, Subject, Enrollment, SubjectAssignment
from .serializers import (
    AcademicYearSerializer, ClassSerializer, SubjectSerializer,
    EnrollmentSerializer, SubjectAssignmentSerializer, ClassDetailSerializer
)
from apps.accounts.permissions import CanManageStudents, IsAdminOrHeadmaster


class AcademicYearViewSet(viewsets.ModelViewSet):
    """ViewSet for AcademicYear management"""
    
    queryset = AcademicYear.objects.all().order_by('-start_date')
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadmaster()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current academic year"""
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            serializer = self.get_serializer(current_year)
            return Response(serializer.data)
        return Response({'error': 'No current academic year set'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def set_as_current(self, request, pk=None):
        """Set this academic year as current"""
        academic_year = self.get_object()

        # Unset current from all others
        AcademicYear.objects.update(is_current=False)

        # Set this as current
        academic_year.is_current = True
        academic_year.save()

        serializer = self.get_serializer(academic_year)
        return Response(serializer.data)
    

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

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get all students in a class"""
        class_obj = self.get_object()
        enrollments = class_obj.enrollments.filter(status='active').select_related('student')

        from apps.students.serializers import StudentSerializer
        students = [enrollment.student for enrollment in enrollments]
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get class statistics"""
        class_obj = self.get_object()

        total_students = class_obj.enrollments.filter(status='active').count()
        gender_breakdown = class_obj.enrollments.filter(status='active').values('student__gender').annotate(count=Count('id'))

        return Response({
            'total_students': total_students,
            'capacity': class_obj.capacity,
            'available_seats': class_obj.capacity - total_students,
            'gender_breakdown': list(gender_breakdown)
        })
    
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