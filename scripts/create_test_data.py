import os
import django
import sys 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.academic.models import AcademicYear, Class, Subject
from datetime import date

User = get_user_model()

def create_test_data():
    print("Creating test data...")
    
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@school.com', 
            'role': 'admin',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('admin123456')
        admin.save()
        print(f"✓ Created admin user")
        print(f"  Email: admin@school.com")
        print(f"  Password: admin123456")
    else:
        
        if not admin.email:
            admin.email = 'admin@school.com'
            admin.save()
        print(f"✓ Admin user already exists")
        print(f"  Email: {admin.email}")
    
    academic_year, created = AcademicYear.objects.get_or_create(
        year_name='2024/2025',
        defaults={
            'start_date': date(2024, 9, 1),
            'end_date': date(2025, 6, 30),
            'is_current': True
        }
    )
    print(f"✓ Created academic year: {academic_year.year_name}")
    
   
    subjects_data = [
                {'subject_name': 'Mathematics', 'subject_code': 'CRE-MATH101', 'grade_level': 'Creche'},
                {'subject_name': 'English Language', 'subject_code': 'CRE-ENG101', 'grade_level': 'Creche'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'CRE-ART101', 'grade_level': 'Creche'}, 
                {'subject_name': 'Computing', 'subject_code': 'CRE-COMP101', 'grade_level': 'Creche'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'NUR-MATH101', 'grade_level': 'Nursery'}, 
                {'subject_name': 'English Language', 'subject_code': 'NUR-ENG101', 'grade_level': 'Nursery'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'NUR-ART101', 'grade_level': 'Nursery'}, 
                {'subject_name': 'Computing', 'subject_code': 'NUR-COMP101', 'grade_level': 'Nursery'}, 
                {'subject_name': 'RME', 'subject_code': 'NUR-RME101', 'grade_level': 'Nursery'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'KG1-MATH101', 'grade_level': 'KG1'}, 
                {'subject_name': 'English Language', 'subject_code': 'KG1-ENG101', 'grade_level': 'KG1'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'KG1-ART101', 'grade_level': 'KG1'}, 
                {'subject_name': 'Computing', 'subject_code': 'KG1-COMP101', 'grade_level': 'KG1'}, 
                {'subject_name': 'RME', 'subject_code': 'KG1-RME101', 'grade_level': 'KG1'}, 
                {'subject_name': 'Owop', 'subject_code': 'KG1-OWOP101', 'grade_level': 'KG1'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'KG2-MATH101', 'grade_level': 'KG2'}, 
                {'subject_name': 'English Language', 'subject_code': 'KG2-ENG101', 'grade_level': 'KG2'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'KG2-ART101', 'grade_level': 'KG2'}, 
                {'subject_name': 'Computing', 'subject_code': 'KG2-COMP101', 'grade_level': 'KG2'}, 
                {'subject_name': 'RME', 'subject_code': 'KG2-RME101', 'grade_level': 'KG2'}, 
                {'subject_name': 'Owop', 'subject_code': 'KG2-OWOP101', 'grade_level': 'KG2'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C1-MATH101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C1-SCI101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C1-SOC101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'English Language', 'subject_code': 'C1-ENG101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Computing', 'subject_code': 'C1-COMP101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'RME', 'subject_code': 'C1-RME101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C1-CT101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Owop', 'subject_code': 'C1-OWOP101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C1-ART101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'French', 'subject_code': 'C1-FR101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Fante', 'subject_code': 'C1-FAN101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'History', 'subject_code': 'C1-HIS101', 'grade_level': 'Class 1'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C2-MATH101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C2-SCI101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C2-SOC101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'English Language', 'subject_code': 'C2-ENG101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Computing', 'subject_code': 'C2-COMP101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'RME', 'subject_code': 'C2-RME101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C2-CT101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Owop', 'subject_code': 'C2-OWOP101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C2-ART101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'French', 'subject_code': 'C2-FR101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Fante', 'subject_code': 'C2-FAN101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'History', 'subject_code': 'C2-HIS101', 'grade_level': 'Class 2'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C3-MATH101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C3-SCI101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C3-SOC101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'English Language', 'subject_code': 'C3-ENG101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Computing', 'subject_code': 'C3-COMP101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'RME', 'subject_code': 'C3-RME101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C3-CT101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Owop', 'subject_code': 'C3-OWOP101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C3-ART101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'French', 'subject_code': 'C3-FR101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Fante', 'subject_code': 'C3-FAN101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'History', 'subject_code': 'C3-HIS101', 'grade_level': 'Class 3'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C4-MATH101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C4-SCI101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C4-SOC101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'English Language', 'subject_code': 'C4-ENG101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Computing', 'subject_code': 'C4-COMP101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'RME', 'subject_code': 'C4-RME101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C4-CT101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Owop', 'subject_code': 'C4-OWOP101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C4-ART101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'French', 'subject_code': 'C4-FR101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Fante', 'subject_code': 'C4-FAN101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'History', 'subject_code': 'C4-HIS101', 'grade_level': 'Class 4'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C5-MATH101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C5-SCI101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C5-SOC101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'English Language', 'subject_code': 'C5-ENG101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Computing', 'subject_code': 'C5-COMP101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'RME', 'subject_code': 'C5-RME101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C5-CT101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Owop', 'subject_code': 'C5-OWOP101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C5-ART101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'French', 'subject_code': 'C5-FR101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Fante', 'subject_code': 'C5-FAN101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'History', 'subject_code': 'C5-HIS101', 'grade_level': 'Class 5'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'C6-MATH101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'C6-SCI101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'C6-SOC101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'English Language', 'subject_code': 'C6-ENG101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Computing', 'subject_code': 'C6-COMP101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'RME', 'subject_code': 'C6-RME101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'C6-CT101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Owop', 'subject_code': 'C6-OWOP101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'C6-ART101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'French', 'subject_code': 'C6-FR101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Fante', 'subject_code': 'C6-FAN101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'History', 'subject_code': 'C6-HIS101', 'grade_level': 'Class 6'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'F1-MATH101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'F1-SCI101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'F1-SOC101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'English Language', 'subject_code': 'F1-ENG101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Computing', 'subject_code': 'F1-COMP101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'RME', 'subject_code': 'F1-RME101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'F1-CT101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'F1-ART101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'French', 'subject_code': 'F1-FR101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Fante', 'subject_code': 'F1-FAN101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'History', 'subject_code': 'F1-HIS101', 'grade_level': 'Form 1'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'F2-MATH101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'F2-SCI101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'F2-SOC101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'English Language', 'subject_code': 'F2-ENG101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Computing', 'subject_code': 'F2-COMP101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'RME', 'subject_code': 'F2-RME101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'F2-CT101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'F2-ART101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'French', 'subject_code': 'F2-FR101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Fante', 'subject_code': 'F2-FAN101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'History', 'subject_code': 'F2-HIS101', 'grade_level': 'Form 2'}, 
                {'subject_name': 'Mathematics', 'subject_code': 'F3-MATH101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Integrated Science', 'subject_code': 'F3-SCI101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Social Studies', 'subject_code': 'F3-SOC101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'English Language', 'subject_code': 'F3-ENG101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Computing', 'subject_code': 'F3-COMP101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'RME', 'subject_code': 'F3-RME101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Career Technology', 'subject_code': 'F3-CT101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Creative Arts', 'subject_code': 'F3-ART101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'French', 'subject_code': 'F3-FR101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'Fante', 'subject_code': 'F3-FAN101', 'grade_level': 'Form 3'}, 
                {'subject_name': 'History', 'subject_code': 'F3-HIS101', 'grade_level': 'Form 3'}
  ]
    
    for subject_data in subjects_data:
        subject, created = Subject.objects.get_or_create(
            subject_code=subject_data['subject_code'],
            defaults=subject_data
        )
        if created:
            print(f"✓ Created subject: {subject.subject_name}")
    
    print("\n" + "="*50)
    print("Test data created successfully!")
    print("="*50)
    print("\nLogin credentials:")
    print("Email: admin@school.com")
    print("Password: admin123456")
    print("="*50)

if __name__ == '__main__':
    create_test_data()