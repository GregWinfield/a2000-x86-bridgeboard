# SPDX-License-Identifier: MIT
"""Sheet 5 power analysis (owner review of PR #10: S5-2, S5-6, S5-7 and the power budget).

Sections:
  1  X4 12 V eFuse current limit (S5-2): ILIM band for each candidate RILM, the selection rule
  2  Overcurrent blanking (ITIMER), fast trip, soft start (dVdt) and inrush
  3  Start-up thermal check against TI's thermal-shutdown curve (Zth model), five load cases
  4  Protection coordination ladder (12 V) and A2000 PSU headroom
  5  Component ratings and requirements (12 V path)
  6  UVLO/OVLO resistor strings for U501 (12 V) and U503 (5 V)
  7  5 V protection chain (S5-6): overvoltage paths, output overshoot bound, regulator comparison
  8  Thermal estimates (S5-7)
  9  Power budget (+12 V, +5 V, +3V3)

Evidence tags as in docs/sources.md: [V] datasheet value, [Vs] secondary source, [K] general engineering
knowledge, [A] assumption, [E] estimate or model output. Every result is a MODEL-DERIVED ESTIMATE built on
datasheet limits plus the stated assumptions; none is a manufacturer guarantee. Rounding is conservative:
maxima and requirements round up, minima, margins and slacks round down.

usage: python tools/analysis/sheet5_power.py
"""
from __future__ import annotations

import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def up(x, step):
    return math.ceil(x / step - 1e-9) * step


def down(x, step):
    return math.floor(x / step + 1e-9) * step


def hdr(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


E96 = [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50,
       1.54, 1.58, 1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
       2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24, 3.32, 3.40, 3.48, 3.57,
       3.65, 3.74, 3.83, 3.92, 4.02, 4.12, 4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
       5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
       8.66, 8.87, 9.09, 9.31, 9.53, 9.76]

# ------------------------------------------------------------------------------------------------ inputs
# TI TPS25947 eFuse, SLVSFC9C (rev. May 2026) [V]
ILIM_TABLE = [(6650, 0.425, 0.500, 0.575), (3320, 0.850, 1.007, 1.150), (1650, 1.800, 2.028, 2.200),
              (750, 3.960, 4.452, 4.840), (549, 5.400, 6.068, 6.600)]   # Table 6.5: RILM (ohm) -> ILIM min/typ/max (A)
K_ILM = 3334.0              # Eq. 5/7: RILM = 3334 / ILIM
ISC_GAIN_TYP = 2.01         # scalable fast-trip threshold : ILIM, 201 % typical (no limits published)
IFT_TYP = 22.2              # fixed fast-trip threshold, typical (A)
T_SC_TYP = 0.5e-6           # tSC / tFT fast-trip response, typical
ITIMER_I = (1.2e-6, 2.5e-6)       # IITIMER discharge current min, max
ITIMER_DV = (1.286, 1.741)        # delta-VITIMER min, max
IDVDT = (0.81e-6, 2.21e-6, 3.82e-6)   # dVdt charging current min, typ, max
SR_K = 2000.0               # Eq. 4: CdVdt (pF) = 2000 / SR (V/ms), at typical IdVdt
RON_MAX = 0.045             # 2.7-23 V, 3 A, -40..125 C
V_UVLO_R = (1.183, 1.223)   # EN/UVLO rising min, max
V_UVLO_F = (1.076, 1.116)
V_OV_R = (1.183, 1.223)     # OVLO rising min, max
V_OV_F = (1.076, 1.116)
V_PIN_ABS = 6.5             # EN/UVLO, OVLO, FLT pin absolute maximum
I_EN_LKG = 0.1e-6           # EN/UVLO and OVLO leakage, max
R_TOP_MIN = 350e3           # ROC note 2: pull-up from IN >= 350 kOhm for supplies > 5 V or reverse-polarity exposure
TSD = 154.0                 # thermal shutdown, typical (no minimum published)
THETA_JA = (41.7, 74.5)     # custom 4-layer with 8 vias / JEDEC 4-layer without vias (C/W)
PSI_JB = (20.0, 27.6)
IMAX = 5.5                  # continuous switch current, TJ <= 125 C
IQ_ON = 610e-6
SR_IN_MAX = 100.0           # V/us, input rising slew-rate absolute maximum
# Figure 8-3 "Thermal Shut-Down Plot During Inrush": (power W, time to TSD s), READ FROM THE GRAPH [E].
# The starting junction temperature of the plot is not stated; 25 C is assumed [A].
FIG83 = [(90, 0.09e-3), (80, 0.105e-3), (50, 0.16e-3), (40, 0.23e-3), (30, 0.35e-3), (20, 1.0e-3), (10, 6.5e-3),
         (8, 10e-3), (6.5, 100e-3), (5, 450e-3), (4, 1.0), (2.8, 10.0)]
FIG83_T0 = 25.0
ZTH_SAFETY = 1.25           # [A] margin on the graph-derived thermal impedance
CDVDT_12 = 10e-9            # selected U501 soft-start capacitor (section 3 grid); TI: 100 ohm in series at >= 10 nF
C501 = 470e-6               # selected X4-side bulk capacitor (section 3: cases A, B and E)

# System and load data
I_DESIGN = 2.5              # X4 design current at 12 V (30 W; Radxa: 12 V >= 2.5 A [V S3]; architecture review 8.3)
I_X4_PEAK_MEAS = 27.3 / 12  # one published peak measurement, 27.3 W [Vs S9]
V12 = (11.4, 12.0, 12.6)    # A2000 12 V, +/-5 % [K]; G-PSU measures the real machine
V5 = (4.75, 5.0, 5.25)      # A2000 5 V, +/-5 % [K]
C_X4 = (150e-6, 250e-6)     # X4 ADP12V input capacitance [E] (architecture review 8.4)
T_A = 60.0                  # ambient inside the closed A2000 near the card [A]
R_TOL = 0.015               # 1 % resistor plus 100 ppm/K over 50 K [E]
C_TOL = 0.05                # C0G capacitors, +/-5 % [A] (part choice)


# ------------------------------------------------------------------------------------------------ helpers
def band_ratios():
    """Envelope of (min/nominal, max/nominal) over the tested points from 549 to 1650 ohm [E: interpolation]."""
    pts = [t for t in ILIM_TABLE if 549 <= t[0] <= 1650]
    lo = min(mn / (K_ILM / r) for r, mn, _, _ in pts)
    hi = max(mx / (K_ILM / r) for r, _, _, mx in pts)
    return lo, hi


RAT_LO, RAT_HI = band_ratios()


def ilim_band(r):
    nom = K_ILM / r
    return RAT_LO * K_ILM / (r * (1 + R_TOL)), nom, RAT_HI * K_ILM / (r * (1 - R_TOL))


_ZPTS = sorted((tt, (TSD - FIG83_T0) / p) for p, tt in FIG83)
_ZLOG = [(math.log(t), math.log(z)) for t, z in _ZPTS]


def zth(t):
    """Junction thermal impedance (C/W) after t seconds of constant power, from the Figure 8-3 readings, x ZTH_SAFETY."""
    if t <= _ZPTS[0][0]:
        return ZTH_SAFETY * _ZPTS[0][1] * math.sqrt(t / _ZPTS[0][0])
    if t >= _ZPTS[-1][0]:
        return ZTH_SAFETY * _ZPTS[-1][1]
    lt = math.log(t)
    for (l1, z1), (l2, z2) in zip(_ZLOG, _ZLOG[1:]):
        if l1 <= lt <= l2:
            return ZTH_SAFETY * math.exp(z1 + (lt - l1) / (l2 - l1) * (z2 - z1))
    raise ValueError(t)


def tj_peak(times, powers, t0, nseg=300):
    """Peak junction temperature for a power profile: the profile is resampled to <= nseg segments of equal length
    (segment-average power, so the energy is kept), then Zth step responses are superposed at every segment end."""
    t_end = times[-1]
    if t_end <= 0:
        return t0
    n = min(nseg, len(times) - 1)
    edges = [t_end * k / n for k in range(n + 1)]
    seg, j = [], 1
    for k in range(n):
        e_sum, t_lo, t_hi = 0.0, edges[k], edges[k + 1]
        while j < len(times) and times[j] <= t_hi + 1e-15:
            e_sum += powers[j] * (times[j] - times[j - 1])
            j += 1
        seg.append(e_sum / (t_hi - t_lo))
    steps, last = [], 0.0
    for k, pw in enumerate(seg):
        if pw != last:
            steps.append((edges[k], pw - last))
            last = pw
    peak = t0
    for tp in edges[1:] + [t_end * 1.5]:
        peak = max(peak, t0 + sum(dp * zth(tp - ts) for ts, dp in steps if tp > ts))
    return peak


# ================================================================================================ 1
def section1():
    hdr("1  X4 12 V eFuse current limit (S5-2): TPS259470L, ILIM band per RILM")
    print(f"Datasheet band ratios over the tested points 549-1650 ohm [V, Table 6.5]: min/nominal >= {RAT_LO:.4f}, "
          f"max/nominal <= {RAT_HI:.4f} (nominal = 3334/RILM, Eq. 7)")
    print(f"RILM tolerance {R_TOL * 100:.1f} % (1 % part + TCR) [E]. Values between tested points interpolated [E].")
    print(f"Design load {I_DESIGN} A [V S3]; highest published X4 measurement {I_X4_PEAK_MEAS:.2f} A (27.3 W) [Vs S9]")
    req = 1.05 * I_DESIGN
    print(f"Selection rule: ILIM_min >= 1.05 x design = {req:.3f} A (a sustained design load never enters active limiting),")
    print("then the largest RILM, so that ILIM_max (the current the eFuse lets through indefinitely) is as low as possible.\n")
    print(f"{'RILM':>8} {'ILIM min':>9} {'nominal':>8} {'ILIM max':>9}  meets rule")
    chosen = None
    for m in E96[:15]:
        r = m * 1000
        lo, nom, hi = ilim_band(r)
        ok = lo >= req
        if ok:
            chosen = r
        print(f"{r:8.0f} {down(lo, 0.01):9.2f} {nom:8.3f} {up(hi, 0.01):9.2f}  {'yes' if ok else 'no'}")
    lo, nom, hi = ilim_band(750)
    print(f"\nRev A proposal, RILM 750: {down(lo, 0.01):.2f}-{up(hi, 0.01):.2f} A (datasheet 3.96-4.84 A at 0 % resistor tolerance)")
    lo, nom, hi = ilim_band(chosen)
    print(f"SELECTED RILM = {chosen:.0f} ohm 1 %: ILIM {down(lo, 0.01):.2f}-{up(hi, 0.01):.2f} A (nominal {nom:.3f} A); "
          f"margin above design >= {down((lo / I_DESIGN - 1) * 100, 1):.0f} %")
    print("Note: no E96 value gives ILIM_max <= 3.0 A with ILIM_min > 2.5 A: the band is 1.22 x wide (datasheet) plus resistor")
    print("tolerance, so a 3 A contact cannot be protected by the eFuse alone; the INA226/FPGA sustained-overload trip (section 4)")
    print("covers the region between the design load and ILIM_max.")
    return chosen


# ================================================================================================ 2
def section2(rilm):
    hdr("2  Overcurrent blanking (ITIMER), fast trip, soft start and inrush")
    lo, nom, hi = ilim_band(rilm)
    print("tITIMER (ms) = dV_ITIMER (V) x C_ITIMER (nF) / I_ITIMER (uA)  (Eq. 8) [V], C0G +/-5 % [A]")
    timer = {}
    for c in (4.7e-9, 10e-9, 22e-9):
        tmin = ITIMER_DV[0] * c * (1 - C_TOL) / ITIMER_I[1]
        tmax = ITIMER_DV[1] * c * (1 + C_TOL) / ITIMER_I[0]
        timer[c] = (tmin, tmax)
        print(f"  C_ITIMER {c * 1e9:5.1f} nF: {down(tmin * 1e3, 0.01):6.2f} - {up(tmax * 1e3, 0.1):5.1f} ms")
    print("SELECTED C_ITIMER = 10 nF: transients between ILIM and the fast-trip threshold pass for >= "
          f"{down(timer[10e-9][0] * 1e3, 0.1):.1f} ms and at most {up(timer[10e-9][1] * 1e3, 0.1):.1f} ms")
    isc_lo, isc_hi = ISC_GAIN_TYP * lo, ISC_GAIN_TYP * hi
    print(f"Scalable fast trip ISC = 2.01 x ILIM (typical ratio only [V]) -> {down(isc_lo, 0.1):.1f}-{up(isc_hi, 0.1):.1f} A [E]; "
          f"fixed fast trip IFT {IFT_TYP} A typ; response 500 ns typ [V]")
    e_pulse = isc_hi ** 2 * timer[10e-9][1]
    print(f"Largest blanked transient: {up(isc_hi, 0.1):.1f} A for {up(timer[10e-9][1] * 1e3, 0.1):.1f} ms -> I^2t "
          f"{up(e_pulse, 0.01):.2f} A^2 s (contact heating negligible: contact thermal time constants are seconds [K])")
    print("\nSoft start: SR = 2000 / CdVdt(pF) V/ms at typical IdVdt (Eq. 4); SR scales with IdVdt 0.81-3.82 uA [V] -> [E]")
    sr = {}
    for cd in (1800e-12, 3300e-12, 4700e-12, 6800e-12, 10000e-12):
        sr[cd] = sr_band(cd)
        smin, typ, smax = sr[cd]
        print(f"  CdVdt {cd * 1e12:4.0f} pF: SR {down(smin, 0.01):.2f} / {typ:.2f} / {up(smax, 0.01):.2f} V/ms "
              f"(min/typ/max); 12 V rise {down(12 / smax, 0.1):.1f}-{up(12 / smin, 0.1):.1f} ms")
    return timer[10e-9], sr, (lo, hi)


def sr_band(cd):
    typ = SR_K / (cd * 1e12)
    return typ * IDVDT[0] / IDVDT[1] / (1 + C_TOL), typ, typ * IDVDT[2] / IDVDT[1] / (1 - C_TOL)


# ================================================================================================ 3
def ramp_profile(vin, sr_vms, c_total, load, ilim, dt=20e-6):
    """Time-step the soft start: SR-limited ramp, total current capped at ILIM (the start-up current limit engages
    without the ITIMER delay [V 7.3.5.3 note 3]). load(v) -> load current (A). A ramp that cannot finish (load above
    ILIM) is reported as STALL: the part then stays in current limit until thermal shutdown (start-up fails)."""
    v, t, times, powers = 0.0, 0.0, [0.0], [0.0]
    sr = sr_vms * 1e3
    while v < vin - 1e-3 and t < 2.0:
        il = load(v)
        i_tot = min(c_total * sr + il, ilim)
        dv = (i_tot - il) / c_total * dt
        if dv <= 0:
            return times, powers, t, True
        t += dt
        times.append(t)
        powers.append((vin - v) * i_tot)
        v = min(vin, v + dv)
    return times, powers, t, False


def case_e(c501, ilim, vin=None):
    """X4 internal-rail switch closing abruptly onto 200 uF after the soft start [A, pessimistic]: charge sharing with
    C501 (-20 %) and the X4's input-side 50 uF [A]; the eFuse fast-trips, then recharges in current limit [V 7.3.5.4]."""
    vin = vin or V12[2]
    c_a = c501 * 0.8 + 50e-6
    c_int = 200e-6
    vf = vin * c_a / (c_a + c_int)
    t, v, dt, times, powers = 0.0, vf, 5e-6, [0.0], [0.0]
    while v < vin - 0.01:
        powers.append((vin - v) * ilim)
        v += ilim / (c_a + c_int) * dt
        t += dt
        times.append(t)
    return vf, t, max(powers), tj_peak(times, powers, T_A + 10.0)


LOADS = [("A capacitive only", lambda v: 0.0),
         ("B + X4 constant 1 A above 9 V [A]", lambda v: 1.0 if v >= 9.0 else 0.0),
         ("C + X4 constant 10 W above 4.5 V [A, pessimistic]", lambda v: 10.0 / v if v >= 4.5 else 0.0)]


def section3(sr, ilim_band_):
    hdr("3  Start-up thermal check (TPS259470L, 12 V): time-stepped ramp + Zth model from Figure 8-3")
    lo, hi = ilim_band_
    print(f"Zth(t) = (154 - 25 C) / P_fig(t) from the graph readings [E], x {ZTH_SAFETY} [A]; start TJ = TA = {T_A:.0f} C [A]")
    print(f"(Check against TI's example, 1.69 W for 20 ms called safe: this model gives +{up(1.69 * zth(0.02), 1):.0f} C.)")
    for t in (1e-4, 1e-3, 1e-2, 0.1, 1.0, 10.0):
        print(f"  Zth({t:g} s) = {zth(t):5.1f} C/W")
    vin = V12[2]
    print(f"\nVIN {vin} V; X4 input capacitance 250 uF [E]; C501 at +20 %; current cap ILIM_min {down(lo, 0.01):.2f} A:")
    print(f"{'case':52} {'C501':>5} {'CdVdt':>6} {'SR':>5} {'ramp ms':>8} {'Pmax W':>7} {'TJ pk':>6} {'margin':>7}")
    grid = {}
    for name, load in LOADS:
        for c501 in (100e-6, 220e-6, 470e-6):
            c_tot = c501 * 1.2 + 1e-6 + C_X4[1]
            for cd, (smin, typ, smax) in sr.items():
                for s_ in (smin, smax):
                    times, powers, tr, stalled = ramp_profile(vin, s_, c_tot, load, lo)
                    tj = tj_peak(times, powers, T_A) if not stalled else float("inf")
                    key = (name[0], c501, cd)
                    grid[key] = max(grid.get(key, -1e9), tj)
                    tjs = f"{tj:6.1f}" if not stalled else "   TSD"
                    mg = f"{down(TSD - tj, 1):7.0f}" if not stalled else "  STALL"
                    print(f"{name:52} {c501 * 1e6:5.0f} {cd * 1e12:6.0f} {s_:5.2f} {tr * 1e3:8.1f} {max(powers):7.1f} {tjs} {mg}")
    print("\nCase E (pessimistic [A]): the X4's internal-rail switch (CH224D-driven Q22/Q23 with 220 pF Miller capacitors")
    print("C344/C345 [V S1 sheet 26], so a controlled turn-on is likely) is assumed to close ABRUPTLY onto 200 uF after the")
    print("soft start; C501 and the X4's input-side 50 uF [A] share charge; the eFuse fast-trips and recharges in current limit:")
    e_worst = {}
    for c501 in (100e-6, 220e-6, 470e-6):
        for ilim in (lo, hi):
            vf, t, pmax, tj = case_e(c501, ilim)
            e_worst[c501] = max(e_worst.get(c501, 0), tj)
            print(f"  C501 {c501 * 1e6:3.0f} uF, ILIM {ilim:.2f} A: VOUT dips to {vf:4.1f} V, recharge {t * 1e3:4.2f} ms, "
                  f"Pmax {pmax:5.1f} W, TJ peak {tj:5.1f} C (from {T_A + 10:.0f} C), margin {down(TSD - tj, 1):.0f} C")
    print("\nSelection (largest worst-case margin over cases A, B and E; case C is a failure mode, not a design case):")
    best = None
    for c501 in (100e-6, 220e-6, 470e-6):
        for cd in sr:
            ab = max(grid[("A", c501, cd)], grid[("B", c501, cd)])
            worst = max(ab, e_worst[c501])
            print(f"  C501 {c501 * 1e6:3.0f} uF, CdVdt {cd * 1e12:4.0f} pF: worst TJ {worst:5.1f} C (A/B {ab:5.1f} C, "
                  f"E {e_worst[c501]:5.1f} C), margin {down(TSD - worst, 1):.0f} C")
            if best is None or (round(worst, 1), round(ab, 1)) < (round(best[0], 1), round(best[3], 1)):
                best = (worst, c501, cd, ab)
    print(f"  -> best: C501 {best[1] * 1e6:.0f} uF with CdVdt {best[2] * 1e12:.0f} pF (selected in selections(): C501 = "
          f"{C501 * 1e6:.0f} uF, CdVdt = {CDVDT_12 * 1e12:.0f} pF)")
    print("Reading: case C (the X4 drawing constant power from a few volts) cannot be started by ANY linear soft start of")
    print("this size; it is excluded only by the X4's own input switch (CH224D gate control) and Radxa's 'do not supply 5 V'")
    print("[V S3], an inference [A]. M-17 measures the X4 input current and voltage during the ramp before an A2000 is used.")
    return best


# ================================================================================================ 4
def section4(rilm, timer):
    hdr("4  Protection coordination (12 V) and A2000 PSU headroom")
    lo, nom, hi = ilim_band(rilm)
    shunt_err = 0.01 + 0.001 + 1e-3 / 2.75       # shunt 1 %, INA226 gain 0.1 %, offset 10 uV / 10 mOhm [V SBOS547C]
    trip = 2.75
    print(f"{'level':40} {'threshold':>22} {'time':>22}  action")
    rows = [("design load", f"<= {I_DESIGN:.2f} A", "continuous", "-"),
            ("FPGA warning (INA226 average)", "> 2.60 A", ">= 1 s", "status flag to the Amiga"),
            ("FPGA sustained-overload trip (INA226)", f"> {trip:.2f} A +/-{up(trip * shunt_err * 1e3, 1):.0f} mA",
             ">= 2 s (register)", "X4_PWR_EN low, latch, report"),
            ("eFuse blanking window", f"ILIM..{ISC_GAIN_TYP:.2f} x ILIM", f"<= {up(timer[1] * 1e3, 0.1):.1f} ms "
             f"(>= {down(timer[0] * 1e3, 0.1):.1f})", "none: transient passes"),
            ("eFuse active current limit", f"{down(lo, 0.01):.2f}-{up(hi, 0.01):.2f} A", "after tITIMER",
             "regulates at ILIM; FLT low -> FPGA off"),
            ("eFuse scalable fast trip", f"~{down(ISC_GAIN_TYP * lo, 0.1):.1f}-{up(ISC_GAIN_TYP * hi, 0.1):.1f} A [E]",
             "0.5 us typ", "off, current-limited restart"),
            ("eFuse fixed fast trip", f"{IFT_TYP} A typ", "0.5 us typ", "off"),
            ("eFuse thermal shutdown", "TJ 154 C typ", "-", "latch-off (L): FPGA toggles EN"),
            ("F501 fuse (eFuse failed short)", "5 A time-lag", "IEC/UL curve [K]", "opens"),
            ("A2000 PSU 12 V", "8 A system [V S14]", "-", "PSU's own protection [A]")]
    for r in rows:
        print(f"{r[0]:40} {r[1]:>22} {r[2]:>22}  {r[3]}")
    print(f"\nTrip accuracy: shunt 1 % + INA226 gain 0.1 % + offset 10 uV [V] -> +/-{up(shunt_err * 100, 0.1):.1f} %: "
          f"{down(trip * (1 - shunt_err), 0.01):.2f}-{up(trip * (1 + shunt_err), 0.01):.2f} A, above the 2.5 A design load and below a 3 A contact.")
    print("Where an individual eFuse limits below 2.75 A, its FLT output (current limit after tITIMER) gives the same FPGA shutdown.")
    print("\nA2000 PSU, +12 V (Haynie's example system [V S14], architecture review 8.3): motherboard 0.05, 2 floppies 0.70,")
    print("hard disk running 1.00, 4 other slots 0.16, keyboard/ports 0.10 A = 2.01 A; hard-disk spin-up surge +1.5 A [A]")
    other, spin, limit = 2.01, 1.5, 8.0
    cases = [("X4 at design load", I_DESIGN), ("X4 at ILIM_max (eFuse-limited sustained fault)", up(hi, 0.01)),
             ("X4 at rev A ILIM_max (RILM 750, +1.5 %)", up(ilim_band(750)[2], 0.01))]
    for name, ix in cases:
        tot = other + spin + ix
        print(f"  {name:48} {ix:5.2f} A -> total {up(tot, 0.01):5.2f} A of {limit:.0f} A: "
              f"{'headroom ' + format(down(limit - tot, 0.01), '.2f') + ' A' if tot <= limit else 'EXCEEDS the system limit'}")
    print("  Blanked transient (fast-trip edge, <= 15.3 ms) on top of a spin-up would exceed 8 A briefly: the start-up delay")
    print("  (PM-2, default 5 s) keeps the X4 start away from the disk spin-up; PSU output capacitance covers ms events [K].")
    print("  The unverified '+12 V 3 A' PSU variant (S15) cannot run this card: G-PSU (architecture review 8.6 step 1).")


# ================================================================================================ 5
def section5(rilm):
    hdr("5  Component ratings and requirements (12 V path)")
    lo, nom, hi = ilim_band(rilm)
    ih = up(hi, 0.01)
    print(f"Continuous current any 12 V path element can see with a working eFuse: ILIM_max = {ih:.2f} A")
    print(f"  U501 TPS259470L: IMAX 5.5 A continuous [V]; at {ih:.2f} A: P = I^2 x RON_max = {up(ih ** 2 * RON_MAX, 0.01):.2f} W")
    for name, r_ohm, rating in (("R501 shunt 10 mOhm (2512, 1 W [A part])", 0.010, 1.0),):
        p = ih ** 2 * r_ohm
        print(f"  {name}: {up(p, 0.01):.2f} W at ILIM_max, {up(5.0 ** 2 * r_ohm, 0.01):.2f} W at 5 A (fuse-limited); "
              f"<= 50 % of rating at 70 C [K]: {'ok' if 5.0 ** 2 * r_ohm <= rating * 0.5 else 'check'}")
    fuse_in = ih / 0.75 / 0.9
    print(f"  F501: carry {ih:.2f} A continuously at 75 % loading and 90 % temperature derating [K] -> rating >= "
          f"{up(fuse_in, 0.1):.1f} A: 5 A time-lag (MPN TBV)")
    print("  D501 SMBJ15A [K, TBV]: VRWM 15 V > OVLO_max; VBR >= 16.7 V; VC <= 24.4 V < 28 V (U501 IN abs max) and < 40 V (INA226)")
    print("Requirements for parts whose ratings could not be retrieved (manufacturer specifications to be checked, TBV):")
    print(f"  X4 lead contacts (J502, and the housing mating J10): >= 4 A per contact continuous at <= 30 C rise "
          f"(covers ILIM_max {ih:.2f} A with margin), contact resistance <= 20 mOhm")
    print("  X4 lead wire: 22 AWG (largest for 2.54 mm crimp terminals: KK 254 2759 terminals take 22-30 AWG [Vs RS 172-9178]),")
    print("    <= 15 cm, twisted pair; 22 AWG chassis-wiring capacity is well above 4 A [K]")
    print("  J501 drive-power contacts: >= 5 A per contact (the A2000 harness side TBV); ribbon conductors and IDC contacts: see the")
    print("    ground-return model (tools/analysis/sheet5_ground.py) for the fault-case currents")


# ================================================================================================ 6
def design_string(v_uv, v_ov, r1_range=(365e3, 562e3)):
    """Choose E96 R1/R2/R3 for TI's 3-resistor string (Eq. 10/11). Returns (r1, r2, r3, bands)."""
    vals = sorted({round(m * d, 6) for m in E96 for d in (1e3, 1e4, 1e5, 1e6)})
    best = None
    for r1 in [v for v in vals if r1_range[0] <= v <= r1_range[1]]:
        tot = r1 / (1 - 1.2 / v_uv)
        r3 = min(vals, key=lambda v: abs(v - 1.2 * tot / v_ov))
        r2 = min(vals, key=lambda v: abs(v - (tot - r1 - 1.2 * tot / v_ov)))
        tot_a = r1 + r2 + r3
        err = abs(1.2 * tot_a / (r2 + r3) / v_uv - 1) + abs(1.2 * tot_a / r3 / v_ov - 1)
        if best is None or err < best[0] - 1e-4:
            best = (err, r1, r2, r3)
    _, r1, r2, r3 = best
    return (r1, r2, r3, string_bands(r1, r2, r3))


def string_bands(r1, r2, r3):
    """Worst-case corners: pin threshold limits [V] x resistor tolerance R_TOL [E] on the resistors above/below the tap."""
    def thr(vr, top, bot, sign):
        return vr * (top * (1 + sign * R_TOL) + bot * (1 - sign * R_TOL)) / (bot * (1 - sign * R_TOL))
    return {"uv_min": thr(V_UVLO_R[0], r1, r2 + r3, -1), "uv_max": thr(V_UVLO_R[1], r1, r2 + r3, +1),
            "uvf_min": thr(V_UVLO_F[0], r1, r2 + r3, -1), "ov_min": thr(V_OV_R[0], r1 + r2, r3, -1),
            "ov_max": thr(V_OV_R[1], r1 + r2, r3, +1), "ovf_min": thr(V_OV_F[0], r1 + r2, r3, -1)}


def print_string(label, r1, r2, r3, b):
    print(f"{label}: R1 {r1 / 1e3:g}k (IN -> EN/UVLO; >= 350k per ROC note 2), R2 {r2 / 1e3:g}k, R3 {r3 / 1e3:g}k "
          f"(string {(r1 + r2 + r3) / 1e3:.1f}k)")
    print(f"  UVLO rising {down(b['uv_min'], 0.01):.2f}-{up(b['uv_max'], 0.01):.2f} V, falling >= {down(b['uvf_min'], 0.01):.2f} V;  "
          f"OVLO rising {down(b['ov_min'], 0.01):.2f}-{up(b['ov_max'], 0.01):.2f} V, falling >= {down(b['ovf_min'], 0.01):.2f} V")


# selections used by the schematic (tools/kicad/sheet5.py) and checked by tools/kicad/audit_sheet5.py
UV12, OV12 = 10.5, 14.0          # U501 targets: A2000 12 V +/-5 % inside with margin; below the X4's SMBJ18CA [V S1]
UV5, OV5 = 4.4, 5.75             # U503 targets: A2000 5 V +/-5 % inside; OVLO_max below the 6.5 V absolute maximum of
                                 # U103/U104 VCCB [V S46, S53]


def selections():
    """Return the component values the analysis selects (dict). No printing."""
    rilm = None
    for m in E96[:15]:
        if ilim_band(m * 1000)[0] >= 1.05 * I_DESIGN:
            rilm = m * 1000
    return {"RILM_12": rilm, "CITIMER": 10e-9, "CDVDT_12": CDVDT_12, "C501": C501,
            "STRING_12": design_string(UV12, OV12)[:3], "STRING_5": design_string(UV5, OV5)[:3],
            "RILM_5": 6650.0, "CDVDT_5": 10e-9}


def section6():
    hdr("6  UVLO/OVLO resistor strings (TI 3-resistor string, Eq. 10/11): R1 IN->EN/UVLO, R2 EN/UVLO->OVLO, R3 OVLO->GND")
    print(f"Pin thresholds 1.183-1.223 V rising [V]; resistors +/-{R_TOL * 100:.1f} % [E] at the worst-case corners.")
    r1, r2, r3, b = design_string(UV12, OV12)
    print_string(f"U501 (12 V, targets UVLO {UV12} V / OVLO {OV12} V)", r1, r2, r3, b)
    tot = r1 + r2 + r3
    i_str = V12[0] / tot
    print(f"  string current >= {down(i_str * 1e6, 0.1):.1f} uA = {down(i_str / I_EN_LKG, 1):.0f} x the 0.1 uA pin leakage (TI: >= 20 x) [V]")
    ok = b["uv_max"] < V12[0] and b["ov_min"] > V12[2]
    print(f"  normal 11.4-12.6 V inside the window: UVLO_max {up(b['uv_max'], 0.01):.2f} < 11.4 and OVLO_min "
          f"{down(b['ov_min'], 0.01):.2f} > 12.6: {'ok' if ok else 'FAIL'}; falling UVLO >= {down(b['uvf_min'], 0.01):.2f} V "
          f"rides through a spin-up sag to 11 V [A]")
    print(f"  at 24.4 V (SMBJ15A VC [K]): EN/UVLO {up(24.4 * (r2 + r3) / tot, 0.01):.2f} V, OVLO {up(24.4 * r3 / tot, 0.01):.2f} V "
          f"(abs max {V_PIN_ABS} V)")
    print("  EN/UVLO is also pulled to GND by Q502 (fail-safe enable stage); below 0.45 V the part is shut down and")
    print(f"  latched faults clear [V 7.3.9]. Q502 sinks <= VIN / R1 = {up(V12[2] / r1 * 1e6, 1):.0f} uA.")
    r1, r2, r3, b5 = design_string(UV5, OV5)
    print_string(f"U503 (5 V, targets UVLO {UV5} V / OVLO {OV5} V)", r1, r2, r3, b5)
    tot = r1 + r2 + r3
    print(f"  string current >= {down(V5[0] / tot * 1e6, 0.1):.1f} uA ({down(V5[0] / tot / I_EN_LKG, 1):.0f} x leakage)")
    ok = b5["uv_max"] < V5[0] and b5["ov_min"] > V5[2]
    print(f"  normal 4.75-5.25 V inside the window: UVLO_max {up(b5['uv_max'], 0.01):.2f} < 4.75 and OVLO_min "
          f"{down(b5['ov_min'], 0.01):.2f} > 5.25: {'ok' if ok else 'FAIL'}")
    for vfault, why in ((12.6, "12 V miswire on the 5 V pin"), (21.5, "SMBJ13A VC [K]")):
        print(f"  at {vfault} V ({why}): EN/UVLO {up(vfault * (r2 + r3) / tot, 0.01):.2f} V, OVLO {up(vfault * r3 / tot, 0.01):.2f} V "
              f"(abs max {V_PIN_ABS} V; above 1.5 V the OVLO pin is outside the ROC but holds the part off)")
    return b5


# ================================================================================================ 7
def section7(b5):
    hdr("7  5 V protection chain (S5-6): U503 TPS259470L (OVLO), C_BUS bulk, U504 regulator")
    ov_max = b5["ov_max"]
    print("Slow overvoltage (PSU regulation drift, miswire ramp): U503 switches OFF at OVLO (not a clamp):")
    print(f"  +5V_BUS <= OVLO_max {up(ov_max, 0.01):.2f} V + slope x tOVLO; tOVLO 1.2 us typ [V] (no maximum published; 5 us assumed [A]).")
    slope_max = 2 * 0.42 / 220e-6           # above this input slope the output current exceeds ISC (fast trip) [E]
    print(f"  For input slopes below ~{slope_max / 1e3:.1f} V/ms the output follows within RON: +5V_BUS <= {up(ov_max + slope_max * 5e-6, 0.01):.2f} V")
    print("Fast overvoltage (12 V wire shorted onto the 5 V wire while running): the output current to charge C_BUS exceeds")
    print("ISC = 2 x ILIM (~0.85-1.2 A) almost at once, so the fast trip (500 ns typ [V]) turns U503 off; then OVLO holds it off.")
    print("Charge delivered before turn-off, harness inductance L limits di/dt = dV / L [E]:")
    print(f"{'L (uH)':>7} {'t_off (us)':>10} {'charge (uC)':>11} " + " ".join(f"{'dV@' + str(int(c * 1e6)) + 'uF':>9}" for c in (22e-6, 100e-6, 220e-6)))
    worst220 = 0
    for L in (0.2e-6, 0.5e-6, 1.0e-6):
        for toff in (0.5e-6, 2.0e-6):
            q = 0.5 * (12.6 - 5.0) / L * toff ** 2
            cols = []
            for c in (22e-6, 100e-6, 220e-6):
                dv = q / (c * 0.8)
                cols.append(f"{dv:9.2f}")
                if c == 220e-6:
                    worst220 = max(worst220, dv)
            print(f"{L * 1e6:7.1f} {toff * 1e6:10.1f} {q * 1e6:11.1f} " + " ".join(cols))
    print(f"  With C_BUS >= 220 uF (-20 %) the overshoot is <= {up(worst220, 0.01):.2f} V: +5V_BUS <= "
          f"{up(V5[2] + worst220, 0.01):.2f} V for L >= 0.2 uH and t_off <= 2 us (4 x typical) [E]")
    print("  Consumers of +5V_BUS: SN74LVCH16T245 U103 and SN74LVC8T245 U104, VCCB 5.5 V recommended / 6.5 V absolute [V S46, S53].")
    print("Failure of U503 (pass FET short) removes this protection: a further PSU fault or miswire then reaches +5V_BUS (double")
    print("fault). The regulator below is chosen so that even then the 3.3 V domain (FPGA, SRAM) is not overstressed.\n")
    regs = [("AP7361C-33 (rev A, BOM 14)", 6.0, 6.5, "+/-1 % 25 C [V]", "SOT-223", 1.1, None, "rejected: 6.5 V abs max"),
            ("LP38692MP-3.3", 10.0, 12.0, "+/-5 % over temp [V]", "SOT-223", 68.5, 0.258, "accuracy uses the whole VCCIO window"),
            ("TLV1117-33 (C/I)", 15.0, 16.0, "+/-2 % (I), from VIN 4.75 V only [V]", "SOT-223", None, 1.25, "spec starts at 4.75 V"),
            ("TLV76733DGNR", 16.0, 18.0, "+/-1 % over load/temp [V]", "HVSSOP-8", 60.1, 0.375, "SELECTED")]
    print(f"{'regulator':28} {'VIN op':>7} {'abs':>5}  {'accuracy':36} {'package':9} {'thJA':>5} {'Vdo@0.25A':>9}  note")
    for n, vop, vab, acc, pkg, th, vdo, note in regs:
        ths = f"{th:5.1f}" if th and th > 5 else ("  -  " if th is None else f"{th:4.1f}W")
        vds = f"{vdo:9.3f}" if vdo else "     -   "
        print(f"{n:28} {vop:7.1f} {vab:5.1f}  {acc:36} {pkg:9} {ths:>5} {vds}  {note}")
    print("  LP38692 dropout 0.25 A interpolated from 110 mV (0.1 A) / 1 V (1 A), -40..125 C [V] -> [E]; TLV767 dropout 1.5 V max at")
    print("  1 A (DGN) scaled linearly to 0.25 A [E]; TLV1117 1.25 V max at 0.5 A [V]. TLV767 COUT 1-220 uF [V]: +3V3 holds ~104 uF")
    print("  on sheets 1-4 (netlist) plus sheet-5 parts: the audit limits the total to <= 200 uF.")
    vin_min = V5[0] - 0.3 * RON_MAX - 0.05
    print(f"Headroom: +5V_BUS >= {down(vin_min, 0.01):.2f} V (4.75 V - U503 RON drop - 50 mV copper/connector [A]) -> TLV76733 needs "
          f"<= 3.30 + 0.375 = 3.68 V: margin {down(vin_min - 3.675, 0.01):.2f} V")
    lo5, hi5 = 0.425 / (1 + R_TOL), 0.575 / (1 - R_TOL)
    smin5, styp5, smax5 = sr_band(10e-9)
    c_bus = 220e-6 * 1.2 + 10.4e-6 + 1e-6
    i_inr = c_bus * smax5 * 1e3
    i_load = 0.15 + 0.072
    print(f"U503 start-up: RILM 6.65 kOhm (tested point) -> ILIM {down(lo5, 0.001):.3f}-{up(hi5, 0.001):.3f} A [V + resistor "
          f"tolerance]; CdVdt 10 nF -> SR {down(smin5, 0.01):.2f}-{up(smax5, 0.01):.2f} V/ms [E, 12 V scaling];")
    print(f"  inrush into C_BUS {c_bus * 1e6:.0f} uF <= {up(i_inr, 0.01):.2f} A, plus start-up load 0.15 A [E] and the FPGA's")
    print(f"  start-up peak 0.072 A (Diamond device model) = {up(i_inr + i_load, 0.01):.2f} A < ILIM_min {down(lo5, 0.01):.2f} A: "
          f"{'ok' if i_inr + i_load < lo5 else 'enters current limit (slower ramp, < 2.2 W: no TSD by Figure 8-3)'}")
    print(f"  +5V_BUS rise {down(5.0 / smax5, 1):.0f}-{up(5.0 / smin5, 1):.0f} ms; with the TPS3808 delay (12-28 ms [V S56]) EN_OK is "
          "released well inside the A2000 reset (about 0.7 s, R-36).")
    print(f"  F502 must carry ILIM_max {up(hi5, 0.01):.2f} A: >= {up(hi5 / 0.75 / 0.9, 0.1):.1f} A rating -> 1 A time-lag (MPN TBV).")
    print("MachXO2 supply ramp 0.01-100 V/ms [V S49]: +3V3 follows +5V_BUS (U503 soft start, <= 0.4 V/ms) and the TLV767's own")
    print("500 us soft start (<= ~7 V/ms): inside the window [E].")


# ================================================================================================ 8
def section8():
    hdr("8  Thermal estimates (S5-7) at TA 60 C [A]")
    i33 = 0.25
    for vin, why in ((V5[2], "5.25 V (PSU max)"), (5.97, "OVLO edge")):
        p = (vin - 3.3) * i33
        tj_ja = T_A + p * 60.1
        tj_jb = (T_A + 10) + p * 32.7
        print(f"U504 TLV76733DGNR at {i33} A from {why}: P {up(p, 0.01):.2f} W; TJ = TA + P x 60.1 = {up(tj_ja, 1):.0f} C; "
              f"TJ = T_board (TA + 10 C [A]) + P x psiJB 32.7 = {up(tj_jb, 1):.0f} C (limit 125 C) [V thermal table]")
    print("  PCB requirement: thermal pad soldered to a GND pour with >= 4 vias to an inner plane (JEDEC high-K basis of 60.1 C/W).")
    for i, why in ((I_DESIGN, "design"), (3.36, "ILIM_max")):
        p = i ** 2 * RON_MAX
        print(f"U501 at {i:.2f} A ({why}): P {up(p, 0.01):.2f} W; TJ <= {up(T_A + p * THETA_JA[0], 1):.0f} C (8 vias) / "
              f"{up(T_A + p * THETA_JA[1], 1):.0f} C (no vias)")
    p = 0.42 ** 2 * RON_MAX
    print(f"U503 at 0.42 A: P {up(p, 0.001):.3f} W (negligible)")
    print(f"R501 at 2.5 A: {2.5 ** 2 * 0.01:.3f} W; at 3.36 A: {up(3.36 ** 2 * 0.01, 0.001):.3f} W")
    print("Alternative for U504: a synchronous buck rated >= 17 V input at ~85-90 % [K] would dissipate ~0.1 W, but adds switching")
    print("noise beside the FPGA, SRAM and ribbon, an inductor and layout rules. Not needed at <= 0.67 W; kept as the documented")
    print("fallback if the measured board temperature (M-22) exceeds the estimate.")


# ================================================================================================ 9
def section9():
    hdr("9  Power budget (typical / design maximum)")
    rows12 = [("Radxa X4 incl. NVMe and fan (architecture review 8.3)", 0.90, 2.50, "[Vs S9]/[V S3]"),
              ("U501 IQ(ON) 610 uA max; UVLO/OVLO string; Q502 divider; INA226 VBUS 830 kOhm", 0.0008, 0.0010, "[V]"),
              ("R511 X4-side bleed 4.7 kOhm (detection decay, S5-9)", 0.0026, 0.0027, "[D]")]
    t_typ = sum(r[1] for r in rows12)
    t_max = sum(r[2] for r in rows12)
    print("+12 V (J501 pin 1):")
    for r in rows12:
        print(f"  {r[0]:84} {r[1]:7.4f} {r[2]:7.4f} A  {r[3]}")
    print(f"  {'total':84} {t_typ:7.3f} {up(t_max, 0.001):7.3f} A  (eFuse-limited to ILIM_max 3.36 A in a fault)")
    rows33 = [("FPGA LCMXO2-4000HC: static ICC 8.45 mA typ [V S49 Table 3.10]; core dynamic [E]", 0.020, 0.040),
              ("FPGA I/O switching (Zorro, SRAM, host link) [E]", 0.010, 0.025),
              ("FPGA peak start-up (Diamond Power Calculator device model: VCC 55 mA + VCCIO 17 mA)", 0.0, 0.0),
              ("SRAM IS61WV25616EDBLL-10: ICC dynamic 30 mA max (Com.) [V S61]", 0.010, 0.035),
              ("Oscillator ECS-2520MV 50 MHz: 8 mA max [V S67]", 0.006, 0.008),
              ("Zorro buffers/translators, 3.3 V side (sheets 1, 3) [E]", 0.010, 0.030),
              ("Host-link translators U401-U404 A side, U406, sheet-4 pull-ups [E]", 0.002, 0.006),
              ("LEDs (sheet 6, 5 x 2 mA) [A]", 0.006, 0.010),
              ("Sheet 5: INA226 330 uA, TLV767 IQ 95 uA, pull-ups when low (SDA, SCL, ALERT, FLT, S0) [V/D]", 0.001, 0.004),
              ("JTAG programming of the FPGA (26.8 mA typ, not with full load) [V S49]", 0.0, 0.0)]
    a_typ = sum(r[1] for r in rows33)
    a_max = sum(r[2] for r in rows33)
    print("+3V3 (U504 output):")
    for r in rows33:
        print(f"  {r[0]:84} {r[1]:7.3f} {r[2]:7.3f} A")
    print(f"  {'total':84} {a_typ:7.3f} {up(a_max, 0.001):7.3f} A  (design maximum kept at 0.25 A)")
    rows5 = [("+3V3 through U504 (LDO: input = output current + IQ)", a_typ, 0.25),
             ("+5V_BUS translator side U103/U104 (bus switching) [E]", 0.02, 0.05),
             ("U503 IQ 610 uA, string, R125 (sheet 1) [V]", 0.001, 0.001)]
    print("+5 V (J501 pin 4):")
    for r in rows5:
        print(f"  {r[0]:84} {r[1]:7.3f} {r[2]:7.3f} A")
    t5 = sum(r[1] for r in rows5)
    m5 = sum(r[2] for r in rows5)
    print(f"  {'total':84} {t5:7.3f} {m5:7.3f} A  (U503 ILIM 0.41-0.59 A [E from Table 6.5, 6.65 kOhm])")
    print(f"Power from the A2000: typical {t_typ * 12 + t5 * 5:.1f} W, design maximum {up(t_max * 12.6 + m5 * 5.25, 0.1):.1f} W "
          f"(+12 V at 12.6 V, +5 V at 5.25 V)")
    print("The Diamond Power Calculator was run on the placed 4000HC design (dia_s4i fit_top): in project mode it did not")
    print("load the placed NCD (0 LUTs reported) and the -ncd option is standalone-only. The device-level start-up peak is")
    print("taken from it; the design's dynamic estimate remains [E] and is open as check P-1 (GUI run before manufacture).")


def main():
    rilm = section1()
    timer, sr, band = section2(rilm)
    best = section3(sr, band)
    assert (best[1], best[2]) == (C501, CDVDT_12), f"selected C501/CdVdt differ from the grid optimum {best[1:3]}"
    section4(rilm, timer)
    section5(rilm)
    b5 = section6()
    section7(b5)
    section8()
    section9()


if __name__ == "__main__":
    main()
