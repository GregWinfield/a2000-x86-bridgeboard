# HDL: Zorro II interface (Stage 2)

Original HDL for the bridgeboard FPGA (Lattice LCMXO2-2000HC-4TG144C). **Licence: MIT** (D-13); every file carries an SPDX header. Specification: [../docs/hdl/zorro-interface-spec.md](../docs/hdl/zorro-interface-spec.md). Requirement-to-evidence map: [../docs/hdl/verification-matrix.md](../docs/hdl/verification-matrix.md).

> **Status (2026-11-18): `run_checks.sh` → ALL HDL CHECKS PASSED** (gate G-SIM; [../docs/hdl/verification-results.md](../docs/hdl/verification-results.md)). Post-place-and-route timing needs Lattice Diamond (gate G-STA).

## Layout

| Path | Contents |
|---|---|
| `rtl/` | Synthesisable RTL: `z2_top` (pins, POR) → `z2_core` (synchronisers, arming, AutoConfig, bus FSM, registers, watchdog, formal properties) → `z2_decode` (combinational select) → `z2_asgate*` (single-LUT /AS gates), `z2_sync` |
| `sim/` | Testbenches: `tb_z2` (bus-functional, sheet-1 board models), `tb_chain` (three-slot AutoConfig chain), `tb_hazard` (gate-level random-delay decode test); `z2_master` (68000 / A2000 bus model); `card_sheet1` (sheet-1 circuit around the RTL); `models/` (part models with datasheet delays, random-delay LUT) |
| `syn/` | `z2_top.lpf` (Diamond constraints), `diamond_sta.tcl` (G-STA flow), `synth_decode.ys` + `check_decode_structure.py` (C-02 netlist check), `synth_xo2.ys` (open-source resource estimate) |
| `formal/` | `z2_core.sby` (SymbiYosys: prove, bmc, cover) |
| `run_checks.sh` | Runs everything; fails on any `ASSERT-FAIL` |

## Running the checks

Needs the [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) (Icarus Verilog, Yosys, SymbiYosys, Yices) and Python 3. From Git Bash on Windows:

```sh
OSS_CAD_SUITE=/c/Users/<you>/AppData/Local/oss-cad-suite-20261031/oss-cad-suite bash hdl/run_checks.sh
bash hdl/run_checks.sh quick      # one seed, no formal
```

Logs go to `hdl/build/log/` (not committed). Delay-corner runs use `-DDLY_MODE=1` (all maxima) or `2` (all minima). `-P tb_z2.FPGA_TMAX=7.24` uses the FPGA datasheet floor instead of the 18 ns allocation.

## Model assumptions (read before trusting a pass)

- The board models use TI datasheet min/max delays (sources S45–S56). FPGA pin-to-pin delay is modelled as 3–18 ns [A] until G-STA provides real values.
- The A2000 is modelled at the slot from MC68000 timing (S57) plus assumptions [A] for DOE, buffer skew and automatic DTACK. They are listed in `sim/z2_master.v`. Measurements M-3, M-7 and M-10 replace them.
- The simulation hook `z2_core.stall_test` is a constant-0 wire in synthesis. The testbench forces it to exercise the watchdog.
