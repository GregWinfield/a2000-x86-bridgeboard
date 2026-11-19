# Sheet 4: S4-6, isolating the FPGA → RP2040 outputs (revision A2)

**Status:** 2026-11-19. This is the response to your review of PR #8. You provisionally accepted the comparator-gated architecture of revision A1, with two concerns.

| Your concern | Finding | Revision A2 |
|---|---|---|
| **1. R424 reverse-current path** (U402 IRQ_N → GP22 → R424 → GP24) | **Confirmed.** While U402 drives IRQ_N high, R424 feeds current into GP24 and from there into the collapsing IOVDD. After the RP2040 releases GP24, R424 can hold GP24 above IOVDD. The model's assumption "GP24 follows IOVDD" did not hold (§3) | **R424 removed.** Firmware enables the RP2040's own GP22 pull-up before it raises GP24 or enables the interrupt (FW-6). Nothing on the carrier can now source current into GP24, so **GP24 ≤ IOVDD at all times**. Idle state verified in every state (§3.3) |
| **2. Comparator timing** (TLV7021: typical delay only) | **Confirmed, and worse than stated.** With worst-case tolerances, revision A1's static margin to VIH max is 8 mV. It stays within VIH max only up to about 18 V/ms even on *typical* delays, and no guaranteed bound exists. **The revision A1 statement "≤ 0.29 V above IOVDD at any discharge rate" was wrong and is withdrawn** (§4.3) | **U405 is a TI TLV3201:** tPD ≤ 55 ns guaranteed over −40 to 125 °C. It drives **Q401**, a BSS138 in series with **Q402**, a BSS138 switched by GP24 itself. **Threshold raised to 0.940 × the header 3.3 V.** Guaranteed protection up to **314 V/ms** (VIH max) and **1564 V/ms** (absolute maximum). The estimated X4 worst case is **≤ 94 V/ms** (§5–§7) |

**Not validated.** Hardware check M-16 (§10) remains open, with every other hardware gate. No PCB manufacture is authorised.

**Reproducible model:** [../../tools/analysis/k4_transient.py](../../tools/analysis/k4_transient.py) (`python -I tools/analysis/k4_transient.py`). Section numbers "model §n" refer to its printed sections.

**Tags:**
- [V Sxx] datasheet value;
- [E] estimate;
- [A] assumption.

Rounding follows your rule: maxima and requirements round up; margins, slacks and minima round down.

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
- the only exposure is the guaranteed latency after IOVDD crosses that point (§7).

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
| K4 (IOVDD collapsing) | Falls with IOVDD / disabled ≤ 160 ns after the trip | Irrelevant: the RP2040 is losing power | – |
| X4 off | 0 / VCCB = 0 | – | – |

## 4. Concern 2: the power-down analysis rerun

### 4.1 Worst-case parameters

| Parameter | Value used | Source |
|---|---|---|
| X4_3V3_REF (P3V3_S) | 3.135–3.465 V | [A] ±5 % |
| Carrier +3V3 (VCCA, R429) | ≥ 3.135 V | [A] |
| Resistors | 1 % plus 100 ppm/K from 25 °C to −40/+85 °C: **±1.65 % each, not tracking** | [A] BOM specification |
| Comparator offset | TLV3201: VIO 4 mV + CMRR 2.6 mV (56 dB over a 1.6 V shift from VCC/2) + hysteresis 10 mV = **16.6 mV**. TLV7021: 8 + 14 = 22 mV | [V S70] except the hysteresis: 1.2 mV typical, no limit; 10 mV [E]. [V S68] |
| Overdrive | The comparator must see **20 mV past its trip point** before its guaranteed tPD applies. On a ramp this costs 20 mV of IOVDD | [V S70] test condition; ramp argument [E] |
| Comparator delay | TLV3201 ≤ 55 ns (guaranteed). TLV7021 310 ns *typical* (no maximum) | [V S70], [V S68] |
| C_eff of P3V_RP | **≥ 1.887 µF**. C206: 25 % retained at 3.3 V DC bias (0402 X5R 6.3 V worst case, as the size is not shown), −20 %, −15 % (X5R), −5 % aging: × 0.162. The 0.1 µF parts: × 0.544 | [E] |
| P3V_RP load | **≤ 176 mA**: IOVDD 50 mA (IIOVDD_MAX), VREG 100 mA (rated output), flash 25 mA, ADC 1 mA | [V S65] for 150 mA; flash and ADC [E] |
| Q32 drop | ≤ 35 mV (176 mA × 0.2 Ω) | [E] |
| GP24 pad | ≤ 85 Ω (from VOH ≥ 2.62 V at 8 mA): ≤ 3 mV at 36 µA | [V S65 → E] |

### 4.2 Discharge rate

After K4, assuming Q32 opens instantly (model §1), the worst case is **176 mA / 1.887 µF = 93.3 V/ms**, rounded up to **94 V/ms [E]**.

For comparison, revision A1's model used the undegraded 10.5 µF and 5–100 mA: 0.48–9.52 V/ms. The new bound is ten times faster than revision A1's fastest case.

In practice Q32's gate has no pull-up and rises only by leakage, so a real K4 turn-off is probably much slower. **Nothing below relies on that.**

**Not covered:** a fault that collapses P3V_RP faster than the bounds in §7, such as a short on the X4. The design makes no claim there.

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
- It crosses the trip point within ≤ 0.36 µs, and U402 is disabled 160 ns later.
- Meanwhile the outputs are ≤ P3V3_S ≤ IOVDD + 35 mV, so there is nothing to protect.
- Q402 turns off within ≤ 10.9 µs (GP24 below VGS(th) min 0.5 V).

**The RP2040 never drives a pad above IOVDD,** and its pads reset to input with pull-down. Any GP24 glitch while browning out is ≤ IOVDD, and so below the trip point.

## 5. Options for more margin (your three questions; model §6)

Same worst-case arithmetic for every row. "Static" is the output level above IOVDD when the trip completes, before latency. "Margin" is the lowest GP24 above the highest falling trip point in normal operation (VS 3.135 V, Q32 at 176 mA).

| Option | Static | Safe rate, VIH max | Safe rate, abs. max | Margin | Basis |
|---|---|---|---|---|---|
| TLV7021, 0.930 (rev A1) | 0.291 V | 18 V/ms | 447 V/ms | 0.166 V | typical delay |
| TLV7021, 0.950 (**earlier threshold only**) | 0.220 V | 172 V/ms | 601 V/ms | 0.104 V | typical delay |
| TLV3201 + BSS138, 0.930 (**alternative comparator only**) | 0.286 V | 88 V/ms | 1338 V/ms | 0.167 V | guaranteed |
| **TLV3201 + BSS138, 0.940 (rev A2)** | **0.250 V** | **314 V/ms** | **1564 V/ms** | **0.136 V** | **guaranteed** |
| TLV3201 + BSS138, 0.950 | 0.214 V | 535 V/ms | 1785 V/ms | 0.106 V | guaranteed |
| TLV3201 + BSS138, 0.960 | 0.178 V | 761 V/ms | 2011 V/ms | 0.075 V | guaranteed |
| TLV3201 + BSS138, 0.930, **U402 B side from a 2.5 V LDO** (±2 %, part not selected) | −0.323 V | 3892 V/ms | 5142 V/ms | 0.167 V | guaranteed |
| TLV7021, 0.930, U402 B side at 2.5 V | −0.317 V | 1325 V/ms | 1754 V/ms | 0.166 V | typical delay |

**Findings:**
1. **A guaranteed bound needs a comparator with a guaranteed maximum delay.** No threshold or supply arrangement turns the TLV7021's typical figure into a guarantee.
2. **The comparator alone is not enough.** At 0.930 the static excursion leaves only 14 mV of the 0.3 V budget. With the TLV3201 that gives 88 V/ms, below the 94 V/ms bound.
3. **An earlier threshold buys the margin.** Each 0.01 of k gives back about 35 mV, at the cost of about 30 mV of noise margin in normal operation:
   - 0.940 gives 3.3 × the bound with 0.136 V of margin;
   - 0.950 gives 5.7 × with 0.106 V;
   - 0.960 leaves only 0.075 V against ribbon noise.
4. **A lower U402 B supply** (an LDO at 2.5 V) gives by far the most margin, but it is a larger change:
   - one more IC and two capacitors;
   - U402 moves to the SCES693I 2.5 V column (MISO 3.3 ns instead of 2.9 ns);
   - the RP2040's VIH margin falls to about 0.25 V.

   It is **not drawn**. It remains available if you want protection at much faster rates.

**Recommended and drawn:** TLV3201 + BSS138 pair at **0.940**.

**Comparator survey.** Open-drain and low-power parts checked for a maximum propagation delay [S68, S70, S72]:
- **Guaranteed maximum:**
  - TLV3201, 55 ns over −40 to 125 °C (push-pull);
  - TLV3011B, 4 µs at 25 °C only (too slow, no temperature limit).
- **Typical only:** TLV7011/7021, TLV9021, TLV1821, LMV7235, LMV7275, TLV1701, LMC7221, TLV4021, TLV7041, onsemi NCS2200.
- **Not assessed:** Microchip MCP6566, and ADI/Maxim parts. Their sites refuse automated downloads here, so nothing is claimed for them.

The TLV3201's push-pull output is why Q401 is needed: it keeps revision A1's domain crossing (§6).

## 6. Revision A2 circuit (drawn on sheet 4)

| Ref | Part / value | Nets | Purpose |
|---|---|---|---|
| U402 | SN74AVC4T774 (unchanged: IRQ_N, ATTN, MISO, TDO, A→B) | VCCB = X4_3V3_REF; **/OE = RP_EN_N** | Outputs toward the RP2040 |
| **U405** | **TI TLV3201AIDBVR** (replaces the TLV7021; same SOT-23-5 pinout) | VCC X4_3V3_REF, GND; **IN+ = RP_EN_SENSE (GP24), IN− = RP_EN_REF**; OUT = RP_EN_CMP | High while GP24 > 0.940 × X4_3V3_REF |
| **Q401** | **BSS138** (Diodes BSS138-7-F) | G = RP_EN_CMP; D = RP_EN_N; S = RP_EN_MID | Fast path: pulls /OE low only while U405 says GP24 is high enough |
| **Q402** | **BSS138** | G = RP_EN_GATE; D = RP_EN_MID; S = GND | Default path: conducts only while GP24 is driven high. U402 stays disabled whenever GP24 is not driven, whatever U405 does below its 2.7 V minimum supply (e.g. while the X4 powers up) |
| R426 | **1 kΩ** (was 10 kΩ) | X4_GP24_EN → RP_EN_SENSE | Input series resistor: RC ≤ 10 ns |
| R427 / R428 | **6.34 kΩ** (was 7.5 kΩ) / 100 kΩ, 1 % | X4_3V3_REF → RP_EN_REF → GND | IN− = 100 / 106.34 = **0.9404** × X4_3V3_REF (0.9385–0.9422 worst case) |
| R429 | **1 kΩ** (was 10 kΩ) | +3V3 → RP_EN_N | /OE pull-up to VCCA (TI's recommendation): disabled unless Q401 and Q402 both conduct. The stack sinks ≤ 3.6 mA from the carrier while enabled |
| R430 | 100 kΩ (unchanged) | X4_GP24_EN → GND | GP24 low when not driven |
| **R431** | **1 kΩ** (new) | X4_GP24_EN → RP_EN_GATE | Q402 gate resistor: GP24 edge current ≤ 3.6 mA |
| R425 | 100 kΩ (unchanged) | X4_GP27_ATTN → GND | ATTN reads "not ready" while U402 is disabled |
| C409 | 100 nF (unchanged) | X4_3V3_REF | U405 decoupling |
| TP407, **TP408** | – | RP_EN_N, **RP_EN_CMP** | M-16: /OE and the comparator output |
| *removed* | **R424** | – | §3 |

**How it works:**
- /OE is pulled low only through Q401 and Q402 in series.
- **Q401** is the fast path: U405's guaranteed-delay output switches it.
- **Q402** guarantees the default: its gate is GP24 itself, held at 0 V by R430 whenever the RP2040 does not drive it. At VGS = 0 a BSS138 is off (IDSS ≤ 0.5 µA) whatever the comparator does.
- Q402 sits at GND, below Q401, so /OE's swing never couples into GP24.

**Domain crossings:**
- The comparator, its inputs and both gates are in the X4 domain. The /OE node, R429 and both channels are in the carrier domain.
- The **only links between them are the two MOSFET gates.** They are insulated, apart from Cgd charge of a few pC. The audit checks that no other part bridges them.
  - With the X4 off, R429's current has nowhere to go: both channels are off and both body diodes are reverse-biased.
  - With the carrier off, the channels only connect /OE to GND, and U402 is isolated by VCC isolation.
- This replaces revision A1's open-drain-output argument and keeps the same property.
- The TLV3201's input clamps (to both rails) see only X4-domain nets. The worst current flows during X4 power-down, when GP24 can exceed X4_3V3_REF by at most Q32's body-diode drop. R426 limits it to ≤ 0.6 mA, against the 10 mA rating.

**ER-3:** X4_3V3_REF static load ≤ 131 µA:
- U405 ≤ 65 µA;
- the divider ≤ 34 µA;
- 4 × ICCB ≤ 8 µA each;
- J401, TP405 and decoupling.

Revision A1 was ≤ 73 µA. The only resistor on the rail is still R427.

## 7. Guaranteed bounds (model §5)

**Trip band** (GP24 falling, all tolerances): 0.9385 × VS − 16.6 mV to 0.9422 × VS + 6.6 mV.
- VS 3.135 V: 2.926–2.960 V;
- VS 3.300 V: 3.080–3.116 V;
- VS 3.465 V: 3.235–3.271 V.

**Latency budget**, from the moment the comparator input passes 20 mV beyond its trip point:

| Term | Value | Basis |
|---|---|---|
| GP24 pad follows IOVDD (85 Ω × 50 pF) | 4.2 ns | [E] |
| R426 × comparator input (1.0165 kΩ × 10 pF) | 10.2 ns | [V S70] typical input capacitance + trace [E] |
| **TLV3201 tPD** (20 mV overdrive, CL 15 pF, −40 to 125 °C) | **55.0 ns** | **[V S70] maximum**. The table gives ≤ 50 ns for 20 and 100 mV overdrive at 15 pF, then a row "TA = −40 to 125 °C: 55 ns" that does not restate the overdrive. It is read here as extending the rows above it |
| Q401 gate: (Ciss + 2 × Crss) maxima × 3.465 V / 10 mA sink | 22.9 ns | [V S71] maxima; sink current derated from 13 mA [E] |
| R429 × /OE node to VIH 2.0 V: 1.0165 kΩ × (2 × Coss + Ci + 5 pF = 59.5 pF) × ln(3.135 / 1.135) | 61.4 ns | [V S66, S71] maxima; Coss doubled for low VDS, trace [E] |
| U402 OE → B disable | 6.2 ns | [V S66] maximum |
| **Total** | **≤ 160 ns** (rounded up) | |

| Result | Value |
|---|---|
| Static excursion (VS 3.465 V, lowest k, offsets, overdrive) | 0.250 V above IOVDD |
| **Safe rate for VIH max (+0.3 V)** | **≤ 314 V/ms: 3.3 × the 94 V/ms bound** |
| **Safe rate for the absolute maximum (+0.5 V)** | **≤ 1564 V/ms: 16.6 × the bound** |
| Peak at the bound | 0.265 V above IOVDD at 94 V/ms (0.266 V at 100 V/ms), reached as U402 goes Hi-Z (IOZ ≤ 5 µA) |
| Normal-operation margin (VS 3.135 V, Q32 at 176 mA) | **≥ 0.136 V** falling; ≥ 0.126 V to re-enable (rising, with hysteresis) |
| Sensitivity: latency 2 × / 5 × the budget | safe rate (VIH max) 157 / 62 V/ms |

**Cross-check:** a time-stepped simulation (1 ns steps, input RC modelled) matches the closed form to 1 mV from 1 to 2000 V/ms (model §5).

**Claims and their basis:**
- **Guaranteed by datasheet maxima** under the stated estimates:
  - outputs never exceed IOVDD + 0.3 V for IOVDD discharge rates ≤ 314 V/ms;
  - outputs never exceed IOVDD + 0.5 V for rates ≤ 1564 V/ms.
- **The estimates** (§4.1, tagged [E]) are C_eff and the load, the TLV3201's hysteresis, the node capacitances, the overdrive-on-a-ramp argument and the Q32 drop. M-16 measures the ones that matter.
- **Not claimed:** faster rates, such as a short on P3V_RP.

**One deviation from the recommended conditions, flagged (also present in rev A1, not reported then):**
- /OE rises through R429 as an RC edge: ≤ 60 ns time constant, about 37 ns/V at 1.5 V.
- SCES693I recommends ≤ 5 ns/V on inputs [V S66].
- This is inherent in TI's own pull-up recommendation for /OE. Revision A1's 10 kΩ was ten times slower.
- The budget runs to VIH 2.0 V, so any enable chatter near the threshold is inside the 160 ns, and the final state is Hi-Z.
- M-16 checks the /OE edge and the outputs during it.

## 8. States

| State | GP24 | U405 OUT | Q402 / Q401 | U402 | Outputs at the RP2040 |
|---|---|---|---|---|---|
| RP2040 running, firmware has raised GP24 | ≈ IOVDD | High | On / on | Enabled | Driven, ≤ P3V3_S ≈ IOVDD + Q32 drop |
| **K4 pressed** (IOVDD collapsing, P3V3_S up) | Follows IOVDD down (≤ IOVDD) | Low; Q401 off ≤ 93 ns after the input passes trip − 20 mV | On / **off** | **Disabled ≤ 160 ns after that** | ≤ +0.25 V statically, ≤ +0.266 V at 100 V/ms; Hi-Z after |
| RP2040 in reset or BOOTSEL; firmware not started | Low (pad, R430) | Low | **Off** / off | Disabled | Hi-Z; ATTN low (R425); IRQ_N low through the pad's reset pull-down, with nobody listening (§3.3) |
| X4 powering up (U405 below 2.7 V, unspecified) | Low (R430) | Unspecified | **Off** / – | Disabled (R429 holds /OE at VCCA) | Hi-Z |
| X4 off (P3V3_S = 0) | 0 | 0 | Off / off | VCC isolation; /OE high | Hi-Z (Ioff) |
| Carrier off, X4 running | High | High | On / on (/OE node at 0 V, VCCA = 0) | VCC isolation | Hi-Z; IRQ_N high (pull-up, FW-6), ATTN low (R425) |
| Carrier powering up, firmware running | High | High | On / on | Enabled while VCCA ramps | Glitches possible, bounded by P3V3_S ≈ IOVDD: no back-feed; the link is down until IDENTIFY |
| Firmware isolates on purpose (GP24 low) | Low | Low | Off / off | Disabled | Hi-Z |

## 9. Firmware (rules FW-1 and FW-6 revised; design notes §9)

- **FW-6 (new order):**
  1. GP22 input with pull-up on and pull-down off.
  2. Then GP24 high.
  3. Wait ≥ 10 µs.
  4. Clear pending GP22 events.
  5. Then enable the GP22 interrupt.
- **FW-1:** GP24 output high with an 8 mA or 12 mA drive setting, which keeps the pad drop ≤ 3 mV at the 36 µA static load. Each GP24 edge draws ≤ 7.1 mA for under 100 ns (R426, R431). The enable follows within about 0.2 µs, so the ≥ 10 µs wait is generous. Driving GP24 low isolates U402 on purpose.

## 10. Verification

| Check | Result |
|---|---|
| Netlist audit `audit_sheet4.py` | **213 checks, 0 failures**. New checks: U405 and Q401/Q402 pins; RP_EN_N, RP_EN_MID, RP_EN_CMP and RP_EN_GATE members; the 0.940 ratio; X4_GP24_EN has exactly J401, R426, R430 and R431; IRQ_N has no resistor; only the MOSFET gates bridge the X4 side and /OE |
| Audit mutation test | **25 of 25** injected faults detected. New since rev A1: R424 path re-created, IRQ_N pulled to the header 3.3 V, Q402 bypassed, Q402 gate on the comparator, Q401 drain and source swapped, a resistor from the X4 side onto /OE, R429 or R426 at the old 10 kΩ, U405 a TLV7021 |
| ERC | 51 entries, identical to rev A1 apart from coordinates ([sheet4-erc-report.md](sheet4-erc-report.md)) |
| Other sheets | Netlist identical outside sheet 4; audits 418 / 1103 / 159. Sheet 2's 3 extra checks are the new net names passing its "not reused on another sheet" check |
| HDL | No RTL change; `run_checks.sh` on this tree: **ALL HDL CHECKS PASSED** (39 testbench runs, 9 formal tasks) |
| Model | §2–§7 numbers from `tools/analysis/k4_transient.py` |

**M-16 (revised): S4-6 on hardware.** Carrier powered, FPGA configured, then repeated with the FPGA blank.

| Step | Procedure | Pass |
|---|---|---|
| a. Trip point | Carrier on, X4 disconnected. Drive J401 pin 22 (GP24) from a slow ramp generator and pins 1/17 from a bench supply at 3.135, 3.300 and 3.465 V | TP408 and TP407 switch at **0.9385 × VS − 17 mV to 0.9422 × VS + 7 mV** (falling) |
| b. Latency | As (a), with a 100 mV step and with ramps of 100 V/ms and 300 V/ms through the trip point | From GP24 passing trip − 20 mV to TP407 reaching 2.0 V: **≤ 160 ns**. TP407's edge recorded, and U402's B outputs checked for chatter during it |
| c. K4 on the X4 | Scope P3V_RP (at C206), GP24, TP408, TP407, and IRQ_N/ATTN/MISO at the header while holding K4; repeat ≥ 20 times | Measured IOVDD slope **≤ 94 V/ms** (else revisit §4.2); **no RP2040 pin above IOVDD + 0.3 V at any time**; clean RP2040 power cycle |
| d. Defaults | RP2040 reset, BOOTSEL, before firmware; X4 power-up with the carrier on; X4 off | TP407 high throughout (including during the X4 ramp) |
| e. Interrupt idle state | Boot with FW-6; carrier off and on with the X4 running | No interrupt taken during boot; IRQ_N ≥ 2.0 V and ATTN low at the header with the carrier off; any interrupt during a carrier ramp ends in a clean LINK_DOWN or IDENTIFY |
| f. Noise | Sustained SRAM_READ traffic at 10 MHz and at 20 MHz (early-launch build), with the X4 CPU loaded | No TP407 glitch, triggering on rising edges for ≥ 10 min; GP24 minus trip ≥ 0.136 V |

## 11. Open items (nothing closed)

- **Your acceptance of the revision A2 S4-6 circuit**, for final sheet-4 schematic approval.
- **R-52** (Mitigating): the link depends on firmware driving GP24 and on U405/Q401/Q402. It is fail-safe in both directions: if firmware does not raise GP24, U402 stays disabled and the link is down.
- **Estimates to confirm** on hardware (M-16): C_eff and the P3V_RP load (§4.2); the TLV3201 hysteresis (≤ 10 mV assumed); the /OE node capacitance; the Q32 drop; P3V3_S tolerance [A].
- The /OE edge-rate deviation (§7).
- **Optional further margin:** the 2.5 V U402 B supply (§5), if you want protection well beyond 314 V/ms.
