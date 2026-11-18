// SPDX-License-Identifier: MIT
// Stage 2 FPGA top level (LCMXO2-2000HC-4TG144C). Port names match the sheet-1 nets.
// Pin LOCATEs are assigned when sheet 2 is drawn (hdl/syn/z2_top.lpf).
`default_nettype none
module z2_top (
    input  wire        clk_core,      // 50 MHz [A] (sheet 2)
    // buffered Zorro inputs (sheet 1, U101/U102)
    input  wire [23:1] ZB_A,
    input  wire        ZB_AS_N,
    input  wire        ZB_UDS_N,
    input  wire        ZB_LDS_N,
    input  wire        ZB_READ,
    input  wire        ZB_DOE,
    input  wire        ZB_E7M,        // timing reference / monitor only (R-29), unused in Stage 2
    input  wire        ZB_CFGIN_N,
    input  wire        ZB_BUSRST_N,
    input  wire        ZB_BERR_N,
    // card enable (sheet 1)
    input  wire        EN_OK,         // supervisors + DISABLE jumper (wired-AND)
    output wire        ZF_ARM,        // 1 = join the bus (gated with EN_OK by U106)
    // FPGA-driven Zorro controls (sheet 1)
    output wire        ZF_SLAVE_N,
    output wire        ZF_CFGOUT_N,
    output wire        ZF_INT2_N,
    output wire        ZF_INT6_N,
    output wire        ZF_XRDY,
    output wire        ZF_OVR_N,
    output wire        ZF_DTACK_N,
    output wire        ZF_DBUF_DIR,
    output wire        ZF_DBUF_OE_N,
    // local data bus (U103 A port; SRAM in Stage 3)
    inout  wire [15:0] LD,
    // DIP switches (sheet 6), active high after the switch pull-ups/inversion [A]
    input  wire        DIP_MODE_B,
    input  wire        DIP_INT6,
    input  wire        DIP_DISABLE,
    output wire [3:0]  LED
);
    // power-on reset: 15 clocks after configuration (GSR has already set the INIT values)
    reg [3:0] por_cnt = 4'd0;
    always @(posedge clk_core) if (por_cnt != 4'hF) por_cnt <= por_cnt + 4'd1;
    wire por = (por_cnt != 4'hF);

    wire [15:0] ld_dout;
    wire        ld_oe;
    assign LD = ld_oe ? ld_dout : 16'hzzzz;

    // Rev 1 uses the automatic motherboard DTACK: own /OVR and /DTACK stay inactive.
    assign ZF_OVR_N   = 1'b1;
    assign ZF_DTACK_N = 1'b1;

    z2_core u_core (
        .clk(clk_core), .por(por),
        .zb_a(ZB_A), .zb_as_n(ZB_AS_N), .zb_uds_n(ZB_UDS_N), .zb_lds_n(ZB_LDS_N), .zb_read(ZB_READ),
        .zb_doe(ZB_DOE), .zb_cfgin_n(ZB_CFGIN_N), .zb_busrst_n(ZB_BUSRST_N), .zb_berr_n(ZB_BERR_N),
        .en_ok(EN_OK), .dip_mode_b(DIP_MODE_B), .dip_int6(DIP_INT6), .dip_disable(DIP_DISABLE),
        .ld_in(LD), .ld_dout(ld_dout), .ld_oe(ld_oe),
        .zf_slave_n(ZF_SLAVE_N), .zf_cfgout_n(ZF_CFGOUT_N), .zf_xrdy(ZF_XRDY),
        .zf_int2_n(ZF_INT2_N), .zf_int6_n(ZF_INT6_N),
        .zf_dbuf_dir(ZF_DBUF_DIR), .zf_dbuf_oe_n(ZF_DBUF_OE_N), .zf_arm(ZF_ARM),
        .led(LED));
endmodule
`default_nettype wire
