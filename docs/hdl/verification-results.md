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
