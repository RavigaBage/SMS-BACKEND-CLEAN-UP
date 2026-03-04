from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from decimal import Decimal
from .models import Staff, SalaryStructure, SalaryPayment


@receiver(post_save, sender=Staff)
def create_default_salary_structure(sender, instance, created, **kwargs):
    if created:
        SalaryStructure.objects.get_or_create(
            staff=instance,
            defaults={
                'base_salary': 0,
                'housing_allowance': 0,
                'transport_allowance': 0,
                'other_allowances': 0,
                'effective_from': instance.employment_date or datetime.now().date()
            }
        )


@receiver(post_save, sender=SalaryStructure)
def recalculate_pending_payments(sender, instance, **kwargs):
    """
    Whenever a salary structure is created or updated,
    recalculate all PENDING zero payments for that staff.
    This ensures no staff ever has a zero salary record.
    """
    staff = instance.staff

    base_salary = instance.base_salary
    allowances = (
        instance.housing_allowance +
        instance.transport_allowance +
        instance.other_allowances
    )
    gross_salary = base_salary + allowances
    tax = gross_salary * Decimal('0.10')
    net_salary = gross_salary - tax

    pending_zero = SalaryPayment.objects.filter(
        staff=staff,
        status=SalaryPayment.PaymentStatus.PENDING,
        base_salary=0
    )

    if pending_zero.exists():
        pending_zero.update(
            base_salary=base_salary,
            allowances=allowances,
            tax=tax,
            net_salary=net_salary,
        )
