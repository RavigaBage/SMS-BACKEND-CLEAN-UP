from django.db import transaction,models
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Invoice, InvoiceItem, Payment, FeeStructure
from apps.students.models import Student
from apps.academic.models import AcademicYear, Class
from datetime import datetime, timedelta


class InvoiceService:
    """Service layer for Invoice operations"""
    
    @transaction.atomic

    def generate_invoice_for_student(self, student_id, academic_year, term, generated_by, due_days=30):
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValidationError("Student not found")
        
       
        # Fix: use the string value for the CharField
        academic_year_str = academic_year # or whatever the string field is

        # Fix: compare with the string, not the object
        existing_invoice = Invoice.objects.filter(
            student=student,
            academic_year=academic_year_str,
            term=term
        ).first()
        
        if existing_invoice:
            raise ValidationError("Invoice already exists for this student and term")
        
        enrollment = student.enrollments.filter(status='active').select_related('class_obj').first()
        if not enrollment:
            raise ValidationError("Student is not enrolled in any class")
        
        fee_structures = FeeStructure.objects.filter(
            academic_year=academic_year,  # this FK lookup is fine on FeeStructure
            is_mandatory=True
        ).filter(
            models.Q(class_obj=enrollment.class_obj) | models.Q(class_obj__isnull=True)
        ).filter(
            models.Q(term=term) | models.Q(term='all')
        )
        
        if not fee_structures.exists():
            raise ValidationError("No fee structures found for this student")
        
        invoice_number = self._generate_invoice_number(academic_year, term)
        total_amount = sum(fee.amount for fee in fee_structures)
        
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            student=student,
            academic_year=academic_year_str,  # Fix: store string, not object
            term=term,
            total_amount=total_amount,
            amount_paid=Decimal('0.00'),
            balance=total_amount,
            due_date=datetime.now().date() + timedelta(days=due_days),
            status=Invoice.InvoiceStatus.UNPAID,
            generated_by=generated_by
        )
        
        # Fix: use the correct field name from FeeStructure (check your model)
        for fee in fee_structures:
            InvoiceItem.objects.create(
                invoice=invoice,
                fee_structure=fee,
                description=fee.category_name,  # <-- verify the actual field name on FeeStructure
                amount=fee.amount
            )
        
        return invoice
    
    def _generate_invoice_number(self, academic_year, term):
        """Generate unique invoice number"""
        year_code = academic_year.replace('-', '')[:4]
        term_code = term.upper()
        
        # Get last invoice number for this period
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f"INV-{year_code}-{term_code}"
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"INV-{year_code}-{term_code}-{new_number:05d}"
    
    @transaction.atomic
    def generate_bulk_invoices(self, class_id, academic_year_id, term, generated_by):
        """Generate invoices for all students in a class"""
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            raise ValidationError("Class not found")
        
        # Get all active enrollments in this class
        enrollments = class_obj.enrollments.filter(status='active').select_related('student')
        
        invoices = []
        errors = []
        
        for enrollment in enrollments:
            try:
                invoice = self.generate_invoice_for_student(
                    enrollment.student.id,
                    academic_year_id,
                    term,
                    generated_by
                )
                invoices.append(invoice)
            except ValidationError as e:
                errors.append({
                    'student': enrollment.student.full_name,
                    'error': str(e)
                })
        
        return {
            'invoices': invoices,
            'errors': errors
        }


class PaymentService:
    """Service layer for Payment operations"""
    
    @transaction.atomic
    def record_payment(self, invoice_id, amount_paid, payment_method, transaction_reference='', received_by=None):
        """
        Record a payment against an invoice.
        
        Args:
            invoice_id: Invoice ID
            amount_paid: Amount being paid
            payment_method: Payment method
            transaction_reference: Transaction reference number
            received_by: User who received the payment
        
        Returns:
            Payment object
        """
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise ValidationError("Invoice not found")
        
        # Validate payment amount
        if amount_paid <= 0:
            raise ValidationError("Payment amount must be greater than zero")
        
        if amount_paid > invoice.balance:
            raise ValidationError(f"Payment amount ({amount_paid}) exceeds balance ({invoice.balance})")
        
        # Generate payment number
        payment_number = self._generate_payment_number()
        
        # Create payment record
        payment = Payment.objects.create(
            payment_number=payment_number,
            invoice=invoice,
            amount_paid=amount_paid,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            received_by=received_by
        )
        
        # Invoice update is handled in Payment.save() method
        
        return payment
    
    def _generate_payment_number(self):
        """Generate unique payment number"""
        today = datetime.now()
        date_code = today.strftime('%Y%m%d')
        
        # Get last payment number for today
        last_payment = Payment.objects.filter(
            payment_number__startswith=f"PAY-{date_code}"
        ).order_by('-payment_number').first()
        
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"PAY-{date_code}-{new_number:04d}"
    
    @staticmethod
    def get_payment_history(invoice_id):
        """Get all payments for an invoice"""
        return Payment.objects.filter(invoice_id=invoice_id).order_by('-payment_date')
    
    @staticmethod
    def get_student_payment_history(student_id):
        """Get all payments for a student across all invoices"""
        return Payment.objects.filter(
            invoice__student_id=student_id
        ).select_related('invoice').order_by('-payment_date')