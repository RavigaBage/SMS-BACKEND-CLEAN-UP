import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.students.models import Student, Parent, StudentParent
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Populates the database with realistic student and parent data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")
        
        # Ensure we have a staff user to attribute 'created_by'
        admin_user = User.objects.filter(role='admin').first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No Admin user found. Please create a superuser with role='admin' first."))
            return

        first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        occupations = ["Engineer", "Teacher", "Doctor", "Business Owner", "Nurse", "Accountant", "Driver"]

        with transaction.atomic():
            for i in range(1, 21):  # Create 20 students
                # 1. Create Student
                year = date.today().year
                admission_no = f"SMS/{year}/{i:04d}"
                
                # Random DOB for kids aged 6-16
                days_old = random.randint(2190, 5840)
                dob = date.today() - timedelta(days=days_old)
                
                student = Student.objects.create(
                    admission_number=admission_no,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    middle_name=random.choice(first_names) if i % 3 == 0 else "",
                    date_of_birth=dob,
                    gender=random.choice(['male', 'female']),
                    admission_date=date.today() - timedelta(days=random.randint(0, 365)),
                    status='active',
                    created_by=admin_user,
                    nationality="Ghanaian",
                    address=f"House No. {random.randint(1, 100)}, Accra",
                )

                # 2. Create Parent
                parent = Parent.objects.create(
                    first_name=random.choice(first_names),
                    last_name=student.last_name,
                    phone_number=f"+23324{random.randint(1000000, 9999999)}",
                    email=f"parent{i}@example.com",
                    occupation=random.choice(occupations),
                    relationship=random.choice(['father', 'mother', 'guardian']),
                    address=student.address
                )

                # 3. Link them
                StudentParent.objects.create(
                    student=student,
                    parent=parent,
                    is_primary_contact=True,
                    can_pickup=True
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded 20 students and parents!"))