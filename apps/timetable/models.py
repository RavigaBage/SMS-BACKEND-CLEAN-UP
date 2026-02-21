from django.db import models
from django.core.exceptions import ValidationError
from apps.academic.models import Class, Subject
from apps.teachers.models import Teacher
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _


class Timetable(models.Model):
    """
    A timetable entry (one class session).
    - class_obj: the Class (FK)
    - subject: the Subject (FK)
    - teacher: the Teacher (FK) — optional
    - term, academic_year: text fields to scope a timetable (e.g. 'Term 1', '2025/2026')
    - day_of_week: one of defined choices
    - start_time / end_time: TimeFields (validated start < end)
    """

    class Day(models.TextChoices):
        MONDAY = "Monday", _("Monday")
        TUESDAY = "Tuesday", _("Tuesday")
        WEDNESDAY = "Wednesday", _("Wednesday")
        THURSDAY = "Thursday", _("Thursday")
        FRIDAY = "Friday", _("Friday")

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="timetables",
        db_column="class_id",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetables",
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="timetables",
        null=True,
        blank=True,
    )

    term = models.CharField(max_length=64, blank=True, default="", db_index=True)
    academic_year = models.CharField(max_length=32, blank=True, default="", db_index=True)

    day_of_week = models.CharField(max_length=10, choices=Day.choices, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "timetable"
        indexes = [
            models.Index(fields=["class_obj", "term", "academic_year"]),
            models.Index(fields=["teacher", "term", "academic_year"]),
            models.Index(fields=["term", "academic_year"]),
        ]
        constraints = [
            # defensive constraint for obvious programming mistakes:
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="timetable_start_before_end",
            ),
            # prevent exact duplicate rows for same class/teacher/time/term/year
            models.UniqueConstraint(
                fields=["class_obj", "subject", "day_of_week", "start_time", "end_time", "term", "academic_year"],
                name="unique_class_subject_exact_timeslot",
            ),
        ]
        verbose_name = "Timetable entry"
        verbose_name_plural = "Timetable entries"

    def __str__(self):
        return f"{self.class_obj} — {self.subject} ({self.day_of_week} {self.start_time}-{self.end_time}) [{self.term} {self.academic_year}]"

    def clean(self):
        """
        Validate:
        - start_time < end_time
        - no overlapping session for same teacher in same term/year
        - no overlapping session for same class in same term/year
        """
        # start / end sanity
        if self.start_time >= self.end_time:
            raise ValidationError({"start_time": "Start time must be before end time."})

        # Build common overlapping filter (same day, overlapping time)
        overlap_q = Q(
            day_of_week=self.day_of_week,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
            term=self.term,
            academic_year=self.academic_year,
        )

        # Exclude self when updating
        base_qs = Timetable.objects.filter(overlap_q)
        if self.pk:
            base_qs = base_qs.exclude(pk=self.pk)

        # Class conflict
        class_conflicts = base_qs.filter(class_obj=self.class_obj)
        if class_conflicts.exists():
            raise ValidationError(
                {"class_obj": "This class already has a session at this time in the selected term/year."}
            )

        # Teacher conflict (only check if teacher is provided)
        if self.teacher:
            teacher_conflicts = base_qs.filter(teacher=self.teacher)
            if teacher_conflicts.exists():
                raise ValidationError(
                    {"teacher": "This teacher is already scheduled at this time in the selected term/year."}
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
