# Sheet 1: ERC and connectivity verification report (revision B)

**Date:** 2026-11-18.
**Tool:** KiCad 10.0.8 `kicad-cli`.
**Input:** `hardware/kicad/a2000-bridgeboard.kicad_sch` (whole hierarchy).
**Command:** `kicad-cli sch erc --severity-all` (default project rule severities).
**Raw report:** [sheet1-erc-report.txt](sheet1-erc-report.txt).

> An ERC result with only expected items does **not** mean the design is electrically, timing- or mechanically validated. It only means no rule the checker knows about was broken unexpectedly. The open engineering concerns are in [sheet1-design-notes.md](sheet1-design-notes.md) §9.

## 1. Result (118 items, all expected)

| Severity | Rule | Count | Items | Assessment |
|---|---|---|---|---|
| Error | `pin_not_connected` | 59 | Hierarchical **sheet pins** of sheet 1 on the root sheet: 32 × ZB_* (now including ZB_BERR_N; ZB_CDAC removed), 16 × LD*, 10 × ZF_* (now including ZF_ARM), EN_OK | **Expected.** Sheet 1's interface to sheet 2 (FPGA), which is not drawn yet |
| Warning | `isolated_pin_label` | 47 | Sheet-1 hierarchical labels ZB_A1–ZB_A23, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_E7M, ZB_CFGIN_N, ZB_BUSRST_N, ZB_BERR_N and LD0–LD15. Each connects to a single pin on this sheet | **Expected**, same cause. ZB_AS_N is absent because it also has TP114 |
| Warning | `pin_to_pin` | 12 | "Bidirectional and Power output connected": U104 pins 5–10 (A3–A8) and 14–19 (B8–B3) tied to GND, which carries the GND PWR_FLAG | **Expected and intended (rev B).** The unused channels of the SN74LVC8T245 must not float: inputs on both ports are always active [V S53]. With DIR = A→B, the B pins drive low into ground when enabled, which is the same level |
| All other rules | – | **0** | Power-pin drive, output↔output conflicts, dangling wires and labels, no-connect misuse, duplicate references, library-symbol mismatches, label naming | – |

**Not suppressed.**
- The 106 interface items disappear once sheet 2 connects the interface.
- The 12 tie-off warnings are permanent and are listed here on purpose. They are not hidden with ERC exclusions, so any **new** pin-to-pin warning stands out.

## 2. Temporary items that affect ERC

- **PWR_FLAGs on `+3V3` and `+5V_BUS` (sheet 1, top right).** They declare these rails as driven until sheet 5 exists. Remove them then (C-12).
- **GND PWR_FLAG.** Permanent: ground enters through the Zorro GND pins and, later, the Molex.
- **Tooling note (revision A).** Flags on the root sheet gave spurious `pin_not_connected` reports, which is why they are on sheet 1.

## 3. Connectivity audit (beyond ERC)

`tools/kicad/audit_sheet1.py` checks the exported netlist against tables transcribed from the TI datasheets and the Zorro pin assignment:

| Check group | Checks |
|---|---|
| All 100 J101 pins: correct net, GND, or unconnected (pin 15 CDAC now unconnected) | 100 |
| U101/U102: 16 A→Y mappings each (Z_BERR_N → ZB_BERR_N on U102 4A4/4Y4), 4 ~OE, 4 VCC, 8 GND | 96 |
| U103: per-bit A/B/RN paths; DIR; **~OE on DBUF_OE_G_N**; VCCA/VCCB; GND | 80 |
| **U104 SN74LVC8T245:** 22 pin nets (DIR, ~OE = CARD_EN_N, A1/A2, unused A3–A8 and B3–B8 to GND, VCCA, VCCB ×2, GND ×3), value, 2 series-resistor paths × 3 | 29 |
| U105: 11 pin nets (inputs now INT2_G_N, INT6_G_N, XRDY_G), unused 6Y, 2 DNP paths × 3 | 18 |
| Default-state resistors (8 × 2.2 kΩ pull-ups, 1 × 10 kΩ pull-down) | 9 |
| **Card enable (rev B):** EN_OK / ZF_ARM / CARD_EN_N / DBUF_OE_G_N pulls (4); U106 pins (5); U107 pins (14); U108/U109 pins, CT open, values, U108 SENSE (13); divider values and ends (3); JP101 (1); EN_OK open-drain drivers = U108 + U109 only (1) | 41 |
| Decoupling: each of 22 capacitors between a rail and GND; rail counts (17 on +3V3, 5 on +5V_BUS); IC supply-pin counts (16 and 4) | 26 |
| Test-point nets (TP101–TP119) | 19 |
| **Total** | **418 checks, 0 failures** |

**Round-trip.** The generated files are re-saved by KiCad itself (`kicad-cli sch upgrade --force`) before ERC, export and audit. The committed files are KiCad's own re-saved versions.

## 4. How to reproduce

From `hardware/kicad`:

```sh
kicad-cli sch erc --severity-all --format report -o erc.txt a2000-bridgeboard.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o sheet1.net a2000-bridgeboard.kicad_sch
```

From the repo root:

```sh
python -I tools/kicad/audit_sheet1.py hardware/kicad/sheet1.net
python -I tools/kicad/pinmatrix_sheet1.py hardware/kicad/sheet1.net
```
