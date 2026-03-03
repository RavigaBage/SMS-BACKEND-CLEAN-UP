import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.finance.models import Expenditure, FeeStructure, Invoice, InvoiceItem, Payment
from apps.students.models import Student


class Command(BaseCommand):
    help = "Populate finance data (fees, invoices, payments, expenditures) for pagination testing."

    def add_arguments(self, parser):
        parser.add_argument("--invoices", type=int, default=200, help="Number of invoices to ensure.")
        parser.add_argument("--expenditures", type=int, default=120, help="Number of expenditures to ensure.")
        parser.add_argument("--year", type=str, default="2025-2026", help="Academic year string.")
        parser.add_argument("--prefix", type=str, default="SEED", help="Invoice/payment/expenditure id prefix.")

    def handle(self, *args, **options):
        target_invoices = max(0, int(options["invoices"]))
        target_expenditures = max(0, int(options["expenditures"]))
        year_name = options["year"].strip()
        prefix = options["prefix"].strip().upper()

        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No admin user found. Run seed_account first."))
            return

        students = list(Student.objects.order_by("id"))
        if not students:
            self.stdout.write(self.style.ERROR("No students found. Run seed_students first."))
            return

        self.stdout.write(self.style.NOTICE("Seeding finance data..."))
        with transaction.atomic():
            fees_data = [
                ("Tuition Fee", Decimal("1500.00"), "term", "all", True),
                ("Development Levy", Decimal("200.00"), "annual", "1", True),
                ("ICT Fee", Decimal("100.00"), "term", "all", True),
                ("Library Fee", Decimal("80.00"), "term", "all", True),
                ("Lunch Program", Decimal("500.00"), "term", "all", False),
            ]
            structures = []
            for name, amt, freq, term, mandatory in fees_data:
                fs, _ = FeeStructure.objects.get_or_create(
                    academic_year=year_name,
                    category_name=name,
                    defaults={
                        "amount": amt,
                        "frequency": freq,
                        "term": term,
                        "is_mandatory": mandatory,
                    },
                )
                structures.append(fs)

            existing_invoice_count = Invoice.objects.filter(
                invoice_number__startswith=f"{prefix}-INV-"
            ).count()
            to_create_invoices = max(0, target_invoices - existing_invoice_count)

            created_invoices = 0
            for i in range(to_create_invoices):
                student = students[(existing_invoice_count + i) % len(students)]
                seq = existing_invoice_count + i + 1
                inv_no = f"{prefix}-INV-{date.today().year}-{seq:06d}"

                if Invoice.objects.filter(invoice_number=inv_no).exists():
                    continue

                invoice = Invoice.objects.create(
                    invoice_number=inv_no,
                    student=student,
                    academic_year=year_name,
                    term=random.choice(["1", "2", "3"]),
                    total_amount=Decimal("0.00"),
                    amount_paid=Decimal("0.00"),
                    balance=Decimal("0.00"),
                    due_date=date.today() + timedelta(days=random.randint(14, 90)),
                    generated_by=admin_user,
                )

                running_total = Decimal("0.00")
                for fs in structures:
                    if fs.is_mandatory or random.randint(1, 100) <= 20:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            fee_structure=fs,
                            description=fs.category_name,
                            amount=fs.amount,
                        )
                        running_total += fs.amount

                invoice.total_amount = running_total
                invoice.save()

                payment_chance = random.randint(1, 100)
                if payment_chance <= 70 and running_total > 0:
                    if payment_chance <= 30:
                        pay_amt = running_total
                    else:
                        pay_amt = (running_total * Decimal(str(random.uniform(0.25, 0.8)))).quantize(
                            Decimal("0.01")
                        )

                    Payment.objects.create(
                        payment_number=f"{prefix}-PAY-{date.today().year}-{seq:06d}",
                        invoice=invoice,
                        amount_paid=pay_amt,
                        payment_method=random.choice(
                            ["cash", "bank_transfer", "mobile_money", "card"]
                        ),
                        transaction_reference=f"REF-{random.randint(100000, 999999)}",
                        received_by=admin_user,
                    )

                created_invoices += 1

            categories = [choice[0] for choice in Expenditure.Category.choices]
            methods = [choice[0] for choice in Expenditure.PaymentMethod.choices]
            existing_exp_count = Expenditure.objects.filter(
                expenditure_number__startswith=f"{prefix}-EXP-"
            ).count()
            to_create_exp = max(0, target_expenditures - existing_exp_count)
            created_exp = 0

            expense_names = [
                "Electricity Bill",
                "Stationery Restock",
                "Plumbing Repairs",
                "Bus Fuel",
                "Internet Subscription",
                "Printer Toner",
                "Sports Kits",
                "Cleaning Supplies",
            ]

            for i in range(to_create_exp):
                seq = existing_exp_count + i + 1
                exp_no = f"{prefix}-EXP-{date.today().year}-{seq:06d}"
                if Expenditure.objects.filter(expenditure_number=exp_no).exists():
                    continue

                Expenditure.objects.create(
                    expenditure_number=exp_no,
                    item_name=random.choice(expense_names),
                    category=random.choice(categories),
                    amount=Decimal(random.randint(50, 5000)),
                    vendor_name=f"Vendor {random.randint(1, 200)}",
                    transaction_date=date.today() - timedelta(days=random.randint(0, 180)),
                    payment_method=random.choice(methods),
                    description="Auto-seeded for pagination testing.",
                    approved_by=admin_user,
                    processed_by=admin_user,
                )
                created_exp += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finance seed complete. Created {created_invoices} invoices and {created_exp} expenditures."
            )
        )
