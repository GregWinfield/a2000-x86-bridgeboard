# SPDX-License-Identifier: MIT
"""Audit sheet-2 connectivity (FPGA and configuration) in a KiCad netlist against the design intent.

usage: python -I tools/kicad/audit_sheet2.py <netlist.net>

The expected connections come from sources that do not depend on the schematic generator:
  * the Lattice MachXO2-2000 pinout file (tools/fpga/, S63): every one of the 144 package pins is
    classified (power, ground, NC, configuration/JTAG, signal, spare) and checked;
  * the pin plan (tools/fpga/pinplan.py) AND the LOCATE constraints Diamond actually used
    (hdl/syn/z2_top.lpf + hdl/syn/fit_top_extra.lpf): plan, LPF and schematic must agree pin by pin;
  * the HDL port directions of the 102-signal fit top (hdl/syn/fit_top.v), checked against the other
    pins on each net (an FPGA input needs exactly one external driver; an FPGA output must have none);
  * the MachXO2 Hardware Checklist FPGA-TN-02154-2.2 (S64): configuration and JTAG pull resistors
    (Table 6.1, Figure 6.1), decoupling (Table 3.1), oscillator supply filter (Figure 13.1).
Every check prints FAIL on failure; exit code 1 on any failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools" / "fpga"))
import netlist                                   # noqa: E402
import pinplan                                   # noqa: E402
from sheet2 import all_pins, net_name            # noqa: E402

fails = 0
checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


CONFIG = {"PROGRAMN": "FPGA_PROGRAMN", "INITN": "FPGA_INITN", "DONE": "FPGA_DONE", "JTAGENB": "FPGA_JTAGENB",
          "TMS": "FPGA_TMS", "TCK": "FPGA_TCK", "TDI": "FPGA_TDI", "TDO": "FPGA_TDO"}
DRIVER_TYPES = {"output", "tri_state", "open_collector", "open_emitter", "power_out", "bidirectional"}
OPEN_NETS_PREFIX = ("I2C_", "INA_", "X4_", "LED_", "DIP_", "DBG")             # sheets 5-6, not yet drawn


def hdl_directions(path: Path):
    """{port[bit] or port: 'in'|'out'|'inout'} from the module port list."""
    out = {}
    for m in re.finditer(r"^[ \t]*(input|output|inout)[ \t]+wire[ \t]*(\[(\d+):(\d+)\])?[ \t]*([^;/\n]*)", path.read_text(encoding="utf-8"), re.M):
        d = {"input": "in", "output": "out", "inout": "inout"}[m.group(1)]
        for name in [n.strip() for n in m.group(5).split(",") if n.strip()]:
            if m.group(2):
                hi, lo = int(m.group(3)), int(m.group(4))
                for i in range(min(hi, lo), max(hi, lo) + 1):
                    out[f"{name}[{i}]"] = d
            else:
                out[name] = d
    return out


def lpf_locates(*paths: Path):
    loc = {}
    for p in paths:
        for m in re.finditer(r'^LOCATE COMP "([^"]+)" SITE "(\d+)" ;', p.read_text(encoding="utf-8"), re.M):
            check(m.group(1) not in loc, f"LPF: {m.group(1)} located twice")
            loc[m.group(1)] = int(m.group(2))
    return loc


def main(path):
    comps, raw_nets = netlist.load(Path(path))
    nets, full = {}, {}
    for name, nodes in raw_nets.items():
        leaf = name.rsplit("/", 1)[-1] if name.startswith("/") else name
        check(leaf not in nets, f"net name {leaf} appears on two sheets: {full.get(leaf)} and {name}")
        nets[leaf], full[leaf] = nodes, name
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p, _ in nodes}

    def net_of(ref, pin):
        return pin_net.get((ref, str(pin)))

    def members(net):
        return sorted((r, p) for r, p, _ in nets.get(net, []))

    def unconnected(ref, pin):
        n = net_of(ref, pin)
        return n is None or n.startswith("unconnected-") or len(nets.get(n, [])) == 1

    def two_pin(ref, value, a, b):
        c = comps.get(ref)
        check(c is not None, f"{ref} present")
        if c:
            check(c["value"] == value, f"{ref} value {c['value']} (want {value})")
            check({net_of(ref, "1"), net_of(ref, "2")} == {a, b}, f"{ref} between {a} and {b}: {net_of(ref, '1')}, {net_of(ref, '2')}")

    # ---------------------------------------------------------------- U201: part
    u = comps.get("U201")
    check(u is not None, "U201 present")
    if u:
        check(u["value"] == "LCMXO2-2000HC-4TG144C", f"U201 value {u['value']}")
        check(u["footprint"] == "Package_QFP:TQFP-144_20x20mm_P0.5mm", f"U201 footprint {u['footprint']}")
        check(u["fields"].get("MPN") == "LCMXO2-2000HC-4TG144C", "U201 MPN field")

    # ---------------------------------------------------------------- every package pin
    tab = all_pins()                                  # {pin: (function, bank, dual function)}
    check(sorted(tab) == list(range(1, 145)), "pinout file lists pins 1-144")
    assign, usable, spare, errors = pinplan.compute(REPO)
    check(not errors, f"pin plan errors: {errors}")
    mig, _ = pinplan.migration(REPO, assign)
    check(not mig, f"LCMXO2-4000HC fallback problems: {mig}")
    by_pin = {p: s for s, p in assign.items()}
    classes = {}
    for p, (fn, bank, dfn) in sorted(tab.items()):
        cfg = [k for k in CONFIG if k in re.split(r"[/ ]", dfn)]
        if fn == "VCC" or fn.startswith("VCCIO"):
            classes[p] = "power"
            check(net_of("U201", p) == "+3V3", f"U201.{p} ({fn}) on +3V3, got {net_of('U201', p)}")
        elif fn == "GND":
            classes[p] = "gnd"
            check(net_of("U201", p) == "GND", f"U201.{p} GND, got {net_of('U201', p)}")
        elif fn == "NC":
            classes[p] = "nc"
            check(unconnected("U201", p), f"U201.{p} (NC) unconnected, got {net_of('U201', p)}")
        elif cfg:
            classes[p] = "config"
            check(p not in by_pin, f"U201.{p} ({cfg[0]}) carries no plan signal")
            check(net_of("U201", p) == CONFIG[cfg[0]], f"U201.{p} ({cfg[0]}) on {CONFIG[cfg[0]]}, got {net_of('U201', p)}")
        elif p in by_pin:
            classes[p] = "signal"
            check(net_of("U201", p) == net_name(by_pin[p]), f"U201.{p} ({fn}) on {net_name(by_pin[p])}, got {net_of('U201', p)}")
        else:
            classes[p] = "spare"
            check(unconnected("U201", p), f"U201.{p} (spare {fn}) unconnected, got {net_of('U201', p)}")
    count = {k: sum(1 for v in classes.values() if v == k) for k in ("power", "gnd", "nc", "config", "signal", "spare")}
    check(count == {"power": 16, "gnd": 12, "nc": 4, "config": 8, "signal": 101, "spare": 3},
          f"pin classes {count} (want 16 supply, 12 GND, 4 NC, 8 configuration/JTAG, 101 signals, 3 spare)")
    check(sorted(p for p, c in classes.items() if c == "spare") == [23, 24, 67], "spare pins are 23, 24 and 67 (C-26)")
    check(by_pin.get(65) == "LED_READY" and net_of("U201", 65) == "LED_READY", "LED_READY on pin 65 (C-26: the one FPGA LED)")
    check("LED_FAULT" not in nets, "no LED_FAULT net (C-26: FAULT LED on the RP2040)")
    # documented pin numbers of the configuration functions (sheet notes, LPF PROHIBIT)
    cfg_pins = {k: [p for p, v in tab.items() if k in re.split(r"[/ ]", v[2])] for k in CONFIG}
    check(cfg_pins == {"PROGRAMN": [119], "INITN": [110], "DONE": [109], "JTAGENB": [120], "TMS": [130], "TCK": [131],
                       "TDI": [136], "TDO": [137]}, f"configuration pins {cfg_pins}")
    sn = [p for p, v in tab.items() if v[2] == "SN"]
    check(sn == [70] and by_pin.get(70) == "SA[17]", f"SN pad {sn} carries SA[17]: {by_pin.get(70)}")
    check(tab[128][2] == "PCLKT0_1" and by_pin.get(128) == "clk_core", "clk_core on PCLKT0_1 (pin 128)")
    check(by_pin.get(125) == "I2C_SDA" and "SDA" in tab[125][2], "I2C_SDA on the primary SDA pin (125)")
    check(by_pin.get(126) == "I2C_SCL" and "SCL" in tab[126][2], "I2C_SCL on the primary SCL pin (126)")

    # ---------------------------------------------------------------- LPF agreement (what Diamond placed)
    lpf = REPO / "hdl/syn/z2_top.lpf"
    loc = lpf_locates(lpf, REPO / "hdl/syn/fit_top_extra.lpf")
    check(set(loc) == set(assign), f"LPF LOCATEs vs plan: missing {sorted(set(assign) - set(loc))}, extra {sorted(set(loc) - set(assign))}")
    for sig, p in sorted(loc.items(), key=lambda t: t[1]):
        check(p == assign.get(sig), f"LPF {sig} SITE {p}, plan {assign.get(sig)}")
        check(net_of("U201", p) == net_name(sig), f"LPF {sig} SITE {p}: schematic net {net_of('U201', p)}")
    lt = lpf.read_text(encoding="utf-8")
    check("IOBUF ALLPORTS IO_TYPE=LVCMOS33" in lt, "LPF: all ports LVCMOS33 (every VCCIO at 3.3 V)")
    check('PROHIBIT SITE "120" ;' in lt, "LPF: JTAGENB (120) prohibited")
    check("SDM_PORT=PROGRAMN_DONE_INITN" in lt and "JTAG_PORT=ENABLE" in lt, "LPF: SYSCONFIG keeps PROGRAMN/INITN/DONE and JTAG")

    # ---------------------------------------------------------------- HDL directions vs the other pins on each net
    dirs = hdl_directions(REPO / "hdl/syn/fit_top.v")
    check(set(dirs) == set(assign), f"fit_top ports vs plan: missing {sorted(set(assign) - set(dirs))}, extra {sorted(set(dirs) - set(assign))}")
    open_nets = []
    for sig, p in sorted(assign.items(), key=lambda t: t[1]):
        net = net_name(sig)
        ext = [(r, q, t) for r, q, t in nets.get(net, []) if r != "U201"]
        drivers = [(r, q, t) for r, q, t in ext if t in DRIVER_TYPES]
        d = dirs.get(sig)
        if net.startswith(OPEN_NETS_PREFIX):
            open_nets.append(net)
            check(not ext, f"{net}: sheet 5-6 net expected open until drawn, has {ext}")
            continue
        if net == "CLK_50M":
            check(sorted((r, q) for r, q, _ in ext) == [("R209", "2"), ("TP204", "1")], f"CLK_50M members {ext}")
            continue
        sheet_refs = {m.group(1) for m in (re.match(r"[A-Z]+(\d)\d\d$", r) for r, _, _ in ext) if m}
        want = ({"1"} if net.startswith(("ZB_", "ZF_", "EN_OK")) else {"3"} if net.startswith(("SA", "SRAM_"))
                else {"4"} if net.startswith("RP_") else {"1", "3"})
        check(want <= sheet_refs, f"{net}: reaches sheet(s) {sorted(want)}; members {ext}")
        if d == "in":
            oc = [x for x in drivers if x[2] == "open_collector"]
            if oc:   # wired-AND input: open-drain drivers plus a pull-up resistor
                check(len(oc) == len(drivers) and any(r.startswith("R") for r, _, _ in ext), f"{net}: open-drain drivers need a pull-up: {ext}")
            else:
                check(len(drivers) == 1, f"{net}: FPGA input needs exactly one external driver, has {drivers}")
        elif d == "out":
            check(not [x for x in drivers if x[2] != "bidirectional"], f"{net}: FPGA output contends with {drivers}")
            check(any(t in ("input", "bidirectional") for _, _, t in ext), f"{net}: FPGA output has no load: {ext}")
        elif d == "inout":
            check(all(t in ("bidirectional", "passive") for _, _, t in ext), f"{net}: bidirectional bus members {ext}")
    check(len(open_nets) == 14, f"open sheet 5-6 signal nets: {len(open_nets)} (want 14, see the ERC report)")
    for net in ("ZF_OVR_N", "ZF_DTACK_N"):         # owner decision C-17: not FPGA pins
        check(not [x for x in members(net) if x[0] == "U201"], f"{net} has no FPGA pin (C-17)")

    # ---------------------------------------------------------------- configuration and JTAG (Table 6.1, Figure 6.1)
    for ref, val, net, rail in (("R201", "4.7k", "FPGA_PROGRAMN", "+3V3"), ("R202", "4.7k", "FPGA_INITN", "+3V3"),
                                ("R203", "4.7k", "FPGA_DONE", "+3V3"), ("R204", "1k", "FPGA_JTAGENB", "+3V3"),
                                ("R205", "4.7k", "FPGA_TCK", "GND"), ("R206", "4.7k", "FPGA_TMS", "+3V3"),
                                ("R207", "4.7k", "FPGA_TDI", "+3V3"), ("R210", "4.7k", "FPGA_TDO", "+3V3"),
                                ("R208", "4.7k", "SA17", "+3V3")):
        two_pin(ref, val, net, rail)
    want = {"FPGA_PROGRAMN": [("R201", "2"), ("TP201", "1"), ("U201", "119")],
            "FPGA_INITN": [("R202", "2"), ("TP202", "1"), ("U201", "110")],
            "FPGA_DONE": [("R203", "2"), ("TP203", "1"), ("U201", "109")],
            "FPGA_JTAGENB": [("R204", "2"), ("U201", "120")],
            "FPGA_TCK": [("J201", "3"), ("R205", "1"), ("U201", "131"), ("U403", "3")],     # U403: sheet-4 JTAG option
            "FPGA_TDO": [("J201", "4"), ("R210", "2"), ("U201", "137"), ("U402", "6")],     # U402 A4 (S4-6)
            "FPGA_TDI": [("J201", "5"), ("R207", "2"), ("U201", "136"), ("U403", "5")],
            "FPGA_TMS": [("J201", "6"), ("R206", "2"), ("U201", "130"), ("U403", "4")]}
    for net, m in want.items():
        check(members(net) == sorted(m), f"{net} members {members(net)}")
    j = comps.get("J201")
    check(j is not None and j["footprint"] == "Connector_Molex:Molex_KK-254_AE-6410-06A_1x06_P2.54mm_Vertical",
          "J201 polarized 1x6 KK 254 header (owner refinement 3)")
    check(j is not None and "pin-1 marker" in j["fields"].get("Silkscreen", ""), "J201 silkscreen requirement recorded")
    for pin, net in (("1", "+3V3"), ("2", "GND"), ("3", "FPGA_TCK"), ("4", "FPGA_TDO"), ("5", "FPGA_TDI"), ("6", "FPGA_TMS")):
        check(net_of("J201", pin) == net, f"J201.{pin} on {net}, got {net_of('J201', pin)}")

    # ---------------------------------------------------------------- decoupling (Table 3.1)
    n_supply = sum(1 for v in tab.values() if v[0] == "VCC" or v[0].startswith("VCCIO"))
    n_banks = len({v[0] for v in tab.values() if v[0].startswith("VCCIO")})
    c100 = [r for r in comps if re.match(r"C2\d\d$", r) and comps[r]["value"] == "100n" and r != "C225"]
    c10 = [r for r in comps if re.match(r"C2\d\d$", r) and comps[r]["value"] == "10u"]
    check(len(c100) == n_supply == 16, f"FPGA 100 nF capacitors {len(c100)}, supply pins {n_supply}")
    check(len(c10) == 2 + n_banks == 8, f"FPGA 10 uF capacitors {len(c10)} (2 VCC + {n_banks} VCCIO banks)")
    for r in c100 + c10:
        check({net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"}, f"{r} between +3V3 and GND")
        fp = "Capacitor_SMD:C_0603_1608Metric" if comps[r]["value"] == "100n" else "Capacitor_SMD:C_0805_2012Metric"
        check(comps[r]["footprint"] == fp, f"{r} footprint {comps[r]['footprint']}")

    # ---------------------------------------------------------------- oscillator (Figure 13.1) and clock
    x = comps.get("X201")
    check(x is not None and x["value"] == "ECS-2520MV-500-BN-TR" and x["fields"].get("MPN") == "ECS-2520MV-500-BN-TR", "X201 part")
    check(x is not None and x["footprint"] == "Oscillator:Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm", "X201 footprint")
    for pin, net in (("1", "VDD_OSC"), ("2", "GND"), ("4", "VDD_OSC")):
        check(net_of("X201", pin) == net, f"X201.{pin} on {net}, got {net_of('X201', pin)}")
    check(net_of("X201", "3") is not None and net_of("X201", "3") == net_of("R209", "1"), "X201.3 (OUT) to R209")
    check(members(net_of("X201", "3")) == [("R209", "1"), ("X201", "3")], f"oscillator output net {members(net_of('X201', '3'))}")
    two_pin("R209", "33R", net_of("X201", "3"), "CLK_50M")
    two_pin("FB201", "600R@100MHz", "+3V3", "VDD_OSC")
    two_pin("C225", "100n", "VDD_OSC", "GND")
    two_pin("C226", "1u", "VDD_OSC", "GND")
    check(members("VDD_OSC") == sorted([("FB201", "2"), ("X201", "1"), ("X201", "4"), ("C225", "1"), ("C226", "1")]),
          f"VDD_OSC members {members('VDD_OSC')}")
    check(net_of("U201", 128) == "CLK_50M", "U201.128 (PCLKT0_1) on CLK_50M")

    # ---------------------------------------------------------------- test points
    for ref, net in (("TP201", "FPGA_PROGRAMN"), ("TP202", "FPGA_INITN"), ("TP203", "FPGA_DONE"), ("TP204", "CLK_50M"),
                     ("TP205", "GND")):
        check(net_of(ref, "1") == net, f"{ref} on {net}, got {net_of(ref, '1')}")

    # ---------------------------------------------------------------- nothing else on sheet 2
    known = ({"U201", "X201", "J201", "FB201"} | {f"R{n}" for n in range(201, 211)} | {f"C{n}" for n in range(201, 227)}
             | {f"TP{n}" for n in range(201, 206)})
    present = {r for r in comps if re.match(r"[A-Z]+2\d\d$", r)}
    check(present == known, f"sheet-2 parts: missing {sorted(known - present)}, unexpected {sorted(present - known)}")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
