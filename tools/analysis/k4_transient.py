# SPDX-License-Identifier: MIT
"""S4-6 isolation analysis (sheet 4): the X4's K4 key switches the RP2040's I/O supply P3V_RP off while the
header 3.3 V (P3V3_S) stays up. How far does the supply of the translator outputs that face the RP2040 rise above
the collapsing IOVDD, and how much current does GP24 source, for each isolation option?

usage: python -I tools/analysis/k4_transient.py

Report: docs/stage2/sheet4-s46-isolation.md. Every parameter is a datasheet value [V] or an estimate [E]:
  IOVDD = P3V_RP: C_RP = 10.5 uF (C206 10 uF + C207, C209-C212 0.1 uF) [V S1 sh.21]. After Q32 opens it is
          discharged by the X4's own load: constant current I0 while IOVDD > V_BO (RP2040 running), then resistive
          (R = V_BO / I0) [E]. I0 = 5 / 25 / 100 mA [E].
  GP24  = IOVDD while the RP2040 runs (pad driven high); after brownout (IOVDD < V_BO = 1.62 V, the VREG_VIN
          minimum, used as the release point [E]) the pad is an input.
  Option A (rev A): U402 VCCB = RP_VIO = GP24 via R416 47 R; C404 100 nF; R417 100 k bleed; pad on-resistance
          50 R [E]. After pad release RP_VIO is held by C404 and clamped one diode drop (VF = 0.6 V [E]) above IOVDD
          by the RP2040's own ESD diodes: that clamp current flows into the unpowered RP2040.
  Option B (rev A1): U402 VCCB = P3V3_S; U402 /OE from a TLV7021 comparing GP24 with K x P3V3_S (K = 100 k /
          107.5 k; 1 % resistors -> K_MIN 0.9289; offset <= 8 mV, hysteresis <= 14 mV [V S68]); disable latency
          2 us budgeted [E] (typical tPLH 310 ns [V S68] + pull-up RC about 0.1 us + translator tPHZ <= 6.2 ns [V S66]).
  Option C (emitter follower): VCCB = GP24 - VBE (0.65 V [E]); a bleed (time constant TAU) is the only pull-down.
Limits [V S65 Tables 622, 625]: pin voltage <= IOVDD + 0.5 V (absolute maximum); VIH <= IOVDD + 0.3 V (operating).
"""

C_RP, V_BO, VF, DT = 10.5e-6, 1.62, 0.6, 0.1e-6
K_NOM, K_MIN, VOS_HYS, T_LAT = 100 / 107.5, 0.9289, 0.008 + 0.014, 2e-6


def iovdd_trace(i0, t_end=60e-3):
    v, t, out = 3.3 - 0.01, 0.0, []
    while t < t_end and v > 0.02:
        i = i0 if v > V_BO else v / (V_BO / i0)
        v -= i / C_RP * DT
        t += DT
        out.append((t, v))
    return out


def option_a(trace):
    r_track, c404, r417 = 50 + 47, 100e-9, 100e3
    vio, worst, t03, t05 = 3.3 - 0.02, -9.0, 0.0, 0.0
    for t, v in trace:
        if v > V_BO:                                         # pad drives: bidirectional tracking through the PMOS
            vio += ((v - vio) / (r_track * c404) - vio / (r417 * c404)) * DT
        else:                                                # pad released: C404 holds, bleeds, clamps at v + VF
            vio -= vio / (r417 * c404) * DT
            vio = min(vio, v + VF)
        d = vio - v
        worst = max(worst, d)
        t03 += DT if d > 0.3 else 0.0
        t05 += DT if d > 0.5 - 1e-9 else 0.0
    return worst, t03, t05


def option_b(trace, p3v3s):
    trip_v = K_MIN * p3v3s - VOS_HYS                         # lowest possible trip point
    t_trip = next((t for t, v in trace if v < trip_v), None)
    if t_trip is None:
        return None
    worst, t03 = -9.0, 0.0
    for t, v in trace:
        if t > t_trip + T_LAT:
            break
        d = p3v3s - v
        worst = max(worst, d)
        t03 += DT if d > 0.3 else 0.0
    return worst, t03, t_trip


def option_c(trace, tau=47e-6, vbe=0.65):
    vb, worst, t05 = 3.3 - vbe, -9.0, 0.0
    for t, v in trace:
        gp = v if v > V_BO else 0.0
        target = gp - vbe
        vb = target if target > vb else vb - vb / tau * DT    # the follower sources; only the bleed pulls down
        d = vb - v
        worst = max(worst, d)
        t05 += DT if d > 0.5 else 0.0
    return worst, t05


def gp24_current():
    """GP24 source current for options A and B (mA): (transient peak, steady state)."""
    v = 3.3
    # A: C404 charged through R416 and the pad (on-resistance not specified: 20-60 R [E]); steady: R417, ICCB
    # (<= 8 uA [V S66]), R424 when IRQ_N is asserted, MISO switching into about 25 pF at 10-20 MHz SPI [E]
    a_peak = (v / (47 + 60) * 1e3, v / (47 + 20) * 1e3)
    sw = tuple(25e-12 * v * f * 1e3 for f in (5e6, 10e6))       # alternating bits: f = SCK / 2
    a_steady = tuple(v / 100e3 * 1e3 + 0.008 + v / 10e3 * 1e3 + s for s in sw)
    # B: R430 pull-down, R424 when IRQ_N is asserted, comparator input bias (5 pA typical [V S68])
    b_steady = v / 100e3 * 1e3 + v / 10e3 * 1e3
    return a_peak, a_steady, b_steady


if __name__ == "__main__":
    print("K4 event: largest (output-side supply - IOVDD) at the RP2040 pins")
    print(f"{'I0':>6} {'IOVDD slope':>12} | {'A: max':>7} {'>0.3V':>9} {'>0.5V':>9} | {'B: max':>7} {'disabled after':>14} | {'C: max':>7}")
    for i0 in (5e-3, 25e-3, 100e-3):
        tr = iovdd_trace(i0)
        a = option_a(tr)
        rows = [option_b(tr, p) for p in (3.135, 3.3, 3.465)]
        c = option_c(tr)
        print(f"{i0*1e3:5.0f}m {i0/C_RP/1e3:8.2f} V/ms | {a[0]:6.3f}V {a[1]*1e6:7.0f}us {a[2]*1e6:7.0f}us | "
              f"{max(r[0] for r in rows):6.3f}V {rows[1][2]*1e6:11.1f} us | {c[0]:6.3f}V")
    print("Option B per P3V3_S (3.135 / 3.3 / 3.465 V), time above +0.3 V in brackets:")
    for i0 in (5e-3, 25e-3, 100e-3):
        tr = iovdd_trace(i0)
        print(f"  I0 {i0*1e3:3.0f} mA: " + ", ".join(f"{r[0]:.3f} V ({r[1]*1e6:.1f} us)" for r in (option_b(tr, p) for p in (3.135, 3.3, 3.465))))
    print("Option C sensitivity to the IOVDD slope and the bleed time constant:")
    for tau in (47e-6, 470e-6):
        for i0 in (100e-3, 500e-3, 1.0):
            print(f"  tau {tau*1e6:3.0f} us, slope {i0/C_RP/1e3:4.0f} V/ms: max {option_c(iovdd_trace(i0), tau)[0]:+.3f} V")
    ap, ast, bst = gp24_current()
    print(f"GP24 current, option A: turn-on peak {ap[0]:.0f}-{ap[1]:.0f} mA [E], steady {ast[0]:.2f}-{ast[1]:.2f} mA "
          f"(IRQ_N asserted, 10-20 MHz SPI)")
    print(f"GP24 current, option B: steady <= {bst:.2f} mA (IRQ_N asserted), no turn-on transient beyond the ribbon capacitance")
