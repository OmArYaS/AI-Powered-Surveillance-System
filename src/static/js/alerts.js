// alerts.js — Alerts tab: live threats feed via REST + WebSocket

const alerts = {
  ws: null,
  events: [],
  level: "all",
  wsReconnectTimer: null,
  reconnectDelay: 2000,
  wsStatus: "disconnected",
  newIds: new Set(),

  init() {
    this.listEl = $("#alerts-list");
    this.totalsEl = $("#alerts-totals");
    this.wsStatusEl = $("#ws-status");
    if (!this.listEl) return;

    $$(".alerts-filters .filter-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        $$(".alerts-filters .filter-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        this.level = chip.dataset.level;
        this.render();
      });
    });

    $("#btn-clear-alerts")?.addEventListener("click", async () => {
      const ok = await showModal({
        title: "Clear all alerts?",
        text: "This will clear the alerts history (snapshots on disk are kept).",
        confirmText: "Clear",
        danger: true,
      });
      if (!ok) return;
      await API.threats.clear();
      this.events = [];
      this.render();
      showToast("Alerts cleared", "success");
    });

    this.connectWS();
    this.refresh();
    setInterval(() => this.refresh(), 8000);
  },

  async refresh() {
    try {
      const data = await API.threats.list(100);
      const knownIds = new Set(this.events.map((e) => e.id));
      this.events = data.events || [];
      const newOnes = this.events.filter((e) => !knownIds.has(e.id));
      this.newIds = new Set(newOnes.map((e) => e.id));
      this.renderTotals(data.stats || {});
      this.render();
      setTimeout(() => {
        this.newIds.clear();
        this.render();
      }, 3000);
    } catch (e) {
      console.warn("alerts refresh failed:", e);
    }
  },

  connectWS() {
    if (this.ws) {
      try { this.ws.close(); } catch {}
    }
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/threats`;
    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      this.scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.setStatus("connected");
      this.reconnectDelay = 2000;
    };
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "threat" && msg.data) {
          this.onNewThreat(msg.data);
        }
      } catch {}
    };
    this.ws.onclose = () => {
      this.setStatus("disconnected");
      this.scheduleReconnect();
    };
    this.ws.onerror = () => {
      try { this.ws.close(); } catch {}
    };
  },

  scheduleReconnect() {
    if (this.wsReconnectTimer) return;
    this.wsReconnectTimer = setTimeout(() => {
      this.wsReconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 15000);
      this.connectWS();
    }, this.reconnectDelay);
  },

  setStatus(s) {
    this.wsStatus = s;
    if (!this.wsStatusEl) return;
    this.wsStatusEl.classList.remove("connected", "disconnected");
    this.wsStatusEl.classList.add(s);
    this.wsStatusEl.querySelector(".ws-text").textContent =
      s === "connected" ? "Live" : "Reconnecting...";
  },

  onNewThreat(event) {
    this.events.unshift(event);
    this.newIds.add(event.id);
    this.render();
    showToast(
      `${event.level.toUpperCase()}: ${event.description}`,
      event.level === "critical" ? "error" : event.level === "high" ? "warning" : "info",
      4000,
    );
    setTimeout(() => {
      this.newIds.delete(event.id);
      this.render();
    }, 3000);
    this.refreshTotals();
  },

  async refreshTotals() {
    try {
      const data = await API.threats.list(1);
      this.renderTotals(data.stats || {});
    } catch {}
  },

  renderTotals(stats) {
    if (!this.totalsEl) return;
    const by = stats.by_level || {};
    this.totalsEl.innerHTML = `
      <div class="stat-mini crit"><span>Critical</span><span class="num">${by.critical || 0}</span></div>
      <div class="stat-mini high"><span>High</span><span class="num">${by.high || 0}</span></div>
      <div class="stat-mini med"><span>Medium</span><span class="num">${by.medium || 0}</span></div>
      <div class="stat-mini low"><span>Low</span><span class="num">${by.low || 0}</span></div>
      <div class="stat-mini"><span>Total</span><span class="num">${stats.total_alerts || 0}</span></div>
    `;
    const badge = document.getElementById("nav-badge-alerts");
    if (badge) {
      const hot = (by.critical || 0) + (by.high || 0);
      const total = stats.total_alerts || 0;
      if (hot > 0) {
        badge.textContent = hot;
        badge.style.display = "";
        badge.classList.add("danger");
      } else if (total > 0) {
        badge.textContent = total;
        badge.style.display = "";
        badge.classList.remove("danger");
      } else {
        badge.style.display = "none";
      }
    }
  },

  render() {
    if (!this.listEl) return;
    const filtered = this.level === "all"
      ? this.events
      : this.events.filter((e) => e.level === this.level);

    if (filtered.length === 0) {
      this.listEl.innerHTML = `
        <div class="alerts-empty" style="grid-column: 1 / -1">
          <div class="icon-big">${icon("shieldCheck")}</div>
          <div class="text">No threats detected</div>
          <div class="sub">System is monitoring. Alerts will appear here in real time.</div>
        </div>`;
      return;
    }

    this.listEl.innerHTML = "";
    filtered.forEach((ev) => this.listEl.appendChild(this.buildCard(ev)));
  },

  buildCard(ev) {
    const isNew = this.newIds.has(ev.id);
    const card = el("div", { class: `alert-card level-${ev.level}${isNew ? " new" : ""}` });
    if (ev.snapshot_url) {
      const img = el("img", { class: "alert-snapshot", src: ev.snapshot_url, alt: ev.description, loading: "lazy" });
      img.onerror = () => {
        img.replaceWith(el("div", { class: "alert-snapshot-placeholder" }, "Snapshot unavailable"));
      };
      card.appendChild(img);
    } else {
      card.appendChild(el("div", { class: "alert-snapshot-placeholder" }, "No snapshot"));
    }
    const body = el("div", { class: "alert-body" });
    body.innerHTML = `
      <div class="alert-header">
        <span class="alert-level-badge level-${ev.level}"><span class="dot"></span>${ev.level}</span>
        <span class="alert-time">${formatTime(new Date(ev.timestamp * 1000))}</span>
      </div>
      <div class="alert-title">${escapeHtml(ev.description)}</div>
      <div class="alert-conf">Confidence: <span class="num">${(ev.confidence * 100).toFixed(0)}%</span></div>
      <div class="alert-meta">
        ${(ev.source_labels || []).map((s) => `<span class="alert-tag">${escapeHtml(s)}</span>`).join("")}
      </div>
    `;
    card.appendChild(body);
    return card;
  },
};

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

window.alerts = alerts;
