from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.grades.models import Grade
from .Utils import GradeCalculator


@receiver(pre_save, sender=Grade)
def calculate_grade_values(sender, instance, **kwargs):
    """
    Automatically calculate weighted scores, total score, and grade letter
    before saving a Grade instance
    """
    # Calculate weighted scores
    weighted_scores = GradeCalculator.calculate_weighted_scores(instance)
    
    instance.weighted_assessment = weighted_scores['weighted_assessment']
    instance.weighted_test = weighted_scores['weighted_test']
    instance.weighted_exam = weighted_scores['weighted_exam']
    
    # Calculate total score
    instance.total_score = GradeCalculator.calculate_total_score(weighted_scores)
    
    # Assign grade letter
    instance.grade_letter = GradeCalculator.get_grade_letter(float(instance.total_score))


@receiver(post_save, sender=Grade)
def log_grade_change(sender, instance, created, **kwargs):
    """
    Log when grades are created or updated
    You can extend this to send notifications, create audit logs, etc.
    """
    if created:
        print(f"New grade created: {instance.student} - {instance.subject} - {instance.grade_letter}")
    else:
        print(f"Grade updated: {instance.student} - {instance.subject} - {instance.grade_letter}")
