// SPDX-License-Identifier: MIT
// Behavioural models of the sheet-1 parts, for the testbenches only (not synthesisable).
// Delays: datasheet min/max at VCCA 3.3 V / VCCB 5 V, -40..85 C (sheet1-design-notes section 2):
//   SN74LVC16244A  tpd 1.1-4.1 ns                       (SCAS699C)
//   SN74LVCH16T245 A->B 0.6-4.4, B->A 0.6-6.0, OE->B en 0.8-6.4 / dis 0.8-6.3,
//                  OE->A en 0.8-8.1 / dis 1.6-8.2 ns   (SCES635B)
//   SN74LVC8T245   A->B 0.5-4.4, OE->B en 0.9-6.8 / dis 0.8-6.3 ns (SCES584D)
//   SN74LVC1G00    tpd 1.0-4.7 ns (CL 30/50 pF)         (SCES212AC)
//   SN74LVC32A     tpd 1.0-3.8 ns                       (SCAS286U)
//   SN74LVC07A     tpd 1.0-3.6 ns                       (SCAS595W)
// Delay selection (compile-time define DLY_MODE): 0 = static random per channel within
// [min,max] (device skew; SEED varies it), 1 = all maximum, 2 = all minimum.
// Output-enable windows are PESSIMISTIC for contention checks: a port is treated as
// possibly driving from (enable + min delay) until (disable + max delay).
`timescale 1ns/1ps
`ifndef DLY_MODE
`define DLY_MODE 0
`endif

// ---------------------------------------------------------------- per-channel transport delay
module m_dly #(
    parameter integer W    = 1,
    parameter real    TMIN = 1.0,
    parameter real    TMAX = 4.0,
    parameter integer SEED = 1
) (
    input  wire [W-1:0] a,
    output wire [W-1:0] y
);
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : ch
        real    d;
        integer s;
        reg     q;
        initial begin
            s = SEED * 7919 + g * 104729 + 1;
            if (`DLY_MODE == 1)      d = TMAX;
            else if (`DLY_MODE == 2) d = TMIN;
            else                     d = TMIN + (TMAX - TMIN) * (($random(s) & 32'h7FFFFFFF) % 100000) / 100000.0;
        end
        initial #(0.001) q = a[g];          // static inputs (e.g. pulled-up nets) never change
        always @(a[g]) q <= #(d) a[g];      // transport delay: pulses are preserved
        assign y[g] = q;
    end endgenerate
endmodule

// ---------------------------------------------------------------- bus-hold (LVCH) keeper
// Weak drive of the last strongly-driven level; any strong driver overrides it.
module m_bushold #(parameter integer W = 16) (inout wire [W-1:0] bus);
    reg [W-1:0] keep = {W{1'b1}};
    assign (weak1, weak0) bus = keep;
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : ch
        always @(bus[g]) if ((bus[g] === 1'b0) || (bus[g] === 1'b1)) keep[g] = bus[g];
    end endgenerate
endmodule

// ---------------------------------------------------------------- pessimistic enable window
module m_en_window #(
    parameter real TMIN = 1.0,
    parameter real TMAX = 6.0
) (
    input  wire en,
    output wire w
);
    reg e_min = 1'b0, e_max = 1'b0;
    always @(en) e_min <= #(TMIN) en;
    always @(en) e_max <= #(TMAX) en;
    assign w = (e_min !== 1'b0) | (e_max !== 1'b0);   // X counts as "may be driving"
endmodule

// ---------------------------------------------------------------- U103 SN74LVCH16T245 (16-bit, halves tied)
module m_lvch16t245 #(parameter integer SEED = 1) (
    input  wire        dir,      // 1 = A->B (card drives Zorro)
    input  wire        oe_n,
    input  wire        pwr,      // VCCA and VCCB both valid (VCC isolation otherwise)
    inout  wire [15:0] a,        // LD side
    inout  wire [15:0] b,        // Zorro D side
    output wire        a_drv,    // A port may be driving
    output wire        b_drv     // B port may be driving
);
    wire want_b = (pwr === 1'b1) & (oe_n !== 1'b1) & (dir !== 1'b0);
    wire want_a = (pwr === 1'b1) & (oe_n !== 1'b1) & (dir !== 1'b1);
    m_en_window #(.TMIN(0.8), .TMAX(6.4)) u_wb (.en(want_b), .w(b_drv));
    m_en_window #(.TMIN(0.8), .TMAX(8.2)) u_wa (.en(want_a), .w(a_drv));
    wire [15:0] a2b, b2a;
    m_dly #(.W(16), .TMIN(0.6), .TMAX(4.4), .SEED(SEED))       u_da (.a(a), .y(a2b));
    m_dly #(.W(16), .TMIN(0.6), .TMAX(6.0), .SEED(SEED + 101)) u_db (.a(b), .y(b2a));
    assign b = b_drv ? a2b : 16'hzzzz;
    assign a = a_drv ? b2a : 16'hzzzz;
    // C-05 assertion: direction must never change while either port is (or may still be) enabled
    always @(dir)
        if ($realtime > 0.0 && (a_drv || b_drv || (pwr === 1'b1 && oe_n === 1'b0)))
            $display("ASSERT-FAIL %0t U103: DIR changed while enabled (oe_n=%b a_drv=%b b_drv=%b)",
                     $realtime, oe_n, a_drv, b_drv);
endmodule

// ---------------------------------------------------------------- U104 SN74LVC8T245 (channels 1-2 used, DIR = A->B)
module m_lvc8t245_2ch #(parameter integer SEED = 1) (
    input  wire       oe_n,      // CARD_EN_N
    input  wire       pwr,
    input  wire [1:0] a,         // {ZF_CFGOUT_N, ZF_SLAVE_N}
    output wire [1:0] b,         // {Z_CFGOUT_N, Z_SLAVE_N} (after 22R)
    output wire       drv        // outputs may be driving
);
    wire want = (pwr === 1'b1) & (oe_n !== 1'b1);
    m_en_window #(.TMIN(0.9), .TMAX(6.8)) u_w (.en(want), .w(drv));
    wire [1:0] ad;
    // A->B 0.5-4.4 ns plus 22R and slot load 0.5-2.0 ns [E]
    m_dly #(.W(2), .TMIN(1.0), .TMAX(6.4), .SEED(SEED)) u_d (.a(a), .y(ad));
    assign b = drv ? ad : 2'bzz;
endmodule

// ---------------------------------------------------------------- simple gates on +3V3
module m_nand2 #(parameter integer SEED = 1) (input wire a, input wire b, input wire pwr, output wire y);
    wire f = (pwr === 1'b1) ? ~(a & b) : 1'b1;     // unpowered: output inert, R123 pull-up [A]
    m_dly #(.W(1), .TMIN(1.0), .TMAX(4.7), .SEED(SEED)) u_d (.a(f), .y(y));
endmodule

module m_or2 #(parameter integer SEED = 1) (input wire a, input wire b, input wire pwr, output wire y);
    wire f = (pwr === 1'b1) ? (a | b) : 1'b1;
    m_dly #(.W(1), .TMIN(1.0), .TMAX(3.8), .SEED(SEED)) u_d (.a(f), .y(y));
endmodule

// U105 SN74LVC07A channel: input low -> output pulls low; otherwise released (Ioff when unpowered)
module m_od #(parameter integer SEED = 1) (input wire a, input wire pwr, output wire y);
    wire f;
    m_dly #(.W(1), .TMIN(1.0), .TMAX(3.6), .SEED(SEED)) u_d (.a(a), .y(f));
    assign y = ((pwr === 1'b1) && (f === 1'b0)) ? 1'b0 : 1'bz;
endmodule

// ---------------------------------------------------------------- U108/U109 TPS3808 + DISABLE jumper
// Open-drain outputs wired-AND onto EN_OK (10k pull-up to +3V3). CT open: release delay
// 12-28 ms after the rail is good (SBVS050N); scaled to TD in simulation. Assertion on a
// rail fault is immediate here (datasheet: <= 20 us).
module m_supervisors #(parameter real TD = 5000.0) (
    input  wire p3_ok,      // +3V3 above 3.07 V
    input  wire p5_ok,      // +5V_BUS above ~4.27 V
    input  wire jumper,     // 1 = DISABLE jumper fitted
    output wire en_ok
);
    reg r3 = 1'b0, r5 = 1'b0;
    always @(negedge p3_ok) begin r3 = 1'b0; disable rise3; end
    always @(posedge p3_ok) begin : rise3 #(TD); if (p3_ok) r3 = 1'b1; end
    always @(negedge p5_ok) begin r5 = 1'b0; disable rise5; end
    always @(posedge p5_ok) begin : rise5 #(TD); if (p5_ok) r5 = 1'b1; end
    assign en_ok = r3 & r5 & ~jumper & p3_ok;    // pull-up rail is +3V3
endmodule
