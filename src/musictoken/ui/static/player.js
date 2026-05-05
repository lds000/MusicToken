(function () {
  const $ = (id) => document.getElementById(id);

  function renderNowPlaying(np) {
    const stateEl = $("np-state");
    const title = $("np-title");
    const artist = $("np-artist");
    const source = $("np-source");
    const cover = $("np-cover");

    if (!np || !np.title) {
      stateEl.textContent = "Idle";
      title.textContent = "Tap a chip";
      artist.textContent = "";
      source.textContent = "";
      cover.style.backgroundImage = "";
      return;
    }
    stateEl.textContent = np.is_playing ? "Now playing" : "Paused";
    title.textContent = np.title || "";
    artist.textContent = np.artist || "";
    source.textContent = np.source || "";
    cover.style.backgroundImage = np.image ? `url("${np.image}")` : "";
  }

  function renderScan(scan) {
    if (!scan) return;
    $("ls-uid").textContent = scan.uid || "—";
    if (scan.chip && scan.chip.label) {
      $("ls-chip").textContent = `${scan.chip.label} (${scan.chip.action_type})`;
    } else if (scan.known === false) {
      $("ls-chip").textContent = "unknown chip — program it in Admin";
    } else {
      $("ls-chip").textContent = "";
    }
  }

  async function refreshState() {
    try {
      const res = await fetch("/api/state");
      const data = await res.json();
      renderNowPlaying(data.now_playing);
      renderScan(data.last_scan);
    } catch (e) {
      console.warn("state fetch failed", e);
    }
  }

  function connectEvents() {
    const es = new EventSource("/api/events");
    es.addEventListener("now_playing", (e) => renderNowPlaying(JSON.parse(e.data).payload));
    es.addEventListener("scan", (e) => renderScan(JSON.parse(e.data).payload));
    es.onerror = () => { setTimeout(connectEvents, 2000); es.close(); };
  }

  document.querySelectorAll(".ctl").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const verb = btn.dataset.verb;
      btn.disabled = true;
      try { await fetch(`/api/control/${verb}`, { method: "POST" }); }
      finally { btn.disabled = false; }
    });
  });

  refreshState();
  connectEvents();
})();
