// SPDX-License-Identifier: MIT
// Host-link protocol testbench (sheet 4): the REAL z2_hostif RTL in z2_top, driven through the FPGA
// pins by the PL022-like SPI master (sim/models/spi_master_bfm.v) via the translator/ribbon delays of
// card_model. Covers HL-1 (protocol and byte order at the pins, normative vectors), HL-3/HL-4
// (buffering, ordering), owner requirements 1, 3, 5 and 7 (no partial commit, flow control,
// interrupted frames and clock stoppage, power and reset events) and a random SCK/skew/phase sweep.
//   P1 power-on IDENTIFY response     P6 oversize LEN                P11 128-word bursts, ECHO 256
//   P2 normative vectors (V1, V5)     P7 wrong major version         P12 counters, RESET_LINK
//   P3 CRC error: nothing written     P8 V6 error responses          P13 X4 power loss mid-frame
//   P4 truncated frame                P9 GET_RESPONSE idempotent     P14 FPGA reload mid-command
//   P5 SCK stops in mid-byte          P10 busy frame during a burst  P15 random rate/skew/phase sweep
//   P16 RP2040 reset with the X4 powered: CS_N reads asserted with no clock (between frames and
//       in mid-frame); nothing executes, no interrupt, ATTN low, the link recovers
`timescale 1ns/1ps
module tb_spi;
    parameter integer SEED = 1;
    parameter integer LAUNCH_RISE = 0;               // must match z2_top's z2_hostif (see run_checks)
    parameter real    HALF_MIN = 50.0;               // SCK half-period range for the sweep (ns)
    parameter real    HALF_MAX = 250.0;
    parameter real    SKEW_MAX = 16.0;               // RP2040 input sampling skew range (ns)

    integer errors = 0, checks = 0;
    task fail; input [8*80-1:0] what; begin errors = errors + 1; if (errors <= 60) $display("ASSERT-FAIL %0t %0s", $realtime, what); end endtask
    task expect16;
        input [8*60-1:0] what;
        input [15:0] got, want;
        begin checks = checks + 1; if (got !== want) begin errors = errors + 1; if (errors <= 60) $display("ASSERT-FAIL %0t %0s: got %h want %h", $realtime, what, got, want); end end
    endtask
    task expect1;
        input [8*60-1:0] what;
        input got, want;
        begin checks = checks + 1; if (got !== want) begin errors = errors + 1; if (errors <= 60) $display("ASSERT-FAIL %0t %0s: got %b want %b", $realtime, what, got, want); end end
    endtask

    // ------------------------------------------------------------------ harness (as tb_shm)
    reg clk = 1'b0;
    initial begin #(0.37 + (SEED % 11)); forever #10.0 clk = ~clk; end
    wire [23:1] Z_A;
    wire        Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, clk7;
    wire [15:0] Z_D;
    m_bushold #(.W(16)) u_dhold (.bus(Z_D));
    tri1 Z_SLAVE_N;
    tri0 Z_CFGOUT_N;
    tri1 Z_XRDY, Z_INT2_N, Z_INT6_N, Z_BERR_N;
    reg  Z_CFGIN_N = 1'b0, Z_BUSRST_N = 1'b1;
    reg  pwr3 = 1'b0, pwr5 = 1'b0, jumper = 1'b0, fpga_cfg = 1'b0, x4_on = 1'b1;
    z2_master m (.A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N), .READ(Z_READ), .DOE(Z_DOE),
                 .D(Z_D), .XRDY(Z_XRDY), .BERR_N(Z_BERR_N), .clk7(clk7));
    wire d_drv, ld_conflict, card_en_n, en_ok, rp_irq_n, sram_drv;
    card_model #(.SEED(SEED), .SUP_TD(5000.0)) c (
        .Z_A(Z_A), .Z_AS_N(Z_AS_N), .Z_UDS_N(Z_UDS_N), .Z_LDS_N(Z_LDS_N), .Z_READ(Z_READ), .Z_DOE(Z_DOE),
        .Z_E7M(clk7), .Z_CFGIN_N(Z_CFGIN_N), .Z_BUSRST_N(Z_BUSRST_N), .Z_BERR_N(Z_BERR_N),
        .Z_D(Z_D), .Z_SLAVE_N(Z_SLAVE_N), .Z_CFGOUT_N(Z_CFGOUT_N), .Z_XRDY(Z_XRDY),
        .Z_INT2_N(Z_INT2_N), .Z_INT6_N(Z_INT6_N),
        .clk_core(clk), .pwr3(pwr3), .pwr5(pwr5), .jumper(jumper), .fpga_cfg(fpga_cfg), .x4_on(x4_on),
        .dip_mode_b(1'b0), .dip_int6(1'b0), .dip_disable(1'b0),
        .d_drv(d_drv), .ld_conflict(ld_conflict), .card_en_n(card_en_n), .en_ok(en_ok),
        .rp_irq_n(rp_irq_n), .sram_drv(sram_drv));
    always @(posedge ld_conflict) if (fpga_cfg) fail("LD contention");

    // no false host interrupt and no READY while the FPGA is blank or the X4 is off (owner req. 7)
    always @(negedge c.spi_irq_n) if (!fpga_cfg) fail("host interrupt asserted while the FPGA is blank");
    always @(posedge c.spi_attn) if (!fpga_cfg) fail("ATTN high while the FPGA is blank");

    // ------------------------------------------------------------------ helpers
    integer i, k, n, seqv;
    reg [15:0] d, crc;
    reg [7:0]  s0;
    task load;                                        // txb[0..nb-1] = the nb low-order bytes of v, MSB first
        input [8*16-1:0] v;
        input integer nb;
        begin for (i = 0; i < nb; i = i + 1) c.spi.txb[i] = v[8 * (nb - 1 - i) +: 8]; end
    endtask
    task ready; reg ok; begin c.spi.wait_attn(ok); if (!ok) fail("ATTN timeout"); end endtask
    task raw;                                         // one raw frame of nb bytes, clocked for nclk
        input integer nb, nclk;
        begin ready; c.spi.frame(nb, nclk); end
    endtask
    task get_resp;                                    // GET_RESPONSE, clocked for 8 + rlen bytes; checks CRC
        input integer rlen;
        integer nl;
        begin
            ready; c.spi.build(8'h03, 0, nl); c.spi.frame(nl, 8 + rlen);
            crc = 16'hFFFF;
            for (i = 0; i < 8 + rlen; i = i + 1) crc = c.spi.crc_upd(crc, c.spi.rxb[i]);
            checks = checks + 1;
            if (c.spi.rxb[0] !== 8'h51 || crc !== 16'h0000) fail("response RSYNC/CRC");
        end
    endtask
    task status;                                      // STATUS: returns the three counters
        output [15:0] ncrc, nframe, nbusy;
        integer nl;
        reg ok;
        reg [7:0] rc;
        begin c.spi.transact(8'h02, 0, 8, ok, rc); ncrc = {c.spi.rxb[7], c.spi.rxb[8]};
              nframe = {c.spi.rxb[9], c.spi.rxb[10]}; nbusy = {c.spi.rxb[11], c.spi.rxb[12]}; end
    endtask
    reg [15:0] e_crc, e_frame, e_busy, g_crc, g_frame, g_busy;
    reg ok;
    reg [7:0] rc;
    reg [15:0] shadow [0:1023];
    real t0;

    initial begin
        c.spi.seed = SEED * 13 + 7;
        c.spi.attn_timeout = 200000.0;
        // ---------------- P0 power, FPGA blank: not ready, no interrupt
        #(500.0); pwr3 = 1'b1; pwr5 = 1'b1; #(2000.0);
        expect1("P0 ATTN low while the FPGA is blank", c.spi_attn, 1'b0);
        expect1("P0 no host interrupt while the FPGA is blank", c.spi_irq_n, 1'b1);
        fpga_cfg = 1'b1;
        // ---------------- P1 power-on response: IDENTIFY with SEQ 0xFF
        get_resp(8);
        expect16("P1 SEQ FF, RCODE OK", {c.spi.rxb[2], c.spi.rxb[3]}, 16'hFF00);
        expect16("P1 payload length 8", {c.spi.rxb[4], c.spi.rxb[5]}, 16'd8);
        expect16("P1 magic Z2", {c.spi.rxb[6], c.spi.rxb[7]}, 16'h5A32);
        expect16("P1 protocol 1.0", {c.spi.rxb[8], c.spi.rxb[9]}, 16'h0100);
        expect16("P1 HDL_VER, MAX_WORDS", {c.spi.rxb[10], c.spi.rxb[11]}, 16'h0380);
        expect16("P1 FIFO depth, FEATURES", {c.spi.rxb[12], c.spi.rxb[13]}, {8'd16, 5'd0, LAUNCH_RISE[0], 2'b11});
        // ---------------- P2 normative vectors (protocol §12): IDENTIFY, SRAM_WRITE (V1), SRAM_READ (V5)
        load(56'ha1_01_00_00_00_e7_8d, 7); raw(7, 7); get_resp(8);
        expect16("P2 IDENTIFY vector accepted (SEQ 00)", {c.spi.rxb[2], c.spi.rxb[3]}, 16'h0000);
        load(112'ha1_10_07_00_07_00_00_10_12_34_ab_cd_ef_c7, 14); raw(14, 14); get_resp(0);
        expect16("P2 SRAM_WRITE vector accepted (SEQ 07)", {c.spi.rxb[2], c.spi.rxb[3]}, 16'h0700);
        expect16("P2 byte order V1: word $10 = $1234", c.u301.mem[16], 16'h1234);
        expect16("P2 byte order V1: word $11 = $ABCD", c.u301.mem[17], 16'hABCD);
        load(88'ha1_11_08_00_04_00_00_10_02_a8_e2, 11); raw(11, 11); get_resp(4);
        for (i = 0; i < 12; i = i + 1) s0 = c.spi.rxb[i];
        expect16("P2 response vector bytes 0-1", {c.spi.rxb[0], c.spi.rxb[1]}, 16'h5100);
        expect16("P2 response vector bytes 2-3", {c.spi.rxb[2], c.spi.rxb[3]}, 16'h0800);
        expect16("P2 response vector bytes 4-5", {c.spi.rxb[4], c.spi.rxb[5]}, 16'h0004);
        expect16("P2 response vector bytes 6-7", {c.spi.rxb[6], c.spi.rxb[7]}, 16'h1234);
        expect16("P2 response vector bytes 8-9", {c.spi.rxb[8], c.spi.rxb[9]}, 16'hABCD);
        expect16("P2 response vector CRC (V5)", {c.spi.rxb[10], c.spi.rxb[11]}, 16'hD9E3);
        // ---------------- P3 CRC error: nothing written, response unchanged, CRC_ERRORS counted
        status(e_crc, e_frame, e_busy);
        seqv = c.spi.seq;                                                 // the STATUS command's SEQ
        load(112'ha1_10_09_00_07_00_00_20_de_ad_be_ef_00_00, 14); raw(14, 14);   // CRC bytes wrong
        get_resp(8);
        expect16("P3 rejected frame: response still the STATUS one", {c.spi.rxb[2], c.spi.rxb[5]}, {seqv[7:0], 8'd8});
        expect1("P3 nothing written at word $20", c.u301.mem[32] === 16'hxxxx, 1'b1);
        status(g_crc, g_frame, g_busy);
        expect16("P3 CRC_ERRORS + 1", g_crc, e_crc + 16'd1);
        // ---------------- P4 truncated frame (CS high inside the payload)
        c.spi.txb[5] = 8'h00; c.spi.txb[6] = 8'h00; c.spi.txb[7] = 8'h21; c.spi.txb[8] = 8'h11; c.spi.txb[9] = 8'h22;
        c.spi.txb[10] = 8'h33; c.spi.txb[11] = 8'h44;
        c.spi.build(8'h10, 7, n); raw(n, 9);
        status(g_crc, g_frame, g_busy);
        expect16("P4 FRAME_ERRORS + 1", g_frame, e_frame + 16'd1);
        expect1("P4 nothing written at word $21", c.u301.mem[33] === 16'hxxxx, 1'b1);
        // ---------------- P5 SCK stops in mid-byte, then CS high
        ready; c.spi.cs_n = 1'b0; #(200.0);
        for (k = 0; k < 5; k = k + 1) begin #(50.0); c.spi.sck = 1'b1; #(50.0); c.spi.sck = 1'b0; end
        #(500.0); c.spi.cs_n = 1'b1; #(2000.0);
        status(g_crc, g_frame, g_busy);
        expect16("P5 interrupted byte: FRAME_ERRORS + 2", g_frame, e_frame + 16'd2);
        // ---------------- P6 oversize LEN, P7 wrong major version
        load(64'ha1_10_0a_01_2c_00_00_00, 8); c.spi.txb[5] = 8'h00;
        crc = 16'hFFFF; for (i = 0; i < 6; i = i + 1) crc = c.spi.crc_upd(crc, c.spi.txb[i]);
        c.spi.txb[6] = crc[15:8]; c.spi.txb[7] = crc[7:0]; raw(8, 40);
        c.spi.txb[0] = 8'hA2; c.spi.build(8'h01, 0, n); c.spi.txb[0] = 8'hA2;          // major 2
        crc = 16'hFFFF; for (i = 0; i < 5; i = i + 1) crc = c.spi.crc_upd(crc, c.spi.txb[i]);
        c.spi.txb[5] = crc[15:8]; c.spi.txb[6] = crc[7:0]; raw(7, 7);
        status(g_crc, g_frame, g_busy);
        expect16("P6/P7 oversize and wrong-version frames rejected", g_frame, e_frame + 16'd4);
        // ---------------- P8 V6 error responses (nothing executed)
        c.spi.transact(8'h7F, 0, 0, ok, rc); expect16("P8 unknown command: ERR_CMD", {7'd0, ok, rc}, 16'h0101);
        c.spi.txb[5] = 8'h00; c.spi.txb[6] = 8'h00; c.spi.txb[7] = 8'h40; c.spi.txb[8] = 8'h00;
        c.spi.transact(8'h11, 4, 0, ok, rc); expect16("P8 SRAM_READ N = 0: ERR_ARG", {7'd0, ok, rc}, 16'h0103);
        c.spi.txb[5] = 8'h03; c.spi.txb[6] = 8'hFF; c.spi.txb[7] = 8'hFF; c.spi.txb[8] = 8'h02;
        c.spi.transact(8'h11, 4, 0, ok, rc); expect16("P8 SRAM_READ past the end: ERR_ARG", {7'd0, ok, rc}, 16'h0103);
        c.spi.txb[5] = 8'h00; c.spi.transact(8'h01, 1, 0, ok, rc); expect16("P8 IDENTIFY with LEN 1: ERR_LEN", {7'd0, ok, rc}, 16'h0102);
        c.spi.txb[5] = 8'd16; c.spi.transact(8'h21, 1, 0, ok, rc); expect16("P8 REG_READ index 16: ERR_ARG", {7'd0, ok, rc}, 16'h0103);
        // ---------------- P9 GET_RESPONSE is idempotent (R2)
        c.spi.transact(8'h01, 0, 8, ok, rc);
        get_resp(8); for (i = 0; i < 16; i = i + 1) shadow[i] = c.spi.rxb[i];
        get_resp(8); n = 0; for (i = 0; i < 16; i = i + 1) if (shadow[i] !== c.spi.rxb[i]) n = n + 1;
        expect16("P9 repeated GET_RESPONSE identical", n, 16'd0);
        // ---------------- P10 busy frame during a 128-word burst: rejected, burst completes
        status(e_crc, e_frame, e_busy);
        for (i = 0; i < 128; i = i + 1) begin c.spi.buf_w[i] = 16'h4000 + i * 3; end
        c.spi.txb[5] = 8'h00; c.spi.txb[6] = 8'h10; c.spi.txb[7] = 8'h00;
        for (i = 0; i < 128; i = i + 1) begin c.spi.txb[8 + 2 * i] = c.spi.buf_w[i][15:8]; c.spi.txb[9 + 2 * i] = c.spi.buf_w[i][7:0]; end
        c.spi.build(8'h10, 259, n); seqv = c.spi.seq; ready; c.spi.frame(n, n);
        expect1("P10 not READY right after the burst frame", c.spi_attn, 1'b0);
        c.spi.build(8'h02, 0, n); c.spi.frame(n, n);          // violates ATTN: busy frame
        get_resp(0);
        expect16("P10 response belongs to the burst", {8'd0, c.spi.rxb[2]}, {8'd0, seqv[7:0]});
        n = 0; for (i = 0; i < 128; i = i + 1) if (c.u301.mem[18'h01000 + i] !== 16'h4000 + i * 3) n = n + 1;
        expect16("P10 all 128 burst words written", n, 16'd0);
        status(g_crc, g_frame, g_busy);
        expect16("P10 BUSY_REJECTS + 1", g_busy, e_busy + 16'd1);
        // ---------------- P11 maximum bursts and ECHO 256
        for (i = 0; i < 128; i = i + 1) c.spi.buf_w[i] = $random(c.spi.seed);
        c.spi.burst_wr(18'h02000, 128); c.spi.burst_rd(18'h02000, 128);
        n = 0; for (i = 0; i < 128; i = i + 1) if (c.spi.buf_r[i] !== c.spi.buf_w[i]) n = n + 1;
        expect16("P11 128-word write/read back", n, 16'd0);
        for (i = 0; i < 256; i = i + 1) c.spi.txb[5 + i] = i ^ 8'h5A;
        c.spi.transact(8'h05, 256, 256, ok, rc);
        n = 0; for (i = 0; i < 256; i = i + 1) if (c.spi.rxb[6 + i] !== (i ^ 8'h5A)) n = n + 1;
        expect16("P11 ECHO 256 bytes", {7'd0, ok, rc}, 16'h0100); expect16("P11 ECHO data", n, 16'd0);
        // ---------------- P12 counters and RESET_LINK
        c.spi.transact(8'h04, 0, 0, ok, rc);
        status(g_crc, g_frame, g_busy);
        expect16("P12 counters cleared", g_crc | g_frame | g_busy, 16'd0);
        // ---------------- P13 X4 power lost in mid-frame: nothing commits, link recovers
        c.spi.txb[5] = 8'h00; c.spi.txb[6] = 8'h30; c.spi.txb[7] = 8'h00; c.spi.txb[8] = 8'hBE; c.spi.txb[9] = 8'hEF;
        c.spi.build(8'h10, 5, n); ready;
        fork : p13
            c.spi.frame(n, n);
            begin #(3000.0); x4_on = 1'b0; end
        join
        #(5000.0);
        expect1("P13 FPGA idle while the X4 is off (no interrupt)", c.spi_irq_n, 1'b1);
        x4_on = 1'b1; c.spi.abort; #(5000.0);
        expect1("P13 nothing written by the interrupted frame", c.u301.mem[18'h03000] === 16'hxxxx, 1'b1);
        c.spi.xfer(1'b0, 1'b1, 18'h03001, 2'b11, 16'h600D, d); c.spi.xfer(1'b0, 1'b0, 18'h03001, 2'b11, 16'h0, d);
        expect16("P13 link works after the X4 returns", d, 16'h600D);
        // ---------------- P14 FPGA reload during a burst: no false interrupt, link recovers
        for (i = 0; i < 128; i = i + 1) c.spi.buf_w[i] = 16'h7000 + i;
        fork : p14
            c.spi.burst_wr(18'h04000, 128);
            begin @(posedge c.dut.u_lbus.h_ld_oe); #(500.0); fpga_cfg = 1'b0; #(3000.0); disable p14; end
        join
        c.spi.abort; #(1000.0); fpga_cfg = 1'b1;
        get_resp(8);
        expect16("P14 after reload: power-on IDENTIFY response", {c.spi.rxb[2], c.spi.rxb[3]}, 16'hFF00);
        c.spi.xfer(1'b0, 1'b0, 18'h03001, 2'b11, 16'h0, d);
        expect16("P14 SRAM kept over the reload", d, 16'h600D);
        // ---------------- P16 RP2040 reset with the X4 powered (independent reset, owner requirement 7);
        // run before the random sweep P15, at the nominal timing.
        // The RP2040 pads reset to inputs with pull-down [V S65]: the FPGA sees CS_N asserted with no clock
        // until firmware drives CS_N high. Nothing may execute or commit, no interrupt, ATTN low meanwhile.
        status(e_crc, e_frame, e_busy);
        c.rp_rst = 1'b1; #(20000.0);                       // reset between frames: a zero-byte frame
        expect1("P16 FPGA ATTN low while the RP2040 reset holds CS_N low", c.f_attn, 1'b0);
        expect1("P16 no host interrupt during the RP2040 reset", c.RP_IRQ_N, 1'b1);
        c.rp_rst = 1'b0; #(2000.0);
        c.spi.txb[5] = 8'h00; c.spi.txb[6] = 8'h30; c.spi.txb[7] = 8'h02; c.spi.txb[8] = 8'hDE; c.spi.txb[9] = 8'hAD;
        c.spi.build(8'h10, 5, n); ready;
        fork : p16
            c.spi.frame(n, n);
            begin #(3000.0); c.rp_rst = 1'b1; end         // reset in mid-frame: SCK stops, CS_N stays low
        join
        #(20000.0);
        expect1("P16 FPGA ATTN low while CS_N is held low", c.f_attn, 1'b0);
        expect1("P16 no host interrupt after the mid-frame reset", c.RP_IRQ_N, 1'b1);
        c.spi.abort; c.rp_rst = 1'b0; #(5000.0);           // firmware: CS_N high first, then the SPI pins
        expect1("P16 nothing written by the interrupted frame", c.u301.mem[18'h03002] === 16'hxxxx, 1'b1);
        status(g_crc, g_frame, g_busy);
        expect16("P16 FRAME_ERRORS + 2 (zero-byte and interrupted frames)", g_frame, e_frame + 16'd2);
        expect16("P16 no CRC or busy counts", (g_crc - e_crc) | (g_busy - e_busy), 16'd0);
        c.spi.xfer(1'b0, 1'b1, 18'h03002, 2'b11, 16'h0B07, d); c.spi.xfer(1'b0, 1'b0, 18'h03002, 2'b11, 16'h0, d);
        expect16("P16 link works after the RP2040 reset", d, 16'h0B07);
        // ---------------- P15 random sweep: SCK rate, input skew, CS timing, clock phase (HL-2 ratios)
        for (n = 0; n < 1024; n = n + 128) begin            // define the region first: a read of a never-
            for (i = 0; i < 128; i = i + 1) begin             // written word is X in the SRAM model, and X
                c.spi.buf_w[i] = $random(c.spi.seed);         // poisons the response CRC (a model artefact)
                shadow[n + i] = c.spi.buf_w[i];
            end
            c.spi.burst_wr(18'h05000 + n, 128);
        end
        c.spi.verbose = 1'b1;
        for (k = 0; k < 60; k = k + 1) begin
            c.spi.half = HALF_MIN + ($unsigned($random(c.spi.seed)) % 1000) * (HALF_MAX - HALF_MIN) / 1000.0;
            c.spi.rx_skew = ($unsigned($random(c.spi.seed)) % 1000) * SKEW_MAX / 1000.0;
            c.spi.t_css = 100.0 + ($unsigned($random(c.spi.seed)) % 400);
            c.spi.t_csh = 100.0 + ($unsigned($random(c.spi.seed)) % 400);
            c.spi.t_csw = 1000.0 + ($unsigned($random(c.spi.seed)) % 3000);
            n = $unsigned($random(c.spi.seed)) % 1000;
            if ($random(c.spi.seed) & 1) begin
                d = $random(c.spi.seed); c.spi.xfer(1'b0, 1'b1, 18'h05000 + n, 2'b11, d, crc); shadow[n] = d;
            end else begin
                c.spi.xfer(1'b0, 1'b0, 18'h05000 + n, 2'b11, 16'h0, d);
                expect16("P15 random read back", d, shadow[n]);
            end
        end
        // ---------------- summary
        errors = errors + c.spi.errors;
        $display("tb_spi: frames %0d, retries %0d, SPI BFM errors %0d", c.spi.frames, c.spi.retries, c.spi.errors);
        if (errors == 0) $display("TB_RESULT PASS tb_spi SEED=%0d LAUNCH_RISE=%0d errors=0 checks=%0d", SEED, LAUNCH_RISE, checks);
        else $display("TB_RESULT FAIL tb_spi SEED=%0d LAUNCH_RISE=%0d errors=%0d checks=%0d", SEED, LAUNCH_RISE, errors, checks);
        $finish;
    end
    initial begin #(200.0e6); $display("TB_RESULT FAIL tb_spi timeout"); $finish; end
endmodule
