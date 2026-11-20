# SPDX-License-Identifier: MIT
"""Sheet 6 (diagnostics, configuration switches, debug header) for tools/kicad/gen_project.py.

Owner decisions S6-1 to S6-5 (review of PR #12; G-SHEET6 approved for design progression, with the debug-header
isolation and the JTAG contention protection needing further evidence before final approval). Design notes:
docs/stage2/sheet6-design-notes.md.

  LEDs (S6-1): D601 LED_READY (FPGA pin 65, independent of the N100/RP2040), D602-D605 LED_RP0-3 (RP2040 GP16-19 through
        U404's carrier-side A outputs; meanings FW-9 to FW-12), D606 +3V3 present, D607 X4_12V present (any source,
        indicator only). Each about 1 mA.
  DIP (S6-2): SW601. Positions 1-3 switch +3V3 through 1k to DIP_MODE_B / DIP_INT6 / DIP_DISABLE, each with a 10k
        pull-down (ON = function active; the RTL inputs are active high). Position 4 switches RP_JTAG_EN_N to GND through
        1k against sheet 4's R407 10k pull-up (active low). All OFF = 64 KB mode, INT2, armed, JTAG option isolated.
  Debug header (S6-4, option B): J601 2x5 keyed box header. DBG0-3 pass U601 SN74AVC4T774 (Ioff, VCC isolation [V S66]):
        A side = carrier +3V3 through 330R series resistors, B side = DBG_VREF through 33R. DBG_VREF is the header's
        protected 3.3 V: +3V3 -> F601 PTC -> D608 Schottky, so no tool can back-feed the carrier. DIR straps: DBG0-2
        header -> FPGA, DBG3 FPGA -> header (SPI-slave arrangement for the future faster host interface); a strap moves to
        change a direction. 100k pull-downs on both sides define every inactive state (R-51).
  Test points (S6-5): TP601 LED_READY, TP602 GND.
"""
from __future__ import annotations

from kisch import Schematic      # noqa: E402

LEDS = [  # ref, resistor, source net, value (colour), meaning
    ("D601", "R601", "LED_READY", "GREEN", "READY (FPGA pin 65)"),
    ("D602", "R602", "LED_RP0", "GREEN", "RP2040 link (FW-9)"),
    ("D603", "R603", "LED_RP1", "GREEN", "RP2040 heartbeat (FW-10)"),
    ("D604", "R604", "LED_RP2", "YELLOW", "mailbox / interrupt activity (FW-11)"),
    ("D605", "R605", "LED_RP3", "RED", "fault (FW-12)"),
    ("D606", "R606", "+3V3", "GREEN", "carrier +3V3 present"),
    ("D607", "R607", "X4_12V", "AMBER", "X4 12 V rail present, any source (indicator only)"),
]
DIP = [  # switch position, series R, net, pull resistor, pull rail
    (1, "R608", "DIP_MODE_B", "R612", "GND"),
    (2, "R609", "DIP_INT6", "R613", "GND"),
    (3, "R610", "DIP_DISABLE", "R614", "GND"),
    (4, "R611", "RP_JTAG_EN_N", None, None),        # pulled up by R407 on sheet 4
]
DBG_DIR = {1: "BA", 2: "BA", 3: "BA", 4: "AB"}     # BA = header -> FPGA (DIR low), AB = FPGA -> header (DIR high)
DBG_PINS = {"A": {1: "3", 2: "4", 3: "5", 4: "6"}, "B": {1: "14", 2: "13", 3: "12", 4: "11"},
            "DIR": {1: "1", 2: "2", 3: "7", 4: "8"}}
J601_MAP = {1: "DBG_VREF", 3: "DBG0_H", 5: "DBG1_H", 7: "DBG2_H", 9: "DBG3_H"}   # even pins 2-10: GND


def build_sheet6(root_uuid: str, sheet_uuid: str, syms, std, consts):
    REV, DATE, COMPANY, LICENCE = consts
    sch = Schematic("sheet6", "A2", "Diagnostics, configuration switches, debug header", REV, DATE,
                    ["Sheet 6 of 6 (Stage 6, rev A). G-SHEET6: design progression; debug isolation and JTAG contention evidence open.",
                     "LEDs D601-D607; DIP SW601; debug header J601 through U601 (SN74AVC4T774); TP601/TP602",
                     "Basis: docs/stage2/sheet6-architecture-proposal.md; notes: sheet6-design-notes.md. NOT VALIDATED",
                     f"Licence: {LICENCE}"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    R, C, TP, P3, GNDS = std["R"], std["C"], std["TP"], std["+3V3"], std["GND"]
    LED, DIPSW, SCH, J25 = std["LED"], std["DIP4"], std["SCHOTTKY"], std["CONN2x5"]
    U = syms["AVC4T774"]
    n_pwr = [0]
    HIER = {"LED_READY": "input", "LED_RP0": "input", "LED_RP1": "input", "LED_RP2": "input", "LED_RP3": "input",
            "X4_12V": "input", "DIP_MODE_B": "output", "DIP_INT6": "output", "DIP_DISABLE": "output",
            "RP_JTAG_EN_N": "output", "DBG0": "bidirectional", "DBG1": "bidirectional", "DBG2": "bidirectional",
            "DBG3": "bidirectional"}

    def pwr(sym, x, y, rot=0):
        n_pwr[0] += 1
        return sch.place(sym, f"#PWR{6000 + n_pwr[0]:04d}", sym.name, x, y, rot,
                         val_at=(x, y - 3.6) if sym.name != "GND" else (x, y + 5.0), hide_value=(sym.name == "GND"),
                         ref_at=(x, y + 3))

    def stub(pt, dx, dy=0.0):
        end = (round(pt[0] + dx, 4), round(pt[1] + dy, 4))
        sch.wire(pt, end)
        return end

    def net_at(pt, net, dx, dy, side):
        e = stub(pt, dx, dy)
        if net == "GND":
            pwr(GNDS, e[0], e[1], 0 if dy > 0 else (180 if dy < 0 else (270 if dx < 0 else 90)))
        elif net == "+3V3":
            pwr(P3, e[0], e[1], 180 if dy > 0 else (0 if dy < 0 else (90 if dx < 0 else 270)))
        elif net in HIER:
            sch.hlabel(net, HIER[net], e, side)
        else:
            sch.label(net, e, side)

    def two(sym, ref, val, x, y, top, bot, fp, spec):
        part = sch.place(sym, ref, val, x, y, 0, footprint=fp, props={"Spec": spec},
                         ref_at=(x + 2.5, y - 1.3), val_at=(x + 2.5, y + 1.3), ref_just="left", val_just="left")
        net_at(part.p("1"), top, 0, -3.81, "right")
        net_at(part.p("2"), bot, 0, 3.81, "right")
        return part

    R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"

    # ================================================================ LEDs (S6-1)
    for i, (dref, rref, src, colour, meaning) in enumerate(LEDS):
        x = 38.1 + 27.94 * i
        rval = "10k" if src == "X4_12V" else "1k"
        why = ("0603 1 %: (12.6 V - 2 V) / 10k = 1.1 mA, 11 mW; a load on X4_12V, indicator only (not the S5-9 detection)"
               if src == "X4_12V" else "0603 1 %: about 1.2 mA from 3.3 V (LED Vf ~1.9-2.1 V [K, TBV])")
        r = sch.place(R, rref, rval, x, 50.8, 0, footprint=R0603, props={"Spec": why},
                      ref_at=(x + 2.5, 49.5), val_at=(x + 2.5, 52.1), ref_just="left", val_just="left")
        net_at(r.p("1"), src, 0, -3.81, "right")
        d = sch.place(LED, dref, colour, x, 66.04, 90, footprint="LED_SMD:LED_0603_1608Metric",
                      props={"Spec": f"0603 LED, {colour.lower()}, ~2 mA rated or more; {meaning}. MPN TBV"},
                      ref_at=(x + 2.5, 64.8), val_at=(x + 2.5, 67.3), ref_just="right", val_just="right")   # rot 90: rotated frame
        sch.wire(r.p("2"), d.p("2"))                       # resistor to LED anode
        net_at(d.p("1"), "GND", 0, 2.54, "right")          # cathode
    for k, (ref, net) in enumerate((("TP601", "LED_READY"), ("TP602", "GND"))):
        x = 38.1 + 27.94 * 7 + 15.24 * k
        tp = sch.place(TP, ref, "TestPoint", x, 50.8, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm", in_bom=False,
                       ref_at=(x + 1.6, 46.6), val_at=(x + 1.6, 48.2), hide_value=True, ref_just="left")
        net_at(tp.p("1"), net, 0, 3.81, "right")

    # ================================================================ DIP switch SW601 (S6-2)
    sx, sy = 50.8, 114.3
    sw = sch.place(DIPSW, "SW601", "SW_DIP_x04", sx, sy, 0,
                   footprint="Button_Switch_SMD:SW_DIP_SPSTx04_Slide_6.7x11.72mm_W8.61mm_P2.54mm_LowProfile",
                   props={"Spec": "4-position SPST slide DIP, ON = function active: 1 512 KB mode B, 2 INT6, 3 DISABLE, "
                                  "4 RP2040 JTAG option. Silkscreen: position numbers, ON arrow and the four functions. "
                                  "Change only with the A2000 powered off. MPN TBV"},
                   ref_at=(sx - 2.54, sy - 10.0), val_at=(sx - 2.54, sy + 11.0))
    # positions 1-3: one side to +3V3 (pins 1, 2, 3 joined), position 4: one side to GND (pin 4)
    sch.wire(sw.p("1"), sw.p("2"))
    sch.wire(sw.p("2"), sw.p("3"))
    e = stub(sw.p("1"), -5.08)
    pwr(P3, e[0], e[1], 0)
    net_at(sw.p("4"), "GND", -5.08, 0, "left")
    for pos, pin in ((1, "8"), (2, "7"), (3, "6"), (4, "5")):
        sch.label(f"DIP{pos}_SW", stub(sw.p(pin), 7.62), "right")
    for i, (pos, rs, net, rp, rail) in enumerate(DIP):
        x = 101.6 + 15.24 * i
        two(R, rs, "1k", x, sy, f"DIP{pos}_SW", net, R0603,
            "0603 1 %: series protection (ESD, misconnection); ON level 3.3 x 10/11 = 3.0 V" if rail else
            "0603 1 %: series protection; ON level 3.3 x 1/11 = 0.3 V < 0.7 V (U403 /OE VIL [V S66])")
    for i, (pos, rs, net, rp, rail) in enumerate([d for d in DIP if d[3]]):
        x = 101.6 + 15.24 * (4 + i)
        two(R, rp, "10k", x, sy, net, rail, R0603, "0603 1 %: pull-down at the FPGA pin: OFF = 0 = default (RTL active high)")

    # ================================================================ debug header (S6-4, option B)
    two(std["PTC"], "F601", "0.05A", 38.1, 177.8, "+3V3", "DBG_3V3_F", "Fuse:Fuse_1206_3216Metric",
        "PTC 0.05 A hold (1206 class): limits the tool supply on J601 pin 1 (keeps +3V3 within its 0.25 A design maximum). MPN TBV")
    dd = sch.place(SCH, "D608", "SCHOTTKY", 55.88, 177.8, 90, footprint="Diode_SMD:D_SOD-323",
                   props={"Spec": "Schottky (BAT54J class [K, TBV]): +3V3 -> DBG_VREF only; a tool driving J601 pin 1 "
                                  "cannot back-feed the carrier (reverse leakage uA)"},
                   ref_at=(58.4, 176.5), val_at=(58.4, 179.1), ref_just="right", val_just="right")   # rot 90: rotated frame
    net_at(dd.p("2"), "DBG_3V3_F", 0, -3.81, "right")      # anode
    net_at(dd.p("1"), "DBG_VREF", 0, 3.81, "right")        # cathode
    for i, (ref, val, net, fp, spec) in enumerate((("C603", "1u", "DBG_VREF", C0805, "0805 X7R 16 V: tool supply"),
                                                   ("C602", "100n", "DBG_VREF", C0603, "0603 X7R 25 V: U601 VCCB"),
                                                   ("C601", "100n", "+3V3", C0603, "0603 X7R 25 V: U601 VCCA"))):
        two(C, ref, val, 76.2 + 12.7 * i, 177.8, net, "GND", fp, spec)
    ux, uy = 190.5, 190.5
    u = sch.place(U, "U601", "SN74AVC4T774PWR", ux, uy, 0,
                  props={"Spec": "S6-4 option B: debug-header isolation. Ioff <= 1 uA and both ports Hi-Z if either supply is "
                                 "at GND [V S66], in every FPGA state (erased, configuring, failed) and with the carrier off"},
                  ref_at=(ux - 10.16, uy - 23.0), val_at=(ux - 10.16, uy + 26.0))
    pwr(P3, *stub(u.p("16"), 0, -5.08))
    fx, fy = 205.74, 157.48                                  # DBG_VREF is fed through D608 (passive): declare it driven
    sch.place(std["FLAG"], "#FLG6001", "PWR_FLAG", fx, fy, 0, ref_at=(fx, fy - 8.0), val_at=(fx + 1.27, fy - 3.2), val_just="left")
    sch.label("DBG_VREF", stub((fx, fy), 0, 3.81), "right")
    sch.label("DBG_VREF", stub(u.p("15"), 0, -5.08), "right")
    pwr(GNDS, *u.p("10"))
    net_at(u.p("9"), "GND", -5.08, 0, "left")              # OE low: enabled while both supplies are up
    for ch in range(1, 5):
        sch.label(f"DBG{ch - 1}_A", stub(u.p(DBG_PINS["A"][ch]), -7.62), "left")
        sch.label(f"DBG{ch - 1}_B", stub(u.p(DBG_PINS["B"][ch]), 7.62), "right")
        sch.label(f"DBG_DIR{ch}", stub(u.p(DBG_PINS["DIR"][ch]), -7.62 if ch % 2 else -15.24), "left")
    jx, jy = 330.2, 190.5
    j = sch.place(J25, "J601", "DEBUG", jx, jy, 0, footprint="Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical",
                  props={"Spec": "2x5 2.54 mm keyed box header: 1 DBG_VREF (protected 3.3 V out, about 2.9-3.1 V after D608, 0.05 A PTC), "
                                 "3/5/7/9 DBG0-DBG3, 2/4/6/8/10 GND (a ground beside every signal). Silkscreen: pin 1 mark, "
                                 "full pinout, directions (DBG0-2 in, DBG3 out by default)"},
                  ref_at=(jx - 1.27, jy - 9.0), val_at=(jx - 1.27, jy + 10.0))
    for pn, net in J601_MAP.items():
        sch.label(net, stub(j.p(str(pn)), -7.62), "left")
    for a_, b_ in ((2, 4), (4, 6), (6, 8), (8, 10)):
        sch.wire(j.p(str(a_)), j.p(str(b_)))
    net_at(j.p("10"), "GND", 5.08, 0, "right")
    # resistor rows: A-side series and pull-downs (FPGA side), B-side series and pull-downs, DIR straps
    rows = []
    for ch in range(4):
        rows.append((f"R{619 + ch}", "330R", f"DBG{ch}", f"DBG{ch}_A",
                     "0603 1 %: FPGA <-> U601 A; limits contention if the RTL drives a pin the strap makes an input "
                     "(<= 3.6 V / 330 R = 10.9 mA)"))
    for ch in range(4):
        rows.append((f"R{623 + ch}", "100k", f"DBG{ch}", "GND", "0603 1 %: FPGA-side default low (R-51)"))
    for ch in range(4):
        rows.append((f"R{627 + ch}", "33R", f"DBG{ch}_B", f"DBG{ch}_H", "0603 1 %: header-side source termination"))
    for ch in range(4):
        rows.append((f"R{631 + ch}", "100k", f"DBG{ch}_B", "GND", "0603 1 %: B side defined with the header open"))
    for ch in range(1, 5):
        top, bot = ("+3V3", f"DBG_DIR{ch}") if DBG_DIR[ch] == "AB" else (f"DBG_DIR{ch}", "GND")
        rows.append((f"R{614 + ch}", "10k", top, bot, "0603: DIR strap, " +
                     ("FPGA -> header (DBG3: MISO of an SPI slave)" if DBG_DIR[ch] == "AB" else "header -> FPGA")))
    for i, (ref, val, top, bot, spec) in enumerate(rows):
        x, y = 30.48 + 15.24 * (i % 10), 251.46 + 30.48 * (i // 10)
        two(R, ref, val, x, y, top, bot, R0603, spec)

    sch.text(
        "DESIGN NOTES (summary; full analysis in docs/stage2/sheet6-design-notes.md)\n"
        "1. LEDs: READY = FPGA pin 65 (off: blank/configuring/reset/not armed; ~1.5 Hz blink: armed, not configured; steady: configured;\n"
        "   ~12 Hz blink: watchdog flag). RP0 link, RP1 heartbeat, RP2 mailbox/IRQ, RP3 fault (FW-9..FW-12): off whenever the RP2040,\n"
        "   the X4 or the carrier is off. +3V3 LED: carrier logic power. X4 LED: X4 12 V rail live from ANY source - INDICATOR ONLY.\n"
        "2. SW601 ON = active: 1 512 KB mode, 2 INT6, 3 disable, 4 RP2040 JTAG option. All OFF = 64 KB, INT2, armed, JTAG isolated.\n"
        "   1-3 are sampled only during a Zorro reset (STATUS b4-b6 show them live). 4 acts immediately. Change with the A2000 off.\n"
        "3. SW601-4 ON ONLY WITH NO CABLE ON J201. If both drive JTAG, U403's 330R resistors (sheet 4) limit the current to 10.9 mA.\n"
        "4. J601 debug header through U601 (Ioff, VCC isolation): no path into the FPGA when it is erased, configuring or unpowered.\n"
        "   Pin 1 is a protected output (PTC + Schottky): a tool cannot back-feed the carrier. Default: DBG0-2 in, DBG3 out (straps).\n"
        "5. Not yet validated: an ERC-clean result does not imply electrical correctness. No PCB manufacture authorised.",
        (25.4, 330.2), 1.27)
    return sch
