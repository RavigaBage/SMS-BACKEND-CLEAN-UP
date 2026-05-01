import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import FeeStructure
from django.db.models.signals import post_save, pre_delete
from .models import FeeStructure, InvoiceItem, Invoice
from decimal import Decimal
from django.db.models import Sum
logger = logging.getLogger(__name__)


@receiver(post_save, sender=FeeStructure)
def on_fee_structure_created(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: _trigger_auto_invoices(instance.pk))


def _trigger_auto_invoices(fee_structure_pk):
    from .models import FeeStructure
    from .services import InvoiceService
    try:
        fee_structure = FeeStructure.objects.select_related('class_obj').get(pk=fee_structure_pk)
        InvoiceService().auto_generate_invoices_for_fee_structure(fee_structure)
    except Exception:
        logger.exception(
            "Auto-invoice generation failed for FeeStructure pk=%s", fee_structure_pk
        )


@receiver(pre_delete, sender=FeeStructure)
def on_fee_structure_deleted(sender, instance, **kwargs):
    items = InvoiceItem.objects.filter(
        fee_structure=instance
    ).select_related('invoice')

    affected_invoice_ids = set(items.values_list('invoice_id', flat=True))

    items.delete()

    for invoice in Invoice.objects.filter(id__in=affected_invoice_ids).prefetch_related('items'):
        remaining_total = invoice.items.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        invoice.total_amount = remaining_total
        invoice.balance = max(remaining_total - invoice.amount_paid, Decimal('0.00'))

        has_no_items = not invoice.items.exists()
        has_no_payments = invoice.amount_paid == Decimal('0.00')

        if has_no_items and has_no_payments:
            invoice.status = Invoice.InvoiceStatus.CANCELLED
        elif invoice.amount_paid >= remaining_total and remaining_total > 0:
            invoice.status = Invoice.InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = Invoice.InvoiceStatus.PARTIAL
        else:
            invoice.status = Invoice.InvoiceStatus.UNPAID

        invoice.save()

    logger.info(
        "FeeStructure pk=%s deleted: %d invoices recalculated.",
        instance.pk, len(affected_invoice_ids)
    )