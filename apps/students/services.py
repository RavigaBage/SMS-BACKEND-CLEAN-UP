from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Student, Parent, StudentParent
from apps.grades.models import Grade
from apps.attendance.models import Attendance
from apps.academic.models import Class, Enrollment
from datetime import datetime


class StudentService:
    """Service layer for Student operations"""
    
    @transaction.atomic
    def register_student(self, student_data, parent_data_list=None, class_id=None, created_by=None):
        """
        Register a new student with optional parents and class enrollment.
        
        Args:
            student_data: dict with student information
            parent_data_list: list of dicts with parent information (optional)
            class_id: Class ID to enroll student in (optional)
            created_by: User who is registering the student
        
        Returns:
            dict with student, parents, and enrollment
        """
        # Validate admission number uniqueness
        if Student.objects.filter(admission_number=student_data['admission_number']).exists():
            raise ValidationError(f"Admission number {student_data['admission_number']} already exists")
        
        # Create Student
        student = Student.objects.create(
            admission_number=student_data['admission_number'],
            first_name=student_data['first_name'],
            last_name=student_data['last_name'],
            middle_name=student_data.get('middle_name', ''),
            date_of_birth=student_data['date_of_birth'],
            gender=student_data['gender'],
            address=student_data.get('address', ''),
            nationality=student_data.get('nationality', ''),
            religion=student_data.get('religion', ''),
            blood_group=student_data.get('blood_group', ''),
            medical_conditions=student_data.get('medical_conditions', ''),
            status=student_data.get('status', Student.Status.ACTIVE),
            admission_date=student_data.get('admission_date', datetime.now().date()),
            photo_url=student_data.get('photo_url', ''),
            created_by=created_by
        )
        
        # Create/Link Parents
        parents = []
        if parent_data_list:
            parents = self._process_parents(student, parent_data_list)
        
        # Enroll in class if provided
        enrollment = None
        if class_id:
            enrollment = self._enroll_student(student, class_id)
        
        return {
            'student': student,
            'parents': parents,
            'enrollment': enrollment
        }
    
    def _process_parents(self, student, parent_data_list):
        """Process and link parents to student"""
        parents = []
        
        for parent_data in parent_data_list:
            # Check if parent already exists (by phone number or national_id)
            parent = None
            
            if parent_data.get('national_id'):
                parent = Parent.objects.filter(national_id=parent_data['national_id']).first()
            
            if not parent and parent_data.get('phone_number'):
                parent = Parent.objects.filter(phone_number=parent_data['phone_number']).first()
            
            # Create parent if doesn't exist
            if not parent:
                parent = Parent.objects.create(
                    first_name=parent_data['first_name'],
                    last_name=parent_data['last_name'],
                    phone_number=parent_data['phone_number'],
                    email=parent_data.get('email', ''),
                    address=parent_data.get('address', ''),
                    occupation=parent_data.get('occupation', ''),
                    workplace=parent_data.get('workplace', ''),
                    national_id=parent_data.get('national_id', ''),
                    relationship=parent_data['relationship']
                )
            
            # Link parent to student
            StudentParent.objects.create(
                student=student,
                parent=parent,
                is_primary_contact=parent_data.get('is_primary_contact', False),
                can_pickup=parent_data.get('can_pickup', True)
            )
            
            parents.append(parent)
        
        return parents
    
    def _enroll_student(self, student, class_id):
        """Enroll student in a class"""
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            raise ValidationError("Class not found")
        
        # Check if already enrolled
        if Enrollment.objects.filter(student=student, class_obj=class_obj).exists():
            raise ValidationError(f"Student already enrolled in {class_obj.class_name}")
        
        # Check class capacity
        if class_obj.current_enrollment >= class_obj.capacity:
            raise ValidationError(f"Class {class_obj.class_name} is at full capacity")
        
        # Get next roll number
        last_enrollment = Enrollment.objects.filter(class_obj=class_obj).order_by('-roll_number').first()
        next_roll_number = (last_enrollment.roll_number + 1) if last_enrollment and last_enrollment.roll_number else 1
        
        enrollment = Enrollment.objects.create(
            student=student,
            class_obj=class_obj,
            roll_number=next_roll_number,
            status=Enrollment.EnrollmentStatus.ACTIVE
        )
        
        return enrollment
    
    @transaction.atomic
    def update_student(self, student_id, student_data):
        """Update student information"""
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValidationError("Student not found")
        
        # Check admission number uniqueness if being changed
        if 'admission_number' in student_data and student_data['admission_number'] != student.admission_number:
            if Student.objects.filter(admission_number=student_data['admission_number']).exists():
                raise ValidationError(f"Admission number {student_data['admission_number']} already exists")
        
        # Update fields
        for field, value in student_data.items():
            if hasattr(student, field):
                setattr(student, field, value)
        
        student.save()
        return student
    
    @transaction.atomic
    def add_parent_to_student(self, student_id, parent_data):
        """Add a new parent to an existing student"""
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValidationError("Student not found")
        
        parents = self._process_parents(student, [parent_data])
        return parents[0]
    
    @transaction.atomic
    def transfer_student(self, student_id, new_class_id, transfer_date=None):
        """Transfer student to a new class"""
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValidationError("Student not found")
        
        # Mark current enrollment as completed
        current_enrollment = Enrollment.objects.filter(
            student=student,
            status=Enrollment.EnrollmentStatus.ACTIVE
        ).first()
        
        if current_enrollment:
            current_enrollment.status = Enrollment.EnrollmentStatus.COMPLETED
            current_enrollment.save()
        
        # Create new enrollment
        new_enrollment = self._enroll_student(student, new_class_id)
        
        return new_enrollment
    
    @staticmethod
    # apps/students/services.py
    def get_student_with_details(student_id):
        # The error is happening right here in this prefetch_related call
        return {
            'student': Student.objects.prefetch_related(
                'parent_links__parent',
                'academic_grades',  # <--- CHANGE THIS from 'grades'
                'enrollments',
                'attendance_records' 
            ).get(id=student_id),
            
            'parents': Parent.objects.filter(student_links__student_id=student_id),
            
            'grades': Grade.objects.filter(student_id=student_id).order_by('-grade_date'),
            
            'attendance': Attendance.objects.filter(student_id=student_id).order_by('-created_at'),
            'current_enrollment': Enrollment.objects.filter(
                student_id=student_id, 
                status='active'
            ).first(),
        }
    
    @staticmethod
    def search_students(query):
        """Search students by name or admission number"""
        return Student.objects.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(admission_number__icontains=query)
        )
    
    def delete_student(self, student_id):
        try:
            student = Student.objects.get(id=student_id)
            # You can add custom logic here, like archiving instead of deleting
            student.delete()
            return True
        except Student.DoesNotExist:
            raise Exception("Student not found")


class ParentService:
    """Service layer for Parent operations"""
    
    @transaction.atomic
    def update_parent(self, parent_id, parent_data):
        """Update parent information"""
        try:
            parent = Parent.objects.get(id=parent_id)
        except Parent.DoesNotExist:
            raise ValidationError("Parent not found")
        
        # Update fields
        for field, value in parent_data.items():
            if hasattr(parent, field):
                setattr(parent, field, value)
        
        parent.save()
        return parent
    
    @staticmethod
    def get_parent_children(parent_id):
        """Get all children linked to a parent"""
        try:
            parent = Parent.objects.prefetch_related('student_links__student').get(id=parent_id)
            return [link.student for link in parent.student_links.all()]
        except Parent.DoesNotExist:
            raise ValidationError("Parent not found")