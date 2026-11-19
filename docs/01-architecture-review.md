# Stage 1: Architecture review

**Project:** A2000 x86 Bridgeboard (working name)
**Document status:** Draft for review, revision A, 2026-11-18
**Scope:** The seven items from the brief's "First task" (see [00-project-brief.md](00-project-brief.md)) plus a recommended revision-1 architecture.
**Not in scope yet:** schematics, HDL, firmware.

> **Update 2026-11-18.** The owner adopted D-01 to D-17 with clarifications; see [02-rev1-baseline.md](02-rev1-baseline.md). During sheet 1 (Stage 2) the data transceiver changed from SN74LVC16T245 to the bus-hold variant **SN74LVCH16T245**; see [stage2/sheet1-design-notes.md](stage2/sheet1-design-notes.md). In sheet 1 **revision B** the /SLAVEn and /CFGOUTn driver changed from SN74LVC2T45 to an output-enabled **SN74LVC8T245** behind card-enable gating. As a result, an unpowered or unconfigured card no longer blocks downstream AutoConfig, which this review still describes in §2 and §8. /BERR also replaced CDAC on the input buffers. See the [baseline change log](02-rev1-baseline.md). This review is otherwise kept as the Stage 1 record.

Evidence tags (`[V]`, `[Vs]`, `[M]`, `[D]`, `[K]`, `[A]`, `[E]`, TBV) and source IDs (`S1`…) are defined in [sources.md](sources.md). Anything tagged `[K]`, `[A]` or TBV must be closed before the relevant schematic sheet is frozen.

---

## 1. Summary

### 1.1 Headline findings (these changed the brief's assumptions)

1. **The X4 has a documented raw 12 V input, so no USB-C PD source is needed.** J10 is a 2-pin 2.54 mm "PWR-IN" header: pin 1 GND, pin 2 `ADP12V_IN`, 12 V DC [V S2, S3]. On the schematic, J10 sits directly on the same net as the USB-C VBUS, with no switch between them [V S1 sh.26]. The USB-C PD sink is a CH224D strapped to request 12 V (R441 = 24 kΩ) [V S1 sh.26].
2. **The RP2040 link is real but slow.** The RP2040 connects to the N100 over **USB 1.1 full-speed**: USB_DP/DM go to N100 USB2 port 6 through 0 Ω links [V S1 sh.21]. There is also a UART: GP0/GP1 to N100 UART1 [V S1 sh.21, sh.6]. Full-speed bulk has a theoretical ceiling of **1.216 MB/s** [K S40]. Realistically expect about 1 MB/s and about 1 ms per request/response from Windows [E].
3. **The RP2040 is not always-on.** It is powered from the S0-only rail `P3V3_S`, and its RUN pin is tied to a buffered copy of the N100's platform reset (`PLTRST_2040`) [V S1 sh.21, sh.9, sh.26]. The bridge link therefore drops whenever Windows reboots, sleeps or shuts down. The RP2040 cannot supervise or power on the X4.
4. **The Zorro II rules force specific design choices** [V S10]:
   - /SLAVEn must assert within **35 ns** of /AS, so the decode must be combinational.
   - The motherboard generates a zero-wait-state /DTACK automatically, so the card never needs to drive /DTACK.
   - AutoConfig logic must reset on /BUSRST.
   - An unconfigured card holds /CFGOUTn negated, which stalls AutoConfig for every board downstream. That makes an **instant-on** FPGA a reliability requirement.
5. **True dual-port SRAM is not worth it.** The Renesas 70V28L15PFG (64K×16) costs about AUD 231 each [Vs S25]. A 256K×16 conventional SRAM costs about USD 2.65–6.17 [Vs S24]. The PC side is serial (SPI) anyway, so dual-port brings no benefit.
6. **The X4 will not fit within one Zorro slot's depth.** The measured envelope is 88.7 × 60.2 × 21.5 mm, and the stacked USB-A ports rise **16.2 mm** above the X4 PCB [M S7]. Mounted on standoffs, it intrudes into the neighbouring slot. Rev 1 should accept **two-slot occupancy**.
7. **The X4's cost has become volatile.** The 8 GB model went from USD 79.96 in 2024 to USD 265.99 in April 2026 [V S29]. The 4 GB model is still about USD 60 / £62 [Vs S30].
8. **Windows 10 Pro is out of support.** Support ended 2025-10-14, and consumer ESU ended 2026-10-13 [K S43, TBV]. The OS choice is a decision for you (D-06).

### 1.2 Recommended rev-1 architecture (detail in §12)

- **x86 board:** an unmodified Radxa X4 (4 GB acceptable) on M2.5 standoffs. It has two field-replaceable connections:
  - a short 40-way ribbon to its GPIO header for the RP2040 SPI link;
  - a 2-wire lead into J10 for 12 V.
- **Logic:** one Lattice MachXO2-2000HC (TQFP-144): instant-on, single 3.3 V supply. It handles every Zorro cycle, AutoConfig, the SRAM arbiter, registers, mailbox doorbells, interrupts and the SPI slave.
- **Shared memory:** 512 KB conventional async SRAM (IS61WV25616, 256K×16) on a local bus shared with the Zorro data transceiver. Arbitration gives the Zorro side priority, so cycles run with zero wait states using the automatic DTACK.
- **Bus interface:** a dual-supply transceiver for D0–D15 (5 V on the Zorro side, with VCC isolation), 5 V-tolerant buffers for address and control, and open-drain drivers for /INT2, /INT6 and XRDY.
- **X4-side isolation:** translators whose X4-side supply is the X4's own 3.3 V header pin. When the X4 is off, they go high-impedance automatically.
- **Power:** taken from the 4-pin Molex only.
  - **+12 V path:** fuse, TVS, then a TPS25947 eFuse with OVLO, UVLO, current limit, soft-start, reverse blocking and an FPGA-controlled enable, then current/voltage telemetry, then the X4's J10.
  - **+5 V path:** fuse/PTC, TVS, reverse-polarity protection, then the translator 5 V rail and a 3.3 V LDO.
  - The Zorro power pins are left unconnected. All Zorro ground pins are connected.
- **Estimated cost:** carrier ≈ **AUD 73–193** per prototype board. X4 + SSD + cooler ≈ **AUD 160–255** (4 GB X4). Excludes Windows licence, shipping and tools. See §10 and [bom/bom-preliminary.csv](bom/bom-preliminary.csv).

---

## 2. Verified Radxa X4 facts that drive the design

| # | Fact | Evidence |
|---|---|---|
| X1 | J10 PWR-IN: 2-pin 2.54 mm, pin 1 GND, pin 2 `ADP12V_IN`, 12 V DC; do not feed 5 V | [V S2, S3]; schematic part `HD_TH1X2_2D54_STA` [V S1 sh.26]. A forum post reports a 2.0 mm header on some boards [Vs S9], so **check the pitch on the actual board** |
| X2 | J10 and USB-C VBUS share `ADP12V_IN`. TVS6 (SMBJ18CA), a 2.2 Ω + 10 µF snubber, and no load switch to `ADP12V` are drawn | [V S1 sh.26] |
| X3 | The CH224D PD sink requests 12 V via R441 = 24 kΩ (table on sheet: 6.8 k = 9 V, 24 k = 12 V, 56 k = 15 V, NC = 20 V). The GATE pin is not connected | [V S1 sh.26] |
| X4 | `ADP12V` feeds the 5 V buck U33 (JW5068C, `P5V_A`) and the 3.3 V buck U34 (JW5168B, `P3V3_A`; sheet notes "OCP 19 A, load 12 A"). Load switches Q22/Q23 (FKBB3006) switch these to `P5V_S`/`P3V3_S` from `VCC_EN`, which derives from `PM_SLP_S3_L` via Q25/Q26, so the `_S` rails are S0-only (polarity detail TBV; the rail naming and SLP_S3 control agree) | [V S1 sh.26] |
| X5 | Header pins 1 and 17 (3.3 V) = `P3V3_S` (S0-only). Header pins 2 and 4 (5 V) = `P5V_A` through D42 (1N5819), so the header 5 V cannot power the board | [V S1 sh.21] |
| X6 | RP2040 USB → N100 USB2 port 6 (R301/R302, 0 Ω). UART0 GP0/GP1 ↔ N100 UART1 (R314/R315, 0 Ω). GP23 ↔ N100 SMI_GPIO via R316 = **NC** | [V S1 sh.21] |
| X7 | RP2040 supply `P3V_RP` comes from `P3V3_S` through Q32 (CJ3139K). RUN is tied via R309 (0 Ω) to `PLTRST_2040`, a buffered PLTRST# (33 Ω). The N100 can also pulse RUN (`RST_RP2040`, GPP_B17, Q29) and force BOOTSEL (`RECOVERY_RP2040`, Q30) | [V S1 sh.21, sh.9, sh.6]; matches Radxa's GPIO-script flashing [V S6] |
| X8 | The 40-pin header carries RP2040 GP2–GP29 (28 GPIOs) plus power and 8 GND pins. Pi SPI0 positions map to RP2040 **SPI1**: pin 19 GP11 (TX), 21 GP8 (RX), 23 GP10 (SCK), 24 GP9 (CSn) | [V S1 sh.21, S5]; function mapping [K S41] |
| X9 | 12 MHz crystal; 16 Mbit W25Q16JV flash for the RP2040 | [V S1 sh.21] |
| X10 | Envelope 88.7 × 60.2 × 21.5 mm (model). USB-A stacks top out at +16.2 mm above the PCB top, RJ45 at +13.6 mm, 40-pin header at +9.65 mm (50.8 mm long, so 2.54 mm pitch). Bottom-side parts and pins reach 3.7 mm below the PCB | [M S7] |
| X11 | Power: idle 4.8–9.1 W, load 16.9–21.2 W, one 27.3 W peak report. BIOS PL1 = 6 W. Radxa recommends a ≥ 18 W supply (≥ 25 W with full USB load) and a 12 V ≥ 2.5 A PD adapter | [Vs S8, S9]; [V S3] |
| X12 | The documented BIOS options are Wake-on-LAN and RTC wake. **No "restore on AC power loss" option is documented** | [V S4 bios pages, via fetch] → TBV on hardware |

---

## 3. Deliverable 1: Proposed hardware block diagram

```text
 AMIGA 2000
 +-----------------------------------------------------------------------------------+
 |  PSU (+5V 20A / +12V 8A per S14; verify per unit)      Zorro II slot, 100-pin edge |
 |   | 4-pin Molex (drive power)                           (2 x 50 contacts, 2.54 mm)  |
 +---|---------------------------------------------------------|-----------------------+
     | +12V  +5V  GND                                          | to card:   A1-A23  D0-D15  /AS /UDS /LDS READ
     |                                                          |            E7M  DOE  /CFGINn  /BUSRST
     |                                                          | from card: /SLAVEn /CFGOUTn /INT2 /INT6 XRDY(OD)
     |                                                          | all GND pins connected; +5V/+12V/-5V/-12V unused
 +---|---------------------------------------------------------|-----------------------+
 |   v   POWER ENTRY                                  BUS INTERFACE (isolating)       |
 |  +12V: fuse > TVS > eFuse TPS25947 ------+    2x 74LVC16244A  A1-A23, ctl  5V-tol  |
 |        (OVLO, UVLO, ILIM, soft-start,     |    SN74LVC16T245   D0-D15 <-> LD0-LD15  |
 |         reverse-block, EN <- FPGA)        |    SN74LVC2T45     /SLAVEn /CFGOUTn @5V |
 |        > INA226 shunt > X4 lead (J10) ----|--+ 74LVC07A        /INT2 /INT6 XRDY OD  |
 |  +5V : PTC > TVS > rev-prot > 5V_BUS (5 V side of translators)    |                |
 |                             > LDO 3.3 V > FPGA, SRAM, logic         | 3.3 V side     |
 |                                                                     v                |
 |      +---------------------------------------------------+   LD[15:0]  +-----------+|
 |      | FPGA  Lattice MachXO2-2000HC, TQFP-144            |<===========>| SRAM      ||
 |      | instant-on, single 3.3 V                          |  SA[17:0],  | 256K x 16 ||
 |      | Zorro FSM, AutoConfig, decode, SRAM arbiter,      |  /CE /OE /WE| 512 KB    ||
 |      | registers, doorbells, semaphores, IRQ, SPI slave, |------------>| 10 ns     ||
 |      | X4 power sequencing, LEDs, DIP, I2C (INA226)      |             +-----------+|
 |      +---------------+-------------------------+---------+                          |
 |                      | SPI + IRQ_N + ATTN      | JTAG (header, or RP2040 option)    |
 |      3x SN74AVC4T774, B-side VCC = X4 header 3.3 V (P3V3_S): Hi-Z when X4 is off    |
 +----------------------|-------------------------|------------------|----------------+
                        | 40-way ribbon to X4 GPIO header            | 2-wire 12 V lead
 +----------------------|-------------------------|------------------|----------------+
 | RADXA X4 (removable, M2.5 standoffs)           v                  v J10 PWR-IN     |
 |   RP2040 SPI1 GP8-GP11 (hdr 21/24/23/19), IRQ GP22 (16), ATTN GP27 (18)             |
 |   RP2040 <== USB 1.1 FS 12 Mbit/s (+UART0) ==> Intel N100: Windows, NVMe 2230,      |
 |   (S0 rail; reset by PLTRST#)                   2.5GbE, Wi-Fi, 2x micro-HDMI, USB  |
 +------------------------------------------------------------------------------------+
```

**Data paths:**
- Amiga CPU ↔ Zorro II ↔ transceiver ↔ local bus ↔ SRAM or FPGA registers. This is direct, memory-mapped, one bus cycle per word.
- Windows ↔ WinUSB ↔ RP2040 firmware ↔ SPI ↔ FPGA ↔ SRAM or registers. This is remote access: one USB transaction per block.
- **Interrupts:** the FPGA drives /INT2 or /INT6 to the Amiga, and IRQ_N to RP2040 GP22, which the firmware forwards as a USB message.
- **Control:** the FPGA controls the X4's 12 V supply through the eFuse enable and reads back fault, telemetry and the X4's S0 state.

---

## 4. Deliverable 2: Zorro II signal and interface requirements

### 4.1 Pinout and electrical requirements

The pin numbers are taken from the Hardware Book table (credited to Commodore's A4000 User's Guide) [V S11]. They were cross-checked pin-for-pin against MNT's tested VA2000 KiCad symbol [V S12]. Signal semantics come from the Zorro III specification, Appendix K [V S10]. Direction is from the card's point of view.

| Pin(s) | Signal | Dir | Electrical type (per spec) | Rev-1 use | Interface part | Requirement / note | Src |
|---|---|---|---|---|---|---|---|
| 1–4, 13, 25, 37, 49, 61, 73, 85, 87–90, 99, 100 | GND | – | – | **All connected** to the ground plane | – | Brief requires Zorro GND retained | S11, S12 |
| 91 | GND (Z2) / SenseZ3 (Z3) | – | Grounded on Zorro II backplanes | Connect to GND (Zorro II practice) | – | A3000/A4000 use out of scope; TBV if ever needed | S10, S11 |
| 5, 6 | +5 VDC | – | – | **Not connected** | – | Brief: no operating power from Zorro | S11 |
| 10 / 8 / 20 | +12 V / −5 V / −12 V | – | – | **Not connected** | – | same | S11 |
| 92 | E7M (7M) | In | 7.16 MHz NTSC, 7.09 MHz PAL; basis of all Zorro II timing | Zorro-domain timing reference | 74LVC16244A | Fig. K-3 shows a 140 ns period | S10 029E |
| 15 | CDAC | In | 7M lagged 90° (≈35 ns) | Not used (optional buffer spare) | – | – | S10 029E |
| 14, 16, 50 | /C3, /C1, E | In | 3.58/3.55 MHz; E clock | Not used | – | – | S10 |
| 74 | /AS | In | Driven by bus master | Cycle start/end | 74LVC16244A | Falling: address/READ valid. Rising: slaves release "as quickly as possible" | S10 02A2 |
| 72, 70 | /UDS, /LDS | In | Byte strobes | Byte enables; write-data valid | 74LVC16244A | **Zorro II memory-space reads assert both strobes regardless of size**; I/O space shows true byte enables | S10 02A2 |
| 68 | READ | In | Asserted = read | Direction | 74LVC16244A | – | S10 02A2 |
| 29, 27, 26, 24, 21, 23, 28, 30, 32, 34, 36, 38, 39, 41, 43, 45, 47, 52, 54, 56, 58, 57, 59 | A1…A23 (in that order) | In | – | Full decode + offset | 2× 74LVC16244A | Valid before /AS falls [K S42] | S11 |
| 75, 77, 79, 81, 83, 86, 84, 82, 80, 78, 76, 71, 69, 67, 65, 63 | D0…D15 (in that order) | Bi | – | 16-bit data | SN74LVC16T245 (5 V side drives the bus) | Drive only when selected, READ asserted and DOE asserted | S10 02A0, S11 |
| 9 | /SLAVEn | Out | Per slot, **driven actively**; feeds collision detection | Board-selected indication | SN74LVC2T45 (5 V out) | **Assert ≤ 35 ns after /AS↓; negate ≤ 50 ns after /AS↑.** Two /SLAVEs, or a /SLAVE on a local-bus address, cause /BERR | S10 029C |
| 12 | /CFGINn | In | Daisy chain | Answer at $E8xxxx only while asserted and unconfigured | 74LVC16244A | – | S10 02A0, 02C7 |
| 11 | /CFGOUTn | Out | Daisy chain | Asserted after the base address is written ($E80048) or on shut-up ($E8004C); **negated immediately on reset** | SN74LVC2T45 | An unpowered or unconfigured card blocks downstream AutoConfig | S10 02C7 |
| 93 | DOE | In | "used by an expansion card to enable the buffers on the data bus" | Gates data-out | 74LVC16244A | **Numeric DOE timing not found**; TBV by measurement (R-13) | S10 02A0 |
| 94 | /BUSRST | In | Buffered, output-only reset; "all expansion devices are required to reset their autoconfiguration logic" on it | Zorro-side reset | 74LVC16244A | Use this, not /RST | S10 029F |
| 53 | /RST | – | Bidirectional, unbuffered, **open-collector only** | Not driven, not loaded | – | – | S10 029F |
| 19 | /INT2 | Out | Wired-OR, open-collector | Default interrupt | 74LVC07A (OD, 5 V-tolerant output) | Shared; the handler must check our status register | S10 029F, 02BE |
| 22 | /INT6 | Out | Wired-OR, open-collector | Alternative (DIP/register) | 74LVC07A | same | S10 |
| 18 | XRDY | Out | Active high, wired-OR, open-collector | Provisioned; not used in normal operation | 74LVC07A | To add wait states: negate ≤ 60 ns after /AS↓, hold until ready; each wait = 1 bus clock | S10 02A2, 02A5 |
| 66 | /DTACK | (OD) | Open-collector; **the bus controller drives zero-wait DTACK if the slave does nothing** | Not driven (rely on automatic DTACK) | Optional open-drain pad, DNP | Sampled at the falling edge of S4 | S10 02A2 |
| 17 | /OVR | (OD) | Inhibits motherboard DTACK | Not used (DNP pad) | – | – | S10 02A2 |
| 46 | /BERR | – | Open-collector, asserted on collision | Not driven; optional monitor | – | – | S10 029F |
| 31, 33, 35 | FC0–FC2 | In | Not driven valid by Zorro II DMA masters | Not used | – | – | S10 02A2 |
| 7, 60, 62, 64, 95 | /OWN, /BRn, /BGACK, /BGn, /GBG | – | DMA arbitration | Not used (no DMA in rev 1); leave open | – | – | S10 02A1 |
| 48, 51, 55 | /VPA, /VMA, /HLT | – | 6800-style cycles / halt | Not used | – | – | S11 |
| 40, 42, 44, 96 | /EINT7, /EINT5, /EINT4, /EINT1 | – | Only /INT2 and /INT6 are supported | Not used | – | – | S10 029F |
| 97, 98 | No connect (Zorro II) | – | /FCS, /DS1 on Zorro III | Not connected | – | – | S11 |

**Edge-connector geometry:** 2 × 50 contacts at 2.54 mm pitch, with even pins on the component side (VA2000 footprint: pads 1.524 × 5 mm) [V S12]. The pin-1 end orientation relative to the bracket is **TBV** against the VA2000 layout and a real A2000 slot before PCB layout.

### 4.2 Bus-cycle timing requirements

| Item | Requirement | Src |
|---|---|---|
| Minimum cycle | 4 bus clocks (≈ 560 ns at 7.09–7.16 MHz) | [V S10 02A5, 029B]; [D] |
| /DTACK | Automatic, zero wait, from the bus controller; sampled at S4↓. Read data latched at S6↓; /AS negated in S7 | [V S10 02A2] |
| /SLAVEn | ≤ 35 ns assert after /AS↓; ≤ 50 ns negate after /AS↑ | [V S10 029C] |
| Wait states | XRDY negated ≤ 60 ns after /AS↓ | [V S10 02A2] |
| Read-data budget | About 260 ns from /AS↓ to valid data at the slot | [D] from S42 states, with an assumed ≈ 10 ns motherboard buffer and 68000 setup [K]. **TBV by scope measurement** |
| Write data | Valid from /UDS//LDS assertion until after the strobes negate. Our SRAM write strobe must finish before S7 | [K S42] |
| Byte-read semantics | Memory-space reads assert both strobes, so **no read side-effects at byte granularity** | [V S10 02A2] |

**How the design meets the 35 ns /SLAVEn limit.** /SLAVEn is a **combinational** function of /AS, the latched-or-stable address match and the configured state. It is not routed through a clock synchroniser. The path is:
- 74LVC16244A, about 2–5 ns [K];
- MachXO2 -4 pin-to-pin, about 7.24 ns [Vs S20];
- SN74LVC2T45, about 3–6 ns [K];
- PCB, about 1 ns.

That totals about 13–19 ns, leaving about 15 ns of margin. It will be enforced as a timing constraint and confirmed with a scope (R-12).

**Reads.** /AS is synchronised at about 50 MHz in at most 40 ns. The SRAM access takes 10 ns and the transceiver about 5–8 ns. Total ≈ 80 ns, comfortably inside the ≈ 260 ns budget. The arbiter grants the local bus to the Zorro side for the whole of /AS. An in-flight SPI word access, at most about 2 clocks, can only delay it by ≈ 40 ns. **No wait states are needed**, but XRDY stays provisioned.

### 4.3 AutoConfig requirements [V S10 02C7, 02C8]

- Respond at $E80000–$E8FFFF only while /CFGINn is asserted and the card is not yet configured or shut up.
- Registers are nibble-paired: register NN's high nibble is at $E8(NN)0 and its low nibble at $E8(NN)2, on D15–D12. **Every register except $00 is returned complemented.**
- **er_Type ($00):**
  - bits 7–6 = `11` (Zorro II);
  - bit 5 (link into the memory free list) = 0;
  - bit 4 (ROM vector valid) = 0 in rev 1;
  - bit 3 (chained) = 0;
  - size = `001` (64 KB) or `100` (512 KB), depending on mode (§7.5).
- **er_Flags ($08):** bit 7 = 8 MB-space preference (0 for 64 KB I/O mode, 1 for 512 KB mode); bit 6 (cannot be shut up) = 0.
- The OS writes the base address to $E8004A (A19–A16), then **$E80048 (A23–A20), which configures the board**. Writing anything to $E8004C shuts it up. /CFGOUTn asserts after either.
- Manufacturer ID, product and serial: decision D-14.

---

## 5. Host link (Intel ↔ RP2040 ↔ FPGA)

| Link | Verified wiring | Raw rate | Expected payload throughput | Latency |
|---|---|---|---|---|
| N100 ↔ RP2040, USB | RP2040 USB → N100 USB2 port 6 [V S1 sh.21] | 12 Mbit/s full speed [K S41] | ≤ 1.216 MB/s theoretical bulk ceiling [K S40]; ~0.8–1.0 MB/s expected [E] | ~1–2 ms per request/response through the Windows USB stack [E] |
| N100 ↔ RP2040, UART | GP0/GP1 ↔ N100 UART1 (GPP_D17/D18) [V S1] | TBV | < USB | Whether Windows exposes this UART on the X4 is TBV; treat as debug/fallback only |
| RP2040 ↔ FPGA, SPI | Header pins 19/21/23/24 = SPI1 [V S1, S5] | 20–30 MHz target [A] | 2.5–3.7 MB/s [D] | µs-scale; **not the bottleneck** |
| Amiga ↔ SRAM, Zorro II | – | 16 bits per 560 ns | ≤ 3.57 MB/s [D]; 68000 copy loops achieve less [K] | 560 ns per word |

**Conclusion.** The RP2040 path satisfies the brief's control-plane needs: mailboxes, interrupts, status and modest data. File sharing, network tunnelling and screen transfer would be limited to about 1 MB/s by USB full speed. That is a property of the X4 itself, verified on the schematic, not of our design.

**Upgrade path, no rev-1 cost.** The FPGA debug/expansion header carries four spare I/O. That is enough for a later plug-in USB 2.0 high-speed SPI bridge plugged into one of the X4's USB-A ports, without changing the carrier. Example parts: WCH CH347 or FTDI FT232H [K, TBV].

**RP2040 notes:**
- The RP2040 resets whenever the N100 platform resets (X7). The FPGA must treat the link as volatile and report link loss to the Amiga.
- The X4's own 3.3 V on header pin 1 (S0-only, X5) is the reference supply for the isolating translators. It gives the FPGA an unambiguous "X4 is in S0" signal.
- PL022 chip-select behaviour between frames in SPI mode 0 is [K]. The firmware may drive CS as a GPIO; TBV in Stage 4.

---

## 6. Deliverable 3: FPGA/CPLD comparison

### 6.1 I/O requirement, calculated before selection

Architecture assumed: Zorro data and SRAM data share a 16-bit local bus (§7.2).

| Group | Signals | Pins |
|---|---|---|
| Zorro inputs | A1–A23 (23); /AS, /UDS, /LDS, READ (4); E7M, DOE, /CFGINn, /BUSRST (4) | 31 |
| Zorro outputs | /SLAVEn, /CFGOUTn, /INT2, /INT6, XRDY | 5 |
| Data transceiver control | DIR, /OE (byte halves tied) | 2 |
| Local data bus (Zorro data, SRAM data, FPGA) | LD0–LD15 | 16 |
| SRAM address + control | SA0–SA17 (18); /CE, /OE, /WE, /UB, /LB (5) | 23 |
| RP2040 link | SCK, CS_N, MOSI, MISO, IRQ_N, ATTN | 6 |
| X4 power/status | X4_S0_SENSE, X4_PWR_OFF (eFuse EN), EFUSE_FLT_N | 3 |
| Telemetry I²C | SCL, SDA, ALERT_N (INA226) | 3 |
| User I/O | 5 LEDs, 3 DIP switches | 8 |
| Clock | External oscillator input (internal oscillator possible) | 1 |
| Debug/expansion header | Spare I/O | 4 |
| **Total user I/O** | | **102** |
| MachXO2 dual-purpose config pins kept (PROGRAMN, INITN, DONE) | | 3 |
| **Total vs LCMXO2-2000HC TQFP-144 (111 I/O)** | | **105 / 111 (6 spare)** |

JTAG uses dedicated pins [K S44]. If pins or logic run short, the LCMXO2-4000HC in the same package is the intended migration (114 I/O [K]; pin-compatibility TBV S44). **Logic estimate [E]:** about 700–1,000 LUTs (Zorro FSM and AutoConfig ~150, arbiter and address mux ~150, SPI slave and command decoder ~200, register file, semaphores and doorbells ~250, watchdogs, power sequencing, I²C and LEDs ~150).

A dedicated SRAM data bus would need 16 more pins (121 in total), which would push the design into a BGA FPGA. That is why rev 1 uses the shared local bus.

### 6.2 Candidate comparison (prices are 1-off snapshots, Nov 2026)

Planning exchange rates: 1 USD = 1.55 AUD, 1 GBP = 2.00 AUD, 1 EUR = 1.75 AUD [A].

| Device | Technology / configuration | Logic / RAM | User I/O (package) | Supply | Instant-on? (AutoConfig chain risk) | Toolchain | 1-off price | ≈ AUD | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Lattice LCMXO2-2000HC-4TG144C** | Flash-based FPGA, internal config | 2112 LUT / 74 Kbit EBR + UFM [Vs S20] | **111** (TQFP-144) [Vs S20] | Single 3.3 V (HC) [K] | **Yes**: internal flash, ms-range (exact time TBV S44) | Lattice Diamond (free licence); openFPGALoader for JTAG [K] | USD 6.29–6.53 LCSC (low stock); €16.28 DigiKey DE, 52-wk factory lead time [Vs S20] | 10–29 | **Recommended** |
| Lattice LCMXO2-4000HC-4TG144C | Same family | 4320 LUT [K] | 114 [K] | same | Yes | same | TBV | TBV | Footprint migration |
| Lattice iCE40HX4K-TQ144 | SRAM-based; external SPI flash | 3520 LUT / 80 Kbit [Vs S21] | 107 (4 shared with config flash) [Vs S21] | 1.2 V core + 3.3 V I/O + VPP [K] | **No**: tens of ms after POR (TBV); risks missing AutoConfig and blocking the chain (R-11) | **Fully open** (Yosys / nextpnr / IceStorm) | USD 10.20 DigiKey US; AUD 16.34 ex GST DigiKey AU [Vs S21] | 16–25 | Alternative if a fully open toolchain is mandatory and the AutoConfig timing is proven |
| Gowin GW1N-UV4LQ144 / -UV9LQ144 | Flash-based | TBV | ~120 (TBV) | Single supply (TBV) | Yes (TBV) | Gowin EDA; open Apicula (TBV) | UV9 ≈ USD 39.52 at Mouser; UV4 at JLCPCB C5173870, price TBV [Vs S22] | 10–60 | Possible lowest-cost option *if* LCSC/JLC pricing is confirmed; weaker Western supply and documentation |
| Microchip ATF1508AS-10AU100 | 5 V EEPROM CPLD | 128 macrocells [Vs S23] | 80 (TQFP-100) [Vs S23] | 5 V [K] | Yes | WinCUPL / community flows | USD 16.13 DigiKey US, Active [Vs S23] | ≈ 25 | Rejected: an SPI slave, arbiter and mailbox registers need far more than 128 macrocells [E]. Still needs 3.3 V translation for the RP2040 |
| Lattice iCE40UP5K-SG48 | SRAM-based; 128 KB SPRAM on-chip | 5280 LUT / 1 Mbit SPRAM [K] | **39** (QFN-48) [K] | 1.2 V core | No | Fully open | not re-verified, ≈ USD 5–8 [E] | 8–12 | Rejected for rev 1: 39 I/O forces address/data multiplexing and makes the 35 ns /SLAVEn limit fragile |

**Why MachXO2.** It is the cheapest option that meets all three hard constraints:
- **≥ 102 I/O in a hand-solderable package.**
- **Instant-on**, which avoids blocking the AutoConfig chain.
- **A single 3.3 V rail**, so no 1.2 V regulator or configuration flash is needed.

Its user flash (UFM) can also store persistent settings and a serial number [K S44].

The main weakness is supply. LCSC's low-cost stock is shallow, and DigiKey quotes a 52-week factory lead time. **Buy prototype quantities early** (R-22).

---

## 7. Deliverable 4: Shared-memory architecture

### 7.1 Options compared

| Option | Cost | FPGA I/O impact | Complexity | True physical sharing? | Verdict |
|---|---|---|---|---|---|
| A. FPGA-internal RAM (iCE40UP5K, 128 KB SPRAM) | No SRAM chip | Forces a 39-I/O FPGA, so multiplexed Zorro bus | High (bus multiplexing, /SLAVEn timing) | Yes | Rejected (rev 1) |
| **B. Conventional async SRAM + FPGA arbitration** (IS61WV25616EDBLL-10TLI, 256K×16, 10 ns, TSOP-II-44) | USD 2.65–6.17 [Vs S24] | 23 pins + shared local bus | Moderate: arbiter ≈ 150 LUT [E] | Yes | **Recommended** |
| C. True dual-port SRAM (Renesas 70V28L15PFG, 64K×16) | ≈ AUD 231 each [Vs S25]; 18-week lead time | The PC side is SPI, so the FPGA would still drive one port; ≈ 80 pins for two ports | Hardware arbitration is simple, but it gains nothing here | Yes | Rejected: ~25–55× the cost, no functional benefit |
| D. SDRAM / PSRAM / HyperRAM | ≈ USD 2–4 [E] | 12–40 pins | High (controller, refresh, latency) | Yes | Rejected: unnecessary for ≤ 512 KB |
| E. Software-maintained copy (RP2040 or Windows mirror) | None | – | High (coherency protocol) | **No** | Rejected as the shared-memory mechanism |

**Capacity.** A 512 KB part costs about the same as a 128 KB one, so rev 1 fits 512 KB, covering the brief's 128–512 KB range. The SRAM is 2.4–3.6 V [Vs S24] and sits entirely on the 3.3 V side.

### 7.2 Local-bus arbitration (how B works)

- The Zorro data transceiver connects the Zorro D0–D15 to a 3.3 V local bus, LD0–LD15. That bus is shared by the SRAM data pins and the FPGA.
- **Zorro read of SRAM:** the FPGA drives the SRAM address from the Zorro address plus mode/bank, and asserts SRAM /CE and /OE. The SRAM drives LD, and the transceiver drives the Zorro bus while DOE is asserted.
- **Zorro write:** the transceiver drives LD from the Zorro bus. The FPGA times the SRAM /WE pulse, with /UB and /LB taken from /UDS and /LDS, and completes it before S7.
- **Register access:** the FPGA drives or captures LD itself, with SRAM /OE held high.
- **SPI access:** the transceiver is disabled and the FPGA performs single-word SRAM accesses between Zorro cycles. Read-ahead and write FIFOs live in EBR.
- **Priority:** Zorro wins and holds the bus for the entire /AS assertion, which includes 68000 read-modify-write (TAS) cycles.

### 7.3 Consistency guarantees (rev 1)

**This is true shared physical memory.** There is exactly one copy, in the SRAM chip.
- **Amiga side:** memory-mapped; every CPU access is a real Zorro cycle to the SRAM.
- **PC side:** accesses go *through* the RP2040. Windows software has **no pointer or memory-mapped access**. It calls an API (`read(addr, len)` / `write(addr, data)`), and each call becomes USB → SPI transactions. The RP2040 firmware must not cache or post writes beyond acknowledging a completed SPI transaction.

| # | Guarantee |
|---|---|
| G1 | Every aligned 16-bit access from either side is atomic. Byte writes (/UDS, /LDS, or SPI byte enables) are atomic per byte |
| G2 | Zorro cycles are never torn by SPI accesses: the arbiter holds the local bus for the full /AS assertion, including RMW/TAS |
| G3 | **No multi-word atomicity** across sides. A multi-word write can be observed partially. Use the hardware semaphores and per-slot ownership flags (§7.4) |
| G4 | Ordering: SPI transactions are executed in order. Within a transaction, words are written in ascending address order. A doorbell written after data, in the same or a later transaction, is ordered after that data |
| G5 | **The Amiga side must use non-cacheable access.** On 68030/040/060 accelerators the driver must map the board non-cacheable and serialise writes before ringing a doorbell (R-16). Zorro II memory-space reads always assert both byte strobes, so registers have no byte-granular read side-effects |
| G6 | PC-side visibility of Amiga writes needs a doorbell or polling plus a USB round trip, typically ≥ 1 ms [E] |
| G7 | SRAM contents survive Amiga resets (/BUSRST resets only the Zorro and AutoConfig state) and PC reboots. They are lost only when carrier power is lost |

### 7.4 Mailbox protocol (outline; full spec in Stage 3)

- **Shared control block** in the fixed window: magic, protocol version, ring geometry, and each side's state and epoch.
- **Two unidirectional rings,** Amiga→PC and PC→Amiga. Each has N fixed-size slots (default 32 × 64 B). Each slot has a 16-byte header: `seq`, `type`, `flags` (OWN, ACK_REQ, RESPONSE, ERROR), `len`, `status`, `ref_seq`, `crc16`, reserved.
- **Ownership:** the producer writes the payload and header, then sets OWN as a single 16-bit write. It then advances its producer index and writes the FPGA doorbell register. The consumer processes the slot, writes `status`, clears OWN and advances its consumer index.
- **Sequencing:** `seq` increments per direction, so gaps and duplicates are detectable. Responses carry `ref_seq`, and duplicates are handled idempotently.
- **Interrupts:** a doorbell sets a pending bit in the FPGA.
  - Amiga side: asserts /INT2 (or /INT6).
  - PC side: asserts IRQ_N to RP2040 GP22, which the firmware forwards to Windows as a USB message.
  - Acknowledge by write-1-to-clear. The interrupt line releases when no enabled pending bits remain.
- **Timeouts:** each request type has a deadline (default 250 ms [A]). Retry up to 3× with the same `seq`, then declare a link fault.
- **Heartbeats:** each side updates a heartbeat register at ≥ 4 Hz. An FPGA hardware watchdog flags PEER_LOST and interrupts the other side after 1 s [A].
- **Reset events:** the FPGA latches and reports:
  - an Amiga reset (/BUSRST);
  - X4 S0 loss (header 3.3 V gone);
  - SPI link idle;
  - power faults.

  A changed epoch forces the rings to be re-initialised.
- **Hardware semaphores:** 16 FPGA semaphores with write-claim/read-verify semantics (write your side ID, read back to confirm). They have no read side-effects, so speculative or duplicated reads are harmless.
- **Error reporting:** an FPGA error register (SPI framing/CRC, arbitration, power fault) plus per-slot `status` codes.

### 7.5 Preliminary memory map (Amiga view; finalised in the Stage 2/3 register spec)

The mode is selected by DIP switch: **default A** (does not consume the 8 MB Fast-RAM space), optional B.

| Mode A: 64 KB I/O board (er_Type size `001`, er_Flags bit 7 = 0) | | |
|---|---|---|
| $0000–$0FFF | 4 KB | FPGA registers: ID, version, status, control, IRQ, doorbells, semaphores, bank, heartbeats, telemetry |
| $1000–$7FFF | 28 KB | Fixed window → SRAM $01000–$07FFF (control block, rings) |
| $8000–$FFFF | 32 KB | Banked window → SRAM bank × 32 KB (16 banks = 512 KB) |

| Mode B: 512 KB linear (size `100`, er_Flags bit 7 = 1; uses the 8 MB space) | | |
|---|---|---|
| $00000–$00FFF | 4 KB | FPGA registers (same layout) |
| $01000–$7FFFF | 508 KB | SRAM $01000–$7FFFF, linear |

**PC view (SPI):** a flat byte address space, SRAM $00000–$7FFFF, plus a separate register space selected by opcode. No banking.

Mode A's 64 KB placement in the $E9xxxx I/O area matches common practice for 64 KB boards [K]. Where expansion.library places larger I/O boards was not verified (R-15).

---

## 8. Deliverable 5: Power

### 8.1 Feeding the X4: J10 direct versus USB-C PD source

| | **J10 direct 12 V (recommended)** | USB-C PD source on the carrier |
|---|---|---|
| Radxa support | Documented input [V S2, S3] | Primary documented input [V S4] |
| Extra parts | Fuse, TVS, eFuse (≈ AUD 3–8) | PD source controller (e.g. TPS25740B, 5/9/12/15 V profile, external NFET path [Vs S28]), 5 V and 12 V path switching, Type-C plug/cable; ≈ AUD 10–25 [E] |
| Compliance | Not a USB port; nothing to comply with | Must deliver 12 V within USB PD tolerance (±5 % [K]). An aged A2000 12 V rail may not, so a buck-boost would be needed to guarantee it [K] |
| Risk | Low. The X4's own USB-C VBUS is live at 12 V (X2), so its USB-C receptacle **must be blocked** and labelled | Moderate: CC/PD negotiation, VBUS discharge, more failure modes |
| Decision | **Rev 1** | Documented fallback if a future X4 revision drops J10 |

### 8.2 Carrier power architecture (preliminary values; designed on sheet 5)

**+12 V (Molex pin 1) to the X4:**
1. Fuse (≈ 5 A slow-blow [A]).
2. TVS (SMBJ15A-class [K]).
3. **TPS25947 eFuse** [Vs S27]:
   - rated 2.7–23 V, 5.5 A, 28 mΩ, 28 V absolute maximum, withstands −15 V reverse;
   - OVLO ≈ 13.8 V (fixed-clamp variant or adjustable lockout, choice TBV);
   - UVLO ≈ 10.5 V via the EN divider [A];
   - ILIM ≈ 4 A [A];
   - dV/dt soft-start ≈ 15 ms [A];
   - **default OFF**: the FPGA must actively enable it, with a jumper override.
4. INA226 shunt (10 mΩ) for voltage/current telemetry to the FPGA.
5. Bulk capacitance, then the 2-wire lead to J10.

**+5 V (Molex pin 4) to the logic:**
1. PTC (≈ 0.75–1 A hold [A]).
2. TVS (SMBJ5.0A-class [K]).
3. P-FET reverse-polarity protection.
4. Then two rails:
   - `+5V_BUS`, the 5 V side of the Zorro translators;
   - a 1 A LDO producing `+3V3` for the FPGA, SRAM, buffers, LEDs and INA226. LDO dissipation ≈ (5.0 − 3.3) V × 0.25 A ≈ 0.43 W [D].

The Zorro +5 V/+12 V/−5 V/−12 V pins are **not connected**. All Zorro GND pins plus the Molex GND pins (2, 3) form one ground system. (Molex pin numbering [K]; TBV against the A2000 harness.)

### 8.3 Power budget

**+12 V (Molex), X4 path**

| Load | Idle | Typical | Heavy | Peak / design | Source |
|---|---|---|---|---|---|
| Radxa X4 incl. NVMe and fan, no USB loads | 4.8–9.1 W | ≈ 10 W [E] | 16.9–21.2 W | 27.3 W (one report) | [Vs S9] |
| X4 USB devices (keyboard, mouse, stick) | 0–1 W | ≈ 1 W [E] | 2.5 W [E] | covered by Radxa's 25 W figure [Vs S8] | |
| Fuse + eFuse + shunt + wiring losses | < 0.1 W | 0.1 W | 0.3 W | ≈ 0.5 W at 2.5 A [D] | S27 |
| **Total** | **5–9 W** | **≈ 11 W** | **≈ 19–24 W** | **30 W design (Radxa: 12 V ≥ 2.5 A)** [V S3] | |
| **Current at 12 V** | 0.4–0.75 A | ≈ 0.9 A | 1.6–2.0 A | **2.5 A design**, ILIM ≈ 4 A | [D] |

**+5 V (Molex), carrier logic** [E]

| Load | Typical | Design max |
|---|---|---|
| 3.3 V logic: FPGA, SRAM, buffers, 5 LEDs, INA226, oscillator (via LDO, so input current ≈ output) | 0.12 A | 0.25 A |
| *C-30 update (2026-11-19):* FPGA now LCMXO2-4000HC: static core current typ 8.45 mA instead of 4.80 mA (+3.7 mA); JTAG programming typ 26.8 mA instead of 22.1 mA (MachXO2 data sheet Tables 3.10, 3.11 [V S49]). Sheet 4 adds U405 (≤ 10 µA, from the X4's header 3.3 V) and translator quiescent current (µA) | +0.004 A | within the 0.25 A design maximum; dynamic FPGA power to be estimated with the Diamond Power Calculator at sheet 5 |
| `+5V_BUS` translator side (bus switching) | 0.02 A | 0.05 A |
| **Total** | **≈ 0.14 A (0.7 W)** | **0.3 A (1.5 W); fuse sized ≈ 0.75–1 A** |

**A2000 PSU context** (Haynie's A2000/B2000 figures [V S14]; your PSU may differ)

| Consumer (example system) | +5 V | +12 V |
|---|---|---|
| Motherboard | 2.5 A | 0.05 A |
| 2 × 3.5" floppy | 0.5 A | 0.7 A |
| 1 × 3.5" hard disk (running) | 0.75 A | 1.0 A |
| 4 other slots at Commodore's suggested 2.0 A / 40 mA each | 8.0 A | 0.16 A |
| Keyboard and ports (approx.) | 0.5 A | 0.1 A |
| **This card** | **0.3 A** | **2.5 A** |
| **Total vs system limit** | **≈ 12.6 A of 20 A** | **≈ 4.5 A of 8 A** |

The budget fits a PSU that meets Haynie's figures. It **does not fit** the unverified "+12 V 3 A" A2000 PSU variant reported by S15. Aged PSUs, and replacement PSUs with weak 12 V rails, are also unknowns. That is why the verification procedure in §8.6 is mandatory.

Commodore's *per-slot* suggestion is only 40 mA at 12 V [V S14]. This card draws its 12 V from drive power, as the brief requires, never from the slot.

### 8.4 Start-up, sequencing and peaks

1. **A2000 power-on.** The Molex 5 V and 12 V rise together. The hard-disk spin-up surge on 12 V is drive-dependent [K]; measure it.
2. **Carrier up.** The 3.3 V LDO comes up in milliseconds, and the MachXO2 configures from internal flash (ms-range, TBV). AutoConfig is answered from the first Kickstart scan. The X4 eFuse stays **off**.
3. **Delay.** After a configurable delay (default 5 s [A]; DIP/UFM setting, "auto-start X4"), the FPGA enables the eFuse. This keeps the X4's boot load from coinciding with the disk spin-up.
4. **Soft-start.** Inrush ≈ C_in × dV/dt. Taking the X4's `ADP12V` input capacitance as ≈ 150–250 µF [E, from the sheet-26/24/25 capacitor count], a 15 ms ramp gives ≈ 0.12–0.2 A.
5. **X4 boot.** The load rises to ≈ 1–2 A during BIOS and Windows boot [E]. The worst case is 2.5 A.
   - The X4 must power on by itself when 12 V appears. **This is not documented (X12) and must be tested first** (R-03).
6. **Shutdown.**
   - Graceful: an Amiga command goes through the mailbox to a Windows shutdown service, which then lets the FPGA remove 12 V.
   - Hard reset: the FPGA power-cycles the eFuse. This needs an Amiga-side unlock sequence so it cannot happen by accident.
   - Switching the A2000 off without shutting Windows down is a known risk (R-23).
7. **Amiga reset (/BUSRST).** Resets only the Zorro and AutoConfig logic. The X4 keeps running and the SRAM is preserved (G7).

### 8.5 Isolation and backfeed analysis

| Scenario | Possible path | Protection |
|---|---|---|
| X4 off/unplugged, carrier powered | FPGA outputs → RP2040 pins → X4 3.3 V rail | SN74AVC4T774 with VCCB = X4 header 3.3 V: outputs go high-Z when VCCB = 0 (VCC isolation [K]). X4_S0 sense uses 10 kΩ series + 100 kΩ pull-down with the FPGA pull-up disabled (≈ 30 µA) |
| X4 on, carrier logic unpowered | RP2040 outputs → unpowered FPGA | Translator A side unpowered, so outputs high-Z (VCC isolation) |
| Carrier unpowered, Amiga on | 5 V Zorro signals → carrier | 74LVC16244A: 5 V-tolerant inputs, Ioff [K]. LVC16T245 / LVC2T45: VCC isolation. 74LVC07A: Ioff. **Side effect:** /CFGOUTn is never asserted, so downstream boards are not configured (documented behaviour) |
| X4 header 5 V | `P5V_A` → carrier 5 V | **Header pins 2 and 4 are not connected** on the carrier |
| A second 12 V source on the X4's USB-C | X4 `ADP12V` → J10 → carrier → A2000 +12 V | eFuse true reverse-current blocking [Vs S27]. The *external* source is not protected, so the USB-C port gets a mechanical cover and label (R-05) |
| Zorro power pins | – | Not connected; no operating power drawn |

### 8.6 Verification procedure before installing in an A2000

1. **Identify the PSU.** Record the label (maker, model, rail ratings) or the replacement PSU's 12 V rating. If the 12 V rating is below 5 A, stop and review.
2. **Inspect.** Check for age-related failure (capacitors, smell, fan). Recap if in doubt.
3. **Baseline.** With your normal drives and cards fitted, measure +5 V and +12 V at a spare Molex with a DMM: at idle, during disk spin-up, and during floppy access.
4. **Static load test.** Connect a 12 V / 2.5 A dummy load (electronic load, or ≈ 4.7 Ω ≥ 50 W) to a spare Molex for 30 minutes with the case closed.
   - Pass criteria [A]: +12 V within 11.4–12.6 V and +5 V within 4.75–5.25 V, including during disk spin-up.
   - Scope the ripple. Use ATX-style limits as a guideline [K]: ≤ 120 mV p-p on 12 V and ≤ 50 mV p-p on 5 V.
5. **Step load test.** Switch the 2.5 A load on and off repeatedly. Watch for 12 V droop, 5 V disturbance from cross-regulation, and any Amiga reset or crash.
6. **Thermal check.** Note the PSU exhaust temperature and fan behaviour after 30 minutes.
7. **Bench-test the card first,** using current-limited bench supplies (12 V / 3 A, 5 V / 1 A):
   - Zorro side unplugged;
   - then the X4 via J10, logging current with the onboard INA226: idle, boot, and stress.
8. **Install in stages:** first the card **without** the X4 (AutoConfig and registers), then with the X4. Repeat step 3 with the card fitted.

---

## 9. Mechanical assessment (Stage 6 must verify)

- **X4 envelope [M S7]:**
  - top side: +16.2 mm (USB-A stacks) and +13.6 mm (RJ45);
  - bottom side: −3.7 mm below the PCB;
  - an installed M.2 2230 SSD is **not in the model** (TBV).
- **Stack height above the carrier.** Standoffs of about 6 mm (clearing the bottom-side 3.7 mm) + 1.6 mm X4 PCB + 16.2 mm gives **≈ 23.8 mm** [D].
- **Space available.** Assuming ISA-style 0.8 in (20.32 mm) slot pitch [A, TBV], about 16–17 mm is available above the component side. **The X4 intrudes ≈ 7 mm into the adjacent slot**, so rev 1 occupies two slots (D-08).
- **Card dimensions.** Zorro cards follow PC card proportions [Vs]. MNT's working VA2000 is 127 × 96 mm [V S12]. The maximum length, height and bracket geometry must come from the A2000 Technical Reference Manual or a physical measurement (R-08).
- **Placement.** Put the X4 at the bracket end with its USB and RJ45 edge facing the rear. Whether the ports can pass through the A2000 rear openings is doubtful (R-10). Panel-mount extension leads are the likely answer.
- **Airflow and thermal.** The N100 needs an active cooler inside a closed A2000. Verify CPU temperature and throttling under sustained load with the case closed (R-09).
- **Mounting.** Four M2.5 standoffs. Take the hole positions from the STEP model during Stage 6 (not yet extracted). Use a ribbon cable, not direct stacking, so the X4 can be swapped without strain on the header.

---

## 10. Deliverable 6: Preliminary BOM summary

The full itemised list, with sources and low/high AUD estimates, is in [bom/bom-preliminary.csv](bom/bom-preliminary.csv).

| Group | Low AUD | High AUD | Notes |
|---|---|---|---|
| FPGA (LCMXO2-2000HC-4TG144C) | 10 | 29 | [Vs S20] |
| SRAM (IS61WV25616EDBLL-10TLI) | 4 | 10 | [Vs S24] |
| Bus interface (LVC16T245, 2× LVC16244A, LVC2T45, LVC07A) | 3 | 11 | [Vs S26] / [E] |
| X4 isolation (3× AVC4T774) | 2 | 8 | [Vs S26] |
| Power entry (fuse, TVS ×2, PTC, P-FET, eFuse, LDO, bulk caps) | 6 | 15 | [Vs S27] / [E] |
| Telemetry (INA226 + shunt), oscillator (optional) | 3 | 8 | [E] |
| Connectors (Molex, 2×20 + ribbon, J10 lead, JTAG, debug), DIP, LEDs | 9 | 22 | [E] |
| Passives and test points | 4 | 13 | [E] |
| Mechanical (standoffs, bracket, USB-C port cover) | 8 | 28 | [E]; bracket custom |
| PCB (4-layer, ENIG, bevelled gold fingers; share of a 5-board order) | 25 | 50 | [E]; size TBD |
| **Carrier total (prototype, per board)** | **≈ 73** | **≈ 193** | Excludes shipping, assembly and tools |
| Radxa X4 4 GB (no eMMC) | 95 | 125 | [Vs S30]; the 8 GB model is ≈ AUD 410+ [V S29] |
| NVMe M.2 2230 SSD, 256 GB | 50 | 100 | [E]; 2026 NAND prices elevated |
| X4 active cooler | 15 | 30 | [E]; product TBD |
| **x86 subtotal** | **≈ 160** | **≈ 255** | |
| **Prototype unit total** | **≈ 233** | **≈ 448** | Plus a Windows licence |

**Production view [E].** At about 100 units the carrier falls to roughly AUD 45–80 (LCSC 120+ FPGA price ≈ USD 4.83 [Vs S20], PCB ≈ AUD 8–15). The X4 remains the dominant and most volatile cost.

**Tools [E].** A JTAG adapter: an FT2232H board or an RP2040 "dirtyJTAG" with openFPGALoader, ≈ AUD 10–40. A logic analyser with ≥ 16 channels and ≥ 100 MHz is strongly recommended for Zorro bring-up.

---

## 11. Deliverable 7: Unresolved decisions and feasibility risks

### 11.1 Decisions needed from you

| ID | Decision | Recommendation |
|---|---|---|
| D-01 | X4 power path: J10 direct, or a USB-C PD source | **J10 direct** (§8.1) |
| D-02 | FPGA family | **MachXO2-2000HC** (migration path to 4000HC). Alternative: iCE40HX4K if a fully open toolchain outweighs instant-on |
| D-03 | Default AutoConfig mode | **64 KB I/O mode default**, 512 KB linear mode by DIP switch |
| D-04 | SRAM size | **512 KB** (same cost as 128 KB) |
| D-05 | X4 SKU | **4 GB for the prototype** (≈ ¼ the price of 8 GB in 2026). Revisit for "daily use" |
| D-06 | Windows edition: Win 10 Pro (out of support), Win 11 Pro, or Win 10 IoT Enterprise LTSC 2021 (supported to 2032 [K]) | Your call. The hardware is OS-agnostic; the Windows software will target 10 and 11 |
| D-07 | X4 connection: ribbon or direct stacking | **Ribbon** (≤ 15 cm, GND-interleaved header) |
| D-08 | Accept two-slot occupancy for rev 1? Card length (half or full)? | **Accept two slots.** Choose length after measuring an A2000 |
| D-09 | X4 port access: internal only, or bracket extension leads (RJ45, USB, HDMI) | Start internal plus Wi-Fi; add extensions after the mechanical check |
| D-10 | Default interrupt level | **INT2** (INT6 selectable) |
| D-11 | Fit INA226 telemetry? | **Yes on prototypes** |
| D-12 | RP2040-driven JTAG for field FPGA updates from Windows | **Yes**, behind a DIP-controlled translator enable |
| D-13 | Project licences | Suggested: **CERN-OHL-S-2.0** (hardware), **GPL-3.0** or **MIT** (HDL/software). Your choice |
| D-14 | AutoConfig manufacturer ID | Prototype: Commodore's "hacker/test" ID 2011 ($07DB) [K, TBV]. Release: obtain or choose a non-conflicting ID |
| D-15 | Network path for RDP: separate Amiga NIC, or SANA-II over the bridge | Defer to Stage 5. The hardware supports both |
| D-16 | X4 start policy: auto-start after a delay, or only on Amiga command | **Auto-start after 5 s**, DIP-selectable |
| D-17 | Janus compatibility goal: none, API-level, or register-level | **None in rev 1.** Register-level needs Janus hardware documentation we do not have (R-26) |

### 11.2 Top feasibility risks

The full register, with mitigations and owners, is in [risk-register.md](risk-register.md).

| ID | Risk | Severity |
|---|---|---|
| R-01 | PC-side bandwidth ~1 MB/s and ~1 ms latency (USB full speed, verified) | High impact on future features; certain |
| R-03 | X4 may not power on automatically when 12 V is applied (undocumented) | High; **test first** |
| R-06 | A2000 PSU 12 V capacity and regulation vary by unit/variant | High; verification procedure |
| R-08 | Mechanical: X4 height forces two-slot occupancy; slot and card dimensions unverified | Medium |
| R-11 | AutoConfig chain blocked if the FPGA configures late | High; mitigated by instant-on |
| R-12 | /SLAVEn 35 ns deadline | High; combinational path plus timing constraint |
| R-13 | DOE timing unknown numerically | Medium; measure |
| R-19 | Windows 10 Pro end of support | Medium (security) |
| R-20 | RDP on a classic 68k Amiga: client availability and performance doubtful on a 68000 | High for the end goal; Stage 5 investigation |
| R-21 | X4 price and availability volatility | Medium |
| R-22 | MachXO2 lead time and stock | Medium; buy early |

**Flagged as unresolved safety and bus-timing issues (per brief §10).**
- **R-05 (safety):** the X4's USB-C VBUS is live while J10 is fed. Mitigated by the eFuse reverse blocking and a port cover, but it needs your acceptance.
- **R-12 and R-13 (timing):** /SLAVEn and DOE timing must be proven on hardware before Zorro bring-up is considered safe.
- **R-03 (behaviour):** no electrical hazard, but it blocks the power-control concept until tested.

---

## 12. Recommendation: lowest-cost credible revision 1

**Architecture.** As in §1.2 and §3.

**Why this is the lowest-cost *credible* option:**
1. **It reuses what the X4 already has.** The RP2040 and its USB link cost nothing, and their limits are now verified rather than assumed.
2. **It avoids a PD source.** J10 is Radxa-documented, so an eFuse at about AUD 3 replaces a PD controller, a buck-boost and a Type-C path. That removes cost and a whole class of compliance and failure modes.
3. **It uses one programmable device.** Instant-on, single-rail MachXO2 needs no configuration flash and no 1.2 V regulator. Instant-on also removes the AutoConfig-chain risk that makes the cheaper SRAM-based FPGAs non-credible.
4. **Its memory is conventional and cheap.** One SRAM costs ≈ 1/25–1/55 of true dual-port, and dual-port would gain nothing because the PC side is serial anyway.
5. **It needs no Zorro wait-state or DTACK logic.** The motherboard's automatic DTACK plus Zorro-priority arbitration keeps the bus logic simple. XRDY stays available as a safety valve.
6. **Its isolation is passive.** Translators powered from each side's own rails make the "either side unpowered" cases safe with no sequencing logic.
7. **It is assembly-friendly.** Everything is TQFP, TSSOP or TSOP except the 2 × 2 mm eFuse. Use stencil/hot-air or PCBA for that part.

**What rev 1 deliberately does not do:**
- PC-side throughput above about 1 MB/s (upgrade: plug-in high-speed SPI bridge on the expansion header);
- DMA;
- Janus register compatibility;
- single-slot mechanical fit;
- PD-compliant USB-C power;
- graceful Windows shutdown on unexpected A2000 power-off.

**Credible alternative for rev 2.** A LattePanda Mu N100 module (9–20 V input [Vs S31]) on a custom carrier integrated into the Zorro card. It gives a low profile, ports on the bracket, and direct DC power, at the cost of high-speed carrier design (PCIe, USB 3, HDMI routing) and higher price.

---

## 13. Reference projects and licensing

| Project | Licence | Reusable | Not reusable |
|---|---|---|---|
| MNT VA2000 (`mntmn/amiga2000-gfxcard`) [V S12] | **MIT** (© 2016 MNT). Also contains Mike Field SDRAM/DVI code under its own terms; not needed | The Zorro II symbol and edge-connector footprint (MIT notice required); the techniques (synchronised sampling, DOE-gated transceiver DIR, XRDY tri-stated, CFGOUT logic, 74LVC8T245 translation). We will **re-derive** pinouts from Commodore sources, not copy blindly | Mike Field-derived modules (separate licence) |
| AmiGUS (`necronomfive/AmiGUS-pub`) [V S13] | PCB **CC BY-NC-ND 4.0**; base software GPL-3.0+; drivers LGPL-3.0 | Study of published PDFs and BOM for ideas only. Facts and techniques are not copyrightable; the schematic and layout are | **No derivative of the PCB or schematic.** No HDL is published (binaries only) |
| Commodore Zorro III spec / A2000 documentation [V S10, S11] | Copyright Commodore (historic) | Facts (pinouts, timing, protocol) | Verbatim reproduction of large text |
| Radxa X4 schematic and STEP [V S1, S7] | Published by Radxa for users | Interface facts; mechanical checks | Redistribution of their files in our repo (link instead) |

---

## 14. Next step after your review: KiCad sheet 1, "Zorro II interface and AutoConfig"

Planned content (nothing drawn until you approve this review):
- **Edge connector.** A custom symbol with all 100 pins named per §4.1. The footprint is built from verified geometry (2.54 mm pitch, 2 × 50), cross-checked against VA2000 (MIT).
- **Address/control input buffers:** 2× 74LVC16244A.
- **Data transceiver:** SN74LVC16T245 (VCCA = 3.3 V local, VCCB = `+5V_BUS`).
- **Output drivers:** SN74LVC2T45 for /SLAVEn and /CFGOUTn; 74LVC07A open-drain for /INT2, /INT6 and XRDY, with DNP pads for /OVR and /DTACK.
- **Default states:** pull-ups and pull-downs that hold every Zorro output inactive while the FPGA is unconfigured.
- **Probing:** test points on /AS, /SLAVEn, DOE, E7M, /CFGINn, /CFGOUTn, /INT2 and READ.
- **Interfaces:** hierarchical labels to the FPGA sheet with named nets (`ZB_A[1..23]`, `LD[0..15]`, `ZB_AS_N` …).
- **Checks:** symbols verified against TI datasheets (pinouts quoted on the sheet). Run ERC with kicad-cli 10.0.8 and report the results without claiming validation. **Done:** see [stage2/](stage2/).
