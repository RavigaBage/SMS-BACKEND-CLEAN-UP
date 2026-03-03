from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
import logging

from apps.students.models import Student,StudentAttendance
from apps.staff.models import Staff,StaffAttendance
from apps.finance.models import Payment

logger = logging.getLogger(__name__)


class DashboardSummary(APIView):

    def get(self, request):

        try:
            
            try:
                student_count = Student.objects.count()
                staff_count = Staff.objects.count()
                total_fees = Payment.objects.aggregate(
                    Sum('amount_paid')
                )['amount_paid__sum'] or 0

            except Exception as e:
                logger.error(f"Error fetching counts: {str(e)}", exc_info=True)
                raise e
            

            try:
                today = timezone.now().date()
                
                total_students = Student.objects.count()
                present_students = StudentAttendance.objects.filter(
                    attendance_date=today,
                    status__in=['present', 'half_day']
                ).count()

                total_staff = Staff.objects.count()
                present_staff = StaffAttendance.objects.filter(
                    attendance_date=today,
                    status__in=['present', 'half_day']
                ).count()

                total_people = total_students + total_staff
                total_present = present_students + present_staff

                if total_people > 0:
                    active_attendance_pct = round((total_present / total_people) * 100, 1)
                else:
                    active_attendance_pct = 0.0

            except Exception as e:
                logger.error(f"Error calculating attendance: {str(e)}")
                active_attendance_pct = 0.0


            try:
                recent_payments = (
                    Payment.objects
                    .select_related('invoice__student')
                    .order_by('-payment_date')[:5]
                )

                transactions = []
                for p in recent_payments:
                    transactions.append({
                        "id": p.id,
                        "student_name": f"{p.invoice.student.first_name} {p.invoice.student.last_name}",
                        "transaction_reference": p.transaction_reference,
                        "amount_paid": float(p.amount_paid),
                        "payment_method": p.payment_method,
                        "payment_date": p.payment_date
                    })

            except Exception as e:
                logger.error(f"Error fetching transactions: {str(e)}", exc_info=True)
                raise e


            try:
                latest_staff = Staff.objects.order_by('-created_at')[:3]
                latest_students = Student.objects.order_by('-created_at')[:3]

                activities = []

                for s in latest_staff:
                    activities.append({
                        "id": f"staff-{s.id}",
                        "text": f"New staff added: {s.first_name} {s.last_name}",
                        "category": "staff",
                        "time": s.created_at
                    })

                for st in latest_students:
                    activities.append({
                        "id": f"stud-{st.id}",
                        "text": f"Student enrolled: {st.first_name} {st.last_name}",
                        "category": "academic",
                        "time": st.created_at
                    })

                activities.sort(key=lambda x: x['time'], reverse=True)

            except Exception as e:
                logger.error(f"Error fetching activities: {str(e)}", exc_info=True)
                raise e

            try:
                monthly_revenue = (
                    Payment.objects
                    .annotate(month=TruncMonth('payment_date'))
                    .values('month')
                    .annotate(total=Sum('amount_paid'))
                    .order_by('month')[:6]
                )

                chart_labels = [
                    d['month'].strftime('%b') for d in monthly_revenue if d['month']
                ]
                chart_values = [
                    float(d['total']) for d in monthly_revenue if d['total']
                ]

            except Exception as e:
                logger.error(f"Error generating chart data: {str(e)}", exc_info=True)
                raise e

            return Response({
                "student_count": student_count,
                "staff_count": staff_count,
                "active_attendance": active_attendance_pct,
                "fees_collected": float(total_fees),
                "recent_transactions": transactions,
                "recent_activities": activities[:5],
                "chart_data": {
                    "labels": chart_labels,
                    "values": chart_values
                }
            })

        except (DRFValidationError, ValidationError) as e:
            logger.error(f"Validation error loading dashboard: {str(e)}")

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
            logger.error(f"Integrity error loading dashboard: {str(e)}")

            error_detail = 'Database constraint violated while generating dashboard.'

            return Response(
                {
                    'error': f'Database Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error loading dashboard: {str(e)}", exc_info=True)

            error_detail = (
                str(e) if str(e)
                else 'An unexpected error occurred while loading dashboard summary.'
            )

            return Response(
                {
                    'error': f'Server Error: {error_detail}',
                    'detail': error_detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )

