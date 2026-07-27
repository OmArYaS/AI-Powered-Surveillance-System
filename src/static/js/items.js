// items.js — Items tab: live item tracking + ownership events

const items = {
  ws: null,
  wsStatus: "disconnected",
  wsReconnectTimer: null,
  reconnectDelay: 2000,

  itemsList: [],
  eventsList: [],
  filter: "all",
  newIds: new Set(),

  init() {
    if (!$("#items-tbody")) return;

    $$(".items-filters .filter-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        $$(".items-filters .filter-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        this.filter = chip.dataset.filter;
        this.renderTable();
      });
    });

    $("#btn-clear-items")?.addEventListener("click", async () => {
      const ok = await showModal({
        title: "Clear all items?",
        text: "This will clear the item tracking state. The events log is preserved.",
        confirmText: "Clear",
        danger: true,
      });
      if (!ok) return;
      await API.items.clear();
      this.itemsList = [];
      this.renderTable();
      showToast("Items cleared", "success");
    });

    this.connectWS();
    this.refresh();
    setInterval(() => this.refresh(), 5000);
  },

  async refresh() {
    try {
      const [data, ev] = await Promise.all([
        API.items.list(),
        API.items.events(100),
      ]);
      this.itemsList = data.items || [];
      const knownEventIds = new Set(this.eventsList.map((e) => e.id));
      const fresh = (ev.events || []).filter((e) => !knownEventIds.has(e.id));
      this.eventsList = ev.events || [];
      this.renderStats(data.stats || {});
      this.renderTable();
      this.renderTimeline();
      if (fresh.length) {
        const top = fresh[0];
        const sev = top.type === "theft" ? "error" : top.type === "drop" ? "info" : "success";
        showToast(`${top.type.toUpperCase()}: ${top.description}`, sev, 3500);
        fresh.forEach((e) => this.newIds.add(e.id));
        setTimeout(() => {
          fresh.forEach((e) => this.newIds.delete(e.id));
          this.renderTimeline();
        }, 2500);
      }
    } catch (e) {
      console.warn("items refresh failed:", e);
    }
  },

  connectWS() {
    if (this.ws) {
      try { this.ws.close(); } catch {}
    }
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/items`;
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
        if (msg.type === "item_event" && msg.data) {
          this.onNewEvent(msg.data);
        } else if (msg.type === "snapshot" && msg.data) {
          // ignore
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
    const el = $("#items-ws-status");
    if (!el) return;
    el.classList.remove("connected", "disconnected");
    el.classList.add(s);
    el.querySelector(".ws-text").textContent =
      s === "connected" ? "Live" : "Reconnecting...";
  },

  onNewEvent(event) {
    this.eventsList.unshift(event);
    this.newIds.add(event.id);
    this.renderTimeline();
    this.renderStats({
      active: this.itemsList.length,
      ...this.computeStats(),
    });
    this.refresh();
    const sev = event.type === "theft" ? "error" : event.type === "drop" ? "info" : "success";
    showToast(`${event.type.toUpperCase()}: ${event.description}`, sev, 3500);
  },

  computeStats() {
    const stats = { by_state: { held: 0, stationary: 0, abandoned: 0, new: 0 }, thefts: 0, owned: 0, unowned: 0 };
    for (const it of this.itemsList) {
      if (stats.by_state[it.state] !== undefined) stats.by_state[it.state]++;
      if (it.owner_id) stats.owned++;
      else stats.unowned++;
    }
    stats.thefts = this.eventsList.filter((e) => e.type === "theft").length;
    return stats;
  },

  renderStats(stats) {
    $("#stat-items-held").textContent = stats.by_state?.held || 0;
    $("#stat-items-stationary").textContent = stats.by_state?.stationary || 0;
    $("#stat-items-abandoned").textContent = stats.by_state?.abandoned || 0;
    $("#stat-items-thefts").textContent = stats.thefts || 0;

    const heldEl = $("#stat-items-held-status");
    if (heldEl) heldEl.textContent = (stats.by_state?.held || 0) > 0 ? "In use" : "Idle";

    const abEl = $("#stat-items-abandoned-status");
    if (abEl) abEl.textContent = (stats.by_state?.abandoned || 0) > 0 ? "Forgotten" : "Clear";

    const theftCard = $("#items-theft-card");
    if (theftCard) {
      if ((stats.thefts || 0) > 0) theftCard.classList.add("danger-pulse");
      else theftCard.classList.remove("danger-pulse");
    }
    const tStatus = $("#stat-items-thefts-status");
    if (tStatus) {
      tStatus.textContent = (stats.thefts || 0) > 0 ? "Detected" : "Safe";
      tStatus.classList.toggle("active", (stats.thefts || 0) === 0);
    }

    const badge = $("#nav-badge-items");
    if (badge) {
      const t = stats.thefts || 0;
      if (t > 0) {
        badge.textContent = t;
        badge.style.display = "";
        badge.classList.add("danger");
      } else {
        badge.style.display = "none";
      }
    }

    $("#items-count").textContent = `${this.itemsList.length} active`;
    $("#events-count").textContent = `${this.eventsList.length} events`;
  },

  renderTable() {
    const tbody = $("#items-tbody");
    if (!tbody) return;
    const filtered = this.filterItems(this.itemsList);
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state-text">No items match the filter</td></tr>`;
      return;
    }
    tbody.innerHTML = "";
    filtered.forEach((it) => tbody.appendChild(this.buildRow(it)));
  },

  filterItems(items) {
    if (this.filter === "all") return items;
    if (this.filter === "owned") return items.filter((i) => i.owner_id);
    if (this.filter === "unowned") return items.filter((i) => !i.owner_id);
    return items.filter((i) => i.state === this.filter);
  },

  buildRow(it) {
    const tr = el("tr");
    const ownerHtml = it.owner_id
      ? `<span class="owner-cell">${icon("owner")}${escapeHtml(it.owner_id)}</span>`
      : `<span class="owner-cell unowned">— unowned —</span>`;
    const statePill = `<span class="state-pill ${it.state}">${it.state}</span>`;
    tr.innerHTML = `
      <td class="item-id">${escapeHtml(it.id)}</td>
      <td>${escapeHtml(it.type)}</td>
      <td>${statePill}</td>
      <td>${ownerHtml}</td>
      <td class="time-cell">${formatTime(new Date(it.first_seen * 1000))}</td>
      <td class="time-cell">${formatTime(new Date(it.last_seen * 1000))}</td>
      <td><button class="btn-action" data-id="${escapeHtml(it.id)}">Forget</button></td>
    `;
    tr.querySelector(".btn-action")?.addEventListener("click", async () => {
      const ok = await showModal({
        title: "Forget this item?",
        text: `Stop tracking ${it.id} (${it.type}). The events log is preserved.`,
        confirmText: "Forget",
        danger: true,
      });
      if (!ok) return;
      await API.items.forget(it.id);
      this.itemsList = this.itemsList.filter((x) => x.id !== it.id);
      this.renderTable();
      showToast("Item forgotten", "success");
    });
    return tr;
  },

  renderTimeline() {
    const list = $("#events-list");
    if (!list) return;
    if (this.eventsList.length === 0) {
      list.innerHTML = `<div class="empty-state-text">No events yet</div>`;
      return;
    }
    list.innerHTML = "";
    this.eventsList.slice(0, 100).forEach((e) => list.appendChild(this.buildEventRow(e)));
  },

  buildEventRow(e) {
    const isNew = this.newIds.has(e.id);
    const row = el("div", { class: `event-row ${e.type}${isNew ? " new" : ""}` });
    const iconKey =
      e.type === "claim" ? "owner" :
      e.type === "drop" ? "package" :
      e.type === "theft" ? "thief" :
      e.type === "returned" ? "hand" : "clock";
    row.innerHTML = `
      <div class="event-icon">${icon(iconKey)}</div>
      <div class="event-body">
        <div class="event-desc">${escapeHtml(e.description)}</div>
        <div class="event-meta">
          <span>${formatTime(new Date(e.timestamp * 1000))}</span>
          <span>${escapeHtml(e.item_id)}</span>
          <span class="conf">conf: ${(e.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    `;
    return row;
  },
};

window.items = items;
