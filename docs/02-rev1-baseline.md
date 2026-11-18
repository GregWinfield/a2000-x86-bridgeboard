# Revision 1 baseline: adopted decisions and engineering requirements

**Status:** adopted 2026-11-18 by the project owner, after reviewing [01-architecture-review.md](01-architecture-review.md).
**Change control:** any change to a baseline item needs a dated entry in the change log at the end of this file.

## 1. Adopted decisions

All recommended decisions D-01 to D-17 from the review §11.1 are adopted. Where the owner added a clarification, it is shown as a **[clarification]**.

| ID | Decision (Rev 1 baseline) | Owner clarification / consequence |
|---|---|---|
| D-01 | Power the x86 SBC through the documented **J10 12 V input**; no USB-C PD source | **[clarification]** The USB-C backfeed issue is **not** resolved by a removable port cap. A mechanically secured solution or other protection must be investigated; see §3. R-05 stays open |
| D-02 | **Lattice LCMXO2-2000HC-4TG144C** (migration path LCMXO2-4000HC) | **[clarification]** Subject to FPGA timing and pin verification. Pin budget: [pin-assignment-matrix.md](pin-assignment-matrix.md). Timing: [stage2/sheet1-design-notes.md](stage2/sheet1-design-notes.md) §4, which needs Diamond STA |
| D-03 | **64 KB AutoConfig window by default**, 512 KB linear mode selectable | Confirmed. Register map: [hdl/zorro-interface-spec.md](hdl/zorro-interface-spec.md) |
| D-04 | **512 KB conventional SRAM** (IS61WV25616EDBLL-10TLI) | Confirmed |
| D-05 | **Radxa X4 4 GB** for prototyping | **[clarification]** The x86 platform must stay replaceable (ER-4) |
| D-06 | **Windows 10 Pro for development** | Support limitations acknowledged (R-19). The hardware stays OS-agnostic |
| D-07 | Ribbon connection to the SBC GPIO header | Adopted |
| D-08 | **Two-slot occupancy acceptable for Rev 1** | **[clarification]** Prefer a single-slot future revision if practical (track in Stage 6; candidate: a module-based SBC, review §12) |
| D-09 | Internal SBC ports + Wi-Fi first; bracket extension leads after the mechanical check | Adopted |
| D-10 | **INT2 default**, INT6 selectable | Adopted; selection is in FPGA logic (both lines wired) |
| D-11 | Fit the INA226 telemetry on prototypes | Adopted (sheet 5) |
| D-12 | RP2040-driven JTAG for field FPGA updates, behind a DIP-controlled translator enable | Adopted (sheets 4 and 6) |
| D-13 | **CERN-OHL-S-2.0** for original hardware; **MIT** for original HDL, firmware and software | **[clarification]** Subject to third-party licensing obligations. Implemented: [LICENSE](../LICENSE), [LICENSES/](../LICENSES), [NOTICE.md](../NOTICE.md) |
| D-14 | Prototype AutoConfig manufacturer ID 2011 ($07DB); obtain or choose a final ID before release | Adopted, TBV (R-18) |
| D-15 | Network path for RDP decided in Stage 5 | Adopted |
| D-16 | Auto-start the SBC after a delay (default 5 s), DIP-selectable | Adopted |
| D-17 | **New Janus-style protocol**; original Janus binary compatibility is not required initially | **[clarification]** Confirmed |

## 2. Additional engineering requirements (owner, 2026-11-18)

| ID | Requirement | Where it is addressed | Status |
|---|---|---|---|
| ER-1 | Confirm the complete /SLAVEn timing path, including input and output buffers, against the 35 ns requirement | [stage2/sheet1-timing-budget.md](stage2/sheet1-timing-budget.md) (rev B: U104 SN74LVC8T245, 29.8 ns budget); [stage2/sheet1-hazard-analysis.md](stage2/sheet1-hazard-analysis.md); [hdl/zorro-interface-spec.md](hdl/zorro-interface-spec.md) §6 | **Partly closed.** Buffer stages verified from datasheets. The FPGA stage needs Diamond STA (G-STA), then a hardware measurement |
| ER-2 | Preserve an XRDY wait-state provision; do not assume zero-wait SRAM timing is proven until measured | XRDY driver fitted on sheet 1 (U105 ch. 3, R105). HDL default is **XRDY-gated mode**; zero-wait is an opt-in register bit enabled only after measurement | Implemented in schematic and specification |
| ER-3 | Include power-off isolation, signal backfeed prevention and safe FPGA start-up behaviour in the review | Sheet-1 notes rev B §5 (isolation), §6 (card enable: the slot looks empty whenever the card is not operational; state table) and §7 (defaults) | Done for sheet 1 (rev B, verification pending G-SIM); repeat for sheets 2–5 |
| ER-4 | Preserve the ability to use a different x86 SBC in a future revision | SBC-specific circuitry is confined to sheet 4 ("x86 SBC interconnect"), behind a generic host-link interface (SPI + IRQ + ATTN + optional JTAG, with SBC-powered isolating translators) and a generic 12 V SBC power output (sheet 5). Sheets 1–3 and the HDL Zorro/SRAM logic must not reference X4-specific facts | Rule adopted; checked at each sheet review |
| ER-5 | Require actual A2000 PSU measurements before installing powered hardware | **Gate G-PSU:** no powered prototype goes into an A2000 until [test/psu-measurement-record.md](test/psu-measurement-record.md) is completed for that machine and reviewed (procedure: review §8.6) | Gate defined |

## 3. D-01 follow-up: USB-C backfeed protection options (R-05)

**Problem (verified).** On the Radxa X4, the USB-C VBUS pins and J10 sit on the same net (`ADP12V_IN`), with no switch between them (schematic sheet 26). The X4's USB-C port is **power-only**: its D+/D− and SBU pins are unconnected on that sheet [V S1 sh.26]. While the carrier feeds J10, the receptacle is live at 12 V. If a USB-C charger were plugged in, it would see the back-voltage. The carrier's eFuse reverse-current blocking protects the A2000; it does nothing for the external charger.

| Option | Description | Protects the external device? | Cost / complexity | Notes |
|---|---|---|---|---|
| A. Removable cap | Push-in USB-C dust cap | Only while fitted | Trivial | **Rejected by the owner** as insufficient on its own |
| **B. Secured shroud** | A bracket that is part of the SBC mounting frame, screw-fixed to the standoffs. It physically covers the receptacle opening without touching the connector; tool required to remove; labelled "12 V LIVE" | Yes, while installed (removing it needs a tool) | Low (printed or sheet-metal part) | **Recommended baseline.** No mechanical load on the X4 connector. Design in Stage 6 using the STEP model; verify the gap prevents plug insertion |
| C. Captive blanking plug | A USB-C plug with no electrical contacts connected, held in the receptacle by a screwed bracket | Yes | Low | Alternative to B. Risk: stress on the receptacle from tolerance stack. Needs a careful bracket design |
| D. Detection (complements B or C) | Use the INA226 on the carrier's 12 V output: if the SBC is running while our current is about 0 (or the eFuse reports reverse blocking), an external source is present. The FPGA keeps our eFuse off, raises a fault and tells both sides | Detects; does not prevent | Logic only (sheet 5 + HDL) | Recommended in addition to B |
| E. Feed through USB-C with a PD source | Carrier PD source (e.g. TPS25740B-class) and a captive cable into the X4 USB-C; J10 unused | Yes (port occupied) | Higher: PD controller, 5 V/12 V path, ±5 % compliance | Fallback if B/C prove impractical or a future SBC lacks a raw-DC input |

**Recommendation.** Use **B (secured shroud) plus D (detection)** for Rev 1, with C as the mechanical alternative and E as the electrical fallback. R-05 stays **Open** until the shroud is designed and checked against the X4 STEP model (Stage 6) and the detection is specified on sheet 5 and in the HDL.

## 4. Gate list (must pass before the named step)

| Gate | Before | Condition |
|---|---|---|
| G-SHEET1 | Starting sheet 3 (SRAM) | Owner review of sheet 1 **revision B** and its open concerns ([stage2/sheet1-design-notes.md](stage2/sheet1-design-notes.md) §9) |
| G-SIM | Freezing sheet 2 (FPGA pinout); any hardware bring-up | `bash hdl/run_checks.sh` reports `ALL HDL CHECKS PASSED`: lint, bus-functional and chain testbenches (random seeds and delay corners), netlist structure check, gate-level hazard test E1, formal prove/bmc/cover ([hdl/verification-matrix.md](hdl/verification-matrix.md)) |
| G-STA | Freezing the FPGA choice and pinout | Lattice Diamond post-place-and-route analysis at the chosen pins, −4 grade (or the grade bought): every MAXDELAY path ≤ 18 ns at the slow corner (VCCIO min, TJ max), **both edges**, 10 pF load; minimum delays recorded and the hazard setup requirement S_req ≤ (M-7 slot setup − 3 ns) ([stage2/sheet1-timing-budget.md](stage2/sheet1-timing-budget.md) §9) |
| G-PSU (ER-5) | Installing any powered prototype in an A2000 | PSU measurement record completed and reviewed |
| G-ZEROWAIT (ER-2) | Enabling zero-wait mode | Scope or logic-analyser measurement of real cycles on the target A2000 shows the data-valid and DTACK margins |
| G-R05 | Shipping or handing out any carrier with an SBC fitted | Secured USB-C shroud fitted, and detection logic active |

## Change log

| Date | Change |
|---|---|
| 2026-11-18 | Baseline created from owner approval of the Stage 1 review, with clarifications D-01, D-02, D-03/04, D-05, D-06, D-08, D-13, D-17 and requirements ER-1 to ER-5 |
| 2026-11-18 | Sheet 1 detail: data transceiver is **SN74LVCH16T245** (bus-hold) instead of SN74LVC16T245. Reason: the Zorro data bus floats between cycles, and TI requires defined input levels (SCES636B); bus-hold removes the need for pull resistors, which TI advises against combining with bus-hold. Pinout identical. Also added 22 Ω series arrays on D0–D15 (values TBV) and default-state pull resistors (2.2 kΩ, chosen against the MachXO2 weak pull-down) |
| 2026-11-18 | **Sheet 1 revision B** (owner review of C-01 to C-05, new C-13): (1) U104 is an **SN74LVC8T245** with /OE = CARD_EN_N = NAND(EN_OK, ZF_ARM); EN_OK = two TPS3808 supervisors (+3V3, +5V_BUS) wired-AND with a DISABLE jumper; the FPGA arms only inside /BUSRST. (2) U107 ORs CARD_EN_N into the U103 /OE, XRDY and /INTx, so a card that is not operational looks like an empty slot (C-03 → High, C-04 → Medium). (3) /BERR is buffered into the FPGA instead of CDAC [S52]. (4) HDL: data-strobe-phase FSM for RMW (C-13), strobe- and /BERR-qualified buffer enable, registered window state frozen during cycles. (5) New gate **G-SIM**; G-STA made explicit. Carrier BOM estimate now AUD 77.52–206.98 (was 73.47–194.58) |
