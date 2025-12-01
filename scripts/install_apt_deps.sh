#!/usr/bin/env bash
set -euo pipefail

# Install system dependencies required to build and run AgriTroller.

REQUIRED_PACKAGES=(python3-venv python3-pip nodejs npm git cron)
SUDO_BIN=${SUDO:-sudo}

if ! command -v apt-get >/dev/null 2>&1; then
  echo "[!] apt-get not found. Install python3-venv, python3-pip, nodejs, npm, git, and cron manually." >&2
  exit 1
fi

if [[ ${EUID:-0} -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "[!] sudo not available; run this script as root or set SUDO= command." >&2
  exit 1
fi

echo "[*] Updating package index"
${SUDO_BIN} apt-get update

echo "[*] Installing packages: ${REQUIRED_PACKAGES[*]}"
${SUDO_BIN} apt-get install -y "${REQUIRED_PACKAGES[@]}"

echo "[+] System dependencies installed"
