// SPDX-License-Identifier: MIT
// Host-link SPI slave and protocol engine (sheet 4): implements docs/hdl/host-link-protocol.md v1.0
// on the host-port contract H-1..H-6 (docs/hdl/shared-memory-spec.md §3.5). Replaces z2_hostif_stub.
//  * z2_spi_slave (SCK domain) -> z2_afifo (16 x {dropped, sof, byte}) -> engine (clk_core).
//  * The engine pops one FIFO entry per clock in every state, so the FIFO never backs up (§9).
//  * Payload bytes are staged; nothing executes before the whole frame passed V1..V5 (no partial
//    commit, owner requirement 1). One host-port transaction at a time, in order (O-1, H-3).
//  * The response RAM is written only while executing an accepted command; byte 0 (RSYNC) is a
//    register written last, so a partially built response never reads as valid.
//  * ATTN = READY: high only in IDLE with CS_N high (§2, §8). Low after reset until the power-on
//    IDENTIFY response (SEQ 0xFF) exists.
`default_nettype none
module z2_hostif #(
    parameter [7:0] HDL_VER = 8'h03,
    parameter integer LAUNCH_RISE = 0                 // MISO launch edge (z2_spi_slave)
) (
    input  wire        clk,
    input  wire        por,
    // SPI pins (FPGA side of the sheet-4 translators)
    input  wire        rp_sck,
    input  wire        rp_cs_n,
    input  wire        rp_mosi,
    output wire        rp_miso,
    output reg         rp_attn,
    // status for the response STATUS byte
    input  wire        fault_ind,
    input  wire        irq_n,
    // host port (H-1..H-6)
    output reg         h_req,
    output reg         h_we,
    output reg         h_reg,
    output reg  [17:0] h_addr,
    output reg  [1:0]  h_be,
    output reg  [15:0] h_wdata,
    input  wire        h_ack,
    input  wire [15:0] h_rdata
);
    localparam [7:0] SYNC = 8'hA1, RSYNC = 8'h51, MAJOR = 8'd1, MINOR = 8'd0;
    localparam [15:0] MAXLEN = 16'd259;                // largest payload (SRAM_WRITE of 128 words)

    function [15:0] crc_upd;                          // CRC-16/IBM-3740, one byte, MSB first
        input [15:0] c;
        input [7:0]  b;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {b, 8'h00};
            for (i = 0; i < 8; i = i + 1) x = x[15] ? ((x << 1) ^ 16'h1021) : (x << 1);
            crc_upd = x;
        end
    endfunction

    // ---------------- SCK domain, FIFO, response RAM
    wire       f_we, f_full, f_drop, f_empty;
    wire [9:0] f_wdata, f_rdata;
    reg  [7:0] byte0;                                 // response byte 0 (RSYNC when valid)
    wire [8:0] t_addr;
    reg  [7:0] t_data;
    z2_spi_slave #(.RAW(9), .LAUNCH_RISE(LAUNCH_RISE)) u_spi (.sck(rp_sck), .cs_n(rp_cs_n), .mosi(rp_mosi), .miso(rp_miso),
        .fifo_we(f_we), .fifo_wdata(f_wdata), .fifo_full(f_full), .byte0(byte0), .rd_addr(t_addr), .rd_data(t_data));
    z2_afifo #(.W(10), .AW(4)) u_fifo (.wclk(rp_sck), .wrst(por), .we(f_we), .wdata(f_wdata), .wfull(f_full),
        .wdrop(f_drop), .rclk(clk), .rrst(por), .re(~f_empty), .rdata(f_rdata), .rempty(f_empty));

    reg [7:0] rsp [0:511];                            // response RAM: written here, read by SCK falling
    reg       r_we;
    reg [8:0] r_wa;
    reg [7:0] r_wd;
    always @(posedge clk) if (r_we) rsp[r_wa] <= r_wd;
    generate if (LAUNCH_RISE != 0) begin : g_rd_rise
        always @(posedge rp_sck) t_data <= rsp[t_addr];
    end else begin : g_rd_fall
        always @(negedge rp_sck) t_data <= rsp[t_addr];
    end endgenerate

    reg [7:0] stg [0:511];                            // staging RAM (payload of the current frame)
    reg       s_we;
    reg [8:0] s_wa, s_ra;
    reg [7:0] s_wd, s_q;
    always @(posedge clk) begin
        if (s_we) stg[s_wa] <= s_wd;
        s_q <= stg[s_ra];                             // registered read: data two clocks after s_ra is set
    end

    // ---------------- frame detection
    reg cs1, cs2, cs2_d;                              // CS_N synchroniser
    always @(posedge clk or posedge por)
        if (por) begin cs1 <= 1'b1; cs2 <= 1'b1; cs2_d <= 1'b1; end
        else begin cs1 <= rp_cs_n; cs2 <= cs1; cs2_d <= cs2; end
    wire cs_fall = cs2_d & ~cs2;

    localparam [2:0] S_INIT = 3'd0, S_IDLE = 3'd1, S_RX = 3'd2, S_EXEC = 3'd3, S_DRAIN = 3'd4;
    reg [2:0]  st;
    reg        fr_on;                                 // a frame (CS_N low period) is being received
    reg        fr_acc;                                // it started in IDLE (V2)
    reg [2:0]  guard;                                 // clocks with CS_N high and the FIFO empty
    wire       fr_end = fr_on & cs2 & f_empty & (guard == 3'd4);

    // ---------------- parser (one FIFO entry per clock)
    reg [8:0]  pb;                                    // bytes received in this frame (saturating)
    reg [8:0]  p_end5, p_end7;                        // 5 + LEN, 7 + LEN (511 while unknown or invalid)
    reg [15:0] pcrc;
    reg        p_drop, p_sof_err, p_sync_ok, p_len_bad;
    reg [7:0]  p_cmd, p_seq, p_lenh;
    reg [8:0]  p_len;
    reg [8:0]  s_wp;                                  // staging write pointer
    wire       pop = ~f_empty;
    wire [7:0] pbyte = f_rdata[7:0];
    wire [15:0] len16 = {p_lenh, pbyte};              // valid at pb == 4
    wire       in_crc = (pb < 9'd5) | (pb < p_end7);

    // ---------------- counters
    reg [15:0] n_crc, n_frame, n_busy;
    wire       err_any = (n_crc != 16'd0) | (n_frame != 16'd0) | (n_busy != 16'd0);

    // ---------------- executor state
    reg [7:0]  x_cmd, x_seq, x_rcode;
    reg [8:0]  x_len;                                 // command payload length (<= 259)
    reg [8:0]  x_rlen;                                // response payload length
    reg [7:0]  a0, a1, a2, a3, a4, a5;                // staged bytes 0..5
    reg [3:0]  xs;                                    // micro-step
    reg [8:0]  xi;                                    // byte or word counter
    reg [8:0]  xn;                                    // words to transfer
    reg [17:0] xa;                                    // current word address
    reg [7:0]  xhold;
    reg [8:0]  r_ptr;                                 // next response byte address
    reg        r_inc;                                 // the byte being written is covered by the CRC
    reg [15:0] rcrc;                                  // one CRC instance, updated from the written byte
    localparam [3:0] X_LD = 4'd0, X_LDW = 4'd1, X_DEC = 4'd2, X_HDR = 4'd3, X_BODY = 4'd4, X_B2 = 4'd5,
                     X_B3 = 4'd6, X_BUS = 4'd7, X_RDW = 4'd8, X_DONE = 4'd9, X_CRCW = 4'd10, X_CRC = 4'd11;

    function [7:0] hdr_byte;                          // response header bytes 1..5
        input [2:0] k;
        input [7:0] status, seq, rcode;
        input [8:0] rlen;
        case (k)
            3'd1: hdr_byte = status;
            3'd2: hdr_byte = seq;
            3'd3: hdr_byte = rcode;
            3'd4: hdr_byte = {7'd0, rlen[8]};
            default: hdr_byte = rlen[7:0];
        endcase
    endfunction
    function [7:0] info_byte;                         // IDENTIFY (sel 0) / STATUS (sel 1) payload
        input       sel;
        input [2:0] k;
        input [7:0] status;
        input [15:0] c0, c1, c2;
        if (!sel) case (k)
            3'd0: info_byte = 8'h5A; 3'd1: info_byte = 8'h32; 3'd2: info_byte = MAJOR; 3'd3: info_byte = MINOR;
            3'd4: info_byte = HDL_VER; 3'd5: info_byte = 8'd128; 3'd6: info_byte = 8'd16;
            default: info_byte = {5'd0, (LAUNCH_RISE != 0), 2'b11};   // FEATURES: b0 CRC, b1 split reads, b2 early launch
        endcase else case (k)
            3'd0: info_byte = status; 3'd1: info_byte = c0[15:8]; 3'd2: info_byte = c0[7:0]; 3'd3: info_byte = c1[15:8];
            3'd4: info_byte = c1[7:0]; 3'd5: info_byte = c2[15:8]; 3'd6: info_byte = c2[7:0]; default: info_byte = 8'h00;
        endcase
    endfunction
    wire [7:0]  status_byte = {5'd0, err_any, ~irq_n, fault_ind};
    // V6 argument check: one shared adder for "ADDR + N <= 2^18"
    wire [8:0]  dec_n = (x_cmd == 8'h10) ? ((x_len - 9'd3) >> 1) : {1'b0, a3};
    wire [18:0] dec_end = {1'b0, a0[1:0], a1, a2} + {10'd0, dec_n};
    wire        dec_bad_addr = (a0[7:2] != 6'd0) | (dec_end > 19'h40000);

    task rsp_put;                                     // write the next response byte (covered by the CRC)
        input [7:0] d;
        begin r_we <= 1'b1; r_wa <= r_ptr; r_wd <= d; r_ptr <= r_ptr + 9'd1; r_inc <= 1'b1; end
    endtask

    always @(posedge clk or posedge por)
        if (por) begin
            st <= S_INIT; fr_on <= 1'b0; fr_acc <= 1'b0; guard <= 3'd0; rp_attn <= 1'b0; byte0 <= 8'h00;
            pb <= 9'd0; p_end5 <= 9'h1FF; p_end7 <= 9'h1FF; pcrc <= 16'hFFFF;
            p_drop <= 1'b0; p_sof_err <= 1'b0; p_sync_ok <= 1'b0; p_len_bad <= 1'b0;
            p_cmd <= 8'h00; p_seq <= 8'h00; p_lenh <= 8'h00; p_len <= 9'd0; s_wp <= 9'd0;
            n_crc <= 16'd0; n_frame <= 16'd0; n_busy <= 16'd0;
            h_req <= 1'b0; h_we <= 1'b0; h_reg <= 1'b0; h_addr <= 18'd0; h_be <= 2'b00; h_wdata <= 16'h0000;
            x_cmd <= 8'h01; x_seq <= 8'hFF; x_rcode <= 8'h00; x_len <= 9'd0; x_rlen <= 9'd0;
            a0 <= 8'h00; a1 <= 8'h00; a2 <= 8'h00; a3 <= 8'h00; a4 <= 8'h00; a5 <= 8'h00;
            xs <= X_DEC; xi <= 9'd0; xn <= 9'd0; xa <= 18'd0; xhold <= 8'h00;
            r_ptr <= 9'd1; r_inc <= 1'b0; rcrc <= 16'hFFFF;
            r_we <= 1'b0; r_wa <= 9'd0; r_wd <= 8'h00; s_we <= 1'b0; s_wa <= 9'd0; s_wd <= 8'h00; s_ra <= 9'd0;
        end else begin
            r_we <= 1'b0; r_inc <= 1'b0; s_we <= 1'b0;
            if (r_we & r_inc) rcrc <= crc_upd(rcrc, r_wd);             // the one response-CRC instance
            rp_attn <= (st == S_IDLE) & ~fr_on & cs2;

            // ---- frame start / end
            if (cs_fall & ~fr_on) begin
                fr_on <= 1'b1; fr_acc <= (st == S_IDLE); guard <= 3'd0;
                pb <= 9'd0; p_end5 <= 9'h1FF; p_end7 <= 9'h1FF; pcrc <= 16'hFFFF; s_wp <= 9'd0;
                p_drop <= 1'b0; p_sof_err <= 1'b0; p_sync_ok <= 1'b0; p_len_bad <= 1'b0;
                if (st == S_IDLE) st <= S_RX;
            end else if (fr_on) begin
                guard <= (cs2 & f_empty) ? ((guard == 3'd4) ? guard : guard + 3'd1) : 3'd0;
            end

            // ---- parser
            if (pop) begin
                if (!fr_on) n_frame <= (n_frame == 16'hFFFF) ? n_frame : n_frame + 16'd1;   // stray byte
                else begin
                    if (pb != 9'h1FF) pb <= pb + 9'd1;
                    if (f_rdata[9]) p_drop <= 1'b1;
                    if (f_rdata[8] != (pb == 9'd0)) p_sof_err <= 1'b1;
                    if (in_crc) pcrc <= crc_upd(pcrc, pbyte);
                    case (pb)
                        9'd0: p_sync_ok <= (pbyte == SYNC);
                        9'd1: p_cmd <= pbyte;
                        9'd2: p_seq <= pbyte;
                        9'd3: p_lenh <= pbyte;
                        9'd4: begin
                            p_len <= len16[8:0];
                            if (len16 > MAXLEN) p_len_bad <= 1'b1;
                            else begin p_end5 <= len16[8:0] + 9'd5; p_end7 <= len16[8:0] + 9'd7; end
                        end
                        default: ;
                    endcase
                    if (fr_acc && !p_len_bad && pb >= 9'd5 && pb < p_end5) begin
                        s_we <= 1'b1; s_wa <= s_wp; s_wd <= pbyte; s_wp <= s_wp + 9'd1;
                    end
                end
            end

            // ---- frame end: validate (V1..V5) an accepted frame, count a rejected one
            if (fr_end) begin
                fr_on <= 1'b0;
                if (!fr_acc) n_busy <= (n_busy == 16'hFFFF) ? n_busy : n_busy + 16'd1;
                else if (p_drop | ~p_sync_ok | p_sof_err | p_len_bad | (pb < p_end7)) begin
                    n_frame <= (n_frame == 16'hFFFF) ? n_frame : n_frame + 16'd1; st <= S_IDLE;
                end else if (pcrc != 16'h0000) begin
                    n_crc <= (n_crc == 16'hFFFF) ? n_crc : n_crc + 16'd1; st <= S_IDLE;
                end else if (p_cmd == 8'h03) begin                      // GET_RESPONSE: buffer unchanged (R2)
                    st <= S_IDLE;
                end else begin
                    st <= S_EXEC; xs <= X_LD; x_cmd <= p_cmd; x_seq <= p_seq; x_len <= p_len;
                end
            end

            // ---- executor
            if (st == S_EXEC || st == S_INIT) begin
                case (xs)
                    X_LD: begin byte0 <= 8'h00; s_ra <= 9'd0; xi <= 9'd0; xs <= X_LDW; end   // invalidate first
                    X_LDW: begin                                       // staged bytes 0..5 into a0..a5
                        s_ra <= s_ra + 9'd1;
                        case (xi)
                            9'd1: a0 <= s_q; 9'd2: a1 <= s_q; 9'd3: a2 <= s_q; 9'd4: a3 <= s_q; 9'd5: a4 <= s_q; 9'd6: a5 <= s_q;
                            default: ;
                        endcase
                        if (xi == 9'd6) xs <= X_DEC;
                        xi <= xi + 9'd1;
                    end
                    X_DEC: begin                                       // V6: command, length, arguments
                        x_rcode <= 8'h00; x_rlen <= 9'd0; xn <= 9'd0; xa <= {a0[1:0], a1, a2};
                        case (x_cmd)
                            8'h01, 8'h02: if (x_len != 9'd0) x_rcode <= 8'h02; else x_rlen <= 9'd8;
                            8'h04: if (x_len != 9'd0) x_rcode <= 8'h02;
                            8'h05: if (x_len > 9'd256) x_rcode <= 8'h02; else x_rlen <= x_len;
                            8'h10: if (x_len < 9'd5 || !x_len[0]) x_rcode <= 8'h02;
                                   else if (dec_bad_addr) x_rcode <= 8'h03;
                                   else xn <= dec_n;
                            8'h11: if (x_len != 9'd4) x_rcode <= 8'h02;
                                   else if (a3 == 8'd0 || a3 > 8'd128 || dec_bad_addr) x_rcode <= 8'h03;
                                   else begin xn <= {1'b0, a3}; x_rlen <= {a3, 1'b0}; end
                            8'h12: if (x_len != 9'd6) x_rcode <= 8'h02;
                                   else if (a0[7:2] != 6'd0 || a3[7:2] != 6'd0 || a3[1:0] == 2'b00) x_rcode <= 8'h03;
                                   else xn <= 9'd1;
                            8'h20: if (x_len != 9'd4) x_rcode <= 8'h02;
                                   else if (a0 > 8'd15 || a1[7:2] != 6'd0 || a1[1:0] == 2'b00) x_rcode <= 8'h03;
                                   else xn <= 9'd1;
                            8'h21: if (x_len != 9'd1) x_rcode <= 8'h02;
                                   else if (a0 > 8'd15) x_rcode <= 8'h03;
                                   else begin xn <= 9'd1; x_rlen <= 9'd2; end
                            default: x_rcode <= 8'h01;
                        endcase
                        rcrc <= crc_upd(16'hFFFF, RSYNC); r_ptr <= 9'd1; xi <= 9'd1; xs <= X_HDR;
                    end
                    X_HDR: begin                                       // header bytes 1..5
                        rsp_put(hdr_byte(xi[2:0], status_byte, x_seq, x_rcode, (x_rcode == 8'h00) ? x_rlen : 9'd0));
                        if (xi == 9'd5) begin
                            xi <= 9'd0;
                            s_ra <= (x_cmd == 8'h10) ? 9'd3 : 9'd0;    // SRAM_WRITE data start / ECHO start
                            if (x_rcode != 8'h00) xs <= X_CRCW;
                            else if (x_cmd == 8'h04) begin n_crc <= 16'd0; n_frame <= 16'd0; n_busy <= 16'd0; xs <= X_CRCW; end
                            else xs <= X_BODY;
                        end else xi <= xi + 9'd1;
                    end
                    X_BODY: case (x_cmd)
                        8'h01, 8'h02: begin                            // IDENTIFY / STATUS payload
                            rsp_put(info_byte(x_cmd == 8'h02, xi[2:0], status_byte, n_crc, n_frame, n_busy));
                            if (xi == 9'd7) xs <= X_CRCW; else xi <= xi + 9'd1;
                        end
                        8'h05: if (xi == x_len) xs <= X_CRCW; else xs <= X_B2;    // ECHO
                        default: if (xi == xn) xs <= X_CRCW;
                                 else xs <= (x_cmd == 8'h10) ? X_B2 : X_BUS;
                    endcase
                    X_B2: xs <= X_B3;                                  // staging RAM read latency
                    X_B3: begin
                        s_ra <= s_ra + 9'd1;
                        if (x_cmd == 8'h05) begin rsp_put(s_q); xi <= xi + 9'd1; xs <= X_BODY; end
                        else begin xhold <= s_q; xs <= X_RDW; end
                    end
                    X_RDW: xs <= X_BUS;                                // lower byte read latency
                    X_BUS: begin                                       // one transaction (H-1): hold until h_ack
                        if (!h_req) begin
                            h_req <= 1'b1;
                            case (x_cmd)
                                8'h10: begin h_we <= 1'b1; h_reg <= 1'b0; h_addr <= xa; h_be <= 2'b11; h_wdata <= {xhold, s_q}; s_ra <= s_ra + 9'd1; end
                                8'h11: begin h_we <= 1'b0; h_reg <= 1'b0; h_addr <= xa; h_be <= 2'b11; end
                                8'h12: begin h_we <= 1'b1; h_reg <= 1'b0; h_addr <= xa; h_be <= a3[1:0]; h_wdata <= {a4, a5}; end
                                8'h20: begin h_we <= 1'b1; h_reg <= 1'b1; h_addr <= {14'd0, a0[3:0]}; h_be <= a1[1:0]; h_wdata <= {a2, a3}; end
                                default: begin h_we <= 1'b0; h_reg <= 1'b1; h_addr <= {14'd0, a0[3:0]}; h_be <= 2'b11; end
                            endcase
                        end else if (h_ack) begin
                            h_req <= 1'b0;
                            if (x_cmd == 8'h11 || x_cmd == 8'h21) begin rsp_put(h_rdata[15:8]); xhold <= h_rdata[7:0]; xs <= X_DONE; end
                            else begin xa <= xa + 18'd1; xi <= xi + 9'd1; xs <= X_BODY; end
                        end
                    end
                    X_DONE: begin rsp_put(xhold); xa <= xa + 18'd1; xi <= xi + 9'd1; xs <= X_BODY; end
                    X_CRCW: xs <= X_CRC;                               // the last covered byte reaches rcrc
                    X_CRC: begin                                       // CRC (not covered), then RSYNC last
                        if (xi != 9'h1F0 && xi != 9'h1F1) begin r_we <= 1'b1; r_wa <= r_ptr; r_wd <= rcrc[15:8]; r_ptr <= r_ptr + 9'd1; xi <= 9'h1F0; end
                        else if (xi == 9'h1F0) begin r_we <= 1'b1; r_wa <= r_ptr; r_wd <= rcrc[7:0]; xi <= 9'h1F1; end
                        else begin byte0 <= RSYNC; st <= fr_on ? S_DRAIN : S_IDLE; end
                    end
                    default: xs <= X_LD;
                endcase
            end
            if (st == S_DRAIN && !fr_on) st <= S_IDLE;                  // a busy frame was discarded
        end
endmodule
`default_nettype wire
