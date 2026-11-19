# SPDX-License-Identifier: MIT
"""FPGA pin assignment for sheet 2 (LCMXO2-2000HC-4TG144), generated from the Lattice pinout file.

usage: python -I tools/fpga/pinplan.py <repo>

Inputs : tools/fpga/MachXO2-2000_TQFP144_pins.csv (facts-only extract of Lattice document 42568 rev 1.2, S63) and the PLAN below;
         tools/fpga/MachXO2-4000_TQFP144_pins.csv (extract of Lattice document 42571 rev 1.5, S63) for the fallback check.
Outputs: the LOCATE block in hdl/syn/z2_top.lpf (between the generated markers),
         hdl/syn/fit_top_extra.lpf (pins that exist only in the fit test until sheets 4-6 are drawn),
         docs/stage2/sheet2-pin-assignment.md (the pin table).
Rules checked here (sheet-3 notes section 8.1, Hardware Checklist FPGA-TN-02154, S64):
  * no signal on PROGRAMN, INITN, DONE (configuration), TMS/TCK/TDI/TDO (JTAG) or JTAGENB (C-19);
  * SN carries an FPGA output only (it must not be driven low while the device is erased);
  * clk_core on a PCLK input; I2C on the primary I2C pins (SCL/SDA);
  * every pad used at most once; every signal placed in the bank the plan names;
  * fallback (owner decision C-17): on the LCMXO2-4000HC TQFP144 every assigned pin is an I/O pad in the
    same bank, and the reserved, SN, clock and I2C functions sit on the same package pins;
  * freeze: no pin may differ from the G-SHEET2-approved assignment (tools/fpga/pins_gsheet2.csv) except
    the deliberate changes listed in CHANGES, each with its owner decision.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

RESERVED = {"DONE", "INITN", "PROGRAMN", "JTAGENB", "TMS", "TCK", "TDI", "TDO"}

# Deliberate changes since the G-SHEET2 approval (old signal: (new signal or None if removed, decision))
CHANGES = {"LED[0]": ("LED_READY", "C-26: the one FPGA LED, renamed"),
           "LED[1]": (None, "C-26 (option C-17b): FAULT LED moved to the RP2040; pin 67 freed")}
# Authorised pin moves since the G-SHEET2 approval (signal: (new pin, decision)). Each is an owner-approved
# exception to the freeze; the freeze check accepts exactly these pins and nothing else.
MOVES = {"RP_SCK": (5, "S4-3: SCK-clocked SPI slave needs a primary-clock input: PCLKT5_0"),
         "RP_IRQ_N": (1, "S4-3: swapped with RP_SCK")}
# Pads kept free on purpose (not given to any signal by the automatic assignment)
KEEP_FREE = {67: "freed by C-26 (option C-17b); spare"}

# (signal, direction, bank, preferred pin or None, group). Order within a bank = pad order.
PLAN = []
def add(bank, names, direction, group, pins=None):
    for i, n in enumerate(names):
        PLAN.append((n, direction, bank, pins[i] if pins else None, group))

# bank 0 (top): clock, I2C on the primary I2C pins, X4 power/status, remaining Zorro control
add("0", ["clk_core"], "in", "clock", [128])                            # PCLKT0_1
add("0", ["I2C_SDA", "I2C_SCL"], "bidir", "telemetry (sheet 5)", [125, 126])   # SDA/PCLKC0_0, SCL/PCLKT0_0
add("0", ["INA_ALERT_N", "X4_PWR_EN", "X4_PWR_FLT_N", "X4_S0_SENSE"], "mixed", "power/status (sheet 5)")
add("0", [f"ZB_A[{i}]" for i in range(10, 16)] + ["ZB_E7M", "ZB_BUSRST_N"], "in", "Zorro inputs")
add("0", ["ZF_INT2_N", "ZF_INT6_N", "ZF_DBUF_DIR", "ZF_ARM", "EN_OK"], "mixed", "Zorro control")
# bank 1 (right): the whole /SLAVEn, XRDY and buffer-enable decode group, then A1-A9
add("1", [f"ZB_A[{i}]" for i in range(16, 24)] + ["ZB_AS_N", "ZB_BERR_N", "ZB_DOE", "ZB_READ", "ZB_UDS_N", "ZB_LDS_N", "ZB_CFGIN_N"],
    "in", "Zorro decode inputs (C-01/C-02 paths)")
add("1", ["ZF_SLAVE_N", "ZF_XRDY", "ZF_DBUF_OE_N", "ZF_CFGOUT_N"], "out", "Zorro decode outputs")
add("1", [f"ZB_A[{i}]" for i in range(1, 10)], "in", "Zorro inputs")
# bank 2 (bottom): SRAM address/control (SN gets SA17, an output), LEDs, DIP switches
add("2", ["SA[17]"], "out", "SRAM (sheet 3)", [70])                     # SN: output only
add("2", [f"SA[{i}]" for i in range(0, 17)] + ["SRAM_CE_N", "SRAM_OE_N", "SRAM_WE_N", "SRAM_UB_N", "SRAM_LB_N"], "out", "SRAM (sheet 3)")
add("2", ["LED_READY"], "out", "LED (READY; C-26: the other diagnostic LEDs are on the RP2040)")
add("2", ["DIP_MODE_B", "DIP_INT6", "DIP_DISABLE"], "in", "DIP switches (sheet 6)")
# banks 3 and 4 (left, lower): local data bus
add("3", [f"LD[{i}]" for i in range(0, 8)], "bidir", "local bus LD (sheets 1, 3)")
add("4", [f"LD[{i}]" for i in range(8, 16)], "bidir", "local bus LD (sheets 1, 3)")
# bank 5 (left, upper): RP2040 host link and the debug header
add("5", ["RP_SCK", "RP_CS_N", "RP_MOSI", "RP_MISO", "RP_IRQ_N", "RP_ATTN"], "mixed", "host link (sheet 4)",
    [5, 2, 3, 4, 1, 6])                                                      # S4-3: SCK on PCLKT5_0
add("5", [f"DBG[{i}]" for i in range(4)], "bidir", "debug header (sheet 6)")

Z2_TOP_PORTS_ABSENT = {"I2C_SDA", "I2C_SCL", "INA_ALERT_N", "X4_PWR_EN", "X4_PWR_FLT_N", "X4_S0_SENSE",
                       "DBG[0]", "DBG[1]", "DBG[2]", "DBG[3]"}          # sheet 4: the RP_* SPI ports are in z2_top
Z2_TOP_UNUSED = {"ZB_E7M"}       # in z2_top but removed by synthesis (no load): LOCATE only in the fit test


def load_pads(csv_path):
    rows = list(csv.reader(open(csv_path, encoding="utf-8", errors="replace")))
    h = next(i for i, r in enumerate(rows) if r and r[0] == "PAD")
    hdr = rows[h]
    pads = {}
    for r in rows[h + 1:]:
        if not r or not r[0].strip():
            continue
        d = dict(zip(hdr, r))
        if d.get("TQFP144", "-") in ("-", "") or not re.match(r"P[LRTB]\d", d["Pin/Ball Function"]):
            continue
        pads[int(d["TQFP144"])] = (d["Bank"], d["Pin/Ball Function"], d["Dual Function"])
    return pads


def migration(repo: Path, assign):
    """Problems moving this assignment to the LCMXO2-4000HC-4TG144 (empty list = pin-compatible)."""
    a = load_pads(repo / "tools/fpga/MachXO2-2000_TQFP144_pins.csv")
    b = load_pads(repo / "tools/fpga/MachXO2-4000_TQFP144_pins.csv")
    probs = []
    for name, pin in sorted(assign.items(), key=lambda t: t[1]):
        if pin not in b:
            probs.append(f"{name}: pin {pin} is not an I/O pad on the 4000")
        elif b[pin][0] != a[pin][0]:
            probs.append(f"{name}: pin {pin} bank {a[pin][0]} on the 2000, {b[pin][0]} on the 4000")
    for fn in sorted(RESERVED | {"SN", "PCLKT0_1", "SDA", "SCL"}):
        pa = sorted(q for q, v in a.items() if fn in re.split(r"[/ ]", v[2]))
        pb = sorted(q for q, v in b.items() if fn in re.split(r"[/ ]", v[2]))
        if pa != pb:
            probs.append(f"{fn}: pins {pa} on the 2000, {pb} on the 4000")
    return probs, b


def compute(repo: Path):
    """Assign every PLAN signal to a pad. Returns (assign {signal: pin}, usable pads, spare {bank: [pins]}, errors)."""
    pads = load_pads(repo / "tools/fpga/MachXO2-2000_TQFP144_pins.csv")
    usable = {p: v for p, v in pads.items() if not (set(re.split(r"[/ ]", v[2])) & RESERVED)}
    free = {b: sorted(p for p, v in usable.items() if v[0] == b and p not in KEEP_FREE) for b in "012345"}
    errors, assign = [], {}
    for name, direction, bank, pin, group in PLAN:       # fixed pins first
        if pin is not None:
            if pin not in usable or usable[pin][0] != bank:
                errors.append(f"{name}: pin {pin} not usable in bank {bank}")
            elif pin in assign.values():
                errors.append(f"{name}: pin {pin} already used")
            else:
                assign[name] = pin
                free[bank].remove(pin)
    for name, direction, bank, pin, group in PLAN:
        if pin is None:
            # SN is an output-only pad: never give it to an input
            cand = [p for p in free[bank] if not ("SN" == usable[p][2] and direction != "out")]
            if not cand:
                errors.append(f"{name}: bank {bank} full")
                continue
            assign[name] = cand[0]
            free[bank].remove(cand[0])
    for name, direction, bank, pin, group in PLAN:      # rule checks
        p = assign.get(name)
        if p is None:
            continue
        if usable[p][2] == "SN" and direction != "out":
            errors.append(f"{name} on SN must be an output")
        if name == "clk_core" and "PCLK" not in usable[p][2]:
            errors.append("clk_core not on a PCLK pin")
        if name == "RP_SCK" and not usable[p][2].startswith("PCLKT"):
            errors.append("RP_SCK (SPI slave clock, S4-1) not on a PCLKT pin")
    if len(set(assign.values())) != len(assign):
        errors.append("a pad is used twice")
    for pin in KEEP_FREE:                             # kept-free pads are spare pads
        free[usable[pin][0]] = sorted(free[usable[pin][0]] + [pin])
    errors += freeze_check(repo, assign)
    return assign, usable, {b: free[b] for b in free if free[b]}, errors


def freeze_check(repo: Path, assign):
    """Differences from the G-SHEET2-approved assignment that CHANGES does not explain."""
    import csv
    rows = [r for r in csv.reader(open(repo / "tools/fpga/pins_gsheet2.csv", encoding="utf-8")) if r and not r[0].startswith("#")]
    base = {r[0]: int(r[1]) for r in rows[1:]}
    errs = []
    expected = {}
    for sig, pin in base.items():
        new, _ = CHANGES.get(sig, (sig, ""))
        if new is None:
            if pin in assign.values():
                errs.append(f"freeze: {sig} was removed, but its pin {pin} is used again")
        else:
            expected[new] = MOVES.get(new, (pin, ""))[0]
    for sig, pin in expected.items():
        if assign.get(sig) != pin:
            errs.append(f"freeze: {sig} on pin {assign.get(sig)}, approved pin {pin}")
    for sig in assign:
        if sig not in expected:
            errs.append(f"freeze: {sig} is new since G-SHEET2 and not in CHANGES")
    return errs


def main(repo: Path):
    assign, usable, spare, errors = compute(repo)
    n_sig = len(PLAN)
    print(f"signals {n_sig}, placed {len(assign)}, spare pads {sum(len(v) for v in spare.values())}: {spare}")
    if errors:
        print("ERRORS:", *errors, sep="\n  ")
        return 1
    mig, pads4 = migration(repo, assign)
    print(f"LCMXO2-4000HC fallback: {len(mig)} problems", *mig, sep="\n  ")
    if mig:
        return 1

    # ---- LPF blocks
    def loc(name):
        return f'LOCATE COMP "{name}" SITE "{assign[name]}" ;'
    z2 = [loc(n) for n, *_ in PLAN if n not in Z2_TOP_PORTS_ABSENT and n not in Z2_TOP_UNUSED]
    fit = [loc(n) for n, *_ in PLAN if n in Z2_TOP_PORTS_ABSENT or n in Z2_TOP_UNUSED]
    lpf = repo / "hdl/syn/z2_top.lpf"
    s = lpf.read_text(encoding="utf-8")
    begin, end = "# ---------------- BEGIN PIN LOCATES (generated by tools/fpga/pinplan.py; sheet 2)", "# ---------------- END PIN LOCATES"
    block = begin + "\n" + "\n".join(z2) + "\n" + end
    if begin in s:
        s = s[:s.index(begin)] + block + s[s.index(end) + len(end):]
    else:
        s = s.rstrip("\n") + "\n\n" + block + "\n"
    lpf.write_text(s, encoding="utf-8")
    (repo / "hdl/syn/fit_top_extra.lpf").write_text(
        "# SPDX-License-Identifier: MIT\n# Pin LOCATEs for ports that exist only in the fit test (sheets 4-6 not yet drawn) and for ZB_E7M\n"
        "# (unused in z2_top). Generated by tools/fpga/pinplan.py; appended by run_diamond.sh when Z2_TOP=fit_top.\n"
        + "\n".join(fit) + "\n", encoding="utf-8")

    # ---- documentation table
    md = ["# Sheet 2: FPGA pin assignment (LCMXO2-2000HC-4TG144, revision A)", "",
          "Generated by `tools/fpga/pinplan.py` from the Lattice pinout data (facts-only extract of the MachXO2-2000 Pinout rev 1.2, [V S63]) and the plan in that script.",
          "", "- Every bank runs at VCCIO 3.3 V, and every port is LVCMOS33 (`z2_top.lpf`).",
          "- **Reserved, no signal:** PROGRAMN 119, INITN 110, DONE 109 (configuration, `SDM_PORT`); TMS 130, TCK 131, TDI 136, TDO 137 (JTAG); JTAGENB 120 (C-19).",
          f"- **Signals:** {n_sig}. **Spare pads:** {sum(len(v) for v in spare.values())} " + ", ".join(f"bank {b}: {', '.join(map(str, v))}" for b, v in spare.items()) + ".",
          "- **S4-3, owner approval 2026-11-19 (authorised exception to the freeze):** RP_SCK moved from pin 1 to pin 5 "
          "(PCLKT5_0, primary-clock input for the SCK-clocked SPI slave); RP_IRQ_N moved from pin 5 to pin 1.",
          "- **C-26 (option C-17b), owner approval 2026-11-19:** the FAULT LED moved to the RP2040, so pin 67 is spare. "
          "Every other pin is unchanged from the G-SHEET2-approved assignment (`tools/fpga/pins_gsheet2.csv`; `pinplan.py` fails on any other difference).",
          "- **Fallback LCMXO2-4000HC-4TG144C** (owner decision C-17), checked against the MachXO2-4000 pinout rev 1.5 [V S63]:",
          "  every assigned pin is an I/O pad in the same bank, and PROGRAMN, INITN, DONE, JTAGENB, TMS, TCK, TDI, TDO, SN,",
          "  PCLKT0_1, SDA and SCL are the same package pins. The pad names differ (column *4000 pad*); the LPF uses pin numbers.",
          "  On the 4000, the 2000's NC pins 31, 63 and 103 are I/O pads; they stay unconnected.", "",
          "| Pin | Bank | Pad | Dual function | Signal | Dir | Group | 4000 pad |", "|---|---|---|---|---|---|---|---|"]
    for name, direction, bank, pin, group in sorted(PLAN, key=lambda t: assign[t[0]]):
        p = assign[name]
        md.append(f"| {p} | {usable[p][0]} | {usable[p][1]} | {usable[p][2] if usable[p][2] != '-' else ''} | `{name}` | {direction} | {group} | {pads4[p][1]} |")
    for b, v in spare.items():
        for p in v:
            md.append(f"| {p} | {b} | {usable[p][1]} | {usable[p][2] if usable[p][2] != '-' else ''} | *spare* | – | – | {pads4[p][1]} |")
    (repo / "docs/stage2/sheet2-pin-assignment.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("LPF LOCATEs:", len(z2), "z2_top +", len(fit), "fit-only; table written")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
