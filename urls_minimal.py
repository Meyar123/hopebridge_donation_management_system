from django.http import HttpResponse
from django.urls import path

# Ultra-simple test view for root path
def simple_welcome(request):
    return HttpResponse("Hello World! HopeBridge is working!", content_type="text/plain")

# Health check endpoint for Railway
def health_check(request):
    return HttpResponse("OK", status=200)

# Minimal URL patterns
urlpatterns = [
    path('', simple_welcome, name='welcome'),
    path('health/', health_check, name='health_check'),
]
