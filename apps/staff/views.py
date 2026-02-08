from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Staff, SalaryStructure, SalaryPayment, StaffAttendance, LeaveRequest
from .serializers import (
    StaffSerializer, StaffCreateSerializer, StaffUpdateSerializer,
    SalaryStructureSerializer, SalaryPaymentSerializer,
    StaffAttendanceSerializer, LeaveRequestSerializer, LeaveApprovalSerializer
)
from .services import StaffService, SalaryService
from apps.accounts.permissions import CanManageStaff, IsAdminOrHeadmaster


class StaffViewSet(viewsets.ModelViewSet):
    serializer_class = StaffSerializer

    def get_queryset(self):
        queryset = Staff.objects.all().select_related('user')
        
        role = self.request.query_params.get('role')
        department = self.request.query_params.get('department')
        status_param = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        
        if role:
            queryset = queryset.filter(staff_type__icontains=role)
        
        if department:
            queryset = queryset.filter(department__icontains=department)
        
        if status_param:
            queryset = queryset.filter(status__iexact=status_param)
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset

    def create(self, request, *args, **kwargs):
        """Create staff with user account"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        staff_data = {
            'first_name': serializer.validated_data['first_name'],
            'last_name': serializer.validated_data['last_name'],
            'date_of_birth': serializer.validated_data.get('date_of_birth'),
            'phone_number': serializer.validated_data.get('phone_number', ''),
            'address': serializer.validated_data.get('address', ''),
            'gender': serializer.validated_data.get('gender', ''),
            'staff_type': serializer.validated_data['staff_type'],
            'specialization': serializer.validated_data.get('specialization', ''),
            'employment_date': serializer.validated_data.get('employment_date'),
            'national_id': serializer.validated_data.get('national_id', ''),
            'health_info': serializer.validated_data.get('health_info', ''),
            'photo_url': serializer.validated_data.get('photo_url', ''),
        }
        
        # User data (optional)
        user_data = {}
        if 'username' in serializer.validated_data:
            user_data['username'] = serializer.validated_data['username']
        if 'email' in serializer.validated_data:
            user_data['email'] = serializer.validated_data['email']
        if 'password' in serializer.validated_data:
            user_data['password'] = serializer.validated_data['password']
        
        # Salary data (optional)
        if 'base_salary' in serializer.validated_data:
            staff_data['salary'] = {
                'base_salary': serializer.validated_data.get('base_salary', 0),
                'housing_allowance': serializer.validated_data.get('housing_allowance', 0),
                'transport_allowance': serializer.validated_data.get('transport_allowance', 0),
                'other_allowances': serializer.validated_data.get('other_allowances', 0),
                'effective_from': serializer.validated_data.get('salary_effective_from'),
            }
        
        # Create staff
        service = StaffService()
        result = service.create_staff_with_user(
            staff_data=staff_data,
            user_data=user_data if user_data else None,
            created_by=request.user
        )
        
        response_data = StaffSerializer(result['staff']).data
        
        # Include generated credentials if password was auto-generated
        if result['generated_password']:
            response_data['credentials'] = {
                'username': result['username'],
                'password': result['generated_password'],
                'message': 'Please share these credentials with the staff member. Password shown only once.'
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update staff information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        service = StaffService()
        staff = service.update_staff(instance.id, serializer.validated_data)
        
        return Response(StaffSerializer(staff).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanManageStaff])
    def deactivate(self, request, pk=None):
        """Deactivate staff member"""
        staff = self.get_object()
        
        service = StaffService()
        staff = service.deactivate_staff(staff.id, request.user)
        
        return Response({
            'message': f'{staff.full_name} has been deactivated',
            'staff': StaffSerializer(staff).data
        })
    
    @action(detail=False, methods=['get'])
    def teachers(self, request):
        """Get all active teachers"""
        service = StaffService()
        teachers = service.get_active_teachers()
        serializer = StaffSerializer(teachers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def salary_history(self, request, pk=None):
        """Get salary payment history for staff"""
        staff = self.get_object()
        payments = SalaryPayment.objects.filter(staff=staff).order_by('-payment_period')
        serializer = SalaryPaymentSerializer(payments, many=True)
        return Response(serializer.data)


class SalaryStructureViewSet(viewsets.ModelViewSet):
    """ViewSet for SalaryStructure management"""
    
    queryset = SalaryStructure.objects.select_related('staff').all()
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff_id', None)
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        return queryset


class SalaryPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for SalaryPayment management"""
    
    queryset = SalaryPayment.objects.select_related('staff', 'processed_by').all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff_id', None)
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment period
        payment_period = self.request.query_params.get('payment_period', None)
        if payment_period:
            queryset = queryset.filter(payment_period=payment_period)
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def process_salary(self, request):
        """Process monthly salary for a staff member"""
        staff_id = request.data.get('staff_id')
        payment_period = request.data.get('payment_period')
        
        if not staff_id or not payment_period:
            return Response(
                {'error': 'staff_id and payment_period are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = SalaryService()
        try:
            salary_payment = service.process_monthly_salary(
                staff_id=staff_id,
                payment_period=payment_period,
                processed_by=request.user
            )
            
            serializer = SalaryPaymentSerializer(salary_payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def mark_as_paid(self, request, pk=None):
        """Mark salary payment as paid"""
        salary_payment = self.get_object()
        
        payment_date = request.data.get('payment_date')
        payment_method = request.data.get('payment_method')
        
        if not payment_date or not payment_method:
            return Response(
                {'error': 'payment_date and payment_method are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = SalaryService()
        try:
            salary_payment = service.mark_salary_as_paid(
                salary_payment_id=salary_payment.id,
                payment_date=payment_date,
                payment_method=payment_method
            )
            
            serializer = SalaryPaymentSerializer(salary_payment)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffAttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for StaffAttendance management"""
    
    queryset = StaffAttendance.objects.select_related('staff').all()
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by staff ID
        staff_id = self.request.query_params.get('staff_id', None)
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by role/staff type
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(staff__staff_type__icontains=role)
        
        # Filter by search (staff name)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(staff__first_name__icontains=search) |
                Q(staff__last_name__icontains=search) |
                Q(staff__email__icontains=search)
            )
        
        # Filter by specific date
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(attendance_date=date)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(attendance_date__range=[start_date, end_date])
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for LeaveRequest management"""
    
    queryset = LeaveRequest.objects.select_related('staff', 'approved_by').all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Teachers can only see their own leave requests
        if self.request.user.role == 'teacher':
            queryset = queryset.filter(staff__user=self.request.user)
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff_id', None)
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        # If teacher, automatically set staff to their own profile
        if self.request.user.role == 'teacher':
            serializer.save(staff=self.request.user.staff_profile)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadmaster])
    def approve_reject(self, request, pk=None):
        """Approve or reject leave request"""
        leave_request = self.get_object()
        
        serializer = LeaveApprovalSerializer(data=request.data)
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            
            if action_type == 'approve':
                leave_request.status = LeaveRequest.LeaveStatus.APPROVED
            else:
                leave_request.status = LeaveRequest.LeaveStatus.REJECTED
            
            leave_request.approved_by = request.user
            leave_request.save()
            
            response_serializer = LeaveRequestSerializer(leave_request)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)