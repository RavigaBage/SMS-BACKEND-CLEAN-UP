from django.db import models
from apps.accounts.models import User

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    specialization = models.CharField(max_length=100, blank=True)
    
    subjects = models.ManyToManyField('academic.Subject', related_name="teachers", blank=True)

    class Meta:
        db_table = "teachers"
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
