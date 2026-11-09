#!/usr/bin/env bash
# CyberGuard - rule toggle experiment (Phase 6, Kali VM ONLY, manual).
#
# Reproduces the Phase 3 proof that detection depends on the SURICATA RULE, not
# on Python:
#   1. back up the active rules file
#   2. comment out sid 1000001 (CyberGuard Test Alert)
#   3. validate config with `suricata -T`, restart Suricata
#   4. send /cyberguard-test  -> show NO new 1000001 alert appears in eve.json
#   5. restore the rule, validate, restart
#   6. send /cyberguard-test  -> show detection works again
#
# The ONLY thing that changes is the Suricata rule file. Python performs no
# detection here. A trap ALWAYS restores the original rules on exit or error.
#
# Requires sudo (edits the deployed rules + restarts Suricata) and runs ONLY on
# Linux (the Kali VM). It is NEVER invoked by the dashboard or any endpoint.
#
# Written on Windows, validated manually on the Kali VM.

set -u

RULES_FILE="${CYBERGUARD_ACTIVE_RULES:-/var/lib/suricata/rules/cyberguard.rules}"
SURICATA_YAML="${CYBERGUARD_SURICATA_YAML:-/etc/suricata/suricata.yaml}"
PID_FILE="${CYBERGUARD_SURICATA_PID:-/tmp/suricata.pid}"
LAB_BASE="${CYBERGUARD_LAB_BASE:-http://127.0.0.1:8000}"
EVE="${CYBERGUARD_EVE_PATH:-/var/log/suricata/eve.json}"
SID="1000001"

# --- refuse to run anywhere but Linux (the Kali VM) ---
if [ "$(uname -s)" != "Linux" ]; then
  echo "This experiment runs ONLY on Linux (the Kali VM). Detected: $(uname -s). Aborting."
  exit 2
fi

run() {  # echo every command before running it
  echo "+ $*"
  "$@"
}

BACKUP=""
restore() {
  # Only restore from a NON-EMPTY backup, so a failed backup can never clobber
  # the real rules. Idempotent: safe if it runs more than once.
  if [ -n "$BACKUP" ] && [ -s "$BACKUP" ]; then
    echo
    echo ">>> [trap] Restoring original rules from $BACKUP"
    run sudo cp "$BACKUP" "$RULES_FILE"
    echo ">>> [trap] Original rules restored."
  fi
}
# EXIT already covers Ctrl+C / kill in bash; INT and TERM are listed explicitly
# so the intent is unambiguous (restore is idempotent if both fire).
trap restore EXIT INT TERM

restart_suricata() {
  if [ -f "$PID_FILE" ] && [ -r "$PID_FILE" ]; then
    run sudo kill "$(cat "$PID_FILE")" || true
    sleep 2
  fi
  run sudo suricata -c "$SURICATA_YAML" -i lo -D --pidfile "$PID_FILE"
  sleep 3
}

count_sid_in_eve() {  # read-only count of this SID's alerts currently in eve.json
  grep -c "\"signature_id\":$SID" "$EVE" 2>/dev/null || echo 0
}

echo "== CyberGuard rule toggle experiment (Kali VM) =="
echo "Rules file : $RULES_FILE"
echo "Suricata   : $SURICATA_YAML (pidfile $PID_FILE)"
echo "EVE JSON   : $EVE"
echo
echo "This will EDIT the deployed rules and RESTART Suricata (sudo)."
echo "The original rules are backed up first and ALWAYS restored on exit."
echo
printf "Proceed? [y/N] "
read -r answer
case "$answer" in
  y|Y) ;;
  *) echo "Aborted by user."; exit 0 ;;
esac

# 0. Backup the active rules, then VERIFY the backup exists and is non-empty
#    BEFORE making any change. Abort (trap is a no-op: nothing changed yet) if not.
BACKUP="$(mktemp /tmp/cyberguard.rules.bak.XXXXXX)"
run sudo cp "$RULES_FILE" "$BACKUP"
if [ ! -s "$BACKUP" ]; then
  echo "FATAL: backup at $BACKUP is missing or empty — refusing to modify the rules."
  exit 1
fi
echo ">>> Backed up active rules to $BACKUP ($(wc -l < "$BACKUP") lines) — verified non-empty."

# 1. Disable sid 1000001 by commenting out its rule line (alert -> #alert).
echo
echo "--- Step 1: disable sid $SID ---"
run sudo sed -i "/sid:$SID;/s/^alert/#alert/" "$RULES_FILE"
echo ">>> Disabled lines containing sid:$SID; (grep -c '^#alert' shows the count):"
run sudo grep -c "^#alert" "$RULES_FILE" || true

# 2. Validate + restart with the rule disabled.
echo
echo "--- Step 2: validate + restart (rule disabled) ---"
run sudo suricata -T -c "$SURICATA_YAML" -v
restart_suricata

before_off="$(count_sid_in_eve)"
run curl -s -o /dev/null "$LAB_BASE/cyberguard-test"
sleep 4
after_off="$(count_sid_in_eve)"
echo ">>> sid $SID count in eve.json: $before_off -> $after_off (EXPECT UNCHANGED while disabled)"

# 3. Restore the rule, validate, restart.
echo
echo "--- Step 3: restore rule + validate + restart ---"
run sudo cp "$BACKUP" "$RULES_FILE"
run sudo suricata -T -c "$SURICATA_YAML" -v
restart_suricata

before_on="$(count_sid_in_eve)"
run curl -s -o /dev/null "$LAB_BASE/cyberguard-test"
sleep 4
after_on="$(count_sid_in_eve)"
echo ">>> sid $SID count in eve.json: $before_on -> $after_on (EXPECT INCREASED - detection restored)"

echo
echo "================= SUMMARY ================="
echo "rule DISABLED: $before_off -> $after_off  (no new $SID alert => detection depends on the rule)"
echo "rule ENABLED : $before_on -> $after_on  (new $SID alert => detection works again)"
echo "==========================================="
echo "Done. The trap will ensure the original rules are in place on exit."
