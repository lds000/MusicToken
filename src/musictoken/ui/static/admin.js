(function () {
  const $ = (id) => document.getElementById(id);

  function setMsg(text, kind) {
    const el = $("form-msg");
    el.textContent = text || "";
    el.className = "form-msg" + (kind ? " " + kind : "");
  }

  // --- Form submit -------------------------------------------------------
  $("chip-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      uid: $("f-uid").value.trim(),
      label: $("f-label").value.trim(),
      genre: $("f-genre").value,
      action_type: $("f-action").value,
      payload: $("f-payload").value.trim(),
    };
    setMsg("Saving…");
    try {
      const res = await fetch("/api/chips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const chip = await res.json();
      addOrUpdateRow(chip);
      setMsg("Saved.", "ok");
    } catch (err) {
      setMsg("Save failed: " + err.message, "err");
    }
  });

  $("btn-simulate").addEventListener("click", async () => {
    const uid = $("f-uid").value.trim();
    if (!uid) { setMsg("Enter a UID first.", "err"); return; }
    await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid }),
    });
    setMsg("Simulated scan of " + uid, "ok");
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
    row.innerHTML = `
      <td class="mono">${escapeHtml(chip.uid)}</td>
      <td>${escapeHtml(chip.label || "")}</td>
      <td>${escapeHtml(chip.genre || "")}</td>
      <td>${escapeHtml(chip.action_type || "")}</td>
      <td class="mono small">${escapeHtml(JSON.stringify(chip.payload || {}))}</td>
      <td>${chip.scan_count ?? 0}</td>
      <td><button class="ghost danger" data-action="delete">Delete</button></td>
    `;
  }

  document.addEventListener("click", async (e) => {
    if (e.target.matches('[data-action="delete"]')) {
      const row = e.target.closest("tr");
      const uid = row.dataset.uid;
      if (!confirm("Delete chip " + uid + "?")) return;
      const res = await fetch("/api/chips/" + encodeURIComponent(uid), { method: "DELETE" });
      if (res.ok) {
        row.remove();
        $("chip-count").textContent = $("chip-rows").querySelectorAll("tr").length;
      }
    }
  });

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
})();
