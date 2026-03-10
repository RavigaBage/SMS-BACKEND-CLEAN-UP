from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.core.exceptions import ValidationError
from apps.students.models import Student
from apps.academic.models import Class, Enrollment

User = get_user_model()

FINAL_STATUSES = {'promoted', 'demoted', 'graduated', 'withheld'}


class StudentProgression(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('promoted', 'Promoted'),
        ('demoted', 'Demoted'),
        ('graduated', 'Graduated'),
        ('withheld', 'Withheld'),
    ]

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='progressions',
    )
    academic_year = models.CharField(max_length=20)
    from_class = models.CharField(max_length=50)
    to_class = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    enrollment_applied = models.BooleanField(
        default=False,
        help_text='True once apply_to_enrollment() has been successfully run.',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='progression_updates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'academic_year','from_class')
        ordering = ['-academic_year']

    def __str__(self):
        return f"{self.student} | {self.academic_year} | {self.status}"

    def apply_to_enrollment(self):
        """
        Apply final progression status to enrollment records.

        Behaviour:
        promoted  -> close current active enrollment, open in to_class
        demoted   -> close current active enrollment, open in to_class
        withheld  -> close current active enrollment, re-open in from_class
        graduated -> close current active enrollment, no new enrollment
        """
        if self.status not in FINAL_STATUSES:
            raise ValueError(
                f"apply_to_enrollment() called with non-final status '{self.status}'."
            )

        if self.enrollment_applied:
            raise ValueError(
                'Enrollment transition has already been applied for this progression record.'
            )

        with transaction.atomic():
            Enrollment.objects.filter(
                student=self.student,
                status=Enrollment.EnrollmentStatus.ACTIVE,
            ).update(status=Enrollment.EnrollmentStatus.COMPLETED)

            if self.status != 'graduated':
                target_class_name = (
                    self.to_class if self.status in ('promoted', 'demoted') else self.from_class
                )

                if not target_class_name:
                    raise ValueError('Target class is required for this progression status.')

                try:
                    new_class = Class.objects.get(class_name=target_class_name)
                except Class.DoesNotExist:
                    raise ValueError(
                        f"Class '{target_class_name}' not found. "
                        'Make sure to_class/from_class matches an existing Class record.'
                    )

                if new_class.current_enrollment >= new_class.capacity:
                    raise ValueError(f"Class '{new_class.class_name}' is at full capacity.")

                enrollment, created = Enrollment.objects.update_or_create(
                    student=self.student,
                    class_obj=new_class,
                    defaults={
                        'academic_year': self.academic_year,
                        'status': Enrollment.EnrollmentStatus.ACTIVE,
                    },
                )

                self.student.class_obj = new_class
                self.student.save(update_fields=['class_obj'])

            else:
                self.student.class_obj = None
                self.student.save(update_fields=['class_obj'])

            self.enrollment_applied = True
            self.save(update_fields=['enrollment_applied'])

            if self.status in ('promoted', 'demoted') and self.to_class:
                StudentProgression.objects.update_or_create(
                    student=self.student,
                    academic_year=self.academic_year,
                    from_class=self.to_class,  
                    defaults={
                        'to_class': None,    
                        'status': 'pending', 
                        'enrollment_applied': False, 
                        'remarks': None,  
                        'updated_by': self.updated_by,
                    },
                )