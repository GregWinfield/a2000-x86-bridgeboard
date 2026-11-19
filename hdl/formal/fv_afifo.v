// SPDX-License-Identifier: MIT
// Formal harness for z2_afifo (sheet 4, owner requirement 5). Multiclock: wclk and rclk are free
// inputs the solver toggles independently at every global step, so every clock ratio and every clock
// stoppage is covered; we, re and wdata are completely free. rst (asynchronous, common to both sides,
// as por is in z2_hostif) may be asserted at any time.
//   A1  Gray pointers: each equals bin2gray(binary); between global steps each changes in at most
//       one bit (what makes the two-flop synchronisers safe)
//   A2  no overflow, no underflow: 0 <= written - read <= DEPTH (reference counters clocked like the FIFO)
//   A3  flags are conservative: not-empty implies data, not-full implies space
//   A4  data integrity and order: the N-th accepted write is the N-th value read (N free, anyconst)
//   A5  a write is refused (wdrop) exactly when it arrives while full; a refused write stores nothing
//       (wbin follows the count of accepted writes, A2)
//   C1-C3 cover: fill to full, a refused write at full, drain to empty after more than DEPTH writes
`default_nettype none
module fv_afifo (
    input wire       wclk, rclk, rst, we, re,
    input wire [3:0] wdata
);
    localparam integer AW = 4, DEPTH = 16;
    wire        wfull, wdrop, rempty;
    wire [3:0]  rdata;
    wire [AW:0] wbin, rbin, wgray, rgray, rq2, wq2, rq1, wq1;
    wire [3:0]  fmem;                                  // FIFO memory at the tracked slot
    z2_afifo #(.W(4), .AW(AW)) dut (.wclk(wclk), .wrst(rst), .we(we), .wdata(wdata), .wfull(wfull), .wdrop(wdrop),
        .rclk(rclk), .rrst(rst), .re(re), .rdata(rdata), .rempty(rempty),
        .f_wbin(wbin), .f_rbin(rbin), .f_wgray(wgray), .f_rgray(rgray), .f_rq2(rq2), .f_wq2(wq2), .f_rq1(rq1), .f_wq1(wq1),
        .f_idx(tn[AW-1:0]), .f_mem(fmem));

    function [AW:0] g2b; input [AW:0] g; integer i; begin g2b[AW] = g[AW]; for (i = AW - 1; i >= 0; i = i - 1) g2b[i] = g2b[i + 1] ^ g[i]; end endfunction

    reg init = 1'b1;
    always @($global_clock) init <= 1'b0;
    always @(*) if (init) assume (rst);

    // reference model, clocked exactly like the FIFO's two sides
    reg [7:0] nw, nr;
    (* anyconst *) reg [7:0] tn;                       // the tracked write (index from reset)
    reg [3:0] td;
    reg       tw;                                      // tracked write done
    always @(posedge wclk or posedge rst)
        if (rst) begin nw <= 8'd0; tw <= 1'b0; td <= 4'd0; end
        else if (we && !wfull) begin
            nw <= nw + 8'd1;
            if (nw == tn) begin td <= wdata; tw <= 1'b1; end
        end
    always @(posedge rclk or posedge rst)
        if (rst) nr <= 8'd0;
        else if (re && !rempty) nr <= nr + 8'd1;
    wire [7:0] occ = nw - nr;
    wire [AW:0] d_w_wq1 = wbin - g2b(wq1), d_wq1_wq2 = g2b(wq1) - g2b(wq2), d_wq2_r = g2b(wq2) - rbin, d_w_r = wbin - rbin;
    wire [AW:0] d_r_rq1 = rbin - g2b(rq1), d_rq1_rq2 = g2b(rq1) - g2b(rq2), d_w_rq2 = wbin - g2b(rq2);

    always @($global_clock) if (!init && !rst) begin
        // A1
        assert (wgray == ((wbin >> 1) ^ wbin));
        assert (rgray == ((rbin >> 1) ^ rbin));
        if (!$past(rst)) begin
            assert ($countones(wgray ^ $past(wgray)) <= 1);
            assert ($countones(rgray ^ $past(rgray)) <= 1);
        end
        // A2, with the pointer bookkeeping that also serves as the induction invariant
        assert (occ <= DEPTH);
        assert (wbin == nw[AW:0] && rbin == nr[AW:0]);
        // pointer distances are modular (AW+1 bits): computed in sized wires, never widened (see d_*)
        assert (d_w_wq1 <= DEPTH && d_wq1_wq2 <= DEPTH && d_wq2_r <= DEPTH && d_w_r <= DEPTH);
        assert (d_r_rq1 <= DEPTH && d_rq1_rq2 <= DEPTH && d_w_rq2 <= DEPTH);
        // ordered chains without wrap-around: wbin >= wq1 >= wq2 >= rbin and wbin >= rbin >= rq1 >= rq2,
        // the lags adding up exactly to the distance (k-induction invariant)
        assert ({1'b0, d_w_wq1} + {1'b0, d_wq1_wq2} + {1'b0, d_wq2_r} == {1'b0, d_w_r});
        assert ({1'b0, d_w_r} + {1'b0, d_r_rq1} + {1'b0, d_rq1_rq2} == {1'b0, d_w_rq2});
        // A3
        if (!rempty) assert (occ != 8'd0);
        if (!wfull)  assert (occ < DEPTH);
        // A4: the tracked word is at the head when it is the next to be read
        if (tw && !rempty && nr == tn) assert (rdata == td);
        // induction invariants for A4: before the tracked write the count has not passed it (I1);
        // while the tracked entry is in the FIFO its slot holds the recorded value (I2)
        if (!tw) assert (nw <= tn);
        if (tw && ((tn - nr) < occ)) assert (fmem == td);
        // A5
        assert (wdrop == (we && wfull));
    end

    // cover
    always @($global_clock) if (!init) begin
        cover (wfull);
        cover (wdrop && occ == DEPTH);
        cover (rempty && nw > 8'd20);
    end
endmodule
`default_nettype wire
