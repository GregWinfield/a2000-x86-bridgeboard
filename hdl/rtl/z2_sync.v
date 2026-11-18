// SPDX-License-Identifier: MIT
// Two-flop synchroniser for asynchronous Zorro inputs (docs/hdl/zorro-interface-spec.md section 4).
`default_nettype none
module z2_sync #(
    parameter integer W = 1,
    parameter [W-1:0] INIT = {W{1'b0}}
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* ASYNC_REG = "TRUE" *) reg [W-1:0] s1 = INIT /* synthesis syn_preserve=1 */;
    (* ASYNC_REG = "TRUE" *) reg [W-1:0] s2 = INIT /* synthesis syn_preserve=1 */;
    always @(posedge clk) begin
        s1 <= d;
        s2 <= s1;
    end
    assign q = s2;
endmodule
`default_nettype wire
