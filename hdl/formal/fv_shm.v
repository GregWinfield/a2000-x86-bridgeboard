// SPDX-License-Identifier: MIT
// Formal harness for the shared-memory subsystem (Stage 3): z2_core + z2_lbus + z2_mbx, wired as
// in z2_top, with EVERY external input free: Zorro signals, the LD bus value, and the host port
// (any request pattern). Run with fv_shm.sby. The properties must hold for any input sequence.
//   X1 mutual exclusion on the SRAM pins
//   X2 at most one local-bus (LD) driver; X3 at least one idle clock between different drivers
//   X4 determinism: host activity never delays a Zorro local-bus action
//   X5 SRAM write protocol on the pins (both owners): /WE one clock, inside /CE, /OE high,
//      address stable from one clock before /WE falls until the clock after it rises
//   X6 bounded host wait while the Zorro side leaves the bus free
// z2_core's F1-F20 and z2_mbx's M1-M5 are proven again in this context.
`default_nettype none
module fv_shm (
    input  wire        clk,
    input  wire [23:1] zb_a,
    input  wire        zb_as_n, zb_uds_n, zb_lds_n, zb_read, zb_doe, zb_cfgin_n, zb_busrst_n, zb_berr_n,
    input  wire        en_ok, dip_mode_b, dip_int6, dip_disable,
    input  wire [15:0] ld_in,
    input  wire        h_req, h_we, h_reg,
    input  wire [17:0] h_addr,
    input  wire [1:0]  h_be,
    input  wire [15:0] h_wdata
);
    localparam integer GUARD = 2;
    localparam [3:0] ST_IDLE = 4'd0, ST_IGNORE = 4'd2;
    localparam [2:0] H_IDLE = 3'd0, H_RD1 = 3'd1, H_RD2 = 3'd2, H_WR1 = 3'd3, H_WR2 = 3'd4, H_WR3 = 3'd5;

    reg [3:0] por_cnt = 4'd0;
    always @(posedge clk) if (por_cnt != 4'hF) por_cnt <= por_cnt + 4'd1;
    wire por = (por_cnt != 4'hF);

    wire [15:0] ld_dout, h_ld_dout, zr_wdata, zr_rdata, lb_rdata, mb_rdata;
    wire        ld_oe, h_ld_oe;
    wire [17:0] zq_addr, SA;
    wire        zq_ce, zq_oe, zq_we, zq_ub, zq_lb, z_res, z_quiet, zs_drv, h_quiet, h_busy;
    wire        zr_we, z_irq, zrst, busrst, configured, mode_b, en_ok_s, lb_ack, mb_ack, rp_irq_n;
    wire [3:0]  zr_widx, zr_ridx, f_st;
    wire [1:0]  led;
    wire [1:0]  zr_be;
    wire [2:0]  f_res_cnt, f_h_st, f_h_idle_cnt;
    wire        f_nat_go, f_oe_wr_q, f_ld_oe, f_own_h, f_h_start;
    wire        zf_slave_n, zf_cfgout_n, zf_xrdy, zf_int2_n, zf_int6_n, zf_dbuf_dir, zf_dbuf_oe_n, zf_arm;
    wire        SRAM_CE_N, SRAM_OE_N, SRAM_WE_N, SRAM_UB_N, SRAM_LB_N;

    z2_core u_core (
        .clk(clk), .por(por),
        .zb_a(zb_a), .zb_as_n(zb_as_n), .zb_uds_n(zb_uds_n), .zb_lds_n(zb_lds_n), .zb_read(zb_read),
        .zb_doe(zb_doe), .zb_cfgin_n(zb_cfgin_n), .zb_busrst_n(zb_busrst_n), .zb_berr_n(zb_berr_n),
        .en_ok(en_ok), .dip_mode_b(dip_mode_b), .dip_int6(dip_int6), .dip_disable(dip_disable),
        .ld_in(ld_in), .ld_dout(ld_dout), .ld_oe(ld_oe),
        .zf_slave_n(zf_slave_n), .zf_cfgout_n(zf_cfgout_n), .zf_xrdy(zf_xrdy),
        .zf_int2_n(zf_int2_n), .zf_int6_n(zf_int6_n),
        .zf_dbuf_dir(zf_dbuf_dir), .zf_dbuf_oe_n(zf_dbuf_oe_n), .zf_arm(zf_arm), .led(led),
        .zq_addr(zq_addr), .zq_ce(zq_ce), .zq_oe(zq_oe), .zq_we(zq_we), .zq_ub(zq_ub), .zq_lb(zq_lb),
        .z_res(z_res), .z_quiet(z_quiet), .zs_drv(zs_drv), .h_quiet(h_quiet),
        .zr_we(zr_we), .zr_widx(zr_widx), .zr_be(zr_be), .zr_wdata(zr_wdata), .zr_ridx(zr_ridx),
        .zr_rdata(zr_rdata), .z_irq(z_irq),
        .zrst_o(zrst), .busrst_o(busrst), .configured_o(configured), .mode_b_o(mode_b), .en_ok_o(en_ok_s),
        .f_st(f_st), .f_res_cnt(f_res_cnt), .f_nat_go(f_nat_go), .f_oe_wr_q(f_oe_wr_q), .f_ld_oe(f_ld_oe));

    z2_lbus u_lbus (
        .clk(clk), .por(por),
        .zq_addr(zq_addr), .zq_ce(zq_ce), .zq_oe(zq_oe), .zq_we(zq_we), .zq_ub(zq_ub), .zq_lb(zq_lb),
        .z_res(z_res), .z_quiet(z_quiet), .zs_drv(zs_drv), .h_quiet(h_quiet), .h_busy(h_busy),
        .h_req(h_req & ~h_reg), .h_we(h_we), .h_addr(h_addr), .h_be(h_be), .h_wdata(h_wdata),
        .h_ack(lb_ack), .h_rdata(lb_rdata),
        .ld_in(ld_in), .h_ld_oe(h_ld_oe), .h_ld_dout(h_ld_dout),
        .sa(SA), .sram_ce_n(SRAM_CE_N), .sram_oe_n(SRAM_OE_N), .sram_we_n(SRAM_WE_N),
        .sram_ub_n(SRAM_UB_N), .sram_lb_n(SRAM_LB_N),
        .f_h_st(f_h_st), .f_h_idle_cnt(f_h_idle_cnt), .f_own_h(f_own_h), .f_h_start(f_h_start));

    z2_mbx #(.QD_LOG2(2)) u_mbx (
        .clk(clk), .por(por), .zrst(zrst), .busrst(busrst), .armed(zf_arm), .configured(configured),
        .mode_b(mode_b), .en_ok(en_ok_s),
        .zr_we(zr_we), .zr_widx(zr_widx), .zr_be(zr_be), .zr_wdata(zr_wdata), .zr_ridx(zr_ridx),
        .zr_rdata(zr_rdata), .z_irq(z_irq),
        .hr_req(h_req & h_reg), .hr_we(h_we), .hr_idx(h_addr[3:0]), .hr_be(h_be), .hr_wdata(h_wdata),
        .hr_ack(mb_ack), .hr_rdata(mb_rdata), .h_irq_n(rp_irq_n));

    // ==================================================================== properties
    wire sram_out = ~SRAM_CE_N & ~SRAM_OE_N & SRAM_WE_N;        // U301 drives LD
    wire reserved = (f_st != ST_IDLE) && (f_st != ST_IGNORE);
    reg  f_past = 1'b0;
    always @(posedge clk) f_past <= 1'b1;
    reg  [3:0] f_hage = 4'd15;                                  // clocks since the last host start
    always @(posedge clk) f_hage <= f_h_start ? 4'd0 : ((f_hage == 4'd15) ? 4'd15 : f_hage + 4'd1);
    reg  [4:0] f_hwait = 5'd0;                                  // host SRAM request waiting, bus free
    always @(posedge clk)
        f_hwait <= (h_req && !h_reg && !lb_ack && !z_res && !por) ? ((f_hwait == 5'd31) ? 5'd31 : f_hwait + 5'd1) : 5'd0;

    always @* begin
        // X1 while a host access occupies the SRAM pins, no Zorro request is active
        if (f_h_st != H_IDLE) assert(!zq_ce && !zq_oe && !zq_we);
        // X2 at most one LD driver: FPGA (Zorro read), FPGA (host write), SRAM, U103 (write phase)
        assert(!(f_ld_oe && h_ld_oe));
        assert(!(f_ld_oe && sram_out));
        assert(!(h_ld_oe && sram_out));
        assert(!(f_oe_wr_q && (f_ld_oe || h_ld_oe || sram_out)));
        // X4 a Zorro local-bus action that is due by Zorro-side conditions alone never waits for
        //    the host side: h_quiet already holds, so host traffic cannot change Zorro timing
        if (f_nat_go) assert(h_quiet);
        // X5 the SRAM write strobe: only inside /CE, never with /OE (pins, both owners)
        if (!SRAM_WE_N) assert(!SRAM_CE_N && SRAM_OE_N);
        // X6 bounded host wait: a held SRAM request completes within 10 clocks of a free bus
        assert(f_hwait <= 5'd10);
        // ---- helper invariants (k-induction): host phase <-> clocks since its start
        if ((f_h_st == H_RD1) || (f_h_st == H_WR1)) assert(f_hage == 4'd0);
        if ((f_h_st == H_RD2) || (f_h_st == H_WR2)) assert(f_hage == 4'd1);
        if (f_h_st == H_WR3) assert(f_hage == 4'd2);
        if (f_h_st != H_IDLE) assert(f_own_h);
        if (h_ld_oe) assert((f_h_st == H_WR1) || (f_h_st == H_WR2) || (f_h_st == H_WR3));
        if (f_own_h && sram_out) assert((f_h_st == H_RD1) || (f_h_st == H_RD2));
        if (!h_quiet) assert(f_hage <= 4'd4);
        if ((f_h_st == H_IDLE) && (f_h_idle_cnt < GUARD)) assert(f_hage >= 4'd2);
        // a host access starts only before the Zorro side's START, so while the host is not quiet
        // the Zorro FSM is younger than the host access and below the reservation floor
        if (!h_quiet && reserved) assert(f_res_cnt < f_hage);
    end

    always @(posedge clk) if (f_past && !$past(por)) begin
        // X3 at least one idle clock between different LD drivers
        if (h_ld_oe && !$past(h_ld_oe))     assert(!$past(f_ld_oe) && !$past(sram_out) && !$past(f_oe_wr_q));
        if (f_ld_oe && !$past(f_ld_oe))     assert(!$past(h_ld_oe) && !$past(sram_out) && !$past(f_oe_wr_q));
        if (sram_out && !$past(sram_out))   assert(!$past(h_ld_oe) && !$past(f_ld_oe) && !$past(f_oe_wr_q));
        if (f_oe_wr_q && !$past(f_oe_wr_q)) assert(!$past(h_ld_oe) && !$past(f_ld_oe) && !$past(sram_out));
        // X5 /WE low for exactly one clock; address stable while it is low and at the edge it rises
        if (!$past(SRAM_WE_N)) assert(SRAM_WE_N);
        if (!SRAM_WE_N) assert((SA == $past(SA)) && !$past(SRAM_CE_N) && (SRAM_UB_N == $past(SRAM_UB_N)) &&
                               (SRAM_LB_N == $past(SRAM_LB_N)));
        if (!$past(SRAM_WE_N)) assert(SA == $past(SA));
    end

    // reachability: the interleavings the proof is about actually occur
    always @(posedge clk) if (f_past) begin
        cover(lb_ack && $past(h_we));                            // host SRAM write completed
        cover(lb_ack && !$past(h_we));                           // host SRAM read completed
        cover(f_nat_go && (f_hage == 4'd5));                     // Zorro action right after a host write
        cover(zq_we && (f_hage <= 4'd12));                       // Zorro SRAM write shortly after host traffic
    end
endmodule
`default_nettype wire
