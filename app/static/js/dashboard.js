// CyberGuard dashboard — fetches honest engine/API status and renders it.
// It never fabricates an "active" state; it displays exactly what the API reports.

// Map the verified Suricata process state to a label + CSS class.
function describeProcess(state) {
  switch (state) {
    case "verified_running":
      return { label: "SURICATA RUNNING (verified)", cls: "status status--ok" };
    case "verified_not_running":
      return { label: "SURICATA NOT RUNNING (verified)", cls: "status status--bad" };
    default:
      return { label: "SURICATA UNVERIFIED (no /proc)", cls: "status status--unknown" };
  }
}

async function loadStatus() {
  const statusEl = document.getElementById("engine-status");
  const messageEl = document.getElementById("engine-message");
  const evePathEl = document.getElementById("eve-path");
  const eveExistsEl = document.getElementById("eve-exists");
  const lastEventEl = document.getElementById("last-event");
  const lastIngestedEl = document.getElementById("last-ingested");
  const invalidLinesEl = document.getElementById("invalid-lines");
  const alertCountEl = document.getElementById("alert-count");

  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    const p = describeProcess(data.suricata_process);
    statusEl.textContent = p.label;
    statusEl.className = p.cls;

    messageEl.textContent =
      "Suricata is the only detection engine. This page reflects the verified " +
      "process state — never a fake 'active' status.";
    evePathEl.textContent = data.eve_path || "—";
    eveExistsEl.textContent = data.eve_file_exists ? "yes" : "no";
    lastEventEl.textContent = data.last_event_timestamp || "—";
    lastIngestedEl.textContent = data.last_alert_ingested_at || "—";
    invalidLinesEl.textContent =
      data.invalid_lines_count !== undefined ? data.invalid_lines_count : "—";
    alertCountEl.textContent =
      data.total_alerts !== undefined ? data.total_alerts : "—";
  } catch (err) {
    statusEl.textContent = "UNAVAILABLE";
    statusEl.className = "status status--bad";
    messageEl.textContent = "Could not reach /api/status.";
  }
}

async function loadHealth() {
  const el = document.getElementById("api-health");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.status === "ok") {
      el.textContent = "API OK";
      el.className = "status status--ok";
    } else {
      el.textContent = "API DEGRADED";
      el.className = "status status--bad";
    }
  } catch (err) {
    el.textContent = "API UNREACHABLE";
    el.className = "status status--bad";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadStatus();
  loadHealth();
});
