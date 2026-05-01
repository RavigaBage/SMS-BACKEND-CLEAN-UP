from sqlite3 import IntegrityError
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.staff.services import StaffService
from apps.staff.models import Staff, SalaryStructure
from apps.academic.models import Subject
from datetime import datetime
from .models import Teacher
import logging

logger = logging.getLogger(__name__)


class TeacherService:
    """Service layer for Teacher operations"""
    
    @transaction.atomic
    def create_teacher_profile(self, teacher_data, assigned_by=None):
        """
        Create a teacher profile for an existing user
        
        Args:
            teacher_data: dict with teacher information including user_id
            assigned_by: User who is creating this teacher profile (admin/headmaster)
        
        Returns:
            Teacher object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            user_id = teacher_data.get('user_id')
            if not user_id:
                raise ValidationError("user_id is required")
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValidationError(f"User with id {user_id} does not exist")
            
            if user.role != 'teacher':
                raise ValidationError("User must have 'teacher' role")
            
            if hasattr(user, 'teacher_profile'):
                raise ValidationError("Teacher profile already exists for this user")
            
            subject_ids = teacher_data.pop('subject_ids', [])
            
            teacher = Teacher.objects.create(
                user=user,
                first_name=teacher_data.get('first_name', user.first_name or ''),
                last_name=teacher_data.get('last_name', user.last_name or ''),
                specialization=teacher_data.get('specialization', ''),
                qualifications=teacher_data.get('qualifications', ''),
                years_of_experience=teacher_data.get('years_of_experience', 0),
                phone_number=teacher_data.get('phone_number', ''),
                emergency_contact=teacher_data.get('emergency_contact', ''),
                assigned_by=assigned_by
            )
            staff_data = {
                'first_name': teacher_data.get('first_name', user.first_name or ''),
                'last_name': teacher_data.get('last_name', user.last_name or ''),
                'date_of_birth': teacher_data.get('date_of_birth'),
                'phone_number': teacher_data.get('phone_number', ''),
                'address': teacher_data.get('address', ''),
                'gender': teacher_data.get('gender', ''),
                'staff_type': 'teacher',
                'specialization': teacher_data.get('specialization', ''),
                'employment_date': teacher_data.get('employment_date'),
                'national_id': " ",
                'health_info': " ",
                'photo_url': " ",
            }
        
            staff_data['salary'] = {
                'base_salary': 0,
                'housing_allowance': 0,
                'transport_allowance': 0,
                'other_allowances': 0,
                'effective_from': None,
            }
        
            teacherStaff = self.create_staff_with_teacher(
                staff_data=staff_data,
                user=user,
                created_by=assigned_by
            )
  

            if subject_ids and teacherStaff:
                subjects = Subject.objects.filter(id__in=subject_ids)
                teacher.subjects.set(subjects)
            
            logger.info(f"Teacher profile created for user {user.username} by {assigned_by.username if assigned_by else 'system'}")
            return teacher
            
        except ValidationError as e:
            logger.error(f"Validation error creating teacher profile: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating teacher profile: {str(e)}")
            raise Exception(f"Failed to create teacher profile: {str(e)}")
    
    @transaction.atomic
    def create_staff_with_teacher(self, staff_data,user=None, user_data=None, created_by=None):

        try:
            staff = Staff.objects.create(
                    user=user,
                    first_name=staff_data.get('first_name') or "",
                    last_name=staff_data.get('last_name') or "",
                    date_of_birth=staff_data.get('date_of_birth'),  
                    phone_number=staff_data.get('phone_number') or "",
                    email=(user.email if user else staff_data.get('email')) or "",
                    address=staff_data.get('address') or "",
                    gender="male", 
                    staff_type=user.role,
                    specialization=staff_data.get('specialization') or "",
                    employment_date=staff_data.get('employment_date'), 
                    national_id=staff_data.get('national_id') or "091202",
                    health_info=staff_data.get('health_info') or "",
                    photo_url=staff_data.get('photo_url') or ""
                )
            
            
            if 'salary' in staff_data:
                SalaryStructure.objects.create(
                    staff=staff,
                    base_salary=staff_data['salary'].get('base_salary', 0),
                    housing_allowance=staff_data['salary'].get('housing_allowance', 0),
                    transport_allowance=staff_data['salary'].get('transport_allowance', 0),
                    other_allowances=staff_data['salary'].get('other_allowances', 0),
                    effective_from=datetime.now().date()
                )
            
            return {
                'staff': staff,
                'user': user,
            }
            
        except ValidationError as e:
            logger.error(f"Validation error creating staff: {str(e)}")
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error creating staff: {str(e)}")
            raise ValidationError(f"Database integrity error: {str(e)}")
        except KeyError as e:
            logger.error(f"Missing required field: {str(e)}")
            raise ValidationError(f"Missing required field: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating staff: {str(e)}")
            raise Exception(f"Failed to create staff: {str(e)}")
    
    @transaction.atomic
    def update_teacher_profile(self, teacher_id, teacher_data):
        """
        Update teacher profile information
        
        Args:
            teacher_id: Teacher ID to update
            teacher_data: Dictionary of fields to update
            
        Returns:
            Updated Teacher object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            raise ValidationError("Teacher not found")
        
        try:
            
            subject_ids = teacher_data.pop('subject_ids', None)
            
            for field, value in teacher_data.items():
                if hasattr(teacher, field):
                    setattr(teacher, field, value)
            
            teacher.save()
            
            if subject_ids is not None:
                subjects = Subject.objects.filter(id__in=subject_ids)
                teacher.subjects.set(subjects)
            
            logger.info(f"Teacher profile {teacher_id} updated successfully")
            return teacher
            
        except ValidationError as e:
            logger.error(f"Validation error updating teacher {teacher_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating teacher {teacher_id}: {str(e)}")
            raise Exception(f"Failed to update teacher profile: {str(e)}")
    
    @transaction.atomic
    def assign_subjects(self, teacher_id, subject_ids):
        """
        Assign subjects to a teacher
        
        Args:
            teacher_id: Teacher ID
            subject_ids: List of subject IDs to assign
            
        Returns:
            Updated Teacher object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            raise ValidationError("Teacher not found")
        
        try:
            if not subject_ids:
                raise ValidationError("At least one subject ID is required")
            
            subjects = Subject.objects.filter(id__in=subject_ids)
            if subjects.count() != len(subject_ids):
                raise ValidationError("One or more subject IDs are invalid")
            
            teacher.subjects.set(subjects)
            
            logger.info(f"Subjects assigned to teacher {teacher_id}: {subject_ids}")
            return teacher
            
        except ValidationError as e:
            logger.error(f"Validation error assigning subjects to teacher {teacher_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error assigning subjects to teacher {teacher_id}: {str(e)}")
            raise Exception(f"Failed to assign subjects: {str(e)}")
    
    @transaction.atomic
    def remove_subjects(self, teacher_id, subject_ids):
        """
        Remove subjects from a teacher
        
        Args:
            teacher_id: Teacher ID
            subject_ids: List of subject IDs to remove
            
        Returns:
            Updated Teacher object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            raise ValidationError("Teacher not found")
        
        try:
            if not subject_ids:
                raise ValidationError("At least one subject ID is required")
            
            subjects = Subject.objects.filter(id__in=subject_ids)
            teacher.subjects.remove(*subjects)
            
            logger.info(f"Subjects removed from teacher {teacher_id}: {subject_ids}")
            return teacher
            
        except ValidationError as e:
            logger.error(f"Validation error removing subjects from teacher {teacher_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error removing subjects from teacher {teacher_id}: {str(e)}")
            raise Exception(f"Failed to remove subjects: {str(e)}")
    
    @transaction.atomic
    def deactivate_teacher(self, teacher_id, deactivated_by):
        """
        Deactivate a teacher profile
        
        Args:
            teacher_id: Teacher ID to deactivate
            deactivated_by: User performing the deactivation
            
        Returns:
            Deactivated Teacher object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            teacher = Teacher.objects.select_related('user').get(id=teacher_id)
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            raise ValidationError("Teacher not found")
        
        try:
            if teacher.user == deactivated_by:
                raise ValidationError("You cannot deactivate your own teacher profile")
            
            teacher.is_active = False
            teacher.save()
            
            teacher.user.is_active = False
            teacher.user.save()
            
            logger.info(f"Teacher {teacher_id} deactivated by {deactivated_by.username}")
            return teacher
            
        except ValidationError as e:
            logger.error(f"Validation error deactivating teacher {teacher_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deactivating teacher {teacher_id}: {str(e)}")
            raise Exception(f"Failed to deactivate teacher: {str(e)}")
    
    @staticmethod
    def get_active_teachers():
        """
        Get all active teachers
        
        Returns:
            QuerySet of active Teacher objects
        """
        try:
            return Teacher.objects.filter(
                is_active=True,
                user__is_active=True
            ).select_related('user').prefetch_related('subjects')
        except Exception as e:
            logger.error(f"Error retrieving active teachers: {str(e)}")
            raise Exception(f"Failed to retrieve active teachers: {str(e)}")
    
    @staticmethod
    def get_teachers_by_subject(subject_id):
        """
        Get all teachers qualified to teach a specific subject
        
        Args:
            subject_id: Subject ID
            
        Returns:
            QuerySet of Teacher objects
        """
        try:
            return Teacher.objects.filter(
                subjects__id=subject_id,
                is_active=True,
                user__is_active=True
            ).select_related('user').prefetch_related('subjects')
        except Exception as e:
            logger.error(f"Error retrieving teachers by subject {subject_id}: {str(e)}")
            raise Exception(f"Failed to retrieve teachers: {str(e)}")
    
    @staticmethod
    def get_teacher_workload(teacher_id):
        """
        Get teacher's workload (classes and subject assignments)
        
        Args:
            teacher_id: Teacher ID
            
        Returns:
            Dictionary with workload information
        """
        try:
            teacher = Teacher.objects.get(id=teacher_id)
            
            assigned_classes = teacher.get_assigned_classes()
            subject_assignments = teacher.get_subject_assignments()
            
            return {
                'teacher': teacher,
                'assigned_classes': assigned_classes,
                'assigned_classes_count': assigned_classes.count(),
                'subject_assignments': subject_assignments,
                'subject_assignments_count': subject_assignments.count(),
                'total_workload': assigned_classes.count() + subject_assignments.count()
            }
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            raise ValidationError("Teacher not found")
        except Exception as e:
            logger.error(f"Error retrieving teacher workload for {teacher_id}: {str(e)}")
            raise Exception(f"Failed to retrieve teacher workload: {str(e)}")