from django.db import models
from django.core.validators import RegexValidator
from apps.accounts.models import User


class Staff(models.Model):
    """
    Staff profile for all staff members (teachers, headmaster, bursar, etc.)
    Each staff member MUST have a user account.
    """
    
    class StaffType(models.TextChoices):
        TEACHER = 'teacher', 'Teacher'
        HEADMASTER = 'headmaster', 'Headmaster'
        BURSAR = 'bursar', 'Bursar'
        ADMIN_STAFF = 'admin_staff', 'Admin Staff'
        SUPPORT_STAFF = 'support_staff', 'Support Staff'
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'



    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True, help_text="Duplicate of user email for easy access")
    address = models.TextField(blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    
    staff_type = models.CharField(max_length=20, choices=StaffType.choices)
    specialization = models.CharField(
        max_length=100,
        blank=True,
        help_text="Teaching subject/area for teachers"
    )
    employment_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True, unique=True, null=True)
    health_info = models.TextField(
        blank=True,
        help_text="Blood group, allergies, medical conditions"
    )
    photo_url = models.URLField(blank=True, max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff'
        verbose_name_plural = 'staff'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['staff_type']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_staff_type_display()})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class SalaryStructure(models.Model):
    """Salary structure for staff members"""

    

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salary_structures')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'salary_structures'
        ordering = ['-effective_from']
        indexes = [
            models.Index(fields=['staff', 'effective_from']),
        ]
    
    def __str__(self):
        return f"{self.staff.full_name} - {self.base_salary} (from {self.effective_from})"
    
    @property
    def total_salary(self):
        return (
            self.base_salary +
            self.housing_allowance +
            self.transport_allowance +
            self.other_allowances
        )


class SalaryPayment(models.Model):
    """Monthly salary payments to staff"""
    
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH = 'cash', 'Cash'
        CHEQUE = 'cheque', 'Cheque'
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED  = 'failed',  'Failed'

    
    

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salary_payments')
    payment_period = models.CharField(max_length=20, help_text="e.g., 'January 2025'")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_salaries')
    remarks = models.TextField(blank=True)
    
    class Meta:
        db_table = 'salary_payments'
        ordering = ['-payment_period']
        unique_together = ['staff', 'payment_period']
        indexes = [
            models.Index(fields=['staff', 'payment_period']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.staff.full_name} - {self.payment_period}"


class StaffAttendance(models.Model):
    """Daily attendance tracking for staff"""
    
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        ON_LEAVE = 'on_leave', 'On Leave'
        HALF_DAY = 'half_day', 'Half Day'
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    remarks = models.TextField(blank=True)
    
    class Meta:
        db_table = 'staff_attendance'
        unique_together = ['staff', 'attendance_date']
        ordering = ['-attendance_date']
        indexes = [
            models.Index(fields=['staff', 'attendance_date']),
            models.Index(fields=['attendance_date']),
        ]
    
    def __str__(self):
        return f"{self.staff.full_name} - {self.attendance_date} ({self.get_status_display()})"


class LeaveRequest(models.Model):
    """Leave requests from staff"""
    
    class LeaveType(models.TextChoices):
        SICK = 'sick', 'Sick Leave'
        CASUAL = 'casual', 'Casual Leave'
        ANNUAL = 'annual', 'Annual Leave'
        MATERNITY = 'maternity', 'Maternity Leave'
        EMERGENCY = 'emergency', 'Emergency Leave'
    
    class LeaveStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['staff', 'status']),
            models.Index(fields=['start_date']),
        ]
    
    def __str__(self):
        return f"{self.staff.full_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"