# Screenshots

This folder holds the screenshots used in the main README, the demo guide, and the
slides. The images were taken on the Kali VM by the project owner.

The 7 images (exact file names used by the docs):

| File                          | What it shows                                                          |
|-------------------------------|------------------------------------------------------------------------|
| `01-dashboard-overview.png`   | The main dashboard: status card "SURICATA RUNNING (verified)", the Total/Critical/High cards, the severity chart, top lists, and the alert table. |
| `02-alert-detail.png`         | The alert detail panel open for one alert, showing all its fields.     |
| `03-rule-lab.png`             | The Rule Lab page (`/rule-lab`) with both rules and the "file state, not proof" note. |
| `04-e2e-pass-table.png`       | The terminal after `bash scripts/e2e_test.sh`, showing PASS 4 / FAIL 0. |
| `05-rule-toggle-summary.png`  | The terminal SUMMARY from `bash scripts/rule_toggle_experiment.sh` (rule disabled: no new alert; rule enabled: the alert returns). |
| `06-telegram-alerts.jpg`      | The Telegram chat showing the two alert messages (test and warning).   |
| `07-suricata-not-running.png` | The dashboard after stopping Suricata: "SURICATA NOT RUNNING (verified)" and the warning banner. |

Notes:
- `06-telegram-alerts.jpg` is a phone photo, kept in JPG format; every other image is PNG.
- The numbers in the screenshots come from later runs than the numbers in the text,
  so the exact counts may differ. The behaviour shown is the same.
