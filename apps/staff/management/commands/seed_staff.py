import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.staff.models import SalaryStructure, Staff


FIRST_NAMES = ["Kwame", "Aba", "Kofi", "Ama", "John", "Sarah", "Daniel", "Grace"]
LAST_NAMES = ["Mensah", "Quansah", "Addo", "Serwaa", "Doe", "Owusu", "Asante", "Boateng"]
SPECIALIZATIONS = ["Mathematics", "English", "Science", "Administration", "Finance", "ICT Support"]


ROLE_MAP = {
    Staff.StaffType.TEACHER: User.Role.TEACHER,
    Staff.StaffType.HEADMASTER: User.Role.HEADMASTER,
    Staff.StaffType.BURSAR: User.Role.BURSAR,
    Staff.StaffType.ADMIN_STAFF: User.Role.ADMIN,
    Staff.StaffType.SUPPORT_STAFF: User.Role.ADMIN,
}


class Command(BaseCommand):
    help = "Seed staff profiles (with users + salary structures) for pagination testing."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=80, help="Total staff to ensure.")
        parser.add_argument("--prefix", type=str, default="seed", help="Username/email prefix.")
        parser.add_argument("--password", type=str, default="Pass1234!")

    def handle(self, *args, **options):
        target_count = max(0, int(options["count"]))
        prefix = options["prefix"].strip().lower()
        password = options["password"]

        staff_types = [choice[0] for choice in Staff.StaffType.choices]

        self.stdout.write(self.style.NOTICE("Seeding staff data..."))
        with transaction.atomic():
            existing = Staff.objects.filter(user__username__startswith=f"{prefix}_staff_").count()
            to_create = max(0, target_count - existing)
            created = 0
            cursor = existing + 1

            for _ in range(to_create):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                staff_type = random.choice(staff_types)
                username = f"{prefix}_staff_{cursor:04d}"
                email = f"{username}@school.com"
                cursor += 1

                if User.objects.filter(username=username).exists():
                    continue

                role = ROLE_MAP.get(staff_type, User.Role.ADMIN)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_staff=True,
                    is_active=True,
                )

                staff = Staff.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date(1980, random.randint(1, 12), random.randint(1, 28)),
                    phone_number=f"+23320{random.randint(1000000, 9999999)}",
                    email=email,
                    address=f"House {random.randint(1, 200)}, Accra",
                    gender=random.choice([Staff.Gender.MALE, Staff.Gender.FEMALE]),
                    staff_type=staff_type,
                    specialization=random.choice(SPECIALIZATIONS),
                    employment_date=date.today() - timedelta(days=random.randint(180, 2200)),
                    national_id=f"NID{random.randint(10000000, 99999999)}",
                    health_info="N/A",
                )

                SalaryStructure.objects.get_or_create(
                    staff=staff,
                    effective_from=date.today() - timedelta(days=365),
                    defaults={
                        "base_salary": Decimal(random.randint(2500, 9000)),
                        "housing_allowance": Decimal(random.randint(200, 1500)),
                        "transport_allowance": Decimal(random.randint(100, 800)),
                        "other_allowances": Decimal(random.randint(0, 500)),
                    },
                )
                created += 1

        total = Staff.objects.filter(user__username__startswith=f"{prefix}_staff_").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Staff seed complete. Created {created}, total {total} for prefix '{prefix}'."
            )
        )
