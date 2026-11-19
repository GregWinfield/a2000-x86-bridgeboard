# Sheet 1: Zorro II interface and AutoConfig signal buffering (design notes)

**Status:** Stage 2, **revision B**, 2026-11-18. **Not electrically or mechanically validated.**
- ERC shows only the expected interface and tie-off items ([sheet1-erc-report.md](sheet1-erc-report.md)). The netlist audit passes (418 checks).
- Neither proves the design works. The HDL verification suite **passes** (gate G-SIM, 2026-11-18, [../hdl/verification-results.md](../hdl/verification-results.md)). Exploratory post-place-and-route STA (Diamond) passes ([sheet1-sta-results.md](sheet1-sta-results.md)). The final G-STA run at the sheet-2 pinout and the hardware measurements are still open.

**Files:**
- Schematic: [hardware/kicad/sheets/01_zorro_interface.kicad_sch](../../hardware/kicad/sheets/01_zorro_interface.kicad_sch) (KiCad 10.0.8). PDF: [sheet1-schematic.pdf](sheet1-schematic.pdf).
- Timing: [sheet1-timing-budget.md](sheet1-timing-budget.md). Decode hazards: [sheet1-hazard-analysis.md](sheet1-hazard-analysis.md).
- HDL: [../hdl/zorro-interface-spec.md](../hdl/zorro-interface-spec.md), RTL in [../../hdl/](../../hdl/).

Evidence tags follow [../sources.md](../sources.md).

## 0. Revision B in one page (owner review of revision A)

| Concern | Owner direction | Revision B change |
|---|---|---|
| **C-03 → HIGH** | Fail-safe AutoConfig bypass for the unpowered state; compare a mechanical jumper with an automatic normally-closed bypass. Do not connect the Zorro power pins | The A2000's own empty-slot terminations are verified (§6.1), so the card is made **electrically absent whenever it is not operational**. Comparison and state table in §6 |
| **C-04 → MEDIUM** | Output-enable alternative to U104, qualified by power-good and reset, without violating /SLAVEn timing | U104 is now an **SN74LVC8T245** with /OE = CARD_EN_N = NAND(EN_OK, ZF_ARM). EN_OK comes from two TPS3808 supervisors and a DISABLE jumper. The FPGA arms only inside /BUSRST. /SLAVEn budget recalculated: 29.8 ns of 35 |
| C-05 | Keep XRDY gating; prove the buffer is never enabled for an invalid cycle and direction changes cannot cause contention | U107 ORs CARD_EN_N into U103 /OE, XRDY and /INTx. HDL read enable is qualified by the data strobes and /BERR. Registered DIR with guard intervals. Assertions, simulation and formal properties written |
| **C-13 (new)** | RMW with /AS held across read and write | FSM driven by data-strobe phases. Read drive drops at the read strobe's negation (S7), long before R/W falls (S14) |
| (found during rev B) | — | **/BERR is now buffered into the FPGA** (U102 channel moved from CDAC). Haynie's A2000 notes require a card to monitor /BERR and tri-state its bus drivers [V S52] |
| C-01, C-02 | STA; hazard analysis and simulation | **Exploratory Diamond STA passes** (worst 15.31 ns against 18 ns after the I/O-standard correction; [sheet1-sta-results.md](sheet1-sta-results.md)). Hazard analysis done. Simulations and formal proofs run and pass. Setup requirement 16.4 ns (conservative) |

## 1. What this sheet does

The sheet converts the 5 V Zorro II slot interface into 3.3 V signals for the FPGA (sheet 2) and the local data bus (sheets 2 and 3), with power-off isolation in both directions.
- Revision B adds **card-enable gating**: no Zorro-side driver of this card can be active unless both carrier rails are good, the DISABLE jumper is open, and the FPGA has armed the card at a Zorro reset.
- No power is taken from the Zorro +5 V, +12 V, −5 V or −12 V pins.
- All 18 Zorro ground pins are connected to the ground plane.

| Ref | Part | Function |
|---|---|---|
| J101 | Zorro II card edge (project footprint) | 100 contacts; unit A = pins 1–50, unit B = 51–100. **Pin 15 (CDAC) is now unconnected** |
| U101, U102 | TI SN74LVC16244ADGGR | Zorro → FPGA input buffers: A1–A23, /AS, /UDS, /LDS, READ, DOE, E7M, /CFGINn, /BUSRST, **/BERR** (all 32 channels used) |
| U103 | TI SN74LVCH16T245DGGR | D0–D15 transceiver with bus-hold. **/OE = DBUF_OE_G_N** (from U107) |
| RN101–RN104 | 4 × 22 Ω arrays | Series damping on D0–D15 (value TBV, C-07) |
| **U104** | **TI SN74LVC8T245PWR** (was SN74LVC2T45) | /SLAVEn and /CFGOUTn drivers at 5 V levels. **/OE = CARD_EN_N**, DIR tied A→B, unused channels tied to GND |
| R117, R118 | 22 Ω | Series damping on /SLAVEn, /CFGOUTn |
| U105 | TI SN74LVC07APWR | Open-drain /INT2, /INT6, XRDY (inputs now from U107); /OVR, /DTACK via DNP links R119/R120 |
| **U106** | **TI SN74LVC1G00DBVR** | CARD_EN_N = NAND(EN_OK, ZF_ARM) |
| **U107** | **TI SN74LVC32APWR** | DBUF_OE_G_N, XRDY_G, INT2_G_N, INT6_G_N = FPGA signal OR CARD_EN_N |
| **U108** | **TI TPS3808G33DBVR** | +3V3 supervisor (VIT− 3.07 V), open drain to EN_OK |
| **U109** | **TI TPS3808G01DBVR** + R125 95.3 kΩ / R126 10 kΩ | +5V_BUS supervisor (VIT− 4.27 V), open drain to EN_OK |
| **JP101** | 2-pin header | DISABLE: fitted pulls EN_OK low, so the card is held off the bus |
| R101–R108 | 2.2 kΩ pull-ups | Default states of the FPGA-driven nets (§7) |
| R109 | 10 kΩ pull-down | U103 DIR default = Zorro→local |
| **R121–R124** | 10 kΩ | EN_OK pull-up, ZF_ARM pull-down, CARD_EN_N pull-up, DBUF_OE_G_N pull-up |
| C101–C122 | 20 × 100 nF + 2 × 10 µF | One 100 nF per supply pin (16 on +3V3, 4 on +5V_BUS); bulk per rail |
| TP101–TP119 | Test pads | Rev B adds TP118 CARD_EN_N and TP119 EN_OK |

## 2. Part verification (pinouts transcribed from the manufacturer documents)

Every IC pin number was entered from the document below. The netlist audit (`tools/kicad/audit_sheet1.py`, **418 checks, 0 failures**) checks every connected pin against the same tables.

| ID | Document | Facts used |
|---|---|---|
| S45 | TI SN74LVC16244A, SCAS699C | DGG pinout; tpd **1.1–4.1 ns** at 3.3 V ±0.3 V, −40 to 85 °C; inputs 5.5 V-tolerant; Ioff |
| S46 | TI SN74LVCH16T245, SCES635B | DGG pinout; bus-hold; VCC isolation; Ioff. At VCCA 3.3 V / VCCB 5 V: A→B 0.6–4.4, B→A 0.6–6.0, OE→B 0.8–6.4 / 0.8–6.3, OE→A 0.8–8.1 / 1.6–8.2 ns. Pull-up on OE for power-up |
| S48 | TI SN74LVC07A, SCAS595W | PW pinout; open drain; 5.5 V-tolerant; Ioff; tpd ≤ 3.6 ns |
| S49 | Lattice MachXO2, FPGA-DS-02056-4.7 | Weak pull-down (30–305 µA) before and during configuration; tREFRESH 1.4 ms; HC core supply **2.375–3.6 V** (Table 3.2); tPD 7.24 ns floor (−4) |
| **S53** | TI **SN74LVC8T245**, SCES584D (rev. May 2026) | PW pinout (1 VCCA, 2 DIR, 3–10 A1–A8, 11–13 GND, 14–21 B8–B1, 22 /OE, 23–24 VCCB). At VCCA 3.3 V / VCCB 5 V: A→B **0.5–4.4 ns**, OE→B enable 0.9–6.8 / disable 0.8–6.3 ns. VCC isolation (either VCC < 100 mV or floating → all outputs Hi-Z); Ioff. "Input circuitry on both A and B ports is always active and must have a logic HIGH or LOW level applied". "To put the device in the high-impedance state during power up or power down, tie OE to VCC through a pullup resistor" |
| **S54** | TI **SN74LVC1G00**, SCES212AC (rev. Aug 2026) | DBV pinout (1 A, 2 B, 3 GND, 4 Y, 5 VCC); tpd 1.0–4.7 ns at 3.3 V (CL 30/50 pF, −40 to 85 °C); Ioff |
| **S55** | TI **SN74LVC32A**, SCAS286U (rev. July 2024) | PW pinout (1 1A, 2 1B, 3 1Y, 4 2A, 5 2B, 6 2Y, 7 GND, 8 3Y, 9 3A, 10 3B, 11 4Y, 12 4A, 13 4B, 14 VCC); tpd 1.0–3.8 ns at 3.3 V; inputs 5.5 V-tolerant |
| **S56** | TI **TPS3808**, SBVS050N (rev. Aug 2026) | DBV pinout (1 RESET open drain, 2 GND, 3 MR, 4 CT, 5 SENSE, 6 VDD). VIT− 3.07 V (G33), 0.405 V (G01) ±1.5 % / ±1.25 %. CT open = 12–28 ms. MR has a 90 kΩ internal pull-up and responds to a 1 ns pulse, **so MR is tied to VDD**. RESET valid from VDD ≥ 0.8 V; pull-up 10 kΩ–1 MΩ; SENSE→RESET ≤ 20 µs |
| S51 | Commodore A2000 Rev 6 (A2000-CR) schematic, redrawn rev 1.38 | /CFGINn OR-chain U606 (74LS32); RP607 1 kΩ pull-downs on /CFGOUT1–5 (schematic sheet 6); RP800 1 kΩ pull-ups on /SLAVE1–5 into Buster (sheet 8); reset circuit |
| S52 | Dave Haynie, "100 Pin Expansion Signals on Amiga Computers" (1987) | Empty slots pass /CFGOUT→/CFGIN; cards must monitor /BERR and tri-state their bus buffers; read-data buffers consider the data strobes for RMW; DOE semantics |
| S57 | Motorola M68000 User's Manual, 9th ed. | RMW state sequence (S0–S19); #11, #13, #14A, #20A, #25, #26, #29A (8 MHz) |

**Footprints.** All from KiCad 10.0.8's standard libraries except the edge connector:
- U104 `Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm` (TI PW);
- U106 `Package_TO_SOT_SMD:SOT-23-5`;
- U107 `Package_SO:TSSOP-14_4.4x5mm_P0.65mm`;
- U108/U109 `Package_TO_SOT_SMD:SOT-23-6`;
- JP101 `PinHeader_1x02_P2.54mm_Vertical`.

Land patterns are TBV against the TI package drawings before layout.

## 3. Signal paths

- **Zorro inputs (32).** Zorro pin → LVC16244A → FPGA input (`ZB_*`). The ~OE pins are tied low. `ZB_BERR_N` is new in rev B.
- **Data.** Zorro D0–D15 → RN (22 Ω) → U103 B port; U103 A port → `LD0–LD15`. DIR from `ZF_DBUF_DIR`. /OE from `DBUF_OE_G_N = ZF_DBUF_OE_N OR CARD_EN_N`.
- **Push-pull outputs.** `ZF_SLAVE_N`, `ZF_CFGOUT_N` → U104 (A→B, /OE = CARD_EN_N) → 22 Ω → J101 pins 9, 11.
- **Open-drain outputs.** `ZF_INT2_N`, `ZF_INT6_N`, `ZF_XRDY` → U107 (OR CARD_EN_N) → U105 → J101 pins 19, 22, 18.
- **Card enable.** U108, U109 and JP101 wired-AND onto `EN_OK` (R121 pull-up), which goes to the FPGA and to U106. The FPGA drives `ZF_ARM` (R122 pull-down). U106 gives `CARD_EN_N` (R123 pull-up).
- **Clocks.** E7M is buffered as a timing reference. CDAC is no longer buffered: the channel now carries /BERR, and no PLL is locked to the bus clocks (R-29).

## 4. Timing (summary; full budget in [sheet1-timing-budget.md](sheet1-timing-budget.md))

| Path | Limit | Budget (rev B) | Status |
|---|---|---|---|
| /AS → /SLAVEn assert / negate | 35 / 50 ns | 29.8 ns (allocation); **20.7 ns with STA** | STA passes (exploratory; final at the sheet-2 pinout) |
| /AS → XRDY negated | 60 ns | 33.0 ns (allocation); **24.6 ns with STA** | as above |
| Buffer release on /AS, DS, DOE, READ, /BERR | #29A 187 ns; RMW ≥ 431 ns | 33.2 ns (allocation); **28.0 ns with STA** | as above |
| Address setup at the slot (hazard) | — | **16.4 ns** conservative from STA (8.9–9.8 ns same corner) | M-7: pass ≥ 19.4 ns ([sheet1-sta-results.md](../stage2/sheet1-sta-results.md) §4) |
| CARD_EN_N (C-04) | Not in any bus-cycle path | Static during operation; changes inside /BUSRST or on a fault | — |

## 5. Power-off isolation and back-feed (ER-3)

| State | U101/U102 | U103 | **U104 (rev B)** | U105 | U106/U107/U108/U109 | Zorro-side effect |
|---|---|---|---|---|---|---|
| Amiga on; carrier unpowered (Molex unplugged or fuse open) | Ioff; inputs 5.5 V-tolerant | VCC isolation, Ioff | VCC isolation (both VCC < 100 mV) and Ioff [V S53] | Ioff | Unpowered; on the 3.3 V side only | **Slot looks empty:** /SLAVEn negated by RP800, /CFGOUTn asserted by RP607 so the chain passes (§6). No back-feed |
| +5V_BUS present, +3V3 absent | Ioff | VCCA 0 → Hi-Z | VCCA 0 → Hi-Z | Ioff | EN_OK low (pull-up rail at 0 V) | As above |
| +3V3 present, +5V_BUS absent | Normal | VCCB 0 → Hi-Z | VCCB 0 → Hi-Z | Inputs held high by U107 (CARD_EN_N high) | U109 asserts → EN_OK low → CARD_EN_N high | As above; the FPGA disarms |
| Supplies ramping | Outputs only drive FPGA inputs | /OE high: R124 and U107 (CARD_EN_N high) | /OE high: R123 tracks +3V3, U106 input ZF_ARM is low | Released | Supervisors hold EN_OK low from VDD ≥ 0.8 V | Hi-Z throughout (C-04 resolved) |
| Amiga off | – | – | – | – | – | Same PSU: all off together |

**Back-feed paths ruled out (rev A list still holds) plus:**
- **U109 SENSE.** It is fed from +5V_BUS through 95.3 kΩ / 10 kΩ, so it sits at ≤ 0.48 V even with its VDD (+3V3) at 0 V. That is below any ESD-diode conduction, so there is no meaningful injection into a dead +3V3 rail [D].
- **U106/U107.** They connect only to +3V3-domain nets, which are unpowered together.
- **The A2000 terminations.** RP800 pulls the U104 B1 output (Hi-Z) up to +5 V. The leakage current is bounded by the LVC8T245 Ioff specification [V S53], so it does not back-feed the carrier.

## 6. Card enable, AutoConfig bypass and start-up (C-03 HIGH, C-04 MEDIUM)

### 6.1 What the A2000 already does (verified)

- **Chain logic.** U606 (74LS32) ORs each slot's /CFGINn with that slot's /CFGOUTn to form the next slot's /CFGIN [V S51 sheet 6].
- **/CFGOUTn termination.** RP607 is 1 kΩ to GND on /CFGOUT1–5 [V S51 sheet 6]. An empty slot, or an undriven /CFGOUTn, reads as **asserted**, so the OR passes /CFGINn on. Haynie: "On-board logic automatically passes on the state of the previous CFGOUT to the next CFGIN for any slot not occupied by a PIC, so there's no need to sequentially populate the Expansion Bus Slots" [V S52].
- **/SLAVEn termination.** RP800 is 1 kΩ to +5 V on /SLAVE1–5 into Buster [V S51 sheet 8]. An undriven /SLAVEn reads as **negated**.

**Consequence.** A card whose /SLAVEn and /CFGOUTn outputs are high-impedance is, on those two lines, electrically identical to an empty slot.
- The rev A "float" concern is therefore answered by the motherboard itself, for the unpowered state.
- The real rev A defect was the **powered but not operational** state. U104 (no OE) drove /CFGOUTn negated through R102 whenever the rails were up. That blocked every downstream board while the FPGA was blank, configuring or misbehaving (C-10), and left the outputs undefined during the supply ramp (C-04).
- Other A2000 revisions are TBV (C-15, M-8).

### 6.2 Options compared

| | A. Mechanical bypass jumper | B. Automatic normally-closed bypass | **C. Native transparency + OE gating (adopted)** |
|---|---|---|---|
| Principle | Link /CFGINn to /CFGOUTn at the card edge while the carrier is unpowered | Normally-closed switch between /CFGINn and /CFGOUTn (Form-B PhotoMOS, NC relay contact or depletion FET), held open by carrier power | Every carrier output on /SLAVEn, /CFGOUTn, data, XRDY and /INTx is Hi-Z whenever the card is not operational; the A2000's U606/RP607/RP800 do the bypass |
| Unpowered carrier | Works only if someone fitted it | Automatic | **Automatic** (VCC isolation, Ioff) |
| Powered, not ready (blank, configuring, reset, fault) | If left fitted, U104 drives /CFGOUTn against U606 through the link: **contention**. Avoiding it needs a changeover jumper; still manual | Switch opens at power-up, then U104 drives /CFGOUTn negated and blocks the chain unless it is also OE-gated. Needs C anyway | **Automatic** (CARD_EN_N) |
| Start-up sequencing | – | Millisecond switching [K] must be sequenced against U104 to avoid two drivers | Join only inside /BUSRST |
| Failure modes | Human error: forgotten jumper | Stuck closed: permanent bypass plus contention. Stuck open: as rev A. Needs continuous drive current from the carrier rails [K] | Relies on the motherboard terminations (Rev 6 verified; others M-8). A stuck-low CARD_EN_N behaves like rev A |
| Covers data, XRDY, /INTx | No | No | **Yes** (U103 /OE and U105 inputs gated) |
| Zorro power used | No | No | **No** |
| Added cost [E] | ≈ AUD 0.5 | ≈ AUD 3–8 (switch + driver) | ≈ AUD 3.4–10.2 (LVC8T245 instead of LVC2T45, NAND, quad OR, two supervisors, jumper, passives); covers every state and output |
| Verdict | Rejected: manual, contention risk | Rejected: redundant with RP607, adds a failure mode and sequencing | **Adopted**, plus an explicit **DISABLE jumper** on the 3.3 V side, which can never fight a Zorro driver |

### 6.3 Implementation (schematic rev B)

- **EN_OK** = U108 RESET (+3V3 ≥ 3.07 V) AND U109 RESET (+5V_BUS ≥ 4.27 V) AND JP101 open. Open-drain wired-AND with a 10 kΩ pull-up to +3V3.
  - CT is open: each supervisor releases 12–28 ms after its rail is good.
  - MR is tied to VDD.
  - The 4.27 V threshold is TBV against the sheet-5 +5V_BUS tolerance.
- **CARD_EN_N** = NAND(EN_OK, ZF_ARM) (U106).
  - R123 holds it high while +3V3 ramps (TI recommendation [V S53]).
  - R122 holds ZF_ARM low for a blank or configuring FPGA, together with the MachXO2's own weak pull-down [V S49].
- **U104** /OE = CARD_EN_N. **U107** gates U103 /OE (with R124 pull-up), XRDY and /INTx.
  - Unused U104 A3–A8 and B3–B8 are tied to GND: the inputs must not float [V S53], and when the outputs are enabled they drive low into ground, the same level.
  - This produces 12 expected ERC pin-to-pin warnings ([sheet1-erc-report.md](sheet1-erc-report.md)).
- **FPGA arming** (HDL spec §4):
  - ZF_ARM is set only while the filtered /BUSRST is asserted **and** EN_OK is true. It is cleared on the next clock when EN_OK falls.
  - DIP disable means the card never arms.
  - The /BUSRST synchroniser starts negated after every (re)configuration, so a reloaded FPGA cannot arm without a real reset.
  - The card therefore joins the AutoConfig chain only at a reset boundary, never in the middle of a scan.

### 6.4 Behaviour by state (C-03 demonstration)

"Sim" names the scenario in [../../hdl/sim/tb_chain.v](../../hdl/sim/tb_chain.v) (chain of three slots) or [../../hdl/sim/tb_z2.v](../../hdl/sim/tb_z2.v) that checks it. **All listed scenarios pass** (2026-11-18, [../hdl/verification-results.md](../hdl/verification-results.md)).

| State | EN_OK | ZF_ARM | U104 | /SLAVEn | /CFGOUTn | AutoConfig result | Sim |
|---|---|---|---|---|---|---|---|
| Normal: carrier and A2000 powered together | 1 after 12–28 ms | 1, armed during the ≈ 0.7 s A2000 reset | Enabled | Driven; asserted only when selected | Negated until configured or shut up, then asserted while /CFGINn is asserted | Card configured in slot order, downstream boards after it | chain S1; z2 T0–T3 |
| Carrier unpowered | 0 | 0 | Hi-Z (VCC isolation) | Negated (RP800) | Asserted (RP607), chain passes | Card absent; downstream boards configure | chain S2; z2 T18 |
| Powered, FPGA blank or being programmed | 1 | 0 | Hi-Z | Negated | Passes | Card absent; chain passes (**rev A blocked it**) | chain S3 |
| Supplies ramping | 0 | 0 | Hi-Z | Negated | Passes | A2000 in reset | z2 T0 |
| Carrier power good only after the A2000 reset ended | 1 (late) | 0 (no reset seen) | Hi-Z | Negated | Passes | Absent this boot; joins at the next reset (Ctrl-A-A) | chain S4 |
| FPGA reloaded while running | 1 | 0 until the next reset | Hi-Z | Negated | Passes | Leaves the bus; other boards unaffected; rejoins at the next reset | chain S5; z2 T17 |
| Carrier power lost while running | 0 | 0 | Hi-Z | Negated | Passes | Card disappears. Accesses to its window get the automatic DTACK and undefined data, with no collision; drivers must check MAGIC | chain S6; z2 T18 |
| +3V3 fails, +5V_BUS present | 0 | – | Hi-Z (VCCA 0) | Negated | Passes | As above | analysis §5 |
| +5V_BUS fails, +3V3 present | 0 | 0 | Hi-Z (VCCB 0) | Negated | Passes | As above | analysis §5 |
| Brown-out below a threshold | 0 for ≥ 12 ms | 0 | Hi-Z | Negated | Passes | Leaves; rejoins at the next reset | z2 T15 (same logic path) |
| DIP disable | 1 | 0 (never) | Hi-Z | Negated | Passes | Absent | chain S7; z2 T14 |
| DISABLE jumper fitted (e.g. faulty bitstream) | 0 | – | Hi-Z regardless of the FPGA | Negated | Passes | Absent | chain S8; z2 T15 |
| /BUSRST (keyboard reset) | 1 | 1 (re-evaluated) | Enabled | Negated | Negated until configured again | Normal re-configuration; SCRATCH survives | chain S9; z2 T12 |
| Shut up by the OS | 1 | 1 | Enabled | Never asserted | Asserted | Card ignored; downstream configured | chain S10; z2 T13 |
| FPGA logic fault after arming | 1 | 1 | Enabled | Undefined | Undefined | **Not covered by hardware** except the XRDY watchdog (if the fault is elsewhere) and the DISABLE jumper | — |

### 6.5 Residual risks

- **R-37 / C-15.** The terminations are verified on the Rev 6 schematic only. Haynie's statement covers the B2000 design generally. Measure each target machine (M-8). If a machine lacks them, the rev A operating rule applies there: never run with the carrier fitted and unpowered.
- **R-36.** If EN_OK is released after the A2000 reset ends (slow carrier supplies, a short reset), the card is absent until the next reset. This is safe, but must be measured (M-9).

## 7. Safe default states (ER-3)

MachXO2 I/O are tri-stated with a weak pull-down (30–305 µA) before and during configuration [V S49]. Every default resistor makes the card **inactive and non-driving**:

| Net | Resistor | Default | Effect | Check against IPD 305 µA |
|---|---|---|---|---|
| ZF_SLAVE_N, ZF_CFGOUT_N, ZF_INT2_N, ZF_INT6_N, ZF_XRDY, ZF_OVR_N, ZF_DTACK_N, ZF_DBUF_OE_N | R101–R108 2.2 kΩ ↑ | High | Inactive at the U104/U107 inputs (defined levels while Hi-Z) | 3.0 V − 0.67 V = 2.33 V > VIH 2.0 V |
| ZF_DBUF_DIR | R109 10 kΩ ↓ | Low | U103 B→A, never drives Zorro | FPGA pull-down assists |
| **ZF_ARM** | **R122 10 kΩ ↓** | Low | Not armed → CARD_EN_N high | FPGA pull-down assists |
| **EN_OK** | **R121 10 kΩ ↑** | Follows supervisors and JP101 | Low until both rails are good for 12–28 ms | Supervisor VOL ≤ 0.4 V at 1 mA [V S56] |
| **CARD_EN_N** | **R123 10 kΩ ↑** | High | U104 Hi-Z, U107 outputs high | NAND output dominates once powered |
| **DBUF_OE_G_N** | **R124 10 kΩ ↑** | High | U103 isolated | OR output dominates once powered |

## 8. Edge-connector footprint

Unchanged from revision A: 100 pads, 1.524 × 5.0 mm on 2.54 mm pitch, matching MNT VA2000 (S12). **TBV before layout (C-08):** orientation, finger length and bevel.

## 9. Open electrical and timing concerns (gate G-SHEET1)

| ID | Concern | Severity | Status / resolution |
|---|---|---|---|
| **C-01** ⚠ | FPGA share of the /SLAVEn, XRDY and buffer paths | High | **Exploratory STA passes** (Diamond 3.14, −4, commercial 85 °C and industrial 100 °C, 15 pF): worst 15.31 ns against 18 ns; /AS → /SLAVEn 8.91 ns; /SLAVEn total 20.7 of 35 ns (corrected run) ([sheet1-sta-results.md](sheet1-sta-results.md)). **Open until rerun at the sheet-2 pinout** (G-STA) and M-1/M-2 |
| **C-02** ⚠ | Late address, skew, transitions near /AS → false /SLAVEn | High | Mitigated by design; structure verified on the Yosys **and Diamond** netlists; E1 0/800; formal F4/F12 proven. STA setup requirement **16.4 ns** conservative (8.9–9.8 ns same corner). **Open until M-7** (pass ≥ 19.4 ns) |
| **C-03** ⚠ | Unpowered or non-operational carrier: /SLAVEn and /CFGOUTn | **High** (owner) | **Resolved by design in rev B** (§6). tb_chain S1–S10 and tb_z2 T0/T14–T18 **pass**. Open: M-8, M-9 on hardware |
| C-04 | U104 behaviour at start-up | **Medium** (owner) | **Resolved by design:** OE-gated LVC8T245; /SLAVEn budget recalculated, 29.8 ns. Verify M-6, M-9 |
| **C-05** ⚠ | No numeric DOE timing; buffer enable and direction safety | Medium | Design: XRDY-gated; enable qualified by DOE, strobes, READ, /BERR, registered DIR and guards. Assertions C1/C2/DIR monitor **pass**; formal F1/F2/F5/F8/F9 **proven**; mutations M1/M2 caught. M-3 open |
| C-06 | U103 bus-hold load on D0–D15 | Low | Unchanged |
| C-07 | 22 Ω values are placeholders | Low | Unchanged |
| C-08 | Edge-connector mechanics | Medium | Unchanged |
| C-09 | Manufacturer ID $07DB TBV | Low | Unchanged (R-18) |
| C-10 | A blank FPGA blocks downstream AutoConfig | – | **Closed by the rev B design:** a blank FPGA leaves the card transparent. Verification as C-03 |
| C-11 | Z3 machines untested | Low | Unchanged |
| C-12 | Temporary PWR_FLAGs on sheet 1 | Low | Unchanged |
| **C-13** ⚠ | RMW cycles: /AS held across read and write | Medium | **Resolved in the HDL by design and verified in simulation** (tb_z2 T4/T5/T7/T10 pass; mutation M1 caught). M-10 on hardware |
| C-14 | FPGA I/O budget at 110 of 111 after rev B | Medium | At sheet 2, do not route ZF_OVR_N / ZF_DTACK_N to the FPGA, giving 108 of 111 ([../pin-assignment-matrix.md](../pin-assignment-matrix.md) §4) |
| C-15 | Backplane terminations verified only for A2000 Rev 6 | Medium | M-8 per target machine |
| C-16 | Verification not executed | – | **Closed 2026-11-18:** `hdl/run_checks.sh` → ALL HDL CHECKS PASSED ([../hdl/verification-results.md](../hdl/verification-results.md)). STA remains under C-01 / G-STA |

⚠ = unresolved electrical or bus-timing issue under brief §10. **No timing claim is made.** Zero-wait operation stays disabled (ER-2). The schematic is **not** approved for manufacture.

## 10. Measurements for bring-up (after gate G-PSU)

| ID | Measurement | Points | Pass criterion |
|---|---|---|---|
| M-1 | /AS↓→/SLAVEn↓ and /AS↑→/SLAVEn↑ at the edge, for reads and writes | TP101, TP102 | ≤ 35 / ≤ 50 ns, margin recorded |
| M-2 | Per-stage delays | TP101 → TP114 → TP115 → TP102 | Consistent with the timing budget |
| M-3 | DOE relative to /AS, the strobes and E7M; XRDY release relative to DOE | TP103, TP104, TP101, TP111 | Recorded; drive never precedes DOE |
| M-4 | No /BERR during AutoConfig or register access | TP113, BERR_EVENTS register | Never asserted |
| M-5 | XRDY negation in XRDY-gated mode | TP111, TP101 | ≤ 60 ns; released for non-selected cycles |
| M-6 | Power-up/down, unprogrammed FPGA | TP102, TP109, TP110, TP111, TP118 | No assertion of /SLAVEn, /INTx, XRDY; /CFGOUTn passes |
| M-7 | Address setup to /AS at the slot (A16–A23) | J101 | **≥ 19.3 ns** since sheet 2 rev A1 (was 19.4 ns with Diamond-placed pins). Measured minimum minus instrument uncertainty, against the envelope of every analysed placement (S_req 16.239 + 3, rounded up), re-derived for the bitstream under test ([sheet2-sta-results.md](sheet2-sta-results.md) §4). 13.0–19.3 ns only on the same-corner basis, recorded as such |
| **M-8** | Backplane terminations, A2000 off, no cards: each slot's /CFGOUTn to GND and /SLAVEn to +5 V | J101 sockets | ≈ 1 kΩ each (RP607 / RP800) |
| **M-9** | Power-on: +3V3, +5V_BUS, EN_OK, CARD_EN_N against /BUSRST | TP119, TP118, TP112 | CARD_EN_N falls only while /BUSRST is asserted; record the EN_OK delay and the A2000 reset length |
| **M-10** | TAS on SCRATCH0 from the Amiga; logic analyser on /AS, /UDS//LDS, READ, DOE, XRDY, ZF_DBUF_OE_N, ZF_DBUF_DIR | TPs + FPGA debug header | B-port enable ends before READ falls; RMW_CYCLES increments; result correct |

## 11. Revision history

| Rev | Date | Change |
|---|---|---|
| A | 2026-11-18 | First drawing of sheet 1 (Stage 2) |
| B | 2026-11-18 | Owner review (C-03 → High, C-04 → Medium, new C-13). U104 → SN74LVC8T245 with /OE = CARD_EN_N. New U106, U107, U108, U109, JP101, R121–R126, C118–C122, TP118–TP119. /BERR buffered instead of CDAC. New concerns C-14 to C-16; C-10 closed by design |
