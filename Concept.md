# 🎧 NFC Music Chip System — Full Design & Manufacturing Spec

## Overview
This system uses NFC-enabled chips to trigger music, radio, and smart-home actions via a Raspberry Pi and touchscreen interface.

Each chip:
- Uses a 25mm NTAG215 NFC coin
- Has a 3D printed top plate
- Is color-coded by genre
- Contains minimal readable text (artist/song/action)

---

# 🧱 Physical Architecture

## Base (NFC Coin)
- Type: NTAG215
- Diameter: 25mm
- Thickness: ~1.5–2.0mm
- Material: PVC (black)
- Function: NFC communication layer

## Top Plate (3D Printed)
- Diameter: 23.8mm
- Thickness: 0.8mm
- Edge chamfer: 0.2mm
- Material: PLA+ or PETG
- Mount: bonded to NFC coin

### Visual Result
Creates a ~0.6mm black reveal ring around the edge.

---

# 📐 Layout Design

## Structure

TOP BAND      → Artist / Source
CENTER        → Universal icon (ring)
BOTTOM BAND   → Song / Action

## Dimensions

- Top band: 4.0–4.5mm height
- Bottom band: 4.0–4.5mm height
- Center icon: 6–7mm diameter
- Margins: ≥1mm

---

# 🔤 Typography

- Font: Bold sans-serif
- Case: ALL CAPS
- Min stroke: 0.6–0.8mm
- Max characters: ~10 per line

Examples:
- EAGLES
- CNN
- WILD
- DREAMS

---

# 🎯 Icon

- Universal center ring (○)
- Same on all chips
- Optional: small waveform glyph

---

# 🔄 Orientation Marker

- Small dot or notch at top edge
- Ensures consistent orientation

---

# 🖨️ Print Strategy

- Raised bands: +0.3–0.4mm
- Engraved text: -0.3mm

---

# 🎨 Color System

| Genre        | Color |
|--------------|------|
| Rock         | Deep Red |
| Chill        | Slate Blue |
| Party        | Mustard Gold |
| Dinner       | Forest Green |
| Norway       | Deep Purple |
| News/Radio   | Light Gray |
| Wild         | Black |

---

# 🧵 Filament

## Recommended
- PLA+ (easy, clean)
- PETG (durable)

## Avoid
- ABS
- TPU
- Metallic filaments

---

# 🧲 NFC Constraints

- Max added thickness: ~2–3mm
- No metal layers
- Keep surface flat

---

# 🔧 Assembly

## Prep
- Light sanding (400–600 grit)

## Adhesives
- CA glue (preferred)
- 3M 468MP sheet

Avoid:
- Hot glue
- Thick epoxy

---

# 🎨 Paint Fill (Optional)

- Apply acrylic paint
- Wipe surface
- Leaves engraved text filled

---

# 🏭 Production Workflow

## Phase 1
- Print 5–10 chips
- Test scan + readability

## Phase 2
- Adjust layout + colors

## Phase 3
- Batch production

---

# 🧠 UX Philosophy

- Color = category
- Text = hint
- Screen = detail

Goal:
Grab → Scan → Play

---

# 🎲 Chip Types

## Music
- Songs
- Artists

## Mood
- CHILL
- DINNER
- PARTY

## Media
- CNN
- NPR
- NRK

## Command
- WILD
- SKIP
- CLEAR

---

# 🥣 Interaction Model

- Single bowl system
- Random or color-based selection
- Immediate feedback

---

# 🔥 Final Intent

A physical, social, AI-powered music system that feels like a game.
