# SPDX-License-Identifier: MIT
"""S4-6 isolation analysis (sheet 4, revision A2).

The X4's K4 key switches the RP2040's I/O supply P3V_RP (IOVDD) off while the header 3.3 V (P3V3_S, on the carrier
X4_3V3_REF) stays up. U402 drives every carrier -> RP2040 signal (IRQ_N, ATTN, MISO, TDO) from X4_3V3_REF, so its
/OE must disable it before IOVDD has fallen far enough for an output to exceed IOVDD + 0.3 V (RP2040 VIH maximum)
or IOVDD + 0.5 V (absolute maximum) [V S65 Tables 622, 625].

usage: python -I tools/analysis/k4_transient.py

Report: docs/stage2/sheet4-s46-isolation.md. Tags: [V Sxx] datasheet value, [E] estimate, [A] assumption.
Owner rounding rule: maxima and requirements round up; margins, slacks and minima round down.

Sections:
  1  IOVDD discharge-rate bound after K4 (capacitance derating, maximum load)
  2  revision A (history): RP_VIO held above IOVDD by C404
  3  revision A1 rerun with worst-case parameters (TLV7021, 0.930 threshold)
  4  the R424 path (revision A1) and the GP24 <= IOVDD invariant without it
  5  revision A2 (TLV3201 driving a BSS138 pair, 0.940 threshold): latency budget and safe discharge rate
  6  options for more margin: threshold, comparator, lower U402 B supply
  7  RP2040 reset and brownout: GP24 transitions
  8  GP24 current
"""
import math

# ---------------------------------------------------------------- common parameters
VS_MIN, VS_MAX = 3.135, 3.465        # X4_3V3_REF = P3V3_S, +-5 % [A]
VCCA_MIN = 3.135                     # carrier +3V3 (U402 VCCA, R429 supply), -5 % [A]
LIM_VIH, LIM_ABS = 0.30, 0.50        # RP2040: VIH max IOVDD + 0.3 V, pin abs. max IOVDD + 0.5 V [V S65]
R_TOL = 0.01 + 100e-6 * 65           # 1 % resistors, 100 ppm/K, 25 -> -40 / +85 C: 1.65 % each, not tracking [A]
Q32_DROP = 0.035                     # X4 P3V3_S -> P3V_RP switch Q32 at 176 mA x 0.2 ohm [E]
PAD_R = 85.0                         # RP2040 pad: VOH >= 2.62 V at 8 mA (IOVDD 3.3 V) implies <= 85 ohm [V S65 -> E]
VF = 0.6                             # ESD-diode forward drop into an unpowered rail [E]


def up(x, q):
    return math.ceil(x / q - 1e-9) * q


def down(x, q):
    return math.floor(x / q + 1e-9) * q


def k_range(r_top, r_bot, tol=R_TOL):
    """Divider ratio r_bot / (r_top + r_bot): nominal, minimum, maximum with non-tracking tolerances."""
    nom = r_bot / (r_top + r_bot)
    kmin = r_bot * (1 - tol) / (r_bot * (1 - tol) + r_top * (1 + tol))
    kmax = r_bot * (1 + tol) / (r_bot * (1 + tol) + r_top * (1 - tol))
    return nom, kmin, kmax


# ---------------------------------------------------------------- 1. discharge-rate bound
C206, C_SMALL, N_SMALL = 10e-6, 0.1e-6, 5      # C206 10 uF 6.3 V; C207, C209-C212 0.1 uF 16 V [V S1 sh.21]
C206_BIAS, C206_TOL, C206_TEMP, C206_AGE = 0.25, 0.80, 0.85, 0.95   # retained at 3.3 V DC (size not shown: 0402
                                                                     # X5R worst case), -20 %, X5R -15 %, aging [E]
CS_BIAS, CS_TOL, CS_TEMP = 0.80, 0.80, 0.85                          # 0.1 uF 16 V X7R [E]
I_LOAD = {"IOVDD, all GPIO (IIOVDD_MAX)": 0.050,                     # [V S65]
          "VREG_VIN (VREG rated output)": 0.100,                     # 100 mA max [V S65]
          "SPI flash U24 W25Q16JV": 0.025,                           # on P3V_RP [V S1 sh.21]; current [E]
          "ADC_AVDD": 0.001}                                         # [E]
C_NOM = 10.5e-6                                                      # undergraded sum (revision A1 model)


def slope_bound():
    c_eff = C206 * C206_BIAS * C206_TOL * C206_TEMP * C206_AGE + N_SMALL * C_SMALL * CS_BIAS * CS_TOL * CS_TEMP
    i_max = sum(I_LOAD.values())
    return c_eff, i_max, i_max / c_eff


# ---------------------------------------------------------------- 2. revision A (history, unchanged model)
V_BO, DT = 1.62, 0.1e-6              # RP2040 stops driving GP24 near the VREG_VIN minimum 1.63 V [V S65 -> E]


def iovdd_trace(i0, c=C_NOM, t_end=60e-3):
    v, t, out = 3.3 - 0.01, 0.0, []
    while t < t_end and v > 0.02:
        i = i0 if v > V_BO else v / (V_BO / i0)
        v -= i / c * DT
        t += DT
        out.append((t, v))
    return out


def option_a(trace):
    """Revision A: U402 VCCB = RP_VIO = GP24 via R416 47 R; C404 100 nF; R417 100 k; pad 50 R [E]."""
    r_track, c404, r417 = 50 + 47, 100e-9, 100e3
    vio, worst, t03, t05 = 3.3 - 0.02, -9.0, 0.0, 0.0
    for t, v in trace:
        if v > V_BO:
            vio += ((v - vio) / (r_track * c404) - vio / (r417 * c404)) * DT
        else:
            vio -= vio / (r417 * c404) * DT
            vio = min(vio, v + VF)
        d = vio - v
        worst = max(worst, d)
        t03 += DT if d > 0.3 else 0.0
        t05 += DT if d > 0.5 - 1e-9 else 0.0
    return worst, t03, t05


# ---------------------------------------------------------------- comparator stages
class Stage:
    """A comparator-gated /OE: trip at k x VS minus offsets; output switches after the input passes the trip point
    by OD, plus a fixed latency t_fixed. guaranteed: every term of t_fixed is a datasheet maximum or a stated
    estimate on one; otherwise the figure is typical-based."""

    def __init__(self, name, r_top, r_bot, offs, od, t_fixed, guaranteed, v_out=None):
        self.name, self.offs, self.od, self.t_fixed, self.guaranteed = name, offs, od, t_fixed, guaranteed
        self.k, self.kmin, self.kmax = k_range(r_top, r_bot)
        self.r_top, self.r_bot = r_top, r_bot
        self.v_out = v_out           # None: U402 outputs at X4_3V3_REF; else a fixed B supply maximum (V)

    def static_excursion(self, vs):
        """Output high level above IOVDD at the latest trip point (lowest k, offsets against), before latency."""
        vout = vs if self.v_out is None else self.v_out
        return vout - (self.kmin * vs - self.offs - self.od)

    def worst_static(self):
        return max(self.static_excursion(vs) for vs in (VS_MIN, VS_MAX))

    def excursion(self, slope):
        return self.worst_static() + slope * self.t_fixed

    def s_max(self, limit):
        return (limit - self.worst_static()) / self.t_fixed

    def margin_fall(self, offs_no_hys):
        """Normal operation: lowest GP24 above the highest falling trip point (no hysteresis credit)."""
        return min(vs - Q32_DROP - gp24_pad_drop() - (self.kmax * vs + offs_no_hys) for vs in (VS_MIN, VS_MAX))


def gp24_pad_drop():
    return VS_MAX / (R430 * (1 - R_TOL)) * PAD_R + 100e-9 * PAD_R    # R430 and the Q402 gate leakage


R430 = 100e3

# ---- revision A1: TLV7021 open drain [V S68]: VIO <= 8 mV, VHYS <= 14 mV (-40..125 C); tPLH 310 ns TYPICAL at
# VOD 100 mV, RP 2.5 k, CL 15 pF, 25 C (no maximum). Pull-up R429 10 k into the /OE node. Typical-based only.
A1_OFFS = 0.008 + 0.014
A1_C_OE = 5e-12 + 4.5e-12 + 5e-12                      # TLV7021 output [E] + U402 Ci <= 4.5 pF [V S66] + trace [E]
A1_T_RC = 10e3 * (1 + R_TOL) * A1_C_OE * math.log(VCCA_MIN / (VCCA_MIN - 2.0))
A1_T_TYP = 0.31e-6 + A1_T_RC + 6.2e-9                  # tPLH typ + RC + U402 OE->B tPHZ <= 6.2 ns [V S66]
A1_T_BUDGET = 2e-6                                     # the revision A1 document's "2 us budget"

# ---- revision A2: TLV3201 push-pull [V S70] driving Q401 (BSS138, top) in series with Q402 (BSS138, gate from
# GP24 through R431); R429 1 k pull-up to VCCA on /OE.
TLV3201_TPD = 55e-9            # max, VOD 20 mV, CL 15 pF, -40..125 C, at VCC 2.7 V and 5 V [V S70]
TLV3201_OD = 0.020             # the overdrive at which that maximum is specified [V S70]
TLV3201_VIO = 0.004            # max, -40..125 C [V S70]
TLV3201_CMRR = 0.0026          # CMRR >= 56 dB (2.7 V) / 60 dB (5 V) over the full CM range; |VCM - VCC/2| <= 1.6 V
TLV3201_HYS = 0.010            # 1.2 mV typical, no limit given [V S70]; 10 mV assumed [E]
TLV3201_ISINK = 10e-3          # short-circuit sink >= 13 mA at 2.7 V, 25 C [V S70]; derated for temperature [E]
BSS_CISS, BSS_COSS, BSS_CRSS = 50e-12, 25e-12, 8e-12   # maxima at VDS 10 V [V S71, guaranteed by design]
C_GATE = BSS_CISS + 2 * BSS_CRSS                       # gate with the drain near 0 V (Crss rises at low VDS) [E]
C_OE = 2 * BSS_COSS + 4.5e-12 + 5e-12                  # Q401 Coss doubled for low VDS [E], U402 Ci [V S66], trace [E]
C_IN = 10e-12                                          # TLV3201 2 + 4 pF typ [V S70] + trace [E]
C_PAD = 50e-12                                         # GP24 pad, header, ribbon [E] (R426, R431 isolate the rest)
R426, R429, R431 = 1e3, 1e3, 1e3

A2_TERMS = {
    "GP24 pad follows IOVDD (85 ohm x 50 pF)": PAD_R * C_PAD,
    "R426 x comparator input": R426 * (1 + R_TOL) * C_IN,
    "TLV3201 tPD (max, VOD 20 mV, CL 15 pF)": TLV3201_TPD,
    "Q401 gate charge at the minimum sink current": C_GATE * VS_MAX / TLV3201_ISINK,
    "R429 x /OE node to VIH 2.0 V": R429 * (1 + R_TOL) * C_OE * math.log(VCCA_MIN / (VCCA_MIN - 2.0)),
    "U402 /OE -> B disable (tPHZ, tPLZ)": 6.2e-9,                       # [V S66]
}
A2_T = up(sum(A2_TERMS.values()), 10e-9)
A2_OFFS = TLV3201_VIO + TLV3201_CMRR + TLV3201_HYS


def stages():
    return {
        "A1": Stage("rev A1: TLV7021, 0.930 (typical delay)", 7.5, 100.0, A1_OFFS, 0.020, A1_T_TYP, False),
        "A2": Stage("rev A2: TLV3201 + BSS138, 0.940", 6.34, 100.0, A2_OFFS, TLV3201_OD, A2_T, True),
    }


def option_rows():
    """Section 6: the same worst-case arithmetic for each lever."""
    rows = []
    for name, rt, guaranteed, offs, t, vout in (
            ("TLV7021, 0.930 (rev A1)", 7.5, False, A1_OFFS, A1_T_TYP, None),
            ("TLV7021, 0.950", 5.23, False, A1_OFFS, A1_T_TYP, None),
            ("TLV3201 + BSS138, 0.930", 7.5, True, A2_OFFS, A2_T, None),
            ("TLV3201 + BSS138, 0.940 (rev A2)", 6.34, True, A2_OFFS, A2_T, None),
            ("TLV3201 + BSS138, 0.950", 5.23, True, A2_OFFS, A2_T, None),
            ("TLV3201 + BSS138, 0.960", 4.12, True, A2_OFFS, A2_T, None),
            ("TLV3201 + BSS138, 0.930, U402 B at 2.5 V +-2 %", 7.5, True, A2_OFFS, A2_T, 2.55),
            ("TLV7021, 0.930, U402 B at 2.5 V +-2 %", 7.5, False, A1_OFFS, A1_T_TYP, 2.55)):
        s = Stage(name, rt, 100.0, offs, 0.020, t, guaranteed, v_out=vout)
        offs_nh = offs - (TLV3201_HYS if offs == A2_OFFS else 0.014)
        rows.append((s, s.margin_fall(offs_nh)))
    return rows


def ramp_check(stage, slope, vs=VS_MAX):
    """Time-stepped cross-check of the closed form: IOVDD ramps down at `slope` from VS - Q32 drop; the comparator
    input follows through the R426 input RC; the output switches t_fixed after the input passes trip - OD."""
    dt = 1e-9
    trip = stage.kmin * vs - stage.offs
    v_io = vs - Q32_DROP
    v_in, t, t_sw = v_io, 0.0, None
    tau = R426 * (1 + R_TOL) * C_IN
    worst = -9.0
    while True:
        v_io -= slope * dt
        v_in += (v_io - v_in) * dt / tau
        t += dt
        if t_sw is None and v_in < trip - stage.od:
            t_sw = t + stage.t_fixed - tau          # t_fixed already contains the input RC; avoid counting it twice
        vout = vs if stage.v_out is None else stage.v_out
        worst = max(worst, vout - v_io)
        if t_sw is not None and t >= t_sw:
            return worst


# ---------------------------------------------------------------- 4. R424 (revision A1)
R424 = 10e3


def r424_path():
    """With R424 (GP24 -> GP22) and U402 driving IRQ_N high at X4_3V3_REF."""
    out = {}
    # pad driving GP24: R424 current flows into the pad, lifting GP24 above IOVDD by I x R_pad, and into IOVDD.
    # At the rev A1 trip point IRQ_N (at VS) is above GP24 by at most (1 - kmin) x VS + offsets.
    a1 = stages()["A1"]
    i_trip = max(vs - (a1.kmin * vs - a1.offs) for vs in (VS_MIN, VS_MAX)) / R424
    out["GP24 lift at the trip point (mV)"] = i_trip * PAD_R * 1e3
    out["current into IOVDD at the trip point (uA)"] = i_trip * 1e6
    out["current into IOVDD as IOVDD -> 0 (mA)"] = (VS_MAX - VF) / R424 * 1e3
    # pad released (brownout or reset) while U402 still drives IRQ_N high
    rpd = [1 / (1 / R430 + 1 / r) for r in (80e3, 50e3)]
    out["GP24 held by the R424/R430/RPD divider (V)"] = tuple(VS_MAX * r / (r + R424) for r in rpd)
    return out


# ---------------------------------------------------------------- 7. reset and brownout
def reset_release():
    rpd = [1 / (1 / R430 + 1 / r) for r in (80e3, 50e3)]      # R430 || RP2040 pull-down 50-80 k [V S65]
    c_node = C_PAD + C_IN + C_GATE                           # all of it at microsecond time scales
    taus = sorted(r * c_node for r in rpd)
    a2 = stages()["A2"]
    t_trip = max(t * math.log(1 / a2.kmin) for t in taus)    # from IOVDD to kmin x VS (IOVDD = VS, worst)
    t_q402 = max(t * math.log(VS_MAX / 0.5) for t in taus)   # to below VGS(th) min 0.5 V [V S71]
    return taus, t_trip, t_q402


# ---------------------------------------------------------------- 8. GP24 current
def gp24_current():
    static = VS_MAX / (R430 * (1 - R_TOL)) + 100e-9 + 5e-9    # R430, Q402 IGSS <= 100 nA [V S71], IB <= 5 nA [V S70]
    peak = VS_MAX / (R426 * (1 - R_TOL)) + VS_MAX / (R431 * (1 - R_TOL))
    return static, peak, R426 * C_IN, R431 * C_GATE


def main():
    print("1. IOVDD discharge rate after K4 (Q32 assumed to open instantly)")
    c_eff, i_max, s = slope_bound()
    for k, v in I_LOAD.items():
        print(f"   load {k:32s} {v*1e3:5.0f} mA")
    print(f"   C_eff min {c_eff*1e6:.3f} uF (C206 x {C206_BIAS*C206_TOL*C206_TEMP*C206_AGE:.3f}, 0.1 uF parts x "
          f"{CS_BIAS*CS_TOL*CS_TEMP:.3f}); I max {i_max*1e3:.0f} mA")
    print(f"   worst-case slope {s/1e3:.1f} V/ms -> bound {up(s/1e3, 1):.0f} V/ms [E]; "
          f"undergraded 10.5 uF at 5-100 mA: {0.005/C_NOM/1e3:.2f}-{0.1/C_NOM/1e3:.2f} V/ms")

    print("\n2. Revision A (history): RP_VIO - IOVDD, 10.5 uF, X4 load 5/25/100 mA")
    for i0 in (5e-3, 25e-3, 100e-3):
        a = option_a(iovdd_trace(i0))
        print(f"   {i0*1e3:4.0f} mA: peak {a[0]:.3f} V, above +0.3 V {a[1]*1e3:.2f} ms, above +0.5 V {a[2]*1e3:.2f} ms")

    st = stages()
    a1, a2 = st["A1"], st["A2"]
    print("\n3. Revision A1 rerun (TLV7021, R427/R428 7.5 k / 100 k)")
    print(f"   k {a1.k:.4f}, with 1.65 % resistors {a1.kmin:.5f}-{a1.kmax:.5f}; offset + hysteresis {a1.offs*1e3:.0f} mV")
    print(f"   static excursion at the latest trip, VS max, 20 mV overdrive: {a1.worst_static():.3f} V "
          f"(VIH limit 0.300 V leaves {down(LIM_VIH - a1.worst_static(), 0.001)*1e3:.0f} mV)")
    print(f"   latency: typical {a1.t_fixed*1e6:.2f} us (tPLH 310 ns TYPICAL + R429 10 k RC {A1_T_RC*1e9:.0f} ns + "
          f"tPHZ); no maximum exists")
    for lim, nm in ((LIM_VIH, "VIH max"), (LIM_ABS, "abs max")):
        print(f"   slope limit for {nm}: typical-based {down(a1.s_max(lim)/1e3, 1):.0f} V/ms; with the 2 us budget "
              f"{down((lim - a1.worst_static()) / A1_T_BUDGET / 1e3, 1):.0f} V/ms")
    print(f"   at {up(s/1e3, 1):.0f} V/ms: {a1.excursion(up(s, 1e3)):.3f} V typical, "
          f"{a1.worst_static() + up(s, 1e3) * A1_T_BUDGET:.3f} V with the 2 us budget "
          "-> the rev A1 claim 'any discharge rate' does not hold")

    print("\n4. R424 (rev A1): GP24 -> R424 10 k -> GP22, U402 driving IRQ_N high")
    for k, v in r424_path().items():
        print(f"   {k}: " + (", ".join(f"{x:.2f}" for x in v) if isinstance(v, tuple) else f"{v:.2f}"))
    print("   without R424 the GP24 node has no source on the carrier: R426 -> comparator input (<= 5 nA), R430 to GND,")
    print("   R431 -> Q402 gate (<= 100 nA): GP24 <= IOVDD at all times")
    iovdd_min = VS_MIN - Q32_DROP
    print(f"   GP22 (IRQ_N) idle with the RP2040 pull-up (50-80 k [V S65]) instead: U402 Hi-Z (IOZ <= 5 uA) or isolated "
          f"(Ioff <= 1 uA) [V S66] -> >= {down(iovdd_min - 5e-6 * 80e3, 0.01):.2f} V against VIH 2.0 V; "
          f"while U402 drives low it sinks <= {up(VS_MAX / 50e3 * 1e6, 1):.0f} uA")

    print("\n5. Revision A2 (TLV3201 + Q401/Q402 BSS138, R427/R428 6.34 k / 100 k)")
    print(f"   k {a2.k:.5f}, with 1.65 % resistors {a2.kmin:.5f}-{a2.kmax:.5f}; offset {TLV3201_VIO*1e3:.1f} + CMRR "
          f"{TLV3201_CMRR*1e3:.1f} + hysteresis {TLV3201_HYS*1e3:.0f} mV [E] = {a2.offs*1e3:.1f} mV")
    print("   trip band (GP24 falling): "
          + ", ".join(f"VS {vs:.3f}: {a2.kmin*vs - a2.offs:.3f}-{a2.kmax*vs + TLV3201_VIO + TLV3201_CMRR:.3f} V"
                      for vs in (VS_MIN, 3.3, VS_MAX)))
    print("   latency budget (from the input passing trip - 20 mV):")
    for k, v in A2_TERMS.items():
        print(f"     {k:44s} {v*1e9:6.1f} ns")
    print(f"     {'total, rounded up':44s} {A2_T*1e9:6.0f} ns")
    print(f"   static excursion {a2.worst_static():.4f} V (VS max); normal-operation margin "
          f"{down(a2.margin_fall(TLV3201_VIO + TLV3201_CMRR), 0.001):.3f} V (VS min, Q32 {Q32_DROP*1e3:.0f} mV)")
    for lim, nm in ((LIM_VIH, "VIH max"), (LIM_ABS, "abs max")):
        print(f"   safe slope for {nm}: <= {down(a2.s_max(lim)/1e3, 1):.0f} V/ms "
              f"({down(a2.s_max(lim)/up(s, 1e3), 0.1):.1f} x the {up(s/1e3, 1):.0f} V/ms bound)")
    print("   excursion vs slope (closed form | time-stepped check):")
    for sl in (1e3, 10e3, 50e3, 100e3, 200e3, 300e3, 500e3, 1000e3, 1500e3, 2000e3):
        print(f"     {sl/1e3:5.0f} V/ms: {a2.excursion(sl):.3f} V | {ramp_check(a2, sl):.3f} V"
              + ("   > VIH max" if a2.excursion(sl) > LIM_VIH else "")
              + ("   > ABS MAX" if a2.excursion(sl) > LIM_ABS else ""))
    tau_oe = R429 * (1 + R_TOL) * C_OE
    print(f"   /OE rising edge through R429: tau <= {tau_oe*1e9:.0f} ns, {tau_oe/(VCCA_MIN-1.5)*1e9:.0f} ns/V at 1.5 V "
          f"(SCES693I recommends <= 5 ns/V on inputs [V S66]; the budget runs to VIH 2.0 V, so any enable chatter "
          f"below it is inside the {A2_T*1e9:.0f} ns)")
    print("   sensitivity: safe slope (VIH max) if the fixed latency were larger:")
    for mult in (1, 2, 5):
        print(f"     x{mult}: {down((LIM_VIH - a2.worst_static()) / (a2.t_fixed * mult) / 1e3, 1):.0f} V/ms")

    print("\n6. Options (worst case: VS 3.135-3.465 V, 1.65 % resistors; 'typ' = typical delay, no guaranteed bound)")
    print(f"   {'option':46s} {'static':>7s} {'VIH slope':>10s} {'abs slope':>10s} {'margin':>7s} basis")
    for s6, mg in option_rows():
        print(f"   {s6.name:46s} {s6.worst_static():6.3f}V {down(s6.s_max(LIM_VIH)/1e3, 1):7.0f}V/ms "
              f"{down(s6.s_max(LIM_ABS)/1e3, 1):7.0f}V/ms {down(mg, 0.001):6.3f}V "
              + ("guaranteed" if s6.guaranteed else "typ"))

    print("\n7. RP2040 reset / brownout")
    taus, t_trip, t_q402 = reset_release()
    print(f"   reset with IOVDD up: GP24 released, tau {taus[0]*1e6:.2f}-{taus[1]*1e6:.2f} us; below the trip point "
          f"after <= {up(t_trip*1e6, 0.01):.2f} us (outputs <= VS <= IOVDD + {Q32_DROP:.3f} V meanwhile); "
          f"Q402 off after <= {up(t_q402*1e6, 0.1):.1f} us")
    print(f"   K4 brownout: GP24 is driven (= IOVDD) until the VREG input falls below 1.63 V [V S65], far below the "
          f"trip point ({a2.kmin*VS_MIN - a2.offs:.2f} V min); afterwards it is released to R430 || pull-down")

    print("\n8. GP24 current (rev A2)")
    st_i, pk, t1, t2 = gp24_current()
    print(f"   static <= {up(st_i*1e6, 1):.0f} uA; on each GP24 edge <= {up(pk*1e3, 0.1):.1f} mA peak, decaying with "
          f"{t1*1e9:.0f} ns (R426) and {t2*1e9:.0f} ns (R431); against IIOVDD_MAX 50 mA and the 8 mA drive setting")


if __name__ == "__main__":
    main()
