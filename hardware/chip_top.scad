// =====================================================================
// MusicToken — parametric top plate for a 25 mm NTAG215 NFC coin
// ---------------------------------------------------------------------
// Edit the parameters block below for each chip, then:
//   F6 (full render) → File → Export → STL.
// Print at 0.12 mm layer height, 100% infill, no supports.
// =====================================================================

// ----- PARAMETERS ----------------------------------------------------

top_text       = "EAGLES";        // Top band text
bottom_text    = "DREAMS";        // Bottom band text
icon_letter    = "";              // Optional center glyph; "" for ring only

// Geometry (matches Concept.md)
plate_diameter = 23.8;   // mm
plate_height   = 0.8;    // mm  base disc thickness
chamfer        = 0.2;    // mm  edge chamfer
band_height    = 4.2;    // mm  raised band height (top + bottom)
band_raise     = 0.35;   // mm  +Z extrusion for the raised band
text_engrave   = 0.30;   // mm  -Z engraving depth for letters
text_size      = 2.4;    // mm  letter cap height (arc text fits a bit smaller)
text_font      = "Liberation Sans:style=Bold";
text_radius    = (plate_diameter/2) - (band_height/2) - 0.3;
char_arc_deg   = 10;     // deg per character along the arc; 9–12 looks good
center_ring_od = 6.5;
center_ring_id = 4.5;
notch_diameter = 1.2;

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

    translate([0, 0, plate_height + band_raise - text_engrave])
        arc_text_top(top_text, text_radius, char_arc_deg,
                     text_size, text_font, text_engrave + 0.05);

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
}

// ----- MODULES -------------------------------------------------------

module chamfered_disc(d, h, c) {
    union() {
        cylinder(d = d - 2*c, h = c);
        translate([0, 0, c]) cylinder(d = d, h = h - c);
    }
}

module raised_bands(d, band_h, raise) {
    intersection() {
        cylinder(d = d - 0.6, h = raise);
        union() {
            translate([0, d/2 - band_h/2, raise/2])
                cube([d, band_h, raise], center = true);
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

// Top arc: chars centered at 12 o'clock, tops pointing radially outward.
module arc_text_top(s, radius, char_arc, size, font, thickness) {
    n = len(s);
    if (n > 0)
        for (i = [0 : n-1]) {
            a = (i - (n-1)/2) * char_arc;
            rotate([0, 0, -a])
                translate([0, radius, 0])
                linear_extrude(thickness)
                text(s[i], size = size, halign = "center",
                     valign = "center", font = font);
        }
}

// Bottom arc: chars centered at 6 o'clock, upright as read from the
// front (tops pointing radially inward, toward the center ring).
module arc_text_bottom(s, radius, char_arc, size, font, thickness) {
    n = len(s);
    if (n > 0)
        for (i = [0 : n-1]) {
            a = (i - (n-1)/2) * char_arc;
            rotate([0, 0, 180 + a])
                translate([0, radius, 0])
                rotate([0, 0, 180])
                linear_extrude(thickness)
                text(s[i], size = size, halign = "center",
                     valign = "center", font = font);
        }
}
