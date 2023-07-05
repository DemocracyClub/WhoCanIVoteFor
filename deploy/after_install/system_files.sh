#!/usr/bin/env bash
set -xeE

set -a
source /var/www/wcivf/code/.env
INSTANCE_ID=$(curl http://instance-data/latest/meta-data/instance-id)
set +a

SYSTEMD_SRC="${PROJECT_ROOT}/code/deploy/files/systemd"
SYSTEMD_DST="/etc/systemd/system"
CONF_SRC="${PROJECT_ROOT}/code/deploy/files/conf"

# ----------
# cloudwatch config
# ----------
envsubst '$INSTANCE_ID=$(curl http://instance-data/latest/meta-data/instance-id)' < "$CONF_SRC"/cloudwatch.json > /root/.cloudwatch.json
envsubst  '$PROJECT_NAME $PROJECT_ROOT $APP_NAME' < "$SYSTEMD_SRC"/cloudwatch.service > ${SYSTEMD_DST}/"$PROJECT_NAME"_cloudwatch.service
chmod 0644 /root/.cloudwatch.json
systemctl enable "$PROJECT_NAME"_cloudwatch.service
systemctl start "$PROJECT_NAME"_cloudwatch.service


# -------
# Scripts
# -------
for script in "$PROJECT_ROOT"/code/deploy/files/scripts/*.sh; do
  script_name=$(basename "$script")
  # shellcheck disable=SC2016
  envsubst '$PROJECT_NAME $PROJECT_ROOT' < "$script" > "$PROJECT_ROOT"/"$script_name"
  chmod 755 "$PROJECT_ROOT"/"$script_name"
done

# -------------
# Service files
# -------------
for service in "$SYSTEMD_SRC"/*.service; do
  service_name="$PROJECT_NAME"_$(basename "$service")
  # shellcheck disable=SC2016
  envsubst '$PROJECT_NAME $PROJECT_ROOT $APP_NAME' < "$service" > ${SYSTEMD_DST}/"$service_name"
done

# ------
# bashrc
# ------
echo 'cd && cd ../code && source venv/bin/activate' > "$PROJECT_ROOT"/home/.bashrc

# --------------------
# replication log file
# --------------------
mkdir -p /var/log/db_replication && chmod 0777 /var/log/db_replication
touch /var/log/db_replication/logs.log && chmod 0777 /var/log/db_replication/logs.log
