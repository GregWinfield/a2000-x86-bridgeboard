# HDL: Zorro II interface (Stage 2)

Original HDL for the bridgeboard FPGA (Lattice LCMXO2-2000HC-4TG144C). **Licence: MIT** (D-13); every file carries an SPDX header. Specification: [../docs/hdl/zorro-interface-spec.md](../docs/hdl/zorro-interface-spec.md). Requirement-to-evidence map: [../docs/hdl/verification-matrix.md](../docs/hdl/verification-matrix.md).

> **Status (2026-11-19): `run_checks.sh` → ALL HDL CHECKS PASSED** for Stages 2–4 (39 testbench runs, 9 formal tasks; [../docs/hdl/verification-results.md](../docs/hdl/verification-results.md) §5.8). Diamond STA at the frozen pins: every constraint met on the **LCMXO2-4000HC**. With the sheet-4 host link the design **no longer fits the 2000HC** (1090 of 1056 slices): decision C-30 is the owner's ([../docs/stage2/sheet4-sta-results.md](../docs/stage2/sheet4-sta-results.md)).

## Layout

| Path | Contents |
|---|---|
| `rtl/` | Synthesisable RTL: `z2_top` (pins, POR) → `z2_core` (synchronisers, arming, AutoConfig, bus FSM, registers, watchdog, formal properties) → `z2_decode` (combinational select) → `z2_asgate*` (single-LUT /AS gates), `z2_sync`. Stage 3: `z2_lbus` (local-bus arbiter, SRAM sequencer: who may access the memory), `z2_mbx` (queues and interrupts: who has work to do). Stage 4: `z2_spi_slave` (SCK domain: mode-0 receive and transmit; parameter `LAUNCH_RISE`) → `z2_afifo` (Gray-pointer async FIFO) → `z2_hostif` (protocol engine on the host port, [../docs/hdl/host-link-protocol.md](../docs/hdl/host-link-protocol.md)). The early-launch build (MISO on SCK rising, the 20 MHz option) is selected with `-DZ2_LAUNCH_RISE` |
| `sim/` | Testbenches: `tb_z2` (bus-functional, sheet-1 board models), `tb_chain` (three-slot AutoConfig chain), `tb_hazard` (gate-level random-delay decode test); `z2_master` (68000 / A2000 bus model); `card_model` (sheet-1 and sheet-3 circuits around the RTL); `tb_shm` (sheet 3: SRAM windows, coherence, determinism, TAS atomicity, queues, link reset, FPGA reload); `models/` (part models with datasheet delays, random-delay LUT, ISSI SRAM with AC-limit checks, clock-level host-port model `z2_hostif_bfm`, PL022-like SPI master `spi_master_bfm`). Stage 4: `tb_spi` (protocol at the pins, P0–P16); tb_shm and tb_z2 also run through the real SPI link |
| `syn/` | `z2_top.lpf` (Diamond constraints), `diamond_sta.tcl` (G-STA flow), `synth_decode.ys` + `check_decode_structure.py` (C-02 netlist check), `synth_xo2.ys` (open-source resource estimate), `fit_top.v` (pin-budget fit test, 101 signals since C-26: `Z2_TOP=fit_top`) |
| `formal/` | `z2_core.sby` (SymbiYosys: prove, bmc, cover); `fv_shm.sby` + `fv_shm.v` (Stage 3 shared-memory subsystem with every input free: prove, bmc 64, cover; z2_mbx M1–M7); `fv_afifo.sby` + `fv_afifo.v` (Stage 4 async FIFO, multiclock: independent free clocks, arbitrary reset) |
| `run_checks.sh` | Runs everything; fails on any `ASSERT-FAIL` |

## Running the checks

Needs the [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) (Icarus Verilog, Yosys, SymbiYosys, Yices) and Python 3. From Git Bash on Windows:

```sh
OSS_CAD_SUITE=/c/Users/<you>/AppData/Local/oss-cad-suite-20261031/oss-cad-suite bash hdl/run_checks.sh
bash hdl/run_checks.sh quick      # one seed, no formal
```

Logs go to `hdl/build/log/` (not committed). Delay-corner runs use `-DDLY_MODE=1` (all maxima) or `2` (all minima). `-P tb_z2.FPGA_TMAX=7.24` uses the FPGA datasheet floor instead of the 18 ns allocation.

## Gate G-STA: Lattice Diamond (owner's machine)

MachXO2 is supported by **Lattice Diamond only**; Lattice Radiant does not support MachXO2. Per the Lattice licensing matrix, the **free** Diamond licence covers MachXO2. Source pages: `https://www.latticesemi.com/diamond` and `https://www.latticesemi.com/Support/Licensing` (read 2026-11-18).

1. Sign in to, or create, a Lattice account at latticesemi.com.
2. Download **Diamond 3.14 64-bit for Windows** (about 1.6 GB; Windows 10/11 64-bit) from the Diamond page.
3. Request the free **node-locked** licence: Diamond page → "Request Node-locked License" → Lattice licensing portal. It asks for the PC's **Ethernet MAC address**. `getmac /v` in a Command Prompt lists it: twelve hex digits of a physical adapter. The licence is annual and must be regenerated after a year.
4. Run the installer and give it the licence file when asked. Lattice: "place the .lic file in the directory specified during installation". On this project's PC the file is `C:\lscc\diamond\3.14\license\FNP License-LicenseFile.lic`, and **`LM_LICENSE_FILE` was not set** by the installer.
5. From Git Bash, run `bash hdl/syn/run_diamond.sh <space-free work dir> [LCMXO2-2000HC-4TG144C|…I]`. It sets `LM_LICENSE_FILE` for the run only, then copies the sources to the work directory, because Lattice tools mishandle spaces in paths. It runs `diamond_sta.tcl` through `pnmainc.exe` and prints the `twr_summary.py` table.
6. Check the final-gate structure on Diamond's netlist with `python -I hdl/syn/check_diamond_gates.py <work>/work/impl1/z2_sta_impl1_mapvo.vo`.
7. Record the results in `docs/stage2/sheet1-sta-results.md`.

**Status.** The exploratory run of 2026-11-19 passes every constraint at both grades with 15 pF loads: worst **15.31 ns** against 18 ns ([../docs/stage2/sheet1-sta-results.md](../docs/stage2/sheet1-sta-results.md)). These figures come from the same-day **corrected** run. The first run analysed the address inputs as LVCMOS25 because the LPF set IO_TYPE only on some ports. `run_diamond.sh` now fails if any port is not LVCMOS33 or any bank is not at 3.3 V.

**Until sheet 2 fixes the FPGA pinout**, Diamond places the I/O itself. That run is exploratory: it shows the 18 ns allocation is realistic. Gate G-STA proper needs the final pin assignment.

## Model assumptions (read before trusting a pass)

- The board models use TI datasheet min/max delays (sources S45–S56). FPGA pin-to-pin delay is modelled as 3–18 ns [A] until G-STA provides real values.
- The A2000 is modelled at the slot from MC68000 timing (S57) plus assumptions [A] for DOE, buffer skew and automatic DTACK. They are listed in `sim/z2_master.v`. Measurements M-3, M-7 and M-10 replace them.
- The simulation hook `z2_core.stall_test` is a constant-0 wire in synthesis. The testbench forces it to exercise the watchdog.
- `-DHOST_BFM` compiles the clock-level host model `z2_hostif_bfm` in place of the real `z2_hostif` (the stub is gone since Stage 4). It issues host transactions at clock level (any phase, back to back), a worse case than any real SPI rate, so the arbiter stress runs keep it. Every other run uses the real SPI slave, driven through translator and ribbon delays (card_model `SPI_TIN` 3.8 ns, `SPI_TOUT` 3.9 ns, FPGA SCK→MISO 15.4 ns ≥ the Diamond worst). The SRAM model checks every access against the ISSI −10 AC limits.
