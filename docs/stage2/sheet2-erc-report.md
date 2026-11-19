# ERC report: project with sheet 2 revision A1

**Run:** 2026-11-19, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all sheets). Raw report: [sheet2-erc-report.txt](sheet2-erc-report.txt).

**An ERC result is not a validation.** It shows only that the remaining entries are the intended, documented ones. Connectivity is checked separately by the netlist audits, all with **0 failures**:
- `tools/kicad/audit_sheet2.py`: **1046 checks**;
- `tools/kicad/audit_sheet1.py`: **418 checks** (sheet 1 unchanged);
- `tools/kicad/audit_sheet3.py`: **159 checks**.

| Category | Count | Where | Cause | Expected until |
|---|---|---|---|---|
| `pin_not_connected` | 24 | Root sheet | Sheet-2 pins for sheets 4–6, which are not yet drawn: RP_SCK, RP_CS_N, RP_MOSI, RP_MISO, RP_IRQ_N, RP_ATTN, FPGA_TCK/TMS/TDI/TDO (sheet 4); I2C_SDA, I2C_SCL, INA_ALERT_N, X4_PWR_EN, X4_PWR_FLT_N, X4_S0_SENSE (sheet 5); LED_READY, DIP_MODE_B, DIP_INT6, DIP_DISABLE, DBG0–DBG3 (sheet 6) | Sheets 4–6 |
| `isolated_pin_label` | 20 | Sheet 2 | The hierarchical labels of those 20 signals, each with only its FPGA pin. The four JTAG labels are not isolated: J201 and the pull resistors share them | Sheets 4–6 |
| `pin_to_pin` | 12 | Sheet 1 | U104 unused channels tied to GND (intended, unchanged since rev B) | Permanent (documented) |

**Change from revision A** (25 / 21 / 12): LED_FAULT is no longer an FPGA pin (C-26, option C-17b), which removes one open sheet pin and one isolated label.

No other categories appear.
