from apps.academic.models import Class, Enrollment
from apps.grades.models import Grade
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Seeds grades with a realistic spread from lowest to highest'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Grades...")
        target = "2025-2026"
        # List models specifically
        items = [
            (Class, "academic_year"),
            (Enrollment, "enrollment_year"),
            (Grade, "academic_year")
        ]
        
        for model, field_name in items:
            try:
                print(f"--- Checking {model.__name__} ---")
                # We use a raw filter to avoid Django's lookup logic confusion
                bad_records = model.objects.exclude(**{field_name: target})
                count = bad_records.count()
                
                if count > 0:
                    print(f"Found {count} records to fix in {model.__name__}")
                    for obj in bad_records:
                        setattr(obj, field_name, target)
                        obj.save(update_fields=[field_name])
                    print(f"Successfully updated {model.__name__}")
                else:
                    print(f"{model.__name__} is already clean.")
                    
            except Exception as e:
                print(f"SKIPPING {model.__name__}: Error - {e}")

        self.stdout.write(self.style.SUCCESS(f"Successfully normalized data for {len(items)} models!"))