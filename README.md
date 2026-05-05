# MusicToken

A physical, social, AI-powered music system built around NFC tokens.
**Grab → Scan → Play.**

See [`Concept.md`](./Concept.md) for the original design spec.

---

## What this repo contains

| Layer | Path | Purpose |
|------|------|---------|
| App | `src/musictoken/` | Python service: NFC reader, chip registry, action runner, Flask kiosk UI |
| Web UI | `src/musictoken/ui/` | Touchscreen-friendly player + admin/programmer screens |
| Hardware | `hardware/` | OpenSCAD parametric top-plate model |
| Scripts | `scripts/` | CLI utilities (program chips, list chips, dump DB) |
| Service | `deploy/` | systemd unit + Chromium kiosk launcher for Pi |
| Tests | `tests/` | Unit tests |

---

## Architecture at a glance

```
 ┌──────────────────────────┐        ┌──────────────────────┐
 │ NFC Reader (PN532 / RC522│──UID──▶│   ChipRegistry       │
 │  / mock for dev)         │        │   (SQLite)           │
 └──────────────────────────┘        └─────────┬────────────┘
                                               │ Action spec
                                               ▼
 ┌──────────────────────────┐        ┌──────────────────────┐
 │  Flask kiosk UI          │◀──SSE──│   ActionRunner       │
 │  (player + admin)        │        │   (Spotify, radio,   │
 └──────────────────────────┘        │    mood, command)    │
                                     └──────────────────────┘
```

- **Decoupled backends.** The NFC reader and music player are pluggable. On
  Windows/macOS the mock backends let you build and demo end-to-end without
  hardware. On a Pi, swap in the real driver via `config.yaml`.
- **Stateless UI.** The Flask app subscribes to a server-sent-events stream
  emitted by the core service, so the touchscreen always reflects what is
  actually playing.

---

## Quick start (any OS — mock mode)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m musictoken --config config/config.yaml
```

Open http://localhost:8080 in a browser. In mock mode the admin page has a
"Simulate scan" button so you can drive the system without an NFC reader.

---

## Raspberry Pi setup

1. **Hardware.** Recommended: Pi 4 + 7" touchscreen + PN532 board on I²C
   (or MFRC522 on SPI). Wire per the `docs/wiring.md` table.
2. **Install.**
   ```bash
   git clone <this-repo> /opt/musictoken
   cd /opt/musictoken
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt -r requirements-pi.txt
   ```
3. **Configure.** Edit `config/config.yaml`:
   ```yaml
   nfc:
     backend: pn532_i2c   # or mfrc522_spi, or mock
   player:
     backend: spotify     # or vlc, or mock
     spotify:
       client_id: ...
       client_secret: ...
       redirect_uri: http://localhost:8080/spotify/callback
       device_name: MusicTokenPi
   ```
4. **Enable services.**
   ```bash
   sudo cp deploy/musictoken.service /etc/systemd/system/
   sudo cp deploy/musictoken-kiosk.service /etc/systemd/system/
   sudo systemctl enable --now musictoken musictoken-kiosk
   ```

---

## Programming chips

Tap a chip on the reader from the **Admin → Program Chip** page, fill in the
form (genre, action type, payload), and save. Or from the CLI:

```bash
python -m scripts.program_chip --uid 04A2B3C4D5E6F7 \
       --genre rock --action spotify \
       --payload '{"uri": "spotify:album:1DFixLWuPkv3KT3TnV35m3"}' \
       --label "EAGLES / HOTEL CALIFORNIA"
```

List everything you've programmed:

```bash
python -m scripts.list_chips
```

---

## Hardware: 3D-printed top plate

`hardware/chip_top.scad` is a parametric OpenSCAD model that follows the
spec in `Concept.md`:

- 23.8 mm × 0.8 mm disc with 0.2 mm chamfer
- Top + bottom raised text bands (+0.3 mm) with engraved letters (-0.3 mm)
- Center ring icon
- Orientation notch at 12 o'clock

Open it in OpenSCAD and edit the parameters block at the top to render
each chip. Render → Export STL → slice → print at 0.12 mm layer height.

---

## License

MIT (see `LICENSE`).
