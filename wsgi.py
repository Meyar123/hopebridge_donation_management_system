import os
from django.core.wsgi import get_wsgi_application

# Use production settings if in production environment
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()