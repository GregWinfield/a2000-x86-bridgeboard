# tools/kicad

Licence: MIT (see [/LICENSES/MIT.txt](../../LICENSES/MIT.txt)).

| Script | Purpose |
|---|---|
| `gen_project.py` | **Bootstrap generator** that produced the first revision of the KiCad project: root sheet, sheet 1, sheet 2 (FPGA, via `sheet2.py`), sheet 3 (shared SRAM), sheet 4 (host link, via `sheet4.py`), placeholder sheets 5–6, project symbol library and the Zorro edge footprint. IC pin tables inside it were transcribed from the TI datasheets cited in `docs/stage2/sheet1-design-notes.md` §2 |
| `kisch.py` | Minimal KiCad 10 S-expression writer used by the generator |
| `netlist.py` | Reader for `kicad-cli sch export netlist --format kicadsexpr` output |
| `audit_sheet1.py` | Connectivity audit: checks every J101 pin and every U101–U109 pin, pull resistor, divider, jumper, decoupling capacitor and test point against the design tables (418 checks in sheet 1 revision B) |
| `sheet2.py` | Sheet 2 builder: the FPGA symbol from the Lattice pin data, every signal pin from `tools/fpga/pinplan.py`, configuration/JTAG resistors, decoupling, oscillator |
| `audit_sheet2.py` | Connectivity audit of sheet 2: all 144 FPGA pins against the Lattice pin data, the pin plan, **the LPF LOCATEs Diamond used** and the HDL port directions (driver and contention check on every cross-sheet net), plus configuration resistors, decoupling, oscillator filter, JTAG header (polarized, silkscreen recorded). 1046 checks in sheet 2 revision A1; 1100 in revision A2 (LCMXO2-4000HC pinout, C-30) with sheet 4 connected; 1103 with sheet 4 revision A2 (three new sheet-4 net names checked), 1105 with revision A3 |
| `audit_sheet3.py` | Connectivity audit of sheet 3: every U301 pin against the ISSI pin table, the safe-state pull-ups, decoupling, test points, and the cross-sheet local bus LD0–LD15 (U103 A port ↔ U301 I/O), with one FPGA pin on every SA, SRAM and LD net. 159 checks since sheet 2 |
| `sheet4.py` | Sheet 4 builder: X4 ribbon header J401, four SN74AVC4T774, U402's fail-safe output enable (TLV3201 comparator U405 switching Q401, in series with Q402 on GP24, with Schmitt-trigger buffer U406 driving /OE; S4-6 rev A3), default resistors, B-side pull-downs, decoupling, test points |
| `audit_sheet4.py` | Connectivity audit of sheet 4: every J401 pin, every translator's supplies, /OE, DIR and channel nets, series resistors, the S4-6 rules (outputs only on U402; U402 /OE from U406, its input pulled low only through Q401/Q402; comparator and MOSFET pins, threshold divider; no source on GP24; only MOSFET gates cross from the X4 side to /OE; a pull-down on every input), the R-51 defaults, ER-3 and the parts list. 220 checks; 29 of 29 injected faults detected |
| `sheet5.py` | Sheet 5 builder: TPS259470L eFuses U501 (X4 12 V) and U503 (5 V, OVLO), INA226 U502 at 0x44 with a Kelvin shunt, the fail-safe X4 enable stage (Q501/Q502, JP501), TLV76733 U504 (+3V3), the active-low S0 sense (Q503), bonded standoff pads; symbols from the TI pin tables and the TI RPW0010A footprint |
| `audit_sheet5.py` | Connectivity audit of sheet 5: every part, value, footprint and pin; re-derives the ILIM band and UVLO/OVLO windows from the schematic values with `tools/analysis/sheet5_power.py`; C-28 address, C-29 pull-up domains, R-51, ER-3, rail drivers, +3V3 capacitance, J502 order (274 checks; 28 of 28 injected faults detected) |
| `pinmatrix_sheet1.py` | Generates the Zorro connector table in `docs/pin-assignment-matrix.md` from the netlist |

## Important: the KiCad files are authoritative

After generation, the files were re-saved by KiCad itself (`kicad-cli sch upgrade --force`, `sym upgrade --force`) and verified equivalent: same ERC, same audit, identical netlist. **Edit the schematic in KiCad from now on.** Re-running `gen_project.py` would overwrite manual edits to the generated sheets; only do it on a branch and diff the result.

## Typical checks after editing sheet 1

From `hardware/kicad`:

```sh
kicad-cli sch erc --severity-all --format report -o ../../docs/stage2/sheet1-erc-report.txt a2000-bridgeboard.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o /tmp/sheet1.net a2000-bridgeboard.kicad_sch
```

From the repo root:

```sh
python -I tools/kicad/audit_sheet1.py /tmp/sheet1.net
python -I tools/kicad/audit_sheet2.py /tmp/sheet1.net
python -I tools/kicad/audit_sheet3.py /tmp/sheet1.net
python -I tools/kicad/audit_sheet4.py /tmp/sheet1.net
python -I tools/kicad/audit_sheet5.py /tmp/sheet1.net
python -I tools/kicad/pinmatrix_sheet1.py /tmp/sheet1.net
```

The last command prints a table to paste into the pin matrix.
