# Sheet 4: host-link SPI timing budget (owner requirement 4)

**Revision A3, 2026-11-19** (S4-6 rev A2 and A3 change only U402's output-enable circuit; U402's B side stays on the header 3.3 V, as in rev A1, so the figures below are unchanged). This document sets the board-level budget for the SCK-to-MISO path. It also covers MOSI capture, chip select and ATTN at the two SCK targets of decision S4-1: **10 MHz initial** and **20 MHz performance**.

**Inputs:**
- FPGA figures: Diamond STA at the frozen pins on the LCMXO2-4000HC ([sheet4-sta-results.md](sheet4-sta-results.md) §2);
- translator figures: TI SCES693I [V S66];
- everything else: an assumption [A] or an estimate [E], each listed in §5 with the measurement that replaces it.

> **Status:**
> - The budget closes on paper at both targets: 10 MHz with the standard MISO launch and 20 MHz with the early launch.
> - It rests on one conservative assumption about the RP2040's input sampling [A], and on one unmeasured property for early launch (§3.3).
> - **Owner decision (review of PR #7): 10 MHz is the initial operating rate; 20 MHz stays experimental until M-15 establishes safe timing.** M-15 decides the launch edge.

> **Rounding rule (owner refinement 4):** delays and requirements are rounded up; margins and minimum delays are rounded down.

## 1. Path elements

All times are at the pins. "RP2040 pin" means the RP2040 package pin, at the X4 end of the ribbon.

| Term | Maximum | Minimum | Source |
|---|---|---|---|
| Ribbon + carrier traces, per direction | **1.0 ns** | 0 | [A]: ribbon ≤ 15 cm (D-07, about 5 ns/m) plus ≤ 5 cm of carrier trace. Layout and M-15 |
| U401 B→A (SCK, MOSI, CS_N), VCCA = VCCB = 3.3 V ± 0.3 V | 2.8 ns | 0.1 ns | [V S66] |
| U402 A→B (MISO), VCCA = VCCB = 3.3 V ± 0.3 V | 2.9 ns | 0.1 ns | [V S66]. Since S4-6 rev A1 U402's B side is on the header 3.3 V again (its /OE is gated, §5 item 4); unchanged in rev A2 |
| **t_IN**: RP2040 SCK pin → FPGA pin 5 | **3.8 ns** | 0.1 ns | 1.0 + 2.8 |
| **t_OUT**: FPGA pin 4 → RP2040 MISO pin (incl. R411 33 Ω) | **3.9 ns** | 0.1 ns | 2.9 + 1.0 |
| **t_FPGA**: SCK edge at pin 5 → MISO at pin 4 | 15.371 ns (default build), 14.120 ns (early build) | 3.349 ns (default), **3.200 ns** (early) | Diamond, worst of the runs; includes the SCK pad (1.163 ns), the primary clock net (2.364 ns), the flop, the multiplexer and the output pad at 15 pF |
| **t_RS**: the RP2040 samples MISO this long **before** its own SCK↑ at its pin | **16 ns** | – | [A], conservative: two clk_peri periods of input synchronisation at 125 MHz. The SPI master model samples at this offset (`rx_skew`, randomised 0–16 ns in tb_spi P15). Replaced by M-15 |

**FPGA allocation:** the LPF allows t_FPGA ≤ 20 ns (`CLOCK_TO_OUT … MAX 20 ns`). The budget allows ≤ 26.3 ns (§2), so the constraint is stricter than the budget.

## 2. SCK → MISO, setup side

The MISO bit must reach the RP2040 pin t_RS before the SCK↑ that samples it:

    t_IN + t_FPGA + t_OUT + t_RS ≤ W

**W** is the time from the launching edge to the sampling edge, measured at the RP2040:
- **standard launch** (default build, `LAUNCH_RISE = 0`): MISO changes after SCK↓, so W = T/2;
- **early launch** (`-DZ2_LAUNCH_RISE`, `LAUNCH_RISE = 1`): MISO changes after the SCK↑ that sampled the previous bit, so W = T.

The fixed terms are 3.8 + 3.9 + 16 = **23.7 ns**, so **t_FPGA ≤ W − 23.7 ns.**

| Mode | SCK | W | t_FPGA allowed | STA worst | Margin |
|---|---|---|---|---|---|
| **Standard** | **10 MHz** | 50 ns | 26.3 ns | 15.371 ns | **≥ 10.92 ns** |
| Standard | 20 MHz | 25 ns | 1.3 ns | 15.371 ns | **−14.08 ns: not usable** |
| Early | 10 MHz | 100 ns | 76.3 ns | 14.120 ns | ≥ 62.18 ns |
| **Early** | **20 MHz** | 50 ns | 26.3 ns | 14.120 ns | **≥ 12.18 ns** |

**Result:**
- **10 MHz closes with the standard launch.**
- **20 MHz needs the early launch.** The standard launch would need t_FPGA ≤ 1.3 ns, which no FPGA path can meet.

The simulations exercise both modes with these delays at the pins:
- tb_spi with `HALF_MIN`/`HALF_MAX` and t_RS up to 16 ns;
- standard launch up to 10 MHz;
- early launch up to 20 MHz.

Four seeds each pass in `run_checks.sh`.

## 3. Hold side and the early-launch condition

### 3.1 Standard launch

MISO changes after SCK↓, half a period after the sampling edge. Any sampling instant within T/2 of the RP2040's SCK↑ is safe. There is no hold condition at either rate.

### 3.2 MOSI and CS_N at the FPGA

The RP2040 changes MOSI on SCK↓ (mode 0), and SCK and MOSI travel through matched paths (U401, the same ribbon).

**Skew between them, at most 4.8 ns:**

| Contribution | Value | Source |
|---|---|---|
| Translator delay spread | 2.7 ns | 0.1–2.8 ns [V S66]; no channel-to-channel skew is specified, so the full spread is used |
| Trace mismatch | 0.1 ns | [A] |
| RP2040 SCK-to-MOSI output skew | 2.0 ns | [A] |

**Setup and hold available at the FPGA pins:** T/2 − 4.8 ns.
- 45.2 ns at 10 MHz;
- 20.2 ns at 20 MHz.

**Requirements:**
- The LPF states 20 ns of setup and 20 ns of hold, which is within 20.2 ns.
- The FPGA needs ≤ 6.496 ns of setup, so the margin is ≥ 13.7 ns at 20 MHz.
- TRACE reports 0 hold errors against the 20 ns hold.

**CS_N:** CS_N↓ to the first SCK↑ ≥ 100 ns (tCSS), last SCK↓ to CS_N↑ ≥ 100 ns (tCSH), protocol §2.
- CS_N is the asynchronous reset of the SCK-domain frame registers. Its timing is a design rule, not an STA path (`BLOCK RESETPATHS`).
- tb_spi P15 randomises tCSS and tCSH over 100–500 ns.

### 3.3 Early launch: the condition M-15 must confirm

With early launch, MISO for bit n changes after the same SCK↑ at which the RP2040 samples bit n − 1.

**The condition:** the RP2040 must capture bit n − 1 before the change arrives at its pin. The fastest change arrives this long after the RP2040's SCK↑ at its pin:

    t_IN,min + t_FPGA,min + t_OUT,min = 0.1 + 3.200 + 0.1 = 3.4 ns (rounded down)

So early launch is safe if the RP2040 samples MISO **no later than 3.4 ns after its own SCK↑ at the pin**.

**What we know:**
- The model in §1 assumes it samples *before* the edge (t_RS ≥ 0); then this always holds.
- The PL022 is clocked from the same internal clock that generates SCK, so sampling before the pin edge is plausible, but it is not verified [E].

**Hardware measurement M-15:** before the early launch is used, measure both sides on a prototype:
- the setup side: the largest t_RS at which reads still succeed, sweeping the SCK rate;
- the hold side: delay MISO deliberately (an RC on the bench) until reads fail.

The FPGA reports which build it is in IDENTIFY: FEATURES b2 = 1 for early launch (protocol §1). Firmware must not run above 10 MHz on a standard build.

## 4. Other host-link signals

| Signal | Requirement | Budget | Margin |
|---|---|---|---|
| ATTN fall after CS_N↓ (protocol §8: "within 100 ns") | ≤ 100 ns at the RP2040 | t_IN 3.8 + CS_N synchroniser 2 clocks (40 ns) + ATTN register 1 clock (20 ns) + output/t_OUT ≤ 10 ns → ≤ 73.8 ns | ≥ 26.2 ns |
| ATTN, RP_IRQ_N | Level signals sampled by firmware; registered in clk_core | – | No timing relation to SCK |
| RP2040 LEDs (U404) | Static | – | – |
| JTAG option (U403 B→A, TDO via U402) | TCK ≤ a few MHz from RP2040 firmware (bit-banged) [A] | 3.8 + 3.9 ns of translator and ribbon delay per round trip | Large at any bit-banged rate; MachXO2 JTAG limits [V S49] apply |

## 5. Assumptions and the measurements that replace them

| # | Assumption | Value used | Replaced by |
|---|---|---|---|
| 1 | Ribbon and carrier-trace delay per direction | ≤ 1.0 ns | Layout (trace lengths), then M-15 (scope at both ends) |
| 2 | RP2040 MISO sampling before its SCK↑ pin edge | ≤ 16 ns (setup side) | **M-15** |
| 3 | RP2040 MISO sampling after its SCK↑ pin edge (early launch only) | ≤ 3.4 ns needed | **M-15** |
| 4 | U402's B supply = X4_3V3_REF (P3V3_S, 3.135–3.465 V [A]) inside the 3.3 V ± 0.3 V column. *Revision A's GPIO-sourced RP_VIO, which needed this check, is withdrawn (S4-6 rev A1)* | – | P3V3_S tolerance: X4 measurement (M-16) |
| 5 | RP2040 SCK-to-MOSI output skew | ≤ 2.0 ns | M-15 |
| 6 | 15 pF STA output load covers pin 4 + U402 A input + trace | Conservative [A] | Layout |

**M-15:** host-link SPI timing on hardware.
- **Setup:** a prototype with the X4 on its ribbon; scope probes at TP401 (RP_SCK), TP402 (RP_MISO) and the X4 header pins.
- **Procedure:**
  1. Run SRAM_READ bursts with CRC checking (the BridgeDiag or firmware test).
  2. Sweep the SCK rate 1–25 MHz in each launch mode.
  3. Measure t_IN and t_OUT at both ends, and the RP2040's capture window (setup and hold side, §3.3).
- **Pass:**
  - error-free at the chosen rate, with ≥ 25 % of W in hand;
  - the early launch is adopted only if its hold condition is shown with margin.

**M-16:** U402 output enable and back-powering (S4-6 rev A3; the requirement-7 checks in the design notes §7). This is an electrical qualification, required before manufacturing approval. The procedure, steps (a)–(g), is in [sheet4-s46-isolation.md](sheet4-s46-isolation.md) §12. **Pass:**
- trip point within 0.9385 × X4_3V3_REF − 17 mV to 0.9422 × X4_3V3_REF + 7 mV;
- falling-ramp comparator response (TP408) recorded, and the full translator disable time: every U402 B output Hi-Z ≤ 190 ns after GP24 passes the trip point − 20 mV, with the /OE edge ≤ 5 ns/V;
- with K4 held: a measured IOVDD slope ≤ 94 V/ms, and no RP2040 pin (IRQ_N, ATTN, MISO, TDO) above IOVDD + 0.3 V at any time;
- /OE high in reset, in BOOTSEL, before firmware starts and through the X4 power-up;
- the interrupt idle state as stated;
- no /OE glitch during 10 MHz and 20 MHz traffic;
- GP24 HIGH level ≥ 0.126 V above 0.9404 × X4_3V3_REF with the X4 idle and loaded;
- the RP2040 power-cycles cleanly.
