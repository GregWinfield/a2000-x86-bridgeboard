# ERC report: project with sheet 3 revision A

**Run:** 2026-11-19, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all sheets). Raw report: [sheet3-erc-report.txt](sheet3-erc-report.txt).

**An ERC result is not a validation.** It shows only that the connectivity matches the intended, documented exceptions. Connectivity is checked separately by the netlist audits:
- `tools/kicad/audit_sheet3.py`: **120 checks, 0 failures**;
- `tools/kicad/audit_sheet1.py`: **418 checks, 0 failures**. Sheet 1 is unchanged.

| Category | Count | Where | Cause | Expected until |
|---|---|---|---|---|
| `pin_not_connected` | 66 | Root sheet | Sheet pins to the FPGA left open: 43 on sheet 1 (59 in rev B, minus LD0–LD15, now joined to sheet 3) and 23 on sheet 3 (SA0–SA17, SRAM_CE_N/OE_N/WE_N/UB_N/LB_N) | Sheet 2 |
| `isolated_pin_label` | 50 | Labels with one connection | 31 sheet-1 ZB_* labels (unchanged) and 19 sheet-3 labels (SA1–SA17, SRAM_UB_N, SRAM_LB_N), each with only its U301 pin until sheet 2 | Sheet 2 |
| `pin_not_driven` | 19 | Sheet 3 | U301 inputs A1–A17, /UB, /LB have no driver until the FPGA outputs exist. A0, /CE, /OE and /WE also carry a test point or pull-up, so ERC does not list them | Sheet 2 |
| `pin_to_pin` | 12 | Sheet 1 | U104 unused channels tied to GND (intended, unchanged from rev B) | Permanent (documented) |

**Change from the sheet 1 rev B report** (59 / 47 / 12):
- LD0–LD15 are no longer open or isolated, because the root sheet joins sheet 1's U103 A port to sheet 3's U301;
- sheet 3 adds its FPGA-side pins.

No other categories appear.
