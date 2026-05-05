# MusicToken — hardware guide

This is the full recipe for turning a programmed chip into a physical
token. The web UI's **Print chip** button does steps 1 and 2 for you and
hands back a ready-to-render `.scad` file.

---

## 0. The base coin

Use a standard **NTAG215 25 mm round PVC coin** (~1.0 mm thick).
Verified-working part: Amazon ASIN **B09L7LBYZ3** (and any equivalent
NTAG215 coin from the same form factor — most "TagMo / Amiibo
compatible" coin packs are identical).

Total stack with the 0.8 mm printed top plate is ~1.8 mm. Comfortably
inside the read range of any PN532 / RC522 reader.

> You do **not** need to write anything to the NFC chip. MusicToken
> reads the factory-burned hardware UID, not the NDEF payload. Every
> blank coin out of the bag has a unique UID already.

---

## 1. Generate the `.scad` (one click)

In the Admin UI:

1. Fill in the label (e.g. `EAGLES / HOTEL CALIFORNIA`).
2. Pick a genre.
3. Pick the action + payload (or use **AI suggest** / **AI autofill**).
4. Hit **🖨 Print chip**.

You'll get a `LABEL.scad` download. The chip is also saved in the
registry under a `DESIGN-XXXXXXXX` placeholder UID until you claim it
to a real tag.

If you'd rather start from scratch, `chip_top.scad` in this folder is
the same parametric model — edit the parameters block at the top.

---

## 2. Render and print

1. Open the `.scad` in [OpenSCAD](https://openscad.org/).
2. **F6** to render → **File → Export → Export as STL…**
3. Slice and print:
   - Layer height: **0.12 mm** (0.16 mm OK for the body if the text is
     big, but 0.12 mm gives crisp band text)
   - Infill: **100%**
   - **No** supports, **no** brim
   - Print on textured / smooth PEI; the bottom face is the bond face

### Filament per genre

PolyTerra Matte PLA is the recommended default — saturated colors,
hides layer lines on a thin disc, prints clean at low layer heights.

| Genre   | Filament |
|---------|----------|
| Rock    | PolyTerra **Lava Red** *(eSUN PLA+ Fire Engine Red)* |
| Chill   | PolyTerra **Sapphire Blue** *(Prusament Galaxy Blue)* |
| Party   | PolyTerra **Mustard** *(eSUN PLA+ Yellow)* |
| Dinner  | PolyTerra **Forest** *(Prusament Pine Green)* |
| Norway  | PolyTerra **Lavender Purple** *(Muted Lilac)* |
| News    | PolyTerra **Marble** or **Cotton White** *(any light gray)* |
| Wild    | PolyLite **ABS Black** *(any matte black PLA+)* |

**Avoid** anything metallic / silk / glitter / carbon-fill /
stainless-fill. Metal flake attenuates the NFC field. Plain ABS warps
on a 23.8 mm thin disc — PETG is fine if you want extra durability.

---

## 3. Bond plate to coin

### Surface prep

Light pass on **both** mating surfaces with **400-grit** sandpaper, then
wipe with **91%+ isopropyl alcohol**. This roughly doubles bond strength
on either CA or transfer tape.

### Adhesive (best → fastest → avoid)

1. **3M 468MP adhesive transfer tape, 25 mm round die-cut** — clean,
   repeatable, no squeeze-out. Search Aliexpress for *"25 mm 3M 468MP
   round"*. Best for batches: peel, stick, press for 5 s.
2. **Loctite Super Glue Liquid Universal** — thin **ring around the
   edge only**. Don't pool in the center — CA can fog over time and
   bleed into the engraving. 30 s hold.
3. **Avoid:** hot glue (lumps + can de-tune NFC), epoxy (squeeze-out),
   Gorilla Original (foams).

---

## 4. Optional: paint-fill the engraved text

Makes the labels really pop, especially on dark filaments.

1. Brush acrylic craft paint over the entire top face.
2. Wait ~30 s — **not** full dry.
3. Wipe firmly across the surface with a damp microfiber. Paint stays
   in the engraved letters; raised bands wipe clean.
4. Color rules of thumb:
   - **Dark filaments (rock/chill/dinner/norway/wild)** → white or
     silver paint
   - **Light filaments (party/news)** → black paint

---

## 5. Claim the design to a real tag

1. Place the finished chip on the NFC reader.
2. The Admin UI's **Last scan** field auto-fills with the UID.
3. Click **🔗 Claim last scan** on the form for the design row.

The registry entry is migrated from `DESIGN-XXXXXXXX` to the real UID,
the design row is removed, and you're done. Tap to test.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Won't read after gluing | Stack too thick, or metallic filament | Confirm filament is non-metallic; total stack ≤ 3 mm |
| Reads intermittently | Reader sitting too far below print bed | Bring reader to within 5 mm of the chip face |
| Text too thin to read | Layer height or font weight | Increase `text_size` to 2.8 mm or use `Liberation Sans:style=Black` |
| Top plate peels off | Skipped surface prep | Sand both faces, IPA wipe, redo with 3M 468MP |
| CA glue fogged the surface | Pooled CA in the center | Apply only as a thin **ring** at the edge |
