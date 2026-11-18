// SPDX-License-Identifier: MIT
// Final /AS-gating stages of the Zorro-visible combinational outputs.
//
// Each module must map to exactly ONE LUT. They are separate, kept hierarchy so
// that synthesis cannot merge /AS (or /BERR) into the address-decode cone:
//
//     out_n = as_n | ~term                (z2_asgate2: /SLAVEn)
//     out_n = as_n | ~berr_n | ~term      (z2_asgate3: XRDY, data-buffer enable)
//
// While as_n = 1 (or berr_n = 0) the LUT output is 1 for every value of `term`, so
// glitches on the decode cone cannot reach the pin between bus cycles. The netlist
// check hdl/syn/check_decode_structure.py verifies this after synthesis.
// See docs/stage2/sheet1-hazard-analysis.md.
`default_nettype none

(* keep_hierarchy *)
module z2_asgate2 (
    input  wire as_n,
    input  wire term,
    output wire out_n
) /* synthesis syn_hier = "hard" */;
    assign out_n = as_n | ~term;
endmodule

(* keep_hierarchy *)
module z2_asgate3 (
    input  wire as_n,
    input  wire berr_n,
    input  wire term,
    output wire out_n
) /* synthesis syn_hier = "hard" */;
    assign out_n = as_n | ~berr_n | ~term;
endmodule

`default_nettype wire
