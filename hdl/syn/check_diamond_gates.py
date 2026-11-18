# SPDX-License-Identifier: MIT
"""C-02 structural check on the Lattice Diamond post-map netlist (*_mapvo.vo).

usage: python -I hdl/syn/check_diamond_gates.py <impl1/z2_sta_impl1_mapvo.vo>

Checks, on Diamond's own mapping (LSE + map):
  1. the ZB_AS_N and ZB_BERR_N pad nets drive only the LUTs of the z2_asgate* instances, plus
     exactly one flip-flop data input each (the synchroniser);
  2. each z2_asgate* LUT outputs 1 for every input combination with /AS negated (as_n = 1),
     and the asgate3 LUTs also with /BERR asserted (berr_n = 0);
  3. the LUTs drive ZF_SLAVE_N, ZF_XRDY and ZF_DBUF_OE_N.
Exit status 1 on any failure.
"""
from __future__ import annotations

import re
import sys

fails = 0


def check(cond, msg):
    global fails
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        fails += 1


def main(path: str) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    txt = open(path, encoding="utf-8", errors="replace").read()
    mods = {m.group(1): m.group(2) for m in re.finditer(r"^module (\S+) \((.*?)^endmodule", txt, re.S | re.M)}
    lut_init = {}
    for name, body in mods.items():
        m = re.search(r"ROM16X1A #\(16'h([0-9A-Fa-f]{4})\)", body)
        if name.startswith("lut4") and m:
            lut_init[name] = int(m.group(1), 16)
    top = mods["z2_top"]
    # slice instances in the top module: type, name, pin -> net
    insts = []
    # escaped names (\u_core/SLICE_1 ) end at whitespace; plain names may touch the parenthesis
    for m in re.finditer(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$]*)\s*\((.*?)\);", top, re.S | re.M):
        typ, name, conns = m.group(1), m.group(2), m.group(3)
        pins = dict(re.findall(r"\.(\w+)\(([^()]*)\)", conns))
        insts.append((typ, name, {k: v.strip() for k, v in pins.items()}))
    as_net = next(v for t, n, p in insts if t == "ZB_AS_N" for k, v in p.items() if k == "PADDI")
    be_net = next(v for t, n, p in insts if t == "ZB_BERR_N" for k, v in p.items() if k == "PADDI")
    print(f"INFO: /AS pad net {as_net}, /BERR pad net {be_net}")

    gate_luts = []                                   # (slice inst, lut inst name, lut type, {A..D: net}, out net)
    for typ, name, pins in insts:
        body = mods.get(typ, "")
        for m in re.finditer(r"(lut4\d+) (\\\S+) \((.*?)\);", body, re.S):
            ltyp, lname, lconn = m.group(1), m.group(2), m.group(3)
            if "z2_asgate" not in lname:
                continue
            lp = dict(re.findall(r"\.(\w)\((\w+)\)", lconn))
            nets = {k: ("GND" if v == "GNDI" else pins.get(v, "?")) for k, v in lp.items() if k in "ABCD"}
            gate_luts.append((name, lname, ltyp, nets, pins.get(lp["Z"], "?")))
    check(len(gate_luts) == 3, f"three z2_asgate LUTs found ({len(gate_luts)})")
    outs = set()
    for sname, lname, ltyp, nets, out in gate_luts:
        init = lut_init[ltyp]
        order = "ABCD"
        a_idx = [i for i, k in enumerate(order) if nets.get(k) == as_net]
        b_idx = [i for i, k in enumerate(order) if nets.get(k) == be_net]
        is3 = "asgate3" in lname
        check(len(a_idx) == 1, f"{lname}: /AS is one LUT input")
        if is3:
            check(len(b_idx) == 1, f"{lname}: /BERR is one LUT input")
        ok = True
        for i in range(16):
            ctrl = ((i >> a_idx[0]) & 1) == 1 if a_idx else False
            if is3 and b_idx:
                ctrl = ctrl or (((i >> b_idx[0]) & 1) == 0)
            if ctrl and not (init >> i) & 1:
                ok = False
        check(ok, f"{lname} (init 16'h{init:04X}) -> {out}: output 1 whenever /AS negated"
                  + (" or /BERR asserted" if is3 else ""))
        outs.add(out)
    check(outs == {"ZF_SLAVE_N_c", "ZF_XRDY_c", "ZF_DBUF_OE_N_c"}, f"gate outputs {sorted(outs)}")

    # fan-out of the control pad nets
    for net, label in ((as_net, "/AS"), (be_net, "/BERR")):
        users = [(t, n, k) for t, n, p in insts for k, v in p.items() if v == net and t not in ("ZB_AS_N", "ZB_BERR_N")]
        lut_pins = sum(1 for sname, lname, ltyp, nets, out in gate_luts for v in nets.values() if v == net)
        ff_pins = [u for u in users if re.fullmatch(r"M[01]", u[2])]
        check(len(users) == lut_pins + len(ff_pins) and len(ff_pins) == 1,
              f"{label} pad net drives only the gate LUTs ({lut_pins}) and one FF data input ({len(ff_pins)}): {users}")
    print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
