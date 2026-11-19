// SPDX-License-Identifier: MIT
// SPI slave front end, SCK clock domain (host link, sheet 4; docs/hdl/host-link-protocol.md §2).
// Mode 0: MOSI sampled on SCK rising, MSB first. CS_N high is an asynchronous reset of every
// frame-level register here, so an interrupted frame or an SCK that stops in mid-byte leaves no
// state behind (incomplete bytes are never written to the FIFO).
//  RX: every complete byte is offered to the asynchronous FIFO as {dropped, sof, byte}. A byte the
//      FIFO refuses (full) is lost, and the next stored byte of the frame carries dropped = 1, so the
//      core rejects the frame (check V1). sof marks the first byte after CS_N fell.
//  TX: byte 0 comes from byte0, a static register of the core (RSYNC, or 0 while a response is
//      being built), so its first bit is on MISO from CS_N falling, before any SCK edge. Bytes 1..
//      come from the response RAM, read with the address of the next byte a whole byte time before
//      it is shifted out.
//  MISO launch edge (protocol §13, FEATURES b2):
//      LAUNCH_RISE = 0: standard mode 0, MISO changes after SCK falling (half a period of setup).
//      LAUNCH_RISE = 1: early launch, MISO changes after SCK rising, just after the master sampled
//      the previous bit (almost a full period of setup; relies on the RP2040 sampling before its own
//      SCK edge, which hardware measurement M-15 must confirm). Needed for the 20 MHz target.
`default_nettype none
module z2_spi_slave #(
    parameter integer RAW = 9,                        // response RAM address width
    parameter integer LAUNCH_RISE = 0
) (
    input  wire           sck,
    input  wire           cs_n,
    input  wire           mosi,
    output wire           miso,
    // RX FIFO write port (clocked by sck rising inside z2_afifo)
    output wire           fifo_we,
    output wire [9:0]     fifo_wdata,                 // {dropped, sof, byte}
    input  wire           fifo_full,
    // TX
    input  wire [7:0]     byte0,                      // core register, static while frames run
    output wire [RAW-1:0] rd_addr,                    // response RAM: next byte index
    input  wire [7:0]     rd_data                     // response RAM output, registered on the launch edge
);
    // ---------------- receive (SCK rising)
    reg [2:0] rbit;                                   // bits received in the current byte
    reg [6:0] rsh;
    reg       first;                                  // no byte completed yet in this frame
    reg       drop_pend;                              // a byte of this frame was refused
    wire      byte_done = (rbit == 3'd7);
    assign fifo_we    = byte_done;
    assign fifo_wdata = {drop_pend, first, rsh, mosi};
    always @(posedge sck or posedge cs_n)
        if (cs_n) begin rbit <= 3'd0; rsh <= 7'd0; first <= 1'b1; drop_pend <= 1'b0; end
        else begin
            rbit <= rbit + 3'd1;
            rsh  <= {rsh[5:0], mosi};
            if (byte_done) begin
                first <= 1'b0;
                drop_pend <= fifo_full;               // refused: flag the next stored byte; stored: clear
            end
        end

    // ---------------- transmit (launch edge): explicit clock polarity, no derived clock
    reg [2:0]     fbit;                               // launch edges in the current byte
    reg [RAW-1:0] tidx;                               // index of the byte being sent
    reg [7:0]     tsh;                                // shift register for bytes 1..
    generate if (LAUNCH_RISE != 0) begin : g_rise
        always @(posedge sck or posedge cs_n)
            if (cs_n) begin fbit <= 3'd0; tidx <= {RAW{1'b0}}; tsh <= 8'h00; end
            else begin
                fbit <= fbit + 3'd1;
                if (fbit == 3'd7) begin if (tidx != {RAW{1'b1}}) tidx <= tidx + 1'b1; tsh <= rd_data; end
                else tsh <= {tsh[6:0], 1'b0};
            end
    end else begin : g_fall
        always @(negedge sck or posedge cs_n)
            if (cs_n) begin fbit <= 3'd0; tidx <= {RAW{1'b0}}; tsh <= 8'h00; end
            else begin
                fbit <= fbit + 3'd1;
                if (fbit == 3'd7) begin if (tidx != {RAW{1'b1}}) tidx <= tidx + 1'b1; tsh <= rd_data; end
                else tsh <= {tsh[6:0], 1'b0};
            end
    end endgenerate
    assign rd_addr = tidx + {{(RAW-1){1'b0}}, 1'b1};
    assign miso    = (tidx == {RAW{1'b0}}) ? byte0[3'd7 - fbit] : tsh[7];
endmodule
`default_nettype wire
