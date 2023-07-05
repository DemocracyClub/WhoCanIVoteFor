#!/bin/bash
set -xeEo pipefail

set -a
source /var/www/wcivf/code/.env
set +a

# rotate the log file otherwise output is lost in cloudwatch
echo "" > /var/log/db_replication/logs.log

USER=${PROJECT_NAME}
DB=${PROJECT_NAME}
INSTANCE_ID=$(curl http://instance-data/latest/meta-data/instance-id)
SUBSCRIPTION=${USER}_${INSTANCE_ID:2}

# Set up DB and enable PostGIS
dropdb --if-exists "$DB" -U "$USER"
createdb "$DB" -U "$USER"
psql "$DB" -U "$USER" -c 'create extension postgis;'


# Activate Virtual env
source /var/www/wcivf/venv/bin/activate

# Migrate db - this builds the schema before syncing
IGNORE_ROUTERS=True /var/www/wcivf/code/manage.py migrate --run-syncdb
IGNORE_ROUTERS=True /var/www/wcivf/code/manage.py truncate_replicated_tables



# Truncate some tables that are populated by the above steps
psql "$DB" -U "$USER" -c 'TRUNCATE "spatial_ref_sys", "auth_permission", "django_migrations", "django_content_type", "django_site" RESTART IDENTITY CASCADE;'
psql "$DB" -U "$USER" -c 'alter table elections_votingsystem drop constraint elections_votingsystem_pkey cascade;'
psql "$DB" -U "$USER" -c 'TRUNCATE elections_votingsystem RESTART IDENTITY CASCADE;'

# Set up subscription
psql "$DB" -U "$USER" -c "CREATE SUBSCRIPTION $SUBSCRIPTION CONNECTION 'dbname=$RDS_DB_NAME host=$RDS_HOST user=wcivf password=$RDS_DB_PASSWORD' PUBLICATION alltables with (streaming=true, binary=true);"

# Wait for all tables to finish initial sync
echo "starting initial db sync"
WORKER_STATS=("not-set")

COUNTER=0
while [ "${WORKER_STATS[0]}" !=  "r" ]
do
    COUNTER=$((COUNTER+1))
    WORKER_STATS=$(psql wcivf -U wcivf -AXqtc "select distinct srsubstate from pg_subscription_rel;")
    sleep 15
    # 20 here is 5 minutes. If it's working, everything should be finished
    # by then.
    if [ $COUNTER -gt 19 ]; then
      COUNTER=0
      psql "$DB" -U "$DB_USER" -c "DROP SUBSCRIPTION $SUBSCRIPTION;"
      psql "$DB" -U "$USER" -c "CREATE SUBSCRIPTION $SUBSCRIPTION CONNECTION 'dbname=$RDS_DB_NAME host=$RDS_HOST user=wcivf password=$RDS_DB_PASSWORD' PUBLICATION alltables with (streaming=true, binary=true);"
    fi
    COUNTER=$((COUNTER+1))

done

psql "$DB" -U "$USER" -c 'ALTER TABLE elections_votingsystem ADD PRIMARY KEY (slug);'

echo "initial db sync complete"

rm -f /var/www/wcivf/home/server_dirty
