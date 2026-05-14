#!/bin/bash
# Startup script for Railway deployment

# Activate virtual environment
source /opt/venv/bin/activate

# Set environment variables
export DJANGO_SETTINGS_MODULE=settings_production

# Create logs directory
mkdir -p /app/logs

# Run database migrations (ignore errors for now)
python manage.py migrate --settings=settings_production || echo "Migration failed, continuing..."

# Collect static files (ignore errors for now)
python manage.py collectstatic --noinput --settings=settings_production || echo "Static collection failed, continuing..."

# Start the application
echo "PORT variable: $PORT"
echo "Starting Gunicorn on port $PORT..."
echo "Starting with 1 worker to test..."
image.png
# Test Django import first
echo "Testing Django import..."
python -c "import django; print('Django import successful')" || echo "Django import failed"

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --log-level debug wsgi:application
