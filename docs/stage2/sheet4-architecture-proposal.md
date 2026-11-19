# Sheet 4: RP2040 SPI and host interface — architecture proposal (draft)

**Status:** proposal for owner decision before the RTL and schematic are built. 2026-11-19. Nothing here is implemented yet.

**Branch:** `stage2/sheet4-host-link`, based on sheet 2 rev A1 (PR #6). Evidence tags as in [../sources.md](../sources.md).

## 1. Requirements this sheet must meet

| Source | Requirement |
|---|---|
| Shared-memory spec §3.5 | Host-port contract **H-1 to H-6**: one transaction at a time, in order; hold until `h_ack`; latency up to one Zorro cycle (simulation max 2.62 µs, watchdog-bounded); the RP2040 never answers a Zorro cycle |
| Shared-memory spec §6 (owner, 2026-11-19) | Verification on the **real** SPI slave RTL: **HL-1** protocol and byte order at the pins, with a PL022-timed master model; **HL-2** CDC, formally or by CDC check plus random clock-ratio simulation; **HL-3** buffering for H-4 at maximum SCK, with overflow impossible or reported on ATTN; **HL-4** ordering; **HL-5** tb_z2/tb_shm through the real slave; **HL-6** stress during Amiga copy loops |
| C-26 (approved) | Four RP2040 LEDs on GP16–GP19 through a fourth SN74AVC4T774. The host status word carries `fault_ind`. READY stays independent of the X4 |
| D-12 | RP2040-driven JTAG option: TCK/TMS/TDI to the FPGA, TDO back, through a translator whose /OE is a DIP switch (sheet 6) |
| C-29, R-49 | No FPGA input driven while +3V3 is off: every header signal passes an Ioff/VCC-isolated translator |
| R-51 | Default resistors for RP_IRQ_N, RP_ATTN, RP_MISO, so an erased FPGA (weak pull-down) cannot signal an interrupt |
| ER-3, R-27 | Never load or backfeed the X4's header 3.3 V. The translator B side is supplied by `X4_3V3_REF` (µA only) |

## 2. Verified interface facts

| Fact | Value | Source |
|---|---|---|
| RP2040 SPI master peak bit rate | 62.5 Mbit/s | [V S65] PL022 §4.4 |
| PL022 Motorola mode with SPH = 0 (modes 0, 2) | **SSPFSSOUT is pulsed high between every data word**, even in continuous transfers | [V S65] |
| PL022 with SPH = 1 (modes 1, 3) | SSPFSSOUT held low between words while the TX FIFO has data; it ends the frame when the FIFO runs dry | [V S65] |
| SN74AVC4T774, VCCA = VCCB = 3.3 V ± 0.3 V | tpd A→B 0.1–2.9 ns, B→A 0.1–2.8 ns. OE low with DIR low: B→A; with DIR high: A→B. OE high: both ports Hi-Z | [V S66] |
| SN74AVC4T774 PW pinout | 1 DIR1, 2 DIR2, 3–6 A1–A4, 7 DIR3, 8 DIR4, 9 OE, 10 GND, 11 B4, 12 B3, 13 B2, 14 B1, 15 VCCB, 16 VCCA | [V S66] application figure |
| PC side of the RP2040 | USB 1.1 full speed: about 0.8–1.0 MB/s expected, the link's bottleneck | Architecture review §6 [V S1, K S41] |
| FPGA pins (frozen, G-SHEET2) | RP_SCK 1 (L_GPLLT_FB), RP_CS_N 2, RP_MOSI 3, RP_MISO 4, RP_IRQ_N 5 (**PCLKT5_0**), RP_ATTN 6 (PCLKC5_0) | [V S63]; `pins_gsheet2.csv` |

## 3. SPI slave architecture: options

| | A. Oversampled in `clk_core` | B. SCK-clocked front end + asynchronous FIFO | C. Oversampled at a PLL clock (e.g. 150 MHz, 3 × clk_core) |
|---|---|---|---|
| Clock domains | One (SCK, CS, MOSI synchronised as data) | Two: SCK and clk_core; Gray-pointer FIFO or handshake | Two related clocks from one PLL: synchronous ratio crossing |
| Maximum SCK, mode 0 | MISO must change after SCK↓ and settle before SCK↑. Synchroniser + edge detect + output ≈ 4 × 20 ns, so **SCK ≤ about 5.5 MHz** [D] | Limited by SCK↓ → MISO → master: about 19 ns at 20 MHz (see the note below), so **about 20 MHz** [E] | About 4 × 6.7 ns of latency, so **about 12–15 MHz** [E]; needs 150 MHz closure on −4 |
| Throughput (raw) | ≤ 0.69 MB/s: **below USB**, so the SPI becomes the bottleneck | ≈ 2.5 MB/s: USB-limited | ≈ 1.5–1.9 MB/s: USB-limited |
| HL-2 (CDC) | Trivial: 2-FF synchronisers | Standard async FIFO; prove with formal (pointer invariants) plus random-ratio simulation | Ratio crossing; simpler proof, but PLL lock and reset sequencing are added |
| Pin impact | None | SCK should be on a **primary-clock pin**. Pin 1 is not one; reaching the clock network from pin 1 needs general routing [K: to be confirmed in Diamond] | None (SCK is data) |
| Risk | Throughput below the PC link | CDC design and SCK clock routing | PLL and 150 MHz timing closure |

**Note on the option B estimate [E]:** cable 1 ns + translator 2.8 ns + FPGA clock insertion ≈ 6 ns + register and output ≈ 5 ns + translator 2.9 ns + cable 1 ns ≈ 19 ns, against a 25 ns half period. The RP2040's input-sampling delay is to be measured (new M-15).

**Recommendation: B at SCK = 20 MHz (target; TBV by STA and M-15).** It is the only option that keeps the SPI clearly above the USB ceiling with margin, and it matches the architecture review's 20–30 MHz assumption. It needs decision **S4-3** below.

## 4. Protocol proposal (to be detailed in the sheet-4 design notes)

- **Framing:**
  - firmware-controlled CS on GP9 as a GPIO (S4-2), so the PL022 pulsing in §2 cannot split a frame;
  - SPI mode 0;
  - MSB first, ascending addresses, as in the byte-order spec;
  - one transaction per CS-low period.
- **Commands:**
  - WRITE (SRAM or register, burst with auto-increment);
  - READ (split: see below);
  - STATUS (status word including `fault_ind` and the AMIGA_STATUS bits).
- **Reads and the H-4 latency.** The data for a read may not exist when the next byte is clocked, because a host request can wait out a whole Zorro cycle.
  - Proposal: a **split read**. Frame 1 carries the command and address. The FPGA executes and raises ATTN when the data is ready. Frame 2 reads the result.
  - Alternative: a polled ready byte.
- **Writes** are posted into the FIFO and executed in order (H-3, HL-4).
- **Flow control** (HL-3):
  - FIFO depth sized for 2.62 µs at 20 MHz (≈ 7 bytes), so ≥ 16 bytes;
  - ATTN reports "busy or full" and any overflow;
  - a sticky error is visible in STATUS.
- **Integrity:** CRC-16 (CCITT) per frame, in both directions (S4-4). A failed CRC discards the frame before any SRAM write and is reported in STATUS.

## 5. Sheet-4 hardware plan

| Part | Function |
|---|---|
| J401 | X4 GPIO ribbon header, 2 × 20, 2.54 mm, shrouded (BOM item 20) |
| U401 (U_a) | SCK, CS_N, MOSI B→A; MISO A→B |
| U402 (U_b) | IRQ_N, ATTN A→B; 2 spare |
| U403 (U_c) | JTAG: TCK, TMS, TDI B→A, TDO A→B. /OE from a DIP switch (sheet 6), so J201 has priority when it is off |
| U404 (U_d) | LEDs GP16–GP19 B→A, with 100 kΩ B-side pull-downs (C-26) |
| All translators | VCCA = +3V3 and VCCB = `X4_3V3_REF`, each with decoupling. Series resistors on SCK and MISO (values at layout) |
| Default resistors (R-51) | RP_IRQ_N pull-up on the A side, strong enough against the FPGA's 305 µA maximum weak pull-down; RP_ATTN and RP_MISO likewise |

## 6. Decisions for the owner

| ID | Question | Recommendation |
|---|---|---|
| **S4-1** | SPI slave architecture and SCK target | **B**, 20 MHz target, verified by STA and M-15 |
| **S4-2** | CS framing | Firmware GPIO CS on GP9, mode 0 |
| **S4-3** | **Change to the frozen pinout:** swap RP_SCK (pin 1) with RP_IRQ_N (pin 5, PCLKT5_0), so SCK reaches the primary clock network directly | Approve, *if* S4-1 = B. Under A or C no pin change is needed. Alternatively, keep pin 1 and accept general-routing clock insertion, if Diamond shows it closes (to be measured) |
| **S4-4** | Frame CRC | CRC-16/CCITT per frame, both directions |
| **S4-5** | Read style | Split read with ATTN |

After these decisions, sheet 4 follows the usual flow:
- RTL (`z2_hostif` replacing the stub), SPI master BFM, HL-1 to HL-6, formal for the FIFO;
- schematic, ERC, a netlist audit, Diamond;
- design notes and a PR.
