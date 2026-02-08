import random
from datetime import date, time, datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from apps.staff.models import Staff, StaffAttendance

class Command(BaseCommand):
    help = 'Seeds the database with realistic staff attendance for Feb 2026'

    def handle(self, *args, **kwargs):
        staff_members = Staff.objects.all()
        if not staff_members.exists():
            self.stdout.write(self.style.ERROR('No staff found. Please add staff first.'))
            return

        # Start from Monday, Feb 2, 2026
        start_date = date(2026, 2, 2)
        days_to_seed = 5  # Mon to Fri

        self.stdout.write(f'Seeding attendance for {staff_members.count()} staff members...')

        with transaction.atomic():
            for day_offset in range(days_to_seed):
                current_date = start_date + timedelta(days=day_offset)
                
                for staff in staff_members:
                    # Randomize scenarios
                    rand = random.random()
                    
                    status = StaffAttendance.AttendanceStatus.PRESENT
                    remarks = ""
                    # Random arrival between 7:30 and 8:15
                    arrival_min = random.randint(30, 75) 
                    c_in = timezone.make_aware(datetime.combine(current_date, time(7, 0)) + timedelta(minutes=arrival_min))
                    # Random departure between 16:00 and 17:00
                    c_out = timezone.make_aware(datetime.combine(current_date, time(16, 0)) + timedelta(minutes=random.randint(0, 60)))

                    if rand < 0.05:  # 5% chance of Absence
                        status = StaffAttendance.AttendanceStatus.ABSENT
                        c_in, c_out, remarks = None, None, "Unexcused absence"
                    elif rand < 0.10:  # 5% chance of On Leave
                        status = StaffAttendance.AttendanceStatus.ON_LEAVE
                        c_in, c_out, remarks = None, None, "Planned medical leave"
                    elif rand < 0.15:  # 5% chance of Half Day
                        status = StaffAttendance.AttendanceStatus.HALF_DAY
                        c_out = timezone.make_aware(datetime.combine(current_date, time(12, 0)))
                        remarks = "Early departure (Personal)"
                    elif arrival_min > 60: # After 8:00 AM
                        remarks = "Arrived late"

                    StaffAttendance.objects.update_or_create(
                        staff=staff,
                        attendance_date=current_date,
                        defaults={
                            'check_in': c_in,
                            'check_out': c_out,
                            'status': status,
                            'remarks': remarks
                        }
                    )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded attendance for {current_date}'))