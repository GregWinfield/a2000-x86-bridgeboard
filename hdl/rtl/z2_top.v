// SPDX-License-Identifier: MIT
// FPGA top level (LCMXO2-2000HC-4TG144C), Stage 3. Port names match the sheet-1 and sheet-3 nets.
// Pin LOCATEs are assigned when sheet 2 is drawn (hdl/syn/z2_top.lpf).
//
//   z2_core   Zorro II slave, AutoConfig, bus FSM (sheet 1 interface)
//   z2_lbus   local-bus arbiter + SRAM sequencer: WHO MAY ACCESS THE MEMORY (sheet 3)
//   z2_mbx    queues + interrupts: WHO HAS WORK TO DO (sheet 3)
//   z2_hostif host port. Stub until the sheet-4 SPI slave; a bus-functional model in simulation
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
    input  wire        ZB_E7M,        // timing reference / monitor only (R-29), unused
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
    output wire        ZF_DBUF_DIR,
    output wire        ZF_DBUF_OE_N,
    // local data bus: U103 A port (sheet 1) and SRAM U301 data (sheet 3)
    inout  wire [15:0] LD,
    // SRAM U301 address and control (sheet 3); every pin straight from one flip-flop
    output wire [17:0] SA,
    output wire        SRAM_CE_N,
    output wire        SRAM_OE_N,
    output wire        SRAM_WE_N,
    output wire        SRAM_UB_N,
    output wire        SRAM_LB_N,
    // host link (sheet 4): interrupt to the RP2040 (the SPI pins join with the SPI slave)
    output wire        RP_IRQ_N,
    // DIP switches (sheet 6), active high after the switch pull-ups/inversion [A]
    input  wire        DIP_MODE_B,
    input  wire        DIP_INT6,
    input  wire        DIP_DISABLE,
    output wire [1:0]  LED            // {FAULT, READY} (C-17)
);
    // power-on reset: 15 clocks after configuration (GSR has already set the INIT values)
    reg [3:0] por_cnt = 4'd0;
    always @(posedge clk_core) if (por_cnt != 4'hF) por_cnt <= por_cnt + 4'd1;
    wire por = (por_cnt != 4'hF);

    // Rev 1 uses the automatic motherboard DTACK. ZF_OVR_N / ZF_DTACK_N are not routed to the
    // FPGA (C-17): on sheet 1, R106/R107 hold the U105 inputs high and R119/R120 (DNP) isolate them.

    // ---------------- local data bus: at most one FPGA driver (formal X2)
    wire [15:0] ld_dout, h_ld_dout;
    wire        ld_oe, h_ld_oe;
    assign LD = ld_oe ? ld_dout : (h_ld_oe ? h_ld_dout : 16'hzzzz);

    // ---------------- interconnect
    wire [17:0] zq_addr;
    wire        zq_ce, zq_oe, zq_we, zq_ub, zq_lb, z_res, z_quiet, zs_drv, h_quiet, h_busy;
    wire        zr_we, z_irq;
    wire [3:0]  zr_widx, zr_ridx;
    wire [1:0]  zr_be;
    wire [15:0] zr_wdata, zr_rdata;
    wire        zrst, busrst, configured, mode_b, en_ok_s;

    z2_core u_core (
        .clk(clk_core), .por(por),
        .zb_a(ZB_A), .zb_as_n(ZB_AS_N), .zb_uds_n(ZB_UDS_N), .zb_lds_n(ZB_LDS_N), .zb_read(ZB_READ),
        .zb_doe(ZB_DOE), .zb_cfgin_n(ZB_CFGIN_N), .zb_busrst_n(ZB_BUSRST_N), .zb_berr_n(ZB_BERR_N),
        .en_ok(EN_OK), .dip_mode_b(DIP_MODE_B), .dip_int6(DIP_INT6), .dip_disable(DIP_DISABLE),
        .ld_in(LD), .ld_dout(ld_dout), .ld_oe(ld_oe),
        .zf_slave_n(ZF_SLAVE_N), .zf_cfgout_n(ZF_CFGOUT_N), .zf_xrdy(ZF_XRDY),
        .zf_int2_n(ZF_INT2_N), .zf_int6_n(ZF_INT6_N),
        .zf_dbuf_dir(ZF_DBUF_DIR), .zf_dbuf_oe_n(ZF_DBUF_OE_N), .zf_arm(ZF_ARM),
        .led(LED),
        .zq_addr(zq_addr), .zq_ce(zq_ce), .zq_oe(zq_oe), .zq_we(zq_we), .zq_ub(zq_ub), .zq_lb(zq_lb),
        .z_res(z_res), .z_quiet(z_quiet), .zs_drv(zs_drv), .h_quiet(h_quiet),
        .zr_we(zr_we), .zr_widx(zr_widx), .zr_be(zr_be), .zr_wdata(zr_wdata), .zr_ridx(zr_ridx),
        .zr_rdata(zr_rdata), .z_irq(z_irq),
        .zrst_o(zrst), .busrst_o(busrst), .configured_o(configured), .mode_b_o(mode_b), .en_ok_o(en_ok_s));

    // ---------------- host port (sheet 4 SPI slave; stub or BFM until then)
    wire        h_req, h_we, h_reg, h_ack;
    wire [17:0] h_addr;
    wire [1:0]  h_be;
    wire [15:0] h_wdata, h_rdata;
    z2_hostif u_host (.clk(clk_core), .por(por), .h_req(h_req), .h_we(h_we), .h_reg(h_reg), .h_addr(h_addr),
                      .h_be(h_be), .h_wdata(h_wdata), .h_ack(h_ack), .h_rdata(h_rdata));

    // demultiplex by space: SRAM -> z2_lbus, registers -> z2_mbx
    wire        lb_ack, mb_ack;
    wire [15:0] lb_rdata, mb_rdata;
    assign h_ack   = lb_ack | mb_ack;
    assign h_rdata = h_reg ? mb_rdata : lb_rdata;

    z2_lbus u_lbus (
        .clk(clk_core), .por(por),
        .zq_addr(zq_addr), .zq_ce(zq_ce), .zq_oe(zq_oe), .zq_we(zq_we), .zq_ub(zq_ub), .zq_lb(zq_lb),
        .z_res(z_res), .z_quiet(z_quiet), .zs_drv(zs_drv), .h_quiet(h_quiet), .h_busy(h_busy),
        .h_req(h_req & ~h_reg), .h_we(h_we), .h_addr(h_addr), .h_be(h_be), .h_wdata(h_wdata),
        .h_ack(lb_ack), .h_rdata(lb_rdata),
        .ld_in(LD), .h_ld_oe(h_ld_oe), .h_ld_dout(h_ld_dout),
        .sa(SA), .sram_ce_n(SRAM_CE_N), .sram_oe_n(SRAM_OE_N), .sram_we_n(SRAM_WE_N),
        .sram_ub_n(SRAM_UB_N), .sram_lb_n(SRAM_LB_N));

    z2_mbx u_mbx (
        .clk(clk_core), .por(por), .zrst(zrst), .busrst(busrst), .armed(ZF_ARM), .configured(configured),
        .mode_b(mode_b), .en_ok(en_ok_s),
        .zr_we(zr_we), .zr_widx(zr_widx), .zr_be(zr_be), .zr_wdata(zr_wdata), .zr_ridx(zr_ridx),
        .zr_rdata(zr_rdata), .z_irq(z_irq),
        .hr_req(h_req & h_reg), .hr_we(h_we), .hr_idx(h_addr[3:0]), .hr_be(h_be), .hr_wdata(h_wdata),
        .hr_ack(mb_ack), .hr_rdata(mb_rdata), .h_irq_n(RP_IRQ_N));
endmodule
`default_nettype wire
