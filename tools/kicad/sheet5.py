# SPDX-License-Identifier: MIT
"""Sheet 5 (power regulation and protection, X4 power control) for tools/kicad/gen_project.py.

Design basis: docs/stage2/sheet5-architecture-proposal.md (rev A1; owner decisions S5-1 to S5-9) and the analyses in
tools/analysis/sheet5_power.py and sheet5_ground.py. Values marked in SEL come from sheet5_power.selections() and are
checked by tools/kicad/audit_sheet5.py.

  +12 V: J501 pin 1 -> F501 5 A T -> D501 SMBJ15A -> U501 TPS259470L (UVLO/OVLO string R502-R504, dVdt R505/C504,
         ITIMER C505, ILM R506, FLT -> X4_PWR_FLT_N) -> R501 10 mOhm Kelvin shunt (U502 INA226 at 0x44) -> C501/C507/C508,
         bleed R511 -> J502 (pin 1 GND, pin 2 12 V: the X4's J10 order [V S2])
         Fail-safe enable: Q502 holds EN/UVLO low (gate biased from +12 V by R508/R509) unless Q501 (gate X4_PWR_EN,
         pull-down R510) pulls Q502's gate low. JP501: 1-2 force off, 2-3 force on (service only).
  +5 V:  J501 pin 4 -> F502 1 A T -> D502 SMBJ13A -> U503 TPS259470L (OVLO 5.53-6.01 V) -> +5V_BUS (C513-C515)
         -> U504 TLV76733DGNR -> +3V3 (C517, C518)
  S0:    X4_3V3_REF -> R518 100k -> Q503 gate (R519 1M to GND); drain = X4_S0_SENSE with R520 to +3V3: LOW = X4 IN S0
  Ground: H501-H504, the X4 standoff pads, bonded to GND (dedicated X4 return if the X4's holes are bonded: M-21 a)

Pinouts [V]: TPS25947 RPW (SLVSFC9C Table 5-1): 1 EN/UVLO, 2 OVLO, 3 AUXOFF, 4 FLT, 5 IN, 6 OUT, 7 DVDT, 8 GND,
9 ILM, 10 ITIMER. INA226 DGS (SBOS547C Table 4-1): 1 A1, 2 A0, 3 ALERT, 4 SDA, 5 SCL, 6 VS, 7 GND, 8 VBUS, 9 IN-,
10 IN+. TLV767 DGN fixed (SLVSE84D Table 5-1): 1 OUT, 2 SNS, 3 NC, 4 GND, 5 EN, 6 GND, 7 NC, 8 IN, pad (9) GND.
"""
from __future__ import annotations

from pathlib import Path

from kisch import FP_VERSION, GEN_VERSION, Pin, Schematic, SymbolDef, U, f, q      # noqa: E402

FP_RPW = "a2000-bridgeboard:TI_RPW0010A_VQFN-HR-10_2x2mm"

# Selected values (sheet5_power.py selections(); audit_sheet5.py re-derives and compares them)
SEL = {"R506": "1.10k", "C505": "10n", "C504": "10n", "R505": "100R", "C501": "470u",
       "R502": "402k", "R503": "13k", "R504": "39.2k",
       "R512": "432k", "R513": "38.3k", "R514": "124k", "R515": "6.65k", "C512": "10n", "C511": "10n", "R516": "100R"}


def sym_tps259470():
    p = [Pin("5", "IN", "power_in", -15.24, 10.16, 0, 5.08), Pin("1", "EN/UVLO", "input", -15.24, 5.08, 0, 5.08),
         Pin("2", "OVLO", "input", -15.24, 0, 0, 5.08), Pin("7", "DVDT", "passive", -15.24, -5.08, 0, 5.08),
         Pin("6", "OUT", "power_out", 15.24, 10.16, 180, 5.08), Pin("4", "~{FLT}", "open_collector", 15.24, 5.08, 180, 5.08),
         Pin("3", "AUXOFF", "open_collector", 15.24, 0, 180, 5.08), Pin("9", "ILM", "passive", 15.24, -5.08, 180, 5.08),
         Pin("10", "ITIMER", "passive", 15.24, -10.16, 180, 5.08), Pin("8", "GND", "power_in", 0, -17.78, 90, 5.08)]
    return SymbolDef("TPS259470LRPW", "U", "TPS259470LRPWR", FP_RPW, "https://www.ti.com/lit/ds/symlink/tps25947.pdf",
                     "2.7-23 V 5.5 A eFuse, adjustable OVLO, active current limit, FLT, latch-off, true reverse blocking "
                     "(TI SLVSFC9C). RPW: 1 EN/UVLO, 2 OVLO, 3 AUXOFF, 4 FLT, 5 IN, 6 OUT, 7 DVDT, 8 GND, 9 ILM, 10 ITIMER", p,
                     rects={1: [(-10.16, 15.24, 10.16, -12.7)]},
                     extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS259470LRPWR"},
                     keywords="efuse hot swap current limit reverse blocking", ref_at=(-10.16, 17.8), value_at=(-10.16, -21.6))


def sym_ina226():
    p = [Pin("10", "IN+", "input", -15.24, 7.62, 0, 5.08), Pin("9", "IN-", "input", -15.24, 2.54, 0, 5.08),
         Pin("8", "VBUS", "input", -15.24, -2.54, 0, 5.08), Pin("1", "A1", "input", -15.24, -7.62, 0, 5.08),
         Pin("2", "A0", "input", -15.24, -12.7, 0, 5.08),
         Pin("4", "SDA", "bidirectional", 15.24, 7.62, 180, 5.08), Pin("5", "SCL", "input", 15.24, 2.54, 180, 5.08),
         Pin("3", "~{ALERT}", "open_collector", 15.24, -2.54, 180, 5.08),
         Pin("6", "VS", "power_in", 0, 17.78, 270, 5.08), Pin("7", "GND", "power_in", 0, -20.32, 90, 5.08)]
    return SymbolDef("INA226DGS", "U", "INA226AIDGSR", "Package_SO:MSOP-10_3x3mm_P0.5mm",
                     "https://www.ti.com/lit/ds/symlink/ina226.pdf",
                     "36 V current/power monitor, I2C (TI SBOS547C). DGS: 1 A1, 2 A0, 3 ALERT, 4 SDA, 5 SCL, 6 VS, 7 GND, "
                     "8 VBUS, 9 IN-, 10 IN+. IN+/IN-/VBUS -0.3..40 V independent of VS; SCL <= VS + 0.3 V", p,
                     rects={1: [(-10.16, 12.7, 10.16, -15.24)]},
                     extra_props={"Manufacturer": "Texas Instruments", "MPN": "INA226AIDGSR"},
                     keywords="current monitor power monitor i2c shunt", ref_at=(-10.16, 20.4), value_at=(-10.16, -24.0))


def sym_tlv767():
    p = [Pin("8", "IN", "power_in", -12.7, 5.08, 0, 5.08), Pin("5", "EN", "input", -12.7, 0, 0, 5.08),
         Pin("3", "NC", "no_connect", -12.7, -5.08, 0, 5.08),
         Pin("1", "OUT", "power_out", 12.7, 5.08, 180, 5.08), Pin("2", "SNS", "input", 12.7, 0, 180, 5.08),
         Pin("7", "NC", "no_connect", 12.7, -5.08, 180, 5.08),
         Pin("4", "GND", "power_in", -5.08, -15.24, 90, 5.08), Pin("6", "GND", "power_in", 0, -15.24, 90, 5.08),
         Pin("9", "EP", "passive", 5.08, -15.24, 90, 5.08)]
    return SymbolDef("TLV76733DGN", "U", "TLV76733DGNR",
                     "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm_ThermalVias",
                     "https://www.ti.com/lit/ds/symlink/tlv767.pdf",
                     "1 A 16 V LDO, fixed 3.3 V, +/-1 % over load and temperature, VIN 18 V absolute maximum (TI SLVSE84D). "
                     "DGN: 1 OUT, 2 SNS, 3 NC, 4 GND, 5 EN, 6 GND, 7 NC, 8 IN, thermal pad (9) to GND. COUT 1-220 uF", p,
                     rects={1: [(-7.62, 10.16, 7.62, -10.16)]},
                     extra_props={"Manufacturer": "Texas Instruments", "MPN": "TLV76733DGNR"},
                     keywords="ldo regulator 3.3V wide input", ref_at=(-7.62, 12.7), value_at=(-7.62, -21.6))


def write_rpw_footprint(path: Path):
    """TI RPW0010A VQFN-HR, 2 x 2 mm, from the 'EXAMPLE BOARD LAYOUT' of SLVSFC9C (drawing 4225183/A 08/2019):
    side pads 0.6 x 0.25 at x = +/-0.9, y = +/-0.225; corner pads 0.6 x 0.3 at y = +/-0.7 with 0.25 x 0.65 legs at
    x = +/-0.725 reaching the package edge (y = +/-1.2); IN (5) and OUT (6) bars 0.3 x 2.4 at x = -/+0.25. Top view,
    pin 1 top left. Non-solder-mask-defined pads (TI preferred), R0.05 corners."""
    name = path.stem
    o = [f"(footprint {q(name)}\n\t(version {FP_VERSION})\n\t(generator \"pcbnew\")\n\t(generator_version \"{GEN_VERSION}\")\n"
         f"\t(layer \"F.Cu\")\n\t(descr \"TI RPW0010A VQFN-HR 10 pins 2x2 mm (TPS25947), land pattern per SLVSFC9C "
         f"drawing 4225183/A; L-shaped corner pads as two pads each. Verify against the current TI drawing before layout.\")\n"
         f"\t(tags \"TI RPW0010A VQFN-HR TPS25947 eFuse\")"]

    def prop_(n, v, x, y, layer, hide=False):
        h = "\n\t\t(hide yes)" if hide else ""
        return (f"\t(property {q(n)} {q(v)}\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(layer {q(layer)}){h}\n"
                f"\t\t(uuid {q(U('fp/rpw/' + n))})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.5 0.5)\n\t\t\t\t(thickness 0.1)\n"
                "\t\t\t)\n\t\t)\n\t)")
    o += [prop_("Reference", "REF**", 0, -2.0, "F.SilkS"), prop_("Value", name, 0, 2.0, "F.Fab"),
          prop_("Datasheet", "https://www.ti.com/lit/ds/symlink/tps25947.pdf", 0, 0, "F.Fab", True),
          prop_("Description", "TI RPW0010A VQFN-HR 2x2 mm", 0, 0, "F.Fab", True)]
    o.append("\t(attr smd)\n\t(duplicate_pad_numbers_are_jumpers no)")

    def line(x1, y1, x2, y2, layer, key, w=0.1):
        return (f"\t(fp_line\n\t\t(start {f(x1)} {f(y1)})\n\t\t(end {f(x2)} {f(y2)})\n\t\t(stroke\n\t\t\t(width {f(w)})\n"
                f"\t\t\t(type solid)\n\t\t)\n\t\t(layer {q(layer)})\n\t\t(uuid {q(U('fp/rpw/line/' + key))})\n\t)")
    for i, (a, b, c, d) in enumerate(((-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1))):
        o.append(line(a, b, c, d, "F.Fab", f"fab{i}"))
    for i, (a, b, c, d) in enumerate(((-1.5, -1.5, 1.5, -1.5), (1.5, -1.5, 1.5, 1.5), (1.5, 1.5, -1.5, 1.5), (-1.5, 1.5, -1.5, -1.5))):
        o.append(line(a, b, c, d, "F.CrtYd", f"cy{i}", 0.05))
    o.append(line(-1.45, -1.1, -1.45, -1.45, "F.SilkS", "pin1a", 0.12))
    o.append(line(-1.45, -1.45, -1.1, -1.45, "F.SilkS", "pin1b", 0.12))
    pads = [("1", -0.9, -0.7, 0.6, 0.3), ("1", -0.725, -0.875, 0.25, 0.65), ("2", -0.9, -0.225, 0.6, 0.25),
            ("3", -0.9, 0.225, 0.6, 0.25), ("4", -0.9, 0.7, 0.6, 0.3), ("4", -0.725, 0.875, 0.25, 0.65),
            ("5", -0.25, 0, 0.3, 2.4), ("6", 0.25, 0, 0.3, 2.4),
            ("7", 0.9, 0.7, 0.6, 0.3), ("7", 0.725, 0.875, 0.25, 0.65), ("8", 0.9, 0.225, 0.6, 0.25),
            ("9", 0.9, -0.225, 0.6, 0.25), ("10", 0.9, -0.7, 0.6, 0.3), ("10", 0.725, -0.875, 0.25, 0.65)]
    for k, (n, x, y, w, h) in enumerate(pads):
        rr = 0.05 / min(w, h)
        o.append(f"\t(pad {q(n)} smd roundrect\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(h)})\n"
                 f"\t\t(layers \"F.Cu\" \"F.Mask\" \"F.Paste\")\n\t\t(roundrect_rratio {f(rr)})\n"
                 f"\t\t(uuid {q(U('fp/rpw/pad/' + str(k)))})\n\t)")
    o.append("\t(embedded_fonts no)\n)")
    path.write_text("\n".join(o) + "\n", encoding="utf-8")


def build_sheet5(root_uuid: str, sheet_uuid: str, syms, std, consts):
    REV, DATE, COMPANY, LICENCE = consts
    sch = Schematic("sheet5", "A2", "Power regulation & protection, X4 power control", REV, DATE,
                    ["Sheet 5 of 6 (Stage 5, rev A). For owner review. NOT VALIDATED. No PCB manufacture authorised.",
                     "12 V: TPS259470L eFuse + INA226 to the X4 (J502 -> J10); 5 V: TPS259470L (OVLO) -> +5V_BUS -> TLV76733 -> +3V3",
                     "Basis: docs/stage2/sheet5-architecture-proposal.md rev A1; notes: sheet5-design-notes.md",
                     f"Licence: {LICENCE}"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    R, C, TP, P3, GNDS, FLAG = std["R"], std["C"], std["TP"], std["+3V3"], std["GND"], std["FLAG"]
    CP, FUSE, ZD, RSH = std["CP"], std["FUSE"], std["ZENER"], std["RSHUNT"]
    P5 = syms["+5V_BUS"]
    QN, EF, INA, LDO = syms["BSS138"], syms["TPS259470"], syms["INA226"], syms["TLV767"]
    n_pwr = [0]
    HIER = {"X4_PWR_EN": "input", "X4_PWR_FLT_N": "output", "X4_S0_SENSE": "output", "INA_ALERT_N": "output",
            "I2C_SDA": "bidirectional", "I2C_SCL": "input", "X4_3V3_REF": "input"}

    def pwr(sym, x, y, rot=0):
        n_pwr[0] += 1
        return sch.place(sym, f"#PWR{5000 + n_pwr[0]:04d}", sym.name, x, y, rot,
                         val_at=(x, y - 3.6) if sym.name != "GND" else (x, y + 5.0), hide_value=(sym.name == "GND"),
                         ref_at=(x, y + 3))

    def stub(pt, dx, dy=0.0):
        end = (round(pt[0] + dx, 4), round(pt[1] + dy, 4))
        sch.wire(pt, end)
        return end

    def net_at(pt, net, dx, dy, side):
        """Attach a net to a pin end: power symbol, hierarchical label or local label on a stub."""
        if net == "NC":
            sch.noconnect(pt)
            return
        e = stub(pt, dx, dy)
        if net == "GND":
            rot = 0 if dy > 0 else (180 if dy < 0 else (270 if dx < 0 else 90))
            pwr(GNDS, e[0], e[1], rot)
        elif net in ("+3V3", "+5V_BUS"):
            rot = 180 if dy > 0 else (0 if dy < 0 else (90 if dx < 0 else 270))
            pwr(P3 if net == "+3V3" else P5, e[0], e[1], rot)
        elif net in HIER:
            sch.hlabel(net, HIER[net], e, side)
        else:
            sch.label(net, e, side)

    def two(sym, ref, val, x, y, top, bot, fp, spec, note=None, rot=0):
        """Vertical two-pin part, pin 1 at the top."""
        props = {"Spec": spec}
        if note:
            props["Note"] = note
        part = sch.place(sym, ref, val, x, y, rot, footprint=fp, props=props,
                         ref_at=(x + 2.5, y - 1.3), val_at=(x + 2.5, y + 1.3), ref_just="left", val_just="left")
        p1, p2 = (part.p("1"), part.p("2"))
        net_at(p1, top, 0, -3.81, "right")
        net_at(p2, bot, 0, 3.81, "right")
        return part

    def ic_pins(part, nets, stub_len=5.08):
        for pn, net in nets.items():
            pt = part.p(pn)
            cx = part.x
            if abs(pt[1] - part.y) > 15 and abs(pt[0] - cx) < 7.7:      # top/bottom pins
                net_at(pt, net, 0, stub_len if pt[1] > part.y else -stub_len, "right")
            elif pt[0] < cx:
                net_at(pt, net, -stub_len, 0, "left")
            else:
                net_at(pt, net, stub_len, 0, "right")

    R0603, R0805, C0603, C0805, C1206 = ("Resistor_SMD:R_0603_1608Metric", "Resistor_SMD:R_0805_2012Metric",
                                         "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric",
                                         "Capacitor_SMD:C_1206_3216Metric")

    # ================================================================ 12 V input (J501) and protection
    J4 = std["CONN4"]
    jx, jy = 50.8, 63.5
    j = sch.place(J4, "J501", "PERIPH_PWR_4P", jx, jy, 0,
                  footprint="Connector_TE-Connectivity:TE_MATE-N-LOK_350211-1_1x04_P5.08mm_Vertical",
                  props={"Spec": "4-pin peripheral (5.25-inch drive) power header, 5.08 mm, MATE-N-LOK 350211-1 class: "
                                 "1 +12 V, 2 GND, 3 GND, 4 +5 V [K, TBV against the A2000 harness]; >= 6 A per contact "
                                 "(requirement, ground-return model); MPN TBV"},
                  ref_at=(jx + 1.27, jy - 6.0), val_at=(jx + 1.27, jy + 10.0))
    net_at(j.p("1"), "+12V_IN", -7.62, 0, "left")
    sch.wire(j.p("2"), j.p("3"))                                   # both drive-lead grounds
    net_at(j.p("3"), "GND", -7.62, 0, "left")
    net_at(j.p("4"), "+5V_IN", -15.24, 0, "left")
    two(FUSE, "F501", "5A T", 76.2, 63.5, "+12V_IN", "+12V_F", "Fuse:Fuse_Littelfuse-NANO2-451_453",
        "5 A time-lag, 2410 (Littelfuse NANO2 454 class [K]); must carry ILIM_max 3.36 A (75 % loading, 90 % temperature "
        "derating); opens if U501 fails short. MPN TBV")
    zd = sch.place(ZD, "D501", "SMBJ15A", 91.44, 63.5, 270, footprint="Diode_SMD:D_SMB",
                   props={"Spec": "600 W TVS, VRWM 15 V > OVLO_max 14.57 V, VBR >= 16.7 V, VC <= 24.4 V (< 28 V U501 IN, "
                                  "< 40 V INA226) [K, TBV]"},
                   ref_at=(94.0, 62.2), val_at=(94.0, 64.8), ref_just="left", val_just="left")
    net_at(zd.p("1"), "+12V_F", 0, -3.81, "right")
    net_at(zd.p("2"), "GND", 0, 3.81, "right")
    two(C, "C502", "1u", 111.76, 63.5, "+12V_F", "GND", C1206, "1206 X7R 50 V; keeps the hot-plug input slew near "
        "20 V/us (U501 abs max 100 V/us)", "U501 IN")
    two(C, "C503", "100n", 121.92, 63.5, "+12V_F", "GND", C0603, "0603 X7R 50 V", "U501 IN")
    fx, fy = 60.96, 40.64
    sch.place(FLAG, "#FLG5001", "PWR_FLAG", fx, fy, 0, ref_at=(fx, fy - 8.0), val_at=(fx - 1.27, fy - 3.2), val_just="right")
    sch.label("+12V_F", stub((fx, fy), 0, 3.81), "right")

    # ================================================================ U501 eFuse (X4 12 V)
    ux, uy = 165.1, 66.04
    u1 = sch.place(EF, "U501", "TPS259470LRPWR", ux, uy, 0,
                   props={"Spec": "S5-1: X4 12 V eFuse, latch-off. ILIM 2.65-3.36 A (R506), UVLO 10.02-10.93 V / OVLO "
                                  "13.33-14.57 V (R502-R504), tITIMER 4.9-15.3 ms (C505), soft start 35-181 ms (C504)"},
                   ref_at=(ux - 10.16, uy - 17.8), val_at=(ux - 10.16, uy + 21.6))
    ic_pins(u1, {"5": "+12V_F", "1": "X4_EN_UVLO", "2": "X4_OVLO", "7": "X4_DVDT", "6": "X4_12V_EF",
                 "4": "X4_PWR_FLT_N", "3": "NC", "9": "X4_ILM", "10": "X4_ITIMER", "8": "GND"})
    # shunt (Kelvin) and INA226
    sx, sy = 223.52, 63.5
    sh = sch.place(RSH, "R501", "10m", sx, sy, 0, footprint="Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm",
                   props={"Spec": "10 mOhm 1 % 1 W 2512 4-terminal (Kelvin): 1/4 current, 2/3 sense; 0.12 W at 3.36 A. "
                                  "INA226: 25 mV at 2.5 A, full scale 8.19 A (S5-4)"},
                   ref_at=(sx - 6.0, sy - 1.3), val_at=(sx - 6.0, sy + 1.3), ref_just="right", val_just="right")
    net_at(sh.p("1"), "X4_12V_EF", 0, -3.81, "right")
    net_at(sh.p("4"), "X4_12V", 0, 3.81, "right")
    net_at(sh.p("2"), "X4_SH_P", 7.62, 0, "right")
    net_at(sh.p("3"), "X4_SH_N", 7.62, 0, "right")
    ix, iy = 279.4, 66.04
    ina = sch.place(INA, "U502", "INA226AIDGSR", ix, iy, 0,
                    props={"Spec": "S5-4: I2C address 0x44 (A1 = VS, A0 = GND [V SBOS547C Table 6-2]); never 0x40-0x43 "
                                   "(C-28). VS = +3V3; SDA/SCL/ALERT pull-ups to +3V3 only (C-29, SCL <= VS + 0.3 V)"},
                    ref_at=(ix - 10.16, iy - 20.4), val_at=(ix - 10.16, iy + 24.0))
    ic_pins(ina, {"10": "X4_SH_P", "9": "X4_SH_N", "8": "X4_12V", "1": "+3V3", "2": "GND",
                  "4": "I2C_SDA", "5": "I2C_SCL", "3": "INA_ALERT_N", "6": "+3V3", "7": "GND"})
    two(C, "C506", "100n", 302.26, 50.8, "+3V3", "GND", C0603, "0603 X7R 25 V", "U502 VS")
    # X4 side bulk, bleed, J502
    two(CP, "C501", SEL["C501"], 322.58, 63.5, "X4_12V", "GND", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
        "470 uF 25 V low-ESR aluminium (polymer preferred), -20/+20 %: start-up grid optimum with CdVdt 10 nF "
        "(sheet5_power.py section 3; supports the X4's internal-rail inrush, case E)")
    two(C, "C507", "1u", 335.28, 63.5, "X4_12V", "GND", C1206, "1206 X7R 25 V")
    two(C, "C508", "100n", 345.44, 63.5, "X4_12V", "GND", C0603, "0603 X7R 25 V")
    two(R, "R511", "4.7k", 355.6, 63.5, "X4_12V", "GND", R0805, "0805 1 %, 0.25 W (34 mW at 12.6 V): X4-side bleed, "
        "tau ~3.4 s with C501 + X4 (S5-9 decay before the external-source check, PM-2)")
    J2 = std["CONN2"]
    kx, ky = 386.08, 63.5
    k = sch.place(J2, "J502", "X4_PWR", kx, ky, 0,
                  footprint="Connector_Molex:Molex_Micro-Fit_3.0_43650-0215_1x02_P3.00mm_Vertical",
                  props={"Spec": "X4 power lead to J10: pin 1 GND, pin 2 +12 V (same order as the X4's J10 [V S2]); latching, "
                                 ">= 4 A and <= 20 mOhm per contact (requirement); lead 22 AWG twisted pair <= 15 cm, "
                                 "2.54 mm latching housing at J10 (S5-8). MPN TBV"},
                  ref_at=(kx + 1.27, ky - 6.0), val_at=(kx + 1.27, ky + 6.0))
    net_at(k.p("1"), "GND", -7.62, 0, "left")
    net_at(k.p("2"), "X4_12V", -7.62, 0, "left")

    # ================================================================ U501 support and the fail-safe enable stage
    row = [("R502", SEL["R502"], "+12V_F", "X4_EN_UVLO", R0603, "0603 1 %: UVLO/OVLO string top (>= 350k, TI ROC note 2)"),
           ("R503", SEL["R503"], "X4_EN_UVLO", "X4_OVLO", R0603, "0603 1 %: string middle"),
           ("R504", SEL["R504"], "X4_OVLO", "GND", R0603, "0603 1 %: string bottom"),
           ("R505", SEL["R505"], "X4_DVDT", "X4_DVDT_C", R0603, "0603: series resistor for CdVdt >= 10 nF (TI 7.3.5.1)"),
           ("C504", SEL["C504"], "X4_DVDT_C", "GND", C0603, "0603 C0G 50 V +/-5 %: soft start SR 0.07-0.36 V/ms"),
           ("C505", SEL["C505"], "X4_ITIMER", "GND", C0603, "0603 C0G 50 V +/-5 %: tITIMER 4.9-15.3 ms"),
           ("R506", SEL["R506"], "X4_ILM", "GND", R0603, "0603 1 % 100 ppm/K: ILIM 2.65-3.36 A (S5-2)"),
           ("R507", "10k", "+3V3", "X4_PWR_FLT_N", R0603, "0603 1 %: FLT pull-up to +3V3 only (C-29)"),
           ("R508", "100k", "+12V_F", "X4_EN_INH", R0603, "0603 1 %: Q502 gate bias from +12 V (fail-safe off)"),
           ("R509", "47k", "X4_EN_INH", "GND", R0603, "0603 1 %: Q502 VGS 4.0 V at 12.6 V, > 1.5 V above VIN 4.7 V"),
           ("R510", "10k", "X4_PWR_EN", "GND", R0603, "0603 1 %: X4_PWR_EN default low = X4 off (R-51; erased FPGA)")]
    for i, (ref, val, top, bot, fp, spec) in enumerate(row):
        sym = C if ref.startswith("C") else R
        two(sym, ref, val, 30.48 + 15.24 * i, 132.08, top, bot, fp, spec)
    qx = 228.6
    for k_, (ref, gate, drain, why) in enumerate((("Q502", "X4_EN_INH", "X4_EN_UVLO", "holds U501 EN/UVLO < 0.45 V unless released"),
                                                  ("Q501", "X4_PWR_EN", "X4_EN_INH", "FPGA X4_PWR_EN high releases Q502"))):
        x = qx + 50.8 * k_
        qq = sch.place(QN, ref, "BSS138", x, 132.08, 0, footprint="Package_TO_SOT_SMD:SOT-23",
                       props={"Spec": f"BSS138-7-F (Diodes); {why}"},
                       ref_at=(x + 5.08, 129.54), val_at=(x + 5.08, 134.62), ref_just="left", val_just="left")
        net_at(qq.p("1"), gate, -10.16, 0, "left")
        net_at(qq.p("3"), drain, 0, -3.81, "right")
        net_at(qq.p("2"), "GND", 0, 3.81, "right")
    J3 = std["CONN3"]
    px_, py_ = 330.2, 132.08
    jp = sch.place(J3, "JP501", "SERVICE", px_, py_, 0, footprint="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                   props={"Spec": "X4 power service override (S5-3, R-57): shunt 1-2 = FORCE OFF (EN/UVLO to GND); 2-3 = FORCE ON "
                                  "(Q502 gate to GND: bypasses the FPGA power manager; bench only, current-limited supply, "
                                  "nothing on the X4 USB-C); no shunt / parked on one pin = FPGA control (default)"},
                   ref_at=(px_ + 1.27, py_ - 6.0), val_at=(px_ + 1.27, py_ + 6.0))
    net_at(jp.p("1"), "X4_EN_UVLO", -7.62, 0, "left")
    net_at(jp.p("2"), "GND", -7.62, 0, "left")
    net_at(jp.p("3"), "X4_EN_INH", -7.62, 0, "left")

    # ================================================================ I2C and ALERT pull-ups (+3V3 only, C-29)
    for i, (ref, val, net) in enumerate((("R521", "4.7k", "I2C_SDA"), ("R522", "4.7k", "I2C_SCL"), ("R523", "10k", "INA_ALERT_N"))):
        two(R, ref, val, 355.6 + 15.24 * i, 132.08, "+3V3", net, R0603, "0603 1 %: pull-up to +3V3 only (C-28/C-29; "
            "SCL <= VS + 0.3 V)")

    # ================================================================ 5 V input, U503 eFuse, +5V_BUS
    y5 = 218.44
    two(FUSE, "F502", "1A T", 76.2, y5, "+5V_IN", "+5V_F", "Fuse:Fuse_Littelfuse-NANO2-451_453",
        "1 A time-lag, 2410 (NANO2 454 class [K]); carries U503 ILIM_max 0.59 A. MPN TBV")
    zd2 = sch.place(ZD, "D502", "SMBJ13A", 91.44, y5, 270, footprint="Diode_SMD:D_SMB",
                    props={"Spec": "600 W TVS, VRWM 13 V (a 12.6 V miswire does not conduct), VC <= 21.5 V: keeps U503 "
                                   "EN/UVLO <= 5.88 V (< 6.5 V abs max) and IN < 28 V [K, TBV]"},
                    ref_at=(94.0, y5 - 1.3), val_at=(94.0, y5 + 1.3), ref_just="left", val_just="left")
    net_at(zd2.p("1"), "+5V_F", 0, -3.81, "right")
    net_at(zd2.p("2"), "GND", 0, 3.81, "right")
    two(C, "C509", "1u", 111.76, y5, "+5V_F", "GND", C1206, "1206 X7R 25 V", "U503 IN")
    two(C, "C510", "100n", 121.92, y5, "+5V_F", "GND", C0603, "0603 X7R 25 V", "U503 IN")
    fx, fy = 60.96, 195.58
    sch.place(FLAG, "#FLG5002", "PWR_FLAG", fx, fy, 0, ref_at=(fx, fy - 8.0), val_at=(fx - 1.27, fy - 3.2), val_just="right")
    sch.label("+5V_F", stub((fx, fy), 0, 3.81), "right")
    ux5, uy5 = 165.1, 220.98
    u3 = sch.place(EF, "U503", "TPS259470LRPWR", ux5, uy5, 0,
                   props={"Spec": "S5-6 (A1): 5 V eFuse with OVLO DISCONNECT 5.53-6.01 V (not the 472x clamp), UVLO "
                                  "4.23-4.58 V, ILIM 0.42-0.58 A (R515), fast trip ~2 x ILIM; latch-off on TSD"},
                   ref_at=(ux5 - 10.16, uy5 - 17.8), val_at=(ux5 - 10.16, uy5 + 21.6))
    ic_pins(u3, {"5": "+5V_F", "1": "X5_EN_UVLO", "2": "X5_OVLO", "7": "X5_DVDT", "6": "+5V_BUS",
                 "4": "X5_FLT_N", "3": "NC", "9": "X5_ILM", "10": "X5_ITIMER", "8": "GND"})
    row5 = [("R512", SEL["R512"], "+5V_F", "X5_EN_UVLO", R0603, "0603 1 %: string top (>= 350k)"),
            ("R513", SEL["R513"], "X5_EN_UVLO", "X5_OVLO", R0603, "0603 1 %: string middle"),
            ("R514", SEL["R514"], "X5_OVLO", "GND", R0603, "0603 1 %: string bottom"),
            ("R516", SEL["R516"], "X5_DVDT", "X5_DVDT_C", R0603, "0603: series resistor for CdVdt >= 10 nF"),
            ("C511", SEL["C511"], "X5_DVDT_C", "GND", C0603, "0603 C0G 50 V: +5V_BUS rise 13-72 ms"),
            ("C512", SEL["C512"], "X5_ITIMER", "GND", C0603, "0603 C0G 50 V: tITIMER 4.9-15.3 ms"),
            ("R515", SEL["R515"], "X5_ILM", "GND", R0603, "0603 1 %: ILIM 0.42-0.58 A (tested point)"),
            ("R517", "10k", "+3V3", "X5_FLT_N", R0603, "0603 1 %: FLT pull-up (test point only; no FPGA pin)")]
    for i, (ref, val, top, bot, fp, spec) in enumerate(row5):
        sym = C if ref.startswith("C") else R
        two(sym, ref, val, 30.48 + 15.24 * i, 284.48, top, bot, fp, spec)
    bulk = [("C513", "220u", CP, "Capacitor_SMD:CP_Elec_8x10", "220 uF 16 V aluminium: bounds the fast-overvoltage overshoot "
             "to <= 0.44 V (sheet5_power.py section 7) and supports +5V_BUS"),
            ("C514", "10u", C, C0805, "0805 X5R 16 V"), ("C515", "100n", C, C0603, "0603 X7R 25 V")]
    for i, (ref, val, sym, fp, spec) in enumerate(bulk):
        two(sym, ref, val, 205.74 + 12.7 * i, y5, "+5V_BUS", "GND", fp, spec, "+5V_BUS")

    # ================================================================ U504 TLV76733 (+3V3)
    lx, ly = 274.32, 220.98
    ld = sch.place(LDO, "U504", "TLV76733DGNR", lx, ly, 0,
                   props={"Spec": "S5-6/S5-7 (A1): 16 V operating, 18 V absolute maximum, +/-1 %; 0.67 W worst (0.25 A from "
                                  "5.97 V), TJ <= 101 C at 60 C ambient [E]; thermal pad to GND pour, >= 4 vias. Total +3V3 "
                                  "capacitance <= 200 uF (COUT 1-220 uF)"},
                   ref_at=(lx - 7.62, ly - 12.7), val_at=(lx + 10.16, ly + 15.24), val_just="left")
    ic_pins(ld, {"8": "+5V_BUS", "5": "+5V_BUS", "3": "NC", "1": "+3V3", "2": "+3V3", "7": "NC",
                 "4": "GND", "6": "GND", "9": "GND"})
    two(C, "C516", "1u", 251.46, y5 - 22.86, "+5V_BUS", "GND", C0805, "0805 X7R 25 V", "U504 IN")
    two(C, "C517", "10u", 302.26, y5, "+3V3", "GND", C0805, "0805 X5R 10 V", "U504 OUT")
    two(C, "C518", "100n", 314.96, y5, "+3V3", "GND", C0603, "0603 X7R 25 V", "U504 OUT")

    # ================================================================ X4_S0_SENSE (S5-5: active low)
    s0 = [("R518", "100k", "X4_3V3_REF", "X4_S0_GATE", "0603 1 %: gate series from the X4's S0-only 3.3 V (ER-3: <= 3.3 uA)"),
          ("R519", "1M", "X4_S0_GATE", "GND", "0603 1 %: gate pull-down (X4 off or ribbon unplugged = not S0)"),
          ("R520", "10k", "+3V3", "X4_S0_SENSE", "0603 1 %: pull-up to +3V3 only (C-29)")]
    for i, (ref, val, top, bot, spec) in enumerate(s0):
        two(R, ref, val, 182.88 + 15.24 * i, 284.48, top, bot, R0603, spec)
    qx3 = 182.88 + 15.24 * 3 + 22.86
    q3 = sch.place(QN, "Q503", "BSS138", qx3, 284.48, 0, footprint="Package_TO_SOT_SMD:SOT-23",
                   props={"Spec": "BSS138-7-F: X4_S0_SENSE LOW = X4 in S0 (inverted, active low, S5-5); gate-only domain crossing"},
                   ref_at=(qx3 + 5.08, 281.94), val_at=(qx3 + 5.08, 287.02), ref_just="left", val_just="left")
    net_at(q3.p("1"), "X4_S0_GATE", -7.62, 0, "left")
    net_at(q3.p("3"), "X4_S0_SENSE", 0, -3.81, "right")
    net_at(q3.p("2"), "GND", 0, 3.81, "right")

    # ================================================================ X4 standoff pads (ground return, S5-8)
    MH = std["MH"]
    for i in range(4):
        x = 304.8 + 15.24 * i
        h = sch.place(MH, f"H{501 + i}", "M2.5_GND", x, 279.4, 0, footprint="MountingHole:MountingHole_2.7mm_M2.5_Pad_Via",
                      props={"Spec": "X4 standoff pad bonded to GND (S5-8): dedicated X4 return if the X4's hole is bonded to its "
                                     "ground (TBV, M-21 a); joint <= 5 mOhm (plated pad, serrated washer or SEMS screw)"},
                      ref_at=(x + 2.54, 276.86), val_at=(x + 2.54, 279.4), ref_just="left", val_just="left")
        net_at(h.p("1"), "GND", 0, 2.54, "right")

    # ================================================================ test points
    tps = [("TP501", "+12V_F"), ("TP502", "X4_12V"), ("TP503", "X4_EN_UVLO"), ("TP504", "+5V_BUS"), ("TP505", "+3V3"),
           ("TP506", "X5_FLT_N"), ("TP507", "X4_S0_SENSE"), ("TP508", "GND")]
    for i, (ref, net) in enumerate(tps):
        x, y = 406.4 + 15.24 * i, 132.08
        tp = sch.place(TP, ref, "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm", in_bom=False,
                       ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
        net_at(tp.p("1"), net, 0, 3.81, "right")

    sch.text(
        "DESIGN NOTES (summary; analysis in docs/stage2/sheet5-architecture-proposal.md rev A1 and sheet5-design-notes.md)\n"
        "1. X4 12 V (S5-1/S5-2): U501 TPS259470L. ILIM 2.65-3.36 A; blanking 4.9-15.3 ms; FLT -> X4_PWR_FLT_N -> FPGA switches off (PM-4).\n"
        "   FPGA sustained-overload trip 2.75 A / 2 s from the INA226 (PM-5). F501 opens only if U501 fails short.\n"
        "2. FAIL-SAFE ENABLE (S5-3/S5-9): Q502 holds EN/UVLO low from +12 V; only X4_PWR_EN high (Q501) releases it. Erased, configuring,\n"
        "   reset or unpowered FPGA -> X4 OFF. The FPGA checks for an external source on the X4's USB-C (INA226 VBUS) before enabling (PM-2).\n"
        "3. JP501 SERVICE OVERRIDE: 1-2 force OFF; 2-3 force ON bypasses the power manager (bench only, current-limited, X4 USB-C empty; R-57).\n"
        "4. 5 V (S5-6): U503 TPS259470L OVLO disconnect 5.53-6.01 V; C513 bounds fast overshoot; U504 TLV76733 survives 18 V.\n"
        "5. X4_S0_SENSE is ACTIVE LOW: low = X4 in S0 (S5-5). INA226 at 0x44 (C-28). Every pull-up is on +3V3 (C-29).\n"
        "6. GROUND RETURN (S5-8, conditional): H501-H504 bond the X4 standoffs to GND; J502 pin order = X4 J10 (1 GND, 2 +12 V).\n"
        "   Zorro power pins stay unconnected. Contact ratings are requirements (R-56). Bench validation B0-B5 before any A2000.\n"
        "7. Not yet validated: an ERC-clean result does not imply electrical correctness. No PCB manufacture authorised.",
        (25.4, 330.2), 1.27)
    return sch
