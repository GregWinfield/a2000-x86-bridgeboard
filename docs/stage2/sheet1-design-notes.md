# Sheet 1: Zorro II interface and AutoConfig signal buffering (design notes)

**Status:** Stage 2 draft, revision A, 2026-11-18. **Not electrically or mechanically validated.** ERC-clean apart from the expected interface items ([sheet1-erc-report.md](sheet1-erc-report.md)) and netlist-audited (353 checks); neither proves the design works.

**Files:**
- Schematic: [hardware/kicad/sheets/01_zorro_interface.kicad_sch](../../hardware/kicad/sheets/01_zorro_interface.kicad_sch) (project `hardware/kicad/a2000-bridgeboard.kicad_pro`, KiCad 10.0.8).
- PDF: [sheet1-schematic.pdf](sheet1-schematic.pdf).
- HDL interface: [../hdl/zorro-interface-spec.md](../hdl/zorro-interface-spec.md).

Evidence tags follow [../sources.md](../sources.md). New datasheet sources are S45–S50 (§2).

## 1. What this sheet does

The sheet converts the 5 V Zorro II slot interface into 3.3 V signals for the FPGA (sheet 2) and the local data bus (sheets 2 and 3), with power-off isolation in both directions. AutoConfig itself is FPGA logic; this sheet carries every AutoConfig signal (/CFGINn, /CFGOUTn, /BUSRST, A1–A23, D15–D12) and fixes their default states. No power is taken from the Zorro +5 V, +12 V, −5 V or −12 V pins. All 18 Zorro ground pins (including pin 91) are connected to the ground plane.

| Ref | Part | Function |
|---|---|---|
| J101 | Zorro II card edge (project footprint `Zorro2_Edge_2x50_P2.54mm`) | 100 contacts; unit A = pins 1–50, unit B = pins 51–100 |
| U101, U102 | TI SN74LVC16244ADGGR | Zorro → FPGA input buffers: A1–A23, /AS, /UDS, /LDS, READ, DOE, E7M, /CFGINn, /BUSRST, CDAC (32 channels, all used) |
| U103 | TI SN74LVCH16T245DGGR | D0–D15 transceiver. B port = Zorro (VCCB = +5V_BUS), A port = local bus LD0–LD15 (VCCA = +3V3). Bus-hold on both ports |
| RN101–RN104 | 4 × 22 Ω arrays (0603×4 convex) | Series damping on D0–D15 (value TBV, C-07) |
| U104 | TI SN74LVC2T45DCTR | /SLAVEn and /CFGOUTn drivers, full 5 V levels, DIR tied for A→B |
| R117, R118 | 22 Ω | Series damping on /SLAVEn and /CFGOUTn |
| U105 | TI SN74LVC07APWR | Open-drain /INT2, /INT6, XRDY. Channels 4/5 for /OVR and /DTACK go via DNP links R119/R120. Channel 6 unused (input tied high) |
| R101–R108 | 2.2 kΩ pull-ups to +3V3 | Safe start-up defaults on every FPGA-driven Zorro control (§6) |
| R109 | 10 kΩ pull-down | U103 DIR default = Zorro→local |
| C101–C117 | 15 × 100 nF + 2 × 10 µF | One 100 nF per supply pin; bulk per rail |
| TP101–TP117 | Test pads | 13 bus-side, 2 FPGA-side and 2 GND; for timing measurements |

## 2. Part verification (pinouts transcribed from the manufacturer documents)

Every IC symbol pin number was entered from the document below. The netlist audit then checked every connected pin against the same tables (`tools/kicad/audit_sheet1.py`, 353 checks, 0 failures).

| ID | Document | Facts used |
|---|---|---|
| S45 | TI **SN74LVC16244A**, SCAS699C (rev. June 2014) | DGG pinout (all 48 pins). tpd A→Y **≤ 4.1 ns** at VCC 3.3 V ±0.3 V, −40 to 85 °C. Inputs 5.5 V-tolerant at any valid VCC. Ioff partial-power-down |
| S46 | TI **SN74LVCH16T245**, SCES635B (rev. Apr 2015); pinout identical to SN74LVC16T245 SCES636B (checked by diff) | DGG pinout. Function table: OE=L/DIR=L B→A, OE=L/DIR=H A→B, OE=H isolation. DIR/OE referenced to VCCA. **VCC isolation:** either VCC at GND puts all outputs in Hi-Z. Ioff. Bus-hold: "use of pullup or pulldown resistors… not recommended"; overdrive **IBHLO 900 µA at 5.5 V** (rendered table). At VCCA 3.3 V, VCCB 5 V: A→B ≤ 4.4 ns, B→A ≤ 6.0 ns, OE→B enable ≤ 6.4 ns, OE→B disable ≤ 6.3 ns. B port VOH ≥ 3.8 V at −32 mA, VOL ≤ 0.55 V at 32 mA (4.5 V). TI recommends a pull-up on OE for Hi-Z during power-up |
| S47 | TI **SN74LVC2T45**, SCES516N (rev. June 2024) | DCT/DCU pinout: 1 VCCA, 2 A1, 3 A2, 4 GND, 5 DIR, 6 B2, 7 B1, 8 VCCB. DIR=H: A→B. VCC isolation, Ioff. At VCCA 3.3 V, VCCB 5 V: **tPLH ≤ 4.4 ns, tPHL ≤ 4.0 ns** (A→B). No OE pin |
| S48 | TI **SN74LVC07A**, SCAS595W (rev. Oct 2016) | PW pinout (14 pins). Open-drain outputs; inputs and outputs accept up to 5.5 V. Ioff. tpd ≤ 3.6 ns at 3.3 V ±0.3 V |
| S49 | Lattice **MachXO2 Family Data Sheet FPGA-DS-02056-4.7** | Before and during configuration, I/O are tri-stated with a **weak pull-down** (IPD **30–305 µA**). tREFRESH (POR to I/O active) **1.4 ms** for the MachXO2-2000 (2.4 ms for the 4000). tPD best-case pin-LUT-pin **7.24 ns (−4)** at LVCMOS25 8 mA, 0 pF (Table 3.27, note 2). PLL fIN ≥ 7 MHz. TQFP-144 = **111 GPIO** (Table 4.4) |
| S50 | Commodore Zorro III spec, App. K (S10) | /SLAVEn ≤ 35 ns / ≤ 50 ns; XRDY ≤ 60 ns; automatic DTACK; DOE; /BUSRST resets AutoConfig; open-collector list |

Footprints are from KiCad 10.0.8's standard libraries, except the edge connector:

| Part | Footprint | Note |
|---|---|---|
| U101–U103 | `Package_SO:TSSOP-48_6.1x12.5mm_P0.5mm` | TI DGG |
| U104 | `Package_SO:SSOP-8_2.95x2.8mm_P0.65mm` | Intended for TI DCT (SM8). **Land pattern TBV against the TI DCT drawing before layout** |
| U105 | `Package_SO:TSSOP-14_4.4x5mm_P0.65mm` | TI PW |
| RN101–RN104 | `Resistor_SMD:R_Array_Convex_4x0603` | |
| Passives | 0603 / 0805 | |
| J101 | Project footprint (§7) | Geometry matches MNT VA2000 (S12) |

## 3. Signal paths

- **Zorro inputs (31 + CDAC).** Each Zorro pin goes directly to an LVC16244A input. Its output drives one FPGA input (`ZB_*` hierarchical labels). The ~OE pins are tied low: the inputs are always enabled and the outputs only drive FPGA inputs, so there is no contention case. /AS, /UDS, /LDS, READ, DOE and E7M share U102 (tsk(o) applies within one device).
- **Data.** Zorro D0–D15 → RN (22 Ω) → U103 B port, then U103 A port → `LD0–LD15` (sheet 2 now; SRAM on sheet 3 later). Direction and enable come from the FPGA (`ZF_DBUF_DIR`, `ZF_DBUF_OE_N`, byte halves tied).
- **Push-pull outputs.** `ZF_SLAVE_N` and `ZF_CFGOUT_N` → U104 → 22 Ω → J101 pins 9 and 11, at 5 V CMOS levels.
- **Open-drain outputs.** `ZF_INT2_N`, `ZF_INT6_N` and `ZF_XRDY` → U105 → J101 pins 19, 22, 18. The FPGA drives the U105 input **low** to pull the Zorro line low. `ZF_OVR_N` and `ZF_DTACK_N` exist but their outputs reach J101 only if R119/R120 (DNP) are fitted.
- **Clocks.** E7M is buffered (ZB_E7M) as a timing reference. Rev 1 does **not** lock a PLL to E7M (R-29: MachXO2 PLL input ≥ 7 MHz against 7.09 MHz PAL).

## 4. Timing budgets (ER-1, ER-2)

### 4.1 /SLAVEn assertion: /AS↓ at J101-74 → /SLAVEn↓ at J101-9 (limit 35 ns)

| # | Stage | Parameter | Max | Source |
|---|---|---|---|---|
| 1 | J101 → U102 trace | ~30 mm | 0.3 ns | [E] |
| 2 | U102 (LVC16244A) | tpd, 3.3 V ±0.3 V, CL 50 pF | **4.1 ns** | [V S45] |
| 3 | U102 → FPGA trace | | 0.5 ns | [E] |
| 4 | FPGA: /AS AND (address-match ∧ configured) → pin | Datasheet floor: tPD one LUT-4, best-case routing | 7.24 ns | [V S49] |
| | | **Design allocation** (LVCMOS33 I/O, real routing, ~10 pF load, decode depth if the address is still settling, C-02) | **18 ns**, to be proven by Diamond STA (gate G-STA) | [A] |
| 5 | FPGA → U104 trace | | 0.5 ns | [E] |
| 6 | U104 (LVC2T45) A→B | tPHL, VCCA 3.3 V, VCCB 5 V | **4.0 ns** | [V S47] |
| 7 | R117 22 Ω + trace + slot load (~30 pF assumed) | RC ≈ 0.7 ns, edge to TTL threshold | 2.0 ns | [E] |
| | **Total with the 18 ns FPGA allocation** | | **29.4 ns → 5.6 ns margin** | [D] |
| | Total with the datasheet floor | | 18.6 ns → 16.4 ns margin | [D] |

**Negation** (/AS↑ → /SLAVEn↑, limit 50 ns) uses the same path with U104 tPLH 4.4 ns: 29.8 ns allocated, 20.2 ns margin.

**Conclusion.** The buffer stages consume only 8.1 ns of the 35 ns, verified from the datasheets. Everything else depends on the FPGA stage, which this review cannot close without place-and-route timing. That is why gate **G-STA** exists. If the −4 grade misses 18 ns at the chosen pins, the fallbacks are:
1. Pin swapping for shorter routes.
2. A −5 or −6 speed grade (same footprint).
3. LCMXO2-4000HC.

### 4.2 XRDY negation: /AS↓ → XRDY↓ at J101-18 (limit 60 ns), ER-2

U102 4.1 + FPGA ≤ 18 + U105 3.6 [V S48] + traces 1.3 + fall time ≈ 2 [E] gives **≈ 29 ns, about 31 ns margin.** XRDY is released (driver off) for every cycle not addressed to this card. Its rise time depends on the A2000 backplane pull-up, which is unknown; a slow rise only adds latency.

### 4.3 Data-bus release: /AS↑ → U103 B port Hi-Z

U102 4.1 + FPGA ≤ 18 + U103 OE→B disable 6.3 [V S46] + traces 1 gives **≈ 29.4 ns**. No explicit Zorro II limit was found. The design target is the /SLAVEn negation limit (50 ns), C-05.

### 4.4 Read and write data (informational; zero-wait is **not** assumed, ER-2)

- **Register/AutoConfig read.** Path: /AS synchronised (≤ 2 × 20 ns at 50 MHz), then one clock to select data, FPGA tCO, then U103 A→B (≤ 4.4 ns) after OE-enable (≤ 6.4 ns, gated by DOE). That is about 80 ns plus any DOE dependency, against the ≈ 260 ns derived read budget (review §4.2, TBV).
- **Write.** Data is valid from /UDS//LDS↓. U103 B→A ≤ 6.0 ns, and the FPGA samples two clocks after the synchronised strobe.
- **HDL default.** XRDY-gated mode: the card always inserts wait states until the data is ready. Zero-wait mode is enabled only after gate **G-ZEROWAIT**.

## 5. Power-off isolation and back-feed (ER-3)

| State | U101/U102 (LVC16244A) | U103 (LVCH16T245) | U104 (LVC2T45) | U105 (LVC07A) | Zorro-side effect |
|---|---|---|---|---|---|
| Amiga on; carrier unpowered (Molex unplugged or blown fuse) | VCC 0: Ioff, outputs off; inputs 5.5 V-tolerant, so no current from Zorro | Both VCC 0: VCC isolation, all outputs Hi-Z; Ioff | VCC isolation: Hi-Z | Ioff: outputs off | No back-feed into the carrier. /INT2, /INT6, XRDY released. **/SLAVEn and /CFGOUTn float** (C-03) |
| +5V_BUS present, +3V3 absent (regulator fault) | Unpowered: Ioff | VCCA 0 → all outputs Hi-Z | VCCA 0 → Hi-Z | Unpowered: Ioff | Card invisible; /SLAVEn and /CFGOUTn float (C-03) |
| +3V3 present, +5V_BUS absent | Normal | VCCB 0 → Hi-Z | VCCB 0 → Hi-Z | Normal, but its inputs are held inactive by R103–R107 unless the FPGA drives them | Data path and /SLAVEn disabled (fail-safe) |
| Supplies ramping (power-up) | Outputs undefined below VCC(min); they only drive FPGA inputs | OE pulled to VCCA by R108 (TI recommendation) → isolated | **No OE pin**: below 1.65 V the output state is unspecified. A inputs track +3V3 through R101/R102 | Inputs pulled up → outputs off | A2000 is in reset during the PSU ramp [A], so no bus cycles are affected (C-04; verify by scope) |
| Amiga off | – | – | – | – | Same PSU: everything is off together |

**Back-feed paths ruled out:**
- *Zorro signal → carrier rail.* Every part touching a Zorro pin has Ioff or VCC isolation, and no input on the 5 V side has a clamp diode to a 3.3 V rail.
- *Carrier → Zorro power pins.* Those pins are not connected at all.
- *Carrier rails → Zorro lines through pull resistors.* There are no carrier pull resistors on Zorro lines; the default-state resistors sit on the 3.3 V FPGA side only.

The bus-hold on U103's B port stays active on the powered side. With the carrier unpowered it is not powered, and its Ioff applies.

## 6. Safe FPGA start-up behaviour (ER-3)

Before and during configuration, MachXO2 I/O are tri-stated with a weak pull-**down** (IPD 30–305 µA) [V S49]. Configuration completes about 1.4 ms after POR. If the FPGA is blank or being programmed, the pull-downs persist. The board's default states therefore come only from external resistors, and every one is chosen so that the Zorro bus sees an **inactive, non-driving card**:

| Net | Resistor | Default | Zorro result | Check against IPD 305 µA |
|---|---|---|---|---|
| ZF_SLAVE_N | R101 2.2 kΩ ↑ | High | /SLAVEn negated (driven high) | 3.0 V − 0.67 V = **2.33 V > VIH 2.0 V** |
| ZF_CFGOUT_N | R102 2.2 kΩ ↑ | High | /CFGOUTn negated (chain waits; correct while unconfigured) | 2.33 V |
| ZF_INT2_N, ZF_INT6_N | R103, R104 ↑ | High | Interrupts released | 2.33 V |
| ZF_XRDY | R105 ↑ | High | XRDY released (no wait states forced) | 2.33 V |
| ZF_OVR_N, ZF_DTACK_N | R106, R107 ↑ | High | Released (and DNP-isolated) | 2.33 V |
| ZF_DBUF_OE_N | R108 ↑ | High | Transceiver isolated | 2.33 V |
| ZF_DBUF_DIR | R109 10 kΩ ↓ | Low | B→A only (never drives Zorro) | FPGA pull-down assists |

Worst case uses VCC = 3.0 V (−10 %) and VIH = 2.0 V for LVC at 3.3 V [K]. In user mode the FPGA drives these pins actively; a pull-up costs ≤ 1.5 mA while its pin is driven low.

**Consequence.** A blank or unconfigured FPGA leaves /CFGOUTn negated, so boards in later slots are not AutoConfigured (C-10). Instant-on configuration (1.4 ms) keeps this window far shorter than Kickstart's AutoConfig scan [A, TBV by M-6].

## 7. Edge-connector footprint

`Zorro2_Edge_2x50_P2.54mm`:
- **Pads:** 100 `connect` pads, 1.524 × 5.0 mm on 2.54 mm pitch.
- **Sides:** even pins on F.Cu, odd pins on B.Cu. Pins 1/2 at the +X end, 99/100 at the −X end.
- **Origin:** the card edge, with the pads 0.04 mm inside it.
- **Basis:** matches the MNT VA2000 footprint (MIT, S12), which is proven in A2000s.

**TBV before layout (C-08):**
- orientation of the pin-1 end relative to the bracket;
- finger length and insertion depth against the A2000 slot;
- edge bevel and hard-gold plating specification.

## 8. Open electrical and timing concerns (review before sheet 3, gate G-SHEET1)

| ID | Concern | Severity | Proposed resolution |
|---|---|---|---|
| **C-01** ⚠ | The FPGA share of the /SLAVEn path (≤ 18 ns allocated) is unproven. It is also the core of the XRDY and DBUF_OE paths | High | Diamond STA with MAXDELAY constraints (HDL spec §6) before the pinout freeze (G-STA); then measure M-1/M-2 |
| **C-02** ⚠ | Address-to-/AS setup at the slot is unknown. If A16–A23 settle after /AS↓, the combinational match can add delay and could **glitch /SLAVEn** low on a non-selected cycle, risking a collision /BERR | High | Measure M-7 on the target A2000. HDL keeps the match term address-only, gated by /AS. If the setup is < ~10 ns, revisit (e.g. a faster grade, or a registered match with a qualified hold) |
| **C-03** ⚠ | With the carrier unpowered, /SLAVEn and /CFGOUTn float. The outcome depends on A2000 backplane pull-ups (unknown): possible false collision, or a stalled AutoConfig chain | Medium | Operating rule: never run the A2000 with the card fitted and its Molex disconnected. Measure the backplane pull-ups. A pull-up from the Zorro +5 V pin would breach the brief's no-Zorro-power rule, so none is added |
| C-04 | U104 has no OE, so outputs are unspecified during the supply ramp | Low | A2000 is in reset during the ramp [A]; verify M-6 |
| **C-05** ⚠ | No numeric DOE timing in the sources; data-out is gated combinationally by DOE | Medium | Measure DOE against /AS and E7M (M-3) before enabling zero-wait |
| C-06 | U103 bus-hold loads D0–D15 (≤ 900 µA overdrive) | Low | Expected to be fine with TTL-class bus drivers [K]; confirm the A2000 data-bus driver family (TBV) |
| C-07 | 22 Ω series values (D0–D15, /SLAVEn, /CFGOUTn) are placeholders | Low | SI measurement or simulation on the backplane; adjust 0–47 Ω |
| C-08 | Edge-connector orientation, finger length and bevel (§7) | Medium | Mechanical check (Stage 6) |
| C-09 | AutoConfig manufacturer ID 2011 ($07DB) is TBV | Low | R-18 |
| C-10 | A blank or unconfigured FPGA blocks downstream AutoConfig | Medium | Program FPGAs before installation. DIP "disable" (HDL pass-through) needs a programmed FPGA |
| C-11 | Z3 machines (A3000/A4000) are untested; pin 91 tied to GND as on a Zorro II card | Low | Out of scope for Rev 1 |
| C-12 | Temporary PWR_FLAGs on +3V3/+5V_BUS (sheet 1) must be removed when sheet 5 exists | Low | Checklist item for sheet 5 |

⚠ = flagged as an unresolved electrical or bus-timing issue under brief §10. None of these blocks drawing sheets 2 and 3. **C-01, C-02 and C-05 must be resolved before zero-wait operation is enabled or any timing claim is made.**

## 9. Measurements for bring-up (sheet-1 scope)

| ID | Measurement | Points | Pass criterion |
|---|---|---|---|
| M-1 | /AS↓→/SLAVEn↓ and /AS↑→/SLAVEn↑ at the edge, for reads and writes | TP101, TP102 | ≤ 35 ns / ≤ 50 ns, with the margin recorded |
| M-2 | Per-stage delays | TP101 → TP114 (ZB_AS_N) → TP115 (ZF_SLAVE_N) → TP102 | Consistent with §4.1 |
| M-3 | DOE timing relative to /AS and E7M | TP103, TP104, TP101 | Recorded; data-out enable never precedes DOE |
| M-4 | No /BERR during AutoConfig or register access | TP113 | Never asserted |
| M-5 | XRDY negation in XRDY-gated mode | TP111, TP101 | ≤ 60 ns after /AS; released for non-selected cycles |
| M-6 | Power-up/down and an unprogrammed FPGA | TP102, TP109, TP110, TP111 | No assertion of /SLAVEn, /INTx or XRDY |
| M-7 | Address setup to /AS at the slot (A16–A23 against /AS) | J101 pins / probe | Recorded; ≥ 10 ns wanted (C-02) |

Gate **G-PSU** (ER-5) applies before any of these is done in a real A2000.
