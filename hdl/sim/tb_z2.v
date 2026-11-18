// SPDX-License-Identifier: MIT
// Bus-functional testbench for the Zorro II interface (sheet 1 rev B + z2_top RTL).
// Covers C-02 (address transitions near /AS), C-03/C-04 (arming, transparency), C-05 (data
// buffer enable/direction, DOE, /AS release, reset, wait states, bus errors) and C-13 (RMW).
// Every check failure prints "ASSERT-FAIL"; the run script fails on any such line.
// Parameters: SEED (delay skew and random timing), FPGA_TMAX (FPGA pin-to-pin allocation, ns).
`timescale 1ns/1ps
`ifndef DLY_MODE
`define DLY_MODE 0
`endif
module tb_z2;
    parameter integer SEED      = 1;
    parameter real    FPGA_TMAX = 18.0;

    integer errors = 0, checks = 0, false_slave = 0;
    reg     char_mode = 1'b0;            // C-02 characterisation: count false /SLAVEn, do not fail
    reg     relax     = 1'b0;            // deliberately abnormal cycles: skip the normal-cycle timing checks
    integer tseed     = 1;

    task fail;
        input [8*100-1:0] msg;
        begin
            errors = errors + 1;
            if (errors <= 60) $display("ASSERT-FAIL %0t %0s", $realtime, msg);
        end
    endtask
    task expect16;
        input [8*60-1:0] what;
        input [15:0] got, want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                errors = errors + 1;
                if (errors <= 60) $display("ASSERT-FAIL %0t %0s: got %h want %h", $realtime, what, got, want);
            end
        end
    endtask
    task expect1;
        input [8*60-1:0] what;
        input got, want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                errors = errors + 1;
                if (errors <= 60) $display("ASSERT-FAIL %0t %0s: got %b want %b", $realtime, what, got, want);
            end
        end
    endtask

    // ------------------------------------------------------------------ clocks
    reg clk = 1'b0;
    initial begin
        #(0.37 + (SEED % 17));                      // arbitrary phase against the 7 MHz clock
        forever #10.0 clk = ~clk;                   // 50 MHz core clock [A]
    end

    // ------------------------------------------------------------------ slot / backplane
    wire [23:1] Z_A;
    wire        Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, clk7;
    wire [15:0] Z_D;
    m_bushold #(.W(16)) u_dhold (.bus(Z_D));
    tri1 Z_SLAVE_N;                                  // A2000 RP800 1k pull-up (sheet 8 of the R6 schematic)
    tri0 Z_CFGOUT_N;                                 // A2000 RP607 1k pull-down (sheet 6)
    tri1 Z_XRDY, Z_INT2_N, Z_INT6_N, Z_BERR_N;
    reg  Z_CFGIN_N = 1'b0, Z_BUSRST_N = 1'b0;
    reg  pwr3 = 1'b0, pwr5 = 1'b0, jumper = 1'b0, fpga_cfg = 1'b0;
    reg  dip_mode_b = 1'b0, dip_int6 = 1'b0, dip_disable = 1'b0;

    z2_master m (.A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N), .READ(Z_READ), .DOE(Z_DOE),
                 .D(Z_D), .XRDY(Z_XRDY), .BERR_N(Z_BERR_N), .clk7(clk7));

    wire d_drv, ld_conflict, card_en_n, en_ok;
    card_model #(.SEED(SEED), .FPGA_TMAX(FPGA_TMAX), .SUP_TD(5000.0)) c (
        .Z_A(Z_A), .Z_AS_N(Z_AS_N), .Z_UDS_N(Z_UDS_N), .Z_LDS_N(Z_LDS_N), .Z_READ(Z_READ), .Z_DOE(Z_DOE),
        .Z_E7M(clk7), .Z_CFGIN_N(Z_CFGIN_N), .Z_BUSRST_N(Z_BUSRST_N), .Z_BERR_N(Z_BERR_N),
        .Z_D(Z_D), .Z_SLAVE_N(Z_SLAVE_N), .Z_CFGOUT_N(Z_CFGOUT_N), .Z_XRDY(Z_XRDY),
        .Z_INT2_N(Z_INT2_N), .Z_INT6_N(Z_INT6_N),
        .clk_core(clk), .pwr3(pwr3), .pwr5(pwr5), .jumper(jumper), .fpga_cfg(fpga_cfg),
        .dip_mode_b(dip_mode_b), .dip_int6(dip_int6), .dip_disable(dip_disable),
        .d_drv(d_drv), .ld_conflict(ld_conflict), .card_en_n(card_en_n), .en_ok(en_ok));

    // ------------------------------------------------------------------ reference model
    reg       r_armed = 1'b0, r_cfg = 1'b0, r_shut = 1'b0, r_mode_b = 1'b0, r_zw = 1'b0;
    reg [7:0] r_base = 8'h00;
    reg       exp_sel = 1'b0;

    function ref_sel;
        input [23:1] a;
        begin
            ref_sel = r_armed && ((!r_cfg && !r_shut && (Z_CFGIN_N === 1'b0) && (a[23:16] == 8'hE8)) ||
                                  (r_cfg && (r_mode_b ? (a[23:19] == r_base[7:3]) : (a[23:16] == r_base))));
        end
    endfunction

    function [3:0] ref_ac;                           // physical AutoConfig nibble at byte offset off
        input [7:0] off;
        input       mb;
        reg   [7:0] v;
        begin
            case (off[7:2])
                6'd0:    v = mb ? 8'hC4 : 8'hC1;     // er_Type
                6'd1:    v = 8'h01;                  // er_Product
                6'd2:    v = mb ? 8'h80 : 8'h00;     // er_Flags
                6'd4:    v = 8'h07;                  // manufacturer 2011 = $07DB
                6'd5:    v = 8'hDB;
                6'd9:    v = 8'h01;                  // serial ...0001
                default: v = 8'h00;
            endcase
            ref_ac = off[1] ? v[3:0] : v[7:4];
            if (off[7:2] != 6'd0) ref_ac = ~ref_ac;
        end
    endfunction

    // ------------------------------------------------------------------ continuous checkers
    // C1  Zorro data-bus contention between the card (U103 B port) and the master
    always @(d_drv or m.mdrv)
        if (d_drv && m.mdrv) fail("C1 Z_D contention: card and master driving together");

    // C2  the card may drive Z_D only for a valid read of this card; release allowance T_REL
    real T_REL;
    initial T_REL = 4.9 + FPGA_TMAX + 3.8 + 6.3 + 2.0;   // U102 + FPGA + U107 + U103 disable + margin
    wire valid_rd = (Z_AS_N === 1'b0) && (Z_SLAVE_N === 1'b0) && (Z_READ === 1'b1) && (Z_DOE === 1'b1) &&
                    ((Z_UDS_N === 1'b0) || (Z_LDS_N === 1'b0)) && (Z_BERR_N !== 1'b0);
    real t_valid = -1.0e9;
    reg  c2_reported = 1'b0;
    always #0.5 begin
        if (valid_rd) t_valid = $realtime;
        else if (d_drv && (($realtime - t_valid) > T_REL) && !c2_reported) begin
            fail("C2 card drives Z_D outside a valid read of this card (beyond release allowance)");
            c2_reported = 1'b1;
        end
    end
    always @(negedge Z_AS_N) c2_reported = 1'b0;

    // C5  /SLAVEn: no false assertion; <= 35 ns assertion; <= 50 ns release; no glitch
    real t_as_rise = -1.0e9;                                // last /AS negation at the slot
    always @(posedge Z_AS_N) t_as_rise = $realtime;
    // For a selected address /SLAVEn may still fall up to the path delay after a runt /AS has
    // been released (it is a delayed copy of /AS); for an unselected address it may never fall.
    real T_SLAG;
    initial T_SLAG = 4.9 + FPGA_TMAX + 6.4 + 2.0;          // U102 + FPGA + U104 + R117/load
    always @(negedge Z_SLAVE_N)
        if ($realtime > 1.0 && !(exp_sel && ((Z_AS_N === 1'b0) || (($realtime - t_as_rise) <= T_SLAG)))) begin
            if (char_mode) false_slave = false_slave + 1;
            else fail("C5a false /SLAVEn assertion (unselected address or /AS negated)");
        end
    always @(negedge Z_AS_N) begin : c5b
        reg e;
        e = exp_sel;
        #35.0;
        checks = checks + 1;
        if (!char_mode && !relax) begin
            if (e && (Z_SLAVE_N !== 1'b0)) fail("C5b /SLAVEn not asserted within 35 ns of /AS");
            if (!e && (Z_SLAVE_N !== 1'b1)) fail("C5b /SLAVEn asserted for an unselected cycle");
        end
    end
    always @(posedge Z_AS_N) begin : c5c
        #50.0;
        checks = checks + 1;
        if ((Z_AS_N === 1'b1) && (Z_SLAVE_N !== 1'b1)) fail("C5c /SLAVEn not negated within 50 ns of /AS negation");
    end
    always @(posedge Z_SLAVE_N)
        if (exp_sel && (Z_AS_N === 1'b0) && (($realtime - m.t_as) > 35.0) && !char_mode && !relax)
            fail("C5d /SLAVEn glitched high during a selected cycle");

    // C6  XRDY: only for selected cycles in gated mode; <= 60 ns after /AS; released after /AS; bounded
    // C6a allows the card's path delay: XRDY may still assert just after a runt /AS has
    // been released (U102 + FPGA + U107 + U105 + edge), but never for an unselected cycle.
    real T_XLAG;
    initial T_XLAG = 4.9 + FPGA_TMAX + 3.8 + 3.6 + 2.0;
    always @(negedge Z_XRDY)
        if (!(exp_sel && !r_zw && ((Z_AS_N === 1'b0) || (($realtime - t_as_rise) <= T_XLAG))) && !char_mode)
            fail("C6a XRDY held for an unselected cycle, in zero-wait mode or outside /AS (+ path delay)");
    always @(negedge Z_AS_N) begin : c6b
        reg e;
        e = exp_sel && !r_zw;
        #60.0;
        checks = checks + 1;
        if (e && (Z_XRDY !== 1'b0) && !char_mode && !relax) fail("C6b XRDY not negated within 60 ns of /AS");
    end
    always @(posedge Z_AS_N) begin : c6c
        #40.0;
        if (Z_XRDY !== 1'b1) fail("C6c XRDY not released within 40 ns of /AS negation");
    end
    real t_xrdy_low = 0.0;
    always @(negedge Z_XRDY) t_xrdy_low = $realtime;
    always @(posedge Z_XRDY)
        if (($realtime - t_xrdy_low) > 2300.0) fail("C6d XRDY held longer than the watchdog bound (2.0 us + 0.3 us latency)");

    // C7  a disabled card (CARD_EN_N high) must look like an empty slot
    always @(posedge clk) begin : c7
        if ((card_en_n === 1'b1) && (Z_AS_N === 1'b1) && !c.u104_drv) begin
            if (Z_SLAVE_N !== 1'b1)  fail("C7 disabled card: /SLAVEn not released");
            if (Z_CFGOUT_N !== 1'b0) fail("C7 disabled card: /CFGOUTn not passed by the backplane pull-down");
            if (d_drv)               fail("C7 disabled card: data bus driven");
        end
    end

    // ------------------------------------------------------------------ bus helpers
    reg [15:0] rdv;
    reg        bev;
    task bus;                                        // one cycle with the reference select
        input integer kind;
        input [23:0]  a24;
        input [1:0]   lanes;
        input [15:0]  wd;
        begin
            exp_sel = ref_sel(a24[23:1]);
            m.cycle(kind, a24[23:1], lanes, wd, rdv, bev);
            checks = checks + 1;
            if (exp_sel && !r_zw && !bev && (m.last_waits < 1))
                fail("selected cycle completed without an XRDY wait state in gated mode");
            if (r_zw && (m.last_waits != 0)) fail("zero-wait mode: wait states inserted");
            exp_sel = 1'b0;
        end
    endtask
    task rd16;  input [23:0] a; output [15:0] d; begin bus(0, a, 2'b11, 16'h0); d = rdv; end endtask
    task wr16;  input [23:0] a; input [15:0] d;  begin bus(1, a, 2'b11, d); end endtask
    task wr8;   input [23:0] a; input [7:0] d;   begin bus(1, a, a[0] ? 2'b01 : 2'b10, {d, d}); end endtask
    task tas8;  input [23:0] a;                  begin bus(2, a, a[0] ? 2'b01 : 2'b10, 16'h0); end endtask

    task zorro_reset;                                // /BUSRST pulse (scaled; real >= 17.5 us)
        input real len;
        begin
            Z_BUSRST_N = 1'b0;
            r_cfg = 1'b0; r_shut = 1'b0;
            #(len);
            r_armed = en_ok && !dip_disable;
            r_mode_b = dip_mode_b;
            Z_BUSRST_N = 1'b1;
            #(2000.0);
            r_zw = 1'b0;
        end
    endtask

    task autoconfig_check_and_configure;             // expansion.library-style sequence
        input [7:0] base;
        input       mb;
        integer off;
        reg [15:0] d;
        reg [23:0] a;
        begin
            for (off = 0; off < 8'h80; off = off + 2) begin
                a = 24'hE80000 + off;
                if (off[2]) bus(0, a, 2'b10, 16'h0); else bus(0, a, 2'b11, 16'h0);
                d = rdv;
                checks = checks + 1;
                if ((d[15:12] !== ref_ac(off[7:0], mb)) || (d[11:0] !== 12'hFFF)) begin
                    errors = errors + 1;
                    $display("ASSERT-FAIL %0t AutoConfig offset %h: got %h want %h_FFF", $realtime, off, d,
                             ref_ac(off[7:0], mb));
                end
            end
            wr8(24'hE8004A, {base[3:0], 4'h0});      // A19..A16 first, as the OS does
            wr8(24'hE80048, {base[7:4], 4'h0});      // A23..A20: configures at the end of the cycle
            r_cfg = 1'b1; r_base = base;
            #(500.0);
            expect1("/CFGOUTn asserted after configuration", Z_CFGOUT_N, 1'b0);
        end
    endtask

    // ------------------------------------------------------------------ test sequence
    reg [15:0] d;
    reg [23:0] q24, p24;
    integer    i, k, s_idx;
    reg [23:0] B;                                     // board base address

    initial begin
        m.seed = SEED; tseed = SEED * 31 + 7;
        $display("tb_z2: SEED=%0d FPGA_TMAX=%0.1f ns DLY_MODE=%0d", SEED, FPGA_TMAX, `DLY_MODE);

        // ---------------- T0 power-up, startup transparency, arming inside reset (C-03, C-04)
        #(100.0);  pwr5 = 1'b1;                       // Molex 5 V first [A]
        #(300.0);  pwr3 = 1'b1;
        #(200.0);
        expect1("T0 unconfigured FPGA: card disabled", card_en_n, 1'b1);
        #(1000.0); fpga_cfg = 1'b1;                    // configuration complete (scaled from 1.4 ms)
        #(1000.0);
        expect1("T0 before EN_OK: card disabled", card_en_n, 1'b1);
        expect1("T0 before EN_OK: /CFGOUTn passed by backplane", Z_CFGOUT_N, 1'b0);
        wait (en_ok === 1'b1);
        #(2000.0);
        expect1("T0 armed during /BUSRST", c.dut.u_core.armed, 1'b1);
        expect1("T0 armed: card enabled", card_en_n, 1'b0);
        expect1("T0 armed, unconfigured: /CFGOUTn driven negated", Z_CFGOUT_N, 1'b1);
        r_armed = 1'b1;
        Z_BUSRST_N = 1'b1;
`ifdef HOST_BG
        // Stage 3: continuous random host (SPI-side) SRAM traffic in a private region for the
        // rest of the run. Every Zorro check must still pass (arbitration cannot disturb Zorro).
        c.dut.u_host.bg_base = 18'h20000; c.dut.u_host.bg_gap = 3; c.dut.u_host.bg_en = 1'b1;
        $display("tb_z2: host background traffic ON (SRAM words %h-%h)", 18'h20000, 18'h20FFF);
`endif
        #(3000.0);

        // ---------------- T1/T2 AutoConfig (mode A), configure at $E90000
        autoconfig_check_and_configure(8'hE9, 1'b0);
        B = 24'hE90000;
        bus(0, 24'hE80000, 2'b11, 16'h0);              // no longer answers at $E8 (C5 checks)

        // ---------------- T3 registers, word and byte writes
        rd16(B + 24'h0, d);  expect16("MAGIC", d, 16'h4252);
        rd16(B + 24'h2, d);  expect16("VERSION", d, 16'h0A02);
        rd16(B + 24'h4, d);  expect16("STATUS", d, 16'h0600);
        wr16(B + 24'h6, 16'h0050); rd16(B + 24'h6, d); expect16("CONTROL", d, 16'h0050);
        wr16(B + 24'h6, 16'h0000);
        wr16(B + 24'h8, 16'h1234); rd16(B + 24'h8, d); expect16("SCRATCH0 word", d, 16'h1234);
        wr8 (B + 24'h8, 8'hAB);    rd16(B + 24'h8, d); expect16("SCRATCH0 UDS byte", d, 16'hAB34);
        wr8 (B + 24'h9, 8'hCD);    rd16(B + 24'h8, d); expect16("SCRATCH0 LDS byte", d, 16'hABCD);
        wr16(B + 24'hA, 16'h5AA5); rd16(B + 24'hA, d); expect16("SCRATCH1", d, 16'h5AA5);
        // Stage 3: the rest of the window is the shared SRAM (sheet 3)
        wr16(B + 24'h1000, 16'h3C5A); rd16(B + 24'h1000, d); expect16("SRAM fixed window word", d, 16'h3C5A);
        wr8 (B + 24'h1001, 8'hE1);   rd16(B + 24'h1000, d); expect16("SRAM LDS byte", d, 16'h3CE1);
        wr8 (B + 24'h1000, 8'h7B);   rd16(B + 24'h1000, d); expect16("SRAM UDS byte", d, 16'h7BE1);

        // ---------------- T4 RMW (TAS) with byte strobes, DOE variants, write-drive timing (C-13)
        for (k = 0; k < 4; k = k + 1) begin
            m.doe_rmw_mode = k % 2;
            m.mdrv_delay   = (k < 2) ? 0.0 : 30.0;
            wr16(B + 24'h8, 16'h2B4C);
            tas8(B + 24'h8); expect16("TAS read portion (UDS)", rdv, 16'h2B4C);
            rd16(B + 24'h8, d); expect16("TAS even byte result", d, 16'hAB4C);
            tas8(B + 24'h9); expect16("TAS read portion (LDS)", rdv, 16'hAB4C);
            rd16(B + 24'h8, d); expect16("TAS odd byte result", d, 16'hABCC);
        end
        rd16(B + 24'h18, d); expect16("RMW_CYCLES", d, 16'd8);
        m.doe_rmw_mode = 0; m.mdrv_delay = 0.0;

        // ---------------- T5 DOE assertion / release sweep (C-05)
        for (k = 0; k < 12; k = k + 1) begin
            m.doe_rd_on = (k % 4 == 0) ? 0.0 : (k % 4 == 1) ? 30.0 : (k % 4 == 2) ? 70.0 : 140.0;
            m.doe_off   = (k / 4 == 0) ? -30.0 : (k / 4 == 1) ? 0.0 : 30.0;
            rd16(B + 24'h0, d); expect16("DOE sweep MAGIC", d, 16'h4252);
            rd16(B + 24'h8, d); expect16("DOE sweep SCRATCH0", d, 16'hABCC);
            tas8(B + 24'hB);
        end
        m.doe_rd_on = 30.0; m.doe_off = 0.0;
        rd16(B + 24'hA, d); expect16("SCRATCH1 after DOE-sweep TAS", d, 16'h5AA5 | 16'h0080);

        // ---------------- T6 address transitions near /AS (C-02)
        for (s_idx = 0; s_idx < 3; s_idx = s_idx + 1) begin
            m.setup_ns = (s_idx == 0) ? 20.0 : (s_idx == 1) ? 10.0 : 5.0;
            for (i = 0; i < 60; i = i + 1) begin
                m.skew_ns = ($random(tseed) & 15);
                // previous cycle: random, half of them to the board window (selected)
                p24 = ($random(tseed) & 1) ? (B | ($random(tseed) & 24'h00FFFE)) : ($random(tseed) & 24'hFFFFFE);
                bus(0, p24, 2'b11, 16'h0);
                // next cycle: an UNSELECTED address that differs from the window in 1..3 high bits
                q24 = B ^ (24'h010000 << ($random(tseed) & 7)) ^ (($random(tseed) & 1) ? (24'h010000 << ($random(tseed) & 7)) : 24'h0);
                q24 = (q24 & 24'hFF0000) | ($random(tseed) & 24'h00FFFE);
                if (q24[23:16] == B[23:16]) q24 = q24 ^ 24'h800000;
                bus(0, q24, 2'b11, 16'h0);
                bus(0, B | ($random(tseed) & 24'h000FFE), 2'b11, 16'h0);   // selected again
            end
        end
        m.setup_ns = 25.0; m.skew_ns = 10.0;
        // characterisation only (not pass/fail): setups at and below the buffer skew
        char_mode = 1'b1;
        for (s_idx = 0; s_idx < 3; s_idx = s_idx + 1) begin
            false_slave = 0;
            m.setup_ns = (s_idx == 0) ? 2.0 : (s_idx == 1) ? 0.0 : -5.0;
            for (i = 0; i < 60; i = i + 1) begin
                m.skew_ns = 0.0;
                bus(0, B | ($random(tseed) & 24'h00FFFE), 2'b11, 16'h0);
                bus(0, (B ^ 24'h010000) | ($random(tseed) & 24'h00FFFE), 2'b11, 16'h0);
            end
            $display("C-02 characterisation: slot setup %0.1f ns -> %0d false /SLAVEn pulses in 60 transitions",
                     m.setup_ns, false_slave);
        end
        char_mode = 1'b0;
        m.setup_ns = 25.0; m.skew_ns = 10.0;
        #(500.0);

        // ---------------- T7 bus errors (/BERR) during read, write and RMW (C-05)
        m.berr_at = 260.0; rd16(B + 24'h8, d);
        m.berr_at = 120.0; rd16(B + 24'h8, d);
        m.berr_at = 260.0; wr16(B + 24'hA, 16'h1111);
        m.berr_at = 200.0; tas8(B + 24'h8);
        m.berr_at = -1.0;
        rd16(B + 24'h0, d); expect16("MAGIC after bus errors", d, 16'h4252);
        rd16(B + 24'h1A, d);
        checks = checks + 1;
        if (d < 16'd4) fail("BERR_EVENTS did not count the injected bus errors");

        // ---------------- T8 early /AS release and arbitrary strobe/DOE timing (abort robustness)
        relax = 1'b1;
        for (k = 0; k < 8; k = k + 1) begin
            exp_sel = 1'b1;
            m.raw_cycle(B[23:1] | 23'h4, 1'b1, 2'b11, 20.0 + 45.0 * k, 0.0, 15.0 + 40.0 * k, 10.0 * k, 300.0);
            exp_sel = 1'b1;
            m.raw_cycle(B[23:1] | 23'h5, 1'b0, 2'b11, 30.0 + 50.0 * k, 25.0 * k, 400.0, 0.0, 400.0);
            exp_sel = 1'b0;
        end
        // T8b: address changes from unselected to selected while /AS is held 3 us (illegal).
        // The FSM ignored the cycle at START, so XRDY must not be held (C6d bounds it).
        exp_sel = 1'b1;
        m.raw_addr_change((B[23:1] ^ 23'h400000), (B[23:1] | 23'h4), 200.0, 3000.0);
        exp_sel = 1'b0;
        relax = 1'b0;
        rd16(B + 24'h0, d); expect16("MAGIC after aborted cycles", d, 16'h4252);

        // ---------------- T9 watchdog (simulation stall hook)
        wr16(B + 24'hA, 16'h5AA5);                     // known value (T7/T8 writes may or may not have landed)
        force c.dut.u_core.stall_test = 1'b1;
        rd16(B + 24'h8, d); expect16("watchdog read returns $FFFF", d, 16'hFFFF);
        wr16(B + 24'hA, 16'h3333);                     // discarded
        release c.dut.u_core.stall_test;
        rd16(B + 24'h16, d); expect16("WDOG_EVENTS", d, 16'd2);
        rd16(B + 24'h4, d);  expect1("STATUS b8 watchdog flag", d[8], 1'b1);
        wr8 (B + 24'h6, 8'h01);                        // CONTROL b8 W1C (high byte only)
        rd16(B + 24'h4, d);  expect1("STATUS b8 cleared", d[8], 1'b0);
        rd16(B + 24'hA, d);  expect16("SCRATCH1 unchanged by discarded write", d[15:8], 8'h5A);

        // ---------------- T10 zero-wait mode (opt-in; gate G-ZEROWAIT)
        wr16(B + 24'h6, 16'h0001); r_zw = 1'b1;
        rd16(B + 24'h0, d); expect16("zero-wait MAGIC", d, 16'h4252);
        wr16(B + 24'h8, 16'h7E81); rd16(B + 24'h8, d); expect16("zero-wait SCRATCH0", d, 16'h7E81);
        tas8(B + 24'h8); rd16(B + 24'h8, d); expect16("zero-wait TAS", d, 16'hFE81);
        wr16(B + 24'h6, 16'h0000); r_zw = 1'b0;
        rd16(B + 24'h0, d); expect16("back to gated mode", d, 16'h4252);

        // ---------------- T11 interrupts
        wr16(B + 24'h6, 16'h0002);                    // IRQ_EN, INT_SEL = INT2
        wr16(B + 24'h12, 16'h0001); #(500.0);
        expect1("INT2 asserted", Z_INT2_N, 1'b0); expect1("INT6 idle", Z_INT6_N, 1'b1);
        wr16(B + 24'h10, 16'h0001); #(500.0);
        expect1("INT2 released", Z_INT2_N, 1'b1);
        wr16(B + 24'h6, 16'h0006);                    // INT_SEL = INT6
        wr16(B + 24'h12, 16'h0001); #(500.0);
        expect1("INT6 asserted", Z_INT6_N, 1'b0); expect1("INT2 idle", Z_INT2_N, 1'b1);
        wr16(B + 24'h10, 16'h0001); wr16(B + 24'h6, 16'h0000); #(500.0);
        expect1("INT6 released", Z_INT6_N, 1'b1);

        // ---------------- T12 /BUSRST in the middle of a selected read, then re-AutoConfig
        fork
            rd16(B + 24'h8, d);
            begin @(negedge Z_AS_N); #(240.0); exp_sel = 1'b0; Z_BUSRST_N = 1'b0; r_cfg = 1'b0; end
        join
        #(20000.0);
        r_armed = en_ok && !dip_disable;
        Z_BUSRST_N = 1'b1; #(2000.0);
        expect1("after /BUSRST: /CFGOUTn negated (unconfigured)", Z_CFGOUT_N, 1'b1);
        autoconfig_check_and_configure(8'hEC, 1'b0);
        B = 24'hEC0000;
        rd16(B + 24'h8, d); expect16("SCRATCH0 survives /BUSRST", d, 16'hFE81);

        // ---------------- T13 shut-up
        zorro_reset(20000.0);
        wr8(24'hE8004C, 8'h00); r_shut = 1'b1; #(500.0);
        expect1("shut up: /CFGOUTn asserted", Z_CFGOUT_N, 1'b0);
        bus(0, 24'hE80000, 2'b11, 16'h0);             // must not answer (C5)

        // ---------------- T14 DIP disable -> never arms (transparent)
        dip_disable = 1'b1; zorro_reset(20000.0);
        expect1("DIP disable: not armed", c.dut.u_core.armed, 1'b0);
        expect1("DIP disable: card disabled", card_en_n, 1'b1);
        bus(0, 24'hE80000, 2'b11, 16'h0);
        dip_disable = 1'b0; zorro_reset(20000.0);
        expect1("DIP enable again: armed", c.dut.u_core.armed, 1'b1);

        // ---------------- T15 DISABLE jumper / EN_OK loss while running: no mid-operation join
        autoconfig_check_and_configure(8'hE9, 1'b0);
        B = 24'hE90000;
        jumper = 1'b1; r_armed = 1'b0; r_cfg = 1'b0; #(200.0);
        expect1("jumper: card disabled at once", card_en_n, 1'b1);
        bus(0, B, 2'b11, 16'h0);                       // no answer
        jumper = 1'b0; #(8000.0);                      // EN_OK returns (jumper is on the wired-AND net)
        expect1("jumper removed: still not armed (waits for /BUSRST)", c.dut.u_core.armed, 1'b0);
        bus(0, 24'hE80000, 2'b11, 16'h0);              // no answer
        zorro_reset(20000.0);
        expect1("re-armed at the next /BUSRST", c.dut.u_core.armed, 1'b1);

        // ---------------- T16 mode B (512 KB at $200000)
        dip_mode_b = 1'b1; zorro_reset(20000.0);
        autoconfig_check_and_configure(8'h20, 1'b1);
        B = 24'h200000;
        rd16(24'h200000, d); expect16("mode B MAGIC", d, 16'h4252);
        wr16(24'h27FFFE, 16'hBEEF); rd16(24'h27FFFE, d); expect16("mode B top of window (SRAM)", d, 16'hBEEF);
        bus(0, 24'h280000, 2'b11, 16'h0);              // just outside: no answer
        bus(0, 24'h1FFFFE, 2'b11, 16'h0);
        dip_mode_b = 1'b0;

        // ---------------- T17 FPGA reconfigured while the Amiga runs: transparent until /BUSRST
`ifdef HOST_BG
        // the host side quiesces before a reconfiguration (rule H-4, shared-memory spec section 5)
        c.dut.u_host.bg_en = 1'b0; wait (c.dut.u_host.busy == 1'b0);
`endif
        fpga_cfg = 1'b0; r_armed = 1'b0; r_cfg = 1'b0; #(2000.0);
        expect1("reconfiguring FPGA: card disabled", card_en_n, 1'b1);
        fpga_cfg = 1'b1; #(4000.0);
        expect1("reconfigured FPGA does not arm without /BUSRST", c.dut.u_core.armed, 1'b0);
        bus(0, 24'hE80000, 2'b11, 16'h0);
        zorro_reset(20000.0);
        expect1("reconfigured FPGA arms at /BUSRST", c.dut.u_core.armed, 1'b1);

        // ---------------- T18 carrier power lost while running: transparent, no back-drive
        pwr3 = 1'b0; pwr5 = 1'b0; r_armed = 1'b0; r_cfg = 1'b0; #(1000.0);
        expect1("unpowered: /SLAVEn released", Z_SLAVE_N, 1'b1);
        expect1("unpowered: /CFGOUTn passed", Z_CFGOUT_N, 1'b0);
        bus(0, 24'hE80000, 2'b11, 16'h0);

        #(1000.0);
`ifdef HOST_BG
        $display("tb_z2: host transfers %0d SRAM, latency mean %0.1f ns, max %0.1f ns; BFM errors %0d",
                 c.dut.u_host.n_sram, c.dut.u_host.sum_lat / (c.dut.u_host.n_sram + 1.0e-9),
                 c.dut.u_host.max_lat, c.dut.u_host.errors);
        errors = errors + c.dut.u_host.errors;
`endif
        errors = errors + c.u301.errors;
        $display("tb_z2: SRAM model writes %0d, read enables %0d, timing errors %0d", c.u301.writes, c.u301.reads,
                 c.u301.errors);
        $display("TB_RESULT %s tb_z2 SEED=%0d errors=%0d checks=%0d", (errors == 0) ? "PASS" : "FAIL",
                 SEED, errors, checks);
        $finish;
    end

    initial begin
        #(30_000_000.0);
        $display("ASSERT-FAIL timeout");
        $display("TB_RESULT FAIL tb_z2 SEED=%0d timeout", SEED);
        $finish;
    end
endmodule
