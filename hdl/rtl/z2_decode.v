// SPDX-License-Identifier: MIT
// Combinational Zorro II select and output gating. NO clock in any path.
//
// Structure (docs/stage2/sheet1-hazard-analysis.md):
//  * sel_k is a function of address bits A23..A16 and REGISTERED state only
//    (match_en, cmp, care_lo). The registered state is frozen while a bus cycle is
//    in progress (z2_core), so sel_k can only change while the address changes.
//  * Every Zorro-visible output is produced by one final gate (z2_asgate*) in which
//    /AS (and /BERR for the buffer enable and XRDY) is the controlling input.
//  * oe_term is positive-unate in every asynchronous input (READ, DOE, strobes), and
//    the registered dir_q makes the read and write terms mutually exclusive.
//
// Timing: AS_N -> slave_n / xrdy / dbuf_oe_n and A23..A16 -> slave_n are the
// MAXDELAY-constrained paths (hdl/syn/z2_top.lpf, gate G-STA).
`default_nettype none
module z2_decode (
    input  wire [23:16] a_hi,      // ZB_A23..ZB_A16 (buffered, asynchronous)
    input  wire         as_n,      // ZB_AS_N
    input  wire         berr_n,    // ZB_BERR_N
    input  wire         rd,        // ZB_READ (1 = read)
    input  wire         doe,       // ZB_DOE
    input  wire         uds_n,     // ZB_UDS_N
    input  wire         lds_n,     // ZB_LDS_N
    // registered state, frozen during a bus cycle
    input  wire         match_en,  // armed and (AutoConfig-eligible or configured)
    input  wire [23:16] cmp,       // $E8 while unconfigured, base[23:16] once configured
    input  wire         care_lo,   // 0 = ignore A18..A16 (512 KB window)
    input  wire         hold_q,    // XRDY wait wanted for the current data phase
    input  wire         oe_rd_q,   // read-data drive permitted
    input  wire         oe_wr_q,   // write-data capture permitted
    input  wire         dir_q,     // transceiver direction, 1 = A->B (card drives Zorro)
    output wire         sel,       // combinational select (sampled by z2_core)
    output wire         slave_n,   // -> ZF_SLAVE_N (0 = /SLAVEn asserted)
    output wire         xrdy,      // -> ZF_XRDY    (0 = hold off DTACK, 1 = released)
    output wire         dbuf_oe_n  // -> ZF_DBUF_OE_N (0 = transceiver enabled)
);
    wire hi_match = (a_hi[23:19] == cmp[23:19]);
    wire lo_match = ~care_lo | (a_hi[18:16] == cmp[18:16]);

    (* keep *) wire sel_k     /* synthesis syn_keep = 1 */;
    (* keep *) wire xrdy_term /* synthesis syn_keep = 1 */;
    (* keep *) wire oe_term   /* synthesis syn_keep = 1 */;

    assign sel_k     = match_en & hi_match & lo_match;
    assign xrdy_term = sel_k & hold_q;
    // Read term: Haynie's A2000 notes require the data strobes to qualify read-data
    // buffers "in case the cycle actually turns out to be a read-modify-write cycle".
    assign oe_term   = sel_k & ( (oe_rd_q &  dir_q &  rd & doe & ~(uds_n & lds_n))
                               | (oe_wr_q & ~dir_q & ~rd) );
    assign sel       = sel_k;

    z2_asgate2 u_g_slave (.as_n(as_n),                   .term(sel_k),     .out_n(slave_n));
    z2_asgate3 u_g_xrdy  (.as_n(as_n), .berr_n(berr_n), .term(xrdy_term), .out_n(xrdy));
    z2_asgate3 u_g_oe    (.as_n(as_n), .berr_n(berr_n), .term(oe_term),   .out_n(dbuf_oe_n));
endmodule
`default_nettype wire
