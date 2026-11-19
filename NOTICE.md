# Third-party notices and reference material

This file lists third-party material that the design uses or was checked against, and the terms that apply to each.

| Item | Used how | Licence / terms | Obligation |
|---|---|---|---|
| **MNT VA2000** (`github.com/mntmn/amiga2000-gfxcard`), © 2016 Lukas F. Hartmann / MNT Media and Technology UG | **Reference only.** Zorro II pin list and edge-connector pad geometry (2.54 mm pitch, 1.524 × 5 mm pads, even pins on F.Cu) used as a cross-check. AutoConfig $48/$4A/$4C handling and /CFGOUT gating checked as corroboration. The project's symbol, footprint and HDL specification were re-created from Commodore documentation and datasheets, not copied | MIT | None required for facts. If any VA2000 file is ever copied, keep its MIT notice next to it |
| **KiCad libraries** (symbols Device:R, Device:C, Device:R_Pack04, Device:FerriteBead, Connector:TestPoint, Connector_Generic:Conn_01x06, Jumper:Jumper_2_Open, power:+3V3, power:GND, power:PWR_FLAG; footprints from Package_SO, Package_QFP, Oscillator, Resistor_SMD, Capacitor_SMD, Inductor_SMD, Connector_PinHeader_2.54mm, TestPoint) | Embedded in the schematic and referenced as footprints | CC-BY-SA 4.0 with the KiCad library exception for designs that use the libraries | None for designs using the libraries (see the KiCad library licence) |
| **AmiGUS** (`github.com/necronomfive/AmiGUS-pub`) | Licence check only; **nothing derived** | PCB: CC BY-NC-ND 4.0 | Do not derive from the AmiGUS PCB or schematic |
| **Commodore** Zorro III Bus Specification / Amiga Hardware Manual (Amiga Developer CD 2.1) | Facts (pinout, timing rules, AutoConfig protocol) | Commodore copyright (historic) | Facts only; no large verbatim reproduction |
| **Radxa X4** schematic, documentation and 3D model | Interface facts and measurements | Published by Radxa | Link to the originals; their files are not redistributed here |
| **Texas Instruments, Lattice** datasheets | Pin and timing data, cited by document number | Manufacturer copyright | Cite; do not redistribute PDFs |
| **Lattice MachXO2 pinout files** (documents 42568, 42571) | `tools/fpga/*_TQFP144_pins.csv` hold **facts only**: pin number, pad name, bank, dual function, differential pair, for the TQFP144 package. Each records the source revision and SHA-256. The vendor files are not redistributed | Manufacturer copyright (source files) | Cite; download the full files from Lattice (URLs in the extracts and in sources S63) |
