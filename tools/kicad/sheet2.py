# SPDX-License-Identifier: MIT
"""Sheet 2 (FPGA and configuration) for tools/kicad/gen_project.py.

The FPGA symbol is generated from the Lattice MachXO2-2000 pinout file (tools/fpga/, S63), and every
signal pin comes from the pin plan in tools/fpga/pinplan.py, so the schematic, the LPF LOCATEs and
docs/stage2/sheet2-pin-assignment.md cannot disagree. Configuration and decoupling follow the
MachXO2 Hardware Checklist FPGA-TN-02154-2.2 (S64); the oscillator follows the ECS-2520MV data sheet.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fpga"))
from kisch import Pin, Schematic, SymbolDef      # noqa: E402
import pinplan                                    # noqa: E402

CSV = Path(__file__).resolve().parents[1] / "fpga" / "MachXO2-2000_TQFP144_pins.csv"
CSV4000 = Path(__file__).resolve().parents[1] / "fpga" / "MachXO2-4000_TQFP144_pins.csv"
CONFIG_PINS = {"DONE": "FPGA_DONE", "INITN": "FPGA_INITN", "PROGRAMN": "FPGA_PROGRAMN", "JTAGENB": "FPGA_JTAGENB",
               "TMS": "FPGA_TMS", "TCK": "FPGA_TCK", "TDI": "FPGA_TDI", "TDO": "FPGA_TDO"}
UNITS = {1: ["0"], 2: ["1"], 3: ["2"], 4: ["3", "4", "5"]}        # unit 5 = power


def all_pins(path=CSV):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="replace")))
    h = next(i for i, r in enumerate(rows) if r and r[0] == "PAD")
    hdr = rows[h]
    out = {}
    for r in rows[h + 1:]:
        if r and r[0].strip():
            d = dict(zip(hdr, r))
            if d.get("TQFP144", "-") not in ("-", ""):
                out[int(d["TQFP144"])] = (d["Pin/Ball Function"], d["Bank"], d["Dual Function"])
    return out


def net_name(sig: str) -> str:
    """HDL/LPF port name -> schematic net name (sheet-1/3 naming)."""
    m = re.match(r"^(\w+)\[(\d+)\]$", sig)
    if sig == "clk_core":
        return "CLK_50M"
    if m:
        base, i = m.group(1), m.group(2)
        if base == "LED":
            return {"0": "LED_READY", "1": "LED_FAULT"}[i]
        return f"{base}{i}"
    return sig


def plan_assignment(repo: Path):
    """{pin: schematic net} and {signal: direction} from tools/fpga/pinplan.py (one source of truth)."""
    assign, usable, spare, errors = pinplan.compute(repo)
    if errors:
        raise SystemExit("pin plan errors: " + "; ".join(errors))
    return {p: net_name(n) for n, p in assign.items()}, {n: d for n, d, *_ in pinplan.PLAN}


def sym_lcmxo2():
    pins = []
    pin_tab = all_pins()
    for unit, banks in UNITS.items():
        io = sorted(p for p, (fn, b, dfn) in pin_tab.items() if b in banks and re.match(r"P[LRTB]\d", fn))
        for k, p in enumerate(io):
            fn, b, dfn = pin_tab[p]
            name = fn + (f"/{dfn}" if dfn not in ("-", "") else "")
            pins.append(Pin(str(p), name, "bidirectional", -20.32, 35.56 - 2.54 * k, 0, 5.08, unit=unit))
    pw = sorted(p for p, (fn, b, dfn) in pin_tab.items() if not re.match(r"P[LRTB]\d", fn))
    vcc = [p for p in pw if pin_tab[p][0] == "VCC"]
    vio = [p for p in pw if pin_tab[p][0].startswith("VCCIO")]
    gnd = [p for p in pw if pin_tab[p][0] == "GND"]
    nc = [p for p in pw if pin_tab[p][0] == "NC"]
    for k, p in enumerate(vcc):
        pins.append(Pin(str(p), "VCC", "power_in", -7.62 + 5.08 * k, 25.4, 270, 5.08, unit=5))
    for k, p in enumerate(sorted(vio, key=lambda p: (pin_tab[p][0], p))):
        pins.append(Pin(str(p), pin_tab[p][0], "power_in", -20.32, 15.24 - 2.54 * k, 0, 5.08, unit=5))
    for k, p in enumerate(gnd):
        pins.append(Pin(str(p), "GND", "power_in", -13.97 + 2.54 * k, -25.4, 90, 5.08, unit=5))
    for k, p in enumerate(nc):
        pins.append(Pin(str(p), "NC", "no_connect", 20.32, 7.62 - 2.54 * k, 180, 5.08, unit=5))
    rects = {u: [(-15.24, 38.1, 15.24, -35.56)] for u in (1, 2, 3, 4)}
    rects[5] = [(-15.24, 20.32, 15.24, -20.32)]
    return SymbolDef(
        "LCMXO2-2000HC-TG144", "U", "LCMXO2-2000HC-4TG144C", "Package_QFP:TQFP-144_20x20mm_P0.5mm",
        "https://www.latticesemi.com/view_document?document_id=38834",
        "Lattice MachXO2-2000HC FPGA, TQFP-144. Units: A bank 0, B bank 1, C bank 2, D banks 3-5, E power. "
        "Pins from the Lattice MachXO2-2000 Pinout rev 1.2 (document 42568)",
        pins, rects=rects, units=5, extra_props={"Manufacturer": "Lattice Semiconductor", "MPN": "LCMXO2-2000HC-4TG144C"},
        keywords="fpga lattice machxo2 tqfp144", ref_at=(-15.24, 40.0), value_at=(-15.24, -38.0))


def sym_ecs2520mv():
    # ECS-2520MV data sheet: 1 Tri-state (>= 0.7 Vdd or NC = active), 2 GND, 3 Output, 4 Vdd
    pins = [Pin("1", "OE", "input", -10.16, 2.54, 0, 5.08), Pin("3", "OUT", "output", 10.16, 0, 180, 5.08),
            Pin("4", "VDD", "power_in", 0, 10.16, 270, 5.08), Pin("2", "GND", "power_in", 0, -10.16, 90, 5.08)]
    return SymbolDef(
        "ECS-2520MV", "X", "ECS-2520MV-500-BN-TR", "Oscillator:Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm",
        "https://ecsxtal.com/store/pdf/ECS-2520MV.pdf",
        "CMOS oscillator 50.000 MHz, 1.6-3.6 V, +/-50 ppm (-40 to +85 C), 15 pF load, 2.5 x 2.0 mm (ECS-2520MV)",
        pins, rects={1: [(-5.08, 5.08, 5.08, -5.08)]}, extra_props={"Manufacturer": "ECS Inc.", "MPN": "ECS-2520MV-500-BN-TR"},
        keywords="oscillator cmos 50MHz", ref_at=(-5.08, 6.5), value_at=(-5.08, -7.0))


def build_sheet2(repo: Path, root_uuid: str, sheet_uuid: str, syms, std, consts):
    REV2, DATE2, COMPANY, LICENCE = consts
    sch = Schematic("sheet2", "A2", "FPGA and configuration", REV2, DATE2,
                    ["Sheet 2 of 6, rev A1. G-SHEET2 approved for design progression; NOT VALIDATED",
                     "LCMXO2-2000HC-4TG144C: 101 signals, 3 spare (C-17, C-26); 4000HC pin-compatible",
                     "Pins: tools/fpga/pinplan.py, Lattice pinout rev 1.2; FPGA-TN-02154-2.2",
                     f"Licence: {LICENCE}. See docs/stage2/sheet2-design-notes.md"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    R, C, TP = std["R"], std["C"], std["TP"]
    P3, GNDS = std["+3V3"], std["GND"]
    pwr_n = [0]

    def pwr(sym, x, y, rot=0):
        pwr_n[0] += 1
        name = sym.name
        return sch.place(sym, f"#PWR{2000 + pwr_n[0]:04d}", name, x, y, rot,
                         val_at=(x, y - 3.6) if name != "GND" else (x, y + 5.0), hide_value=(name == "GND"),
                         ref_at=(x, y + 3))

    nets, dirs = plan_assignment(repo)
    pin_tab = all_pins()
    fp = syms["LCMXO2"]
    spare = []
    # ---------------- I/O units
    positions = {1: (76.2, 76.2), 2: (76.2, 190.5), 3: (76.2, 304.8), 4: (203.2, 76.2)}
    for unit, (ux, uy) in positions.items():
        u = sch.place(fp, "U201", "LCMXO2-2000HC-4TG144C", ux, uy, 0, unit=unit,
                      ref_at=(ux - 15.24, uy - 40.0), val_at=(ux - 15.24, uy + 38.5))
        for p_ in [p for p in fp.pins if p.unit == unit]:
            pn = int(p_.num)
            pt = u.p(p_.num)
            fn, bank, dfn = pin_tab[pn]
            cfg = next((CONFIG_PINS[k] for k in CONFIG_PINS if k in re.split(r"[/ ]", dfn)), None)
            end = (round(pt[0] - 10.16, 4), pt[1])
            if pn in nets:
                sch.wire(pt, end)
                net = nets[pn]
                if net == "CLK_50M":
                    sch.label(net, end, "left")
                else:
                    sch.hlabel(net, "bidirectional", end, "left")
            elif cfg:
                sch.wire(pt, end)
                if cfg in ("FPGA_TMS", "FPGA_TCK", "FPGA_TDI", "FPGA_TDO"):
                    sch.hlabel(cfg, "bidirectional", end, "left")      # JTAG: header here, RP2040 option on sheet 4
                else:
                    sch.label(cfg, end, "left")
            else:
                sch.noconnect(pt)
                spare.append(pn)
    # ---------------- power unit
    ux, uy = 203.2, 228.6
    u = sch.place(fp, "U201", "LCMXO2-2000HC-4TG144C", ux, uy, 0, unit=5, ref_at=(ux - 15.24, uy - 23.0),
                  val_at=(ux + 10.16, uy - 23.0), val_just="left")
    pins5 = [p for p in fp.pins if p.unit == 5]
    for p_ in pins5:
        if p_.name == "NC":
            sch.noconnect(u.p(p_.num))

    def rail(pts, axis, offset, ext, sym):
        """Join pins to one rail: a stub from each pin to the rail, the rail split at every stub (junction at each
        T), extended past the first (ext < 0) or last (ext > 0) stub to a single power symbol."""
        k = 1 if axis == "x" else 0                      # coordinate that varies along the rail
        taps = []
        for pt in pts:
            tap = (pt[0], round(pt[1] + offset, 4)) if axis == "x" else (round(pt[0] + offset, 4), pt[1])
            sch.wire(pt, tap)
            taps.append(tap)
        taps.sort(key=lambda t: t[1 - k])
        end = list(taps[0] if ext < 0 else taps[-1])
        end[1 - k] = round(end[1 - k] + ext, 4)
        end = tuple(end)
        chain = ([end] + taps) if ext < 0 else (taps + [end])
        for a, b in zip(chain, chain[1:]):
            sch.wire(a, b)
        for t in taps:
            if t != (taps[-1] if ext < 0 else taps[0]):  # every tap except the far corner is a T
                sch.junction(t)
        pwr(sym, end[0], end[1])

    rail([u.p(p.num) for p in pins5 if p.name == "VCC"], "x", -2.54, -5.08, P3)          # top: VCC
    rail([u.p(p.num) for p in pins5 if p.name == "GND"], "x", 2.54, 5.08, GNDS)          # bottom: GND
    rail([u.p(p.num) for p in pins5 if p.name.startswith("VCCIO")], "y", -5.08, -5.08, P3)  # left: VCCIO0-5
    nc = sorted(p for p, v in pin_tab.items() if v[0] == "NC")
    p4 = all_pins(CSV4000)
    nc_io4 = [p for p in nc if re.match(r"P[LRTB]\d", p4[p][0])]
    sch.text("POWER (data sheet Table 3.2: HC core VCC 2.375-3.6 V, VCCIO 1.14-3.6 V): VCC and every VCCIO bank on the\n"
             "same +3V3 supply (Table 3.2 note 1: like supplies tied together); all banks LVCMOS33. Sheet 5: ramp 0.01-100 V/ms\n"
             "(Table 3.3); regulator within 3% (FPGA-TN-02154 section 2.2).\n"
             f"NC pins {', '.join(map(str, nc))} not connected (pinout file). On the LCMXO2-4000HC fallback, pins\n"
             f"{', '.join(map(str, nc_io4))} are I/O pads (MachXO2-4000 pinout): unconnected here, so no change is needed.",
             (ux - 30.48, uy + 35.56), 1.27)

    # ---------------- decoupling (Hardware Checklist Table 3.1)
    sch.text("DECOUPLING (Lattice FPGA-TN-02154 Table 3.1): VCC 2 x 10 uF + 100 nF per pin (4 pins);\n"
             "VCCIO 10 uF per bank + 100 nF per pin (12 pins, 6 banks). 100 nF at each pin on the PCB.",
             (304.8, 30.48), 1.27)
    caps = [(f"C{201 + i}", "100n", f"VCC pin {p}") for i, p in enumerate(sorted(p for p, v in pin_tab.items() if v[0] == "VCC"))]
    vio = sorted((p for p, v in pin_tab.items() if v[0].startswith("VCCIO")), key=lambda p: (pin_tab[p][0], p))
    caps += [(f"C{205 + i}", "100n", f"{pin_tab[p][0]} pin {p}") for i, p in enumerate(vio)]
    caps += [("C217", "10u", "VCC bulk"), ("C218", "10u", "VCC bulk")]
    caps += [(f"C{219 + b}", "10u", f"VCCIO{b} bulk") for b in range(6)]
    for i, (ref, val, note) in enumerate(caps):
        x, y = 304.8 + 12.7 * (i % 12), 45.72 + 25.4 * (i // 12)
        cf = "Capacitor_SMD:C_0805_2012Metric" if val == "10u" else "Capacitor_SMD:C_0603_1608Metric"
        spec = "0805 X5R 16 V" if val == "10u" else "0603 X7R 25 V"
        c = sch.place(C, ref, val, x, y, 0, footprint=cf, props={"Spec": spec, "Note": note},
                      ref_at=(x + 2.5, y - 1.3), val_at=(x + 2.5, y + 1.3), ref_just="left", val_just="left")
        pwr(P3, *c.p("1"))
        pwr(GNDS, *c.p("2"))

    # ---------------- configuration and JTAG pulls (Hardware Checklist Table 6.1 and figures)
    sch.text("CONFIGURATION (FPGA-TN-02154 section 6, Table 6.1, Figure 6.1): PROGRAMN, INITN, DONE kept as\n"
             "configuration pins (SYSCONFIG SDM_PORT=PROGRAMN_DONE_INITN), 4.7k pull-ups to VCCIO0. JTAG port enabled.\n"
             "JTAGENB: no signal (C-19), 1k pull-up = JTAG mode, so JTAG stays available whatever the bitstream.\n"
             "TCK 4.7k pull-down; TMS, TDI, TDO 4.7k pull-ups. SN (pin 70) carries SA17, an FPGA output: 4.7k\n"
             "pull-up to VCCIO2 keeps SN high while the device is erased (\"ensure SN and PROGRAMN are not driven low\").",
             (304.8, 104.14), 1.27)
    pulls = [("R201", "4.7k", "FPGA_PROGRAMN", P3, "label"), ("R202", "4.7k", "FPGA_INITN", P3, "label"),
             ("R203", "4.7k", "FPGA_DONE", P3, "label"), ("R204", "1k", "FPGA_JTAGENB", P3, "label"),
             ("R205", "4.7k", "FPGA_TCK", GNDS, "hlabel"), ("R206", "4.7k", "FPGA_TMS", P3, "hlabel"),
             ("R207", "4.7k", "FPGA_TDI", P3, "hlabel"), ("R208", "4.7k", "SA17", P3, "hlabel"),
             ("R210", "4.7k", "FPGA_TDO", P3, "hlabel")]
    for i, (ref, val, net, rail, kind) in enumerate(pulls):
        x, y = 309.88 + 22.86 * i, 134.62
        r = sch.place(R, ref, val, x, y, 0, footprint="Resistor_SMD:R_0603_1608Metric", props={"Spec": "0603 1% 0.1 W"},
                      ref_at=(x + 1.8, y - 1.3), val_at=(x + 1.8, y + 1.3), ref_just="left", val_just="left")
        if rail is GNDS:
            pwr(GNDS, *r.p("2"))
            a = r.p("1")
            sch.wire(a, (a[0], a[1] - 5.08))
            sch.hlabel(net, "bidirectional", (a[0], a[1] - 5.08), "right")
        else:
            pwr(P3, *r.p("1"))
            b = r.p("2")
            sch.wire(b, (b[0], b[1] + 5.08))
            if kind == "hlabel":
                sch.hlabel(net, "bidirectional", (b[0], b[1] + 5.08), "right")
            else:
                sch.label(net, (b[0], b[1] + 5.08), "right")

    # ---------------- JTAG header J201 (1x6, 2.54 mm, polarized; project pin order, documented [A])
    J = std["CONN6"]
    jx, jy = 314.96, 182.88
    j = sch.place(J, "J201", "JTAG", jx, jy, 0, footprint="Connector_Molex:Molex_KK-254_AE-6410-06A_1x06_P2.54mm_Vertical",
                  props={"Spec": "1x6 2.54 mm polarized friction-lock header, Molex KK 254 family. Candidate 22-27-2061 "
                                 "(KiCad library cross-reference; TBV against the Molex drawing before BOM freeze). "
                                 "1 VREF (+3V3), 2 GND, 3 TCK, 4 TDO, 5 TDI, 6 TMS (project order [A])",
                         "Silkscreen": "Name at every pin (VREF GND TCK TDO TDI TMS), pin-1 marker, legend JTAG 3V3"},
                  ref_at=(jx, jy - 10.0), val_at=(jx, jy + 12.0))
    for pn, net in (("1", "+3V3"), ("2", "GND"), ("3", "FPGA_TCK"), ("4", "FPGA_TDO"), ("5", "FPGA_TDI"), ("6", "FPGA_TMS")):
        pt = j.p(pn)
        end = (round(pt[0] - 7.62, 4), pt[1])
        sch.wire(pt, end)
        if net == "+3V3":
            pwr(P3, end[0], end[1], 90)
        elif net == "GND":
            pwr(GNDS, end[0], end[1], 270)
        else:
            sch.hlabel(net, "bidirectional", end, "left")
    sch.text("J201 JTAG (programming, boundary scan). PROJECT PIN ORDER, not a vendor standard:\n"
             "1 VREF (+3V3)  2 GND  3 TCK  4 TDO  5 TDI  6 TMS.\n"
             "Polarized KK 254 header: the mating housing fits one way only. PCB silkscreen:\n"
             "the signal name at every pin, a pin-1 marker and \"JTAG 3V3\".\n"
             "VREF = carrier +3V3, so a programmer never powers the board. The RP2040 JTAG\n"
             "option (D-12) joins these nets on sheet 4 via a translator enabled by a DIP\n"
             "switch (sheet 6).", (330.2, 170.18), 1.27)

    # ---------------- 50 MHz oscillator
    xo = syms["ECS2520"]
    ox, oy = 457.2, 190.5
    x2 = sch.place(xo, "X201", "ECS-2520MV-500-BN-TR", ox, oy, 0, ref_at=(ox - 5.08, oy - 13.0), val_at=(ox - 5.08, oy + 14.0))
    vd = x2.p("4")
    sch.wire(vd, (vd[0], vd[1] - 5.08))
    sch.label("VDD_OSC", (vd[0], vd[1] - 5.08), "right")
    pwr(GNDS, *x2.p("2"))
    oe = x2.p("1")
    sch.wire(oe, (oe[0] - 5.08, oe[1]))
    sch.label("VDD_OSC", (oe[0] - 5.08, oe[1]), "left")
    fb = sch.place(std["FB"], "FB201", "600R@100MHz", ox - 25.4, oy - 22.86, 0, footprint="Inductor_SMD:L_0603_1608Metric",
                   props={"Spec": "0603 ferrite bead, 600 ohm at 100 MHz, >= 500 mA (FPGA-TN-02154 Figure 13.1); "
                          "MPN to be selected and verified before BOM freeze (criteria: sheet2-design-notes section 5)"},
                   ref_at=(ox - 22.4, oy - 24.2), val_at=(ox - 22.4, oy - 21.6), ref_just="left", val_just="left")
    pwr(P3, *fb.p("1"))
    f2 = fb.p("2")
    fl = (f2[0], round(f2[1] + 3.81, 4))
    sch.wire(f2, fl)
    sch.label("VDD_OSC", fl, "right")
    # VDD_OSC is sourced through a passive bead: declare it driven (permanent flag, not a sheet-5 placeholder)
    sch.place(std["FLAG"], "#FLG2001", "PWR_FLAG", fl[0], fl[1], 180, ref_at=(fl[0] - 2.5, fl[1] + 7.0),
              val_at=(fl[0] - 2.5, fl[1] + 5.2), ref_just="right", val_just="right")
    out = x2.p("3")
    r = sch.place(R, "R209", "33R", out[0] + 10.16, out[1], 90, footprint="Resistor_SMD:R_0603_1608Metric",
                  props={"Spec": "0603 1%; series termination. 33 ohm PROVISIONAL until layout and signal-integrity review"},
                  ref_at=(out[0] + 10.16, out[1] - 3.0), val_at=(out[0] + 10.16, out[1] + 3.0))
    sch.wire(out, r.p("1"))
    b = r.p("2")
    sch.wire(b, (b[0] + 7.62, b[1]))
    sch.label("CLK_50M", (b[0] + 7.62, b[1]), "right")
    for k, (ref, val, cf, spec) in enumerate((("C225", "100n", "Capacitor_SMD:C_0603_1608Metric", "0603 X7R 25 V"),
                                              ("C226", "1u", "Capacitor_SMD:C_0603_1608Metric", "0603 X7R 16 V"))):
        cx, cy = ox + 12.7 + 12.7 * k, oy - 22.86
        c = sch.place(C, ref, val, cx, cy, 0, footprint=cf, props={"Spec": spec, "Note": "X201 VDD (VDD_OSC)"},
                      ref_at=(cx + 2.5, cy - 1.3), val_at=(cx + 2.5, cy + 1.3), ref_just="left", val_just="left")
        c1 = c.p("1")
        sch.wire(c1, (c1[0], c1[1] - 3.81))
        sch.label("VDD_OSC", (c1[0], c1[1] - 3.81), "right")
        pwr(GNDS, *c.p("2"))
    sch.text("X201 50.000 MHz CMOS oscillator (ECS-2520MV-500-BN-TR: +/-50 ppm, -40 to +85 C, 8.0 mA max at 3.3 V)\n"
             "-> R209 -> PCLKT0_1 (pin 128; FPGA-TN-02154 section 13: single-ended clocks on PCLKT pins only).\n"
             "Supply filter per FPGA-TN-02154 Figure 13.1: FB201 600 ohm bead, C225 0.1 uF, C226 1 uF on VDD_OSC.\n"
             "OE (pin 1) tied to VDD_OSC: always running (>= 0.7 Vdd = active). 15 pF maximum load per the data sheet.",
             (431.8, 213.36), 1.27)

    # ---------------- test points
    for k, net in enumerate(("FPGA_PROGRAMN", "FPGA_INITN", "FPGA_DONE", "CLK_50M")):
        x, y = 309.88 + 20.32 * k, 241.3
        tp = sch.place(TP, f"TP{201 + k}", "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm", in_bom=False,
                       ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
        p_ = tp.p("1")
        sch.wire(p_, (p_[0], p_[1] + 3.81))
        sch.label(net, (p_[0], p_[1] + 3.81), "right")
    x, y = 309.88 + 20.32 * 4, 241.3
    tp = sch.place(TP, "TP205", "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm", in_bom=False,
                   ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
    pwr(GNDS, *tp.p("1"))

    sch.text(
        "DESIGN NOTES (summary; full analysis in docs/stage2/sheet2-design-notes.md)\n"
        "1. Every signal pin comes from tools/fpga/pinplan.py (also the LPF LOCATEs and docs/stage2/sheet2-pin-assignment.md).\n"
        "   Bank 1 holds the whole /SLAVEn, XRDY and buffer-enable decode group (C-01/C-02 paths).\n"
        "2. Owner decisions C-17 and C-26 (option C-17b): 101 signals; PROGRAMN/INITN/DONE and JTAG kept; JTAGENB unused (C-19);\n"
        "   3 spare (pins 23, 24, 67). Only the READY LED is on the FPGA; FAULT and the other diagnostic LEDs are on the RP2040.\n"
        "   Fallback LCMXO2-4000HC-4TG144C: every assigned pin is an I/O in the same bank, and the configuration, JTAG, SN,\n"
        "   PCLKT0_1 and I2C pins are the same package pins (checked by tools/fpga/pinplan.py against the 4000 pinout file).\n"
        "3. Post-place-and-route STA at these pins (rev A1, both grades, 15 pF): every constraint met; worst Zorro path\n"
        "   14.91 ns of 18; /SLAVEn at the slot 20.40 ns of 35; M-7 slot setup criterion >= 19.3 ns (sheet2-sta-results.md).\n"
        "4. Interfaces: sheet 1 (ZB_*, ZF_*, EN_OK, LD*), sheet 3 (SA*, SRAM_*, LD*), sheet 4 (RP_*, FPGA_TCK/TMS/TDI/TDO),\n"
        "   sheet 5 (I2C_*, INA_ALERT_N, X4_*), sheet 6 (LED_READY, DIP_*, DBG*). Sheets 4-6 are not yet drawn.\n"
        "5. Erased-device rules (FPGA-TN-02155 section 6): the I2C configuration port on pins 125/126 ACKs 7-bit\n"
        "   addresses 0x40-0x43, so no telemetry device on I2C_SDA/I2C_SCL may use them (sheet 5). SN is never driven low.\n"
        "   SDA/SCL are limited to -0.25..3.75 V (data sheet Table 3.1 note 5): I2C pull-ups to +3V3 only.\n"
        "6. Back-powering (FPGA-TN-02154 section 14): no FPGA input may be driven while +3V3 is off. Sheets 1 and 3 comply\n"
        "   (Ioff / VCC-isolated buffers, pull-ups to +3V3); sheets 4-6 must keep this rule (debug header, X4 sense lines).\n"
        "7. Erased or unconfigured FPGA: every Zorro-side output is held inactive by its sheet-1 resistor and ZF_ARM is pulled\n"
        "   low, so the card is disabled and the slot looks empty; SRAM deselected (R301/R302). Hardware check M-14.\n"
        "8. Not yet validated: an ERC-clean result does not imply electrical or timing correctness.",
        (25.4, 355.6), 1.27)
    return sch, spare
