# SPDX-License-Identifier: MIT
"""Sheet 4 (x86 SBC interconnect: RP2040 host link) for tools/kicad/gen_project.py.

J401 is the X4 GPIO ribbon header (pin map: docs/pin-assignment-matrix.md section 3, [V S1 sh.21]).
Every X4 header signal passes an SN74AVC4T774 (A port = carrier +3V3), so the X4 is never loaded or
back-fed (ER-3, R-27, C-29): VCC isolation and Ioff [V S66]. B ports: U401, U403, U404 (inputs from the
RP2040 only) on X4_3V3_REF; U402 (every FPGA -> RP2040 output) on RP_VIO, an RP2040 GPIO driven high by
firmware, so no B output can rise above the RP2040's own IOVDD, which the X4's K4 key can switch off
while the header 3.3 V stays up (Q32, [V S1 sh.21]; decision S4-6). Translator pinout
from the SCES693I application figure (PW package): 1 DIR1, 2 DIR2, 3-6 A1-A4, 7 DIR3, 8 DIR4, 9 OE,
10 GND, 11 B4, 12 B3, 13 B2, 14 B1, 15 VCCB, 16 VCCA. DIR high = A->B, low = B->A; OE high = isolated.
"""
from __future__ import annotations

from kisch import Pin, Schematic, SymbolDef      # noqa: E402

# J401 pin -> (X4 net, translator, channel)
J401_SIG = {23: ("X4_GP10_SCK", "U401", 1), 24: ("X4_GP9_CS_N", "U401", 2), 19: ("X4_GP11_MOSI", "U401", 3),
            16: ("X4_GP22_IRQ_N", "U402", 1), 18: ("X4_GP27_ATTN", "U402", 2), 21: ("X4_GP8_MISO", "U402", 3),
            38: ("X4_GP2_TDO", "U402", 4),
            37: ("X4_GP14_TCK", "U403", 1), 35: ("X4_GP15_TMS", "U403", 2), 36: ("X4_GP26_TDI", "U403", 3),
            27: ("X4_GP16_LED", "U404", 1), 28: ("X4_GP17_LED", "U404", 2),
            26: ("X4_GP18_LED", "U404", 3), 32: ("X4_GP19_LED", "U404", 4)}
J401_VIO = {22: "X4_GP24_VIO"}                            # GP24 driven high by firmware: U402's B supply (S4-6)
J401_REF = (1, 17)                                        # P3V3_S: reference only (ER-3)
J401_GND = (6, 9, 14, 20, 25, 30, 34, 39)
J401_NC = (2, 4, 3, 5, 7, 8, 10, 11, 12, 13, 15, 29, 31, 33, 40)   # 5 V pins and reserved GPIO
# translator channels: (A-side net, direction) ; "AB" = A->B (DIR high), "BA" = B->A (DIR low)
XLAT = {"U401": [("RP_SCK", "BA"), ("RP_CS_N", "BA"), ("RP_MOSI", "BA"), (None, "AB")],
        "U402": [("RP_IRQ_N", "AB"), ("RP_ATTN", "AB"), ("RP_MISO", "AB"), ("FPGA_TDO", "AB")],
        "U403": [("FPGA_TCK", "BA"), ("FPGA_TMS", "BA"), ("FPGA_TDI", "BA"), (None, "AB")],
        "U404": [("LED_RP0", "BA"), ("LED_RP1", "BA"), ("LED_RP2", "BA"), ("LED_RP3", "BA")]}
VCCB = {"U401": "X4_3V3_REF", "U402": "RP_VIO", "U403": "X4_3V3_REF", "U404": "X4_3V3_REF"}
# B outputs driving the ribbon: series source terminations
SERIES = {("U402", 1): "R412", ("U402", 2): "R413", ("U402", 3): "R411", ("U402", 4): "R414"}
# B-side 100k pull-downs: every RP2040 -> carrier input is defined while the RP2040 is unpowered or in reset
BPULL = {("U401", 1): "R418", ("U401", 2): "R419", ("U401", 3): "R420", ("U403", 1): "R421", ("U403", 2): "R422",
         ("U403", 3): "R423", ("U404", 1): "R408", ("U404", 2): "R409", ("U404", 3): "R410", ("U404", 4): "R415"}
PINS = {"A": {1: "3", 2: "4", 3: "5", 4: "6"}, "B": {1: "14", 2: "13", 3: "12", 4: "11"},
        "DIR": {1: "1", 2: "2", 3: "7", 4: "8"}}


def sym_avc4t774():
    p = [Pin("16", "VCCA", "power_in", -5.08, 20.32, 270, 5.08), Pin("15", "VCCB", "power_in", 5.08, 20.32, 270, 5.08),
         Pin("10", "GND", "power_in", 0, -22.86, 90, 5.08)]
    for ch, y in ((1, 10.16), (2, 7.62), (3, 5.08), (4, 2.54)):
        p.append(Pin(PINS["A"][ch], f"A{ch}", "bidirectional", -15.24, y, 0, 5.08))
        p.append(Pin(PINS["B"][ch], f"B{ch}", "bidirectional", 15.24, y, 180, 5.08))
    p.append(Pin("9", "~{OE}", "input", -15.24, -2.54, 0, 5.08))
    for ch, y in ((1, -7.62), (2, -10.16), (3, -12.7), (4, -15.24)):
        p.append(Pin(PINS["DIR"][ch], f"DIR{ch}", "input", -15.24, y, 0, 5.08))
    return SymbolDef("SN74AVC4T774PW", "U", "SN74AVC4T774PWR", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
                     "https://www.ti.com/lit/ds/symlink/sn74avc4t774.pdf",
                     "4-bit dual-supply bus transceiver, independent direction per channel, VCC isolation, Ioff "
                     "(TI SCES693I). DIR high = A->B, low = B->A; OE high = isolated", p,
                     rects={1: [(-10.16, 15.24, 10.16, -17.78)]},
                     extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74AVC4T774PWR"},
                     keywords="level translator dual supply ioff", ref_at=(-10.16, 23.0), value_at=(-10.16, -26.0))


def build_sheet4(root_uuid: str, sheet_uuid: str, syms, std, consts):
    REV, DATE, COMPANY, LICENCE = consts
    sch = Schematic("sheet4", "A2", "x86 SBC interconnect (RP2040 host link)", REV, DATE,
                    ["Sheet 4 of 6 (Stage 4, rev A). NOT VALIDATED: design review pending (G-SHEET4).",
                     "X4 ribbon J401; 4 x SN74AVC4T774 (SPI, IRQ/ATTN, JTAG option, RP2040 LEDs)",
                     "Protocol: docs/hdl/host-link-protocol.md; notes: sheet4-design-notes.md",
                     f"Licence: {LICENCE}"],
                    COMPANY, f"/{root_uuid}/{sheet_uuid}")
    R, C, TP, P3, GNDS, FLAG = std["R"], std["C"], std["TP"], std["+3V3"], std["GND"], std["FLAG"]
    n_pwr = [0]

    def pwr(sym, x, y, rot=0):
        n_pwr[0] += 1
        return sch.place(sym, f"#PWR{4000 + n_pwr[0]:04d}", sym.name, x, y, rot,
                         val_at=(x, y - 3.6) if sym.name != "GND" else (x, y + 5.0), hide_value=(sym.name == "GND"),
                         ref_at=(x, y + 3))

    def stub(pt, dx, dy=0.0):
        end = (round(pt[0] + dx, 4), round(pt[1] + dy, 4))
        sch.wire(pt, end)
        return end

    # ---------------- J401: X4 GPIO ribbon (2 x 20, keyed box header)
    J = std["CONN2x20"]
    jx, jy = 355.6, 127.0
    j = sch.place(J, "J401", "X4 GPIO", jx, jy, 0, footprint="Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical",
                  props={"Spec": "2x20 2.54 mm shrouded (keyed) box header; 40-way IDC ribbon <= 15 cm to the X4 (D-07)"},
                  ref_at=(jx + 1.27, jy - 27.0), val_at=(jx + 1.27, jy + 28.5))
    for pn in range(1, 41):
        pt = j.p(str(pn))
        side = -7.62 if pn % 2 else 7.62                  # odd pins on the left, even on the right
        if pn in J401_REF:
            sch.label("X4_3V3_REF", stub(pt, side), "left" if side < 0 else "right")
        elif pn in J401_GND:
            e = stub(pt, side)
            pwr(GNDS, e[0], e[1], 270 if side < 0 else 90)
        elif pn in J401_NC:
            sch.noconnect(pt)
        elif pn in J401_VIO:
            sch.label(J401_VIO[pn], stub(pt, side), "left" if side < 0 else "right")
        else:
            sch.label(J401_SIG[pn][0], stub(pt, side), "left" if side < 0 else "right")
    # X4_3V3_REF comes from the X4 through J401 (a passive pin): declare it driven
    fl = (jx - 30.48, jy - 38.1)
    sch.label("X4_3V3_REF", stub(fl, 0, 3.81), "right")
    sch.place(FLAG, "#FLG4001", "PWR_FLAG", fl[0], fl[1], 0, ref_at=(fl[0], fl[1] - 8.0), val_at=(fl[0] - 1.27, fl[1] - 3.2),
              val_just="right")
    tp = sch.place(TP, "TP405", "TestPoint", fl[0] + 10.16, fl[1], 0, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   in_bom=False, ref_at=(fl[0] + 11.8, fl[1] - 4.2), val_at=(fl[0] + 11.8, fl[1] - 2.6), hide_value=True, ref_just="left")
    sch.label("X4_3V3_REF", stub(tp.p("1"), 0, 3.81), "right")

    # ---------------- translators
    U = syms["AVC4T774"]
    pos = {"U401": (101.6, 76.2), "U402": (101.6, 190.5), "U403": (228.6, 76.2), "U404": (228.6, 190.5)}
    x4net = {(u, ch): net for _, (net, u, ch) in J401_SIG.items()}
    series = SERIES
    cnum = [401]
    for uref, (ux, uy) in pos.items():
        u = sch.place(U, uref, "SN74AVC4T774PWR", ux, uy, 0, ref_at=(ux - 10.16, uy - 23.0), val_at=(ux - 10.16, uy + 26.0))
        # supplies and decoupling (100 nF per supply pin, at the pin on the PCB)
        pwr(P3, *stub(u.p("16"), 0, -5.08))
        sch.label(VCCB[uref], stub(u.p("15"), 0, -5.08), "right")
        pwr(GNDS, *u.p("10"))
        for k, (net, rail) in enumerate((("+3V3", P3), (VCCB[uref], None))):
            cx, cy = ux + 25.4 + 10.16 * k, uy - 30.48
            c = sch.place(C, f"C{cnum[0]}", "100n", cx, cy, 0, footprint="Capacitor_SMD:C_0603_1608Metric",
                          props={"Spec": "0603 X7R 25 V", "Note": f"{uref} {'VCCA' if k == 0 else 'VCCB'}"},
                          ref_at=(cx + 2.5, cy - 1.3), val_at=(cx + 2.5, cy + 1.3), ref_just="left", val_just="left")
            cnum[0] += 1
            if rail is not None:
                pwr(rail, *c.p("1"))
            else:
                sch.label(VCCB[uref], stub(c.p("1"), 0, -3.81), "right")
            pwr(GNDS, *c.p("2"))
        # channels
        for ch, (anet, d) in enumerate(XLAT[uref], start=1):
            a, b, dr = u.p(PINS["A"][ch]), u.p(PINS["B"][ch]), u.p(PINS["DIR"][ch])
            e = stub(dr, -5.08 if ch % 2 else -12.7)            # alternate stub lengths: labels do not collide
            if d == "AB":
                pwr(P3, e[0], e[1], 90)
            else:
                pwr(GNDS, e[0], e[1], 270)
            if anet is None:                                # spare channel: A input tied low, B output open
                e = stub(a, -5.08)
                pwr(GNDS, e[0], e[1], 270)
                sch.noconnect(b)
                continue
            ea = stub(a, -10.16)
            sch.hlabel(anet, "bidirectional", ea, "left")
            if (uref, ch) in series:                        # B output driving the ribbon: series termination
                # fan the four terminated outputs out to a 5.08 mm pitch so each resistor's text has room;
                # the jogs alternate in x and no vertical crosses another channel's horizontal
                yb1 = u.p(PINS["B"][1])[1]
                yt = round(yb1 + 3.81 + (ch - 2.5) * 5.08, 4)
                xj = round(b[0] + (7.62 if ch in (1, 4) else 5.08), 4)
                sch.wire(b, (xj, b[1]))
                if yt != b[1]:
                    sch.wire((xj, b[1]), (xj, yt))
                rx = b[0] + 17.78
                r = sch.place(R, series[(uref, ch)], "33R", rx, yt, 90, footprint="Resistor_SMD:R_0603_1608Metric",
                              props={"Spec": "0603 1%; source termination for the ribbon, value TBV at layout"},
                              ref_at=(rx - 3.2, yt - 1.8), val_at=(rx + 3.0, yt - 1.8))
                sch.wire((xj, yt), r.p("1"))
                sch.label(x4net[(uref, ch)], stub(r.p("2"), 5.08), "right")
            else:
                sch.label(x4net[(uref, ch)], stub(b, 10.16), "right")
        # OE
        oe = u.p("9")
        if uref == "U403":                                  # JTAG option: DIP switch (sheet 6), default isolated
            sch.hlabel("RP_JTAG_EN_N", "input", stub(oe, -10.16), "left")
        else:
            e = stub(oe, -5.08)
            pwr(GNDS, e[0], e[1], 270)

    # ---------------- default resistors (FPGA side, R-51; idle levels when the translators isolate)
    pulls = [("R401", "10k", "RP_CS_N", P3), ("R402", "10k", "RP_SCK", GNDS), ("R403", "10k", "RP_MOSI", GNDS),
             ("R404", "10k", "RP_MISO", GNDS), ("R405", "2.2k", "RP_IRQ_N", P3), ("R406", "10k", "RP_ATTN", GNDS),
             ("R407", "10k", "RP_JTAG_EN_N", P3)]
    for i, (ref, val, net, rail) in enumerate(pulls):
        x, y = 30.48 + 15.24 * i, 266.7
        r = sch.place(R, ref, val, x, y, 0, footprint="Resistor_SMD:R_0603_1608Metric", props={"Spec": "0603 1%"},
                      ref_at=(x + 1.8, y - 1.3), val_at=(x + 1.8, y + 1.3), ref_just="left", val_just="left")
        if rail is GNDS:
            pwr(GNDS, *r.p("2"))
            sch.hlabel(net, "bidirectional", stub(r.p("1"), 0, -5.08), "right")
        else:
            pwr(P3, *r.p("1"))
            sch.hlabel(net, "bidirectional" if net != "RP_JTAG_EN_N" else "input", stub(r.p("2"), 0, 5.08), "right")
    # B-side 100k pull-downs on every RP2040 -> carrier input: defined lows while the RP2040 is unpowered
    # (K4, [V S1 sh.21]) or in reset (its pads also pull down [V S65]). LEDs: C-26
    for i, ((uref, ch), ref) in enumerate(sorted(BPULL.items(), key=lambda t: t[1])):
        x, y = (152.4 + 15.24 * i, 266.7) if i < 4 else (30.48 + 15.24 * (i - 4), 241.3)
        r = sch.place(R, ref, "100k", x, y, 0, footprint="Resistor_SMD:R_0603_1608Metric",
                      props={"Spec": "0603 1%; B-side pull-down" + (" (C-26)" if uref == "U404" else " (S4-6)")},
                      ref_at=(x + 1.8, y - 1.3), val_at=(x + 1.8, y + 1.3), ref_just="left", val_just="left")
        pwr(GNDS, *r.p("2"))
        sch.label(x4net[(uref, ch)], stub(r.p("1"), 0, -5.08), "right")
    # U402's B supply (S4-6): GP24 -> R416 -> RP_VIO, with C on the VCCB pin (above) and a 100k bleed, so
    # VCCB = 0 and U402 isolates whenever GP24 is not driven high (RP2040 unpowered, in reset or in BOOTSEL)
    x, y = 152.4 + 15.24 * 6, 241.3
    r = sch.place(R, "R416", "47R", x, y, 0, footprint="Resistor_SMD:R_0603_1608Metric",
                  props={"Spec": "0603 1%; limits the GPIO's inrush into U402's VCCB decoupling (value TBV, M-16)"},
                  ref_at=(x + 1.8, y - 1.3), val_at=(x + 1.8, y + 1.3), ref_just="left", val_just="left")
    sch.label("X4_GP24_VIO", stub(r.p("1"), 0, -5.08), "right")
    sch.label("RP_VIO", stub(r.p("2"), 0, 5.08), "right")
    x = 152.4 + 15.24 * 7
    r = sch.place(R, "R417", "100k", x, y, 0, footprint="Resistor_SMD:R_0603_1608Metric",
                  props={"Spec": "0603 1%; RP_VIO bleed: U402 isolates when GP24 floats"},
                  ref_at=(x + 1.8, y - 1.3), val_at=(x + 1.8, y + 1.3), ref_just="left", val_just="left")
    pwr(GNDS, *r.p("2"))
    sch.label("RP_VIO", stub(r.p("1"), 0, -5.08), "right")
    fl = (152.4 + 15.24 * 8 + 5.08, 236.22)                 # RP_VIO is driven through R416 (passive): declare it
    sch.label("RP_VIO", stub(fl, 0, 3.81), "right")
    sch.place(FLAG, "#FLG4002", "PWR_FLAG", fl[0], fl[1], 0, ref_at=(fl[0], fl[1] - 8.0), val_at=(fl[0] - 1.27, fl[1] - 3.2),
              val_just="right")
    tp = sch.place(TP, "TP407", "TestPoint", fl[0] + 15.24, fl[1], 0, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   in_bom=False, ref_at=(fl[0] + 16.9, fl[1] - 4.2), val_at=(fl[0] + 16.9, fl[1] - 2.6), hide_value=True,
                   ref_just="left")
    sch.label("RP_VIO", stub(tp.p("1"), 0, 3.81), "right")

    # ---------------- test points (FPGA side)
    for k, net in enumerate(("RP_SCK", "RP_MISO", "RP_CS_N", "RP_ATTN")):
        x, y = 274.32 + 15.24 * k, 266.7
        tp = sch.place(TP, f"TP{401 + k}", "TestPoint", x, y, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm", in_bom=False,
                       ref_at=(x + 1.6, y - 4.2), val_at=(x + 1.6, y - 2.6), hide_value=True, ref_just="left")
        sch.hlabel(net, "bidirectional", stub(tp.p("1"), 0, 3.81), "right")
    tp = sch.place(TP, "TP406", "TestPoint", 274.32 + 15.24 * 4, 266.7, 0, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   in_bom=False, ref_at=(337.4, 262.5), val_at=(337.4, 264.1), hide_value=True, ref_just="left")
    pwr(GNDS, *tp.p("1"))

    sch.text(
        "DESIGN NOTES (summary; full analysis in docs/stage2/sheet4-design-notes.md)\n"
        "1. Every X4 signal passes an SN74AVC4T774 (A = carrier +3V3). VCC isolation + Ioff: no back-feed when a side is off (C-29).\n"
        "   U401/U403/U404 carry RP2040 -> carrier inputs only; B = X4_3V3_REF (header 3.3 V, reference only: uA; ER-3).\n"
        "2. U402 carries EVERY carrier -> RP2040 output (IRQ_N, ATTN, MISO, TDO). Its B supply is RP_VIO = RP2040 GP24, driven\n"
        "   high by firmware (S4-6): the X4's K4 key can cut the RP2040's IOVDD while the header 3.3 V stays up (Q32,\n"
        "   [V S1 sh.21]); no B output can then exceed the RP2040's own supply, and U402 isolates when GP24 is not high.\n"
        "3. U401 SPI (mode 0, GPIO chip select); U403 JTAG option (D-12: OE from a DIP switch, default isolated, so J201\n"
        "   on sheet 2 has priority); U404 four RP2040 LEDs (C-26). B-side 100k pull-downs on every RP2040 -> carrier input.\n"
        "4. Default resistors (R-51): CS_N high, SCK/MOSI low, MISO/ATTN low (not ready), IRQ_N 2.2k pull-up, strong\n"
        "   enough against the blank FPGA's weak pull-down (305 uA max: 2.6 V). Host-link pins use PULLMODE=NONE in the LPF.\n"
        "5. R411-R414 33R source terminations on the ribbon drivers; R416 47R GP24 inrush limit (values TBV at layout, M-16).\n"
        "6. Not yet validated: an ERC-clean result does not imply electrical or timing correctness.",
        (25.4, 300.0), 1.27)
    return sch
