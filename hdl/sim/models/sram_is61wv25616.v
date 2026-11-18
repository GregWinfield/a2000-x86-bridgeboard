// SPDX-License-Identifier: MIT
// Behavioural model of the ISSI IS61WV25616EDBLL-10 (256K x 16 asynchronous SRAM), with the
// datasheet's AC limits checked on every access. Testbench only.
// Source: ISSI IS61/64WV25616EDBLL datasheet Rev. A2 (2020-07-14), -10 column (VDD 2.4-3.6 V):
//   read : tAA 10, tOHA 2.0, tACE 10, tDOE 4.5, tHZOE 4, tLZOE 0, tHZCE 4, tLZCE 3, tBA 6.5,
//          tHZB 3, tLZB 0
//   write: tWC 10, tSCE 8, tAW 8, tHA 0, tSA 0, tPWB 8, tPWE1 8 (OE high), tPWE2 10 (OE low),
//          tSD 6, tHD 0, tHZWE 5, tLZWE 2
// A write is the overlap of /CE low, /WE low and /UB or /LB low; it ends at the first of these to
// rise (datasheet note 3). Output data are X between tOHA and the access time (resolution
// 0.5 ns). The device drives io from the moment its enables are all asserted until the longest
// High-Z time after the first one is negated, which is conservative for contention checking. With power
// off, the contents are lost and the outputs are Hi-Z.
`timescale 1ns/1ps
module m_sram_is61wv25616 #(
    parameter real TAA = 10.0, TOHA = 2.0, TACE = 10.0, TDOE = 4.5, TBA = 6.5,
    parameter real THZOE = 4.0, THZCE = 4.0, THZB = 3.0, THZWE = 5.0,
    parameter real TAW = 8.0, TSCE = 8.0, TPWB = 8.0, TPWE1 = 8.0, TPWE2 = 10.0, TSD = 6.0
) (
    input  wire [17:0] a,
    inout  wire [15:0] io,
    input  wire        ce_n, oe_n, we_n, ub_n, lb_n,
    input  wire        pwr,
    output wire        drv            // any byte lane driven (for contention monitors)
);
    reg [15:0] mem [0:262143];
    integer i, errors = 0, writes = 0, reads = 0;

    task fail;
        input [8*90-1:0] msg;
        begin
            errors = errors + 1;
            if (errors <= 30) $display("ASSERT-FAIL %0t SRAM %0s (a=%h)", $realtime, msg, a);
        end
    endtask

    // ---------------- event times
    real t_a = 0.0, t_ce_f = 0.0, t_oe_f = 0.0, t_ub_f = 0.0, t_lb_f = 0.0, t_d = 0.0, t_w0 = 0.0;
    real t_off_ub = -1.0, t_off_lb = -1.0;          // output-disable deadlines per lane
    wire en_ub = pwr & ~ce_n & ~oe_n & we_n & ~ub_n;
    wire en_lb = pwr & ~ce_n & ~oe_n & we_n & ~lb_n;
    wire wr    = pwr & ~ce_n & ~we_n & (~ub_n | ~lb_n);
    reg  drv_ub = 1'b0, drv_lb = 1'b0;
    reg  [15:0] dout = 16'hxxxx;
    assign drv = drv_ub | drv_lb;
    assign io[15:8] = drv_ub ? dout[15:8] : 8'hzz;
    assign io[7:0]  = drv_lb ? dout[7:0]  : 8'hzz;

    initial for (i = 0; i < 262144; i = i + 1) mem[i] = 16'hxxxx;     // undefined at power-up
    always @(negedge pwr) for (i = 0; i < 262144; i = i + 1) mem[i] = 16'hxxxx;

    always @(a)            t_a    = $realtime;
    always @(negedge ce_n) t_ce_f = $realtime;
    always @(negedge oe_n) t_oe_f = $realtime;
    always @(negedge ub_n) t_ub_f = $realtime;
    always @(negedge lb_n) t_lb_f = $realtime;
    always @(io)           t_d    = $realtime;
    // a disable starts the High-Z timer (conservative: the longest applicable High-Z time)
    function real hz_of;
        input dummy;
        begin
            hz_of = THZOE;
            if (THZCE > hz_of) hz_of = THZCE;
            if (THZWE > hz_of) hz_of = THZWE;
            if (THZB  > hz_of) hz_of = THZB;
        end
    endfunction
    always @(negedge en_ub) t_off_ub = $realtime + hz_of(1'b0);
    always @(negedge en_lb) t_off_lb = $realtime + hz_of(1'b0);

    // ---------------- output evaluation: on every input change, and every 0.5 ns while the
    // device is enabled or releasing the bus (delayed toggles alone can lose evaluations)
    task evaluate;
        real tv;
        begin
            drv_ub = pwr && (en_ub || ($realtime < t_off_ub));
            drv_lb = pwr && (en_lb || ($realtime < t_off_lb));
            tv = t_a + TAA;
            if (t_ce_f + TACE > tv) tv = t_ce_f + TACE;
            if (t_oe_f + TDOE > tv) tv = t_oe_f + TDOE;
            if (en_ub && (t_ub_f + TBA > tv)) tv = t_ub_f + TBA;
            if (en_lb && (t_lb_f + TBA > tv)) tv = t_lb_f + TBA;
            if ((en_ub || en_lb) && ($realtime >= tv - 1.0e-6))
                dout = mem[a];
            else if ($realtime >= t_a + TOHA - 1.0e-6)
                dout = 16'hxxxx;                     // between tOHA and the access time: invalid
        end
    endtask
    always @(en_ub or en_lb or a or pwr) evaluate;
    always #0.5 if (pwr && (en_ub || en_lb || drv_ub || drv_lb)) evaluate;
    always @(posedge en_ub or posedge en_lb) reads = reads + 1;

    // ---------------- writes
    reg w_ub = 1'b0, w_lb = 1'b0;                   // lanes taking part in the current write
    always @(posedge wr) begin
        t_w0 = $realtime;
        w_ub = ~ub_n; w_lb = ~lb_n;
        if (!oe_n) fail("write with /OE low (design keeps /OE high, tPWE2 applies)");
        if (drv) fail("write started while the outputs are still driving (tHZOE/tHZWE)");
    end
    always @(negedge ub_n) if (wr) w_ub = 1'b1;
    always @(negedge lb_n) if (wr) w_lb = 1'b1;
    always @(a) if (wr) fail("address changed during a write (tSA/tHA, corrupt write)");
    always @(negedge wr) if (pwr) begin : wend
        real tw;
        tw = $realtime;
        writes = writes + 1;
        if (tw - t_w0 < TPWE1 - 1.0e-6) fail("write pulse (overlap) shorter than tPWE1/tSCE/tPWB 8 ns");
        if (tw - t_a  < TAW - 1.0e-6)   fail("address valid to end of write shorter than tAW 8 ns");
        if (tw - t_d  < TSD - 1.0e-6)   fail("data setup to end of write shorter than tSD 6 ns");
        // commit the lanes that were written (both lanes sampled at the end of the write)
        if (w_ub) begin
            if (^io[15:8] === 1'bx) fail("write of undefined data (upper lane)");
            mem[a][15:8] = io[15:8];
        end
        if (w_lb) begin
            if (^io[7:0] === 1'bx) fail("write of undefined data (lower lane)");
            mem[a][7:0] = io[7:0];
        end
    end
    // tHD = 0: data may change at the end of the write; tHA = 0: likewise the address
endmodule
