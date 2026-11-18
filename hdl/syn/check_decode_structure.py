# SPDX-License-Identifier: MIT
"""Structural hazard check of the synthesised Zorro decode (C-02).

usage: python -I hdl/syn/check_decode_structure.py hdl/build/decode_lut.json

Checks, on the Yosys LUT netlist:
  1. each z2_asgate2 / z2_asgate3 module is exactly one $lut cell;
  2. that LUT outputs 1 for every input combination with as_n = 1 (and, for asgate3,
     with berr_n = 0), i.e. /AS (/BERR) is a controlling input of the final gate;
  3. inside z2_decode, the as_n and berr_n port bits feed ONLY asgate instances, never a
     decode LUT, so they cannot be merged into the address cone;
  4. slave_n / xrdy / dbuf_oe_n are driven directly by the asgate outputs.
Also reports LUT count and LUT levels from A23..A16 to the select term.
Exit status 1 on any failure.
"""
from __future__ import annotations

import json
import sys

fails = 0


def check(cond: bool, msg: str) -> None:
    global fails
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        fails += 1


def lut_bits(cell) -> tuple[int, str]:
    width = int(cell["parameters"]["WIDTH"], 2)
    table = cell["parameters"]["LUT"]          # MSB first binary string, 2**width chars
    return width, table


def lut_value(table: str, index: int) -> str:
    return table[len(table) - 1 - index]


def main(path: str) -> int:
    mods = json.load(open(path, encoding="utf-8"))["modules"]

    # ---- 1 + 2: final gates
    for name, ctrl in (("z2_asgate2", {"as_n": "1"}), ("z2_asgate3", {"as_n": "1", "berr_n": "0"})):
        m = mods.get(name)
        check(m is not None, f"{name} kept as a separate module")
        if m is None:
            continue
        luts = [c for c in m["cells"].values() if c["type"] == "$lut"]
        other = [c["type"] for c in m["cells"].values() if c["type"] != "$lut"]
        check(len(luts) == 1 and not other, f"{name} is exactly one LUT (found {len(luts)} LUT, others {other})")
        if len(luts) != 1:
            continue
        cell = luts[0]
        width, table = lut_bits(cell)
        a_bits = cell["connections"]["A"]
        ports = {p: d["bits"][0] for p, d in m["ports"].items()}
        check(cell["connections"]["Y"] == [ports["out_n"]], f"{name}: LUT drives out_n directly")
        for port, level in ctrl.items():
            if ports[port] not in a_bits:
                check(False, f"{name}: {port} is an input of the LUT")
                continue
            idx = a_bits.index(ports[port])
            ok = all(lut_value(table, i) == "1"
                     for i in range(2 ** width) if ((i >> idx) & 1) == int(level))
            check(ok, f"{name}: output is 1 for all inputs whenever {port} = {level}")

    # ---- 3 + 4: z2_decode boundary
    d = mods["z2_decode"]
    pbits = {p: v["bits"] for p, v in d["ports"].items()}
    ctrl_bits = set(pbits["as_n"]) | set(pbits["berr_n"])
    users = []
    for cname, c in d["cells"].items():
        for conn in c["connections"].values():
            if ctrl_bits & set(b for b in conn if isinstance(b, int)):
                users.append((cname, c["type"]))
                break
    bad = [u for u in users if not u[1].startswith("z2_asgate")]
    check(not bad and len(users) == 3, f"as_n/berr_n feed only the 3 asgate instances (users: {users})")
    outs = {c["connections"]["out_n"][0]: cname for cname, c in d["cells"].items()
            if c["type"].startswith("z2_asgate")}
    for p in ("slave_n", "xrdy", "dbuf_oe_n"):
        check(pbits[p][0] in outs, f"{p} driven directly by an asgate instance ({outs.get(pbits[p][0])})")

    # ---- depth report
    driver = {}
    for cname, c in d["cells"].items():
        if c["type"] == "$lut":
            driver[c["connections"]["Y"][0]] = c["connections"]["A"]
    memo: dict[int, int] = {}

    def depth(bit) -> int:
        if not isinstance(bit, int) or bit not in driver:
            return 0
        if bit not in memo:
            memo[bit] = 1 + max(depth(b) for b in driver[bit])
        return memo[bit]

    slave_gate = next(c for c in d["cells"].values() if c["type"] == "z2_asgate2")
    sel_depth = depth(slave_gate["connections"]["term"][0])
    nlut = len(driver)
    print(f"INFO: z2_decode uses {nlut} decode LUTs; select term depth = {sel_depth} LUT level(s); "
          f"A23..A16 -> /SLAVEn = {sel_depth + 1} levels, /AS -> /SLAVEn = 1 level")
    print(f"{'ALL PASS' if fails == 0 else str(fails) + ' FAILURE(S)'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
