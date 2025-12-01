#!/usr/bin/env bash
set -euo pipefail

# Configure polkit to allow the current user (or specified USERNAME) to control
# NetworkManager via nmcli without requiring sudo. This is needed for Wi-Fi
# connect/scan actions from the AgriTroller UI.

USERNAME=${USERNAME:-"${USER}"}
GROUP_NAME=${GROUP_NAME:-netdev}
RULES_PATH=${RULES_PATH:-/etc/polkit-1/rules.d/10-agritroller-wifi.rules}
SUDO_BIN=${SUDO:-sudo}

if [[ -z "${USERNAME}" ]]; then
  echo "[!] USERNAME is empty; aborting" >&2
  exit 1
fi

echo "[*] Ensuring user ${USERNAME} is in group ${GROUP_NAME}"
if ! id -nG "${USERNAME}" | tr ' ' '\n' | grep -qx "${GROUP_NAME}"; then
  ${SUDO_BIN} usermod -aG "${GROUP_NAME}" "${USERNAME}"
  echo "[+] Added ${USERNAME} to ${GROUP_NAME}"
else
  echo "[=] ${USERNAME} already in ${GROUP_NAME}"
fi

echo "[*] Writing polkit rule to ${RULES_PATH}"
${SUDO_BIN} tee "${RULES_PATH}" >/dev/null <<EOF
polkit.addRule(function(action, subject) {
  if (action.id.indexOf("org.freedesktop.NetworkManager.") === 0 &&
      (subject.user == "${USERNAME}" || subject.isInGroup("${GROUP_NAME}"))) {
    return polkit.Result.YES;
  }
});
EOF

echo "[*] Restarting polkit"
${SUDO_BIN} systemctl restart polkit || true

echo "[+] Polkit configured for NetworkManager control via nmcli (user: ${USERNAME})"
echo "[i] Re-log the user session or run 'newgrp ${GROUP_NAME}' to apply group membership immediately."
