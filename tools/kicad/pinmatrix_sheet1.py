# SPDX-License-Identifier: MIT
"""Print the Zorro II connector pin table (markdown) derived from a KiCad netlist.

usage: python -I tools/kicad/pinmatrix_sheet1.py <netlist.net>

Each J101 pin is followed through series resistors and buffers to the
3.3 V FPGA-side net, using the pin-function names in the netlist.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlist                     # noqa: E402
from gen_project import ZNAMES     # noqa: E402

PARTNER_RN = {"1": "8", "2": "7", "3": "6", "4": "5", "5": "4", "6": "3", "7": "2", "8": "1"}


def main(path):
    sys.stdout.reconfigure(encoding="utf-8")
    comps, raw = netlist.load(Path(path))
    nets = {(n.rsplit("/", 1)[-1] if n.startswith("/") else n): v for n, v in raw.items()}
    pin_net = {(r, p): name for name, nodes in nets.items() for r, p, _ in nodes}
    func = netlist.PINFUNC
    by_func = {}
    for (r, p), fn in func.items():
        by_func[(r, fn)] = p

    def partner(ref, pin):
        fn = func.get((ref, pin), "")
        val = comps[ref]["value"]
        if "16244" in val and "A" in fn:
            return by_func.get((ref, fn.replace("A", "Y")))
        if "16T245" in val and "B" in fn:
            return by_func.get((ref, fn.replace("B", "A")))
        if "2T45" in val and fn.startswith("B"):
            return by_func.get((ref, fn.replace("B", "A")))
        if "07A" in val and fn.endswith("Y"):
            return by_func.get((ref, fn.replace("Y", "A")))
        return None

    def follow(net, seen=()):
        """Return (path text, fpga-side net) for a Zorro-domain net."""
        for r, p, _ in nets.get(net, []):
            if r == "J101" or r.startswith("TP") or (r, p) in seen:
                continue
            val = comps[r]["value"]
            if r.startswith("RN") or (r.startswith("R") and val in ("22R", "0R DNP")):
                other = PARTNER_RN[p] if r.startswith("RN") else ("2" if p == "1" else "1")
                nxt = pin_net.get((r, other))
                tag = f"{r} {val}" + (" (DNP)" if "DNP" in val else "")
                sub, fnet = follow(nxt, seen + ((r, p), (r, other)))
                return f"{tag} → {sub}", fnet
            if r.startswith("U"):
                fn = func.get((r, p), p)
                pp = partner(r, p)
                fnet = pin_net.get((r, pp)) if pp else None
                return f"{r}.{p} ({fn}) ↔ {r}.{pp} ({func.get((r, pp), '')})", fnet
        return "", None

    print("| Pin | Zorro II name | Net | Carrier path (from netlist) | FPGA-side net |")
    print("|---|---|---|---|---|")
    for n in range(1, 101):
        net = pin_net.get(("J101", str(n)))
        name = ZNAMES[n].replace("~{", "/").replace("}", "")
        if net is None or net.startswith("unconnected") or len(nets.get(net, [])) == 1:
            print(f"| {n} | {name} | – | **not connected** (no-connect flag) | – |")
        elif net == "GND":
            print(f"| {n} | {name} | GND | ground plane | – |")
        else:
            path_txt, fnet = follow(net)
            tps = [r for r, _, _ in nets[net] if r.startswith("TP")]
            extra = f"; test point {', '.join(tps)}" if tps else ""
            print(f"| {n} | {name} | `{net}` | {path_txt or '—'}{extra} | {('`' + fnet + '`') if fnet else '—'} |")


if __name__ == "__main__":
    main(sys.argv[1])
