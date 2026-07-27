// stream.js — MJPEG stream controls (fullscreen, screenshot)

const stream = {
  el: null,
  startTime: Date.now(),
  durationEl: null,
  clockTimer: null,

  init() {
    this.el = document.getElementById("stream");
    this.durationEl = document.getElementById("stream-duration");
    this._bindControls();
    this._updateDuration();
    this.clockTimer = setInterval(() => this._updateDuration(), 1000);
  },

  _updateDuration() {
    if (!this.durationEl) return;
    const sec = Math.floor((Date.now() - this.startTime) / 1000);
    const h = String(Math.floor(sec / 3600)).padStart(2, "0");
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    this.durationEl.textContent = `${h}:${m}:${s}`;
  },

  _bindControls() {
    const fsBtn = document.getElementById("btn-fullscreen");
    const shotBtn = document.getElementById("btn-screenshot");
    const viewer = document.querySelector(".viewer");

    if (fsBtn && viewer) {
      fsBtn.addEventListener("click", () => {
        viewer.classList.toggle("fullscreen");
        if (viewer.classList.contains("fullscreen")) {
          viewer.style.position = "fixed";
          viewer.style.inset = "0";
          viewer.style.zIndex = "8000";
          viewer.style.borderRadius = "0";
        } else {
          viewer.style.position = "";
          viewer.style.inset = "";
          viewer.style.zIndex = "";
          viewer.style.borderRadius = "";
        }
      });
    }

    if (shotBtn) {
      shotBtn.addEventListener("click", () => this.screenshot());
    }
  },

  async screenshot() {
    if (!this.el) return;
    try {
      const blob = await api.captureSnapshot();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `screenshot-${Date.now()}.jpg`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("Screenshot saved", "success", 2000);
    } catch (e) {
      showToast("Screenshot failed: " + e.message, "error");
    }
  },
};
