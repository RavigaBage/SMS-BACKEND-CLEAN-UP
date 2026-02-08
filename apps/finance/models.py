from django.db import models
from decimal import Decimal
from apps.students.models import Student
from apps.academic.models import AcademicYear, Class
from apps.accounts.models import User


class FeeStructure(models.Model):
    """Fee structure configuration"""
    
    class Frequency(models.TextChoices):
        ONE_TIME = 'one_time', 'One Time'
        TERM = 'term', 'Per Term'
        ANNUAL = 'annual', 'Annual'
    
    class Term(models.TextChoices):
        TERM_1 = '1', 'Term 1'
        TERM_2 = '2', 'Term 2'
        TERM_3 = '3', 'Term 3'
        ALL = 'all', 'All Terms'
 
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='fee_structures')
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fee_structures',
        help_text="Leave blank to apply to all classes"
    )
    category_name = models.CharField(max_length=100, help_text="Tuition, Lab Fee, Transport, etc.")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.TERM)
    term = models.CharField(max_length=3, choices=Term.choices, default=Term.ALL)
    is_mandatory = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'fee_structures'
        ordering = ['academic_year', 'category_name']
        indexes = [
            models.Index(fields=['academic_year']),
            models.Index(fields=['class_obj']),
        ]
    
    def __str__(self):
        class_name = self.class_obj.class_name if self.class_obj else "All Classes"
        return f"{self.category_name} - {class_name} ({self.academic_year.year_name})"


class Invoice(models.Model):
    """Student fee invoices"""
    
    class InvoiceStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PARTIAL = 'partial', 'Partially Paid'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class Term(models.TextChoices):
        TERM_1 = '1', 'Term 1'
        TERM_2 = '2', 'Term 2'
        TERM_3 = '3', 'Term 3'
        ANNUAL = 'annual', 'Annual'

    
    invoice_number = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='invoices')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='invoices')
    term = models.CharField(max_length=10, choices=Term.choices)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_invoices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['student', 'academic_year']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.student.full_name}"

    def save(self, *args, **kwargs):
        # Auto-calculate balance
        self.balance = self.total_amount - self.amount_paid

        # Auto-update status
        if self.amount_paid >= self.total_amount:
            self.status = self.InvoiceStatus.PAID
        elif self.amount_paid > 0:
            self.status = self.InvoiceStatus.PARTIAL

        super().save(*args, **kwargs)

class InvoiceItem(models.Model):
    """Line items in an invoice"""

    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'invoice_items'
        indexes = [
            models.Index(fields=['invoice']),
        ]

    def __str__(self):
        return f"{self.description} - {self.amount}"
    
class Payment(models.Model):
    """Payment records"""

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'
        CHEQUE = 'cheque', 'Cheque'


    payment_number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_payments'
    )

    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['invoice']),
            models.Index(fields=['payment_date']),
        ]

    def __str__(self):
        return f"Payment {self.payment_number} - {self.amount_paid}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update invoice amount_paid
        self.invoice.amount_paid = self.invoice.payments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')
        self.invoice.save()


class Expenditure(models.Model):
    """School expenditures"""

    class Category(models.TextChoices):
        UTILITIES = 'utilities', 'Utilities'
        SUPPLIES = 'supplies', 'Supplies'
        MAINTENANCE = 'maintenance', 'Maintenance'
        SALARIES = 'salaries', 'Salaries'
        TRANSPORT = 'transport', 'Transport'
        OTHER = 'other', 'Other'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CHEQUE = 'cheque', 'Cheque'

    expenditure_number = models.CharField(max_length=50, unique=True)
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    vendor_name = models.CharField(max_length=255, blank=True)
    transaction_date = transaction_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    description = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True, max_length=255)
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_expenditures'
    )
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_expenditures'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'expenditures'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['expenditure_number']),
            models.Index(fields=['category']),
            models.Index(fields=['transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.expenditure_number} - {self.item_name} ({self.amount})"