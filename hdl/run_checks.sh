#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Runs every Stage 2 HDL verification step and fails on any "ASSERT-FAIL" or failing tool.
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
    grep -E "TB_RESULT|characterisation|^E1|^E2|^PASS:|^FAIL:|^INFO:|ALL PASS|FAILURE|scenario|DONE|PASS|FAIL" \
        "build/log/$name.log" | grep -v "ASSERT-FAIL" | sed 's/^/   /' | head -40
}

MODELS="sim/models/board_models.v sim/z2_master.v sim/card_sheet1.v"
RTL="rtl/z2_sync.v rtl/z2_asgate.v rtl/z2_decode.v rtl/z2_core.v rtl/z2_top.v"
SEEDS="1 2 3 4"
[ "${1:-}" = "quick" ] && SEEDS="1"

# 1. lint (RTL alone)
run lint iverilog -g2005 -Wall -Wno-timescale -o build/lint.vvp $RTL

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
fi

# 6. open-source MachXO2 synthesis: resources and logic depth (not timing sign-off)
run synth_xo2 yosys -q -s syn/synth_xo2.ys

echo
[ $status -eq 0 ] && echo "ALL HDL CHECKS PASSED" || echo "HDL CHECKS FAILED"
exit $status
