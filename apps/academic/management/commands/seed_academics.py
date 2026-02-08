from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from apps.academic.models import AcademicYear, Class, Subject, Enrollment, SubjectAssignment
from apps.students.models import Student
from apps.staff.models import Staff  # Assumes Staff exist

class Command(BaseCommand):
    help = 'Populates academic years, subjects, classes, and enrollments'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Academic Data...")

        with transaction.atomic():
            # 1. Create Academic Year
            academic_year, _ = AcademicYear.objects.get_or_create(
                year_name="2025/2026",
                defaults={
                    'start_date': date(2025, 9, 1),
                    'end_date': date(2026, 7, 31),
                    'is_current': True
                }
            )

            # 2. Create Subjects
            subjects_data = [
                ('Mathematics', 'MATH101', 1),
                ('English Language', 'ENG101', 1),
                ('Integrated Science', 'SCI101', 1),
                ('Social Studies', 'SOC101', 1),
                ('Information Technology', 'ICT101', 1),
            ]
            
            created_subjects = []
            for name, code, level in subjects_data:
                sub, _ = Subject.objects.get_or_create(
                    subject_code=code,
                    defaults={'subject_name': name, 'grade_level': level}
                )
                created_subjects.append(sub)

            # 3. Create Classes
            # We'll create Grade 1A and Grade 1B
            staff_member = Staff.objects.first() # Assigns first staff as class teacher for demo
            
            classes = []
            for section in ['A', 'B']:
                cls, _ = Class.objects.get_or_create(
                    class_name=f"Grade 1{section}",
                    academic_year=academic_year,
                    defaults={
                        'grade_level': 1,
                        'section': section,
                        'class_teacher': staff_member,
                        'capacity': 30,
                        'room_number': f"R{100 + ord(section)}"
                    }
                )
                classes.append(cls)

                # 4. Create Subject Assignments (Assign all subjects to these classes)
                for sub in created_subjects:
                    SubjectAssignment.objects.get_or_create(
                        class_obj=cls,
                        subject=sub,
                        defaults={'teacher': staff_member}
                    )

            # 5. Enroll Students
            all_students = Student.objects.all()
            if not all_students.exists():
                self.stdout.write(self.style.WARNING("No students found. Run seed_students first!"))
                return

            for index, student in enumerate(all_students):
                # Distribute students: first 10 to Grade 1A, next 10 to Grade 1B
                target_class = classes[0] if index < 10 else classes[1]
                
                Enrollment.objects.get_or_create(
                    student=student,
                    class_obj=target_class,
                    defaults={
                        'status': 'active',
                        'roll_number': (index % 10) + 1
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Academic structure!"))