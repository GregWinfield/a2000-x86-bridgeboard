// SPDX-License-Identifier: MIT
// Shared-memory work signalling (Stage 3, sheet 3): queues and interrupts.
//
// This block decides WHO HAS WORK TO DO. It never touches the SRAM; who may access the memory is
// decided by z2_lbus. Messages live in SRAM rings defined by software; this block holds only the
// ring indices, their ownership rules and the interrupts derived from them.
//
//   Q0 = Amiga -> PC (A2P): the Zorro side writes Q0_PROD, the host side writes Q0_CONS.
//   Q1 = PC -> Amiga (P2A): the host side writes Q1_PROD, the Zorro side writes Q1_CONS.
//
//   * Each register has ONE writer side. A write from the other side is ignored and flagged
//     (ERR_OWNER). Both sides may read every register, and reads have no side effects (R-17).
//   * An index write is {EPOCH[7:0], INDEX[7:0]}, as one full 16-bit word. It is accepted only if
//     EPOCH equals the current epoch and the index advances by no more than the free space
//     (producer) or the queued entries (consumer). Otherwise it is ignored and flagged
//     (ERR_EPOCH / ERR_RANGE). So 0 <= PROD - CONS <= QDEPTH always holds (formal M1), and a
//     write prepared before a link reset can never be accepted after it.
//   * Slot ownership: slots with index in [CONS, PROD) belong to the consumer, the others to the
//     producer. Ownership moves only through an accepted index write.
//   * Interrupts are LEVELS derived from state, so a notification cannot be lost. "Work for the
//     Amiga" = Q1 not empty; "work for the PC" = Q0 not empty; "space" = the producer's queue not
//     full; plus sticky events and errors. Draining a queue removes its request; there is nothing
//     to acknowledge.
//   * Link reset (flush both queues, EPOCH + 1, LINK_RESET event to both sides) on: a QCTL write
//     of $A55A by either side, or the start of a Zorro reset (/BUSRST). SRAM is not touched (G7).
//
// Specification: docs/hdl/shared-memory-spec.md
`default_nettype none
module z2_mbx #(
    parameter integer QD_LOG2 = 5                    // queue depth 2^QD_LOG2 slots (1..7)
) (
    input  wire        clk,
    input  wire        por,
    input  wire        zrst,          // Zorro-domain reset (por or filtered /BUSRST)
    input  wire        busrst,        // filtered /BUSRST (the rising edge starts a link reset)
    input  wire        armed,
    input  wire        configured,
    input  wire        mode_b,
    input  wire        en_ok,
    // Zorro side (z2_core): one-clock write strobe; combinational read port
    input  wire        zr_we,
    input  wire [3:0]  zr_widx,
    input  wire [1:0]  zr_be,          // {UDS, LDS} lanes written
    input  wire [15:0] zr_wdata,
    input  wire        zr_magic,       // registered with zr_we: QCTL, full word, $A55A (z2_core; timing)
    input  wire [3:0]  zr_ridx,
    output wire [15:0] zr_rdata,
    output wire        z_irq,          // Zorro-side request (z2_core gates it with CONTROL.IRQ_EN)
    // host side (host port, register space); request held until hr_ack
    input  wire        hr_req,
    input  wire        hr_we,
    input  wire [3:0]  hr_idx,
    input  wire [1:0]  hr_be,
    input  wire [15:0] hr_wdata,
    input  wire        hr_magic,       // registered with hr_req: QCTL, full word, $A55A (z2_hostif; timing)
    output reg         hr_ack,
    output reg  [15:0] hr_rdata,
    output reg         h_irq_n         // RP_IRQ_N: host-side request, active low (registered)
);
    localparam [7:0] QDEPTH = 8'd1 << QD_LOG2;
    localparam [3:0] R_Q0P = 4'd0, R_Q0C = 4'd1, R_Q1P = 4'd2, R_Q1C = 4'd3, R_QSTAT = 4'd4, R_EPOCH = 4'd5,
                     R_ZIEN = 4'd6, R_ZEV = 4'd7, R_HIEN = 4'd8, R_HEV = 4'd9, R_QCTL = 4'd10,
                     R_ZPEND = 4'd11, R_HPEND = 4'd12, R_ASTAT = 4'd13;
    localparam [15:0] QCTL_MAGIC = 16'hA55A;
    // event bits (Z_EVENTS / H_EVENTS)
    localparam integer EV_LINK = 0, EV_ARST = 1, EV_ACFG = 2, EV_EPOCH = 8, EV_RANGE = 9, EV_OWNER = 10;

    reg [7:0]  epoch;
    reg [7:0]  q0p, q0c, q1p, q1c;
    reg [3:0]  z_ien, h_ien;
    reg [15:0] z_ev, h_ev;
    reg        busrst_d, cfg_d;

    initial begin
        epoch = 8'd0; q0p = 8'd0; q0c = 8'd0; q1p = 8'd0; q1c = 8'd0;
        z_ien = 4'd0; h_ien = 4'd0; z_ev = 16'd0; h_ev = 16'd0; busrst_d = 1'b0; cfg_d = 1'b0;
        hr_ack = 1'b0; hr_rdata = 16'h0000; h_irq_n = 1'b1;
    end

    // ------------------------------------------------------------------ queue state
    wire [7:0] q0n = q0p - q0c;                     // entries queued (0..QDEPTH, formal M1)
    wire [7:0] q1n = q1p - q1c;
    // Flags as equality compares, without the subtraction (sheet 4 timing, R-43). Under M1
    // (0 <= p - c <= QDEPTH = 2^QD_LOG2): p - c = 0 exactly when p = c, and p - c = QDEPTH exactly
    // when p != c and the low QD_LOG2 bits agree. Formal M6 checks both against the q0n/q1n forms.
    wire q0_ne = (q0p != q0c), q0_full = q0_ne & (q0p[QD_LOG2-1:0] == q0c[QD_LOG2-1:0]);
    wire q1_ne = (q1p != q1c), q1_full = q1_ne & (q1p[QD_LOG2-1:0] == q1c[QD_LOG2-1:0]);

    function prod_ok;                               // producer may move p to nv: nv - p <= QDEPTH - (p - c)
        input [7:0] nv, p, c;
        reg   [7:0] d, q;
        begin
            // Two parallel subtractions and a compare, not two in series (sheet 4 timing, R-43).
            // With d = nv - c and q = p - c (mod 256): if q <= QDEPTH (formal M1), "nv - p <= QDEPTH - q"
            // is exactly "q <= d <= QDEPTH" (d >= q: nv is not behind p, no wrap). If q > QDEPTH (never
            // reachable) this form rejects, where the series form could accept.
            d = nv - c;
            q = p - c;
            prod_ok = (d >= q) && (d <= QDEPTH);
        end
    endfunction
    function cons_ok;                               // consumer may move c to nv
        input [7:0] nv, p, c;
        reg   [7:0] adv, avail;
        begin
            adv = nv - c;
            avail = p - c;
            cons_ok = (adv <= avail);
        end
    endfunction

    // ------------------------------------------------------------------ interrupts (levels)
    wire [3:0] z_src = {|z_ev[15:8], |z_ev[7:0], ~q0_full, q1_ne};   // err, event, Q0 space, Q1 work
    wire [3:0] h_src = {|h_ev[15:8], |h_ev[7:0], ~q1_full, q0_ne};   // err, event, Q1 space, Q0 work
    wire [3:0] z_pend = z_src & z_ien;
    wire [3:0] h_pend = h_src & h_ien;
    assign z_irq = |z_pend;

    // ------------------------------------------------------------------ read ports (shared map)
    // Written as always @* multiplexers, not a function: a continuous assignment of a function
    // call is re-evaluated only when its arguments change, so a simulator may return a stale
    // value when only the registers read inside the function change.
    reg [15:0] zr_mux, hr_mux;
`define Z2_MBX_RD(IDX, OUT)         case (IDX)             R_Q0P:   OUT = {epoch, q0p};             R_Q0C:   OUT = {epoch, q0c};             R_Q1P:   OUT = {epoch, q1p};             R_Q1C:   OUT = {epoch, q1c};             R_QSTAT: OUT = {4'd0, QD_LOG2[3:0], 4'd0, q1_full, q1_ne, q0_full, q0_ne};             R_EPOCH: OUT = {8'd0, epoch};             R_ZIEN:  OUT = {12'd0, z_ien};             R_ZEV:   OUT = z_ev;             R_HIEN:  OUT = {12'd0, h_ien};             R_HEV:   OUT = h_ev;             R_ZPEND: OUT = {|z_pend, 11'd0, z_pend};             R_HPEND: OUT = {|h_pend, 11'd0, h_pend};             R_ASTAT: OUT = {11'd0, mode_b, en_ok, busrst, configured, armed};             default: OUT = 16'h0000;         endcase
    always @* begin `Z2_MBX_RD(zr_ridx, zr_mux) end      // QCTL is write-only and reads 0
    always @* begin `Z2_MBX_RD(hr_idx, hr_mux) end
`undef Z2_MBX_RD
    assign zr_rdata = zr_mux;

    // ------------------------------------------------------------------ writes
    wire hw      = hr_req & hr_we & ~hr_ack;            // one host register write per request
    wire z_full  = (zr_be == 2'b11);
    wire h_full  = (hr_be == 2'b11);
    // The QCTL magic compare is made at the source, registered with the strobe (zr_magic, hr_magic), so
    // the link-reset decision is one gate deep (sheet 4 timing, R-43). Formal M7 checks it equals
    // (index == QCTL) & full word & (data == $A55A) on every write.
    wire z_qrst  = zr_we & zr_magic;
    wire h_qrst  = hw    & hr_magic;
    wire brst_up = busrst & ~busrst_d;
    wire flush   = z_qrst | h_qrst | brst_up;

    always @(posedge clk) begin
        busrst_d <= busrst;
        cfg_d    <= configured;
        hr_ack   <= 1'b0;
        if (hr_req && !hr_ack) begin                     // host register access: one clock
            hr_ack <= 1'b1;
            if (!hr_we) hr_rdata <= hr_mux;
        end

        if (flush) begin
            // Link reset wins over any index write in the same clock. Such a write was made
            // under the old epoch, and the LINK_RESET event tells its writer.
            q0p <= 8'd0; q0c <= 8'd0; q1p <= 8'd0; q1c <= 8'd0;
            epoch <= epoch + 8'd1;
            h_ev[EV_LINK] <= 1'b1;
            z_ev[EV_LINK] <= 1'b1;
            if (brst_up) h_ev[EV_ARST] <= 1'b1;
        end else begin
            // ---- Zorro (Amiga) side
            if (zr_we) begin
                case (zr_widx)
                    R_Q0P:
                        if (!z_full)                                   z_ev[EV_RANGE] <= 1'b1;  // one full word
                        else if (zr_wdata[15:8] != epoch)                  z_ev[EV_EPOCH] <= 1'b1;
                        else if (!prod_ok(zr_wdata[7:0], q0p, q0c))      z_ev[EV_RANGE] <= 1'b1;
                        else                                           q0p <= zr_wdata[7:0];
                    R_Q1C:
                        if (!z_full)                                   z_ev[EV_RANGE] <= 1'b1;  // one full word
                        else if (zr_wdata[15:8] != epoch)                  z_ev[EV_EPOCH] <= 1'b1;
                        else if (!cons_ok(zr_wdata[7:0], q1p, q1c))      z_ev[EV_RANGE] <= 1'b1;
                        else                                           q1c <= zr_wdata[7:0];
                    R_ZIEN:  if (zr_be[0]) z_ien <= zr_wdata[3:0];
                    R_ZEV: begin                                             // write 1 to clear
                        if (zr_be[1]) z_ev[15:8] <= z_ev[15:8] & ~zr_wdata[15:8];
                        if (zr_be[0]) z_ev[7:0]  <= z_ev[7:0]  & ~zr_wdata[7:0];
                    end
                    R_QCTL:  ;                                               // non-magic: ignored
                    default: z_ev[EV_OWNER] <= 1'b1;                         // host-owned or read-only
                endcase
            end
            // ---- host (PC) side
            if (hw) begin
                case (hr_idx)
                    R_Q0C:
                        if (!h_full)                                   h_ev[EV_RANGE] <= 1'b1;  // one full word
                        else if (hr_wdata[15:8] != epoch)                  h_ev[EV_EPOCH] <= 1'b1;
                        else if (!cons_ok(hr_wdata[7:0], q0p, q0c))      h_ev[EV_RANGE] <= 1'b1;
                        else                                           q0c <= hr_wdata[7:0];
                    R_Q1P:
                        if (!h_full)                                   h_ev[EV_RANGE] <= 1'b1;  // one full word
                        else if (hr_wdata[15:8] != epoch)                  h_ev[EV_EPOCH] <= 1'b1;
                        else if (!prod_ok(hr_wdata[7:0], q1p, q1c))      h_ev[EV_RANGE] <= 1'b1;
                        else                                           q1p <= hr_wdata[7:0];
                    R_HIEN:  if (hr_be[0]) h_ien <= hr_wdata[3:0];
                    R_HEV: begin
                        if (hr_be[1]) h_ev[15:8] <= h_ev[15:8] & ~hr_wdata[15:8];
                        if (hr_be[0]) h_ev[7:0]  <= h_ev[7:0]  & ~hr_wdata[7:0];
                    end
                    R_QCTL:  ;
                    default: h_ev[EV_OWNER] <= 1'b1;
                endcase
            end
        end
        if (configured && !cfg_d) h_ev[EV_ACFG] <= 1'b1;    // the Amiga has configured the card

        h_irq_n <= ~(|h_pend);

        // The Zorro-side enables and events belong to the Amiga's software. A Zorro reset clears
        // them, so no interrupt can fire before a new driver has enabled it.
        if (zrst) begin
            z_ien <= 4'd0;
            z_ev  <= 16'd0;
        end
        if (por) begin
            epoch <= 8'd0; q0p <= 8'd0; q0c <= 8'd0; q1p <= 8'd0; q1c <= 8'd0;
            h_ien <= 4'd0; h_ev <= 16'd0; h_irq_n <= 1'b1; hr_ack <= 1'b0;
        end
    end

`ifdef FORMAL
    // M1: 0 <= PROD - CONS <= QDEPTH for both queues, for any input sequence
    always @* begin
        assert(q0n <= QDEPTH);
        assert(q1n <= QDEPTH);
    end
    reg f_past = 1'b0;
    always @(posedge clk) f_past <= 1'b1;
    always @(posedge clk) if (f_past && !$past(por)) begin
        // M2: each index changes only by its owner's accepted write, or by a link reset to 0
        if (q0p != $past(q0p)) assert(($past(zr_we) && $past(zr_widx) == R_Q0P) || q0p == 8'd0);
        if (q1c != $past(q1c)) assert(($past(zr_we) && $past(zr_widx) == R_Q1C) || q1c == 8'd0);
        if (q0c != $past(q0c)) assert(($past(hr_req) && $past(hr_we) && $past(hr_idx) == R_Q0C) || q0c == 8'd0);
        if (q1p != $past(q1p)) assert(($past(hr_req) && $past(hr_we) && $past(hr_idx) == R_Q1P) || q1p == 8'd0);
        // M3: a link reset empties both queues and advances the epoch
        if ($past(flush)) assert(q0p == 0 && q0c == 0 && q1p == 0 && q1c == 0 && epoch == $past(epoch) + 8'd1);
        // M4: an accepted index write carried the current epoch
        if (!$past(flush) && q0p != $past(q0p)) assert($past(zr_wdata[15:8]) == $past(epoch));
        if (!$past(flush) && q1p != $past(q1p)) assert($past(hr_wdata[15:8]) == $past(epoch));
        // M5: the host interrupt line follows the enabled sources (one clock)
        assert(h_irq_n == ~(|$past(h_pend)) || $past(por));
    end
    always @* begin
        // M6: the equality-compare flags equal the occupancy definitions
        assert(q0_ne == (q0n != 8'd0) && q0_full == (q0n == QDEPTH));
        assert(q1_ne == (q1n != 8'd0) && q1_full == (q1n == QDEPTH));
        // M7: the precomputed QCTL flags equal the full decode on every write
        if (zr_we) assert(zr_magic == ((zr_widx == R_QCTL) & z_full & (zr_wdata == QCTL_MAGIC)));
        if (hw)    assert(hr_magic == ((hr_idx  == R_QCTL) & h_full & (hr_wdata == QCTL_MAGIC)));
    end
`endif
endmodule
`default_nettype wire
