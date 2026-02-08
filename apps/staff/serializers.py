from rest_framework import serializers
from .models import Staff, SalaryStructure, SalaryPayment, StaffAttendance, LeaveRequest
from apps.accounts.serializers import UserSerializer

class StaffSerializer(serializers.ModelSerializer):
    """Serializer for Staff model"""
    
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    staff_type_display = serializers.CharField(source='get_staff_type_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    assigned_subjects = serializers.SerializerMethodField()
    
    managed_classes = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            'id', 'user', 'first_name', 'last_name', 'full_name',
            'date_of_birth', 'phone_number', 'email', 'address',
            'gender', 'gender_display', 'staff_type', 'staff_type_display',
            'specialization', 'employment_date', 'national_id',
            'health_info', 'photo_url', 'created_at', 'updated_at','managed_classes','assigned_subjects'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    def get_assigned_subjects(self, obj):
            """Returns subjects the staff is assigned to teach across different classes"""
            assignments = obj.subject_assignments.select_related('class_obj', 'subject', 'class_obj__academic_year')
            return [
                {
                    "id": a.id,
                    "subject_name": a.subject.subject_name,
                    "subject_code": a.subject.subject_code,
                    "class_name": a.class_obj.class_name,
                    "academic_year": a.class_obj.academic_year.year_name
                } for a in assignments
            ]

    def get_managed_classes(self, obj):
        """Returns classes where this staff is the main Class Teacher"""
        from apps.academic.serializers import AssignedClassSerializer
        try:
            
            if hasattr(obj.user, 'teacher_profile'): # Adjust based on your Teacher model's related_name
                classes = obj.user.teacher_profile.assigned_classes.all()
                return AssignedClassSerializer(classes, many=True).data
        except Exception:
            return []
        return []


class StaffCreateSerializer(serializers.Serializer):
    """Serializer for creating staff with user account"""
    
    # User fields
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, write_only=True, min_length=10)
    
    # Staff fields
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=17, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Staff.Gender.choices, required=False, allow_blank=True)
    staff_type = serializers.ChoiceField(choices=Staff.StaffType.choices)
    specialization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    employment_date = serializers.DateField(required=False, allow_null=True)
    national_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    health_info = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(required=False, allow_blank=True)
    
    # Salary fields (optional)
    base_salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    housing_allowance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    transport_allowance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    other_allowances = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    salary_effective_from = serializers.DateField(required=False)


class StaffUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating staff information"""
    
    class Meta:
        model = Staff
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'phone_number',
            'email', 'address', 'gender', 'specialization',
            'national_id', 'health_info', 'photo_url'
        ]


class SalaryStructureSerializer(serializers.ModelSerializer):
    """Serializer for SalaryStructure model"""
    
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    total_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = SalaryStructure
        fields = [
            'id', 'staff', 'staff_name', 'base_salary',
            'housing_allowance', 'transport_allowance', 'other_allowances',
            'total_salary', 'effective_from', 'effective_to'
        ]
        read_only_fields = ['id']


class SalaryPaymentSerializer(serializers.ModelSerializer):
    """Serializer for SalaryPayment model"""
    
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = SalaryPayment
        fields = [
            'id', 'staff', 'staff_name', 'payment_period',
            'base_salary', 'allowances', 'deductions', 'tax', 'net_salary',
            'payment_date', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'processed_by', 'processed_by_username',
            'remarks'
        ]
        read_only_fields = ['id']


class StaffAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for StaffAttendance model"""
    
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = StaffAttendance
        fields = [
            'id', 'staff', 'staff_name', 'attendance_date',
            'check_in', 'check_out', 'status', 'status_display', 'remarks'
        ]
        read_only_fields = ['id']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model"""
    
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'staff', 'staff_name', 'leave_type', 'leave_type_display',
            'start_date', 'end_date', 'total_days', 'reason',
            'status', 'status_display', 'approved_by', 'approved_by_username',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'approved_by']


class LeaveApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting leave requests"""
    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    remarks = serializers.CharField(required=False, allow_blank=True)


class StaffClassroomSerializer(serializers.Serializer):
    """Simplified classroom serializer for nesting inside Staff"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True) # e.g., "Grade 10 - Math"
    subject_name = serializers.CharField(read_only=True)
    student_count = serializers.IntegerField(read_only=True)