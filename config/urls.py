from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# Import views
from apps.accounts.views import UserViewSet, LoginView, RefreshTokenView, LogoutView, CurrentUserView, health_check
from apps.staff.views import (
    StaffViewSet, SalaryStructureViewSet, SalaryPaymentViewSet,
    StaffAttendanceViewSet, LeaveRequestViewSet
)
from apps.students.views import StudentViewSet, ParentViewSet, StudentParentViewSet
from apps.academic.views import (
    AcademicYearViewSet, SubjectViewSet, ClassViewSet,
    EnrollmentViewSet, SubjectAssignmentViewSet
)
from apps.grades.views import GradeViewSet
from apps.attendance.views import AttendanceViewSet
from apps.finance.views import (
    FeeStructureViewSet, InvoiceViewSet, PaymentViewSet,
    ExpenditureViewSet, FinancialDashboardViewSet
)
from apps.timetable.views import TimetableViewSet

# Create router
router = routers.DefaultRouter()

# Register viewsets
router.register(r'users', UserViewSet, basename='user')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'salary-structures', SalaryStructureViewSet, basename='salary-structure')
router.register(r'salary-payments', SalaryPaymentViewSet, basename='salary-payment')
router.register(r'staff-attendance', StaffAttendanceViewSet, basename='staff-attendance')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'parents', ParentViewSet, basename='parent')
router.register(r'student-parents', StudentParentViewSet, basename='student-parent')
router.register(r'academic-years', AcademicYearViewSet, basename='academic-year')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'subject-assignments', SubjectAssignmentViewSet, basename='subject-assignment')
router.register(r'grades', GradeViewSet, basename='grade')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'fee-structures', FeeStructureViewSet, basename='fee-structure')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'expenditures', ExpenditureViewSet, basename='expenditure')
router.register(r'financial-dashboard', FinancialDashboardViewSet, basename='financial-dashboard')
router.register(r'timetable', TimetableViewSet, basename='timetable')
# router.register(r'syllabus', SyllabusViewSet, basename='syllabus')

urlpatterns = [
    # Root endpoint
    path('', lambda r: JsonResponse({
        'service': 'School Management System API',
        'version': '1.0.0',
        'status': 'running',
        'docs': '/api/docs/',
        'api': '/api/'
    })),
    
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Health check
    path('health/', health_check, name='health-check'),
    
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication endpoints
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh', RefreshTokenView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    
    # API routes
    path('', include(router.urls)),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)