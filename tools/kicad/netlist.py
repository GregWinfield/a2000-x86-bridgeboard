# SPDX-License-Identifier: MIT
"""Tiny reader for KiCad 'kicadsexpr' netlists (kicad-cli sch export netlist)."""
from __future__ import annotations

import re
from pathlib import Path

_TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


def parse_sexpr(text: str):
    stack, cur = [], []
    for m in _TOK.finditer(text):
        t = m.group(1)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\") if t.startswith('"') else t)
    return cur[0]


PINFUNC: dict = {}   # (ref, pin) -> pin function name, filled by load()


def _find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def load(path: Path):
    """Return (components, nets): components {ref: {value, footprint, fields}}, nets {name: [(ref, pin, pintype)]}."""
    root = parse_sexpr(Path(path).read_text(encoding="utf-8"))
    comps = {}
    for comp in _find(_find(root, "components")[0], "comp"):
        ref = _find(comp, "ref")[0][1]
        val = _find(comp, "value")[0][1] if _find(comp, "value") else ""
        fp = _find(comp, "footprint")[0][1] if _find(comp, "footprint") else ""
        fields = {}
        for fl in _find(comp, "fields"):
            for fld in _find(fl, "field"):
                nm = _find(fld, "name")[0][1]
                fields[nm] = fld[-1] if isinstance(fld[-1], str) else ""
        comps[ref] = {"value": val, "footprint": fp, "fields": fields}
    nets = {}
    for net in _find(_find(root, "nets")[0], "net"):
        name = _find(net, "name")[0][1]
        nodes = []
        for nd in _find(net, "node"):
            ref = _find(nd, "ref")[0][1]
            pin = _find(nd, "pin")[0][1]
            ptype = _find(nd, "pintype")[0][1] if _find(nd, "pintype") else ""
            nodes.append((ref, pin, ptype))
            if _find(nd, "pinfunction"):
                fn = _find(nd, "pinfunction")[0][1]
                if fn.endswith("_" + pin):            # KiCad 10 writes "<name>_<number>"
                    fn = fn[: -(len(pin) + 1)]
                PINFUNC[(ref, pin)] = fn
        nets[name] = nodes
    return comps, nets
