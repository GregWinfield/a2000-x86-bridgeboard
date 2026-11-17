# SPDX-License-Identifier: MIT
"""Minimal KiCad 10 schematic / symbol / footprint writer.

Bootstrap tooling only: it generated the first revision of the KiCad files.
Once a .kicad_sch has been edited in KiCad, that file is authoritative and this
generator must not be re-run over it blindly (see tools/kicad/README.md).

Coordinates are millimetres. Library (symbol) coordinates are Y-up; schematic
coordinates are Y-down, as in KiCad.
"""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

SCH_VERSION = "20260306"      # KiCad 10.0 schematic format (from shipped demos)
SYM_VERSION = "20251024"      # KiCad 10.0 symbol library format
FP_VERSION = "20260206"       # KiCad 10.0 footprint format
GEN_VERSION = "10.0"
PROJECT = "a2000-bridgeboard"
LIB = PROJECT                 # project library nickname

_NS = uuid.UUID("6f0c1f7e-6a4b-4f3e-9a7e-2b1d5c3a9e10")


def U(key: str) -> str:
    """Deterministic UUID so regeneration does not churn version control."""
    return str(uuid.uuid5(_NS, key))


def f(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "", "-") else s


def q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def font(size=1.27, justify=None, hide=False):
    j = f"\n\t\t\t\t(justify {justify})" if justify else ""
    return f"(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {f(size)} {f(size)})\n\t\t\t\t){j}\n\t\t\t)"


def prop(name, value, x, y, ang=0, hide=False, justify=None, size=1.27, indent="\t\t"):
    h = f"\n{indent}\t(hide yes)" if hide else ""
    return (f"{indent}(property {q(name)} {q(value)}\n{indent}\t(at {f(x)} {f(y)} {f(ang)})"
            f"{h}\n{indent}\t(show_name no)\n{indent}\t(do_not_autoplace no)\n{indent}\t{font(size, justify)}\n{indent})")


# --------------------------------------------------------------------------- symbols
@dataclass
class Pin:
    num: str
    name: str
    etype: str          # input output bidirectional tri_state passive power_in power_out open_collector ...
    x: float
    y: float
    angle: int          # 0: pin points right (connection on the left); 180: connection on the right; 90/270 vertical
    length: float = 2.54
    unit: int = 1
    shape: str = "line"


@dataclass
class SymbolDef:
    name: str
    ref: str
    value: str
    footprint: str
    datasheet: str
    description: str
    pins: list[Pin]
    rects: dict[int, list[tuple[float, float, float, float]]] = field(default_factory=dict)  # unit -> rects
    extra_props: dict[str, str] = field(default_factory=dict)
    keywords: str = ""
    power: bool = False
    pin_name_offset: float = 0.508
    hide_pin_numbers: bool = False
    hide_pin_names: bool = False
    units: int = 1
    ref_at: tuple[float, float] = (0, 0)
    value_at: tuple[float, float] = (0, 0)
    graphics_raw: str = ""        # extra raw graphics for unit 0 (power symbols)

    def pin(self, num: str) -> Pin:
        for p in self.pins:
            if p.num == num:
                return p
        raise KeyError(f"{self.name}: no pin {num}")

    def sexpr(self, cache: bool) -> str:
        top = f"{LIB}:{self.name}" if cache else self.name
        o = [f"\t(symbol {q(top)}"]
        if self.power:
            o.append("\t\t(power global)")
        if self.hide_pin_numbers:
            o.append("\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)")
        pn = f"\t\t(pin_names\n\t\t\t(offset {f(self.pin_name_offset)})"
        pn += "\n\t\t\t(hide yes)\n\t\t)" if self.hide_pin_names else "\n\t\t)"
        o.append(pn)
        o.append("\t\t(exclude_from_sim no)\n\t\t(in_bom {0})\n\t\t(on_board {0})\n\t\t(in_pos_files {0})\n"
                 "\t\t(duplicate_pin_numbers_are_jumpers no)".format("no" if self.power else "yes"))
        o.append(prop("Reference", self.ref, *self.ref_at, hide=self.power))
        o.append(prop("Value", self.value, *self.value_at))
        o.append(prop("Footprint", self.footprint, 0, 0, hide=True))
        o.append(prop("Datasheet", self.datasheet, 0, 0, hide=True))
        o.append(prop("Description", self.description, 0, 0, hide=True))
        if self.keywords:
            o.append(prop("ki_keywords", self.keywords, 0, 0, hide=True))
        for k, v in self.extra_props.items():
            o.append(prop(k, v, 0, 0, hide=True))
        # unit 0 = graphics common to all units
        common = self.rects.get(0, [])
        if common or self.graphics_raw:
            g = [f"\t\t(symbol {q(self.name + '_0_1')}"]
            for (x1, y1, x2, y2) in common:
                g.append(f"\t\t\t(rectangle\n\t\t\t\t(start {f(x1)} {f(y1)})\n\t\t\t\t(end {f(x2)} {f(y2)})\n"
                         "\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n"
                         "\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)")
            if self.graphics_raw:
                g.append(self.graphics_raw)
            g.append("\t\t)")
            o.append("\n".join(g))
        for u in range(1, self.units + 1):
            g = [f"\t\t(symbol {q(self.name + f'_{u}_1')}"]
            for (x1, y1, x2, y2) in self.rects.get(u, []):
                g.append(f"\t\t\t(rectangle\n\t\t\t\t(start {f(x1)} {f(y1)})\n\t\t\t\t(end {f(x2)} {f(y2)})\n"
                         "\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n"
                         "\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)")
            for p in [p for p in self.pins if p.unit == u]:
                g.append(f"\t\t\t(pin {p.etype} {p.shape}\n\t\t\t\t(at {f(p.x)} {f(p.y)} {p.angle})\n"
                         f"\t\t\t\t(length {f(p.length)})\n"
                         f"\t\t\t\t(name {q(p.name)}\n\t\t\t\t\t{font()}\n\t\t\t\t)\n"
                         f"\t\t\t\t(number {q(p.num)}\n\t\t\t\t\t{font()}\n\t\t\t\t)\n\t\t\t)")
            g.append("\t\t)")
            o.append("\n".join(g))
        o.append("\t\t(embedded_fonts no)\n\t)")
        return "\n".join(o)


def write_symbol_lib(path: Path, syms: list[SymbolDef]):
    body = "\n".join(s.sexpr(cache=False) for s in syms)
    path.write_text(f"(kicad_symbol_lib\n\t(version {SYM_VERSION})\n\t(generator \"kicad_symbol_editor\")\n"
                    f"\t(generator_version \"{GEN_VERSION}\")\n{body}\n)\n", encoding="utf-8")


class StdSymbol:
    """A symbol copied verbatim from an installed KiCad library."""

    def __init__(self, libfile: Path, lib: str, name: str):
        t = libfile.read_text(encoding="utf-8")
        i = t.find(f'\t(symbol "{name}"')
        if i < 0:
            raise KeyError(name)
        start = t.index("(", i)
        depth, k = 0, start
        while True:
            c = t[k]
            if c == '"':
                k += 1
                while t[k] != '"':
                    k += 2 if t[k] == "\\" else 1
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        raw = t[start:k + 1]
        if "(extends" in raw:
            raise ValueError(f"{lib}:{name} extends another symbol; flatten first")
        self.lib, self.name = lib, name
        self.lib_id = f"{lib}:{name}"
        self.cache = "\t" + raw.replace(f'(symbol "{name}"', f'(symbol "{self.lib_id}"', 1)
        self.pins = {}
        for m in re.finditer(r'\(pin (\w+) (\w+)\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]+)"', raw, re.S):
            self.pins[m.group(6)] = (float(m.group(3)), float(m.group(4)))
        self.power = "(power" in raw.split("(property", 1)[0]

    def pin_xy(self, num):
        return self.pins[num]


# --------------------------------------------------------------------------- schematic
def xform(sx, sy, rot, px, py):
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return (round(sx + rx, 4), round(sy - ry, 4))


@dataclass
class Placed:
    ref: str
    sym: object
    x: float
    y: float
    rot: int
    unit: int

    def p(self, num):
        if isinstance(self.sym, SymbolDef):
            pin = self.sym.pin(num)
            return xform(self.x, self.y, self.rot, pin.x, pin.y)
        px, py = self.sym.pin_xy(num)
        return xform(self.x, self.y, self.rot, px, py)


class Schematic:
    def __init__(self, key, paper, title, rev, date, comments, company, path):
        self.uuid = U(key)
        self.key = key
        self.paper = paper
        self.tb = (title, rev, date, comments, company)
        self.path = path                  # instance path for symbols placed on this sheet
        self.items: list[str] = []
        self.libsyms: dict[str, str] = {}
        self.placed: list[Placed] = []
        self._n = 0
        self.wire_ends: dict[tuple, int] = {}

    def _u(self, kind):
        self._n += 1
        return U(f"{self.key}/{kind}/{self._n}")

    # -- primitives ---------------------------------------------------------
    def wire(self, a, b):
        if a == b:
            return
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError(f"non-orthogonal wire {a}->{b}")
        for pt in (a, b):
            self.wire_ends[pt] = self.wire_ends.get(pt, 0) + 1
        self.items.append(f"\t(wire\n\t\t(pts\n\t\t\t(xy {f(a[0])} {f(a[1])}) (xy {f(b[0])} {f(b[1])})\n\t\t)\n"
                          f"\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid {q(self._u('w'))})\n\t)")

    def path_wire(self, *pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def junction(self, p):
        self.items.append(f"\t(junction\n\t\t(at {f(p[0])} {f(p[1])})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n"
                          f"\t\t(uuid {q(self._u('j'))})\n\t)")

    def noconnect(self, p):
        self.items.append(f"\t(no_connect\n\t\t(at {f(p[0])} {f(p[1])})\n\t\t(uuid {q(self._u('nc'))})\n\t)")

    def label(self, name, p, side):
        """side='right': text extends right of p; 'left': extends left."""
        ang, just = (0, "left bottom") if side == "right" else (180, "right bottom")
        self.items.append(f"\t(label {q(name)}\n\t\t(at {f(p[0])} {f(p[1])} {ang})\n\t\t{font(1.27, just)}\n"
                          f"\t\t(uuid {q(self._u('l'))})\n\t)")

    def hlabel(self, name, shape, p, side):
        ang, just = (0, "left") if side == "right" else (180, "right")
        self.items.append(f"\t(hierarchical_label {q(name)}\n\t\t(shape {shape})\n\t\t(at {f(p[0])} {f(p[1])} {ang})\n"
                          f"\t\t{font(1.27, just)}\n\t\t(uuid {q(self._u('hl'))})\n\t)")

    def text(self, s, p, size=1.27, bold=False):
        b = "\n\t\t\t\t(bold yes)" if bold else ""
        self.items.append(f"\t(text {q(s)}\n\t\t(exclude_from_sim no)\n\t\t(at {f(p[0])} {f(p[1])} 0)\n"
                          f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)}){b}\n\t\t\t)\n\t\t\t(justify left top)\n\t\t)\n"
                          f"\t\t(uuid {q(self._u('t'))})\n\t)")

    def raw(self, s):
        self.items.append(s)

    # -- symbols --------------------------------------------------------------
    def place(self, sym, ref, value, x, y, rot=0, unit=1, footprint=None, dnp=False, in_bom=True,
              props=None, ref_at=None, val_at=None, hide_value=False, extra_pins=None, field_ang=None,
              ref_just=None, val_just=None, hide_ref=False):
        if isinstance(sym, SymbolDef):
            lib_id = f"{LIB}:{sym.name}"
            self.libsyms[lib_id] = sym.sexpr(cache=True)
            pins = [p.num for p in sym.pins if p.unit == unit]
            fp = sym.footprint if footprint is None else footprint
            ds, desc = sym.datasheet, sym.description
            power = sym.power
            extra = dict(sym.extra_props)
        else:
            lib_id = sym.lib_id
            self.libsyms[lib_id] = sym.cache
            pins = list(sym.pins.keys())
            fp = footprint or ""
            ds, desc = "", ""
            power = sym.power
            extra = {}
        if props:
            extra.update(props)
        if field_ang is None:
            field_ang = 90 if rot in (90, 270) else 0
        rx, ry = ref_at if ref_at else (x, y - 3.0)
        vx, vy = val_at if val_at else (x, y + 3.0)
        o = [f"\t(symbol\n\t\t(lib_id {q(lib_id)})\n\t\t(at {f(x)} {f(y)} {rot})\n\t\t(unit {unit})\n\t\t(body_style 1)\n"
             f"\t\t(exclude_from_sim no)\n\t\t(in_bom {'yes' if (in_bom and not power) else 'no'})\n"
             f"\t\t(on_board {'no' if power else 'yes'})\n\t\t(in_pos_files {'no' if power else 'yes'})\n"
             f"\t\t(dnp {'yes' if dnp else 'no'})\n\t\t(uuid {q(U(self.key + '/sym/' + ref + '/' + str(unit)))})"]
        o.append(prop("Reference", ref, rx, ry, field_ang, hide=power or hide_ref, justify=ref_just))
        o.append(prop("Value", value, vx, vy, field_ang, hide=hide_value, justify=val_just))
        o.append(prop("Footprint", fp, x, y, 0, hide=True))
        o.append(prop("Datasheet", ds, x, y, 0, hide=True))
        o.append(prop("Description", desc, x, y, 0, hide=True))
        for k, v in extra.items():
            o.append(prop(k, v, x, y, 0, hide=True))
        for pn in pins:
            o.append(f"\t\t(pin {q(pn)}\n\t\t\t(uuid {q(U(self.key + '/pin/' + ref + '/' + pn))})\n\t\t)")
        o.append(f"\t\t(instances\n\t\t\t(project {q(PROJECT)}\n\t\t\t\t(path {q(self.path)}\n"
                 f"\t\t\t\t\t(reference {q(ref)})\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)")
        self.items.append("\n".join(o))
        pl = Placed(ref, sym, x, y, rot, unit)
        self.placed.append(pl)
        return pl

    def write(self, path: Path, sheet_instances: str = ""):
        title, rev, date, comments, company = self.tb
        cm = "".join(f"\n\t\t(comment {i} {q(c)})" for i, c in enumerate(comments, 1))
        libs = "\n".join(self.libsyms[k] for k in sorted(self.libsyms))
        body = "\n".join(self.items)
        si = f"\n{sheet_instances}" if sheet_instances else ""
        path.write_text(
            f"(kicad_sch\n\t(version {SCH_VERSION})\n\t(generator \"eeschema\")\n\t(generator_version \"{GEN_VERSION}\")\n"
            f"\t(uuid {q(self.uuid)})\n\t(paper {q(self.paper)})\n\t(title_block\n\t\t(title {q(title)})\n"
            f"\t\t(date {q(date)})\n\t\t(rev {q(rev)})\n\t\t(company {q(company)}){cm}\n\t)\n"
            f"\t(lib_symbols\n{libs}\n\t)\n{body}{si}\n\t(embedded_fonts no)\n)\n", encoding="utf-8")
