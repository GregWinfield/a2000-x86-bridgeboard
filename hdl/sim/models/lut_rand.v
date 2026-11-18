// SPDX-License-Identifier: MIT
// Simulation model of Yosys' generic $lut cell with a RANDOM TRANSPORT delay per instance,
// redrawn on every tb_hazard.redraw event. Used only by tb_hazard (C-02): transport delay keeps
// every glitch a skewed input can produce, so the test is pessimistic about decode hazards.
// The output is a pure function of the inputs (no internal LUT-mux glitch is modelled: a 4-input
// LUT is assumed glitch-free for single-input changes that do not change its value [K, TBV]).
`timescale 1ns/1ps
module \$lut (A, Y);
    parameter WIDTH = 0;
    parameter LUT   = 0;
    input  [WIDTH-1:0] A;
    output reg         Y;
    real d = 1.0;
    always @(tb_hazard.redraw)
        d = tb_hazard.LUT_MIN + (tb_hazard.LUT_MAX - tb_hazard.LUT_MIN) * (($random & 32'h7FFFFFFF) % 100000) / 100000.0;
    always @(A) Y <= #(d) LUT[A];
endmodule
