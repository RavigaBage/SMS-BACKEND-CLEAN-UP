from django.db import models
from apps.students.models import Student
from apps.academic.models import Subject, Enrollment, Class
from apps.accounts.models import User

class Grade(models.Model):
    """
    Unified Grade model combining categorical assessment types 
    and weighted scoring metrics.
    """

    class Term(models.TextChoices):
        FIRST = "first", "First Term"
        SECOND = "second", "Second Term"
        THIRD = "third", "Third Term"

    class GradeType(models.TextChoices):
        ASSIGNMENT = 'assignment', 'Assignment'
        QUIZ = 'quiz', 'Quiz'
        MIDTERM = 'midterm', 'Midterm Exam'
        FINAL = 'final', 'Final Exam'
        PROJECT = 'project', 'Project'

    # --- Relationships ---
    # Use unique related_names to avoid the clashes from your previous error
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='academic_grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='academic_grades')
    class_obj = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name="class_grades",
        db_column="class_id"
    )
    enrollment = models.ForeignKey(
        Enrollment, 
        on_delete=models.CASCADE, 
        related_name='enrollment_grades',
        null=True, 
        blank=True
    )
    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='grades_recorded'
    )

    
    academic_year = models.CharField(max_length=9, default="2025-2026")
    term = models.CharField(max_length=10, choices=Term.choices, default=Term.FIRST, db_index=True)
    grade_type = models.CharField(max_length=20, choices=GradeType.choices, blank=True)
    grade_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    assessment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    assessment_total = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    test_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    test_total = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_total = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    weighted_assessment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weighted_test = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weighted_exam = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade_letter = models.CharField(max_length=2, blank=True)

    class Meta:
        db_table = "grades"
        unique_together = ["student", "class_obj", "subject", "academic_year", "term"]
        ordering = ['-grade_date']
        indexes = [
            models.Index(fields=['student', 'subject']),
            models.Index(fields=['term', 'academic_year']),
        ]

    def __str__(self):
        return f"{self.student} | {self.subject} | {self.total_score}%"

    def save(self, *args, **kwargs):
        # Automatically calculate total_score before saving
        self.total_score = self.weighted_assessment + self.weighted_test + self.weighted_exam
        self.grade_letter = self.calculate_letter_grade(self.total_score)
        super().save(*args, **kwargs)

    def calculate_letter_grade(self, score):
        if score >= 90: return 'A+'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        elif score >= 50: return 'D'
        return 'F'