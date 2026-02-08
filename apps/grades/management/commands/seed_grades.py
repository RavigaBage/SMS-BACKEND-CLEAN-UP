import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.grades.models import Grade
from apps.academic.models import Subject, Enrollment
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Seeds grades with a realistic spread from lowest to highest'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Grades...")

        admin_user = User.objects.filter(role='admin').first()
        enrollments = Enrollment.objects.select_related('student', 'class_obj').all()
        subjects = Subject.objects.all()

        if not enrollments.exists() or not subjects.exists():
            self.stdout.write(self.style.ERROR("Missing Enrollments or Subjects. Run previous seeds first!"))
            return

        with transaction.atomic():
            # We will clear existing grades to avoid unique_together conflicts
            Grade.objects.all().delete()

            # Weighting Logic: 
            # Assessment (20%), Test (30%), Exam (50%)
            
            for subject in subjects:
                # Sort enrollments by student name to apply a consistent spread
                sorted_enrollments = sorted(enrollments, key=lambda e: e.student.first_name)
                total_students = len(sorted_enrollments)

                for index, enrollment in enumerate(sorted_enrollments):
                    # Progress from 0.0 to 1.0 based on position in the list
                    progression = index / (total_students - 1) if total_students > 1 else 0.5
                    
                    # Calculate raw scores (out of 100)
                    # Lowest: ~30, Highest: ~98
                    base_score = 30 + (progression * 65) + random.uniform(-3, 3)
                    base_score = min(max(base_score, 0), 100)

                    # Calculate Weighted components
                    # Assessment: 20% of base
                    w_assessment = Decimal(base_score * 0.20).quantize(Decimal('0.00'))
                    # Test: 30% of base
                    w_test = Decimal(base_score * 0.30).quantize(Decimal('0.00'))
                    # Exam: 50% of base
                    w_exam = Decimal(base_score * 0.50).quantize(Decimal('0.00'))

                    Grade.objects.create(
                        student=enrollment.student,
                        subject=subject,
                        class_obj=enrollment.class_obj,
                        enrollment=enrollment,
                        entered_by=admin_user,
                        academic_year="2025-2026",
                        term=Grade.Term.FIRST,
                        grade_type=Grade.GradeType.FINAL,
                        
                        # Raw Score inputs
                        assessment_score=Decimal(base_score),
                        test_score=Decimal(base_score),
                        exam_score=Decimal(base_score),
                        
                        # Weighted values (used by your save() method)
                        weighted_assessment=w_assessment,
                        weighted_test=w_test,
                        weighted_exam=w_exam,
                        
                        remarks="Performance tracked via automated seed."
                    )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded grades for {enrollments.count()} students across {subjects.count()} subjects!"))