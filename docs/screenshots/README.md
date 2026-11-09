# Screenshots

This folder holds the screenshots used in the README, the demo guide, and the
slides. The images are taken on the Kali VM by the project owner. They are not in
the repository yet.

Please add these 7 PNG files with these exact names:

| File                          | What to capture                                                        |
|-------------------------------|------------------------------------------------------------------------|
| `01-dashboard-overview.png`   | The main dashboard: status card "SURICATA RUNNING (verified)", the Total/Critical/High cards, the severity chart, top lists, and the alert table. |
| `02-alert-detail.png`         | The alert detail panel open for one alert, showing all its fields.     |
| `03-rule-lab.png`             | The Rule Lab page (`/rule-lab`) with both rules and the "file state, not proof" note. |
| `04-e2e-pass-table.png`       | The terminal after `bash scripts/e2e_test.sh`, showing PASS 4 / FAIL 0. |
| `05-rule-toggle-summary.png`  | The terminal SUMMARY from `bash scripts/rule_toggle_experiment.sh` (disabled 7→7, enabled 7→8). |
| `06-telegram-alerts.png`      | The Telegram chat showing the two alert messages (test and warning).   |
| `07-suricata-not-running.png` | The dashboard after stopping Suricata: "SURICATA NOT RUNNING (verified)" and the warning banner. |

Tips:
- Use PNG format.
- Hide any personal data (for example your Telegram name) if you want.
- Keep the file names exactly as above, so the links in the docs work.
