#!/bin/bash
set -e

echo "Waiting for MySQL..."
./scripts/wait-for-db.sh

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"