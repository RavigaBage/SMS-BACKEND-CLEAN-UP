from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123')
        role = os.environ.get('DJANGO_SUPERUSER_ROLE', User.Role.ADMIN) 

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role=role
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" with role "{role}" created successfully'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists'))