#!/usr/bin/env bash
set -xeE

cd /var/www/wcivf/code/
uv run python /var/www/wcivf/code/manage.py collectstatic --noinput --clear
