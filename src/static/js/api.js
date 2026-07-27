// api.js — fetch wrapper with error handling

const api = {
  async _fetch(url, options = {}) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try { detail = JSON.parse(text).detail || text; } catch {}
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) return res.json();
      return res;
    } catch (e) {
      if (e.message === "Failed to fetch") throw new Error("Network error");
      throw e;
    }
  },

  // Settings
  getSettings() {
    return this._fetch("/api/settings");
  },
  updateSettings(payload) {
    return this._fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  // Detections
  getDetections() {
    return this._fetch("/api/detections");
  },

  // Faces
  getFaces() {
    return this._fetch("/api/faces");
  },
  registerFace(name, base64Image) {
    return this._fetch("/api/faces/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, image: base64Image }),
    });
  },
  deleteFace(name) {
    return this._fetch("/api/faces/" + encodeURIComponent(name), { method: "DELETE" });
  },
  getDetected() {
    return this._fetch("/api/faces/auto");
  },
  deleteDetected(personId) {
    return this._fetch("/api/faces/auto/" + personId, { method: "DELETE" });
  },
  promoteDetected(personId, name) {
    return this._fetch("/api/faces/auto/" + personId + "/promote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  },
  getFaceStats() {
    return this._fetch("/api/faces/stats");
  },
  captureSnapshot() {
    return this._fetch("/api/faces/snapshot");
  },

  // Threats
  threats: {
    list(limit = 50, level = null) {
      const q = new URLSearchParams();
      if (limit) q.set("limit", String(limit));
      if (level) q.set("level", level);
      return this._fetch("/api/threats" + (q.toString() ? "?" + q.toString() : ""));
    },
    clear() {
      return this._fetch("/api/threats", { method: "DELETE" });
    },
  },

  // Items (theft detection)
  items: {
    list() {
      return this._fetch("/api/items");
    },
    events(limit = 100) {
      return this._fetch("/api/items/events?limit=" + limit);
    },
    clear() {
      return this._fetch("/api/items", { method: "DELETE" });
    },
    forget(itemId) {
      return this._fetch("/api/items/" + encodeURIComponent(itemId), { method: "DELETE" });
    },
  },
};
