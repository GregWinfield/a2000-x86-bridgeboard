# Pin-assignment matrix

**Status:** maintained document. Revision G, 2026-11-19 (sheet 2 revision A1: G-SHEET2 approved; C-26 approved). Section 2 reflects sheet 1 rev B as built. Section 4 holds the owner's C-17 plan (102 signals) and, since revision F, the **physical FPGA pin assignment of sheet 2** (§4.1). Section 3 is still a plan.
- FPGA *package* pin numbers are assigned on KiCad sheet 2 by `tools/fpga/pinplan.py`. Full pin table: [stage2/sheet2-pin-assignment.md](stage2/sheet2-pin-assignment.md).
- Connector pin numbers below are verified [V].
- Carrier connections are proposals pending review.

## 1. Net naming convention

| Prefix / name | Domain | Meaning |
|---|---|---|
| `Z_<sig>` | 5 V, Zorro edge | Zorro connector net, e.g. `Z_A1`, `Z_D0`, `Z_AS_N` |
| `ZB_<sig>` | 3.3 V | Buffered Zorro input into the FPGA, e.g. `ZB_A1`, `ZB_AS_N` |
| `ZF_<sig>` | 3.3 V | FPGA-driven Zorro output before its driver, e.g. `ZF_SLAVE_N` |
| `LD[15:0]` | 3.3 V | Local data bus: Zorro transceiver ↔ SRAM ↔ FPGA |
| `SA[17:0]`, `SRAM_CE_N`, `SRAM_OE_N`, `SRAM_WE_N`, `SRAM_UB_N`, `SRAM_LB_N` | 3.3 V | SRAM address and control |
| `RP_<sig>` | carrier 3.3 V | FPGA side of the RP2040 link, e.g. `RP_SCK` |
| `X4_<sig>` | X4 3.3 V | X4 header side of the isolating translators, e.g. `X4_GP10_SCK` |
| `+12V_IN`, `+12V_PROT`, `+12V_X4` | 12 V | Molex 12 V; after fuse/TVS; eFuse output to J10 |
| `+5V_IN`, `+5V_BUS`, `+3V3` | 5 V / 3.3 V | Molex 5 V; protected 5 V for translators; LDO output |
| `X4_3V3_REF` | X4 3.3 V | X4 header pins 1/17 (`P3V3_S`, S0-only), reference supply only |
| suffix `_N` | – | Active low |

## 2. Zorro II edge connector J101 (100 pins), as built on sheet 1 (revision B)

- **Origin:** this table is **generated from the KiCad netlist** (`tools/kicad/pinmatrix_sheet1.py`). It follows each pin through series resistors, buffers and (rev B) the U107 enable gates to the 3.3 V FPGA-side net.
- **Sources:** pin names [V S11], cross-checked against [V S12]; signal semantics [V S10]; /BERR monitoring requirement [V S52].
- **Not connected:** a no-connect flag in KiCad; the finger exists but has no copper connection.
- **Netlist audit:** 418 checks, 0 failures ([stage2/sheet1-erc-report.md](stage2/sheet1-erc-report.md)).

| Pin | Zorro II name | Net | Carrier path (from netlist) | FPGA-side net |
|---|---|---|---|---|
| 1 | GND | GND | ground plane | – |
| 2 | GND | GND | ground plane | – |
| 3 | GND | GND | ground plane | – |
| 4 | GND | GND | ground plane | – |
| 5 | +5V | – | **not connected** (no-connect flag) | – |
| 6 | +5V | – | **not connected** (no-connect flag) | – |
| 7 | /OWN | – | **not connected** (no-connect flag) | – |
| 8 | -5V | – | **not connected** (no-connect flag) | – |
| 9 | /SLAVEn | `Z_SLAVE_N` | R117 22R → U104.21 (B1) ↔ U104.3 (A1); test point TP102 | `ZF_SLAVE_N` |
| 10 | +12V | – | **not connected** (no-connect flag) | – |
| 11 | /CFGOUTn | `Z_CFGOUT_N` | R118 22R → U104.20 (B2) ↔ U104.4 (A2); test point TP109 | `ZF_CFGOUT_N` |
| 12 | /CFGINn | `Z_CFGIN_N` | U102.29 (4A2) ↔ U102.20 (4Y2); test point TP108 | `ZB_CFGIN_N` |
| 13 | GND | GND | ground plane | – |
| 14 | /C3 | – | **not connected** (no-connect flag) | – |
| 15 | CDAC | – | **not connected** (no-connect flag) | – |
| 16 | /C1 | – | **not connected** (no-connect flag) | – |
| 17 | /OVR | `Z_OVR_N` | R119 0R DNP (DNP) → U105.8 (4Y) ↔ U105.9 (4A) | `ZF_OVR_N` |
| 18 | XRDY | `Z_XRDY` | U105.6 (3Y) ↔ U105.5 (3A) → `XRDY_G` → U107.6 (2Y) ↔ U107.4 (2A); test point TP111 | `ZF_XRDY` |
| 19 | /INT2 | `Z_INT2_N` | U105.2 (1Y) ↔ U105.1 (1A) → `INT2_G_N` → U107.8 (3Y) ↔ U107.9 (3A); test point TP110 | `ZF_INT2_N` |
| 20 | -12V | – | **not connected** (no-connect flag) | – |
| 21 | A5 | `Z_A5` | U101.41 (2A1) ↔ U101.8 (2Y1) | `ZB_A5` |
| 22 | /INT6 | `Z_INT6_N` | U105.4 (2Y) ↔ U105.3 (2A) → `INT6_G_N` → U107.11 (4Y) ↔ U107.12 (4A) | `ZF_INT6_N` |
| 23 | A6 | `Z_A6` | U101.40 (2A2) ↔ U101.9 (2Y2) | `ZB_A6` |
| 24 | A4 | `Z_A4` | U101.43 (1A4) ↔ U101.6 (1Y4) | `ZB_A4` |
| 25 | GND | GND | ground plane | – |
| 26 | A3 | `Z_A3` | U101.44 (1A3) ↔ U101.5 (1Y3) | `ZB_A3` |
| 27 | A2 | `Z_A2` | U101.46 (1A2) ↔ U101.3 (1Y2) | `ZB_A2` |
| 28 | A7 | `Z_A7` | U101.38 (2A3) ↔ U101.11 (2Y3) | `ZB_A7` |
| 29 | A1 | `Z_A1` | U101.47 (1A1) ↔ U101.2 (1Y1) | `ZB_A1` |
| 30 | A8 | `Z_A8` | U101.37 (2A4) ↔ U101.12 (2Y4) | `ZB_A8` |
| 31 | FC0 | – | **not connected** (no-connect flag) | – |
| 32 | A9 | `Z_A9` | U101.36 (3A1) ↔ U101.13 (3Y1) | `ZB_A9` |
| 33 | FC1 | – | **not connected** (no-connect flag) | – |
| 34 | A10 | `Z_A10` | U101.35 (3A2) ↔ U101.14 (3Y2) | `ZB_A10` |
| 35 | FC2 | – | **not connected** (no-connect flag) | – |
| 36 | A11 | `Z_A11` | U101.33 (3A3) ↔ U101.16 (3Y3) | `ZB_A11` |
| 37 | GND | GND | ground plane | – |
| 38 | A12 | `Z_A12` | U101.32 (3A4) ↔ U101.17 (3Y4) | `ZB_A12` |
| 39 | A13 | `Z_A13` | U101.30 (4A1) ↔ U101.19 (4Y1) | `ZB_A13` |
| 40 | /EINT7 | – | **not connected** (no-connect flag) | – |
| 41 | A14 | `Z_A14` | U101.29 (4A2) ↔ U101.20 (4Y2) | `ZB_A14` |
| 42 | /EINT5 | – | **not connected** (no-connect flag) | – |
| 43 | A15 | `Z_A15` | U101.27 (4A3) ↔ U101.22 (4Y3) | `ZB_A15` |
| 44 | /EINT4 | – | **not connected** (no-connect flag) | – |
| 45 | A16 | `Z_A16` | U101.26 (4A4) ↔ U101.23 (4Y4) | `ZB_A16` |
| 46 | /BERR | `Z_BERR_N` | U102.26 (4A4) ↔ U102.23 (4Y4); test point TP113 | `ZB_BERR_N` |
| 47 | A17 | `Z_A17` | U102.47 (1A1) ↔ U102.2 (1Y1) | `ZB_A17` |
| 48 | /VPA | – | **not connected** (no-connect flag) | – |
| 49 | GND | GND | ground plane | – |
| 50 | E | – | **not connected** (no-connect flag) | – |
| 51 | /VMA | – | **not connected** (no-connect flag) | – |
| 52 | A18 | `Z_A18` | U102.46 (1A2) ↔ U102.3 (1Y2) | `ZB_A18` |
| 53 | /RST | – | **not connected** (no-connect flag) | – |
| 54 | A19 | `Z_A19` | U102.44 (1A3) ↔ U102.5 (1Y3) | `ZB_A19` |
| 55 | /HLT | – | **not connected** (no-connect flag) | – |
| 56 | A20 | `Z_A20` | U102.43 (1A4) ↔ U102.6 (1Y4) | `ZB_A20` |
| 57 | A22 | `Z_A22` | U102.40 (2A2) ↔ U102.9 (2Y2) | `ZB_A22` |
| 58 | A21 | `Z_A21` | U102.41 (2A1) ↔ U102.8 (2Y1) | `ZB_A21` |
| 59 | A23 | `Z_A23` | U102.38 (2A3) ↔ U102.11 (2Y3) | `ZB_A23` |
| 60 | /BRn | – | **not connected** (no-connect flag) | – |
| 61 | GND | GND | ground plane | – |
| 62 | /BGACK | – | **not connected** (no-connect flag) | – |
| 63 | D15 | `Z_D15` | RN104 4x22R → U103.23 (2B8) ↔ U103.26 (2A8) | `LD15` |
| 64 | /BGn | – | **not connected** (no-connect flag) | – |
| 65 | D14 | `Z_D14` | RN104 4x22R → U103.22 (2B7) ↔ U103.27 (2A7) | `LD14` |
| 66 | /DTACK | `Z_DTACK_N` | R120 0R DNP (DNP) → U105.10 (5Y) ↔ U105.11 (5A) | `ZF_DTACK_N` |
| 67 | D13 | `Z_D13` | RN104 4x22R → U103.20 (2B6) ↔ U103.29 (2A6) | `LD13` |
| 68 | READ | `Z_READ` | U102.33 (3A3) ↔ U102.16 (3Y3); test point TP105 | `ZB_READ` |
| 69 | D12 | `Z_D12` | RN104 4x22R → U103.19 (2B5) ↔ U103.30 (2A5) | `LD12` |
| 70 | /LDS | `Z_LDS_N` | U102.35 (3A2) ↔ U102.14 (3Y2); test point TP107 | `ZB_LDS_N` |
| 71 | D11 | `Z_D11` | RN103 4x22R → U103.17 (2B4) ↔ U103.32 (2A4) | `LD11` |
| 72 | /UDS | `Z_UDS_N` | U102.36 (3A1) ↔ U102.13 (3Y1); test point TP106 | `ZB_UDS_N` |
| 73 | GND | GND | ground plane | – |
| 74 | /AS | `Z_AS_N` | U102.37 (2A4) ↔ U102.12 (2Y4); test point TP101 | `ZB_AS_N` |
| 75 | D0 | `Z_D0` | RN101 4x22R → U103.2 (1B1) ↔ U103.47 (1A1) | `LD0` |
| 76 | D10 | `Z_D10` | RN103 4x22R → U103.16 (2B3) ↔ U103.33 (2A3) | `LD10` |
| 77 | D1 | `Z_D1` | RN101 4x22R → U103.3 (1B2) ↔ U103.46 (1A2) | `LD1` |
| 78 | D9 | `Z_D9` | RN103 4x22R → U103.14 (2B2) ↔ U103.35 (2A2) | `LD9` |
| 79 | D2 | `Z_D2` | RN101 4x22R → U103.5 (1B3) ↔ U103.44 (1A3) | `LD2` |
| 80 | D8 | `Z_D8` | RN103 4x22R → U103.13 (2B1) ↔ U103.36 (2A1) | `LD8` |
| 81 | D3 | `Z_D3` | RN101 4x22R → U103.6 (1B4) ↔ U103.43 (1A4) | `LD3` |
| 82 | D7 | `Z_D7` | RN102 4x22R → U103.12 (1B8) ↔ U103.37 (1A8) | `LD7` |
| 83 | D4 | `Z_D4` | RN102 4x22R → U103.8 (1B5) ↔ U103.41 (1A5) | `LD4` |
| 84 | D6 | `Z_D6` | RN102 4x22R → U103.11 (1B7) ↔ U103.38 (1A7) | `LD6` |
| 85 | GND | GND | ground plane | – |
| 86 | D5 | `Z_D5` | RN102 4x22R → U103.9 (1B6) ↔ U103.40 (1A6) | `LD5` |
| 87 | GND | GND | ground plane | – |
| 88 | GND | GND | ground plane | – |
| 89 | GND | GND | ground plane | – |
| 90 | GND | GND | ground plane | – |
| 91 | GND/SenseZ3 | GND | ground plane | – |
| 92 | E7M | `Z_E7M` | U102.30 (4A1) ↔ U102.19 (4Y1); test point TP104 | `ZB_E7M` |
| 93 | DOE | `Z_DOE` | U102.32 (3A4) ↔ U102.17 (3Y4); test point TP103 | `ZB_DOE` |
| 94 | /BUSRST | `Z_BUSRST_N` | U102.27 (4A3) ↔ U102.22 (4Y3); test point TP112 | `ZB_BUSRST_N` |
| 95 | /GBG | – | **not connected** (no-connect flag) | – |
| 96 | /EINT1 | – | **not connected** (no-connect flag) | – |
| 97 | NC | – | **not connected** (no-connect flag) | – |
| 98 | NC | – | **not connected** (no-connect flag) | – |
| 99 | GND | GND | ground plane | – |
| 100 | GND | GND | ground plane | – |

**Input buffer channels.** 23 address + /AS, /UDS, /LDS, READ + DOE, E7M, /CFGINn, /BUSRST + /BERR = 32. That uses all 32 channels of U101/U102. Rev B moved the last channel from CDAC (monitor only, R-29) to /BERR, which a card must monitor so that it can release its bus drivers [V S52].

**Gated outputs (rev B).** XRDY, /INT2 and /INT6 reach U105 through U107, ORed with CARD_EN_N; /SLAVEn and /CFGOUTn pass U104, whose /OE is CARD_EN_N. When the card is not enabled, every Zorro-side driver is off and the slot behaves as an empty slot.

## 3. Radxa X4 40-pin header (via ribbon)

Header mapping: [V S1 sh.21], matches [V S5]. RP2040 alternate functions: [K S41] / [V S5].

| X4 pin | X4 net / RP2040 GPIO | Proposed use | Carrier net (X4 side → FPGA side) | Direction |
|---|---|---|---|---|
| 1 | 3.3 V (`P3V3_S`, S0-only) | Translator VCCB reference + S0 sense | `X4_3V3_REF` | X4 → carrier (µA only) |
| 2 | 5 V (`P5V_A` via D42) | **Not connected** (backfeed prevention) | – | – |
| 3 | GP28 | Reserved | – | – |
| 4 | 5 V | **Not connected** | – | – |
| 5 | GP29 | Reserved | – | – |
| 6 | GND | GND | GND | – |
| 7 | GP4 | Reserved | – | – |
| 8 | GP20 | Reserved (UART1 TX: possible FPGA debug UART) | – | – |
| 9 | GND | GND | GND | – |
| 10 | GP21 | Reserved (UART1 RX) | – | – |
| 11 | GP5 | Reserved | – | – |
| 12 | GP23 | Reserved | – | – |
| 13 | GP6 | Reserved | – | – |
| 14 | GND | GND | GND | – |
| 15 | GP3 | Reserved | – | – |
| 16 | GP22 | **IRQ to PC** | `X4_GP22_IRQ_N` ← R412 ← U402 ← `RP_IRQ_N`; R424 10k to `RP_VIO` | FPGA → RP2040 |
| 17 | 3.3 V (`P3V3_S`) | Reference (parallel with pin 1) | `X4_3V3_REF` | – |
| 18 | GP27 | **ATTN / flow control** | `X4_GP27_ATTN` ← R413 ← U402 ← `RP_ATTN`; R425 100k to GND | FPGA → RP2040 |
| 19 | GP11 (SPI1 TX) | **MOSI** | `X4_GP11_MOSI` → U401 → `RP_MOSI`; R420 100k to GND | RP2040 → FPGA |
| 20 | GND | GND | GND | – |
| 21 | GP8 (SPI1 RX) | **MISO** | `X4_GP8_MISO` ← R411 ← U402 ← `RP_MISO` | FPGA → RP2040 |
| 22 | GP24 | **RP_VIO: U402's B-side supply** (S4-6, proposed); firmware drives it high | `X4_GP24_VIO` → R416 47R → `RP_VIO` | RP2040 → carrier |
| 23 | GP10 (SPI1 SCK) | **SCK** | `X4_GP10_SCK` → U401 → `RP_SCK` (FPGA pin 5, S4-3); R418 100k to GND | RP2040 → FPGA |
| 24 | GP9 (SPI1 CSn) | **CS_N** (GPIO, S4-2) | `X4_GP9_CS_N` → U401 → `RP_CS_N`; R419 100k to GND | RP2040 → FPGA |
| 25 | GND | GND | GND | – |
| 26 | GP18 | **Diagnostic LED** (C-26, option C-17b) | `X4_GP18_LED` → carrier LED via SN74AVC4T774 (B→A) | RP2040 → carrier |
| 27 | GP16 | **Diagnostic LED** (C-26, option C-17b) | `X4_GP16_LED` → carrier LED via SN74AVC4T774 (B→A) | RP2040 → carrier |
| 28 | GP17 | **Diagnostic LED** (C-26, option C-17b) | `X4_GP17_LED` → carrier LED via SN74AVC4T774 (B→A) | RP2040 → carrier |
| 29 | GP7 | Reserved | – | – |
| 30 | GND | GND | GND | – |
| 31 | GP12 | Reserved | – | – |
| 32 | GP19 | **Diagnostic LED** (C-26, option C-17b) | `X4_GP19_LED` → carrier LED via SN74AVC4T774 (B→A) | RP2040 → carrier |
| 33 | GP13 | Reserved | – | – |
| 34 | GND | GND | GND | – |
| 35 | GP15 | **JTAG TMS** (option, D-12) | `X4_GP15_TMS` → U403 → FPGA TMS; R422 100k to GND | RP2040 → FPGA |
| 36 | GP26 | **JTAG TDI** (option) | `X4_GP26_TDI` → U403 → FPGA TDI; R423 100k to GND | RP2040 → FPGA |
| 37 | GP14 | **JTAG TCK** (option) | `X4_GP14_TCK` → U403 → FPGA TCK; R421 100k to GND | RP2040 → FPGA |
| 38 | GP2 | **JTAG TDO** (option) | `X4_GP2_TDO` ← R414 ← U402 ← FPGA TDO | FPGA → RP2040 |
| 39 | GND | GND | GND | – |
| 40 | GP25 | Reserved | – | – |

Not on the header: GP0/GP1 go to the N100's UART1 (R314/R315 0 Ω); GP23 also has an unfitted 0 Ω (R316, NC) to an N100 GPIO [V S1 sheet 21].

**Option C-17b: approved 2026-11-19 (C-26).** LEDs on **GP16–GP19** (header pins 27, 28, 26, 32) through a fourth SN74AVC4T774 (U_d), all channels B→A, with 100 kΩ B-side pull-downs. The net names `X4_GPnn_LED` are provisional until sheet 4. GPIO availability, LED drive current, reset state and power-off behaviour are verified on sheets 4/6. READY stays on the FPGA, so standalone indication does not depend on the X4. See [stage2/sheet3-design-notes.md](stage2/sheet3-design-notes.md) §8.2.

**Translator allocation, sheet 4 revision A** (4× SN74AVC4T774, A side = `+3V3`; [stage2/sheet4-design-notes.md](stage2/sheet4-design-notes.md) §6):
- **U401:** SCK, CS_N, MOSI (B→A); B side `X4_3V3_REF`.
- **U402:** IRQ_N, ATTN, MISO, TDO, every FPGA → RP2040 signal (A→B). **B side `RP_VIO` = RP2040 GP24 (proposed S4-6)**, so no output can exceed the RP2040's own supply, which the X4 can switch off while its header 3.3 V stays up [V S1 sh.21].
- **U403 (JTAG option):** TCK, TMS, TDI (B→A); B side `X4_3V3_REF`. /OE comes from a DIP switch (sheet 6), so the external JTAG header has priority when the switch is off.
- **U404:** the four RP2040 LEDs (B→A); B side `X4_3V3_REF` (C-26).
- Every RP2040 → carrier input has a 100 kΩ B-side pull-down. *Superseded allocation (proposal): U_a carried MISO and U_c carried TDO, all B sides on `X4_3V3_REF`.*

## 4. FPGA I/O budget (LCMXO2-2000HC-4TG144C)

> **Revision D correction (2026-11-19).** The MachXO2 datasheet counts **111 general-purpose I/O** for the 144 TQFP: banks 0–5 = 27/28/28/8/10/10, plus 1 pin reserved for configuration (Table 4.4 [V S49]). The 33 dual-function I/O within the 111 include **TMS, TCK, TDI and TDO**. With the JTAG port enabled, which this design needs, Diamond reserves them ("PIO sites used: n + 4(JTAG) out of 112" [V S62]). **The table below therefore needs 114 pins, not 110.** The JTAG pins are not dedicated, contrary to revision C. Recommended plan and Diamond fit tests: [stage2/sheet3-design-notes.md](stage2/sheet3-design-notes.md) §8. Decision C-17.

Revision C table (sheet 1 rev B). The Stage 1 count omitted `ZF_OVR_N` and `ZF_DTACK_N`, which are FPGA nets on sheet 1; they are included.

| Group | Pins |
|---|---|
| Zorro inputs (`ZB_*`: 23 address, /AS, /UDS, /LDS, READ, DOE, E7M, /CFGINn, /BUSRST, /BERR) | 32 |
| Zorro outputs (`ZF_SLAVE_N`, `ZF_CFGOUT_N`, `ZF_INT2_N`, `ZF_INT6_N`, `ZF_XRDY`) | 5 |
| `ZF_OVR_N`, `ZF_DTACK_N` (outputs DNP-isolated in Rev 1) | 2 |
| Transceiver `ZF_DBUF_DIR`, `ZF_DBUF_OE_N` | 2 |
| Card enable: `ZF_ARM` (out), `EN_OK` (in), rev B | 2 |
| `LD[15:0]` | 16 |
| SRAM `SA[17:0]` + 5 control | 23 |
| RP2040 link (`RP_*`) | 6 |
| X4 power/status | 3 |
| I²C telemetry | 3 |
| LEDs (5) + DIP (3) | 8 (rev E: 2 LEDs + 3 DIP = 5) |
| Clock in | 1 |
| Debug/expansion header | 4 |
| **Subtotal** | **107** |
| PROGRAMN, INITN, DONE (kept) | 3 |
| **Total** | **110**, plus **4 JTAG = 114 of 111: does not fit** (rev D) |
| **Rev E plan (owner decision C-17, 2026-11-19):** ZF_OVR_N, ZF_DTACK_N not routed; **2 LEDs**; PROGRAMN, INITN, DONE kept as configuration pins; JTAG kept | **102 signals; 111 − 4 JTAG − 3 configuration = 104 available; 2 spare.** Diamond fit test `fit_top`: 102 + 4 JTAG of 112 placed, 0 timing errors (JTAGENB and SN prohibited, so a conservative 103 available) |
| Option C-17b: 4 LEDs on RP2040 GPIO, 1 FPGA READY LED | **Approved (C-26, 2026-11-19): 101 signals, 3 spare** (pins 23, 24, 67) |

**Concern C-14 (sheet 2).** One spare pin is too tight. Planned resolution, at no cost to Rev 1 function: do not route `ZF_OVR_N` and `ZF_DTACK_N` to the FPGA. R106/R107 already hold the U105 inputs high and R119/R120 (DNP) isolate the outputs, giving **108 of 111**. Alternative: LCMXO2-4000HC in the same package (I/O count TBV against the MachXO2 data sheet before relying on it). *Revision F:* the sheet-2 assignment is pin-compatible with the LCMXO2-4000HC-4TG144C and meets timing on it ([stage2/sheet2-design-notes.md](stage2/sheet2-design-notes.md) §7).

JTAG uses four of the general-purpose pins while the JTAG port is enabled. Pin rules for sheet 2 (sheet-3 notes §8.1):
- PROGRAMN, INITN and DONE: configuration only.
- JTAGENB: no signal (C-19).
- **SN: never an externally driven input**, because it must not be low while the device is erased.
- `clk_core` on a PCLK pin.

### 4.1 Physical assignment (sheet 2 revision A, 2026-11-19)

Generated by `tools/fpga/pinplan.py` from the Lattice pinout data [V S63]. The same computation writes the LPF LOCATEs and the schematic pins. `audit_sheet2.py` checks the netlist against the pinout data, the LPF and the HDL port directions.

| Bank | Used / pads | Contents |
|---|---|---|
| 0 | 20 / 28 (8 reserved: PROGRAMN 119, INITN 110, DONE 109, JTAGENB 120, TMS 130, TCK 131, TDI 136, TDO 137) | clk_core on PCLKT0_1 (128); I2C_SDA 125, I2C_SCL 126 (primary I2C pins); INA_ALERT_N, X4_PWR_EN, X4_PWR_FLT_N, X4_S0_SENSE; ZB_A10–A15, ZB_E7M, ZB_BUSRST_N; ZF_INT2_N, ZF_INT6_N, ZF_DBUF_DIR, ZF_ARM, EN_OK |
| 1 | 28 / 28 | /SLAVEn, XRDY and buffer-enable decode group: ZB_A16–A23, /AS, /BERR, DOE, READ, /UDS, /LDS, /CFGIN; ZF_SLAVE_N, ZF_XRDY, ZF_DBUF_OE_N, ZF_CFGOUT_N; ZB_A1–A9 |
| 2 | 27 / 28 | SA0–SA17 (SA17 on SN, pin 70: an output, 4.7 kΩ pull-up), SRAM_CE_N/OE_N/WE_N/UB_N/LB_N, LED_READY (65), DIP_MODE_B, DIP_INT6, DIP_DISABLE; **spare pin 67** (C-26) |
| 3 | 8 / 8 | LD0–LD7 |
| 4 | 8 / 10 | LD8–LD15; **spare pins 23, 24** |
| 5 | 10 / 10 | RP_SCK, RP_CS_N, RP_MOSI, RP_MISO, RP_IRQ_N, RP_ATTN, DBG0–DBG3 |

- **Budget:** 104 usable (112 pads − 8 reserved, or equally 111 − 7, so C-19 does not affect it); **101 signals; 3 spare** (pins 23, 24, 67). C-26 freed pin 67; every other pin is unchanged from the G-SHEET2-approved assignment (`tools/fpga/pins_gsheet2.csv`).
- **Voltage:** every bank at VCCIO 3.3 V on the same supply as VCC; every port LVCMOS33 (Diamond pad check on every run).
- **Fallback:** the assignment is valid unchanged on the LCMXO2-4000HC-4TG144C (same banks; configuration, JTAG, SN, PCLK and I2C on the same pins).
- **Timing at these pins:** [stage2/sheet2-sta-results.md](stage2/sheet2-sta-results.md).
