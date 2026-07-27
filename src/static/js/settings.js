// settings.js — load/save settings, toggles, sliders

const settings = {
  data: {},
  els: {},
  dirty: false,

  init() {
    this.els = {
      host: document.getElementById("set-host"),
      port: document.getElementById("set-port"),
      user: document.getElementById("set-user"),
      pass: document.getElementById("set-pass"),
      channel: document.getElementById("set-channel"),
      quality: document.getElementById("set-quality"),
      qualityVal: document.getElementById("set-quality-val"),
      motion: document.getElementById("set-motion"),
      recording: document.getElementById("set-recording"),
      notifications: document.getElementById("set-notifications"),
      night: document.getElementById("set-night"),
      save: document.getElementById("set-save"),
      reset: document.getElementById("set-reset"),
    };
    this._load();
    this._bindEvents();
  },

  async _load() {
    try {
      const d = await api.getSettings();
      this.data = d;
      this.els.host.value = d.rtsp_host || "";
      this.els.port.value = d.rtsp_port || 554;
      this.els.user.value = d.rtsp_username || "";
      this.els.pass.value = d.rtsp_password || "";
      this.els.channel.value = d.rtsp_channel || 101;
      this.els.quality.value = d.jpeg_quality || 85;
      this.els.qualityVal.textContent = d.jpeg_quality || 85;
      this._setToggle(this.els.motion, d.motion_detection);
      this._setToggle(this.els.recording, d.auto_recording);
      this._setToggle(this.els.notifications, d.notifications);
      this._setToggle(this.els.night, d.night_vision);
    } catch (e) {
      showToast("Failed to load settings: " + e.message, "error");
    }
  },

  _setToggle(el, on) {
    if (!el) return;
    el.classList.toggle("on", !!on);
  },

  _readToggle(el) {
    return el && el.classList.contains("on");
  },

  _bindEvents() {
    this.els.quality?.addEventListener("input", () => {
      this.els.qualityVal.textContent = this.els.quality.value;
    });
    [this.els.motion, this.els.recording, this.els.notifications, this.els.night].forEach((t) => {
      t?.addEventListener("click", () => t.classList.toggle("on"));
    });
    this.els.save?.addEventListener("click", () => this._save());
    this.els.reset?.addEventListener("click", () => this._load());
  },

  async _save() {
    const payload = {
      rtsp_host: this.els.host.value,
      rtsp_port: parseInt(this.els.port.value, 10),
      rtsp_username: this.els.user.value,
      rtsp_password: this.els.pass.value,
      rtsp_channel: parseInt(this.els.channel.value, 10),
      jpeg_quality: parseInt(this.els.quality.value, 10),
      motion_detection: this._readToggle(this.els.motion),
      auto_recording: this._readToggle(this.els.recording),
      notifications: this._readToggle(this.els.notifications),
      night_vision: this._readToggle(this.els.night),
    };
    try {
      const d = await api.updateSettings(payload);
      this.data = d;
      showToast("Settings saved", "success", 2000);
    } catch (e) {
      showToast("Save failed: " + e.message, "error");
    }
  },
};
