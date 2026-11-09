// CyberGuard SOC dashboard.
//
// Displays ONLY data returned by the Flask API — it performs no detection and
// fabricates nothing. All dynamic values are rendered with textContent / DOM
// nodes (never innerHTML), so attacker-controlled fields (URL, user agent, …)
// can never inject markup. The same script drives the dashboard (/) and the
// alerts page (/alerts); render functions no-op when their element is absent.

(function () {
  "use strict";

  var POLL_MS = 3000;
  var PAGE_SIZE = 25;
  var SVG_NS = "http://www.w3.org/2000/svg";

  var SEVERITY = {
    1: { label: "Critical", color: "#f85149" },
    2: { label: "High", color: "#ff8c42" },
    3: { label: "Medium", color: "#d29922" },
    4: { label: "Low", color: "#3fb950" },
    5: { label: "Info", color: "#4da3ff" },
  };

  var state = {
    filters: {},
    offset: 0,
    lastCount: 0,
    total: null,
    alertsLoaded: false,
  };

  function $(id) { return document.getElementById(id); }

  function sevInfo(sev) {
    return SEVERITY[sev] || { label: "Sev " + sev, color: "#8b98a5" };
  }

  // --- Networking --------------------------------------------------------

  async function fetchJSON(url) {
    var res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  function showApiError(show) {
    var el = $("api-banner");
    if (!el) return;
    if (show) {
      el.textContent = "API unavailable — cannot reach the CyberGuard backend. Showing last known data.";
      el.classList.add("show");
    } else {
      el.classList.remove("show");
    }
  }

  // --- Status ------------------------------------------------------------

  function renderStatus(data) {
    var pill = $("suricata-state");
    var detail = $("suricata-detail");
    var banner = $("suricata-banner");

    var proc = data.suricata_process;
    var label, cls, bannerMsg = "";
    if (proc === "verified_running") {
      label = "SURICATA RUNNING (verified)";
      cls = "status status--ok";
    } else if (proc === "verified_not_running") {
      label = "SURICATA NOT RUNNING (verified)";
      cls = "status status--bad";
      bannerMsg = "Suricata is verified NOT running — no new detections are being produced.";
    } else {
      label = "SURICATA UNVERIFIED";
      cls = "status status--warn";
      bannerMsg = "Suricata process state is unverified (no /proc access on this host).";
    }
    if (pill) { pill.textContent = label; pill.className = cls; }
    if (detail) {
      detail.textContent =
        "EVE: " + (data.eve_file_exists ? "present" : "missing") +
        " · invalid lines: " + (data.invalid_lines_count != null ? data.invalid_lines_count : "—") +
        " · last ingest: " + (data.last_alert_ingested_at || "—");
    }
    if (banner) {
      if (bannerMsg) { banner.textContent = bannerMsg; banner.classList.add("show"); }
      else { banner.classList.remove("show"); }
    }
  }

  async function loadStatus() {
    try {
      var data = await fetchJSON("/api/status");
      showApiError(false);
      renderStatus(data);
    } catch (e) {
      showApiError(true);
      var pill = $("suricata-state");
      if (pill) { pill.textContent = "UNAVAILABLE"; pill.className = "status status--bad"; }
    }
  }

  // --- Stats (dashboard only) -------------------------------------------

  function renderChart(bySeverity) {
    var host = $("severity-chart");
    if (!host) return;
    var sevs = [1, 2, 3, 4, 5];
    var counts = sevs.map(function (s) { return Number((bySeverity || {})[String(s)] || 0); });
    var max = Math.max.apply(null, [1].concat(counts));
    var rowH = 22, gap = 8, top = 6, left = 70, barMax = 180;
    var height = top * 2 + sevs.length * rowH + (sevs.length - 1) * gap;

    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 300 " + height);
    svg.setAttribute("class", "chart");
    svg.setAttribute("width", "100%");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Alert count by severity");

    sevs.forEach(function (s, i) {
      var y = top + i * (rowH + gap);
      var w = (counts[i] / max) * barMax;

      var label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("x", "0");
      label.setAttribute("y", String(y + rowH / 2 + 4));
      label.textContent = s + " " + sevInfo(s).label;

      var rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("x", String(left));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(Math.max(0, w)));
      rect.setAttribute("height", String(rowH - 4));
      rect.setAttribute("rx", "3");
      rect.setAttribute("fill", sevInfo(s).color);

      var cnt = document.createElementNS(SVG_NS, "text");
      cnt.setAttribute("x", String(left + Math.max(0, w) + 4));
      cnt.setAttribute("y", String(y + rowH / 2 + 4));
      cnt.textContent = String(counts[i]);

      svg.appendChild(label);
      svg.appendChild(rect);
      svg.appendChild(cnt);
    });
    host.replaceChildren(svg);
  }

  function renderTopList(id, dict) {
    var host = $(id);
    if (!host) return;
    var entries = Object.keys(dict || {}).map(function (k) { return [k, dict[k]]; });
    entries.sort(function (a, b) { return b[1] - a[1]; });
    entries = entries.slice(0, 6);

    if (!entries.length) {
      var empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = "No data.";
      host.replaceChildren(empty);
      return;
    }
    var max = Math.max.apply(null, [1].concat(entries.map(function (e) { return e[1]; })));
    var frag = document.createDocumentFragment();
    entries.forEach(function (e) {
      var li = document.createElement("li");
      var label = document.createElement("span");
      label.className = "label";
      label.textContent = e[0];
      var bar = document.createElement("span");
      bar.className = "bar";
      bar.style.width = (e[1] / max) * 110 + "px";
      var count = document.createElement("span");
      count.className = "count";
      count.textContent = String(e[1]);
      li.append(label, bar, count);
      frag.appendChild(li);
    });
    host.replaceChildren(frag);
  }

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text;
  }

  async function loadStats() {
    if (!$("stat-total")) return; // not on this page
    try {
      var s = await fetchJSON("/api/stats");
      showApiError(false);
      state.total = s.total;
      setText("stat-total", String(s.total));
      setText("stat-last24", "last 24h: " + (s.last_24h != null ? s.last_24h : "—"));
      setText("stat-critical", String((s.by_severity || {})["1"] || 0));
      setText("stat-high", String((s.by_severity || {})["2"] || 0));
      renderChart(s.by_severity);
      renderTopList("top-src-ips", s.by_src_ip);
      renderTopList("top-signatures", s.by_signature);
    } catch (e) {
      showApiError(true);
    }
  }

  // --- Alerts table ------------------------------------------------------

  function severityBadge(sev) {
    var span = document.createElement("span");
    span.className = "badge badge--" + (SEVERITY[sev] ? sev : 5);
    span.textContent = sev + " " + sevInfo(sev).label;
    return span;
  }

  function cell(text) {
    var td = document.createElement("td");
    td.textContent = text == null || text === "" ? "—" : String(text);
    return td;
  }

  function stateRow(message, spinner) {
    var tr = document.createElement("tr");
    tr.className = "state-row";
    var td = document.createElement("td");
    td.colSpan = 8;
    if (spinner) {
      var dot = document.createElement("span");
      dot.className = "loading-dot";
      td.appendChild(dot);
    }
    td.appendChild(document.createTextNode(message));
    tr.appendChild(td);
    return tr;
  }

  function openDetail(alert) {
    var panel = $("detail-panel");
    var content = $("detail-content");
    if (!panel || !content) return;

    var fields = [
      ["Time (raw)", alert.timestamp_raw],
      ["Time (UTC)", alert.timestamp_utc],
      ["Severity", alert.severity + " — " + sevInfo(alert.severity).label],
      ["Signature", alert.signature],
      ["SID", alert.signature_id],
      ["Category", alert.category],
      ["Action", alert.action],
      ["Protocol", alert.proto],
      ["App proto", alert.app_proto],
      ["Source IP", alert.src_ip],
      ["Source port", alert.src_port],
      ["Dest IP", alert.dest_ip],
      ["Dest port", alert.dest_port],
      ["Interface", alert.in_iface],
      ["HTTP method", alert.http_method],
      ["HTTP URL", alert.http_url],
      ["HTTP host", alert.http_hostname],
      ["HTTP status", alert.http_status],
      ["User agent", alert.http_user_agent],
    ];

    var frag = document.createDocumentFragment();
    fields.forEach(function (f) {
      var dt = document.createElement("dt");
      dt.textContent = f[0];
      var dd = document.createElement("dd");
      dd.textContent = f[1] == null || f[1] === "" ? "—" : String(f[1]);
      frag.appendChild(dt);
      frag.appendChild(dd);
    });
    content.replaceChildren(frag);
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
  }

  function closeDetail() {
    var panel = $("detail-panel");
    if (!panel) return;
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
  }

  function renderAlerts(alerts) {
    var tbody = $("alerts-tbody");
    if (!tbody) return;

    if (!alerts.length) {
      tbody.replaceChildren(stateRow("No alerts match the current filters.", false));
      return;
    }
    var frag = document.createDocumentFragment();
    alerts.forEach(function (a) {
      var tr = document.createElement("tr");
      tr.appendChild(cell(a.timestamp_utc));

      var sevTd = document.createElement("td");
      sevTd.appendChild(severityBadge(a.severity));
      tr.appendChild(sevTd);

      tr.appendChild(cell(a.signature));
      tr.appendChild(cell(a.signature_id));
      tr.appendChild(cell((a.src_ip || "—") + ":" + (a.src_port != null ? a.src_port : "—")));
      tr.appendChild(cell((a.dest_ip || "—") + ":" + (a.dest_port != null ? a.dest_port : "—")));
      tr.appendChild(cell(a.proto));
      tr.appendChild(cell(a.http_url));

      tr.addEventListener("click", function () { openDetail(a); });
      frag.appendChild(tr);
    });
    tbody.replaceChildren(frag);
  }

  function updatePagination() {
    var prev = $("page-prev");
    var next = $("page-next");
    var info = $("page-info");
    if (prev) prev.disabled = state.offset <= 0;
    if (next) next.disabled = state.lastCount < PAGE_SIZE;
    if (info) {
      if (state.lastCount === 0) {
        info.textContent = "No results";
      } else {
        var start = state.offset + 1;
        var end = state.offset + state.lastCount;
        info.textContent = "Showing " + start + "–" + end +
          (state.total != null ? " of " + state.total + " total" : "");
      }
    }
  }

  function buildQuery() {
    var p = new URLSearchParams();
    p.set("limit", String(PAGE_SIZE));
    p.set("offset", String(state.offset));
    var f = state.filters;
    Object.keys(f).forEach(function (k) {
      if (f[k] !== "" && f[k] != null) p.set(k, f[k]);
    });
    return p.toString();
  }

  async function loadAlerts(showLoading) {
    var tbody = $("alerts-tbody");
    if (!tbody) return;
    if (showLoading || !state.alertsLoaded) {
      tbody.replaceChildren(stateRow("Loading…", true));
    }
    try {
      var data = await fetchJSON("/api/alerts?" + buildQuery());
      showApiError(false);
      state.lastCount = data.count;
      state.alertsLoaded = true;
      renderAlerts(data.alerts || []);
      updatePagination();
    } catch (e) {
      showApiError(true);
      if (!state.alertsLoaded) {
        tbody.replaceChildren(stateRow("Could not load alerts.", false));
      }
      // On background-poll failure, keep the last rows (no flicker / no wipe).
    }
  }

  // --- Filters / pagination wiring --------------------------------------

  function readFilters() {
    var f = {};
    var sev = $("f-severity"); if (sev && sev.value) f.severity = sev.value;
    var sig = $("f-signature"); if (sig && sig.value.trim()) f.signature = sig.value.trim();
    var ip = $("f-src-ip"); if (ip && ip.value.trim()) f.src_ip = ip.value.trim();
    var q = $("f-q"); if (q && q.value.trim()) f.q = q.value.trim();
    var from = $("f-from"); if (from && from.value) f.from = from.value;
    var to = $("f-to"); if (to && to.value) f.to = to.value;
    return f;
  }

  function applyFilters() {
    state.filters = readFilters();
    state.offset = 0;
    loadAlerts(true);
  }

  function clearFilters() {
    ["f-severity", "f-signature", "f-src-ip", "f-q", "f-from", "f-to"].forEach(function (id) {
      var el = $(id);
      if (el) el.value = "";
    });
    state.filters = {};
    state.offset = 0;
    loadAlerts(true);
  }

  function wireControls() {
    var apply = $("f-apply"); if (apply) apply.addEventListener("click", applyFilters);
    var clear = $("f-clear"); if (clear) clear.addEventListener("click", clearFilters);
    ["f-signature", "f-src-ip", "f-q"].forEach(function (id) {
      var el = $(id);
      if (el) el.addEventListener("keydown", function (e) { if (e.key === "Enter") applyFilters(); });
    });
    var prev = $("page-prev");
    if (prev) prev.addEventListener("click", function () {
      if (state.offset > 0) { state.offset = Math.max(0, state.offset - PAGE_SIZE); loadAlerts(true); }
    });
    var next = $("page-next");
    if (next) next.addEventListener("click", function () {
      if (state.lastCount >= PAGE_SIZE) { state.offset += PAGE_SIZE; loadAlerts(true); }
    });
    var close = $("detail-close"); if (close) close.addEventListener("click", closeDetail);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDetail(); });
  }

  // --- Boot --------------------------------------------------------------

  function pollAll() {
    loadStatus();
    loadStats();
    loadAlerts(false); // background refresh — no loading flicker
  }

  document.addEventListener("DOMContentLoaded", function () {
    wireControls();
    loadStatus();
    loadStats();
    loadAlerts(true);
    setInterval(pollAll, POLL_MS);
  });
})();
