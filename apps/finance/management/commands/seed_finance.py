import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.finance.models import FeeStructure, Invoice, InvoiceItem, Payment, Expenditure
from apps.academic.models import AcademicYear, Class
from apps.students.models import Student
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Populates financial data: Fee structures, Invoices, Payments, and Expenditures'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Financial Data...")

        # Get prerequisites
        admin_user = User.objects.filter(role='admin').first()
        academic_year = AcademicYear.objects.filter(is_current=True).first()
        
        if not admin_user or not academic_year:
            self.stdout.write(self.style.ERROR("Prerequisites missing. Ensure an Admin user and Current Academic Year exist."))
            return

        with transaction.atomic():
            # 1. Create Fee Structures (General and Class-specific)
            fees_data = [
                ("Tuition Fee", Decimal('1500.00'), 'term', 'all', True),
                ("Development Levy", Decimal('200.00'), 'annual', '1', True),
                ("ICT Fee", Decimal('100.00'), 'term', 'all', True),
                ("Lunch Program", Decimal('500.00'), 'term', 'all', False),
            ]

            structures = []
            for name, amt, freq, term, mandatory in fees_data:
                fs, _ = FeeStructure.objects.get_or_create(
                    academic_year=academic_year,
                    category_name=name,
                    defaults={
                        'amount': amt,
                        'frequency': freq,
                        'term': term,
                        'is_mandatory': mandatory
                    }
                )
                structures.append(fs)

            # 2. Generate Invoices for all Students
            students = Student.objects.all()
            for i, student in enumerate(students):
                inv_no = f"INV/{date.today().year}/{i+1:04d}"
                
                # Create the base invoice
                invoice = Invoice.objects.create(
                    invoice_number=inv_no,
                    student=student,
                    academic_year=academic_year,
                    term='1',
                    total_amount=0, # Will update after adding items
                    amount_paid=0,
                    balance=0,
                    due_date=date.today() + timedelta(days=30),
                    generated_by=admin_user
                )

                # Add items based on mandatory FeeStructures
                running_total = Decimal('0.00')
                for fs in structures:
                    if fs.is_mandatory:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            fee_structure=fs,
                            description=fs.category_name,
                            amount=fs.amount
                        )
                        running_total += fs.amount
                
                # Update Invoice total
                invoice.total_amount = running_total
                invoice.save() # Triggers balance calculation in model save()

                # 3. Randomly Add Payments to some invoices
                if i % 2 == 0:  # Every second student has made a payment
                    pay_amt = invoice.total_amount if i % 4 == 0 else Decimal('500.00')
                    Payment.objects.create(
                        payment_number=f"PAY/{date.today().year}/{i+1:04d}",
                        invoice=invoice,
                        amount_paid=pay_amt,
                        payment_method=random.choice(['cash', 'bank_transfer', 'mobile_money']),
                        transaction_reference=f"REF-{random.randint(10000, 99999)}",
                        received_by=admin_user
                    )

            # 4. Create Realistic Expenditures
            expenses = [
                ("Electricity Bill", 'utilities', Decimal('450.00'), "Utility Co."),
                ("Stationery Restock", 'supplies', Decimal('1200.00'), "Office Depot"),
                ("Plumbing Repairs", 'maintenance', Decimal('300.00'), "FixIt Plumbers"),
                ("Fuel for School Bus", 'transport', Decimal('800.00'), "Shell Station"),
            ]

            for i, (name, cat, amt, vendor) in enumerate(expenses):
                Expenditure.objects.create(
                    expenditure_number=f"EXP/{date.today().year}/{i+1:04d}",
                    item_name=name,
                    category=cat,
                    amount=amt,
                    vendor_name=vendor,
                    transaction_date=date.today() - timedelta(days=random.randint(1, 30)),
                    payment_method='cash',
                    approved_by=admin_user,
                    processed_by=admin_user
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded fees, {students.count()} invoices, payments, and expenses!"))