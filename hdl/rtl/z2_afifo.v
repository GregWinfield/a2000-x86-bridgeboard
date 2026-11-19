// SPDX-License-Identifier: MIT
// Asynchronous FIFO (host link, sheet 4): write side in the SPI clock domain, read side in clk_core.
// Gray-coded pointers, each crossing through a two-flop synchroniser; storage written only in the
// write domain and read in the read domain at an entry the write side released at least two read
// clocks earlier (C. Cummings, "Simulation and Synthesis Techniques for Asynchronous FIFO Design").
// The read data is first-word-fall-through: rdata is valid whenever rempty = 0.
// Safety does not depend on the clock ratio: a write while full is not stored and wdrop pulses
// (the SPI receiver turns that into the "byte dropped" flag of the protocol, check V1).
// Resets are asynchronous to both clocks; release them while the write clock is idle (H-5).
`default_nettype none
module z2_afifo #(
    parameter integer W  = 10,                   // data width
    parameter integer AW = 4                     // depth 2**AW
) (
    // write domain
    input  wire          wclk,
    input  wire          wrst,                   // asynchronous, active high
    input  wire          we,
    input  wire [W-1:0]  wdata,
    output wire          wfull,
    output wire          wdrop,                  // a write was refused because the FIFO was full
    // read domain
    input  wire          rclk,
    input  wire          rrst,                   // asynchronous, active high
    input  wire          re,
    output wire [W-1:0]  rdata,
    output wire          rempty
);
    reg [W-1:0] mem [0:(1<<AW)-1];
    reg  [AW:0] wbin, wgray;                      // write pointer (binary, Gray)
    reg  [AW:0] rbin, rgray;                      // read pointer (binary, Gray)

    // ---------------- write domain
    reg  [AW:0] rq1, rq2;                         // read pointer (Gray) synchronised into wclk
    wire [AW:0] wbin_n  = wbin + {{AW{1'b0}}, (we & ~wfull)};
    wire [AW:0] wgray_n = (wbin_n >> 1) ^ wbin_n;
    assign wfull = (wgray == {~rq2[AW:AW-1], rq2[AW-2:0]});
    assign wdrop = we & wfull;
    always @(posedge wclk or posedge wrst)
        if (wrst) begin wbin <= 0; wgray <= 0; rq1 <= 0; rq2 <= 0; end
        else begin
            if (we & ~wfull) mem[wbin[AW-1:0]] <= wdata;
            wbin <= wbin_n; wgray <= wgray_n;
            rq1 <= rgray; rq2 <= rq1;
        end

    // ---------------- read domain
    reg  [AW:0] wq1, wq2;                         // write pointer (Gray) synchronised into rclk
    wire [AW:0] rbin_n  = rbin + {{AW{1'b0}}, (re & ~rempty)};
    wire [AW:0] rgray_n = (rbin_n >> 1) ^ rbin_n;
    assign rempty = (rgray == wq2);
    assign rdata  = mem[rbin[AW-1:0]];
    always @(posedge rclk or posedge rrst)
        if (rrst) begin rbin <= 0; rgray <= 0; wq1 <= 0; wq2 <= 0; end
        else begin
            rbin <= rbin_n; rgray <= rgray_n;
            wq1 <= wgray; wq2 <= wq1;
        end
endmodule
`default_nettype wire
