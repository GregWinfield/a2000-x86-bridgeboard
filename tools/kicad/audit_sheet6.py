# SPDX-License-Identifier: MIT
"""Netlist audit for sheet 6 (diagnostics, configuration switches, debug header).

usage: python -I tools/kicad/audit_sheet6.py <netlist from kicad-cli sch export netlist>

Checks every sheet-6 part, value, footprint and pin against the design (sheet6.py; owner decisions S6-1 to S6-5):
  - S6-1 LEDs: each LED fed from its source through its resistor only, cathode to GND; LED current 0.5-2.5 mA for
    Vf 1.8-2.2 V [K]; U404's four LED outputs within +/-12 mA each and 100 mA total [V S66]; READY from FPGA pin 65.
  - S6-2 DIP: positions 1-3 switch +3V3 through 1k to the FPGA pins with 10k pull-downs (OFF = 0, ON >= 2.0 V);
    position 4 switches RP_JTAG_EN_N to GND through 1k against R407 (ON <= 0.7 V, OFF = high).
  - S6-4 debug header: J601 reaches the FPGA only through U601 (SN74AVC4T774) and the series resistors; U601 VCCA = +3V3,
    VCCB = DBG_VREF; DBG_VREF fed from +3V3 only through F601 and D608 (cathode to the header); DIR straps (DBG0-2
    header -> FPGA, DBG3 FPGA -> header); pull-downs on both sides (R-51); a GND beside every signal pin.
  - S6-5: TP601 LED_READY, TP602 GND; U403's JTAG-option outputs through 330R (contention <= 12 mA).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist                                   # noqa: E402

fails = checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


MULT = {"k": 1e3, "M": 1e6, "R": 1.0, "": 1.0}


def ohms(s):
    m = re.match(r"^([\d.]+)([kMR]?)$", s or "")
    return float(m.group(1)) * MULT[m.group(2)] if m else None


R0603 = "Resistor_SMD:R_0603_1608Metric"
LEDS = {"D601": ("R601", "LED_READY", "1k", "GREEN"), "D602": ("R602", "LED_RP0", "1k", "GREEN"),
        "D603": ("R603", "LED_RP1", "1k", "GREEN"), "D604": ("R604", "LED_RP2", "1k", "YELLOW"),
        "D605": ("R605", "LED_RP3", "1k", "RED"), "D606": ("R606", "+3V3", "1k", "GREEN"),
        "D607": ("R607", "X4_12V", "10k", "AMBER")}
SRC_V = {"LED_READY": 3.465, "LED_RP0": 3.465, "LED_RP1": 3.465, "LED_RP2": 3.465, "LED_RP3": 3.465, "+3V3": 3.465,
         "X4_12V": 12.6}
SRC_VMIN = {"X4_12V": 11.4}
DIP_FPGA = {"DIP_MODE_B": ("U201", "68", "R608", "R612", "DIP1_SW", "8"),
            "DIP_INT6": ("U201", "69", "R609", "R613", "DIP2_SW", "7"),
            "DIP_DISABLE": ("U201", "71", "R610", "R614", "DIP3_SW", "6")}
DBG_FPGA_PIN = {0: "9", 1: "10", 2: "11", 3: "12"}
A_PIN = {0: "3", 1: "4", 2: "5", 3: "6"}
B_PIN = {0: "14", 1: "13", 2: "12", 3: "11"}
DIR_PIN = {0: "1", 1: "2", 2: "7", 3: "8"}
DIR_DEFAULT = {0: "GND", 1: "GND", 2: "GND", 3: "+3V3"}       # BA, BA, BA, AB
J601 = {"1": "DBG_VREF", "3": "DBG0_H", "5": "DBG1_H", "7": "DBG2_H", "9": "DBG3_H",
        "2": "GND", "4": "GND", "6": "GND", "8": "GND", "10": "GND"}


def main(path):
    comps, raw = netlist.load(Path(path))
    nets = {(n.rsplit("/", 1)[-1] if n.startswith("/") else n): v for n, v in raw.items()}
    pin_net = {(r, p): n for n, v in nets.items() for r, p, _ in v}

    def net_of(r, p):
        n = pin_net.get((r, str(p)))
        return None if n is None or n.startswith("unconnected-") else n

    def members(n):
        return sorted((r, p) for r, p, _ in nets.get(n, []))

    def two_pin(ref, value, n1, n2, fp=R0603):
        c = comps.get(ref)
        check(c is not None and c["value"] == value and (fp is None or c["footprint"] == fp),
              f"{ref}: {c and (c['value'], c['footprint'])} (want {value})")
        check(net_of(ref, "1") == n1 and net_of(ref, "2") == n2,
              f"{ref}: pin 1 {net_of(ref, '1')} (want {n1}), pin 2 {net_of(ref, '2')} (want {n2})")

    expected = set()
    # ---------------- S6-1 LEDs
    u404_total = 0.0
    for d, (r, src, rv, colour) in LEDS.items():
        expected |= {d, r}
        c = comps.get(d)
        check(c is not None and c["value"] == colour and c["footprint"] == "LED_SMD:LED_0603_1608Metric", f"{d} {colour} 0603 LED")
        rc = comps.get(r)
        check(rc is not None and rc["value"] == rv, f"{r} {rv}")
        check(net_of(r, "1") == src, f"{r} fed from {src}, got {net_of(r, '1')}")
        mid = net_of(r, "2")
        check(mid is not None and mid == net_of(d, "2") and members(mid) == sorted([(r, "2"), (d, "2")]),
              f"{d} anode only through {r}: {mid and members(mid)}")
        check(net_of(d, "1") == "GND", f"{d} cathode to GND")
        rohm = ohms(rc["value"]) if rc else None
        if rohm:
            i_max = (SRC_V[src] - 1.8) / rohm
            i_min = (SRC_VMIN.get(src, 3.135 - 0.1) - 2.2) / rohm      # 3.3 V sources: VCC min minus ~0.1 V output drop [E]
            check(0.5e-3 <= i_min and i_max <= 2.5e-3, f"{d} current {i_min * 1e3:.2f}-{i_max * 1e3:.2f} mA (want 0.5-2.5)")
            if src.startswith("LED_RP"):
                check(i_max <= 12e-3, f"{d}: U404 output {i_max * 1e3:.2f} mA <= 12 mA [V S66]")
                u404_total += i_max
    check(u404_total <= 100e-3, f"U404 LED current total {u404_total * 1e3:.2f} mA <= 100 mA (VCC/GND continuous [V S66])")
    check(set(members("LED_READY")) == {("U201", "65"), ("R601", "1"), ("TP601", "1")},
          f"LED_READY: FPGA pin 65 only (independent of the RP2040, C-26): {members('LED_READY')}")
    for k in range(4):
        n = f"LED_RP{k}"
        check(set(members(n)) == {("U404", str(3 + k)), (f"R{602 + k}", "1")}, f"{n}: U404 A output (carrier side) only: {members(n)}")
    check(("R607", "1") in members("X4_12V") and net_of("R607", "2") == net_of("D607", "2"), "X4-power LED on X4_12V")

    # ---------------- S6-2 DIP switch
    expected |= {"SW601"}
    c = comps.get("SW601")
    check(c is not None and c["value"] == "SW_DIP_x04" and "SW_DIP_SPSTx04" in c["footprint"], "SW601 4-position DIP")
    for p in ("1", "2", "3"):
        check(net_of("SW601", p) == "+3V3", f"SW601.{p} (positions 1-3) on +3V3")
    check(net_of("SW601", "4") == "GND", "SW601.4 (position 4) on GND")
    for net, (u, up, rs, rp, swnet, swpin) in DIP_FPGA.items():
        expected |= {rs, rp}
        check(net_of("SW601", swpin) == swnet, f"SW601.{swpin} on {swnet}")
        two_pin(rs, "1k", swnet, net)
        two_pin(rp, "10k", net, "GND")
        check(set(members(net)) == {(u, up), (rs, "2"), (rp, "1")}, f"{net}: FPGA pin {up}, series and pull-down only: {members(net)}")
        check(set(members(swnet)) == {("SW601", swpin), (rs, "1")}, f"{swnet} members")
        von = 3.135 * 10e3 / (10e3 + 1e3)
        check(von >= 2.0, f"{net} ON level {von:.2f} V >= VIH 2.0 V (LVCMOS33)")
    expected |= {"R611"}
    check(net_of("SW601", "5") == "DIP4_SW", "SW601.5 on DIP4_SW")
    two_pin("R611", "1k", "DIP4_SW", "RP_JTAG_EN_N")
    check(set(members("RP_JTAG_EN_N")) == {("U403", "9"), ("R407", "2"), ("R611", "2")},
          f"RP_JTAG_EN_N: U403 /OE, R407 pull-up (sheet 4), R611: {members('RP_JTAG_EN_N')}")
    check(net_of("R407", "1") == "+3V3" and comps.get("R407", {}).get("value") == "10k", "R407 10k to +3V3 (JTAG option off by default)")
    v4 = 3.465 * 1e3 / (1e3 + 10e3 * 0.99)
    check(v4 <= 0.7, f"SW601-4 ON level {v4:.2f} V <= U403 /OE VIL 0.7 V [V S66]")

    # ---------------- S6-4 debug header through U601
    expected |= {"U601", "J601", "F601", "D608", "C601", "C602", "C603"}
    c = comps.get("U601")
    check(c is not None and c["value"] == "SN74AVC4T774PWR", "U601 SN74AVC4T774PWR (Ioff, VCC isolation)")
    check(net_of("U601", "16") == "+3V3" and net_of("U601", "15") == "DBG_VREF" and net_of("U601", "10") == "GND",
          "U601 VCCA +3V3, VCCB DBG_VREF, GND")
    check(net_of("U601", "9") == "GND", "U601 OE low (enabled while both supplies are up)")
    for k in range(4):
        dbg = f"DBG{k}"
        ra, rp, rb, rpb, rd = f"R{619 + k}", f"R{623 + k}", f"R{627 + k}", f"R{631 + k}", f"R{615 + k}"
        expected |= {ra, rp, rb, rpb, rd}
        check(set(members(dbg)) == {("U201", DBG_FPGA_PIN[k]), (ra, "1"), (rp, "1")},
              f"{dbg}: FPGA pin {DBG_FPGA_PIN[k]}, series {ra}, pull-down {rp} only: {members(dbg)}")
        two_pin(ra, "330R", dbg, f"{dbg}_A")
        two_pin(rp, "100k", dbg, "GND")
        check(set(members(f"{dbg}_A")) == {(ra, "2"), ("U601", A_PIN[k])}, f"{dbg}_A: series resistor and U601 A only")
        check(net_of("U601", B_PIN[k]) == f"{dbg}_B", f"U601 B{k + 1} on {dbg}_B")
        two_pin(rb, "33R", f"{dbg}_B", f"{dbg}_H")
        two_pin(rpb, "100k", f"{dbg}_B", "GND")
        check(set(members(f"{dbg}_H")) == {(rb, "2"), ("J601", str(3 + 2 * k))}, f"{dbg}_H: header pin only through {rb}")
        dirnet = f"DBG_DIR{k + 1}"
        check(net_of("U601", DIR_PIN[k]) == dirnet, f"U601 DIR{k + 1} on {dirnet}")
        if DIR_DEFAULT[k] == "GND":
            two_pin(rd, "10k", dirnet, "GND")
        else:
            two_pin(rd, "10k", "+3V3", dirnet)
        i_cont = 3.6 / 330.0
        check(i_cont <= 12e-3, f"{ra}: FPGA/U601 contention <= {i_cont * 1e3:.1f} mA")
    for pn, net in J601.items():
        check(net_of("J601", pn) == net, f"J601.{pn} on {net}, got {net_of('J601', pn)}")
    check(comps.get("J601", {}).get("footprint") == "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical", "J601 keyed 2x5 box header")
    # header supply: +3V3 -> F601 -> D608 (anode) -> cathode DBG_VREF; nothing else joins DBG_VREF to a carrier rail
    two_pin("F601", "0.05A", "+3V3", "DBG_3V3_F", fp="Fuse:Fuse_1206_3216Metric")
    check(net_of("D608", "2") == "DBG_3V3_F" and net_of("D608", "1") == "DBG_VREF", "D608 anode DBG_3V3_F, cathode DBG_VREF")
    check(set(members("DBG_3V3_F")) == {("F601", "2"), ("D608", "2")}, "DBG_3V3_F: PTC and diode only")
    vref = {r for r, _ in members("DBG_VREF")}
    check(vref == {"D608", "U601", "C602", "C603", "J601"}, f"DBG_VREF members {sorted(vref)} (no path back to +3V3 except D608)")
    two_pin("C603", "1u", "DBG_VREF", "GND", fp=None)
    two_pin("C602", "100n", "DBG_VREF", "GND", fp=None)
    two_pin("C601", "100n", "+3V3", "GND", fp=None)
    # no sheet-6 connection from any J601 signal to an FPGA pin other than through U601
    for k in range(4):
        h = f"DBG{k}_H"
        check(not [m for m in members(h) if m[0] in ("U201", "U601")], f"{h} does not touch the FPGA or U601 directly")

    # ---------------- S6-5 test points; U403 contention resistors (sheet 4)
    expected |= {"TP601", "TP602"}
    check(net_of("TP601", "1") == "LED_READY" and net_of("TP602", "1") == "GND", "TP601 LED_READY, TP602 GND")
    for ref, net in (("R432", "FPGA_TCK"), ("R433", "FPGA_TMS"), ("R434", "FPGA_TDI")):
        c = comps.get(ref)
        check(c is not None and c["value"] == "330R" and net_of(ref, "1") == net, f"{ref} 330R to {net} (JTAG contention, S6-5)")
        check(3.6 / 330.0 <= 12e-3, f"{ref}: contention current <= 12 mA")

    present = {r for r in comps if re.match(r"[A-Z]+6\d\d$", r)}
    check(present == expected, f"sheet-6 parts: missing {sorted(expected - present)}, unexpected {sorted(present - expected)}")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
