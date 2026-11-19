# ERC report: project with sheet 2 revision A

**Run:** 2026-11-19, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all sheets). Raw report: [sheet2-erc-report.txt](sheet2-erc-report.txt).

**An ERC result is not a validation.** It shows only that the remaining entries are the intended, documented ones. Connectivity is checked separately by the netlist audits, all **0 failures**:
- `tools/kicad/audit_sheet2.py`: **1047 checks**;
- `tools/kicad/audit_sheet1.py`: **418 checks** (sheet 1 unchanged);
- `tools/kicad/audit_sheet3.py`: **159 checks**. It now also expects one FPGA pin on every SA, SRAM and LD net, and R208 on SA17.

| Category | Count | Where | Cause | Expected until |
|---|---|---|---|---|
| `pin_not_connected` | 25 | Root sheet | Sheet-2 pins for sheets 4–6, which are not yet drawn: RP_SCK, RP_CS_N, RP_MOSI, RP_MISO, RP_IRQ_N, RP_ATTN, FPGA_TCK/TMS/TDI/TDO (sheet 4); I2C_SDA, I2C_SCL, INA_ALERT_N, X4_PWR_EN, X4_PWR_FLT_N, X4_S0_SENSE (sheet 5); LED_READY, LED_FAULT, DIP_MODE_B, DIP_INT6, DIP_DISABLE, DBG0–DBG3 (sheet 6) | Sheets 4–6 |
| `isolated_pin_label` | 21 | Sheet 2 | The hierarchical labels of those 21 signals, each with only its FPGA pin. The four JTAG labels are not isolated: J201 and the pull resistors share them | Sheets 4–6 |
| `pin_to_pin` | 12 | Sheet 1 | U104 unused channels tied to GND (intended, unchanged since rev B) | Permanent (documented) |

**Change from the sheet 3 rev A1 report** (66 / 50 / 19 / 12):
- All entries caused by the missing FPGA are gone:
  - the 66 open sheet 1/3 sheet pins;
  - the 50 isolated ZB_*, SA and SRAM labels;
  - the 19 undriven U301 inputs.
- ZF_OVR_N and ZF_DTACK_N are not FPGA pins (owner decision C-17). Their sheet-1 pins carry no-connect flags on the root sheet, and R106/R107 on sheet 1 hold them inactive.
- During this revision, one `power_pin_not_driven` entry was resolved for X201 VDD. VDD_OSC is sourced through the passive bead FB201, so a permanent PWR_FLAG marks it as driven.
- Duplicate references (sheet 1 already used `#PWR0201`–`#PWR0210`) were resolved: sheet-2 power symbols are numbered from `#PWR2001`.

No other categories appear.
