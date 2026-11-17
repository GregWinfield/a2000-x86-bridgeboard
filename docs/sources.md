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
| S1 | Radxa X4 V1.11 schematic, `https://dl.radxa.com/x/x4/radxa_x4_v1.11_schematic.pdf` (dated 2024-07-08). **Schematic sheet N = PDF page N+1** | [V]. Sheet 21 "RS2040": RP2040, 40-pin header GPIO1, BOOTSEL, P3V_RP switch. Sheet 26 "DC POWER": USB-C J9, CH224D U35, J10, rail switches. Sheet 9 "MSIC_EMMC": PLTRST_2040. Sheet 6: N100 UART1/GPIOs. Rendered and read page-by-page |
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

## Standards / general references (not fetched in this review)

| ID | Source | How used |
|---|---|---|
| S40 | USB 2.0 Specification, Table 5-9: full-speed bulk max 19 × 64-byte transactions per 1 ms frame | [K] → 1,216,000 B/s theoretical bulk payload ceiling |
| S41 | Raspberry Pi RP2040 datasheet | [K]. USB 1.1 controller + PHY (full speed 12 Mbit/s); 2× PL022 SPI; GPIO function table (GP8 SPI1 RX, GP9 SPI1 CSn, GP10 SPI1 SCK, GP11 SPI1 TX), consistent with S5 |
| S42 | Motorola MC68000 user's manual: bus cycle states S0–S7, read/write timing | [K] |
| S43 | Microsoft lifecycle: Windows 10 end of support 2025-10-14; consumer ESU to 2026-10-13; Windows 10 IoT Enterprise LTSC 2021 to 2032-01-13 | [K], TBV |
| S44 | Lattice MachXO2 family datasheet (DS1035) and configuration guide (TN1204) | [K]. Instant-on from internal flash, HC = single 2.5/3.3 V supply, dedicated JTAG. **Exact configuration time and package-migration pinout TBV** |
