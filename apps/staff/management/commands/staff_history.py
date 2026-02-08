import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.staff.models import Staff, SalaryPayment, LeaveRequest
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Seeds historical salary payments and leave requests for existing staff'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Staff History (Salaries & Leaves)...")

        admin_user = User.objects.filter(role='admin').first()
        all_staff = Staff.objects.all()

        if not all_staff.exists():
            self.stdout.write(self.style.ERROR("No staff found. Run seed_staff first!"))
            return

        months = [
            "August 2025", "September 2025", "October 2025", 
            "November 2025", "December 2025", "January 2026"
        ]

        with transaction.atomic():
            for staff in all_staff:
                # 1. Seed Salary Payments (Last 6 Months)
                # Get their current salary structure
                structure = staff.salary_structures.first()
                if structure:
                    base = structure.base_salary
                    allowances = structure.housing_allowance + structure.transport_allowance
                    
                    for month_name in months:
                        # Add some random deductions (tax/social security)
                        tax = (base * Decimal('0.15')).quantize(Decimal('0.00'))
                        deductions = Decimal(random.randint(50, 200))
                        net = (base + allowances) - (tax + deductions)

                        SalaryPayment.objects.get_or_create(
                            staff=staff,
                            payment_period=month_name,
                            defaults={
                                'base_salary': base,
                                'allowances': allowances,
                                'tax': tax,
                                'deductions': deductions,
                                'net_salary': net,
                                'status': 'paid',
                                'payment_method': 'bank_transfer',
                                'payment_date': date.today() - timedelta(days=random.randint(1, 150)),
                                'processed_by': admin_user
                            }
                        )

                # 2. Seed Leave Requests
                leave_types = ['sick', 'casual', 'annual', 'emergency']
                
                # Create 3-4 leave requests per staff member
                for _ in range(random.randint(2, 4)):
                    start = date.today() - timedelta(days=random.randint(-30, 180))
                    duration = random.randint(1, 5)
                    end = start + timedelta(days=duration)
                    
                    status = random.choice(['approved', 'rejected', 'pending'])
                    
                    LeaveRequest.objects.create(
                        staff=staff,
                        leave_type=random.choice(leave_types),
                        start_date=start,
                        end_date=end,
                        total_days=duration,
                        reason="Personal matters or health reasons.",
                        status=status,
                        approved_by=admin_user if status == 'approved' else None
                    )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded history for {all_staff.count()} staff members!"))