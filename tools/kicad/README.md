# tools/kicad

Licence: MIT (see [/LICENSES/MIT.txt](../../LICENSES/MIT.txt)).

| Script | Purpose |
|---|---|
| `gen_project.py` | **Bootstrap generator** that produced the first revision of the KiCad project: root sheet, sheet 1, sheet 2 (FPGA, via `sheet2.py`), sheet 3 (shared SRAM), placeholder sheets 4–6, project symbol library and the Zorro edge footprint. IC pin tables inside it were transcribed from the TI datasheets cited in `docs/stage2/sheet1-design-notes.md` §2 |
| `kisch.py` | Minimal KiCad 10 S-expression writer used by the generator |
| `netlist.py` | Reader for `kicad-cli sch export netlist --format kicadsexpr` output |
| `audit_sheet1.py` | Connectivity audit: checks every J101 pin and every U101–U109 pin, pull resistor, divider, jumper, decoupling capacitor and test point against the design tables (418 checks in sheet 1 revision B) |
| `sheet2.py` | Sheet 2 builder: the FPGA symbol from the Lattice pin data, every signal pin from `tools/fpga/pinplan.py`, configuration/JTAG resistors, decoupling, oscillator |
| `audit_sheet2.py` | Connectivity audit of sheet 2: all 144 FPGA pins against the Lattice pin data, the pin plan, **the LPF LOCATEs Diamond used** and the HDL port directions (driver and contention check on every cross-sheet net), plus configuration resistors, decoupling, oscillator filter, JTAG header. 1047 checks in sheet 2 revision A |
| `audit_sheet3.py` | Connectivity audit of sheet 3: every U301 pin against the ISSI pin table, the safe-state pull-ups, decoupling, test points, and the cross-sheet local bus LD0–LD15 (U103 A port ↔ U301 I/O), with one FPGA pin on every SA, SRAM and LD net. 159 checks since sheet 2 |
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
python -I tools/kicad/pinmatrix_sheet1.py /tmp/sheet1.net
```

The last command prints a table to paste into the pin matrix.
