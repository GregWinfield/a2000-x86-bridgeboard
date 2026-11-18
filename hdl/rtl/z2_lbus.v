// SPDX-License-Identifier: MIT
// Local-bus arbiter and SRAM sequencer (Stage 3, sheet 3).
//
// This block decides WHO MAY ACCESS THE MEMORY at each instant. It knows nothing about queues,
// messages or interrupts; those are z2_mbx, which decides who has work to do.
//
//   * It owns the SRAM pins. Each pin comes straight from one flip-flop, with no logic after it,
//     so the pins cannot glitch. It also owns the FPGA's LD drive for host writes.
//   * Zorro accesses: z2_core's registered requests zq_* appear on the pins one clock later.
//   * Host accesses (the SPI side, through the host port) start only when the Zorro side is not
//     reserving the bus (z_res = 0) and every Zorro local-bus driver has been off for GUARD
//     clocks (z_quiet). A host access is never aborted: a read takes 3 clocks, a write 4.
//   * z2_core never acts on the local bus earlier than START + ZRES. By then any host access
//     that started before the reservation has finished and been quiet for GUARD clocks
//     (h_quiet), so host traffic cannot change Zorro timing (formal property X4).
//
// Specification: docs/hdl/shared-memory-spec.md
`default_nettype none
module z2_lbus #(
    parameter integer GUARD = 2
) (
    input  wire        clk,
    input  wire        por,
    // Zorro side (z2_core)
    input  wire [17:0] zq_addr,
    input  wire        zq_ce, zq_oe, zq_we, zq_ub, zq_lb,
    input  wire        z_res,          // Zorro reservation: no host access may start
    input  wire        z_quiet,        // Zorro local-bus drivers off for >= GUARD clocks
    output wire        zs_drv,         // SRAM outputs enabled for a Zorro read (pin registers)
    output wire        h_quiet,        // host idle and its drivers off for >= GUARD clocks
    output wire        h_busy,         // a host access occupies the SRAM pins
    // host port, SRAM space (clk domain). A request is held until h_ack; the transaction
    // completes at the clock edge where h_ack is 1.
    input  wire        h_req,
    input  wire        h_we,
    input  wire [17:0] h_addr,         // word address (SRAM byte address / 2)
    input  wire [1:0]  h_be,           // {upper, lower} byte enables, writes only
    input  wire [15:0] h_wdata,
    output reg         h_ack,
    output reg  [15:0] h_rdata,
    // local data bus
    input  wire [15:0] ld_in,
    output reg         h_ld_oe,
    output reg  [15:0] h_ld_dout,
    // SRAM pins (sheet 3, U301 IS61WV25616EDBLL)
    output reg  [17:0] sa,
    output reg         sram_ce_n,
    output reg         sram_oe_n,
    output reg         sram_we_n,
    output reg         sram_ub_n,
    output reg         sram_lb_n
`ifdef FORMAL
    ,                                // observation for the shared-memory proof (formal/fv_shm.v)
    output wire [2:0]  f_h_st,
    output wire [2:0]  f_h_idle_cnt,
    output wire        f_own_h,
    output wire        f_h_start
`endif
);
    localparam [2:0] H_IDLE = 3'd0, H_RD1 = 3'd1, H_RD2 = 3'd2, H_WR1 = 3'd3, H_WR2 = 3'd4, H_WR3 = 3'd5;

    reg [2:0] h_st;
    reg       own_h;                   // the pin registers carry a host access
    reg [2:0] h_idle_cnt;              // clocks since the host drivers were last on (saturating)

    initial begin
        h_st = H_IDLE; own_h = 1'b0; h_idle_cnt = 3'd7; h_ack = 1'b0; h_rdata = 16'h0000;
        h_ld_oe = 1'b0; h_ld_dout = 16'h0000; sa = 18'd0;
        sram_ce_n = 1'b1; sram_oe_n = 1'b1; sram_we_n = 1'b1; sram_ub_n = 1'b1; sram_lb_n = 1'b1;
    end

    wire sram_out = ~sram_ce_n & ~sram_oe_n & sram_we_n;      // SRAM drives LD (pin registers)
    wire h_drv    = h_ld_oe | (own_h & sram_out);
    assign zs_drv  = ~own_h & sram_out;
    assign h_busy  = (h_st != H_IDLE);
    assign h_quiet = (h_st == H_IDLE) && (h_idle_cnt >= GUARD);

    // !h_ack: the requester sees the acknowledge one clock late, so the request that was just
    // completed may still be visible in that clock and must not start a second access.
    wire h_start = (h_st == H_IDLE) && h_req && !h_ack && !z_res && z_quiet && h_quiet;

`ifdef FORMAL
    assign f_h_st = h_st; assign f_h_idle_cnt = h_idle_cnt; assign f_own_h = own_h; assign f_h_start = h_start;
`endif

    always @(posedge clk) begin
        h_ack <= 1'b0;
        if (h_drv)                    h_idle_cnt <= 3'd0;
        else if (h_idle_cnt != 3'd7)  h_idle_cnt <= h_idle_cnt + 3'd1;

        if (por) begin
            h_st <= H_IDLE; own_h <= 1'b0; h_ld_oe <= 1'b0;
            sram_ce_n <= 1'b1; sram_oe_n <= 1'b1; sram_we_n <= 1'b1; sram_ub_n <= 1'b1; sram_lb_n <= 1'b1;
        end else begin
            case (h_st)
            H_IDLE:
                if (h_start) begin                      // edge s: address, /CE, lanes (and data)
                    own_h     <= 1'b1;
                    sa        <= h_addr;
                    sram_ce_n <= 1'b0;
                    sram_we_n <= 1'b1;
                    if (h_we) begin
                        sram_oe_n <= 1'b1;               // /OE high throughout a write
                        sram_ub_n <= ~h_be[1];
                        sram_lb_n <= ~h_be[0];
                        h_ld_dout <= h_wdata;
                        h_ld_oe   <= 1'b1;               // FPGA drives LD (U103 is disabled)
                        h_st      <= H_WR1;
                    end else begin
                        sram_oe_n <= 1'b0;               // word read
                        sram_ub_n <= 1'b0;
                        sram_lb_n <= 1'b0;
                        h_st      <= H_RD1;
                    end
                end else begin                           // Zorro side (or idle): follow zq_*
                    own_h     <= 1'b0;
                    sa        <= zq_addr;
                    sram_ce_n <= ~zq_ce;
                    sram_oe_n <= ~zq_oe;
                    sram_we_n <= ~zq_we;
                    sram_ub_n <= ~zq_ub;
                    sram_lb_n <= ~zq_lb;
                end
            H_RD1: h_st <= H_RD2;                        // s+1: access time (tAA 10 ns)
            H_RD2: begin                                 // s+2: capture, release
                h_rdata   <= ld_in;
                sram_oe_n <= 1'b1; sram_ce_n <= 1'b1; sram_ub_n <= 1'b1; sram_lb_n <= 1'b1;
                h_ack     <= 1'b1;
                h_st      <= H_IDLE;
            end
            H_WR1: begin sram_we_n <= 1'b0; h_st <= H_WR2; end   // s+1: /WE low (address set up 1 clock)
            H_WR2: begin sram_we_n <= 1'b1; h_st <= H_WR3; end   // s+2: /WE high (pulse 1 clock)
            H_WR3: begin                                 // s+3: release address, /CE, data
                sram_ce_n <= 1'b1; sram_ub_n <= 1'b1; sram_lb_n <= 1'b1;
                h_ld_oe   <= 1'b0;
                h_ack     <= 1'b1;
                h_st      <= H_IDLE;
            end
            default: h_st <= H_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
