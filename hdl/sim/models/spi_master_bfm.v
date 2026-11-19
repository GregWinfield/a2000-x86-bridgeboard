// SPDX-License-Identifier: MIT
// RP2040 side of the host link (testbench only): an SPI master with PL022-like mode-0 timing and a
// GPIO chip select, speaking host-link protocol v1.0 (docs/hdl/host-link-protocol.md). It drives the
// REAL z2_hostif RTL through the FPGA pins (HL-1, HL-5, HL-6). Same task interface and statistics as
// the clock-level model sim/models/hostif_bfm.v, so tb_shm and tb_z2 run unchanged on either.
//   xfer(reg, we, addr, be, wdata, rdata)   one word: command frame, ATTN, GET_RESPONSE, checks
//   burst_wr / burst_rd                     SRAM_WRITE / SRAM_READ of up to 128 words (buf_w / buf_r)
//   frame(n_tx, n_clk)                      raw frame: txb[0..n_tx-1], then padding, n_clk bytes
//   background traffic: bg_en, bg_base, bg_gap (random single and burst SRAM traffic, shadow-checked)
// Timing knobs: half (SCK half period, ns), t_css, t_csh, t_csw, rx_skew (MISO is sampled rx_skew ns
// before the SCK rising edge: a conservative model of the RP2040 input sampling, owner requirement 4).
`timescale 1ns/1ps
module spi_master_bfm (
    output reg  sck,
    output reg  cs_n,
    output reg  mosi,
    input  wire miso,
    input  wire attn,
    input  wire irq_n
);
    initial begin sck = 1'b0; cs_n = 1'b1; mosi = 1'b0; end

    real    half = 50.0, t_css = 100.0, t_csh = 100.0, t_csw = 1000.0, rx_skew = 16.0;
    real    attn_timeout = 1.0e6;                     // 1 ms (protocol §8)
    integer seed = 5, n_sram = 0, n_reg = 0, errors = 0, retries = 0, frames = 0;
    real    max_lat = 0.0, sum_lat = 0.0, bt0 = 0.0;   // sum_lat / n_sram = time per word
    reg     busy = 1'b0;
    reg [7:0] seq = 8'h00;
    reg [7:0] txb [0:599];
    reg [7:0] rxb [0:599];
    reg [15:0] buf_w [0:127];
    reg [15:0] buf_r [0:127];
    reg     verbose = 1'b0;
    initial if ($test$plusargs("spi_verbose")) verbose = 1'b1;

    function [15:0] crc_upd;
        input [15:0] c;
        input [7:0]  b;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {b, 8'h00};
            for (i = 0; i < 8; i = i + 1) x = x[15] ? ((x << 1) ^ 16'h1021) : (x << 1);
            crc_upd = x;
        end
    endfunction

    // ---------------- one frame: CS low, n_clk bytes (txb then 0x00 padding), CS high
    task automatic frame;
        input integer n_tx;
        input integer n_clk;
        integer i, k;
        reg [7:0] b, r;
        begin
            cs_n = 1'b0; #(t_css);
            for (i = 0; i < n_clk; i = i + 1) begin
                b = (i < n_tx) ? txb[i] : 8'h00;
                for (k = 7; k >= 0; k = k - 1) begin
                    mosi = b[k];
                    #(half - rx_skew); r[k] = miso;          // effective RP2040 sampling instant
                    #(rx_skew); sck = 1'b1;
                    #(half); sck = 1'b0;
                end
                rxb[i] = r;
            end
            #(t_csh); cs_n = 1'b1; mosi = 1'b0; #(t_csw);
            frames = frames + 1;
        end
    endtask

    task automatic wait_attn;                         // wait for READY; ok = 0 on timeout
        output ok;
        real t0;
        begin
            t0 = $realtime; ok = 1'b1;
            while (attn !== 1'b1 && ($realtime - t0) < attn_timeout) #(20.0);
            if (attn !== 1'b1) ok = 1'b0;
        end
    endtask

    task automatic build;                             // header + CRC around txb[5 .. 4+len]
        input [7:0]   cmd;
        input integer len;
        output integer n;
        reg [15:0] c;
        integer i;
        begin
            seq = seq + 8'd1;
            txb[0] = 8'hA1; txb[1] = cmd; txb[2] = seq; txb[3] = len[15:8]; txb[4] = len[7:0];
            c = 16'hFFFF;
            for (i = 0; i < 5 + len; i = i + 1) c = crc_upd(c, txb[i]);
            txb[5 + len] = c[15:8]; txb[6 + len] = c[7:0];
            n = 7 + len;
        end
    endtask

    // ---------------- one command with its response, per the recovery rules of §8
    // returns ok = 1 and the response payload in rxb[6 ..] (rlen bytes), rcode in rc
    task automatic transact;
        input [7:0]   cmd;
        input integer len;                            // payload already in txb[5 ..]
        input integer rlen;                           // expected response payload length
        output        ok;
        output [7:0]  rc;
        integer n, tries, gets, i, nl;
        reg [7:0] myseq;
        reg [7:0] save [0:299];
        reg [15:0] c;
        reg a_ok, good;
        begin
            ok = 1'b0; rc = 8'hFF;
            for (i = 0; i < 5 + len && i < 300; i = i + 1) save[i] = txb[i];
            for (tries = 0; tries < 3 && !ok; tries = tries + 1) begin
                for (i = 5; i < 5 + len && i < 300; i = i + 1) txb[i] = save[i];
                build(cmd, len, n); myseq = seq;
                wait_attn(a_ok);
                if (!a_ok) begin errors = errors + 1; $display("%0t SPI BFM: ATTN timeout before command", $realtime); disable transact; end
                frame(n, n);
                good = 1'b0;
                for (gets = 0; gets < 3 && !good; gets = gets + 1) begin
                    wait_attn(a_ok);
                    if (!a_ok) begin errors = errors + 1; $display("%0t SPI BFM: ATTN timeout after command", $realtime); disable transact; end
                    build(8'h03, 0, nl); seq = seq - 8'd1;   // GET_RESPONSE does not consume a sequence number
                    frame(nl, 8 + rlen);
                    c = 16'hFFFF;
                    for (i = 0; i < 8 + rlen; i = i + 1) c = crc_upd(c, rxb[i]);
                    if (rxb[0] == 8'h51 && c == 16'h0000) good = 1'b1;
                    else begin
                        retries = retries + 1;               // response corrupted: fetch again (R2)
                        if (verbose) $display("%0t SPI BFM: bad response (half %0.1f skew %0.1f css %0.1f): %h %h %h %h %h %h %h %h %h %h",
                            $realtime, half, rx_skew, t_css, rxb[0], rxb[1], rxb[2], rxb[3], rxb[4], rxb[5], rxb[6], rxb[7], rxb[8], rxb[9]);
                    end
                end
                if (!good) begin errors = errors + 1; $display("%0t SPI BFM: no valid response", $realtime); disable transact; end
                if (rxb[2] == myseq) begin ok = 1'b1; rc = rxb[3]; end
                else retries = retries + 1;                   // command rejected (R3): send it again
            end
            if (!ok) begin errors = errors + 1; $display("%0t SPI BFM: command 0x%02h not accepted", $realtime, cmd); end
        end
    endtask

    // ---------------- single-word transaction (interface of hostif_bfm)
    task automatic xfer;
        input         r;
        input         we;
        input  [17:0] addr;
        input  [1:0]  be;
        input  [15:0] wd;
        output [15:0] rd;
        real t0, lat;
        reg ok;
        reg [7:0] rc;
        begin
            while (busy) #(20.0);
            busy = 1'b1; t0 = $realtime; rd = 16'hxxxx;
            if (r && we)       begin txb[5] = {4'd0, addr[3:0]}; txb[6] = {6'd0, be}; txb[7] = wd[15:8]; txb[8] = wd[7:0]; transact(8'h20, 4, 0, ok, rc); end
            else if (r)        begin txb[5] = {4'd0, addr[3:0]}; transact(8'h21, 1, 2, ok, rc); rd = {rxb[6], rxb[7]}; end
            else if (we)       begin txb[5] = {6'd0, addr[17:16]}; txb[6] = addr[15:8]; txb[7] = addr[7:0]; txb[8] = {6'd0, be};
                                     txb[9] = wd[15:8]; txb[10] = wd[7:0]; transact(8'h12, 6, 0, ok, rc); end
            else               begin txb[5] = {6'd0, addr[17:16]}; txb[6] = addr[15:8]; txb[7] = addr[7:0]; txb[8] = 8'd1;
                                     transact(8'h11, 4, 2, ok, rc); rd = {rxb[6], rxb[7]}; end
            if (ok && rc != 8'h00) begin errors = errors + 1; $display("%0t SPI BFM: RCODE %02h", $realtime, rc); end
            if (r) n_reg = n_reg + 1; else n_sram = n_sram + 1;
            lat = $realtime - t0; sum_lat = sum_lat + lat; if (lat > max_lat) max_lat = lat;
            busy = 1'b0;
        end
    endtask

    task automatic burst_wr;                          // SRAM_WRITE of n words from buf_w
        input [17:0] addr;
        input integer n;
        reg ok;
        reg [7:0] rc;
        integer i;
        begin
            while (busy) #(20.0);
            busy = 1'b1; bt0 = $realtime;
            txb[5] = {6'd0, addr[17:16]}; txb[6] = addr[15:8]; txb[7] = addr[7:0];
            for (i = 0; i < n; i = i + 1) begin txb[8 + 2 * i] = buf_w[i][15:8]; txb[9 + 2 * i] = buf_w[i][7:0]; end
            transact(8'h10, 3 + 2 * n, 0, ok, rc);
            if (ok && rc != 8'h00) begin errors = errors + 1; $display("%0t SPI BFM: burst write RCODE %02h", $realtime, rc); end
            n_sram = n_sram + n; sum_lat = sum_lat + ($realtime - bt0); busy = 1'b0;
        end
    endtask

    task automatic burst_rd;                          // SRAM_READ of n words into buf_r
        input [17:0] addr;
        input integer n;
        reg ok;
        reg [7:0] rc;
        integer i;
        begin
            while (busy) #(20.0);
            busy = 1'b1; bt0 = $realtime;
            txb[5] = {6'd0, addr[17:16]}; txb[6] = addr[15:8]; txb[7] = addr[7:0]; txb[8] = n[7:0];
            transact(8'h11, 4, 2 * n, ok, rc);
            for (i = 0; i < n; i = i + 1) buf_r[i] = {rxb[6 + 2 * i], rxb[7 + 2 * i]};
            if (ok && rc != 8'h00) begin errors = errors + 1; $display("%0t SPI BFM: burst read RCODE %02h", $realtime, rc); end
            n_sram = n_sram + n; sum_lat = sum_lat + ($realtime - bt0); busy = 1'b0;
        end
    endtask

    task abort;                                       // used when a test kills a transfer in flight
        begin cs_n = 1'b1; sck = 1'b0; mosi = 1'b0; busy = 1'b0; end
    endtask

    // ---------------- background traffic (HL-6): random single and burst SRAM accesses in
    // [bg_base, bg_base + 4095], checked against a shadow copy
    reg        bg_en = 1'b0;
    reg [17:0] bg_base = 18'h30000;
    integer    bg_gap = 2;
    reg [15:0] shadow [0:4095];
    reg [4095:0] valid = 4096'd0;
    integer    j, nb;
    reg [11:0] off;
    reg        allv;
    reg [15:0] d;
    always begin
        #(100.0);
        while (bg_en) begin
            off = $random(seed); nb = 1 + ($unsigned($random(seed)) % 16);
            if (off > 12'd4095 - nb) off = 12'd4095 - nb;
            allv = 1'b1;
            for (j = 0; j < nb; j = j + 1) if (!valid[off + j]) allv = 1'b0;
            // a never-written word reads as X in the SRAM model and poisons the response CRC (a model
            // artefact, unlike real SRAM), so a range that is not fully defined is written, not read
            if (($random(seed) & 1) || !allv) begin
                for (j = 0; j < nb; j = j + 1) begin buf_w[j] = $random(seed); end
                if (nb == 1) xfer(1'b0, 1'b1, bg_base + off, 2'b11, buf_w[0], d); else burst_wr(bg_base + off, nb);
                for (j = 0; j < nb; j = j + 1) begin shadow[off + j] = buf_w[j]; valid[off + j] = 1'b1; end
            end else begin
                if (nb == 1) begin xfer(1'b0, 1'b0, bg_base + off, 2'b11, 16'h0, d); buf_r[0] = d; end
                else burst_rd(bg_base + off, nb);
                for (j = 0; j < nb; j = j + 1)
                    if (valid[off + j] && buf_r[j] !== shadow[off + j]) begin
                        errors = errors + 1;
                        $display("%0t SPI BFM background: word %h read %h, expected %h", $realtime, bg_base + off + j, buf_r[j], shadow[off + j]);
                    end
            end
            #(bg_gap * 20.0);
        end
    end
endmodule
