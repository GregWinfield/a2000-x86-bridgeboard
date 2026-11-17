# SPDX-License-Identifier: MIT
"""Audit sheet-1 connectivity in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet1.py <netlist.net>

The expected connections come from the same tables used to draw the sheet
(gen_project.ZNET) plus explicit per-IC pin maps transcribed from the TI
datasheets.  Every check prints PASS/FAIL; exit code 1 on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlist                     # noqa: E402
from gen_project import ZNET       # noqa: E402

fails = 0
checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


def main(path):
    comps, raw_nets = netlist.load(Path(path))
    # KiCad prefixes sheet-local nets with the sheet path ("/1 Zorro II .../Z_A1"); compare bare names.
    nets = {}
    for name, nodes in raw_nets.items():
        bare = name.rsplit("/", 1)[-1] if name.startswith("/") else name
        if bare in nets:
            check(False, f"net name collision after stripping sheet path: {name}")
        nets[bare] = nodes
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin, _ in nodes:
            pin_net[(ref, pin)] = name

    def net_of(ref, pin):
        return pin_net.get((ref, pin))

    def is_unconnected(ref, pin):
        n = net_of(ref, pin)
        return n is None or n.startswith("unconnected-") or len(nets.get(n, [])) == 1

    # ---- J101: all 100 Zorro pins -------------------------------------------
    for n in range(1, 101):
        want = ZNET[n]
        got = net_of("J101", str(n))
        if want is None:
            check(is_unconnected("J101", str(n)), f"J101.{n} should be unconnected, is on {got}")
        else:
            check(got == want, f"J101.{n} expected {want}, got {got}")

    # ---- U101/U102 SN74LVC16244A ----------------------------------------------
    a_pins = ["47", "46", "44", "43", "41", "40", "38", "37", "36", "35", "33", "32", "30", "29", "27", "26"]
    y_pins = ["2", "3", "5", "6", "8", "9", "11", "12", "13", "14", "16", "17", "19", "20", "22", "23"]
    m101 = [(f"Z_A{i}", f"ZB_A{i}") for i in range(1, 17)]
    m102 = [(f"Z_A{i}", f"ZB_A{i}") for i in range(17, 24)] + [
        ("Z_AS_N", "ZB_AS_N"), ("Z_UDS_N", "ZB_UDS_N"), ("Z_LDS_N", "ZB_LDS_N"), ("Z_READ", "ZB_READ"),
        ("Z_DOE", "ZB_DOE"), ("Z_E7M", "ZB_E7M"), ("Z_CFGIN_N", "ZB_CFGIN_N"), ("Z_BUSRST_N", "ZB_BUSRST_N"),
        ("Z_CDAC", "ZB_CDAC")]
    for ref, mp in (("U101", m101), ("U102", m102)):
        for ap, yp, (zi, zo) in zip(a_pins, y_pins, mp):
            check(net_of(ref, ap) == zi, f"{ref}.{ap} expected {zi}, got {net_of(ref, ap)}")
            check(net_of(ref, yp) == zo, f"{ref}.{yp} expected {zo}, got {net_of(ref, yp)}")
        for p in ("1", "48", "25", "24"):
            check(net_of(ref, p) == "GND", f"{ref}.{p} (/OE) expected GND, got {net_of(ref, p)}")
        for p in ("7", "18", "31", "42"):
            check(net_of(ref, p) == "+3V3", f"{ref}.{p} (VCC) expected +3V3, got {net_of(ref, p)}")
        for p in ("4", "10", "15", "21", "28", "34", "39", "45"):
            check(net_of(ref, p) == "GND", f"{ref}.{p} (GND) expected GND, got {net_of(ref, p)}")

    # ---- U103 SN74LVCH16T245 + RN101..104 ---------------------------------------
    b = ["2", "3", "5", "6", "8", "9", "11", "12", "13", "14", "16", "17", "19", "20", "22", "23"]
    a = ["47", "46", "44", "43", "41", "40", "38", "37", "36", "35", "33", "32", "30", "29", "27", "26"]
    for bit in range(16):
        check(net_of("U103", a[bit]) == f"LD{bit}", f"U103.{a[bit]} expected LD{bit}, got {net_of('U103', a[bit])}")
        bnet = net_of("U103", b[bit])
        nodes = nets.get(bnet, [])
        rn = [(r, p) for r, p, _ in nodes if r.startswith("RN")]
        check(len(nodes) == 2 and len(rn) == 1, f"U103.{b[bit]} net {bnet} should be U103<->one RN pin only: {nodes}")
        if rn:
            r, p = rn[0]
            other = {"1": "8", "2": "7", "3": "6", "4": "5", "5": "4", "6": "3", "7": "2", "8": "1"}[p]
            check(net_of(r, other) == f"Z_D{bit}", f"{r}.{other} expected Z_D{bit}, got {net_of(r, other)}")
            check(comps[r]["value"] == "4x22R", f"{r} value {comps[r]['value']}")
    for p in ("1", "24"):
        check(net_of("U103", p) == "ZF_DBUF_DIR", f"U103.{p} (DIR) expected ZF_DBUF_DIR, got {net_of('U103', p)}")
    for p in ("48", "25"):
        check(net_of("U103", p) == "ZF_DBUF_OE_N", f"U103.{p} (/OE) expected ZF_DBUF_OE_N, got {net_of('U103', p)}")
    for p, rail in (("7", "+5V_BUS"), ("18", "+5V_BUS"), ("31", "+3V3"), ("42", "+3V3")):
        check(net_of("U103", p) == rail, f"U103.{p} expected {rail}, got {net_of('U103', p)}")
    for p in ("4", "10", "15", "21", "28", "34", "39", "45"):
        check(net_of("U103", p) == "GND", f"U103.{p} (GND) expected GND, got {net_of('U103', p)}")

    # ---- U104 SN74LVC2T45 -------------------------------------------------------------
    exp104 = {"1": "+3V3", "2": "ZF_SLAVE_N", "3": "ZF_CFGOUT_N", "4": "GND", "5": "+3V3", "8": "+5V_BUS"}
    for p, n_ in exp104.items():
        check(net_of("U104", p) == n_, f"U104.{p} expected {n_}, got {net_of('U104', p)}")
    for upin, rref, znet in (("7", "R117", "Z_SLAVE_N"), ("6", "R118", "Z_CFGOUT_N")):
        nodes = nets.get(net_of("U104", upin), [])
        check({r for r, _, _ in nodes} == {"U104", rref}, f"U104.{upin} should go only to {rref}: {nodes}")
        other = [p for r, p, _ in nodes if r == rref]
        if other:
            o = "2" if other[0] == "1" else "1"
            check(net_of(rref, o) == znet, f"{rref}.{o} expected {znet}, got {net_of(rref, o)}")
        check(comps[rref]["value"] == "22R", f"{rref} value {comps[rref]['value']}")

    # ---- U105 SN74LVC07A ----------------------------------------------------------------
    exp105 = {"1": "ZF_INT2_N", "2": "Z_INT2_N", "3": "ZF_INT6_N", "4": "Z_INT6_N", "5": "ZF_XRDY", "6": "Z_XRDY",
              "9": "ZF_OVR_N", "11": "ZF_DTACK_N", "13": "+3V3", "14": "+3V3", "7": "GND"}
    for p, n_ in exp105.items():
        check(net_of("U105", p) == n_, f"U105.{p} expected {n_}, got {net_of('U105', p)}")
    check(is_unconnected("U105", "12"), "U105.12 (6Y) should be unconnected")
    for upin, rref, znet in (("8", "R119", "Z_OVR_N"), ("10", "R120", "Z_DTACK_N")):
        nodes = nets.get(net_of("U105", upin), [])
        check({r for r, _, _ in nodes} == {"U105", rref}, f"U105.{upin} should go only to {rref}: {nodes}")
        o = [p for r, p, _ in nodes if r == rref]
        if o:
            oo = "2" if o[0] == "1" else "1"
            check(net_of(rref, oo) == znet, f"{rref}.{oo} expected {znet}, got {net_of(rref, oo)}")
        check(comps[rref]["fields"].get("DNP", "") != "" or "DNP" in comps[rref]["value"],
              f"{rref} should be marked DNP")

    # ---- default-state resistors ---------------------------------------------------------
    for net in ("ZF_SLAVE_N", "ZF_CFGOUT_N", "ZF_INT2_N", "ZF_INT6_N", "ZF_XRDY", "ZF_OVR_N", "ZF_DTACK_N",
                "ZF_DBUF_OE_N"):
        rs = [(r, p) for r, p, _ in nets.get(net, []) if r.startswith("R")]
        ok = False
        for r, p in rs:
            o = "2" if p == "1" else "1"
            if net_of(r, o) == "+3V3" and comps[r]["value"] == "2.2k":
                ok = True
        check(ok, f"{net} needs a 2.2k pull-up to +3V3 (found {rs})")
    rs = [(r, p) for r, p, _ in nets.get("ZF_DBUF_DIR", []) if r.startswith("R")]
    check(any(net_of(r, "2" if p == "1" else "1") == "GND" and comps[r]["value"] == "10k" for r, p in rs),
          f"ZF_DBUF_DIR needs a 10k pull-down to GND (found {rs})")

    # ---- decoupling -------------------------------------------------------------------------
    n3 = sum(1 for r, p, _ in nets.get("+3V3", []) if r.startswith("C"))
    n5 = sum(1 for r, p, _ in nets.get("+5V_BUS", []) if r.startswith("C"))
    for r, cp in comps.items():
        if r.startswith("C"):
            nn = {net_of(r, "1"), net_of(r, "2")}
            check(("GND" in nn) and (nn & {"+3V3", "+5V_BUS"}), f"{r} must sit between a rail and GND: {nn}")
    # one 100 nF per supply pin: +3V3 pins = U101 4 + U102 4 + U103 VCCA 2 + U104 VCCA 1 + U105 1 = 12, plus 1 bulk
    # +5V_BUS pins = U103 VCCB 2 + U104 VCCB 1 = 3, plus 1 bulk
    check(n3 == 13, f"+3V3 decoupling count {n3} (expected 12x100n + 1x10u = 13)")
    check(n5 == 4, f"+5V_BUS decoupling count {n5} (expected 3x100n + 1x10u = 4)")
    for rail, pins in (("+3V3", 12), ("+5V_BUS", 3)):
        ic_pins = sum(1 for r, p, t in nets.get(rail, []) if r.startswith("U") and t == "power_in")
        check(ic_pins == pins, f"{rail}: {ic_pins} IC supply pins (expected {pins})")

    # ---- test points ---------------------------------------------------------------------------
    tp_expect = ["Z_AS_N", "Z_SLAVE_N", "Z_DOE", "Z_E7M", "Z_READ", "Z_UDS_N", "Z_LDS_N", "Z_CFGIN_N",
                 "Z_CFGOUT_N", "Z_INT2_N", "Z_XRDY", "Z_BUSRST_N", "Z_BERR_N", "ZB_AS_N", "ZF_SLAVE_N", "GND", "GND"]
    for i, want in enumerate(tp_expect):
        ref = f"TP{101 + i}"
        check(net_of(ref, "1") == want, f"{ref} expected on {want}, got {net_of(ref, '1')}")

    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
