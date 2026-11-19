# Sheet 5 (power and X4 power control): architecture proposal

**Status:** revision A1, 2026-11-20. It records your review of PR #10 (decisions S5-1 to S5-9). It also answers the two concerns you asked to see before the schematic: the 5 V regulator margin (§3) and the X4 ground-return architecture (§4).
- Rev A (2026-11-19) asked for the decisions. Its content is kept where it still applies; changes are marked **(A1)**.
- **The schematic is drawn in a separate implementation PR** (branch `stage2/sheet5-schematic`). That PR includes this revision.
- **No PCB manufacture is authorised.** Every hardware verification and manufacturing gate stays open.

**Analysis tools (A1):**
- [`tools/analysis/sheet5_power.py`](../../tools/analysis/sheet5_power.py): current limit, start-up thermal, coordination, PSU headroom, UVLO/OVLO strings, the 5 V chain, regulators, thermal and the budget.
- [`tools/analysis/sheet5_ground.py`](../../tools/analysis/sheet5_ground.py): the ground-return network.
- Both are pure Python and print every table used here.
- Every figure from them is a **model-derived estimate** (datasheet limits plus the stated [K]/[A]/[E] inputs), never a guarantee.
- Rounding is conservative: maxima and requirements round up; minima and margins round down.

**Datasheets used [V]:**

| Part | Document | Used for |
|---|---|---|
| TI TPS25947 eFuse | SLVSFC9C (May 2026) | Pinout, thresholds, ILIM table, ITIMER, fast trip, dVdt, absolute maxima, thermal-shutdown curve (Fig. 8-3), fault table |
| TI INA226 | SBOS547C (Aug 2026) | Pinout (DGS), address table, input ranges, accuracy |
| TI TLV767 LDO **(A1)** | SLVSE84D (Jul 2021) | 2.5–16 V input, 18 V absolute maximum, ±1 % over load and temperature, DGN pinout and thermal data |
| TI LP38692 LDO **(A1)** | SNVS322M (Dec 2015) | Compared: 12 V absolute maximum, ±5 % over temperature |
| TI TLV1117 LDO **(A1)** | SLVS561O (Jun 2025) | Compared: 16 V absolute maximum, specified from VIN 4.75 V |
| Diodes AP7361C LDO | AP7361C data sheet | Rev A choice, now rejected (6.5 V absolute maximum) |
| TI SN74LVCH16T245, SN74LVC8T245 | S46, S53 (re-read) | +5V_BUS loads: VCCB 5.5 V recommended, 6.5 V absolute maximum |
| Radxa X4 schematic, sheet 26 | S1 (re-read) | J10 = `HD_TH1X2_2D54_STA`. The input runs through a CH224D-controlled switch (Q22/Q23, 220 pF Miller capacitors C344/C345) to the internal 12 V rail, and has an SMBJ18CA TVS |
| Lattice Diamond Power Calculator | Diamond 3.14 (device model) | Peak start-up current of the LCMXO2-4000HC: VCC 55 mA, VCCIO 17 mA. MachXO2 data sheet Table 3.10 note 6 points to this tool |

The fuses, TVS diodes, connectors, ribbon and IDC contacts are still [K]/[A]. Their manufacturer ratings could not be retrieved: Molex, 3M and Amphenol refused automated access or timed out. They are therefore written as **requirements** that the chosen parts must meet (§4.3, new risk R-56).

## 1. Your decisions (review of PR #10) and what this revision does

| ID | Your decision | Done in A1 |
|---|---|---|
| S5-1 | **TPS259470L approved** for the X4 12 V supply | Kept as U501. **Also proposed for the 5 V eFuse U503** (§3), so both are one part number |
| S5-2 | UVLO/OVLO approach **provisionally approved**. Recalculate and justify the current limit: start-up transients, PSU headroom, component ratings, protection coordination | §2. **RILM 1.10 kΩ: ILIM 2.65–3.36 A** (rev A: 3.89–4.92 A). Plus:<br>• ITIMER 10 nF;<br>• soft start 10 nF + 100 Ω;<br>• C501 470 µF;<br>• an INA226/FPGA sustained-overload trip at 2.75 A;<br>• a 5 A time-lag fuse.<br>UVLO/OVLO strings re-derived with R1 ≥ 350 kΩ, a TI requirement that rev A missed |
| S5-3 | Automatic X4 power-on after successful FPGA configuration and power/safety checks. Default OFF during reset, fault or unsafe conditions. Software shutdown/restart. A documented service override | §5. Hardware fail-safe enable stage (state table), power-manager requirements PM-1 to PM-10 for the HDL stage, and JP501 (force-off / force-on service override) |
| S5-4 | **INA226 at 0x44 with the 10 mΩ shunt approved**; keep the I²C power-domain protections | Unchanged. SDA, SCL and ALERT pull-ups go to +3V3 only (C-28, C-29) |
| S5-5 | **Isolated NMOS S0 sensing approved.** Document and implement the inverted active-low polarity | §6. The hardware inverts the signal: **X4_S0_SENSE low = X4 in S0**. The frozen net name stays. The polarity is recorded in the pin matrix, the schematic and PM-6 |
| S5-6 | Investigate the second eFuse for 5 V, but improve the downstream regulator margin. The 472x clamp can reach 6.2 V, against the AP7361C's 6.0 V recommended and 6.5 V absolute maximum. Account for the eFuse's transient response and faults; do not rely on the nominal 5.7 V clamp | §3. **TPS259470L with OVLO** (a disconnect with a 5.53–6.01 V window, not a clamp), C_BUS ≥ 220 µF, an SMBJ13A input TVS. **TLV76733 regulator: 18 V absolute maximum, 16 V operating.** For your confirmation (§8) |
| S5-7 | Keep the 3.3 V linear regulator provisionally; verify the PCB dissipation and the alternatives | §7. TLV76733DGNR: ≤ 0.67 W, TJ ≤ 101 °C at 60 °C ambient [E]. Buck alternative assessed. Measurement M-22 |
| S5-8 | **Conditional**, with six conditions | §4. The condition-by-condition answer is §4.4. **Not closed:** M-21 measurements are mandatory, and the "preferred dedicated path" is met only if the X4's mounting holes are bonded to its ground |
| S5-9 | Secured USB-C protection, external-source detection, and an interlock against enabling the X4 eFuse with an external source present. Safe during FPGA reset/configuration. Controlled bench tests | §5. The hardware keeps U501 off whenever the FPGA is not actively enabling it. PM-2 step 3 runs the external-source check before any enable. FLT reports reverse current while running. Bench test M-20 |

## 2. X4 12 V current limit and coordination (S5-2)

### 2.1 Current limit

**ILIM band.** The datasheet tests five RILM values (Table 6.5). Between 549 and 1650 Ω, the band is 0.8892–1.0888 × 3334/RILM [V]. With the RILM tolerance (1 % + TCR, ±1.5 % [E]):

| RILM | ILIM min | ILIM max | Note |
|---|---|---|---|
| 750 Ω (rev A) | 3.89 A | 4.92 A | ILIM_max is above a 2.54 mm contact's ~3 A [K]. A2000 PSU worst case 8.43 A > 8 A (§2.3) |
| **1.10 kΩ (A1)** | **2.65 A** | **3.36 A** | Largest E96 value with ILIM_min ≥ 1.05 × the 2.5 A design load |
| 1.13 kΩ | 2.58 A | 3.27 A | Fails the rule |

**The design load.** 2.5 A is Radxa's "12 V ≥ 2.5 A" [V S3]. The highest published X4 measurement is 2.27 A (27.3 W [Vs S9]).

**What the eFuse alone cannot do.** The datasheet band is 1.22 × wide. **No RILM gives ILIM_max ≤ 3.0 A while keeping ILIM_min > 2.5 A.** A 3 A contact therefore cannot be protected by the eFuse alone. The FPGA trip (§2.2) covers the region between the design load and ILIM_max.

### 2.2 Coordination ladder

| Level | Threshold | Time | Action |
|---|---|---|---|
| Design load | ≤ 2.50 A | Continuous | – |
| FPGA warning (INA226 average) | > 2.60 A | ≥ 1 s | Status flag to the Amiga |
| **FPGA sustained-overload trip** (INA226) | **> 2.75 A**: shunt 1 %, gain 0.1 %, offset 10 µV → 2.71–2.79 A | ≥ 2 s (register) | X4_PWR_EN low, latched, reported |
| eFuse blanking window | ILIM to the fast-trip threshold | **4.8–15.3 ms** (C_ITIMER 10 nF C0G) | None: the transient passes. At most 6.8 A for 15.3 ms = 0.70 A²s, negligible for contacts [K] |
| eFuse active current limit | **2.65–3.36 A** | After tITIMER | Regulates at ILIM. **FLT goes low → the FPGA switches off** (PM-4) |
| eFuse scalable fast trip | 2.01 × ILIM, typical only [V]: ~5.3–6.8 A [E] | 0.5 µs typ | Off, then current-limited restart |
| eFuse fixed fast trip | 22.2 A typ | 0.5 µs typ | Off |
| eFuse thermal shutdown | TJ 154 °C typ | – | Latch-off (L variant). The FPGA clears it by toggling EN below 0.45 V |
| F501 | **5 A time-lag** (must carry 3.36 A at 75 % load and 90 % temperature derating [K]) | Fuse curve | Opens if the eFuse fails short |
| A2000 PSU, +12 V | 8 A system limit [V S14] | – | The PSU's own protection [A] |

Where an individual eFuse limits below 2.75 A, its FLT output gives the same FPGA shutdown. Every overload ends in a latched, reported shutdown. None can persist above 2.79 A for more than about 2 s while the FPGA is in control.

### 2.3 A2000 PSU headroom

Haynie's example system [V S14] (architecture review §8.3) draws 2.01 A of +12 V without this card. The hard-disk spin-up surge is taken as +1.5 A [A].

| X4 current | Total | Against the 8 A system limit |
|---|---|---|
| 2.50 A (design) | 6.01 A | 1.99 A headroom |
| **3.36 A** (ILIM_max, eFuse-limited sustained fault) | **6.87 A** | **1.13 A headroom** |
| 4.92 A (rev A ILIM_max) | 8.43 A | **Exceeds the limit**: the recalculation was needed |

- A blanked transient (≤ 15.3 ms) on top of a spin-up could exceed 8 A briefly. The default 5 s start-up delay (PM-2) keeps the X4 start away from the spin-up.
- The unverified "+12 V 3 A" PSU variant (S15) cannot run this card. G-PSU (architecture review §8.6 step 1) still applies.

### 2.4 Start-up transients and thermal

**Thermal model.** The eFuse junction temperature during the soft start is computed from TI's thermal-shutdown curve (Figure 8-3). The curve is read as a thermal impedance Zth(t) = 129 °C / P(t) [E] and multiplied by 1.25 [A]. Ambient is 60 °C [A]. TI's own example (1.69 W for 20 ms, "safe") gives +37 °C on this model.

**X4 input.** The X4 input capacitance is ≤ 250 µF [E]. Sheet 26 of the X4 schematic shows that its internal 12 V rail is switched by a CH224D-driven MOSFET pair with Miller capacitors [V S1]. So the X4's main load and most of its capacitance probably connect **after** the input reaches 12 V [A].

| Case | Worst TJ (C501 470 µF, CdVdt 10 nF) | Comment |
|---|---|---|
| A: capacitive only | 120.6 °C (margin 33 °C) | Soft start 35–181 ms (SR 0.07–0.36 V/ms) |
| B: + X4 drawing 1 A above 9 V [A] | 128.4 °C (margin 25 °C) | |
| E: the X4's internal switch closes **abruptly** onto 200 µF after the soft start [A, pessimistic] | 123.0 °C (margin 30 °C) | The eFuse fast-trips, then recharges in current limit. C501 decides this case: with 100 µF it would reach 170 °C |
| C: the X4 drawing constant power (10 W) from 4.5 V [A] | **Fails (> 200 °C) with any soft start** | Not a design case. It is excluded only by inference from the X4's input switch and Radxa's "do not supply 5 V" [V S3]. **Measured by M-17 before any A2000 use** |

**Selection.** The script tries C501 ∈ {100, 220, 470} µF and CdVdt ∈ {1.8, 3.3, 4.7, 6.8, 10} nF. It selects **470 µF / 10 nF**: the largest worst-case margin over A, B and E. TI recommends 100 Ω in series with a dVdt capacitor of 10 nF or more.

### 2.5 Ratings on the 12 V path

| Element | Worst continuous current (working eFuse) | Rating / requirement |
|---|---|---|
| U501 | 3.36 A, 0.51 W | 5.5 A continuous [V]. TJ ≤ 82 °C with 8 thermal vias, 98 °C without [E] |
| R501 10 mΩ | 0.12 W (0.25 W at 5 A, fuse-limited) | 1 W 2512 [A part] |
| D501 SMBJ15A | – | VRWM 15 V > OVLO_max. VC 24.4 V < 28 V (U501) and < 40 V (INA226) [K] |
| X4 lead contacts (J502 and the J10 mating housing) | 3.36 A (all current, ribbon unplugged) | **≥ 4 A per contact, ≤ 20 mΩ** (requirement) |
| X4 lead wire | 3.36 A | **22 AWG**, the largest for 2.54 mm crimp terminals (KK 254 2759: 22–30 AWG [Vs]). Twisted pair, ≤ 15 cm |

### 2.6 UVLO/OVLO resistor strings

TI 3-resistor string. **R1 ≥ 350 kΩ** (ROC note 2: supplies above 5 V, or reverse-polarity exposure). Pin thresholds [V] are combined with ±1.5 % resistors at the worst-case corners:

| eFuse | R1 / R2 / R3 | UVLO rising (falling) | OVLO rising | Check |
|---|---|---|---|---|
| U501 12 V | 402k / 13k / 39.2k | 10.02–10.93 V (≥ 9.11 V) | 13.33–14.57 V | 11.4–12.6 V is inside. A spin-up sag to 11 V rides through. 24.4 V (TVS clamp) puts 2.81 V on EN/UVLO, below the 6.5 V absolute maximum |
| U503 5 V | 432k / 38.3k / 124k | 4.23–4.58 V (≥ 3.85 V) | **5.53–6.01 V** | 4.75–5.25 V is inside. A 12.6 V miswire gives 3.45 V / 2.63 V on EN/UVLO / OVLO (the OVLO pin then holds the part off). 21.5 V (SMBJ13A clamp) gives 5.88 V on EN/UVLO, below 6.5 V |

In both strings the current is ≥ 20 × the 0.1 µA pin leakage, as TI requires. Q502 pulls U501's EN/UVLO to GND to keep it off (§5).

## 3. 5 V protection chain and regulator margin (S5-6, focus concern 1)

### 3.1 Rev A problem and the A1 chain

Rev A relied on the TPS259472 clamp: up to 6.2 V threshold and 6.12 V output, after a 5 µs typical response. That sat against the AP7361C's 6.0 V recommended and 6.5 V absolute maximum. **The A1 chain does not rely on a clamp.**

**The A1 chain, J501 pin 4 → +5V_BUS → +3V3:**
1. F502, a **1 A time-lag fuse**: it carries U503's 0.59 A ILIM_max.
2. D502, an **SMBJ13A**: VRWM 13 V survives a 12.6 V miswire without conducting. VC 21.5 V keeps U503's pins below 6.5 V and IN below 28 V [K].
3. U503, a **TPS259470L**:
   - OVLO window 5.53–6.01 V, a **disconnect** (response 1.2 µs typ);
   - UVLO 4.23–4.58 V;
   - ILIM 0.42–0.58 A (RILM 6.65 kΩ, a tested point);
   - fast trip at about 2 × ILIM;
   - −15 V reverse polarity and reverse blocking [V].
4. **C_BUS ≥ 220 µF** (16 V) on +5V_BUS, plus 10 µF and 100 nF.
5. U504, a **TLV76733DGNR**.

### 3.2 Overvoltage paths

| Event | What limits +5V_BUS | Bound [E] |
|---|---|---|
| Slow rise (PSU regulation drift, miswire ramp) | OVLO switches U503 off; the output follows the input until then | ≤ **6.01 V** + slope × tOVLO. tOVLO is 1.2 µs typ with no maximum published; 5 µs is assumed [A], adding < 0.03 V |
| Fast step (12 V wire shorted onto the 5 V wire while running) | Charging C_BUS needs more than 2 × ILIM almost at once, so U503 fast-trips (0.5 µs typ). OVLO then holds it off | Charge before turn-off ½ × (ΔV/L) × t_off², with harness L ≥ 0.2 µH and t_off ≤ 2 µs (4 × typical): **≤ 0.44 V on 220 µF** (4.3 V on 22 µF). +5V_BUS ≤ 5.69 V |
| Hot-plug onto a live harness | U503 is off until UVLO plus soft start; ringing is clamped by D502. The input slew must stay ≤ 100 V/µs [V]: C_IN 1 µF keeps it near 20 V/µs [E] | – |
| **U503 failed short (pass FET)** + a PSU fault or miswire | Nothing on +5V_BUS. A **double fault** | +5V_BUS consumers (SN74LVCH16T245 U103, SN74LVC8T245 U104: 6.5 V absolute maximum [V S46, S53]) can be damaged. **The 3.3 V domain is protected** by the regulator choice below |

### 3.3 Regulator comparison

| Regulator | VIN operating / absolute max | Output accuracy | Package, θJA | Dropout at 0.25 A | Verdict |
|---|---|---|---|---|---|
| AP7361C-33 (rev A, BOM item 14) | 6.0 / **6.5 V** | ±1 % at 25 °C | SOT-223 | – | **Rejected:** no margin above the eFuse window |
| LP38692MP-3.3 | 10 / 12 V | **±5 %** over temperature, which uses the whole MachXO2 VCCIO window (3.135–3.465 V) | SOT-223, 68.5 °C/W | ≤ 0.26 V [E] | Margin to a 12.6 V miswire is negative after a U503 failure |
| TLV1117-33 | 15 / 16 V | ±2 % (I grade), specified only from VIN 4.75 V | SOT-223 | ≤ 1.25 V (0.5 A) | Specification starts at the bottom of our input range |
| **TLV76733DGNR** | **16 / 18 V** | **±1 % over load and temperature** | HVSSOP-8 with thermal pad, 60.1 °C/W | ≤ 0.38 V [E] (1.5 V max at 1 A) | **Selected.** Survives a 12.6 V miswire even with U503 failed short |

**TLV76733 conditions:**
- **Headroom:** +5V_BUS ≥ 4.68 V needs ≤ 3.68 V, a margin of 1.01 V.
- **Output capacitance:** COUT must be 1–220 µF [V]. The +3V3 rail carries about 104 µF on sheets 1–4 (netlist); the sheet-5 audit limits the total to ≤ 200 µF.
- **Start-up:** the inrush plus start-up load (0.15 A [E]) plus the FPGA's peak (0.072 A) totals 0.33 A, below U503's ILIM_min of 0.41 A.
- **Ramp:** +3V3 rises at ≤ 0.4 V/ms, inside the MachXO2's 0.01–100 V/ms [V S49].
- **EN_OK timing:** +5V_BUS rises in 13–72 ms, and EN_OK is released well inside the A2000 reset (R-36).

**Cost class:** the TLV prefix is TI's value line [K]. Prices are not checked here; that happens at the BOM stage.

## 4. X4 ground-return architecture (S5-8, focus concern 2)

### 4.1 Model

`sheet5_ground.py` solves the DC network of every return path, with each resistance at its minimum and maximum (2^7 corners).

**Paths:**
- X4 ground to carrier:
  - J10 lead: 8–38 mΩ, contact-limited;
  - ribbon: 8 GND conductors, 3.6–13.3 mΩ in parallel;
  - optional bonded standoffs: 0.5–5 mΩ for 4.
- Carrier plane segments.
- Carrier to PSU:
  - J501 drive-lead grounds: 4.1–13.8 mΩ for the pair;
  - Zorro fingers (18 GND pins, from the netlist), the motherboard and its PSU harness: 3–18 mΩ [A];
  - an external path (an earthed monitor through HDMI) in the cases that name it.

**Loads:** the X4 return, the carrier's 0.3 A, and up to 3 A of the **motherboard's own** return passing the slot [A].

### 4.2 Results

| Case | I_X4 | J10 lead | Per ribbon conductor | Per J501 contact | Per Zorro finger | ΔG = X4 − carrier | X4 return in dedicated paths | Card return via J501 |
|---|---|---|---|---|---|---|---|---|
| N1 normal, standoffs not bonded | 2.5 A | ≤ 1.54 A | ≤ 0.38 A | ≤ 2.79 A | ≤ 0.19 A | **≤ 24.6 mV** | 8–62 % | 19–83 % |
| N2 normal, standoffs bonded (2–20 mΩ joints) | 2.5 A | ≤ 0.77 A | ≤ 0.23 A | ≤ 2.79 A | ≤ 0.19 A | ≤ 8.3 mV | 45–97 % | 19–83 % |
| **N2s** normal, bonded standoffs with joints specified ≤ 5 mΩ | 2.5 A | ≤ 0.31 A | ≤ 0.11 A | ≤ 2.79 A | ≤ 0.19 A | **≤ 2.8 mV** | **74–97 %** | 19–83 % |
| N3 ILIM_max sustained | 3.36 A | ≤ 2.07 A | ≤ 0.50 A | ≤ 3.21 A | ≤ 0.25 A | ≤ 33.0 mV | 8–62 % | 19–83 % |
| F1 J10 ground open | 3.36 A | 0 | **≤ 0.55 A** | ≤ 3.21 A | ≤ 0.25 A | ≤ 44.6 mV | 0 % | 19–83 % |
| F2 J10 intermittent (1 Ω) | 3.36 A | ≤ 0.05 A | ≤ 0.55 A | ≤ 3.21 A | ≤ 0.25 A | ≤ 44.0 mV | 0–2 % | 19–83 % |
| F3 J10 open, standoffs bonded | 3.36 A | 0 | ≤ 0.32 A | ≤ 3.21 A | ≤ 0.25 A | ≤ 12.2 mV | 42–97 % | 19–83 % |
| F4 ribbon disconnected | 3.36 A | 3.36 A | 0 | ≤ 3.21 A | ≤ 0.25 A | ≤ 128 mV (no signals) | 100 % | 19–83 % |
| F5 one J501 ground open | 3.36 A | ≤ 2.07 A | ≤ 0.50 A | **≤ 5.43 A** | ≤ 0.28 A | ≤ 33.0 mV | 8–62 % | 11–71 % |
| F6 both J501 grounds open | 3.36 A | ≤ 2.07 A | ≤ 0.50 A | 0 | **≤ 0.31 A** | ≤ 33.0 mV | 8–62 % | 0 % |
| F7 J10 open + ribbon off, earthed monitor | 2.5 A | 0 | 0 | ≤ 1.57 A | ≤ 0.20 A | ≤ 2.5 V | 0 %: **2.5 A through the HDMI shield** | – |
| F8 as F7, no other path | – | – | – | – | – | – | The X4 cannot draw current: safe | – |
| T1 / T2 blanked transient 6.75 A (≤ 15.3 ms), normal / J10 open | 6.75 A | ≤ 4.16 A / 0 | ≤ 1.01 / 1.10 A | ≤ 4.86 A | ≤ 0.48 A | ≤ 66 / 90 mV for ≤ 15 ms | – | – |

**Columns:** "per contact" includes a share imbalance of ×1.3 for the ribbon, ×1.5 for the Zorro fingers and ×1.2 for J501 [A]. The J501 currents include up to 1.85 A of motherboard return diverted through the card (Zorro fingers → plane → J501), because the two grounds are joined.

### 4.3 Requirements derived from the model

These are part requirements. **None of the ratings could be retrieved from the manufacturers here, so each is a procurement gate (R-56):**

| Path | Worst steady current | Requirement |
|---|---|---|
| Ribbon ground conductor and IDC contact | 0.55 A (F1); 1.10 A for ≤ 15.3 ms (T2) | ≥ **1.0 A** per conductor and contact, continuous |
| X4 lead contact (both ends) | 3.36 A (F4) | ≥ **4 A**, ≤ 20 mΩ |
| J501 drive-power contact | 5.43 A (F5, including the motherboard loop current) | ≥ **6 A** per contact |
| Zorro ground finger | 0.31 A (F6) | ≥ 2 A is implied by Haynie's 4 A per slot on +5 V pins 5 and 6 [D from V S52] |

### 4.4 Your six conditions

| # | Condition | Answer |
|---|---|---|
| 1 | Model the current division through the J10 ground, the ribbon grounds, the carrier plane, the Molex grounds and the Zorro grounds | §4.1–4.2 |
| 2 | Verify wire and contact ratings, including start-up and fault currents | §4.3 (and §2.5): every current is derived and turned into a requirement. **Manufacturer ratings are not yet verified (R-56):** they must be confirmed from the chosen parts' specifications before ordering |
| 3 | Design the harness so that the dedicated ground return is the preferred low-impedance path | **Finding:** the J10 lead alone **cannot** be made the preferred path. Its two 2.54 mm contacts make it 8–38 mΩ against the ribbon's 3.6–13.3 mΩ, so in N1 the ribbon carries 38–92 %.<br>**A1 design:**<br>(a) **H501–H504: the four M2.5 standoff pads bonded to GND.** With the joints specified ≤ 5 mΩ each, the dedicated paths (J10 lead + standoffs) carry **74–97 %** (N2s), and ΔG ≤ 2.8 mV. This works **only if the X4's mounting holes are bonded to its ground** (TBV; the X4 schematic shows no hole nets): **M-21 (a) measures it first**.<br>(b) The X4 lead: 22 AWG twisted pair ≤ 15 cm, latching polarised housings, J502 pin order = J10 (1 GND, 2 12 V).<br>(c) A dedicated drive-power lead: both GND contacts, no splitter.<br>(d) Layout: the 12 V path and its return as a pair over solid ground, a direct pour from J502 GND to J501 GND, no plane splits.<br>**If M-21 (a) finds the holes isolated,** the ribbon remains the main X4 return. That is within the §4.3 ratings, but it is **your decision**: accept it, or add an X4-side ground strap (for example, a ring lug at a grounded X4 connector shell) |
| 4 | Open or intermittent J10 ground: can the ribbon or Zorro ground carry the X4 return? | **Yes, both can.**<br>• J10 open or intermittent: the ribbon carries 100 % (≤ 0.55 A per conductor), and ΔG ≤ 45 mV stays inside the 50 mV allowance. It is not hazardous with ≥ 1 A-rated parts, but it cannot be detected from the current. Hence the latching connector and the bench fault tests.<br>• **The Zorro ground always carries part of the card's return** (17–81 %), because the bus ground must stay common. It carries all of it (≤ 0.31 A per finger) if both J501 grounds open.<br>• The double fault F7 (J10 and ribbon both lost) sends the return through an earthed monitor. PM-6 detects it (X4 current with no S0 sense) and switches the X4 off |
| 5 | Current-limited bench validation before an actual A2000 motherboard | §9: stages B0–B5, with limits on every supply, fault injection on the bench, and an emulated Zorro ground path. The A2000 motherboard comes only in stage B5 |
| 6 | Keep the normal-operation ground offset within the S4-6 assumptions | ΔG ≤ 24.6 mV at 2.5 A and ≤ 33.0 mV at 3.36 A without standoffs; ≤ 8.3 mV (≤ 2.8 mV specified) with them. All against the 50 mV allowed in sheet4-s46-isolation §9; the GP24 margin cost is ≤ 2.0 mV. **Measured by M-21 (c); the calculation alone is not offered as approval** |

## 5. X4 power control, power-on policy and interlock (S5-3, S5-9)

### 5.1 Hardware

**U501 enable stage:**
- Q502 (BSS138) pulls U501's EN/UVLO below the 0.45 V shutdown threshold.
- Q502's gate is biased **from +12 V**: R 100k / 47k, giving 4.0 V at 12.6 V and above 1.5 V for any VIN above 4.7 V.
- Q501 (BSS138, gate = X4_PWR_EN through a 10 kΩ pull-down) releases Q502.

| Condition | X4_PWR_EN | Q501 / Q502 | U501 |
|---|---|---|---|
| +12 V present, +3V3 absent | Low (R pull-down) | off / on | **OFF** |
| FPGA erased, configuring or in reset: I/O tri-stated with weak pull-down [V S49] | Low | off / on | **OFF** |
| FPGA running, power manager off or faulted | Low (driven) | off / on | **OFF** |
| FPGA running, power manager enabling | High | on / off | ON, while 10.9 V < VIN < 13.3 V (UVLO/OVLO bands) |
| JP501 1–2 (**service: force off**) | Any | Any | **OFF**, whatever the FPGA does |
| JP501 2–3 (**service: force on**) | Any | Q502 gate grounded | ON within UVLO/OVLO. **The FPGA can no longer switch it off.** The eFuse's own protections remain (ILIM, fast trip, thermal latch-off, OVLO/UVLO, reverse blocking) |

**Other hardware:**
- **FLT** (open drain, pull-up to +3V3) → X4_PWR_FLT_N. It asserts on persistent overcurrent (after tITIMER), overtemperature, an ILM pin fault and **reverse current** [V Table 7-3].
- **R511** (4.7 kΩ X4-side bleed) discharges C501 + the X4 (τ ≈ 3.4 s) so that the interlock can tell residual charge from an external source.
- **The service override** is a 3-pin header with a shunt. It is fitted on prototypes, with the shunt parked on one pin = FPGA control. Force-on is for bench service with a current-limited supply and **nothing connected to the X4's USB-C**. It bypasses PM-2 to PM-6 and is **not for user builds** (R-57).

### 5.2 Power-manager requirements for the HDL stage (new)

| ID | Requirement |
|---|---|
| PM-1 | X4_PWR_EN reset value 0. LPF: no pull-up on pin 112. The output is driven low at all times except in the PM_ON state |
| PM-2 | **Automatic power-on** (your S5-3), after configuration:<br>1. The INA226 answers at 0x44 with its manufacturer and die IDs [V SBOS547C], and is configured (PM-9). Otherwise: fault, no start.<br>2. Wait T_DELAY (default 5 s, register / DIP "auto-start" on sheet 6) to stay clear of disk spin-up.<br>3. **External-source check (S5-9):** VBUS (X4 side) < 3.0 V. If not, wait up to T_DECAY (default 10 s) for the bleed decay. If it is still above, latch EXT_SOURCE and do not enable.<br>4. X4_PWR_FLT_N high and INA_ALERT_N inactive.<br>5. Enable. Within 300 ms, VBUS must be inside 11.0–13.2 V, otherwise disable and latch.<br>6. Report S0 (PM-6) |
| PM-3 | **Software shutdown and restart** from the Amiga:<br>• "request graceful shutdown" (mailbox to the Windows service; power removed after the S0 sense goes inactive and the current falls below I_STBY, or after a timeout);<br>• "power off now" behind a two-write unlock (architecture review §8.4);<br>• "restart" = off, ≥ 5 s, then PM-2 from step 3 |
| PM-4 | X4_PWR_FLT_N low (filtered over 2 clocks) → X4_PWR_EN low within 1 ms; latch FAULT_FLT; no automatic retry by default (optional limited retries, ≥ 10 s apart) |
| PM-5 | INA226 current > I_TRIP (default 2.75 A) over ≥ 2 s → off and latch OVERLOAD. ALERT is set as a shunt over-limit at I_TRIP, for prompt notice |
| PM-6 | **X4_S0_SENSE is active low** (S5-5): s0 = !X4_S0_SENSE. Current > 0.5 A with s0 inactive for T_RIB (default 30 s) → off and latch RIBBON (ground-return double fault F7, ribbon unplugged) |
| PM-7 | VBUS > 11 V with current > 0.1 A while X4_PWR_EN is low → flag OVERRIDE (JP501 force-on). Forward current through the shunt distinguishes it from an external source |
| PM-8 | Every latch is reported to the Amiga and cleared only by an explicit command. A cleared fault restarts at PM-2 step 3 |
| PM-9 | INA226: calibration for 10 mΩ, current LSB ≤ 0.1 mA, averaging 16, 1.1 ms conversions, continuous shunt and bus |
| PM-10 | I²C master on pins 125/126; never addresses 0x40–0x43 (C-28) |

These go into the HDL stage. **No RTL change is made by sheet 5.**

### 5.3 R-05 (X4 USB-C live at 12 V)

- **Before an enable:** PM-2 step 3 refuses to enable while a USB or PD source holds VBUS up.
- **While running:** a source above our 12 V makes U501 block reverse current and FLT go low → PM-4. A source below it (5 V) cannot be detected electrically, so **the secured shroud remains the primary protection** (baseline, G-R05).
- Bench tests are in M-20.

## 6. X4_S0_SENSE polarity (S5-5)

**Circuit:** Q503 (BSS138). Gate from X4_3V3_REF (the X4's S0-only P3V3_S [V S1 sh.21]) through 100 kΩ, with 1 MΩ to GND. Drain to X4_S0_SENSE (pin 114), with 10 kΩ to +3V3.

**Low = X4 in S0. High = S5, G3, X4 absent or ribbon unplugged** (fail-safe: "not running").

- **ER-3:** ≤ 3.3 µA from X4_3V3_REF.
- **C-29:** pin 114 sees only the +3V3 pull-up and a drain.
- The frozen net name is kept. The active-low polarity is written into the schematic, the pin matrix (pin 114) and PM-6.

## 7. Thermal (S5-7)

At 60 °C ambient [A]:

| Part | Dissipation | TJ [E] |
|---|---|---|
| U504 TLV76733DGNR, 0.25 A from 5.25 V | 0.49 W | 90 °C (θJA 60.1) |
| U504 at the OVLO edge (5.97 V) | 0.67 W | 101 °C (θJA); 92 °C (ψJB with the board at 70 °C) |
| U501, 2.5 A / 3.36 A | 0.29 / 0.51 W | 72 / 82 °C (8 vias); 81 / 98 °C (no vias) |
| U503 | < 0.01 W | – |
| R501 | 0.06 W at 2.5 A | – |

**PCB requirements (Stage 6):** U504's thermal pad soldered to a GND pour with ≥ 4 vias; U501 with 8 thermal vias (the basis of TI's 41.7 °C/W).

**Alternative:** a ≥ 17 V synchronous buck would cut U504's dissipation to about 0.1 W [K]. It adds switching noise beside the FPGA, SRAM and ribbon, plus an inductor. It is kept as the fallback if M-22 measures more than this estimate.

## 8. Changes from rev A that need your confirmation

1. **U503 = TPS259470L with OVLO** instead of the TPS259472 5.7 V clamp: a disconnect with a defined 5.53–6.01 V window, the same part as U501, no reliance on a clamp.
2. **U504 = TLV76733DGNR** instead of the AP7361C-33 (BOM item 14): 18 V absolute maximum, ±1 %. HVSSOP-8 with a thermal pad (hot air or PCBA, like the QFN eFuses, R-28).
3. **RILM 1.10 kΩ, ITIMER 10 nF, CdVdt 10 nF + 100 Ω, C501 470 µF**, the 2.75 A / 2 s FPGA trip and F501 5 A time-lag (§2).
4. **D502 = SMBJ13A** (not SMBJ15A) on the 5 V input, so that the clamp keeps U503's EN/UVLO below 6.5 V.
5. **H501–H504 bonded standoff pads** (§4.4 item 3), dependent on M-21 (a).
6. **JP501 force-off / force-on service header** (§5.1).

## 9. Verification plan (new M-numbers; bench before any A2000 motherboard)

**Bench stages (condition 5):**

| Stage | Set-up | Limits | Contents |
|---|---|---|---|
| B0 | Unpowered | – | 4-wire resistance of the X4 lead, ribbon grounds and standoff joints; X4 mounting-hole bonding (M-21 a); 12 V/5 V to GND isolation |
| B1 | Carrier only, lab supplies, no X4 | 5 V at 0.5 A, 12 V at 0.5 A | M-18 thresholds; default-off through erase/configure/reset (M-20); INA226 (M-19) |
| B2 | + electronic load on J502 | 12 V at 4 A | ILIM, fast trip, tITIMER, FLT, latch-off and EN recovery (M-18); thermal (M-22) |
| B3 | + real X4 on its own lead and ribbon | 12 V at 3.5 A | M-17 start-up, M-21 (b)–(d) current split, ΔG and J10-ground faults, M-24 S0 sense |
| B4 | + emulated slot ground: a resistor network from carrier GND to supply GND | 12 V at 3.5 A | M-21 (e) J501 ground-open faults, Zorro-path current |
| B5 | A2000 PSU after G-PSU, then the A2000 (card first without the X4, architecture review §8.6 step 8) | PSU | Repeat M-21 (c) and M-17 in the machine |

**Measurements:**

| ID | Measurement | Pass criterion |
|---|---|---|
| M-17 | X4 input voltage and current through the soft start and the X4's internal-switch closure (current probe); U501 temperature; 11.4 / 12.0 / 12.6 V | No current limiting or TSD during start-up; case C excluded; peaks inside the blanking window. CdVdt / C501 / C_ITIMER retuned if needed |
| M-18 | U501/U503 UVLO and OVLO (rising and falling), ILIM, fast trip, tITIMER, FLT, latch-off recovery | Inside the §2.6 bands; ILIM 2.65–3.36 A and 0.42–0.58 A |
| M-19 | INA226 ACK at 0x44 and IDs; current and VBUS against a meter at 0.1 / 1 / 2.5 / 3 A; ALERT at 2.75 A | ±2 %; trip 2.71–2.79 A |
| M-20 | Default-off with an erased, configuring and resetting FPGA (EN/UVLO < 0.45 V); auto-start sequence; shutdown, restart and fault latches; **external-source tests with a 5 V USB source and a 12 V PD source on the X4 USB-C, U501 off, source current-limited**; JP501 positions | U501 never on outside PM_ON; enable refused with a source present |
| M-21 | (a) X4 mounting holes to X4 GND (4-wire); (b) current split J10 / ribbon / standoffs at 1 and 2.5 A; (c) **ΔG at J401 ≤ 50 mV** idle and loaded; (d) J10 ground open / intermittent: ribbon conductor temperature rise; (e) J501 one / both grounds open on the B4 rig | Model ranges in §4.2; ratings in §4.3 |
| M-22 | U501, U503, U504, R501 temperatures at the design load in an A2000-like enclosure or at 60 °C | Below the §7 estimates |
| M-23 | U503 OVLO with a slow ramp; fast 12 V step onto the 5 V input through a 0.5 m lead (current-limited) | +5V_BUS ≤ 6.0 V; +3V3 undisturbed |
| M-24 | X4_S0_SENSE in S0 / S5 / G3 / ribbon unplugged; X4_3V3_REF load from sheet 5 | Polarity as §6; ≤ 5 µA |
| P-1 | Diamond Power Calculator run in the GUI on the placed design: in Tcl project mode it did not load the NCD | FPGA dynamic power inside the §10 budget |

## 10. Power budget (summary of `sheet5_power.py` §9)

| Rail | Typical | Design maximum | Limit |
|---|---|---|---|
| +12 V (X4 + sheet-5 overhead) | 0.90 A | 2.50 A | eFuse ILIM 2.65–3.36 A; FPGA trip 2.75 A |
| +3V3 (computed sum) | 0.065 A | 0.158 A | Design maximum kept at **0.25 A** |
| +5 V (J501 pin 4: +3V3 through the LDO, +5V_BUS, quiescent currents) | 0.086 A | 0.301 A | U503 ILIM 0.42–0.58 A; F502 1 A |
| Power from the A2000 | 11.3 W | 33.2 W | – |

The FPGA dynamic figures are [E], so P-1 stays open. The FPGA's 72 mA start-up peak comes from the Diamond device model.

## 11. Sheet 6 (next)

**Scope:**
- LED_READY (FPGA pin 65), and the RP2040 LEDs LED_RP0–3 from U404 (C-26);
- the DIP switches DIP_MODE_B, DIP_INT6, DIP_DISABLE and RP_JTAG_EN_N, plus the "auto-start" setting PM-2 needs;
- the debug header DBG0–3 (R-51 defaults, R-49).

A proposal follows after your review of sheet 5.
