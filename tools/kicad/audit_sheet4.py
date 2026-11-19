# SPDX-License-Identifier: MIT
"""Audit sheet-4 connectivity (RP2040 host link) in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet4.py <netlist.net>

Expected connections come from: the X4 header map (docs/pin-assignment-matrix.md section 3, [V S1 sh.21]),
the SN74AVC4T774 pinout and function table (TI SCES693I [V S66]: DIR high = A->B, low = B->A; OE high =
isolated), the TLV7021 pinout (TI SLVSDM5F: DBV 1 OUT, 2 VEE, 3 IN+, 4 IN-, 5 VCC), the host-link protocol
idle levels and R-51 (docs/hdl/host-link-protocol.md sections 2, 11), ER-3 (the X4's header 3.3 V is a
reference: only microamp loads on it) and decision S4-6 rev A1 (docs/stage2/sheet4-s46-isolation.md): every
carrier -> RP2040 output on U402, whose /OE comes only from comparator U405 (enabled only while GP24 is above
0.930 x X4_3V3_REF); a B-side pull-down on every RP2040 -> carrier input; IRQ_N and ATTN defined at the
RP2040 while U402 is isolated. Every check prints FAIL on failure; exit code 1 on any failure.
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

    # ---------------- S4-6 rev A1: U402's /OE only from comparator U405 (GP24 vs 0.930 x X4_3V3_REF)
    c5 = comps.get("U405")
    check(c5 is not None and c5["value"] == "TLV7021DBVR" and c5["footprint"] == "Package_TO_SOT_SMD:SOT-23-5",
          "U405 TLV7021DBVR, SOT-23-5")
    for pin, net in (("5", "X4_3V3_REF"), ("2", "GND"), ("3", "RP_EN_REF"), ("4", "RP_EN_SENSE"), ("1", "RP_EN_N")):
        check(net_of("U405", pin) == net, f"U405.{pin} on {net}, got {net_of('U405', pin)}")
    check(members("RP_EN_N") == sorted([("U402", "9"), ("U405", "1"), ("R429", "2"), ("TP407", "1")]),
          f"RP_EN_N (U402 /OE) only U405 OUT, R429 and TP407: {members('RP_EN_N')}")
    two_pin("R429", "10k", "+3V3", "RP_EN_N")
    two_pin("R426", "10k", "X4_GP24_EN", "RP_EN_SENSE")
    check(members("RP_EN_SENSE") == sorted([("U405", "4"), ("R426", "2")]), f"RP_EN_SENSE members {members('RP_EN_SENSE')}")
    two_pin("R427", "7.5k", "X4_3V3_REF", "RP_EN_REF")
    two_pin("R428", "100k", "RP_EN_REF", "GND")
    check(sorted(refs("RP_EN_REF")) == ["R427", "R428", "U405"], f"RP_EN_REF members {members('RP_EN_REF')}")
    k = EN_REF_RATIO[1] / (EN_REF_RATIO[0] + EN_REF_RATIO[1])
    check(0.925 <= k <= 0.935 and EN_REF_RATIO == (7.5, 100.0), f"enable threshold {k:.4f} x X4_3V3_REF (want 0.930)")
    two_pin("R430", "100k", "X4_GP24_EN", "GND")
    check(sorted(refs("X4_GP24_EN")) == ["J401", "R424", "R426", "R430"], f"X4_GP24_EN members {members('X4_GP24_EN')}")
    # RP2040-side defaults while U402 is isolated (carrier off, X4 on): IRQ_N high (no interrupt), ATTN low
    two_pin("R424", "10k", "X4_GP24_EN", "X4_GP22_IRQ_N")
    two_pin("R425", "100k", "X4_GP27_ATTN", "GND")
    check(members("X4_GP22_IRQ_N") == sorted([("J401", "16"), ("R412", "2"), ("R424", "2")]),
          f"X4_GP22_IRQ_N members {members('X4_GP22_IRQ_N')}")
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
    allowed = ({(u, "15") for u in XLAT} | {("U405", "5"), ("R427", "1"), ("TP405", "1"), ("J401", "1"), ("J401", "17")} |
               {(c, p) for c, p in members("X4_3V3_REF") if re.match(r"C4\d\d$", c)})
    extra = [m for m in members("X4_3V3_REF") if m not in allowed]
    check(not extra, f"X4_3V3_REF loaded only by VCCB, U405, the reference divider, decoupling, TP405: extra {extra}")
    check([r for r, _ in members("X4_3V3_REF") if r.startswith("R")] == ["R427"],
          "the only resistor on X4_3V3_REF is the reference divider R427 (3.3 V / 107.5 k = 31 uA; ER-3)")

    # ---------------- decoupling: one 100 nF per supply pin (translators: VCCA and VCCB; U405: VCC)
    caps = sorted(r for r in comps if re.match(r"C4\d\d$", r))
    check(caps == [f"C{401 + i}" for i in range(9)], f"sheet-4 capacitors {caps}")
    n_a = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"})
    n_b = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"X4_3V3_REF", "GND"})
    check(n_a == 4 and n_b == 5, f"decoupling: {n_a} on +3V3, {n_b} on X4_3V3_REF (want 4, 5)")

    # ---------------- test points and parts list
    for ref, net in (("TP401", "RP_SCK"), ("TP402", "RP_MISO"), ("TP403", "RP_CS_N"), ("TP404", "RP_ATTN"),
                     ("TP405", "X4_3V3_REF"), ("TP406", "GND"), ("TP407", "RP_EN_N")):
        check(net_of(ref, "1") == net, f"{ref} on {net}, got {net_of(ref, '1')}")
    known = ({"J401", "U401", "U402", "U403", "U404", "U405"} | {f"R{n}" for n in range(401, 431) if n not in (416, 417)} |
             {f"C{n}" for n in range(401, 410)} | {f"TP{n}" for n in range(401, 408)})
    present = {r for r in comps if re.match(r"[A-Z]+4\d\d$", r)}
    check(present == known, f"sheet-4 parts: missing {sorted(known - present)}, unexpected {sorted(present - known)}")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
