# Project brief (as supplied, 2026-11-18)

> This is the original requirements brief, kept verbatim so that every later
> document can be checked against it. Changes to requirements should be made
> here with a dated note, not silently in other documents.

# Project: Amiga 2000 Modern x86 Bridgeboard

You are my senior digital hardware engineer, FPGA developer and KiCad design assistant.

We are designing an affordable, open-source, modern successor to the Commodore A2386SX PC bridgeboard for the Amiga 2000.

Our objective is to produce **real, editable, electrically validated KiCad schematics**, followed by FPGA firmware, host software and eventually a manufacturable PCB.

Do not rush into generating a PCB. We will design, review and validate the hardware in stages.

## 1. Project objectives

Create a genuine Zorro II expansion card containing an independently operating x86 computer running Windows 10 Pro.

The x86 motherboard must be removable/replaceable, not soldered permanently to the custom Zorro PCB.

Windows must eventually be accessible inside a native AmigaOS Workbench window using RDP, with potential future support for seamless individual Windows application windows.

The Zorro II interface must provide real hardware integration inspired by the original Commodore Janus bridgeboards:

- Zorro II AutoConfig
- Shared memory accessible to both systems
- Bidirectional command mailboxes
- Interrupt signalling and acknowledgement
- Hardware status registers
- Safe independent startup, shutdown and reset
- Potential for future filesystem and peripheral sharing

Original Janus binary compatibility would be desirable, but is not an initial requirement.

**Design priorities:** Low cost, reliability, repairability, open-source licensing and readily obtainable parts.

## 2. Proposed x86 platform

Initial candidate: Radxa X4, Intel N100.

This board contains an RP2040 microcontroller connected to the Intel CPU through internal USB/UART interfaces.

Investigate using its exposed RP2040 SPI/GPIO pins to communicate with our custom FPGA/CPLD bridge.

Use the official Radxa X4 schematics and documentation to verify every relevant pin and voltage.

Do not assume that the complete interface or desired communication speed is supported without verification.

The x86 motherboard must attach to the custom carrier through replaceable connectors and mechanical mounting.

Investigate cheaper alternative boards where appropriate.

## 3. Zorro II design

Support the original Commodore A2000 Zorro II expansion bus.

Use verified technical specifications and existing open-source reference designs.

Required:

- Correct Zorro II edge connector and pinout
- AutoConfig implementation
- Address decoding
- 16-bit data interface
- Bus-cycle timing and DTACK
- Bidirectional data buffering
- Safe 5 V to 3.3 V interfacing
- Interrupt handling
- Shared-memory access arbitration
- Correct startup, shutdown and reset behaviour

A small FPGA or CPLD should handle all timing-sensitive Zorro bus operations. The RP2040 must not be responsible for responding to individual Zorro bus cycles in software.

Do not include ISA.

DMA is not required for revision 1.

## 4. Shared-memory architecture

Investigate a 128 KB to 512 KB shared SRAM arrangement, starting with a 128 KB requirement similar to the original A2386SX.

The Amiga must access this through memory-mapped Zorro II addresses.

The Intel CPU accesses the same logical memory through its onboard RP2040, using a protocol such as SPI.

The FPGA manages memory arbitration, access permissions and synchronization.

Investigate dual-port SRAM versus conventional SRAM with arbitration, comparing cost and complexity.

Define a robust mailbox protocol with ownership flags, sequencing, error reporting, timeouts and interrupts.

Distinguish true shared physical SRAM from a software-maintained copy. Document all consistency guarantees.

## 5. Power

The card must be powered from the A2000's internal four-pin Molex peripheral power connector.

Do not draw operating power from Zorro II power pins.

Zorro II ground connections must be retained.

Investigate:

- +12 V to Radxa via compliant USB-C PD circuitry
- +5 V and +3.3 V regulator requirements
- Input fuses and reverse-polarity protection
- Filtering and decoupling
- Power sequencing
- Bus isolation when either system is unpowered
- Prevention of backfeeding through I/O pins
- Existing A2000 PSU load capacity

Do not assume that 12 V / 2.5 A of additional loading is available from every A2000 PSU.

Provide a power budget, including startup peaks, and a recommended verification procedure before hardware installation.

## 6. Physical design

Target a mechanically compatible A2000 expansion card.

Verify actual slot dimensions, mounting position, component height, airflow and clearance against adjacent cards.

The x86 computer must be field-replaceable.

Prefer low-cost PCB fabrication and readily sourced parts.

Provide test points, a programming/debug connector and useful diagnostic LEDs.

## 7. Reference projects

Study these sources:

- https://github.com/mntmn/amiga2000-gfxcard
- https://github.com/necronomfive/AmiGUS-pub
- https://docs.radxa.com/en/x/x4
- https://dl.radxa.com/x/x4/radxa_x4_v1.11_schematic.pdf
- Commodore A500/A2000 Technical Reference Manual
- Commodore A2386SX and Janus technical documentation

Identify which designs and techniques are reusable.

Check licensing carefully. Do not copy or create derivatives of third-party material whose licences prohibit it.

## 8. KiCad deliverables

Create an organised KiCad project with separate hierarchical sheets:

1. Zorro II interface and AutoConfig
2. FPGA/CPLD and configuration
3. Shared SRAM and arbitration
4. Radxa X4 interconnection
5. Power regulation and protection
6. Interrupts, diagnostics and programming

Maintain:

- A system architecture document
- A complete pin-assignment matrix
- Component-selection and availability rationale
- A bill of materials with estimated AUD costs
- A register and memory-map specification
- An engineering risk/unknowns register
- Version-controlled KiCad source files

Use real manufacturer components, verified symbols, correct footprints and named nets.

Run KiCad Electrical Rules Check (ERC) and report the findings. Do not claim a schematic is electrically or mechanically validated merely because ERC passes.

## 9. Development stages

**Stage 1 — Architecture review**

Analyse feasibility, compare affordable implementation choices, identify unknowns and select candidate hardware.

**Stage 2 — Zorro II minimum system**

Create schematic and HDL for a minimal AutoConfig card with test registers and safe bus interfacing.

**Stage 3 — Shared memory**

Add SRAM, FPGA arbitration, SPI interface and interrupts.

**Stage 4 — RP2040 communication**

Develop firmware and a Windows-side test utility for reading and writing shared memory.

**Stage 5 — Integration**

Add Windows boot/control services and Amiga-side drivers. Investigate RDP connectivity separately.

**Stage 6 — PCB**

Only after schematic, logic, component availability and power design reviews have passed, begin PCB layout.

## 10. Engineering rules

- Never invent pinouts, voltages or electrical specifications.
- Cite datasheets and reference designs for hardware decisions.
- Mark assumptions explicitly.
- Calculate FPGA I/O requirements before selecting a device.
- Compare at least two realistic FPGA/CPLD options.
- Prioritise components actually available in low quantities.
- Avoid unnecessary high-speed interfaces such as PCIe unless justified.
- Keep prototype and eventual production costs visible.
- Produce actual KiCad project files, not images pretending to be schematics.
- Stop and flag any unresolved electrical safety or bus-timing issue.

## First task

Do not start drawing the full schematic yet.

First produce:

1. A proposed hardware block diagram.
2. A Zorro II signal/interface requirements table.
3. An FPGA/CPLD comparison with approximate cost.
4. A shared-memory architecture comparison.
5. A preliminary power budget.
6. A preliminary BOM.
7. A list of unresolved design decisions and feasibility risks.

Then recommend the lowest-cost credible revision 1 architecture and explain your reasoning.

Once we have reviewed that architecture, proceed with the first KiCad schematic sheet.
