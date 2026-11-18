# Verification matrix: sheet 1 revision B and the Stage 2 HDL

**Status:** 2026-11-18. Every item below is **written**. **None has been executed yet.**
- The OSS CAD Suite (Icarus Verilog, Yosys, SymbiYosys, release 2026-10-31) is downloaded and SHA-256 checked, but has not been run (gate G-SIM).
- Lattice Diamond is not installed (gate G-STA).

"Pass criterion" is what the run must show before the item can be marked done. Test IDs refer to [../../hdl/sim/tb_z2.v](../../hdl/sim/tb_z2.v) (T*), [../../hdl/sim/tb_chain.v](../../hdl/sim/tb_chain.v) (S*), [../../hdl/sim/tb_hazard.v](../../hdl/sim/tb_hazard.v) (E*) and the formal properties in [../../hdl/rtl/z2_core.v](../../hdl/rtl/z2_core.v) (F*).

## C-01 /SLAVEn timing (owner: worst-case post-place-and-route STA, assertion and release, voltage, temperature, loading)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Entire combinational decode, /SLAVEn assertion and release | Diamond TRACE with [../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf), [../../hdl/syn/diamond_sta.tcl](../../hdl/syn/diamond_sta.tcl) | Every path ≤ 18 ns at the slow corner, both edges, 10 pF load; conditions printed in the report | **Pending:** Diamond and its licence |
| Budget closes with real buffer delays | [../stage2/sheet1-timing-budget.md](../stage2/sheet1-timing-budget.md) §2 | 29.8 ns ≤ 35 with the allocation; recomputed with STA | Budgeted, not proven |
| Simulation with the delay allocation | tb_z2 at FPGA_TMAX 18 and 7.24 ns, all-max/all-min corners (C5b, C5c) | No ASSERT-FAIL | Written |
| Shorter predecode if needed | Hazard analysis §6 (O1–O5) | Applied only if G-STA margin < 3 ns | Documented |

## C-02 Address stability and hazards (owner: late address, skew, transitions near /AS; no false /SLAVEn)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Structure: /AS only in the final gate; output inactive for /AS negated | `check_decode_structure.py` on the Yosys netlist; formal F4, F12 | ALL PASS; proof | Written |
| No assertion while /AS is negated, under any delay | tb_hazard E1 (random LUT and buffer delays) | 0 false assertions of /SLAVEn, XRDY, buffer enable | Written |
| Setup requirement quantified | tb_hazard E2 (setup sweep) + Diamond minimum/maximum delays + M-7 | Model S_req reported; STA S_req ≤ M-7 setup − 3 ns | Written / pending |
| RTL-level transitions near /AS, per-bit skew | tb_z2 T6 (setup 20/10/5 ns + 0–15 ns spread: pass/fail; 2/0/−5 ns: characterisation) | No false /SLAVEn (C5a), ≤ 35 ns (C5b), no glitch (C5d) | Written |
| Decode transient cannot enable the data drivers | Formal F1/F2; tb_z2 C2 | No failure | Written |

## C-03 AutoConfig bypass, unpowered carrier (owner: normal, unpowered, startup, faults)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Motherboard terminations | A2000 R6 schematic (S51) and Haynie (S52); M-8 on the target | ≈ 1 kΩ pull-down on /CFGOUTn, ≈ 1 kΩ pull-up on /SLAVEn | Verified on schematic; M-8 pending |
| Normal | tb_chain S1; tb_z2 T0–T3 | Chain order 11, 01, 33; card answers at its base | Written |
| Unpowered | tb_chain S2; tb_z2 T18 | Chain 11, 33; no collision | Written |
| Startup (blank FPGA, ramp, late power-good) | tb_chain S3, S4; tb_z2 T0 | Transparent until a reset with EN_OK; joins at the next reset | Written |
| Faults (FPGA reload, power loss, DIP, jumper, reset mid-scan, shut-up) | tb_chain S5–S10; tb_z2 T12–T17; C7 empty-slot checker | As in the design notes §6.4 | Written |
| Arming only inside a reset | Formal F10, F11 | Proof | Written |

## C-04 U104 output enable (owner: OE-controlled, power-good and reset qualified; /SLAVEn timing kept)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| OE gating by EN_OK · ZF_ARM | Schematic rev B; netlist audit (418 checks) | 0 failures | **Done** (audit run) |
| Timing budget recalculated | Timing budget §2, §8 | /SLAVEn 29.8 ns; OE not in the cycle path | Done (budget); STA pending |
| Hi-Z through the power ramp | Design notes §5; tb_z2 T0; M-6/M-9 | No assertion during the ramp | Written / pending |

## C-05 Data-buffer safety (owner: never enabled for an invalid cycle; no contention on direction change; DOE, /AS release, reset, wait states, bus errors)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| Never enabled for an invalid cycle | tb_z2 C2 (sampled every 0.5 ns, release allowance); formal F1/F2 | No failure; proof | Written |
| No contention on direction changes | U103 model "DIR changed while enabled"; card_sheet1 LD-contention monitor; tb_z2 C1; formal F5, F8, F9 | No failure; proof | Written |
| DOE assertion and release | tb_z2 T5 (DOE on 0/30/70/140 ns, off −30/0/+30 ns) | Data correct, no failure | Written |
| /AS release, aborted cycles | tb_z2 T8 (raw cycles, /AS 20–335 ns, arbitrary strobes and DOE) | No failure; next cycle correct | Written |
| Reset | tb_z2 T12 (/BUSRST during a driven read) | Release; AutoConfig again; SCRATCH preserved | Written |
| Wait states | tb_z2 `bus` check (≥ 1 wait when gated, 0 in zero-wait); C6a–C6d; T9 watchdog; T10 zero-wait | No failure | Written |
| Bus errors | tb_z2 T7 (/BERR during read, write, RMW); BERR_EVENTS | Release within the allowance; counter ≥ 4 | Written |

## C-13 Read-modify-write (owner: RMW, byte strobes, direction changes, OE, XRDY)

| Requirement | Evidence | Pass criterion | Status |
|---|---|---|---|
| RMW with /AS held | tb_z2 T4 (TAS even/odd byte × DOE continuous/split × motherboard data drive 0/30 ns), T5, T7, T10 | Correct read value and result, RMW_CYCLES = 8 after T4, no C1/C2/DIR failure | Written |
| Read drive ends at the read strobe (S7) | RTL read term; timing budget §4.1, §7 | ≥ 398 ns margin to S14 | Analysed |
| Per-phase XRDY | FSM ST_BETWN re-hold; formal F16 | XRDY held for the write portion; bounded | Written |
| Hardware confirmation | M-10 | B-port enable ends before READ falls | Pending (hardware) |

## Gates

| Gate | Condition | Status |
|---|---|---|
| **G-SIM** (new) | `bash hdl/run_checks.sh` prints `ALL HDL CHECKS PASSED`: lint, tb_z2 (4 seeds + 4 corner runs), tb_chain (4 seeds), structure check, tb_hazard E1 = 0, formal prove/bmc/cover | Pending: toolchain run |
| **G-STA** | Diamond, as in the timing budget §9 | Pending: Diamond |
| G-SHEET1 | Owner review of sheet 1 revision B | Pending |
