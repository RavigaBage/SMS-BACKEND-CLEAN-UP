from datetime import date
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academic.models import (
    AcademicYear,
    Class,
    Enrollment,
    Subject,
    SubjectAssignment,
)
from apps.staff.models import Staff
from apps.students.models import Student
from apps.teachers.models import Teacher


class Command(BaseCommand):
    help = "Populate academic year, classes, subjects, students, and enrollments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=str,
            default="2025-2026",
            help="Academic year label (example: 2025-2026).",
        )
        parser.add_argument(
            "--grades",
            type=str,
            default="1,2,3",
            help="Comma-separated grade levels (example: 1,2,3).",
        )
        parser.add_argument(
            "--sections",
            type=str,
            default="A,B",
            help="Comma-separated sections (example: A,B).",
        )
        parser.add_argument(
            "--students-per-section",
            type=int,
            default=40,
            help="Number of students to enroll in each class section.",
        )
        parser.add_argument(
            "--reset-enrollments",
            action="store_true",
            help="Delete enrollments for seeded classes before reassigning.",
        )

    def handle(self, *args, **options):
        year_name = options["year"].strip()
        grades = [int(g.strip()) for g in options["grades"].split(",") if g.strip()]
        sections = [s.strip().upper() for s in options["sections"].split(",") if s.strip()]
        students_per_section = max(1, int(options["students_per_section"]))
        reset_enrollments = options["reset_enrollments"]

        self.stdout.write(self.style.NOTICE("Seeding academic data..."))

        with transaction.atomic():
            teacher = Teacher.objects.select_related("user").first()
            if not teacher:
                self.stdout.write(
                    self.style.ERROR("No Teacher found. Seed/create teachers first.")
                )
                return

            staff_teacher = Staff.objects.filter(user=teacher.user).first()

            try:
                start_year = int(year_name.split("-")[0])
            except (ValueError, IndexError):
                self.stdout.write(
                    self.style.ERROR(
                        "Invalid --year format. Use format like 2025-2026."
                    )
                )
                return

            academic_year, _ = AcademicYear.objects.get_or_create(
                year_name=year_name,
                defaults={
                    "start_date": date(start_year, 9, 1),
                    "end_date": date(start_year + 1, 7, 31),
                    "is_current": True,
                },
            )
            if not academic_year.is_current:
                academic_year.is_current = True
                academic_year.save(update_fields=["is_current"])
            AcademicYear.objects.exclude(id=academic_year.id).update(is_current=False)

            subjects_data = [
                ("Mathematics", "MATH101"),
                ("English Language", "ENG101"),
                ("Integrated Science", "SCI101"),
                ("Social Studies", "SOC101"),
                ("Information Technology", "ICT101"),
                ("Creative Arts", "ART101"),
                ("Physical Education", "PE101"),
            ]

            subjects = []
            for subject_name, subject_code in subjects_data:
                subject, _ = Subject.objects.get_or_create(
                    subject_code=subject_code,
                    defaults={
                        "subject_name": subject_name,
                        "grade_level": min(grades) if grades else 1,
                    },
                )
                subjects.append(subject)

            classes = []
            for grade in grades:
                for section in sections:
                    class_name = f"Grade {grade}{section}"
                    cls, _ = Class.objects.get_or_create(
                        grade_level=grade,
                        section=section,
                        academic_year=year_name,
                        defaults={
                            "class_name": class_name,
                            "class_teacher": teacher,
                            "capacity": max(50, students_per_section + 5),
                            "room_number": f"R{grade}{section}",
                        },
                    )

                    dirty = False
                    if cls.class_name != class_name:
                        cls.class_name = class_name
                        dirty = True
                    if cls.class_teacher_id != teacher.id:
                        cls.class_teacher = teacher
                        dirty = True
                    if dirty:
                        cls.save()

                    classes.append(cls)

                    for subject in subjects:
                        assignment, created = SubjectAssignment.objects.get_or_create(
                            class_obj=cls,
                            subject=subject,
                            defaults={"teacher": staff_teacher},
                        )
                        if (
                            not created
                            and staff_teacher
                            and assignment.teacher_id != staff_teacher.id
                        ):
                            assignment.teacher = staff_teacher
                            assignment.save(update_fields=["teacher"])

            total_needed = len(classes) * students_per_section
            existing_students = list(Student.objects.order_by("id")[:total_needed])
            to_create = total_needed - len(existing_students)

            first_names = [
                "Kwame",
                "Akosua",
                "Kofi",
                "Ama",
                "Yaw",
                "Efua",
                "Kojo",
                "Abena",
                "Nana",
                "Yaa",
            ]
            last_names = [
                "Mensah",
                "Boateng",
                "Asante",
                "Owusu",
                "Adjei",
                "Appiah",
                "Agyeman",
                "Darko",
                "Ofori",
                "Bonsu",
            ]
            genders = [choice[0] for choice in Student.Gender.choices]

            seq = Student.objects.count() + 1
            for _ in range(to_create):
                while True:
                    admission_number = f"{start_year}{seq:05d}"
                    if not Student.objects.filter(admission_number=admission_number).exists():
                        break
                    seq += 1

                student = Student.objects.create(
                    admission_number=admission_number,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    date_of_birth=date(
                        start_year - 9,
                        random.randint(1, 12),
                        random.randint(1, 28),
                    ),
                    gender=random.choice(genders),
                    status=Student.Status.ACTIVE,
                    admission_date=date(start_year, 9, 1),
                    created_by=teacher.user,
                )
                existing_students.append(student)
                seq += 1

            students = existing_students[:total_needed]

            if reset_enrollments:
                Enrollment.objects.filter(class_obj__in=classes).delete()

            for class_index, cls in enumerate(classes):
                start = class_index * students_per_section
                stop = start + students_per_section
                section_students = students[start:stop]

                for roll_number, student in enumerate(section_students, start=1):
                    Enrollment.objects.update_or_create(
                        student=student,
                        class_obj=cls,
                        defaults={
                            "status": Enrollment.EnrollmentStatus.ACTIVE,
                            "roll_number": roll_number,
                        },
                    )
                    if student.class_obj_id != cls.id:
                        student.class_obj = cls
                        student.save(update_fields=["class_obj"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(classes)} classes, {len(subjects)} subjects, "
                f"{total_needed} enrolled students for {year_name}."
            )
        )
