// dashboard.js — live detection stats + face recognition panel

const dashboard = {
  threatEl: null,
  statEls: {},

  init() {
    this.statEls = {
      persons: { value: document.getElementById("stat-persons"), status: document.getElementById("stat-persons-status") },
      phones:  { value: document.getElementById("stat-phones"),  status: document.getElementById("stat-phones-status") },
      bags:    { value: document.getElementById("stat-bags"),    status: document.getElementById("stat-bags-status") },
      threats: { value: document.getElementById("stat-threats"), status: document.getElementById("stat-threats-status") },
    };
    this.threatEl = document.getElementById("threat-card");

    this._poll();
    setInterval(() => this._poll(), 1000);
    this._pollFaces();
    setInterval(() => this._pollFaces(), 2000);
  },

  async _poll() {
    try {
      const d = await api.getDetections();
      this._set("persons", d.persons, d.persons > 0 ? "Detected" : "Clear", d.persons > 0);
      this._set("phones",  d.phones,  d.phones  > 0 ? "Detected" : "Clear", d.phones  > 0);
      this._set("bags",    d.bags,    d.bags    > 0 ? "Detected" : "Clear", d.bags    > 0);
      this._setThreat(d.threats);
    } catch {}
  },

  _set(key, value, statusText, active) {
    const s = this.statEls[key];
    if (!s.value) return;
    s.value.textContent = value;
    if (s.status) {
      s.status.textContent = statusText;
      s.status.classList.toggle("active", active);
    }
  },

  _setThreat(n) {
    if (!this.threatEl) return;
    const status = this.statEls.threats.status;
    if (n > 0) {
      this.threatEl.classList.add("alert");
      if (status) {
        status.textContent = "ALERT";
        status.classList.add("alert");
        status.classList.remove("active");
      }
    } else {
      this.threatEl.classList.remove("alert");
      if (status) {
        status.textContent = "Safe";
        status.classList.remove("alert");
        status.classList.add("active");
      }
    }
    this.statEls.threats.value.textContent = n;
  },

  async _pollFaces() {
    try {
      const s = await api.getFaceStats();
      const el = document.getElementById("live-faces");
      if (!el) return;
      const tags = [];
      for (const name of s.known || []) {
        tags.push(`<div class="live-tag known"><span class="dot"></span>${escapeHtml(name)}</div>`);
      }
      for (const name of s.auto || []) {
        tags.push(`<div class="live-tag auto"><span class="dot"></span>${escapeHtml(name)}</div>`);
      }
      for (const name of s.new || []) {
        tags.push(`<div class="live-tag new"><span class="dot"></span>${escapeHtml(name)}</div>`);
      }
      el.innerHTML = tags.length
        ? tags.join("")
        : '<div class="empty-state-text" style="padding:1rem">No faces detected</div>';

      // Update nav badge with total unique visitors
      const totalEl = document.getElementById("nav-badge-faces");
      if (totalEl && s.total_visitors != null) {
        totalEl.textContent = s.total_visitors;
      }
    } catch {}
  },
};

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
