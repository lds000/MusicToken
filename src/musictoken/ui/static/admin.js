(function () {
  const $ = (id) => document.getElementById(id);

  function setMsg(text, kind) {
    const el = $("form-msg");
    el.textContent = text || "";
    el.className = "form-msg" + (kind ? " " + kind : "");
  }

  // --- Live preview ------------------------------------------------------
  let printMeta = {};
  let stlAvailable = false;
  fetch("/api/print_meta").then(r => r.json()).then(d => { printMeta = d; updatePreview(); });
  fetch("/api/printing/status").then(r => r.json()).then(d => {
    stlAvailable = !!d.openscad_available;
    updatePrintBadge();
  });

  function updatePrintBadge() {
    const btn = $("btn-print");
    if (!btn) return;
    if (stlAvailable) {
      btn.textContent = "🖨 Print chip (save + download .stl)";
      btn.title = "Save chip and download an STL ready for Creality Print";
    } else {
      btn.textContent = "🖨 Print chip (save + download .scad)";
      btn.title = "OpenSCAD not found — falling back to .scad. Install OpenSCAD to get STL directly.";
    }
  }

  function splitLabel(label) {
    label = (label || "").toUpperCase();
    const sep = label.includes(" / ") ? " / " : (label.includes("/") ? "/" : null);
    if (!sep) return [label.slice(0, 12), ""];
    const i = label.indexOf(sep);
    return [label.slice(0, i).trim().slice(0, 12), label.slice(i + sep.length).trim().slice(0, 12)];
  }

  function updatePreview() {
    const genre = $("f-genre").value;
    const meta = printMeta[genre] || { name: "—", hex: "#475C7A", filament: "pick a genre for filament hint" };
    $("pv-disc").setAttribute("fill", meta.hex);
    $("pv-ring-in").setAttribute("fill", meta.hex);
    $("pv-color-name").textContent = meta.name;
    $("pv-filament").textContent = meta.filament;

    const [top, bottom] = splitLabel($("f-label").value);
    $("pv-top").textContent = top;
    $("pv-bottom").textContent = bottom;
  }
  ["f-genre", "f-label"].forEach(id => $(id).addEventListener("input", updatePreview));
  $("f-genre").addEventListener("change", updatePreview);

  // --- Save chip (returns the saved chip dict) ---------------------------
  async function saveChip() {
    const body = {
      uid: $("f-uid").value.trim(),
      label: $("f-label").value.trim(),
      genre: $("f-genre").value,
      action_type: $("f-action").value,
      payload: $("f-payload").value.trim(),
    };
    const res = await fetch("/api/chips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  }

  $("chip-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    setMsg("Saving…");
    try {
      const chip = await saveChip();
      $("f-uid").value = chip.uid;
      addOrUpdateRow(chip);
      setMsg("Saved as " + chip.uid + ".", "ok");
    } catch (err) {
      setMsg("Save failed: " + err.message, "err");
    }
  });

  // --- Print: save + download (STL preferred, .scad fallback) -----------
  $("btn-print").addEventListener("click", async () => {
    if (!$("f-label").value.trim()) {
      setMsg("Add a label before printing.", "err"); return;
    }
    if (stlAvailable) {
      $("form-msg").innerHTML = 'Saving and rendering STL (~15–20 s) <span class="spinner"></span>';
      $("form-msg").className = "form-msg";
    } else {
      setMsg("Saving and generating .scad…");
    }
    try {
      const chip = await saveChip();
      $("f-uid").value = chip.uid;
      addOrUpdateRow(chip);
      const fmt = await downloadFor(chip.uid);
      const verb = fmt === "stl"
        ? "Downloaded " + chip.uid + ".stl — opens in your default STL app (Creality Print)."
        : "Downloaded " + chip.uid + ".scad — open in OpenSCAD → F6 → Export STL.";
      setMsg(verb, "ok");
    } catch (err) {
      setMsg("Print failed: " + err.message, "err");
    }
  });

  // Returns the format that ended up downloading ("stl" or "scad").
  async function downloadFor(uid) {
    if (stlAvailable) {
      // Probe with GET; if 503, OpenSCAD is missing → fall back.
      const head = await fetch("/api/chips/" + encodeURIComponent(uid) + "/stl",
                               { method: "GET" });
      if (head.ok) {
        // Re-trigger as a download via anchor (we already have the bytes
        // but a fresh GET via <a> kicks the browser's download UI).
        const blob = await head.blob();
        triggerBlobDownload(blob, uid + ".stl");
        return "stl";
      }
      const err = await head.json().catch(() => ({}));
      if (err.kind === "openscad_missing") {
        stlAvailable = false;
        updatePrintBadge();
        setMsg("OpenSCAD not installed — falling back to .scad. " +
               "Install with: winget install OpenSCAD.OpenSCAD", "err");
      } else {
        setMsg("STL render failed: " + (err.error || head.statusText) + " — falling back to .scad", "err");
      }
    }
    const a = document.createElement("a");
    a.href = "/api/chips/" + encodeURIComponent(uid) + "/scad";
    a.download = "";
    document.body.appendChild(a); a.click(); a.remove();
    return "scad";
  }

  function triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // --- Claim: re-key DESIGN-... to the latest real scan ------------------
  $("btn-claim").addEventListener("click", async () => {
    const uid = $("f-uid").value.trim();
    if (!uid) { setMsg("No design loaded — save first.", "err"); return; }
    if (!uid.startsWith("DESIGN-")) {
      if (!confirm("This UID isn't a DESIGN- placeholder. Claim anyway?")) return;
    }
    setMsg("Tap a real chip on the reader, then click Claim again. Or claim the last scan now.");
    const res = await fetch("/api/chips/" + encodeURIComponent(uid) + "/claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) {
      setMsg("Claim failed: " + await res.text(), "err");
      return;
    }
    const chip = await res.json();
    document.querySelector(`tr[data-uid="${uid}"]`)?.remove();
    addOrUpdateRow(chip);
    $("f-uid").value = chip.uid;
    setMsg("Migrated to real UID " + chip.uid + ". Tap that chip now to test.", "ok");
  });

  $("btn-autofill").addEventListener("click", async () => {
    const payload = $("f-payload").value.trim();
    if (!payload) { setMsg("Paste a Spotify URI / URL into payload first.", "err"); return; }
    setMsg("Asking AI… ");
    $("form-msg").innerHTML = 'Asking AI <span class="spinner"></span>';
    try {
      const res = await fetch("/api/ai/autofill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload, action_type: $("f-action").value }),
      });
      if (!res.ok) throw new Error(await res.text());
      const sug = await res.json();
      if (sug.label) $("f-label").value = sug.label;
      if (sug.genre) $("f-genre").value = sug.genre;
      setMsg("Autofilled. Review and save.", "ok");
    } catch (err) {
      setMsg("Autofill failed: " + err.message, "err");
    }
  });

  // --- Suggestions panel -------------------------------------------------
  $("suggest-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = $("sg-prompt").value.trim();
    const count = parseInt($("sg-count").value, 10) || 6;
    if (!prompt) return;
    const out = $("suggest-results");
    out.innerHTML = '<div class="hint">Thinking <span class="spinner"></span></div>';
    try {
      const res = await fetch("/api/ai/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, count }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      renderSuggestions(data.suggestions || []);
    } catch (err) {
      out.innerHTML = '<div class="form-msg err">' + err.message + "</div>";
    }
  });

  function renderSuggestions(list) {
    const out = $("suggest-results");
    if (!list.length) {
      out.innerHTML = '<div class="hint">No suggestions came back.</div>';
      return;
    }
    out.innerHTML = "";
    list.forEach((s, i) => {
      const card = document.createElement("div");
      card.className = "suggest-card";
      card.innerHTML = `
        <div>
          <div class="sc-title">${escapeHtml(s.label || "(no label)")}</div>
          <div class="sc-meta">${escapeHtml(s.genre || "")} · ${escapeHtml(s.action_type || "")}${s.reason ? " · " + escapeHtml(s.reason) : ""}</div>
          <div class="sc-payload">${escapeHtml(JSON.stringify(s.payload || {}))}</div>
        </div>
        <button class="primary sc-add">Use</button>
      `;
      card.querySelector(".sc-add").addEventListener("click", () => {
        $("f-label").value = s.label || "";
        if (s.genre) $("f-genre").value = s.genre;
        if (s.action_type) $("f-action").value = s.action_type;
        $("f-payload").value = JSON.stringify(s.payload || {}, null, 2);
        $("f-uid").focus();
        setMsg("Loaded suggestion #" + (i + 1) + " — tap a chip and save.", "ok");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      out.appendChild(card);
    });
  }

  // --- Live SSE: autofill UID on real / simulated scan -------------------
  function connectEvents() {
    const es = new EventSource("/api/events");
    es.addEventListener("scan", (e) => {
      const evt = JSON.parse(e.data);
      const uid = evt.payload?.uid;
      if (uid) $("f-uid").value = uid;
    });
    es.onerror = () => { setTimeout(connectEvents, 2000); es.close(); };
  }
  connectEvents();

  // --- Chip table rendering ---------------------------------------------
  function addOrUpdateRow(chip) {
    const tbody = $("chip-rows");
    let row = tbody.querySelector(`tr[data-uid="${chip.uid}"]`);
    if (!row) {
      row = document.createElement("tr");
      row.dataset.uid = chip.uid;
      tbody.prepend(row);
      $("chip-count").textContent = tbody.querySelectorAll("tr").length;
    }
    row.dataset.label = chip.label || "";
    row.dataset.genre = chip.genre || "";
    row.dataset.action = chip.action_type || "";
    row.dataset.payload = JSON.stringify(chip.payload || {});
    row.innerHTML = `
      <td class="mono">${escapeHtml(chip.uid)}</td>
      <td>${escapeHtml(chip.label || "")}</td>
      <td>${escapeHtml(chip.genre || "")}</td>
      <td>${escapeHtml(chip.action_type || "")}</td>
      <td class="mono small">${escapeHtml(JSON.stringify(chip.payload || {}))}</td>
      <td>${chip.scan_count ?? 0}</td>
      <td class="row-actions">
        <button class="ghost" data-row-action="print" title="Save + download .scad">🖨</button>
        <button class="ghost danger" data-row-action="delete" title="Delete">✕</button>
      </td>
    `;
  }

  function loadRowIntoForm(row) {
    $("f-uid").value = row.dataset.uid || "";
    $("f-label").value = row.dataset.label || "";
    $("f-genre").value = row.dataset.genre || "";
    $("f-action").value = row.dataset.action || "spotify";
    let payload = row.dataset.payload || "{}";
    try { payload = JSON.stringify(JSON.parse(payload), null, 2); } catch (_) {}
    $("f-payload").value = payload;
    updatePreview();
    setMsg("Loaded " + row.dataset.uid + " — edit and Save / Print, or click 🖨 in the row.");
    document.querySelector(".design-grid")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Trigger an STL (preferred) or .scad download for the given chip.
  async function downloadFromRow(uid) {
    const fmt = await downloadFor(uid);
    setMsg("Downloaded " + uid + "." + fmt + (fmt === "stl"
      ? " — opens in your default STL app (Creality Print)."
      : " — open in OpenSCAD → F6 → Export STL."), "ok");
  }

  // Single delegated handler for the table.
  document.getElementById("chip-rows").addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-row-action]");
    const row = e.target.closest("tr[data-uid]");
    if (!row) return;
    const uid = row.dataset.uid;

    if (btn) {
      e.stopPropagation();
      const action = btn.dataset.rowAction;
      if (action === "print") {
        downloadFromRow(uid);
        return;
      }
      if (action === "delete") {
        if (!confirm("Delete chip " + uid + "?")) return;
        const res = await fetch("/api/chips/" + encodeURIComponent(uid), { method: "DELETE" });
        if (res.ok) {
          row.remove();
          $("chip-count").textContent = $("chip-rows").querySelectorAll("tr").length;
        }
        return;
      }
    }
    // Row click (not on a button) → load into form.
    loadRowIntoForm(row);
  });

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
})();
