import random
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User
from apps.teachers.models import Teacher
from apps.academic.models import Subject  # Adjust path if needed

class Command(BaseCommand):
    help = 'Seeds teachers and links them to existing subjects'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Teachers...")

        # Get some subjects to assign randomly
        available_subjects = list(Subject.objects.all())
        if not available_subjects:
            self.stdout.write(self.style.WARNING("No subjects found. Run your subject seed first if you want to link them!"))

        teacher_data = [
            ('math_guru', 'John', 'Doe', 'Advanced Mathematics'),
            ('bio_expert', 'Jane', 'Smith', 'Biological Sciences'),
            ('history_buff', 'Alice', 'Johnson', 'Modern History'),
            ('tech_lead', 'Bob', 'Wilson', 'Computer Science'),
            ('lit_lover', 'Claire', 'Davis', 'English Literature'),
        ]

        with transaction.atomic():
            for username, f_name, l_name, spec in teacher_data:
                # 1. Create the User
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"{username}@school.com",
                        'first_name': f_name,
                        'last_name': l_name,
                        'is_staff': True
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()

                # 2. Create the Teacher Profile
                teacher, t_created = Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        'first_name': f_name,
                        'last_name': l_name,
                        'specialization': spec,
                    }
                )

                # 3. Assign 1-2 random subjects if they exist
                if t_created and available_subjects:
                    random_subs = random.sample(available_subjects, min(len(available_subjects), 2))
                    teacher.subjects.add(*random_subs)
                    self.stdout.write(f"Added {teacher} with subjects: {[s.subject_name for s in random_subs]}")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(teacher_data)} teachers."))