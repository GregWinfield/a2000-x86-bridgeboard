// SPDX-License-Identifier: MIT
// Host-port placeholder (Stage 3). The RP2040 SPI slave that drives the host port belongs to
// sheet 4 (host link) and replaces this module. Until then the host port is idle in synthesis.
// Simulation compiles hdl/sim/models/hostif_bfm.v instead, a bus-functional model with the
// same ports that issues host transactions.
//
// Host-port contract (docs/hdl/shared-memory-spec.md section 5):
//   * clk domain; h_req is held with stable h_we/h_reg/h_addr/h_be/h_wdata until h_ack = 1;
//     the transaction completes at that clock edge (h_rdata valid with h_ack for reads)
//   * h_reg = 0: SRAM word address h_addr[17:0]; h_reg = 1: shared register h_addr[3:0]
//   * transactions are executed one at a time, in order (ordering guarantee G4)
`default_nettype none
module z2_hostif (
    input  wire        clk,
    input  wire        por,
    output wire        h_req,
    output wire        h_we,
    output wire        h_reg,
    output wire [17:0] h_addr,
    output wire [1:0]  h_be,
    output wire [15:0] h_wdata,
    input  wire        h_ack,
    input  wire [15:0] h_rdata
);
    assign h_req   = 1'b0;
    assign h_we    = 1'b0;
    assign h_reg   = 1'b0;
    assign h_addr  = 18'd0;
    assign h_be    = 2'b00;
    assign h_wdata = 16'h0000;
endmodule
`default_nettype wire
