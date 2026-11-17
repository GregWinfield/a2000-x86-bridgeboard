# A2000 x86 Bridgeboard (working name)

An open-source, modern successor to the Commodore A2386SX bridgeboard. It is a genuine **Zorro II** card for the Amiga 2000 that carries a removable x86 single-board computer (Rev 1: Radxa X4, Intel N100). The two systems share memory, mailboxes and interrupts through an FPGA bridge.

## Status

| Stage | Description | State |
|---|---|---|
| 1 | Architecture review | **Done**: decisions adopted as the [Rev 1 baseline](docs/02-rev1-baseline.md) (2026-11-18) |
| 2 | Zorro II minimum system | **Sheet 1 drawn, in review**: [schematic PDF](docs/stage2/sheet1-schematic.pdf), [design notes](docs/stage2/sheet1-design-notes.md), [ERC report](docs/stage2/sheet1-erc-report.md), [HDL interface spec](docs/hdl/zorro-interface-spec.md). The HDL itself is not written yet |
| 3 | Shared memory, SPI, interrupts | Waits for gate G-SHEET1 (review of the sheet-1 open concerns) |
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
| [docs/stage2/](docs/stage2/) | Sheet 1: design notes (timing budgets, power-off isolation, safe start-up, open concerns), ERC report, PDF |
| [docs/hdl/zorro-interface-spec.md](docs/hdl/zorro-interface-spec.md) | FPGA Zorro II slave / AutoConfig interface specification |
| [docs/risk-register.md](docs/risk-register.md) | Engineering risks and unknowns (maintained) |
| [docs/pin-assignment-matrix.md](docs/pin-assignment-matrix.md) | Zorro connector (generated from the netlist), SBC header and FPGA I/O allocation |
| [docs/bom/bom-preliminary.csv](docs/bom/bom-preliminary.csv) | Preliminary BOM with AUD estimates |
| [docs/sources.md](docs/sources.md) | Source register and evidence tags |
| [docs/test/psu-measurement-record.md](docs/test/psu-measurement-record.md) | Gate G-PSU record template |

## KiCad project

- **Open:** `hardware/kicad/a2000-bridgeboard.kicad_pro` in KiCad 10 (made with 10.0.8).
- **Libraries:** project symbols and footprints are in `hardware/kicad/lib/`, referenced through the project `sym-lib-table` and `fp-lib-table`.
- **Hierarchy:** the root sheet holds the six sheets from the brief. Only sheet 1 is drawn; sheets 2–6 are labelled placeholders.

```text
docs/                  architecture, baseline, stage reports, specs, BOM, risks, test records
hardware/kicad/        KiCad 10 project (root + sheets 1-6, project libraries)
hdl/                   FPGA sources + constraints                    [Stage 2, not started]
firmware/rp2040/       RP2040 bridge firmware                         [Stage 4]
software/windows/      Windows service / test utility                 [Stage 4-5]
software/amiga/        Amiga driver / library / tools                 [Stage 5]
tools/kicad/           schematic bootstrap generator, netlist audit, pin-table generator
```

## Licensing

| Material | Licence | Text |
|---|---|---|
| Original hardware designs (`hardware/`, and `docs/` as design documentation) | **CERN-OHL-S-2.0** | [LICENSES/CERN-OHL-S-2.0.txt](LICENSES/CERN-OHL-S-2.0.txt) |
| Original HDL, firmware, software and tools | **MIT** | [LICENSES/MIT.txt](LICENSES/MIT.txt) |

Summary in [LICENSE](LICENSE); third-party material in [NOTICE.md](NOTICE.md). The CERN-OHL-S source location is this repository.
