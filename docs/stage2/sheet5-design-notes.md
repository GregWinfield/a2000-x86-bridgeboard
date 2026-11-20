# Sheet 5: power regulation and protection, X4 power control (revision A)

**Status:** 2026-11-20. Drawn from the [sheet 5 architecture proposal, revision A1](sheet5-architecture-proposal.md), which records your review of PR #10.
- **For your review. Not validated. No PCB manufacture is authorised.**
- Every hardware verification and manufacturing gate stays open.

**Files:**
- Schematic: `hardware/kicad/sheets/05_power.kicad_sch` (generator `tools/kicad/sheet5.py`).
- PDF: [sheet5-schematic.pdf](sheet5-schematic.pdf) (page 6). ERC: [sheet5-erc-report.md](sheet5-erc-report.md).
- Analyses: [`tools/analysis/sheet5_power.py`](../../tools/analysis/sheet5_power.py), [`tools/analysis/sheet5_ground.py`](../../tools/analysis/sheet5_ground.py). Figures from them are **model-derived estimates**, not guarantees.
- Audit: [`tools/kicad/audit_sheet5.py`](../../tools/kicad/audit_sheet5.py), 274 checks, 0 failures, 28 of 28 mutants.

## 0. Decisions applied

| ID | Your decision | On the schematic |
|---|---|---|
| S5-1 | TPS259470L for the X4 12 V | U501 TPS259470LRPWR. **Also U503** (proposal §8 item 1, for your confirmation) |
| S5-2 | UVLO/OVLO provisionally approved; recalculate the current limit | R506 1.10 kΩ (ILIM 2.65–3.36 A); R502/R503/R504 402k/13k/39.2k (UVLO 10.02–10.93 V, OVLO 13.33–14.57 V); C505 10 nF (tITIMER 4.9–15.3 ms); C504 10 nF + R505 100 Ω; C501 470 µF; F501 5 A T; D501 SMBJ15A |
| S5-3 | Automatic power-on after configuration and checks; default off; software shutdown/restart; service override | Fail-safe enable stage Q501/Q502/R508–R510 (§2.2); JP501. Power-manager requirements PM-1 to PM-10 for the HDL stage (§10) |
| S5-4 | INA226 at 0x44, 10 mΩ | U502: A1 = +3V3, A0 = GND. R501 is a 4-terminal (Kelvin) shunt. R521/R522/R523 pull-ups to +3V3 |
| S5-5 | Isolated NMOS S0 sense, active low | Q503, R518 100k, R519 1M, R520 10k: **X4_S0_SENSE low = X4 in S0** |
| S5-6 | Improve the 5 V regulator margin; do not rely on the clamp | U503 TPS259470L with **OVLO disconnect** 5.53–6.01 V; D502 SMBJ13A; F502 1 A T; C513 220 µF; **U504 TLV76733DGNR** (18 V absolute maximum) replaces the AP7361C |
| S5-7 | Keep the LDO provisionally; verify thermal | U504 in HVSSOP-8 with a thermal pad; footprint with thermal vias; M-22 |
| S5-8 | Conditional (six conditions) | H501–H504: standoff pads bonded to GND. J502 pin order = J10 (1 GND, 2 12 V). Contact requirements written on J501/J502. Conditions answered in proposal §4.4; **not closed** |
| S5-9 | Interlock, safe during configuration | Hardware default off (§2.2). INA226 VBUS on the X4 side (U502.8 = X4_12V) for PM-2's external-source check. R511 bleed. FLT reports reverse current |

## 1. Block diagram

```
J501.1 +12V_IN -F501 5A T- +12V_F -[D501, C502, C503]- U501 TPS259470L -X4_12V_EF- R501 10m (Kelvin) - X4_12V -[C501 470u, C507, C508, R511]- J502.2 -> X4 J10.2
                                    |  EN/UVLO <- R502/R503/R504 string, Q502 (inhibit), JP501.1          |  U502 INA226 0x44: IN+/IN- = R501.2/.3, VBUS = X4_12V
                                    |  FLT -> X4_PWR_FLT_N (R507 to +3V3)                                 |  SDA/SCL/ALERT -> FPGA pins 125/126/111
                         Q502 gate X4_EN_INH <- R508/R509 from +12V_F, Q501 (gate X4_PWR_EN, R510 pull-down), JP501.3
J501.2/.3 GND (joined)                                                                                    J502.1 GND -> X4 J10.1
J501.4 +5V_IN -F502 1A T- +5V_F -[D502, C509, C510]- U503 TPS259470L (OVLO 5.53-6.01 V) - +5V_BUS -[C513 220u, C514, C515] - U504 TLV76733 - +3V3 [C517, C518]
X4_3V3_REF (sheet 4) -R518 100k- X4_S0_GATE (R519 1M) - Q503 - X4_S0_SENSE (R520 to +3V3) -> FPGA pin 114   LOW = S0
H501-H504 (X4 standoffs) -> GND
```

## 2. Schematic

### 2.1 12 V path to the X4

**U501, TPS259470LRPWR** (pinout [V] SLVSFC9C Table 5-1). The project footprint `TI_RPW0010A_VQFN-HR-10_2x2mm` is drawn from TI's example board layout for RPW0010A (drawing 4225183/A):
- side pads 0.6 × 0.25 mm at ±0.9 / ±0.225 mm;
- L-shaped corner pads (0.6 × 0.3 with 0.25 × 0.65 legs);
- IN and OUT bars 0.3 × 2.4 mm.

The footprint must be re-checked against TI's current drawing before layout.

**Pins:**
- **IN** on +12V_F, after F501 and D501, with C502 1 µF 50 V and C503 100 nF. C502 keeps a hot-plug input edge near 20 V/µs, well below the 100 V/µs absolute maximum [V].
- **OUT** → X4_12V_EF → the R501 Kelvin shunt → X4_12V.
- **EN/UVLO and OVLO:** TI's 3-resistor string R502 402k / R503 13k / R504 39.2k. R1 ≥ 350 kΩ per TI's ROC note 2. At the 24.4 V TVS clamp the pins see 2.81 / 2.11 V, against the 6.5 V absolute maximum.
- **ILM** R506 1.10 kΩ; **ITIMER** C505 10 nF C0G; **DVDT** R505 100 Ω + C504 10 nF C0G.
- **FLT** (open drain, 6.5 V absolute maximum) → X4_PWR_FLT_N, pulled up to +3V3 by R507.
- AUXOFF is not connected.
- **GND** to the plane. The PCB gets 8 thermal vias, the basis of TI's 41.7 °C/W.

**U502, INA226AIDGSR** (DGS pinout [V] SBOS547C Table 4-1):
- IN+ = R501 pin 2, IN− = R501 pin 3 (Kelvin sense pins of the WSK2512-class shunt).
- **VBUS = X4_12V**, on the X4 side, so that PM-2 can see an external source on the X4's USB-C while U501 is off.
- VS = +3V3, with C506.
- A1 = VS, A0 = GND → **0x44**.
- SDA, SCL and ALERT go to FPGA pins 125, 126 and 111, with R521/R522 4.7 kΩ and R523 10 kΩ to +3V3.

**X4 side:**
- C501 470 µF 25 V (low-ESR aluminium, polymer preferred), C507 1 µF, C508 100 nF.
- R511 4.7 kΩ bleed (34 mW), τ ≈ 3.4 s with the X4's capacitance, so that PM-2 can distinguish residual charge from an external source.

**J502** (Micro-Fit 3.0 class, 2 circuits; MPN TBV):
- pin 1 GND, pin 2 +12 V: **the X4 J10 order** [V S2], so a straight lead cannot reverse it;
- requirement ≥ 4 A and ≤ 20 mΩ per contact;
- the lead is a 22 AWG twisted pair, ≤ 15 cm, with a latching 2.54 mm housing at J10 (proposal §4.4 item 3).

**J501** (TE MATE-N-LOK 350211-1 class, the 5.25-inch-drive power header):
- 1 +12 V, 2 and 3 GND (joined at the pins), 4 +5 V [K]. The pin numbering against the actual A2000 harness is TBV (layout keying).
- Requirement ≥ 6 A per contact (ground-return model, case F5).

### 2.2 Fail-safe enable and service override (S5-3, S5-9)

**How it works:**
- **Q502** (BSS138) pulls U501's EN/UVLO to GND, below the 0.45 V shutdown threshold. That also clears a latched fault [V 7.3.9].
- Q502's gate (X4_EN_INH) is biased **from +12V_F** by R508 100k / R509 47k: 4.0 V at 12.6 V, and ≥ 1.5 V for any VIN above 4.7 V. That is below U501's own UVLO, so Q502 is fully on before U501 could start.
- **Q501** (BSS138) pulls X4_EN_INH low only while **X4_PWR_EN** (FPGA pin 112) is high. **R510** 10 kΩ pulls X4_PWR_EN low (R-51).

**Result:**
- U501 is off whenever the FPGA is erased, configuring (I/O tri-stated with weak pull-down [V S49]), in reset or unpowered, or whenever +3V3 is absent.
- It turns on only when the FPGA drives pin 112 high and VIN is inside 10.9–13.3 V.

**JP501** (3-pin header, shunt):

| Position | Effect |
|---|---|
| 1–2 | **Force off**: EN/UVLO to GND |
| 2–3 | **Force on**: Q502's gate to GND. **Bypasses the power manager**. For bench service only: a current-limited supply and nothing on the X4's USB-C. Not for user builds (R-57). The eFuse's own protections remain |
| No shunt, or shunt on one pin | FPGA control (default) |

The full state table is in proposal §5.1.

### 2.3 5 V path, +5V_BUS and +3V3 (S5-6, S5-7)

**U503, TPS259470LRPWR:**
- R512 432k / R513 38.3k / R514 124k: UVLO 4.23–4.58 V, OVLO **5.53–6.01 V**, a disconnect.
- At the SMBJ13A clamp (21.5 V) EN/UVLO sees 5.88 V, below 6.5 V. A 12.6 V miswire holds it off with 3.45 / 2.63 V on EN/UVLO / OVLO.
- R515 6.65 kΩ: ILIM 0.42–0.58 A (a tested point [V], plus resistor tolerance).
- C512 10 nF ITIMER; R516 100 Ω + C511 10 nF: +5V_BUS rises in 13–72 ms.
- FLT → X5_FLT_N with R517 to +3V3 and test point TP506. There is no FPGA pin for it: if U503 trips, +3V3 is lost anyway.
- F502 1 A time-lag, D502 SMBJ13A, C509/C510 at the input.

**+5V_BUS:**
- C513 220 µF 16 V bounds the fast-overvoltage overshoot to ≤ 0.44 V (proposal §3.2). C514 10 µF and C515 100 nF.
- Loads: U103/U104 VCCB (sheet 1, 6.5 V absolute maximum [V S46, S53]), R125 (sheet 1 supervisor divider) and U504.

**U504, TLV76733DGNR** (DGN pinout [V] SLVSE84D Table 5-1):
- IN and EN on +5V_BUS (EN tied high), C516 1 µF.
- OUT and SNS on +3V3, C517 10 µF and C518 100 nF.
- NC pins 3 and 7 open; GND pins 4, 6 and the thermal pad (9) to GND.
- Footprint `HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm_ThermalVias`: the 1.57 × 1.89 mm pad matches TI's DGN0008G land pattern [V].
- **+3V3 now has a single driver (U504)** and about 114 µF in total. The audit limits it to ≤ 200 µF, against the TLV767's COUT maximum of 220 µF [V].

### 2.4 X4_S0_SENSE (S5-5)

- **Q503** (BSS138): gate X4_S0_GATE from X4_3V3_REF (sheet 4, the X4's S0-only 3.3 V [V S1 sh.21]) through R518 100 kΩ, with R519 1 MΩ to GND. Drain → X4_S0_SENSE (FPGA pin 114), R520 10 kΩ to +3V3.
- **Low = X4 in S0.** High = S5, G3, the X4 absent or the ribbon unplugged.
- The load on X4_3V3_REF is ≤ 3.465 V / 1.1 MΩ = 3.2 µA (ER-3).
- The two MOSFET gates (Q503 here, Q402 on sheet 4) are the only links from the X4 domain into carrier nodes.

### 2.5 Ground return (S5-8)

- **H501–H504:** M2.5 plated pads bonded to GND, for the X4's four standoffs. If the X4's holes are bonded to its ground (TBV, **M-21 a**), this is the dedicated low-impedance X4 return. With joints ≤ 5 mΩ, the dedicated paths carry 74–97 % of the X4 return and ΔG ≤ 2.8 mV (`sheet5_ground.py` case N2s).
- **The ribbon's 8 ground conductors stay connected** (signal return, and ΔG).
- **J501's two GND contacts and the 18 Zorro GND fingers are one ground system.** The Zorro **power** pins stay unconnected (audit).
- **Layout rules** (Stage 6):
  - the 12 V path J501 → F501 → U501 → R501 → J502 and its return as a pair over solid ground;
  - a direct pour from J502 GND to J501 GND;
  - no plane splits;
  - U501 and U504 thermal vias.

### 2.6 Test points

| Ref | Net |
|---|---|
| TP501 | +12V_F |
| TP502 | X4_12V |
| TP503 | X4_EN_UVLO |
| TP504 | +5V_BUS |
| TP505 | +3V3 |
| TP506 | X5_FLT_N |
| TP507 | X4_S0_SENSE |
| TP508 | GND |

## 3. Interfaces

| Net | FPGA pin | Direction (FPGA) | On sheet 5 | Default with the FPGA blank |
|---|---|---|---|---|
| X4_PWR_EN | 112 | Output | Q501 gate, R510 10k to GND | Low: X4 off |
| X4_PWR_FLT_N | 113 | Input | U501 FLT (open drain), R507 to +3V3 | High (no fault) |
| X4_S0_SENSE | 114 | Input | Q503 drain, R520 to +3V3. **Active low** | High (not S0) when the X4 is off |
| INA_ALERT_N | 111 | Input | U502 ALERT (open drain), R523 to +3V3 | High |
| I2C_SDA / I2C_SCL | 125 / 126 | Inout | U502, R521/R522 4.7k to +3V3 | High; **no device at 0x40–0x43** (C-28) |
| X4_3V3_REF | – | – | From sheet 4 (hierarchical label added there) | – |

**C-29:** every FPGA input on this sheet is an open drain or a MOSFET drain with its pull-up on +3V3. With +3V3 off, nothing can drive current into the FPGA.

## 4. Values and their derivation

| Part | Value | Derivation |
|---|---|---|
| R506 | 1.10 kΩ 1 % | `sheet5_power.py` §1: largest E96 value with ILIM_min ≥ 1.05 × 2.5 A |
| C505 | 10 nF C0G | §2: tITIMER 4.9–15.3 ms |
| C504 + R505 | 10 nF + 100 Ω | §3: start-up thermal grid, worst margin 25 °C over the capacitive, 1 A and abrupt-switch cases |
| C501 | 470 µF 25 V | Same grid |
| R502–R504, R512–R514 | as drawn | §6: worst-case corners |
| F501 / F502 | 5 A / 1 A time-lag | §5 / §7: carry ILIM_max at 75 % loading and 90 % temperature derating [K] |
| D501 / D502 | SMBJ15A / SMBJ13A | [K, TBV]: VRWM above the operating window, clamp below the 28 V IN and 6.5 V pin limits |
| R508 / R509 | 100k / 47k | Q502 gate 4.0 V at 12.6 V |
| R518 / R519 | 100k / 1M | ER-3 ≤ 3.2 µA; gate 3.0 V in S0, above VGS(th) max 1.5 V [V S71] |
| R511 | 4.7 kΩ | Bleed τ ≈ 3.4 s |

**`audit_sheet5.py` re-derives** the ILIM band and every UVLO/OVLO window from the schematic's resistor values, by importing `sheet5_power.py`. It fails if they drift from the analysis selection.

## 5. Changes to other sheets (all related to drawing sheet 5)

**Sheet 1:**
- The two TEMPORARY PWR_FLAGs on +3V3 and +5V_BUS were removed, with their two power symbols, as their note asked. Otherwise ERC now reports power output against power output.
- Edited surgically in the committed file and in the generator. The `#PWR` counter skips the two numbers, so no other reference changed.
- The sheet-1 netlist is unchanged.

**Sheet 4:**
- X4_3V3_REF is exported by a hierarchical label at its PWR_FLAG. It replaces a local label that overlapped TP405's.

**Root:** sheet 5's block and pins; labels join them to sheet 2's six power-control pins and to sheet 4's X4_3V3_REF.

**Audits:**
- `audit_sheet2.py`: the sheet-5 nets are checked as connected; the open-net count is 8.
- `audit_sheet4.py`: ER-3 allows R518.

**The netlist outside sheet 5 is identical to revision A3.**

## 6. Audit and mutation test

`audit_sheet5.py`, **274 checks**, covers:
- every part, value, footprint and pin;
- the windows and the current limit re-derived from the schematic values;
- R1 ≥ 350 kΩ, and the pins ≤ 6.5 V at the clamp;
- the rails each have one driver (+3V3 = U504, +5V_BUS = U503, X4_12V_EF = U501);
- +3V3 capacitance ≤ 200 µF;
- no Zorro power pin is connected;
- no FPGA, Zorro or X4-header pin on a 12 V or 5 V input net;
- the X4_PWR_EN membership and R-51 pull-down;
- the Q502 gate bias;
- the EN/UVLO and inhibit node members;
- the INA226 address (0x44);
- I²C membership;
- C-29 pull-up domains;
- the S0 polarity membership;
- ER-3 (sheet 5 loads X4_3V3_REF only through R518, ≤ 3.5 µA);
- the J502 pin order;
- VBUS on the X4 side;
- the Kelvin connections.

**Mutation test:** 28 of 28 injected faults are detected (scratchpad `kigen/mut_audit5.py`):
- ILIM 750 Ω or 1.30 kΩ;
- R1 200k;
- the OVLO resistor changed;
- a 5 V OVLO above 6.1 V;
- INA226 A1 to GND (0x40);
- the SDA pull-up to +5V_BUS;
- the X4_PWR_EN pull-down missing;
- Q502's gate on X4_PWR_EN;
- the Q502 bias from +3V3;
- JP501 positions swapped;
- J502 reversed;
- the Kelvin sense swapped;
- VBUS on the eFuse side;
- D501 reversed;
- U504 fed from 12 V;
- C501 100 µF;
- CdVdt 3.3 nF;
- the S0 gate from +3V3;
- the S0 pull-up to the X4 rail;
- R519 100k (ER-3);
- a standoff pad not grounded;
- the FLT pull-up to 12 V;
- F501 bypassed;
- U503 driving +3V3;
- an extra 220 µF on +3V3;
- ITIMER 2.2 nF;
- R505 0 Ω.

## 7. ERC

**39 entries.** All are the documented sheet-6 open pins and labels (13 + 12) plus the 14 permanent pin-to-pin entries ([sheet5-erc-report.md](sheet5-erc-report.md)). This is 12 fewer than revision A3, because the six sheet-5 pins of sheet 2 are now connected.

## 8. Power budget

From `sheet5_power.py` §9. Typical / design maximum:

| Rail | Load | Typical | Design maximum | Basis |
|---|---|---|---|---|
| +12 V | Radxa X4 incl. NVMe and fan | 0.90 A | 2.50 A | [Vs S9] / [V S3] |
| | U501 IQ, string, Q502 divider, INA226 VBUS | 0.8 mA | 1.0 mA | [V] |
| | R511 bleed | 2.6 mA | 2.7 mA | [D] |
| | **Total** | **0.90 A** | **2.50 A** | eFuse ILIM 2.65–3.36 A; FPGA trip 2.75 A |
| +3V3 | FPGA LCMXO2-4000HC core (static 8.45 mA typ [V S49]) + dynamic | 20 mA | 40 mA | [E] |
| | FPGA I/O switching | 10 mA | 25 mA | [E] |
| | SRAM IS61WV25616EDBLL-10 | 10 mA | 35 mA | ICC 30 mA max (Com.) [V S61] |
| | Oscillator | 6 mA | 8 mA | [V S67] |
| | Zorro buffers and translators (3.3 V side) | 10 mA | 30 mA | [E] |
| | Host-link translators, U406, pull-ups | 2 mA | 6 mA | [E] |
| | LEDs (sheet 6) | 6 mA | 10 mA | [A] |
| | Sheet 5: INA226, TLV767 IQ, pull-ups | 1 mA | 4 mA | [V]/[D] |
| | **Sum** | **65 mA** | **158 mA** | **Design maximum kept at 0.25 A** |
| +5 V | +3V3 through U504 + U503 IQ + +5V_BUS translators | 86 mA | 301 mA | U503 ILIM 0.42–0.58 A; F502 1 A |

- **Start-up:** the FPGA's peak start-up current (VCC 55 mA, VCCIO 17 mA, from the Diamond Power Calculator device model, which data sheet Table 3.10 note 6 points to) is covered by U503's start-up budget: 0.33 A < 0.41 A.
- **Power from the A2000:** 11.3 W typical, 33.2 W design maximum.
- **A2000 12 V headroom** (Haynie's example system [V S14]): 1.99 A at the design load, 1.13 A at ILIM_max (proposal §2.3).
- **Open (P-1):** the Diamond Power Calculator did not load the placed NCD in Tcl project mode (0 LUTs reported), and `-ncd` is standalone-only. A GUI run on the placed design is open, so the FPGA dynamic figures stay [E].

## 9. Verification plan

The bench stages B0–B5 and the measurements M-17 to M-24 and P-1 are defined in [proposal §9](sheet5-architecture-proposal.md). In short:
- **Current-limited bench validation comes first.** The carrier alone (B1), then an electronic load (B2), the real X4 (B3) and an emulated slot ground (B4), all before the A2000 motherboard (B5).
- M-17 X4 start-up;
- M-18 eFuse thresholds and limits;
- M-19 INA226;
- M-20 default-off, power-manager and external-source tests;
- M-21 ground return (mounting-hole bonding first, current split, **ΔG ≤ 50 mV**, J10 and J501 ground faults);
- M-22 thermal;
- M-23 5 V overvoltage;
- M-24 S0 sense.

Manufacturing approval would require these. **None is done.**

## 10. Obligations on the HDL power manager (proposal §5.2)

PM-1 to PM-10 are requirements for the HDL stage:

| ID | Requirement |
|---|---|
| PM-1 | X4_PWR_EN reset value 0 |
| PM-2 | Auto power-on sequence: INA226 present at 0x44; T_DELAY default 5 s; **external-source check** VBUS < 3.0 V with a 10 s decay window; FLT/ALERT clear; enable; VBUS inside 11.0–13.2 V within 300 ms |
| PM-3 | Graceful shutdown, unlocked hard off, restart |
| PM-4 | FLT → off within 1 ms, latched |
| PM-5 | > 2.75 A for ≥ 2 s → off, latched |
| PM-6 | `s0 = !X4_S0_SENSE` (active low); current > 0.5 A with no S0 for 30 s → off (ribbon or ground double fault) |
| PM-7 | Detect the JP501 override |
| PM-8 | Latches reported and cleared explicitly |
| PM-9 | INA226 configuration |
| PM-10 | Never address 0x40–0x43 |

No RTL is changed by this sheet: `hdl/` is identical to main, and the STA results stand.

## 11. Findings while drawing sheet 5

1. **TI ROC note 2** asks for ≥ 350 kΩ from IN to EN/UVLO and OVLO for supplies above 5 V or reverse-polarity exposure. Rev A's strings did not respect it. Both A1 strings do, with R1 402k and 432k.
2. **SMBJ15A on the 5 V input** would let U503's EN/UVLO reach 6.7 V at the TVS's maximum clamp. **SMBJ13A** keeps it at 5.88 V.
3. **The X4 switches its internal 12 V rail** with a CH224D-driven MOSFET pair (sheet 26 [V S1]). That inrush follows the soft start. It decided C501 (case E): with 100 µF the modelled TJ would reach 170 °C.
4. **Sheet 1's temporary PWR_FLAGs would conflict** with the new power outputs. They were removed, as their note intended.
5. **The INA226 must sense VBUS on the X4 side** (not the eFuse input) for the S5-9 interlock to work.
6. **The Diamond Power Calculator's Tcl interface does not read a placed NCD in project mode** (P-1).

## 12. Open items and concerns (nothing closed)

- **Your confirmations** (proposal §8):
  1. U503 = 470L with OVLO;
  2. U504 = TLV76733;
  3. the §2 current-limit values;
  4. D502 SMBJ13A;
  5. the bonded standoffs;
  6. JP501.
- **S5-8 remains conditional:** M-21, and your decision if the X4's mounting holes are not bonded.
- **R-56:** manufacturer ratings of J501, J502, the X4-end housing, the ribbon and the IDC sockets are not yet verified. Confirm from each chosen part's specification before ordering. MPNs for F501, F502, D501, D502, J501, J502 and C501 are TBV.
- **R-54 (X4 start-up behaviour), R-55 (5 V double fault), R-57 (service override), R-53 (ground return).**
- **J501 pin numbering** against the A2000 harness (TBV); X4 J10 pitch and population (R-04).
- **RTL:** the power manager (PM-1 to PM-10) is not yet written.
- **P-1:** the Diamond Power Calculator GUI run.
- **Sheet 6:** the "auto-start" DIP and the LEDs.
