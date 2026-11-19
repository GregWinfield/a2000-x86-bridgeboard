// SPDX-License-Identifier: MIT
// Zorro II slave core (Stage 2 minimum system).
//   * arming: the card joins the bus only at a Zorro reset boundary, with EN_OK true
//   * AutoConfig (64 KB mode A / 512 KB mode B), shut-up, /CFGOUTn
//   * bus FSM driven by DATA-STROBE PHASES, so a read-modify-write cycle (/AS held
//     across a read phase and a write phase, MC68000 TAS) is handled as two phases
//   * transceiver direction/enable sequencing with guard intervals (no contention)
//   * Stage 2 test registers, interrupt test, XRDY wait states with a watchdog
//   * Stage 3: SRAM target (mode A: fixed window + 16 x 32 KB banked window; mode B: linear)
//     through the local-bus arbiter z2_lbus, and a register port to the queue/interrupt block
//     z2_mbx. Local-bus actions never happen before START + ZRES, so host (SPI-side) traffic
//     cannot change Zorro timing.
// Specification: docs/hdl/zorro-interface-spec.md (revision C), docs/hdl/shared-memory-spec.md.
`default_nettype none
module z2_core #(
    parameter integer GUARD      = 2,           // clocks: OE off -> DIR change -> OE on
    parameter integer WDOG_LIMIT = 100,         // XRDY watchdog, clocks (2.0 us at 50 MHz), < 256
    parameter integer ZRES       = 4,           // reservation floor: no local-bus action while res_cnt < ZRES
    parameter integer SRAM_RD_WAIT = 2,         // SRAM read: clocks from the read start to the XRDY release
    parameter [7:0]   HW_REV     = 8'h0A,
    parameter [7:0]   HDL_VER    = 8'h03,   // 03: sheet-4 host link (SPI slave)
    parameter [15:0]  MFR_ID     = 16'h07DB,    // prototype manufacturer ID 2011, TBV (R-18)
    parameter [7:0]   PRODUCT_ID = 8'h01,
    parameter [31:0]  SERIAL     = 32'h0000_0001
) (
    input  wire        clk,
    input  wire        por,          // power-on reset, active high, synchronous
    // buffered Zorro inputs (asynchronous to clk)
    input  wire [23:1] zb_a,
    input  wire        zb_as_n,
    input  wire        zb_uds_n,
    input  wire        zb_lds_n,
    input  wire        zb_read,
    input  wire        zb_doe,
    input  wire        zb_cfgin_n,
    input  wire        zb_busrst_n,
    input  wire        zb_berr_n,
    input  wire        en_ok,        // EN_OK: both supervisors released and no DISABLE jumper
    input  wire        dip_mode_b,
    input  wire        dip_int6,
    input  wire        dip_disable,
    // local data bus
    input  wire [15:0] ld_in,
    output reg  [15:0] ld_dout,
    output reg         ld_oe,
    // to the sheet-1 drivers
    output wire        zf_slave_n,
    output wire        zf_cfgout_n,
    output wire        zf_xrdy,
    output reg         zf_int2_n,
    output reg         zf_int6_n,
    output wire        zf_dbuf_dir,
    output wire        zf_dbuf_oe_n,
    output wire        zf_arm,
    output wire [1:0]  led,          // {FAULT, READY} (C-17: two FPGA LEDs)
    // Stage 3: local-bus arbiter (z2_lbus). zq_* are requests; z2_lbus puts them on the pins.
    output reg  [17:0] zq_addr,
    output reg         zq_ce, zq_oe, zq_we, zq_ub, zq_lb,
    output wire        z_res,        // Zorro reservation: the host may not start an SRAM access
    output wire        z_quiet,      // every Zorro-side local-bus driver off for >= GUARD clocks
    input  wire        zs_drv,       // SRAM outputs enabled for a Zorro read (z2_lbus pin registers)
    input  wire        h_quiet,      // host idle, its drivers off for >= GUARD clocks
    // Stage 3: shared registers (z2_mbx), board-window offsets $0040-$005E
    output reg         zr_we,
    output reg  [3:0]  zr_widx,
    output reg  [1:0]  zr_be,
    output reg  [15:0] zr_wdata,
    output wire [3:0]  zr_ridx,
    input  wire [15:0] zr_rdata,
    input  wire        z_irq,        // queue/event interrupt request from z2_mbx
    output wire        zrst_o,
    output wire        busrst_o,
    output wire        configured_o,
    output wire        mode_b_o,
    output wire        en_ok_o
`ifdef FORMAL
    ,                                // observation for the shared-memory proof (formal/fv_shm.v)
    output wire [3:0]  f_st,
    output wire [2:0]  f_res_cnt,
    output wire        f_nat_go,     // a local-bus action is due by Zorro-side conditions alone
    output wire        f_oe_wr_q,
    output wire        f_ld_oe
`endif
);
    // ------------------------------------------------------------------ state
    localparam [3:0] ST_IDLE   = 4'd0,  ST_START  = 4'd1,  ST_IGNORE = 4'd2,  ST_WAITDS = 4'd3,
                     ST_RD_DIR = 4'd4,  ST_RD_DRV = 4'd5,  ST_RD_HLD = 4'd6,  ST_BETWN  = 4'd7,
                     ST_WR_DIR = 4'd8,  ST_WR_CAP = 4'd9,  ST_WR_HLD = 4'd10, ST_ABORT  = 4'd11;

    reg  [3:0]  st;
    reg         configured, shutup, pend_cfg, pend_shut;
    reg  [23:16] base;
    reg         match_en, care_lo;
    reg  [23:16] cmp;
    reg         sel_q, tgt_ac, ph_any, ph_two, ph_rd, held;
    reg  [23:1] addr_q;
    reg         dir_q, dir_req, oe_rd_q, oe_wr_q, hold_q;
    reg  [2:0]  oe_idle_cnt, dir_cnt, wr_cnt;
    reg  [7:0]  wd_cnt;
    reg         wd_trip, wd_flag;
    reg         zero_wait, irq_en, int_sel, irq_pend;
    reg  [1:0]  led_r;                // CONTROL b5..b4: LED test
    reg  [15:0] scratch0, scratch1, zcycles, waitstats, wdog_events, rmw_cycles, berr_events, ticks;
    reg  [9:0]  tick_pre;
    reg         berr_s_d;
    reg  [1:0]  brst_cnt;
    reg         busrst_q;
    reg         mode_b_l, armed;
    reg  [15:0] brd_rdata;
    reg  [3:0]  bank;                 // mode A banked window: SRAM bank (16 x 32 KB)
    reg  [1:0]  rd_cnt;               // read: clocks until the XRDY release
    reg  [2:0]  res_cnt;              // clocks since START (saturating), for the reservation floor

    initial begin
        st = ST_IDLE; configured = 1'b0; shutup = 1'b0; pend_cfg = 1'b0; pend_shut = 1'b0; base = 8'h00;
        match_en = 1'b0; care_lo = 1'b1; cmp = 8'hE8;
        sel_q = 1'b0; tgt_ac = 1'b0; ph_any = 1'b0; ph_two = 1'b0; ph_rd = 1'b0; held = 1'b0; addr_q = 23'd0;
        dir_q = 1'b0; dir_req = 1'b0; oe_rd_q = 1'b0; oe_wr_q = 1'b0; hold_q = 1'b1; ld_oe = 1'b0; ld_dout = 16'h0000;
        oe_idle_cnt = 3'd0; dir_cnt = 3'd0; wr_cnt = 3'd0; wd_cnt = 8'd0; wd_trip = 1'b0; wd_flag = 1'b0;
        // (guard counters start at the GSR value 0 and saturate during the 15-clock por)
        zero_wait = 1'b0; irq_en = 1'b0; int_sel = 1'b0; irq_pend = 1'b0; led_r = 2'd0;
        scratch0 = 16'h0000; scratch1 = 16'h0000; zcycles = 16'h0000; waitstats = 16'h0000;
        wdog_events = 16'h0000; rmw_cycles = 16'h0000; berr_events = 16'h0000; ticks = 16'h0000;
        tick_pre = 10'd0; berr_s_d = 1'b0; brst_cnt = 2'd0; busrst_q = 1'b0; mode_b_l = 1'b0; armed = 1'b0;
        zf_int2_n = 1'b1; zf_int6_n = 1'b1;
        bank = 4'd0; rd_cnt = 2'd0; res_cnt = 3'd0;
        zq_addr = 18'd0; zq_ce = 1'b0; zq_oe = 1'b0; zq_we = 1'b0; zq_ub = 1'b0; zq_lb = 1'b0;
        zr_we = 1'b0; zr_widx = 4'd0; zr_be = 2'b00; zr_wdata = 16'h0000;
    end

    // ------------------------------------------------------------------ synchronisers
    // INIT: strobes, READ, /CFGIN, /BUSRST and /BERR start NEGATED; EN_OK starts false.
    // /BUSRST must start negated so that an FPGA (re)configured while the Amiga runs
    // can never arm without observing a real reset.
    wire as_n_s, uds_n_s, lds_n_s, read_s, cfgin_n_s, busrst_n_s, berr_n_s, en_ok_s;
    z2_sync #(.W(8), .INIT(8'b1111_1110)) u_sync (
        .clk(clk),
        .d({zb_as_n, zb_uds_n, zb_lds_n, zb_read, zb_cfgin_n, zb_busrst_n, zb_berr_n, en_ok}),
        .q({as_n_s,  uds_n_s,  lds_n_s,  read_s,  cfgin_n_s,  busrst_n_s,  berr_n_s,  en_ok_s}));

    wire as_s    = ~as_n_s;
    wire uds_s   = ~uds_n_s;
    wire lds_s   = ~lds_n_s;
    wire ds_s    = uds_s | lds_s;
    wire rd_s    = read_s;
    wire cfgin_s = ~cfgin_n_s;
    wire berr_s  = ~berr_n_s;
    wire zrst    = por | busrst_q;   // Zorro-domain reset (AutoConfig state, bus FSM)

    // Simulation hook: the testbench forces this to 1 to stall data phases and
    // exercise the XRDY watchdog. Constant 0 in synthesis.
    wire stall_test = 1'b0;

    // ------------------------------------------------------------------ combinational decode
    wire sel_c;
    z2_decode u_dec (
        .a_hi(zb_a[23:16]), .as_n(zb_as_n), .berr_n(zb_berr_n), .rd(zb_read), .doe(zb_doe),
        .uds_n(zb_uds_n), .lds_n(zb_lds_n),
        .match_en(match_en), .cmp(cmp), .care_lo(care_lo),
        .hold_q(hold_q), .oe_rd_q(oe_rd_q), .oe_wr_q(oe_wr_q), .dir_q(dir_q),
        .sel(sel_c), .slave_n(zf_slave_n), .xrdy(zf_xrdy), .dbuf_oe_n(zf_dbuf_oe_n));

    assign zf_dbuf_dir = dir_q;
    // /CFGOUTn: asserted while /CFGINn is asserted and the board is configured or shut up.
    // When the card is not armed, sheet-1 U104 is disabled and the A2000's own /CFGOUTn
    // pull-down passes the chain (empty-slot behaviour).
    assign zf_cfgout_n = zb_cfgin_n | ~(configured | shutup);
    assign zf_arm      = armed;
    // READY (LED0) alone shows the card state, so it suffices for standalone diagnostics:
    //   off = not armed (also FPGA blank: pin Hi-Z); slow blink = armed, waiting for AutoConfig;
    //   steady = configured; fast blink = watchdog flag set (fault).
    // FAULT (LED1): watchdog flag, or an interrupt asserted towards the Amiga.
    wire led_ready = wd_flag ? ticks[11] : configured ? 1'b1 : armed ? ticks[14] : 1'b0;
    wire led_fault = wd_flag | (irq_en & (irq_pend | z_irq));
    assign led         = led_r | {led_fault, led_ready};
    assign zrst_o       = zrst;
    assign busrst_o     = busrst_q;
    assign configured_o = configured;
    assign mode_b_o     = mode_b_l;
    assign en_ok_o      = en_ok_s;

    // ------------------------------------------------------------------ read data
    function [7:0] ac_reg;               // logical AutoConfig register values
        input [5:0] r;                   // register index = offset / 4
        input       mb;                  // mode B (512 KB)
        begin
            case (r)
                6'h00:   ac_reg = mb ? 8'hC4 : 8'hC1;   // $00 er_Type: Zorro II, 512 KB / 64 KB
                6'h01:   ac_reg = PRODUCT_ID;            // $04 er_Product
                6'h02:   ac_reg = mb ? 8'h80 : 8'h00;    // $08 er_Flags
                6'h04:   ac_reg = MFR_ID[15:8];          // $10 er_Manufacturer (high)
                6'h05:   ac_reg = MFR_ID[7:0];           // $14 er_Manufacturer (low)
                6'h06:   ac_reg = SERIAL[31:24];         // $18 er_SerialNumber
                6'h07:   ac_reg = SERIAL[23:16];         // $1C
                6'h08:   ac_reg = SERIAL[15:8];          // $20
                6'h09:   ac_reg = SERIAL[7:0];           // $24
                default: ac_reg = 8'h00;                 // $0C, $28.. (no diag ROM), reserved
            endcase
        end
    endfunction

    wire [5:0]  ac_r      = addr_q[7:2];
    wire [7:0]  ac_v      = ac_reg(ac_r, mode_b_l);
    wire [3:0]  ac_nib    = addr_q[1] ? ac_v[3:0] : ac_v[7:4];   // NN = high nibble, NN+2 = low
    wire [3:0]  ac_phys   = (ac_r == 6'h00) ? ac_nib : ~ac_nib;  // all but $00/$02 inverted
    wire        reg_space = mode_b_l ? (addr_q[18:12] == 7'd0) : (addr_q[15:12] == 4'd0);
    wire [10:0] ridx      = addr_q[11:1];
    wire        tgt_mem   = ~tgt_ac & ~reg_space;                // board window outside the registers
    wire        mbx_space = (ridx[10:4] == 7'd2);                // $0040-$005E: z2_mbx registers
    assign      zr_ridx   = ridx[3:0];
    // SRAM word address. Mode A: $1000-$7FFF -> SRAM $01000-$07FFF; $8000-$FFFF -> bank x 32 KB.
    // Mode B: the 512 KB window maps linearly (the first 4 KB are the registers).
    wire [17:0] sram_wa   = mode_b_l ? addr_q[18:1] : (addr_q[15] ? {bank, addr_q[14:1]} : {4'd0, addr_q[14:1]});
    wire [15:0] status_w  = {5'd0, armed, en_ok_s, wd_flag, 1'b0, dip_disable, dip_int6, dip_mode_b,
                             1'b0, zero_wait, int_sel, mode_b_l};
    wire [15:0] control_w = {8'd0, 2'b00, led_r, 1'b0, int_sel, irq_en, zero_wait};

    always @* begin
        case (ridx)
            11'd0:   brd_rdata = 16'h4252;             // $0000 MAGIC "BR"
            11'd1:   brd_rdata = {HW_REV, HDL_VER};    // $0002 VERSION
            11'd2:   brd_rdata = status_w;             // $0004 STATUS
            11'd3:   brd_rdata = control_w;            // $0006 CONTROL
            11'd4:   brd_rdata = scratch0;             // $0008 SCRATCH0
            11'd5:   brd_rdata = scratch1;             // $000A SCRATCH1
            11'd6:   brd_rdata = zcycles;              // $000C ZCYCLES
            11'd7:   brd_rdata = ticks;                // $000E TICKS
            11'd8:   brd_rdata = {15'd0, irq_pend};    // $0010 IRQ_STATUS
            11'd10:  brd_rdata = waitstats;            // $0014 WAITSTATS
            11'd11:  brd_rdata = wdog_events;          // $0016 WDOG_EVENTS
            11'd12:  brd_rdata = rmw_cycles;           // $0018 RMW_CYCLES
            11'd13:  brd_rdata = berr_events;          // $001A BERR_EVENTS
            11'd16:  brd_rdata = {12'd0, bank};        // $0020 BANK (mode A)
            default: brd_rdata = 16'h0000;             // $0012 IRQ_SET (write-only), reserved
        endcase
    end
    wire [15:0] rdata = tgt_ac ? {ac_phys, 12'hFFF} : (mbx_space ? zr_rdata : brd_rdata);

    // ------------------------------------------------------------------ helpers
    wire oe_quiet    = (oe_idle_cnt >= GUARD);   // every enable off for >= GUARD clocks
    wire dir_settled = (dir_cnt >= GUARD);       // DIR unchanged for >= GUARD clocks
    wire res_ok      = (res_cnt >= ZRES);        // reservation floor reached (property X4)
    // The Zorro side reserves the local bus from the clock /AS is seen until the cycle ends,
    // except for a cycle it is ignoring (another card's): host accesses may then proceed.
    assign z_res     = (st == ST_IDLE) ? as_s : (st != ST_IGNORE);
    assign z_quiet   = oe_quiet;
    wire lane_hi     = uds_s;                    // D15..D8
    wire lane_lo     = lds_s;                    // D7..D0

    // ------------------------------------------------------------------ /BUSRST filter
    // 4 consecutive synchronised samples are needed to change the filtered state.
    always @(posedge clk) begin
        if (por) begin
            brst_cnt <= 2'd0;
            busrst_q <= 1'b0;
        end else if (busrst_n_s == busrst_q) begin      // raw (active-high ~busrst_n_s) differs
            if (brst_cnt == 2'd3) begin
                busrst_q <= ~busrst_q;
                brst_cnt <= 2'd0;
            end else
                brst_cnt <= brst_cnt + 2'd1;
        end else
            brst_cnt <= 2'd0;
    end

    // ------------------------------------------------------------------ DIP latch, arming
    always @(posedge clk) begin
        if (zrst) mode_b_l <= dip_mode_b;
        if (por)           armed <= 1'b0;
        else if (!en_ok_s) armed <= 1'b0;            // power not good or DISABLE jumper fitted
        else if (busrst_q) armed <= ~dip_disable;    // join (or not) only inside a Zorro reset
    end

    // ------------------------------------------------------------------ interrupt outputs (registered)
    always @(posedge clk) begin
        zf_int2_n <= ~(armed & irq_en & (irq_pend | z_irq) & ~int_sel);
        zf_int6_n <= ~(armed & irq_en & (irq_pend | z_irq) &  int_sel);
    end

    // ------------------------------------------------------------------ main sequential logic
    always @(posedge clk) begin
        // guard counters (saturating)
        if (oe_rd_q | oe_wr_q | ld_oe | zs_drv) oe_idle_cnt <= 3'd0;
        else if (oe_idle_cnt != 3'd7)  oe_idle_cnt <= oe_idle_cnt + 3'd1;
        if (dir_cnt != 3'd7)           dir_cnt     <= dir_cnt + 3'd1;
        zr_we <= 1'b0;                                  // one-clock register write strobe to z2_mbx

        // direction controller: DIR changes only while every enable has been off for GUARD clocks
        if ((dir_q != dir_req) && !oe_rd_q && !oe_wr_q && !ld_oe && oe_quiet) begin
            dir_q   <= dir_req;
            dir_cnt <= 3'd0;
        end

        // free-running tick counter (clk / 1024)
        tick_pre <= tick_pre + 10'd1;
        if (tick_pre == 10'h3FF) ticks <= ticks + 16'd1;

        // /BERR events seen on the bus while armed (any cycle; survives /BUSRST)
        berr_s_d <= berr_s;
        if (berr_s && !berr_s_d && armed) berr_events <= berr_events + 16'd1;

        if (zrst) begin
            st <= ST_IDLE;
            configured <= 1'b0; shutup <= 1'b0; base <= 8'h00; pend_cfg <= 1'b0; pend_shut <= 1'b0;
            match_en <= 1'b0; cmp <= 8'hE8; care_lo <= 1'b1;
            sel_q <= 1'b0; tgt_ac <= 1'b0; ph_any <= 1'b0; ph_two <= 1'b0; ph_rd <= 1'b0; held <= 1'b0;
            oe_rd_q <= 1'b0; oe_wr_q <= 1'b0; ld_oe <= 1'b0; dir_req <= 1'b0;
            zq_ce <= 1'b0; zq_oe <= 1'b0; zq_we <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0; bank <= 4'd0; res_cnt <= 3'd0;
            hold_q <= 1'b1;
            zero_wait <= 1'b0; irq_en <= 1'b0; int_sel <= dip_int6; irq_pend <= 1'b0; led_r <= 2'd0;
            wd_cnt <= 8'd0; wd_trip <= 1'b0;
            zcycles <= 16'd0; waitstats <= 16'd0; rmw_cycles <= 16'd0;
        end else begin
            // ---- decode state: updated only between bus cycles, frozen during a cycle
            if (!armed)
                match_en <= 1'b0;
            else if ((st == ST_IDLE) && !as_s) begin
                match_en <= configured | (~shutup & cfgin_s);
                cmp      <= configured ? base : 8'hE8;
                care_lo  <= ~(configured & mode_b_l);
            end

            // ---- XRDY watchdog: bounds every continuous XRDY hold within one /AS cycle.
            // It is re-armed only when XRDY has been released (a completed phase), never
            // by a new strobe phase, so a master that toggles the strobes cannot defeat it.
            if ((st == ST_IDLE) || !as_s) begin
                wd_cnt  <= 8'd0;
                wd_trip <= 1'b0;
            end else if (sel_q && hold_q && !wd_trip) begin
                if (wd_cnt == WDOG_LIMIT - 1) begin
                    wd_trip     <= 1'b1;
                    wd_flag     <= 1'b1;
                    wdog_events <= wdog_events + 16'd1;
                end else
                    wd_cnt <= wd_cnt + 8'd1;
            end else if (!hold_q)
                wd_cnt <= 8'd0;

            // ---- reservation floor: clocks since START
            if (st == ST_IDLE)          res_cnt <= 3'd0;
            else if (res_cnt != 3'd7)   res_cnt <= res_cnt + 3'd1;

            // ---- bus-cycle FSM
            if ((st != ST_IDLE) && !as_s) begin
                // end of the bus cycle: everything off, bookkeeping, back to idle
                if (sel_q) begin
                    if (pend_cfg)  configured <= 1'b1;   // /CFGOUTn changes between cycles
                    if (pend_shut) shutup     <= 1'b1;
                    if (!tgt_ac)   zcycles    <= zcycles + 16'd1;
                    if (held)      waitstats  <= waitstats + 16'd1;
                    if (ph_two)    rmw_cycles <= rmw_cycles + 16'd1;
                end
                pend_cfg <= 1'b0; pend_shut <= 1'b0; sel_q <= 1'b0;
                oe_rd_q <= 1'b0; oe_wr_q <= 1'b0; ld_oe <= 1'b0; dir_req <= 1'b0;
                zq_ce <= 1'b0; zq_oe <= 1'b0; zq_we <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0;
                hold_q <= ~zero_wait;
                st <= ST_IDLE;
            end else begin
                case (st)
                ST_IDLE: begin
                    hold_q  <= ~zero_wait;               // XRDY-gated mode: hold from /AS
                    dir_req <= 1'b0;
                    if (as_s) st <= ST_START;
                end

                ST_START: begin                          // /AS seen for >= 1 clock: select is stable
                    sel_q  <= sel_c;
                    addr_q <= zb_a;
                    tgt_ac <= ~configured;
                    ph_any <= 1'b0; ph_two <= 1'b0; ph_rd <= 1'b0;
                    held   <= sel_c & hold_q;
                    if (sel_c)
                        st <= ST_WAITDS;
                    else begin
                        hold_q <= 1'b0;                  // never hold XRDY for a cycle we ignore
                        st     <= ST_IGNORE;
                    end
                end

                ST_IGNORE: hold_q <= 1'b0;               // not ours: wait for /AS negation

                ST_WAITDS, ST_BETWN: begin               // waiting for a data-strobe phase
                    if (berr_s)
                        st <= ST_ABORT;
                    else begin
                        if (wd_trip)
                            hold_q <= 1'b0;
                        else if ((st == ST_BETWN) && ph_rd && !rd_s)
                            hold_q <= ~zero_wait;        // RMW: READ fell after the read phase
                        if (ds_s) begin
                            ph_two <= ph_any;            // second phase within one /AS = RMW
                            ph_any <= 1'b1;
                            ph_rd  <= rd_s;
                            if (rd_s) begin dir_req <= 1'b1; st <= ST_RD_DIR; end
                            else      begin dir_req <= 1'b0; st <= ST_WR_DIR; end
                        end
                    end
                end

                ST_RD_DIR: begin                         // wait for DIR = A->B, settled
                    if (berr_s)
                        st <= ST_ABORT;
                    else if (!ds_s) begin
                        dir_req <= 1'b0;
                        st      <= ST_BETWN;
                    end else if (dir_q && dir_req && dir_settled && !oe_wr_q && res_ok && h_quiet &&
                                 (!stall_test || wd_trip)) begin
                        oe_rd_q <= 1'b1;                 // transceiver may drive Zorro with DOE & DS
                        if (tgt_mem && !wd_trip) begin   // SRAM drives LD (pins one clock later)
                            zq_addr <= sram_wa;
                            zq_ce   <= 1'b1; zq_oe <= 1'b1; zq_ub <= 1'b1; zq_lb <= 1'b1;
                            rd_cnt  <= SRAM_RD_WAIT;
                        end else begin                   // FPGA drives LD (U103 A port is an input)
                            ld_dout <= wd_trip ? 16'hFFFF : rdata;
                            ld_oe   <= 1'b1;
                            rd_cnt  <= 2'd0;
                        end
                        st      <= ST_RD_DRV;
                    end
                end

                ST_RD_DRV: begin                         // data on LD: release XRDY after rd_cnt clocks
                    if (rd_cnt == 2'd0) begin
                        hold_q <= 1'b0;
                        st     <= ST_RD_HLD;
                    end else begin
                        rd_cnt <= rd_cnt - 2'd1;
                        if (berr_s) st <= ST_ABORT;
                    end
                end

                ST_RD_HLD: begin                         // hold data until the strobe is negated
                    if (berr_s)
                        st <= ST_ABORT;
                    else if (!ds_s) begin                // normal end, or S7 of an RMW cycle
                        oe_rd_q <= 1'b0;
                        ld_oe   <= 1'b0;
                        zq_oe   <= 1'b0; zq_ce <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0;
                        dir_req <= 1'b0;
                        st      <= ST_BETWN;
                    end
                end

                ST_WR_DIR: begin                         // wait for DIR = B->A, settled, LD free
                    if (berr_s)
                        st <= ST_ABORT;
                    else if (!ds_s)
                        st <= ST_BETWN;
                    else if (!dir_q && !dir_req && dir_settled && oe_quiet && res_ok && h_quiet) begin
                        oe_wr_q <= 1'b1;                 // transceiver B->A drives LD
                        wr_cnt  <= 3'd0;
                        if (tgt_mem) begin               // SRAM write: address, /CE, lanes first
                            zq_addr <= sram_wa;
                            zq_ce   <= 1'b1; zq_ub <= lane_hi; zq_lb <= lane_lo;
                        end
                        st      <= ST_WR_CAP;
                    end
                end

                ST_WR_CAP: begin                         // let data settle through U103, then capture
                    if (berr_s) begin
                        zq_we <= 1'b0;                   // an SRAM write strobe never exceeds one clock
                        st    <= ST_ABORT;
                    end
                    else if (!ds_s) begin
                        oe_wr_q <= 1'b0;
                        ph_rd   <= 1'b0;
                        zq_we   <= 1'b0; zq_ce <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0;
                        st      <= ST_BETWN;
                    end else if (wr_cnt < GUARD)
                        wr_cnt <= wr_cnt + 3'd1;
                    else if (tgt_mem) begin
                        // SRAM write: data has been on LD for GUARD clocks; one-clock /WE pulse
                        // (pins one clock later), then release XRDY (/WE is already high).
                        if (wr_cnt == GUARD) begin
                            if (!wd_trip && !stall_test) zq_we <= 1'b1;   // a watchdog trip discards the write
                            if (!stall_test || wd_trip) wr_cnt <= wr_cnt + 3'd1;
                        end else if (wr_cnt == GUARD + 1) begin
                            zq_we  <= 1'b0;
                            wr_cnt <= wr_cnt + 3'd1;
                        end else begin
                            zq_ce <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0;
                            hold_q <= 1'b0;              // release XRDY
                            st     <= ST_WR_HLD;
                        end
                    end else if (!stall_test || wd_trip) begin
                        if (!wd_trip) begin               // a watchdog release discards the write
                            if (tgt_ac) begin
                                if (lane_hi) begin
                                    case ({addr_q[7:1], 1'b0})
                                        8'h48:   begin base[23:20] <= ld_in[15:12]; pend_cfg <= 1'b1; end
                                        8'h4A:   base[19:16] <= ld_in[15:12];
                                        8'h4C:   pend_shut <= 1'b1;
                                        default: ;
                                    endcase
                                end
                            end else if (reg_space) begin
                                case (ridx)
                                    11'd3: begin                                   // CONTROL
                                        if (lane_lo) begin
                                            zero_wait <= ld_in[0];
                                            irq_en    <= ld_in[1];
                                            int_sel   <= ld_in[2];
                                            led_r     <= ld_in[5:4];
                                        end
                                        if (lane_hi && ld_in[8]) wd_flag <= 1'b0;   // W1C
                                    end
                                    11'd4: begin                                   // SCRATCH0
                                        if (lane_hi) scratch0[15:8] <= ld_in[15:8];
                                        if (lane_lo) scratch0[7:0]  <= ld_in[7:0];
                                    end
                                    11'd5: begin                                   // SCRATCH1
                                        if (lane_hi) scratch1[15:8] <= ld_in[15:8];
                                        if (lane_lo) scratch1[7:0]  <= ld_in[7:0];
                                    end
                                    11'd8:   if (lane_lo && ld_in[0]) irq_pend <= 1'b0;  // IRQ_STATUS W1C
                                    11'd9:   if (lane_lo && ld_in[0]) irq_pend <= 1'b1;  // IRQ_SET
                                    11'd16:  if (lane_lo) bank <= ld_in[3:0];            // BANK
                                    default: ;
                                endcase
                                if (mbx_space) begin                                    // z2_mbx
                                    zr_we    <= 1'b1;
                                    zr_widx  <= ridx[3:0];
                                    zr_be    <= {lane_hi, lane_lo};
                                    zr_wdata <= ld_in;
                                end
                            end
                        end
                        hold_q <= 1'b0;                  // release XRDY
                        st     <= ST_WR_HLD;
                    end
                end

                ST_WR_HLD: begin
                    if (berr_s)
                        st <= ST_ABORT;
                    else if (!ds_s) begin
                        oe_wr_q <= 1'b0;
                        ph_rd   <= 1'b0;
                        st      <= ST_BETWN;
                    end
                end

                ST_ABORT: begin                          // /BERR: release everything, wait for /AS
                    oe_rd_q <= 1'b0; oe_wr_q <= 1'b0; ld_oe <= 1'b0; dir_req <= 1'b0;
                    zq_ce <= 1'b0; zq_oe <= 1'b0; zq_we <= 1'b0; zq_ub <= 1'b0; zq_lb <= 1'b0;
                    hold_q  <= 1'b0;
                    pend_cfg <= 1'b0; pend_shut <= 1'b0;
                end

                default: st <= ST_IDLE;
                endcase
                // a watchdog trip releases XRDY in every state, for the rest of the cycle
                if (wd_trip) hold_q <= 1'b0;
            end
        end

        // power-on reset of the state that survives /BUSRST
        if (por) begin
            wd_flag <= 1'b0; wdog_events <= 16'd0; berr_events <= 16'd0;
            scratch0 <= 16'd0; scratch1 <= 16'd0; ticks <= 16'd0; tick_pre <= 10'd0;
        end
    end

`ifdef FORMAL
    // ---- observation ports (formal/fv_shm.v): the go conditions WITHOUT h_quiet. Property X4
    //      there proves h_quiet is already true whenever one of them holds, so host activity
    //      never delays a Zorro local-bus action.
    assign f_st      = st;
    assign f_res_cnt = res_cnt;
    assign f_nat_go  = ((st == ST_RD_DIR) && !berr_s && ds_s && dir_q && dir_req && dir_settled && !oe_wr_q && res_ok) ||
                       ((st == ST_WR_DIR) && !berr_s && ds_s && !dir_q && !dir_req && dir_settled && oe_quiet && res_ok);
    assign f_oe_wr_q = oe_wr_q;
    assign f_ld_oe   = ld_oe;

    // ==================================================================== formal properties
    // Run with hdl/formal/z2_core.sby (SymbiYosys). Inputs are unconstrained: every
    // property must hold for ANY sequence of Zorro, EN_OK, DIP and reset inputs.
    reg f_past = 1'b0;
    always @(posedge clk) f_past <= 1'b1;

    always @* begin
        // F1  the transceiver drives the Zorro data bus only for a valid read of this card
        if (!zf_dbuf_oe_n && zf_dbuf_dir)
            assert(!zb_as_n && zb_berr_n && sel_c && zb_read && zb_doe && !(zb_uds_n && zb_lds_n) && oe_rd_q);
        // F2  the transceiver drives LD (B->A) only during a write phase of this card
        if (!zf_dbuf_oe_n && !zf_dbuf_dir)
            assert(!zb_as_n && zb_berr_n && sel_c && !zb_read && oe_wr_q);
        // F3  XRDY is held only for a selected cycle, never during /BERR
        if (!zf_xrdy)    assert(!zb_as_n && zb_berr_n && sel_c && hold_q);
        // F4  /SLAVEn only with /AS asserted and the address selected
        if (!zf_slave_n) assert(!zb_as_n && sel_c);
        // F5  local-bus ownership: the FPGA, the SRAM and U103 never drive LD together.
        //     A read drives LD from the FPGA (registers) or the SRAM, never both; U103's A port
        //     is then an input (dir_q = 1).
        assert(oe_rd_q == (ld_oe | zq_oe));
        assert(!(ld_oe && zq_oe));
        assert(!(ld_oe && oe_wr_q));
        assert(!(zq_oe && oe_wr_q));
        if (ld_oe)   assert(dir_q);
        if (zq_oe)   assert(dir_q && zq_ce && !zq_we);
        if (oe_wr_q) assert(!dir_q);
        // F17 an SRAM write strobe only inside a write phase, with /CE, never with /OE
        if (zq_we)   assert(zq_ce && !zq_oe && oe_wr_q && (st == ST_WR_CAP) && (wr_cnt == GUARD + 1));
        if (zq_ce)   assert((st == ST_RD_DRV) || (st == ST_RD_HLD) || (st == ST_WR_CAP) || (st == ST_ABORT));
        // helper invariants for the SRAM paths (k-induction)
        if (st == ST_WR_CAP) assert((zq_ce == tgt_mem) && oe_wr_q && !zq_oe && (wr_cnt <= (tgt_mem ? GUARD + 2 : GUARD)));
        if ((st == ST_RD_DRV) || (st == ST_RD_HLD)) assert(zq_oe == zq_ce);
        if (st == ST_RD_HLD) assert(rd_cnt == 2'd0);
        // F6  /CFGOUTn asserted only with /CFGINn and configured or shut up
        if (!zf_cfgout_n) assert(!zb_cfgin_n && (configured || shutup));
        // F7  idle means everything released
        if (st == ST_IDLE) assert(!oe_rd_q && !oe_wr_q && !ld_oe && !zq_ce && !zq_oe && !zq_we);
        // F18 the reservation covers every state that may act on the local bus
        if ((st != ST_IDLE) && (st != ST_IGNORE)) assert(z_res);
        if (st == ST_IGNORE) assert(!oe_rd_q && !oe_wr_q && !ld_oe && !zq_ce);
        // helper invariants (aid k-induction)
        if (oe_rd_q) assert((st == ST_RD_DRV) || (st == ST_RD_HLD) || (st == ST_ABORT));
        if (oe_wr_q) assert((st == ST_WR_CAP) || (st == ST_WR_HLD) || (st == ST_ABORT));
        if (st == ST_IGNORE) assert(!sel_q);
    end

    // F16 XRDY bound. Synchronous form (inductive): a selected cycle holds XRDY for at most
    // WDOG_LIMIT + 2 clocks of FSM time. The pin-level form (BMC only, it depends on the raw
    // asynchronous inputs) is enabled with FORMAL_BMC_ONLY.
    reg [9:0] f_hold_cnt = 10'd0;
    always @(posedge clk)
        f_hold_cnt <= ((st != ST_IDLE) && as_s && sel_q && hold_q && !zrst) ? f_hold_cnt + 10'd1 : 10'd0;
    always @* begin
        assert(wd_cnt <= WDOG_LIMIT - 1);
        if (!wd_trip) assert(f_hold_cnt <= wd_cnt + 1);
        assert(f_hold_cnt <= WDOG_LIMIT + 2);
    end
`ifdef FORMAL_BMC_ONLY
    reg [9:0] f_xrdy_cnt = 10'd0;
    always @(posedge clk) f_xrdy_cnt <= zf_xrdy ? 10'd0 : (f_xrdy_cnt == 10'h3FF ? f_xrdy_cnt : f_xrdy_cnt + 10'd1);
    always @* assert(f_xrdy_cnt <= WDOG_LIMIT + 8);
`endif

    always @(posedge clk) if (f_past) begin
        // F8  DIR changes only after every enable has been off for GUARD clocks
        if (dir_q != $past(dir_q))
            assert(!$past(oe_rd_q) && !$past(oe_wr_q) && !$past(ld_oe) && ($past(oe_idle_cnt) >= GUARD));
        // F9  an enable is raised only after DIR has been stable for GUARD clocks
        if (oe_rd_q && !$past(oe_rd_q)) assert($past(dir_q) && ($past(dir_cnt) >= GUARD));
        if (oe_wr_q && !$past(oe_wr_q)) assert(!$past(dir_q) && ($past(dir_cnt) >= GUARD) && ($past(oe_idle_cnt) >= GUARD));
        // F19 every local-bus action waits for the reservation floor and for a quiet host side
        if ((oe_rd_q && !$past(oe_rd_q)) || (oe_wr_q && !$past(oe_wr_q)))
            assert($past(res_ok) && $past(h_quiet));
        // F20 SRAM write strobe: exactly one clock, address and lanes unchanged around it
        if ($past(zq_we)) assert(!zq_we);
        if (zq_we) assert((zq_addr == $past(zq_addr)) && (zq_ub == $past(zq_ub)) && (zq_lb == $past(zq_lb)) && $past(zq_ce));
        if ($past(zq_we) && !$past(zrst)) assert((zq_addr == $past(zq_addr)) && (zq_ce || (st == ST_IDLE) || (st == ST_BETWN) || (st == ST_ABORT)));
        // F10 arming only inside a Zorro reset with EN_OK; EN_OK loss disarms next clock
        if (armed && !$past(armed)) assert($past(busrst_q) && $past(en_ok_s) && !$past(dip_disable));
        if (!$past(en_ok_s)) assert(!armed);
        // F11 disarmed -> no select from the next clock
        if (!$past(armed)) assert(!match_en);
        // F12 the decode state is frozen while a bus cycle is in progress
        if (($past(st) != ST_IDLE) && !$past(zrst) && $past(armed))
            assert((match_en == $past(match_en)) && (cmp == $past(cmp)) && (care_lo == $past(care_lo)));
        // F13 /AS negated -> idle on the next clock
        if (!$past(as_s) && !$past(zrst)) assert(st == ST_IDLE);
        // F14 configured only at the end of a configuring write of this card
        if (configured && !$past(configured)) assert(!$past(as_s) && $past(pend_cfg) && $past(sel_q));
        // F15 Zorro reset clears the AutoConfig state
        if ($past(zrst)) assert(!configured && !shutup && !match_en && (st == ST_IDLE));
        // F16 a watchdog trip releases XRDY on the next clock
        if ($past(wd_trip) && !$past(zrst) && $past(as_s) && ($past(st) != ST_IDLE)) assert(!hold_q);
    end

    // reachability (cover) of the interesting behaviours
    always @(posedge clk) if (f_past) begin
        cover(configured);
        cover(($past(st) != ST_IDLE) && (st == ST_IDLE) && $past(ph_two) && $past(sel_q));   // RMW completed
        cover(wd_trip);
        cover(armed && $past(armed) && (st == ST_RD_HLD) && !zf_dbuf_oe_n);
    end
`endif
endmodule
`default_nettype wire
