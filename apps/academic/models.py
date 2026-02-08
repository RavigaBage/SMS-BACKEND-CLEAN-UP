from django.db import models
from apps.staff.models import Staff
from apps.students.models import Student
from apps.teachers.models import Teacher


class AcademicYear(models.Model):
    """Academic year configuration"""


    year_name = models.CharField(max_length=20, unique=True, help_text="e.g., '2024/2025'")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'academic_years'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['year_name']),
            models.Index(fields=['is_current']),
        ]
    
    def __str__(self):
        return f"{self.year_name} {'(Current)' if self.is_current else ''}"
    
    def save(self, *args, **kwargs):
        # Ensure only one academic year is marked as current
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Class(models.Model):
    """Class/Grade configuration"""
    
    class_name = models.CharField(max_length=50, help_text="e.g., 'Grade 5A'")
    grade_level = models.IntegerField(help_text="1-12 or your grading system")
    section = models.CharField(max_length=10, blank=True, help_text="A, B, C, etc.")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='classes')
    class_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_classes'
    )
    capacity = models.IntegerField(default=40)
    room_number = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'classes'
        verbose_name_plural = 'classes'
        unique_together = ['class_name', 'academic_year']
        ordering = ['grade_level', 'section']
        indexes = [
            models.Index(fields=['academic_year']),
        ]
    
    def __str__(self):
        return f"{self.class_name} ({self.academic_year.year_name})"
    
    @property
    def current_enrollment(self):
        return self.enrollments.filter(status='active').count()


class Subject(models.Model):
    """Subject/Course configuration"""
    subject_name = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    grade_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Which grade this subject is for (optional)"
    )
    
    class Meta:
        db_table = 'subjects'
        ordering = ['subject_code']
        indexes = [
            models.Index(fields=['subject_code']),
            models.Index(fields=['grade_level']),
        ]
    
    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class Enrollment(models.Model):
    """Student enrollment in classes"""
    
    class EnrollmentStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
    

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE)
    roll_number = models.IntegerField(null=True, blank=True, help_text="Position in class")
    
    class Meta:
        db_table = 'enrollments'
        unique_together = ['student', 'class_obj']
        ordering = ['roll_number']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['class_obj']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student.full_name} in {self.class_obj.class_name}"


class SubjectAssignment(models.Model):
    """Which teacher teaches which subject to which class"""

    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='subject_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='class_assignments')
    teacher = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subject_assignments'
    )
    
    class Meta:
        db_table = 'subject_assignments'
        unique_together = ['class_obj', 'subject']
        indexes = [
            models.Index(fields=['teacher']),
        ]
    
    def __str__(self):
        teacher_name = self.teacher.full_name if self.teacher else "No teacher assigned"
        return f"{self.subject.subject_name} - {self.class_obj.class_name} ({teacher_name})"