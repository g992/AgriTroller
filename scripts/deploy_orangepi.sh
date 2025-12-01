#!/usr/bin/env bash
set -euo pipefail

# Production bootstrap helper for OrangePi or other Debian/Ubuntu SBCs.
# Installs prerequisites, builds the frontend for production, installs backend
# dependencies into a virtualenv, and runs the backend using production settings.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${AGRITROLLER_HOST:-0.0.0.0}"
PORT="${AGRITROLLER_PORT:-8080}"
API_BASE="${VITE_API_BASE_URL:-http://localhost:${PORT}/api}"
LOG_LEVEL="${AGRITROLLER_LOG_LEVEL:-INFO}"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

install_system_deps() {
  if command_exists apt-get; then
    echo "[*] Installing system dependencies (python3-venv, pip, nodejs, npm)..."
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip git nodejs npm
  else
    echo "[!] apt-get not found. Install python3-venv, python3-pip, nodejs, and npm manually." >&2
  fi
}

create_venv() {
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
  echo "[*] Building frontend (production) with API base ${API_BASE}"
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

start_backend() {
  echo "[*] Starting AgriTroller backend on ${HOST}:${PORT}"
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
  AGRITROLLER_ENV="${AGRITROLLER_ENV:-production}" \
  AGRITROLLER_HOST="${HOST}" \
  AGRITROLLER_PORT="${PORT}" \
  AGRITROLLER_LOG_LEVEL="${LOG_LEVEL}" \
  AGRITROLLER_FRONTEND_DIST="${PROJECT_ROOT}/frontend/dist/spa" \
  python "${PROJECT_ROOT}/main.py"
}

usage() {
  cat <<'EOF'
Usage: deploy_orangepi.sh [command]

Commands:
  all      Install system deps, create venv, build frontend, and start backend
  deps     Install system dependencies only
  build    Create/refresh venv and build frontend (no start)
  start    Start backend using existing builds/venv

Environment overrides:
  AGRITROLLER_HOST, AGRITROLLER_PORT, AGRITROLLER_ENV, AGRITROLLER_LOG_LEVEL
  AGRITROLLER_FRONTEND_DIST, VENV_DIR, PYTHON_BIN, VITE_API_BASE_URL
EOF
}

cmd="${1:-all}"
case "${cmd}" in
  all)
    install_system_deps
    create_venv
    build_frontend
    start_backend
    ;;
  deps)
    install_system_deps
    ;;
  build)
    create_venv
    build_frontend
    ;;
  start)
    start_backend
    ;;
  *)
    usage
    exit 1
    ;;
esac
