from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.accounts.services import UserService
from .models import Staff, SalaryStructure, SalaryPayment
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StaffService:
    """Service layer for Staff operations"""
    
    @transaction.atomic
    def create_staff_with_user(self, staff_data, user_data=None, created_by=None):
        """
        Atomically create User + Staff profile in a single transaction.
        
        Args:
            staff_data: dict with staff profile information
            user_data: dict with user account information (optional, will be generated if not provided)
            created_by: User object who is creating this staff
        
        Returns:
            Staff object with associated User
        
        Raises:
            ValidationError: If validation fails
            Exception: For other errors
        """
        try:
            role = staff_data.get('staff_type', 'teacher')
            user_role_map = {
                'teacher': User.Role.TEACHER,
                'headmaster': User.Role.HEADMASTER,
                'bursar': User.Role.BURSAR,
                'admin_staff': User.Role.ADMIN,
                'support_staff': User.Role.TEACHER,
            }
            
            target_role = user_role_map.get(role, User.Role.TEACHER)
            
            if created_by:
                UserService.validate_role_permissions(created_by, target_role)
            
            if not user_data:
                user_data = {}
            
            if 'username' not in user_data:
                user_data['username'] = UserService.generate_username(
                    staff_data['first_name'],
                    staff_data['last_name'],
                    role
                )
            
            if 'email' not in user_data:
                user_data['email'] = f"{user_data['username']}@school.com"
            
            UserService.validate_email_unique(user_data['email'])
            
            if 'password' not in user_data:
                user_data['password'] = UserService.generate_password()
                generated_password = user_data['password']
            else:
                generated_password = None
            
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                role=target_role,
                created_by=created_by
            )
            
          
            staff = Staff.objects.create(
                user=user,
                first_name=staff_data['first_name'],
                last_name=staff_data['last_name'],
                date_of_birth=staff_data.get('date_of_birth'),
                phone_number=staff_data.get('phone_number', ''),
                email=user_data['email'], 
                address=staff_data.get('address', ''),
                gender=staff_data.get('gender', ''),
                staff_type=role,
                specialization=staff_data.get('specialization', ''),
                employment_date=staff_data.get('employment_date'),
                national_id=staff_data.get('national_id', ''),
                health_info=staff_data.get('health_info', ''),
                photo_url=staff_data.get('photo_url', '')
            )
            
            if 'salary' in staff_data:
                SalaryStructure.objects.create(
                    staff=staff,
                    base_salary=staff_data['salary'].get('base_salary', 0),
                    housing_allowance=staff_data['salary'].get('housing_allowance', 0),
                    transport_allowance=staff_data['salary'].get('transport_allowance', 0),
                    other_allowances=staff_data['salary'].get('other_allowances', 0),
                    effective_from=staff_data['salary'].get('effective_from', datetime.now().date())
                )
            
            return {
                'staff': staff,
                'user': user,
                'generated_password': generated_password,
                'username': user.username
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
    def update_staff(self, staff_id, staff_data):
        """
        Update staff information
        
        Args:
            staff_id: Staff ID to update
            staff_data: Dictionary of fields to update
            
        Returns:
            Updated Staff object
            
        Raises:
            ValidationError: If validation fails or staff not found
        """
        try:
            staff = Staff.objects.select_related('user').get(id=staff_id)
        except Staff.DoesNotExist:
            logger.error(f"Staff with id {staff_id} not found")
            raise ValidationError("Staff not found")
        
        try:
          
            for field, value in staff_data.items():
                if field not in ['user', 'salary'] and hasattr(staff, field):
                    setattr(staff, field, value)
            
            if 'email' in staff_data:
                if staff_data['email'] != staff.user.email:
                    UserService.validate_email_unique(staff_data['email'])
                    staff.user.email = staff_data['email']
                    staff.user.save()
            
            staff.save()
            return staff
            
        except ValidationError as e:
            logger.error(f"Validation error updating staff {staff_id}: {str(e)}")
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error updating staff {staff_id}: {str(e)}")
            raise ValidationError(f"Database integrity error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating staff {staff_id}: {str(e)}")
            raise Exception(f"Failed to update staff: {str(e)}")
    
    @transaction.atomic
    def deactivate_staff(self, staff_id, deactivated_by):
        """
        Deactivate staff member (disable their user account)
        
        Args:
            staff_id: Staff ID to deactivate
            deactivated_by: User performing the deactivation
            
        Returns:
            Deactivated Staff object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            staff = Staff.objects.select_related('user').get(id=staff_id)
        except Staff.DoesNotExist:
            logger.error(f"Staff with id {staff_id} not found")
            raise ValidationError("Staff not found")
        
        try:
            
            if staff.user == deactivated_by:
                raise ValidationError("You cannot deactivate your own account")
            
            staff.user.is_active = False
            staff.user.save()
            
            logger.info(f"Staff {staff_id} deactivated by {deactivated_by.username}")
            return staff
            
        except ValidationError as e:
            logger.error(f"Validation error deactivating staff {staff_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deactivating staff {staff_id}: {str(e)}")
            raise Exception(f"Failed to deactivate staff: {str(e)}")
    
    @staticmethod
    def get_staff_by_type(staff_type):
        """
        Get all staff of a specific type
        
        Args:
            staff_type: Type of staff to retrieve
            
        Returns:
            QuerySet of Staff objects
        """
        try:
            return Staff.objects.filter(staff_type=staff_type).select_related('user')
        except Exception as e:
            logger.error(f"Error retrieving staff by type {staff_type}: {str(e)}")
            raise Exception(f"Failed to retrieve staff: {str(e)}")
    
    @staticmethod
    def get_active_teachers():
        """
        Get all active teachers
        
        Returns:
            QuerySet of active teacher Staff objects
        """
        try:
            return Staff.objects.filter(
                staff_type='teacher',
                user__is_active=True
            ).select_related('user')
        except Exception as e:
            logger.error(f"Error retrieving active teachers: {str(e)}")
            raise Exception(f"Failed to retrieve active teachers: {str(e)}")


class SalaryService:
    """Service layer for salary operations"""
    
    @transaction.atomic
    def process_monthly_salary(self, staff_id, payment_period, processed_by):
        """
        Process monthly salary for a staff member
        
        Args:
            staff_id: Staff ID
            payment_period: String like "January 2025"
            processed_by: User who is processing the payment
            
        Returns:
            Created SalaryPayment object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            logger.error(f"Staff with id {staff_id} not found")
            raise ValidationError("Staff not found")
        
        try:
          
            if SalaryPayment.objects.filter(staff=staff, payment_period=payment_period).exists():
                raise ValidationError(f"Salary already processed for {payment_period}")
            
            salary_structure = SalaryStructure.objects.filter(
                staff=staff,
                effective_from__lte=datetime.now().date()
            ).order_by('-effective_from').first()
            
            if not salary_structure:
                raise ValidationError("No salary structure found for this staff")
            
            
            base_salary = salary_structure.base_salary
            allowances = (
                salary_structure.housing_allowance +
                salary_structure.transport_allowance +
                salary_structure.other_allowances
            )
            
            gross_salary = base_salary + allowances
            tax = gross_salary * 0.10
            
            net_salary = gross_salary - tax
            
            salary_payment = SalaryPayment.objects.create(
                staff=staff,
                payment_period=payment_period,
                base_salary=base_salary,
                allowances=allowances,
                deductions=0,
                tax=tax,
                net_salary=net_salary,
                status=SalaryPayment.PaymentStatus.PENDING,
                processed_by=processed_by
            )
            
            logger.info(f"Salary processed for staff {staff_id}, period {payment_period}")
            return salary_payment
            
        except ValidationError as e:
            logger.error(f"Validation error processing salary for staff {staff_id}: {str(e)}")
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error processing salary for staff {staff_id}: {str(e)}")
            raise ValidationError(f"Database integrity error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing salary for staff {staff_id}: {str(e)}")
            raise Exception(f"Failed to process salary: {str(e)}")
    
    @transaction.atomic
    def mark_salary_as_paid(self, salary_payment_id, payment_date, payment_method):
        """
        Mark a salary payment as paid
        
        Args:
            salary_payment_id: SalaryPayment ID
            payment_date: Date of payment
            payment_method: Method used for payment
            
        Returns:
            Updated SalaryPayment object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            salary_payment = SalaryPayment.objects.get(id=salary_payment_id)
        except SalaryPayment.DoesNotExist:
            logger.error(f"Salary payment with id {salary_payment_id} not found")
            raise ValidationError("Salary payment not found")
        
        try:
            if salary_payment.status == SalaryPayment.PaymentStatus.PAID:
                raise ValidationError("Salary already marked as paid")
            
            salary_payment.status = SalaryPayment.PaymentStatus.PAID
            salary_payment.payment_date = payment_date
            salary_payment.payment_method = payment_method
            salary_payment.save()
            
            logger.info(f"Salary payment {salary_payment_id} marked as paid")
            return salary_payment
            
        except ValidationError as e:
            logger.error(f"Validation error marking salary as paid {salary_payment_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error marking salary as paid {salary_payment_id}: {str(e)}")
            raise Exception(f"Failed to mark salary as paid: {str(e)}")