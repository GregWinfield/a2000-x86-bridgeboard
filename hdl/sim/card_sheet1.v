// SPDX-License-Identifier: MIT
// The bridgeboard as seen from a Zorro II slot: sheet-1 circuit (revision B) around the
// FPGA RTL. Used by tb_z2 and tb_chain. Net names follow the schematic.
//
//   slot -> U101/U102 -> ZB_* -> FPGA (z2_top) -> ZF_* -> U106/U107 gating -> U103/U104/U105 -> slot
//   EN_OK = TPS3808 (+3V3) & TPS3808 (+5V_BUS) & no DISABLE jumper   (wired-AND)
//   CARD_EN_N = NAND(EN_OK, ZF_ARM)  -> U104 /OE and ORed into U103 /OE, XRDY, /INT2, /INT6
`timescale 1ns/1ps
module card_sheet1 #(
    parameter integer SEED   = 1,
    parameter real    FPGA_TMIN = 3.0,    // FPGA pin-to-pin combinational delay range [A]
    parameter real    FPGA_TMAX = 18.0,   //   (18 ns = sheet-1 allocation, unproven until G-STA)
    parameter real    TCO_MIN   = 2.0,    // FPGA clock-to-out for registered outputs [A]
    parameter real    TCO_MAX   = 9.0,
    parameter real    SUP_TD    = 5000.0  // supervisor release delay, scaled (real 12-28 ms)
) (
    // slot (Zorro II edge, after the A2000 backplane)
    input  wire [23:1] Z_A,
    input  wire        Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, Z_E7M,
    input  wire        Z_CFGIN_N, Z_BUSRST_N, Z_BERR_N,
    inout  wire [15:0] Z_D,
    inout  wire        Z_SLAVE_N, Z_CFGOUT_N, Z_XRDY, Z_INT2_N, Z_INT6_N,
    // environment controls
    input  wire        clk_core,
    input  wire        pwr3,         // +3V3 valid
    input  wire        pwr5,         // +5V_BUS valid (Molex)
    input  wire        jumper,       // JP101 DISABLE fitted
    input  wire        fpga_cfg,     // 1 = FPGA configured and running (0 = blank / configuring)
    input  wire        dip_mode_b, dip_int6, dip_disable,
    // observation for the checkers
    output wire        d_drv,        // U103 B port may be driving Z_D
    output wire        ld_conflict,  // FPGA and U103 may both be driving LD
    output wire        card_en_n,
    output wire        en_ok
);
    wire pwr_both = pwr3 & pwr5;
    wire fpga_on  = fpga_cfg & pwr3;

    // ---------------- U101/U102 input buffers (+3V3); 1.1-4.1 ns + ~0.8 ns traces [E]
    wire [23:1] ZB_A;
    wire ZB_AS_N, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_E7M, ZB_CFGIN_N, ZB_BUSRST_N, ZB_BERR_N;
    m_dly #(.W(23), .TMIN(1.4), .TMAX(4.9), .SEED(SEED + 1)) u101 (.a(Z_A), .y(ZB_A));
    m_dly #(.W(9),  .TMIN(1.4), .TMAX(4.9), .SEED(SEED + 2)) u102 (
        .a({Z_AS_N, Z_UDS_N, Z_LDS_N, Z_READ, Z_DOE, Z_E7M, Z_CFGIN_N, Z_BUSRST_N, Z_BERR_N}),
        .y({ZB_AS_N, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_E7M, ZB_CFGIN_N, ZB_BUSRST_N, ZB_BERR_N}));

    // ---------------- FPGA
    wire ZF_SLAVE_N_i, ZF_CFGOUT_N_i, ZF_INT2_N_i, ZF_INT6_N_i, ZF_XRDY_i, ZF_OVR_N_i, ZF_DTACK_N_i;
    wire ZF_DBUF_DIR_i, ZF_DBUF_OE_N_i, ZF_ARM_i;
    wire [3:0] led;
    wire [15:0] LD;
    m_bushold #(.W(16)) u_ld_hold (.bus(LD));   // U103 A-port bus-hold keeps the last level
    wire EN_OK;
    z2_top dut (
        .clk_core(clk_core),
        .ZB_A(ZB_A), .ZB_AS_N(ZB_AS_N), .ZB_UDS_N(ZB_UDS_N), .ZB_LDS_N(ZB_LDS_N), .ZB_READ(ZB_READ),
        .ZB_DOE(ZB_DOE), .ZB_E7M(ZB_E7M), .ZB_CFGIN_N(ZB_CFGIN_N), .ZB_BUSRST_N(ZB_BUSRST_N),
        .ZB_BERR_N(ZB_BERR_N), .EN_OK(EN_OK), .ZF_ARM(ZF_ARM_i),
        .ZF_SLAVE_N(ZF_SLAVE_N_i), .ZF_CFGOUT_N(ZF_CFGOUT_N_i), .ZF_INT2_N(ZF_INT2_N_i), .ZF_INT6_N(ZF_INT6_N_i),
        .ZF_XRDY(ZF_XRDY_i), .ZF_OVR_N(ZF_OVR_N_i), .ZF_DTACK_N(ZF_DTACK_N_i),
        .ZF_DBUF_DIR(ZF_DBUF_DIR_i), .ZF_DBUF_OE_N(ZF_DBUF_OE_N_i),
        .LD(LD), .DIP_MODE_B(dip_mode_b), .DIP_INT6(dip_int6), .DIP_DISABLE(dip_disable), .LED(led));

    // Blank or configuring FPGA: I/O tri-stated (weak pull-down, overridden by the board
    // resistors). The design restarts from its power-on state when configuration completes.
    always @(fpga_on)
        if (!fpga_on) force dut.por_cnt = 4'd0;
        else          release dut.por_cnt;

    // FPGA output pins: delay model, then the sheet-1 default resistors when tri-stated
    wire s_comb_slave, s_comb_xrdy, s_comb_oe, s_reg_dir, s_reg_cfgout, s_reg_int2, s_reg_int6, s_reg_arm;
    m_dly #(.W(3), .TMIN(FPGA_TMIN), .TMAX(FPGA_TMAX), .SEED(SEED + 3)) u_fpga_comb (
        .a({ZF_SLAVE_N_i, ZF_XRDY_i, ZF_DBUF_OE_N_i}), .y({s_comb_slave, s_comb_xrdy, s_comb_oe}));
    m_dly #(.W(5), .TMIN(TCO_MIN), .TMAX(TCO_MAX), .SEED(SEED + 4)) u_fpga_reg (
        .a({ZF_DBUF_DIR_i, ZF_CFGOUT_N_i, ZF_INT2_N_i, ZF_INT6_N_i, ZF_ARM_i}),
        .y({s_reg_dir, s_reg_cfgout, s_reg_int2, s_reg_int6, s_reg_arm}));
    tri1 ZF_SLAVE_N, ZF_CFGOUT_N, ZF_INT2_N, ZF_INT6_N, ZF_XRDY, ZF_DBUF_OE_N;   // R101-R105, R108 2.2k up
    tri0 ZF_DBUF_DIR;                                                             // R109 10k down
    tri0 ZF_ARM;                                                                  // R122 10k down
    assign ZF_SLAVE_N   = fpga_on ? s_comb_slave : 1'bz;
    assign ZF_XRDY      = fpga_on ? s_comb_xrdy  : 1'bz;
    assign ZF_DBUF_OE_N = fpga_on ? s_comb_oe    : 1'bz;
    assign ZF_DBUF_DIR  = fpga_on ? s_reg_dir    : 1'bz;
    assign ZF_CFGOUT_N  = fpga_on ? s_reg_cfgout : 1'bz;
    assign ZF_INT2_N    = fpga_on ? s_reg_int2   : 1'bz;
    assign ZF_INT6_N    = fpga_on ? s_reg_int6   : 1'bz;
    assign ZF_ARM       = fpga_on ? s_reg_arm    : 1'bz;

    // ---------------- U108/U109 supervisors + JP101 -> EN_OK (R121 10k up)
    m_supervisors #(.TD(SUP_TD)) u_sup (.p3_ok(pwr3), .p5_ok(pwr5), .jumper(jumper), .en_ok(EN_OK));
    assign en_ok = EN_OK;

    // ---------------- U106 NAND -> CARD_EN_N (R123 10k up); U107 OR gating
    wire CARD_EN_N, DBUF_OE_G_N, XRDY_G, INT2_G_N, INT6_G_N;
    m_nand2 #(.SEED(SEED + 5)) u106 (.a(EN_OK), .b(ZF_ARM), .pwr(pwr3), .y(CARD_EN_N));
    m_or2   #(.SEED(SEED + 6)) u107a (.a(ZF_DBUF_OE_N), .b(CARD_EN_N), .pwr(pwr3), .y(DBUF_OE_G_N));
    m_or2   #(.SEED(SEED + 7)) u107b (.a(ZF_XRDY),      .b(CARD_EN_N), .pwr(pwr3), .y(XRDY_G));
    m_or2   #(.SEED(SEED + 8)) u107c (.a(ZF_INT2_N),    .b(CARD_EN_N), .pwr(pwr3), .y(INT2_G_N));
    m_or2   #(.SEED(SEED + 9)) u107d (.a(ZF_INT6_N),    .b(CARD_EN_N), .pwr(pwr3), .y(INT6_G_N));
    assign card_en_n = CARD_EN_N;

    // ---------------- U103 data transceiver (RN101-RN104 22R not modelled separately)
    wire a_drv;
    m_lvch16t245 #(.SEED(SEED + 10)) u103 (.dir(ZF_DBUF_DIR), .oe_n(DBUF_OE_G_N), .pwr(pwr_both),
                                           .a(LD), .b(Z_D), .a_drv(a_drv), .b_drv(d_drv));

    // ---------------- U104 /SLAVEn, /CFGOUTn driver (+ R117/R118)
    wire u104_drv;
    m_lvc8t245_2ch #(.SEED(SEED + 11)) u104 (.oe_n(CARD_EN_N), .pwr(pwr_both),
                                             .a({ZF_CFGOUT_N, ZF_SLAVE_N}), .b({Z_CFGOUT_N, Z_SLAVE_N}),
                                             .drv(u104_drv));

    // ---------------- U105 open-drain drivers
    m_od #(.SEED(SEED + 12)) u105_xrdy (.a(XRDY_G),   .pwr(pwr3), .y(Z_XRDY));
    m_od #(.SEED(SEED + 13)) u105_int2 (.a(INT2_G_N), .pwr(pwr3), .y(Z_INT2_N));
    m_od #(.SEED(SEED + 14)) u105_int6 (.a(INT6_G_N), .pwr(pwr3), .y(Z_INT6_N));

    // ---------------- local-bus contention monitor: FPGA LD drive (tCO window) vs U103 A port
    wire fpga_ld_drv;
    m_en_window #(.TMIN(TCO_MIN), .TMAX(TCO_MAX)) u_ldw (.en(dut.ld_oe & fpga_on), .w(fpga_ld_drv));
    assign ld_conflict = fpga_ld_drv & a_drv;
    always @(posedge ld_conflict)
        if ($realtime > 1.0)                 // ignore X resolution at time 0
            $display("ASSERT-FAIL %0t LD contention: FPGA and U103 A port both enabled", $realtime);
endmodule
