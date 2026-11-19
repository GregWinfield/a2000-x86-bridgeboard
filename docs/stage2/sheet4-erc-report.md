# ERC report: project with sheet 4 revision A1 and sheet 2 revision A2

**Run:** 2026-11-19, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all sheets). Raw report: [sheet4-erc-report.txt](sheet4-erc-report.txt). Schematic PDF of the whole project: [sheet4-schematic.pdf](sheet4-schematic.pdf) (sheet 4 is page 5).

**An ERC result is not a validation.** It shows only that the remaining entries are the intended, documented ones. Connectivity is checked separately by the netlist audits, all with **0 failures**:
- `tools/kicad/audit_sheet4.py`: **204 checks**. It detects 17 of 17 injected wiring and value faults (mutation test: [sheet4-design-notes.md](sheet4-design-notes.md) §6.5);
- `tools/kicad/audit_sheet2.py`: **1100 checks** (FPGA_TDO reaches U402; since C-30, U201 is the LCMXO2-4000HC, checked against the 4000 pinout);
- `tools/kicad/audit_sheet1.py`: **418 checks** (sheet 1 unchanged);
- `tools/kicad/audit_sheet3.py`: **159 checks** (sheet 3 unchanged).

| Category | Count | Where | Cause | Expected until |
|---|---|---|---|---|
| `pin_not_connected` | 19 | Root sheet | 14 sheet-2 pins for sheets 5–6, which are not yet drawn: I2C_SDA, I2C_SCL, INA_ALERT_N, X4_PWR_EN, X4_PWR_FLT_N, X4_S0_SENSE (sheet 5); LED_READY, DIP_MODE_B, DIP_INT6, DIP_DISABLE, DBG0–DBG3 (sheet 6). Plus 5 sheet-4 pins for sheet 6: LED_RP0–LED_RP3 (the RP2040 LEDs, C-26) and RP_JTAG_EN_N (the JTAG-option DIP switch) | Sheets 5–6 |
| `isolated_pin_label` | 18 | Sheets 2 and 4 (KiCad lists them under the root) | The hierarchical labels of the 14 sheet 5–6 signals on sheet 2, each with only its FPGA pin, and LED_RP0–LED_RP3 on sheet 4, each with only its U404 output. RP_JTAG_EN_N is not isolated: U403's OE and R407 share it | Sheets 5–6 |
| `pin_to_pin` | 12 | Sheet 1 | U104 unused channels tied to GND (intended, unchanged since rev B) | Permanent (documented) |
| `pin_to_pin` | 2 | Sheet 4 | U401 A4 and U403 A4: spare translator channels (DIR high, A→B) with the A input tied to GND and the B output open: "all unused data inputs of the device must be held at VCCI or GND" [V S66, §5.3 note 3]. The warning is the bidirectional pin meeting the GND net's PWR_FLAG | Permanent (documented) |

**Change from sheet 2 revision A1** (24 / 20 / 12):
- the ten host-link and JTAG pins of sheet 2 are now connected to sheet 4;
- sheet 4 adds 5 open pins and 4 isolated labels toward sheet 6, and 2 spare-channel warnings.

No other categories appear. In particular:
- no `power_pin_not_driven`: X4_3V3_REF, fed through J401, carries a PWR_FLAG;
- no duplicate references;
- no annotation errors.

**Revision A1 / A2 (2026-11-19):**
- Re-run after S4-6 rev A1 (comparator U405, R426–R430, C409; R416, R417 and RP_VIO removed) and C-30 (U201 from the 4000HC pinout).
- Same 51 entries in the same categories. U405's open-drain output on RP_EN_N, with the R429 pull-up, raises no ERC entry.
