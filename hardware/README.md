# MusicToken — hardware

## Top plate

Open `chip_top.scad` in [OpenSCAD](https://openscad.org/). Edit the
parameter block at the top:

```scad
top_text    = "EAGLES";
bottom_text = "DREAMS";
icon_letter = "";          // leave blank for the universal ring
```

Render with **F6**, then **File → Export → Export as STL…**.

### Print settings

- Layer height: 0.12 mm (0.16 mm acceptable for body, 0.12 for crisp text)
- Infill: 100 %
- No supports, no brim
- Filament: PLA+ (easy) or PETG (durable). Avoid metallic blends — they
  attenuate the NFC field.

### Color guide

Match the genre color from `Concept.md`:

| Genre   | Filament                |
|---------|-------------------------|
| Rock    | Deep red                |
| Chill   | Slate blue              |
| Party   | Mustard gold            |
| Dinner  | Forest green            |
| Norway  | Deep purple             |
| News    | Light gray              |
| Wild    | Black                   |

### Assembly

1. Lightly sand the back face (400–600 grit) so glue keys.
2. Apply a thin ring of CA glue (or a 23 mm 3M 468MP disc) around the
   edge of the printed plate.
3. Press the plate centered onto the NTAG215 coin. The 0.6 mm reveal ring
   of black PVC will frame the print.
4. Optional: rub acrylic paint into the engraved text, wipe surface.

### Troubleshooting

- **NFC won't read after gluing:** confirm total stack height ≤ 3 mm and
  that no metallic filament is in the path.
- **Text too thin:** raise `text_size` to 2.8 mm or use a thicker bold
  font (e.g. `Liberation Sans:style=Black`).
