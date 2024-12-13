#!/usr/bin/env bash
set -xeE pipefail

cd /var/www/wcivf/
deploy/files/scripts/install-uv.sh
uv sync --group deploy
