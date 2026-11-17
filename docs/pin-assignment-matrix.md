# Pin-assignment matrix

**Status:** maintained document. Revision A, 2026-11-18 (Stage 1, preliminary).
- FPGA *package* pin numbers are assigned on KiCad sheet 2.
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

## 2. Zorro II edge connector (100 pins)

Pin names are from [V S11], cross-checked against [V S12]. Signal semantics are from [V S10]. **NC** means no copper connection beyond the finger (a no-connect flag in KiCad).

| Pin | Zorro II name | Net | Carrier connection | FPGA signal | Note |
|---|---|---|---|---|---|
| 1 | GND | GND | Ground plane | – | |
| 2 | GND | GND | Ground plane | – | |
| 3 | GND | GND | Ground plane | – | |
| 4 | GND | GND | Ground plane | – | |
| 5 | +5VDC | – | **NC** | – | No power from Zorro |
| 6 | +5VDC | – | **NC** | – | No power from Zorro |
| 7 | /OWN | – | NC | – | No DMA |
| 8 | −5VDC | – | NC | – | |
| 9 | /SLAVEn | `Z_SLAVE_N` | SN74LVC2T45 B-port (5 V) | `ZF_SLAVE_N` | ≤ 35 ns / ≤ 50 ns; pull-up keeps it inactive while unconfigured |
| 10 | +12VDC | – | **NC** | – | No power from Zorro |
| 11 | /CFGOUTn | `Z_CFGOUT_N` | SN74LVC2T45 B-port (5 V) | `ZF_CFGOUT_N` | Negated on reset |
| 12 | /CFGINn | `Z_CFGIN_N` | 74LVC16244A | `ZB_CFGIN_N` | |
| 13 | GND | GND | Ground plane | – | |
| 14 | /C3 | – | NC | – | |
| 15 | CDAC | `Z_CDAC` | 74LVC16244A (32nd channel) | `ZB_CDAC` (optional) | Uses 1 of the 6 spare FPGA pins if fitted |
| 16 | /C1 | – | NC | – | |
| 17 | /OVR | `Z_OVR_N` | 74LVC07A channel via **DNP** 0 Ω | – | Not used in rev 1 |
| 18 | XRDY | `Z_XRDY` | 74LVC07A (open drain) | `ZF_XRDY_HOLD` | Provisioned for wait states |
| 19 | /INT2 | `Z_INT2_N` | 74LVC07A (open drain) | `ZF_INT2` | Default IRQ |
| 20 | −12VDC | – | NC | – | |
| 21 | A5 | `Z_A5` | 74LVC16244A | `ZB_A5` | |
| 22 | /INT6 | `Z_INT6_N` | 74LVC07A (open drain) | `ZF_INT6` | Alternative IRQ |
| 23 | A6 | `Z_A6` | 74LVC16244A | `ZB_A6` | |
| 24 | A4 | `Z_A4` | 74LVC16244A | `ZB_A4` | |
| 25 | GND | GND | Ground plane | – | |
| 26 | A3 | `Z_A3` | 74LVC16244A | `ZB_A3` | |
| 27 | A2 | `Z_A2` | 74LVC16244A | `ZB_A2` | |
| 28 | A7 | `Z_A7` | 74LVC16244A | `ZB_A7` | |
| 29 | A1 | `Z_A1` | 74LVC16244A | `ZB_A1` | |
| 30 | A8 | `Z_A8` | 74LVC16244A | `ZB_A8` | |
| 31 | FC0 | – | NC | – | Not valid for Z2 DMA masters |
| 32 | A9 | `Z_A9` | 74LVC16244A | `ZB_A9` | |
| 33 | FC1 | – | NC | – | |
| 34 | A10 | `Z_A10` | 74LVC16244A | `ZB_A10` | |
| 35 | FC2 | – | NC | – | |
| 36 | A11 | `Z_A11` | 74LVC16244A | `ZB_A11` | |
| 37 | GND | GND | Ground plane | – | |
| 38 | A12 | `Z_A12` | 74LVC16244A | `ZB_A12` | |
| 39 | A13 | `Z_A13` | 74LVC16244A | `ZB_A13` | |
| 40 | (/EINT7) | – | NC | – | Unsupported |
| 41 | A14 | `Z_A14` | 74LVC16244A | `ZB_A14` | |
| 42 | (/EINT5) | – | NC | – | Unsupported |
| 43 | A15 | `Z_A15` | 74LVC16244A | `ZB_A15` | |
| 44 | (/EINT4) | – | NC | – | Unsupported |
| 45 | A16 | `Z_A16` | 74LVC16244A | `ZB_A16` | |
| 46 | /BERR | – | NC (optional TP) | – | Never driven |
| 47 | A17 | `Z_A17` | 74LVC16244A | `ZB_A17` | |
| 48 | (/VPA) | – | NC | – | |
| 49 | GND | GND | Ground plane | – | |
| 50 | E Clock | – | NC | – | |
| 51 | (/VMA) | – | NC | – | |
| 52 | A18 | `Z_A18` | 74LVC16244A | `ZB_A18` | |
| 53 | /RST | – | NC | – | Open-collector, bidirectional: do not load |
| 54 | A19 | `Z_A19` | 74LVC16244A | `ZB_A19` | |
| 55 | /HLT | – | NC | – | |
| 56 | A20 | `Z_A20` | 74LVC16244A | `ZB_A20` | |
| 57 | A22 | `Z_A22` | 74LVC16244A | `ZB_A22` | Note: 57 = A22, 58 = A21 |
| 58 | A21 | `Z_A21` | 74LVC16244A | `ZB_A21` | |
| 59 | A23 | `Z_A23` | 74LVC16244A | `ZB_A23` | |
| 60 | /BRn | – | NC | – | No DMA |
| 61 | GND | GND | Ground plane | – | |
| 62 | /BGACK | – | NC | – | |
| 63 | D15 | `Z_D15` | SN74LVC16T245 B-port | `LD15` (via transceiver) | |
| 64 | /BGn | – | NC | – | |
| 65 | D14 | `Z_D14` | SN74LVC16T245 B-port | `LD14` | |
| 66 | /DTACK | `Z_DTACK_N` | 74LVC07A channel via **DNP** 0 Ω | – | Automatic DTACK used |
| 67 | D13 | `Z_D13` | SN74LVC16T245 B-port | `LD13` | |
| 68 | READ | `Z_READ` | 74LVC16244A | `ZB_READ` | |
| 69 | D12 | `Z_D12` | SN74LVC16T245 B-port | `LD12` | |
| 70 | /LDS | `Z_LDS_N` | 74LVC16244A | `ZB_LDS_N` | |
| 71 | D11 | `Z_D11` | SN74LVC16T245 B-port | `LD11` | |
| 72 | /UDS | `Z_UDS_N` | 74LVC16244A | `ZB_UDS_N` | |
| 73 | GND | GND | Ground plane | – | |
| 74 | /AS | `Z_AS_N` | 74LVC16244A | `ZB_AS_N` | Combinational path to /SLAVEn |
| 75 | D0 | `Z_D0` | SN74LVC16T245 B-port | `LD0` | |
| 76 | D10 | `Z_D10` | SN74LVC16T245 B-port | `LD10` | |
| 77 | D1 | `Z_D1` | SN74LVC16T245 B-port | `LD1` | |
| 78 | D9 | `Z_D9` | SN74LVC16T245 B-port | `LD9` | |
| 79 | D2 | `Z_D2` | SN74LVC16T245 B-port | `LD2` | |
| 80 | D8 | `Z_D8` | SN74LVC16T245 B-port | `LD8` | |
| 81 | D3 | `Z_D3` | SN74LVC16T245 B-port | `LD3` | |
| 82 | D7 | `Z_D7` | SN74LVC16T245 B-port | `LD7` | |
| 83 | D4 | `Z_D4` | SN74LVC16T245 B-port | `LD4` | |
| 84 | D6 | `Z_D6` | SN74LVC16T245 B-port | `LD6` | |
| 85 | GND | GND | Ground plane | – | |
| 86 | D5 | `Z_D5` | SN74LVC16T245 B-port | `LD5` | |
| 87 | GND | GND | Ground plane | – | |
| 88 | GND | GND | Ground plane | – | |
| 89 | GND | GND | Ground plane | – | |
| 90 | GND | GND | Ground plane | – | |
| 91 | GND (Z2) / SenseZ3 | GND | Ground plane | – | Zorro II convention |
| 92 | E7M | `Z_E7M` | 74LVC16244A | `ZB_E7M` | Route to a clock-capable FPGA pin |
| 93 | DOE | `Z_DOE` | 74LVC16244A | `ZB_DOE` | Gates data-out |
| 94 | /BUSRST | `Z_BUSRST_N` | 74LVC16244A | `ZB_BUSRST_N` | Resets AutoConfig logic |
| 95 | /GBG | – | NC | – | |
| 96 | (/EINT1) | – | NC | – | |
| 97 | NC (Z2) | – | NC | – | /FCS on Z3 |
| 98 | NC (Z2) | – | NC | – | /DS1 on Z3 |
| 99 | GND | GND | Ground plane | – | |
| 100 | GND | GND | Ground plane | – | |

**Input buffer channel count.** 23 address + 4 strobes/READ + 4 (E7M, DOE, /CFGINn, /BUSRST) = 31, with CDAC as the 32nd. That fits 2× 74LVC16244A (32 channels) exactly.

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
| 16 | GP22 | **IRQ to PC** | `X4_GP22_IRQ_N` ← `RP_IRQ_N` | FPGA → RP2040 |
| 17 | 3.3 V (`P3V3_S`) | Reference (parallel with pin 1) | `X4_3V3_REF` | – |
| 18 | GP27 | **ATTN / flow control** | `X4_GP27_ATTN` ← `RP_ATTN` | FPGA → RP2040 |
| 19 | GP11 (SPI1 TX) | **MOSI** | `X4_GP11_MOSI` → `RP_MOSI` | RP2040 → FPGA |
| 20 | GND | GND | GND | – |
| 21 | GP8 (SPI1 RX) | **MISO** | `X4_GP8_MISO` ← `RP_MISO` | FPGA → RP2040 |
| 22 | GP24 | Reserved | – | – |
| 23 | GP10 (SPI1 SCK) | **SCK** | `X4_GP10_SCK` → `RP_SCK` | RP2040 → FPGA |
| 24 | GP9 (SPI1 CSn) | **CS_N** | `X4_GP9_CS_N` → `RP_CS_N` | RP2040 → FPGA |
| 25 | GND | GND | GND | – |
| 26 | GP18 | Reserved | – | – |
| 27 | GP16 | Reserved | – | – |
| 28 | GP17 | Reserved | – | – |
| 29 | GP7 | Reserved | – | – |
| 30 | GND | GND | GND | – |
| 31 | GP12 | Reserved | – | – |
| 32 | GP19 | Reserved | – | – |
| 33 | GP13 | Reserved | – | – |
| 34 | GND | GND | GND | – |
| 35 | GP15 | **JTAG TMS** (option, D-12) | `X4_GP15_TMS` → FPGA TMS | RP2040 → FPGA |
| 36 | GP26 | **JTAG TDI** (option) | `X4_GP26_TDI` → FPGA TDI | RP2040 → FPGA |
| 37 | GP14 | **JTAG TCK** (option) | `X4_GP14_TCK` → FPGA TCK | RP2040 → FPGA |
| 38 | GP2 | **JTAG TDO** (option) | `X4_GP2_TDO` ← FPGA TDO | FPGA → RP2040 |
| 39 | GND | GND | GND | – |
| 40 | GP25 | Reserved | – | – |

**Translator allocation** (3× SN74AVC4T774: A side = `+3V3`, B side = `X4_3V3_REF`):
- **U_a:** SCK, CS_N, MOSI (B→A) and MISO (A→B).
- **U_b:** IRQ_N and ATTN (A→B), plus 2 spare.
- **U_c (JTAG):** TCK, TMS, TDI (B→A) and TDO (A→B). /OE comes from a DIP switch, so the external JTAG header has priority when the switch is off.

## 4. FPGA I/O budget (LCMXO2-2000HC-4TG144C, 111 I/O)

| Group | Pins |
|---|---|
| Zorro inputs (`ZB_*`) | 31 (+1 optional CDAC) |
| Zorro outputs (`ZF_*`) | 5 |
| Transceiver DIR, /OE | 2 |
| `LD[15:0]` | 16 |
| SRAM `SA[17:0]` + 5 control | 23 |
| RP2040 link (`RP_*`) | 6 |
| X4 power/status | 3 |
| I²C telemetry | 3 |
| LEDs (5) + DIP (3) | 8 |
| Clock in | 1 |
| Debug/expansion header | 4 |
| **Subtotal** | **102** (103 with CDAC) |
| PROGRAMN, INITN, DONE (kept) | 3 |
| **Total** | **105–106 of 111** |

JTAG uses dedicated pins. Bank assignments (planned for sheet 2):
- Zorro inputs and outputs grouped on banks nearest the edge connector;
- `LD` and `SA` on the banks facing the SRAM;
- RP2040 and JTAG signals towards the X4 connector.

All banks run at VCCIO = 3.3 V.
