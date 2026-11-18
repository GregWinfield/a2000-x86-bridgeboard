# Sheet 1 / FPGA: post-place-and-route static timing results (C-01, gate G-STA)

**Run:** 2026-11-19 on the owner's PC. Lattice Diamond 3.14.0.75.2 (64-bit) with the free licence; LSE synthesis, map, PAR and TRACE.
- **Command:** `bash hdl/syn/run_diamond.sh <work dir> <device>`. It runs [../../hdl/syn/diamond_sta.tcl](../../hdl/syn/diamond_sta.tcl) with [../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf) and summarises with `twr_summary.py`.
- **RTL:** as merged in PR #2 (sheet 1 revision B, G-SIM passed).

> **Exploratory, not final.** Sheet 2 does not exist yet, so **Diamond chose the pin locations itself**. Gate G-STA closes only when this run is repeated with the final sheet-2 pin assignment and still meets every limit.

> **Correction (2026-11-19, after PR #2 was merged).**
> - **What was wrong.** The first exploratory run set IO_TYPE only on the ports in bank 0, which included /AS, the strobes and the ZF outputs. Diamond's default for every other port is LVCMOS25, and it set those banks to VCCIO 2.5 V. So **ZB_A[23:1]**, LD[15:1], clk_core, LED and DIP were analysed as LVCMOS25 at 2.5 V. ZB_A16–A23 are on the constrained /SLAVEn and XRDY paths.
> - **Found** while reading the pad report for the sheet-3 pin reassessment.
> - **Fixed.** The LPF now has `IOBUF ALLPORTS IO_TYPE=LVCMOS33` plus explicit lines for ZB_A and LD. Both grades were re-run. The pad reports show **0 LVCMOS25 ports** and VCCIO 3.3 V in every used bank.
> - **Superseded figures.** The first run reported worst 14.79 ns, /AS → /SLAVEn 8.84 ns, /SLAVEn total 20.6 ns, S_req 15.2 ns and M-7 ≥ 18.2 ns. The corrected values are below.
> - **Confounding factor.** Diamond also placed the pins differently in the re-run, so the change mixes the I/O standard with placement.

## 1. Conditions

| Item | Setting | Source |
|---|---|---|
| Devices | LCMXO2-2000HC-**4**TG144**C** (commercial) and LCMXO2-2000HC-**4**TG144**I** (industrial, map `-oc Industrial`) | Diamond log |
| Timing data | "Performance Hardware Data Status: Final, Version 36.4"; package data Final 1.44 | TRACE header |
| Maximum delays (setup) | Speed grade 4 (`trce -sp 4`). No TEMPERATURE/VOLTAGE preference, so derating factor 1.0. This is the default worst case for the grade: **TJ 85 °C commercial, 100 °C industrial** | Diamond constraint reference, TEMPERATURE / VOLTAGE |
| Minimum delays (hold) | Fast model (`trce -sphld m`), reported through `MAXDELAY … MIN 0 ns` on the /SLAVEn paths | TRACE command line, LPF |
| Output loading | **15 pF on every output** (`OUTPUT ALLPORTS LOAD`; Diamond default 0 pF). Actual loads: SN74LVC8T245 A port 8.5 pF typ [V S53]; SN74LVC32A input 5 pF [V S55]; LVCH16T245 DIR 4–5 pF × 2 [V S46]; plus trace and pad | LPF |
| I/O standard | **LVCMOS33 on every port**; every used bank at **VCCIO 3.3 V**. Outputs 8 mA; FAST slew on ZF_SLAVE_N, ZF_XRDY, ZF_DBUF_OE_N | LPF; pad report "Vccio by Bank" |
| Placement | Diamond-placed I/O, different in each run. **The two grades are therefore not a like-for-like comparison**; take the worst of the two | pad report |
| Edges | TRACE times both rising and falling transitions of every constrained path; the worst is reported | TRACE |

## 2. Results (all 27 constraints met; 0 setup errors, 0 hold errors, both grades)

| Path (FPGA pin to pin) | Commercial max | Industrial max | Allocation | Worst slack | Minimum (C / I) |
|---|---|---|---|---|---|
| ZB_AS_N → ZF_SLAVE_N | **8.913** | 8.235 | 18 | 9.087 | 2.735 / **2.344** |
| ZB_A[23:16] → ZF_SLAVE_N (worst: A16) | **15.227** | 13.634 | 18 | 2.773 | 3.101 / **2.676** (A20) |
| ZB_AS_N → ZF_XRDY | **9.614** | 8.276 | 18 | 8.386 | – |
| ZB_BERR_N → ZF_XRDY | **9.660** | 8.752 | 18 | 8.340 | – |
| ZB_A[23:16] → ZF_XRDY (worst: A16) | **15.311** | 13.656 | 18 | **2.689** | – |
| ZB_AS_N → ZF_DBUF_OE_N | 8.807 | **9.089** | 18 | 8.911 | – |
| ZB_BERR_N → ZF_DBUF_OE_N | **9.701** | 9.572 | 18 | 8.299 | – |
| ZB_DOE / ZB_READ → ZF_DBUF_OE_N | 11.654 / **12.059** | 11.441 / 11.505 | 18 | 5.941 | – |
| ZB_UDS_N / ZB_LDS_N → ZF_DBUF_OE_N | 12.027 / **12.813** | 12.142 / 12.253 | 18 | 5.187 | – |
| ZB_CFGIN_N → ZF_CFGOUT_N | **9.799** | 9.441 | 25 | 15.201 | – |
| clk_core (50 MHz) worst register path | 13.794 | 12.991 | 20 | 5.924 | – |

All values in ns. The worst path overall is **A16 → ZF_XRDY at 15.311 ns**, which leaves **2.7 ns** of the 18 ns allocation.

## 3. Board-level budgets with the STA values

Built from the worst FPGA figure of either grade and the datasheet maxima ([sheet1-timing-budget.md](sheet1-timing-budget.md)):

| Budget | Total | Limit | Margin |
|---|---|---|---|
| /AS → /SLAVEn, assertion and negation: 0.3 + 4.1 + 0.5 + **8.913** + 0.5 + 4.4 + 2.0 | **20.7 ns** | 35 / 50 ns | **14.3 / 29.3 ns** |
| /AS → XRDY negated: 5.1 + **9.614** + 3.8 + 4.1 + 2.0 | **24.6 ns** | 60 ns | **35.4 ns** |
| Data-buffer release, worst input (LDS): 5.1 + **12.813** + 3.8 + 6.3 | **28.0 ns** | #29A 187 ns; RMW ≥ 431 ns | ≥ 159 ns |

## 4. Hazard inequality with STA delays (C-02)

From [sheet1-hazard-analysis.md](sheet1-hazard-analysis.md) §4.2. The buffer skew term is 3.5 ns (LVC16244A 4.1 − 1.1 ns, plus 0.5 ns of trace).

| Requirement | Conservative: slow maximum − fast minimum | Same corner (slow) |
|---|---|---|
| **Slot address setup S_req** | 3.5 + (15.227 − 2.344) = **16.4 ns** | C: 3.5 + (15.227 − 8.913) = **9.8 ns**; I: 3.5 + (13.634 − 8.235) = 8.9 ns |
| Slot address hold | 3.5 + (8.913 − 2.676) = **9.7 ns** | – |

- **Which bound applies.** Both paths sit on one die at one temperature and voltage, so the same-corner bound is the realistic one. The conservative bound also covers on-chip variation and the model's corners being far apart.
- **Pass criterion for M-7.** Measured slot setup ≥ **19.4 ns** (conservative S_req + 3 ns). A result between **12.8 and 19.4 ns** is acceptable only on the same-corner basis and must be recorded as such. Hold needs ≤ 9.7 ns, against the 68000's ≥ 40 ns (#13) [V S57].
- **Slowest bits.** A16–A18 are the slowest (they carry the mode-B mask). Placement (O1) or the predecode options (O3) shorten them if M-7 shows less margin than needed. The final pinout (sheet 2) should put A16–A18 next to the decode logic.
- **Model check.** The gate-level model corner (tb_hazard E3, 11.0 ns) lies between the two STA bounds.

## 5. Structure on Diamond's own netlist (C-02 S1/S2)

`python -I hdl/syn/check_diamond_gates.py impl1/z2_sta_impl1_mapvo.vo` → **ALL PASS** for both grades (corrected runs).

| Check | Result |
|---|---|
| Gate LUTs (LSE kept the hierarchy names) | z2_asgate2 → ZF_SLAVE_N, init `16'hBBBB` (inputs /AS, select). z2_asgate3 → ZF_XRDY, `16'hFF7F` (LSE merged the `sel_k & hold_q` AND into it). z2_asgate3 → ZF_DBUF_OE_N, `16'hF7F7` |
| Controlling input | Each LUT outputs 1 for every input combination with /AS negated; the asgate3 LUTs also with /BERR asserted |
| Fan-out of the /AS and /BERR pads | Only those LUTs and one synchroniser flip-flop each |

## 6. Warnings reviewed

| Warning | Assessment |
|---|---|
| Initial value ignored on `ld_dout[15:0]` | Benign: probably packed into I/O registers, and always loaded before LD is driven |
| ZB_E7M unused / IO buffer missing | Expected: E7M is a monitor input with no Stage 2 load |
| `VCC_net` / `GND_net` of the asgate instances have no load | Artefact of the preserved hierarchy |
| "No user .sdc file" | LSE uses the LPF for place and route |

## 7. What remains for G-STA

1. Repeat with the **sheet-2 pin assignment**, every limit still met, worst slack recorded.
2. Re-derive §4 with the final numbers.
3. Compare with M-1, M-2 and M-7 on hardware (after G-PSU).
4. **Check rule (from this correction):** every G-STA run must show 0 ports with an unintended IO_TYPE in the pad report and the intended VCCIO in every bank, before the timing figures are quoted.
