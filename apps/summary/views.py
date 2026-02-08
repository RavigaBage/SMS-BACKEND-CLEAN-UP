from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from django.db.models.functions import TruncMonth


from apps.students.models import Student
from apps.staff.models import Staff
from apps.finance.models import Payment

class DashboardSummary(APIView):
    def get(self, request):
        student_count = Student.objects.count()
        staff_count = Staff.objects.count()
        total_fees = Payment.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

        recent_payments = Payment.objects.select_related('invoice').order_by('-payment_date')[:5]
        
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

        monthly_revenue = (
            Payment.objects
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('amount_paid'))
            .order_by('month')[:6]
        )

        chart_labels = [d['month'].strftime('%b') for d in monthly_revenue]
        chart_values = [float(d['total']) for d in monthly_revenue]

        return Response({
            "student_count": student_count,
            "staff_count": staff_count,
            "active_attendance": 94.2,
            "fees_collected": float(total_fees),
            "recent_transactions": transactions,
            "recent_activities": activities[:5],
            "chart_data": {
                "labels": chart_labels,
                "values": chart_values
            }
        })