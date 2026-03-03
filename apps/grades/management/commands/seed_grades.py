import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.academic.models import Enrollment, Subject
from apps.grades.models import Grade


class Command(BaseCommand):
    help = "Seed grades with realistic spread across students/subjects/terms."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=str, default="2025-2026")
        parser.add_argument(
            "--terms",
            type=str,
            default="first,second,third",
            help="Comma-separated terms from: first,second,third",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing grades for selected year/terms before seeding.",
        )

    def handle(self, *args, **options):
        year_name = options["year"].strip()
        terms = [t.strip().lower() for t in options["terms"].split(",") if t.strip()]
        reset = options["reset"]

        valid_terms = {choice[0] for choice in Grade.Term.choices}
        terms = [t for t in terms if t in valid_terms]
        if not terms:
            terms = [Grade.Term.FIRST]

        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        enrollments = list(
            Enrollment.objects.select_related("student", "class_obj").filter(
                status=Enrollment.EnrollmentStatus.ACTIVE
            )
        )
        subjects = list(Subject.objects.all())

        if not enrollments or not subjects:
            self.stdout.write(
                self.style.ERROR("Missing enrollments or subjects. Run academic/students seed first.")
            )
            return

        self.stdout.write(self.style.NOTICE("Seeding grades..."))
        with transaction.atomic():
            if reset:
                Grade.objects.filter(academic_year=year_name, term__in=terms).delete()

            created_or_updated = 0
            sorted_enrollments = sorted(enrollments, key=lambda e: (e.class_obj_id, e.student.first_name))
            total_students = len(sorted_enrollments)

            for subject in subjects:
                for index, enrollment in enumerate(sorted_enrollments):
                    progression = index / (total_students - 1) if total_students > 1 else 0.5
                    base_score = 35 + (progression * 60) + random.uniform(-4, 4)
                    base_score = float(min(max(base_score, 0), 100))

                    assessment = Decimal(base_score * 0.20).quantize(Decimal("0.01"))
                    test = Decimal(base_score * 0.30).quantize(Decimal("0.01"))
                    exam = Decimal(base_score * 0.50).quantize(Decimal("0.01"))

                    for term in terms:
                        _, created = Grade.objects.update_or_create(
                            student=enrollment.student,
                            subject=subject,
                            class_obj=enrollment.class_obj,
                            academic_year=year_name,
                            term=term,
                            defaults={
                                "enrollment": enrollment,
                                "entered_by": admin_user,
                                "grade_type": Grade.GradeType.FINAL,
                                "assessment_score": Decimal(base_score).quantize(Decimal("0.01")),
                                "test_score": Decimal(base_score).quantize(Decimal("0.01")),
                                "exam_score": Decimal(base_score).quantize(Decimal("0.01")),
                                "weighted_assessment": assessment,
                                "weighted_test": test,
                                "weighted_exam": exam,
                                "remarks": "Auto-seeded for pagination and test data.",
                            },
                        )
                        created_or_updated += 1

        total = Grade.objects.filter(academic_year=year_name, term__in=terms).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Grades seed complete. Upserted {created_or_updated} rows. Total now {total} for {year_name}."
            )
        )
