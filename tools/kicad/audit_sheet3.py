# SPDX-License-Identifier: MIT
"""Audit sheet-3 connectivity (shared SRAM) in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet3.py <netlist.net>

Expected connections: the U301 pin table transcribed from the ISSI IS61/64WV25616EDBLL datasheet
Rev. A2 (44-pin TSOP-II), the safe-state pull-ups, decoupling, test points, and the cross-sheet
local bus (each LDn joins U103's A port on sheet 1 to U301's I/On). Since sheet 2 is drawn, every SA,
SRAM_* and LD net also carries exactly one FPGA pin (U201; which pin is checked by audit_sheet2.py),
and SA17 carries R208, the SN pull-up. Every check prints FAIL on failure; exit code 1 on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlist                     # noqa: E402

fails = 0
checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


# ISSI IS61/64WV25616EDBLL Rev. A2, 44-pin TSOP (Type II)
U301_A = {0: "1", 1: "2", 2: "3", 3: "4", 4: "5", 5: "18", 6: "19", 7: "20", 8: "21", 9: "22", 10: "23", 11: "24",
          12: "25", 13: "26", 14: "27", 15: "42", 16: "43", 17: "44"}
U301_IO = {0: "7", 1: "8", 2: "9", 3: "10", 4: "13", 5: "14", 6: "15", 7: "16", 8: "29", 9: "30", 10: "31", 11: "32",
           12: "35", 13: "36", 14: "37", 15: "38"}
U301_CTL = {"6": "SRAM_CE_N", "41": "SRAM_OE_N", "17": "SRAM_WE_N", "40": "SRAM_UB_N", "39": "SRAM_LB_N"}
# TI SCES635B (SN74LVCH16T245 DGG): A port, LD0-LD7 = 1A1-1A8, LD8-LD15 = 2A1-2A8 (sheet 1)
U103_A = [47, 46, 44, 43, 41, 40, 38, 37, 36, 35, 33, 32, 30, 29, 27, 26]


def main(path):
    comps, raw_nets = netlist.load(Path(path))
    nets = {}
    for name, nodes in raw_nets.items():
        nets[name.rsplit("/", 1)[-1] if name.startswith("/") else name] = nodes
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p, _ in nodes}

    def net_of(ref, pin):
        return pin_net.get((ref, pin))

    def members(net):
        return sorted((r, p) for r, p, _ in nets.get(net, []))

    # ---- U301: part, footprint, every pin
    u = comps.get("U301")
    check(u is not None, "U301 present")
    if u:
        check(u["value"] == "IS61WV25616EDBLL-10TLI", f"U301 value {u['value']}")
        check(u["footprint"] == "Package_SO:TSOP-II-44_10.16x18.41mm_P0.8mm", f"U301 footprint {u['footprint']}")
        check(u["fields"].get("MPN") == "IS61WV25616EDBLL-10TLI", "U301 MPN field")
    def one_fpga(net):
        f = [x for x in members(net) if x[0] == "U201"]
        check(len(f) == 1, f"{net} has exactly one FPGA (U201) pin: {f}")

    for i, pin in U301_A.items():
        check(net_of("U301", pin) == f"SA{i}", f"U301.{pin} (A{i}) on SA{i}, got {net_of('U301', pin)}")
        want = [("U301", pin)] + ([("TP304", "1")] if i == 0 else []) + ([("R208", "2")] if i == 17 else [])
        check(sorted(x for x in members(f"SA{i}") if x[0] != "U201") == sorted(want), f"SA{i} members {members(f'SA{i}')}")
        one_fpga(f"SA{i}")
    for i, pin in U301_IO.items():
        check(net_of("U301", pin) == f"LD{i}", f"U301.{pin} (I/O{i}) on LD{i}, got {net_of('U301', pin)}")
        m = members(f"LD{i}")
        check(("U103", str(U103_A[i])) in m, f"LD{i} joins U103.{U103_A[i]} (A port, sheet 1): {m}")
        extra = [x for x in m if x not in (("U301", pin), ("U103", str(U103_A[i])), ("TP305", "1")) and x[0] != "U201"]
        check(not extra, f"LD{i} unexpected members {extra}")
        one_fpga(f"LD{i}")
    for pin, net in U301_CTL.items():
        check(net_of("U301", pin) == net, f"U301.{pin} on {net}, got {net_of('U301', pin)}")
        one_fpga(net)
    for pin in ("11", "33"):
        check(net_of("U301", pin) == "+3V3", f"U301.{pin} VDD on +3V3")
    for pin in ("12", "34"):
        check(net_of("U301", pin) == "GND", f"U301.{pin} GND on GND")
    n28 = net_of("U301", "28")
    check(n28 is None or n28.startswith("unconnected-") or len(nets.get(n28, [])) == 1, f"U301.28 (NC) unconnected: {n28}")

    # ---- safe-state pull-ups (2.2k to +3V3)
    for ref, net in (("R301", "SRAM_CE_N"), ("R302", "SRAM_WE_N")):
        c = comps.get(ref)
        check(c is not None and c["value"] == "2.2k", f"{ref} 2.2k")
        check({net_of(ref, "1"), net_of(ref, "2")} == {"+3V3", net}, f"{ref} between +3V3 and {net}")
    for net in ("SRAM_OE_N", "SRAM_UB_N", "SRAM_LB_N"):
        check(not any(r.startswith("R") for r, _ in members(net)), f"{net} has no pull resistor (design: only /CE, /WE)")

    # ---- decoupling: one 100 nF per VDD pin, one 10 uF bulk
    caps = {r: c for r, c in comps.items() if r.startswith("C3")}
    check(sorted(caps) == ["C301", "C302", "C303"], f"sheet-3 capacitors {sorted(caps)}")
    for r, val in (("C301", "100n"), ("C302", "100n"), ("C303", "10u")):
        if r in caps:
            check(caps[r]["value"] == val, f"{r} value {caps[r]['value']}")
            check({net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"}, f"{r} between +3V3 and GND")
    vdd = sum(1 for r, p, t in nets.get("+3V3", []) if r == "U301" and t == "power_in")
    check(vdd == 2, f"U301 supply pins on +3V3: {vdd}")

    # ---- test points
    for ref, net in (("TP301", "SRAM_CE_N"), ("TP302", "SRAM_OE_N"), ("TP303", "SRAM_WE_N"), ("TP304", "SA0"),
                     ("TP305", "LD0"), ("TP306", "GND")):
        check(net_of(ref, "1") == net, f"{ref} on {net}, got {net_of(ref, '1')}")

    # ---- nothing else on sheet 3
    known = {"U301", "R301", "R302", "C301", "C302", "C303", "TP301", "TP302", "TP303", "TP304", "TP305", "TP306"}
    check(set(r for r in comps if r in known) == known, f"sheet-3 parts present: {sorted(known - set(comps))} missing")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
