# Verification matrix: sheet 1 revision B and the Stage 2 HDL

**Status:** 2026-11-18. Every simulation, netlist and formal item below was **executed on 2026-11-18 and passes**. The run record is [verification-results.md](verification-results.md). **Still open:** Diamond STA (G-STA) and the hardware measurements.
- Lattice Diamond is not installed (gate G-STA).

"Pass criterion" is what the run must show before the item can be marked done. Test IDs refer to [../../hdl/sim/tb_z2.v](../../hdl/sim/tb_z2.v) (T*), [../../hdl/sim/tb_chain.v](../../hdl/sim/tb_chain.v) (S*), [../../hdl/sim/tb_hazard.v](../../hdl/sim/tb_hazard.v) (E*) and the formal properties in [../../hdl/rtl/z2_core.v](../../hdl/rtl/z2_core.v) (F*).

## C-01 /SLAVEn timing (owner: worst-case post-place-and-route STA, assertion and release, voltage, temperature, loading)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Entire combinational decode, /SLAVEn assertion and release | Diamond TRACE with [../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf), [../../hdl/syn/run_diamond.sh](../../hdl/syn/run_diamond.sh) | Every path ≤ 18 ns at the slow corner, both edges, 15 pF | **Pass at the sheet-2 pinout** (rev A1, 2026-11-19: worst 14.910 ns, both grades, z2_top and fit test; 4000HC fallback 14.993 ns; rev A 15.094 ns): [../stage2/sheet2-sta-results.md](../stage2/sheet2-sta-results.md). Exploratory run: [../stage2/sheet1-sta-results.md](../stage2/sheet1-sta-results.md) |
| Budget closes with real buffer delays | [../stage2/sheet1-timing-budget.md](../stage2/sheet1-timing-budget.md) §2 | ≤ 35 ns | **20.7 ns with STA** |
| Simulation with the delay allocation | tb_z2 at FPGA_TMAX 18 and 7.24 ns, all-max/all-min corners (C5b, C5c) | No ASSERT-FAIL | **Pass** (2026-11-18) |
| Shorter predecode if needed | Hazard analysis §6 (O1–O5) | Applied only if G-STA margin < 3 ns | Documented |

## C-02 Address stability and hazards (owner: late address, skew, transitions near /AS; no false /SLAVEn)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Structure: /AS only in the final gate; output inactive for /AS negated | `check_decode_structure.py` on the Yosys netlist; formal F4, F12 | ALL PASS; proof | **Pass** (2026-11-18) |
| No assertion while /AS is negated, under any delay | tb_hazard E1 (random LUT and buffer delays) | 0 false assertions of /SLAVEn, XRDY, buffer enable | **Pass** (2026-11-18) |
| Setup requirement quantified | tb_hazard E2 (setup sweep) + Diamond minimum/maximum delays + M-7 | Model S_req reported; STA S_req ≤ M-7 setup − 3 ns | **Pass** / hardware pending |
| RTL-level transitions near /AS, per-bit skew | tb_z2 T6 (setup 20/10/5 ns + 0–15 ns spread: pass/fail; 2/0/−5 ns: characterisation) | No false /SLAVEn (C5a), ≤ 35 ns (C5b), no glitch (C5d) | **Pass** (2026-11-18) |
| Decode transient cannot enable the data drivers | Formal F1/F2; tb_z2 C2 | No failure | **Pass** (2026-11-18) |

## C-03 AutoConfig bypass, unpowered carrier (owner: normal, unpowered, startup, faults)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Motherboard terminations | A2000 R6 schematic (S51) and Haynie (S52); M-8 on the target | ≈ 1 kΩ pull-down on /CFGOUTn, ≈ 1 kΩ pull-up on /SLAVEn | Verified on schematic; M-8 pending |
| Normal | tb_chain S1; tb_z2 T0–T3 | Chain order 11, 01, 33; card answers at its base | **Pass** (2026-11-18) |
| Unpowered | tb_chain S2; tb_z2 T18 | Chain 11, 33; no collision | **Pass** (2026-11-18) |
| Startup (blank FPGA, ramp, late power-good) | tb_chain S3, S4; tb_z2 T0 | Transparent until a reset with EN_OK; joins at the next reset | **Pass** (2026-11-18) |
| Faults (FPGA reload, power loss, DIP, jumper, reset mid-scan, shut-up) | tb_chain S5–S10; tb_z2 T12–T17; C7 empty-slot checker | As in the design notes §6.4 | **Pass** (2026-11-18) |
| Arming only inside a reset | Formal F10, F11 | Proof | **Pass** (2026-11-18) |

## C-04 U104 output enable (owner: OE-controlled, power-good and reset qualified; /SLAVEn timing kept)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| OE gating by EN_OK · ZF_ARM | Schematic rev B; netlist audit (418 checks) | 0 failures | **Done** (audit run) |
| Timing budget recalculated | Timing budget §2, §8 | /SLAVEn 29.8 ns; OE not in the cycle path | Done (budget); STA pending |
| Hi-Z through the power ramp | Design notes §5; tb_z2 T0; M-6/M-9 | No assertion during the ramp | **Pass** / hardware pending |

## C-05 Data-buffer safety (owner: never enabled for an invalid cycle; no contention on direction change; DOE, /AS release, reset, wait states, bus errors)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Never enabled for an invalid cycle | tb_z2 C2 (sampled every 0.5 ns, release allowance); formal F1/F2 | No failure; proof | **Pass** (2026-11-18) |
| No contention on direction changes | U103 model "DIR changed while enabled"; card_sheet1 LD-contention monitor; tb_z2 C1; formal F5, F8, F9 | No failure; proof | **Pass** (2026-11-18) |
| DOE assertion and release | tb_z2 T5 (DOE on 0/30/70/140 ns, off −30/0/+30 ns) | Data correct, no failure | **Pass** (2026-11-18) |
| /AS release, aborted cycles | tb_z2 T8 (raw cycles, /AS 20–335 ns, arbitrary strobes and DOE) | No failure; next cycle correct | **Pass** (2026-11-18) |
| Reset | tb_z2 T12 (/BUSRST during a driven read) | Release; AutoConfig again; SCRATCH preserved | **Pass** (2026-11-18) |
| Wait states | tb_z2 `bus` check (≥ 1 wait when gated, 0 in zero-wait); C6a–C6d; T9 watchdog; T10 zero-wait | No failure | **Pass** (2026-11-18) |
| Bus errors | tb_z2 T7 (/BERR during read, write, RMW); BERR_EVENTS | Release within the allowance; counter ≥ 4 | **Pass** (2026-11-18) |

## C-13 Read-modify-write (owner: RMW, byte strobes, direction changes, OE, XRDY)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| RMW with /AS held | tb_z2 T4 (TAS even/odd byte × DOE continuous/split × motherboard data drive 0/30 ns), T5, T7, T10 | Correct read value and result, RMW_CYCLES = 8 after T4, no C1/C2/DIR failure | **Pass** (2026-11-18) |
| Read drive ends at the read strobe (S7) | RTL read term; timing budget §4.1, §7 | ≥ 398 ns margin to S14 | Analysed |
| Per-phase XRDY | FSM ST_BETWN re-hold; formal F16 | XRDY held for the write portion; bounded | **Pass** (2026-11-18) |
| Hardware confirmation | M-10 | B-port enable ends before READ falls | Pending (hardware) |

## Gates

| Gate | Condition | Status |
|---|---|---|
| **G-SIM** (new) | `bash hdl/run_checks.sh` prints `ALL HDL CHECKS PASSED`: lint, tb_z2 (4 seeds + 4 corner runs), tb_chain (4 seeds), structure check, tb_hazard E1 = 0, formal prove/bmc/cover | **Passed 2026-11-18** |
| **G-STA** | Diamond, as in the timing budget §9 | **Passed at the sheet-2 pinout 2026-11-19** for every Zorro path and the 50 MHz clock; open for the host SPI capture path (sheet 4) and the hardware comparison (M-1, M-2, M-7) |
| G-SHEET1 | Owner review of sheet 1 revision B | **Approved 2026-11-19** for design progression |

## Sheet 3 (Stage 3): shared SRAM, arbitration, queues and interrupts

Evidence executed on 2026-11-19 ([verification-results.md](verification-results.md) §5). Test IDs: [../../hdl/sim/tb_shm.v](../../hdl/sim/tb_shm.v) (S*), formal [../../hdl/formal/fv_shm.v](../../hdl/formal/fv_shm.v) (X*, M*).

| Owner priority / requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Correct arbitration Zorro ↔ SPI side | X1, X2, X3, X6 (k-induction); tb_z2 4 seeds with continuous host traffic; tb_shm | Proof holds; 0 failures; SRAM model 0 AC violations; LD contention monitor silent | **Pass** |
| Deterministic Zorro timing | **X4** (k-induction); tb_shm S3 (host off/on) | Proof holds; local-bus action at one fixed clock offset in every cycle, identical off/on | **Pass** (START + 6 reads, DS + 1 writes) |
| Simultaneous requests, RMW atomicity | X1, X4; tb_shm S4 (TAS while the host writes the same word) | Proof holds; M1 monitor silent; TAS results correct | **Pass** |
| Mailbox ownership and synchronisation | M1–M5; tb_shm S5 (both directions, full, stale epoch, wrong owner, byte write), S6 (link resets, events) | Proof holds; every rejection and event as specified | **Pass** |
| No RP2040 response to Zorro cycles | Design (host-port contract H-6); tb_z2 passes with the host idle and with continuous host traffic | – | **Pass** (by construction; checked) |
| SRAM AC limits (ISSI −10) | SRAM model checks on every access; timing budget §2 with Diamond tCO | 0 violations; every margin positive | **Pass** (model and budget); hardware M-11 open |
| Safe state while the FPGA is blank or reloading | tb_shm S8 (deselected, /WE high, contents kept); card model pin-float timing | /CE, /WE high; no LD drive; data kept | **Pass** (model); hardware M-9/M-11 open |
| FPGA pin availability | Diamond fit tests `fit_top`, `fit_top_rc`; pad check | Places with JTAG enabled, all banks 3.3 V, 0 timing errors | **Pass**: physical assignment on sheet 2 (`pinplan.py`; `audit_sheet2.py` 1047 checks; C-18 rules applied) |
| Schematic connectivity | `audit_sheet3.py` (120 checks), ERC | 0 failures; only documented ERC entries | **Pass** |

### Sheet 3 revision A1 additions (owner review, 2026-11-19)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| C-17 plan: 102 signals with JTAG and PROGRAMN/INITN/DONE kept | Diamond `fit_top` with SYSCONFIG SDM_PORT and JTAGENB/SN prohibited | Places; 0 timing errors; pad check | **Pass** (102 + 4 JTAG of 112) |
| C-17 fallback: LCMXO2-4000HC at the same pins | `pinplan.py` migration check; Diamond z2_top and `fit_top` on the 4000HC −4 C | Same banks and dedicated pins; 0 timing errors | **Pass** (sheet 2) |
| Canonical byte order (hardware lanes) | tb_shm S12, vectors V1–V4, V6 | Every view as in the byte-order spec | **Pass** |
| Two-LED interface, READY blink code | tb_z2 T3 (CONTROL b5..b4, LED test) | Register and pins as specified | **Pass** |
| C-26: one FPGA LED (READY pin) plus the internal fault indication | tb_z2 T3 checks `LED_READY` and `fault_ind`; pin freeze in `pinplan.py`; audit (LED_READY on pin 65, no LED_FAULT net) | As specified; only pin 67 changed from the approved assignment | **Pass** (rev A1) |
| Fail-safe bus behaviour with an erased, configuring or failed FPGA | Sheet-1 design and chain simulation (S3); sheet-2 notes §8; hardware M-6 + **M-14** | Card absent, chain passes, SRAM deselected, READY off | Design/simulation **Pass**; hardware open |

## Sheet 4 (Stage 4): RP2040 host link, revision A (owner decisions S4-1 to S4-5, requirements 1–9)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| HL-1 protocol and byte order at the pins, normative vectors | tb_spi P1, P2 (vectors from `tools/hostlink/hostlink.py`), P8 | Byte-exact at the pins | **Pass** (simulation) |
| HL-2 CDC | fv_afifo (multiclock k-induction) and random-rate simulation (tb_spi P15) | Proven; no failure | **Pass** |
| HL-3 buffering at maximum SCK; overflow impossible or reported | Sizing argument (protocol §9); fv_afifo A2/A5; tb_spi P10, P11 | No loss; overflow refused and flagged | **Pass** |
| HL-4 ordering | Protocol §7; tb_spi P11 (128-word bursts read back); tb_z2 SPI background (shadow-checked) | Order and data preserved | **Pass** |
| HL-5 tb_shm through the real slave | tb_shm (SPI build), 4 seeds | All 127 checks; Zorro timing identical with SPI traffic (S3) | **Pass** |
| HL-6 stress during Amiga copy loops | tb_z2 with continuous SPI background, 4 seeds | All 5 554 checks | **Pass** (simulation); hardware **M-13** open |
| Req. 1 no partial commit | tb_spi P3, P4, P5, P13, P16 | Target words unwritten; counters | **Pass** |
| Req. 3 flow control, busy Zorro bus | tb_spi P10; HL-5; HL-6 | No SCK stall needed; busy frames rejected without effect | **Pass** |
| Req. 4 SCK → MISO timing | [../stage2/sheet4-timing-budget.md](../stage2/sheet4-timing-budget.md); STA | Budget closes: 10 MHz standard, 20 MHz early launch | Paper **Pass**; hardware **M-15** open |
| Req. 5 async FIFO | fv_afifo | Proven for every clock ratio, stoppage, reset | **Pass** |
| Req. 6 sheet-3 ordering and atomicity | fv_shm (X1–X6, M1–M7); tb_shm via SPI | Proven; all checks | **Pass** |
| Req. 7 back-powering and false interrupts | Design-notes §7 state table; S4-6 rev A3 worst-case analysis and K4 model ([../stage2/sheet4-s46-isolation.md](../stage2/sheet4-s46-isolation.md)); audit_sheet4 (S4-6 rules incl. no source on GP24 and gate-only domain crossing, R-51 defaults, ER-3; 29 of 29 mutants); tb_spi P0, P13, P14, P16 and always-on checkers | No path; no RP2040 pin above IOVDD + 0.3 V (model-derived bound: IOVDD slopes ≤ 264 V/ms; X4 estimate ≤ 94 V/ms); no false interrupt or ATTN | Design/simulation **Pass**; S4-6 rev A3 accepted (owner review of PR #9); hardware **M-14** (extended), **M-16** open |
| Req. 8 re-run timing and HDL | run_checks.sh; Diamond 6 runs (+1 confirming run, rev A1) | All pass | **Pass** on the LCMXO2-4000HC (C-30 approved) |
| Req. 9 versioning | tb_spi P1, P7 | IDENTIFY fields; wrong major rejected | **Pass** |

## Sheet 5 (power and X4 power control), revision A (owner decisions S5-1 to S5-9)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| S5-2 current limit, start-up, coordination | `tools/analysis/sheet5_power.py` §1–§5; audit_sheet5 re-derives ILIM from R506 | ILIM_min ≥ 1.05 × 2.5 A, ILIM_max ≤ 3.4 A; start-up margin ≥ 20 °C in cases A, B, E | Model **Pass** (2.65–3.36 A; worst margin 25 °C) [E]; hardware **M-17**, **M-18** open |
| S5-2 UVLO/OVLO windows | sheet5_power.py §6; audit_sheet5 (from schematic values) | 11.4–12.6 V and 4.75–5.25 V inside; R1 ≥ 350 kΩ; pins ≤ 6.5 V at the clamp | **Pass** (paper); **M-18** open |
| S5-3/S5-9 default off, interlock safe during configuration | Proposal §5.1 state table; audit_sheet5 (enable chain membership, Q502 bias, R510) | U501 off unless X4_PWR_EN high | Design **Pass**; RTL PM-1 to PM-10 not written; **M-20** open |
| S5-4 INA226 0x44, I²C domains (C-28, C-29) | audit_sheet5; audit_sheet2 | Address 0x44; pull-ups on +3V3 only | **Pass** (netlist); **M-19** open |
| S5-5 S0 sense active low, ER-3 | audit_sheet5; audit_sheet4 (ER-3) | Q503 drain + +3V3 pull-up; ≤ 3.5 µA from X4_3V3_REF | **Pass** (netlist); **M-24** open |
| S5-6 5 V margin | sheet5_power.py §7; audit_sheet5 (U503 window ≤ 6.10 V, U504 = TLV76733) | +5V_BUS ≤ 6.0 V in slow and fast overvoltage; regulator survives 12.6 V | Model **Pass** [E]; **M-23** open |
| S5-7 thermal | sheet5_power.py §8 | TJ ≤ 125 °C at 60 °C ambient | Model **Pass** (≤ 101 °C) [E]; **M-22** open |
| S5-8 ground return (conditional) | `tools/analysis/sheet5_ground.py`; audit_sheet5 (H501–H504 on GND, J502 order) | ΔG ≤ 50 mV in normal operation; currents within the derived requirements | Model **Pass** (≤ 33 mV; ≤ 2.8 mV with bonded standoffs) [E]; ratings **TBV** (R-56); **M-21** open |
| Netlist integrity | audit_sheet5 (274 checks), mutation 28 of 28; audits 1–4 unchanged results; netlist outside sheet 5 identical | 0 failures | **Pass** |
| FPGA dynamic power | Diamond Power Calculator | Inside the 0.25 A +3V3 design maximum | **Open (P-1)**: the Tcl project mode did not load the NCD |

