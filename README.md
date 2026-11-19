# A2000 x86 Bridgeboard (working name)

An open-source, modern successor to the Commodore A2386SX bridgeboard. It is a genuine **Zorro II** card for the Amiga 2000 that carries a removable x86 single-board computer (Rev 1: Radxa X4, Intel N100). The two systems share memory, mailboxes and interrupts through an FPGA bridge.

## Status

| Stage | Description | State |
|---|---|---|
| 1 | Architecture review | **Done**: decisions adopted as the [Rev 1 baseline](docs/02-rev1-baseline.md) (2026-11-18) |
| 2 | Zorro II minimum system | **Sheet 1 revision B: approved for design progression** (G-SHEET1, 2026-11-19; hardware gates open): [schematic PDF](docs/stage2/sheet1-schematic.pdf), [design notes](docs/stage2/sheet1-design-notes.md), [timing budget](docs/stage2/sheet1-timing-budget.md), [hazard analysis](docs/stage2/sheet1-hazard-analysis.md), [ERC report](docs/stage2/sheet1-erc-report.md), [HDL spec](docs/hdl/zorro-interface-spec.md), [RTL and testbenches](hdl/). HDL verification **passes** (G-SIM); exploratory Diamond STA **passes** ([STA results](docs/stage2/sheet1-sta-results.md)). **Sheet 2 revision A1 (FPGA pin assignment and configuration): G-SHEET2 approved for design progression**: [design notes](docs/stage2/sheet2-design-notes.md), [pin table](docs/stage2/sheet2-pin-assignment.md), [STA at the final pins](docs/stage2/sheet2-sta-results.md) (all Zorro paths met; host SPI path with sheet 4), [ERC report](docs/stage2/sheet2-erc-report.md), [schematic PDF](docs/stage2/sheet2-schematic.pdf) |
| 3 | Shared memory, SPI, interrupts | **Sheet 3 revision A1 (shared SRAM, arbitration, queues and interrupts): G-SHEET3 approved for design progression**: [design notes](docs/stage2/sheet3-design-notes.md), [timing budget](docs/stage2/sheet3-timing-budget.md), [HDL spec](docs/hdl/shared-memory-spec.md), [schematic PDF](docs/stage2/sheet3-schematic.pdf), [ERC report](docs/stage2/sheet3-erc-report.md). The SPI host link follows with sheet 4 **Sheet 4 revision A3 (RP2040 SPI host link): G-SHEET4 approved as a schematic baseline**: [design notes](docs/stage2/sheet4-design-notes.md), [protocol v1.0](docs/hdl/host-link-protocol.md), [timing budget](docs/stage2/sheet4-timing-budget.md), [STA results](docs/stage2/sheet4-sta-results.md), [schematic PDF](docs/stage2/sheet4-schematic.pdf), [ERC report](docs/stage2/sheet4-erc-report.md), [S4-6 isolation analysis](docs/stage2/sheet4-s46-isolation.md). C-30 approved (LCMXO2-4000HC); S4-6 rev A2 accepted, rev A3 /OE buffer for confirmation; electrical qualifications (M-16) open |
| 4 | RP2040 firmware + Windows test utility | – |
| 5 | Integration, drivers, RDP investigation | – |
| 6 | PCB | – |

**Nothing in this repository is electrically, timing- or mechanically validated.** ERC results and netlist audits are reported, but they are not validation. Before any powered hardware is installed in an A2000, gate **G-PSU** applies ([PSU measurement record](docs/test/psu-measurement-record.md)).

## Documents

| Document | Purpose |
|---|---|
| [docs/00-project-brief.md](docs/00-project-brief.md) | Original requirements, verbatim |
| [docs/01-architecture-review.md](docs/01-architecture-review.md) | Stage 1 review: block diagram, Zorro II requirements, FPGA comparison, shared memory, power budget, BOM, risks |
| [docs/02-rev1-baseline.md](docs/02-rev1-baseline.md) | Adopted decisions D-01 to D-17, owner clarifications, engineering requirements ER-1 to ER-5, gates |
| [docs/stage2/](docs/stage2/) | Sheets 1–4: design notes, timing budgets, decode hazard analysis, STA results, FPGA pin table, ERC reports, PDFs |
| [docs/hdl/zorro-interface-spec.md](docs/hdl/zorro-interface-spec.md) | FPGA Zorro II slave / AutoConfig specification (revision B) |
| [docs/hdl/host-link-protocol.md](docs/hdl/host-link-protocol.md) | RP2040 ↔ FPGA SPI host-link protocol v1.0 (normative; vectors from `tools/hostlink/hostlink.py`) |
| [docs/hdl/verification-matrix.md](docs/hdl/verification-matrix.md) | Review requirements (C-01 to C-05, C-13, sheet 3, sheet-4 requirements 1–9 and HL-1 to HL-6) mapped to tests, proofs, analyses and gates |
| [docs/risk-register.md](docs/risk-register.md) | Engineering risks and unknowns (maintained) |
| [docs/pin-assignment-matrix.md](docs/pin-assignment-matrix.md) | Zorro connector (generated from the netlist), SBC header and FPGA I/O allocation |
| [docs/bom/bom-preliminary.csv](docs/bom/bom-preliminary.csv) | Preliminary BOM with AUD estimates |
| [docs/sources.md](docs/sources.md) | Source register and evidence tags |
| [docs/test/psu-measurement-record.md](docs/test/psu-measurement-record.md) | Gate G-PSU record template |

## KiCad project

- **Open:** `hardware/kicad/a2000-bridgeboard.kicad_pro` in KiCad 10 (made with 10.0.8).
- **Libraries:** project symbols and footprints are in `hardware/kicad/lib/`, referenced through the project `sym-lib-table` and `fp-lib-table`.
- **Hierarchy:** the root sheet holds the six sheets from the brief. Sheets 1–4 are drawn; sheets 5–6 are labelled placeholders.

```text
docs/                  architecture, baseline, stage reports, specs, BOM, risks, test records
hardware/kicad/        KiCad 10 project (root + sheets 1-6, project libraries)
hdl/                   FPGA RTL, testbenches, formal, constraints   [Stages 2-4, simulation and formal passing]
firmware/rp2040/       RP2040 bridge firmware                         [Stage 4]
software/windows/      Windows service / test utility                 [Stage 4-5]
software/amiga/        Amiga driver / library / tools                 [Stage 5]
tools/kicad/           schematic bootstrap generator, netlist audits, pin-table generator
tools/fpga/            FPGA pin plan (LPF LOCATEs, schematic pins), Lattice pin-fact extracts
```

## Licensing

| Material | Licence | Text |
|---|---|---|
| Original hardware designs (`hardware/`, and `docs/` as design documentation) | **CERN-OHL-S-2.0** | [LICENSES/CERN-OHL-S-2.0.txt](LICENSES/CERN-OHL-S-2.0.txt) |
| Original HDL, firmware, software and tools | **MIT** | [LICENSES/MIT.txt](LICENSES/MIT.txt) |

Summary in [LICENSE](LICENSE); third-party material in [NOTICE.md](NOTICE.md). The CERN-OHL-S source location is this repository.
