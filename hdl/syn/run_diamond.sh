#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Run the Diamond G-STA flow (diamond_sta.tcl) in a space-free work directory and summarise
# the TRACE report. Lattice tools are not reliable with spaces in paths, so the RTL, LPF and
# script are copied to WORK first.
#   bash hdl/syn/run_diamond.sh [WORK_DIR] [DEVICE]
#   DIAMOND (default C:/lscc/diamond/3.14), LM_LICENSE_FILE (default: the .lic in DIAMOND/license)
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-${TMPDIR:-/tmp}/z2_diamond}"
DEV="${2:-LCMXO2-2000HC-4TG144C}"
DIAMOND="${DIAMOND:-/c/lscc/diamond/3.14}"
if [ -z "${LM_LICENSE_FILE:-}" ]; then
    LM_LICENSE_FILE="$(ls "$DIAMOND"/license/*.lic | head -1)"
fi
export LM_LICENSE_FILE
export Z2_DEV="$DEV"
export Z2_TOP="${Z2_TOP:-z2_top}"   # pin-budget fit test: Z2_TOP=fit_top or fit_top_rc
rm -rf "$WORK" && mkdir -p "$WORK/rtl" "$WORK/syn" "$WORK/work"
cp "$HERE"/../rtl/*.v "$WORK/rtl/"
cp "$HERE/z2_top.lpf" "$HERE/diamond_sta.tcl" "$HERE"/*.v "$WORK/syn/"
# fit_top has no ZF_OVR_N / ZF_DTACK_N ports; an IOBUF on a missing port is a Diamond error
if [ "$Z2_TOP" = "fit_top" ]; then sed -i '/"ZF_OVR_N"\|"ZF_DTACK_N"/d' "$WORK/syn/z2_top.lpf"; fi
( cd "$WORK/work" && "$DIAMOND/bin/nt64/pnmainc.exe" ../syn/diamond_sta.tcl > ../pnmainc.log 2>&1 )
grep -E "^(ERROR|WARNING) -" "$WORK/pnmainc.log" | sort | uniq -c | sort -rn | head -20 || true
# I/O-standard check (added 2026-11-19 after the first exploratory run analysed unconstrained ports as
# LVCMOS25): every placed port must be LVCMOS33 and every used bank must be at VCCIO 3.3 V.
PAD="$WORK/work/impl1/z2_sta_impl1.pad"
BAD_IO=$(sed -n '/^Pinout by Port Name/,/^Vccio by Bank/p' "$PAD" | grep -E '^\| [A-Za-z_]' | grep -v 'Port Name' | grep -vc 'LVCMOS33' || true)
BAD_BANK=$(sed -n '/^Vccio by Bank/,/^Vref by Bank\|^Pinout by Pin Number/p' "$PAD" | grep -E '^\| [0-9]' | grep -vc '3\.3V' || true)
if [ "$BAD_IO" != "0" ] || [ "$BAD_BANK" != "0" ]; then
    echo "PAD CHECK FAIL: $BAD_IO port(s) not LVCMOS33, $BAD_BANK bank(s) not at 3.3 V (see $PAD)"
    exit 1
fi
echo "PAD CHECK PASS: all ports LVCMOS33, all used banks VCCIO 3.3 V"
"${PYTHON:-python}" -I "$HERE/twr_summary.py" "$WORK/work/impl1/z2_sta_impl1.twr"
