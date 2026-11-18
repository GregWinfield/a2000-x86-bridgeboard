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
        ("Z_BERR_N", "ZB_BERR_N")]                       # rev B: /BERR monitored (was CDAC)
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
        check(net_of("U103", p) == "DBUF_OE_G_N", f"U103.{p} (/OE) expected DBUF_OE_G_N, got {net_of('U103', p)}")
    for p, rail in (("7", "+5V_BUS"), ("18", "+5V_BUS"), ("31", "+3V3"), ("42", "+3V3")):
        check(net_of("U103", p) == rail, f"U103.{p} expected {rail}, got {net_of('U103', p)}")
    for p in ("4", "10", "15", "21", "28", "34", "39", "45"):
        check(net_of("U103", p) == "GND", f"U103.{p} (GND) expected GND, got {net_of('U103', p)}")

    # ---- U104 SN74LVC8T245 (rev B; TI SCES584D PW pinout) --------------------------------
    exp104 = {"1": "+3V3", "2": "+3V3", "3": "ZF_SLAVE_N", "4": "ZF_CFGOUT_N", "22": "CARD_EN_N",
              "23": "+5V_BUS", "24": "+5V_BUS", "11": "GND", "12": "GND", "13": "GND"}
    exp104.update({str(n): "GND" for n in range(5, 11)})      # unused A3..A8
    exp104.update({str(n): "GND" for n in range(14, 20)})     # unused B8..B3
    for p, n_ in exp104.items():
        check(net_of("U104", p) == n_, f"U104.{p} expected {n_}, got {net_of('U104', p)}")
    check(comps["U104"]["value"] == "SN74LVC8T245PWR", f"U104 value {comps['U104']['value']}")
    for upin, rref, znet in (("21", "R117", "Z_SLAVE_N"), ("20", "R118", "Z_CFGOUT_N")):
        nodes = nets.get(net_of("U104", upin), [])
        check({r for r, _, _ in nodes} == {"U104", rref}, f"U104.{upin} should go only to {rref}: {nodes}")
        other = [p for r, p, _ in nodes if r == rref]
        if other:
            o = "2" if other[0] == "1" else "1"
            check(net_of(rref, o) == znet, f"{rref}.{o} expected {znet}, got {net_of(rref, o)}")
        check(comps[rref]["value"] == "22R", f"{rref} value {comps[rref]['value']}")

    # ---- U105 SN74LVC07A ----------------------------------------------------------------
    exp105 = {"1": "INT2_G_N", "2": "Z_INT2_N", "3": "INT6_G_N", "4": "Z_INT6_N", "5": "XRDY_G", "6": "Z_XRDY",
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

    # ---- rev B card-enable / fail-safe gating ---------------------------------------------
    def pull(net, rail, value):
        rs_ = [(r, p) for r, p, _ in nets.get(net, []) if r.startswith("R")]
        check(any(net_of(r, "2" if p == "1" else "1") == rail and comps[r]["value"] == value for r, p in rs_),
              f"{net} needs a {value} resistor to {rail} (found {rs_})")
    pull("EN_OK", "+3V3", "10k")          # R121: wired-AND pull-up
    pull("ZF_ARM", "GND", "10k")          # R122: blank FPGA = not armed
    pull("CARD_EN_N", "+3V3", "10k")      # R123: U104 ~OE high at power-up (TI)
    pull("DBUF_OE_G_N", "+3V3", "10k")    # R124: U103 ~OE high at power-up (TI)
    # U106 SN74LVC1G00 (SCES212AC DBV): 1 A, 2 B, 3 GND, 4 Y, 5 VCC
    for p, n_ in {"1": "EN_OK", "2": "ZF_ARM", "3": "GND", "4": "CARD_EN_N", "5": "+3V3"}.items():
        check(net_of("U106", p) == n_, f"U106.{p} expected {n_}, got {net_of('U106', p)}")
    # U107 SN74LVC32A (SCAS286U PW): gates (A, B, Y)
    exp107 = {"1": "ZF_DBUF_OE_N", "2": "CARD_EN_N", "3": "DBUF_OE_G_N",
              "4": "ZF_XRDY", "5": "CARD_EN_N", "6": "XRDY_G",
              "9": "ZF_INT2_N", "10": "CARD_EN_N", "8": "INT2_G_N",
              "12": "ZF_INT6_N", "13": "CARD_EN_N", "11": "INT6_G_N", "7": "GND", "14": "+3V3"}
    for p, n_ in exp107.items():
        check(net_of("U107", p) == n_, f"U107.{p} expected {n_}, got {net_of('U107', p)}")
    # U108/U109 TPS3808 (SBVS050N DBV): 1 RESET, 2 GND, 3 MR, 4 CT, 5 SENSE, 6 VDD
    for ref, sense, mpn in (("U108", "+3V3", "TPS3808G33DBVR"), ("U109", None, "TPS3808G01DBVR")):
        for p, n_ in {"1": "EN_OK", "2": "GND", "3": "+3V3", "6": "+3V3"}.items():
            check(net_of(ref, p) == n_, f"{ref}.{p} expected {n_}, got {net_of(ref, p)}")
        check(is_unconnected(ref, "4"), f"{ref}.4 (CT) must be open (fixed 12-28 ms delay)")
        check(comps[ref]["value"] == mpn, f"{ref} value {comps[ref]['value']} (expected {mpn})")
        if sense:
            check(net_of(ref, "5") == sense, f"{ref}.5 (SENSE) expected {sense}, got {net_of(ref, '5')}")
    sn = net_of("U109", "5")
    div = {r: comps[r]["value"] for r, _, _ in nets.get(sn, []) if r.startswith("R")}
    check(sorted(div.values()) == ["10k", "95.3k"], f"U109 SENSE divider 95.3k/10k (found {div})")
    for r, v in div.items():
        p_ = next(p for rr, p, _ in nets[sn] if rr == r)
        other = net_of(r, "2" if p_ == "1" else "1")
        check(other == ("+5V_BUS" if v == "95.3k" else "GND"), f"{r} ({v}) far end on {other}")
    check({net_of("JP101", "1"), net_of("JP101", "2")} == {"EN_OK", "GND"}, "JP101 between EN_OK and GND")
    en_ok_drivers = sorted(r for r, p, t in nets.get("EN_OK", []) if t == "open_collector")
    check(en_ok_drivers == ["U108", "U109"], f"EN_OK open-drain drivers {en_ok_drivers}")

    # ---- decoupling -------------------------------------------------------------------------
    n3 = sum(1 for r, p, _ in nets.get("+3V3", []) if r.startswith("C"))
    n5 = sum(1 for r, p, _ in nets.get("+5V_BUS", []) if r.startswith("C"))
    for r, cp in comps.items():
        if r.startswith("C"):
            nn = {net_of(r, "1"), net_of(r, "2")}
            check(("GND" in nn) and (nn & {"+3V3", "+5V_BUS"}), f"{r} must sit between a rail and GND: {nn}")
    # one 100 nF per supply pin: +3V3 pins = U101 4 + U102 4 + U103 VCCA 2 + U104 VCCA 1 + U105 1 + U106 1
    # + U107 1 + U108 VDD 1 + U109 VDD 1 = 16, plus 1 bulk; +5V_BUS pins = U103 VCCB 2 + U104 VCCB 2 = 4, plus 1 bulk
    check(n3 == 17, f"+3V3 decoupling count {n3} (expected 16x100n + 1x10u = 17)")
    check(n5 == 5, f"+5V_BUS decoupling count {n5} (expected 4x100n + 1x10u = 5)")
    for rail, pins in (("+3V3", 16), ("+5V_BUS", 4)):
        ic_pins = sum(1 for r, p, t in nets.get(rail, []) if r.startswith("U") and t == "power_in")
        check(ic_pins == pins, f"{rail}: {ic_pins} IC supply pins (expected {pins})")

    # ---- test points ---------------------------------------------------------------------------
    tp_expect = ["Z_AS_N", "Z_SLAVE_N", "Z_DOE", "Z_E7M", "Z_READ", "Z_UDS_N", "Z_LDS_N", "Z_CFGIN_N",
                 "Z_CFGOUT_N", "Z_INT2_N", "Z_XRDY", "Z_BUSRST_N", "Z_BERR_N", "ZB_AS_N", "ZF_SLAVE_N", "GND", "GND",
                 "CARD_EN_N", "EN_OK"]
    for i, want in enumerate(tp_expect):
        ref = f"TP{101 + i}"
        check(net_of(ref, "1") == want, f"{ref} expected on {want}, got {net_of(ref, '1')}")

    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
