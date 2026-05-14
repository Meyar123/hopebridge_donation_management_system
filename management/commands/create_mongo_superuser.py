"""
Django management command to create a MongoDB superuser
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from mongo_utils import connect_to_mongodb, get_mongodb_connection
from mongo_models import User as MongoUser
from datetime import datetime

class Command(BaseCommand):
    help = 'Create a MongoDB superuser for admin access'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Superuser email', default='admin@example.com')
        parser.add_argument('--name', type=str, help='Superuser name', default='Admin User')
        parser.add_argument('--password', type=str, help='Superuser password', default='admin123')
        parser.add_argument('--phone', type=str, help='Superuser phone', default='1234567890')

    def handle(self, *args, **options):
        # Ensure MongoDB connection
        connect_to_mongodb()
        
        if not get_mongodb_connection():
            self.stdout.write(
                self.style.ERROR('Failed to connect to MongoDB. Please check your MongoDB connection.')
            )
            return

        email = options['email']
        name = options['name']
        password = options['password']
        phone = options['phone']

        # Check if user already exists
        existing_user = MongoUser.objects(email=email).first()
        if existing_user:
            self.stdout.write(
                self.style.WARNING(f'User with email {email} already exists.')
            )
            return

        # Create superuser
        try:
            superuser = MongoUser(
                email=email,
                name=name,
                phone=phone,
                password_hash=make_password(password),
                is_active=True,
                is_staff=True,
                is_superuser=True,
                date_joined=datetime.utcnow()
            )
            superuser.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created MongoDB superuser:\n'
                    f'Email: {email}\n'
                    f'Name: {name}\n'
                    f'Password: {password}\n'
                    f'Access admin at: http://localhost:8000/admin/'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
