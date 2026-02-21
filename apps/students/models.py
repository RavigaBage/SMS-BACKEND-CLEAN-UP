import random
import string
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User


# ─── Student ──────────────────────────────────────────────────────────────────

class Student(models.Model):
    """
    Student records - NO user account required.
    Students are just data records.
    """

    class Gender(models.TextChoices):
        MALE   = 'male',   'Male'
        FEMALE = 'female', 'Female'
        OTHER  = 'other',  'Other'

    class Status(models.TextChoices):
        ACTIVE      = 'active',      'Active'
        GRADUATED   = 'graduated',   'Graduated'
        SUSPENDED   = 'suspended',   'Suspended'
        TRANSFERRED = 'transferred', 'Transferred'
        WITHDRAWN   = 'withdrawn',   'Withdrawn'

    admission_number = models.CharField(max_length=50, unique=True)
    first_name       = models.CharField(max_length=50)
    last_name        = models.CharField(max_length=50)
    middle_name      = models.CharField(max_length=50, blank=True)
    date_of_birth    = models.DateField()
    gender           = models.CharField(max_length=10, choices=Gender.choices)

    address           = models.TextField(blank=True)
    nationality       = models.CharField(max_length=50, blank=True)
    religion          = models.CharField(max_length=50, blank=True)
    blood_group       = models.CharField(max_length=5, blank=True)
    medical_conditions = models.TextField(blank=True)

    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    admission_date = models.DateField()
    photo_url      = models.URLField(blank=True, max_length=255)
    class_obj      = models.ForeignKey(
        'academic.Class', on_delete=models.SET_NULL, null=True, blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_students',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        ordering = ['admission_number']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['status']),
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.admission_number} - {self.full_name}"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def class_info(self):
        enrollment = self.enrollments.filter(status="active").select_related("class_obj").first()
        if enrollment:
            c = enrollment.class_obj
            return {
                "id":            c.id,
                "name":          c.class_name,
                "grade_level":   c.grade_level,
                "section":       c.section,
                "academic_year": c.academic_year.year_name,
            }
        return None


# ─── Parent ───────────────────────────────────────────────────────────────────

class Parent(models.Model):
    """
    Parent/Guardian records.
    Optionally linked to a User account for app access.
    The admin creates the User account and links it here.
    """

    class Relationship(models.TextChoices):
        FATHER   = 'father',   'Father'
        MOTHER   = 'mother',   'Mother'
        GUARDIAN = 'guardian', 'Guardian'
        OTHER    = 'other',    'Other'

    # ── Optional User account link ────────────────────────────────────────────
    # Null means no app access yet. Admin sets this when granting access.
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parent_profile',
        limit_choices_to={'role': 'parent'},
        help_text="Link to User account for app access. Leave blank until access is granted."
    )

    first_name   = models.CharField(max_length=50)
    last_name    = models.CharField(max_length=50)

    phone_regex  = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    email        = models.EmailField(blank=True)
    address      = models.TextField(blank=True)

    occupation   = models.CharField(max_length=100, blank=True)
    workplace    = models.CharField(max_length=100, blank=True)
    national_id  = models.CharField(max_length=50, blank=True)
    relationship = models.CharField(max_length=20, choices=Relationship.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parents'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def has_app_access(self):
        return self.user is not None

    @property
    def wards(self):
        """Return all students linked to this parent"""
        return Student.objects.filter(parent_links__parent=self)


# ─── StudentParent ────────────────────────────────────────────────────────────

class StudentParent(models.Model):
    """Many-to-Many bridge between students and parents."""

    student            = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parent_links')
    parent             = models.ForeignKey(Parent,  on_delete=models.CASCADE, related_name='student_links')
    is_primary_contact = models.BooleanField(default=False)
    can_pickup         = models.BooleanField(default=True)

    class Meta:
        db_table       = 'student_parents'
        unique_together = ['student', 'parent']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.student.full_name} ← {self.parent.full_name}"


# ─── ParentInvite ─────────────────────────────────────────────────────────────

def _generate_code():
    """Generate a random 8-character uppercase invite code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def _default_expiry():
    return timezone.now() + timedelta(days=7)


class ParentInvite(models.Model):
    """
    One-time invite code generated by admin for a parent.
    Parent redeems it in the app to create their login.
    Each code is tied to a specific Parent record.
    """

    code       = models.CharField(max_length=12, unique=True, default=_generate_code)
    parent     = models.ForeignKey(
        Parent, on_delete=models.CASCADE, related_name='invites'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='parent_invites_created'
    )
    used       = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=_default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'parent_invites'
        ordering = ['-created_at']

    def __str__(self):
        status = 'used' if self.used else ('expired' if self.is_expired else 'active')
        return f"Invite [{self.code}] → {self.parent.full_name} ({status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    def redeem(self, user: User):
        """Mark invite as used and link parent to the new user"""
        self.parent.user = user
        self.parent.save(update_fields=['user'])
        self.used    = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])


# ─── StudentAttendance ────────────────────────────────────────────────────────

class StudentAttendance(models.Model):
    """Daily attendance tracking for Student"""

    class AttendanceStatus(models.TextChoices):
        PRESENT  = 'present',  'Present'
        ABSENT   = 'absent',   'Absent'
        ON_LEAVE = 'on_leave', 'On Leave'
        HALF_DAY = 'half_day', 'Half Day'

    student         = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='daily_attendance_logs'
    )
    attendance_date = models.DateField()
    check_in        = models.DateTimeField(null=True, blank=True)
    check_out       = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    remarks         = models.TextField(blank=True)

    class Meta:
        db_table        = 'student_attendance'
        unique_together = ['student', 'attendance_date']
        ordering        = ['-attendance_date']
        indexes = [
            models.Index(fields=['student', 'attendance_date']),
            models.Index(fields=['attendance_date']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.attendance_date} ({self.get_status_display()})"