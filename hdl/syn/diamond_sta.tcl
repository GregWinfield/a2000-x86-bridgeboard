# SPDX-License-Identifier: MIT
# Lattice Diamond batch flow for gate G-STA (C-01): LSE synthesis, map, place & route and TRACE
# timing analysis of z2_top on LCMXO2-4000HC-4TG144C (C-30) with hdl/syn/z2_top.lpf.
# Commands follow the Diamond 3.14 "Diamond Project Tcl Commands" reference.
#
# Run from an empty work directory (the project is created in the current directory):
# Normally run through hdl/syn/run_diamond.sh, which copies the sources to a space-free directory and
# sets LM_LICENSE_FILE for the process (pnmainc.exe <this script>, from the work directory).
#
# Outputs (work directory): impl1/z2_sta_impl1.twr (TRACE: MAXDELAY setup and MIN/hold results),
# impl1/z2_sta_impl1_mapvo.vo (post-map netlist: hdl/syn/check_diamond_gates.py), map/par reports.
set here [file dirname [file normalize [info script]]]
set rtl  [file normalize "$here/../rtl"]

file copy -force "$here/z2_top.lpf" [file join [pwd] z2_sta.lpf]
# Device: default LCMXO2-4000HC commercial -4 (C-30); set Z2_DEV=LCMXO2-4000HC-4TG144I for the industrial grade.
set dev [expr {[info exists ::env(Z2_DEV)] ? $::env(Z2_DEV) : "LCMXO2-4000HC-4TG144C"}]
puts "G-STA device: $dev"
prj_project new -name z2_sta -impl impl1 -dev $dev -lpf z2_sta.lpf
prj_syn set lse
foreach f {z2_sync.v z2_asgate.v z2_decode.v z2_core.v z2_lbus.v z2_mbx.v z2_afifo.v z2_spi_slave.v z2_hostif.v z2_top.v} {
    prj_src add [file join $rtl $f]
}
# Top level: z2_top (default), or Z2_TOP=fit_top / fit_top_rc for the pin-budget fit test
# (both modules are in hdl/syn/fit_top.v).
set top [expr {[info exists ::env(Z2_TOP)] ? $::env(Z2_TOP) : "z2_top"}]
if {$top ne "z2_top"} { prj_src add [file join $here "fit_top.v"] }
prj_impl option top $top
prj_project save

prj_run Synthesis -impl impl1
prj_run Translate -impl impl1
prj_run Map       -impl impl1
prj_run Map       -impl impl1 -task MapVerilogSimFile
prj_run PAR       -impl impl1
prj_run PAR       -impl impl1 -task PARTrace
prj_project save
prj_project close
puts "G-STA flow complete: see impl1/z2_sta_impl1.twr"
