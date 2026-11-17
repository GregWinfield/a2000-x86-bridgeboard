# Sheet 1: ERC and connectivity verification report

**Date:** 2026-11-18.
**Tool:** KiCad 10.0.8 `kicad-cli`.
**Input:** `hardware/kicad/a2000-bridgeboard.kicad_sch` (whole hierarchy).
**Command:** `kicad-cli sch erc --severity-all` (default project rule severities).
**Raw report:** [sheet1-erc-report.txt](sheet1-erc-report.txt).

> An ERC-clean result does **not** mean the design is electrically, timing- or mechanically validated. It only means no rule the checker knows about was broken. See [sheet1-design-notes.md](sheet1-design-notes.md) §8 for the open engineering concerns.

## 1. Result

| Severity | Rule | Count | Items | Assessment |
|---|---|---|---|---|
| Error | `pin_not_connected` | 57 | Hierarchical **sheet pins** of sheet 1 on the root sheet: 32 × ZB_*, 16 × LD*, 9 × ZF_* | **Expected.** These are sheet 1's interface to sheet 2 (FPGA), which is not drawn yet. Every one becomes a real connection on sheet 2 |
| Warning | `isolated_pin_label` | 47 | Sheet-1 hierarchical labels ZB_A1–ZB_A23, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_E7M, ZB_CFGIN_N, ZB_BUSRST_N, ZB_CDAC and LD0–LD15. Each connects to a single pin on this sheet (a buffer output or transceiver A pin) | **Expected**, same cause. ZB_AS_N is not listed because it also has test point TP114 |
| All other rules | – | **0** | Power-pin drive, pin-type conflicts (output↔output and similar), dangling wires and labels, no-connect misuse, duplicate references, library-symbol mismatches, label naming | – |

**No unexpected violations.** The 104 expected items all disappear once sheet 2 connects the interface. They were deliberately **not** suppressed with ERC exclusions or no-connect flags, so that an unconnected interface net cannot slip through later.

## 2. Temporary items that affect ERC

- **PWR_FLAGs on `+3V3` and `+5V_BUS` (sheet 1, top-right).** They declare these rails as driven, because their source (sheet 5) is not drawn yet. Remove them when sheet 5 exists (concern C-12).
  - Without them, ERC would report every IC supply pin as "input power pin not driven", which would hide real issues.
  - The GND PWR_FLAG is permanent: ground enters through the Zorro GND pins and, later, the Molex.
- **Tooling note.** The same flags on the **root** sheet were reported as `pin_not_connected` in three different arrangements (overlapping pins, a vertical wire, a horizontal wire). The same arrangement works on sub-sheets. The flags were moved to sheet 1. This behaviour of `kicad-cli` 10.0.8 is unexplained; it is recorded here in case it reappears.

## 3. Connectivity audit (beyond ERC)

ERC cannot tell whether the wiring matches the *design intent*. The exported netlist was therefore checked by `tools/kicad/audit_sheet1.py` against tables transcribed from the TI datasheets and the Zorro pin assignment:

| Check group | Checks |
|---|---|
| All 100 J101 pins: correct net, GND, or unconnected | 100 |
| U101/U102: 16 A→Y channel mappings each (A and Y net), 4 ~OE to GND, 4 VCC, 8 GND | 2 × 48 = 96 |
| U103: per bit, A pin net, B pin goes to exactly one RN element, far side of that element is Z_Dn, RN value (16 × 4); DIR ×2, ~OE ×2, VCCA/VCCB ×4, GND ×8 | 64 + 16 = 80 |
| U104 (6 pin nets + 2 series-resistor paths × 3) and U105 (11 pin nets + unused 6Y + 2 DNP paths × 3) | 12 + 18 = 30 |
| Default-state resistors (8 pull-ups of 2.2 kΩ, 1 pull-down of 10 kΩ) | 9 |
| Decoupling: each of 17 capacitors between a rail and GND; rail counts (13 on +3V3, 4 on +5V_BUS); IC supply-pin counts (12 and 3) | 17 + 2 + 2 = 21 |
| Test-point nets | 17 |
| **Total** | **353 checks, 0 failures** |

**Round-trip check.** The generated files were re-saved by KiCad itself (`kicad-cli sch upgrade --force`). The re-saved files give the same ERC result and pass the same audit. Their netlist is identical to the original (ignoring timestamps). The committed files are KiCad's own re-saved versions.

## 4. How to reproduce

From `hardware/kicad`:

```sh
kicad-cli sch erc --severity-all --format report -o erc.txt a2000-bridgeboard.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o sheet1.net a2000-bridgeboard.kicad_sch
```

From the repo root:

```sh
python -I tools/kicad/audit_sheet1.py hardware/kicad/sheet1.net
```
