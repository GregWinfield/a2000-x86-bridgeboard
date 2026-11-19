# SPDX-License-Identifier: MIT
"""Audit sheet-4 connectivity (RP2040 host link) in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet4.py <netlist.net>

Expected connections come from: the X4 header map (docs/pin-assignment-matrix.md section 3, [V S1 sh.21]),
the SN74AVC4T774 pinout and function table (TI SCES693I [V S66]: DIR high = A->B, low = B->A; OE high =
isolated), the host-link protocol idle levels and R-51 (docs/hdl/host-link-protocol.md sections 2, 11),
ER-3 (the X4's header 3.3 V is a reference: only translator supplies, decoupling and a test point on it)
and decision S4-6 (every carrier -> RP2040 output on U402, whose B supply RP_VIO is the RP2040's GP24, so
no B output can exceed the RP2040's own IOVDD; B-side pull-downs on every RP2040 -> carrier input).
Every check prints FAIL on failure; exit code 1 on any failure.
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
from sheet4 import (BPULL, J401_GND, J401_NC, J401_REF, J401_SIG, J401_VIO, PINS, SERIES, VCCB,  # noqa: E402
                    XLAT)

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
        elif pn in J401_VIO:
            check(net_of("J401", pn) == J401_VIO[pn], f"J401.{pn} on {J401_VIO[pn]}, got {net_of('J401', pn)}")
        else:
            check(net_of("J401", pn) == J401_SIG[pn][0], f"J401.{pn} on {J401_SIG[pn][0]}, got {net_of('J401', pn)}")
    check(sorted(set(J401_REF) | set(J401_GND) | set(J401_NC) | set(J401_SIG) | set(J401_VIO)) == list(range(1, 41)),
          "J401 every pin classified")

    # ---------------- translators: supplies, OE, DIR per channel, A and B nets
    x4net = {(u, ch): net for _, (net, u, ch) in J401_SIG.items()}
    for u, chans in XLAT.items():
        c = comps.get(u)
        check(c is not None and c["value"] == "SN74AVC4T774PWR" and c["footprint"] == "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
              f"{u} SN74AVC4T774PWR, TSSOP-16")
        check(net_of(u, 16) == "+3V3" and net_of(u, 15) == VCCB[u] and net_of(u, 10) == "GND",
              f"{u} VCCA +3V3, VCCB {VCCB[u]}, GND: {net_of(u, 16)}, {net_of(u, 15)}, {net_of(u, 10)}")
        check(net_of(u, 9) == ("RP_JTAG_EN_N" if u == "U403" else "GND"), f"{u} OE: {net_of(u, 9)}")
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

    # ---------------- S4-6: every carrier -> RP2040 output on U402 (VCCB = RP_VIO); the X4_3V3_REF translators
    # carry only RP2040 -> carrier inputs, each with a 100k B-side pull-down
    for u, chans in XLAT.items():
        outs = [n for n, d in chans if n is not None and d == "AB"]
        if VCCB[u] == "X4_3V3_REF":
            check(not outs, f"{u} on X4_3V3_REF drives no RP2040 pin: {outs}")
        else:
            check(sorted(outs) == ["FPGA_TDO", "RP_ATTN", "RP_IRQ_N", "RP_MISO"], f"{u} carries every output: {outs}")
    ins = sorted((u, ch) for u, chans in XLAT.items() for ch, (n, d) in enumerate(chans, start=1) if n and d == "BA")
    check(sorted(BPULL) == ins, f"a B-side pull-down on every RP2040 -> carrier input: {sorted(BPULL)} vs {ins}")
    for (u, ch), ref in BPULL.items():
        two_pin(ref, "100k", x4net[(u, ch)], "GND")
        check(members(x4net[(u, ch)]) == sorted([("J401", str(next(p for p, v in J401_SIG.items() if v[1:] == (u, ch)))),
                                                 (u, PINS["B"][ch]), (ref, "1")]),
              f"{x4net[(u, ch)]} members {members(x4net[(u, ch)])}")
    # RP_VIO: GP24 -> R416 47R -> U402 VCCB, its 100 nF, R417 100k bleed, TP407; nothing else
    two_pin("R416", "47R", "X4_GP24_VIO", "RP_VIO")
    two_pin("R417", "100k", "RP_VIO", "GND")
    check(members("X4_GP24_VIO") == sorted([("J401", "22"), ("R416", "1")]), f"X4_GP24_VIO members {members('X4_GP24_VIO')}")
    vio = members("RP_VIO")
    vio_caps = [m for m in vio if m[0].startswith("C4")]
    check(len(vio_caps) == 1 and sorted(set(vio) - set(vio_caps)) == sorted([("U402", "15"), ("R416", "2"), ("R417", "1"),
                                                                                ("TP407", "1")]),
          f"RP_VIO members {vio}")

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

    # ---------------- ER-3: nothing but translator supplies, decoupling and TP405 on the X4's 3.3 V
    ref_members = members("X4_3V3_REF")
    bad = [m for m in ref_members if not (m[0] in XLAT and m[1] == "15") and not m[0].startswith(("C4", "TP405", "J401"))]
    check(not bad, f"X4_3V3_REF loaded only by VCCB, decoupling and TP405: extra {bad}")
    check(not [m for m in ref_members if m[0].startswith("R")], "no resistor on X4_3V3_REF (ER-3)")
    check(sorted(m[0] for m in ref_members if m[1] == "15" and m[0] in XLAT) ==
          sorted(u for u in XLAT if VCCB[u] == "X4_3V3_REF"), "VCCB on X4_3V3_REF: U401, U403, U404")

    # ---------------- decoupling: one 100 nF per translator supply pin
    caps = sorted(r for r in comps if re.match(r"C4\d\d$", r))
    check(caps == [f"C{401 + i}" for i in range(8)], f"sheet-4 capacitors {caps}")
    n_a = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"})
    n_b = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"X4_3V3_REF", "GND"})
    n_v = sum(1 for r in caps if {net_of(r, "1"), net_of(r, "2")} == {"RP_VIO", "GND"})
    check(n_a == 4 and n_b == 3 and n_v == 1, f"decoupling: {n_a} on VCCA, {n_b} on X4_3V3_REF, {n_v} on RP_VIO (want 4, 3, 1)")

    # ---------------- test points and parts list
    for ref, net in (("TP401", "RP_SCK"), ("TP402", "RP_MISO"), ("TP403", "RP_CS_N"), ("TP404", "RP_ATTN"),
                     ("TP405", "X4_3V3_REF"), ("TP406", "GND"), ("TP407", "RP_VIO")):
        check(net_of(ref, "1") == net, f"{ref} on {net}, got {net_of(ref, '1')}")
    known = ({"J401", "U401", "U402", "U403", "U404"} | {f"R{n}" for n in range(401, 424)} |
             {f"C{n}" for n in range(401, 409)} | {f"TP{n}" for n in range(401, 408)})
    present = {r for r in comps if re.match(r"[A-Z]+4\d\d$", r)}
    check(present == known, f"sheet-4 parts: missing {sorted(known - present)}, unexpected {sorted(present - known)}")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
