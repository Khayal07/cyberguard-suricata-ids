// CyberGuard dashboard — fetches honest engine/API status and renders it.
// It never fabricates an "active" state; it displays exactly what the API reports.

async function loadStatus() {
  const statusEl = document.getElementById("engine-status");
  const messageEl = document.getElementById("engine-message");
  const evePathEl = document.getElementById("eve-path");
  const eveExistsEl = document.getElementById("eve-exists");
  const alertCountEl = document.getElementById("alert-count");

  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    if (data.suricata_configured) {
      statusEl.textContent = "CONFIGURED";
      statusEl.className = "status status--ok";
    } else {
      statusEl.textContent = "NOT CONFIGURED";
      statusEl.className = "status status--bad";
    }

    messageEl.textContent = data.message || "";
    evePathEl.textContent = data.eve_json_path || "—";
    eveExistsEl.textContent = data.eve_json_exists ? "yes" : "no";
    alertCountEl.textContent =
      data.alert_count !== undefined ? data.alert_count : "—";
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
