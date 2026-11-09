#!/usr/bin/env bash
# CyberGuard - lab readiness check (Phase 6).
#
# CHECKS (never starts anything, never uses sudo itself) the pieces needed for
# the end-to-end test, and prints the EXACT command to fix whatever is missing:
#   1. Suricata running  - via /tmp/suricata.pid + /proc/<pid>/comm
#   2. Lab HTTP server listening on port 8000
#   3. Flask backend listening on port 5000
#
# Detection stays entirely with Suricata; this script only inspects state and
# never writes to eve.json or the database.
#
# Written on Windows, validated manually on the Kali VM.

set -u

PID_FILE="${CYBERGUARD_SURICATA_PID:-/tmp/suricata.pid}"
SURICATA_YAML="${CYBERGUARD_SURICATA_YAML:-/etc/suricata/suricata.yaml}"
LAB_PORT="${CYBERGUARD_LAB_PORT:-8000}"
API_PORT="${CYBERGUARD_API_PORT:-5000}"

missing=0

echo "== CyberGuard lab readiness check =="
echo

# --- 1. Suricata (pidfile + /proc/<pid>/comm, no sudo) ---
check_suricata() {
  local start_cmd="sudo suricata -c $SURICATA_YAML -i lo -D --pidfile $PID_FILE"
  if [ ! -f "$PID_FILE" ]; then
    echo "[MISSING] Suricata pidfile not found at $PID_FILE"
    echo "  Fix (run it yourself, needs sudo):"
    echo "    $start_cmd"
    return 1
  fi
  local pid comm
  pid="$(cat "$PID_FILE" 2>/dev/null)"
  if [ -z "$pid" ] || [ ! -r "/proc/$pid/comm" ]; then
    echo "[MISSING] Suricata pid '$pid' from $PID_FILE is not running"
    echo "  Fix:"
    echo "    $start_cmd"
    return 1
  fi
  comm="$(cat "/proc/$pid/comm" 2>/dev/null)"
  case "$comm" in
    *[Ss]uricata*)
      echo "[OK] Suricata running (pid $pid, comm=$comm)"
      return 0 ;;
    *)
      echo "[MISSING] pid $pid is alive but is not Suricata (comm=$comm)"
      echo "  Fix:"
      echo "    $start_cmd"
      return 1 ;;
  esac
}

# --- port listener helper (ss -> netstat -> /dev/tcp fallback) ---
port_listening() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -q ":$port "
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | grep -q ":$port "
  else
    (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && { exec 3>&- 3<&-; return 0; }
    return 1
  fi
}

check_port() {
  local port="$1" name="$2" fix="$3"
  if port_listening "$port"; then
    echo "[OK] $name listening on port $port"
    return 0
  fi
  echo "[MISSING] $name not listening on port $port"
  echo "  Fix:"
  echo "    $fix"
  return 1
}

check_suricata || missing=1
check_port "$LAB_PORT" "Lab HTTP server" "python3 lab/server.py --port $LAB_PORT" || missing=1
check_port "$API_PORT" "Flask backend" "python3 -m app.main" || missing=1

echo
if [ "$missing" -eq 0 ]; then
  echo "All lab components are ready. Next: bash scripts/e2e_test.sh"
  exit 0
fi
echo "Some components are missing (see the Fix commands above). Re-run after fixing."
exit 1
