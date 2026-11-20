# ERC report: project with sheet 5 revision A

**Run:** 2026-11-20, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all sheets).
- Raw report: [sheet5-erc-report.txt](sheet5-erc-report.txt).
- Schematic PDF of the whole project: [sheet5-schematic.pdf](sheet5-schematic.pdf). Sheet 5 is page 6. This PDF supersedes [sheet4-schematic.pdf](sheet4-schematic.pdf) for sheet 4, which gained one hierarchical label.

**An ERC result is not a validation.** It shows only that the remaining entries are the intended, documented ones. Connectivity is checked separately by the netlist audits, all with **0 failures**:

| Audit | Checks | Note |
|---|---|---|
| `tools/kicad/audit_sheet5.py` | **274** | New. It detects **28 of 28** injected wiring and value faults (mutation test, [sheet5-design-notes.md](sheet5-design-notes.md) §6) |
| `tools/kicad/audit_sheet2.py` | 1139 | Was 1105. The six sheet-5 nets of sheet 2 are now checked as connected nets: they reach sheet 5, open-drain drivers have a pull-up, the discrete open drain on X4_S0_SENSE is recognised, inout I²C members are allowed to be `input`. The open-net count is now 8 (sheet 6) |
| `tools/kicad/audit_sheet4.py` | 220 | Unchanged in count. ER-3 now allows sheet 5's R518 on X4_3V3_REF (≤ 3 µA through R519 1 MΩ); the sheet-4 mutation test still detects 29 of 29 |
| `tools/kicad/audit_sheet1.py` | 418 | |
| `tools/kicad/audit_sheet3.py` | 159 | |

**The netlist outside sheet 5 is identical to sheet 4 revision A3**: no pin changed net, no value changed, no part added or removed (scripted comparison).

| Category | Count | Where | Cause | Expected until |
|---|---|---|---|---|
| `pin_not_connected` | 13 | Root sheet | 8 sheet-2 pins for sheet 6: LED_READY, DIP_MODE_B, DIP_INT6, DIP_DISABLE, DBG0–DBG3. 5 sheet-4 pins for sheet 6: LED_RP0–LED_RP3 and RP_JTAG_EN_N | Sheet 6 |
| `isolated_pin_label` | 12 | Sheets 2 and 4 (listed under the root) | The 8 sheet-6 hierarchical labels on sheet 2, and LED_RP0–LED_RP3 on sheet 4 | Sheet 6 |
| `pin_to_pin` | 12 | Sheet 1 | U104's unused channels tied to GND (unchanged since rev B) | Permanent (documented) |
| `pin_to_pin` | 2 | Sheet 4 | U401 A4 and U403 A4 spare channels (unchanged since sheet 4 rev A) | Permanent (documented) |

**Change from sheet 4 revision A3** (51 entries: 19 / 18 / 14):
- the six sheet-5 pins of sheet 2 (I2C_SDA, I2C_SCL, INA_ALERT_N, X4_PWR_EN, X4_PWR_FLT_N, X4_S0_SENSE) are now connected: 6 `pin_not_connected` and 6 `isolated_pin_label` fewer;
- the 14 `pin_to_pin` entries are identical (scripted comparison).

**What else was checked:**
- **No `power_pin_not_driven`.** +3V3 is driven by U504 OUT and +5V_BUS by U503 OUT, both `power_out`. X4_12V_EF is driven by U501 OUT. The fused inputs +12V_F and +5V_F, fed through passive fuses, carry PWR_FLAGs #FLG5001 and #FLG5002.
- **Sheet 1's two temporary PWR_FLAGs removed.** These were the PWR_FLAGs on +3V3 and +5V_BUS (and their two power symbols), placed "until sheet 5 exists".
  - Kept, they would now give power-output-to-power-output errors.
  - They were removed from the committed sheet-1 file and from the generator. The generator's `#PWR` counter skips their two numbers, so no other reference changed.
  - The sheet-1 netlist is unchanged (418 checks).
- **Sheet 4** exports X4_3V3_REF through a hierarchical label at its PWR_FLAG, replacing a local label that overlapped TP405's label. Local and hierarchical labels of the same name on a sheet are one net: the netlist has a single `/X4_3V3_REF` with all sheet-4 members plus R518.
- No duplicate references; no annotation errors.
- U501/U503 AUXOFF carry no-connect flags. U504's NC pins are typed `no_connect`.
