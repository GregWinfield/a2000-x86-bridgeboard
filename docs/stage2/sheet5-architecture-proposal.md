# Sheet 5 (power and X4 power control): architecture proposal

**Status:** 2026-11-19. This proposal asks for your decisions before sheet 5 is drawn, as with sheet 4.
- **Nothing is drawn yet.** This is not a design release.
- **No PCB fabrication.**

**Basis:**
- the architecture review §8 (power);
- the baseline decisions D-11 (INA226 fitted on prototypes) and R-05 (shroud plus detection);
- the open items that sheet 5 must close or respect: C-28/R-50, C-29/R-49, R-51 and ER-3;
- the sheet-2 pin plan: the six sheet-5 FPGA pins are frozen.

**Datasheets fetched for this proposal [V]:**

| Part | Document | Used for |
|---|---|---|
| TI TPS25947 eFuse | SLVSFC9C (rev. May 2026) | Variants, thresholds, current limit, reverse blocking |
| TI INA226 power monitor | SBOS547C (rev. Aug 2026) | Address table, input ranges, absolute maxima |
| Diodes AP7361C LDO | AP7361C data sheet | Input range, dropout, dissipation |
| Diodes DMG2305UX P-FET | DS36196 Rev. 8-2 | VDS, VGS, RDS(on) |

They will be registered in `sources.md` when the sheet is drawn. The fuses, PTC, TVS diodes and connectors are still [K] or [A].

## 1. What sheet 5 must do

| Function | Requirement | Source |
|---|---|---|
| 12 V to the X4 | From the A2000's internal drive power connector to the X4's J10: a 2-pin 2.54 mm header, pin 1 GND, pin 2 ADP12V_IN, 12 V "consistent with the 12 V USB-PD specification". Design 2.5 A | [V S2, S3, S4]; architecture review §8.1, §8.3 |
| X4 power control | **Default off.** The FPGA enables it with X4_PWR_EN (pin 112). A jumper override is provided for bring-up | Architecture review §8.2; R-51 |
| Fault report | X4_PWR_FLT_N (pin 113) | Sheet-2 pin plan |
| Telemetry | INA226 on I2C_SDA/I2C_SCL (pins 125/126); INA_ALERT_N (pin 111) | D-11 |
| X4 S0 sense | X4_S0_SENSE (pin 114): is the X4 running? The header 3.3 V (pins 1, 17) is the X4's S0-only P3V3_S | Architecture review §5 (X5), §8.5 [V S1 sh.21] |
| Carrier logic supplies | +5V_BUS (Zorro translators) and +3V3 (FPGA, SRAM, buffers, LEDs, INA226): ≤ 0.3 A design | Architecture review §8.2, §8.3 |
| Constraints | Zorro power pins not connected. C-28: no I2C device at 0x40–0x43. C-29: no FPGA input driven while +3V3 is off. ER-3: microamps only from the X4's header 3.3 V. R-05: the X4's USB-C VBUS is live at 12 V | Owner decisions; risk register |

## 2. Proposed architecture

**12 V branch:**
1. J501, a 4-pin drive power header [K].
2. F501, a fuse of about 5 A, slow-blow [A].
3. D501, a TVS, SMBJ15A class [K].
4. **U501, a TPS25947 eFuse** (S5-1, S5-2).
5. R501, a 10 mΩ shunt read by **U502, the INA226**.
6. Bulk capacitance.
7. J502, a 2-pin lead to the X4's J10.

**5 V branch** (S5-6 option B):
1. J501 pin 4.
2. D502, a TVS.
3. **U503, a TPS25947 eFuse** with the 5.7 V overvoltage clamp: current limit, reverse polarity and reverse blocking.
4. +5V_BUS.
5. **U504, an AP7361C-33**, producing +3V3.

**Control:**
- X4_PWR_EN drives a fail-safe enable stage on U501's EN/UVLO pin, with a jumper override.
- U501's FLT pin drives X4_PWR_FLT_N.
- The INA226 sits on I2C, with INA_ALERT_N.
- X4_S0_SENSE comes through an isolating NMOS from X4_3V3_REF.

## 3. Verified facts behind the proposal

| Part | Facts [V] |
|---|---|
| TPS25947 (SLVSFC9C) | **VIN 2.7–23 V operating, 28 V absolute maximum**; "withstands negative voltages up to −15 V"; **true reverse current blocking**.<br>**RON** 28.2 mΩ typical (12 V, 3 A, 25 °C), ≤ 45 mΩ (−40 to 125 °C).<br>**EN/UVLO** rising 1.183–1.223 V, falling 1.076–1.116 V; shutdown threshold 0.45–0.74 V.<br>**OVLO (470x/474x)** rising 1.183–1.223 V.<br>**OVC (472x):** OVCSEL open 5.25–6.2 V; 390 kΩ 13.2–14.5 V.<br>**Current limit:** RILM 750 Ω gives 3.96–4.84 A; 6.65 kΩ gives 0.425–0.575 A.<br>IQ(ON) ≤ 610 µA.<br>**Variants:** 470A/470L (adjustable OVLO, active current limit, FLT, auto-retry or latch-off); 472A/472L (pin-selectable OVC, PG); 474A/474L (adjustable OVLO, circuit breaker, PG) |
| INA226 (SBOS547C) | **Address** set by A1/A0 (GND, VS, SDA, SCL): 0x40–0x4F, and **A1 = GND gives 0x40–0x43**.<br>**Inputs:** shunt ±81.92 mV; bus 0–36 V; IN+, IN− and VBUS −0.3 to 40 V absolute maximum, **independent of VS**.<br>**SDA ≤ 6 V, SCL ≤ VS + 0.3 V.**<br>Shunt offset ≤ ±10 µV; gain error ≤ 0.1 %; VBUS input impedance 830 kΩ |
| AP7361C | VIN 2.2–6.0 V, **6.5 V absolute maximum**; ±1 %; dropout 360 mV typical at 1 A (3.3 V); SOT-223 dissipation 1.1 W |
| DMG2305UX (DS36196) | VDS −20 V; **VGS ±8 V**; RDS(on) ≤ 100 mΩ at VGS −2.5 V |

## 4. Decisions requested

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| **S5-1** | eFuse for the X4 12 V path | TPS259470L/A (adjustable OVLO, active current limit, FLT; latch-off or auto-retry); 472x (13.85 V clamp, PG instead of FLT); 474x (circuit breaker, PG) | **TPS259470LRPW**. FLT feeds X4_PWR_FLT_N directly. Latch-off means firmware decides whether to retry, rather than the part hiccuping into a faulty X4 |
| **S5-2** | Protection thresholds | OVLO, UVLO, current limit and soft-start values | **OVLO ≈ 14.0 V rising** (a ±2.5 % window with 1 % resistors). The A2000 12 V is +5 % at most [K], and PD 12 V is ±5 %; the X4's own input maximum is not published [A].<br>**UVLO ≈ 10.5 V rising.**<br>**Current limit RILM 750 Ω: 3.96–4.84 A**, at least 1.58 × the 2.5 A design.<br>**Soft-start about 15 ms**, sized at drawing time against the X4's input capacitance [E] |
| **S5-3** | X4 power control and power-on policy | Policy: (a) the FPGA switches the X4 on automatically after configuration; (b) only on command from the Amiga; (c) DIP-selectable (sheet 6) | **Hardware:**<br>• default off (X4_PWR_EN pulled down, R-51; an erased FPGA also pulls weakly low);<br>• X4_PWR_EN high = on;<br>• the enable stage is biased from +12 V, so the eFuse stays off whenever +3V3 or the FPGA is absent (fail-safe);<br>• jumper JP501 forces it on for bring-up (default open).<br>**Policy: your choice.** I suggest (a), with a register to switch the X4 off and on. Whether the X4 boots by itself when power is applied is a BIOS setting [TBV] |
| **S5-4** | INA226 address and bus | Any address outside 0x40–0x43 | **0x44 (A1 = VS, A0 = GND).** It is the only device on the bus.<br>• SDA/SCL pull-ups (4.7 kΩ) and the INA_ALERT_N pull-up (10 kΩ) go to +3V3 only. SCL is limited to VS + 0.3 V, and C-29 applies too.<br>• Shunt 10 mΩ, 1 %, ≥ 0.5 W rating (234 mW at 4.84 A): 25 mV at 2.5 A, full scale 8.19 A, LSB 0.25 mA |
| **S5-5** | X4_S0_SENSE | (a) BSS138 isolating NMOS: gate from X4_3V3_REF (the X4's S0-only rail [V S1]) through a resistor, drain to pin 114 with a pull-up to +3V3; (b) a resistor divider from X4_3V3_REF (the architecture review's §8.5 sketch, 10 kΩ series and 100 kΩ, which predates C-29); (c) infer S0 from the INA226 current only | **(a).**<br>• ER-3: only gate leakage on X4_3V3_REF.<br>• C-29: pin 114 sees only a +3V3 pull-up and a drain.<br>• It is the same gate-only crossing as sheet 4.<br>• **The NMOS inverts it: X4_S0_SENSE low = X4 in S0.** The net name is frozen, so the polarity is an RTL convention for you to confirm.<br>(b) violates C-29 when the carrier is off. (c) cannot tell S0 from a stalled X4 |
| **S5-6** | 5 V input protection | (A) PTC + SMBJ5.0A + DMG2305UX P-FET, as in the architecture review; (B) a second TPS25947 (472x, OVCSEL open: 5.7 V clamp) | **(B).** Finding F5-1: the SMBJ5.0A clamps up to about 9.2 V [K], above the AP7361C's 6.5 V and the P-FET's ±8 V gate rating. Option (B):<br>• clamps +5V_BUS at ≤ 6.2 V [V], which also protects the Zorro translators' 5 V side;<br>• limits current (RILM 6.65 kΩ: ≥ 0.425 A against the 0.3 A design);<br>• withstands −15 V and blocks reverse current;<br>• replaces the PTC and the P-FET |
| **S5-7** | 3.3 V regulator | AP7361C-33 (BOM item 14), another LDO, or a buck converter | **AP7361C-33, SOT-223.** At 0.25 A from ≤ 5.25 V it dissipates ≤ 0.49 W, within its 1.1 W. With S5-6 (B), its input stays below 6.5 V |
| **S5-8** | Connectors and cabling | – | **Input:** 4-pin peripheral power header (5.25-inch-drive style): 1 = +12 V, 2 and 3 = GND, 4 = +5 V [K, TBV against the A2000 harness].<br>**X4 lead:** 2-pin 2.54 mm to J10 (pin 1 GND, pin 2 ADP12V_IN [V S2]); keyed housing rated ≥ 3 A; 18 AWG, ≤ 30 cm.<br>The X4 warns against reverse polarity [V S2], and U501's reverse protection covers only its own input, so the lead must be keyed and labelled.<br>See F5-2 for the return-current share |
| **S5-9** | R-05: the X4's USB-C VBUS is live at 12 V | Confirm the baseline: a secured shroud plus detection | **Detection:**<br>• the INA226 reads the X4-side bus voltage;<br>• about 12 V there while U501 is off means an external source;<br>• the FPGA flags it and refuses to enable U501.<br>U501's reverse current blocking [V] prevents back-feed into the A2000's 12 V. **Your decision:** never enable with an external source present (recommended), or allow it |

## 5. Findings while preparing this proposal

| # | Finding | Handling |
|---|---|---|
| F5-1 | The 5 V TVS (SMBJ5.0A class) clamps to about 9.2 V at its rated pulse current [K]. That is above the AP7361C's 6.5 V absolute maximum and the DMG2305UX's ±8 V gate rating, so the architecture review's 5 V chain was not self-consistent | S5-6 (B) |
| F5-2 | The X4's return current has two paths: the J10 lead (about 10 mΩ for 0.3 m of 20 AWG [E]) and the ribbon's 8 ground wires (about 4 mΩ in parallel for 15 cm of 28 AWG [E], plus IDC contacts). **Most of the 2.5 A may return through the ribbon.** That gives a ground offset ΔG of about 7–10 mV [E]: within the 50 mV the S4-6 GP24 margin allows, and about 0.2 A per ribbon conductor | 18 AWG J10 lead, kept short (S5-8); confirm ΔG on hardware |
| F5-3 | TPS259470 FLT is open-drain, 6.5 V absolute maximum. EN/UVLO and OVLO are analogue inputs near 1.2 V | X4_PWR_FLT_N pull-up to +3V3 (C-29). Divider values set at drawing time from the §3 thresholds |
| F5-4 | The INA226's IN+, IN− and VBUS see 12 V even when its VS (+3V3) is off: the A2000 12 V, or back-feed from the X4's USB-C (R-05). They are rated −0.3 to 40 V independent of VS [V] | No issue. SCL stays on the same +3V3 (VS + 0.3 V limit) |
| F5-5 | X4_S0_SENSE through an NMOS is inverted | S5-5: the RTL polarity is your decision |

## 6. Verification plan for sheet 5 (once drawn)

- **Checks:** `audit_sheet5.py` (every pin and net against this proposal, the C-28 address, C-29 pull-up domains, ER-3 members, defaults), with a mutation test; ERC; an updated power budget; thermal checks for U501, U503 and U504.
- **Hardware measurements (new M-numbers):**
  - eFuse thresholds (OVLO, UVLO) and current limit;
  - soft-start into the X4;
  - FLT behaviour and latch-off recovery;
  - INA226 readings against a meter;
  - S0 sense;
  - the R-05 external-source test (a PD charger on the X4 with U501 off);
  - the 5 V clamp;
  - the ground offset ΔG.
- **R-49, R-50 and R-51:** closed for sheet 5 only by those checks, and kept open for sheet 6.

## 7. Sheet 6 (next)

**Scope:**
- LED_READY (FPGA pin 65), and the RP2040 LEDs LED_RP0–3 from U404 (C-26);
- the DIP switches DIP_MODE_B, DIP_INT6, DIP_DISABLE and RP_JTAG_EN_N;
- the debug header DBG0–3 (R-51 defaults, R-49).

The JTAG header J201 is on sheet 2. A sheet-6 proposal follows once you have decided on sheet 5, or alongside if you prefer.
