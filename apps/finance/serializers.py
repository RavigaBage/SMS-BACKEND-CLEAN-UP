from rest_framework import serializers
from .models import FeeStructure, Invoice, InvoiceItem, Payment, Expenditure
from apps.students.serializers import StudentSerializer
from apps.academic.serializers import ClassSerializer
from django.apps import apps

Class = apps.get_model('academic', 'Class')


class FeeStructureSerializer(serializers.ModelSerializer):
    academic_year    = serializers.CharField()

    class_obj        = ClassSerializer(read_only=True)
    class_obj_id     = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_obj',
        write_only=True,
        required=False,
        allow_null=True,
    )

    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    term_display      = serializers.CharField(source='get_term_display',      read_only=True)

    class Meta:
        model  = FeeStructure
        fields = [
            'id', 'academic_year',
            'class_obj', 'class_obj_id',
            'category_name', 'amount',
            'frequency', 'frequency_display',
            'term', 'term_display',
            'is_mandatory',
        ]
        read_only_fields = ['id']


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = InvoiceItem
        fields = ['id','description', 'amount']


class InvoiceSerializer(serializers.ModelSerializer):
    student    = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=apps.get_model('students', 'Student').objects.all(),
        source='student',
        write_only=True,
    )

    # academic_year is a plain string — just accept it as-is
    academic_year = serializers.CharField()
    items                  = InvoiceItemSerializer(many=True, read_only=True)
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    term_display           = serializers.CharField(source='get_term_display',   read_only=True)
    generated_by_username  = serializers.CharField(
        source='generated_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model  = Invoice
        fields = '__all__'
        read_only_fields = [
                'id',
                'invoice_number',
                'student',           # the nested representation
                'items',
                'amount_paid',
                'balance',           # auto-calculated in model.save()
                'status',
                'status_display',
                'term_display',
                'generated_by_username',
            ]


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number         = serializers.CharField(source='invoice.invoice_number', read_only=True)
    student_name           = serializers.CharField(source='invoice.student.full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    received_by_username   = serializers.CharField(
        source='received_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model  = Payment
        fields = [
            'id', 'payment_number',
            'invoice', 'invoice_number', 'student_name',
            'amount_paid', 'payment_method', 'payment_method_display',
            'transaction_reference', 'payment_date', 'remarks',
            'received_by', 'received_by_username',
        ]
        read_only_fields = ['id', 'payment_number', 'payment_date']


class PaymentCreateSerializer(serializers.Serializer):
    invoice_id            = serializers.IntegerField()
    amount_paid           = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method        = serializers.ChoiceField(choices=Payment.PaymentMethod.choices)
    transaction_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    remarks               = serializers.CharField(required=False, allow_blank=True)


class ExpenditureSerializer(serializers.ModelSerializer):
    category_display       = serializers.CharField(source='get_category_display',       read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    approved_by_username   = serializers.CharField(
        source='approved_by.username',      read_only=True, allow_null=True
    )
    processed_by_username  = serializers.CharField(
        source='processed_by.username',     read_only=True, allow_null=True
    )
    staff_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    date       = serializers.DateField(source='transaction_date', read_only=True)

    class Meta:
        model  = Expenditure
        fields = [
            'id', 'expenditure_number', 'item_name',
            'category', 'category_display',
            'amount', 'vendor_name', 'date', 'staff_name',
            'description', 'receipt_url', 'created_at',
            'approved_by_username', 'processed_by_username',
            'payment_method_display',
        ]


class FinancialSummarySerializer(serializers.Serializer):
    total_revenue     = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_expenditure = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_income        = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    outstanding_fees  = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    paid_invoices     = serializers.IntegerField(read_only=True)
    unpaid_invoices   = serializers.IntegerField(read_only=True)
    partial_invoices  = serializers.IntegerField(read_only=True)