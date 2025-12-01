#!/usr/bin/env bash
set -euo pipefail

# Install a crontab entry to start AgriTroller on reboot using scripts/stat.sh start.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAT_SCRIPT="${PROJECT_ROOT}/scripts/stat.sh"
LOG_FILE=${AGRITROLLER_CRON_LOG:-"${HOME}/.agritroller/cron.log"}
HOST=${AGRITROLLER_HOST:-0.0.0.0}
PORT=${AGRITROLLER_PORT:-8080}
ENV_NAME=${AGRITROLLER_ENV:-production}
LOG_LEVEL=${AGRITROLLER_LOG_LEVEL:-INFO}

if [[ ! -x "${STAT_SCRIPT}" ]]; then
  echo "[!] ${STAT_SCRIPT} not found or not executable" >&2
  exit 1
fi

mkdir -p "$(dirname "${LOG_FILE}")"

CRON_MARKER="# AGRITROLLER_STAT_START"
CRON_CMD="cd ${PROJECT_ROOT} && AGRITROLLER_ENV=${ENV_NAME} AGRITROLLER_HOST=${HOST} AGRITROLLER_PORT=${PORT} AGRITROLLER_LOG_LEVEL=${LOG_LEVEL} /bin/bash ${STAT_SCRIPT} start >> ${LOG_FILE} 2>&1"
CRON_LINE="@reboot ${CRON_CMD} ${CRON_MARKER}"

existing_cron=$(crontab -l 2>/dev/null || true)

if echo "${existing_cron}" | grep -F "${CRON_MARKER}" >/dev/null 2>&1; then
  echo "[=] Crontab entry already present; refreshing it"
  existing_cron=$(echo "${existing_cron}" | grep -v "${CRON_MARKER}")
fi

printf "%s\n%s\n" "${existing_cron}" "${CRON_LINE}" | crontab -

echo "[+] Installed @reboot crontab to launch AgriTroller"
echo "    Host: ${HOST}, Port: ${PORT}, Log: ${LOG_FILE}"
