# Sheet 3: shared SRAM and memory arbitration, design notes (revision A)

**Status:** 2026-11-19, ready for review. **Not validated:** the hardware gates (G-STA final, G-PSU, measurements M-1 to M-13) are open.

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
| Reassess FPGA pin availability before finalising the SRAM interface | Done (§8). The SRAM interface keeps 23 pins plus the shared LD bus. **The overall budget was 3 pins short**: the four JTAG pins are part of the 111 I/O. A recommended plan fits, proven by Diamond place-and-route; owner decision C-17 | Datasheet Table 4.4 [V S49]; Diamond pad/map reports [V S62]; fit tests |

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

**Correction to the pin matrix.**
- **What revision C said:** 110 of 111 I/O, with "JTAG uses dedicated pins".
- **What the data show:**
  - MachXO2 datasheet Table 4.4 (LCMXO2-2000, 144 TQFP) gives **111 general-purpose I/O**: banks 27/28/28/8/10/10, plus 1 pin reserved for configuration [V S49].
  - The 33 dual-function I/O within those 111 include TMS, TCK, TDI and TDO.
  - With the JTAG port enabled, which we need (D-12 and the JTAG header), Diamond reserves those four: "Number of PIO sites used: … + 4(JTAG) out of 112" [V S62].
- **Result:** the usable count is **107** (datasheet basis) or 108 (Diamond's 112 sites; the extra site corresponds to the datasheet's "reserved for configuration" pin, not yet identified, concern C-19).

| Plan | Signals | Config pins reserved | Needed | Fits 107? | Diamond fit test |
|---|---|---|---|---|---|
| Pin matrix rev C as written | 107 | 3 (PROGRAMN, INITN, DONE) | 110 + 4 JTAG = 114 | **No (−3)** | – |
| Rev C signals, config pins released | 107 | 0 | 107 + 4 | 0 spare | `fit_top_rc`: places, 107 + 4 of 112 |
| **Recommended:** /OVR and /DTACK not routed (C-14), config pins released | **105** | 0 | 105 + 4 | **2 spare** (3 by Diamond) | `fit_top`: places, 105 + 4 of 112; 0 timing errors |
| LCMXO2-4000HC-4TG144C | 105–107 | 0–3 | – | 115 GPIO (datasheet Table 1.1, rev 4.7) → 4–8 spare | Not run; pin compatibility and price TBV |

- **SRAM interface:** unchanged and not reducible without cost. It needs 18 address + 5 control pins and uses the shared LD bus.
  - The only cheap saving would be tying /CE low, with pull-ups on /OE and /WE instead (−1 pin). That loses the single-resistor deselect, so it is not recommended.
- **Bank voltages:** with every port LVCMOS33, Diamond places all of them with every used bank at VCCIO 3.3 V. The pad check in `run_diamond.sh` enforces this.
- **Dual-function configuration pins.** Diamond's auto-placement put SRAM_OE_N on PROGRAMN, SRAM_UB_N on DONE, LED0 on INITN, ZB_A17 on JTAGENB and SA0 on MCLK. Sheet 2 must assign these pins deliberately:
  - which signals may use them;
  - how they behave during configuration;
  - which SYSCONFIG settings apply.

  That needs the MachXO2 configuration guide (concern C-18). Proposed rule: only LEDs, debug pins, or inputs whose configuration-time state is harmless.

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
| **C-17** | FPGA I/O budget: rev C needs 114 of 111 pins once JTAG is counted (§8) | **High** | **Owner decision.** Recommended: /OVR and /DTACK not routed (C-14) and PROGRAMN/INITN/DONE released, giving 105 of 107 (fit test passes). Alternative: LCMXO2-4000HC, after pin-compatibility and price checks |
| C-18 | Dual-function configuration pins (PROGRAMN, INITN, DONE, JTAGENB, MCLK, SN, SI, SO, CSSPIN) | Medium | Check configuration-time behaviour against the MachXO2 configuration guide before sheet 2; restrict to tolerant signals |
| C-19 | The datasheet's one "reserved for configuration" pin vs Diamond's 112 sites | Low | Identify it from the Lattice pinout file; plan with 107 until then |
| C-20 | SRAM second source not yet verified | Low | Verify alternates from their datasheets before listing them |
| C-21 | Hardware semaphores from the architecture review §7.4 are not implemented | Low | Owner to confirm: queues need no locks; add later only for a multi-writer structure |
| C-22 | Host port waits up to one Zorro cycle (≤ 2.6 µs, watchdog-bounded); the SPI slave is not designed yet | Medium | Sheet 4: buffer at least one Zorro-cycle's worth of SPI data, or use ATTN as busy; quiesce before reconfiguration (H-5) |
| C-23 | 50 MHz register-path slack 2.7 ns at Stage 3 (START decision path) | Low–Medium | Watch at each sheet; if below 1 ns, pipeline the START decision (one extra clock, still deterministic) |
| C-24 | Zero-wait SRAM cycles: thin margins in the model | Low | Stays disabled until G-ZEROWAIT |
| C-25 | PiStorm/Emu68 and other non-68000 masters: address setup, strobe widths and cycle gaps unknown. The design assumes ≥ 1 clock of /AS negation between cycles for host progress, and slot setup ≥ S_req | Medium | New measurement M-12; risk R-41 |

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
