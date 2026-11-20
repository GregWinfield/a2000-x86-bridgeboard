# SPDX-License-Identifier: MIT
"""Netlist audit for sheet 5 (power regulation and protection, X4 power control).

usage: python -I tools/kicad/audit_sheet5.py <netlist from kicad-cli sch export netlist>

Checks every sheet-5 part, value, footprint and pin net against the design (sheet5.py, proposal rev A1), and
re-derives the protection windows from the schematic's resistor values with tools/analysis/sheet5_power.py:
  - S5-2: U501 ILIM band from R506 (min >= 1.05 x 2.5 A, max <= 3.4 A); UVLO/OVLO windows contain 11.4-12.6 V;
    R1 >= 350 kOhm (TI ROC note 2); EN/UVLO and OVLO <= 6.5 V at the TVS clamp.
  - S5-6: U503 window contains 4.75-5.25 V and OVLO_max <= 6.1 V (< 6.5 V of the +5V_BUS loads); U504 is the 18 V TLV767.
  - S5-3/S5-9: the fail-safe enable chain (Q502 holds EN/UVLO low, biased from +12 V; only Q501 / X4_PWR_EN releases it);
    JP501 positions; R-51 pull-down on X4_PWR_EN.
  - S5-4 / C-28: INA226 at 0x44 (A1 = VS, A0 = GND); no other device on the I2C nets. C-29: every pull-up on an FPGA
    input or the I2C bus goes to +3V3.
  - S5-5: X4_S0_SENSE is a MOSFET drain with a +3V3 pull-up (active low); ER-3: <= 3.3 uA from X4_3V3_REF.
  - S5-8: J502 pin order = X4 J10 (1 GND, 2 +12 V); H501-H504 on GND; Zorro power pins unconnected.
  - Rails: +3V3 driven only by U504, +5V_BUS only by U503; total +3V3 capacitance <= 200 uF (TLV767 COUT <= 220 uF).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "analysis"))
import netlist                                   # noqa: E402
import sheet5_power as sp                        # noqa: E402

fails = checks = 0


def check(cond, msg):
    global fails, checks
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", msg)


MULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "R": 1.0, "k": 1e3, "M": 1e6}


def val(s):
    """'1.10k' -> 1100, '470u' -> 4.7e-4, '100R' -> 100, '10m' -> 0.01 (milliohm for the shunt)."""
    m = re.match(r"^([\d.]+)([pnumRkM]?)", s or "")
    if not m:
        return None
    return float(m.group(1)) * MULT.get(m.group(2), 1.0) if m.group(2) else float(m.group(1))


# expected sheet-5 parts: ref -> (value, footprint)
FP = {"R0603": "Resistor_SMD:R_0603_1608Metric", "R0805": "Resistor_SMD:R_0805_2012Metric",
      "C0603": "Capacitor_SMD:C_0603_1608Metric", "C0805": "Capacitor_SMD:C_0805_2012Metric",
      "C1206": "Capacitor_SMD:C_1206_3216Metric"}
PARTS = {
    "J501": ("PERIPH_PWR_4P", "Connector_TE-Connectivity:TE_MATE-N-LOK_350211-1_1x04_P5.08mm_Vertical"),
    "J502": ("X4_PWR", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0215_1x02_P3.00mm_Vertical"),
    "JP501": ("SERVICE", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),
    "F501": ("5A T", "Fuse:Fuse_Littelfuse-NANO2-451_453"), "F502": ("1A T", "Fuse:Fuse_Littelfuse-NANO2-451_453"),
    "D501": ("SMBJ15A", "Diode_SMD:D_SMB"), "D502": ("SMBJ13A", "Diode_SMD:D_SMB"),
    "U501": ("TPS259470LRPWR", "a2000-bridgeboard:TI_RPW0010A_VQFN-HR-10_2x2mm"),
    "U503": ("TPS259470LRPWR", "a2000-bridgeboard:TI_RPW0010A_VQFN-HR-10_2x2mm"),
    "U502": ("INA226AIDGSR", "Package_SO:MSOP-10_3x3mm_P0.5mm"),
    "U504": ("TLV76733DGNR", "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm_ThermalVias"),
    "Q501": ("BSS138", "Package_TO_SOT_SMD:SOT-23"), "Q502": ("BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "Q503": ("BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "R501": ("10m", "Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm"),
    "C501": ("470u", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm"), "C513": ("220u", "Capacitor_SMD:CP_Elec_8x10"),
}
for i in range(4):
    PARTS[f"H{501 + i}"] = ("M2.5_GND", "MountingHole:MountingHole_2.7mm_M2.5_Pad_Via")
# two-pin parts: ref -> (value, footprint key, net of pin 1, net of pin 2)
TWO = {
    "F501": ("5A T", None, "+12V_IN", "+12V_F"), "F502": ("1A T", None, "+5V_IN", "+5V_F"),
    "D501": ("SMBJ15A", None, "+12V_F", "GND"), "D502": ("SMBJ13A", None, "+5V_F", "GND"),     # pin 1 = K
    "C502": ("1u", "C1206", "+12V_F", "GND"), "C503": ("100n", "C0603", "+12V_F", "GND"),
    "C506": ("100n", "C0603", "+3V3", "GND"), "C501": ("470u", None, "X4_12V", "GND"),          # CP pin 1 = +
    "C507": ("1u", "C1206", "X4_12V", "GND"), "C508": ("100n", "C0603", "X4_12V", "GND"),
    "R511": ("4.7k", "R0805", "X4_12V", "GND"),
    "R502": ("402k", "R0603", "+12V_F", "X4_EN_UVLO"), "R503": ("13k", "R0603", "X4_EN_UVLO", "X4_OVLO"),
    "R504": ("39.2k", "R0603", "X4_OVLO", "GND"), "R505": ("100R", "R0603", "X4_DVDT", "X4_DVDT_C"),
    "C504": ("10n", "C0603", "X4_DVDT_C", "GND"), "C505": ("10n", "C0603", "X4_ITIMER", "GND"),
    "R506": ("1.10k", "R0603", "X4_ILM", "GND"), "R507": ("10k", "R0603", "+3V3", "X4_PWR_FLT_N"),
    "R508": ("100k", "R0603", "+12V_F", "X4_EN_INH"), "R509": ("47k", "R0603", "X4_EN_INH", "GND"),
    "R510": ("10k", "R0603", "X4_PWR_EN", "GND"),
    "R521": ("4.7k", "R0603", "+3V3", "I2C_SDA"), "R522": ("4.7k", "R0603", "+3V3", "I2C_SCL"),
    "R523": ("10k", "R0603", "+3V3", "INA_ALERT_N"),
    "C509": ("1u", "C1206", "+5V_F", "GND"), "C510": ("100n", "C0603", "+5V_F", "GND"),
    "R512": ("432k", "R0603", "+5V_F", "X5_EN_UVLO"), "R513": ("38.3k", "R0603", "X5_EN_UVLO", "X5_OVLO"),
    "R514": ("124k", "R0603", "X5_OVLO", "GND"), "R516": ("100R", "R0603", "X5_DVDT", "X5_DVDT_C"),
    "C511": ("10n", "C0603", "X5_DVDT_C", "GND"), "C512": ("10n", "C0603", "X5_ITIMER", "GND"),
    "R515": ("6.65k", "R0603", "X5_ILM", "GND"), "R517": ("10k", "R0603", "+3V3", "X5_FLT_N"),
    "C513": ("220u", None, "+5V_BUS", "GND"), "C514": ("10u", "C0805", "+5V_BUS", "GND"),
    "C515": ("100n", "C0603", "+5V_BUS", "GND"), "C516": ("1u", "C0805", "+5V_BUS", "GND"),
    "C517": ("10u", "C0805", "+3V3", "GND"), "C518": ("100n", "C0603", "+3V3", "GND"),
    "R518": ("100k", "R0603", "X4_3V3_REF", "X4_S0_GATE"), "R519": ("1M", "R0603", "X4_S0_GATE", "GND"),
    "R520": ("10k", "R0603", "+3V3", "X4_S0_SENSE"),
}
IC = {
    "U501": {"5": "+12V_F", "1": "X4_EN_UVLO", "2": "X4_OVLO", "7": "X4_DVDT", "6": "X4_12V_EF", "4": "X4_PWR_FLT_N",
             "3": None, "9": "X4_ILM", "10": "X4_ITIMER", "8": "GND"},
    "U503": {"5": "+5V_F", "1": "X5_EN_UVLO", "2": "X5_OVLO", "7": "X5_DVDT", "6": "+5V_BUS", "4": "X5_FLT_N",
             "3": None, "9": "X5_ILM", "10": "X5_ITIMER", "8": "GND"},
    "U502": {"10": "X4_SH_P", "9": "X4_SH_N", "8": "X4_12V", "1": "+3V3", "2": "GND", "4": "I2C_SDA", "5": "I2C_SCL",
             "3": "INA_ALERT_N", "6": "+3V3", "7": "GND"},
    "U504": {"8": "+5V_BUS", "5": "+5V_BUS", "1": "+3V3", "2": "+3V3", "3": None, "7": None, "4": "GND", "6": "GND",
             "9": "GND"},
    "R501": {"1": "X4_12V_EF", "4": "X4_12V", "2": "X4_SH_P", "3": "X4_SH_N"},
    "Q502": {"1": "X4_EN_INH", "3": "X4_EN_UVLO", "2": "GND"},
    "Q501": {"1": "X4_PWR_EN", "3": "X4_EN_INH", "2": "GND"},
    "Q503": {"1": "X4_S0_GATE", "3": "X4_S0_SENSE", "2": "GND"},
    "J501": {"1": "+12V_IN", "2": "GND", "3": "GND", "4": "+5V_IN"},
    "J502": {"1": "GND", "2": "X4_12V"},
    "JP501": {"1": "X4_EN_UVLO", "2": "GND", "3": "X4_EN_INH"},
    "TP501": {"1": "+12V_F"}, "TP502": {"1": "X4_12V"}, "TP503": {"1": "X4_EN_UVLO"}, "TP504": {"1": "+5V_BUS"},
    "TP505": {"1": "+3V3"}, "TP506": {"1": "X5_FLT_N"}, "TP507": {"1": "X4_S0_SENSE"}, "TP508": {"1": "GND"},
}
for i in range(4):
    IC[f"H{501 + i}"] = {"1": "GND"}


def main(path):
    comps, raw = netlist.load(Path(path))
    nets = {(n.rsplit("/", 1)[-1] if n.startswith("/") else n): v for n, v in raw.items()}
    pin_net = {(r, p): n for n, v in nets.items() for r, p, _ in v}

    def net_of(r, p):
        n = pin_net.get((r, str(p)))
        return None if n is None or n.startswith("unconnected-") else n

    def members(n):
        return sorted((r, p) for r, p, _ in nets.get(n, []))

    def v_of(ref):
        return val(comps.get(ref, {}).get("value", ""))

    # ---------------- parts, values, footprints, pins
    for ref, (value, fp) in PARTS.items():
        c = comps.get(ref)
        check(c is not None and c["value"] == value and c["footprint"] == fp, f"{ref}: {c and (c['value'], c['footprint'])}")
    for ref, (value, fpk, n1, n2) in TWO.items():
        c = comps.get(ref)
        check(c is not None and c["value"] == value, f"{ref} value {c and c['value']} (want {value})")
        if fpk:
            check(c is not None and c["footprint"] == FP[fpk], f"{ref} footprint {c and c['footprint']}")
        check(net_of(ref, "1") == n1 and net_of(ref, "2") == n2,
              f"{ref}: pin 1 {net_of(ref, '1')} (want {n1}), pin 2 {net_of(ref, '2')} (want {n2})")
    for ref, pins in IC.items():
        for pn, want in pins.items():
            got = net_of(ref, pn)
            if want is None:
                check(got is None or len(nets.get(got, [])) == 1, f"{ref}.{pn} must be unconnected, is on {got}")
            else:
                check(got == want, f"{ref}.{pn} on {got} (want {want})")
    present = {r for r in comps if re.match(r"(?:[A-Z]+)5\d\d$", r)}
    check(present == set(PARTS) | set(TWO) | set(IC), f"sheet-5 parts: missing {sorted((set(PARTS) | set(TWO) | set(IC)) - present)}, "
          f"unexpected {sorted(present - (set(PARTS) | set(TWO) | set(IC)))}")
    for ref in ("U501", "U503"):
        check(comps.get(ref, {}).get("fields", {}).get("MPN") == "TPS259470LRPWR", f"{ref} MPN TPS259470LRPWR (S5-1)")

    # ---------------- S5-2: U501 window and current limit re-derived from the schematic values
    sel = sp.selections()
    rilm = v_of("R506")
    lo, nom, hi = sp.ilim_band(rilm) if rilm else (0, 0, 9)
    check(rilm == sel["RILM_12"], f"R506 {rilm} ohm equals the analysis selection {sel['RILM_12']}")
    check(lo >= 1.05 * sp.I_DESIGN and hi <= 3.40, f"U501 ILIM {lo:.2f}-{hi:.2f} A (want >= 2.625, <= 3.40)")
    r1, r2, r3 = v_of("R502"), v_of("R503"), v_of("R504")
    b = sp.string_bands(r1, r2, r3)
    check((r1, r2, r3) == tuple(sel["STRING_12"]), f"U501 string {r1, r2, r3} equals the selection {sel['STRING_12']}")
    check(r1 >= sp.R_TOP_MIN, f"R502 {r1} >= 350 kOhm (TI ROC note 2)")
    check(b["uv_max"] < sp.V12[0] and b["ov_min"] > sp.V12[2],
          f"U501 window UVLO <= {b['uv_max']:.2f} V < 11.4 V, OVLO >= {b['ov_min']:.2f} V > 12.6 V")
    tot = r1 + r2 + r3
    check(24.4 * (r2 + r3) / tot <= sp.V_PIN_ABS and 24.4 * r3 / tot <= sp.V_PIN_ABS, "U501 pins <= 6.5 V at the 24.4 V clamp")
    check(v_of("C505") == sel["CITIMER"] and v_of("C504") == sel["CDVDT_12"] and v_of("C501") == sel["C501"],
          "C505 / C504 / C501 equal the analysis selections (ITIMER, soft start, bulk)")
    check(v_of("R505") == 100.0, "R505 100 ohm in series with CdVdt >= 10 nF (TI 7.3.5.1)")
    # ---------------- S5-6: U503 window, U504 rating
    r1, r2, r3 = v_of("R512"), v_of("R513"), v_of("R514")
    b5 = sp.string_bands(r1, r2, r3)
    check((r1, r2, r3) == tuple(sel["STRING_5"]), f"U503 string {r1, r2, r3} equals the selection {sel['STRING_5']}")
    check(r1 >= sp.R_TOP_MIN, f"R512 {r1} >= 350 kOhm")
    check(b5["uv_max"] < sp.V5[0] and b5["ov_min"] > sp.V5[2] and b5["ov_max"] <= 6.10,
          f"U503 window: UVLO <= {b5['uv_max']:.2f} V, OVLO {b5['ov_min']:.2f}-{b5['ov_max']:.2f} V (want > 5.25, <= 6.10)")
    tot = r1 + r2 + r3
    check(21.5 * (r2 + r3) / tot <= sp.V_PIN_ABS, "U503 EN/UVLO <= 6.5 V at the SMBJ13A clamp (21.5 V)")
    check(v_of("R515") == sel["RILM_5"] and v_of("C511") == sel["CDVDT_5"] and v_of("R516") == 100.0,
          "R515 6.65 kOhm, C511 10 nF + R516 100 ohm (U503)")
    check(comps.get("U504", {}).get("fields", {}).get("MPN") == "TLV76733DGNR", "U504 TLV76733DGNR (18 V absolute maximum)")

    # ---------------- rails
    def drivers(n):
        return [(r, p) for r, p, t in nets.get(n, []) if t == "power_out"]
    check(drivers("+3V3") == [("U504", "1")], f"+3V3 driven only by U504 OUT: {drivers('+3V3')}")
    check(drivers("+5V_BUS") == [("U503", "6")], f"+5V_BUS driven only by U503 OUT: {drivers('+5V_BUS')}")
    check(drivers("X4_12V_EF") == [("U501", "6")], "X4_12V_EF driven only by U501 OUT")
    cap33 = 0.0
    for r, p in members("+3V3"):
        if r.startswith("C") and {net_of(r, "1"), net_of(r, "2")} == {"+3V3", "GND"}:
            cap33 += v_of(r) or 0.0
    check(cap33 <= 200e-6, f"total +3V3 capacitance {cap33 * 1e6:.1f} uF <= 200 uF (TLV767 COUT 1-220 uF)")
    check(not [m for m in members("+5V_BUS") if m[0] == "J101"] and not [m for m in members("+3V3") if m[0] == "J101"],
          "no Zorro pin on +5V_BUS or +3V3")
    for pn in ("5", "6", "8", "10", "20"):
        check(net_of("J101", pn) is None, f"Zorro power pin J101.{pn} unconnected")
    for n in ("+12V_IN", "+12V_F", "X4_12V_EF", "X4_12V", "+5V_IN", "+5V_F"):
        check(not [m for m in members(n) if m[0] in ("U201", "J101", "J401")], f"{n}: no FPGA, Zorro or X4-header pin")

    # ---------------- S5-3 / S5-9: fail-safe enable chain and service override
    check(set(members("X4_PWR_EN")) == {("U201", "112"), ("Q501", "1"), ("R510", "1")},
          f"X4_PWR_EN only FPGA pin 112, Q501 gate and the R-51 pull-down: {members('X4_PWR_EN')}")
    vg = sp.V12[2] * v_of("R509") / (v_of("R508") + v_of("R509"))
    vg_min = 4.7 * v_of("R509") / (v_of("R508") + v_of("R509"))
    check(2.5 <= vg <= 10.0 and vg_min >= 1.5, f"Q502 gate {vg:.2f} V at 12.6 V and >= 1.5 V from 4.7 V ({vg_min:.2f} V)")
    check(set(members("X4_EN_UVLO")) == {("U501", "1"), ("R502", "2"), ("R503", "1"), ("Q502", "3"), ("JP501", "1"), ("TP503", "1")},
          f"EN/UVLO node members {members('X4_EN_UVLO')}")
    check(set(members("X4_EN_INH")) == {("Q502", "1"), ("R508", "2"), ("R509", "1"), ("Q501", "3"), ("JP501", "3")},
          f"Q502 gate node members {members('X4_EN_INH')}")
    # ---------------- S5-4 / C-28 / C-29
    a1, a0 = net_of("U502", "1"), net_of("U502", "2")
    code = {"GND": 0, "+3V3": 1, "I2C_SDA": 2, "I2C_SCL": 3}
    addr = 0x40 + 4 * code.get(a1, 9) + code.get(a0, 9) if a1 in code and a0 in code else None
    check(addr == 0x44, f"INA226 address {addr and hex(addr)} (want 0x44; C-28 forbids 0x40-0x43)")
    for n, extra in (("I2C_SDA", ("U502", "4")), ("I2C_SCL", ("U502", "5"))):
        refs = {r for r, _ in members(n)}
        check(refs == {"U201", "U502", "R521" if n == "I2C_SDA" else "R522"}, f"{n}: only the FPGA, the INA226 and its pull-up: {sorted(refs)}")
    for n in ("X4_PWR_FLT_N", "INA_ALERT_N", "I2C_SDA", "I2C_SCL", "X4_S0_SENSE", "X5_FLT_N"):
        pulls = [r for r, _ in members(n) if r.startswith("R")]
        check(pulls and all("+3V3" in (net_of(r, "1"), net_of(r, "2")) for r in pulls), f"{n}: pull-up(s) {pulls} to +3V3 only (C-29)")
    check(set(members("X4_PWR_FLT_N")) == {("U201", "113"), ("U501", "4"), ("R507", "2")}, "X4_PWR_FLT_N members")
    check(set(members("INA_ALERT_N")) == {("U201", "111"), ("U502", "3"), ("R523", "2")}, "INA_ALERT_N members")
    # ---------------- S5-5 / ER-3
    check(set(members("X4_S0_SENSE")) == {("U201", "114"), ("Q503", "3"), ("R520", "2"), ("TP507", "1")},
          f"X4_S0_SENSE: FPGA pin 114, Q503 drain (active low), +3V3 pull-up, TP: {members('X4_S0_SENSE')}")
    s5_on_ref = [m for m in members("X4_3V3_REF") if re.match(r"[A-Z]+5\d\d$", m[0])]
    check(s5_on_ref == [("R518", "1")], f"sheet 5 loads X4_3V3_REF only through R518: {s5_on_ref}")
    i_ref = 3.465 / (v_of("R518") + v_of("R519"))
    check(i_ref <= 3.5e-6, f"S0 sense load on X4_3V3_REF {i_ref * 1e6:.2f} uA <= 3.5 uA (ER-3)")
    # ---------------- S5-8: X4 lead, standoffs
    check(net_of("J502", "1") == "GND" and net_of("J502", "2") == "X4_12V", "J502 pin 1 GND, pin 2 +12 V (X4 J10 order)")
    check(net_of("U502", "8") == "X4_12V", "INA226 VBUS on the X4 side (external-source check, S5-9)")
    check(net_of("R501", "1") == net_of("U501", "6") and net_of("R501", "2") == net_of("U502", "10")
          and net_of("R501", "3") == net_of("U502", "9"), "Kelvin shunt: 1 from U501 OUT, 2 -> IN+, 3 -> IN-")
    print(f"{checks} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
