// SPDX-License-Identifier: MIT
// C-02 hazard test on the SYNTHESISED decode (build/decode_lut.v from hdl/syn/synth_decode.ys),
// with a random transport delay on every LUT (models/lut_rand.v) and on every input buffer.
//
// E1  address activity while /AS is negated, including codes that pass through the selected
//     window: /SLAVEn, XRDY and the buffer enable must NEVER assert (structural property).
// E2  /AS asserted with setup s after the last address bit settles at the slot, moving from a
//     random previous address to an UNSELECTED one: count false /SLAVEn pulses per s.
//     The smallest s with zero failures, under these delay assumptions, is the model's
//     required slot address setup. It must be re-derived from Diamond min/max path delays (G-STA).
// Delay assumptions [A]: LUT incl. routing LUT_MIN..LUT_MAX; U101/U102 + traces BUF_MIN..BUF_MAX.
`timescale 1ns/1ps
module tb_hazard;
    parameter integer N = 400;                        // trials per setup value
    real LUT_MIN = 0.3, LUT_MAX = 2.5;
    real BUF_MIN = 1.4, BUF_MAX = 4.9;
    event redraw;

    integer errors = 0;
    reg [23:16] a_slot = 8'h00;
    reg         as_n_slot = 1'b1;
    wire [23:16] a_f;
    wire         as_n_f;

    // input buffers: per-bit random transport delay, redrawn per trial
    genvar g;
    generate for (g = 0; g < 9; g = g + 1) begin : buf_ch
        real d = 2.0;
        reg  q;
        wire i = (g == 8) ? as_n_slot : a_slot[16 + (g % 8)];
        always @(redraw) d = BUF_MIN + (BUF_MAX - BUF_MIN) * (($random & 32'h7FFFFFFF) % 100000) / 100000.0;
        always @(i) q <= #(d) i;
        if (g == 8) begin : as_b assign as_n_f = q; end
        else        begin : a_b  assign a_f[16 + g] = q; end
    end endgenerate

    // registered decode state for the trial
    reg [23:16] cmp = 8'hE9;
    reg         care_lo = 1'b1;
    wire        slave_n, xrdy, dbuf_oe_n, sel;
    z2_decode dut (.a_hi(a_f), .as_n(as_n_f), .berr_n(1'b1), .rd(1'b1), .doe(1'b1), .uds_n(1'b0), .lds_n(1'b0),
                   .match_en(1'b1), .cmp(cmp), .care_lo(care_lo), .hold_q(1'b1), .oe_rd_q(1'b1),
                   .oe_wr_q(1'b0), .dir_q(1'b1), .sel(sel), .slave_n(slave_n), .xrdy(xrdy), .dbuf_oe_n(dbuf_oe_n));

    // glitch monitors
    integer g_slave = 0, g_xrdy = 0, g_oe = 0;
    reg     armed_mon = 1'b0;
    always @(negedge slave_n)   if (armed_mon) g_slave = g_slave + 1;
    always @(negedge xrdy)      if (armed_mon) g_xrdy  = g_xrdy + 1;
    always @(negedge dbuf_oe_n) if (armed_mon) g_oe    = g_oe + 1;

    function [7:0] rnd_unsel;                         // random A23..A16 that is NOT selected
        input [7:0] base;
        input       lo;
        reg   [7:0] v;
        begin
            v = $random;
            if (lo ? (v == base) : (v[7:3] == base[7:3])) v = v ^ 8'h80;
            rnd_unsel = v;
        end
    endfunction

    task transition;                                  // move a_slot to v, each bit at a random time in [0, skew]
        input [7:0] v;
        input real  skew;
        integer b;
        begin
            for (b = 0; b < 8; b = b + 1)
                a_slot[16 + b] <= #(skew * (($random & 32'h7FFFFFFF) % 1000) / 1000.0) v[b];
        end
    endtask

    integer t, s, k, fails;
    real    setup;
    reg [7:0] p, q;
    initial begin
        $display("tb_hazard: LUT %0.2f-%0.2f ns, buffers %0.2f-%0.2f ns, %0d trials per point",
                 LUT_MIN, LUT_MAX, BUF_MIN, BUF_MAX, N);
        // ---------------- E1: /AS negated, address wandering through the selected window
        for (k = 0; k < 2; k = k + 1) begin
            care_lo = (k == 0);
            g_slave = 0; g_xrdy = 0; g_oe = 0;
            for (t = 0; t < N; t = t + 1) begin
                -> redraw;
                cmp = $random;
                as_n_slot = 1'b1;
                #(30.0);
                armed_mon = 1'b1;
                p = $random;
                transition(cmp, 12.0); #(20.0);       // through the selected code
                transition(p, 12.0);   #(20.0);
                transition(cmp ^ 8'h01, 12.0); #(20.0);
                transition(cmp, 3.0);  #(20.0);
                armed_mon = 1'b0;
            end
            $display("E1 (care_lo=%0d): /AS negated, %0d trials: /SLAVEn %0d, XRDY %0d, buffer enable %0d false assertions",
                     care_lo, N, g_slave, g_xrdy, g_oe);
            if (g_slave || g_xrdy || g_oe) begin
                errors = errors + 1;
                $display("ASSERT-FAIL E1 output asserted while /AS negated");
            end
        end
        care_lo = 1'b1;

        // ---------------- E2: setup sweep, unselected target address
        for (s = -8; s <= 14; s = s + 2) begin
            setup = s;
            fails = 0;
            for (t = 0; t < N; t = t + 1) begin
                -> redraw;
                cmp = $random;
                as_n_slot = 1'b1;
                a_slot = ($random & 1) ? cmp : $random;      // previous cycle: often the selected window
                #(40.0);
                q = rnd_unsel(cmp, care_lo);
                g_slave = 0; armed_mon = 1'b1;
                transition(q, 10.0);                         // slot skew 0..10 ns between bits
                as_n_slot <= #(10.0 + setup) 1'b0;           // /AS 'setup' after the LAST bit settles
                #(10.0 + setup + 80.0);
                if (slave_n !== 1'b1) g_slave = g_slave + 1;  // must be negated (unselected)
                armed_mon = 1'b0;
                if (g_slave) fails = fails + 1;
                as_n_slot = 1'b1;
                #(40.0);
            end
            $display("E2 slot setup %0d ns: %0d / %0d trials with a false /SLAVEn", s, fails, N);
        end

        $display("TB_RESULT %s tb_hazard errors=%0d (E2 is a characterisation, see the table above)",
                 (errors == 0) ? "PASS" : "FAIL", errors);
        $finish;
    end
endmodule
