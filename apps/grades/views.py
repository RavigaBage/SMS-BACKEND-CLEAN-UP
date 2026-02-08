from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Grade,Student,Class
from .serializers import GradeSerializer, ClassStudentListSerializer,StudentTranscriptSerializer
from apps.accounts.permissions import CanManageGrades
from .Utils import AcademicReportGenerator
# --------------------------
# Grade ViewSet
# --------------------------
class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related('student', 'subject', 'class_obj').all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            class_id = self.request.query_params.get("class")
            subject_id = self.request.query_params.get("subject")
            academic_year = self.request.query_params.get("academic_year")
            term = self.request.query_params.get("term")

            if class_id:
                queryset = queryset.filter(class_obj_id=class_id)
            if subject_id:
                queryset = queryset.filter(subject_id=subject_id)
            if academic_year:
                queryset = queryset.filter(academic_year=academic_year)
            if term:
                queryset = queryset.filter(term=term)
        return queryset

    @action(detail=False, methods=['get', 'patch'], url_path='by-params')
    @action(detail=False, methods=['get', 'patch'], url_path='by-params')
    def get_by_params(self, request):
        student_id = request.query_params.get('student')
        class_id = request.query_params.get('class')
        subject_id = request.query_params.get('subject')
        academic_year = request.query_params.get('academic_year')
        term = request.query_params.get('term')

        if not all([student_id, class_id, subject_id, academic_year, term]):
            return Response(
                {"detail": "All parameters required: student, class, subject, academic_year, term"},
                status=400
            )

        grade = get_object_or_404(
            Grade,
            student_id=student_id,
            class_obj_id=class_id,
            subject_id=subject_id,
            academic_year=academic_year,
            term=term
        )

        if request.method == 'GET':
            ranks = AcademicReportGenerator.get_subject_ranks_dict(class_id, academic_year)
            
            serializer = self.get_serializer(grade, context={'subject_ranks': ranks})
            return Response(serializer.data)
            
        elif request.method == 'PATCH':
            serializer = self.get_serializer(grade, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        # Pull parameters from the request
        class_id = self.request.query_params.get("class")
        academic_year = self.request.query_params.get("academic_year")

        # If IDs are present, fetch the rank map and put it in context
        if class_id and academic_year:
            context['subject_ranks'] = AcademicReportGenerator.get_subject_ranks_dict(
                class_id, academic_year
            )
            
        return context
# --------------------------
# Transcript ViewSet
# --------------------------
class TranscriptViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {
            'academic_year': self.request.query_params.get('academic_year'),
            'term': self.request.query_params.get('term')
        }

    def list(self, request):
        class_name = request.query_params.get('class_name')
        academic_year = request.query_params.get('academic_year')
        search = request.query_params.get('search')
        status_filter = request.query_params.get('status')

        students = Student.objects.all()

        if class_name:
            students = students.filter(enrollments__class_obj__class_name=class_name)
        if academic_year:
            students = students.filter(enrollments__class_obj__academic_year=academic_year)
        if search:
            students = students.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(student_id__icontains=search)
            )
        if status_filter:
            students = students.filter(status=status_filter)

        students = students.distinct()

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        total_count = students.count()
        students_page = students[start:end]

        serializer = ClassStudentListSerializer(students_page, many=True)
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': serializer.data
        })

    def retrieve(self, request, pk=None):
        student = get_object_or_404(Student, pk=pk)
        academic_year = request.query_params.get('academic_year')
        term = request.query_params.get('term')
        serializer = StudentTranscriptSerializer(student, context={'academic_year': academic_year, 'term': term})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        student = get_object_or_404(Student, pk=pk)
        return Response({
            'message': 'PDF generation endpoint',
            'student_id': student.student_id,
            'student_name': f"{student.first_name} {student.last_name}"
        })

    @action(detail=False, methods=['get'])
    def class_summary(self, request):
        class_name = request.query_params.get('class_name', 'Grade 10-B')
        academic_year = request.query_params.get('academic_year', '2025/26')
        try:
            class_obj = Class.objects.get(class_name=class_name, academic_year=academic_year)
            total_students = class_obj.enrollments.count()
            active_students = class_obj.enrollments.filter(student__status='active').count()
            students_on_leave = class_obj.enrollments.filter(student__status='on_leave').count()
            return Response({
                'total_students': total_students,
                'active_students': active_students,
                'students_on_leave': students_on_leave,
                'academic_year': academic_year
            })
        except Class.DoesNotExist:
            return Response({
                'total_students': 0,
                'active_students': 0,
                'students_on_leave': 0,
                'academic_year': academic_year
            })

    @action(detail=False, methods=['get'])
    def available_classes(self, request):
        classes = Class.objects.values('id', 'class_name', 'academic_year').distinct()
        return Response(list(classes))

    @action(detail=False, methods=['get'])
    def available_years(self, request):
        years = Class.objects.values_list('academic_year', flat=True).distinct().order_by('-academic_year')
        return Response(list(years))
