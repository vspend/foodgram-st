#!/bin/bash

echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready!"

echo "Running migrations..."
python manage.py migrate

echo "Loading ingredients..."
python manage.py load_ingredients

echo "Starting server..."
exec gunicorn --bind 0.0.0.0:8000 foodgram.wsgi 