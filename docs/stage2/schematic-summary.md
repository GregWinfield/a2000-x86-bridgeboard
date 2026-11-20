# Six-sheet schematic summary and what remains before PCB placement

**Status:** 2026-11-21, with sheet 6 revision A drawn.
- All six sheets now exist in KiCad 10, and every sheet pin is connected.
- **Nothing is electrically validated. No PCB placement or fabrication is authorised.**
- Every hardware and manufacturing gate is open.

## 1. The design at a glance

An Amiga 2000 Zorro II card carrying a Radxa X4 (Intel N100). The two systems share 512 KB of SRAM, mailboxes and interrupts through a MachXO2 FPGA. The host link runs over the X4's RP2040 (SPI).

| Sheet | Revision | Contents | Gate | Netlist audit | Main open evidence |
|---|---|---|---|---|---|
| 1 Zorro II interface | B | J101 edge; U101/U102 SN74LVC16244A (address); U103 SN74LVCH16T245 (data, bus-hold); U104 SN74LVC8T245 (/SLAVEn, /CFGOUTn, gated by CARD_EN_N); U105 LVC07A; U106 LVC1G00; U107 LVC32A (enable gating); U108/U109 TPS3808 (EN_OK); JP101 hard disable. Zorro power pins unconnected | **G-SHEET1** approved for design progression | 418 | M-1 to M-12: bus timing (/SLAVEn, address hazard M-7 ≥ 19.8 ns on the 4000HC), terminations on the target machine |
| 2 FPGA and configuration | A2 | U201 LCMXO2-4000HC-4TG144C (C-30); 50 MHz oscillator; J201 JTAG; configuration resistors; decoupling. 101 signals; **pin plan frozen**; 6 spare (23, 24, 67; 31, 63, 103 kept free for the 2000HC) | **G-SHEET2** approved | 1180 | FB201/J201 MPNs; R209 provisional |
| 3 Shared SRAM | A1 | U301 IS61WV25616EDBLL-10 (256K × 16) on LD/SA; safe-state pull-ups | **G-SHEET3** approved | 159 | M-11 (SRAM timing on hardware) |
| 4 RP2040 host link | A3 (+ R432–R434) | J401 X4 ribbon; U401–U404 SN74AVC4T774 (VCC isolation); **S4-6** U402 output enable (U405 TLV3201, Q401/Q402, U406); **R432–R434** (S6-5) | **G-SHEET4** schematic baseline | 226 | **M-16 (a)–(g)** before manufacture (K4, disable latency, GP24 margin); M-13, M-15 |
| 5 Power and X4 power control | A | U501 TPS259470L X4 eFuse (ILIM 2.65–3.36 A), U502 INA226 at 0x44, fail-safe enable Q501/Q502 + JP501, U503 TPS259470L 5 V (OVLO 5.53–6.01 V), U504 TLV76733, Q503 S0 sense (active low), bonded standoff pads | **G-SHEET5 pending** your review (PR #10, #11) | 274 | Your §8 confirmations; S5-8 conditional; M-17 to M-24; R-56 ratings |
| 6 Diagnostics, switches, debug | A | D601–D607 LEDs; SW601 (mode B, INT6, disable, JTAG option); J601 debug header through U601 SN74AVC4T774; TP601/TP602 | **G-SHEET6** approved for design progression | 189 | M-27 (isolation), M-28 (JTAG contention), M-25, M-26, M-29 |

**Whole project:**

| Item | Value |
|---|---|
| Parts (without power symbols) | 308 |
| Nets | 344 |
| ERC | **14 entries, all permanent and documented** (12 U104 spare channels, 2 spare translator channels) |
| Netlist mutation tests | sheet 4 30/30, sheet 5 28/28, sheet 6 26/26 |
| HDL | `hdl/run_checks.sh` ALL PASSED (G-SIM). Diamond STA on the 4000HC: every Zorro path ≤ 14.773 ns, /SLAVEn board total 21.92 ns, 50 MHz slack ≥ 2.21 ns |
| BOM estimate | AUD 250.34–496.91 including the X4 and its cooler; carrier alone AUD 140.34–341.91 [E]. Most prices not checked |

## 2. Domain and safety architecture

| Concern | How the six sheets handle it | Evidence still needed |
|---|---|---|
| Unpowered or blank card in a running A2000 (C-03, R-31) | Every Zorro driver is Hi-Z unless EN_OK and ZF_ARM; the slot looks empty | M-6, M-8, M-9 |
| Back-powering the FPGA (C-29, R-49) | Every input from another domain passes an Ioff/VCC-isolated buffer: sheets 1, 3 and 4, and U601 for the debug header. Pull-ups go to +3V3 only. Switches reach only +3V3 or GND | M-14, M-16, M-27 |
| The X4's K4 key cutting the RP2040's supply (S4-6, R-52) | Comparator-gated U402 enable | M-16 (a)–(g) |
| X4 12 V supply (S5-1/S5-2) | eFuse with UVLO/OVLO, ILIM, blanking, fast trip, latch-off; FPGA overload trip; fuse | M-17, M-18 |
| X4 power default off and interlock (S5-3/S5-9) | Hardware default off in every FPGA state; external-source check before enable (PM-2) | M-20 |
| 5 V overvoltage (S5-6) | OVLO disconnect; bulk capacitor; 18 V-rated LDO | M-23 |
| Ground return (S5-8, conditional) | Model; bonded standoffs (if the X4's holes are bonded); harness rules | M-21 (a)–(e) |
| USB-C back-feed (R-05) | Secured shroud + detection + interlock; X4-power LED as an indicator | G-R05, M-20 |
| JTAG contention (S6-5) | 330 Ω current limiting + procedure | M-28; mechanical interlock at layout (R-58) |

**Owner-facing decision rules in force:**
- bounds are model-derived, never "guaranteed";
- no operating-rule-only safety solutions;
- rounding conservative.

## 3. What remains before PCB placement (gate G-PLACE)

**G-PLACE** (new in the baseline) lists what must be complete before placement starts. Placement is not manufacture.

### 3.1 Your reviews and decisions

1. **Sheet 5 (PR #10 rev A1, PR #11):**
   - the six confirmations of proposal §8;
   - G-SHEET5;
   - and, if M-21 (a) finds the X4's mounting holes isolated, your choice between accepting the ribbon as the main X4 return and adding an X4-side ground strap.
2. **Sheet 6 (this implementation PR): final G-SHEET6.**
   - It needs M-27 (debug isolation) and M-28 (JTAG contention). Both are bench measurements.
   - **Your decision:**
     - (a) measure them before placement on a bench rig: a MachXO2 development board, an SN74AVC4T774 breakout and a JTAG cable; or
     - (b) accept the datasheet-based design for placement and measure on the first prototype, before any A2000 use.
   - The same question applies to the other pre-layout bench items you might want: an X4 start-up measurement (M-17) needs only the X4 and a lab supply.
3. The final status of the earlier conditional items: R-52/M-16 and the S4-6 qualification plan remain manufacturing gates, not placement gates.

### 3.2 Parts and footprints (R-56)

4. **MPN selection with verified ratings.** The manufacturer specifications could not be fetched here. Each part must meet the requirement derived from the analyses:

   | Part | Requirement |
   |---|---|
   | J501 drive-power header | ≥ 6 A per contact; pin numbering against the A2000 harness |
   | J502 X4 lead connector | ≥ 4 A and ≤ 20 mΩ per contact |
   | The 2.54 mm housing for the X4's J10 | As J502, with 22 AWG |
   | J401 box header, 40-way ribbon and IDC sockets | ≥ 1 A per conductor and contact |
   | J601 box header | – |
   | F501 / F502 | 5 A / 1 A time-lag |
   | F601 | 0.05 A PTC |
   | D501 / D502 | SMBJ15A / SMBJ13A from a datasheet (the [K] values become [V]) |
   | D608 | Leakage |
   | R501 shunt, C501, C513 | – |
   | SW601 | Orientation drawing |
   | LEDs | Vf and brightness at 1 mA |
   | FB201, J201 | – |

5. **Footprints:**
   - the project's TI RPW0010A footprint against TI's current drawing;
   - every chosen MPN's footprint (DIP, box headers, Micro-Fit, MATE-N-LOK, NANO2 fuse, CP sizes);
   - the Zorro edge (bevel, finger length and bracket orientation are TBV in sheet 1).

### 3.3 Mechanical (R-08)

6. **A2000 data:**
   - slot pitch;
   - card length, height and outline;
   - bracket;
   - two-slot occupancy (D-08);
   - clearance to neighbouring cards.
7. **X4 placement:**
   - standoff heights and the X4 position;
   - the mounting-hole bonding check M-21 (a), which decides whether H501–H504 are the dedicated ground return;
   - a ribbon of ≤ 15 cm (D-07) with J401's position;
   - J502 and the lead route (22 AWG twisted pair ≤ 15 cm);
   - J501's position relative to the A2000 drive-power harness;
   - LED visibility.

### 3.4 Layout rules to collect into a constraints document

8. **Zorro bus:**
   - edge-to-buffer distances;
   - U103 bus-hold;
   - the STA board budget: trace delays assumed in the /SLAVEn and data paths must be honoured.
9. **Host link:** ribbon series terminations (R411–R414, values TBV at layout), the SPI timing budget (M-15) and the S4-6 nodes.
10. **Power:**
    - the 12 V path and its return as a pair;
    - a direct pour from J502 GND to J501 GND;
    - no plane splits;
    - U501 with 8 thermal vias;
    - U504's thermal pad with ≥ 4 vias;
    - the creepage and spacing of the 12 V nets;
    - Kelvin routing of R501.
11. **Stack-up:** 4-layer stack and the impedance of the fast nets; a mechanical-interlock evaluation for J201 versus SW601-4 (R-58).

### 3.5 Not needed for placement, but open

- **HDL stage:**
  - the power manager PM-1 to PM-10;
  - DIP synchronisers (R-59);
  - the DBG direction contract;
  - optional CLAMP=OFF, not relied on;
  - the Diamond Power Calculator GUI run (P-1).
- **RP2040 firmware** FW-1 to FW-12; the Windows software.
- **All M-numbers on prototypes**, G-PSU before any A2000 use, G-ZEROWAIT, G-R05.

## 4. Where to look

| Topic | Document |
|---|---|
| Per-sheet design notes | [sheet 1](sheet1-design-notes.md), [sheet 2](sheet2-design-notes.md), [sheet 3](sheet3-design-notes.md), [sheet 4](sheet4-design-notes.md), [sheet 5 proposal](sheet5-architecture-proposal.md) and [notes](sheet5-design-notes.md), [sheet 6 proposal](sheet6-architecture-proposal.md) and [notes](sheet6-design-notes.md) |
| Gates and the decision log | [02-rev1-baseline.md](../02-rev1-baseline.md) |
| Risks | [risk-register.md](../risk-register.md), revision H |
| Verification | [hdl/verification-matrix.md](../hdl/verification-matrix.md) |
| Full schematic PDF | [sheet6-schematic.pdf](sheet6-schematic.pdf) |
