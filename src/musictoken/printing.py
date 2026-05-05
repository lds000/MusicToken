"""Per-chip OpenSCAD generation + STL rendering.

Renders a parametric top-plate model with the chip's text + genre baked
into the parameter block. Two output formats are supported:

- :func:`render_chip_scad` — returns the OpenSCAD source (always works).
- :func:`render_chip_stl`  — invokes the OpenSCAD CLI to produce an STL
  the user can drop into Creality Print / Orca / Cura / Prusa Slicer.

If OpenSCAD is not installed, :func:`render_chip_stl` raises
:class:`OpenSCADNotFound` with a clear install hint so the UI can fall
back to the .scad download.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from .registry import Chip

log = logging.getLogger(__name__)

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


class OpenSCADNotFound(RuntimeError):
    """Raised when the OpenSCAD CLI can't be located."""


class OpenSCADRenderError(RuntimeError):
    """Raised when OpenSCAD ran but failed to produce an STL."""


def find_openscad(explicit: Optional[str] = None) -> Optional[Path]:
    """Locate the OpenSCAD CLI.

    Search order:
      1. Explicit path argument (from config).
      2. ``OPENSCAD`` environment variable.
      3. ``openscad`` / ``openscad.exe`` on ``PATH``.
      4. Common install locations on Windows / macOS / Linux.
    """
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    env = os.environ.get("OPENSCAD")
    if env:
        p = Path(env)
        if p.exists():
            return p

    found = shutil.which("openscad") or shutil.which("openscad.exe")
    if found:
        return Path(found)

    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "OpenSCAD" / "openscad.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "OpenSCAD" / "openscad.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs" / "OpenSCAD" / "openscad.exe",
        Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        Path("/usr/local/bin/openscad"),
        Path("/usr/bin/openscad"),
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except (OSError, ValueError):
            continue
    return None


def render_chip_stl(
    chip: Chip,
    *,
    openscad_path: Optional[str] = None,
    timeout: float = 60.0,
) -> bytes:
    """Render an STL for the chip via the OpenSCAD CLI.

    Raises :class:`OpenSCADNotFound` if OpenSCAD is missing, or
    :class:`OpenSCADRenderError` if the render fails.
    """
    osc = find_openscad(openscad_path)
    if not osc:
        raise OpenSCADNotFound(
            "OpenSCAD is not installed (or not on PATH). Install it from "
            "https://openscad.org/downloads.html, or set "
            "printing.openscad_path in config.yaml. On Windows you can also "
            "run:  winget install OpenSCAD.OpenSCAD"
        )

    scad_source = render_chip_scad(chip)
    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "chip.scad"
        stl_path = Path(tmpdir) / "chip.stl"
        scad_path.write_text(scad_source, encoding="utf-8")
        cmd = [str(osc), "-o", str(stl_path), str(scad_path)]
        log.info("OpenSCAD render: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OpenSCADRenderError(
                f"OpenSCAD timed out after {timeout:.0f}s rendering chip {chip.uid}"
            ) from exc
        if proc.returncode != 0 or not stl_path.exists():
            stderr = proc.stderr.decode("utf-8", errors="replace")[:800]
            raise OpenSCADRenderError(
                f"OpenSCAD exited {proc.returncode}: {stderr or '(no stderr)'}"
            )
        return stl_path.read_bytes()


def render_chip_scad(chip: Chip) -> str:
    """Return a fully-parameterised OpenSCAD source for a chip."""
    top, bottom = split_label(chip.label)
    color_name, color_hex, filament = GENRE_COLORS.get(
        (chip.genre or "").lower(),
        ("(unset)", "#888888", "any non-metallic matte PLA"),
    )
    return f"""// =====================================================================
// MusicToken — generated top plate (arc text)
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
text_size      = 2.4;
text_font      = "Liberation Sans:style=Bold";
text_radius    = (plate_diameter/2) - (band_height/2) - 0.3;  // ~ 9.6 mm
// Per-character arc step. Tweak between 9–12 deg if your text crowds or sprawls.
char_arc_deg   = 10;
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

    // Engraved arc text on the top band.
    translate([0, 0, plate_height + band_raise - text_engrave])
        arc_text_top(top_text, text_radius, char_arc_deg,
                     text_size, text_font, text_engrave + 0.05);

    // Engraved arc text on the bottom band (chars upright, reading L→R).
    translate([0, 0, plate_height + band_raise - text_engrave])
        arc_text_bottom(bottom_text, text_radius, char_arc_deg,
                        text_size, text_font, text_engrave + 0.05);

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

// Place a string along the top arc, centered at 12 o'clock, characters
// upright with their "tops" pointing radially outward.
module arc_text_top(s, radius, char_arc, size, font, thickness) {{
    n = len(s);
    if (n > 0)
        for (i = [0 : n-1]) {{
            a = (i - (n-1)/2) * char_arc;
            rotate([0, 0, -a])
                translate([0, radius, 0])
                linear_extrude(thickness)
                text(s[i], size = size, halign = "center",
                     valign = "center", font = font);
        }}
}}

// Place a string along the bottom arc, centered at 6 o'clock, characters
// upright as read from the front (tops point radially inward).
module arc_text_bottom(s, radius, char_arc, size, font, thickness) {{
    n = len(s);
    if (n > 0)
        for (i = [0 : n-1]) {{
            a = (i - (n-1)/2) * char_arc;
            rotate([0, 0, 180 + a])
                translate([0, radius, 0])
                rotate([0, 0, 180])
                linear_extrude(thickness)
                text(s[i], size = size, halign = "center",
                     valign = "center", font = font);
        }}
}}
"""
