// =====================================================================
// MusicToken — parametric top plate for a 25 mm NTAG215 NFC coin
// ---------------------------------------------------------------------
// Edit the parameters block below for each chip, then:
//   F6 (full render) → File → Export → STL.
// Print at 0.12 mm layer height, 100% infill, no supports.
// =====================================================================

// ----- PARAMETERS ----------------------------------------------------

top_text       = "EAGLES";       // Top band text   (≤10 chars)
bottom_text    = "DREAMS";       // Bottom band text(≤10 chars)
icon_letter    = "";             // Optional center glyph; "" for ring only

// Geometry (matches Concept.md)
plate_diameter = 23.8;   // mm
plate_height   = 0.8;    // mm  base disc thickness
chamfer        = 0.2;    // mm  edge chamfer
band_height    = 4.2;    // mm  raised band height (top + bottom)
band_raise     = 0.35;   // mm  +Z extrusion for the raised band
text_engrave   = 0.30;   // mm  -Z engraving depth for letters
text_size      = 2.6;    // mm  letter cap height
text_font      = "Liberation Sans:style=Bold";
center_ring_od = 6.5;    // mm  outer diameter of universal ring icon
center_ring_id = 4.5;    // mm  inner diameter of universal ring icon
notch_diameter = 1.2;    // mm  orientation notch (top edge)

$fn = 128;

// ----- BUILD ---------------------------------------------------------

difference() {
    union() {
        chamfered_disc(plate_diameter, plate_height, chamfer);
        translate([0, 0, plate_height])
            raised_bands(plate_diameter, band_height, band_raise);
        translate([0, 0, plate_height])
            center_ring(center_ring_od, center_ring_id, band_raise);
    }

    // Engraved text on top and bottom raised bands.
    translate([0, plate_diameter/2 - band_height/2 - 0.3,
               plate_height + band_raise - text_engrave])
        linear_extrude(text_engrave + 0.05)
            text(top_text, size = text_size, halign = "center",
                 valign = "center", font = text_font);

    translate([0, -(plate_diameter/2 - band_height/2 - 0.3),
               plate_height + band_raise - text_engrave])
        linear_extrude(text_engrave + 0.05)
            text(bottom_text, size = text_size, halign = "center",
                 valign = "center", font = text_font);

    // Optional center glyph engraved into the ring.
    if (len(icon_letter) > 0) {
        translate([0, 0, plate_height + band_raise - text_engrave])
            linear_extrude(text_engrave + 0.05)
                text(icon_letter, size = text_size + 0.4,
                     halign = "center", valign = "center", font = text_font);
    }

    // Orientation notch at 12 o'clock.
    translate([0, plate_diameter/2 - 0.2, -0.05])
        cylinder(d = notch_diameter, h = plate_height + band_raise + 0.3);
}

// ----- MODULES -------------------------------------------------------

module chamfered_disc(d, h, c) {
    // A simple chamfered disc using a cylinder + a thin cone.
    union() {
        cylinder(d = d - 2*c, h = c);
        translate([0, 0, c]) cylinder(d = d, h = h - c);
    }
}

module raised_bands(d, band_h, raise) {
    // Two ring segments at the top and bottom of the disc.
    intersection() {
        cylinder(d = d - 0.6, h = raise); // 0.3 mm reveal ring all around
        union() {
            // top band (positive Y)
            translate([0, d/2 - band_h/2, raise/2])
                cube([d, band_h, raise], center = true);
            // bottom band (negative Y)
            translate([0, -(d/2 - band_h/2), raise/2])
                cube([d, band_h, raise], center = true);
        }
    }
}

module center_ring(od, id, raise) {
    difference() {
        cylinder(d = od, h = raise);
        translate([0, 0, -0.05]) cylinder(d = id, h = raise + 0.1);
    }
}
