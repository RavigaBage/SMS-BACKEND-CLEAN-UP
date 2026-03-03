import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.staff.models import Staff, StaffAttendance


class Command(BaseCommand):
    help = "Seed realistic staff attendance for pagination/testing."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=60, help="How many recent days to seed.")
        parser.add_argument("--skip-weekends", action="store_true", help="Skip Saturday/Sunday records.")

    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        skip_weekends = options["skip_weekends"]

        staff_members = Staff.objects.all()
        if not staff_members.exists():
            self.stdout.write(self.style.ERROR("No staff found. Run seed_staff first."))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Seeding attendance for {staff_members.count()} staff across {days} days..."
            )
        )

        seeded = 0
        start_date = date.today() - timedelta(days=days - 1)
        with transaction.atomic():
            for day_offset in range(days):
                current_date = start_date + timedelta(days=day_offset)
                if skip_weekends and current_date.weekday() >= 5:
                    continue

                for staff in staff_members:
                    rand = random.random()
                    status = StaffAttendance.AttendanceStatus.PRESENT
                    remarks = ""

                    arrival_min = random.randint(25, 80)
                    c_in = timezone.make_aware(
                        datetime.combine(current_date, time(7, 0)) + timedelta(minutes=arrival_min)
                    )
                    c_out = timezone.make_aware(
                        datetime.combine(current_date, time(16, 0)) + timedelta(minutes=random.randint(0, 90))
                    )

                    if rand < 0.06:
                        status = StaffAttendance.AttendanceStatus.ABSENT
                        c_in, c_out, remarks = None, None, "Unexcused absence"
                    elif rand < 0.12:
                        status = StaffAttendance.AttendanceStatus.ON_LEAVE
                        c_in, c_out, remarks = None, None, "Approved leave"
                    elif rand < 0.18:
                        status = StaffAttendance.AttendanceStatus.HALF_DAY
                        c_out = timezone.make_aware(datetime.combine(current_date, time(12, 0)))
                        remarks = "Half day"
                    elif arrival_min > 60:
                        remarks = "Arrived late"

                    StaffAttendance.objects.update_or_create(
                        staff=staff,
                        attendance_date=current_date,
                        defaults={
                            "check_in": c_in,
                            "check_out": c_out,
                            "status": status,
                            "remarks": remarks,
                        },
                    )
                    seeded += 1

        self.stdout.write(
            self.style.SUCCESS(f"Attendance seed complete. Upserted {seeded} records.")
        )
