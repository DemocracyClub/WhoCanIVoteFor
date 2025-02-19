#!/usr/bin/env bash
set -xeE

cd /var/www/wcivf/code/
uv run python manage.py compilemessages
