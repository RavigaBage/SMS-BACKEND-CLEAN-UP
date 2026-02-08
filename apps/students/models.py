from django.db import models
from django.core.validators import RegexValidator
from apps.accounts.models import User


class Student(models.Model):
    """
    Student records - NO user account required.
    Students are just data records.
    """
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        GRADUATED = 'graduated', 'Graduated'
        SUSPENDED = 'suspended', 'Suspended'
        TRANSFERRED = 'transferred', 'Transferred'
        WITHDRAWN = 'withdrawn', 'Withdrawn'


    admission_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    
    address = models.TextField(blank=True)
    nationality = models.CharField(max_length=50, blank=True)
    religion = models.CharField(max_length=50, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    medical_conditions = models.TextField(
        blank=True,
        help_text="Any medical conditions, allergies, or special needs"
    )
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    admission_date = models.DateField()
    photo_url = models.URLField(blank=True, max_length=255)
    class_obj = models.ForeignKey('class.Class', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_students',
        help_text="Staff member who registered this student"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class_obj =  models.ForeignKey('academic.Class', on_delete=models.SET_NULL, null=True, blank=True)
    
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
                "id": c.id,
                "name": c.class_name,
                "grade_level": c.grade_level,
                "section": c.section,
                "academic_year": c.academic_year.year_name
            }
        return None
    


class Parent(models.Model):
    """
    Parent/Guardian records - NO user account required.
    Parents are just contact information.
    """
    
    class Relationship(models.TextChoices):
        FATHER = 'father', 'Father'
        MOTHER = 'mother', 'Mother'
        GUARDIAN = 'guardian', 'Guardian'
        OTHER = 'other', 'Other'

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    occupation = models.CharField(max_length=100, blank=True)
    workplace = models.CharField(max_length=100, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
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


class StudentParent(models.Model):
    """
    Many-to-Many relationship between students and parents.
    One student can have multiple parents/guardians.
    """
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parent_links')
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='student_links')
    is_primary_contact = models.BooleanField(
        default=False,
        help_text="Primary contact for school communications"
    )
    can_pickup = models.BooleanField(
        default=True,
        help_text="Authorized to pick up student from school"
    )
    
    class Meta:
        db_table = 'student_parents'
        unique_together = ['student', 'parent']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.parent.full_name}"