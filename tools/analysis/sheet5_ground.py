# SPDX-License-Identifier: MIT
"""Sheet 5 ground-return model (owner review of PR #10, S5-8 conditions 1-6).

A DC resistive network of every path the X4's supply return (and the carrier's own return) can take back to the
A2000 power supply:

    X  (X4 ground) --J10 lead--------------+
    X  --ribbon, 8 GND conductors (J401)---+-- CX (carrier plane, X4 area) --plane-- CJ (J501) --drive lead GND-- P (PSU)
    X  --4 standoffs (only if bonded, TBV)-+         \\--plane-- CZ (Zorro edge) --18 GND fingers-- M (slot) --MB-- P
    X  --external: HDMI/USB shield, mains earth (only in the cases that say so)----------------------------------- P

Loads: the X4 return I_X4 enters at X, the carrier logic return (0.3 A) at CZ, and the part of the motherboard's own
return that passes the slot region (I_MB, [A]) at M. Every resistance has a minimum and a maximum; each case is solved
at all 2^7 corners of the seven resistance groups and the extreme currents and offsets are reported. Values are
estimates [E] built on [K] wire and contact data and stated assumptions [A]; manufacturer ratings for the ribbon, the
IDC contacts and the 2.54 mm crimp contacts could not be retrieved and are stated as REQUIREMENTS for the parts.

The offset that the S4-6 analysis allows is dG = V(X) - V(CX) <= 50 mV, costing 0.06 x dG of GP24 margin
(docs/stage2/sheet4-s46-isolation.md section 9).

usage: python tools/analysis/sheet5_ground.py
"""
from __future__ import annotations

import itertools
import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def up(x, step):
    return math.ceil(x / step - 1e-9) * step


def down(x, step):
    return math.floor(x / step + 1e-9) * step


MOHM = 1e-3
# ------------------------------------------------------------------------------------------------ resistances (ohm)
# wire: 22 AWG 52.9 mOhm/m, 18 AWG 20.9 mOhm/m, 28 AWG solid 212.9 mOhm/m, stranded tinned ~230-240 mOhm/m [K]
J10_WIRE = (0.10 * 52.9 * MOHM, 0.15 * 52.9 * MOHM)          # 22 AWG, 10-15 cm [A] (S5-8 harness rule: <= 15 cm)
J10_CONTACT_X4 = (2 * MOHM, 20 * MOHM)                        # 2.54 mm crimp on the X4's J10 post; 20 mOhm max per a
                                                              # distributor listing for Molex 08-50-0114 [Vs], min [K]
J10_CONTACT_C = (1 * MOHM, 10 * MOHM)                         # carrier-end connector J502 [K]
RIB_COND = (0.08 * 0.213, 0.15 * 0.240)                       # 28 AWG, 8-15 cm (D-07: <= 15 cm) [K, A]
RIB_ENDS = (2 * 6 * MOHM, 2 * 35 * MOHM)                      # two ends: IDC socket on header pin + IDC termination [K]
STANDOFF = (2 * MOHM, 20 * MOHM)                              # per M2.5 standoff: two screw/pad joints + body [K]
STANDOFF_SPEC = (2 * MOHM, 5 * MOHM)                          # the same with the joint specified and measured (M-21)
J501_PATH = (1 * MOHM + 0.30 * 20.9 * MOHM + 1 * MOHM,        # per GND contact: socket/pin + 18 AWG 0.3-0.6 m + PSU end
             10 * MOHM + 0.60 * 20.9 * MOHM + 5 * MOHM)       # [K, A]
ZFINGER = (5 * MOHM, 30 * MOHM)                               # per Zorro edge contact [K]
MB = (3 * MOHM, 18 * MOHM)                                    # slot -> PSU connector plane + PSU harness to motherboard [A]
PLANE = (0.5 * MOHM, 4 * MOHM)                                # carrier plane segment between connector areas [E]
R_EXT = (0.1, 1.0)                                            # X4 -> mains earth -> PSU (HDMI monitor etc.) [A]
N_RIB_GND, N_ZGND, N_STANDOFF, N_J501_GND = 8, 18, 4, 2      # J401 GND pins 6, 9, 14, 20, 25, 30, 34, 39; J101 GND pins
                                                              # 1-4, 13, 25, 37, 49, 61, 73, 85, 87-91, 99, 100 (netlist)
IMBAL_RIB, IMBAL_Z, IMBAL_J501 = 1.3, 1.5, 1.2                # share imbalance between parallel contacts [A]

I_CARRIER = 0.30                                              # carrier logic return, design maximum (sheet-5 budget)
I_MB = (0.0, 3.0)                                             # motherboard return passing the slot region [A]

# ratings and limits used for the checks
REQ_RIB = 1.0          # requirement per ribbon conductor and IDC contact (A, continuous) [requirement; part TBV]
REQ_J10 = 4.0          # requirement per X4-lead contact (sheet5_power.py section 5)
ZF_RATING = 2.0        # per Zorro contact: Haynie allows 4 A per slot on +5 V pins 5 and 6 [V S52] -> >= 2 A [D]
REQ_J501 = 6.0         # requirement per drive-power contact [requirement; harness side TBV]
DG_LIMIT = 0.050       # S4-6 assumption for the X4 - carrier ground offset


def solve(branches, injections, nodes):
    """Nodal analysis. branches: list of (a, b, R) with node names ('P' is the 0 V reference); injections: {node: A}
    (current leaving the node towards P through the network). Returns {node: V} or None if a node is floating."""
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    g = [[0.0] * n for _ in range(n)]
    rhs = [0.0] * n
    for a, b, r in branches:
        y = 1.0 / r
        for u, v in ((a, b), (b, a)):
            if u != "P":
                g[idx[u]][idx[u]] += y
                if v != "P":
                    g[idx[u]][idx[v]] -= y
    for node, i_in in injections.items():
        rhs[idx[node]] += i_in
    # Gaussian elimination with partial pivoting
    m = [row[:] + [rhs[i]] for i, row in enumerate(g)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[piv][c]) < 1e-12:
            return None
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c and m[r][c] != 0.0:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return {nodes[i]: m[i][n] / m[i][i] for i in range(n)}


def network(corner, case):
    """corner: dict group -> 0 (min) / 1 (max). case: dict of options. Returns (branches, labels)."""
    k = corner
    r_j10 = J10_WIRE[k["j10"]] + J10_CONTACT_X4[k["j10"]] + J10_CONTACT_C[k["j10"]]
    r_rib1 = RIB_COND[k["rib"]] + RIB_ENDS[k["rib"]]
    br = []
    if case.get("j10_r") is not None:
        r_j10 = case["j10_r"]
    if not case.get("j10_open"):
        br.append(("X", "CX", r_j10, "j10"))
    if not case.get("ribbon_off"):
        n_rib = case.get("rib_n", N_RIB_GND)
        br.append(("X", "CX", r_rib1 / n_rib, "rib"))
    if case.get("standoffs"):
        so = STANDOFF_SPEC if case.get("so_spec") else STANDOFF
        br.append(("X", "CX", so[k["so"]] / N_STANDOFF, "so"))
    if case.get("ext"):
        br.append(("X", "P", R_EXT[k["ext"]], "ext"))
    pl = PLANE[k["pl"]]
    br += [("CX", "CJ", pl, "pl1"), ("CX", "CZ", pl, "pl2"), ("CJ", "CZ", pl, "pl3")]
    n_j501 = case.get("j501_n", N_J501_GND) * case.get("j501_connectors", 1)
    if n_j501 > 0:
        br.append(("CJ", "P", J501_PATH[k["j501"]] / n_j501, "j501"))
    br.append(("CZ", "M", ZFINGER[k["z"]] / N_ZGND, "z"))
    br.append(("M", "P", MB[k["mb"]], "mb"))
    return br


GROUPS = ["j10", "rib", "so", "j501", "z", "mb", "pl"]


def run_case(name, case, i_x4, i_mb_vals=I_MB):
    res = {"j10": 0, "rib": 0, "so": 0, "ext": 0, "j501": 0, "z": 0, "dg": 0, "dz": 0, "loop": 0.0,
           "share_ded": [1, 0], "share_rib": [1, 0], "share_j501": [1, 0], "floating": False}
    corners = list(itertools.product((0, 1), repeat=len(GROUPS)))
    for bits in corners:
        k = dict(zip(GROUPS, bits))
        k["ext"] = 0
        for ext_bit in ((0, 1) if case.get("ext") else (0,)):
            k["ext"] = ext_bit
            for i_mb in i_mb_vals:
                br = network(k, case)
                nodes = ["X", "CX", "CJ", "CZ", "M"]
                v = solve([(a, b, r) for a, b, r, _ in br], {"X": i_x4, "CZ": I_CARRIER, "M": i_mb}, nodes)
                if v is None:
                    res["floating"] = True
                    continue
                vv = dict(v, P=0.0)
                cur = {}
                for a, b, r, lab in br:
                    cur[lab] = cur.get(lab, 0.0) + (vv[a] - vv[b]) / r
                for lab in ("j10", "rib", "so", "ext", "j501", "z"):
                    res[lab] = max(res[lab], abs(cur.get(lab, 0.0)))
                res["dg"] = max(res["dg"], abs(vv["X"] - vv["CX"]))
                res["dz"] = max(res["dz"], abs(vv["CZ"] - vv["M"]))
                if i_x4 > 0:
                    ded = (cur.get("j10", 0) + cur.get("so", 0)) / i_x4
                    rib = cur.get("rib", 0) / i_x4
                    res["share_ded"] = [min(res["share_ded"][0], ded), max(res["share_ded"][1], ded)]
                    res["share_rib"] = [min(res["share_rib"][0], rib), max(res["share_rib"][1], rib)]
                if i_mb == 0:                     # share of the card's own return carried by J501
                    tot = cur.get("j501", 0) + cur.get("z", 0)
                    if tot > 0:
                        sj = cur.get("j501", 0) / tot
                        res["share_j501"] = [min(res["share_j501"][0], sj), max(res["share_j501"][1], sj)]
                else:                             # motherboard current diverted through the card
                    res["loop"] = max(res["loop"], -cur.get("z", 0.0))
    return res


CASES = [
    ("N1 normal, standoffs not bonded (default until M-21)", {}, 2.5),
    ("N2 normal, standoffs bonded (joints 2-20 mOhm each)", {"standoffs": True}, 2.5),
    ("N2s normal, standoffs bonded, joints specified <= 5 mOhm (M-21)", {"standoffs": True, "so_spec": True}, 2.5),
    ("N3 normal, ILIM_max sustained (eFuse-limited)", {}, 3.36),
    ("F1 J10 ground open, ribbon connected", {"j10_open": True}, 3.36),
    ("F2 J10 ground intermittent (1 ohm)", {"j10_r": 1.0}, 3.36),
    ("F3 J10 ground open, standoffs bonded", {"j10_open": True, "standoffs": True}, 3.36),
    ("F4 ribbon disconnected (J10 only)", {"ribbon_off": True}, 3.36),
    ("F5 one J501 ground contact open", {"j501_n": 1}, 3.36),
    ("F6 both J501 ground contacts open (Zorro carries all)", {"j501_n": 0}, 3.36),
    ("F7 J10 open + ribbon disconnected, monitor earthed", {"j10_open": True, "ribbon_off": True, "ext": True}, 2.5),
    ("F8 J10 open + ribbon disconnected, nothing else", {"j10_open": True, "ribbon_off": True}, 2.5),
    ("T1 blanked transient 6.75 A <= 15.3 ms, normal", {}, 6.75),
    ("T2 blanked transient 6.75 A <= 15.3 ms, J10 open", {"j10_open": True}, 6.75),
    ("H1 option: second drive connector in parallel (4 GND contacts)", {"j501_connectors": 2}, 2.5),
]


def main():
    print("Sheet 5 ground-return model: extremes over 2^7 resistance corners and I_MB 0-3 A [E]")
    print(f"Per-path resistance ranges (mOhm): J10 lead {1e3 * (J10_WIRE[0] + J10_CONTACT_X4[0] + J10_CONTACT_C[0]):.1f}-"
          f"{1e3 * (J10_WIRE[1] + J10_CONTACT_X4[1] + J10_CONTACT_C[1]):.1f}; ribbon conductor "
          f"{1e3 * (RIB_COND[0] + RIB_ENDS[0]):.0f}-{1e3 * (RIB_COND[1] + RIB_ENDS[1]):.0f} (x8 in parallel "
          f"{1e3 * (RIB_COND[0] + RIB_ENDS[0]) / 8:.1f}-{1e3 * (RIB_COND[1] + RIB_ENDS[1]) / 8:.1f}); standoffs "
          f"{1e3 * STANDOFF[0] / 4:.1f}-{1e3 * STANDOFF[1] / 4:.1f} (x4); J501 GND pair "
          f"{1e3 * J501_PATH[0] / 2:.1f}-{1e3 * J501_PATH[1] / 2:.1f}; Zorro 18 fingers {1e3 * ZFINGER[0] / 18:.2f}-"
          f"{1e3 * ZFINGER[1] / 18:.2f}; motherboard {1e3 * MB[0]:.0f}-{1e3 * MB[1]:.0f}")
    print("Per-contact maxima include share imbalance: ribbon x1.3, Zorro x1.5, J501 x1.2 [A].\n")
    hdr = (f"{'case':62} {'I_X4':>5} {'J10 A':>6} {'rib/c A':>7} {'so A':>5} {'ext A':>6} {'J501/c':>7} {'Zf/c':>6} "
           f"{'dG mV':>6} {'dZ mV':>6} {'X4 dedicated':>12} {'ribbon':>9} {'via J501':>9} {'MB loop':>7}")
    print(hdr)
    out = {}
    for name, case, i_x4 in CASES:
        r = run_case(name, case, i_x4)
        out[name.split()[0]] = r
        if r["floating"] and r["j10"] == 0 and r["rib"] == 0 and r["ext"] == 0:
            print(f"{name:62} {i_x4:5.2f}  X4 ground floating: no return path, the X4 cannot draw current (see note F8)")
            continue
        rib_c = r["rib"] / N_RIB_GND * IMBAL_RIB
        z_c = r["z"] / N_ZGND * IMBAL_Z
        n_j = case.get("j501_n", N_J501_GND) * case.get("j501_connectors", 1)
        j_c = r["j501"] / n_j * IMBAL_J501 if n_j else 0.0
        sd, sr_, sj = r["share_ded"], r["share_rib"], r["share_j501"]
        print(f"{name:62} {i_x4:5.2f} {up(r['j10'], 0.01):6.2f} {up(rib_c, 0.01):7.2f} {up(r['so'], 0.01):5.2f} "
              f"{up(r['ext'], 0.01):6.2f} {up(j_c, 0.01):7.2f} {up(z_c, 0.01):6.2f} {up(r['dg'] * 1e3, 0.1):6.1f} "
              f"{up(r['dz'] * 1e3, 0.1):6.1f} {down(sd[0] * 100, 1):5.0f}-{up(sd[1] * 100, 1):3.0f} % "
              f"{down(sr_[0] * 100, 1):3.0f}-{up(sr_[1] * 100, 1):3.0f} % {down(sj[0] * 100, 1):3.0f}-{up(sj[1] * 100, 1):3.0f} % "
              f"{up(r['loop'], 0.01):6.2f}A")
    print("\nColumns: J10 = X4 lead ground current; rib/c, J501/c, Zf/c = largest current in one ribbon ground conductor,")
    print("one drive-connector ground contact and one Zorro ground finger; dG = V(X4 ground) - V(carrier, X4 area);")
    print("dZ = V(carrier, Zorro edge) - V(motherboard slot); shares = fraction of the X4 return in the dedicated paths")
    print("(J10 lead + bonded standoffs) and in the ribbon; 'via J501' = fraction of the card's own return carried by the")
    print("drive-connector grounds (I_MB = 0); 'MB loop' = motherboard return current diverted through the Zorro fingers and")
    print("J501 when 3 A of it passes the slot region [A]. dG in T1/T2 lasts <= 15.3 ms (blanked transient).\n")
    print("Checks against the ratings / requirements:")
    worst_rib = max(out[k]["rib"] for k in out) / N_RIB_GND * IMBAL_RIB
    print(f"  ribbon conductor / IDC contact, worst case in any listed case: {up(worst_rib, 0.01):.2f} A "
          f"(T2, <= 15.3 ms); steady worst {up(max(out[k]['rib'] for k in ('N1', 'N3', 'F1', 'F2', 'F5', 'F6')) / 8 * 1.3, 0.01):.2f} A "
          f"(F1): requirement >= {REQ_RIB} A per conductor and contact (TBV against the chosen parts)")
    print(f"  X4 lead contact, worst steady: {up(max(out[k]['j10'] for k in ('N1', 'N3', 'F4', 'F5', 'F6')), 0.01):.2f} A "
          f"(F4, all current) <= requirement {REQ_J10} A")
    print(f"  Zorro finger, worst steady (F6, J501 grounds open): {up(out['F6']['z'] / N_ZGND * IMBAL_Z, 0.01):.2f} A "
          f"<= {ZF_RATING} A [D from V S52]")
    print(f"  J501 contact, worst steady (F5, one contact open, incl. MB loop): {up(out['F5']['j501'] * IMBAL_J501, 0.01):.2f} A "
          f"<= requirement {REQ_J501} A")
    normal = max(out[k]["dg"] for k in ("N1", "N2", "N2s", "N3"))
    print(f"  dG in normal operation (N1-N3): <= {up(normal * 1e3, 0.1):.1f} mV against the S4-6 assumption "
          f"{DG_LIMIT * 1e3:.0f} mV: {'ok' if normal <= DG_LIMIT else 'EXCEEDS'} (GP24 margin cost <= "
          f"{up(0.06 * normal * 1e3, 0.1):.1f} mV)")
    f12 = max(out[k]["dg"] for k in ("F1", "F2", "F3", "F5", "F6"))
    print(f"  dG in the single faults with the ribbon connected (F1-F3, F5, F6): <= {up(f12 * 1e3, 0.1):.1f} mV "
          f"({'inside' if f12 <= DG_LIMIT else 'outside'} the 50 mV assumption)")
    print("\nNotes:")
    print("  F7: with the J10 ground and the ribbon both lost, an earthed monitor's HDMI shield (or USB/Ethernet) becomes the")
    print(f"  X4 return: up to {up(out['F7']['ext'], 0.01):.2f} A through it, and the X4 ground floats up to "
          f"{up(out['F7']['dg'], 0.1):.1f} V from the carrier. Detection: X4 current above 0.5 A while X4_S0_SENSE says")
    print("  'not S0' (the ribbon carries X4_3V3_REF) -> PM-6 switches the X4 off within T_RIB.")
    print("  F8: without any other path the X4 cannot draw current: safe, and the X4 simply does not start.")
    print("  H1: a second drive-power connector halves the J501 resistance; it raises the J501 share but cannot remove the")
    print("  Zorro share, because the Zorro ground must stay connected (bus signal reference).")


if __name__ == "__main__":
    main()
