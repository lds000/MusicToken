"""Per-chip OpenSCAD generation.

Renders a parametric top-plate model with the chip's text + genre baked
into the parameter block. The model itself mirrors hardware/chip_top.scad;
keeping a copy here means the printable .scad file is fully standalone
(the user can open it in OpenSCAD without anything else from the repo).
"""
from __future__ import annotations

from typing import Tuple

from .registry import Chip

# Genre → (display name, hex color, suggested filament). The hex is used
# by the live SVG preview; the filament hint is embedded as a comment in
# the generated .scad so the print queue is self-documenting.
GENRE_COLORS = {
    "rock":   ("Deep Red",     "#8B1A1A", "PolyTerra Matte PLA — Lava Red"),
    "chill":  ("Slate Blue",   "#475C7A", "PolyTerra Matte PLA — Sapphire Blue"),
    "party":  ("Mustard Gold", "#D4A636", "PolyTerra Matte PLA — Mustard"),
    "dinner": ("Forest Green", "#2F5233", "PolyTerra Matte PLA — Forest"),
    "norway": ("Deep Purple",  "#4B2E83", "PolyTerra Matte PLA — Lavender Purple"),
    "news":   ("Light Gray",   "#B8B8B8", "PolyTerra Matte PLA — Marble or Cotton White"),
    "wild":   ("Black",        "#111111", "PolyLite ABS Black or any matte black PLA+"),
}


def split_label(label: str) -> Tuple[str, str]:
    """Split a chip label like 'EAGLES / HOTEL CALIFORNIA' into the top
    and bottom band strings. If there is no separator, the whole label
    goes on top and the bottom is left blank.
    """
    if not label:
        return "", ""
    if " / " in label:
        top, bottom = label.split(" / ", 1)
        return top.strip().upper()[:12], bottom.strip().upper()[:12]
    if "/" in label:
        top, bottom = label.split("/", 1)
        return top.strip().upper()[:12], bottom.strip().upper()[:12]
    return label.strip().upper()[:12], ""


def _scad_string(s: str) -> str:
    """Escape a string for safe embedding inside OpenSCAD double quotes."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_chip_scad(chip: Chip) -> str:
    """Return a fully-parameterised OpenSCAD source for a chip."""
    top, bottom = split_label(chip.label)
    color_name, color_hex, filament = GENRE_COLORS.get(
        (chip.genre or "").lower(),
        ("(unset)", "#888888", "any non-metallic matte PLA"),
    )
    return f"""// =====================================================================
// MusicToken — generated top plate
// ---------------------------------------------------------------------
// Chip uid     : {chip.uid}
// Label        : {chip.label}
// Genre        : {chip.genre or "(unset)"}
// Action       : {chip.action_type or "(unset)"}
// Color        : {color_name} ({color_hex})
// Filament     : {filament}
//
// Open in OpenSCAD, press F6 to render, File -> Export -> Export as STL.
// Print at 0.12 mm layer height, 100% infill, no supports.
// Glue: 3M 468MP 25 mm round, or thin ring of CA on the edge.
// =====================================================================

top_text       = "{_scad_string(top)}";
bottom_text    = "{_scad_string(bottom)}";
icon_letter    = "";

plate_diameter = 23.8;
plate_height   = 0.8;
chamfer        = 0.2;
band_height    = 4.2;
band_raise     = 0.35;
text_engrave   = 0.30;
text_size      = 2.6;
text_font      = "Liberation Sans:style=Bold";
center_ring_od = 6.5;
center_ring_id = 4.5;
notch_diameter = 1.2;

$fn = 128;

difference() {{
    union() {{
        chamfered_disc(plate_diameter, plate_height, chamfer);
        translate([0, 0, plate_height])
            raised_bands(plate_diameter, band_height, band_raise);
        translate([0, 0, plate_height])
            center_ring(center_ring_od, center_ring_id, band_raise);
    }}

    if (len(top_text) > 0)
        translate([0, plate_diameter/2 - band_height/2 - 0.3,
                   plate_height + band_raise - text_engrave])
            linear_extrude(text_engrave + 0.05)
                text(top_text, size = text_size, halign = "center",
                     valign = "center", font = text_font);

    if (len(bottom_text) > 0)
        translate([0, -(plate_diameter/2 - band_height/2 - 0.3),
                   plate_height + band_raise - text_engrave])
            linear_extrude(text_engrave + 0.05)
                text(bottom_text, size = text_size, halign = "center",
                     valign = "center", font = text_font);

    if (len(icon_letter) > 0)
        translate([0, 0, plate_height + band_raise - text_engrave])
            linear_extrude(text_engrave + 0.05)
                text(icon_letter, size = text_size + 0.4,
                     halign = "center", valign = "center", font = text_font);

    translate([0, plate_diameter/2 - 0.2, -0.05])
        cylinder(d = notch_diameter, h = plate_height + band_raise + 0.3);
}}

module chamfered_disc(d, h, c) {{
    union() {{
        cylinder(d = d - 2*c, h = c);
        translate([0, 0, c]) cylinder(d = d, h = h - c);
    }}
}}

module raised_bands(d, band_h, raise) {{
    intersection() {{
        cylinder(d = d - 0.6, h = raise);
        union() {{
            translate([0, d/2 - band_h/2, raise/2])
                cube([d, band_h, raise], center = true);
            translate([0, -(d/2 - band_h/2), raise/2])
                cube([d, band_h, raise], center = true);
        }}
    }}
}}

module center_ring(od, id, raise) {{
    difference() {{
        cylinder(d = od, h = raise);
        translate([0, 0, -0.05]) cylinder(d = id, h = raise + 0.1);
    }}
}}
"""
