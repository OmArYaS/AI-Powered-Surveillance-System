// faces.js — register, list, detect, promote, delete

const faces = {
  capturedImage: null,
  els: {},

  init() {
    this.els.nameInput = document.getElementById("reg-name");
    this.els.previewArea = document.getElementById("reg-preview");
    this.els.previewImg = document.getElementById("reg-preview-img");
    this.els.knownList = document.getElementById("known-list");
    this.els.detectedList = document.getElementById("detected-list");
    this.els.detectedCount = document.getElementById("detected-count");

    this._loadAll();
    setInterval(() => this._loadDetected(), 5000);
  },

  async _loadAll() {
    await Promise.all([this._loadKnown(), this._loadDetected()]);
  },

  async _loadKnown() {
    try {
      const d = await api.getFaces();
      const list = this.els.knownList;
      if (!d.faces || d.faces.length === 0) {
        list.innerHTML = renderEmpty(icon("user"), "No faces registered", "Register faces to enable named recognition");
        return;
      }
      list.innerHTML = d.faces.map((name) => `
        <div class="person-card">
          <div class="person-avatar known">${icon("user")}</div>
          <div class="person-info">
            <div class="person-name">${escapeHtml(name)}</div>
            <div class="person-meta">Registered</div>
          </div>
          <div class="person-actions">
            <button class="btn btn-icon-sm btn-ghost" title="Delete" onclick="faces.deleteKnown('${escapeAttr(name)}')">${icon("trash")}</button>
          </div>
        </div>
      `).join("");
    } catch (e) {
      showToast("Failed to load faces: " + e.message, "error");
    }
  },

  async _loadDetected() {
    try {
      const d = await api.getDetected();
      const list = this.els.detectedList;
      const count = (d.persons || []).length;
      if (this.els.detectedCount) this.els.detectedCount.textContent = `${count} unique`;
      if (count === 0) {
        list.innerHTML = renderEmpty(icon("detect"), "No visitors detected", "Anyone appearing on camera will be logged here");
        return;
      }
      list.innerHTML = d.persons.map((p) => `
        <div class="person-card">
          <div class="person-avatar auto">
            <img src="${p.snapshot_url}?t=${p.last_seen}" alt="" onerror="this.style.display='none'"/>
          </div>
          <div class="person-info">
            <div class="person-name auto">${escapeHtml(p.person_id)}</div>
            <div class="person-meta">${p.sample_count} sample${p.sample_count !== 1 ? "s" : ""} · last ${timeAgo(p.last_seen)}</div>
          </div>
          <div class="person-actions">
            <button class="btn btn-icon-sm btn-ghost" title="Assign name" style="color:var(--success)" onclick="faces.promote('${escapeAttr(p.person_id)}')">${icon("edit")}</button>
            <button class="btn btn-icon-sm btn-ghost" title="Delete" onclick="faces.deleteDetected('${escapeAttr(p.person_id)}')">${icon("trash")}</button>
          </div>
        </div>
      `).join("");
    } catch (e) {}
  },

  async capture() {
    const name = this.els.nameInput.value.trim();
    if (!name) {
      showToast("Enter a name first", "warning");
      this.els.nameInput.focus();
      return;
    }
    try {
      const res = await api.captureSnapshot();
      const blob = await res.blob();
      const reader = new FileReader();
      reader.onload = () => {
        this.capturedImage = reader.result.split(",")[1];
        this.els.previewImg.src = URL.createObjectURL(blob);
        this.els.previewArea.classList.remove("hidden");
      };
      reader.readAsDataURL(blob);
    } catch (e) {
      showToast("Capture failed: " + e.message, "error");
    }
  },

  cancel() {
    this.capturedImage = null;
    this.els.previewArea.classList.add("hidden");
    this.els.previewImg.src = "";
  },

  async register() {
    const name = this.els.nameInput.value.trim();
    if (!name) return showToast("Enter a name", "warning");
    if (!this.capturedImage) return showToast("Capture a photo first", "warning");
    try {
      await api.registerFace(name, this.capturedImage);
      showToast(`Registered "${name}"`, "success");
      this.els.nameInput.value = "";
      this.cancel();
      this._loadKnown();
    } catch (e) {
      showToast("Failed: " + e.message, "error");
    }
  },

  async deleteKnown(name) {
    const ok = await showModal({
      title: "Delete face",
      text: `Remove "${name}" from the known faces list? This will also remove the stored embeddings.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteFace(name);
      showToast(`Deleted "${name}"`, "success");
      this._loadKnown();
    } catch (e) {
      showToast("Failed: " + e.message, "error");
    }
  },

  async deleteDetected(personId) {
    const ok = await showModal({
      title: "Delete visitor",
      text: `Remove ${personId} from detected persons? This cannot be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteDetected(personId);
      showToast(`Deleted ${personId}`, "success");
      this._loadDetected();
    } catch (e) {
      showToast("Failed: " + e.message, "error");
    }
  },

  async promote(personId) {
    const name = await showPrompt({
      title: "Assign name",
      text: `Assign a real name to ${personId}. The person will be moved from detected to known.`,
      placeholder: "Enter real name...",
    });
    if (!name) return;
    try {
      await api.promoteDetected(personId, name);
      showToast(`${personId} → ${name}`, "success");
      this._loadAll();
    } catch (e) {
      showToast("Failed: " + e.message, "error");
    }
  },
};

function renderEmpty(iconSvg, title, text) {
  return `<div class="empty-state">
    ${iconSvg}
    <div class="empty-state-title">${title}</div>
    <div class="empty-state-text">${text}</div>
  </div>`;
}

function timeAgo(ts) {
  if (!ts) return "—";
  const sec = Math.floor((Date.now() / 1000) - ts);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

function escapeAttr(str) {
  return String(str).replace(/'/g, "&#39;");
}
