# SPDX-License-Identifier: MIT
"""Summarise a Lattice Diamond TRACE report (.twr) for gate G-STA.

usage: python -I hdl/syn/twr_summary.py <report.twr>

For every preference, the worst path from the setup section and, when the preference has a MIN
value, the corresponding path from the hold section. Also the overall error counts. Prints a
markdown table.
  MAXDELAY      : port-to-port path delay.
  CLOCK_TO_OUT  : the total from the clock pad to the output pin (clock path + data path,
                  TRACE's "totaling" figure). The min column is the fastest such total.
  FREQUENCY     : the worst register-to-register data path and its slack.
TRACE lists the worst path of each preference first; its verdict is "meets", "exceeds" or
"fails" requirements by N ns (negative slack for the last two).
"""
from __future__ import annotations

import re
import sys

PREF = re.compile(r"^Preference: (.+?)\n(.*?)(?=^Preference: |\Z)", re.S | re.M)
VERDICT = re.compile(r"(meets|exceeds|fails) requirements by ([\-\d.]+)ns")
TOTAL = re.compile(r"\(totaling ([\d.]+)ns\)")
DELAY = re.compile(r"Delay:\s+([\d.]+)ns")


def parse(section: str):
    out = {}
    for m in PREF.finditer(section):
        pref, body = m.group(1).strip(), m.group(2)
        v = VERDICT.search(body)
        if v:
            slack = float(v.group(2)) * (1 if v.group(1) == "meets" else -1)
            rest = body[v.start():]
        else:
            slack, rest = None, body
        d = (TOTAL if pref.startswith("CLOCK_TO_OUT") else DELAY).search(rest)
        out[pref] = (float(d.group(1)) if d else None, slack)
    return out


def label(pref: str) -> str:
    name = pref.rstrip(" ;").replace('"', "")
    m = re.match(r"CLOCK_TO_OUT (?:GROUP|PORT) (\S+) MAX [\d.]+ ns MIN [\d.]+ ns CLKPORT (\S+)", name)
    if m:
        return f"clock-to-out {m.group(1)} (from {m.group(2)})"
    name = name.replace("MAXDELAY FROM PORT ", "").replace(" TO PORT ", " → ")
    return re.sub(r"\s+[\d.]+ ns( MIN [\d.]+ ns)?$", "", name)


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
        mn = ho.get(pref, (None, None))[0] if "MIN" in pref else None
        print(f"| {label(pref)} | {d if d is not None else '–'} | {s if s is not None else '–'} | "
              f"{mn if mn is not None else '–'} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
