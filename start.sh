#!/bin/bash
# Start Gunicorn processes
echo "Starting Gunicorn."
exec gunicorn run:app \
  --bind 0.0.0.0:2121 \
  --workers 3