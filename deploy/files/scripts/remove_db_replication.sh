#!/bin/bash
set -xeEo pipefail

set -a
source /var/www/wcivf/code/.env
set +a

# rotate the log file otherwise output is lost in cloudwatch
echo "" > /var/log/db_replication/logs.log

USER=`whoami`
INSTANCE_ID=$(curl http://instance-data/latest/meta-data/instance-id)
SUBSCRIPTION=${USER}_${INSTANCE_ID:2}

drop_subscription () {
    psql -U "$USER" -c "DROP SUBSCRIPTION $SUBSCRIPTION;"
}

# if subscription is active it will fail - repeat until inactive
until drop_subscription; do
    echo "Trying to drop subscription again..."
done

echo "Subscription dropped"
touch "${PROJECT_ROOT}"/home/server_dirty
