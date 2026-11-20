# SPDX-License-Identifier: MIT
"""Audit sheet-4 connectivity (RP2040 host link) in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet4.py <netlist.net>

Expected connections come from: the X4 header map (docs/pin-assignment-matrix.md section 3, [V S1 sh.21]),
the SN74AVC4T774 pinout and function table (TI SCES693I [V S66]: DIR high = A->B, low = B->A; OE high =
isolated), the TLV3201 pinout (TI SBOS561C: DBV 1 OUT, 2 GND, 3 IN+, 4 IN-, 5 VCC), the BSS138 pinout (SOT-23:
1 G, 2 S, 3 D), the SN74AUP1G17 pinout (TI SCES579J: DBV 1 NC, 2 A, 3 GND, 4 Y, 5 VCC), the host-link
protocol idle levels and R-51 (docs/hdl/host-link-protocol.md sections 2, 11), ER-3 (the X4's header 3.3 V is a
reference: only microamp loads on it) and decision S4-6 rev A3 (docs/stage2/sheet4-s46-isolation.md): every
carrier -> RP2040 output on U402, whose /OE is driven by buffer U406 from the open-drain node RP_EN_OD, which is
pulled low only through Q401 (gate: comparator U405, GP24 above 0.940 x X4_3V3_REF) and Q402 (gate: GP24) in
series; only MOSFET gates link the X4-side enable nets to the carrier's enable nodes; nothing on the carrier sources current into
GP24 (R424 removed); a B-side pull-down on every RP2040 -> carrier input; ATTN defined at the RP2040 while U402
is isolated (IRQ_N by the RP2040's own pull-up, firmware FW-6). Every check prints FAIL on failure; exit code 1 on any failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "fpga"))
import netlist                                   # noqa: E402
import pinplan                                   # noqa: E402
from sheet4 import (BPULL, EN_REF_RATIO, J401_EN, J401_GND, J401_NC, J401_REF, J401_SIG, OE, PINS,  # noqa: E402
                    SERIES, VCCB, XLAT)

fails = checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


def main(path):
    comps, raw = netlist.load(Path(path))
    nets = {(n.rsplit("/", 1)[-1] if n.startswith("/") else n): v for n, v in raw.items()}
    pin_net = {(r, p): n for n, v in nets.items() for r, p, _ in v}

    def net_of(r, p):
        return pin_net.get((r, str(p)))

    def members(n):
        return sorted((r, p) for r, p, _ in nets.get(n, []))

    def refs(n):
        return sorted(r for r, _, _ in nets.get(n, []))

    def unconnected(r, p):
        n = net_of(r, p)
        return n is None or n.startswith("unconnected-") or len(nets.get(n, [])) == 1

    def two_pin(ref, value, a, b):
        c = comps.get(ref)
        check(c is not None and c["value"] == value, f"{ref} value {c and c['value']} (want {value})")
        check({net_of(ref, "1"), net_of(ref, "2")} == {a, b}, f"{ref} between {a} and {b}: {net_of(ref, '1')}, {net_of(ref, '2')}")

    # ---------------- J401
    j = comps.get("J401")
    check(j is not None and j["footprint"] == "Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical", "J401 keyed 2x20 box header")
    for pn in range(1, 41):
        if pn in J401_REF:
            check(net_of("J401", pn) == "X4_3V3_REF", f"J401.{pn} X4_3V3_REF")
        elif pn in J401_GND:
            check(net_of("J401", pn) == "GND", f"J401.{pn} GND")
        elif pn in J401_NC:
            check(unconnected("J401", pn), f"J401.{pn} not connected (5 V or reserved), got {net_of('J401', pn)}")
        elif pn in J401_EN:
            check(net_of("J401", pn) == J401_EN[pn], f"J401.{pn} on {J401_EN[pn]}, got {net_of('J401', pn)}")
        else:
            check(net_of("J401", pn) == J401_SIG[pn][0], f"J401.{pn} on {J401_SIG[pn][0]}, got {net_of('J401', pn)}")
    check(sorted(set(J401_REF) | set(J401_GND) | set(J401_NC) | set(J401_SIG) | set(J401_EN)) == list(range(1, 41)),
          "J401 every pin classified")

    # ---------------- translators: supplies, OE, DIR per channel, A and B nets
    x4net = {(u, ch): net for _, (net, u, ch) in J401_SIG.items()}
    for u, chans in XLAT.items():
        c = comps.get(u)
        check(c is not None and c["value"] == "SN74AVC4T774PWR" and c["footprint"] == "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
              f"{u} SN74AVC4T774PWR, TSSOP-16")
        check(net_of(u, 16) == "+3V3" and net_of(u, 15) == VCCB[u] == "X4_3V3_REF" and net_of(u, 10) == "GND",
              f"{u} VCCA +3V3, VCCB X4_3V3_REF, GND: {net_of(u, 16)}, {net_of(u, 15)}, {net_of(u, 10)}")
        check(net_of(u, 9) == OE[u], f"{u} OE on {OE[u]}, got {net_of(u, 9)}")
        for ch, (anet, d) in enumerate(chans, start=1):
            check(net_of(u, PINS["DIR"][ch]) == ("+3V3" if d == "AB" else "GND"), f"{u} DIR{ch} = {d}")
            a, b = PINS["A"][ch], PINS["B"][ch]
            if anet is None:
                check(net_of(u, a) == "GND" and unconnected(u, b), f"{u} spare channel {ch}: A low, B open")
                continue
            check(net_of(u, a) == anet, f"{u} A{ch} on {anet}, got {net_of(u, a)}")
            if (u, ch) in SERIES:
                r = SERIES[(u, ch)]
                two_pin(r, "33R", net_of(u, b), x4net[(u, ch)])
                check(members(net_of(u, b)) == sorted([(u, b), (r, "1")]), f"{u} B{ch} only through {r}")
            else:
                check(net_of(u, b) == x4net[(u, ch)], f"{u} B{ch} on {x4net[(u, ch)]}, got {net_of(u, b)}")

    # ---------------- S4-6: every carrier -> RP2040 output on U402; a B-side pull-down on every RP2040 -> carrier input
    for u, chans in XLAT.items():
        outs = [n for n, d in chans if n is not None and d == "AB"]
        if u == "U402":
            check(sorted(outs) == ["FPGA_TDO", "RP_ATTN", "RP_IRQ_N", "RP_MISO"], f"U402 carries every output: {outs}")
        else:
            check(not outs, f"{u} drives no RP2040 pin: {outs}")
    ins = sorted((u, ch) for u, chans in XLAT.items() for ch, (n, d) in enumerate(chans, start=1) if n and d == "BA")
    check(sorted(BPULL) == ins, f"a B-side pull-down on every RP2040 -> carrier input: {sorted(BPULL)} vs {ins}")
    for (u, ch), ref in BPULL.items():
        two_pin(ref, "100k", x4net[(u, ch)], "GND")
        check(members(x4net[(u, ch)]) == sorted([("J401", str(next(p for p, v in J401_SIG.items() if v[1:] == (u, ch)))),
                                                 (u, PINS["B"][ch]), (ref, "1")]),
              f"{x4net[(u, ch)]} members {members(x4net[(u, ch)])}")

    # ---------------- S4-6 rev A3: U402's /OE from buffer U406, whose input is pulled low only through Q401 (U405)
    # and Q402 (GP24) in series
    c5 = comps.get("U405")
    check(c5 is not None and c5["value"] == "TLV3201AIDBVR" and c5["footprint"] == "Package_TO_SOT_SMD:SOT-23-5",
          "U405 TLV3201AIDBVR, SOT-23-5")
    for pin, net in (("5", "X4_3V3_REF"), ("2", "GND"), ("3", "RP_EN_SENSE"), ("4", "RP_EN_REF"), ("1", "RP_EN_CMP")):
        check(net_of("U405", pin) == net, f"U405.{pin} on {net}, got {net_of('U405', pin)}")
    for q, g, d, s_ in (("Q401", "RP_EN_CMP", "RP_EN_OD", "RP_EN_MID"), ("Q402", "RP_EN_GATE", "RP_EN_MID", "GND")):
        c = comps.get(q)
        check(c is not None and c["value"] == "BSS138" and c["footprint"] == "Package_TO_SOT_SMD:SOT-23",
              f"{q} BSS138, SOT-23")
        check((net_of(q, "1"), net_of(q, "3"), net_of(q, "2")) == (g, d, s_),
              f"{q} G/D/S on {g}/{d}/{s_}: {net_of(q, '1')}/{net_of(q, '3')}/{net_of(q, '2')}")
    c6 = comps.get("U406")
    check(c6 is not None and c6["value"] == "SN74AUP1G17DBVR" and c6["footprint"] == "Package_TO_SOT_SMD:SOT-23-5",
          "U406 SN74AUP1G17DBVR, SOT-23-5")
    for pin, net in (("5", "+3V3"), ("3", "GND"), ("2", "RP_EN_OD"), ("4", "RP_EN_N")):
        check(net_of("U406", pin) == net, f"U406.{pin} on {net}, got {net_of('U406', pin)}")
    check(unconnected("U406", "1"), f"U406.1 (NC) unconnected, got {net_of('U406', '1')}")
    check(members("RP_EN_N") == sorted([("U402", "9"), ("U406", "4"), ("TP407", "1")]),
          f"RP_EN_N (U402 /OE) only U406's output and TP407: {members('RP_EN_N')}")
    check(members("RP_EN_OD") == sorted([("Q401", "3"), ("R429", "2"), ("U406", "2")]),
          f"RP_EN_OD only Q401 drain, R429 and U406's input: {members('RP_EN_OD')}")
    check(members("RP_EN_MID") == sorted([("Q401", "2"), ("Q402", "3")]), f"RP_EN_MID members {members('RP_EN_MID')}")
    check(members("RP_EN_CMP") == sorted([("U405", "1"), ("Q401", "1"), ("TP408", "1")]),
          f"RP_EN_CMP members {members('RP_EN_CMP')}")
    check(members("RP_EN_GATE") == sorted([("Q402", "1"), ("R431", "2")]), f"RP_EN_GATE members {members('RP_EN_GATE')}")
    two_pin("R429", "1k", "+3V3", "RP_EN_OD")
    two_pin("R426", "1k", "X4_GP24_EN", "RP_EN_SENSE")
    check(members("RP_EN_SENSE") == sorted([("U405", "3"), ("R426", "2")]), f"RP_EN_SENSE members {members('RP_EN_SENSE')}")
    two_pin("R427", "6.34k", "X4_3V3_REF", "RP_EN_REF")
    two_pin("R428", "100k", "RP_EN_REF", "GND")
    check(sorted(refs("RP_EN_REF")) == ["R427", "R428", "U405"], f"RP_EN_REF members {members('RP_EN_REF')}")
    k = EN_REF_RATIO[1] / (EN_REF_RATIO[0] + EN_REF_RATIO[1])
    check(0.935 <= k <= 0.945 and EN_REF_RATIO == (6.34, 100.0), f"enable threshold {k:.4f} x X4_3V3_REF (want 0.940)")
    two_pin("R430", "100k", "X4_GP24_EN", "GND")
    two_pin("R431", "1k", "X4_GP24_EN", "RP_EN_GATE")
    # nothing on the carrier may source current into GP24 (owner review of PR #8: R424 removed)
    check(sorted(refs("X4_GP24_EN")) == ["J401", "R426", "R430", "R431"], f"X4_GP24_EN members {members('X4_GP24_EN')}")
    # domain crossing: the X4-side enable nets reach the carrier's /OE node only through MOSFET gates
    x4_side = {"X4_3V3_REF", "X4_GP24_EN", "RP_EN_SENSE", "RP_EN_REF", "RP_EN_CMP", "RP_EN_GATE"}
    oe_side = {"RP_EN_N", "RP_EN_OD", "RP_EN_MID"}
    pins_of = {}
    for (r, p) in pin_net:
        pins_of.setdefault(r, set()).add(p)
    bridges = sorted({r for n in oe_side for r, _, _ in nets.get(n, [])          # U402 bridges by design (VCCA/VCCB)
                      if r != "U402" and any(net_of(r, p) in x4_side for p in pins_of.get(r, ()))})
    check(bridges == ["Q401", "Q402"] and net_of("Q401", "1") in x4_side and net_of("Q402", "1") in x4_side
          and not ({net_of("Q401", "2"), net_of("Q401", "3"), net_of("Q402", "2"), net_of("Q402", "3")} & x4_side),
          f"only Q401/Q402 gates link the X4 side to /OE: {bridges}")
    # RP2040-side defaults while U402 is isolated (carrier off, X4 on): ATTN low; IRQ_N only by the RP2040's pull-up
    two_pin("R425", "100k", "X4_GP27_ATTN", "GND")
    check(members("X4_GP22_IRQ_N") == sorted([("J401", "16"), ("R412", "2")]),
          f"X4_GP22_IRQ_N members (no resistor to GP24 or a rail) {members('X4_GP22_IRQ_N')}")
    check(members("X4_GP27_ATTN") == sorted([("J401", "18"), ("R413", "2"), ("R425", "1")]),
          f"X4_GP27_ATTN members {members('X4_GP27_ATTN')}")
    check("RP_VIO" not in nets, "no RP_VIO net (rev A's GPIO-powered translator supply is removed)")

    # ---------------- FPGA side: the RP_* nets reach the FPGA pins of the plan (sheet 2)
    assign = pinplan.compute(HERE.parents[1])[0]
    for sig in ("RP_SCK", "RP_CS_N", "RP_MOSI", "RP_MISO", "RP_IRQ_N", "RP_ATTN"):
        check(("U201", str(assign[sig])) in members(sig), f"{sig} on FPGA pin {assign[sig]}")
    check(assign["RP_SCK"] == 5, "RP_SCK on pin 5 (PCLKT5_0, S4-3)")

    # ---------------- default resistors (R-51, protocol idle levels)
    for ref, val, net, rail in (("R401", "10k", "RP_CS_N", "+3V3"), ("R402", "10k", "RP_SCK", "GND"),
                                ("R403", "10k", "RP_MOSI", "GND"), ("R404", "10k", "RP_MISO", "GND"),
                                ("R405", "2.2k", "RP_IRQ_N", "+3V3"), ("R406", "10k", "RP_ATTN", "GND"),
                                ("R407", "10k", "RP_JTAG_EN_N", "+3V3")):
        two_pin(ref, val, net, rail)

    # ---------------- ER-3: only microamp loads on the X4's header 3.3 V
    # sheet 5 (S5-5): R518 100k into Q503's gate (R519 1M to GND): <= 3.3 V / 1.1 M = 3 uA (audit_sheet5 checks it)
    allowed = ({(u, "15") for u in XLAT} | {("U405", "5"), ("R427", "1"), ("TP405", "1"), ("J401", "1"), ("J401", "17"),
                                            ("R518", "1")} |
               {(c, p) for c, p in members("X4_3V3_REF") if re.match(r"C4\d\d$", c)})
    extra = [m for m in members("X4_3V3_REF") if m not in allowed]
    check(not extra, f"X4_3V3_REF loaded only by VCCB, U405, the reference divider, decoupling, TP405, R518: extra {extra}")
    check(sorted(r for r, _ in members("X4_3V3_REF") if r.startswith("R")) == ["R427", "R518"],
          "the only resistors on X4_3V3_REF are the reference divider R427 (31 uA) and sheet 5's S0 gate resistor R518 "
          "(3 uA): ER-3")

    # ---------------- decoupling: one 100 nF per supply pin (translators: VCCA and VCCB; U405, U406: VCC)
    caps = sorted(r for r in comps if re.match(r"C4\d\d$", r))
    check(caps == [f"C{401 + i}" for i in range(10)], f"sheet-4 capacitors {caps}")
    n_a = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"})
    n_b = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"X4_3V3_REF", "GND"})
    check(n_a == 5 and n_b == 5, f"decoupling: {n_a} on +3V3, {n_b} on X4_3V3_REF (want 5, 5)")

    # ---------------- test points and parts list
    for ref, net in (("TP401", "RP_SCK"), ("TP402", "RP_MISO"), ("TP403", "RP_CS_N"), ("TP404", "RP_ATTN"),
                     ("TP405", "X4_3V3_REF"), ("TP406", "GND"), ("TP407", "RP_EN_N"), ("TP408", "RP_EN_CMP")):
        check(net_of(ref, "1") == net, f"{ref} on {net}, got {net_of(ref, '1')}")
    known = ({"J401", "U401", "U402", "U403", "U404", "U405", "U406", "Q401", "Q402"} |
             {f"R{n}" for n in range(401, 432) if n not in (416, 417, 424)} |
             {f"C{n}" for n in range(401, 411)} | {f"TP{n}" for n in range(401, 409)})
    present = {r for r in comps if re.match(r"[A-Z]+4\d\d$", r)}
    check(present == known, f"sheet-4 parts: missing {sorted(known - present)}, unexpected {sorted(present - known)}")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
