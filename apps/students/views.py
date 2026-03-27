import pandas as pd
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Student, Parent, StudentParent, StudentAttendance
from .serializers import (
    StudentSerializer, StudentCreateSerializer, StudentUpdateSerializer,
    ParentSerializer, StudentParentSerializer, StudentDetailSerializer,
    StudentAttendanceSerializer, ParentAccessSerializer
)
from apps.attendance.models import Attendance 
from apps.attendance.serializers import AttendanceSerializer 

from apps.grades.serializers import StudentMinimalSerializer, StudentTranscriptSerializer
from .services import StudentService, ParentService
from apps.accounts.permissions import CanManageStudents, IsAdminOrHeadmaster
import logging

logger = logging.getLogger(__name__)


class StudentViewSet(viewsets.ModelViewSet):
    """ViewSet for Student management"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated, CanManageStudents]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StudentUpdateSerializer
        elif self.action == 'retrieve':
            return StudentDetailSerializer
        return StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.select_related('class_obj') 
            
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(middle_name__icontains=search) |
                Q(admission_number__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """Register a new student with exception handling"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            student_data = {
                'admission_number': serializer.validated_data['admission_number'],
                'first_name': serializer.validated_data['first_name'],
                'last_name': serializer.validated_data['last_name'],
                'middle_name': serializer.validated_data.get('middle_name', ''),
                'date_of_birth': serializer.validated_data['date_of_birth'],
                'gender': serializer.validated_data['gender'],
                'address': serializer.validated_data.get('address', ''),
                'nationality': serializer.validated_data.get('nationality', ''),
                'religion': serializer.validated_data.get('religion', ''),
                'blood_group': serializer.validated_data.get('blood_group', ''),
                'medical_conditions': serializer.validated_data.get('medical_conditions', ''),
                'admission_date': serializer.validated_data.get('admission_date'),
                'photo_url': serializer.validated_data.get('photo_url', ''),
            }
            
            parent_data_list = serializer.validated_data.get('parents', [])
            
            class_id = serializer.validated_data.get('class_obj')
            
            service = StudentService()
            result = service.register_student(
                student_data=student_data,
                parent_data_list=parent_data_list,
                class_id=class_id,
                created_by=request.user
            )
            
            response_data = StudentDetailSerializer(result['student']).data
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating student: {str(e)}")
            
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
            logger.error(f"Integrity error creating student: {str(e)}")
            error_detail = 'Admission number already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating student: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while registering the student.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
    def update(self, request, *args, **kwargs):
        """Update student information with exception handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            service = StudentService()
            student = service.update_student(instance.id, serializer.validated_data)
            return Response(StudentSerializer(student).data)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error updating student: {str(e)}")
            
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
            logger.error(f"Integrity error updating student: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating student: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while updating the student.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def add_parent(self, request, pk=None):
        """Add a parent to a student with exception handling"""
        try:
            student = self.get_object()
            parent_data = request.data
            
            service = StudentService()
            parent = service.add_parent_to_student(student.id, parent_data)
            return Response(ParentSerializer(parent).data, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error adding parent to student {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error adding parent to student {pk}: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while adding the parent.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def transfer_class(self, request, pk=None):
        """Transfer student to a new class with exception handling"""
        try:
            student = self.get_object()
            
            new_class_id = request.data.get('class_id')
            if not new_class_id:
                error_detail = 'class_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = StudentService()
            enrollment = service.transfer_student(student.id, new_class_id)
            from apps.academic.serializers import EnrollmentSerializer
            return Response(EnrollmentSerializer(enrollment).data)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error transferring student {pk}: {str(e)}")
            
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
            logger.error(f"Unexpected error transferring student {pk}: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while transferring the student.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def full_details(self, request, pk=None):
        """Get full student details with exception handling"""
        try:
            student = self.get_object()
            
            service = StudentService()
            details = service.get_student_with_details(student.id)
            
            transcript_serializer = StudentTranscriptSerializer(details['student'])
            
            from apps.attendance.serializers import AttendanceSerializer
            
            return Response({
                "status": "success",
                "data": {
                    'student': StudentDetailSerializer(details['student']).data,
                    'parents': ParentSerializer(details['parents'], many=True).data,
                    'academic_record': transcript_serializer.data, 
                    'recent_attendance': AttendanceSerializer(details['attendance'][:30], many=True).data,
                    'current_enrollment': details['current_enrollment'].class_obj.class_name if details['current_enrollment'] else "Not Enrolled"
                }
            })
            
        except Student.DoesNotExist:
            logger.error(f"Student {pk} not found")
            error_detail = f'Student with id {pk} not found.'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Unexpected error getting full details for student {pk}: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while retrieving student details.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Delete a student record with exception handling"""
        try:
            instance = self.get_object()
            service = StudentService()
            
            service.delete_student(instance.id)
            return Response(
                {"message": "Student deleted successfully"}, 
                status=status.HTTP_204_NO_CONTENT
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error deleting student: {str(e)}")
            
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
            logger.error(f"Unexpected error deleting student: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while deleting the student.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_excel(file, encoding='latin-1')

                 
            # 2. Flexible column check (case-insensitive and strip whitespace)
            df.columns = [c.lower().strip() for c in df.columns]
            df = df.dropna(how='all')
            
            # 3. Validation
            required_columns = ['admission_number', 'first_name', 'last_name', 'date_of_birth', 'gender']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                return Response({'error': f'Missing required columns: {", ".join(missing_cols)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. Data Sanitization
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
            df['admission_number'] = df['admission_number'].astype(str).replace(r'\.0$', '', regex=True)

            if 'class_id' in df.columns:
                df['class_id'] = df['class_id'].astype(str).replace(r'\.0$', '', regex=True)

            # 5. Execute service
            service = StudentService()
            results = service.bulk_upload_students(df, created_by=request.user)

            return Response({
                "summary": {
                    "total": len(df),
                    "success": results['success_count'],
                    "failed": results['fail_count']
                },
                "errors": results['errors']
            }, status=status.HTTP_201_CREATED if results['success_count'] > 0 else status.HTTP_207_MULTI_STATUS)
        
        except Exception as e:
            logger.error(f"Bulk upload failed: {str(e)}", exc_info=True)
            return Response({"error": f"Failed to process file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class ParentViewSet(viewsets.ModelViewSet):
    """ViewSet for Parent management"""
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated, CanManageStudents]
    
    def get_queryset(self):
        queryset = super().get_queryset().distinct()
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search)
            )

        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(
                student_links__student__enrollments__class_obj_id=class_id,
                student_links__student__enrollments__status="active"
            )

        year_id = self.request.query_params.get('academic_year_id', None)
        if year_id:
            queryset = queryset.filter(
                student_links__student__enrollments__class_obj__academic_year_id=year_id,
                student_links__student__enrollments__status="active"
            )
        
        return queryset

    @action(detail=False, methods=['get'], url_path='app-access')
    def app_access(self, request):
        """
        List parent app-access rows with latest invite details for frontend app-access page.
        """
        queryset = (
            self.get_queryset()
            .select_related('user')
            .prefetch_related(
                'student_links__student',
                'invites',
            )
            .order_by('last_name', 'first_name')
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ParentAccessSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ParentAccessSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create parent with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating parent: {str(e)}")
            
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
            logger.error(f"Integrity error creating parent: {str(e)}")
            error_detail = 'Parent with this email or phone already exists or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating parent: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the parent.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update parent with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error updating parent: {str(e)}")
            
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
            logger.error(f"Integrity error updating parent: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating parent: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the parent.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get all children linked to a parent with exception handling"""
        try:
            parent = self.get_object()
            service = ParentService()
            children = service.get_parent_children(parent.id)
            return Response(StudentSerializer(children, many=True).data)
            
        except Parent.DoesNotExist:
            logger.error(f"Parent {pk} not found")
            error_detail = f'Parent with id {pk} not found.'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Unexpected error getting children for parent {pk}: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while retrieving children.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class StudentParentViewSet(viewsets.ModelViewSet):
    """ViewSet for StudentParent relationship management"""
    
    queryset = StudentParent.objects.select_related('student', 'parent').all()
    serializer_class = StudentParentSerializer
    permission_classes = [IsAuthenticated, CanManageStudents]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        parent_id = self.request.query_params.get('parent_id', None)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create student-parent relationship with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating student-parent link: {str(e)}")
            
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
            logger.error(f"Integrity error creating student-parent link: {str(e)}")
            error_detail = 'This parent is already linked to this student or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating student-parent link: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the student-parent link.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudentAttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for StudentAttendance management"""
    
    queryset = StudentAttendance.objects.select_related('student').all()
    serializer_class = StudentAttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search)
            )
        
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(attendance_date=date)
        
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(attendance_date__range=[start_date, end_date])
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_attendance(self, request):

        records = request.data.get('attendance_records', [])

        if not records:
            return Response(
                {'error': 'attendance_records is required and cannot be empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(records, list):
            return Response(
                {'error': 'attendance_records must be a list.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created    = []
        updated    = []
        errors     = []

        for index, record in enumerate(records):
            student_id      = record.get('student_id')
            attendance_date = record.get('attendance_date')
            att_status      = record.get('status', 'present')
            remarks         = record.get('remarks', '')

            if not student_id:
                errors.append({'index': index, 'error': 'student_id is required.'})
                continue

            if not attendance_date:
                errors.append({'index': index, 'student_id': student_id, 'error': 'attendance_date is required.'})
                continue

            try:
                student = Student.objects.get(pk=student_id)
            except Student.DoesNotExist:
                errors.append({'index': index, 'student_id': student_id, 'error': f'Student {student_id} does not exist.'})
                continue

            try:
                attendance, was_created = Attendance.objects.update_or_create(
                    student=student,
                    attendance_date=attendance_date,
                    defaults={
                        'status':  att_status,
                        'remarks': remarks,
                        'recorded_by': request.user,
                    }
                )

                serialized = AttendanceSerializer(attendance).data
                if was_created:
                    created.append(serialized)
                else:
                    updated.append(serialized)

            except Exception as e:
                logger.error(f"Error saving attendance for student {student_id}: {e}", exc_info=True)
                errors.append({'index': index, 'student_id': student_id, 'error': str(e)})

        response_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED

        return Response(
            {
                'summary': {
                    'total':   len(records),
                    'created': len(created),
                    'updated': len(updated),
                    'failed':  len(errors),
                },
                'created': created,
                'updated': updated,
                'errors':  errors,
            },
            status=response_status
        )


    def create(self, request, *args, **kwargs):
        """Create attendance with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating attendance: {str(e)}")
            
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
            logger.error(f"Integrity error creating attendance: {str(e)}")
            error_detail = 'Attendance already exists for this student and date or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating attendance: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the attendance record.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update attendance with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error updating attendance: {str(e)}")
            
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
            logger.error(f"Integrity error updating attendance: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating attendance: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the attendance record.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

