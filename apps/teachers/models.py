from django.db import models
from apps.accounts.models import User

class Teacher(models.Model):
    """
    Teacher model - extends User with teaching-specific information
    Admin can assign specialization and subjects to teachers
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="teacher_profile",
        limit_choices_to={'role': 'teacher'}
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    specialization = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Primary subject or area of expertise (e.g., Mathematics, Science)"
    )
    
    subjects = models.ManyToManyField(
        'academic.Subject', 
        related_name="teachers", 
        blank=True,
        help_text="Subjects this teacher is qualified to teach"
    )
    
    date_joined = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    qualifications = models.TextField(
        blank=True,
        help_text="Educational qualifications (e.g., B.Ed, M.Sc)"
    )
    years_of_experience = models.PositiveIntegerField(
        default=0,
        help_text="Total years of teaching experience"
    )
    
    phone_number = models.CharField(max_length=17, blank=True)
    emergency_contact = models.CharField(max_length=17, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers_assigned",
        help_text="Admin/Headmaster who assigned this teacher"
    )

    class Meta:
        db_table = "teachers"
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        """Return teacher's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def subject_list(self):
        """Return comma-separated list of subjects"""
        return ", ".join([subject.subject_name for subject in self.subjects.all()])
    
    def get_assigned_classes(self):
        """Get all classes where this teacher is the class teacher"""
        from apps.academic.models import Class
        return Class.objects.filter(class_teacher__user=self.user)
    
    def get_subject_assignments(self):
        """Get all subject assignments for this teacher"""
        from apps.academic.models import SubjectAssignment
        return SubjectAssignment.objects.filter(teacher__user=self.user)
    
    def save(self, *args, **kwargs):
        """Override save to sync with user model"""
        if self.user:
            if not self.first_name and self.user.first_name:
                self.first_name = self.user.first_name
            if not self.last_name and self.user.last_name:
                self.last_name = self.user.last_name
        
        super().save(*args, **kwargs)