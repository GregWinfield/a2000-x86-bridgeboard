# Sheet 4: S4-6, isolating the FPGA → RP2040 outputs (revision A3)

**Status:** 2026-11-19. This is the response to your review of revision A2.
- **S4-6 rev A2 was accepted** as the preferred Rev 1 schematic implementation.
- **G-SHEET4 is approved as a schematic baseline for continued design**, with the electrical qualifications open.

Revision A3 answers the three residual requirements:

| Residual requirement | Finding | Revision A3 |
|---|---|---|
| **1. U402 /OE transition rate** (about 37 ns/V against TI's ≤ 5 ns/V) | Five options evaluated (§6). Lowering R429 alone cannot reach 5 ns/V: Q401's output capacitance dominates. A PMOS active pull-up does not reach it with certainty | **U406, a TI SN74AUP1G17 Schmitt-trigger buffer**, between the open-drain node and U402's /OE. It gives an estimated 0.8 ns/V push-pull edge. It sits wholly on the carrier side, specified from 0.8 V, with Ioff, so the power-off isolation is preserved. The disable latency becomes 190 ns. **For your confirmation** (§6–§7) |
| **2. Transient timing** | Agreed: the slope figures are model results, not manufacturer guarantees | **Relabelled throughout as model-derived bounds** that depend on stated assumptions (box below). New figures: **264 V/ms** (VIH max) and **1317 V/ms** (absolute maximum). M-16 keeps the falling-ramp comparator response and the full translator disable time (§12) |
| **3. GP24 HIGH-level margin** against 0.940 × X4_3V3_REF | **≥ 0.126 V** in the worst static case (FW-1 8 mA drive, 3.135 V supply, maximum X4 load, all tolerances). 0.186 V in a representative case. ≥ 0.117 V even with the weakest 2 mA drive. Dynamic contributors (supply transients, ribbon crosstalk) are estimated, not bounded (§9) | No circuit change. M-16 (f) and (g) measure the margin under traffic and X4 load |

> **Model-derived bounds.** Every slope limit and latency in this document comes from `tools/analysis/k4_transient.py`. It combines:
> - datasheet maxima where the manufacturer publishes them: TLV3201 tPD, BSS138 capacitances, SN74AUP1G17 tPD, SN74AVC4T774 disable time;
> - with the estimates [E] and assumptions [A] listed in §4.1 and §8.
>
> **None of the slope limits is a manufacturer guarantee.** They hold only while those assumptions hold. Hardware check M-16 measures the ones that matter, and **manufacturing approval requires that electrical qualification**.

**Not validated.** Hardware check M-16 (§12) remains open, with every other hardware and manufacturing gate. No PCB fabrication is authorised.

**Reproducible model:** [../../tools/analysis/k4_transient.py](../../tools/analysis/k4_transient.py) (`python -I tools/analysis/k4_transient.py`). Section numbers "model §n" refer to its printed sections.

**Tags:**
- [V Sxx] datasheet value;
- [E] estimate;
- [A] assumption.

Rounding follows your rule: maxima and requirements round up; margins, slacks and minima round down.

**Earlier review (PR #8, revision A1), answered in revision A2 and accepted:**

| Your concern | Finding | Revision A2 |
|---|---|---|
| R424 reverse-current path | Confirmed (§3) | R424 removed; GP22 pull-up in firmware (FW-6); GP24 ≤ IOVDD at all times |
| Comparator timing (TLV7021: typical delay only) | Confirmed. Revision A1's "≤ 0.29 V at any discharge rate" was wrong and is withdrawn (§4.3) | TLV3201 (datasheet-maximum delay) switching Q401, in series with Q402 on GP24; threshold 0.940 (§5) |

## 1. Requirement and facts

**Requirement (approved).** Every FPGA → RP2040 signal (IRQ_N, ATTN, MISO, TDO) must be isolated whenever the RP2040's I/O supply is unavailable:
- in reset;
- in BOOTSEL;
- when the X4's K4 key switches its supply P3V_RP off while the header 3.3 V (P3V3_S) stays up;
- on power loss.

An operating instruction is not an acceptable means.

| Fact | Value | Source |
|---|---|---|
| P3V_RP feeds | IOVDD1–6, VREG_VIN, ADC_AVDD through L10, and the RP2040's SPI flash U24 (W25Q16JV). USB_VDD is on P3V3_A | [V S1 sh.21] |
| P3V_RP switch | Q32 (CJ3139K, P-MOSFET) from P3V3_S. Its gate is pulled low through R481 by Q33; K4 grounds Q33's base node. **Q32 has no gate pull-up**, so after K4 its gate rises only by leakage | [V S1 sh.21] |
| P3V_RP decoupling | C206 10 µF 6.3 V; C207, C209–C212 0.1 µF 16 V: 10.5 µF nominal. Package sizes are not shown | [V S1 sh.21] |
| RP2040 pin limits | Pin ≤ **IOVDD + 0.5 V** (absolute maximum); VIH ≤ **IOVDD + 0.3 V**; VIH ≥ 2.0 V and VOH ≥ 2.62 V at IOVDD 3.3 V; pull-up/down 50–80 kΩ; IIOVDD_MAX 50 mA; no per-pin current rating. Pads reset to input with pull-down | [V S65 §5.5.3, Tables 622, 625] |
| RP2040 reset | The core regulator is rated 100 mA and needs VREG_VIN ≥ 1.63 V. Brown-out acts on DVDD (0.86 V nominal); afterwards the pads return to their reset state | [V S65 §2.10 Table 192, §2.12.3 Table 194] |
| SN74AVC4T774 | /OE high: Hi-Z, IOZ ≤ ±5 µA; VCC isolation, Ioff ≤ ±1 µA; ICCB ≤ 8 µA; /OE referenced to VCCA, VIH 2.0 V at VCCA 2.7–3.6 V, Ci ≤ 4.5 pF; OE → B disable ≤ 6.2 ns; recommended input transition ≤ 5 ns/V; TI recommends /OE pulled up to VCCA for Hi-Z during supply ramps | [V S66] |
| **TLV3201** (new U405) | 2.7–5.5 V; IQ ≤ 60–65 µA; **tPD ≤ 55 ns, −40 to 125 °C**, at 20 mV and 100 mV overdrive, CL 15 pF, in both the 2.7 V and 5 V tables; VIO ≤ 4 mV over temperature; CMRR ≥ 56 dB; hysteresis 1.2 mV typical, no limit; inputs −0.2 V to VCC + 0.2 V, diode-clamped to both rails; **push-pull** output; sink short-circuit current ≥ 13 mA (2.7 V, 25 °C); DBV pinout 1 OUT, 2 GND, 3 IN+, 4 IN−, 5 VCC | [V S70] |
| **BSS138** (new Q401, Q402) | 50 V, 200 mA; VGS(th) 0.5–1.5 V; IDSS ≤ 0.5 µA; IGSS ≤ 100 nA; **Ciss ≤ 50 pF, Coss ≤ 25 pF, Crss ≤ 8 pF** (maxima, guaranteed by design); SOT-23: 1 G, 2 S, 3 D | [V S71] |
| **SN74AUP1G17** (new U406, rev A3) | 0.8–3.6 V; Schmitt-trigger input: VT+ ≤ 2.29 V and VT− ≥ 0.88 V at VCC 3 V, −40 to 85 °C; no input transition-rate limit in the recommended operating conditions; tpd ≤ 6.2 ns (CL 15 pF, 3.3 V ± 0.3 V, −40 to 85 °C); VOH ≥ 2.55 V at −4 mA (VCC 3 V); Ioff ≤ 0.6 µA; DBV pinout 1 NC, 2 A, 3 GND, 4 Y, 5 VCC | [V S73] |
| TLV7021 (rev A1 U405) | VIO ≤ 8 mV, hysteresis ≤ 14 mV; **tPHL/tPLH 260/310 ns typical only** (100 mV overdrive, 25 °C, 5 V); open drain; inputs clamped to VEE only; power-on reset | [V S68] |

## 2. Revision A (history)

Revision A supplied U402's B side from GP24 (R416 47 Ω, C404 100 nF, R417 100 kΩ). It was withdrawn after your review of PR #7:
- RP_VIO stays about 0.6 V above the collapsing IOVDD for 0.70–7.42 ms (model §2). Only the RP2040's ESD diodes clamp it, beyond the pin's absolute maximum.
- Charging C404 at turn-on needs 31–49 mA from GP24 [E].

## 3. Concern 1: the R424 path

### 3.1 What R424 did

In revision A1, R424 (10 kΩ) ran from GP24 to GP22 (IRQ_N), so that IRQ_N read "no interrupt" while U402 was disabled. U402 drives IRQ_N high at X4_3V3_REF whenever it is enabled and no interrupt is pending. Two effects follow (model §4).

**While the RP2040 drives GP24:**
- R424's current flows into the GP24 pad and on into IOVDD.
- At revision A1's trip point it is ≤ 27 µA. It lifts GP24 ≤ 2.3 mV above IOVDD, which delays the trip slightly.
- If U402 were still enabled as IOVDD collapsed, it would reach 0.29 mA, fed into the unpowered RP2040.

**After the RP2040 releases GP24** (reset, or brownout at VREG_VIN below 1.63 V):
- R424 and the pull-downs (R430 ∥ the pad's 50–80 kΩ) hold GP24 at 2.67–2.83 V while U402 drives IRQ_N high.
- That is above a collapsed IOVDD. GP24's ESD diode then conducts into the unpowered RP2040.
- It does not latch the enable: 2.83 V is below the lowest trip point.
- **But it breaks the invariant GP24 ≤ IOVDD**, on which the timing argument rests, and it is a back-feed path.

**Your concern is confirmed.**

### 3.2 Revision A2: R424 removed

**GP24's net (X4_GP24_EN) now has exactly four members** (the audit checks this):
- J401 pin 22 (the RP2040 pad);
- R426 to the comparator input (≤ 5 nA);
- R430 100 kΩ to GND;
- R431 1 kΩ to Q402's gate (≤ 100 nA).

Nothing on the carrier can source current into it. So **GP24 ≤ IOVDD at all times**, and the enable is monotonic:
- U402 can be enabled only while GP24, and therefore IOVDD, is above 0.9385 × X4_3V3_REF − 17 mV;
- the only exposure is the disable latency after IOVDD crosses that point (§8: ≤ 190 ns, model-derived).

**IRQ_N's "no interrupt" default** now comes from the RP2040's own GP22 pull-up. The pull-up is in the RP2040's I/O domain, so it cannot back-feed anything. **New firmware rule FW-6**, in this order:
1. Configure GP22 as an input with the pull-up enabled and the pull-down disabled.
2. Then drive GP24 high (FW-1).
3. Wait ≥ 10 µs.
4. Clear any pending GP22 edge or level event.
5. Only then enable the GP22 interrupt.

The interrupt is level-low active (IRQ_N).

### 3.3 Interrupt idle state, verified state by state

IRQ_N's net at the RP2040 is J401 pin 16 and R412 only (audit). Its loads:
- U402's B1 output when enabled;
- otherwise U402's leakage: IOZ ≤ 5 µA, or Ioff ≤ 1 µA when isolated [V S66].

Against an 80 kΩ maximum pull-up, the idle level is **≥ IOVDD − 0.4 V ≥ 2.70 V**, above VIH 2.0 V (IOVDD ≥ 3.10 V: P3V3_S − 5 % − Q32 drop [A/E]). While U402 drives IRQ_N low it sinks ≤ 70 µA from the pull-up.

| State | GP24 / U402 | IRQ_N at the RP2040 | Interrupt seen |
|---|---|---|---|
| Normal operation | High / enabled | Driven by U402 from RP_IRQ_N (high = idle) | Only real requests |
| FPGA blank or configuring, X4 running | High / enabled | High: R405 2.2 kΩ holds U402's A input ≥ 2.46 V against the blank FPGA's pull-down | None |
| RP2040 boot, before FW-6 | Low (pad pull-down, R430) / disabled | Low (the pad's reset pull-down) | **None: the interrupt is not enabled yet.** FW-6 orders pull-up → GP24 → clear → enable |
| RP2040 reset or BOOTSEL | Low / disabled | Low (pad reset default) | None: no firmware is running. After reset, the boot sequence above repeats |
| Firmware isolates on purpose (GP24 low, FW-8) | Low / disabled | High (pull-up) | None |
| **Carrier power loss**, X4 running | High / U402 VCCA = 0, isolated (Ioff ≤ 1 µA) | **High** (pull-up) | **None in the final state.** During the collapse U402 passes the FPGA's RP_IRQ_N; a pulse is possible only if the FPGA's outputs glitch before its power-on reset. Firmware treats any interrupt as "read STATUS"; with the carrier down that fails, and the §8 retries end in LINK_DOWN. This is unchanged from rev A1 |
| Carrier power-up, firmware running | High / enabled as VCCA ramps | Follows RP_IRQ_N once U402 operates; glitches possible during the ramp | As above: a spurious interrupt costs one failed STATUS read; frames before IDENTIFY are ignored |
| K4 (IOVDD collapsing) | Falls with IOVDD / disabled ≤ 190 ns after the trip (model-derived) | Irrelevant: the RP2040 is losing power | – |
| X4 off | 0 / VCCB = 0 | – | – |

## 4. Concern 2: the power-down analysis rerun

### 4.1 Worst-case parameters

| Parameter | Value used | Source |
|---|---|---|
| X4_3V3_REF (P3V3_S) | 3.135–3.465 V | [A] ±5 % |
| Carrier +3V3 (VCCA, R429) | ≥ 3.135 V | [A] |
| Resistors | 1 % plus 100 ppm/K from 25 °C to −40/+85 °C: **±1.65 % each, not tracking** | [A] BOM specification |
| Comparator offset | TLV3201: VIO 4 mV + CMRR 2.6 mV (56 dB over a 1.6 V shift from VCC/2) + hysteresis 10 mV = **16.6 mV**. TLV7021: 8 + 14 = 22 mV | [V S70] except the hysteresis: 1.2 mV typical, no limit; 10 mV [E]. [V S68] |
| Overdrive | The comparator must see **20 mV past its trip point** before its datasheet-maximum tPD applies. On a ramp this costs 20 mV of IOVDD | [V S70] test condition; ramp argument [E] |
| Comparator delay | TLV3201 ≤ 55 ns (datasheet maximum). TLV7021 310 ns *typical* (no maximum) | [V S70], [V S68] |
| C_eff of P3V_RP | **≥ 1.887 µF**. C206: 25 % retained at 3.3 V DC bias (0402 X5R 6.3 V worst case, as the size is not shown), −20 %, −15 % (X5R), −5 % aging: × 0.162. The 0.1 µF parts: × 0.544 | [E] |
| P3V_RP load | **≤ 176 mA**: IOVDD 50 mA (IIOVDD_MAX), VREG 100 mA (rated output), flash 25 mA, ADC 1 mA | [V S65] for 150 mA; flash and ADC [E] |
| Q32 drop | ≤ 35 mV (176 mA × 0.2 Ω) | [E] |
| X4 copper, P3V3_S to the RP2040 IOVDD pins | ≤ 10 mV at 176 mA | [E] (added in rev A3, §9) |
| GP24 pad | ≤ 85 Ω (from VOH ≥ 2.62 V at 8 mA): ≤ 3 mV at 36 µA | [V S65 → E] |

### 4.2 Discharge rate

After K4, assuming Q32 opens instantly (model §1), the worst case is **176 mA / 1.887 µF = 93.3 V/ms**, rounded up to **94 V/ms [E]**.

For comparison, revision A1's model used the undegraded 10.5 µF and 5–100 mA: 0.48–9.52 V/ms. The new bound is ten times faster than revision A1's fastest case.

In practice Q32's gate has no pull-up and rises only by leakage, so a real K4 turn-off is probably much slower. **Nothing below relies on that.**

**Not covered:** a fault that collapses P3V_RP faster than the bounds in §8, such as a short on the X4. The design makes no claim there.

### 4.3 Revision A1 rerun (model §3)

| Quantity | Value |
|---|---|
| Threshold k = R428 / (R427 + R428) | 0.9302 nominal; **0.92806–0.93234** with ±1.65 % resistors |
| Output level above IOVDD when the trip completes, before latency (VS 3.465 V, lowest k, 22 mV offset, 20 mV overdrive) | **0.291 V**: 8 mV short of VIH max before any delay is counted |
| Latency | 0.47 µs **typical** (tPLH 310 ns typical + R429 10 kΩ × /OE node 150 ns + 6.2 ns). **No maximum exists** |
| Safe rate, VIH max (+0.3 V) | **≈ 18 V/ms on typical delays**; 4 V/ms with the document's own 2 µs budget |
| Safe rate, absolute maximum (+0.5 V) | ≈ 447 V/ms on typical delays; 104 V/ms with the 2 µs budget |
| At the 94 V/ms bound | 0.335 V (typical delay), 0.479 V (2 µs budget): **above VIH max** |

**What was wrong in revision A1:**
- The tolerance stack omitted resistor temperature drift and the comparator overdrive.
- The slope × latency term was dismissed as "only the ≤ 2 µs latency matters". Its size depends on the discharge rate, which rev A1's model capped at 9.5 V/ms.
- The 2 µs budget was itself an estimate on a typical figure.

**The claim "≤ 0.29 V at any discharge rate" is withdrawn.**

### 4.4 RP2040 GPIO transitions during reset and brownout (model §7)

**K4 brownout:**
- GP24 stays driven, equal to IOVDD, until the regulator input falls below 1.63 V and DVDD browns out [V S65].
- That is far below the trip point (≥ 2.93 V), so U402 has long been disabled.
- After the release, GP24 decays through R430 ∥ the pad pull-down. With R424 gone, nothing can raise it.

**Reset or BOOTSEL with IOVDD up:**
- GP24 is released and decays with τ = 4.2–5.6 µs (33–44 kΩ × 126 pF [E]).
- It crosses the trip point within ≤ 0.36 µs, and U402 is disabled ≤ 190 ns later (model-derived).
- Meanwhile the outputs are ≤ P3V3_S ≤ IOVDD + 35 mV, so there is nothing to protect.
- Q402 turns off within ≤ 10.9 µs (GP24 below VGS(th) min 0.5 V).

**The RP2040 never drives a pad above IOVDD,** and its pads reset to input with pull-down. Any GP24 glitch while browning out is ≤ IOVDD, and so below the trip point.

## 5. Options for more margin (rev A2 review; model §6)

These are the figures you reviewed in revision A2, at its 160 ns latency. The margin column now includes a 10 mV allowance for X4 copper (§9). "Static" is the output level above IOVDD when the trip completes, before latency. "Margin" is the lowest GP24 above the highest falling trip point in normal operation (VS 3.135 V, X4 load 176 mA). Every slope figure is a model-derived bound.

| Option | Static | Bound, VIH max | Bound, abs. max | Margin | Basis |
|---|---|---|---|---|---|
| TLV7021, 0.930 (rev A1) | 0.291 V | 18 V/ms | 447 V/ms | 0.156 V | typical delay |
| TLV7021, 0.950 (earlier threshold only) | 0.220 V | 172 V/ms | 601 V/ms | 0.094 V | typical delay |
| TLV3201 + BSS138, 0.930 (alternative comparator only) | 0.286 V | 88 V/ms | 1338 V/ms | 0.157 V | datasheet maxima + estimates |
| **TLV3201 + BSS138, 0.940 (rev A2, accepted)** | **0.250 V** | **314 V/ms** | **1564 V/ms** | **0.126 V** | datasheet maxima + estimates |
| TLV3201 + BSS138, 0.950 | 0.214 V | 535 V/ms | 1785 V/ms | 0.096 V | datasheet maxima + estimates |
| TLV3201 + BSS138, 0.960 | 0.178 V | 761 V/ms | 2011 V/ms | 0.065 V | datasheet maxima + estimates |
| TLV3201 + BSS138, 0.930, U402 B side from a 2.5 V LDO (±2 %, part not selected) | −0.323 V | 3892 V/ms | 5142 V/ms | 0.157 V | datasheet maxima + estimates |
| TLV7021, 0.930, U402 B side at 2.5 V | −0.317 V | 1325 V/ms | 1754 V/ms | 0.156 V | typical delay |

**Findings (unchanged in substance):**
1. A bound built on datasheet maxima needs a comparator with a published maximum delay. The TLV3201 is the only part found with one over temperature [S70, S72].
2. The comparator alone is not enough: at 0.930 the model gives 88 V/ms, below the 94 V/ms estimate.
3. The threshold 0.940 balances the slope bound against the normal-operation margin.
4. The 2.5 V U402 B supply gives the most margin but is a larger change. It is not drawn.

**Comparator survey:**
- **Published maximum over temperature:** TLV3201 only.
- **Maximum at 25 °C only:** TLV3011B.
- **Typical only:** TLV7011/7021, TLV9021, TLV1821, LMV7235, LMV7275, TLV1701, LMC7221, TLV4021, TLV7041 and NCS2200.
- **Not assessed:** MCP6566 and the ADI/Maxim parts (the downloads were refused).

## 6. Residual 1: U402 /OE transition rate (model §9)

In revision A2, /OE rose through R429 into about 60 pF (Q401's output capacitance dominates). That is about 37 ns/V at 1.5 V, against the ≤ 5 ns/V input transition rate in SCES693I's recommended operating conditions [V S66]. The edge occurs only on disable events.

| Option | /OE edge at 1.5 V | Disable latency | Bound, VIH max | Stack current | Power-off isolation | Assessment |
|---|---|---|---|---|---|---|
| Retain rev A2 | 37 ns/V | 160 ns | 314 V/ms | 3.5 mA | Unchanged | The deviation would stay; it would need recording and electrical qualification before manufacturing approval |
| R429 330 Ω | 12 ns/V | 120 ns | 419 V/ms | 10.7 mA | Unchanged | Still above 5 ns/V. Q401's Coss (≤ 25 pF at 10 V, more at low VDS) sets the floor; meeting 5 ns/V would need about 130 Ω (25 mA) |
| PMOS active pull-up, gate on U405's output | ~1–7 ns/V [E] | not modelled | – | 3.6 mA | Unchanged (gate-only crossing); it can only disable | Its turn-on overlaps Q401's turn-off over the BSS138 threshold spread. In the worst case the edge follows the comparator's slew through that overlap and may exceed 5 ns/V. Not guaranteed to fix the deviation |
| **U406 SN74AUP1G17 Schmitt buffer, R429 1 kΩ (drawn, rev A3)** | **≈ 0.8 ns/V [E]** | **190 ns** | **264 V/ms** | 3.5 mA | **Unchanged** (below) | Removes the deviation with about 6 × margin; +2 parts (U406, C410) |
| U406, R429 680 Ω | ≈ 0.8 ns/V [E] | 170 ns | 295 V/ms | 5.2 mA | Unchanged | Available if you want the latency back |

**Why U406 keeps the power-off isolation:**
- **Carrier side only.** U406 is supplied from +3V3, U402's VCCA. Its input is the open-drain node RP_EN_OD, pulled up to +3V3 by R429. Its output is /OE. No X4-side net touches it, so the two MOSFET gates remain the only X4-side links (the audit checks this).
- **Carrier off:** U406 is unpowered, with Ioff ≤ 0.6 µA [V S73], and U402 is VCC-isolated.
- **X4 off, carrier on:** Q401 and Q402 are off, R429 holds RP_EN_OD high, and /OE is high.
- **Carrier power ramps:** while RP_EN_OD is pulled to +3V3 by R429, U406's output follows its own supply, so /OE equals VCCA from 0.8 V up.
  - U406 is specified from 0.8 V, below U402's 1.1 V minimum VCCA.
  - TI's intent for /OE during supply ramps (held at VCCA) is therefore kept wherever both devices are specified.
  - Below 0.8 V neither device is specified [E].
- **Slow input edge:** SCES579J's recommended operating conditions set no input transition-rate limit on the Schmitt-trigger input, so RP_EN_OD's RC rise is within U406's conditions [V S73].
- **Output edge:** VOH ≥ 2.55 V at −4 mA (VCC 3 V) implies ≤ 113 Ω output resistance. Into about 12 pF (U402's Ci, TP407, trace) that is a 1.4 ns time constant, about 0.8 ns/V at 1.5 V [E from V S73].

**Trade-offs:**
- **One more active device in the disable path.** A U406 output stuck low would enable U402 whatever Q401 and Q402 do. That is a single-point fault, of the same kind a Q401 drain-source short already is for the fast path.
- **The latency rises from 160 to 190 ns,** because the Schmitt threshold (≤ 0.764 × VCC) sits above U402's VIH (2.0 V). R429 680 Ω would recover most of it, at 5.2 mA.

**Recommendation: U406 with R429 1 kΩ, drawn in revision A3, for your confirmation.** If you prefer the rev A2 circuit unchanged, the deviation is recorded here and in the design notes (F-14). Electrical qualification M-16 (b) is then required before manufacturing approval.

## 7. Revision A3 circuit (drawn on sheet 4)

| Ref | Part / value | Nets | Purpose |
|---|---|---|---|
| U402 | SN74AVC4T774 (IRQ_N, ATTN, MISO, TDO, A→B) | VCCB = X4_3V3_REF; **/OE = RP_EN_N** | Outputs toward the RP2040 |
| U405 | TI TLV3201AIDBVR | VCC X4_3V3_REF, GND; IN+ = RP_EN_SENSE (GP24), IN− = RP_EN_REF; OUT = RP_EN_CMP | High while GP24 > 0.940 × X4_3V3_REF |
| Q401 | BSS138 (BSS138-7-F) | G = RP_EN_CMP; **D = RP_EN_OD**; S = RP_EN_MID | Fast path |
| Q402 | BSS138 | G = RP_EN_GATE; D = RP_EN_MID; S = GND | Default path: off whenever GP24 is not driven |
| **U406** | **TI SN74AUP1G17DBVR** (new) | VCC +3V3, GND; **A = RP_EN_OD; Y = RP_EN_N**; pin 1 NC | Schmitt-trigger buffer: push-pull /OE edge |
| **C410** | **100 nF** (new) | +3V3 | U406 decoupling |
| R426 | 1 kΩ | X4_GP24_EN → RP_EN_SENSE | Input series resistor (RC ≤ 10 ns) |
| R427 / R428 | 6.34 kΩ / 100 kΩ, 1 % | X4_3V3_REF → RP_EN_REF → GND | IN− = 0.9404 × X4_3V3_REF (0.9385–0.9422 worst case) |
| R429 | 1 kΩ | +3V3 → **RP_EN_OD** | Pull-up of the open-drain node (U406's input). U402 is disabled unless Q401 and Q402 both conduct; the stack sinks ≤ 3.6 mA while enabled |
| R430 | 100 kΩ | X4_GP24_EN → GND | GP24 low when not driven |
| R431 | 1 kΩ | X4_GP24_EN → RP_EN_GATE | Q402 gate resistor (GP24 edge current ≤ 3.6 mA) |
| R425 | 100 kΩ | X4_GP27_ATTN → GND | ATTN reads "not ready" while U402 is disabled |
| C409 | 100 nF | X4_3V3_REF | U405 decoupling |
| TP407, TP408 | – | RP_EN_N (/OE), RP_EN_CMP | M-16 |
| *removed in rev A2* | R424 | – | §3 |

**How it works:**
- RP_EN_OD is pulled low only through Q401 and Q402 in series, and U406 copies it onto /OE.
- **Q401** is the fast path, switched by U405.
- **Q402** sets the default state. Its gate is GP24 itself, held at 0 V by R430 whenever the RP2040 does not drive it; at VGS = 0 a BSS138 is off (IDSS ≤ 0.5 µA) whatever the comparator does.
- Q402 sits at GND, below Q401, so the enable node's swing never couples into GP24.

**Domain crossings:**
- The comparator, its inputs and both gates are on the X4 side. RP_EN_OD, RP_EN_MID, R429, U406, /OE and both MOSFET channels are on the carrier side.
- The only links are the two insulated MOSFET gates, and the audit checks that no other part bridges them.
- The TLV3201's input clamps see only X4-side nets. R426 limits the worst case, during X4 power-down, to ≤ 0.6 mA.

**ER-3:** X4_3V3_REF static load ≤ 131 µA (U405 ≤ 65 µA, divider ≤ 34 µA, 4 × ICCB ≤ 8 µA), unchanged; U406 is on +3V3.

## 8. Model-derived bounds (revision A3; model §5, §5b)

**Trip band** (GP24 falling, all tolerances): 0.9385 × VS − 16.6 mV to 0.9422 × VS + 6.6 mV.
- VS 3.135 V: 2.926–2.960 V;
- VS 3.300 V: 3.080–3.116 V;
- VS 3.465 V: 3.235–3.271 V.

**Disable latency**, counted from the moment the comparator input passes 20 mV beyond its trip point:

| Term | Value | Basis |
|---|---|---|
| GP24 pad follows IOVDD (85 Ω × 50 pF) | 4.2 ns | [E] |
| R426 × comparator input (1.0165 kΩ × 10 pF) | 10.2 ns | [V S70] typical input capacitance + trace [E] |
| TLV3201 tPD (20 mV overdrive, CL 15 pF, −40 to 125 °C) | 55.0 ns | [V S70] maximum. The −40 to 125 °C row (55 ns) does not restate the overdrive; it is read as extending the 50 ns rows above it |
| Q401 gate: (Ciss + 2 × Crss) maxima × 3.465 V / 10 mA sink | 22.9 ns | [V S71] maxima; sink current derated from 13 mA [E] |
| R429 × RP_EN_OD to U406 VT+: 1.0165 kΩ × (2 × Coss + U406 Ci 3 pF + 5 pF = 58 pF) × ln(1 / (1 − 0.764)) | 85.0 ns | [V S71] Coss, doubled for low VDS [E]. VT+ ≤ 2.29 V at VCC 3 V [V S73], scaled with VCC to 3.465 V [E] |
| U406 tPD (CL 15 pF, VCC 3.3 V ± 0.3 V, −40 to 85 °C) | 6.2 ns | [V S73] maximum |
| U402 OE → B disable | 6.2 ns | [V S66] maximum |
| **Total** | **≤ 190 ns** (rounded up) | **Model-derived** |

| Result (model-derived; assumptions in §4.1 and above) | Value |
|---|---|
| Static excursion (VS 3.465 V, lowest k, offsets, overdrive) | 0.250 V above IOVDD |
| **Bound on the IOVDD slope for VIH max (+0.3 V)** | **≤ 264 V/ms: 2.8 × the 94 V/ms estimate** |
| **Bound for the absolute maximum (+0.5 V)** | **≤ 1317 V/ms: 14.0 × the estimate** |
| Peak at the estimate | 0.268 V above IOVDD at 94 V/ms (0.269 V at 100 V/ms), reached as U402 goes Hi-Z (IOZ ≤ 5 µA) |
| Sensitivity: latency 2 × / 5 × the budget | VIH-max bound 132 / 52 V/ms |
| /OE edge (U406 output) | ≈ 0.8 ns/V [E]: within SCES693I's 5 ns/V |
| Normal-operation GP24 margin | §9 |

**Cross-check:** a time-stepped simulation (1 ns steps, input RC modelled) agrees with the closed form: 0.269 / 0.300 / 0.307 V at 100 / 264 / 300 V/ms (model §5b).

**What is claimed, and on what basis:**
- **Model-derived bounds**, not manufacturer guarantees: outputs stay below IOVDD + 0.3 V for IOVDD discharge rates ≤ 264 V/ms, and below IOVDD + 0.5 V for ≤ 1317 V/ms. They rest on:
  - datasheet maxima for the TLV3201, BSS138, SN74AUP1G17 and SN74AVC4T774 timings and capacitances;
  - the estimates: the overdrive-on-a-ramp argument, node and trace capacitances, the doubled Coss at low VDS, the TLV3201 sink current and hysteresis, U406's VT+ scaling, the GP24 pad resistance;
  - the assumptions: P3V3_S and +3V3 within ±5 %, 1 % resistors at ≤ 100 ppm/K.
- **The X4 slope estimate** (≤ 94 V/ms) rests on its own estimates: C206's derating and the maximum P3V_RP load (§4.2).
- **M-16 must confirm** both: the latency on the bench (b), and the slope on the X4 (c).
- **Not claimed:** faster collapses, such as a short on P3V_RP.

## 9. Residual 3: GP24 HIGH-level margin (model §10)

**The margin** is GP24's HIGH level minus the comparator's highest falling trip point (0.9422 × VS + 6.6 mV), with no hysteresis credit. For re-enabling, the rising trip point adds the hysteresis (≤ 10 mV [E]).

**GP24's HIGH level** = P3V3_S − Q32 drop − X4 copper − pad drop. The pad carries only ≤ 36 µA (R430, R426 and R431 see gates and the comparator input).

| Condition | GP24 HIGH | Falling trip | Margin | Re-enable margin |
|---|---|---|---|---|
| **Representative:** VS 3.300 V, X4 load 30 mA, 8 mA drive, typical offsets and nominal divider | 3.292 V | 3.105 V | **0.186 V** | – |
| **Worst, FW-1 drive:** VS 3.135 V, 176 mA (Q32 35 mV + copper 10 mV), 8 mA drive, ±1.65 % resistors, maximum offsets | ≥ 3.087 V | ≤ 2.960 V | **≥ 0.126 V** | ≥ 0.116 V |
| Worst, weakest drive (2 mA, if firmware leaves it there) | ≥ 3.078 V | ≤ 2.960 V | ≥ 0.117 V | ≥ 0.107 V |
| Worst at VS 3.465 V, 8 mA drive | ≥ 3.417 V | ≤ 3.271 V | ≥ 0.145 V | ≥ 0.135 V |

**What moves it:**
- **The supply tolerance enters only through (1 − k) × VS**, because the threshold is ratiometric. The lowest supply is the worst case.
- **X4 load,** through Q32 (≤ 35 mV at 176 mA [E]) and copper (≤ 10 mV [E]).
- **The pad drop:** ≤ 3 mV at the FW-1 drive, ≤ 12 mV at 2 mA. The drive setting barely matters, because GP24's static load is microamps.
- **Resistor tolerance and drift:** k up to 0.9422.
- **Comparator offset and CMRR** (6.6 mV), and hysteresis on re-enable.
- **Ground offset between the X4 and the carrier:** it costs only (1 − k) × ΔG = 0.06 × ΔG, ≤ 3 mV for 50 mV [E].

**Dynamic contributors (estimated, not bounded):**
- **P3V3_S transients.** The threshold follows X4_3V3_REF at once, while IOVDD follows through Q32 × C_RP (about 2 µs [E]).
  - A P3V3_S overshoot faster than that briefly costs up to 0.94 × its size.
  - More than about 0.13 V at once (4 % of 3.3 V) could cause a momentary false disable.
- **Ribbon crosstalk.** GP24 (conductor 22) lies between MISO (21) and SCK (23), with no ground conductor between them.
  - Spikes of a few nanoseconds are attenuated by R426 × C_in (≥ 5.9 ns [E]): a 2 ns spike reaches the comparator input at about 0.29 of its amplitude.
  - The comparator's own response is about 40 ns typical [S70].

**Conclusion:**
- **The static margin is adequate:** ≥ 0.126 V with FW-1, ≥ 0.117 V at any drive setting, 0.186 V representative.
- **A false disable fails safe.** U402 goes Hi-Z, the frame fails its CRC and the RP2040 retries (protocol §8). It is never a protection failure, but it would cost link reliability.
- **M-16 (f) and (g)** measure the margin and count false disables under traffic, X4 load and temperature.
- **If (f) finds false disables,** the layout-stage remedy is a 10–22 pF capacitor on RP_EN_SENSE. It adds 10–22 ns of latency; the VIH-max bound becomes 237–251 V/ms. It is not drawn.

## 10. States

| State | GP24 | U405 OUT | Q402 / Q401 | RP_EN_OD → /OE (U406) | Outputs at the RP2040 |
|---|---|---|---|---|---|
| RP2040 running, firmware has raised GP24 | ≈ IOVDD | High | On / on | Low → low: enabled | Driven, ≤ P3V3_S ≈ IOVDD + Q32 drop |
| **K4 pressed** (IOVDD collapsing, P3V3_S up) | Follows IOVDD down (≤ IOVDD) | Low | On / **off** | Rises → **high ≤ 190 ns** after the input passes trip − 20 mV | ≤ +0.25 V statically, ≤ +0.269 V at 100 V/ms (model); Hi-Z after |
| RP2040 in reset or BOOTSEL; firmware not started | Low (pad, R430) | Low | **Off** / off | High → high | Hi-Z; ATTN low (R425); IRQ_N low through the pad's reset pull-down, with nobody listening (§3.3) |
| X4 powering up (U405 below 2.7 V, unspecified) | Low (R430) | Unspecified | **Off** / – | High → high | Hi-Z |
| X4 off (P3V3_S = 0) | 0 | 0 | Off / off | High → high; U402 VCC isolation as well | Hi-Z (Ioff) |
| Carrier off, X4 running | High | High | On / on | U406 unpowered (Ioff); U402 VCC-isolated (VCCA = 0) | Hi-Z; IRQ_N high (pull-up, FW-6), ATTN low (R425) |
| Carrier powering up, X4 off or GP24 low | Low or 0 | – | Off | R429 holds RP_EN_OD at VCCA; U406 output = VCCA from 0.8 V up → /OE high | Hi-Z |
| Carrier powering up, firmware running | High | High | On / on | Low → low: enabled while VCCA ramps | Glitches possible, bounded by P3V3_S ≈ IOVDD: no back-feed; the link is down until IDENTIFY |
| Firmware isolates on purpose (GP24 low) | Low | Low | Off / off | High → high | Hi-Z |

## 11. Firmware (FW-1 and FW-6; design notes §9)

- **FW-6:**
  1. GP22 input with pull-up on and pull-down off.
  2. Then GP24 high.
  3. Wait ≥ 10 µs.
  4. Clear pending GP22 events.
  5. Then enable the GP22 interrupt.
- **FW-1:** GP24 output high with an 8 mA or 12 mA drive setting.
  - The static load is ≤ 36 µA. Each GP24 edge draws ≤ 7.1 mA for under 100 ns (R426, R431).
  - The enable follows within about 0.3 µs, so the ≥ 10 µs wait is generous.
  - Driving GP24 low isolates U402 on purpose.

## 12. Verification and M-16

| Check | Result |
|---|---|
| Netlist audit `audit_sheet4.py` | **220 checks, 0 failures**. New in rev A3: U406's pins (NC pin open), RP_EN_OD = Q401 drain, R429, U406 input; RP_EN_N (/OE) = U406 output and TP407 only; 5 + 5 decoupling; the gate-only crossing now covers RP_EN_OD too |
| Audit mutation test | **29 of 29** injected faults detected. New: U406 bypassed (/OE on RP_EN_OD), U406 supplied from the X4 3.3 V, R429 on /OE instead of U406's input, C410 moved to the X4 rail |
| ERC | 51 entries, identical to rev A2 apart from coordinates ([sheet4-erc-report.md](sheet4-erc-report.md)) |
| Other sheets | Netlist identical outside sheet 4. Audits 418 / 1105 / 159; sheet 2's +2 checks are the new net RP_EN_OD and U406's unconnected NC pin, passing its "not reused on another sheet" check |
| HDL | No RTL change since rev A2. `run_checks.sh` passed on the rev A2 tree, whose `hdl/` is identical |
| Model | §1–§10 numbers from `tools/analysis/k4_transient.py` |

**M-16 (revised): S4-6 electrical qualification on hardware.** Carrier powered, FPGA configured, then repeated with the FPGA blank. **Manufacturing approval requires all of (a)–(g).**

| Step | Procedure | Pass |
|---|---|---|
| a. Trip points | Carrier on, X4 disconnected. Drive J401 pin 22 (GP24) with a slow ramp, down and up, and pins 1/17 from a bench supply at 3.135, 3.300 and 3.465 V | TP408 and TP407 switch, falling, within **0.9385 × VS − 17 mV to 0.9422 × VS + 7 mV**. The rising (re-enable) point is recorded |
| b. **Falling-ramp comparator response and full translator disable time** | As (a). A 100 mV step, then falling ramps of 100 V/ms and 300 V/ms through the trip point. Each of U402's B outputs (header pins 16, 18, 21, 38) is held at a defined level by the FPGA, with a 10 kΩ load to the opposite rail, so the moment it goes Hi-Z is visible | From GP24 passing trip − 20 mV: TP408 (comparator) recorded; **TP407 (/OE) high, and every B output Hi-Z, ≤ 190 ns**; /OE edge ≤ 5 ns/V; no chatter on the B outputs |
| c. K4 on the X4 | Scope P3V_RP (at C206), GP24, TP408, TP407, and IRQ_N/ATTN/MISO at the header while holding K4; repeat ≥ 20 times | Measured IOVDD slope ≤ 94 V/ms (else revisit §4.2 and §8); **no RP2040 pin above IOVDD + 0.3 V at any time**; clean RP2040 power cycle |
| d. Defaults | RP2040 reset, BOOTSEL, before firmware; X4 power-up with the carrier on; carrier power-up with the X4 off; X4 off | TP407 high throughout, including during both ramps |
| e. Interrupt idle state | Boot with FW-6; carrier off and on with the X4 running | No interrupt taken during boot; IRQ_N ≥ 2.0 V and ATTN low at the header with the carrier off; any interrupt during a carrier ramp ends in a clean LINK_DOWN or IDENTIFY |
| f. Noise | Sustained SRAM_READ traffic at 10 MHz and at 20 MHz (early-launch build), with the X4 CPU and USB loaded and load steps applied | No TP408 or TP407 glitch, triggering on edges for ≥ 10 min |
| g. **GP24 HIGH-level margin** | X4 idle and loaded; ambient and the available temperature extremes; the X4 supply as delivered. Measure GP24 and X4_3V3_REF at the carrier | **GP24 − 0.9404 × X4_3V3_REF ≥ 0.126 V**, the model's worst case; below that, the §9 assumptions are revisited |

## 13. Open items (nothing closed)

- **Your confirmation of U406 (rev A3)** as the improvement for residual 1. Alternatively, keep rev A2 unchanged, with the deviation recorded (§6) and qualified.
- **Electrical qualification M-16 (a)–(g)** before manufacturing approval.
- **R-52** (Mitigating): the link depends on firmware driving GP24 and on U405, Q401, Q402 and U406. If firmware does not raise GP24, U402 stays disabled.
- **Estimates to confirm on hardware:** C_eff and the P3V_RP load (§4.2); TLV3201 hysteresis; node capacitances; U406's VT+ at 3.3 V; the Q32 and copper drops; P3V3_S tolerance [A].
- **Options held back:**
  - R429 680 Ω (bound 295 V/ms);
  - the 2.5 V U402 B supply (§5);
  - an RP_EN_SENSE filter capacitor, if M-16 (f) finds false disables (§9).
