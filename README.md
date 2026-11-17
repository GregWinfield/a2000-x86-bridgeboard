# A2000 x86 Bridgeboard (working name)

An open-source, modern successor to the Commodore A2386SX bridgeboard. It is a genuine **Zorro II** card for the Amiga 2000 that carries a removable x86 single-board computer (Radxa X4, Intel N100). The two systems share memory, mailboxes and interrupts through an FPGA bridge.

## Status

| Stage | Description | State |
|---|---|---|
| 1 | Architecture review | **Draft complete, awaiting review** (2026-11-18) |
| 2 | Zorro II minimum system (schematic + HDL) | Not started; sheet 1 is planned in the review §14 |
| 3 | Shared memory, SPI, interrupts | – |
| 4 | RP2040 firmware + Windows test utility | – |
| 5 | Integration, drivers, RDP investigation | – |
| 6 | PCB | – |

No schematic, HDL or firmware exists yet. Nothing in this repository is electrically or mechanically validated.

## Documents

| Document | Purpose |
|---|---|
| [docs/00-project-brief.md](docs/00-project-brief.md) | Original requirements, verbatim |
| [docs/01-architecture-review.md](docs/01-architecture-review.md) | Stage 1: block diagram, Zorro II requirements, FPGA comparison, shared-memory design, power budget, BOM summary, decisions, recommendation |
| [docs/risk-register.md](docs/risk-register.md) | Engineering risks and unknowns (maintained) |
| [docs/pin-assignment-matrix.md](docs/pin-assignment-matrix.md) | Zorro connector, X4 header and FPGA I/O allocation (maintained) |
| [docs/bom/bom-preliminary.csv](docs/bom/bom-preliminary.csv) | Preliminary BOM with AUD estimates |
| [docs/sources.md](docs/sources.md) | Source register and evidence tags used in every document |

## Planned layout

```text
docs/                  architecture, specs, registers, BOM, risks
hardware/kicad/        KiCad 10 project (hierarchical sheets 1-6)   [Stage 2+]
hdl/                   FPGA sources + constraints                   [Stage 2+]
firmware/rp2040/       RP2040 bridge firmware                        [Stage 4]
software/windows/      Windows service / test utility                [Stage 4-5]
software/amiga/        Amiga driver / library / tools                [Stage 5]
```

## Tooling

- KiCad 10.0.3 (`kicad-cli` is used for ERC reports)
- FPGA (proposed): Lattice Diamond; openFPGALoader for JTAG programming

## Licensing

To be decided (decision D-13 in the architecture review). Third-party material:
- MNT VA2000 items, if reused (Zorro II symbol/footprint), are MIT-licensed and must keep their copyright notice.
- AmiGUS hardware is CC BY-NC-ND 4.0 and is **not** to be used to derive designs.
