# HDL interface specification: Zorro II slave and AutoConfig (Stage 2 minimum system)

**Status:** draft revision A, 2026-11-18. This is a *specification*; no HDL has been written yet.
**Target:** Lattice LCMXO2-2000HC-4TG144C (D-02).
**Board interface:** sheet 1 ([../stage2/sheet1-design-notes.md](../stage2/sheet1-design-notes.md)). Net names match the schematic.
**Licence of the future HDL:** MIT (D-13).
**Reference:** the logic structure follows the Zorro III spec, Appendix K (S10). MNT VA2000 (MIT, S12) was read for corroboration only. Nothing is copied.

## 1. Scope

**Stage 2 delivers:**
- a Zorro II slave that AutoConfigures as a 64 KB I/O board (mode A, default) or a 512 KB board (mode B);
- a small set of **test registers**;
- an interrupt test;
- the **XRDY wait-state mechanism** (default ON, ER-2).

**Out of scope for Stage 2:**
- the SRAM arbiter, SPI slave, mailboxes and power control (Stage 3+);
- they get reserved hooks here.

## 2. Module partition

| Module | Function |
|---|---|
| `z2_sync` | 2-flip-flop synchronisers for ZB_AS_N, ZB_UDS_N, ZB_LDS_N, ZB_READ, ZB_DOE, ZB_CFGIN_N, ZB_BUSRST_N; edge detection |
| `z2_decode` | **Combinational** select terms `sel_ac` and `sel_board` (§5) |
| `z2_comb_out` | **Combinational** output equations for ZF_SLAVE_N, ZF_XRDY, ZF_DBUF_OE_N (§5) |
| `z2_cycle` | Synchronous bus-cycle FSM: address latch, read-data mux, write capture, `ready`, DIR register, LD bus grant |
| `z2_autoconfig` | AutoConfig ROM, base-address registers, configured/shut-up state, ZF_CFGOUT_N |
| `z2_regs` | Stage 2 test registers (§9) |
| `z2_xrdy_wdog` | Watchdog that releases XRDY after a timeout |
| `top` | Pins, clock, reset, DIP sampling, LEDs |

## 3. Top-level ports (Zorro side)

| Port | Dir | Width | Net (sheet 1) | I/O standard | Notes |
|---|---|---|---|---|---|
| `ZB_A` | in | [23:1] | ZB_A1–ZB_A23 | LVCMOS33, PULLMODE=NONE | Buffered by U101/U102. Stable throughout /AS |
| `ZB_AS_N`, `ZB_UDS_N`, `ZB_LDS_N`, `ZB_READ` | in | 1 each | same | LVCMOS33, NONE | Async; synchronised **and** used combinationally (ZB_AS_N, ZB_READ) |
| `ZB_DOE` | in | 1 | ZB_DOE | LVCMOS33, NONE | Gates data-out (combinational) |
| `ZB_CFGIN_N` | in | 1 | ZB_CFGIN_N | LVCMOS33, NONE | |
| `ZB_BUSRST_N` | in | 1 | ZB_BUSRST_N | LVCMOS33, NONE | Zorro-domain reset (spec: must reset AutoConfig) |
| `ZB_E7M`, `ZB_CDAC` | in | 1 each | same | LVCMOS33, NONE | Timing reference/monitor only; no PLL (R-29) |
| `ZF_SLAVE_N` | out | 1 | ZF_SLAVE_N | LVCMOS33, 8 mA, FAST, NONE | External 2.2 kΩ pull-up (R101) defines the unconfigured state |
| `ZF_CFGOUT_N` | out | 1 | ZF_CFGOUT_N | LVCMOS33, 8 mA, SLOW, NONE | R102 pull-up |
| `ZF_INT2_N`, `ZF_INT6_N` | out | 1 each | same | LVCMOS33, 8 mA, SLOW, NONE | Drive **low** = assert (U105 open-drain). R103/R104 |
| `ZF_XRDY` | out | 1 | ZF_XRDY | LVCMOS33, 8 mA, FAST, NONE | Drive **low** = XRDY negated (wait). R105 |
| `ZF_OVR_N`, `ZF_DTACK_N` | out | 1 each | same | LVCMOS33, SLOW, NONE | Not used; keep driven **high** (R106/R107; R119/R120 DNP) |
| `ZF_DBUF_DIR` | out | 1 | ZF_DBUF_DIR | LVCMOS33, 8 mA, SLOW, NONE | 1 = A→B (card drives Zorro, reads). R109 pull-down |
| `ZF_DBUF_OE_N` | out | 1 | ZF_DBUF_OE_N | LVCMOS33, 8 mA, FAST, NONE | 0 = transceiver enabled. R108 pull-up |
| `LD` | inout | [15:0] | LD0–LD15 | LVCMOS33, 8 mA, NONE | **No FPGA pull or keeper:** U103 bus-hold holds the bus, and TI advises against adding pulls |
| `clk_core` | in | 1 | (sheet 2) | LVCMOS33 | 50 MHz [A]: external oscillator, or the internal OSCH as an alternative |
| `dip_mode_b`, `dip_int6`, `dip_disable` | in | 1 each | (sheet 6) | LVCMOS33, PULLMODE=UP | Sampled at reset (§8.6) |

## 4. Clocking and reset

- **clk_core.** All synchronous logic runs at 50 MHz [A] (20 ns period). Zorro inputs are asynchronous to it: each goes through a 2-FF synchroniser before synchronous use. Only the §5 equations use the raw pins.
- **Power-on reset.** GSR clears everything to reset values. The device is configured about 1.4 ms after POR [V S49].
- **/BUSRST.** Asynchronous assert, synchronised de-assert. Asserted, it immediately:
  - clears `configured`, `shutup` and `base`;
  - negates ZF_CFGOUT_N combinationally ("negated immediately on reset", S10);
  - releases XRDY, disables DBUF and releases LD;
  - resets CONTROL and IRQ_STATUS.

  SCRATCH0/1 are **not** reset by /BUSRST, so an Amiga reset can be shown to leave the card's state intact (brief: independent reset). Future SRAM, mailbox and SBC-power state will likewise survive /BUSRST.

## 5. Combinational paths (no clock in the path)

```text
as      = ~ZB_AS_N
mode_b  = latched DIP (section 8.6)
sel_ac  = ~ZB_CFGIN_N & ~configured & ~shutup & ~disable & (ZB_A[23:16] == 8'hE8)
sel_brd =  configured & ~disable & ( mode_b ? (ZB_A[23:19] == base[23:19])
                                             : (ZB_A[23:16] == base[23:16]) )
sel     = sel_ac | sel_brd

ZF_SLAVE_N   = ~(as & sel)
ZF_XRDY      = ~(as & sel & ~zero_wait_en & ~ready_q)        // low = wait
ZF_DBUF_OE_N = ~(as & sel & grant_q & (ZB_READ ? (ZB_DOE & dir_q) : ~dir_q))
ZF_DBUF_DIR  =  dir_q                                         // registered (section 7)
ZF_CFGOUT_N  =  ZB_CFGIN_N | ~(configured | shutup | disable) // VA2000-style gating
```

**Rules:**
1. `sel` depends only on address bits and registered state, so it is stable throughout /AS. /AS is the last term to arrive. Concern **C-02**: if the slot address settles after /AS, `sel` may glitch; measure M-7.
2. **No term may drive the Zorro bus unless all of these hold:** /AS asserted, selected, a read, DOE asserted, DIR already registered A→B. The release on /AS↑ or DOE↓ is combinational.
3. `ZF_OVR_N` and `ZF_DTACK_N` are driven constant 1 in Rev 1. The automatic motherboard DTACK is used, and XRDY is the only wait mechanism.
4. **XRDY may only be held for cycles selected to this card**, and never longer than the watchdog limit (§8.5).

## 6. Timing constraints (indicative Lattice LPF; finalise with the first HDL)

```text
FREQUENCY NET "clk_core" 50.0 MHz ;
MAXDELAY FROM PORT "ZB_AS_N"   TO PORT "ZF_SLAVE_N"   18.0 ns ;   # sheet-1 notes 4.1 (35 ns total)
MAXDELAY FROM PORT "ZB_A*"     TO PORT "ZF_SLAVE_N"   18.0 ns ;   # covers late-address case (C-02)
MAXDELAY FROM PORT "ZB_CFGIN_N" TO PORT "ZF_SLAVE_N"  18.0 ns ;
MAXDELAY FROM PORT "ZB_AS_N"   TO PORT "ZF_XRDY"      18.0 ns ;   # sheet-1 notes 4.2 (60 ns total)
MAXDELAY FROM PORT "ZB_AS_N"   TO PORT "ZF_DBUF_OE_N" 18.0 ns ;   # release path, 4.3
MAXDELAY FROM PORT "ZB_DOE"    TO PORT "ZF_DBUF_OE_N" 18.0 ns ;
MAXDELAY FROM PORT "ZB_CFGIN_N" TO PORT "ZF_CFGOUT_N" 25.0 ns ;
# synchroniser inputs: async -> exclude from setup/hold analysis into the first flop
```

**Gate G-STA:** all MAXDELAY paths must meet timing in Diamond at the −4 grade, with the real pin assignment, before the sheet-2 pinout is frozen.

## 7. Bus-cycle FSM (synchronous, clk_core)

```text
IDLE --(as_s falls & sel)--> ACCEPT --> READ | WRITE --> HOLD --(as_s rises)--> END --> IDLE
```

**ACCEPT.** Latch `ZB_A[23:1]`, `ZB_READ` and the target:
- AutoConfig register;
- board register;
- a future SRAM window (returns 0 / ignores writes in Stage 2).

Then set `dir_q = READ`. Request the LD bus (`grant_q`; immediate in Stage 2, from the arbiter in Stage 3).

**READ.**
1. Drive `LD` with the selected data (FPGA LD output enable `ld_oe_q = 1`).
2. One clock later set `ready_q`. In XRDY-gated mode this releases XRDY.
3. The transceiver drives Zorro only while DOE is asserted (§5).

**WRITE.**
1. Keep `ld_oe_q = 0`; U103 B→A drives LD.
2. Wait for synchronised `/UDS` or `/LDS` asserted, plus **1 clock** (U103 B→A ≤ 6.0 ns ≪ 20 ns).
3. Capture `LD` with the byte lanes: /UDS → [15:8], /LDS → [7:0].
4. Set `ready_q`.

**HOLD/END.** On synchronised /AS↑:
- clear `ld_oe_q`, `grant_q` and `ready_q`;
- clear `dir_q` **one clock after** the OE release, so DIR never changes while the transceiver is enabled;
- if this was the configuring $48 write, assert `configured` here, so /CFGOUTn changes between cycles.

**LD contention rules:**
- the FPGA drives LD only in READ with `dir_q = 1`;
- U103 drives LD (B→A) only in WRITE with `dir_q = 0`;
- in Stage 3 the SRAM drives LD only when the arbiter grants a non-Zorro access, and never while `grant_q` is set for a Zorro cycle.

These rules are **simulation assertions** (§11).

## 8. AutoConfig

### 8.1 Address and data format [V S10]

- **Address:** responds at **$E80000–$E8FFFF** only while `sel_ac` is true.
- **Register layout:** register NN (8 bits) = high nibble at $E8_00NN, low nibble at $E8_00(NN+2), on **D15–D12**. The card drives **D11–D0 = 1**.
- **Inversion:** all registers except $00 are returned **complemented**.
- **Unused offsets:** offsets not listed below read as logical 0 (physical $F).

### 8.2 Read registers (logical values)

| Reg | Name | Mode A (64 KB, default) | Mode B (512 KB) | Physical nibbles (high @NN, low @NN+2) |
|---|---|---|---|---|
| $00 | er_Type | **$C1**: Zorro II; no memory list; no ROM; not chained; size 001 = 64 KB | **$C4** (size 100 = 512 KB) | A: C,1 / B: C,4 (not inverted) |
| $04 | er_Product | $01 (prototype, TBD) | $01 | F,E |
| $08 | er_Flags | **$00**: bit 7 = 0, may go anywhere it fits; bit 6 = 0, can be shut up | **$80**: bit 7 = 1, 8 MB space | A: F,F / B: 7,F |
| $0C | er_Reserved03 | $00 | $00 | F,F |
| $10 | er_Manufacturer (hi) | $07 (prototype ID 2011 = $07DB, TBV R-18) | $07 | F,8 |
| $14 | er_Manufacturer (lo) | $DB | $DB | 2,4 |
| $18–$24 | er_SerialNumber (MSB first) | $00 $00 $00 $01 (placeholder; future: UFM) | same | F,F F,F F,F F,E |
| $28, $2C | er_InitDiagVec | $00, $00 (no boot ROM) | same | F,F F,F |
| $30–$3C | reserved | $00 | $00 | F,F |
| $40–$7E | Z2 control/reserved and write-only base registers | read $00 | $00 | F,F |

$40 (ec_Interrupt) behaviour is not used in Rev 1 (TBV against the Zorro II AutoConfig docs if needed).

### 8.3 Write registers [V S10; corroborated by S12]

| Write | Effect |
|---|---|
| $E8004A | `base[19:16] ← D15–D12` (A19–A16) |
| $E80048 | `base[23:20] ← D15–D12` (A23–A20), then `configured ← 1` **at the end of that cycle** (§7) |
| $E8004C | `shutup ← 1` at the end of the cycle; the board never responds again until /BUSRST |

**Write order.** The spec says writing register $48 configures the board, and the OS writes $4A first. The HDL must also accept $48 alone, keeping the previously latched (reset = 0) A19–A16. In mode B only A23–A19 are compared (A18–A16 are ignored).

### 8.4 /CFGOUTn

`ZF_CFGOUT_N` asserts (low) only while ZB_CFGIN_N is asserted **and** the board is configured, shut up or DIP-disabled. It is negated immediately by /BUSRST. A blank or unconfigured FPGA leaves it negated through the R102 pull-up (C-10).

### 8.5 XRDY wait-state mode (ER-2)

- **`zero_wait_en` = 0 after every reset** (XRDY-gated mode).
  - Each selected cycle holds XRDY from /AS↓ (combinational, ≤ 18 ns FPGA path) until `ready_q`. That gives at least one wait state.
- **Zero-wait mode** is entered by CONTROL bit 0, **only after gate G-ZEROWAIT** (measured margins). Software must not set it by default.
- **Watchdog.** If XRDY has been held for more than **2.0 µs** (100 clocks at 50 MHz, [A]):
  - force `ready_q` (release the bus);
  - return $FFFF for reads and discard writes;
  - set STATUS bit 8 and increment WDOG_EVENTS.

  This guarantees that an HDL fault cannot hang the A2000 bus indefinitely (Zorro II has no bus timeout, S10).

### 8.6 DIP-selected options (sampled at power-on and at /BUSRST de-assertion)

| DIP | Effect |
|---|---|
| `dip_mode_b` | 0 = mode A (64 KB), 1 = mode B (512 KB) |
| `dip_int6` | Reset value of CONTROL.INT_SEL (0 = /INT2, 1 = /INT6) |
| `dip_disable` | Board never responds; `ZF_CFGOUT_N` follows `ZB_CFGIN_N` (pass-through, so downstream boards still configure) |

## 9. Stage 2 test registers (board window; same offsets in both modes)

All registers are 16-bit, big-endian, at even offsets. **Reads have no side effects** (R-17): Zorro II memory-space reads assert both strobes.

| Offset | Name | Access | Reset | Description |
|---|---|---|---|---|
| $0000 | MAGIC | R | $4252 ("BR") | Identifies the bridge |
| $0002 | VERSION | R | $0A01 | [15:8] hardware revision (A), [7:0] HDL version |
| $0004 | STATUS | R | – | b0 mode B; b1 INT6 selected; b2 zero-wait active; b7..4 DIP raw; b8 XRDY watchdog tripped (sticky) |
| $0006 | CONTROL | R/W | $0000 (b2 from DIP) | b0 ZERO_WAIT_EN (gate G-ZEROWAIT); b1 IRQ_EN; b2 INT_SEL; b7..4 LED test; b8 write-1 clears the watchdog flag (reads 0) |
| $0008 | SCRATCH0 | R/W | $0000 (POR only) | Byte lanes honoured; survives /BUSRST |
| $000A | SCRATCH1 | R/W | $0000 (POR only) | As above |
| $000C | ZCYCLES | R | 0 | Count of Zorro cycles to this board (wraps) |
| $000E | TICKS | R | 0 | Free-running clk_core/1024 counter |
| $0010 | IRQ_STATUS | R/W1C | 0 | b0 TEST pending; write 1 to clear |
| $0012 | IRQ_SET | W | – | Write b0 = 1 to set TEST pending (reads 0) |
| $0014 | WAITSTATS | R | 0 | Count of XRDY-held cycles |
| $0016 | WDOG_EVENTS | R | 0 | Count of watchdog releases |
| $0018–$0FFE | reserved | R | 0 | Writes ignored |
| $1000–$FFFF (A) / –$7FFFF (B) | SRAM windows | R/W | – | Stage 3. In Stage 2, reads return $0000 and writes are ignored (still XRDY-gated) |

**Interrupt.** The selected line is asserted while `IRQ_EN & IRQ_STATUS.b0`, and released when cleared. The Amiga handler is shared on the chain and must check IRQ_STATUS.

## 10. Safe defaults summary (ties to sheet-1 notes §6)

| Condition | /SLAVEn | /CFGOUTn | /INTx | XRDY | Data bus |
|---|---|---|---|---|---|
| FPGA unconfigured or blank | Negated (R101) | Negated (R102) | Released | Released | Isolated (R108), DIR B→A (R109) |
| After POR, before AutoConfig | Responds only to $E8xxxx with /CFGINn asserted | Negated | Released | Gated per cycle | Per cycle |
| /BUSRST asserted | Negated | Negated | Released | Released | Isolated |
| DIP disable | Negated | Follows /CFGINn | Released | Released | Isolated |

## 11. Verification plan (before hardware)

1. **Bus-functional simulation.** A 68000/Zorro II cycle model at 7.09 MHz with S-state timing (reads, writes, byte writes, RMW) and an `expansion.library`-style AutoConfig sequence covering:
   - reading every register and checking the inversion;
   - writing $4A then $48, and $48 only;
   - shut-up;
   - /CFGINn gating;
   - DIP disable;
   - /BUSRST mid-cycle.
2. **Assertions:**
   - no LD contention;
   - the transceiver never drives Zorro (`DIR & ~OE_N`) outside selected, DOE-qualified reads;
   - XRDY is never held for unselected cycles;
   - the watchdog bound;
   - /SLAVEn only for matching addresses (randomised addresses);
   - /CFGOUTn negated during /BUSRST.
3. **Static timing.** Diamond TRACE on all §6 constraints at −4 with the real pinout (G-STA).
4. **Hardware.** Sheet-1 measurements M-1 to M-7 (after gate G-PSU). Amiga-side tests:
   - ShowConfig lists the board in modes A and B;
   - MAGIC and VERSION;
   - SCRATCH word and byte writes, and persistence across Ctrl-A-A;
   - interrupt test on INT2 and INT6;
   - WAITSTATS increments;
   - no /BERR.
