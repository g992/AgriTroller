#!/usr/bin/env bash
set -euo pipefail

# Orchestrator for production setup: install packages, build frontend, set up
# autostart, and launch the app. Tasks are idempotent and report completion
# status; they can be rerun except that the app will not be started twice.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR=${VENV_DIR:-"${PROJECT_ROOT}/.venv"}
PYTHON_BIN=${PYTHON_BIN:-python3}
HOST=${AGRITROLLER_HOST:-0.0.0.0}
PORT=${AGRITROLLER_PORT:-8080}
LOG_LEVEL=${AGRITROLLER_LOG_LEVEL:-INFO}
API_BASE=${VITE_API_BASE_URL:-http://localhost:${PORT}/api}
LOG_FILE=${AGRITROLLER_LOG_FILE:-"${HOME}/.agritroller/agritroller.log"}

SCRIPT_DEPS="${PROJECT_ROOT}/scripts/install_apt_deps.sh"
SCRIPT_CRON="${PROJECT_ROOT}/scripts/install_crontab_start.sh"

status_line() {
  local label="$1"; local done="$2"; local info="$3"
  if [[ "${done}" == "1" ]]; then
    echo "[done] ${label}${info:+ - ${info}}"
  else
    echo "[todo] ${label}${info:+ - ${info}}"
  fi
}

have_apt_deps() {
  command -v python3 >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 && command -v node >/dev/null 2>&1 && command -v git >/dev/null 2>&1
}

backend_ready() {
  [[ -x "${VENV_DIR}/bin/python" ]] || return 1
  "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1
import fastapi  # noqa: F401
import uvicorn  # noqa: F401
PY
}

frontend_built() {
  [[ -f "${PROJECT_ROOT}/frontend/dist/index.html" ]]
}

cron_installed() {
  crontab -l 2>/dev/null | grep -F "AGRITROLLER_STAT_START" >/dev/null 2>&1
}

app_running() {
  pgrep -f "python[0-9.]* .*main.py" >/dev/null 2>&1
}

install_apt_deps() {
  if have_apt_deps; then
    echo "[=] System deps already present"
    return
  fi
  bash "${SCRIPT_DEPS}"
}

setup_backend() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[*] Creating virtualenv at ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  fi
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
  pip install --upgrade pip
  pip install -r "${PROJECT_ROOT}/requirements.txt"
}

build_frontend() {
  echo "[*] Building frontend with API base ${API_BASE}"
  pushd "${PROJECT_ROOT}/frontend" >/dev/null
  export VITE_API_BASE_URL="${API_BASE}"
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
  npm run build
  popd >/dev/null
}

install_cron() {
  bash "${SCRIPT_CRON}" || true
}

start_app() {
  if app_running; then
    echo "[=] App already running; skipping start"
    return
  fi
  mkdir -p "$(dirname "${LOG_FILE}")"
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
  echo "[*] Starting backend on ${HOST}:${PORT}; logs -> ${LOG_FILE}"
  AGRITROLLER_ENV=${AGRITROLLER_ENV:-production} \
  AGRITROLLER_HOST=${HOST} \
  AGRITROLLER_PORT=${PORT} \
  AGRITROLLER_LOG_LEVEL=${LOG_LEVEL} \
  AGRITROLLER_FRONTEND_DIST="${PROJECT_ROOT}/frontend/dist" \
  nohup python "${PROJECT_ROOT}/main.py" >> "${LOG_FILE}" 2>&1 &
  echo "[+] Started with PID $!"
}

show_status() {
  status_line "System packages" "$(have_apt_deps && echo 1 || echo 0)"
  status_line "Backend venv + deps" "$(backend_ready && echo 1 || echo 0)" "dir=${VENV_DIR}"
  status_line "Frontend build" "$(frontend_built && echo 1 || echo 0)" "dist/frontend/dist"
  status_line "Autostart (crontab)" "$(cron_installed && echo 1 || echo 0)"
  status_line "App running" "$(app_running && echo 1 || echo 0)"
}

usage() {
  cat <<'EOF'
Usage: stat.sh [command]
Commands:
  all       Install deps, build, set autostart, and start the app (if not running)
  deps      Install system deps via apt
  backend   Create venv and install backend deps
  frontend  Build frontend
  cron      Install @reboot crontab entry
  start     Start the app if not already running
  status    Show completion status
EOF
}

cmd=${1:-all}
case "${cmd}" in
  all)
    install_apt_deps
    setup_backend
    build_frontend
    install_cron
    start_app
    ;;
  deps)
    install_apt_deps
    ;;
  backend)
    setup_backend
    ;;
  frontend)
    build_frontend
    ;;
  cron)
    install_cron
    ;;
  start)
    start_app
    ;;
  status)
    ;;
  *)
    usage
    exit 1
    ;;
esac

show_status
