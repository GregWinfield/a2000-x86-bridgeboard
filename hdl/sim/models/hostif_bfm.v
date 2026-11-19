// SPDX-License-Identifier: MIT
// Host-port bus-functional model (testbench only), selected in z2_top with -DHOST_BFM in place of
// the real sheet-4 SPI slave (rtl/z2_hostif.v). It stands for the SPI slave and
// issues host transactions at the clk_core level, the worst case for the arbiter: requests at
// any phase, back to back, with no SPI-rate limit.
//   xfer(reg, we, addr, be, wdata, rdata)  one transaction (waits for any background transfer)
//   background traffic: set bg_en = 1; random SRAM reads and writes in a private region
//   [bg_base, bg_base + 4095] (word addresses), checked against a shadow copy.
`timescale 1ns/1ps
module z2_hostif_bfm (
    input  wire        clk,
    input  wire        por,
    output reg         h_req,
    output reg         h_we,
    output reg         h_reg,
    output reg  [17:0] h_addr,
    output reg  [1:0]  h_be,
    output reg  [15:0] h_wdata,
    input  wire        h_ack,
    input  wire [15:0] h_rdata
);
    initial begin h_req = 1'b0; h_we = 1'b0; h_reg = 1'b0; h_addr = 18'd0; h_be = 2'b00; h_wdata = 16'h0000; end

    integer n_sram = 0, n_reg = 0, errors = 0, seed = 11;
    real    max_lat = 0.0, sum_lat = 0.0;
    reg     busy = 1'b0;

    task automatic xfer;                          // automatic: the testbench and the background
        input         r;                          // generator may both call it
        input         we;
        input  [17:0] addr;
        input  [1:0]  be;
        input  [15:0] wd;
        output [15:0] rd;
        real t0, lat;
        begin
            while (busy) @(posedge clk);
            busy = 1'b1;
            @(posedge clk); #1;
            h_req = 1'b1; h_we = we; h_reg = r; h_addr = addr; h_be = be; h_wdata = wd; t0 = $realtime;
            @(posedge clk);
            while (h_ack !== 1'b1) @(posedge clk);        // completes at the edge with h_ack = 1
            rd = h_rdata;
            #1; h_req = 1'b0;
            lat = $realtime - t0;
            if (!r) begin
                n_sram = n_sram + 1; sum_lat = sum_lat + lat;
                if (lat > max_lat) max_lat = lat;
            end else
                n_reg = n_reg + 1;
            busy = 1'b0;
        end
    endtask

    // ---------------- background SRAM traffic in a private region
    reg        bg_en = 1'b0;
    reg [17:0] bg_base = 18'h3F000;               // SRAM byte $7E000-$7FFFF by default
    integer    bg_gap = 6;                        // 0..bg_gap idle clocks between transfers
    reg [15:0] shadow [0:4095];
    reg [4095:0] known = 4096'd0;
    integer    k, gap;
    reg [11:0] off;
    reg [15:0] wd, rv;
    reg [1:0]  be;
    initial begin
        for (k = 0; k < 4096; k = k + 1) shadow[k] = 16'h0000;
        forever begin
            @(posedge clk);
            if (bg_en && !por) begin
                off = $random(seed);
                if ($random(seed) & 1) begin
                    wd = $random(seed);
                    be = (($random(seed) & 3) == 0) ? (($random(seed) & 1) ? 2'b10 : 2'b01) : 2'b11;
                    xfer(1'b0, 1'b1, bg_base + off, be, wd, rv);
                    if (be[1]) shadow[off][15:8] = wd[15:8];
                    if (be[0]) shadow[off][7:0]  = wd[7:0];
                    if (be == 2'b11) known[off] = 1'b1;
                end else begin
                    xfer(1'b0, 1'b0, bg_base + off, 2'b11, 16'h0000, rv);
                    if (known[off] && (rv !== shadow[off])) begin
                        errors = errors + 1;
                        if (errors <= 20)
                            $display("ASSERT-FAIL %0t host BFM: SRAM word %h read %h, expected %h", $realtime,
                                     bg_base + off, rv, shadow[off]);
                    end
                end
                gap = ($random(seed) & 32'h7FFFFFFF) % (bg_gap + 1);
                repeat (gap) @(posedge clk);
            end
        end
    end
endmodule
