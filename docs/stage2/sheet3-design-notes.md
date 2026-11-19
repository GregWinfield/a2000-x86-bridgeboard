# Sheet 3: shared SRAM and memory arbitration, design notes (revision A)

**Status:** revision A1, 2026-11-19. Incorporates the owner's review of revision A (§13): C-17 decided, C-21 approved, canonical byte order defined. **G-SHEET3 is approved for design progression** once these are incorporated and verified (done; §13), which does not authorise PCB manufacture. **Not validated:** the hardware gates (G-STA final, G-PSU, measurements M-1 to M-13) are open.

**Gate.** G-SHEET1 was approved by the owner on 2026-11-19 "for design progression, pending final hardware verification". That approval started this sheet. Its five open requirements are carried in §11 and in the risk register.

**Contents of this revision:**
- schematic: [../../hardware/kicad/sheets/03_sram.kicad_sch](../../hardware/kicad/sheets/03_sram.kicad_sch) and [sheet3-schematic.pdf](sheet3-schematic.pdf);
- ERC: [sheet3-erc-report.md](sheet3-erc-report.md);
- timing: [sheet3-timing-budget.md](sheet3-timing-budget.md);
- HDL specification: [../hdl/shared-memory-spec.md](../hdl/shared-memory-spec.md);
- RTL, testbenches and formal proofs under `hdl/` (all passing);
- the FPGA pin reassessment (§8).

## 1. The owner's sheet-3 priorities

| Priority (owner, 2026-11-19) | Answer | Evidence |
|---|---|---|
| Low-cost 512 KB conventional SRAM | One IS61WV25616EDBLL-10TLI (D-04, retained): 256K × 16, matching the 16-bit local bus with byte lanes; JEDEC TSOP-II-44 pinout shared by second sources (§2) | ISSI datasheet [V S61]; BOM item 2 |
| Correct arbitration between Zorro II and the RP2040 SPI interface | `z2_lbus`. Zorro priority from the clock /AS is synchronised; host (SPI-side) accesses only when the Zorro side leaves the bus free; never aborted; at most one LD driver, with idle clocks between drivers | Formal X1–X3, X6; tb_z2 with continuous host traffic (4 seeds, 0 failures); tb_shm |
| Deterministic Zorro memory access timing | Reservation floor ZRES: no Zorro local-bus action before START + 4 clocks. Any host access already in flight has then finished, so host traffic cannot move a Zorro cycle by even one clock | **Formal X4** (proof for any inputs); tb_shm S3: action at exactly START + 6 (reads) and DS + 1 (writes), host traffic off and on |
| Safe handling of simultaneous access requests | Fixed priority, decided in one clock on synchronised signals. A host access never starts during a Zorro reservation. The whole /AS is reserved, so RMW (TAS) is atomic | X1, X4, A5/A6 in the HDL spec; tb_shm S4 (TAS with the host hammering the same word) |
| Defined mailbox ownership and synchronisation | Two single-producer, single-consumer queues. Every index register has one writer side; index writes carry the epoch and are range-checked; link reset by either side or /BUSRST; level interrupts derived from queue state | Formal M1–M5; tb_shm S5/S6 |
| RP2040 firmware never responds to individual Zorro cycles | Every Zorro cycle (SRAM or register) completes in FPGA hardware. The host side only reads and writes memory and registers on its own schedule, and its absence, reset or hang cannot stall a Zorro cycle | Host-port contract H-6; tb_z2 runs with the host idle and busy |
| Reassess FPGA pin availability before finalising the SRAM interface | Done (§8). The SRAM interface keeps 23 pins plus the shared LD bus. The overall budget was 3 pins short (JTAG pins are part of the 111 I/O). **Owner decision C-17: 102 signals**, verified with the Lattice package pinout and a Diamond fit (§8.1) | Lattice pinout file [V S63]; datasheet Table 4.4 [V S49]; Diamond pad/map reports [V S62]; fit test |

**Added principle (owner, 2026-11-19).** "SRAM arbitration should be controlling who may access memory. The queues and interrupts control who has work to do." This is implemented as two separate blocks with no shared responsibility ([shared-memory-spec.md](../hdl/shared-memory-spec.md) §1):
- the arbiter has no queue knowledge;
- the queue block never touches the SRAM.

## 2. Parts

| Ref | Part | Key data [V S61] | Notes |
|---|---|---|---|
| U301 | ISSI IS61WV25616EDBLL-10TLI | 256K × 16 asynchronous SRAM, VDD 2.4–3.6 V (−10), tAA 10 ns, VIH 2.0 V / VIL 0.8 V, ICC ≤ 35 mA (industrial, f max), ISB2 ≤ 6 mA, CIN 6 pF / CI/O 8 pF, data retention ≥ 2.0 V | Per-byte ECC inside the device (1-bit correct per byte), transparent to us. Byte writes through /UB and /LB need no read-modify-write. Industrial −40 to +85 °C |
| R301, R302 | 2.2 kΩ 1 % 0603 | Pull-ups on SRAM_CE_N and SRAM_WE_N | §3 |
| C301, C302 / C303 | 100 nF X7R 0603 / 10 µF X5R 0805 | One per VDD pin (11, 33) / bulk | – |
| TP301–TP306 | Test pads | /CE, /OE, /WE, SA0, LD0, GND | Measurement M-11 |

**Footprint.** KiCad `Package_SO:TSOP-II-44_10.16x18.41mm_P0.8mm`, checked against the ISSI outline (44L 400 mil TSOP-II, rev F):
- body E1 10.16 mm and length D 18.41 mm nominal, pitch 0.80 mm;
- lead span E 11.56–11.96 mm, foot L 0.40–0.69 mm;
- KiCad pads 1.525 × 0.55 mm at ±5.59 mm cover the foot with about 0.4 mm toe and 0.3 mm heel.

**Low cost and second sources.**
- Price: the Stage 1 snapshot is USD 2.65 (LCSC) to 6.17 (Farnell) [Vs S24]. 512 KB costs about the same as 128 KB. True dual-port RAM was rejected at about AUD 231 (S25).
- Footprint compatibility: the 256K × 16 TSOP-II-44 pinout is a JEDEC standard, so pin-compatible parts from other vendors fit the same footprint.
- Not yet checked: each candidate's datasheet (pinout, −10 timing, VDD range) must be verified before it is listed as an alternate. BOM note; concern C-20.

## 3. Circuit and safe states

U301 sits on LD[15:0] with U103's A port (sheet 1) and the FPGA (sheet 2). SA[17:0] and the five control lines come from FPGA flip-flops (sheet 2).

| State | U301 | LD bus | Why |
|---|---|---|---|
| Carrier unpowered | Unpowered; contents lost | Every device on LD is on +3V3 and unpowered; U103 isolates the Zorro side (VCC isolation, Ioff) [V S46] | No backfeed path: U301 has no other supply |
| FPGA blank, configuring or reloading (JTAG) | /CE held high by R301 and /WE by R302 → deselected, outputs Hi-Z, no write. Contents kept | Not driven by U301; U103 disabled (ZF_ARM pulled low, so CARD_EN_N is high) | MachXO2 I/O are Hi-Z with a weak pull-down (30–305 µA) [V S49]: node ≥ 3.0 V − 2.2 kΩ × 305 µA = 2.33 V > VIH 2.0 V. In simulation, /CE and /WE reach "deselected" before any other pin can drift (card model) |
| Running, Zorro cycle to the card | Zorro access per §5 | One driver at a time | Formal X2/X3 |
| Running, host access | Host access between Zorro cycles | One driver at a time | X1/X2 |
| Amiga reset (/BUSRST) | Host access continues; contents kept (G7) | – | tb_shm S7 |
| FPGA reconfigured while a host write is in flight | That one word may be lost or undefined; others kept | No contention | tb_shm S9; host rule H-5 (quiesce first) |

**Pull-up choice.** Only /CE and /WE get resistors.
- /CE alone is enough to deselect U301.
- /WE is the second, independent guard, because SRAM contents must survive an FPGA reload: a failed R301 alone must not allow writes.
- /OE, /UB and /LB need none.
- When driven low by the FPGA, each pull-up draws 1.5 mA, well within the 8 mA drive.

**Layout permutation (noted on the sheet).**
- Address lines may be permuted freely.
- Data lines may be permuted within a byte lane (LD0–7 with I/O0–7, LD8–15 with I/O8–15). Both sides access U301 through the same wiring, so the permutation is invisible to them.

## 4. Local bus and arbitration

Specified in [shared-memory-spec.md](../hdl/shared-memory-spec.md) §3: rules A1–A8, the Zorro SRAM sequence and the host-port contract H-1 to H-6. Summary:
- **Host accesses:** 3 clocks for a read, 4 for a write, never aborted; started only when the Zorro side is not reserving the bus and has been quiet for 2 clocks.
- **Zorro side:** reserves from synchronised /AS. Its local-bus actions wait for the reservation floor, which hides any host access in flight. Measured result: identical Zorro timing with and without host traffic.
- **Host latency (simulation, tb_z2 with continuous traffic):** mean ≈ 185 ns. The maximum is 2.62 µs, when a request waits out a Zorro cycle that the watchdog test holds for 2 µs.
- **Bandwidth.** The SPI side needs at most about one word per 640 ns at 25 MHz SPI, and the USB full-speed link limits the PC side to about 1 MB/s anyway (R-01). The arbiter is not the bottleneck.

## 5. Memory map

[shared-memory-spec.md](../hdl/shared-memory-spec.md) §3.4:
- **Mode A:** registers at $0000–$0FFF, fixed window $1000–$7FFF, banked window $8000–$FFFF (BANK at $0020).
- **Mode B:** linear from $01000.
- **Host:** flat 512 KB.

This implements the Stage 1 outline (architecture review §7.5) unchanged.

## 6. Queues and interrupts

[shared-memory-spec.md](../hdl/shared-memory-spec.md) §4: rules Q-1 to Q-7 and the register map (board window $0040–$005A). The design answers "defined ownership and synchronisation" in four parts:
1. **Who may write what:** one writer side per register, enforced in hardware.
2. **Who owns a slot:** the consumer owns [CONS, PROD); the producer owns the rest.
3. **When data are visible:** the producer writes the payload before PROD; both sides execute in order.
4. **What happens at a reset:** a link reset flushes both queues and bumps the epoch, and epoch-tagged writes make a stale update impossible to accept.

Interrupts are levels from queue state, so they cannot be lost.

## 7. Timing

[sheet3-timing-budget.md](sheet3-timing-budget.md). Every SRAM AC limit is met in both Zorro and host accesses.
- **Margins:** most are tens of ns; the tightest is tPWE1 at ≥ 4.7 ns, under a deliberately pessimistic skew assumption.
- **Zorro read data** reach the slot ≥ 14.5 ns before XRDY can be released.
- **FPGA STA at Stage 3 size:** 0 setup and 0 hold errors at both grades; SRAM clock-to-out 2.74–10.09 ns; the sheet-1 /SLAVEn paths still meet 18 ns (worst 15.09 ns).

## 8. FPGA pin availability (reassessment)

**Correction to the pin matrix (revision A of this sheet).**
- **What revision C said:** 110 of 111 I/O, with "JTAG uses dedicated pins".
- **What the data show:** the four JTAG pins (TMS, TCK, TDI, TDO) are among the 111 general-purpose I/O of the 144 TQFP (datasheet Table 4.4 [V S49]), and Diamond reserves them while the JTAG port is enabled [V S62].
- **Result:** revision C needed 110 + 4 = 114 pins of 111.

### 8.1 Decision (owner, 2026-11-19) and its verification

**Decision.** Retain the LCMXO2-2000HC for Rev 1, provisionally:
- remove ZF_OVR_N and ZF_DTACK_N from the FPGA;
- reduce the five diagnostic LEDs to two;
- keep PROGRAMN, INITN and DONE as configuration pins, and keep JTAG.

This gives **102 signals**. Use the smaller FPGA only if complete design timing and fitting pass, and retain the LCMXO2-4000HC as the fallback. Do not rely on Diamond's 112-site count until C-19 is resolved.

| Item | Count | Source |
|---|---|---|
| Package I/O pads (Lattice pinout file, TQFP144) | 112: banks 0–5 = 28/28/28/8/10/10 | [V S63] |
| Datasheet general-purpose I/O | **111** (bank 0 = 27) + 1 reserved for configuration | [V S49] Table 4.4 |
| JTAG (TMS, TCK, TDI, TDO), JTAG port enabled | −4 | [V S62] |
| PROGRAMN, INITN, DONE kept (`SYSCONFIG SDM_PORT=PROGRAMN_DONE_INITN`) | −3 | Diamond SYSCONFIG [V S60] |
| **Available** | **104** | |
| **Required** | **102**: 32 Zorro in, 5 Zorro out, 2 transceiver control, 2 card enable, 16 LD, 23 SRAM, 6 host link, 3 X4 power/status, 3 I²C, 2 LEDs, 3 DIP, 1 clock, 4 debug | Pin matrix §4 |
| **Spare** | **2** | |

**C-19 (the reserved pad).**
- **What is known.** The pinout file lists 28 pads in bank 0, while Table 4.4 counts 27 GPIO there; every other bank matches. The reserved pad is therefore one of bank 0's configuration-related pads. The datasheet revision history also says revision 2.0 updated the I/O total "to include JTAGENB".
- **How it is handled.** The documents do not name the pad, so it is handled conservatively: **JTAGENB (pin 120) carries no signal.** It gets the Hardware Checklist's 1 kΩ pull-up ("JTAG mode") [V S64], so JTAG stays available even if a future bitstream disabled the JTAG port.
- **The count.** The budget above uses the datasheet's 111, as directed.

**Placement rules found during verification (for sheet 2).**

| Pin(s) | Rule | Source |
|---|---|---|
| PROGRAMN 119, INITN 110, DONE 109 | Configuration only; 4.7 kΩ pull-ups to VCCIO0 | [V S64] Table 6.1 and figures |
| JTAGENB 120 | Not used (C-19); 1 kΩ pull-up | [V S64] |
| TCK 131 | 4.7 kΩ pull-down; TMS/TDI/TDO have weak internal pull-ups | [V S64] |
| **SN 70** | **Must not be driven low while the device is erased** ("ensure SN and Programn are not driven low"). No externally driven input; an FPGA output (Hi-Z when erased) with a pull-up is acceptable | [V S64] §6 |
| SI 71, SO 45, MCLK/CCLK 44, CSSPIN 40 | Ordinary I/O in user mode, with the slave and master SPI ports disabled. Usable, given that SN stays high when the device is erased | [V S64]; Diamond defaults [V S62] |
| Clock | `clk_core` on a PCLK pin | [V S63] |

**Verification.**
- **Fit test.** The 102-signal fit test (`Z2_TOP=fit_top`) was run with:
  - `SYSCONFIG SDM_PORT=PROGRAMN_DONE_INITN JTAG_PORT=ENABLE`;
  - JTAGENB and SN prohibited, a conservative 103 available sites.

  Results: it places **102 + 4 JTAG of 112** with PROGRAMN/INITN/DONE reported as "Reserved: sysCONFIG"; **0 setup and 0 hold errors**; every port LVCMOS33 with every bank at 3.3 V; worst Zorro path 15.14 ns; 50 MHz slack 3.66 ns.
- **z2_top.** At both grades: 0 errors, worst 14.94 ns.
- **Not yet done.** The **physical pin assignment** (which signal on which pin and bank) is sheet 2's job. Its STA at the real pins is gate G-STA.
- **Fallback.** If that run fails, the fallback is the LCMXO2-4000HC (115 GPIO), after the pin-compatibility check with the TQFP144 migration file [V S63].

### 8.2 Option C-17b: four LEDs on the X4's RP2040 GPIO, one FPGA READY LED (owner request, 2026-11-19)

| Question | Finding | Source |
|---|---|---|
| GPIO availability | The X4's 40-pin header carries RP2040 GP2–GP29. GP0/GP1 go to the N100's UART1 (R314/R315), not to the header. GP23 also has an unfitted 0 Ω (R316, NC) to an N100 GPIO. This design uses GP8–GP11 (SPI1), GP22 (IRQ), GP27 (ATTN) and, optionally, GP2/GP14/GP15/GP26 (JTAG). **Free: GP3–GP7, GP12, GP13, GP16–GP21, GP23–GP25, GP28, GP29.** Proposed LEDs: **GP16–GP19** (header pins 27, 28, 26, 32), contiguous for one firmware mask; ground pins 25, 30 and 34 adjacent. GP20/GP21 stay reserved for a UART | [V S1] sheet 21; pin matrix §3 |
| RP2040 pad behaviour | After reset every GPIO is an input with pull-down (PDE = 1), Schmitt trigger, drive setting 4 mA (2/4/8/12 mA selectable); the sum of sourced currents ≤ IIOVDD_MAX = 50 mA. IOVDD = P3V_RP, switched from the S0-only P3V3_S. RUN follows PLTRST, so the RP2040 is in reset or unpowered whenever the N100 is | [V S65] §2.19, Table 625; [V S1] sheet 21 |
| Electrical connection | The architecture forbids loading the X4's header 3.3 V or backfeeding the X4 (R-27, ER-3). So each LED signal passes an **SN74AVC4T774** like every other header signal (sheet 4): VCCB = X4_3V3_REF (µA only), VCCA = carrier +3V3, all four channels B→A, OE tied active. The A outputs (±12 mA at 3.0–3.6 V) drive the LEDs from the carrier's +3V3 (≈ 2 mA each, 680–750 Ω) | [V S66] SCES693I |
| N100/RP2040 unpowered | P3V3_S at 0 V. The translator's VCC isolation puts both ports Hi-Z, and Ioff blocks backflow into the X4. The LEDs are off: each output Hi-Z, with the LED and resistor to GND | [V S66] |
| RP2040 in reset or BOOTSEL | Its pads are inputs with pull-downs, so the translator inputs read low and the LEDs are off. Add 100 kΩ pull-downs on the B inputs for the case where P3V3_S is up but P3V_RP is switched off (Q32) | [V S65], [V S1] |
| Cost | One more SN74AVC4T774 (USD 0.42–1.65 [Vs S26]), 4 LEDs and 8 resistors: about AUD 2–4 | – |

**Pin budget with C-17b:** 101 FPGA signals, so **3 spare** (instead of 2).

**Trade-off:**
- **Gain:** one more spare FPGA pin, and four LEDs that can show PC-side state the FPGA cannot know (USB link, Windows driver, SPI activity).
- **Cost:** the four LEDs are dark whenever the X4 is off, and they depend on RP2040 firmware.
- **Standalone diagnostics** come from one FPGA LED, READY, which already encodes the whole card state in this revision of the HDL:
  - off: not armed, or FPGA blank;
  - slow blink: armed, waiting for AutoConfig;
  - steady: configured;
  - fast blink: watchdog fault.

**Recommendation.**
- **Adopt C-17b if the extra spare pin is wanted.** The isolation follows the existing sheet-4 scheme and adds no new risk.
- **Sheet 2 can take either choice without re-layout.** It assigns READY and FAULT to FPGA pins; under C-17b the FAULT pin simply becomes the third spare.
- **Owner decision C-26: approved 2026-11-19.** Implemented in sheet 2 revision A1 (pin 67 freed); the RP2040 side follows on sheets 4/6.

## 9. Verification summary

| Check | Result |
|---|---|
| `hdl/run_checks.sh` (lint; tb_z2 4 seeds + 4 corners; tb_z2 with continuous host traffic, 4 seeds; tb_shm 4 seeds + 2 corners; tb_chain; netlist structure; gate-level hazard; formal z2_core and fv_shm) | **ALL HDL CHECKS PASSED** (2026-11-19) |
| Formal fv_shm: X1–X6, M1–M5, F1–F20 | prove PASS, bmc 64 PASS, cover all reached; 7 of 8 mutants caught (the 8th is equivalent) |
| SRAM model AC checks (every access, all runs) | 0 violations |
| Diamond: Stage 3 z2_top, both grades; fit tests | 0 setup / 0 hold errors; pad check pass |
| KiCad: ERC | 147 entries, all expected ([sheet3-erc-report.md](sheet3-erc-report.md)) |
| KiCad: netlist audits | sheet 3: 120 checks, 0 failures; sheet 1: 418, 0 failures |

Defects found during this work are listed in [../hdl/verification-results.md](../hdl/verification-results.md) §5.4: one RTL defect found by k-induction, one simulation-only RTL coding hazard, and several in the verification code.

## 10. Concerns for review

| ID | Concern | Severity | Proposed resolution / status |
|---|---|---|---|
| **C-17** | FPGA I/O budget: rev C needed 114 of 111 pins once JTAG is counted | High | **Decided (owner):** 102 signals, 2 spare; configuration pins and JTAG kept. Verified by the Diamond fit (§8.1); physical assignment and G-STA at sheet 2; LCMXO2-4000HC fallback |
| C-18 | Dual-function configuration pins (PROGRAMN, INITN, DONE, JTAGENB, MCLK, SN, SI, SO, CSSPIN) | Medium | Check configuration-time behaviour against the MachXO2 configuration guide before sheet 2; restrict to tolerant signals |
| C-19 | The datasheet's one "reserved for configuration" pad vs 112 pads in the pinout file | Low | **Bounded:** it is in bank 0. Handled conservatively: JTAGENB carries no signal and the budget uses 111 (§8.1). Ask Lattice to name the pad |
| C-20 | SRAM second source not yet verified | Low | Verify alternates from their datasheets before listing them |
| C-21 | Hardware semaphores from the architecture review §7.4 are not implemented | Low | **Approved (owner):** not required for the two SPSC queues. Multiple producers on the same processor must be serialised in software ([shared-memory-spec.md](../hdl/shared-memory-spec.md) §1) |
| C-22 | Host port waits up to one Zorro cycle (≤ 2.6 µs, watchdog-bounded); the SPI slave is not designed yet | Medium | Sheet 4 must verify the real SPI slave, the clock-domain crossing, host-request buffering and ordering (owner requirement 3; [shared-memory-spec.md](../hdl/shared-memory-spec.md) §6) |
| C-23 | 50 MHz register-path slack 2.7 ns at Stage 3 (START decision path) | Low–Medium | Watch at each sheet; if below 1 ns, pipeline the START decision (one extra clock, still deterministic) |
| C-24 | Zero-wait SRAM cycles: thin margins in the model | Low | Stays disabled until G-ZEROWAIT |
| C-25 | PiStorm/Emu68 and other non-68000 masters: address setup, strobe widths and cycle gaps unknown. The design assumes ≥ 1 clock of /AS negation between cycles for host progress, and slot setup ≥ S_req | Medium | New measurement M-12; risk R-41 (tracked, owner requirement 4) |
| C-26 | Option C-17b: four LEDs moved to RP2040 GPIO through an isolating translator, one FPGA READY LED (§8.2) | Low | **Approved 2026-11-19** (owner). Implemented in sheet 2 revision A1; RP2040 GPIO availability, LED drive current, reset state and power-off behaviour to be verified on sheets 4/6 |
| C-27 | Byte order across a big-endian Amiga and little-endian RP2040/x86 | Medium | **Defined:** [byte-order-spec.md](../hdl/byte-order-spec.md). Shared memory is a byte array, multi-byte values are big-endian, SPI is MSB first. Vectors for BridgeDiag and firmware; hardware lanes checked by tb_shm S12 |

## 11. Open requirements carried from the G-SHEET1 approval

| # | Requirement (owner, 2026-11-19) | Tracked as |
|---|---|---|
| 1 | Final FPGA pin assignment and post-place-and-route STA, including the complete /SLAVEn path | G-STA (open); sheet 2 |
| 2 | MachXO2 package pin budget, I/O bank compatibility and voltage | C-17, C-18, C-19; R-38, R-42. Partial evidence: Diamond fit tests, all banks at 3.3 V |
| 3 | Physical Zorro II bus timing, including stock 68000 and PiStorm/Emu68 where practical | M-1 to M-10, new **M-12**; R-12, R-32, **R-41** |
| 4 | AutoConfig, power-off isolation, XRDY, DOE and RMW on hardware | M-1 to M-10; new **M-11** (SRAM timing) and **M-13** (host traffic during Amiga copy loops) |
| 5 | A2000 PSU capacity before powered installation | G-PSU (open), R-06 |

## 12. Measurements to add (bring-up, after G-PSU)

| ID | What | Where | Pass criterion |
|---|---|---|---|
| M-11 | SRAM access waveforms: tSA, tAW, /WE width, tSD; read data valid before XRDY release | TP301–TP305, Zorro slot | Every limit of [sheet3-timing-budget.md](sheet3-timing-budget.md) §2 met with ≥ 50 % of the computed margin |
| M-12 | Bus cycles from a PiStorm/Emu68 (and any accelerator in use): address setup to /AS, strobe widths, /AS gap between cycles, RMW sequence | Logic analyser at the slot | Setup ≥ M-7 criterion; gap ≥ 1 FPGA clock for host progress; RMW as in S57 or the card's behaviour re-verified |
| M-13 | Host SRAM traffic at full SPI rate during Amiga memory-copy loops to the card | Software test + logic analyser | No data errors; Zorro wait states unchanged with and without host traffic |

## 13. Owner review of revision A (2026-11-19) and how it is incorporated

| Item | Incorporated in | Verified by |
|---|---|---|
| PR #3 approved | Merged by the owner | – |
| C-17: 102 signals, 2000HC provisionally, 4000HC fallback, no reliance on 112 sites | §8.1; pin matrix rev E §4; `z2_top` (no /OVR, /DTACK; two LEDs); LPF SYSCONFIG and PROHIBIT | Diamond fit 102 + 4 JTAG of 112; z2_top both grades; HDL suite |
| C-17b (four LEDs on RP2040 GPIO) investigated | §8.2 | X4 schematic, RP2040 and SN74AVC4T774 datasheets |
| C-21 approved; multiple producers on one processor serialised in software | [shared-memory-spec.md](../hdl/shared-memory-spec.md) §1 | – |
| 1. Canonical byte order | [byte-order-spec.md](../hdl/byte-order-spec.md) | tb_shm S12 |
| 2. Cross-endian test patterns | [../test/cross-endian-vectors.csv](../test/cross-endian-vectors.csv) | tb_shm S12 (V1–V4, V6) |
| 3. Sheet 4 verifies the real SPI slave, CDC, buffering and ordering | [shared-memory-spec.md](../hdl/shared-memory-spec.md) §6 (requirements HL-1 to HL-6) | At sheet 4 |
| 4. 50 MHz margin and PiStorm/Emu68 tracked | R-43 (slack now 3.66–4.76 ns), R-41 and M-12 | Each Diamond run |
| 5. Hardware gates preserved | §11, §12; baseline gate list | – |
