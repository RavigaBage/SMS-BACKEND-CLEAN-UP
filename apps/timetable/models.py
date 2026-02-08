from django.db import models
from django.core.exceptions import ValidationError
from apps.academic.models import Class, Subject
from apps.teachers.models import Teacher

class Timetable(models.Model):
    class Day(models.TextChoices):
        MONDAY = "Monday"
        TUESDAY = "Tuesday"
        WEDNESDAY = "Wednesday"
        THURSDAY = "Thursday"
        FRIDAY = "Friday"

    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="timetables", db_column="class_id"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="timetables"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="timetables",null=True,
        blank=True
    )
    term = models.CharField(max_length=50, blank=True, default='')
    academic_year = models.CharField(max_length=50, blank=True, default='')
    day_of_week = models.CharField(max_length=10, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=20)

    class Meta:
        db_table = "timetable"
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'day_of_week', 'start_time', 'end_time', 'term', 'academic_year'],
                name='unique_teacher_schedule'
            )
        ]

    def __str__(self):
        return f"{self.class_obj} - {self.subject} ({self.day_of_week})"

    def clean(self):
        # Validate start time < end time
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # Check for teacher scheduling conflicts
        clash = Timetable.objects.filter(
            teacher=self.teacher,
            day_of_week=self.day_of_week,
            term=self.term,
            academic_year=self.academic_year,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        
        if self.pk:
            clash = clash.exclude(pk=self.pk)
        
        if clash.exists():
            raise ValidationError(
                f"Teacher {self.teacher} already has a class scheduled during this time."
            )

class Syllabus(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="syllabi")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="syllabi")
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="syllabi",null=True,blank=True)
    week_number = models.IntegerField()
    topic_title = models.CharField(max_length=255)
    content_summary = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)

    class Meta:
        db_table = "syllabus"
        verbose_name_plural = "syllabi"

    def __str__(self):
        return f"Week {self.week_number}: {self.topic_title}"
