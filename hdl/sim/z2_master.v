// SPDX-License-Identifier: MIT
// Bus-functional model of the A2000 bus master (MC68000 through the motherboard buffers)
// and of the motherboard's automatic DTACK, as seen at a Zorro II slot. Testbench only.
//
// MC68000 timing (M68000 8-/16-/32-Bit Microprocessors User's Manual, 9th ed., section 10.10,
// 8 MHz part; read/write/RMW state sequences sections 4.1.3 and 5.1): CPU clock 7.09379 MHz (PAL).
//   S2 rising: /AS (and read strobes) asserted, #9 3-60 ns     #11 address valid >= 30 ns before /AS
//   write: R/W low <= 10 ns after /AS (#20A), data valid >= 40 ns before DS (#26), DS at S4 rising
//   DTACK sampled at the falling edge ending S4 (and each wait state); read data latched entering S7
//   /AS, DS negated entering S7 (+#12 <= 62 ns); write data held >= 40 ns after (#25)
//   RMW: DS negated entering S7 with /AS held; R/W low at S14, data at S15, DS at S16, /AS negated
//   entering S19.
// Model assumptions [A] (no A2000 numbers are published; see the hazard-analysis document):
//   * slot-level address setup to /AS = setup_ns + per-bit spread skew_ns (default 25 + 0..10 ns)
//   * DOE: asserted doe_rd_on / doe_wr_on after /AS, negated doe_off after /AS negation; in RMW
//     either held across both portions (doe_rmw_mode 0) or split per portion (1)
//   * the motherboard drives write data from R/W low + mdrv_delay (worst case 0 ns)
//   * auto-DTACK: XRDY sampled on each CPU-clock rising edge from S4 (S16 for the RMW write
//     portion); DTACK asserted 10 ns after the first sample with XRDY released
`timescale 1ns/1ps
module z2_master #(
    parameter real T = 140.968                 // CPU clock period (PAL)
) (
    output reg  [23:1] A,
    output reg         AS_N,
    output reg         UDS_N,
    output reg         LDS_N,
    output reg         READ,
    output reg         DOE,
    inout  wire [15:0] D,
    input  wire        XRDY,
    inout  wire        BERR_N,
    output reg         clk7
);
    localparam integer K_READ = 0, K_WRITE = 1, K_TAS = 2, K_RMW = 3;

    // ---------------- knobs (set hierarchically by the testbench)
    integer seed         = 1;
    real    setup_ns     = 25.0;
    real    skew_ns      = 10.0;
    real    doe_rd_on    = 30.0;
    real    doe_wr_on    = 30.0;
    real    doe_off      = 0.0;
    integer doe_rmw_mode = 0;
    real    mdrv_delay   = 0.0;
    real    berr_at      = -1.0;              // >= 0: motherboard asserts /BERR this long after /AS

    // ---------------- observation
    reg         in_cycle = 1'b0;
    reg  [23:1] cur_addr = 23'd0;
    real        t_as = 0.0, t_asn = 0.0;
    integer     last_waits = 0;
    reg         mdrv = 1'b0;                   // master drives D
    reg  [15:0] dout = 16'h0000;
    reg         berr_drv = 1'b0;

    assign D      = mdrv ? dout : 16'hzzzz;
    assign BERR_N = berr_drv ? 1'b0 : 1'bz;

    initial begin
        A = 23'd0; AS_N = 1'b1; UDS_N = 1'b1; LDS_N = 1'b1; READ = 1'b1; DOE = 1'b0; clk7 = 1'b0;
    end
    always #(T / 2.0) clk7 = ~clk7;

    function real rnd;
        input real lo;
        input real hi;
        begin
            rnd = lo + (hi - lo) * (($random(seed) & 32'h7FFFFFFF) % 100000) / 100000.0;
        end
    endfunction

    function real later;                        // delay from now to absolute time t (>= 0)
        input real t;
        begin
            later = (t > $realtime) ? (t - $realtime) : 0.0;
        end
    endfunction

    // motherboard auto-DTACK and CPU termination sampling, starting at rising edge p
    task wait_term;
        input  real    p0;
        output real    ts;
        output reg     is_berr;
        output integer waits;
        real    p;
        reg     done, dtack;
        begin
            p = p0; waits = 0; is_berr = 1'b0; done = 1'b0;
            #(later(p));
            while (!done) begin
                dtack = (XRDY !== 1'b0);              // XRDY released at the motherboard sample
                #(later(p + T / 2.0));                // CPU samples DTACK/BERR at the falling edge
                if (BERR_N === 1'b0) begin
                    is_berr = 1'b1; done = 1'b1; ts = $realtime;
                end else if (dtack) begin
                    done = 1'b1; ts = $realtime;
                end else begin
                    waits = waits + 1;
                    p = p + T;
                    if (waits > 4000) begin
                        $display("ASSERT-FAIL %0t master: no DTACK for 4000 wait states (bus hang)", $realtime);
                        done = 1'b1; ts = $realtime; is_berr = 1'b1;
                    end else
                        #(later(p));
                end
            end
        end
    endtask

    // release the end of a cycle: /AS, strobes, DOE, write data, R/W, /BERR
    task finish;
        input integer kind;
        real tf;
        begin
            t_asn = $realtime + rnd(5.0, 50.0);
            AS_N  <= #(later(t_asn)) 1'b1;
            UDS_N <= #(later(t_asn + rnd(-2.0, 2.0))) 1'b1;
            LDS_N <= #(later(t_asn + rnd(-2.0, 2.0))) 1'b1;
            DOE   <= #(later(t_asn + doe_off)) 1'b0;
            tf = t_asn + rnd(40.0, 60.0);
            if (kind != K_READ) begin
                mdrv <= #(later(tf)) 1'b0;
                READ <= #(later(t_asn + rnd(40.0, 70.0))) 1'b1;
            end
            berr_drv <= #(later(t_asn + 20.0)) 1'b0;
            #(later(t_asn + 80.0));                   // every end event has happened
            in_cycle = 1'b0;
        end
    endtask

    // one complete bus cycle
    task cycle;
        input  integer kind;          // K_READ, K_WRITE, K_TAS (write-back = read | $80 on the lane), K_RMW
        input  [23:1]  addr;
        input  [1:0]   lanes;         // {UDS, LDS}: 1 = strobe used
        input  [15:0]  wdata;
        output [15:0]  rdata;
        output         berr;
        real    t0, t_ds, d, ts, t_s7, t_rw, t_ds2, ts2;
        integer i, w1, w2;
        reg     b1, b2;
        reg [15:0] wnew;
        begin
            rdata = 16'hxxxx; berr = 1'b0; w2 = 0;
            @(posedge clk7);
            t0 = $realtime;                                   // S0
            in_cycle = 1'b1; cur_addr = addr;
            t_as = t0 + T + rnd(5.0, 40.0);                   // S2 rising + #9
            for (i = 1; i <= 23; i = i + 1)
                A[i] <= #(later(t_as - setup_ns - rnd(0.0, skew_ns))) addr[i];
            AS_N <= #(later(t_as)) 1'b0;
            if (berr_at >= 0.0) berr_drv <= #(later(t_as + berr_at)) 1'b1;
            if (kind != K_WRITE) begin                        // read, or read portion of RMW
                READ <= 1'b1;
                t_ds = t_as + rnd(-2.0, 4.0);
                if (lanes[1]) UDS_N <= #(later(t_ds)) 1'b0;
                if (lanes[0]) LDS_N <= #(later(t_ds)) 1'b0;
                DOE <= #(later(t_as + doe_rd_on)) 1'b1;
            end else begin                                    // write
                READ <= #(later(t_as + rnd(0.0, 10.0))) 1'b0;
                t_ds = t0 + 2.0 * T + rnd(5.0, 40.0);         // S4 rising + #9
                d = t0 + 1.5 * T + rnd(5.0, 30.0);            // S3 falling + #23
                if (d > t_ds - 40.0) d = t_ds - 40.0;         // #26
                dout <= #(later(t_as)) 16'hxxxx;
                dout <= #(later(d)) wdata;
                mdrv <= #(later(t_as + mdrv_delay)) 1'b1;
                if (lanes[1]) UDS_N <= #(later(t_ds)) 1'b0;
                if (lanes[0]) LDS_N <= #(later(t_ds)) 1'b0;
                DOE <= #(later(t_as + doe_wr_on)) 1'b1;
            end

            wait_term(t0 + 2.0 * T, ts, b1, w1);              // S4 sampling
            last_waits = w1;
            #(later(ts + T));                                 // entering S7
            if (!b1) rdata = D;
            berr = b1;

            if ((kind == K_TAS || kind == K_RMW) && !b1) begin
                // ---- read portion ends: strobes negated, /AS held (sections 4.1.3 / 5.1.3)
                t_s7 = $realtime;
                d = t_s7 + rnd(5.0, 50.0);
                UDS_N <= #(later(d)) 1'b1;
                LDS_N <= #(later(d)) 1'b1;
                if (doe_rmw_mode == 1) DOE <= #(later(d + 10.0)) 1'b0;
                wnew = wdata;
                if (kind == K_TAS) begin
                    wnew = rdata;
                    if (lanes[1]) wnew[15] = 1'b1;
                    if (lanes[0]) wnew[7]  = 1'b1;
                end
                t_rw  = t_s7 + 3.5 * T + rnd(5.0, 40.0);       // S14 rising: R/W low
                t_ds2 = t_s7 + 4.5 * T + rnd(5.0, 40.0);       // S16 rising: DS asserted
                d     = t_s7 + 4.0 * T + rnd(5.0, 30.0);       // S15: data out
                if (d > t_ds2 - 40.0) d = t_ds2 - 40.0;
                READ <= #(later(t_rw)) 1'b0;
                dout <= #(later(t_rw)) 16'hxxxx;
                dout <= #(later(d)) wnew;
                mdrv <= #(later(t_rw + mdrv_delay)) 1'b1;
                if (lanes[1]) UDS_N <= #(later(t_ds2)) 1'b0;
                if (lanes[0]) LDS_N <= #(later(t_ds2)) 1'b0;
                if (doe_rmw_mode == 1) DOE <= #(later(t_ds2 + doe_wr_on)) 1'b1;
                wait_term(t_s7 + 4.5 * T, ts2, b2, w2);       // S16 sampling
                last_waits = w1 + w2;
                berr = b2;
                #(later(ts2 + T));                            // entering S19
                finish(K_WRITE);
            end else
                finish(kind);
        end
    endtask

    // Arbitrary-timing cycle (abort / early /AS release / bus-error robustness).
    // All times are relative to /AS assertion; the address is stable setup_ns before /AS.
    task raw_cycle;
        input [23:1] addr;
        input        is_read;
        input [1:0]  lanes;
        input real   as_len, ds_on, ds_len, doe_on, doe_len;
        begin
            @(posedge clk7);
            in_cycle = 1'b1; cur_addr = addr;
            A = addr; READ = is_read;
            #(setup_ns + 5.0);
            AS_N = 1'b0; t_as = $realtime;
            if (!is_read) begin dout = 16'hA55A; mdrv = 1'b1; end
            fork
                begin #(ds_on);  UDS_N = ~lanes[1]; LDS_N = ~lanes[0]; #(ds_len); UDS_N = 1'b1; LDS_N = 1'b1; end
                begin #(doe_on); DOE = 1'b1; #(doe_len); DOE = 1'b0; end
                begin #(as_len); AS_N = 1'b1; t_asn = $realtime; end
            join
            #(40.0); mdrv = 1'b0; READ = 1'b1;
            #(100.0);
            in_cycle = 1'b0;
        end
    endtask
endmodule
