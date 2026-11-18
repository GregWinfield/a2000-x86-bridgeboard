// SPDX-License-Identifier: MIT
// Testbench for sheet 3 (shared SRAM, arbitration, queues and interrupts) on the full card model.
// Every check failure prints "ASSERT-FAIL"; the run script fails on any such line.
//   S1  Zorro SRAM: fixed window, banked window (BANK), byte lanes, aliasing
//   S2  coherence between the Zorro side and the host side (word and byte lanes)
//   S3  determinism: Zorro SRAM cycles with host traffic off and on. The local-bus action
//       happens at the same FPGA clock in every cycle, and the slot latency range is unchanged
//   S4  RMW (TAS) on SRAM with the host hammering the same word: no host access inside the cycle
//   S5  queues: both directions, level interrupts, full/space, epoch, ownership, format errors
//   S6  link reset by either side and by /BUSRST; events; Zorro enables cleared by /BUSRST
//   S7  host access in every Amiga state (reset, unconfigured, disabled); SRAM survives /BUSRST
//   S8  FPGA reload: SRAM deselected while blank, contents kept (host quiesced first)
//   S9  FPGA reconfiguration during a host write (characterisation: no contention, other words kept)
//   S10 watchdog and /BERR on SRAM cycles; S11 zero-wait mode on SRAM (characterisation, G-ZEROWAIT)
`timescale 1ns/1ps
module tb_shm;
    parameter integer SEED = 1;

    integer errors = 0, checks = 0, tseed = 1;
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

    // ------------------------------------------------------------------ clocks, slot, card
    reg clk = 1'b0;
    initial begin
        #(0.53 + (SEED % 13));
        forever #10.0 clk = ~clk;
    end
    wire [23:1] Z_A;
    wire        Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, clk7;
    wire [15:0] Z_D;
    m_bushold #(.W(16)) u_dhold (.bus(Z_D));
    tri1 Z_SLAVE_N;
    tri0 Z_CFGOUT_N;
    tri1 Z_XRDY, Z_INT2_N, Z_INT6_N, Z_BERR_N;
    reg  Z_CFGIN_N = 1'b0, Z_BUSRST_N = 1'b0;
    reg  pwr3 = 1'b0, pwr5 = 1'b0, jumper = 1'b0, fpga_cfg = 1'b0;
    reg  dip_mode_b = 1'b0, dip_int6 = 1'b0, dip_disable = 1'b0;

    z2_master m (.A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N), .READ(Z_READ), .DOE(Z_DOE),
                 .D(Z_D), .XRDY(Z_XRDY), .BERR_N(Z_BERR_N), .clk7(clk7));
    wire d_drv, ld_conflict, card_en_n, en_ok, rp_irq_n, sram_drv;
    card_model #(.SEED(SEED), .SUP_TD(5000.0)) c (
        .Z_A(Z_A), .Z_AS_N(Z_AS_N), .Z_UDS_N(Z_UDS_N), .Z_LDS_N(Z_LDS_N), .Z_READ(Z_READ), .Z_DOE(Z_DOE),
        .Z_E7M(clk7), .Z_CFGIN_N(Z_CFGIN_N), .Z_BUSRST_N(Z_BUSRST_N), .Z_BERR_N(Z_BERR_N),
        .Z_D(Z_D), .Z_SLAVE_N(Z_SLAVE_N), .Z_CFGOUT_N(Z_CFGOUT_N), .Z_XRDY(Z_XRDY),
        .Z_INT2_N(Z_INT2_N), .Z_INT6_N(Z_INT6_N),
        .clk_core(clk), .pwr3(pwr3), .pwr5(pwr5), .jumper(jumper), .fpga_cfg(fpga_cfg),
        .dip_mode_b(dip_mode_b), .dip_int6(dip_int6), .dip_disable(dip_disable),
        .d_drv(d_drv), .ld_conflict(ld_conflict), .card_en_n(card_en_n), .en_ok(en_ok),
        .rp_irq_n(rp_irq_n), .sram_drv(sram_drv));

    // ------------------------------------------------------------------ continuous checkers
    // C1 no Zorro data contention; C2 the card drives Z_D only for a valid read of this card
    always @(d_drv or m.mdrv) if (d_drv && m.mdrv) fail("C1 Z_D contention: card and master driving together");
    real T_REL;
    initial T_REL = 4.9 + 18.0 + 3.8 + 6.3 + 2.0;
    wire valid_rd = (Z_AS_N === 1'b0) && (Z_SLAVE_N === 1'b0) && (Z_READ === 1'b1) && (Z_DOE === 1'b1) &&
                    ((Z_UDS_N === 1'b0) || (Z_LDS_N === 1'b0)) && (Z_BERR_N !== 1'b0);
    real t_valid = -1.0e9;
    reg  c2_rep = 1'b0;
    always #0.5 begin
        if (valid_rd) t_valid = $realtime;
        else if (d_drv && (($realtime - t_valid) > T_REL) && !c2_rep) begin
            fail("C2 card drives Z_D outside a valid read of this card"); c2_rep = 1'b1;
        end
    end
    always @(negedge Z_AS_N) c2_rep = 1'b0;
    real t_xlow = 0.0;
    always @(negedge Z_XRDY) t_xlow = $realtime;
    always @(posedge Z_XRDY) if (($realtime - t_xlow) > 2300.0) fail("C6d XRDY held beyond the watchdog bound");

    // M1 no host SRAM access inside a reserved Zorro cycle once its local-bus actions may start
    //    (simulation form of formal X1/X4)
    always @(posedge clk)
        if ((c.dut.u_core.st != 4'd0) && (c.dut.u_core.st != 4'd2) && (c.dut.u_core.res_cnt >= 3'd4) &&
            (c.dut.u_lbus.h_st != 3'd0))
            fail("M1 host SRAM access inside a reserved Zorro cycle");

    // ------------------------------------------------------------------ determinism monitor (S3)
    integer clkn = 0;                                // counted inside the monitor (one process)
    integer n_start = 0, n_ds = 0;
    reg [3:0] st_d = 4'd0;
    reg oe_rd_d = 1'b0, oe_wr_d = 1'b0;
    integer rd_lat_min = 99, rd_lat_max = -1, wr_lat_min = 99, wr_lat_max = -1, n_rd = 0, n_wr = 0;
    reg     det_on = 1'b0;
    always @(posedge clk) begin : detmon
        reg [3:0] st;
        clkn = clkn + 1;
        st = c.dut.u_core.st;
        if ((st_d == 4'd0) && (st == 4'd1)) n_start = clkn;                     // IDLE -> START
        if (((st_d == 4'd3) || (st_d == 4'd7)) && (st == 4'd8)) n_ds = clkn;   // WAITDS/BETWN -> WR_DIR
        if (det_on && c.dut.u_core.oe_rd_q && !oe_rd_d && c.dut.u_core.tgt_mem && !c.dut.u_core.ph_two) begin
            n_rd = n_rd + 1;
            if (clkn - n_start < rd_lat_min) rd_lat_min = clkn - n_start;
            if (clkn - n_start > rd_lat_max) rd_lat_max = clkn - n_start;
        end
        if (det_on && c.dut.u_core.oe_wr_q && !oe_wr_d && c.dut.u_core.tgt_mem && !c.dut.u_core.ph_two) begin
            n_wr = n_wr + 1;
            if (clkn - n_ds < wr_lat_min) wr_lat_min = clkn - n_ds;
            if (clkn - n_ds > wr_lat_max) wr_lat_max = clkn - n_ds;
        end
        st_d = st; oe_rd_d = c.dut.u_core.oe_rd_q; oe_wr_d = c.dut.u_core.oe_wr_q;
    end
    // slot-level: /AS falling to XRDY rising, SRAM reads
    real t_asf = 0.0, sl_min = 1.0e9, sl_max = 0.0;
    reg  sl_on = 1'b0;
    always @(negedge Z_AS_N) t_asf = $realtime;
    always @(posedge Z_XRDY) if (sl_on && (Z_AS_N === 1'b0)) begin
        if ($realtime - t_asf < sl_min) sl_min = $realtime - t_asf;
        if ($realtime - t_asf > sl_max) sl_max = $realtime - t_asf;
    end

    // ------------------------------------------------------------------ bus helpers
    reg [15:0] rdv;
    reg        bev;
    task bus;
        input integer kind;
        input [23:0]  a24;
        input [1:0]   lanes;
        input [15:0]  wd;
        begin
            m.cycle(kind, a24[23:1], lanes, wd, rdv, bev);
        end
    endtask
    task rd16; input [23:0] a; output [15:0] d; begin bus(0, a, 2'b11, 16'h0); d = rdv; end endtask
    task wr16; input [23:0] a; input [15:0] d;  begin bus(1, a, 2'b11, d); end endtask
    task wr8;  input [23:0] a; input [7:0] d;   begin bus(1, a, a[0] ? 2'b01 : 2'b10, {d, d}); end endtask
    task tas8; input [23:0] a;                  begin bus(2, a, a[0] ? 2'b01 : 2'b10, 16'h0); end endtask

    task hreg_wr; input [3:0] i; input [15:0] d; reg [15:0] x; begin c.dut.u_host.xfer(1'b1, 1'b1, {14'd0, i}, 2'b11, d, x); end endtask
    task hreg_wr8; input [3:0] i; input [15:0] d; reg [15:0] x; begin c.dut.u_host.xfer(1'b1, 1'b1, {14'd0, i}, 2'b01, d, x); end endtask
    task hreg_rd; input [3:0] i; output [15:0] d; begin c.dut.u_host.xfer(1'b1, 1'b0, {14'd0, i}, 2'b11, 16'h0, d); end endtask
    task hmem_wr; input [17:0] a; input [15:0] d; input [1:0] be; reg [15:0] x; begin c.dut.u_host.xfer(1'b0, 1'b1, a, be, d, x); end endtask
    task hmem_rd; input [17:0] a; output [15:0] d; begin c.dut.u_host.xfer(1'b0, 1'b0, a, 2'b11, 16'h0, d); end endtask

    task zorro_reset;
        input real len;
        begin
            Z_BUSRST_N = 1'b0; #(len); Z_BUSRST_N = 1'b1; #(2000.0);
        end
    endtask
    task configure;                                   // AutoConfig writes only (tb_z2 checks the ROM)
        input [7:0] base;
        begin
            rd16(24'hE80000, rdv);
            wr8(24'hE8004A, {base[3:0], 4'h0});
            wr8(24'hE80048, {base[7:4], 4'h0});
            #(500.0);
        end
    endtask

    // mbx register offsets in the board window (Zorro view) and the register indices
    localparam [3:0] Q0P = 4'd0, Q0C = 4'd1, Q1P = 4'd2, Q1C = 4'd3, QST = 4'd4, EPO = 4'd5, ZIEN = 4'd6,
                     ZEV = 4'd7, HIEN = 4'd8, HEV = 4'd9, QCTL = 4'd10, ZPEND = 4'd11, HPEND = 4'd12, ASTAT = 4'd13;
    reg  [23:0] B;
    function [23:0] mreg; input [3:0] i; begin mreg = B + 24'h40 + {19'd0, i, 1'b0}; end endfunction

    // ------------------------------------------------------------------ test sequence
    reg [15:0] d, e, ep, x;
    integer i, k, r1, r2;
    reg [17:0] wa;
    initial begin
        m.seed = SEED; tseed = SEED * 17 + 3; c.dut.u_host.seed = SEED * 7 + 1;
        $display("tb_shm: SEED=%0d", SEED);
        // ---------------- power-up, arm, configure (mode A at $E90000)
        #(100.0); pwr5 = 1'b1; #(300.0); pwr3 = 1'b1; #(1200.0); fpga_cfg = 1'b1;
        wait (en_ok === 1'b1); #(2000.0);
        Z_BUSRST_N = 1'b1; #(3000.0);
        configure(8'hE9); B = 24'hE90000;
        expect1("S0 configured", c.dut.u_core.configured, 1'b1);
        // SRAM is not touched by anything above: the host side may already use it (S7)

        // ---------------- S1 Zorro SRAM windows
        wr16(B + 24'h1000, 16'h1111); wr16(B + 24'h7FFE, 16'h7FFE);
        rd16(B + 24'h1000, d); expect16("S1 fixed window $1000", d, 16'h1111);
        rd16(B + 24'h7FFE, d); expect16("S1 fixed window $7FFE", d, 16'h7FFE);
        for (k = 0; k < 16; k = k + 1) begin                       // every bank, distinct pattern
            wr16(B + 24'h20, k); wr16(B + 24'h8000 + 24'h2468, 16'hB000 | k);
        end
        for (k = 15; k >= 0; k = k - 1) begin
            wr16(B + 24'h20, k); rd16(B + 24'h8000 + 24'h2468, d); expect16("S1 banked window", d, 16'hB000 | k);
            hmem_rd({k[3:0], 14'h1234}, d); expect16("S1 bank mapping seen by the host", d, 16'hB000 | k);
        end
        rd16(B + 24'h20, d); expect16("S1 BANK register", d, 16'h0000);
        wr16(B + 24'h8000 + 24'h1000, 16'hA1A1);                    // bank 0 aliases the fixed window
        rd16(B + 24'h1000, d); expect16("S1 bank 0 aliases the fixed window", d, 16'hA1A1);
        wr8(B + 24'h1000, 8'h5C); wr8(B + 24'h1001, 8'h3D);
        rd16(B + 24'h1000, d); expect16("S1 byte lanes", d, 16'h5C3D);

        // ---------------- S2 coherence Zorro <-> host
        hmem_wr(18'h00900, 16'hC0DE, 2'b11); rd16(B + 24'h1200, d); expect16("S2 host write seen by Zorro", d, 16'hC0DE);
        wr16(B + 24'h1202, 16'hFACE); hmem_rd(18'h00901, d); expect16("S2 Zorro write seen by host", d, 16'hFACE);
        hmem_wr(18'h00900, 16'h99AA, 2'b10); rd16(B + 24'h1200, d); expect16("S2 host upper-byte write", d, 16'h99DE);
        hmem_wr(18'h00900, 16'hBB55, 2'b01); rd16(B + 24'h1200, d); expect16("S2 host lower-byte write", d, 16'h9955);
        wr8(B + 24'h1203, 8'h77); hmem_rd(18'h00901, d); expect16("S2 Zorro LDS byte seen by host", d, 16'hFA77);

        // ---------------- S3 determinism: host traffic off, then on
        for (r1 = 0; r1 < 2; r1 = r1 + 1) begin
            rd_lat_min = 99; rd_lat_max = -1; wr_lat_min = 99; wr_lat_max = -1; n_rd = 0; n_wr = 0;
            sl_min = 1.0e9; sl_max = 0.0;
            c.dut.u_host.bg_base = 18'h30000; c.dut.u_host.bg_gap = 2; c.dut.u_host.bg_en = (r1 == 1);
            det_on = 1'b1;
            for (i = 0; i < 120; i = i + 1) begin
                wa = 24'h2000 + (($random(tseed) & 24'h3FFE));
                if (i % 2) wr16(B + wa, i[15:0]);
                else begin sl_on = 1'b1; rd16(B + wa, d); sl_on = 1'b0; end
                #($random(tseed) & 63);                                // vary the phase against clk
            end
            det_on = 1'b0;
            c.dut.u_host.bg_en = 1'b0; wait (c.dut.u_host.busy == 1'b0);
            $display("S3 host traffic %s: SRAM read action at START+[%0d..%0d] clocks (%0d reads), write action at DS+[%0d..%0d] (%0d writes); slot /AS->XRDY %0.1f..%0.1f ns",
                     r1 ? "ON " : "OFF", rd_lat_min, rd_lat_max, n_rd, wr_lat_min, wr_lat_max, n_wr, sl_min, sl_max);
            checks = checks + 1;
            if ((rd_lat_min != rd_lat_max) || (wr_lat_min != wr_lat_max))
                fail("S3 Zorro SRAM local-bus action is not at a fixed clock");
            if (r1 == 0) begin r2 = rd_lat_min * 100 + wr_lat_min; end
            else if (r2 != rd_lat_min * 100 + wr_lat_min) fail("S3 host traffic changed the Zorro timing");
        end
        $display("S3 host transfers during the ON run: %0d (max latency %0.1f ns)", c.dut.u_host.n_sram, c.dut.u_host.max_lat);

        // ---------------- S4 RMW (TAS) on SRAM, host hammering the same word
        wr16(B + 24'h1400, 16'h2B4C);
        tas8(B + 24'h1400); expect16("S4 TAS read portion (UDS)", rdv, 16'h2B4C);
        rd16(B + 24'h1400, d); expect16("S4 TAS even byte result", d, 16'hAB4C);
        tas8(B + 24'h1401); rd16(B + 24'h1400, d); expect16("S4 TAS odd byte result", d, 16'hABCC);
        fork
            begin : hammer
                for (i = 0; i < 400; i = i + 1) hmem_wr(18'h00A00, 16'h0101 * (i & 8'h7F), 2'b11);
            end
            begin
                for (k = 0; k < 40; k = k + 1) begin
                    tas8(B + 24'h1400 + (k & 1));
                    // atomic: the value written back equals the value read with bit 7 set, unless the
                    // host overwrote the word AFTER the whole cycle (then bit 7 of that lane is 0)
                    hmem_rd(18'h00A00, x);
                end
            end
        join
        rd16(B + 24'h18, d);
        $display("S4 RMW_CYCLES %0d after TAS under host contention", d);
        checks = checks + 1;
        if (d < 16'd42) fail("S4 RMW cycles not counted");

        // ---------------- S5 queues and interrupts
        hreg_rd(EPO, ep);
        rd16(mreg(EPO), d); expect16("S5 EPOCH same in both views", d, ep);
        rd16(mreg(QST), d); expect16("S5 QSTAT empty, depth 2^5", d, 16'h0500);
        // Amiga -> PC: payload in SRAM, then publish; host interrupt (level) follows queue state
        hreg_wr(HIEN, 16'h0001);
        expect1("S5 host IRQ idle while Q0 empty", rp_irq_n, 1'b1);
        wr16(B + 24'h3000, 16'h4D53);                                 // slot 0 payload
        wr16(mreg(Q0P), {ep[7:0], 8'd1});
        #(200.0); expect1("S5 host IRQ asserted by Q0 work", rp_irq_n, 1'b0);
        hreg_rd(Q0P, d); expect16("S5 host sees Q0_PROD", d, {ep[7:0], 8'd1});
        hmem_rd(18'h01800, d); expect16("S5 host reads the payload", d, 16'h4D53);
        hreg_wr(Q0C, {ep[7:0], 8'd1});
        #(200.0); expect1("S5 host IRQ released when Q0 drained", rp_irq_n, 1'b1);
        // PC -> Amiga: Amiga INT2 through CONTROL.IRQ_EN and Z_IRQ_EN b0
        wr16(B + 24'h6, 16'h0002); wr16(mreg(ZIEN), 16'h0001);
        hmem_wr(18'h01C00, 16'h5043, 2'b11);
        hreg_wr(Q1P, {ep[7:0], 8'd1});
        #(300.0); expect1("S5 Amiga INT2 asserted by Q1 work", Z_INT2_N, 1'b0);
        rd16(mreg(ZPEND), d); expect16("S5 Z_IRQ_PEND", d, 16'h8001);
        rd16(B + 24'h3800, d); expect16("S5 Amiga reads the payload", d, 16'h5043);
        wr16(mreg(Q1C), {ep[7:0], 8'd1});
        #(300.0); expect1("S5 Amiga INT2 released when Q1 drained", Z_INT2_N, 1'b1);
        // fill Q0 to its depth; one more is rejected (ERR_RANGE); space interrupt for the producer
        wr16(mreg(Q0P), {ep[7:0], 8'd34});                            // 33 entries > depth 32
        rd16(mreg(Q0P), d); expect16("S5 over-advance rejected", d, {ep[7:0], 8'd1});
        rd16(mreg(ZEV), d); expect16("S5 ERR_RANGE flagged (Zorro side)", d, 16'h0200);
        wr16(mreg(ZEV), 16'hFFFF); rd16(mreg(ZEV), d); expect16("S5 Z_EVENTS W1C", d, 16'h0000);
        wr16(mreg(Q0P), {ep[7:0], 8'd33});                            // 32 queued = full
        rd16(mreg(QST), d); expect16("S5 Q0 full", d, 16'h0503);
        wr16(mreg(ZIEN), 16'h0002);                                   // space interrupt only
        #(300.0); expect1("S5 no space interrupt while full", Z_INT2_N, 1'b1);
        hreg_wr(Q0C, {ep[7:0], 8'd2});                                // host consumes one
        #(300.0); expect1("S5 space interrupt when not full", Z_INT2_N, 1'b0);
        wr16(mreg(ZIEN), 16'h0000);
        // stale epoch, wrong owner, byte write: all rejected and flagged
        hreg_wr(Q1P, {ep[7:0] + 8'd1, 8'd2});
        hreg_rd(Q1P, d); expect16("S5 stale-epoch write rejected", d, {ep[7:0], 8'd1});
        hreg_wr(Q0P, {ep[7:0], 8'd5});                                // Q0_PROD belongs to the Amiga
        hreg_rd(Q0P, d); expect16("S5 wrong-owner write rejected", d, {ep[7:0], 8'd33});
        hreg_wr8(Q1P, {ep[7:0], 8'd2});
        hreg_rd(Q1P, d); expect16("S5 byte write to an index rejected", d, {ep[7:0], 8'd1});
        hreg_rd(HEV, d); expect16("S5 H_EVENTS: epoch, range, owner errors (+ link, configured)", d & 16'hFF00, 16'h0700);
        wr16(mreg(Q0C), {ep[7:0], 8'd9});                             // Q0_CONS belongs to the PC
        rd16(mreg(ZEV), d); expect16("S5 Zorro wrong-owner flagged", d, 16'h0400);
        hreg_wr(HEV, 16'hFFFF); wr16(mreg(ZEV), 16'hFFFF);

        // ---------------- S6 link reset by the host, by the Amiga, by /BUSRST
        hreg_wr(QCTL, 16'h1234);                                      // not the magic value: ignored
        hreg_rd(EPO, d); expect16("S6 non-magic QCTL ignored", d, ep);
        wr16(mreg(ZIEN), 16'h0004);                                   // event interrupt
        hreg_wr(QCTL, 16'hA55A);
        hreg_rd(EPO, d); expect16("S6 host link reset: epoch + 1", d, ep + 16'd1);
        rd16(mreg(QST), d); expect16("S6 queues empty after link reset", d, 16'h0500);
        #(300.0); expect1("S6 Amiga event interrupt", Z_INT2_N, 1'b0);
        rd16(mreg(ZEV), d); expect16("S6 Amiga LINK_RESET event", d, 16'h0001);
        wr16(mreg(ZEV), 16'h0001); #(300.0); expect1("S6 event interrupt cleared by W1C", Z_INT2_N, 1'b1);
        hreg_wr(Q1P, {ep[7:0], 8'd1});                                // prepared before the reset: rejected
        hreg_rd(Q1P, d); expect16("S6 old-epoch write after reset rejected", d, {ep[7:0] + 8'd1, 8'd0});
        wr16(mreg(QCTL), 16'hA55A);
        hreg_rd(EPO, d); expect16("S6 Amiga link reset: epoch + 1", d, ep + 16'd2);
        hreg_wr(HEV, 16'hFFFF);
        hmem_wr(18'h01000, 16'h600D, 2'b11);
        zorro_reset(20000.0);
        hreg_rd(EPO, d); expect16("S6 /BUSRST link reset: epoch + 1", d, ep + 16'd3);
        hreg_rd(HEV, d); expect16("S6 host events: link reset + Amiga reset", d & 16'h0003, 16'h0003);
        hreg_rd(ASTAT, d); expect16("S6 Amiga status: armed, not configured", d & 16'h0007, 16'h0001);

        // ---------------- S7 host access in every Amiga state; SRAM survives /BUSRST (G7)
        hmem_rd(18'h01000, d); expect16("S7 SRAM survives /BUSRST", d, 16'h600D);
        Z_BUSRST_N = 1'b0; #(3000.0);
        hmem_wr(18'h01001, 16'h1D1E, 2'b11); hmem_rd(18'h01001, d); expect16("S7 host access during /BUSRST", d, 16'h1D1E);
        Z_BUSRST_N = 1'b1; #(3000.0);
        hmem_wr(18'h01002, 16'hC0FF, 2'b11); hmem_rd(18'h01002, d); expect16("S7 host access while unconfigured", d, 16'hC0FF);
        configure(8'hE9);
        rd16(B + 24'h0, d); expect16("S7 configured again", d, 16'h4252);
        hreg_rd(HEV, d); expect16("S7 AMIGA_CONFIGURED event", d & 16'h0004, 16'h0004);
        rd16(mreg(ZIEN), d); expect16("S7 Zorro interrupt enables cleared by /BUSRST", d, 16'h0000);
        rd16(B + 24'h2000, d); expect16("S7 SRAM via the window after re-configuration", d, 16'h600D);

        // ---------------- S8 FPGA reload: deselected while blank, contents kept
        hmem_wr(18'h01003, 16'h5AFE, 2'b11);
        wait (c.dut.u_host.busy == 1'b0);
        fpga_cfg = 1'b0; #(500.0);
        expect1("S8 SRAM deselected while the FPGA is blank", c.SRAM_CE_N, 1'b1);
        expect1("S8 /WE held high while the FPGA is blank", c.SRAM_WE_N, 1'b1);
        expect1("S8 SRAM not driving LD", sram_drv, 1'b0);
        #(2000.0); fpga_cfg = 1'b1; #(2000.0);
        hmem_rd(18'h01003, d); expect16("S8 SRAM contents kept over an FPGA reload", d, 16'h5AFE);
        zorro_reset(20000.0); configure(8'hE9);

        // ---------------- S9 reconfiguration during a host write (characterisation)
        hmem_wr(18'h01010, 16'h1010, 2'b11); hmem_wr(18'h01011, 16'h1111, 2'b11);
        fork : s9
            begin hmem_wr(18'h01012, 16'h1212, 2'b11); end            // never acknowledged
            begin @(posedge c.dut.u_lbus.h_ld_oe); #(25.0); fpga_cfg = 1'b0; #(3000.0); disable s9; end
        join
        c.dut.u_host.h_req = 1'b0; c.dut.u_host.busy = 1'b0;          // the transfer in flight was lost
        fpga_cfg = 1'b1; #(2000.0);
        hmem_rd(18'h01010, d); expect16("S9 neighbour word kept (1)", d, 16'h1010);
        hmem_rd(18'h01011, d); expect16("S9 neighbour word kept (2)", d, 16'h1111);
        hmem_rd(18'h01012, d);
        $display("S9 word written during the reconfiguration reads %h (any value is acceptable)", d);
        zorro_reset(20000.0); configure(8'hE9);

        // ---------------- S10 watchdog and /BERR on SRAM cycles
        wr16(B + 24'h1500, 16'h1234);
        force c.dut.u_core.stall_test = 1'b1;
        rd16(B + 24'h1500, d); expect16("S10 watchdog: SRAM read returns $FFFF", d, 16'hFFFF);
        wr16(B + 24'h1500, 16'h4321);
        release c.dut.u_core.stall_test;
        rd16(B + 24'h1500, d); expect16("S10 watchdog: SRAM write discarded", d, 16'h1234);
        m.berr_at = 80.0; rd16(B + 24'h1500, d); wr16(B + 24'h1502, 16'h0BAD); m.berr_at = -1.0;
        checks = checks + 1;
        if (!bev) fail("S10 /BERR cycle did not end in a bus error");
        rd16(B + 24'h1500, d); expect16("S10 SRAM intact after /BERR cycles", d, 16'h1234);

        // ---------------- S11 zero-wait mode on SRAM (characterisation; gated by G-ZEROWAIT)
        wr16(B + 24'h6, 16'h0001);
        wr16(B + 24'h1600, 16'h2EE0); rd16(B + 24'h1600, d);
        $display("S11 zero-wait SRAM write+read: %s (read %h, waits %0d)", (d === 16'h2EE0) ? "OK" : "WRONG DATA",
                 d, m.last_waits);
        wr16(B + 24'h6, 16'h0000);

        #(2000.0);
        errors = errors + c.u301.errors + c.dut.u_host.errors;
        $display("tb_shm: SRAM model writes %0d, read enables %0d, timing errors %0d; host transfers %0d SRAM, %0d registers",
                 c.u301.writes, c.u301.reads, c.u301.errors, c.dut.u_host.n_sram, c.dut.u_host.n_reg);
        $display("TB_RESULT %s tb_shm SEED=%0d errors=%0d checks=%0d", (errors == 0) ? "PASS" : "FAIL", SEED, errors, checks);
        $finish;
    end

    initial begin
        #(40_000_000.0);
        $display("ASSERT-FAIL timeout");
        $display("TB_RESULT FAIL tb_shm SEED=%0d timeout", SEED);
        $finish;
    end
endmodule
