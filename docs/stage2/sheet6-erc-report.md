# ERC report: complete project with sheet 6 revision A

**Run:** 2026-11-21, KiCad 10.0.8, `kicad-cli sch erc --severity-all` on the root schematic (all six sheets).
- Raw report: [sheet6-erc-report.txt](sheet6-erc-report.txt).
- Schematic PDF of the whole project: [sheet6-schematic.pdf](sheet6-schematic.pdf). Sheet 6 is page 7; it supersedes the earlier sheet PDFs for sheets 4 and 5.

**An ERC result is not a validation.** It shows only that the remaining entries are the intended, documented ones. Connectivity is checked by the netlist audits, all with **0 failures**:

| Audit | Checks | Mutation test |
|---|---|---|
| `audit_sheet6.py` (new) | **189** | **26 of 26** |
| `audit_sheet5.py` | 274 | 28 of 28 |
| `audit_sheet4.py` | 226 (R432–R434 added) | 30 of 30 |
| `audit_sheet3.py` | 159 | – |
| `audit_sheet2.py` | 1180 (sheet-6 nets connected; no open net left) | – |
| `audit_sheet1.py` | 418 | – |

**Remaining entries: 14, all permanent and documented, identical to every earlier report** (scripted comparison):

| Category | Count | Where | Cause |
|---|---|---|---|
| `pin_to_pin` | 12 | Sheet 1 | U104's unused channels tied to GND (since rev B) |
| `pin_to_pin` | 2 | Sheet 4 | U401 A4 and U403 A4 spare channels (since sheet 4 rev A) |

**Change from sheet 5 revision A** (39 entries: 13 / 12 / 14):
- the 8 sheet-2 pins and 5 sheet-4 pins for sheet 6 are now connected: 13 `pin_not_connected` and 12 `isolated_pin_label` entries fewer;
- **no sheet pin is open any more.**

**Also checked:**
- **No `power_pin_not_driven`.** U601's VCCB is on DBG_VREF, which is fed through D608 (passive) and so carries PWR_FLAG #FLG6001. A first run without it reported one entry, which this flag fixed.
- No duplicate references; no annotation errors.
- The netlist outside sheet 6 is identical to sheet 5 revision A, except U403 A1–A3, which reach FPGA_TCK/TMS/TDI through R432–R434 (S6-5).
