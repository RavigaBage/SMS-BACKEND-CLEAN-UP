from apps.academic.models import Enrollment
from apps.studentManager.models import StudentProgression
from django.utils import timezone
class ProgressionService:
    @staticmethod
    def handle_new_enrollment(enrollment: Enrollment):
        """Called after every successful manual or system enrollment"""
        final_statuses = {'promoted', 'demoted', 'graduated', 'withheld'}
        if enrollment.status != Enrollment.EnrollmentStatus.ACTIVE:
            return

        try:

            progression = StudentProgression.objects.get(
                student=enrollment.student,
                academic_year=enrollment.academic_year
            )

            
            if progression.status in final_statuses and progression.enrollment_applied:
                progression.status = 'pending'
                progression.to_class = enrollment.class_obj.class_name
                progression.enrollment_applied = False
                progression.remarks = f"Reset to pending due to manual re-enrollment on {timezone.now().date()}"
                progression.save()
        except StudentProgression.DoesNotExist:
            StudentProgression.objects.create(
                student=enrollment.student,
                academic_year=enrollment.academic_year,
                from_class=enrollment.class_obj.class_name,
                status='pending',
            )
