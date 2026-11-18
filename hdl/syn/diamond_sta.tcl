# SPDX-License-Identifier: MIT
# Lattice Diamond batch flow for gate G-STA (C-01): synthesis (LSE), map, place & route and
# TRACE timing analysis of z2_top on LCMXO2-2000HC-4TG144C with hdl/syn/z2_top.lpf.
#
#   cd hdl/syn ; pnmainc diamond_sta.tcl          (Diamond Tcl console, Windows)
#
# Status: written against the Diamond Tcl command reference [K]; NOT yet run (Diamond is not
# installed on the development machine). Check every command on the first run.
#
# What the run must report (docs/stage2/sheet1-timing-budget.md, section 3):
#   * every MAXDELAY path in z2_top.lpf, worst case (slow corner: TJ max, VCC min, -4 grade)
#   * the MINIMUM delay of ZB_AS_N -> ZF_SLAVE_N and ZB_A[16..23] -> ZF_SLAVE_N (fast corner /
#     hold analysis) for the address-setup inequality of the hazard analysis
#   * the TRACE header (performance grade, voltage, temperature) copied into the record
#   * the post-map netlist check that each z2_asgate* instance is a single LUT
set here [file dirname [file normalize [info script]]]
set rtl  [file normalize "$here/../rtl"]

prj_project new -name "z2_sta" -impl "impl1" -dev LCMXO2-2000HC-4TG144C \
    -lpf "$here/z2_top.lpf" -synthesis "lse"
foreach f {z2_sync.v z2_asgate.v z2_decode.v z2_core.v z2_top.v} {
    prj_src add "$rtl/$f"
}
prj_impl option top "z2_top"
prj_run Synthesis -impl impl1
prj_run Translate -impl impl1
prj_run Map       -impl impl1
prj_run PAR       -impl impl1
prj_run PAR       -impl impl1 -task PARTrace
prj_project save
prj_project close
puts "G-STA: open impl1/z2_sta_impl1.twr (setup) and the hold/min report; fill in the timing budget."
