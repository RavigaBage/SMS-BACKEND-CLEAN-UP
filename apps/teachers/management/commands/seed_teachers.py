import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academic.models import Subject
from apps.accounts.models import User
from apps.teachers.models import Teacher


FIRST_NAMES = [
    "John",
    "Jane",
    "Alice",
    "Bob",
    "Claire",
    "Daniel",
    "Grace",
    "Samuel",
    "Naomi",
    "Prince",
]

LAST_NAMES = [
    "Mensah",
    "Boateng",
    "Asante",
    "Owusu",
    "Adjei",
    "Appiah",
    "Darko",
    "Ofori",
]

SPECIALIZATIONS = [
    "Mathematics",
    "Science",
    "English",
    "History",
    "ICT",
    "Arts",
]


class Command(BaseCommand):
    help = "Seed teacher users/profiles with subject links for pagination testing."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=80, help="Total teachers to ensure.")
        parser.add_argument("--prefix", type=str, default="seed", help="Username/email prefix.")
        parser.add_argument("--password", type=str, default="Pass1234!")

    def handle(self, *args, **options):
        target_count = max(0, int(options["count"]))
        prefix = options["prefix"].strip().lower()
        password = options["password"]

        available_subjects = list(Subject.objects.all())
        self.stdout.write(self.style.NOTICE("Seeding teachers..."))

        with transaction.atomic():
            existing = Teacher.objects.filter(user__username__startswith=f"{prefix}_teacher_").count()
            to_create = max(0, target_count - existing)
            created = 0
            cursor = existing + 1

            for _ in range(to_create):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                username = f"{prefix}_teacher_{cursor:04d}"
                email = f"{username}@school.com"
                cursor += 1

                if User.objects.filter(username=username).exists():
                    continue

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=User.Role.TEACHER,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True,
                    is_active=True,
                )

                teacher = Teacher.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    specialization=random.choice(SPECIALIZATIONS),
                    years_of_experience=random.randint(1, 20),
                    qualifications="B.Ed",
                    phone_number=f"+23320{random.randint(1000000, 9999999)}",
                    emergency_contact=f"+23324{random.randint(1000000, 9999999)}",
                    assigned_by=User.objects.filter(role=User.Role.ADMIN).first(),
                )

                if available_subjects:
                    chosen = random.sample(available_subjects, min(len(available_subjects), random.randint(1, 3)))
                    teacher.subjects.add(*chosen)

                created += 1

        total = Teacher.objects.filter(user__username__startswith=f"{prefix}_teacher_").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Teachers seed complete. Created {created}, total {total} for prefix '{prefix}'."
            )
        )
