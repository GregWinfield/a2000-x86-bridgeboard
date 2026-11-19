# HDL verification results: sheet 1 revision B (gate G-SIM)

**Run:** 2026-11-18, on the development PC (Windows 11).
- **Command:** `OSS_CAD_SUITE=<dir> bash hdl/run_checks.sh`
- **Result:** **`ALL HDL CHECKS PASSED`** in 22.6 s.

**Tools.** OSS CAD Suite release 2026-10-31 (S59, SHA-256 verified):
- Icarus Verilog 14.0 (devel, s20260301-786-g5d0488854);
- Yosys 0.70+286 (git 63eecf3dd);
- SymbiYosys with the Yices SMT engine.

**What this does not cover.**
- These are **model** results. Board and A2000 behaviour come from datasheet delays and the assumptions listed in [../../hdl/sim/z2_master.v](../../hdl/sim/z2_master.v).
- The formal proofs cover `z2_core` (cycle-level, all inputs unconstrained), not analogue or timing behaviour.
- Post-place-and-route timing (G-STA, Lattice Diamond) and the hardware measurements M-1 to M-10 are still open.

Requirement mapping: [verification-matrix.md](verification-matrix.md).

## 1. Results

| Check | Runs | Result |
|---|---|---|
| Lint: `iverilog -Wall` on the RTL | 1 | Clean, no warnings |
| **tb_z2** bus-functional | Seeds 1–8 (random per-channel skew); all-maximum and all-minimum delay corners × FPGA delay 18 ns and 7.24 ns | **12 runs, 5 526 checks each, 0 failures** |
| **tb_chain** AutoConfig chain (S1–S10) | Seeds 1–4 | **0 failures.** Chain contents as expected in every scenario; no /SLAVEn collision |
| Netlist structure (C-02) | Yosys generic 4-LUT mapping | **13/13 PASS.** /AS and /BERR feed only the three single-LUT final gates. Each gate outputs 1 for every decode value while /AS is negated (and, for asgate3, while /BERR is asserted) |
| **tb_hazard** E1: /AS negated, random LUT and buffer delays | 2 × 400 trials | **0 false assertions** of /SLAVEn, XRDY and buffer enable |
| **Formal** prove (k-induction, depth 24) | F1–F16 | **PASS:** proof holds for any input sequence |
| Formal bmc (depth 48) | Adds the pin-level XRDY bound | **PASS** |
| Formal cover | 4 goals | **All reached** (steps 18–22): configured; RMW cycle completed; watchdog trip; read drive active |
| MachXO2 synthesis (Yosys `synth_lattice -family xo2`) | Resource estimate only | 382 LUT4, 57 CCU2D, 264 FF, 16 tristate LD bits; about 18 % of the XO2-2000's 2 112 LUTs. Each final gate is one LUT4 |

## 2. C-02 characterisation (not pass/fail)

**Decode depth (Yosys mapping).**
- A17, A18 and A21–A23 → `sel_k`: 3 LUT levels.
- A16, A19 and A20: 2 levels.
- One more level (the final gate) to /SLAVEn. /AS → /SLAVEn: 1 level.

**Required slot address setup S_req.** The model assumes LUT plus routing 0.3–2.5 ns per level [A] and buffers 1.4–4.9 ns.

| Experiment | Result |
|---|---|
| **E3 deterministic corner:** every LUT 2.5 ns, address buffer max, /AS buffer min | **S_req = 11.0 ns** for 3-level bits; 8.5 ns for 2-level bits. This equals the inequality (4.9 + 3 × 2.5 − 1.4 = 11.0) exactly |
| E2a Monte-Carlo, single-bit change (worst pattern), 400 trials per point | False /SLAVEn in 400/400 trials at ≤ −2 ns; 193/400 at 0 ns; 37/400 at 6 ns; **0 from 8 ns** |
| E2b Monte-Carlo, random unselected address, 0–10 ns skew | 0 from 6 ns |
| tb_z2 T6 RTL level (buffer skew only, zero-delay FPGA) | 0 false at 2 ns (all runs); at 0 ns, 60/60 or 0 depending on the drawn skew; 60/60 at −5 ns |

**Conclusion.** Under the model's worst corner the slot must provide ≥ 11 ns address setup to /AS. The hand estimate in revision B, ≈ 8.5 ns, was optimistic and has been corrected in the hazard analysis. The real figure comes from Diamond minimum/maximum delays (G-STA), compared with M-7.

## 3. Are the checks able to fail? (mutation tests)

Deliberately broken copies of the RTL, kept outside the repository, were run through the same checks:

| Mutation | Caught by |
|---|---|
| M1: read enable without the data-strobe term (the rev A logic) | tb_z2 **C2** (21 failures: drive after the read strobe in RMW cycles) |
| M2: DIR may change without the guard interval | **Formal F8** (basecase and induction). Simulation passes: one clock of separation still exceeds the modelled OE-disable time, so this is a margin loss, not a modelled fault |
| M3: /SLAVEn not gated by /AS | tb_z2 **C5a/C5c**; tb_chain S6/S9 |
| M4: drop the XRDY release in ST_IGNORE | Not a fault: equivalent mutant (START already clears `hold_q`) |
| M4b: drop both XRDY releases for ignored cycles | **Formal bmc** pin-level XRDY bound; tb_z2 **T8b/C6d** (added after this mutation exposed a coverage gap) |
| M5: arm without a Zorro reset | tb_z2 T15/T17; tb_chain **S4a** |

## 4. Defects found and fixed during the first runs

All defects were in the verification code. **The RTL committed in 704ea69 needed no change.**

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | 998 failures: XRDY never held | `m_dly` model output stayed X for inputs that never change. /BERR is pulled up from time 0, so the XRDY gate saw X | Model samples its input once after time 0 |
| 2 | "LD contention" at time 0 | X resolution race in the monitor | Monitor ignores t ≤ 1 ns |
| 3 | C6a/C5a failures in T8 (20 ns runt /AS) | XRDY and /SLAVEn are delayed copies of /AS and may still assert just after a runt /AS ends | Same path-delay allowance as C2. Unselected addresses are still never allowed |
| 4 | Hazard E1–E3 too optimistic | `write_verilog` printed LUTs as zero-delay expressions, so the random-delay LUT model was never used | `write_verilog -noexpr`; all hazard results re-run (§2) |
| 5 | E2 looked optimistic | Random multi-bit targets let the select term fall early | Added E2a (single-bit worst case) and E3 (deterministic corner) |
| 6 | Coverage gap (mutation M4b) | No test changed the address during /AS | Added T8b |
| 7 | Formal basecase failed after a 2026-11-19 RTL edit | A `//` comment placed mid-line in the `initial` block commented out four initial values. Simulation passed because the power-on reset clears those registers; formal starts from the declared initial state | Line fixed; full suite re-run: ALL HDL CHECKS PASSED |

Post-place-and-route timing (Lattice Diamond) is recorded separately in [../stage2/sheet1-sta-results.md](../stage2/sheet1-sta-results.md).

## 5. Stage 3 (sheet 3 revision A), 2026-11-19

`bash hdl/run_checks.sh` → **ALL HDL CHECKS PASSED** (same tools as §1).

### 5.1 Results

| Check | Runs | Result |
|---|---|---|
| Lint (`iverilog -Wall`, RTL with the host-port stub) | 1 | Clean |
| tb_z2 (unchanged tests; SRAM fitted; VERSION $0A02; T3/T16 now write and read the SRAM) | 4 seeds + 4 corners | 5 552 checks each, **0 failures** |
| **tb_z2 with continuous random host SRAM traffic** (`-DHOST_BG`) | 4 seeds | 5 552 checks each, **0 failures**; about 4 760–4 790 host transfers per run, all data correct; host latency mean ≈ 186 ns, max 2.40–2.64 µs |
| **tb_shm** S1–S11 | 4 seeds + 2 corners | 99 checks each, **0 failures** |
| tb_shm S3 determinism | 6 runs × 120 cycles × host off/on | Read action always START + 6, write action always DS + 1, off and on; slot /AS → XRDY range unchanged |
| SRAM model AC checks | every run | **0 violations** |
| tb_chain | 4 seeds | 0 failures (card model now includes sheet 3) |
| Formal z2_core (F1–F20) | prove / bmc / cover | PASS |
| **Formal fv_shm** (X1–X6, M1–M5, F1–F20, every input free) | prove (k-induction) / bmc 64 / cover | **PASS / PASS / all reached** |
| Yosys MachXO2 estimate | – | 634 LUT4, 85 CCU2D, 386 FF (about 30 % of the XO2-2000); the host path is tied off by the stub |

### 5.2 Diamond (exploratory, Diamond-placed pins)

| Run | Errors | Worst Zorro path | SRAM clock-to-out | 50 MHz slack |
|---|---|---|---|---|
| Stage 3 z2_top, −4 C / −4 I | 0 / 0 | 14.87 / 15.09 ns (A16 → XRDY) | 9.95 / 9.60 ns max, 2.93 / 2.74 ns min | 2.73 / 3.41 ns |
| Fit test 105 signals / 107 signals (−4 C) | 0 / 0 | – | 9.94 / 10.09 ns max | 4.15 / 3.98 ns |

Pad check (every port LVCMOS33, every used bank at 3.3 V): pass in every run.

### 5.3 Mutation check of the shared-memory proof

| Mutant | Caught by |
|---|---|
| A reservation floor too low (ZRES = 2) | X4: k-induction fails; real counterexample within 64 steps |
| B host starts without `z_quiet` | X3: induction; real counterexample within 64 steps |
| C host starts during a Zorro reservation | X1/X2: counterexample within 20 steps |
| D host /WE pulse two clocks | X5: counterexample within 20 steps |
| E Zorro read go without `h_quiet` | **Equivalent:** X4 proves the check is redundant given ZRES. It is kept in the RTL as a defensive guard |
| F index write without the epoch check | M4: real counterexample within 64 steps |
| G producer may overrun (no free-space check) | M1: counterexample within 20 steps |
| H SRAM /WE on a register target | F17/F5: real counterexample within 64 steps |

### 5.4 Defects found and fixed during Stage 3

| # | Where | Symptom | Cause | Fix |
|---|---|---|---|---|
| 8 | **RTL** (z2_core) | k-induction failure of the one-clock /WE property | A /BERR in the clock after the SRAM /WE pulse started took the ABORT branch without clearing `zq_we`, so /WE stayed low for 2 clocks. Harmless (address stable), but not the specified pulse; too deep for the 24-step base case | Clear `zq_we` on the /BERR exit; invariant `zq_we → WR_CAP & wr_cnt = GUARD + 1` added |
| 9 | **RTL** (z2_mbx), simulation only | A read after a write-1-to-clear returned the old value | `assign zr_rdata = rd(zr_ridx)`: a continuous assignment of a function is re-evaluated only when its arguments change, not when the registers it reads change (synthesis would be correct) | `always @*` multiplexers. Found by tb_shm S5 |
| 10 | SRAM model | First reads returned X; drive window never closed | Delayed `tick <= #T ~tick` toggles computed their value at scheduling time, so the second of two pending toggles changed nothing and an evaluation was lost | Evaluate on input changes plus a 0.5 ns poll while enabled |
| 11 | Card model | False "address changed during a write" at an FPGA reload | FPGA pins modelled as tri-stating instantly; the float register was loaded after the pin multiplexer had already seen the old value | Pins hold their level briefly, then pull-ups (≈ 20 ns) and the weak pull-down (≥ 80 ns) take over; float registers track the driven values |
| 12 | Diamond summary script | Wrong slack for a failing CLOCK_TO_OUT; data-path delay only | TRACE writes "exceeds requirements" for failures; CLOCK_TO_OUT totals are in "totaling" | Parser rewritten; earlier MAXDELAY results unchanged |
| 13 | Constraint | LD clock-to-out 12.05 ns against a 12 ns allocation chosen without derivation | Allocation, not a requirement | Allocation derived: 16 ns (sheet-3 timing budget §3) |

Earlier finding (Stage 2, same day): the exploratory STA had analysed most ports as LVCMOS25. That is corrected in the STA record, and `run_diamond.sh` now fails on any non-LVCMOS33 port.

### 5.5 Revision A1 (owner decisions), 2026-11-19

| Change | Check | Result |
|---|---|---|
| z2_top: ZF_OVR_N/ZF_DTACK_N removed; LED[1:0] (READY blink code, FAULT); CONTROL LED test b5..b4 | Full `run_checks.sh` | **ALL HDL CHECKS PASSED** (tb_z2 5 554 checks per run; tb_shm 127 per run) |
| tb_shm S12: canonical byte order through both ports | 4 seeds + 2 corners | 0 failures |
| LPF: `SYSCONFIG SDM_PORT=PROGRAMN_DONE_INITN JTAG_PORT=ENABLE`; `PROHIBIT SITE "120"` (JTAGENB), `"70"` (SN) | Diamond z2_top −4 C / −4 I; `fit_top` (102 signals) −4 C | 0 / 0 / 0 errors; worst Zorro path 13.71 / 14.94 / 15.14 ns; 50 MHz slack 4.76 / 4.11 / 3.66 ns; configuration pins "Reserved: sysCONFIG"; 102 + 4 JTAG of 112 sites |

### 5.6 Sheet 2 revision A (final FPGA pins), 2026-11-19

| Change | Check | Result |
|---|---|---|
| LPF: 86 LOCATEs generated by `tools/fpga/pinplan.py` (plus 16 fit-only in `fit_top_extra.lpf`); `PROHIBIT SITE "70"` removed because SN now carries SA17, an output (rule: never an externally driven input); `PROHIBIT SITE "120"` kept | Diamond z2_top and `fit_top`, −4 C and −4 I; pad check | 0 setup / 0 hold errors in all four runs; worst Zorro path 15.094 ns; 50 MHz slack ≥ 3.92 ns ([../stage2/sheet2-sta-results.md](../stage2/sheet2-sta-results.md)) |
| Fallback device LCMXO2-4000HC-4TG144C | Diamond z2_top and `fit_top`, −4 C | 0 / 0 errors; worst 15.85 ns; slack ≥ 3.60 ns |
| Schematic sheet 2 | `audit_sheet2.py` against the pinout data, the LPF and `fit_top.v` port directions | 1047 checks, 0 failures; mutation test 7 of 7 faults detected |
| RTL | none changed; full `run_checks.sh` re-run on the final tree | **ALL HDL CHECKS PASSED**: 23 testbench runs (tb_z2 5 554 checks per run, tb_shm 127, tb_chain 18, tb_hazard) and 6 formal tasks |
