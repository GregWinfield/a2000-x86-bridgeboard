# SPDX-License-Identifier: MIT
"""Summarise a Lattice Diamond TRACE report (.twr) for gate G-STA.

usage: python -I hdl/syn/twr_summary.py <report.twr>

For every MAXDELAY preference: the worst (maximum) path delay from the setup section and,
when the preference has a MIN value, the minimum path delay from the hold section. Also the
FREQUENCY result and the overall error counts. Prints a markdown table.
"""
from __future__ import annotations

import re
import sys


def parse(section: str):
    out = {}
    for m in re.finditer(r'^Preference: (.+?)\n(.*?)(?=^Preference: |\Z)', section, re.S | re.M):
        pref, body = m.group(1).strip(), m.group(2)
        d = re.search(r'Delay:\s+([\d.]+)ns', body)
        sl = re.search(r'meets requirements by ([\-\d.]+)ns|fails requirements by ([\-\d.]+)ns', body)
        out[pref] = (float(d.group(1)) if d else None,
                     (float(sl.group(1)) if sl and sl.group(1) else -float(sl.group(2)) if sl else None))
    return out


def main(path: str) -> int:
    sys.stdout.reconfigure(encoding="utf-8")       # Windows consoles default to cp1252
    txt = open(path, encoding="utf-8", errors="replace").read()
    split = txt.find("Lattice TRACE Report - Hold")
    setup, hold = (txt[:split], txt[split:]) if split >= 0 else (txt, "")
    su, ho = parse(setup), parse(hold)
    dev = re.search(r"Device,speed:\s+(\S+)", txt)
    print(f"Device/speed: {dev.group(1) if dev else '?'}")
    errs = re.findall(r"Timing errors: (\d+) \(setup\), (\d+) \(hold\)", txt)
    print(f"Timing errors (setup, hold): {errs[-1] if errs else '?'}\n")
    print("| Preference | Max delay (ns) | Slack (ns) | Min delay (ns) |")
    print("|---|---|---|---|")
    for pref, (d, s) in su.items():
        name = pref.replace("MAXDELAY FROM PORT ", "").replace(" TO PORT ", " → ").rstrip(" ;")
        name = re.sub(r'\s+[\d.]+ ns( MIN [\d.]+ ns)?$', "", name).replace('"', "")
        mn = ho.get(pref, (None, None))[0] if "MIN" in pref else None
        print(f"| {name} | {d if d is not None else '–'} | {s if s is not None else '–'} | "
              f"{mn if mn is not None else '–'} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
