#!/bin/sh
set -e

# Apply database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn warehouse_project.wsgi:application --bind 0.0.0.0:8000 --workers 3 --worker-tmp-dir /tmp
