# Sheet 4: S4-6, isolating the FPGA → RP2040 outputs (revision A1)

**Status:** 2026-11-19. This is the response to your review of PR #7.
- **Approved:** the isolation requirement.
- **Revise or prove:** the revision A implementation, U402's B supply taken from GP24.

This document gives:
- the analysis you asked for (§2);
- the alternatives, with component count, cost, timing, start-up defaults and transient behaviour (§3);
- the circuit now drawn on sheet 4 revision A1 (§4).

**Not validated.** Hardware check M-16 (§5) remains.

**Reproducible model:** [../../tools/analysis/k4_transient.py](../../tools/analysis/k4_transient.py) (`python -I tools/analysis/k4_transient.py`).

## 1. Requirement and facts

**Requirement (approved).** Every FPGA → RP2040 signal (IRQ_N, ATTN, MISO, TDO) must be isolated whenever the RP2040's I/O supply is unavailable:
- in reset;
- in BOOTSEL;
- when the X4's K4 key switches its supply P3V_RP off while the header 3.3 V (P3V3_S) stays up;
- on power loss.

An operating instruction is not an acceptable means.

| Fact | Value | Source |
|---|---|---|
| P3V_RP feeds | IOVDD1–6 and VREG_VIN; ADC_AVDD through L10. USB_VDD is on P3V3_A through R304 (R303 to P3V3_S not fitted) | [V S1 sh.21] |
| P3V_RP switch | Q32 (CJ3139K, P-MOSFET) from P3V3_S; gate pulled low through R481 by Q33 (2SC5658). K4 grounds Q33's base node. No gate pull-up on Q32 | [V S1 sh.21] |
| P3V_RP decoupling identified | C206 10 µF; C207, C209–C212 0.1 µF each: **10.5 µF** | [V S1 sh.21] |
| RP2040 pin limits | Voltage at an I/O pin ≤ **IOVDD + 0.5 V** (absolute maximum); VIH ≤ **IOVDD + 0.3 V** (operating); VIH ≥ 2.0 V and VOH ≥ 2.62 V at IOVDD 3.3 V (VOH at the rated 2/4/8/12 mA of the drive setting); pull-up/pull-down 50–80 kΩ; **IIOVDD_MAX 50 mA**, the sum of all sourced GPIO/QSPI currents. **No per-pin current rating.** Pads reset to input with pull-down | [V S65 §5.5.3, Tables 622, 625] |
| SN74AVC4T774 | /OE high: both ports Hi-Z, IOZ ≤ ±5 µA; VCC isolation and Ioff ≤ ±1 µA; ICCB ≤ 8 µA; /OE referenced to VCCA; OE → B disable (tPHZ) ≤ 6.2 ns at 3.3 V; TI recommends /OE pulled up to VCCA for Hi-Z during supply ramps | [V S66] |
| TLV7021 (new) | 1.6–5.5 V; 5 µA typical, 10 µA max; rail-to-rail inputs; offset ≤ ±8 mV; internal hysteresis 1.2–14 mV; tPHL/tPLH 260/310 ns typical (no maximum given); **inputs diode-clamped to VEE only, rated to 6 V regardless of VCC**; open-drain output rated to 6 V regardless of VCC; **power-on reset keeps the output high-impedance** while the supply ramps | [V S68] |

## 2. Revision A (U402 VCCB = GP24 through R416 47 Ω, C404 100 nF, R417 100 kΩ): your two questions

### 2.1 Power-down sequencing: RP_VIO can stay above IOVDD

Both rails were modelled through a K4 event:
- P3V_RP: 10.5 µF, discharged by the X4's own load of 5, 25 or 100 mA [E];
- RP_VIO: as described below.

| Phase | RP_VIO behaviour |
|---|---|
| While the RP2040 runs | GP24's output PMOS is on and conducts in both directions, so RP_VIO tracks IOVDD (time constant about (R_pad + 47 Ω) × 100 nF ≈ 10 µs [E]) |
| From brownout (assumed at the VREG_VIN minimum, 1.62 V [E]) | The pad stops driving. C404 now holds RP_VIO. Its only discharge paths are R417 (τ = 10 ms, far slower than IOVDD) and the **RP2040's own ESD diodes**: the GP24 pin through R416, and every U402 output pin that is high |

So RP_VIO, and every high U402 output, sits about one diode drop above the collapsing IOVDD, and the clamp current flows into the unpowered RP2040.

| X4 load (IOVDD slope) | Peak RP_VIO − IOVDD | Time above +0.3 V | Time above +0.5 V (absolute maximum) |
|---|---|---|---|
| 5 mA (0.48 V/ms) | 0.60 V (diode-clamped) | 13.8 ms | **7.4 ms** |
| 25 mA (2.38 V/ms) | 0.60 V | 2.9 ms | **2.7 ms** |
| 100 mA (9.52 V/ms) | 0.60 V | 0.72 ms | **0.70 ms** |

**Conclusion: your concern is confirmed.** Revision A does not keep RP_VIO ≤ IOVDD. It relies on the RP2040's ESD structures as the clamp, beyond the pins' absolute maximum, for milliseconds.

### 2.2 GPIO current: GP24 is not demonstrably within limits

GP24 sources everything on RP_VIO.

| Component | Current | Basis |
|---|---|---|
| Charging C404 at turn-on | **31–49 mA peak**, τ ≈ 7–11 µs | 3.3 V / (47 Ω + R_pad). R_pad is not specified; 20–60 Ω [E]. The VOH limit (≥ 2.62 V at 12 mA) implies ≤ 57 Ω only at that current |
| R417 bleed | 33 µA | |
| U402 ICCB, static | ≤ 8 µA | [V S66] |
| R424 while IRQ_N is asserted | 0.33 mA | |
| MISO switching, about 25 pF at 10–20 MHz SPI | 0.41–0.83 mA average; edges from C404, recharged through GP24 | [E] |
| **Steady state** | **≈ 0.8–1.2 mA** | |

The steady state is within the drive setting and IIOVDD_MAX. **The turn-on transient is 3–4× the highest rated drive current**, and the datasheet gives no per-pin limit to compare it with. As you noted, the 12 mA setting is not a current limiter.

**Revision A's S4-6 implementation is withdrawn.**

## 3. Options evaluated

| | Principle | Parts vs rev A | Cost [E] | Timing (U402 A→B) | Start-up default | K4 transient (model, §2 cases) | GP24 current | Verdict |
|---|---|---|---|---|---|---|---|---|
| **A** (rev A) | U402 VCCB from GP24 | – | – | ≤ 2.9 ns (≥ 3.0 V) | VCCB 0 until firmware raises GP24 | **+0.6 V for 0.7–7.4 ms** (ESD-diode clamp) | **31–49 mA turn-on peak**; ≈ 1 mA steady | Withdrawn |
| **B** (recommended) | VCCB on the header 3.3 V like the other translators; U402 /OE from a **comparator: GP24 against 0.930 × the header 3.3 V** | +TLV7021, +5 R, +1 C; −R416, −R417 | ≈ AUD 0.6–1.5 | ≤ 2.9 ns: **unchanged from the approved budget** | Disabled. R429 holds /OE at VCCA (TI's recommendation), the comparator's power-on reset keeps its output off, and R430 pulls GP24 low | **≤ +0.29 V, never above +0.3 V**, for any discharge rate (only the ≤ 2 µs latency matters). Disabled 26–518 µs after K4, long before brownout | **≤ 0.36 mA**; no transient | **Adopted (rev A1)** |
| **C** | Emitter follower: VCCB = GP24 − V_BE | +NPN, +2 R, smaller C | ≈ AUD 0.1 | ≤ 3.3 ns (VCCB ≈ 2.6 V); VOH 2.6 V against VIH 2.0 V | VCCB 0: isolated | ≤ IOVDD up to about 48 V/ms with τ = 47 µs; **> +0.5 V at about 95 V/ms, or at 10 V/ms with τ = 470 µs**: rate-dependent | Base current ≈ 15 µA [E] | Alternative. Safety depends on the X4's discharge rate and V_BE. The collector supply either loads P3V3_S with milliamps or, from the carrier, back-feeds the carrier through the B–C junction when the carrier is off |
| **D** | Open-drain IRQ_N, ATTN and TDO, pulled up in the RP2040's own domain | +open-drain buffer; ATTN polarity change | ≈ AUD 0.3 | Slow edges (µs): fine for IRQ/ATTN/JTAG | Off = pulled up | Cannot source current: inherently safe **for those three** | µA | Partial. **MISO cannot be open-drain at 10 MHz** (a pull-up ≤ 330 Ω would draw 10 mA from a GPIO), so it still needs B or C. Not simpler than B alone |
| **E** | Op-amp tracking supply: VCCB = 0.9 × GP24, active in both directions | +op-amp, +3 R | ≈ AUD 1 | ≈ 2.9 ns (VCCB ≈ 3.0 V, edge of the 3.3 V column) | VCCB 0 | Tracks within the op-amp's bandwidth | µA | Workable, but an op-amp driving a 100 nF supply node needs stability measures. More design risk than B for no gain |
| **F** | Supervisor with an absolute threshold (e.g. TPS3808G01, already in the BOM) driving /OE through an inverter | +IC, +FET, +3–4 R | ≈ AUD 1.5 | As B | As B | At P3V3_S + 5 %, an absolute 2.95 V threshold lets outputs reach **≈ +0.5 V** before disabling | µA | Rejected: B's threshold tracks P3V3_S, so its margin does not depend on the supply tolerance |
| – | Rely on ESD clamps, or an operating rule for K4 | – | – | – | – | – | – | Rejected (your instruction) |

**Translators with an independent supply on each side** were considered under B: the SN74AVC4T774 already is one. What it lacks is a supply that tracks the RP2040's switched IOVDD, and the header does not provide one (§1). B therefore isolates by output enable, keyed to a precise relative threshold, instead of by supply.

## 4. Recommended circuit (drawn on sheet 4 revision A1)

| Ref | Part / value | Nets | Purpose |
|---|---|---|---|
| U402 | SN74AVC4T774 (unchanged channels: IRQ_N, ATTN, MISO, TDO, A→B) | VCCB = **X4_3V3_REF** (was RP_VIO); **/OE = RP_EN_N** | Outputs toward the RP2040, enabled only by U405 |
| U405 | **TI TLV7021DBVR** (SOT-23-5: 1 OUT, 2 VEE, 3 IN+, 4 IN−, 5 VCC) | VCC = X4_3V3_REF, VEE = GND, IN+ = RP_EN_REF, IN− = RP_EN_SENSE, OUT = RP_EN_N | GP24 above IN+: OUT low, U402 enabled. Otherwise OUT off: U402 disabled |
| R427 / R428 | 7.5 kΩ / 100 kΩ, 1 % | X4_3V3_REF → RP_EN_REF → GND | IN+ = 100 / 107.5 = **0.930 × X4_3V3_REF** (1 % resistors: 0.9289–0.9315) |
| R426 | 10 kΩ | X4_GP24_EN → RP_EN_SENSE | Series input resistor |
| R430 | 100 kΩ | X4_GP24_EN → GND | Defines "disabled" while GP24 is not driven |
| R429 | 10 kΩ | +3V3 → RP_EN_N | /OE pull-up to VCCA: disabled by default (TI's recommendation for ramps) |
| C409 | 100 nF | X4_3V3_REF | U405 decoupling |
| R424 | 10 kΩ | **X4_GP24_EN** (was RP_VIO) → X4_GP22_IRQ_N | IRQ_N reads "no interrupt" at the RP2040 while U402 is disabled. Against a 50 kΩ pad pull-down it gives ≥ 2.75 V |
| R425 | 100 kΩ (unchanged) | X4_GP27_ATTN → GND | ATTN reads "not ready" while U402 is disabled |
| TP407 | – | RP_EN_N | M-16 |
| *removed* | R416, R417, RP_VIO, #FLG4002 | – | – |

**Bounds** (supply X4_3V3_REF = P3V3_S, 3.135–3.465 V [A]):

| Quantity | Value | Derivation |
|---|---|---|
| Trip point (GP24 falling) | 0.9289–0.9315 × X4_3V3_REF, ± 22 mV | Resistor tolerance, comparator offset ≤ 8 mV and hysteresis ≤ 14 mV [V S68] |
| **Margin in normal operation** | **≥ 0.15 V** | GP24 ≥ X4_3V3_REF − 40 mV: Q32 drop ≤ 10 mV [E] plus the pad drop ≤ 31 mV at ≤ 0.37 mA with an 8 mA drive setting (VOH ≥ 2.62 V at 8 mA implies ≤ 85 Ω) [V S65]. Highest trip: 0.9315 × V + 22 mV |
| **Worst output overvoltage during K4** | **≤ 0.29 V above IOVDD** (model: 0.246–0.287 V) | (1 − 0.9289) × 3.465 V + 22 mV + slope × 2 µs. Within VIH max (+0.3 V) and the absolute maximum (+0.5 V) |
| Current into the RP2040 pins at that overvoltage | Negligible (ESD diodes not forward-biased at < 0.3 V) | Assessment, not a datasheet value [E] |
| Disable latency | ≈ 0.4 µs typical; **2 µs budgeted** | tPLH 310 ns typical [V S68] + R429 × (OE and output capacitance, ≈ 10 pF) ≈ 0.1 µs + tPHZ ≤ 6.2 ns [V S66]. Even at 100 V/ms, 2 µs adds only 0.2 V |
| After disabling | U402 B outputs Hi-Z (IOZ ≤ ±5 µA) | When P3V3_S also goes: VCC isolation, Ioff ≤ ±1 µA |
| **GP24 load** | **≤ 0.36 mA**, no capacitive inrush | R430 33 µA, R424 ≤ 0.33 mA while IRQ_N is asserted, comparator input 5 pA typical. Against IIOVDD_MAX 50 mA (all GPIO): ≤ 0.7 % |
| X4_3V3_REF static load (ER-3) | ≤ 73 µA | U405 ≤ 10 µA + divider 31 µA + 4 × ICCB ≤ 8 µA. MISO switching current is drawn from X4_3V3_REF as in the approved proposal (MISO's B side was on it then too) |

**States:**

| State | GP24 | U405 OUT | U402 | Outputs at the RP2040 |
|---|---|---|---|---|
| RP2040 running, firmware has raised GP24 | ≈ IOVDD | Low | Enabled | Driven, ≤ P3V3_S ≈ IOVDD + Q32 drop |
| **K4 pressed** (IOVDD collapsing, P3V3_S up) | Follows IOVDD down | Off once GP24 < 0.93 × P3V3_S | **Disabled 26–518 µs after K4**, while IOVDD is still within 0.29 V of P3V3_S (2.89–3.20 V) | ≤ +0.29 V until then; Hi-Z after |
| RP2040 in reset or BOOTSEL; firmware not started | Low (pad pull-down, R430) | Off | Disabled | Hi-Z; IRQ_N follows GP24 through R424 (nobody listening), ATTN low |
| X4 off (P3V3_S = 0) | 0 | Power-on reset: off | VCC isolation | Hi-Z (Ioff) |
| Carrier off, X4 running (Amiga off) | High | Low (irrelevant) | VCC isolation (VCCA = 0) | IRQ_N high (R424), ATTN low (R425): no false interrupt |
| X4 powering up | Low until firmware | Power-on reset, then off | Disabled | Hi-Z |
| Carrier powering up, firmware running | High | Low | Enabled while VCCA ramps | Glitches possible, bounded by P3V3_S ≈ IOVDD: no back-feed; the link is down until IDENTIFY |

**Domain crossings:**
- U405 is in the X4 domain.
- Its inputs are clamped only to VEE and rated to 6 V regardless of VCC, so neither input can feed P3V3_S.
- Its open-drain output is rated to 6 V regardless of VCC and is off during power-on reset. So R429 (carrier +3V3) can hold /OE high while the X4 is off without feeding the X4 [V S68].

**Firmware (FW-1 revised):**
- Drive GP24 high with an 8 mA or 12 mA drive setting before using the link. The enable follows in about 0.4 µs; wait ≥ 10 µs.
- Driving GP24 low isolates U402 on purpose.

## 5. Verification

| Check | Result |
|---|---|
| Netlist audit `audit_sheet4.py` | 204 checks, 0 failures |
| Audit mutation test | **17 of 17** injected faults detected, including /OE tied low, comparator inputs swapped, wrong threshold divider, /OE pull-up moved into the X4 domain, comparator supplied from the carrier, GP24 pull-down missing |
| ERC | 51 entries, all expected ([sheet4-erc-report.md](sheet4-erc-report.md)) |
| Model | §2–§4 numbers from `tools/analysis/k4_transient.py` |
| Hardware **M-16** (revised) | See below |

**M-16 procedure:** carrier powered, FPGA configured, then repeated with the FPGA blank. Scope P3V_RP (X4 side), GP24, TP407 (/OE) and ATTN or IRQ_N at the X4 header while holding K4.

**M-16 pass criteria:**
- /OE rises before IOVDD falls below X4_3V3_REF − 0.3 V;
- no RP2040 pin above IOVDD + 0.3 V at any time;
- the RP2040 power-cycles cleanly;
- /OE high in reset, in BOOTSEL and before firmware starts;
- with the carrier off and the X4 running: IRQ_N high and ATTN low at the header.
