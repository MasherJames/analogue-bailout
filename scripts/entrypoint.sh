#!/usr/bin/env bash


python manage.py makemigrations
python manage.py migrate

#run the app with gunicorn
exec gunicorn backendservice.wsgi:application --bind 0.0.0.0:8000
# start to consume transactions
python3 transactionprocessor.py