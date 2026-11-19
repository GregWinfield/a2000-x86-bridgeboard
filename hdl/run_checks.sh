#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Runs every Stage 2 and Stage 3 HDL verification step and fails on any "ASSERT-FAIL" or failing tool.
# Needs the OSS CAD Suite tools on PATH (iverilog, vvp, yosys, sby, yices), or set
# OSS_CAD_SUITE to its install directory. Python 3 runs the netlist structure check.
#   bash hdl/run_checks.sh            # everything
#   bash hdl/run_checks.sh quick      # one seed, no formal
set -u
cd "$(dirname "$0")"
if [ -n "${OSS_CAD_SUITE:-}" ]; then export PATH="$OSS_CAD_SUITE/bin:$OSS_CAD_SUITE/lib:$PATH"; fi
PY=${PYTHON:-python}
mkdir -p build/log
status=0

run() {                                   # run <name> <command...>
    local name="$1"; shift
    echo "== $name"
    if ! "$@" > "build/log/$name.log" 2>&1; then echo "   command failed (see build/log/$name.log)"; status=1; fi
    if grep -q "ASSERT-FAIL" "build/log/$name.log"; then
        echo "   ASSERT-FAIL lines:"; grep -m 12 "ASSERT-FAIL" "build/log/$name.log" | sed 's/^/     /'; status=1
    fi
    grep -E "TB_RESULT|characterisation|^E1|^E2|^S3 |^S9 |^S11 |host transfers|^PASS:|^FAIL:|^INFO:|ALL PASS|FAILURE|scenario|DONE|PASS|FAIL" \
        "build/log/$name.log" | grep -v "ASSERT-FAIL" | sed 's/^/   /' | head -40
}

MODELS="sim/models/board_models.v sim/models/sram_is61wv25616.v sim/models/hostif_bfm.v sim/models/spi_master_bfm.v sim/z2_master.v sim/card_model.v"
# Simulation uses the host-port bus-functional model (sim/models/hostif_bfm.v) in place of the
# RTL stub; lint and synthesis use the stub (the sheet-4 SPI slave replaces it).
RTL="rtl/z2_sync.v rtl/z2_asgate.v rtl/z2_decode.v rtl/z2_core.v rtl/z2_lbus.v rtl/z2_mbx.v rtl/z2_afifo.v rtl/z2_spi_slave.v rtl/z2_hostif.v rtl/z2_top.v"
RTL_SYN="$RTL"
SEEDS="1 2 3 4"
[ "${1:-}" = "quick" ] && SEEDS="1"

# 1. lint (RTL alone)
run lint iverilog -g2005 -Wall -Wno-timescale -o build/lint.vvp $RTL_SYN

# 2. bus-functional testbench: random skew seeds, then all-maximum and all-minimum delay corners,
#    with the 18 ns FPGA allocation and with the 7.24 ns datasheet floor
for seed in $SEEDS; do
    run "tb_z2_rand_s$seed" sh -c "iverilog -g2005 -Wno-timescale -P tb_z2.SEED=$seed -o build/tb_z2_r$seed.vvp $MODELS sim/tb_z2.v $RTL && vvp -n build/tb_z2_r$seed.vvp"
done
for mode in 1 2; do
    for tmax in 18.0 7.24; do
        run "tb_z2_corner${mode}_fpga${tmax}" sh -c "iverilog -g2005 -Wno-timescale -DDLY_MODE=$mode -P tb_z2.FPGA_TMAX=$tmax -o build/tb_z2_c$mode.vvp $MODELS sim/tb_z2.v $RTL && vvp -n build/tb_z2_c$mode.vvp"
    done
done

# 2b. Stage 3: the same bus-functional tests with continuous random host (SPI-side) SRAM traffic.
#     Every Zorro check must still pass: arbitration may not disturb a Zorro cycle.
for seed in $SEEDS; do
    run "tb_z2_hostbg_s$seed" sh -c "iverilog -g2005 -Wno-timescale -DHOST_BG -DHOST_BFM -P tb_z2.SEED=$seed -o build/tb_z2_h$seed.vvp $MODELS sim/tb_z2.v $RTL && vvp -n build/tb_z2_h$seed.vvp"
done

# 2c. Stage 3: shared SRAM, arbitration, determinism, queues and interrupts (sheet 3)
for seed in $SEEDS; do
    run "tb_shm_s$seed" sh -c "iverilog -g2005 -Wno-timescale -DHOST_BFM -P tb_shm.SEED=$seed -o build/tb_shm_$seed.vvp $MODELS sim/tb_shm.v $RTL && vvp -n build/tb_shm_$seed.vvp"
done
for mode in 1 2; do
    run "tb_shm_corner$mode" sh -c "iverilog -g2005 -Wno-timescale -DHOST_BFM -DDLY_MODE=$mode -o build/tb_shm_c$mode.vvp $MODELS sim/tb_shm.v $RTL && vvp -n build/tb_shm_c$mode.vvp"
done

# 2d. Stage 4 (sheet 4): the REAL SPI slave. tb_spi: protocol, vectors, errors, power and reset
#     events, random SCK/skew sweep, standard launch at <= 10 MHz and early launch at <= 20 MHz.
#     HL-5: tb_shm through the SPI slave. HL-6: tb_z2 with continuous SPI background traffic.
for seed in $SEEDS; do
    run "tb_spi_s$seed" sh -c "iverilog -g2005 -Wno-timescale -P tb_spi.SEED=$seed -o build/tb_spi_$seed.vvp $MODELS sim/tb_spi.v $RTL && vvp -n build/tb_spi_$seed.vvp"
    run "tb_spi_rise_s$seed" sh -c "iverilog -g2005 -Wno-timescale -DZ2_LAUNCH_RISE=1 -P tb_spi.SEED=$seed -P tb_spi.LAUNCH_RISE=1 -P tb_spi.HALF_MIN=25.0 -o build/tb_spi_r$seed.vvp $MODELS sim/tb_spi.v $RTL && vvp -n build/tb_spi_r$seed.vvp"
    run "tb_shm_spi_s$seed" sh -c "iverilog -g2005 -Wno-timescale -P tb_shm.SEED=$seed -o build/tb_shm_spi_$seed.vvp $MODELS sim/tb_shm.v $RTL && vvp -n build/tb_shm_spi_$seed.vvp"
    run "tb_z2_spibg_s$seed" sh -c "iverilog -g2005 -Wno-timescale -DHOST_BG -P tb_z2.SEED=$seed -o build/tb_z2_sb$seed.vvp $MODELS sim/tb_z2.v $RTL && vvp -n build/tb_z2_sb$seed.vvp"
done

# 3. AutoConfig chain: normal, unpowered, startup and fault scenarios
for seed in $SEEDS; do
    run "tb_chain_s$seed" sh -c "iverilog -g2005 -Wno-timescale -P tb_chain.SEED=$seed -o build/tb_chain_$seed.vvp $MODELS sim/tb_chain.v $RTL && vvp -n build/tb_chain_$seed.vvp"
done

# 4. decode synthesis, structural hazard check, gate-level random-delay hazard simulation
run synth_decode yosys -q -s syn/synth_decode.ys
run structure "$PY" -I syn/check_decode_structure.py build/decode_lut.json
run tb_hazard sh -c "iverilog -g2005 -Wno-timescale -o build/tb_hazard.vvp sim/models/lut_rand.v sim/tb_hazard.v build/decode_lut.v && vvp -n build/tb_hazard.vvp"

# 5. formal proof / BMC / cover (SymbiYosys)
if [ "${1:-}" != "quick" ]; then
    run formal sh -c "cd formal && sby -f z2_core.sby"
    run formal_shm sh -c "cd formal && sby -f fv_shm.sby"       # Stage 3: X1-X6, M1-M5 (prove, bmc 64, cover)
    run formal_afifo sh -c "cd formal && sby -f fv_afifo.sby"   # Stage 4: async FIFO, free clocks (prove, bmc 60, cover)
fi

# 6. open-source MachXO2 synthesis: resources and logic depth (not timing sign-off)
run synth_xo2 yosys -q -s syn/synth_xo2.ys

echo
[ $status -eq 0 ] && echo "ALL HDL CHECKS PASSED" || echo "HDL CHECKS FAILED"
exit $status
