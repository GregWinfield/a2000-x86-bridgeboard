# Sheet 6: diagnostics, configuration switches and debug header (revision A)

**Status:** 2026-11-21. Implements your decisions on the [sheet 6 proposal](sheet6-architecture-proposal.md) (review of PR #12).
- **G-SHEET6: approved for design progression.** Final schematic approval still needs evidence for the debug-header isolation (§4) and the JTAG contention protection (§5).
- **Not validated. No PCB fabrication is authorised.**
- Every hardware gate stays open. C-29 / R-49 and R-51 are **not** closed (§11).

**Files:**
- Schematic: `hardware/kicad/sheets/06_irq_diag_prog.kicad_sch` (generator `tools/kicad/sheet6.py`).
- PDF: [sheet6-schematic.pdf](sheet6-schematic.pdf) (sheet 6 is page 7). ERC: [sheet6-erc-report.md](sheet6-erc-report.md).
- Audit: [`tools/kicad/audit_sheet6.py`](../../tools/kicad/audit_sheet6.py), 189 checks, 0 failures, 26 of 26 mutants.

**This branch builds on PR #11 (sheet 5) and includes PR #12 (the proposal).** It neither duplicates nor overwrites their changes.

## 0. Decisions applied

| ID | Your decision | On the schematic |
|---|---|---|
| S6-1 | Approved: seven LEDs with defined meanings; READY independent of the N100/RP2040; check U404's output budget; the X4 LED is an indicator only; coordinate X4_12V with sheet 5 | D601–D607 with R601–R607 (§2). U404 budget: ≤ 1.67 mA per output and 6.7 mA in total, against ±12 mA and 100 mA [V S66]. X4_12V exported from sheet 5 by a hierarchical label only: no power-path change |
| S6-2 | Approved: SW601, positions 1–3 to +3.3 V with 10 kΩ pull-downs and series protection, position 4 to GND (active low). Defaults: 64 KB, INT2, armed, JTAG isolated. Document the reset sampling; do not assume glitch-free changes | SW601 with R608–R611 1 kΩ in series and R612–R614 10 kΩ pull-downs (§3). No RTL change |
| S6-3 | Approved: no auto-start switch; pin 67 unused; frozen pin plan kept | Nothing added. The pin plan is unchanged (audit_sheet2) |
| S6-4 | Conditional: J601 2×5 with grounds, protected +3.3 V, series resistors, defined states, pin-1 marking. Examine CLAMP=OFF in the erased, unconfigured, configuring and fault states; compare A, B and C; no back-power through the +3.3 V pin | **Option B drawn:** U601 SN74AVC4T774 isolation buffer, plus F601 PTC and D608 Schottky on the header supply (§4). The analysis rejects A as sole protection, and C is kept as an assembly option |
| S6-5 | Approved with safeguard: J201 stays the programming connector; TP601/TP602; investigate an interlock; otherwise keep the procedure and an open requirement | TP601 LED_READY, TP602 GND. **R432–R434 330 Ω** in U403's JTAG-option outputs (sheet 4) bound any contention to ≤ 10.9 mA (§5). No practical interlock, so the procedure stays mandatory and an open requirement (R-58) |

## 1. Contents

| Block | Parts | Function |
|---|---|---|
| LEDs | D601–D607, R601–R607 | READY, RP0–RP3, +3V3, X4 12 V |
| Switches | SW601, R608–R614 | Mode B, INT6, disable, RP2040 JTAG option |
| Debug header | J601, U601, R615–R634, F601, D608, C601–C603, #FLG6001 | Isolated DBG0–DBG3 |
| Test points | TP601, TP602 | LED_READY, GND |
| Sheet 4 (S6-5) | R432–R434 | U403 JTAG-option outputs through 330 Ω |

## 2. LEDs (S6-1)

Each LED is fed through its own resistor, cathode to GND.

**Currents** [E, LED Vf 1.8–2.2 V [K]; MPNs TBV]:
- 3.3 V LEDs (1 kΩ): 0.84–1.67 mA.
- X4 LED (10 kΩ from 11.4–12.6 V): 0.92–1.08 mA. R607 dissipates ≤ 12 mW.

| LED | Colour | Source | Meaning | Off when |
|---|---|---|---|---|
| D601 READY | Green | FPGA pin 65 (no RP2040 or N100 involvement, C-26) | **Off:** FPGA blank, configuring, in reset, or the card not armed (SW601-3 ON, EN_OK low). **Blink about 1.5 Hz** (ticks[14]: 50 MHz / 1024 / 2¹⁵): armed, not yet AutoConfigured. **Steady:** configured. **Blink about 12 Hz** (ticks[11]): watchdog flag set. CONTROL b4 forces it on (LED test). From `z2_core.v` `led_ready` | +3V3 off, FPGA unconfigured |
| D602 RP0 | Green | RP2040 GP16 via U404 | **FW-9 link:** on = host link up (IDENTIFY answered, protocol major version matches); off = no link; one 50 ms off-pulse per 64 frames of traffic | RP2040 in reset or unpowered, X4 off or in S5, carrier +3V3 off |
| D603 RP1 | Green | GP17 | **FW-10 heartbeat:** 1 Hz, 50 % duty, while the RP2040 firmware main loop runs. A steady or dark LED with RP0 on means the firmware has stalled | As D602 |
| D604 RP2 | Yellow | GP18 | **FW-11 mailbox/interrupt activity:** 30 ms pulse on each RP_IRQ_N assertion or ATTN-driven split read | As D602 |
| D605 RP3 | Red | GP19 | **FW-12 fault:** on = latched fault (CRC error rate above threshold, link loss after IDENTIFY, or the FPGA's host-status FAULT bit (C-26)); 2 Hz blink = firmware boot self-test failed; cleared by the host | As D602 |
| D606 | Green | +3V3 | Carrier logic power present | +3V3 off |
| D607 X4 | Amber | X4_12V (sheet 5, after the shunt) | **The X4's 12 V rail is live, from any source:** U501, JP501 force-on, **or an external USB-C/PD source** (R-05). **Indicator only:** not part of the S5-9 detection or interlock, which use the INA226 and the FPGA (PM-2) | X4 rail below about 2 V. It is independent of +3V3, so it also lights with the A2000 off if a source powers the X4 |

**Hardware behaviour of the RP2040 LEDs:** off whenever the RP2040 is unpowered or in reset (B-side pull-downs R408–R410, R415 on sheet 4), or the X4's header 3.3 V is off (U404 VCC isolation: A outputs Hi-Z, and the LED holds the node at 0 V) [V S66].

**Notes:**
- **D607** adds about 1 mA to the X4-side load. It flows through R501, so the INA226 reads +1 mA, and it shortens the S5-9 decay together with R511. Neither matters for PM-2 or PM-6.
- **FW-9 to FW-12** are new obligations on the RP2040 firmware (Stage 4), alongside FW-1 to FW-8.

## 3. DIP switch SW601 (S6-2)

| Position | ON | Net | Electrical | Sampled |
|---|---|---|---|---|
| 1 | 512 KB mode B | DIP_MODE_B (pin 68) | +3V3 → R608 1k → pin; R612 10k to GND | **Only during a Zorro reset** (`mode_b_l <= dip_mode_b` while zrst). Changing it in operation has no effect until the next reset (AutoConfig is re-run) |
| 2 | INT6 | DIP_INT6 (pin 69) | R609, R613 | **At reset** it loads CONTROL b2 (INT_SEL). Software may change INT_SEL afterwards; the switch is not re-read until the next reset |
| 3 | Disable bridgeboard | DIP_DISABLE (pin 71, SI/SISPI pad) | R610, R614 | **During reset** (`armed <= ~dip_disable` while /BUSRST is asserted). Outside reset it is ignored. JP101 (sheet 1) is the hard disable |
| 4 | RP2040 JTAG option | RP_JTAG_EN_N | GND → R611 1k → U403 /OE, against R407 10k to +3V3 (sheet 4) | **Live:** U403 enables immediately. Change it only with JTAG idle and **no cable on J201** (§5) |

Positions 1–3 are readable live in STATUS b4–b6 (zorro-interface-spec §9).

**Levels** [V]:
- **Positions 1–3:** ON gives 3.135 × 10/11 ≥ 2.85 V, above the LVCMOS33 VIH of 2.0 V [V S49]. OFF gives 0 V through 10 kΩ. ON draws 0.3 mA per position.
- **Position 4:** ON gives 3.465 × 1/(1 + 9.9) ≤ 0.32 V, below the U403 /OE VIL of 0.7 V [V S66]. OFF gives 3.3 V through R407.

**Defaults, all OFF:** 64 KB mode A (D-03), INT2, armed, JTAG option isolated (D-12).

**Pin 71 while erased:** the SSPI port responds only with SN low, and SN is held high by R208, so the switch cannot disturb configuration [V S64].

**Glitches and metastability:**
- **Bounce:** mechanical DIP switches bounce [K]. Positions 1–3 matter only while a reset is in progress. A change during the reset window, especially at its release, can latch either value.
- **No synchroniser:** the RTL samples these inputs without a synchroniser (`z2_core.v`), so a change exactly at reset release could, in principle, go metastable.
- **Procedure:** **change SW601 only with the A2000 powered off.**
- **HDL-stage recommendation:** a two-flip-flop synchroniser on DIP_MODE_B, DIP_INT6 and DIP_DISABLE, with STA and formal re-run. **No RTL change now.**

**Power loss:** positions 1–3 switch an unpowered +3V3, and position 4 switches GND. Nothing drives an FPGA or U403 pin from another rail (C-29).

**Layout requirements (Stage 6):**
- SW601's ON side is marked on the silkscreen with an arrow and the word ON.
- Position numbers 1–4, and the legend "1 512K, 2 INT6, 3 DISABLE, 4 RP JTAG".
- The note "SW601-4 ON only with no cable on J201".
- The physical orientation (pin 1 versus position 1) must be verified against the chosen part's drawing (MPN TBV). Checked by M-26.

## 4. Debug header J601 and its isolation (S6-4)

### 4.1 Why CLAMP=OFF alone is not defensible (option A)

**MachXO2 sysIO User Guide** (FPGA-TN-02158-2.4 [V S64]):
- **§9.1.5 CLAMP:** default ON for inputs. **Unlike every other attribute in §9.1** (PULLMODE, HYSTERESIS, VREF, OPENDRAIN, SLEWRATE, DIFFRESISTOR), it gives **no "Hardware Default (Erased)" value**. The clamp state of an erased, unconfigured or configuring device is therefore **not documented**.
- **CLAMP=OFF is a bitstream attribute.** It cannot apply before a successful configuration, or after a configuration fault.
- **Appendix D** ("GPIO Input Prevents Powering Down the FPGA") describes the exact failure mode: an external circuit driving inputs through the clamps into a VCC/VCCIO rail tied to other devices (our +3V3). It warns that "chip failures can occur when the datasheet input current limits are exceeded". It recommends limiting pad current to **n × 8 mA per group between power pins**, with 200 Ω–1 kΩ series resistors.

**MachXO2 data sheet Table 3.6** (hot socketing [V S49]):
- IDK ≤ ±1 mA for 0 < VIN < VIH(max) (3.6 V for LVCMOS33);
- conditions 0 < VCC, 0 < VCCIO;
- "assumes monotonic rise/fall";
- **"Internal clamp diode disabled"**.

**Conclusion:** this specification describes power sequencing with the clamp disabled. It does **not** establish a limit for an erased or unconfigured device (clamp state unknown), for a fully unpowered carrier with other loads on +3V3, or for a tool above 3.6 V.

**So option A cannot be defended for the erased, configuring, configuration-fault or unpowered states.** A 100 Ω resistor alone would allow (3.6 − 0.6) / 100 = 30 mA per pin, far above Appendix D's 8 mA guidance.

### 4.2 Options compared

| Option | Protection | Cost [E] | Function | Verdict |
|---|---|---|---|---|
| A. CLAMP=OFF + series resistors | Only after configuration; undefined erased or unpowered; would need ≥ 1 kΩ to meet Appendix D's 8 mA guidance, which limits speed | ~AUD 0.10 | Slow with 1 kΩ | **Not defensible alone** |
| **B. SN74AVC4T774 isolation buffer (U601)** | **Ioff ≤ ±1 µA and "if either VCC input is at GND, both ports are in the high-impedance state"** [V S66], whatever the FPGA's state. Same part and mechanism as the sheet-4 host link (C-29 compliance) | **~AUD 1.0–3.0** (U601 + 3 capacitors + 20 resistors + PTC + diode; the header is needed anyway) | Up to 200–380 Mbps [V S66]: adequate for the ≤ 25–50 MHz faster host interface. Fixed direction per channel (straps) | **Chosen: lowest-cost defensible option** |
| C. Header unpopulated, or the FPGA isolated by DNP resistors | Complete while unpopulated | ~AUD 0 | **None until populated**; protection then depends on what is fitted | Kept as an **assembly option** (U601 and J601 DNP), not the design |

### 4.3 The drawn circuit (option B)

**FPGA side:** DBG0–DBG3 (pins 9–12, bank 5) → R619–R622 330 Ω → U601 A1–A4. U601 VCCA = +3V3 (C601).
- The 330 Ω bounds contention to ≤ 3.6 V / 330 Ω = 10.9 mA. That can happen if the RTL drives a pin that the strap makes a buffer output.
- R623–R626 100 kΩ pull-downs define the FPGA pins low whenever U601 is Hi-Z (R-51).

**Header side:**
- U601 B1–B4 → R627–R630 33 Ω (termination) → J601 pins 3, 5, 7, 9.
- R631–R634 100 kΩ pull-downs on the B side define the signals with the header open.
- VCCB = **DBG_VREF** (C602, C603).

**Header supply, J601 pin 1:**
- +3V3 → **F601** PTC, 0.05 A hold → **D608** Schottky → DBG_VREF, about 2.9–3.1 V.
- **A tool connected to pin 1, powered or not, cannot back-feed the carrier.** The diode is reverse-biased and leaks only microamps [K].
- With the carrier off and a tool powering DBG_VREF, U601 has VCCA = 0, so both ports are Hi-Z (VCC isolation) and Ioff ≤ 1 µA.
- 0.05 A keeps +3V3 within its 0.25 A design maximum (§8).

**Directions** (DIR straps R615–R618 10 kΩ, referenced to VCCA):
- DBG0–DBG2: header → FPGA (DIR low).
- DBG3: FPGA → header (DIR high).
- This suits an SPI-slave arrangement for the future faster host interface (SCK, MOSI, CS_N in; MISO out). Changing a direction means moving a strap.
- **RTL contract (HDL stage):** DBG0–DBG2 are FPGA inputs, DBG3 an output, unless the straps change.

**OE** is tied low: enabled whenever both supplies are up. This is the same arrangement as U401/U404.

**J601** (keyed 2×5 box header):

| Pin | Signal |
|---|---|
| 1 | DBG_VREF (protected supply out) |
| 3, 5, 7, 9 | DBG0–DBG3 |
| 2, 4, 6, 8, 10 | GND (a ground beside every signal) |

The silkscreen carries the pin-1 mark, the full pinout, the directions and the text "VREF out, protected, 50 mA".

**Inactive states:**

| State | Result |
|---|---|
| FPGA erased, configuring, failed or in reset | U601 powered; DBG0–2 driven by U601 from the header side (low with nothing connected); DBG3's header pin follows the FPGA pin (weak pull-down, then R623) |
| Carrier off | U601 Hi-Z; no path in either direction |
| Header open | B side low through R631–R634 |

### 4.4 Evidence still required before final approval

- **M-27:** with the carrier unpowered, drive each J601 signal pin and pin 1 from a 3.3 V and a 3.6 V current-limited source.
  - Measure the current into the carrier and the voltage on +3V3: ≤ 10 µA per pin, +3V3 ≤ 0.1 V.
  - Repeat with the FPGA erased, and configured with CLAMP left at its default.
- **The diode** (MPN, leakage at 60 °C), the PTC (MPN, hold and trip) and the box header (MPN) are TBV.

## 5. JTAG contention (S6-5)

**The hazard:** SW601-4 ON enables U403, so the RP2040's GP14/15/26 drive FPGA_TCK/TMS/TDI. A programming cable on J201 drives the same nets. Push-pull against push-pull, with nothing between them, would exceed U403's ±12 mA output rating [V S66].

**Interlock investigation:**

| Approach | Finding |
|---|---|
| Electrical cable detection | J201's pin 1 (VREF) is a sense input of the cable (high impedance [K]). No J201 pin identifies a mated cable, so no detection without a non-standard cable |
| Mechanical interlock | A shunt beside J201 that the mated housing blocks, replacing SW601-4. Depends on the housing and layout (TBV); it would also move SW601-4 off the DIP you approved |
| **Current limiting (implemented)** | **R432–R434 330 Ω** in series with U403's A outputs (sheet 4). Worst case 3.6 V / 330 Ω = **10.9 mA**: within U403's ±12 mA, and within typical cable drivers (±24 mA class [K]). The JTAG transfer is corrupted, but **no part is overstressed**. RP2040 JTAG timing: 330 Ω × ~15 pF ≈ 5 ns, adequate for TCK ≤ 10 MHz [E]. The TCK pull-down R205 4.7 kΩ gives a high level of 3.3 × 4.7/5.03 = 3.08 V |

**Procedure (mandatory, silkscreen and service notes):** SW601-4 ON only with no cable on J201. Connect or remove a J201 cable only with SW601-4 OFF. Change SW601-4 only with JTAG idle.

**Open hardware requirement R-58:** a mechanical interlock can be evaluated at layout. **M-28** measures the contention current with a real cable.

## 6. Behaviour in every power and reset state (implementation requirement 9)

| State | LED_READY | RP LEDs | +3V3 LED | X4 LED | DIP inputs | RP_JTAG_EN_N | J601 / U601 |
|---|---|---|---|---|---|---|---|
| FPGA erased | Off (weak pull-down) | Per the RP2040 | On | Per the X4 rail | Defined by pull-downs; ignored | Per SW601-4 | U601 active; DBG pins defined, no FPGA drive |
| FPGA configuring or reset | Off | Per the RP2040 | On | Per rail | Positions 1–3 sampled during the Zorro reset | As above | As above |
| FPGA configuration fault | Off | Per the RP2040 | On | Per rail | Not sampled | As above | As above (no reliance on CLAMP) |
| RP2040 reset or unpowered (X4 on) | Unaffected | Off | On | On | Unaffected | U403 isolated or enabled per SW601-4; RP2040 pins pulled down | Unaffected |
| X4 shutdown (S5) or off | Unaffected | Off (U404 Hi-Z) | On | Off after decay (unless an external source) | Unaffected | U403 VCCB off → Hi-Z | Unaffected |
| Carrier power loss (+3V3 off) | Off | Off | Off | Per the X4 rail | No current (switches to the dead rail or GND) | No current | U601 Hi-Z (VCC isolation), Ioff ≤ 1 µA; D608 blocks pin 1 |
| External source on the X4's USB-C | Unaffected | Per the RP2040 | Per +3V3 | **On** | – | – | – |

## 7. Checks

| Check | Result |
|---|---|
| `audit_sheet6.py` | **189 checks, 0 failures**: every LED path, current and the U404 budget; READY only from pin 65; DIP polarity, levels, members and defaults; RP_JTAG_EN_N; U601 supplies, OE, straps and every channel's series and pull resistors; the J601 pinout; DBG_VREF reachable from +3V3 only through F601 + D608; no direct header-to-FPGA path; TP601/TP602; R432–R434 |
| Mutation test (scratchpad `kigen/mut_audit6.py`) | **26 of 26** injected faults detected |
| Sheet-4 mutation test | **30 of 30** (one new: R432 bypassed) |
| Sheet-5 mutation test | 28 of 28 |
| Audits 1–5 | 418 / 1180 / 159 / 226 / 274, 0 failures |
| ERC | **14 entries**, only the permanent pin-to-pin entries, identical to before ([ERC report](sheet6-erc-report.md)). Every sheet pin is connected |
| Netlist outside sheet 6 | Identical to PR #11, except U403 A1–A3, which now reach FPGA_TCK/TMS/TDI through R432–R434 |

## 8. Power budget change

**+3V3:**
- LEDs D601–D606: ≤ 10 mA, the 10 mA already allowed.
- DIP positions ON: ≤ 0.9 mA.
- U601: µA.
- Header supply: ≤ 50 mA (PTC hold).
- New design sum: 0.158 + 0.001 + 0.050 = **0.209 A**, within the 0.25 A design maximum.
- U504 dissipation stays ≤ 0.67 W at 0.25 A.

**X4_12V:** + 1.1 mA (D607).

## 9. Electrical and functional verification checklist

| ID | Check | Pass criterion |
|---|---|---|
| M-25 | LED states and currents in every §6 state, including READY with the RP2040 held in reset and the X4 off (C-26) | Matches §2/§6; currents 0.8–1.7 mA (X4 LED about 1 mA) |
| M-26 | SW601: each position ON/OFF read back in STATUS b4–b6; the defaults; behaviour of a change during reset; RP_JTAG_EN_N levels; physical orientation against the silkscreen | Levels as §3; sampled only in reset; orientation correct |
| M-27 | Debug-header isolation (§4.4): carrier off, FPGA erased or configured, 3.3 V and 3.6 V sources on each J601 pin and on pin 1 | ≤ 10 µA per pin; +3V3 ≤ 0.1 V; no LED glow |
| M-28 | JTAG contention: J201 cable connected, SW601-4 ON, cable and RP2040 driving opposite levels | ≤ 12 mA on each of TCK/TMS/TDI; no damage after 10 minutes |
| M-29 | Debug header in use: 25 MHz signals through U601 with a tool on J601 | Edges clean, 0 errors |

## 10. Changes to other sheets (all requested by these decisions)

**Sheet 4 (S6-5):**
- R432–R434 330 Ω between U403 A1–A3 and FPGA_TCK/TMS/TDI, with a jog fan-out so the text stays clear.
- `audit_sheet4.py` checks them; mutation test 30 of 30.

**Sheet 5 (S6-1):**
- X4_12V is now a hierarchical label (labels only, no new parts or connections on sheet 5).
- `audit_sheet5.py` is unchanged and passes.

**Root:**
- Sheet 6's block and pins.
- Labels join them to sheet 2 (LED_READY, DIP_*, DBG0–3), sheet 4 (LED_RP0–3, RP_JTAG_EN_N) and sheet 5 (X4_12V).

**`audit_sheet2.py`:**
- No open nets remain.
- The DIP inputs are checked as series-plus-pull-down networks.
- LED_READY's resistor load is accepted.
- The J201 net members include R432–R434.

## 11. Open items (nothing closed)

- **G-SHEET6 final approval:** M-27 (isolation) and M-28 (contention) evidence; the mechanical-interlock evaluation at layout (R-58).
- **C-29 / R-49 and R-51 remain open** until the final implementation and these validations are documented.
- **MPNs TBV:** LEDs (Vf and brightness at 1 mA), SW601 (orientation drawing), J601 box header, D608 (leakage), F601 (hold and trip).
- **HDL stage:**
  - two-flip-flop synchronisers on the DIP inputs;
  - the DBG direction contract (DBG0–2 in, DBG3 out);
  - CLAMP may still be set OFF on the DBG pins as extra protection, but **it is not relied on**.
- **Firmware:** FW-9 to FW-12 (LED meanings) join FW-1 to FW-8.
