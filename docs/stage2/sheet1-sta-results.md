# Sheet 1 / FPGA: post-place-and-route static timing results (C-01, gate G-STA)

**Run:** 2026-11-19 on the owner's PC. Lattice Diamond 3.14.0.75.2 (64-bit) with the free licence; LSE synthesis, map, PAR and TRACE.
- **Command:** `bash hdl/syn/run_diamond.sh <work dir> <device>`. It runs [../../hdl/syn/diamond_sta.tcl](../../hdl/syn/diamond_sta.tcl) with [../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf) and summarises with `twr_summary.py`.
- **RTL:** this branch, after the 2026-11-19 initial-value change; simulation and formal suite re-run and passing.

> **Exploratory, not final.** Sheet 2 does not exist yet, so **Diamond chose the pin locations itself**. Gate G-STA closes only when this run is repeated with the final sheet-2 pin assignment and still meets every limit.

## 1. Conditions

| Item | Setting | Source |
|---|---|---|
| Devices | LCMXO2-2000HC-**4**TG144**C** (commercial) and LCMXO2-2000HC-**4**TG144**I** (industrial, map `-oc Industrial`) | Diamond log |
| Timing data | "Performance Hardware Data Status: Final, Version 36.4"; package data Final 1.44 | TRACE header |
| Maximum delays (setup) | Speed grade 4 (`trce -sp 4`). No TEMPERATURE/VOLTAGE preference, so derating factor 1.0. This is the default worst case for the grade: **TJ 85 °C commercial, 100 °C industrial** | Diamond constraint reference, TEMPERATURE / VOLTAGE |
| Minimum delays (hold) | Fast model (`trce -sphld m`), reported through `MAXDELAY … MIN 0 ns` on the /SLAVEn paths | TRACE command line, LPF |
| Output loading | **15 pF on every output** (`OUTPUT ALLPORTS LOAD`; Diamond default 0 pF). Actual loads: SN74LVC8T245 A port 8.5 pF typ [V S53]; SN74LVC32A input 5 pF [V S55]; LVCH16T245 DIR 4–5 pF × 2 [V S46]; plus trace and pad | LPF |
| I/O standard | LVCMOS33, 8 mA; FAST slew on ZF_SLAVE_N, ZF_XRDY, ZF_DBUF_OE_N | LPF |
| Edges | TRACE times both rising and falling transitions of every constrained path; the worst is reported | TRACE |

## 2. Results (all 27 constraints met; 0 setup errors, 0 hold errors, both grades)

| Path (FPGA pin to pin) | Commercial max | Industrial max | Allocation | Worst slack | Minimum (C / I) |
|---|---|---|---|---|---|
| ZB_AS_N → ZF_SLAVE_N | 8.369 | **8.840** | 18 | 9.160 | 2.581 / **2.479** |
| ZB_A[23:16] → ZF_SLAVE_N (worst: A16) | **14.054** | **14.193** | 18 | 3.807 | 3.181 / **2.920** (A20) |
| ZB_AS_N → ZF_XRDY | 9.101 | 9.064 | 18 | 8.899 | – |
| ZB_BERR_N → ZF_XRDY | 8.941 | 11.223 | 18 | 6.777 | – |
| ZB_A[23:16] → ZF_XRDY (worst: A16) | **14.786** | 14.277 | 18 | **3.214** | – |
| ZB_AS_N → ZF_DBUF_OE_N | 9.255 | 9.439 | 18 | 8.561 | – |
| ZB_BERR_N → ZF_DBUF_OE_N | 9.510 | 9.594 | 18 | 8.406 | – |
| ZB_DOE / ZB_READ → ZF_DBUF_OE_N | 11.788 / 11.434 | 10.965 / 10.979 | 18 | 6.212 | – |
| ZB_UDS_N / ZB_LDS_N → ZF_DBUF_OE_N | 12.108 / 12.322 | 12.516 / 12.784 | 18 | 5.216 | – |
| ZB_CFGIN_N → ZF_CFGOUT_N | 10.921 | 9.265 | 25 | 14.079 | – |
| clk_core (50 MHz) worst register path | 12.796 | 12.991 | 20 | 6.726 | – |

All values in ns. The worst path overall is A16 → ZF_XRDY at 14.786 ns, which leaves **3.2 ns** of the 18 ns allocation.

## 3. Board-level budgets with the STA values

Built from the worst FPGA figure of either grade and the datasheet maxima ([sheet1-timing-budget.md](sheet1-timing-budget.md)):

| Budget | Total | Limit | Margin |
|---|---|---|---|
| /AS → /SLAVEn, assertion and negation: 0.3 + 4.1 + 0.5 + **8.84** + 0.5 + 4.4 + 2.0 | **20.6 ns** | 35 / 50 ns | **14.4 / 29.4 ns** |
| /AS → XRDY negated: 5.1 + **9.10** + 3.8 + 4.1 + 2.0 | **24.1 ns** | 60 ns | **35.9 ns** |
| Data-buffer release, worst input (LDS): 5.1 + **12.78** + 3.8 + 6.3 | **28.0 ns** | #29A 187 ns; RMW ≥ 431 ns | ≥ 159 ns |

## 4. Hazard inequality with STA delays (C-02)

From [sheet1-hazard-analysis.md](sheet1-hazard-analysis.md) §4.2. The buffer skew term is 3.5 ns (LVC16244A 4.1 − 1.1 ns, plus 0.5 ns of trace).

| Requirement | Conservative: slow maximum − fast minimum | Same corner (slow) |
|---|---|---|
| **Slot address setup S_req** | 3.5 + (14.193 − 2.479) = **15.2 ns** | 3.5 + (14.193 − 8.840) = **8.9 ns** (C: 9.2 ns) |
| Slot address hold | 3.5 + (8.840 − 2.920) = **9.4 ns** | – |

- **Which bound applies.** Both paths sit on one die at one temperature and voltage, so the same-corner bound is the realistic one. The conservative bound also covers on-chip variation and the model's corners being far apart.
- **Pass criterion for M-7.** Measured slot setup ≥ **18.2 ns** (conservative S_req + 3 ns). A result between 12.2 and 18.2 ns is acceptable only on the same-corner basis and must be recorded as such. Hold needs ≤ 9.4 ns, against the 68000's ≥ 40 ns (#13) [V S57].
- **Slowest bits.** A16–A18 are the slowest (they carry the mode-B mask). Placement (O1) or the predecode options (O3) shorten them if M-7 shows less margin than needed.
- **Model check.** The gate-level model corner (tb_hazard E3, 11.0 ns) lies between the two STA bounds.

## 5. Structure on Diamond's own netlist (C-02 S1/S2)

`python -I hdl/syn/check_diamond_gates.py impl1/z2_sta_impl1_mapvo.vo` → **ALL PASS** for both grades.

| Check | Result |
|---|---|
| Gate LUTs (LSE kept the hierarchy names) | z2_asgate2 → ZF_SLAVE_N, init `16'hBBBB` (inputs /AS, select). z2_asgate3 → ZF_XRDY, `16'hFF7F` (LSE merged the `sel_k & hold_q` AND into it). z2_asgate3 → ZF_DBUF_OE_N, `16'hF7F7` |
| Controlling input | Each LUT outputs 1 for every input combination with /AS negated; the asgate3 LUTs also with /BERR asserted |
| Fan-out of the /AS and /BERR pads | Only those LUTs and one synchroniser flip-flop each |

## 6. Warnings reviewed

| Warning | Assessment |
|---|---|
| Initial value ignored on `ld_dout[15:0]` | Benign: probably packed into I/O registers, and always loaded before LD is driven |
| ZB_E7M unused / IO buffer missing | Expected: E7M is a monitor input with no Stage 2 load. Its IOBUF preference is commented out |
| `VCC_net` / `GND_net` of the asgate instances have no load | Artefact of the preserved hierarchy |
| "No user .sdc file" | LSE uses the LPF for place and route |

## 7. What remains for G-STA

1. Repeat with the **sheet-2 pin assignment**, every limit still met, worst slack recorded.
2. Re-derive §4 with the final numbers.
3. Compare with M-1, M-2 and M-7 on hardware (after G-PSU).
