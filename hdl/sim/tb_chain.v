// SPDX-License-Identifier: MIT
// AutoConfig chain testbench (C-03): three Zorro II slots on an A2000 Rev 6-style backplane.
//   /CFGIN1 asserted; /CFGIN(n+1) = /CFGIN(n) OR /CFGOUT(n)         (U606 74LS32, R6 schematic sheet 6)
//   1k pull-down on every /CFGOUTn (RP607): an empty or Hi-Z slot passes the chain
//   1k pull-up on every /SLAVEn (RP800, sheet 8); Buster flags a collision (/BERR) when two
//   or more /SLAVEn are asserted together.
// Slot 1 and slot 3 hold simple behavioural AutoConfig boards; slot 2 holds the bridgeboard
// (card_model = sheet-1 and sheet-3 circuits + RTL). Scenarios: normal, unpowered, blank FPGA, late power,
// FPGA reload while running, power loss while running, DIP disable, DISABLE jumper, /BUSRST in
// the middle of the scan, shut-up. Every scenario must configure exactly the expected boards,
// in chain order, with no collision.
`timescale 1ns/1ps

module dummy_z2 #(parameter [7:0] PRODUCT = 8'h11) (
    input  wire        powered,
    input  wire [23:1] A,
    input  wire        AS_N, UDS_N, LDS_N, READ, DOE, CFGIN_N, BUSRST_N,
    inout  wire [15:0] D,
    output wire        SLAVE_N,
    output wire        CFGOUT_N
);
    reg       configured = 1'b0, shutup = 1'b0;
    reg [7:0] base = 8'h00;
    wire [7:0] off = {A[7:1], 1'b0};
    wire sel = powered && ((!configured && !shutup && !CFGIN_N && (A[23:16] == 8'hE8)) ||
                           (configured && (A[23:16] == base)));
    reg [7:0] v;
    always @* begin
        case (off[7:2])
            6'd0: v = 8'hC1;  6'd1: v = PRODUCT;  6'd4: v = 8'h12;  6'd5: v = 8'h34;
            default: v = 8'h00;
        endcase
    end
    wire [3:0] nib  = off[1] ? v[3:0] : v[7:4];
    wire [3:0] phys = (off[7:2] == 6'd0) ? nib : ~nib;
    wire [15:0] rdata = configured ? {8'h5A, PRODUCT} : {phys, 12'hFFF};
    wire drv = powered && !AS_N && sel && READ && DOE && (!UDS_N || !LDS_N);
    assign #8 D        = drv ? rdata : 16'hzzzz;
    assign #5 SLAVE_N  = powered ? (AS_N | ~sel) : 1'bz;
    assign #5 CFGOUT_N = powered ? (CFGIN_N | ~(configured | shutup)) : 1'bz;
    always @(posedge AS_N)                               // writes take effect at the end of the cycle
        if (sel && !READ && !configured) begin
            if (off == 8'h48) begin base[7:4] <= D[15:12]; configured <= 1'b1; end
            if (off == 8'h4A) base[3:0] <= D[15:12];
            if (off == 8'h4C) shutup <= 1'b1;
        end
    always @(negedge BUSRST_N or negedge powered) begin configured <= 1'b0; shutup <= 1'b0; base <= 8'h00; end
endmodule

module tb_chain;
    parameter integer SEED = 1;
    integer errors = 0, checks = 0;
    task fail;
        input [8*100-1:0] msg;
        begin
            errors = errors + 1;
            if (errors <= 60) $display("ASSERT-FAIL %0t %0s", $realtime, msg);
        end
    endtask

    reg clk = 1'b0;
    initial begin #(3.1 + (SEED % 11)); forever #10.0 clk = ~clk; end

    // ---------------- shared bus
    wire [23:1] Z_A;
    wire        Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, clk7;
    wire [15:0] Z_D;
    m_bushold #(.W(16)) u_dhold (.bus(Z_D));
    tri1 Z_XRDY, Z_INT2_N, Z_INT6_N, Z_BERR_N;
    reg  Z_BUSRST_N = 1'b0;
    z2_master m (.A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N), .READ(Z_READ), .DOE(Z_DOE),
                 .D(Z_D), .XRDY(Z_XRDY), .BERR_N(Z_BERR_N), .clk7(clk7));

    // ---------------- slot-private chain signals (A2000 Rev 6 style)
    tri1 SLAVE1_N, SLAVE2_N, SLAVE3_N;
    tri0 CFGOUT1_N, CFGOUT2_N, CFGOUT3_N;
    wire CFGIN1_N = 1'b0;
    wire CFGIN2_N, CFGIN3_N;
    assign #10 CFGIN2_N = CFGIN1_N | CFGOUT1_N;             // 74LS32 [K] ~10 ns
    assign #10 CFGIN3_N = CFGIN2_N | CFGOUT2_N;

    // ---------------- Buster collision detection -> /BERR
    wire [1:0] nslaves = (SLAVE1_N === 1'b0) + (SLAVE2_N === 1'b0) + (SLAVE3_N === 1'b0);
    reg  collision = 1'b0;
    always @* collision = (nslaves > 1);
    reg  buster_berr = 1'b0;
    always @(posedge collision) begin #20.0; if (collision) buster_berr = 1'b1; end
    always @(posedge Z_AS_N) buster_berr = 1'b0;
    assign Z_BERR_N = buster_berr ? 1'b0 : 1'bz;
    always @(posedge collision) fail("COLLISION: two or more /SLAVEn asserted together");

    // ---------------- slots
    reg p1 = 1'b0, p3b = 1'b0;                               // dummy boards powered
    reg pwr3 = 1'b0, pwr5 = 1'b0, jumper = 1'b0, fpga_cfg = 1'b0, dip_disable = 1'b0;
    dummy_z2 #(.PRODUCT(8'h11)) s1 (.powered(p1), .A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N),
        .READ(Z_READ), .DOE(Z_DOE), .CFGIN_N(CFGIN1_N), .BUSRST_N(Z_BUSRST_N), .D(Z_D),
        .SLAVE_N(SLAVE1_N), .CFGOUT_N(CFGOUT1_N));
    wire d_drv, ld_conflict, card_en_n, en_ok;
    card_model #(.SEED(SEED), .SUP_TD(5000.0)) s2 (
        .Z_A(Z_A), .Z_AS_N(Z_AS_N), .Z_UDS_N(Z_UDS_N), .Z_LDS_N(Z_LDS_N), .Z_READ(Z_READ), .Z_DOE(Z_DOE),
        .Z_E7M(clk7), .Z_CFGIN_N(CFGIN2_N), .Z_BUSRST_N(Z_BUSRST_N), .Z_BERR_N(Z_BERR_N),
        .Z_D(Z_D), .Z_SLAVE_N(SLAVE2_N), .Z_CFGOUT_N(CFGOUT2_N), .Z_XRDY(Z_XRDY),
        .Z_INT2_N(Z_INT2_N), .Z_INT6_N(Z_INT6_N),
        .clk_core(clk), .pwr3(pwr3), .pwr5(pwr5), .jumper(jumper), .fpga_cfg(fpga_cfg),
        .dip_mode_b(1'b0), .dip_int6(1'b0), .dip_disable(dip_disable),
        .d_drv(d_drv), .ld_conflict(ld_conflict), .card_en_n(card_en_n), .en_ok(en_ok));
    dummy_z2 #(.PRODUCT(8'h33)) s3 (.powered(p3b), .A(Z_A), .AS_N(Z_AS_N), .UDS_N(Z_UDS_N), .LDS_N(Z_LDS_N),
        .READ(Z_READ), .DOE(Z_DOE), .CFGIN_N(CFGIN3_N), .BUSRST_N(Z_BUSRST_N), .D(Z_D),
        .SLAVE_N(SLAVE3_N), .CFGOUT_N(CFGOUT3_N));

    // ---------------- which slots answered the current cycle
    reg seen1 = 1'b0, seen2 = 1'b0, seen3 = 1'b0;
    always @(negedge Z_AS_N) begin seen1 = 1'b0; seen2 = 1'b0; seen3 = 1'b0; end
    always @(negedge SLAVE1_N) seen1 = 1'b1;
    always @(negedge SLAVE2_N) seen2 = 1'b1;
    always @(negedge SLAVE3_N) seen3 = 1'b1;

    reg [15:0] rdv;
    reg        bev;
    task rd;  input [23:0] a; begin m.cycle(0, a[23:1], 2'b11, 16'h0, rdv, bev); end endtask
    task wr8; input [23:0] a; input [7:0] d; begin m.cycle(1, a[23:1], 2'b10, {d, d}, rdv, bev); end endtask

    // ---------------- expansion.library-style scan (presence = some /SLAVEn answered $E80000)
    reg [7:0] found [0:3];
    integer   nfound;
    task scan;
        input integer shut_ours;                             // 1: shut up the bridgeboard instead of configuring it
        integer k;
        reg [7:0] prod, b;
        reg       done;
        begin
            nfound = 0; done = 1'b0;
            for (k = 0; k < 4; k = k + 1) found[k] = 8'h00;
            for (k = 0; (k < 4) && !done; k = k + 1) begin
                rd(24'hE80000);
                if (!(seen1 || seen2 || seen3)) done = 1'b1;
                else begin
                    rd(24'hE80004); prod[7:4] = ~rdv[15:12];
                    rd(24'hE80006); prod[3:0] = ~rdv[15:12];
                    found[nfound] = prod; nfound = nfound + 1;
                    b = 8'hE9 + k;
                    if (shut_ours && (prod == 8'h01))
                        wr8(24'hE8004C, 8'h00);
                    else begin
                        wr8(24'hE8004A, {b[3:0], 4'h0});
                        wr8(24'hE80048, {b[7:4], 4'h0});
                    end
                end
            end
        end
    endtask

    task expect_chain;
        input [8*40-1:0] name;
        input integer n;
        input [7:0] f0, f1, f2;
        begin
            checks = checks + 1;
            if ((nfound != n) || (n > 0 && found[0] != f0) || (n > 1 && found[1] != f1) || (n > 2 && found[2] != f2)) begin
                errors = errors + 1;
                $display("ASSERT-FAIL %0t scenario %0s: found %0d boards [%h %h %h], expected %0d [%h %h %h]",
                         $realtime, name, nfound, found[0], found[1], found[2], n, f0, f1, f2);
            end else
                $display("scenario %0s: OK, chain = %0d board(s)", name, n);
        end
    endtask

    task system_reset;                                        // A2000 power-on / keyboard reset (scaled)
        input real len;
        begin
            Z_BUSRST_N = 1'b0; #(len); Z_BUSRST_N = 1'b1; #(3000.0);
        end
    endtask

    task power_all_off;
        begin
            Z_BUSRST_N = 1'b0; p1 = 1'b0; p3b = 1'b0; pwr3 = 1'b0; pwr5 = 1'b0; fpga_cfg = 1'b0; #(2000.0);
        end
    endtask

    task boot_normal;                                         // A2000 and carrier powered together
        begin
            power_all_off;
            p1 = 1'b1; p3b = 1'b1; pwr5 = 1'b1; #(300.0); pwr3 = 1'b1; #(1000.0); fpga_cfg = 1'b1;
            #(9000.0);                                        // > supervisor delay, still inside reset
            Z_BUSRST_N = 1'b1; #(3000.0);
        end
    endtask

    initial begin
        m.seed = SEED;
        // S1 normal operation
        boot_normal; scan(0); expect_chain("S1 normal", 3, 8'h11, 8'h01, 8'h33);
        rd(24'hEA0000);
        checks = checks + 1;
        if (!seen2 || rdv !== 16'h4252) fail("S1 bridgeboard does not answer at its base $EA0000");

        // S2 carrier unpowered (Molex unplugged): the slot must behave as an empty slot
        power_all_off; p1 = 1'b1; p3b = 1'b1; #(9000.0); Z_BUSRST_N = 1'b1; #(3000.0);
        scan(0); expect_chain("S2 carrier unpowered", 2, 8'h11, 8'h33, 8'h00);

        // S3 carrier powered, FPGA blank
        power_all_off; p1 = 1'b1; p3b = 1'b1; pwr5 = 1'b1; pwr3 = 1'b1; #(9000.0); Z_BUSRST_N = 1'b1; #(3000.0);
        scan(0); expect_chain("S3 blank FPGA", 2, 8'h11, 8'h33, 8'h00);

        // S4 carrier power good only after the Amiga reset ended: transparent until the next reset
        power_all_off; p1 = 1'b1; p3b = 1'b1; #(4000.0); Z_BUSRST_N = 1'b1; #(500.0);
        pwr5 = 1'b1; pwr3 = 1'b1; fpga_cfg = 1'b1;
        scan(0); expect_chain("S4a late carrier power, first boot", 2, 8'h11, 8'h33, 8'h00);
        #(9000.0);
        system_reset(20000.0); scan(0); expect_chain("S4b after keyboard reset", 3, 8'h11, 8'h01, 8'h33);

        // S5 FPGA reloaded while running: transparent, others keep working, joins at the next reset
        fpga_cfg = 1'b0; #(2000.0); fpga_cfg = 1'b1; #(4000.0);
        rd(24'hEB0000);
        checks = checks + 1;
        if (!seen3 || seen2) fail("S5 slot-3 board not answering (or bridgeboard answering) after FPGA reload");
        rd(24'hEA0000);
        checks = checks + 1;
        if (seen2) fail("S5 reloaded FPGA answered without a reset");
        system_reset(20000.0); scan(0); expect_chain("S5 after reset", 3, 8'h11, 8'h01, 8'h33);

        // S6 carrier power lost while running: transparent, no collision, others unaffected
        pwr3 = 1'b0; pwr5 = 1'b0; #(2000.0);
        rd(24'hEB0000);
        checks = checks + 1;
        if (!seen3) fail("S6 slot-3 board lost after carrier power loss");
        rd(24'hEA0000);
        checks = checks + 1;
        if (seen2) fail("S6 unpowered carrier answered");
        pwr5 = 1'b1; pwr3 = 1'b1; #(9000.0);
        rd(24'hEA0000);
        checks = checks + 1;
        if (seen2) fail("S6 carrier rejoined without a reset");
        system_reset(20000.0); scan(0); expect_chain("S6 after reset", 3, 8'h11, 8'h01, 8'h33);

        // S7 DIP disable
        dip_disable = 1'b1; system_reset(20000.0); scan(0); expect_chain("S7 DIP disable", 2, 8'h11, 8'h33, 8'h00);
        dip_disable = 1'b0;

        // S8 DISABLE jumper fitted
        jumper = 1'b1; system_reset(20000.0); scan(0); expect_chain("S8 DISABLE jumper", 2, 8'h11, 8'h33, 8'h00);
        jumper = 1'b0; #(200.0);

        // S9 /BUSRST in the middle of the scan, then a full scan
        system_reset(20000.0);
        rd(24'hE80000); wr8(24'hE8004A, 8'h90); wr8(24'hE80048, 8'hE0);     // slot 1 configured
        system_reset(20000.0); scan(0); expect_chain("S9 reset mid-scan", 3, 8'h11, 8'h01, 8'h33);

        // S10 shut-up of the bridgeboard: the chain continues to slot 3
        system_reset(20000.0); scan(1); expect_chain("S10 shut-up", 3, 8'h11, 8'h01, 8'h33);
        rd(24'hEA0000);
        checks = checks + 1;
        if (seen2) fail("S10 shut-up bridgeboard answered");

        #(1000.0);
        $display("TB_RESULT %s tb_chain SEED=%0d errors=%0d checks=%0d", (errors == 0) ? "PASS" : "FAIL",
                 SEED, errors, checks);
        $finish;
    end

    initial begin
        #(20_000_000.0);
        $display("ASSERT-FAIL timeout");
        $display("TB_RESULT FAIL tb_chain SEED=%0d timeout", SEED);
        $finish;
    end
endmodule
