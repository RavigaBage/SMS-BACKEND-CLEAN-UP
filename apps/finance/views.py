from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django.db.models import Sum, Q, Count
from decimal import Decimal
from datetime import datetime, timedelta
from .models import FeeStructure, Invoice, InvoiceItem, Payment, Expenditure
from .serializers import (
    FeeStructureSerializer, InvoiceSerializer, InvoiceItemSerializer,
    PaymentSerializer, PaymentCreateSerializer, ExpenditureSerializer,
    FinancialSummarySerializer
)
from .services import InvoiceService, PaymentService
from apps.accounts.permissions import CanManageFinance
from drf_spectacular.utils import extend_schema, OpenApiParameter


class FeeStructureViewSet(viewsets.ModelViewSet):
    """ViewSet for FeeStructure management"""
    
    queryset = FeeStructure.objects.select_related('academic_year', 'class_obj').all()
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]

    queryset = Expenditure.objects.all().order_by('-transaction_date')
    serializer_class = ExpenditureSerializer
    filter_backends = [SearchFilter]
    search_fields = ['item_name', 'vendor_name', 'description']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by academic year
        academic_year_id = self.request.query_params.get('academic_year_id', None)
        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)
        
        # Filter by class
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(Q(class_obj_id=class_id) | Q(class_obj__isnull=True))
        
        # Filter by term
        term = self.request.query_params.get('term', None)
        if term:
            queryset = queryset.filter(Q(term=term) | Q(term='all'))
        
        return queryset


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice management"""
    
    queryset = Invoice.objects.select_related('student', 'academic_year', 'generated_by').prefetch_related('items').all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by student
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by academic year
        academic_year_id = self.request.query_params.get('academic_year_id', None)
        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)
        
        # Filter by term
        term = self.request.query_params.get('term', None)
        if term:
            queryset = queryset.filter(term=term)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter overdue invoices
        overdue = self.request.query_params.get('overdue', None)
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                due_date__lt=datetime.now().date(),
                status__in=['unpaid', 'partial']
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate invoice for a student"""
        student_id = request.data.get('student_id')
        academic_year_id = request.data.get('academic_year_id')
        term = request.data.get('term')
        due_days = request.data.get('due_days', 30)
        
        if not all([student_id, academic_year_id, term]):
            return Response(
                {'error': 'student_id, academic_year_id, and term are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = InvoiceService()
        try:
            invoice = service.generate_invoice_for_student(
                student_id=student_id,
                academic_year_id=academic_year_id,
                term=term,
                generated_by=request.user,
                due_days=due_days
            )
            
            serializer = InvoiceSerializer(invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate invoices for all students in a class"""
        class_id = request.data.get('class_id')
        academic_year_id = request.data.get('academic_year_id')
        term = request.data.get('term')
        
        if not all([class_id, academic_year_id, term]):
            return Response(
                {'error': 'class_id, academic_year_id, and term are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = InvoiceService()
        try:
            result = service.generate_bulk_invoices(
                class_id=class_id,
                academic_year_id=academic_year_id,
                term=term,
                generated_by=request.user
            )
            
            return Response({
                'success': len(result['invoices']),
                'errors': len(result['errors']),
                'invoices': InvoiceSerializer(result['invoices'], many=True).data,
                'error_details': result['errors']
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for an invoice"""
        invoice = self.get_object()
        service = PaymentService()
        payments = service.get_payment_history(invoice.id)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for Payment management"""
    
    queryset = Payment.objects.select_related('invoice', 'received_by').all()
    permission_classes = [IsAuthenticated, CanManageFinance]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()

        params = self.request.query_params

        # 🔍 Search (student name, invoice number, payment number)
        search = params.get("search")
        if search:
            
            queryset = queryset.filter(
                Q(invoice__student__first_name__icontains=search) |
                Q(invoice__student__last_name__icontains=search) |
                Q(invoice__invoice_number__icontains=search) |
                Q(payment_number__icontains=search)
            )

        # 🎓 Filter by student
        student_id = params.get("student_id")
        if student_id:
            queryset = queryset.filter(invoice__student_id=student_id)

        # 💳 Payment method
        payment_method = params.get("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # 📅 Month filter (YYYY-MM)
        month = params.get("month")
        if month:
            year, month = month.split("-")
            queryset = queryset.filter(
                payment_date__year=year,
                payment_date__month=month
            )

        # 📆 Date range
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        if start_date and end_date:
            queryset = queryset.filter(payment_date__date__range=[start_date, end_date])

        return queryset.order_by("-payment_date")

    def create(self, request, *args, **kwargs):
        """Record a payment"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = PaymentService()
        try:
            payment = service.record_payment(
                invoice_id=serializer.validated_data['invoice_id'],
                amount_paid=serializer.validated_data['amount_paid'],
                payment_method=serializer.validated_data['payment_method'],
                transaction_reference=serializer.validated_data.get('transaction_reference', ''),
                received_by=request.user
            )
            
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def daily_collection(self, request):
        """Get daily collection summary"""
        date = request.query_params.get('date', datetime.now().date())
        
        payments = Payment.objects.filter(
            payment_date__date=date
        )
        
        total_collection = payments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        payment_methods = payments.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount_paid')
        )
        
        return Response({
            'date': date,
            'total_collection': total_collection,
            'total_transactions': payments.count(),
            'by_payment_method': list(payment_methods)
        })


class ExpenditureViewSet(viewsets.ModelViewSet):
    """ViewSet for Expenditure management"""
    
    queryset = Expenditure.objects.select_related('approved_by', 'processed_by').all()
    serializer_class = ExpenditureSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(transaction_date__range=[start_date, end_date])
        
        return queryset
    
    def perform_create(self, serializer):
        # Generate expenditure number
        today = datetime.now()
        date_code = today.strftime('%Y%m%d')
        
        last_expenditure = Expenditure.objects.filter(
            expenditure_number__startswith=f"EXP-{date_code}"
        ).order_by('-expenditure_number').first()
        
        if last_expenditure:
            last_number = int(last_expenditure.expenditure_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
    
        expenditure_number = f"EXP-{date_code}-{new_number:04d}"

        serializer.save(
            expenditure_number=expenditure_number,
            processed_by=self.request.user
        )

    @action(detail=False, methods=['get'])
    def category_summary(self, request):
        """Get expenditure summary by category"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        query = Expenditure.objects.all()

        if start_date and end_date:
            query = query.filter(transaction_date__range=[start_date, end_date])

        category_totals = query.values('category').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        total_expenditure = query.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'total_expenditure': total_expenditure,
            'by_category': list(category_totals)
        })

class FinancialDashboardViewSet(viewsets.ViewSet):
    """ViewSet for financial dashboard and reports"""
    
    permission_classes = [IsAuthenticated, CanManageFinance]
    serializer_class = FinancialSummarySerializer  # Add this line
    
    @extend_schema(
        responses={200: FinancialSummarySerializer},
        parameters=[
            OpenApiParameter(name='start_date', type=str, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=str, description='End date (YYYY-MM-DD)'),
        ],
        description="Get financial summary for a date range"
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get financial summary"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Default to current month
        if not start_date or not end_date:
            today = datetime.now().date()
            start_date = today.replace(day=1)
            end_date = today
        
        # Revenue (payments received)
        payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date]
        )
        total_revenue = payments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        
        # Expenditure
        expenditures = Expenditure.objects.filter(
            transaction_date__range=[start_date, end_date]
        )
        total_expenditure = expenditures.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Outstanding fees
        outstanding_invoices = Invoice.objects.filter(
            status__in=['unpaid', 'partial']
        )
        outstanding_fees = outstanding_invoices.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
        
        # Invoice statistics
        paid_invoices = Invoice.objects.filter(status='paid').count()
        unpaid_invoices = Invoice.objects.filter(status='unpaid').count()
        partial_invoices = Invoice.objects.filter(status='partial').count()
        
        summary_data = {
            'total_revenue': total_revenue,
            'total_expenditure': total_expenditure,
            'net_income': total_revenue - total_expenditure,
            'outstanding_fees': outstanding_fees,
            'paid_invoices': paid_invoices,
            'unpaid_invoices': unpaid_invoices,
            'partial_invoices': partial_invoices,
        }
        
        serializer = FinancialSummarySerializer(summary_data)
        return Response(serializer.data)
    
@action(detail=False, methods=['get'])
def monthly_trends(self, request):
    """Get monthly financial trends for the year"""
    year = int(request.query_params.get('year', datetime.now().year))
    
    monthly_data = []
    
    for month in range(1, 13):
        month_start = datetime(year, month, 1).date()
        if month == 12:
            month_end = datetime(year, 12, 31).date()
        else:
            month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Revenue
        revenue = Payment.objects.filter(
            payment_date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        
        # Expenditure
        expenditure = Expenditure.objects.filter(
            transaction_date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_data.append({
            'month': month,
            'month_name': month_start.strftime('%B'),
            'revenue': float(revenue),
            'expenditure': float(expenditure),
            'net': float(revenue - expenditure)
        })
    
    return Response({
        'year': year,
        'monthly_data': monthly_data
    })