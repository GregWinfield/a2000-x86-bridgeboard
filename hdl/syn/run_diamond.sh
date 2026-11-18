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
rm -rf "$WORK" && mkdir -p "$WORK/rtl" "$WORK/syn" "$WORK/work"
cp "$HERE"/../rtl/*.v "$WORK/rtl/"
cp "$HERE/z2_top.lpf" "$HERE/diamond_sta.tcl" "$WORK/syn/"
( cd "$WORK/work" && "$DIAMOND/bin/nt64/pnmainc.exe" ../syn/diamond_sta.tcl > ../pnmainc.log 2>&1 )
grep -E "^(ERROR|WARNING) -" "$WORK/pnmainc.log" | sort | uniq -c | sort -rn | head -20 || true
"${PYTHON:-python}" -I "$HERE/twr_summary.py" "$WORK/work/impl1/z2_sta_impl1.twr"
