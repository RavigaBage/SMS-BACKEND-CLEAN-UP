import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User
from apps.staff.models import Staff, SalaryStructure

class Command(BaseCommand):
    help = 'Seeds staff members with linked user accounts'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Staff Data...")

        staff_data = [
            ('kwame.mensah', 'Kwame', 'Mensah', 'teacher', 'Mathematics'),
            ('aba.quansah', 'Aba', 'Quansah', 'teacher', 'English'),
            ('kofi.addo', 'Kofi', 'Addo', 'bursar', 'Finance'),
            ('ama.serwaa', 'Ama', 'Serwaa', 'headmaster', 'Administration'),
            ('john.doe', 'John', 'Doe', 'admin_staff', 'IT Support'),
        ]

        with transaction.atomic():
            for username, f_name, l_name, s_type, spec in staff_data:
                # 1. Create the User Account
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"{username}@school.com",
                        'first_name': f_name,
                        'last_name': l_name,
                        'role': s_type if s_type in dict(User.Role.choices) else 'admin',
                        'is_staff': True
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()

                # 2. Create the Staff Profile
                staff, _ = Staff.objects.get_or_create(
                    user=user,
                    defaults={
                        'first_name': f_name,
                        'last_name': l_name,
                        'email': user.email,
                        'staff_type': s_type,
                        'specialization': spec,
                        'gender': random.choice(['male', 'female']),
                        'employment_date': date(2024, 1, 1),
                        'phone_number': f"+23320{random.randint(1000000, 9999999)}"
                    }
                )

                # 3. Create Salary Structure
                SalaryStructure.objects.get_or_create(
                    staff=staff,
                    effective_from=date(2024, 1, 1),
                    defaults={
                        'base_salary': Decimal(random.randint(3000, 7000)),
                        'housing_allowance': Decimal(500),
                        'transport_allowance': Decimal(300)
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(staff_data)} staff members!"))