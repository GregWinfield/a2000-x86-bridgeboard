# Source register

Every hardware statement in the project documents cites one of these IDs.
"How used" records *how* the fact was obtained, so its strength is visible.

| Tag | Meaning |
|---|---|
| **[V]** | Verified directly in the primary/official source during this review |
| **[Vs]** | Seen only through a search-engine summary of the cited page; page not opened. Confirm before relying on exact figures |
| **[M]** | Measured by us from vendor data (e.g. STEP model, schematic geometry) |
| **[D]** | Derived/calculated from [V]/[M] values |
| **[K]** | Engineering knowledge or a standard reference **not re-verified in this review**. Must be checked against the datasheet before schematic freeze |
| **[A]** | Assumption |
| **[E]** | Estimate |
| **TBV** | To be verified |

Retrieval date for all online sources: 2026-11-18.

## Radxa X4 (x86 platform)

| ID | Source | How used |
|---|---|---|
| S1 | Radxa X4 V1.11 schematic, `https://dl.radxa.com/x/x4/radxa_x4_v1.11_schematic.pdf` (dated 2024-07-08). **Schematic sheet N = PDF page N+1** | [V]. Sheet 21 "RS2040": RP2040, 40-pin header GPIO1, BOOTSEL, P3V_RP switch. **Sheet 21 detail (read for sheet 4, 2026-11-19):** the RP2040's IOVDD1–6 and VREG_VIN are on P3V_RP (ADC_AVDD through L10; USB_VDD instead on P3V3_A through R304, R303 to P3V3_S not fitted), decoupled by C206 10 µF and C207, C209–C212 0.1 µF (10.5 µF), switched from the header's P3V3_S by P-MOSFET Q32 (CJ3139K); its gate is pulled low through R481 by NPN Q33 (2SC5658), whose base node is pulled up to P3V3_S (R482 10k) and grounded by key K4 through R485 (D41 ESD), with no gate-source pull-up on Q32. RUN is pulled low by Q29 from the N100's RST_RP2040; BOOTSEL by Q30 from RECOVERY_RP2040. Header pins 1 and 17 carry P3V3_S. Sheet 26 "DC POWER": USB-C J9, CH224D U35, J10, rail switches. Sheet 9 "MSIC_EMMC": PLTRST_2040. Sheet 6: N100 UART1/GPIOs. Rendered and read page-by-page |
| S2 | Radxa X4 docs, power input, `https://docs.radxa.com/en/x/x4/hardware/power-input` | [V]. J10 "2-Pin 2.54mm pitch power input header (designator J10, silkscreen PWR-IN)", pin 1 GND, pin 2 ADP12V_IN, 12 V DC, reverse-polarity warning |
| S3 | Radxa X4 FAQ, `https://docs.radxa.com/en/x/x4/faq` | [V]. Header accepts 12 V DC "consistent with the 12V USB Type-C PD power specification"; recommended PD adapter 12 V ≥ 2.5 A; "Do not supply 5V to this header" |
| S4 | Radxa X4 overview/spec, `https://docs.radxa.com/en/x/x4` | [V]. 85 mm × 56 mm; LPDDR5 4/8/12/16 GB; M.2 M-key 2230 NVMe (no SATA); optional eMMC; 2× micro-HDMI; 2.5 GbE; 3× USB 3.2 + 1× USB 2.0 Type-A; power "USB Type-C PD (supports 12V, and the current >= 2.5A under 12V)"; 1× power button, 1× BOOTSEL button, fan header, RTC header |
| S5 | Radxa X4 GPIO definition, `https://docs.radxa.com/en/x/x4/software/gpio` | [V]. 40-pin table (v1.110) matches S1 sheet 21 pin-for-pin. Note: page also shows a different "before v1.110" table |
| S6 | Radxa X4 RP2040 flashing, `https://docs.radxa.com/en/x/x4/software/flash` | [V]. BOOTSEL button or host GPIO script (`gpioset gpiochip0 17/7`) then UF2 drag-and-drop |
| S7 | Radxa X4 V1.11 3D model, `https://dl.radxa.com/x/x4/radxa_x4_3d_pcba.zip` (`radxa_x4_v1.11_3d_20241120.stp`, Creo export) | [M]. 698 placed bodies, all identity transforms. Bounding boxes computed with a local script |
| S8 | Radxa X4 product brief, `https://dl.radxa.com/x/x4/radxa_x4_product_brief.pdf` | [Vs]. BIOS PL1 = 6 W; recommended supply ≥ 18 W without USB loads, 25 W with full USB load |
| S9 | Power measurements: Jeff Geerling `https://github.com/geerlingguy/sbc-reviews/issues/48`; CNX Software review `https://www.cnx-software.com/2024/09/29/radxa-x4-review-an-intel-n100-alternative-to-raspberry-pi-5-tested-with-ubuntu-24.04/`; Tom's Hardware `https://www.tomshardware.com/raspberry-pi/radxa-x4-review`; bret.dk `https://bret.dk/intel-n100-radxa-x4-first-thoughts/`; Radxa forum `https://forum.radxa.com/t/radxa-x4-power-input-and-consumption-measurements/26093` | [Vs]. Idle 4.84–9.1 W, load 16.9–21.2 W, one 27.3 W peak. Forum: X4 boots from 9 V and 12 V on J10, not 5 V; a post mentions a 2.0 mm header on some boards |

## Zorro II / Amiga

| ID | Source | How used |
|---|---|---|
| S10 | *The Zorro III Bus Specification* as Appendix K of the Amiga Hardware Manual on Amiga Developer CD 2.1. Mirror: `https://discmaster.textfiles.com/file/18/Amiga%20Developer%20CD%20v2.1.iso/Reference/HTML/Hardware_Manual_guide/` nodes 028F, 029B, 029C, 029E, 029F, 02A0, 02A1, 02A2, 02A5, 02BE, 02C7, 02C8 | [V]. Zorro II signal semantics, driver types, automatic DTACK, /SLAVE timing (35 ns / 50 ns), XRDY (60 ns), AutoConfig registers, /BUSRST, open-collector list |
| S11 | Hardware Book, Zorro II/III connector, `https://isa.umh.es/micros/doc/hwb/co_Zorro.html` (credits "Amiga 4000 User's Guide") | [V]. Complete 100-pin table with Zorro II names |
| S12 | MNT VA2000 graphics card, `https://github.com/mntmn/amiga2000-gfxcard` (MIT licence, © 2016 Lukas F. Hartmann / MNT) | [V]. `kicad/zorro2port_exp.lib` pin list matches S11 pin-for-pin. `kicad/zorro2.pretty/zorro2card.kicad_mod`: 2×50 pads at 2.54 mm, 1.524 × 5 mm, even pins on F.Cu. `va2000-spartan6/va2000.v`: DOE-gated buffers, XRDY tri-stated, CFGOUT logic. 74LVC8T245 translators. Board outline 127 × 96 mm |
| S13 | AmiGUS, `https://github.com/necronomfive/AmiGUS-pub` | [V]. Licences: PCB CC BY-NC-ND 4.0; base software GPL-3.0+; drivers LGPL-3.0. Public repo has FPGA **binaries only**, no HDL |
| S14 | Dave Haynie, A2000/B2000 power budget, `https://www.devili.iki.fi/mirrors/haynie/systems/amiga2k/docs/power.txt` | [V]. System limits +5 V 20.0 A, +12 V 8.0 A, −5 V 0.3 A, −12 V 0.3 A, +5 USER 0.5 A. Per-device and per-slot suggested budgets. 4 A per-slot connector note |
| S15 | Ian Stedman, Amiga PSU guide, `https://www.ianstedman.co.uk/?p=20` | [Vs] only; the site was unreachable (DNS failure) when fetched. Summary claims A1500/A2000 variants of +5 V 20.5 A / +12 V 8 A and +5 V 17.25 A / **+12 V 3 A**. **Unverified** |
| S16 | Amiga Developer CD 2.1 BB guide, `386bb.html` (AMIGAplus Sonderheft 18) | [Vs]. A2386SX: Janus handler segment A0000 or D0000 (PCPrefs), 1 MB RAM. No Amiga-side Janus memory map found |
| S17 | rdesktop for Amiga: Aminet `comm/tcp/rdesktop` (OS4 PPC build, 2006); amiga-news.de 2005–2007 notices of AmigaOS 68k/MorphOS builds; "RDesktopMUI" | [Vs]. A historical 68k RDP client existed; current availability TBV |

## Components and pricing

Prices are snapshots taken through search results on 2026-11-18. They are indicative only; confirm live before purchase.

| ID | Source | How used |
|---|---|---|
| S20 | Lattice LCMXO2-2000HC-4TG144C: LCSC (C5340501), DigiKey DE, Octopart | [Vs]. 2112 LUTs, 111 I/O, 75,776 RAM bits, 144-LQFP. LCSC ≈ USD 6.29–6.53 (9–19 in stock). DigiKey DE ≈ €16.28 (1 pc), 52-week factory lead time |
| S21 | Lattice iCE40HX4K-TQ144: DigiKey (220-1572-ND), LCSC (C1521989) | [Vs]. 3520 LUTs, 107 I/O, 81,920 RAM bits. DigiKey US USD 10.20 (332 stock). DigiKey AU AUD 16.34 ex GST. LCSC ≈ USD 16.03 |
| S22 | Gowin GW1N-UV4LQ144 (JLCPCB C5173870); GW1N-UV9LQ144 (Mouser) | [Vs]. UV4 price not shown. UV9 ≈ USD 39.52 (1 pc, Mouser) |
| S23 | Microchip ATF1508AS-10AU100: DigiKey, RS, LCSC | [Vs]. 128 macrocells, 80 I/O, TQFP-100, Active. DigiKey US USD 16.13 (≈1.7k stock) |
| S24 | ISSI IS61WV25616EDBLL-10TLI: LCSC (C883296), Farnell (2901196), Octopart | [Vs]. 4 Mbit (256K×16), 10 ns, 2.4–3.6 V, TSOP-II-44. LCSC ≈ USD 2.65 (869 stock). Farnell ≈ USD 6.17 |
| S25 | Renesas 70V28L15PFG dual-port SRAM (64K×16), DigiKey AU/UK/IE | [Vs]. DigiKey AU ≈ AUD 231 (1 pc). UK £117.69. 18-week lead time |
| S26 | TI SN74LVC16T245DGGR (LCSC C148170); TI SN74AVC4T774PWR (FindChips/TME) | [Vs]. LCSC ≈ USD 0.70 (2.3k stock); AVC4T774 ≈ USD 0.42–1.65 |
| S27 | TI TPS25947 eFuse, `https://www.ti.com/product/TPS25947`; Mouser 595-TPS259472LRPWR etc. | [Vs]. 2.7–23 V, 28 mΩ, 5.5 A, 28 V abs max, withstands −15 V. OV clamp options (3.8/5.7/13.8 V) or adjustable OVLO. ILIM 0.5–6 A. True reverse-current blocking. 2 × 2 mm 10-pin HotRod QFN. ≈ USD 1.29–2.17 (1 pc) |
| S28 | TI TPS25740B USB PD source controller, `https://ti.com/product/TPS25740B` | [Vs]. Pin-selectable 5/9/12/15 V or 5/9/15/20 V profiles, external NFET power path. Datasheet Rev C (2018) |
| S29 | CNX Software, "What a difference two years make? Comparing SBC prices in 2024 and 2026", `https://www.cnx-software.com/2026/04/28/what-a-difference-two-years-make-comparing-sbc-prices-in-2024-and-2026/` | [V] (fetched). Radxa X4 8 GB USD 79.96 at launch → USD 265.99 in April 2026 (3.33×, RS UK ex VAT). Cause: RAM/storage price rises since late 2025. Stock-outs noted |
| S30 | RS Components Radxa X4 4 GB listings, `https://uk.rs-online.com/web/p/rock-sbc-boards/0329065`, `.../0329066` | [Vs]. 4 GB no-eMMC £62.22 (indicative). 4 GB/32 GB £65.34 ex VAT, out of stock until 2026-01-22 at time of index. AliExpress ≈ USD 60 |
| S31 | DFRobot LattePanda Mu, `https://www.dfrobot.com/product-2820.html` | [Vs]. N100 module, 9–20 V input. Launch USD 139. Lite carrier USD 39 |

## Stage 2 (sheet 1) datasheets: downloaded and read directly, 2026-11-18

| ID | Source | How used |
|---|---|---|
| S45 | TI SN74LVC16244A data sheet, SCAS699C (Aug 2003, rev. June 2014), `https://www.ti.com/lit/ds/symlink/sn74lvc16244a.pdf` | [V]. DGG pinout; tpd ≤ 4.1 ns at 3.3 V ±0.3 V (−40 to 85 °C); inputs 5.5 V-tolerant at any VCC; Ioff |
| S46 | TI SN74LVCH16T245 data sheet, SCES635B (rev. Apr 2015), `https://www.ti.com/lit/ds/symlink/sn74lvch16t245.pdf`; plus SN74LVC16T245 SCES636B (rev. Apr 2015) for pinout comparison | [V]. Pinout (identical in both, checked by diff); function table; DIR/OE referenced to VCCA; VCC isolation; Ioff; bus-hold (no pull resistors; IBHLO 900 µA at 5.5 V read from the rendered table); switching at VCCA 3.3 V / VCCB 5 V; OE pull-up recommendation |
| S47 | TI SN74LVC2T45 data sheet, SCES516N (rev. June 2024), `https://www.ti.com/lit/ds/symlink/sn74lvc2t45.pdf` | [V]. DCT/DCU pinout; DIR function; VCC isolation; Ioff; A→B tPLH ≤ 4.4 ns / tPHL ≤ 4.0 ns at VCCA 3.3 V, VCCB 5 V |
| S48 | TI SN74LVC07A data sheet, SCAS595W (rev. Oct 2016), `https://www.ti.com/lit/ds/symlink/sn74lvc07a.pdf` | [V]. PW pinout; open-drain; 5.5 V-tolerant I/O; Ioff; tpd ≤ 3.6 ns at 3.3 V |
| S49 | Lattice MachXO2 Family Data Sheet FPGA-DS-02056-4.7 (2026), `https://www.latticesemi.com/view_document?document_id=38834` | [V]. I/O tri-stated with weak pull-down before and during configuration; IPU/IPD 26–309 / 30–305 µA; tREFRESH 1.4 ms (XO2-2000), 2.4 ms (XO2-4000); tPD 7.24 ns (−4, best case, LVCMOS25 8 mA, 0 pF); PLL fIN ≥ 7 MHz; TQFP-144 = 111 GPIO (Table 4.4). Supersedes the [K] entry S44. **C-30 (MachXO2-4000):** TQFP-144 = 115 GPIO, banks 0–5 = 28/29/29/9/10/10 (Table 4.5); static core current (HC, blank pattern, 25 °C) typ 8.45 mA (2000HC 4.80 mA, Table 3.10); programming/erase current typ 26.8 mA (2000HC 22.1 mA, Table 3.11) |
| S50 | = S10, used for the sheet-1 timing rules | [V] |

## Stage 2 (sheet 1 revision B): read directly, 2026-11-18

| ID | Source | How used |
|---|---|---|
| S51 | Commodore A2000 Rev 6 (A2000-CR, 312721) schematic, redrawn edition rev. 1.38 (2012), `https://www.amigawiki.org/dnl/schematics/A2000_R6.pdf` | [V]. Schematic sheet 6 (PDF page 7): U606 74LS32 /CFGIN–/CFGOUT OR chain, RP607 1 kΩ pull-downs on /CFGOUT1–5. Sheet 8 (PDF page 9): RP800 1 kΩ pull-ups to +5 V on /SLAVE1–5 into Buster U800. Power-on reset (LM339 U805, C814 22 µF, R805 47 kΩ, PST518B), giving ≈ 0.7 s [D]. Third-party document: read only, nothing copied into the project |
| S52 | Dave Haynie, "100 Pin Expansion Signals on Amiga Computers", 20 July 1987 (troff source `100pin.nr`), mirror `https://www.devili.iki.fi/mirrors/haynie/systems/amiga2k/docs/100pin.nr` | [V]. Empty slots pass /CFGOUT→/CFGIN on the motherboard; a card must monitor /BERR and be ready to tri-state its on-bus buffers whenever it is asserted; read-data buffers consider /UDS//LDS "in case the cycle actually turns out to be a read-modify-write cycle"; DOE enables card data buffers and its timing differs between read and write; read data enabling is delayed for collision detection |
| S53 | TI SN74LVC8T245 data sheet, SCES584D (June 2005, rev. May 2026), `https://www.ti.com/lit/ds/symlink/sn74lvc8t245.pdf` | [V]. PW pinout; A→B 0.5–4.4 ns, OE→B enable 0.9–6.8 ns, disable 0.8–6.3 ns at VCCA 3.3 V ±0.3 V / VCCB 5 V ±0.5 V; VCC isolation below 100 mV or floating; Ioff; inputs on both ports always active; OE pull-up for Hi-Z during power-up and power-down |
| S54 | TI SN74LVC1G00 data sheet, SCES212AC (rev. Aug 2026), `https://www.ti.com/lit/ds/symlink/sn74lvc1g00.pdf` | [V]. DBV pinout; tpd 1.0–4.7 ns at 3.3 V ±0.3 V (CL 30/50 pF, −40 to 85 °C); Ioff |
| S55 | TI SN74LVC32A data sheet, SCAS286U (rev. July 2024), `https://www.ti.com/lit/ds/symlink/sn74lvc32a.pdf` | [V]. PW pinout; tpd 1.0–3.8 ns at 3.3 V ±0.3 V (−40 to 85 °C); inputs 5.5 V-tolerant |
| S56 | TI TPS3808 data sheet, SBVS050N (rev. Aug 2026), `https://www.ti.com/lit/ds/symlink/tps3808.pdf` | [V]. DBV pinout; VIT− 3.07 V (G33), 0.405 V (G01); accuracy; CT open 12–28 ms; MR 90 kΩ internal pull-up, 1 ns pulse width; open-drain RESET valid from VDD ≥ 0.8 V; SENSE→RESET ≤ 20 µs; pull-up 10 kΩ–1 MΩ |
| S57 | Motorola M68000 8-/16-/32-Bit Microprocessors User's Manual, 9th edition (Freescale reprint), retrieved from the Internet Archive copy of `https://www.nxp.com/docs/en/reference-manual/MC68000UM.pdf` (NXP blocked automated download) | [V]. Read-modify-write cycle states S0–S19 (§4.1.3, §5.1.3); AC timing §10.10 (8 MHz): #11 address to /AS ≥ 30 ns, #13 address hold ≥ 40 ns, #14A DS width (write) ≥ 140 ns, #20A R/W valid ≤ 10 ns after /AS, #25 data hold ≥ 40 ns, #26 data valid before DS ≥ 40 ns, #29A data-in Hi-Z ≤ 187 ns. Supersedes the [K] entry S42 |
| S58 | Dave Haynie, Buster-2 chip specification (A3000), mirror `https://www.devili.iki.fi/mirrors/haynie/chips/buster/docs/buster2.pdf` | [V]. DOE driven by Buster for Zorro II cycles; collision detection from multiple /SLAVEn before data buffers are enabled; automatic Zorro II DTACK held off by XRDY. A3000 part: used for corroboration of signal semantics only |
| S59 | YosysHQ OSS CAD Suite, release 2026-10-31, `oss-cad-suite-windows-x64-20261031.tgz` from `https://github.com/YosysHQ/oss-cad-suite-build/releases/tag/2026-10-31` | Tool provenance: SHA-256 `4e845291d99e1711e4c3a005661132deef8f8cc0afaf1e3fd0f4811cc103e783` matched the published value. Contains Icarus Verilog, Yosys, SymbiYosys, nextpnr-machxo2. **Not yet executed** on the development machine |
| S60 | Lattice Diamond 3.14 (3.14.0.75.2) installed help: *Constraints Reference Guide* (MAXDELAY, OUTPUT LOAD, TEMPERATURE, VOLTAGE, BLOCK) and *Diamond Project Tcl Commands*, `C:/lscc/diamond/3.14/docs/webhelp/eng/` (published 2024-10-08) | [V]. MAXDELAY FROM/TO with optional MIN (hold); OUTPUT LOAD default 0 pF; default derating 1.0 = TJ 85 °C commercial / 100 °C industrial; BLOCK ASYNCPATHS affects pad→FF frequency analysis only; prj_project / prj_syn / prj_run syntax |

| S61 | ISSI IS61/64WV25616EDBLL datasheet, Rev. A2 (2020-07-14), `https://www.issi.com/WW/pdf/61-64WV25616EDBLL.pdf`. ISSI's site refuses automated download; the copy used is the web.archive.org capture of 2022-11-16 of that URL (14 pages) | [V]. TSOP-II-44 pin configuration; −10 read/write AC table; DC table (VDD 2.4–3.6 V, VIH 2.0 V); package outline 44L 400 mil TSOP-II rev F. Used for sheet 3, the SRAM model and the timing budget |
| S62 | Lattice Diamond 3.14 reports for LCMXO2-2000HC-4TG144C/I from this project's runs (2026-11-19): PAR pad report (pinout by pin number, bank VCCIO, dual functions, "Reserved: sysCONFIG" for TMS/TCK/TDI/TDO with JTAG_PORT=ENABLE) and map report ("Number of PIO sites used: n + 4(JTAG) out of 112"); default SYSCONFIG (SDM_PORT=DISABLE, JTAG_PORT=ENABLE) | [V] (tool output). Pin reassessment, fit tests |

| S63 | Lattice **MachXO2-2000 Pinout** CSV, revision 1.2 (Feb 2014), `https://www.latticesemi.com/view_document?document_id=42568`; **MachXO2-4000 Pinout** CSV, revision 1.5 (27 Mar 2026), document 42571; MachXO2 144-pin TQFP package migration file (document 39444) | [V]. TQFP144: 112 I/O pads on the 2000 (banks 28/28/28/8/10/10) and 115 on the 4000; 12 VCCIO, 4 VCC, 12 GND, 4 NC (2000); dual functions (PCLK, configuration, JTAG). Pin reassessment, C-19, sheet 2 assignment and the 4000HC migration check. **The repository keeps facts-only TQFP144 extracts** (`tools/fpga/*_TQFP144_pins.csv`) with the source files' SHA-256, not the files themselves |
| S64 | Lattice **MachXO2 Hardware Checklist**, FPGA-TN-02154-2.2 (document 39095); **MachXO2 Programming and Configuration Usage Guide**, FPGA-TN-02155-5.1 (document 39085); **MachXO2 sysIO Usage Guide**, FPGA-TN-02158-2.4 (document 39083) | [V]. Decoupling (VCC 2 × 10 µF + 100 nF per pin; VCCIO 10 µF + 100 nF per pin), configuration-pin pull-ups (4.7 kΩ; TCK 4.7 kΩ pull-down; JTAGENB 1 kΩ for JTAG mode), "SN and PROGRAMN not driven low when erased" |
| S65 | Raspberry Pi **RP2040 datasheet**, build 2025-02-20 (3184e62), `https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf` | [V]. PADS_BANK0 reset state (input, pull-down, Schmitt, 4 mA), drive 2/4/8/12 mA, IIOVDD_MAX 50 mA, IO electrical characteristics (Table 625). Supersedes the [K] use of S41 for these facts. **Read for S4-6 rev A1:** voltage at IO −0.5 to IOVDD + 0.5 V (Table 622, absolute maximum); at IOVDD 3.3 V VIH 2.0 V to IOVDD + 0.3 V, VIL ≤ 0.8 V, VOH ≥ 2.62 V at the rated IOH of the drive setting, VOL ≤ 0.5 V; RPU, RPD 50–80 kΩ; IIOVDD_MAX and IIOVSS_MAX 50 mA (sums over all GPIO/QSPI pins); no per-pin current rating (Table 625) |
| S66 | TI **SN74AVC4T774** data sheet, SCES693I (rev. Feb 2025), `https://www.ti.com/lit/ds/symlink/sn74avc4t774.pdf` | [V]. Independent DIR per channel, Ioff, VCC isolation (both ports Hi-Z if either supply is at GND), 1.1–3.6 V supplies, ±12 mA at 3.0–3.6 V. Host-link translators (sheet 4), C-17b. **Read for sheet 4 rev A (2026-11-19):** data inputs VIH ≥ 2.0 V, VIL ≤ 0.8 V at VCCI 2.7–3.6 V (§5.3); "all unused data inputs … must be held at VCCI or GND" (§5.3 note 3); input transition ≤ 5 ns/V; Ioff ≤ ±1 µA (−40 to 85 °C); at VCCA 3.3 V ± 0.3 V: A→B 0.1–2.9 ns (VCCB 3.3 V), ≤ 3.3 ns (VCCB 2.5 V), B→A 0.1–2.8 ns (§5.10); function table (/OE, DIR); §8: OE pulled up to VCCA guarantees Hi-Z during supply ramps, and "OE inputs may also be tied to GND to keep device enabled" |
| S67 | ECS Inc. **ECS-2520MV** SMD MultiVolt oscillator data sheet (rev. 2026), `https://ecsxtal.com/store/pdf/ECS-2520MV.pdf` | [V]. 0.75–160 MHz; ±50 ppm (BN option, −40 to +85 °C); 1.6–3.6 V; 15 pF CMOS load; rise/fall ≤ 7 ns; duty 45/55 %; start-up ≤ 5 ms; 8.0 mA max at 3.3 V, 50 MHz; pad 1 tri-state (≥ 0.7 Vdd or NC = active), 2 GND, 3 output, 4 Vdd; part code 500 = 50.000 MHz. Sheet 2 X201 |
| S68 | TI **TLV7011, TLV7021, TLV7012, TLV7022** comparator data sheet, SLVSDM5F (rev. March 2020), `https://www.ti.com/lit/ds/symlink/tlv7011.pdf` | [V]. DBV/DCK (SOT-23-5/SC70-5) pinout 1 OUT, 2 VEE, 3 IN+, 4 IN−, 5 VCC; supply 1.6–5.5 V; ICC 5 µA typ, 10 µA max; VIO ±8 mV max; hysteresis 1.2–14 mV; common mode VEE to VCC + 0.1 V; tPHL/tPLH 260/310 ns typical (no maximum); inputs diode-clamped to VEE only, abs max 6 V regardless of VCC; TLV7021 open-drain output abs max 6 V regardless of VCC, "can be pulled beyond VCC"; power-on reset holds the TLV702x output high-impedance while the supply ramps (§7.4); tON 20 µs. Sheet 4 U405 (S4-6 rev A1) |
| S69 | Price and stock snapshot for **LCMXO2-4000HC-4TG144C**, web search 2026-11-19: LCSC C1521625 (about USD 8.00 1-off, low stock), Future Electronics (USD 20.15, 3,365 in stock), DigiKey (USD 22.72 1-off, via an aggregator), Arrow (about USD 17.80 via an aggregator) | [Vs]: listing pages and aggregators without retrieval dates; confirm with the distributor before ordering. BOM item 1 (C-30) |

## Standards / general references (not fetched in this review)

| ID | Source | How used |
|---|---|---|
| S40 | USB 2.0 Specification, Table 5-9: full-speed bulk max 19 × 64-byte transactions per 1 ms frame | [K] → 1,216,000 B/s theoretical bulk payload ceiling |
| S41 | Raspberry Pi RP2040 datasheet | [K]. USB 1.1 controller + PHY (full speed 12 Mbit/s); 2× PL022 SPI; GPIO function table (GP8 SPI1 RX, GP9 SPI1 CSn, GP10 SPI1 SCK, GP11 SPI1 TX), consistent with S5 |
| S42 | Motorola MC68000 user's manual: bus cycle states S0–S7, read/write timing | [K] |
| S43 | Microsoft lifecycle: Windows 10 end of support 2025-10-14; consumer ESU to 2026-10-13; Windows 10 IoT Enterprise LTSC 2021 to 2032-01-13 | [K], TBV |
| S44 | Lattice MachXO2 family datasheet (DS1035) and configuration guide (TN1204) | [K]. Instant-on from internal flash, HC = single 2.5/3.3 V supply, dedicated JTAG. **Exact configuration time and package-migration pinout TBV** |
