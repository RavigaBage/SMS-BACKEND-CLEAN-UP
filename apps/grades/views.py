from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Grade, Student, Class
from .serializers import GradeSerializer, ClassStudentListSerializer, StudentTranscriptSerializer
from apps.accounts.permissions import CanManageGrades
from .Utils import AcademicReportGenerator
import logging

logger = logging.getLogger(__name__)


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

    def create(self, request, *args, **kwargs):
        """Create grade with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error creating grade: {str(e)}")
            
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
            logger.error(f"Integrity error creating grade: {str(e)}")
            error_detail = 'Grade already exists for this student, subject, and term or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating grade: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the grade.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update grade with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except ValidationError as e:
            logger.error(f"Validation error updating grade: {str(e)}")
            
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
            logger.error(f"Integrity error updating grade: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating grade: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the grade.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get', 'patch'], url_path='by-params')
    def get_by_params(self, request):
        """Get or update grade by parameters with exception handling"""
        try:
            student_id = request.query_params.get('student')
            class_id = request.query_params.get('class')
            subject_id = request.query_params.get('subject')
            academic_year = request.query_params.get('academic_year')
            term = request.query_params.get('term')

            if not all([student_id, class_id, subject_id, academic_year, term]):
                error_detail = "All parameters required: student, class, subject, academic_year, term"
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
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
                
        except Grade.DoesNotExist:
            logger.error(f"Grade not found with params: student={student_id}, class={class_id}, subject={subject_id}")
            error_detail = 'Grade not found with the provided parameters.'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except ValidationError as e:
            logger.error(f"Validation error in get_by_params: {str(e)}")
            
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
            logger.error(f"Unexpected error in get_by_params: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while processing the grade.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        class_id = self.request.query_params.get("class")
        academic_year = self.request.query_params.get("academic_year")

        if class_id and academic_year:
            try:
                context['subject_ranks'] = AcademicReportGenerator.get_subject_ranks_dict(
                    class_id, academic_year
                )
            except Exception as e:
                logger.error(f"Error getting subject ranks: {str(e)}")
                context['subject_ranks'] = {}
            
        return context

class TranscriptViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {
            'academic_year': self.request.query_params.get('academic_year'),
            'term': self.request.query_params.get('term')
        }

    def list(self, request):
        """List students with transcript data with exception handling"""
        try:
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
            
        except ValueError as e:
            logger.error(f"Value error in transcript list: {str(e)}")
            error_detail = 'Invalid page or page_size parameter. Must be a valid number.'
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in transcript list: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving student transcripts.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Retrieve student transcript with exception handling"""
        try:
            student = get_object_or_404(Student, pk=pk)
            academic_year = request.query_params.get('academic_year')
            term = request.query_params.get('term')
            
            serializer = StudentTranscriptSerializer(
                student, 
                context={'academic_year': academic_year, 'term': term}
            )
            return Response(serializer.data)
            
        except Student.DoesNotExist:
            logger.error(f"Student with id {pk} not found")
            error_detail = f'Student with id {pk} not found.'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving transcript for student {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving the student transcript.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download transcript as PDF with exception handling"""
        try:
            student = get_object_or_404(Student, pk=pk)
            
            # TODO: Implement actual PDF generation
            return Response({
                'message': 'PDF generation endpoint',
                'student_id': student.student_id,
                'student_name': f"{student.first_name} {student.last_name}"
            })
            
        except Student.DoesNotExist:
            logger.error(f"Student with id {pk} not found for PDF download")
            error_detail = f'Student with id {pk} not found.'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF for student {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while generating the PDF.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def class_summary(self, request):
        """Get class summary statistics with exception handling"""
        try:
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
                logger.info(f"Class not found: {class_name} for year {academic_year}")
                return Response({
                    'total_students': 0,
                    'active_students': 0,
                    'students_on_leave': 0,
                    'academic_year': academic_year
                })
                
        except Exception as e:
            logger.error(f"Unexpected error in class_summary: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving class summary.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_classes(self, request):
        """Get available classes with exception handling"""
        try:
            classes = Class.objects.values('id', 'class_name', 'academic_year').distinct()
            return Response(list(classes))
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving available classes: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving available classes.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_years(self, request):
        """Get available academic years with exception handling"""
        try:
            years = Class.objects.values_list('academic_year', flat=True).distinct().order_by('-academic_year')
            return Response(list(years))
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving available years: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving available academic years.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )