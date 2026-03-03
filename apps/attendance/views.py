from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import datetime, timedelta
from .models import Attendance
from .serializers import AttendanceSerializer, BulkAttendanceSerializer, AttendanceReportSerializer
from apps.accounts.permissions import CanManageStudents
import logging

logger = logging.getLogger(__name__)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance management"""
    
    queryset = Attendance.objects.select_related('student', 'class_obj', 'marked_by').all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, CanManageStudents]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        
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
            error_detail = 'Attendance record already exists for this student on this date or database constraint violated.'
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
    
    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def bulk_mark(self, request):
        """Mark attendance for multiple students at once"""
        try:
            serializer = BulkAttendanceSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        'error': f'Validation Error: {serializer.errors}',
                        'detail': serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            class_id = serializer.validated_data['class_id']
            attendance_date = serializer.validated_data['attendance_date']
            attendance_records = serializer.validated_data['attendance_records']
            
            created_records = []
            updated_records = []
            errors = []
            
            for record in attendance_records:
                try:
                    student_id = record['student_id']
                    status_value = record['status']
                    remarks = record.get('remarks', '')
                    
                    attendance, created = Attendance.objects.update_or_create(
                        student_id=student_id,
                        attendance_date=attendance_date,
                        defaults={
                            'class_obj_id': class_id,
                            'status': status_value,
                            'remarks': remarks,
                            'marked_by': request.user
                        }
                    )
                    
                    if created:
                        created_records.append(attendance)
                    else:
                        updated_records.append(attendance)
                        
                except Exception as e:
                    logger.error(f"Error processing attendance for student {student_id}: {str(e)}")
                    errors.append({
                        'student_id': student_id,
                        'error': str(e)
                    })
            
            return Response({
                'created': AttendanceSerializer(created_records, many=True).data,
                'updated': AttendanceSerializer(updated_records, many=True).data,
                'errors': errors
            }, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error in bulk mark: {str(e)}")
            
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
            logger.error(f"Unexpected error in bulk mark: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while marking bulk attendance.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def class_attendance(self, request):
        """Get attendance for entire class on a specific date"""
        try:
            class_id = request.query_params.get('class_id')
            date = request.query_params.get('date', datetime.now().date())
            
            if not class_id:
                error_detail = 'class_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from apps.academic.models import Enrollment
            enrollments = Enrollment.objects.filter(
                class_obj_id=class_id,
                status='active'
            ).select_related('student')
            
            attendance_records = Attendance.objects.filter(
                class_obj_id=class_id,
                attendance_date=date
            )
            
            attendance_map = {
                record.student_id: record for record in attendance_records
            }
            
            students_data = []
            for enrollment in enrollments:
                student = enrollment.student
                attendance = attendance_map.get(student.id)
                
                students_data.append({
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'admission_number': student.admission_number,
                    'roll_number': enrollment.roll_number,
                    'attendance': AttendanceSerializer(attendance).data if attendance else None
                })
            
            return Response({
                'class_id': class_id,
                'date': date,
                'total_students': len(students_data),
                'marked': len(attendance_records),
                'unmarked': len(students_data) - len(attendance_records),
                'students': students_data
            })
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error getting class attendance: {str(e)}")
            
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
            logger.error(f"Unexpected error getting class attendance: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving class attendance.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def student_report(self, request):
        """Get attendance report for a student"""
        try:
            student_id = request.query_params.get('student_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not student_id:
                error_detail = 'student_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not start_date or not end_date:
                today = datetime.now().date()
                start_date = today.replace(day=1)
                end_date = today
            
            attendance_records = Attendance.objects.filter(
                student_id=student_id,
                attendance_date__range=[start_date, end_date]
            )
            
            total_days = attendance_records.count()
            present_days = attendance_records.filter(status='present').count()
            absent_days = attendance_records.filter(status='absent').count()
            late_days = attendance_records.filter(status='late').count()
            excused_days = attendance_records.filter(status='excused').count()
            
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
            
            from apps.students.models import Student
            student = Student.objects.get(id=student_id)
            
            report_data = {
                'student': student,
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'excused_days': excused_days,
                'attendance_percentage': round(attendance_percentage, 2)
            }
            
            serializer = AttendanceReportSerializer(report_data)
            return Response(serializer.data)
            
        except Student.DoesNotExist:
            logger.error(f"Student {student_id} not found")
            error_detail = f'Student with id {student_id} not found'
            return Response(
                {
                    'error': f'Not Found: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error getting student report: {str(e)}")
            
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
            logger.error(f"Unexpected error getting student report: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while generating the student report.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def class_summary(self, request):
        """Get attendance summary for a class"""
        try:
            class_id = request.query_params.get('class_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not class_id:
                error_detail = 'class_id is required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not start_date or not end_date:
                today = datetime.now().date()
                start_date = today.replace(day=1)
                end_date = today
            
            attendance_records = Attendance.objects.filter(
                class_obj_id=class_id,
                attendance_date__range=[start_date, end_date]
            )
            
            total_records = attendance_records.count()
            status_breakdown = attendance_records.values('status').annotate(count=Count('id'))
            
            unique_dates = attendance_records.values('attendance_date').distinct().count()
            
            return Response({
                'class_id': class_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': unique_dates,
                'total_records': total_records,
                'status_breakdown': list(status_breakdown)
            })
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error getting class summary: {str(e)}")
            
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
            logger.error(f"Unexpected error getting class summary: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while generating the class summary.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def defaulters(self, request):
        """Get list of students with low attendance"""
        try:
            class_id = request.query_params.get('class_id')
            threshold = float(request.query_params.get('threshold', 75))  
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                today = datetime.now().date()
                start_date = today.replace(day=1)
                end_date = today
            
            from apps.academic.models import Enrollment
            query = Enrollment.objects.filter(status='active').select_related('student')
            
            if class_id:
                query = query.filter(class_obj_id=class_id)
            
            defaulters = []
            
            for enrollment in query:
                student = enrollment.student
                
                attendance_records = Attendance.objects.filter(
                    student=student,
                    attendance_date__range=[start_date, end_date]
                )
                
                total_days = attendance_records.count()
                if total_days == 0:
                    continue
                
                present_days = attendance_records.filter(status='present').count()
                attendance_percentage = (present_days / total_days * 100)
                
                if attendance_percentage < threshold:
                    defaulters.append({
                        'student_id': student.id,
                        'student_name': student.full_name,
                        'admission_number': student.admission_number,
                        'class': enrollment.class_obj.class_name,
                        'total_days': total_days,
                        'present_days': present_days,
                        'attendance_percentage': round(attendance_percentage, 2)
                    })
            
            return Response({
                'threshold': threshold,
                'start_date': start_date,
                'end_date': end_date,
                'total_defaulters': len(defaulters),
                'defaulters': defaulters
            })
            
        except ValueError as e:
            logger.error(f"Value error in defaulters (threshold): {str(e)}")
            error_detail = 'Invalid threshold value. Must be a number between 0 and 100.'
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error getting defaulters: {str(e)}")
            
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
            logger.error(f"Unexpected error getting defaulters: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while getting attendance defaulters.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
