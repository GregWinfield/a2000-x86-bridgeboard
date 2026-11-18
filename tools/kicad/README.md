# tools/kicad

Licence: MIT (see [/LICENSES/MIT.txt](../../LICENSES/MIT.txt)).

| Script | Purpose |
|---|---|
| `gen_project.py` | **Bootstrap generator** that produced the first revision of the KiCad project: root sheet, sheet 1, placeholder sheets 2–6, project symbol library and the Zorro edge footprint. IC pin tables inside it were transcribed from the TI datasheets cited in `docs/stage2/sheet1-design-notes.md` §2 |
| `kisch.py` | Minimal KiCad 10 S-expression writer used by the generator |
| `netlist.py` | Reader for `kicad-cli sch export netlist --format kicadsexpr` output |
| `audit_sheet1.py` | Connectivity audit: checks every J101 pin and every U101–U109 pin, pull resistor, divider, jumper, decoupling capacitor and test point against the design tables (418 checks in sheet 1 revision B) |
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
python -I tools/kicad/pinmatrix_sheet1.py /tmp/sheet1.net
```

The last command prints a table to paste into the pin matrix.
