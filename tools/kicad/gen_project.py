# SPDX-License-Identifier: MIT
"""Generate the Rev-A KiCad project skeleton and sheet 1 (Zorro II interface).

usage: python -I tools/kicad/gen_project.py <repo_root>

Bootstrap only. After the generated files have been edited in KiCad, the
.kicad_sch files are authoritative; do not re-run this over them blindly.
All IC pin numbers below were transcribed from the TI datasheets listed in the
symbol Datasheet fields and docs/stage2/sheet1-design-notes.md (section 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kisch import (FP_VERSION, GEN_VERSION, LIB, PROJECT, Pin, Schematic, StdSymbol, SymbolDef, U, f, q,
                   write_symbol_lib)

KICAD_SYM = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
DATE = "2026-11-18"
REV = "A (draft)"
COMPANY = "A2000 x86 Bridgeboard project"
LICENCE = "CERN-OHL-S-2.0"

# ============================================================================ symbols
def ic_power_pins(pins, top_nums_names, bot_nums, top_y, bot_y, top_xs, bot_xs):
    for (num, name), x in zip(top_nums_names, top_xs):
        pins.append(Pin(num, name, "power_in", x, top_y, 270, 2.54))
    for num, x in zip(bot_nums, bot_xs):
        pins.append(Pin(num, "GND", "power_in", x, bot_y, 90, 2.54))


def sym_lvc16244():
    # TI SCAS699C, DGG (TSSOP-48) pinout
    a = {"1A1": "47", "1A2": "46", "1A3": "44", "1A4": "43", "2A1": "41", "2A2": "40", "2A3": "38", "2A4": "37",
         "3A1": "36", "3A2": "35", "3A3": "33", "3A4": "32", "4A1": "30", "4A2": "29", "4A3": "27", "4A4": "26"}
    y_ = {"1Y1": "2", "1Y2": "3", "1Y3": "5", "1Y4": "6", "2Y1": "8", "2Y2": "9", "2Y3": "11", "2Y4": "12",
          "3Y1": "13", "3Y2": "14", "3Y3": "16", "3Y4": "17", "4Y1": "19", "4Y2": "20", "4Y3": "22", "4Y4": "23"}
    oe = {"1": "1", "2": "48", "3": "25", "4": "24"}
    pins = []
    rows = []
    for g, y0 in ((1, 33.02), (2, 20.32), (3, 7.62), (4, -5.08)):
        for i in range(4):
            rows.append((f"{g}A{i+1}", f"{g}Y{i+1}", y0 - 2.54 * i))
    for an, yn, y in rows:
        pins.append(Pin(a[an], an, "input", -15.24, y, 0, 5.08))
        pins.append(Pin(y_[yn], yn, "tri_state", 15.24, y, 180, 5.08))
    for k, (g, y) in enumerate(((1, -17.78), (2, -20.32), (3, -22.86), (4, -25.4))):
        pins.append(Pin(oe[str(g)], f"~{{{g}OE}}", "input", -15.24, y, 0, 5.08))
    ic_power_pins(pins, [("7", "VCC"), ("18", "VCC"), ("31", "VCC"), ("42", "VCC")],
                  ["4", "10", "15", "21", "28", "34", "39", "45"], 43.18, -35.56,
                  [-3.81, -1.27, 1.27, 3.81], [-8.89, -6.35, -3.81, -1.27, 1.27, 3.81, 6.35, 8.89])
    return SymbolDef(
        "SN74LVC16244ADGG", "U", "SN74LVC16244ADGGR", "Package_SO:TSSOP-48_6.1x12.5mm_P0.5mm",
        "https://www.ti.com/lit/ds/symlink/sn74lvc16244a.pdf",
        "16-bit buffer/driver, 3-state, 5.5 V tolerant inputs, Ioff (TI SCAS699C)",
        pins, rects={1: [(-10.16, 40.64, 10.16, -33.02)]},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC16244ADGGR"},
        keywords="buffer driver 16bit LVC 5V tolerant", ref_at=(-10.16, 37.0), value_at=(-10.16, -33.0))


def sym_lvch16t245():
    # TI SCES635B (LVCH) == SCES636B (LVC) DGG pinout (verified identical)
    b = {f"1B{i}": n for i, n in zip(range(1, 9), ["2", "3", "5", "6", "8", "9", "11", "12"])}
    b.update({f"2B{i}": n for i, n in zip(range(1, 9), ["13", "14", "16", "17", "19", "20", "22", "23"])})
    a = {f"1A{i}": n for i, n in zip(range(1, 9), ["47", "46", "44", "43", "41", "40", "38", "37"])}
    a.update({f"2A{i}": n for i, n in zip(range(1, 9), ["36", "35", "33", "32", "30", "29", "27", "26"])})
    pins = []
    for g, y0 in ((1, 33.02), (2, 10.16)):
        for i in range(8):
            y = y0 - 2.54 * i
            pins.append(Pin(b[f"{g}B{i+1}"], f"{g}B{i+1}", "bidirectional", -15.24, y, 0, 5.08))
            pins.append(Pin(a[f"{g}A{i+1}"], f"{g}A{i+1}", "bidirectional", 15.24, y, 180, 5.08))
    pins += [Pin("48", "~{1OE}", "input", 15.24, -15.24, 180, 5.08), Pin("25", "~{2OE}", "input", 15.24, -17.78, 180, 5.08),
             Pin("1", "1DIR", "input", 15.24, -22.86, 180, 5.08), Pin("24", "2DIR", "input", 15.24, -25.4, 180, 5.08)]
    ic_power_pins(pins, [("7", "VCCB"), ("18", "VCCB"), ("31", "VCCA"), ("42", "VCCA")],
                  ["4", "10", "15", "21", "28", "34", "39", "45"], 43.18, -38.1,
                  [-6.35, -3.81, 3.81, 6.35], [-8.89, -6.35, -3.81, -1.27, 1.27, 3.81, 6.35, 8.89])
    return SymbolDef(
        "SN74LVCH16T245DGG", "U", "SN74LVCH16T245DGGR", "Package_SO:TSSOP-48_6.1x12.5mm_P0.5mm",
        "https://www.ti.com/lit/ds/symlink/sn74lvch16t245.pdf",
        "16-bit dual-supply bus transceiver, bus-hold, VCC isolation, Ioff; DIR/OE referenced to VCCA (TI SCES635B)",
        pins, rects={1: [(-10.16, 40.64, 10.16, -35.56)]},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVCH16T245DGGR"},
        keywords="transceiver level translator dual supply bus hold", ref_at=(-10.16, 37.0), value_at=(-10.16, -35.6))


def sym_lvc2t45():
    # TI SCES516N, DCT/DCU pinout: 1 VCCA, 2 A1, 3 A2, 4 GND, 5 DIR, 6 B2, 7 B1, 8 VCCB
    pins = [Pin("2", "A1", "bidirectional", -12.7, 5.08, 0, 5.08), Pin("3", "A2", "bidirectional", -12.7, 0, 0, 5.08),
            Pin("5", "DIR", "input", -12.7, -5.08, 0, 5.08), Pin("7", "B1", "bidirectional", 12.7, 5.08, 180, 5.08),
            Pin("6", "B2", "bidirectional", 12.7, 0, 180, 5.08), Pin("1", "VCCA", "power_in", -2.54, 12.7, 270, 2.54),
            Pin("8", "VCCB", "power_in", 2.54, 12.7, 270, 2.54), Pin("4", "GND", "power_in", 0, -12.7, 90, 2.54)]
    return SymbolDef(
        "SN74LVC2T45DCT", "U", "SN74LVC2T45DCTR", "Package_SO:SSOP-8_2.95x2.8mm_P0.65mm",
        "https://www.ti.com/lit/ds/symlink/sn74lvc2t45.pdf",
        "2-bit dual-supply transceiver, VCC isolation, Ioff; DIR referenced to VCCA (TI SCES516N)",
        pins, rects={1: [(-7.62, 10.16, 7.62, -10.16)]},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC2T45DCTR"},
        keywords="level translator dual supply 2bit", ref_at=(-7.62, 9.5), value_at=(-7.62, -10.0))


def sym_lvc07a():
    # TI SCAS595W, PW (TSSOP-14): 1 1A 2 1Y 3 2A 4 2Y 5 3A 6 3Y 7 GND 8 4Y 9 4A 10 5Y 11 5A 12 6Y 13 6A 14 VCC
    an = {1: "1", 2: "3", 3: "5", 4: "9", 5: "11", 6: "13"}
    yn = {1: "2", 2: "4", 3: "6", 4: "8", 5: "10", 6: "12"}
    pins = []
    for i in range(1, 7):
        y = 12.7 - 5.08 * (i - 1)
        pins.append(Pin(an[i], f"{i}A", "input", -12.7, y, 0, 5.08))
        pins.append(Pin(yn[i], f"{i}Y", "open_collector", 12.7, y, 180, 5.08))
    pins += [Pin("14", "VCC", "power_in", 0, 20.32, 270, 2.54), Pin("7", "GND", "power_in", 0, -20.32, 90, 2.54)]
    return SymbolDef(
        "SN74LVC07APW", "U", "SN74LVC07APWR", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        "https://www.ti.com/lit/ds/symlink/sn74lvc07a.pdf",
        "Hex buffer, open-drain outputs, inputs/outputs 5.5 V tolerant, Ioff (TI SCAS595W)",
        pins, rects={1: [(-7.62, 17.78, 7.62, -17.78)]},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC07APWR"},
        keywords="buffer open drain open collector", ref_at=(-7.62, 13.0), value_at=(-7.62, -13.5))


# Zorro II pin names (Hardware Book table credited to the A4000 User's Guide; matches MNT VA2000 symbol)
ZNAMES = {1: "GND", 2: "GND", 3: "GND", 4: "GND", 5: "+5V", 6: "+5V", 7: "~{OWN}", 8: "-5V", 9: "~{SLAVEn}",
          10: "+12V", 11: "~{CFGOUTn}", 12: "~{CFGINn}", 13: "GND", 14: "~{C3}", 15: "CDAC", 16: "~{C1}",
          17: "~{OVR}", 18: "XRDY", 19: "~{INT2}", 20: "-12V", 21: "A5", 22: "~{INT6}", 23: "A6", 24: "A4",
          25: "GND", 26: "A3", 27: "A2", 28: "A7", 29: "A1", 30: "A8", 31: "FC0", 32: "A9", 33: "FC1",
          34: "A10", 35: "FC2", 36: "A11", 37: "GND", 38: "A12", 39: "A13", 40: "~{EINT7}", 41: "A14",
          42: "~{EINT5}", 43: "A15", 44: "~{EINT4}", 45: "A16", 46: "~{BERR}", 47: "A17", 48: "~{VPA}",
          49: "GND", 50: "E", 51: "~{VMA}", 52: "A18", 53: "~{RST}", 54: "A19", 55: "~{HLT}", 56: "A20",
          57: "A22", 58: "A21", 59: "A23", 60: "~{BRn}", 61: "GND", 62: "~{BGACK}", 63: "D15", 64: "~{BGn}",
          65: "D14", 66: "~{DTACK}", 67: "D13", 68: "READ", 69: "D12", 70: "~{LDS}", 71: "D11", 72: "~{UDS}",
          73: "GND", 74: "~{AS}", 75: "D0", 76: "D10", 77: "D1", 78: "D9", 79: "D2", 80: "D8", 81: "D3",
          82: "D7", 83: "D4", 84: "D6", 85: "GND", 86: "D5", 87: "GND", 88: "GND", 89: "GND", 90: "GND",
          91: "GND/SenseZ3", 92: "E7M", 93: "DOE", 94: "~{BUSRST}", 95: "~{GBG}", 96: "~{EINT1}", 97: "NC",
          98: "NC", 99: "GND", 100: "GND"}

# Pin -> carrier net.  "GND" = ground plane, None = not connected (no-connect flag)
ZNET = {n: None for n in range(1, 101)}
for n in (1, 2, 3, 4, 13, 25, 37, 49, 61, 73, 85, 87, 88, 89, 90, 91, 99, 100):
    ZNET[n] = "GND"
ZNET.update({9: "Z_SLAVE_N", 11: "Z_CFGOUT_N", 12: "Z_CFGIN_N", 15: "Z_CDAC", 17: "Z_OVR_N", 18: "Z_XRDY",
             19: "Z_INT2_N", 21: "Z_A5", 22: "Z_INT6_N", 23: "Z_A6", 24: "Z_A4", 26: "Z_A3", 27: "Z_A2",
             28: "Z_A7", 29: "Z_A1", 30: "Z_A8", 32: "Z_A9", 34: "Z_A10", 36: "Z_A11", 38: "Z_A12", 39: "Z_A13",
             41: "Z_A14", 43: "Z_A15", 45: "Z_A16", 46: "Z_BERR_N", 47: "Z_A17", 52: "Z_A18", 54: "Z_A19",
             56: "Z_A20", 57: "Z_A22", 58: "Z_A21", 59: "Z_A23", 63: "Z_D15", 65: "Z_D14", 66: "Z_DTACK_N",
             67: "Z_D13", 68: "Z_READ", 69: "Z_D12", 70: "Z_LDS_N", 71: "Z_D11", 72: "Z_UDS_N", 74: "Z_AS_N",
             75: "Z_D0", 76: "Z_D10", 77: "Z_D1", 78: "Z_D9", 79: "Z_D2", 80: "Z_D8", 81: "Z_D3", 82: "Z_D7",
             83: "Z_D4", 84: "Z_D6", 86: "Z_D5", 92: "Z_E7M", 93: "Z_DOE", 94: "Z_BUSRST_N"})


def sym_zorro():
    pins = []
    for n in range(1, 101):
        unit = 1 if n <= 50 else 2
        k = n - 1 if unit == 1 else n - 51
        pins.append(Pin(str(n), ZNAMES[n], "passive", 7.62, 62.23 - 2.54 * k, 180, 2.54, unit=unit))
    return SymbolDef(
        "Zorro2_Edge_100", "J", "Zorro II edge (100)", f"{LIB}:Zorro2_Edge_2x50_P2.54mm",
        "https://isa.umh.es/micros/doc/hwb/co_Zorro.html",
        "Amiga Zorro II 100-pin card-edge connector (A2000). Unit A = pins 1-50, unit B = pins 51-100.",
        pins, rects={0: [(-10.16, 64.77, 5.08, -64.77)]}, units=2,
        extra_props={"Manufacturer": "n/a (PCB gold fingers)", "MPN": "n/a"},
        keywords="amiga zorro edge connector", ref_at=(-10.16, 66.5), value_at=(-10.16, -66.5))


def sym_power(name):
    g = ("\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy -0.762 1.27) (xy 0 2.54)\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n"
         "\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n"
         "\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy 0 2.54) (xy 0.762 1.27)\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n"
         "\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n"
         "\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy 0 0) (xy 0 2.54)\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n"
         "\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)")
    return SymbolDef(name, "#PWR", name, "", "", f"Power symbol creates a global label with name \"{name}\"",
                     [Pin("1", "", "power_in", 0, 0, 90, 0)], power=True, hide_pin_numbers=True,
                     hide_pin_names=True, pin_name_offset=0, ref_at=(0, -3.81), value_at=(0, 3.556),
                     graphics_raw=g, keywords="global power")


# ============================================================================ footprint
def write_zorro_footprint(path: Path):
    o = [f"(footprint \"Zorro2_Edge_2x50_P2.54mm\"\n\t(version {FP_VERSION})\n\t(generator \"pcbnew\")\n"
         f"\t(generator_version \"{GEN_VERSION}\")\n\t(layer \"F.Cu\")\n"
         "\t(descr \"Amiga Zorro II 100-pin card edge, 2.54 mm pitch, 2x50 gold fingers. Even pins on F.Cu, odd on "
         "B.Cu; pins 1/2 at +X end. Pad geometry follows MNT VA2000 zorro2card footprint (MIT). Origin = card "
         "edge. Finger length, bevel and orientation relative to the A2000 bracket: TBV (Stage 6).\")\n"
         "\t(tags \"Amiga Zorro edge connector card edge gold fingers\")"]
    def p(name, val, x, y, layer, hide=False):
        h = "\n\t\t(hide yes)" if hide else ""
        return (f"\t(property {q(name)} {q(val)}\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(layer {q(layer)}){h}\n"
                f"\t\t(uuid {q(U('fp/' + name))})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n"
                "\t\t\t)\n\t\t)\n\t)")
    o += [p("Reference", "REF**", 0, -8.0, "F.SilkS"), p("Value", "Zorro2_Edge_2x50_P2.54mm", 0, -10.0, "F.Fab"),
          p("Datasheet", "", 0, 0, "F.Fab", True), p("Description", "", 0, 0, "F.Fab", True)]
    o.append("\t(attr exclude_from_pos_files exclude_from_bom)\n\t(duplicate_pad_numbers_are_jumpers no)")
    def line(x1, y1, x2, y2, layer, key, w=0.1):
        return (f"\t(fp_line\n\t\t(start {f(x1)} {f(y1)})\n\t\t(end {f(x2)} {f(y2)})\n\t\t(stroke\n\t\t\t(width {f(w)})\n"
                f"\t\t\t(type solid)\n\t\t)\n\t\t(layer {q(layer)})\n\t\t(uuid {q(U('fp/line/' + key))})\n\t)")
    o.append(line(-64.0, 0, 64.0, 0, "F.Fab", "edge"))
    for i, (a, b, c, d) in enumerate(((-63.5, -5.6, 63.5, -5.6), (63.5, -5.6, 63.5, 0.5), (63.5, 0.5, -63.5, 0.5),
                                      (-63.5, 0.5, -63.5, -5.6))):
        o.append(line(a, b, c, d, "F.CrtYd", f"cy{i}", 0.05))
    o.append(f"\t(fp_text user \"CARD EDGE - bevel, hard gold (TBV)\"\n\t\t(at 0 1.5 0)\n\t\t(layer \"F.Fab\")\n"
             f"\t\t(uuid {q(U('fp/txt'))})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)")
    for n in range(1, 101):
        idx = (n // 2 - 1) if n % 2 == 0 else ((n + 1) // 2 - 1)
        x = 62.23 - 2.54 * idx
        layers = '"F.Cu" "F.Mask"' if n % 2 == 0 else '"B.Cu" "B.Mask"'
        o.append(f"\t(pad {q(str(n))} connect rect\n\t\t(at {f(x)} -2.54)\n\t\t(size 1.524 5)\n\t\t(layers {layers})\n"
                 f"\t\t(uuid {q(U('fp/pad/' + str(n)))})\n\t)")
    o.append("\t(embedded_fonts no)\n)")
    path.write_text("\n".join(o) + "\n", encoding="utf-8")


# ============================================================================ sheet 1
def build_sheet1(repo: Path, root_uuid: str, sheet_uuid: str, syms, std):
    sch = Schematic("sheet1", "A2", "Zorro II interface and AutoConfig signal buffering", REV, DATE,
                    ["Sheet 1 of 6 (Stage 2). NOT VALIDATED: design review pending.",
                     "5 V Zorro <-> 3.3 V logic. No power drawn from Zorro +5V/+12V pins; all Zorro GND pins used.",
                     "Pin data: TI SCAS699C, SCES635B, SCES516N, SCAS595W; Zorro: Commodore Zorro III spec App. K.",
                     f"Licence: {LICENCE}. See docs/stage2/sheet1-design-notes.md"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    R, C, RN, TP = std["R"], std["C"], std["RN"], std["TP"]
    P3, GNDS, FLAG = std["+3V3"], std["GND"], std["FLAG"]
    P5 = syms["+5V_BUS"]
    pwr_n = [0]

    def pwr(sym, x, y, rot=0, val_at=None, hide_value=False):
        pwr_n[0] += 1
        name = sym.value if isinstance(sym, SymbolDef) else sym.name
        vat = val_at if val_at else (x, y - 3.6) if name != "GND" else (x, y + 5.0)
        return sch.place(sym, f"#PWR{100 + pwr_n[0]:04d}", name, x, y, rot, val_at=vat, hide_value=hide_value,
                         ref_at=(x, y + 3))

    def tie(points, direction, sym, ext=2.54):
        """Connect pin points (on one line) to one power symbol via stubs + tie line."""
        dx, dy = {"up": (0, -2.54), "down": (0, 2.54), "left": (-2.54, 0), "right": (2.54, 0)}[direction]
        stubs = [(round(px + dx, 4), round(py + dy, 4)) for px, py in points]
        for pnt, s in zip(points, stubs):
            sch.wire(pnt, s)
        horiz = direction in ("up", "down")
        stubs.sort(key=lambda s: s[0] if horiz else s[1])
        for a, b in zip(stubs, stubs[1:]):
            sch.wire(a, b)
        end = stubs[0]
        ext_pt = (round(end[0] - ext, 4), end[1]) if horiz else (end[0], round(end[1] - ext, 4))
        sch.wire(end, ext_pt)
        for s in stubs[1:-1]:
            sch.junction(s)
        if len(stubs) > 1:
            sch.junction(end)
        is_gnd = getattr(sym, "name", "") == "GND"
        return pwr(sym, ext_pt[0], ext_pt[1], 0, hide_value=is_gnd)

    # ---------------- J101 edge connector -----------------------------------
    jx = 25.4
    for unit, jy in ((1, 104.14), (2, 251.46)):
        j = sch.place(syms["ZORRO"], "J101", "Zorro II edge (100)", jx, jy, 0, unit=unit,
                      ref_at=(jx - 10.16, jy - 66.5), val_at=(jx - 10.16, jy + 67.5))
        for n in (range(1, 51) if unit == 1 else range(51, 101)):
            pt = j.p(str(n))
            net = ZNET[n]
            if net is None:
                sch.noconnect(pt)
            elif net == "GND":
                end = (pt[0] + 2.54, pt[1])
                sch.wire(pt, end)
                pwr(GNDS, end[0], end[1], 90, val_at=(end[0] + 6.0, end[1]), hide_value=True)
            else:
                end = (pt[0] + 7.62, pt[1])
                sch.wire(pt, end)
                sch.label(net, end, "right")
    # PWR_FLAG on GND (ground enters through Zorro GND pins and the Molex on sheet 5)
    gp = (63.5, 182.88)
    sch.place(FLAG, "#FLG0101", "PWR_FLAG", gp[0], gp[1], 0, ref_at=(gp[0], gp[1] - 5), val_at=(gp[0], gp[1] - 3.2))
    pwr(GNDS, gp[0], gp[1], 0)
    # TEMPORARY flags for rails that sheet 5 will source (same proven overlap arrangement as the GND flag)
    for k, (ps, nm) in enumerate(((P3, "+3V3"), (P5, "+5V_BUS"))):
        fx, fy = 304.8 + 30.48 * k, 30.48
        pwr(ps, fx, fy, 0, val_at=(fx - 6.5, fy - 1.0))
        sch.place(FLAG, f"#FLG{102 + k:04d}", "PWR_FLAG", fx, fy, 180, ref_at=(fx, fy + 7), val_at=(fx + 7.0, fy + 3.2),
                  field_ang=0)
    sch.text("TEMPORARY: remove these two PWR_FLAGs when sheet 5 (power) sources +3V3 / +5V_BUS.",
             (304.8 + 60.96, 28.0), 1.27)
    sch.text("Ground: all 18 Zorro GND pins (incl. pin 91)\nto the ground plane. Zorro +5V (5,6), +12V (10),\n"
             "-5V (8), -12V (20) deliberately NOT connected\n(brief: no operating power from Zorro pins).",
             (15.24, 325.12), 1.27)

    # ---------------- U101/U102 input buffers --------------------------------
    u_in = syms["LVC16244"]
    U101 = sch.place(u_in, "U101", "SN74LVC16244ADGGR", 101.6, 99.06, ref_at=(91.44, 60.96), val_at=(111.76, 139.7),
                      ref_just="right", val_just="left")
    U102 = sch.place(u_in, "U102", "SN74LVC16244ADGGR", 101.6, 220.98, ref_at=(91.44, 182.88), val_at=(111.76, 261.62),
                      ref_just="right", val_just="left")
    map101 = [(f"Z_A{i}", f"ZB_A{i}") for i in range(1, 17)]
    map102 = [(f"Z_A{i}", f"ZB_A{i}") for i in range(17, 24)] + [
        ("Z_AS_N", "ZB_AS_N"), ("Z_UDS_N", "ZB_UDS_N"), ("Z_LDS_N", "ZB_LDS_N"), ("Z_READ", "ZB_READ"),
        ("Z_DOE", "ZB_DOE"), ("Z_E7M", "ZB_E7M"), ("Z_CFGIN_N", "ZB_CFGIN_N"), ("Z_BUSRST_N", "ZB_BUSRST_N"),
        ("Z_CDAC", "ZB_CDAC")]
    order = [f"{g}A{i}" for g in range(1, 5) for i in range(1, 5)]
    for U_, mp in ((U101, map101), (U102, map102)):
        for an, (zin, zout) in zip(order, mp):
            pa = U_.p(u_in.pin(next(p.num for p in u_in.pins if p.name == an)).num)
            yname = an.replace("A", "Y")
            py = U_.p(next(p.num for p in u_in.pins if p.name == yname))
            sch.wire(pa, (pa[0] - 7.62, pa[1]))
            sch.label(zin, (pa[0] - 7.62, pa[1]), "left")
            sch.wire(py, (py[0] + 7.62, py[1]))
            sch.hlabel(zout, "output", (py[0] + 7.62, py[1]), "right")
        oe = [U_.p(n) for n in ("1", "48", "25", "24")]
        oe.sort(key=lambda p: p[1])
        stubs = [(p[0] - 2.54, p[1]) for p in oe]
        for p_, s in zip(oe, stubs):
            sch.wire(p_, s)
        for a, b in zip(stubs, stubs[1:]):
            sch.wire(a, b)
        gpt = (stubs[-1][0], stubs[-1][1] + 2.54)
        sch.wire(stubs[-1], gpt)
        for s in stubs[1:]:
            sch.junction(s)
        pwr(GNDS, gpt[0], gpt[1], hide_value=True)
        tie([U_.p(n) for n in ("7", "18", "31", "42")], "up", P3)
        tie([U_.p(n) for n in ("4", "10", "15", "21", "28", "34", "39", "45")], "down", GNDS)
    sch.text("~{OE} tied low: inputs always enabled.\nOutputs drive FPGA inputs only.\n"
             "5.5 V-tolerant inputs; Ioff = no backfeed\nwhen +3V3 is off (TI SCAS699C).", (60.96, 147.32), 1.27)

    # ---------------- U103 data transceiver + RN101..RN104 --------------------
    ut = syms["LVCH16T245"]
    U103 = sch.place(ut, "U103", "SN74LVCH16T245DGGR", 226.06, 99.06, ref_at=(215.9, 60.96), val_at=(236.22, 144.78),
                      ref_just="right", val_just="left")
    rn_x = 200.66
    groups = [("RN101", 68.58, [("1B1", 0), ("1B2", 1), ("1B3", 2), ("1B4", 3)]),
              ("RN102", 78.74, [("1B5", 4), ("1B6", 5), ("1B7", 6), ("1B8", 7)]),
              ("RN103", 91.44, [("2B1", 8), ("2B2", 9), ("2B3", 10), ("2B4", 11)]),
              ("RN104", 101.6, [("2B5", 12), ("2B6", 13), ("2B7", 14), ("2B8", 15)])]
    rn_rows = [("4", "5"), ("3", "6"), ("2", "7"), ("1", "8")]   # rows top..bottom after rot 90
    for ref, ry, members in groups:
        rn = sch.place(RN, ref, "4x22R", rn_x, ry, 90, footprint="Resistor_SMD:R_Array_Convex_4x0603",
                       props={"Manufacturer": "Yageo", "MPN": "YC164-JR-0722RL (TBV)", "Spec": "4x22R 5% 0603x4 convex"},
                       ref_at=(170.18, ry), val_at=(170.18, ry + 2.54))
        for (bname, bit), (pr, pl) in zip(members, rn_rows):
            bp = U103.p(next(p.num for p in ut.pins if p.name == bname))
            rp, lp = rn.p(pr), rn.p(pl)
            assert abs(rp[1] - bp[1]) < 1e-6, (ref, bname, rp, bp)
            sch.wire(rp, bp)
            sch.wire(lp, (lp[0] - 7.62, lp[1]))
            sch.label(f"Z_D{bit}", (lp[0] - 7.62, lp[1]), "left")
            an = bname.replace("B", "A")
            ap = U103.p(next(p.num for p in ut.pins if p.name == an))
            sch.wire(ap, (ap[0] + 7.62, ap[1]))
            sch.hlabel(f"LD{bit}", "bidirectional", (ap[0] + 7.62, ap[1]), "right")
    oe_pts = [U103.p("48"), U103.p("25")]
    dir_pts = [U103.p("1"), U103.p("24")]
    for pts, name in ((oe_pts, "ZF_DBUF_OE_N"), (dir_pts, "ZF_DBUF_DIR")):
        st = [(p[0] + 2.54, p[1]) for p in pts]
        for p_, s in zip(pts, st):
            sch.wire(p_, s)
        sch.wire(st[0], st[1])
        sch.wire(st[0], (st[0][0] + 7.62, st[0][1]))
        sch.junction(st[0])
        sch.hlabel(name, "input", (st[0][0] + 7.62, st[0][1]), "right")
    tie([U103.p("7"), U103.p("18")], "up", P5)
    t = [U103.p("31"), U103.p("42")]
    st = [(p[0], p[1] - 2.54) for p in t]
    for p_, s in zip(t, st):
        sch.wire(p_, s)
    sch.wire(st[0], st[1])
    sch.wire(st[1], (st[1][0] + 2.54, st[1][1]))
    sch.junction(st[1])
    pwr(P3, st[1][0] + 2.54, st[1][1])
    tie([U103.p(n) for n in ("4", "10", "15", "21", "28", "34", "39", "45")], "down", GNDS)
    sch.text("B port = Zorro D0-D15 (VCCB = +5V_BUS): drives full 5 V levels.\nA port = local bus LD0-LD15 "
             "(VCCA = +3V3).\nDIR=H: A->B (card drives Zorro, reads). DIR=L: B->A.\n~{OE}=H: both ports Hi-Z "
             "(isolation).\nBus-hold on all data inputs: no pull resistors (TI SCES635B).\nVCC isolation: either "
             "supply at 0 V -> all outputs Hi-Z.\nRN101-RN104: 22R series damping, value TBV by SI measurement.",
             (172.72, 152.4), 1.27)

    # ---------------- U104 /SLAVEn, /CFGOUTn driver ----------------------------
    u2 = syms["LVC2T45"]
    U104 = sch.place(u2, "U104", "SN74LVC2T45DCTR", 226.06, 190.5, ref_at=(217.17, 177.8), val_at=(234.95, 203.2),
                      ref_just="right", val_just="left")
    for pn, net in (("2", "ZF_SLAVE_N"), ("3", "ZF_CFGOUT_N")):
        p_ = U104.p(pn)
        sch.wire(p_, (p_[0] - 7.62, p_[1]))
        sch.hlabel(net, "input", (p_[0] - 7.62, p_[1]), "left")
    dp = U104.p("5")
    sch.wire(dp, (dp[0] - 2.54, dp[1]))
    pwr(P3, dp[0] - 2.54, dp[1], 90, val_at=(dp[0] - 9.0, dp[1]))
    for pn, ref, rx, net in (("7", "R117", 245.11, "Z_SLAVE_N"), ("6", "R118", 255.27, "Z_CFGOUT_N")):
        p_ = U104.p(pn)
        r = sch.place(R, ref, "22R", rx, p_[1], 90, footprint="Resistor_SMD:R_0603_1608Metric",
                      props={"Spec": "0603 1% 0.1 W"}, ref_at=(rx, p_[1] - 2.2), val_at=(rx, p_[1] + 2.2))
        a, b = r.p("1"), r.p("2")
        sch.wire(p_, a)
        sch.wire(b, (b[0] + 5.08, b[1]))
        sch.label(net, (b[0] + 5.08, b[1]), "right")
    pwr(P3, *U104.p("1"), val_at=(U104.p("1")[0] - 4.0, U104.p("1")[1] - 3.6))
    pwr(P5, *U104.p("8"), val_at=(U104.p("8")[0] + 5.0, U104.p("8")[1] - 3.6))
    pwr(GNDS, *U104.p("4"))
    sch.text("U104 has no ~{OE}: outputs follow A inputs, held HIGH\n(inactive) by 2.2k pull-ups while the FPGA is\n"
             "unconfigured. DIR=H (A->B). /SLAVEn path: see\nsheet notes (35 ns budget).", (172.72, 210.82), 1.27)

    # ---------------- U105 open-drain drivers ----------------------------------
    uo = syms["LVC07A"]
    U105 = sch.place(uo, "U105", "SN74LVC07APWR", 226.06, 251.46, ref_at=(217.17, 233.68), val_at=(234.95, 274.32),
                      ref_just="right", val_just="left")
    od = [("1", "2", "ZF_INT2_N", "Z_INT2_N", None), ("3", "4", "ZF_INT6_N", "Z_INT6_N", None),
          ("5", "6", "ZF_XRDY", "Z_XRDY", None), ("9", "8", "ZF_OVR_N", "Z_OVR_N", ("R119", 245.11)),
          ("11", "10", "ZF_DTACK_N", "Z_DTACK_N", ("R120", 255.27))]
    for ain, yout, fnet, znet, dnp in od:
        pa, py = U105.p(ain), U105.p(yout)
        sch.wire(pa, (pa[0] - 7.62, pa[1]))
        sch.hlabel(fnet, "input", (pa[0] - 7.62, pa[1]), "left")
        if dnp:
            ref, rx = dnp
            r = sch.place(R, ref, "0R DNP", rx, py[1], 90, footprint="Resistor_SMD:R_0603_1608Metric", dnp=True,
                          props={"Spec": "0603 jumper, fit only if own DTACK/OVR is ever needed"},
                          ref_at=(rx, py[1] - 2.2), val_at=(rx, py[1] + 2.2))
            sch.wire(py, r.p("1"))
            sch.wire(r.p("2"), (r.p("2")[0] + 5.08, py[1]))
            sch.label(znet, (r.p("2")[0] + 5.08, py[1]), "right")
        else:
            sch.wire(py, (py[0] + 7.62, py[1]))
            sch.label(znet, (py[0] + 7.62, py[1]), "right")
    p6 = U105.p("13")
    sch.wire(p6, (p6[0] - 2.54, p6[1]))
    pwr(P3, p6[0] - 2.54, p6[1], 90, val_at=(p6[0] - 9.0, p6[1]))
    sch.noconnect(U105.p("12"))
    pwr(P3, *U105.p("14"), val_at=(U105.p("14")[0] + 4.5, U105.p("14")[1] - 3.6))
    pwr(GNDS, *U105.p("7"))
    sch.text("Open-drain (wired-OR per Zorro spec): /INT2, /INT6, XRDY.\nFPGA drives input LOW to assert. XRDY is "
             "kept fitted\n(wait-state provision; zero-wait timing is NOT assumed\nuntil measured). /OVR, /DTACK paths "
             "DNP (automatic\nDTACK used). Spare channel 6: input tied high.", (172.72, 281.94), 1.27)

    # ---------------- default-state (safe start-up) resistor bank -------------
    bank = [("R101", "ZF_SLAVE_N"), ("R102", "ZF_CFGOUT_N"), ("R103", "ZF_INT2_N"), ("R104", "ZF_INT6_N"),
            ("R105", "ZF_XRDY"), ("R106", "ZF_OVR_N"), ("R107", "ZF_DTACK_N"), ("R108", "ZF_DBUF_OE_N")]
    bx, by = 304.8, 63.5
    sch.text("SAFE START-UP DEFAULTS. MachXO2 I/O are tri-stated with a weak pull-DOWN (IPD 30-305 uA) before/during\n"
             "configuration (Lattice FPGA-DS-02056-4.7). 2.2k pull-ups hold every Zorro output INACTIVE: node >= 3.0 V - "
             "2.2k x 305 uA = 2.33 V > VIH 2.0 V.\nDIR pull-down keeps U103 pointing Zorro->local (never drives the Zorro bus).",
             (bx - 5.08, 40.64), 1.27)
    for i, (ref, net) in enumerate(bank):
        x = bx + 22.86 * i
        r = sch.place(R, ref, "2.2k", x, by, 0, footprint="Resistor_SMD:R_0603_1608Metric", props={"Spec": "0603 1% 0.1 W"},
                      ref_at=(x + 1.8, by - 1.3), val_at=(x + 1.8, by + 1.3), ref_just="left", val_just="left")
        pwr(P3, *r.p("1"))
        b = r.p("2")
        sch.wire(b, (b[0], b[1] + 5.08))
        sch.hlabel(net, "input", (b[0], b[1] + 5.08), "right")
    x = bx + 22.86 * len(bank)
    r = sch.place(R, "R109", "10k", x, by, 0, footprint="Resistor_SMD:R_0603_1608Metric", props={"Spec": "0603 1% 0.1 W"},
                  ref_at=(x + 1.8, by - 1.3), val_at=(x + 1.8, by + 1.3), ref_just="left", val_just="left")
    a = r.p("1")
    sch.wire(a, (a[0], a[1] - 5.08))
    sch.hlabel("ZF_DBUF_DIR", "input", (a[0], a[1] - 5.08), "right")
    pwr(GNDS, *r.p("2"))

    # ---------------- decoupling ------------------------------------------------
    caps = [("C101", "100n", P3, "U101"), ("C102", "100n", P3, "U101"), ("C103", "100n", P3, "U101"),
            ("C104", "100n", P3, "U101"), ("C105", "100n", P3, "U102"), ("C106", "100n", P3, "U102"),
            ("C107", "100n", P3, "U102"), ("C108", "100n", P3, "U102"), ("C109", "100n", P3, "U103 VCCA"),
            ("C110", "100n", P3, "U103 VCCA"), ("C111", "100n", P5, "U103 VCCB"), ("C112", "100n", P5, "U103 VCCB"),
            ("C113", "100n", P3, "U104 VCCA"), ("C114", "100n", P5, "U104 VCCB"), ("C115", "100n", P3, "U105"),
            ("C116", "10u", P3, "bulk +3V3"), ("C117", "10u", P5, "bulk +5V_BUS")]
    cx, cy = 304.8, 116.84
    sch.text("DECOUPLING: one 100 nF per supply pin, placed at the pin (PCB); 10 uF bulk per rail on this sheet.",
             (cx - 5.08, 100.33), 1.27)
    for i, (ref, val, ps, note) in enumerate(caps):
        x = cx + 12.7 * i
        fp = "Capacitor_SMD:C_0805_2012Metric" if val == "10u" else "Capacitor_SMD:C_0603_1608Metric"
        spec = "0805 X5R 16 V" if val == "10u" else "0603 X7R 25 V"
        c = sch.place(C, ref, val, x, cy, 0, footprint=fp, props={"Spec": spec, "Note": note},
                      ref_at=(x + 2.5, cy - 1.3), val_at=(x + 2.5, cy + 1.3), ref_just="left", val_just="left")
        pwr(ps, *c.p("1"), hide_value=False)
        pwr(GNDS, *c.p("2"), hide_value=True)

    # ---------------- test points ---------------------------------------------
    tps = ["Z_AS_N", "Z_SLAVE_N", "Z_DOE", "Z_E7M", "Z_READ", "Z_UDS_N", "Z_LDS_N", "Z_CFGIN_N", "Z_CFGOUT_N",
           "Z_INT2_N", "Z_XRDY", "Z_BUSRST_N", "Z_BERR_N", "ZB_AS_N", "ZF_SLAVE_N"]
    tx, ty = 304.8, 160.02
    sch.text("TEST POINTS (bring-up timing: measure /AS->/SLAVEn at the edge connector and per stage; "
             "/BERR monitors bus collisions).", (tx - 5.08, 147.32), 1.27)
    for i, net in enumerate(tps):
        x = tx + 20.32 * (i % 8)
        y = ty + 20.32 * (i // 8)
        tp = sch.place(TP, f"TP{101 + i}", "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                       in_bom=False, ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
        p_ = tp.p("1")
        sch.wire(p_, (p_[0], p_[1] + 3.81))
        if net.startswith("Z_"):
            sch.label(net, (p_[0], p_[1] + 3.81), "right")
        else:
            sch.hlabel(net, "input" if net.startswith("ZF") else "output", (p_[0], p_[1] + 3.81), "right")
    for k in range(2):
        x = tx + 20.32 * k
        y = ty + 40.64
        tp = sch.place(TP, f"TP{101 + len(tps) + k}", "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                       in_bom=False, ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
        pwr(GNDS, *tp.p("1"))

    # ---------------- design notes block -----------------------------------------
    sch.text(
        "DESIGN NOTES (summary; full analysis in docs/stage2/sheet1-design-notes.md)\n"
        "1. /SLAVEn must assert <= 35 ns after /AS and negate <= 50 ns after /AS rises (Zorro III spec App. K, Zorro II\n"
        "   compatibility). Path: U102 (tpd <= 4.1 ns) + FPGA combinational (datasheet floor 7.24 ns, -4; final value from\n"
        "   Diamond STA) + U104 (tpd <= 4.4 ns) + R117 + PCB. Budget closes only if the FPGA segment is <= ~20 ns.\n"
        "2. XRDY provision is fitted. HDL default mode inserts wait states via XRDY until zero-wait timing is measured.\n"
        "3. Power-off isolation: U101/U102 Ioff, U103/U104 VCC isolation + Ioff, U105 Ioff. With the carrier unpowered,\n"
        "   /SLAVEn and /CFGOUTn float: depends on A2000 backplane pull-ups (open concern C-03).\n"
        "4. Interfaces to sheet 2 (FPGA) are hierarchical labels: ZB_* (buffered Zorro inputs), ZF_* (FPGA-driven\n"
        "   outputs), LD0-LD15 (local data bus). Power nets +3V3 / +5V_BUS come from sheet 5 (not yet drawn).\n"
        "5. Not yet validated: no ERC-clean claim implies electrical or timing correctness.",
        (304.8, 214.63), 1.27)
    return sch


# ============================================================================ root + placeholders
SHEETS = [
    (1, "01_zorro_interface.kicad_sch", "1 Zorro II interface & AutoConfig"),
    (2, "02_fpga.kicad_sch", "2 FPGA & configuration"),
    (3, "03_sram.kicad_sch", "3 Shared SRAM & arbitration"),
    (4, "04_x86_interconnect.kicad_sch", "4 x86 SBC interconnect (Radxa X4 in Rev 1)"),
    (5, "05_power.kicad_sch", "5 Power regulation & protection"),
    (6, "06_irq_diag_prog.kicad_sch", "6 Interrupts, diagnostics & programming"),
]
PLACEHOLDER_TEXT = {
    2: "Planned: LCMXO2-2000HC-4TG144C (migration LCMXO2-4000HC), 111 I/O budget (docs/pin-assignment-matrix.md),\n"
       "JTAG header + optional RP2040-driven JTAG, oscillator (optional), bank planning, decoupling.",
    3: "Planned: IS61WV25616EDBLL-10TLI 256K x 16 SRAM on local bus LD[15:0], SA[17:0], /CE /OE /WE /UB /LB.\n"
       "Do not start until sheet 1 open concerns are reviewed (docs/stage2/sheet1-design-notes.md).",
    4: "Planned: generic host link (SPI + IRQ + ATTN + JTAG option) through isolating translators powered from\n"
       "the SBC's own 3.3 V. Kept SBC-agnostic so a different x86 board can replace the Radxa X4 (ER-4).",
    5: "Planned: Molex 4-pin input, +12 V fuse/TVS/TPS25947 eFuse/INA226 to the SBC, +5 V PTC/TVS/reverse\n"
       "protection -> +5V_BUS, 3.3 V LDO -> +3V3. USB-C backfeed mitigation (R-05) to be designed here.",
    6: "Planned: status LEDs, DIP switches (mode / IRQ level / auto-start / JTAG source), debug header,\n"
       "test points, programming connector.",
}


def build_placeholder(n, root_uuid, sheet_uuid, title):
    sch = Schematic(f"sheet{n}", "A3", title.split(" ", 1)[1], REV, DATE,
                    [f"Sheet {n} of 6. PLACEHOLDER: not yet designed (Stage 2+).", "", "", f"Licence: {LICENCE}"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    sch.text(f"PLACEHOLDER - {title}\n\n{PLACEHOLDER_TEXT[n]}", (25.4, 25.4), 2.0, bold=False)
    return sch


def build_root(root_uuid, sheet_uuids, sheet1_pins, std, syms):
    sch = Schematic("root", "A3", "A2000 x86 Bridgeboard: top level", REV, DATE,
                    ["Zorro II bridgeboard carrying a removable x86 SBC (Rev 1: Radxa X4).",
                     "Hierarchy follows the brief: sheets 1-6. Only sheet 1 is drawn (Stage 2).",
                     "TEMPORARY PWR_FLAGs on +3V3/+5V_BUS until sheet 5 exists.", f"Licence: {LICENCE}"],
                    COMPANY, f"/{root_uuid}")
    sch.uuid = root_uuid
    # sheet 1 with pins
    x0, y0, w = 50.8, 30.48, 71.12
    h = 2.54 * (len(sheet1_pins) + 2)
    pins = []
    for i, (name, shape) in enumerate(sheet1_pins):
        py = y0 + 2.54 * (i + 1)
        pins.append(f"\t\t(pin {q(name)} {shape}\n\t\t\t(at {f(x0 + w)} {f(py)} 0)\n\t\t\t(uuid {q(U('root/pin/' + name))})\n"
                    f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)\n\t\t)")
    def sheet_block(n, fname, title, x, y, ww, hh, pins_txt=""):
        return (f"\t(sheet\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(ww)} {f(hh)})\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n"
                f"\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type solid)\n\t\t)\n"
                f"\t\t(fill\n\t\t\t(color 0 0 0 0)\n\t\t)\n\t\t(uuid {q(sheet_uuids[n])})\n"
                f"\t\t(property \"Sheetname\" {q(title)}\n\t\t\t(at {f(x)} {f(y - 0.76)} 0)\n\t\t\t(show_name no)\n"
                f"\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.524 1.524)\n\t\t\t\t)\n"
                f"\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)\n"
                f"\t\t(property \"Sheetfile\" {q('sheets/' + fname)}\n\t\t\t(at {f(x)} {f(y + hh + 0.6)} 0)\n"
                f"\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n"
                f"\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left top)\n\t\t\t)\n\t\t)\n"
                f"{pins_txt}"
                f"\t\t(instances\n\t\t\t(project {q(PROJECT)}\n\t\t\t\t(path {q('/' + root_uuid)}\n"
                f"\t\t\t\t\t(page {q(str(n + 1))})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)")
    sch.raw(sheet_block(1, SHEETS[0][1], SHEETS[0][2], x0, y0, w, h, "\n".join(pins) + "\n"))
    for k, (n, fname, title) in enumerate(SHEETS[1:]):
        sch.raw(sheet_block(n, fname, title, 228.6, 30.48 + 30.48 * k, 106.68, 20.32))
    sch.text("Sheet-1 interface pins are intentionally unconnected at this level until sheet 2 (FPGA) is drawn.\n"
             "ERC reports for these are expected and listed in docs/stage2/sheet1-erc-report.md.", (50.8, y0 + h + 7.62), 1.27)
    sch.text("+3V3 and +5V_BUS are sourced by sheet 5 (not yet drawn). TEMPORARY PWR_FLAGs on sheet 1\n"
             "declare them driven so ERC can check sheet 1; remove them when sheet 5 exists.", (228.6, 238.76), 1.27)
    return sch


def main(repo: Path):
    kdir = repo / "hardware" / "kicad"
    (kdir / "sheets").mkdir(parents=True, exist_ok=True)
    (kdir / "lib" / f"{LIB}.pretty").mkdir(parents=True, exist_ok=True)
    syms = {"LVC16244": sym_lvc16244(), "LVCH16T245": sym_lvch16t245(), "LVC2T45": sym_lvc2t45(),
            "LVC07A": sym_lvc07a(), "ZORRO": sym_zorro(), "+5V_BUS": sym_power("+5V_BUS")}
    write_symbol_lib(kdir / "lib" / f"{LIB}.kicad_sym", list(syms.values()))
    write_zorro_footprint(kdir / "lib" / f"{LIB}.pretty" / "Zorro2_Edge_2x50_P2.54mm.kicad_mod")
    std = {"R": StdSymbol(KICAD_SYM / "Device.kicad_sym", "Device", "R"),
           "C": StdSymbol(KICAD_SYM / "Device.kicad_sym", "Device", "C"),
           "RN": StdSymbol(KICAD_SYM / "Device.kicad_sym", "Device", "R_Pack04"),
           "TP": StdSymbol(KICAD_SYM / "Connector.kicad_sym", "Connector", "TestPoint"),
           "+3V3": StdSymbol(KICAD_SYM / "power.kicad_sym", "power", "+3V3"),
           "GND": StdSymbol(KICAD_SYM / "power.kicad_sym", "power", "GND"),
           "FLAG": StdSymbol(KICAD_SYM / "power.kicad_sym", "power", "PWR_FLAG")}
    root_uuid = U("root")
    sheet_uuids = {n: U(f"sheetblock{n}") for n, _, _ in SHEETS}
    s1 = build_sheet1(repo, root_uuid, sheet_uuids[1], syms, std)
    s1.write(kdir / "sheets" / SHEETS[0][1])
    # sheet-1 interface (unique hierarchical labels in order of appearance)
    seen, s1pins = set(), []
    import re
    for m in re.finditer(r'\(hierarchical_label "([^"]+)"\n\t\t\(shape (\w+)\)', "\n".join(s1.items)):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            s1pins.append((m.group(1), m.group(2)))
    def order(n):
        grp = 0 if n[0].startswith("ZB_") else 1 if n[0].startswith("LD") else 2
        return (grp, [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", n[0])])
    s1pins.sort(key=order)
    for n, fname, title in SHEETS[1:]:
        build_placeholder(n, root_uuid, sheet_uuids[n], title).write(kdir / "sheets" / fname)
    root = build_root(root_uuid, sheet_uuids, s1pins, std, syms)
    root.write(kdir / f"{PROJECT}.kicad_sch", "\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)")
    (kdir / "sym-lib-table").write_text(
        f"(sym_lib_table\n\t(version 7)\n\t(lib (name \"{LIB}\") (type \"KiCad\") (uri \"${{KIPRJMOD}}/lib/{LIB}.kicad_sym\") "
        f"(options \"\") (descr \"Project symbols (pins verified against TI datasheets)\"))\n)\n", encoding="utf-8")
    (kdir / "fp-lib-table").write_text(
        f"(fp_lib_table\n\t(version 7)\n\t(lib (name \"{LIB}\") (type \"KiCad\") (uri \"${{KIPRJMOD}}/lib/{LIB}.pretty\") "
        f"(options \"\") (descr \"Project footprints\"))\n)\n", encoding="utf-8")
    pro = {"meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
           "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
           "sheets": [[root_uuid, "Root"]] + [[sheet_uuids[n], t] for n, _, t in SHEETS],
           "text_variables": {"LICENCE": LICENCE}}
    (kdir / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
    print("sheet-1 interface pins:", len(s1pins))
    print("placed symbols on sheet 1:", len(s1.placed))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
