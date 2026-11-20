# Sheet 6 (diagnostics, configuration switches, debug header): architecture proposal

**Status:** revision A, 2026-11-20. It asks for your decisions before sheet 6 is drawn, as for sheets 4 and 5.
- **Nothing is drawn.** This is not a design release. **No PCB manufacture is authorised.**
- It is written while sheet 5 (PR #10 proposal rev A1, PR #11 schematic) awaits your review. It depends on sheet 5 only through the X4-power LED option (S6-1 b) and PM-2's auto-start (S6-3).

**Basis:**
- the brief: "Provide test points, a programming/debug connector and useful diagnostic LEDs";
- C-26 (LED_READY on the FPGA; diagnostic LEDs on RP2040 GPIO; the READY indication must be preserved when the N100 or RP2040 is unavailable; LED drive current, reset state and power-off behaviour to be verified on sheets 4 and 6);
- D-03 (64 KB I/O mode by default, 512 KB by DIP switch);
- D-12 (RP2040 JTAG option, default isolated, so J201 has priority);
- the open items R-49 (C-29), R-51 (DBG defaults), and R-01 (four spare FPGA I/O kept for a future USB-HS SPI bridge);
- the frozen sheet-2 pin plan.

## 1. What sheet 6 must connect

| Signal | Source | Pin | Meaning (RTL / earlier sheets) | Today |
|---|---|---|---|---|
| LED_READY | FPGA output | 65 (bank 2) | **Active high**. Off = not armed or FPGA blank; slow blink = armed, unconfigured; steady = configured; fast blink = watchdog flag; ORed with CONTROL b4 (zorro-interface-spec §3) | Open (ERC) |
| DIP_MODE_B | FPGA input | 68 | **High = 512 KB mode B**, latched during the Zorro reset (z2_core) | Open |
| DIP_INT6 | FPGA input | 69 | **High = INT6** (CONTROL b2 reset value) | Open |
| DIP_DISABLE | FPGA input | 71 (SI/SISPI pad) | **High = the card does not arm** (soft disable; JP101 on sheet 1 is the hard disable) | Open |
| DBG0–DBG3 | FPGA I/O | 9–12 (bank 5) | Debug / expansion; R-01's future USB-HS SPI bridge | Open; R-51: no default yet |
| LED_RP0–3 | U404 A outputs (sheet 4, carrier +3V3) | – | RP2040 GP16–19 through U404 (B→A); off when the X4 or RP2040 is unpowered (VCC isolation, B-side pull-downs R408–R410, R415) | Open (sheet-4 pins) |
| RP_JTAG_EN_N | U403 /OE (sheet 4) | – | **Low = RP2040 JTAG option enabled**; R407 10k pull-up on sheet 4 = isolated by default (D-12) | Pull-up only |

**ERC:** drawing sheet 6 connects all 13 remaining open sheet pins and 12 isolated labels. Only the 14 permanent pin-to-pin entries would remain.

## 2. Verified facts used

- **MachXO2:**
  - I/O tri-stated with weak pull-down (30–305 µA) before and during configuration [V S49].
  - **Hot socketing:** IDK ≤ ±1000 µA for 0 < VIN < VIH(max), **with the internal clamp diode disabled** (Table 3.6, note 4) [V S49]. With the clamp enabled (the input default), the current into an unpowered pin is limited only by what drives it.
- **SN74AVC4T774 (U404, LEDs):** ±12 mA output at VCCA 3.0–3.6 V [V S66]. Its outputs are Hi-Z when either supply is off [V S66].
- **Pin 71 (SI/SISPI):** on an erased device the SSPI port responds only while SN is low, and SN is held high by R208 (sheet 2 notes §3.3) [V S64]. So the DIP_DISABLE switch is harmless while the FPGA is erased.

## 3. Decisions requested

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| **S6-1** | LEDs | (a) the five signal LEDs only: LED_READY + LED_RP0–3; (b) add two hardware LEDs: **+3V3 present** and **X4 12 V present** (on X4_12V, lit whatever powers the X4: U501, JP501 force-on, or an external USB-C source) | **(b).** The X4-power LED makes a live X4 rail visible to anyone servicing the card, including back-feed from the X4's USB-C (R-05). It needs one sheet-5 net exported (X4_12V), a small change to sheet 5.<br>Drive: 2 mA each through 680 Ω from 3.3 V (LED Vf ~2.0 V [K]); the X4 LED 1 mA through 10 kΩ from 12 V (10 mW).<br>**Colours:** READY green; RP0–3 per the firmware's assignment (proposed: link, heartbeat, attention, error); +3V3 green; X4 power amber |
| **S6-2** | DIP switch polarity | (a) conventional: switch to GND, pull-ups to +3V3. Every open switch then reads **high**, so by default the card would be **disabled, in mode B and on INT6**. Fixing that means inverting three RTL inputs (an HDL change, re-verified). (b) **switches to +3V3 with 10 kΩ pull-downs** at the FPGA pins, matching the RTL's active-high inputs | **(b).**<br>• 4-position DIP SW601, every position **ON = function active**:<br>  1 mode B,<br>  2 INT6,<br>  3 disable,<br>  4 RP2040 JTAG option (a switch to GND against sheet 4's R407).<br>• Defaults with all OFF: mode A (D-03), INT2, armed, JTAG option isolated (D-12).<br>• 1 kΩ series resistors for ESD (ON level 3.0 V).<br>• C-29 holds: the switches reach only +3V3 or GND, so nothing is driven while +3V3 is off. **No RTL change** |
| **S6-3** | X4 auto-start setting (PM-2) | (a) no switch: automatic power-on as you decided in S5-3; disable through an Amiga register (PM-3) or JP501 force-off; (b) use spare pin 67 for DIP_AUTOSTART: a change to the frozen pin plan (pin plan, LPF, Diamond re-run) | **(a).** It keeps the frozen pin plan, and S5-3 already makes automatic start the policy |
| **S6-4** | Debug header J601 and back-powering (R-49, R-51) | Header: 2×5, 2.54 mm, with a GND beside every signal (good for a future ≤ 25 MHz SPI bridge, R-01), carrying DBG0–3, +3V3 (through a 0.1 A PTC or 10 Ω) and GND.<br>Protection against a separately powered tool driving DBG while the carrier is off:<br>(a) **CLAMP=OFF** on DBG0–3 in the LPF (IDK ≤ 1 mA by datasheet), plus 100 Ω series resistors (ESD, ringing);<br>(b) an isolating buffer (SN74AVC4T774 as on sheet 4, VCCB from the tool, DIR per channel): full isolation, but the directions are fixed per channel;<br>(c) operating rule only (power the tool from J601's +3V3) | **(a).** The 1 mA bound is the datasheet hot-socket limit, so this is not an operating rule. CLAMP=OFF is an LPF attribute applied in the HDL stage (Diamond re-run). Take (b) when the SPI bridge's directions are fixed (SCK, MOSI, CS in; MISO out).<br>**Defaults (R-51):** 100 kΩ pull-downs on DBG0–3, so they are defined low with the FPGA erased, configuring or unpowered |
| **S6-5** | Test points and programming | J201 (FPGA JTAG, sheet 2) stays the programming connector; the RP2040 JTAG option is SW601-4 | Test points: TP601 LED_READY, TP602 GND. No extra programming connector. A note on the silkscreen: **SW601-4 ON only with no cable on J201** (otherwise U403 and the cable both drive JTAG) |

## 4. Checks once drawn

**`audit_sheet6.py`:**
- every LED with its resistor value, polarity and rail (the LED_RP LEDs on U404's A side, never the X4 side);
- the DIP polarity (pull-downs on 68, 69, 71; RP_JTAG_EN_N switch to GND);
- the DBG pull-downs and series resistors;
- C-29: no switch or header pin can drive an FPGA input from a rail other than +3V3 or GND;
- a mutation test.

**ERC** should then show only the 14 permanent entries.

**Measurements:**

| ID | Measurement |
|---|---|
| M-25 | LEDs: drive current and states through erase, configuration and reset of the FPGA, the RP2040 unpowered, and the X4 off. Includes C-26's READY indication with the RP2040 unavailable |
| M-26 | DIP defaults and every position read back through the STATUS register b4–b6 (zorro-interface-spec §9) |
| M-27 | DBG: current into an unpowered carrier from a 3.3 V source on each pin, with CLAMP=OFF: ≤ 1 mA |

## 5. Risks touched

| Risk | How sheet 6 addresses it |
|---|---|
| R-49 (C-29) | Debug header via CLAMP=OFF plus series resistors (S6-4) |
| R-51 | DBG defaults (S6-4) |
| R-05 | X4-power LED (S6-1 b) |
| R-01 | Header layout for the SPI bridge |

No risk can close before the measurements.
