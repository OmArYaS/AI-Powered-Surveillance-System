// app.js — bootstraps the app, tab switching, clock

const app = {
  init() {
    this._bindNav();
    this._updateClock();
    setInterval(() => this._updateClock(), 1000);
    this._initViews();
  },

  _initViews() {
    stream.init();
    dashboard.init();
    faces.init();
    settings.init();
    alerts.init();
    items.init();
  },

  _bindNav() {
    $$(".nav-item").forEach((n) => {
      n.addEventListener("click", () => {
        const view = n.dataset.view;
        this.switchView(view);
      });
    });
  },

  switchView(name) {
    $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === name));
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
    const titles = {
      dashboard: "Live Monitor",
      faces: "Face Registry",
      alerts: "Threat Alerts",
      items: "Item Tracking",
      settings: "Settings",
    };
    const t = document.getElementById("topbar-title");
    if (t) t.textContent = titles[name] || "";
  },

  _updateClock() {
    const c = document.getElementById("topbar-clock");
    if (c) c.textContent = formatTime();
  },
};

document.addEventListener("DOMContentLoaded", () => app.init());
