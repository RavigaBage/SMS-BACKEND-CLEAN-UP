import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.students.models import Parent, Student, StudentParent


FIRST_NAMES = [
    "James",
    "Mary",
    "Robert",
    "Patricia",
    "John",
    "Jennifer",
    "Michael",
    "Linda",
    "David",
    "Elizabeth",
    "Daniel",
    "Grace",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
]

OCCUPATIONS = [
    "Engineer",
    "Teacher",
    "Doctor",
    "Business Owner",
    "Nurse",
    "Accountant",
    "Driver",
]


class Command(BaseCommand):
    help = "Populate student and parent test data for pagination."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=120, help="Total students to ensure.")
        parser.add_argument(
            "--prefix",
            type=str,
            default="seed",
            help="Prefix used for admission numbers and parent emails.",
        )

    def handle(self, *args, **options):
        target_count = max(0, int(options["count"]))
        prefix = options["prefix"].strip().lower()

        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No admin user found. Seed accounts first.")
            )
            return

        self.stdout.write(self.style.NOTICE("Seeding students and parents..."))

        with transaction.atomic():
            existing = Student.objects.filter(admission_number__startswith=f"{prefix}-").count()
            to_create = max(0, target_count - existing)

            year = date.today().year
            seq = existing + 1
            created_students = 0

            for _ in range(to_create):
                admission_no = f"{prefix}-{year}-{seq:05d}"
                seq += 1

                if Student.objects.filter(admission_number=admission_no).exists():
                    continue

                days_old = random.randint(2190, 5840)  # 6 to 16 years
                dob = date.today() - timedelta(days=days_old)
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)

                student = Student.objects.create(
                    admission_number=admission_no,
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=random.choice(FIRST_NAMES) if random.randint(1, 3) == 1 else "",
                    date_of_birth=dob,
                    gender=random.choice([Student.Gender.MALE, Student.Gender.FEMALE]),
                    admission_date=date.today() - timedelta(days=random.randint(0, 365)),
                    status=Student.Status.ACTIVE,
                    created_by=admin_user,
                    nationality="Ghanaian",
                    address=f"House No. {random.randint(1, 200)}, Accra",
                )

                parent_email = f"{prefix}.parent.{student.id}@example.com"
                parent, _ = Parent.objects.get_or_create(
                    email=parent_email,
                    defaults={
                        "first_name": random.choice(FIRST_NAMES),
                        "last_name": student.last_name,
                        "phone_number": f"+23324{random.randint(1000000, 9999999)}",
                        "occupation": random.choice(OCCUPATIONS),
                        "relationship": random.choice(
                            [Parent.Relationship.FATHER, Parent.Relationship.MOTHER, Parent.Relationship.GUARDIAN]
                        ),
                        "address": student.address,
                    },
                )

                StudentParent.objects.get_or_create(
                    student=student,
                    parent=parent,
                    defaults={"is_primary_contact": True, "can_pickup": True},
                )
                created_students += 1

        total_now = Student.objects.filter(admission_number__startswith=f"{prefix}-").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Students seed complete. Created {created_students}, total {total_now} for prefix '{prefix}'."
            )
        )
