import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User


FIRST_NAMES = [
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
    "Michael",
    "Sarah",
    "Daniel",
    "Grace",
]

LAST_NAMES = [
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
    "Williams",
    "Smith",
]


class Command(BaseCommand):
    help = "Seed account users for pagination/testing (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--admins", type=int, default=6)
        parser.add_argument("--headmasters", type=int, default=8)
        parser.add_argument("--bursars", type=int, default=16)
        parser.add_argument("--teachers", type=int, default=60)
        parser.add_argument("--parents", type=int, default=120)
        parser.add_argument(
            "--password",
            type=str,
            default="Pass1234!",
            help="Default password for all seeded users.",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="seed",
            help="Username/email prefix for seeded users.",
        )
        parser.add_argument(
            "--inactive-rate",
            type=int,
            default=10,
            help="Approximate percentage of inactive accounts among generated users.",
        )

    def handle(self, *args, **options):
        prefix = options["prefix"].strip().lower()
        password = options["password"]
        inactive_rate = max(0, min(90, int(options["inactive_rate"])))

        targets = {
            User.Role.ADMIN: max(0, int(options["admins"])),
            User.Role.HEADMASTER: max(0, int(options["headmasters"])),
            User.Role.BURSAR: max(0, int(options["bursars"])),
            User.Role.TEACHER: max(0, int(options["teachers"])),
            User.Role.PARENT: max(0, int(options["parents"])),
        }

        self.stdout.write(self.style.NOTICE("Seeding account data..."))

        with transaction.atomic():
            root = self._ensure_root_admin(prefix=prefix, password=password)

            created_total = 0
            for role, target_count in targets.items():
                created = self._ensure_role_population(
                    role=role,
                    target_count=target_count,
                    prefix=prefix,
                    password=password,
                    inactive_rate=inactive_rate,
                    created_by=root,
                )
                created_total += created
                existing = User.objects.filter(
                    role=role, username__startswith=f"{prefix}_{role}_"
                ).count()
                self.stdout.write(
                    f"- {role}: {existing}/{target_count} available (created {created})"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Account seed complete. Newly created users: {created_total}."
            )
        )

    def _ensure_root_admin(self, prefix: str, password: str) -> User:
        username = f"{prefix}_superadmin"
        email = f"{username}@example.com"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": User.Role.ADMIN,
                "first_name": "System",
                "last_name": "Admin",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        dirty = False
        if user.role != User.Role.ADMIN:
            user.role = User.Role.ADMIN
            dirty = True
        if not user.is_staff:
            user.is_staff = True
            dirty = True
        if not user.is_superuser:
            user.is_superuser = True
            dirty = True
        if user.email != email:
            user.email = email
            dirty = True

        if created or dirty:
            user.set_password(password)
            user.save()

        return user

    def _ensure_role_population(
        self,
        role: str,
        target_count: int,
        prefix: str,
        password: str,
        inactive_rate: int,
        created_by: User,
    ) -> int:
        base_qs = User.objects.filter(role=role, username__startswith=f"{prefix}_{role}_")
        existing_count = base_qs.count()
        to_create = max(0, target_count - existing_count)
        if to_create == 0:
            return 0

        is_staff_role = role != User.Role.PARENT
        created = 0
        cursor = existing_count + 1

        while created < to_create:
            username = f"{prefix}_{role}_{cursor:04d}"
            email = f"{username}@example.com"
            cursor += 1

            if User.objects.filter(username=username).exists():
                continue
            if User.objects.filter(email=email).exists():
                continue

            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            joined_days_ago = random.randint(0, 730)
            is_active = random.randint(1, 100) > inactive_rate

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active,
                is_staff=is_staff_role,
                created_by=created_by,
            )

            user.date_joined = timezone.now() - timedelta(days=joined_days_ago)
            user.save(update_fields=["date_joined"])
            created += 1

        return created
