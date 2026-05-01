from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django.db.models import Sum, Q, Count
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from datetime import datetime, timedelta
from .models import FeeStructure, Invoice, InvoiceItem, Payment, Expenditure
from .serializers import (
    FeeStructureSerializer, InvoiceSerializer, InvoiceItemSerializer,
    PaymentSerializer, PaymentCreateSerializer, ExpenditureSerializer,
    FinancialSummarySerializer
)
from apps.staff.models import Staff
from .services import InvoiceService, PaymentService
from apps.accounts.permissions import CanManageFinance
from drf_spectacular.utils import extend_schema, OpenApiParameter
import logging
import uuid
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class FeeStructureViewSet(viewsets.ModelViewSet):
    """ViewSet for FeeStructure management"""
    
    queryset = FeeStructure.objects.select_related('class_obj').all()
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        academic_year = self.request.query_params.get('academic_year', None)
        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)
                
        class_id = self.request.query_params.get('class_id', None)
        if class_id:
            queryset = queryset.filter(Q(class_obj_id=class_id) | Q(class_obj__isnull=True))
        
        term = self.request.query_params.get('term', None)
        if term:
            queryset = queryset.filter(Q(term=term) | Q(term='all'))
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create fee structure with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating fee structure: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating fee structure: {str(e)}")
            error_detail = 'Fee structure already exists for this class and term or database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating fee structure: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the fee structure.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Update fee structure with exception handling"""
        try:
            return super().update(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error updating fee structure: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error updating fee structure: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error updating fee structure: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while updating the fee structure.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateInvoiceView(APIView):
    def post(self, request):
        service = InvoiceService()
        try:
            invoice = service.generate_invoice_for_student(
                student_id=request.data.get('student_id'),
                academic_year=request.data.get('academic_year'),
                term=request.data.get('term'),
                generated_by=request.user,
                due_days=request.data.get('due_days', 30)
            )
        except (DRFValidationError, ValidationError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice management"""
    
    queryset = Invoice.objects.select_related('student','generated_by').prefetch_related('items').all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]
    
    def get_queryset(self):
        queryset = super().get_queryset()

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        academic_year = self.request.query_params.get('academic_year')
        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)

        term = self.request.query_params.get('term')
        if term:
            queryset = queryset.filter(term=term)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        class_id = self.request.query_params.get('class_id')
        if class_id:
            from apps.academic.models import Enrollment
            student_ids = Enrollment.objects.filter(
                class_obj_id=class_id,
                status=Enrollment.EnrollmentStatus.ACTIVE,
            ).values_list('student_id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)

        overdue = self.request.query_params.get('overdue')
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                due_date__lt=datetime.now().date(),
                status__in=['unpaid', 'partial']
            )

        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate invoice for a student"""
        try:
            student_id = request.data.get('student_id')
            academic_year_id = request.data.get('academic_year_id')
            term = request.data.get('term')
            due_days = request.data.get('due_days', 30)
            
            if not all([student_id, academic_year_id, term]):
                error_detail = 'student_id, academic_year_id, and term are required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = InvoiceService()
            invoice = service.generate_invoice_for_student(
                student_id=student_id,
                academic_year_id=academic_year_id,
                term=term,
                generated_by=request.user,
                due_days=due_days
            )
            
            
            serializer = InvoiceSerializer(invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error generating invoice: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error generating invoice: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while generating the invoice.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate invoices for all students in a class"""
        try:
            class_id = request.data.get('class_id')
            academic_year_id = request.data.get('academic_year_id')
            term = request.data.get('term')
            
            if not all([class_id, academic_year_id, term]):
                error_detail = 'class_id, academic_year_id, and term are required'
                return Response(
                    {
                        'error': f'Validation Error: {error_detail}',
                        'detail': error_detail
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = InvoiceService()
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
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error bulk generating invoices: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error bulk generating invoices: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while bulk generating invoices.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def save(self, *args, **kwargs):
        if self.total_amount is None:
            raise ValueError("total_amount must be set before saving an Invoice.")
        
        self.balance = self.total_amount - self.amount_paid

        if self.amount_paid >= self.total_amount:
            self.status = self.InvoiceStatus.PAID
        elif self.amount_paid > 0:
            self.status = self.InvoiceStatus.PARTIAL

        if not self.invoice_number:
            while True:
                number = str(uuid.uuid4())[:8].upper()
                if not Invoice.objects.filter(invoice_number=number).exists():
                    self.invoice_number = number
                    break

        super().save(*args, **kwargs)

    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for an invoice"""
        try:
            invoice = self.get_object()
            service = PaymentService()
            payments = service.get_payment_history(invoice.id)
            serializer = PaymentSerializer(payments, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving payment history for invoice {pk}: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving payment history.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(invoice__student__first_name__icontains=search) |
                Q(invoice__student__last_name__icontains=search) |
                Q(invoice__invoice_number__icontains=search) |
                Q(payment_number__icontains=search)
            )

        student_id = params.get("student_id")
        if student_id:
            queryset = queryset.filter(invoice__student_id=student_id)

        payment_method = params.get("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        month = params.get("month")
        if month:
            year, month = month.split("-")
            queryset = queryset.filter(
                payment_date__year=year,
                payment_date__month=month
            )

        start_date = params.get("start_date")
        end_date = params.get("end_date")
        if start_date and end_date:
            queryset = queryset.filter(payment_date__date__range=[start_date, end_date])

        return queryset.order_by("-payment_date")

    def create(self, request, *args, **kwargs):
        """Record a payment with exception handling"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = PaymentService()
            payment = service.record_payment(
                invoice_id=serializer.validated_data['invoice_id'],
                amount_paid=serializer.validated_data['amount_paid'],
                payment_method=serializer.validated_data['payment_method'],
                transaction_reference=serializer.validated_data.get('transaction_reference', ''),
                received_by=request.user
            )
            
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error recording payment: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error recording payment: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error recording payment: {str(e)}", exc_info=True)
            error_detail = str(e) if str(e) else 'An unexpected error occurred while recording the payment.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def daily_collection(self, request):
        """Get daily collection summary"""
        try:
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
            
        except Exception as e:
            logger.error(f"Error retrieving daily collection: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving daily collection.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExpenditureViewSet(viewsets.ModelViewSet):
    """ViewSet for Expenditure management"""
    
    queryset = Expenditure.objects.select_related('approved_by', 'processed_by').all()
    serializer_class = ExpenditureSerializer
    permission_classes = [IsAuthenticated, CanManageFinance]
    filter_backends = [SearchFilter]
    search_fields = ['item_name', 'vendor_name', 'description']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(transaction_date__range=[start_date, end_date])
        
        return queryset.order_by('-transaction_date')
    
    def create(self, request, *args, **kwargs):
        """Create expenditure with exception handling"""
        try:
            return super().create(request, *args, **kwargs)
            
        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error creating expenditure: {str(e)}")
            
            if hasattr(e, 'message_dict'):
                error_detail = e.message_dict
            elif hasattr(e, 'messages'):
                error_detail = e.messages[0] if e.messages else str(e)
            else:
                error_detail = str(e)
            
            return Response(
                {
                    'error': f'Validation Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating expenditure: {str(e)}")
            error_detail = 'Database constraint violated.'
            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error creating expenditure: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while creating the expenditure.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
   
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

        try:
            staff = Staff.objects.get(user=self.request.user)
        except Staff.DoesNotExist:
            staff = None

        serializer.save(
            expenditure_number=expenditure_number,
            processed_by=staff         
        )

        serializer.save(
            expenditure_number=expenditure_number,
            processed_by=staff
        )

    @action(detail=False, methods=['get'])
    def category_summary(self, request):
        """Get expenditure summary by category"""
        try:
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
            
        except Exception as e:
            logger.error(f"Error retrieving category summary: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving category summary.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FinancialDashboardViewSet(viewsets.ViewSet):
    """ViewSet for financial dashboard and reports"""
    
    permission_classes = [IsAuthenticated, CanManageFinance]
    serializer_class = FinancialSummarySerializer
    
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
        """Get financial summary with exception handling"""
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                today = datetime.now().date()
                start_date = today.replace(day=1)
                end_date = today
            
            payments = Payment.objects.filter(
                payment_date__range=[start_date, end_date]
            )
            total_revenue = payments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
            
            expenditures = Expenditure.objects.filter(
                transaction_date__range=[start_date, end_date]
            )
            total_expenditure = expenditures.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            outstanding_invoices = Invoice.objects.filter(
                status__in=['unpaid', 'partial']
            )
            outstanding_fees = outstanding_invoices.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
            
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
            
        except Exception as e:
            logger.error(f"Error retrieving financial summary: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving financial summary.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def monthly_trends(self, request):
        """Get monthly financial trends for the year"""
        try:
            year = int(request.query_params.get('year', datetime.now().year))
            
            monthly_data = []
            
            for month in range(1, 13):
                month_start = datetime(year, month, 1).date()
                if month == 12:
                    month_end = datetime(year, 12, 31).date()
                else:
                    month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
                
                revenue = Payment.objects.filter(
                    payment_date__range=[month_start, month_end]
                ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
                
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
            
        except Exception as e:
            logger.error(f"Error retrieving monthly trends: {str(e)}", exc_info=True)
            error_detail = 'An unexpected error occurred while retrieving monthly trends.'
            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
