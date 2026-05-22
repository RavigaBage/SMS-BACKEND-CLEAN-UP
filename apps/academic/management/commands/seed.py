from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from datetime import date
from django.contrib.auth import get_user_model

from apps.academic.models import AcademicYear, Subject, Class
from apps.settings.models import EmailConfiguration
from apps.teachers.models import Teacher

User = get_user_model()


class Command(BaseCommand):
    help = "Reset DB and seed data"

    def handle(self, *args, **kwargs):

        self.stdout.write("Flushing database...")
        call_command("flush", "--noinput")

        self.stdout.write("Running seed...")
        self.create_test_data()

        self.stdout.write(self.style.SUCCESS("Done ✔"))


    @transaction.atomic
    def create_test_data(self):
                
        subjects_data = [
                            {'subject_name': 'adm_system', 'subject_code': 'Adm_sys', 'grade_level': 0},
                            {'subject_name': 'Mathematics', 'subject_code': 'CRE-MATH101', 'grade_level': 0},
                            {'subject_name': 'English Language', 'subject_code': 'CRE-ENG101', 'grade_level': 0}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'CRE-ART101', 'grade_level': 0}, 
                            {'subject_name': 'Computing', 'subject_code': 'CRE-COMP101', 'grade_level': 0}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'NUR-MATH101', 'grade_level': 0}, 
                            {'subject_name': 'English Language', 'subject_code': 'NUR-ENG101', 'grade_level': 0}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'NUR-ART101', 'grade_level': 0}, 
                            {'subject_name': 'Computing', 'subject_code': 'NUR-COMP101', 'grade_level': 0}, 
                            {'subject_name': 'RME', 'subject_code': 'NUR-RME101', 'grade_level': 0}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'KG1-MATH101', 'grade_level': 0}, 
                            {'subject_name': 'English Language', 'subject_code': 'KG1-ENG101', 'grade_level': 0}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'KG1-ART101', 'grade_level': 0}, 
                            {'subject_name': 'Computing', 'subject_code': 'KG1-COMP101', 'grade_level': 0}, 
                            {'subject_name': 'RME', 'subject_code': 'KG1-RME101', 'grade_level': 0}, 
                            {'subject_name': 'Owop', 'subject_code': 'KG1-OWOP101', 'grade_level': 0}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'KG2-MATH101', 'grade_level': 0}, 
                            {'subject_name': 'English Language', 'subject_code': 'KG2-ENG101', 'grade_level': 0}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'KG2-ART101', 'grade_level': 0}, 
                            {'subject_name': 'Computing', 'subject_code': 'KG2-COMP101', 'grade_level': 0}, 
                            {'subject_name': 'RME', 'subject_code': 'KG2-RME101', 'grade_level': 0}, 
                            {'subject_name': 'Owop', 'subject_code': 'KG2-OWOP101', 'grade_level': 0}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C1-MATH101', 'grade_level': 1}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C1-SCI101', 'grade_level': 1}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C1-SOC101', 'grade_level': 1}, 
                            {'subject_name': 'English Language', 'subject_code': 'C1-ENG101', 'grade_level': 1}, 
                            {'subject_name': 'Computing', 'subject_code': 'C1-COMP101', 'grade_level': 1}, 
                            {'subject_name': 'RME', 'subject_code': 'C1-RME101', 'grade_level': 1}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C1-CT101', 'grade_level': 1}, 
                            {'subject_name': 'Owop', 'subject_code': 'C1-OWOP101', 'grade_level': 1}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C1-ART101', 'grade_level': 1}, 
                            {'subject_name': 'French', 'subject_code': 'C1-FR101', 'grade_level': 1}, 
                            {'subject_name': 'Fante', 'subject_code': 'C1-FAN101', 'grade_level': 1}, 
                            {'subject_name': 'History', 'subject_code': 'C1-HIS101', 'grade_level': 1}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C2-MATH101', 'grade_level': 2}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C2-SCI101', 'grade_level': 2}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C2-SOC101', 'grade_level': 2}, 
                            {'subject_name': 'English Language', 'subject_code': 'C2-ENG101', 'grade_level': 2}, 
                            {'subject_name': 'Computing', 'subject_code': 'C2-COMP101', 'grade_level': 2}, 
                            {'subject_name': 'RME', 'subject_code': 'C2-RME101', 'grade_level': 2}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C2-CT101', 'grade_level': 2}, 
                            {'subject_name': 'Owop', 'subject_code': 'C2-OWOP101', 'grade_level': 2}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C2-ART101', 'grade_level': 2}, 
                            {'subject_name': 'French', 'subject_code': 'C2-FR101', 'grade_level': 2}, 
                            {'subject_name': 'Fante', 'subject_code': 'C2-FAN101', 'grade_level': 2}, 
                            {'subject_name': 'History', 'subject_code': 'C2-HIS101', 'grade_level': 2}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C3-MATH101', 'grade_level': 3}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C3-SCI101', 'grade_level': 3}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C3-SOC101', 'grade_level': 3}, 
                            {'subject_name': 'English Language', 'subject_code': 'C3-ENG101', 'grade_level': 3}, 
                            {'subject_name': 'Computing', 'subject_code': 'C3-COMP101', 'grade_level': 3}, 
                            {'subject_name': 'RME', 'subject_code': 'C3-RME101', 'grade_level': 3}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C3-CT101', 'grade_level': 3}, 
                            {'subject_name': 'Owop', 'subject_code': 'C3-OWOP101', 'grade_level': 3}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C3-ART101', 'grade_level': 3}, 
                            {'subject_name': 'French', 'subject_code': 'C3-FR101', 'grade_level': 3}, 
                            {'subject_name': 'Fante', 'subject_code': 'C3-FAN101', 'grade_level': 3}, 
                            {'subject_name': 'History', 'subject_code': 'C3-HIS101', 'grade_level': 3}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C4-MATH101', 'grade_level': 4}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C4-SCI101', 'grade_level': 4}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C4-SOC101', 'grade_level': 4}, 
                            {'subject_name': 'English Language', 'subject_code': 'C4-ENG101', 'grade_level': 4}, 
                            {'subject_name': 'Computing', 'subject_code': 'C4-COMP101', 'grade_level': 4}, 
                            {'subject_name': 'RME', 'subject_code': 'C4-RME101', 'grade_level': 4}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C4-CT101', 'grade_level': 4}, 
                            {'subject_name': 'Owop', 'subject_code': 'C4-OWOP101', 'grade_level': 4}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C4-ART101', 'grade_level': 4}, 
                            {'subject_name': 'French', 'subject_code': 'C4-FR101', 'grade_level': 4}, 
                            {'subject_name': 'Fante', 'subject_code': 'C4-FAN101', 'grade_level': 4}, 
                            {'subject_name': 'History', 'subject_code': 'C4-HIS101', 'grade_level': 4}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C5-MATH101', 'grade_level': 5}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C5-SCI101', 'grade_level': 5}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C5-SOC101', 'grade_level': 5}, 
                            {'subject_name': 'English Language', 'subject_code': 'C5-ENG101', 'grade_level': 5}, 
                            {'subject_name': 'Computing', 'subject_code': 'C5-COMP101', 'grade_level': 5}, 
                            {'subject_name': 'RME', 'subject_code': 'C5-RME101', 'grade_level': 5}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C5-CT101', 'grade_level': 5}, 
                            {'subject_name': 'Owop', 'subject_code': 'C5-OWOP101', 'grade_level': 5}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C5-ART101', 'grade_level': 5}, 
                            {'subject_name': 'French', 'subject_code': 'C5-FR101', 'grade_level': 5}, 
                            {'subject_name': 'Fante', 'subject_code': 'C5-FAN101', 'grade_level': 5}, 
                            {'subject_name': 'History', 'subject_code': 'C5-HIS101', 'grade_level': 5}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'C6-MATH101', 'grade_level': 6}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'C6-SCI101', 'grade_level': 6}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'C6-SOC101', 'grade_level': 6}, 
                            {'subject_name': 'English Language', 'subject_code': 'C6-ENG101', 'grade_level': 6}, 
                            {'subject_name': 'Computing', 'subject_code': 'C6-COMP101', 'grade_level': 6}, 
                            {'subject_name': 'RME', 'subject_code': 'C6-RME101', 'grade_level': 6}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'C6-CT101', 'grade_level': 6}, 
                            {'subject_name': 'Owop', 'subject_code': 'C6-OWOP101', 'grade_level': 6}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'C6-ART101', 'grade_level': 6}, 
                            {'subject_name': 'French', 'subject_code': 'C6-FR101', 'grade_level': 6}, 
                            {'subject_name': 'Fante', 'subject_code': 'C6-FAN101', 'grade_level': 6}, 
                            {'subject_name': 'History', 'subject_code': 'C6-HIS101', 'grade_level': 6}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'F1-MATH101', 'grade_level': 7}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'F1-SCI101', 'grade_level': 7}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'F1-SOC101', 'grade_level': 7}, 
                            {'subject_name': 'English Language', 'subject_code': 'F1-ENG101', 'grade_level': 7}, 
                            {'subject_name': 'Computing', 'subject_code': 'F1-COMP101', 'grade_level': 7}, 
                            {'subject_name': 'RME', 'subject_code': 'F1-RME101', 'grade_level': 7}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'F1-CT101', 'grade_level': 7}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'F1-ART101', 'grade_level': 7}, 
                            {'subject_name': 'French', 'subject_code': 'F1-FR101', 'grade_level': 7}, 
                            {'subject_name': 'Fante', 'subject_code': 'F1-FAN101', 'grade_level': 7}, 
                            {'subject_name': 'History', 'subject_code': 'F1-HIS101', 'grade_level': 7}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'F2-MATH101', 'grade_level': 8}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'F2-SCI101', 'grade_level': 8}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'F2-SOC101', 'grade_level': 8}, 
                            {'subject_name': 'English Language', 'subject_code': 'F2-ENG101', 'grade_level': 8}, 
                            {'subject_name': 'Computing', 'subject_code': 'F2-COMP101', 'grade_level': 8}, 
                            {'subject_name': 'RME', 'subject_code': 'F2-RME101', 'grade_level': 8}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'F2-CT101', 'grade_level': 8}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'F2-ART101', 'grade_level': 8}, 
                            {'subject_name': 'French', 'subject_code': 'F2-FR101', 'grade_level': 8}, 
                            {'subject_name': 'Fante', 'subject_code': 'F2-FAN101', 'grade_level': 8}, 
                            {'subject_name': 'History', 'subject_code': 'F2-HIS101', 'grade_level': 8}, 
                            {'subject_name': 'Mathematics', 'subject_code': 'F3-MATH101', 'grade_level': 9}, 
                            {'subject_name': 'Integrated Science', 'subject_code': 'F3-SCI101', 'grade_level': 9}, 
                            {'subject_name': 'Social Studies', 'subject_code': 'F3-SOC101', 'grade_level': 9}, 
                            {'subject_name': 'English Language', 'subject_code': 'F3-ENG101', 'grade_level': 9}, 
                            {'subject_name': 'Computing', 'subject_code': 'F3-COMP101', 'grade_level': 9}, 
                            {'subject_name': 'RME', 'subject_code': 'F3-RME101', 'grade_level': 9}, 
                            {'subject_name': 'Career Technology', 'subject_code': 'F3-CT101', 'grade_level': 9}, 
                            {'subject_name': 'Creative Arts', 'subject_code': 'F3-ART101', 'grade_level': 9}, 
                            {'subject_name': 'French', 'subject_code': 'F3-FR101', 'grade_level': 9}, 
                            {'subject_name': 'Fante', 'subject_code': 'F3-FAN101', 'grade_level': 9}, 
                            {'subject_name': 'History', 'subject_code': 'F3-HIS101', 'grade_level': 9}
            ]
            

        classes_data = [

        {"class_name": "Creche A", "grade_level": 100, "section": "A", "academic_year": "2024/2025", "capacity": 30, "room_number": "CR-1"},
        {"class_name": "Creche B", "grade_level": 101, "section": "B", "academic_year": "2024/2025", "capacity": 30, "room_number": "CR-2"},

        {"class_name": "Nursery 1A", "grade_level": 102, "section": "Aa", "academic_year": "2024/2025", "capacity": 35, "room_number": "NR-1A"},
        {"class_name": "Nursery 1B", "grade_level": 103, "section": "Bb", "academic_year": "2024/2025", "capacity": 35, "room_number": "NR-1B"},
        {"class_name": "Nursery 2A", "grade_level": 104, "section": "Aa", "academic_year": "2024/2025", "capacity": 35, "room_number": "NR-2A"},
        {"class_name": "Nursery 2B", "grade_level": 105, "section": "Bb", "academic_year": "2024/2025", "capacity": 35, "room_number": "NR-2B"},

        {"class_name": "KG 1A", "grade_level": 107, "section": "Aa", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-1A"},
        {"class_name": "KG 1B", "grade_level": 108, "section": "Bb", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-1B"},
        {"class_name": "KG 2A", "grade_level": 109, "section": "Aa", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-2A"},
        {"class_name": "KG 2B", "grade_level": 1011, "section": "Bb", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-2B"},
        {"class_name": "KG 3A", "grade_level": 1012, "section": "Aa", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-3A"},
        {"class_name": "KG 3B", "grade_level": 1013, "section": "Bb", "academic_year": "2024/2025", "capacity": 40, "room_number": "KG-3B"},

        {"class_name": "Class 1A", "grade_level": 1, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P1-A"},
        {"class_name": "Class 1B", "grade_level": 1, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P1-B"},

        {"class_name": "Class 2A", "grade_level": 2, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P2-A"},
        {"class_name": "Class 2B", "grade_level": 2, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P2-B"},

        {"class_name": "Class 3A", "grade_level": 3, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P3-A"},
        {"class_name": "Class 3B", "grade_level": 3, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P3-B"},

        {"class_name": "Class 4A", "grade_level": 4, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P4-A"},
        {"class_name": "Class 4B", "grade_level": 4, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P4-B"},

        {"class_name": "Class 5A", "grade_level": 5, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P5-A"},
        {"class_name": "Class 5B", "grade_level": 5, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P5-B"},

        {"class_name": "Class 6A", "grade_level": 6, "section": "A", "academic_year": "2024/2025", "capacity": 45, "room_number": "P6-A"},
        {"class_name": "Class 6B", "grade_level": 6, "section": "B", "academic_year": "2024/2025", "capacity": 45, "room_number": "P6-B"},
        {"class_name": "Form 1A", "grade_level": 7, "section": "A", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-1A"},
        {"class_name": "Form 1B", "grade_level": 7, "section": "B", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-1B"},

        {"class_name": "Form 2A", "grade_level": 8, "section": "A", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-2A"},
        {"class_name": "Form 2B", "grade_level": 8, "section": "B", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-2B"},

        {"class_name": "Form 3A", "grade_level": 9, "section": "A", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-3A"},
        {"class_name": "Form 3B", "grade_level": 9, "section": "B", "academic_year": "2024/2025", "capacity": 50, "room_number": "JHS-3B"},
    ]
        print("\nCreating test data...\n")

        try:

            admin_user, created = User.objects.get_or_create(
                email="admin@school.com",
                defaults={
                    "username": "admin",
                    "first_name": "System",
                    "last_name": "Admin",
                    "role": User.Role.ADMIN,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                }
            )

            if created:
                admin_user.set_password("admin123456")
                admin_user.save()
                print("✓ Admin created")


            academic_year, _ = AcademicYear.objects.get_or_create(
                year_name="2024/2025",
                defaults={
                    "start_date": date(2024, 9, 1),
                    "end_date": date(2025, 6, 30),
                    "is_current": True,
                }
            )

            print("✓ Academic year ready")
    
            created_subjects = []

            for subject_data in subjects_data:
                subject, created = Subject.objects.get_or_create(
                    subject_code=subject_data["subject_code"],
                    defaults=subject_data
                )

                created_subjects.append(subject)

        
            teacher_user, created = User.objects.get_or_create(
                email="kwame@school.com",
                defaults={
                    "username": "kwame_teacher",
                    "first_name": "Kwame",
                    "last_name": "Asante",
                    "role": User.Role.TEACHER,
                    "is_active": True,
                    "created_by": admin_user,
                }
            )

            if created:
                teacher_user.set_password("teacher123")
                teacher_user.save()

      
            teacher, created = Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    "first_name": "admin",
                    "last_name": "system",
                    "specialization": "Mathematics",
                    "qualifications": "B.Ed Mathematics",
                    "years_of_experience": 5,
                    "phone_number": "+233241112223",
                    "emergency_contact": "+233201112223",
                    "assigned_by": admin_user,
                    "is_active": True,
                }
            )

            if created:
                print(len(created_subjects))
                print(type(created_subjects[0]))
                teacher.subjects.add(created_subjects[0])

 
            for data in classes_data:

                classroom, created = Class.objects.get_or_create(
                    class_name=data["class_name"],
                    academic_year="2024/2025",
                    defaults={
                        "grade_level": data["grade_level"],
                        "section": data["section"],
                        "capacity": data["capacity"],
                        "room_number": data["room_number"],
                        "class_teacher": teacher,
                    }
                )

                classroom.subjects.set(created_subjects)

            email_settings, created = EmailConfiguration.objects.get_or_create(
                backend="smtp",
                defaults={
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "use_tls": True,
                    "host_user": "theoacad@edu.gh",
                    "host_password": "app-password-here",
                    "default_from_email": "morousman045@gmail.com",
                    "school_name": "Theohans Academy",
                }
            )

            print("✓ Email config ready")

            print("\nTEST DATA CREATED SUCCESSFULLY")

        except Exception as e:
            print("\nSEED FAILED")
            print(str(e))
            raise