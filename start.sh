#!/bin/bash
source .env
exec gunicorn --bind 0.0.0.0:2100 run:app
