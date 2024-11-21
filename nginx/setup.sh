#!/bin/bash

gunicorn django.wsgi:application --bind 0.0.0.0:8000 --certfile "/etc/ssl/certs/cert.pem" --keyfile "/etc/ssl/certs/key.pem" --workers 4 --timeout 300 
