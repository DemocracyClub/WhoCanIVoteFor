#!/usr/bin/env bash
set -xeE pipefail

cd /var/www/wcivf/code/
uv sync --group deploy
