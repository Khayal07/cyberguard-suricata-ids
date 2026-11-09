# CyberGuard Lab

This folder documents the **authorized local laboratory** used to generate
controlled traffic for testing Suricata detection rules.

## Rules of engagement

- All experiments run only in an isolated, authorized local environment.
- Use **harmless HTTP markers** and controlled traffic only.
- **Do not** perform external scanning, unauthorized penetration testing,
  credential attacks, or any destructive activity.
- Never expose the Flask application publicly; keep it bound to `localhost`.

## Planned contents (later phases)

- Instructions to generate benign test traffic (e.g. `curl` requests carrying a
  unique marker string) that trips a custom lab rule.
- Small sample PCAP files for offline Suricata analysis when live capture is
  unreliable. (PCAPs are git-ignored by default; sample lab PCAPs may be added
  explicitly.)
- Expected EVE JSON output for each test, so detections can be verified as
  genuine Suricata output — never fabricated.

Nothing here performs detection. Detection happens only inside Suricata.
