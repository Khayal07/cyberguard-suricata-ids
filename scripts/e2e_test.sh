#!/usr/bin/env bash
# CyberGuard - end-to-end detection test (Phase 6).
#
# Drives harmless local HTTP traffic and checks that the REAL pipeline
# (Suricata -> eve.json -> backend -> API) reflects it. This script NEVER writes
# to the database or eve.json; it only READS the API and sends HTTP requests to
# the lab server. ALL detection is performed by Suricata.
#
# Preconditions (use scripts/start_lab.sh to check):
#   - Suricata verified running (via /api/status)
#   - lab server on :8000, backend on :5000
#
# Uses only curl + python3 for JSON parsing (no jq dependency).
#
# Written on Windows, pending validation on the Kali VM.

set -u

API_BASE="${CYBERGUARD_API_BASE:-http://127.0.0.1:5000}"
LAB_BASE="${CYBERGUARD_LAB_BASE:-http://127.0.0.1:8000}"
POLL_MAX="${CYBERGUARD_POLL_MAX:-15}"   # seconds to wait for an alert via the API
SETTLE=$(( POLL_MAX / 3 ))              # quiet window to confirm "no new alert"

pass_count=0
fail_count=0
RESULTS=()

record() {  # $1 = PASS|FAIL, $2 = description
  RESULTS+=("$1|$2")
  if [ "$1" = "PASS" ]; then pass_count=$((pass_count + 1)); else fail_count=$((fail_count + 1)); fi
}

get_total() {
  curl -s "$API_BASE/api/stats" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["total"])'
}
get_proc() {
  curl -s "$API_BASE/api/status" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["suricata_process"])'
}
count_sid() {  # $1 = signature_id -> number of stored alerts with that SID
  curl -s "$API_BASE/api/alerts?signature_id=$1&limit=500" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["count"])'
}
hit() {  # send one benign GET to the lab server (discard body)
  curl -s -o /dev/null "$LAB_BASE$1"
}

poll_total_ge() {  # wait until /api/stats total >= $1 (max POLL_MAX s); echoes last seen total
  local want="$1" deadline cur
  deadline=$(( $(date +%s) + POLL_MAX ))
  while :; do
    cur="$(get_total)"
    if [ "${cur:-0}" -ge "$want" ]; then echo "$cur"; return 0; fi
    if [ "$(date +%s)" -ge "$deadline" ]; then echo "${cur:-0}"; return 1; fi
    sleep 1
  done
}

echo "== CyberGuard end-to-end test =="
echo "API: $API_BASE   Lab: $LAB_BASE"
echo

# --- Precondition: Suricata verified running (else FAIL and exit) ---
proc="$(get_proc)"
if [ "$proc" != "verified_running" ]; then
  echo "FATAL: /api/status suricata_process = '$proc' (expected 'verified_running')."
  echo "Start Suricata on the Kali VM (see scripts/start_lab.sh) and re-run."
  exit 2
fi
echo "[OK] Suricata verified running."

baseline="$(get_total)"
echo "Baseline total alerts: $baseline"
echo

# --- (A) Benign request must NOT create an alert ---
hit "/index.html"
sleep "$SETTLE"
after_a="$(get_total)"
if [ "$after_a" -eq "$baseline" ]; then
  record PASS "A benign /index.html: total unchanged at $baseline"
else
  record FAIL "A benign /index.html: total $baseline -> $after_a (expected unchanged)"
fi

# --- (B) /cyberguard-test -> new sid 1000001 alert, total +1 ---
b_before="$(count_sid 1000001)"
hit "/cyberguard-test"
want=$(( after_a + 1 ))
after_b="$(poll_total_ge "$want")"
b_after="$(count_sid 1000001)"
if [ "$after_b" -eq "$want" ] && [ "$b_after" -gt "$b_before" ]; then
  record PASS "B /cyberguard-test: sid 1000001 fired, total $after_a -> $after_b (+1)"
else
  record FAIL "B /cyberguard-test: total $after_a -> $after_b (want $want); sid1000001 $b_before -> $b_after"
fi

# --- (C) /cyberguard-warning -> new sid 1000002 alert, total +1 ---
c_before="$(count_sid 1000002)"
hit "/cyberguard-warning"
want=$(( after_b + 1 ))
after_c="$(poll_total_ge "$want")"
c_after="$(count_sid 1000002)"
if [ "$after_c" -eq "$want" ] && [ "$c_after" -gt "$c_before" ]; then
  record PASS "C /cyberguard-warning: sid 1000002 fired, total $after_b -> $after_c (+1)"
else
  record FAIL "C /cyberguard-warning: total $after_b -> $after_c (want $want); sid1000002 $c_before -> $c_after"
fi

# --- (D) No duplicates: total stays put after another ingest window ---
sleep "$SETTLE"
after_d="$(get_total)"
if [ "$after_d" -eq "$after_c" ]; then
  record PASS "D no duplicates: total stable at $after_c after a re-ingest window"
else
  record FAIL "D no duplicates: total $after_c -> $after_d with no new request (possible duplicate)"
fi

# --- Report ---
echo
echo "================= RESULTS ================="
printf "%-6s %s\n" "STATUS" "CHECK"
for row in "${RESULTS[@]}"; do
  printf "%-6s %s\n" "${row%%|*}" "${row#*|}"
done
echo "==========================================="
echo "PASS: $pass_count   FAIL: $fail_count"

[ "$fail_count" -eq 0 ] || exit 1
