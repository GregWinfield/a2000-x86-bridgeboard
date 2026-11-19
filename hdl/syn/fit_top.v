// SPDX-License-Identifier: MIT
// FPGA pin-budget fit test (synthesis and place-and-route only, never a real design).
// z2_top plus every FPGA signal still planned for sheets 4-6 (docs/pin-assignment-matrix.md section 4),
// for the owner's C-17 plan (2026-11-19) with option C-17b (C-26): 101 signals. /OVR and /DTACK are not
// routed to the FPGA; one FPGA LED (READY); PROGRAMN, INITN and DONE are configuration pins (SYSCONFIG);
// JTAG enabled; JTAGENB prohibited; pins fixed by tools/fpga/pinplan.py (z2_top.lpf). Each planned pin gets minimal logic so synthesis keeps it.
//   Z2_TOP=fit_top bash hdl/syn/run_diamond.sh <work dir>
`default_nettype none
module fit_top (
    input  wire        clk_core,
    input  wire [23:1] ZB_A,
    input  wire        ZB_AS_N, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_E7M, ZB_CFGIN_N, ZB_BUSRST_N, ZB_BERR_N,
    input  wire        EN_OK,
    output wire        ZF_ARM, ZF_SLAVE_N, ZF_CFGOUT_N, ZF_INT2_N, ZF_INT6_N, ZF_XRDY,
    output wire        ZF_DBUF_DIR, ZF_DBUF_OE_N,
    inout  wire [15:0] LD,
    output wire [17:0] SA,
    output wire        SRAM_CE_N, SRAM_OE_N, SRAM_WE_N, SRAM_UB_N, SRAM_LB_N,
    output wire        RP_IRQ_N,
    input  wire        DIP_MODE_B, DIP_INT6, DIP_DISABLE,
    output wire        LED_READY,
    // sheet 4 (host link): SPI to the real slave in z2_top
    input  wire        RP_SCK, RP_CS_N, RP_MOSI,
    output wire        RP_MISO, RP_ATTN,
    // planned for sheet 5 (power): X4 eFuse enable, fault, S0 sense; INA226 I2C and alert
    output wire        X4_PWR_EN,
    input  wire        X4_PWR_FLT_N, X4_S0_SENSE,
    inout  wire        I2C_SCL, I2C_SDA,
    input  wire        INA_ALERT_N,
    // planned for sheet 6: debug / expansion header
    inout  wire [3:0]  DBG
);
    z2_top u_top (
        .clk_core(clk_core), .ZB_A(ZB_A), .ZB_AS_N(ZB_AS_N), .ZB_UDS_N(ZB_UDS_N), .ZB_LDS_N(ZB_LDS_N),
        .ZB_READ(ZB_READ), .ZB_DOE(ZB_DOE), .ZB_E7M(ZB_E7M), .ZB_CFGIN_N(ZB_CFGIN_N), .ZB_BUSRST_N(ZB_BUSRST_N),
        .ZB_BERR_N(ZB_BERR_N), .EN_OK(EN_OK), .ZF_ARM(ZF_ARM), .ZF_SLAVE_N(ZF_SLAVE_N), .ZF_CFGOUT_N(ZF_CFGOUT_N),
        .ZF_INT2_N(ZF_INT2_N), .ZF_INT6_N(ZF_INT6_N), .ZF_XRDY(ZF_XRDY),
        .ZF_DBUF_DIR(ZF_DBUF_DIR), .ZF_DBUF_OE_N(ZF_DBUF_OE_N), .LD(LD), .SA(SA), .SRAM_CE_N(SRAM_CE_N),
        .SRAM_OE_N(SRAM_OE_N), .SRAM_WE_N(SRAM_WE_N), .SRAM_UB_N(SRAM_UB_N), .SRAM_LB_N(SRAM_LB_N),
        .RP_IRQ_N(RP_IRQ_N), .DIP_MODE_B(DIP_MODE_B), .DIP_INT6(DIP_INT6), .DIP_DISABLE(DIP_DISABLE), .LED_READY(LED_READY),
        .RP_SCK(RP_SCK), .RP_CS_N(RP_CS_N), .RP_MOSI(RP_MOSI), .RP_MISO(RP_MISO), .RP_ATTN(RP_ATTN));

    // placeholder logic: every planned input feeds a shift register that drives every planned output
    reg [7:0] sh = 8'd0;
    always @(posedge clk_core)
        sh <= {sh[6:0], X4_PWR_FLT_N ^ X4_S0_SENSE ^ INA_ALERT_N ^ ZB_E7M ^
                        I2C_SCL ^ I2C_SDA ^ (^DBG)};
    assign X4_PWR_EN = sh[2];
    assign I2C_SCL   = sh[4] ? 1'b0 : 1'bz;       // open drain
    assign I2C_SDA   = sh[5] ? 1'b0 : 1'bz;
    assign DBG       = sh[6] ? sh[7:4] : 4'bzzzz;
endmodule
`default_nettype wire
