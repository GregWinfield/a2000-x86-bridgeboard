# HDL specification: shared SRAM, arbitration, queues and interrupts (Stage 3, sheet 3)

**Status:** revision A1, 2026-11-19 (owner decisions: C-21 approved; byte order defined in [byte-order-spec.md](byte-order-spec.md)).
- RTL: [z2_lbus.v](../../hdl/rtl/z2_lbus.v), [z2_mbx.v](../../hdl/rtl/z2_mbx.v), the SRAM target in [z2_core.v](../../hdl/rtl/z2_core.v), [z2_top.v](../../hdl/rtl/z2_top.v), and the host-port stub [z2_hostif_stub.v](../../hdl/rtl/z2_hostif_stub.v). Licence MIT (D-13).
- Verification: `hdl/run_checks.sh` passes ([verification-results.md](verification-results.md) §5).
- Companion documents: [zorro-interface-spec.md](zorro-interface-spec.md) (Zorro side, revision C); board: [../stage2/sheet3-design-notes.md](../stage2/sheet3-design-notes.md).

## 1. Principle: access is separate from work

| Layer | Block | Decides | Knows nothing about |
|---|---|---|---|
| Memory access | `z2_lbus` (arbiter + SRAM sequencer) | **Who may access the memory** at each instant: one word at a time, the Zorro side first, bounded latency | Queues, messages, interrupts |
| Work signalling | `z2_mbx` (queues + interrupts) | **Who has work to do**: queue indices with one writer side each, interrupts derived from queue state | The SRAM and the bus timing |

- No side ever needs a lock to access memory. Memory access is always granted within a bounded time (§3.5).
- The queue protocol stops both sides working on the same slot (§4.2). The arbiter never makes a protocol decision.
- **No hardware semaphores** (C-21, approved by the owner 2026-11-19). The two single-producer, single-consumer queues with single-writer indices need no locks. Single-writer enforcement, the ownership rules, epoch tracking and level interrupts are retained.
- **Multiple producers on one processor** must be serialised in software. Examples are several Amiga tasks posting to Q0, or several PC threads posting to Q1. They may use a mutex, or a single owning task that posts on their behalf. The hardware sees exactly one writer per index.

## 2. Blocks and interfaces

```text
Zorro FSM (z2_core) --zq_* requests, z_res, z_quiet--> z2_lbus --SA, SRAM_*--> U301
      ^                         <--zs_drv, h_quiet--      |   <--LD-->  (U103 A port, U301, FPGA)
      |  zr_* register port                      host port (SRAM space)
   z2_mbx <------------------- host port (register space) ------------- z2_hostif
      |--z_irq--> z2_core INT2/INT6           RP_IRQ_N --> sheet 4 (RP2040)
```

| Signal | From → to | Meaning |
|---|---|---|
| `zq_addr[17:0]`, `zq_ce`, `zq_oe`, `zq_we`, `zq_ub`, `zq_lb` | z2_core → z2_lbus | Registered Zorro SRAM requests; on the pins one clock later |
| `z_res` | z2_core → z2_lbus | Reservation: 1 from the clock /AS is seen until the cycle ends, except for a cycle being ignored (another card's) |
| `z_quiet` | z2_core → z2_lbus | Every Zorro local-bus driver (FPGA LD drive, SRAM read output, U103 write enable) off for ≥ GUARD clocks |
| `zs_drv` | z2_lbus → z2_core | U301 outputs enabled for a Zorro read (pin registers). Counted by z2_core's guard counter |
| `h_quiet` | z2_lbus → z2_core | Host sequencer idle and its drivers off for ≥ GUARD clocks |
| `zr_we`, `zr_widx`, `zr_be`, `zr_wdata`; `zr_ridx` → `zr_rdata` | z2_core ↔ z2_mbx | Zorro register port (board window $0040–$005E) |
| `z_irq` | z2_mbx → z2_core | Zorro-side interrupt request, gated by CONTROL.IRQ_EN and routed by INT_SEL |

**Pins.** Every SRAM pin (`SA[17:0]`, `SRAM_CE_N`, `SRAM_OE_N`, `SRAM_WE_N`, `SRAM_UB_N`, `SRAM_LB_N`) comes straight from one flip-flop, with no logic after it, so it cannot glitch. The registers initialise to "deselected" (/CE, /OE, /WE, /UB, /LB = 1). While the FPGA is blank, R301/R302 hold /CE and /WE high (sheet 3).

## 3. Arbitration (`z2_lbus` and the reservation in `z2_core`)

### 3.1 Local-bus drivers

LD[15:0] has three possible drivers. At most one drives at a time (formal X2), with at least one idle clock between different drivers (X3). The design uses GUARD = 2 clocks.

| Driver | When | Enable |
|---|---|---|
| FPGA | Zorro register / AutoConfig read (`ld_oe`), or host write (`h_ld_oe`) | `LD = ld_oe ? ld_dout : h_ld_oe ? h_ld_dout : Z` |
| U301 | Zorro SRAM read, or host SRAM read | /CE·/OE low, /WE high (pin registers) |
| U103 A port | Zorro write phase (`oe_wr_q`, DIR = B→A) | Combinational at the pin; permission registered |

A Zorro read drives the Zorro bus through U103 (A→B). LD is then U103's *input*, so the read data source (FPGA or U301) and U103's enable coexist. That is not contention.

### 3.2 Rules

| Rule | Statement | Evidence |
|---|---|---|
| A1 | A host SRAM access starts only when `z_res = 0`, `z_quiet`, `h_quiet`, and the previous acknowledge has been seen | RTL `h_start`; formal X1–X3 |
| A2 | A host access is never aborted: a read takes 3 clocks (s, s+1, capture and release at s+2), a write 4 (s address/data, s+1 /WE low, s+2 /WE high, s+3 release) | RTL; SRAM model AC checks |
| A3 | Every Zorro local-bus action (FPGA LD drive, SRAM read, U103 write enable, SRAM address/control) waits for `res_ok` (≥ START + ZRES) and `h_quiet` | F19 |
| A4 | **Determinism.** ZRES = 4 is chosen so that any host access that started before the reservation has finished and been quiet for GUARD clocks by then. A Zorro action that is due by Zorro-side conditions alone therefore never waits | **X4** (k-induction); tb_shm S3 (measured) |
| A5 | Simultaneous requests: the Zorro side reserves from the clock /AS is synchronised. A host request in the same clock waits; one already started finishes first and is hidden by A4 | X1, X4 |
| A6 | RMW (68000 TAS): the reservation covers the whole /AS, so no host access can fall between the read and write portions (G2) | X1; tb_shm S4 (host hammering the TAS word) |
| A7 | Cycles for other cards (`IGNORE`) do not reserve the bus; host accesses may proceed | `z_res` definition; tb_z2 with host traffic |
| A8 | Host progress: while the Zorro side leaves the bus free, a held request completes within 10 clocks | X6 (k-induction) |

### 3.3 Zorro SRAM timing (FPGA clocks, 20 ns)

| Access | Action | XRDY release | Notes |
|---|---|---|---|
| Read | At go (START + 6 by the existing direction guards): `zq_ce`, `zq_oe`, both lanes, address; U301 pins one clock later | go + 3 (`SRAM_RD_WAIT` = 2) | U301 drives LD; the FPGA does not |
| Write | At go (one clock after the write strobe is seen): address, /CE, lanes from /UDS, /LDS; /WE at go + 3 (one clock wide) | go + 5 | Data reach LD through U103 at go; the /WE pulse starts after GUARD clocks |
| Watchdog trip | Read: the FPGA drives $FFFF instead of the SRAM. Write: no /WE pulse (discarded) | – | As for registers ([zorro-interface-spec.md](zorro-interface-spec.md) §7.5) |
| /BERR | Every request is cleared; a /WE pulse already started ends after its one clock | – | A write interrupted by /BERR may or may not complete |

**Determinism, measured** (tb_shm S3, 4 seeds and 2 delay corners): every SRAM read acted at START + 6 and every write at DS + 1, with host traffic both off and on. The slot /AS → XRDY range was unchanged, for example 243.8–263.6 ns off and 244.1–263.4 ns on. The ≈ 20 ns spread is the asynchronous phase of /AS against the 50 MHz clock. The CPU-visible wait states can still differ by one, because the motherboard samples XRDY on its own clock.

### 3.4 Memory map

| View | Range | Target |
|---|---|---|
| Zorro, mode A (64 KB) | $0000–$0FFF | Registers ([zorro-interface-spec.md](zorro-interface-spec.md) §9; shared registers §4.3 below) |
| | $1000–$7FFF | SRAM $01000–$07FFF (fixed window: control block, rings) |
| | $8000–$FFFF | SRAM BANK × 32 KB (BANK register $0020, 0–15) |
| Zorro, mode B (512 KB) | $00000–$00FFF | Registers |
| | $01000–$7FFFF | SRAM $01000–$7FFFF (linear) |
| Host (SPI side) | SRAM space | SRAM $00000–$7FFFF, flat (word address `h_addr`) |
| | Register space | Shared registers, index 0–15 (§4.3) |

- SRAM $00000–$00FFF is reachable from the Amiga only through bank 0 in mode A.
- In mode B it is host-only, for example as PC-private scratch.

### 3.5 Host-port contract (for the sheet-4 SPI slave)

| Item | Requirement |
|---|---|
| H-1 | `clk_core` domain. `h_req` is held with stable `h_we`, `h_reg`, `h_addr`, `h_be` and `h_wdata` until `h_ack` = 1. The transaction completes at that clock edge, and read data are valid with `h_ack` |
| H-2 | `h_reg = 0`: SRAM word `h_addr[17:0]`; reads return both lanes; writes honour `h_be` = {upper, lower}. `h_reg = 1`: shared register `h_addr[3:0]` (one clock) |
| H-3 | Transactions execute one at a time, in order (ordering G4). The SPI slave must not post a write as complete before `h_ack` |
| H-4 | **Latency.** Typically ≤ 6 clocks while the Zorro side is idle. A host request can wait out one whole selected Zorro cycle, bounded by the XRDY watchdog: simulation max 2.62 µs. The SPI slave must buffer for that, or signal busy on ATTN |
| H-5 | **Before an FPGA reconfiguration** (JTAG reload or refresh), the host side stops issuing transactions. A write in flight at the moment of reconfiguration may be lost or leave that one word undefined; other words are kept (tb_shm S9). The RP2040 drives the JTAG (D-12), so it can quiesce first |
| H-6 | The host port has no Zorro-cycle dependence: the RP2040 never has to answer a Zorro cycle. Every Zorro cycle completes in FPGA hardware, also while the host side is absent, in reset, or hung |

## 4. Queues and interrupts (`z2_mbx`)

### 4.1 Queues

- **Q0, Amiga → PC (A2P).** The Zorro side writes Q0_PROD; the host side writes Q0_CONS.
- **Q1, PC → Amiga (P2A).** The host side writes Q1_PROD; the Zorro side writes Q1_CONS.
- **Indices** are 8-bit free-running counters. QDEPTH = 2^QD_LOG2 = 32 slots per queue (readable in QSTAT).
- **Slot index** = index mod QDEPTH. Slot size and ring placement are defined by software in the SRAM control block; the hardware never touches the SRAM.

### 4.2 Ownership and synchronisation

| Rule | Statement | Evidence |
|---|---|---|
| Q-1 | Each register has **one writer side**. A write from the other side, or to a read-only register, is ignored and flags ERR_OWNER | tb_shm S5 |
| Q-2 | An index write is one full 16-bit word {EPOCH, INDEX}. It is accepted only if both byte lanes are written, EPOCH equals the current epoch, and the advance does not exceed the free space (producer) or the queued entries (consumer). Otherwise it is ignored and flags ERR_RANGE or ERR_EPOCH | Formal M1, M4; S5 |
| Q-3 | **Invariant:** 0 ≤ PROD − CONS ≤ QDEPTH for both queues, for any input sequence, including simultaneous writes from both sides (each check uses the other index's current value, which is conservative) | Formal **M1** (k-induction) |
| Q-4 | **Slot ownership:** slots in [CONS, PROD) belong to the consumer, the rest to the producer. Ownership moves only through an accepted index write | M2 |
| Q-5 | **Ordering:** the producer completes its SRAM payload writes before writing PROD. Each side executes in order (68000 bus cycles; host port H-3), and the arbiter serialises SRAM access, so a consumer that sees PROD advance then reads a complete payload. On 68030/040/060 accelerators the driver maps the board non-cacheable and serialises writes (R-16) | Design; S5 |
| Q-6 | **Link reset:** QCTL = $A55A (either side), or the start of /BUSRST, sets all four indices to 0, increments EPOCH, and sets LINK_RESET for both sides (AMIGA_RESET too for /BUSRST). It wins over any index write in the same clock. A write prepared under the old epoch is rejected afterwards. SRAM is not touched (G7) | M3; S6 |
| Q-7 | A Zorro reset clears the Zorro-side interrupt enables and events, so no interrupt can fire before a new driver enables it. Host-side state survives /BUSRST and is cleared only at power-on | S6, S7 |

### 4.3 Shared registers (Zorro view: board window offset $0040 + 2 × index; host view: register index)

All registers are 16-bit. Reads have no side effects (R-17).

| Idx | Zorro offset | Name | Writer | Content |
|---|---|---|---|---|
| 0 | $0040 | Q0_PROD | Zorro | {EPOCH, A2P producer index} |
| 1 | $0042 | Q0_CONS | Host | {EPOCH, A2P consumer index} |
| 2 | $0044 | Q1_PROD | Host | {EPOCH, P2A producer index} |
| 3 | $0046 | Q1_CONS | Zorro | {EPOCH, P2A consumer index} |
| 4 | $0048 | QSTAT | – | [11:8] QD_LOG2; b3 Q1 full, b2 Q1 not empty, b1 Q0 full, b0 Q0 not empty |
| 5 | $004A | EPOCH | – | [7:0] link epoch |
| 6 | $004C | Z_IRQ_EN | Zorro | b0 Q1 work, b1 Q0 space, b2 event, b3 error |
| 7 | $004E | Z_EVENTS | Zorro (W1C) | b0 LINK_RESET; b8 ERR_EPOCH, b9 ERR_RANGE, b10 ERR_OWNER |
| 8 | $0050 | H_IRQ_EN | Host | b0 Q0 work, b1 Q1 space, b2 event, b3 error |
| 9 | $0052 | H_EVENTS | Host (W1C) | b0 LINK_RESET, b1 AMIGA_RESET, b2 AMIGA_CONFIGURED; b8 ERR_EPOCH, b9 ERR_RANGE, b10 ERR_OWNER |
| 10 | $0054 | QCTL | Both | Write $A55A: link reset (Q-6). Reads 0 |
| 11 | $0056 | Z_IRQ_PEND | – | b15 any; [3:0] Zorro sources AND enables |
| 12 | $0058 | H_IRQ_PEND | – | b15 any; [3:0] host sources AND enables |
| 13 | $005A | AMIGA_STATUS | – | b4 mode B, b3 EN_OK, b2 /BUSRST active, b1 configured, b0 armed |

Zorro-side registers outside the queue block: **$0020 BANK** (Zorro, reset by /BUSRST), banked-window bank 0–15.

### 4.4 Interrupts are levels

- **Zorro sources:** {error, event, Q0 not full, Q1 not empty} AND Z_IRQ_EN. The /INT2 or /INT6 line asserts while `armed & CONTROL.IRQ_EN & (IRQ_STATUS.b0 | any)`, and is gated by U107.
- **Host sources:** {error, event, Q1 not full, Q0 not empty} AND H_IRQ_EN → `RP_IRQ_N`, registered, active low.
- "Work" is a queue that is not empty, so draining the queue removes the request. There is nothing to acknowledge, and a notification cannot be lost between a check and a clear.
- "Space" is level-sensitive too: a producer enables it only while blocked, and it fires at once if space already exists.

### 4.5 Byte order

Normative in [byte-order-spec.md](byte-order-spec.md):
- shared memory is a byte array, and multi-byte values are big-endian;
- byte 2n is the upper lane (D15–D8, /UDS, `h_be[1]`);
- the SPI link sends MSB first, in ascending addresses.

tb_shm S12 checks the lanes.

## 5. Formal properties (hdl/formal/fv_shm.v, every input free)

| ID | Property |
|---|---|
| X1 | While a host access occupies the SRAM pins, no Zorro SRAM request is active |
| X2 | At most one LD driver (FPGA for Zorro, FPGA for host, U301, U103 write permission) |
| X3 | At least one idle clock between different LD drivers |
| X4 | A Zorro local-bus action that is due by Zorro-side conditions alone finds `h_quiet` already true |
| X5 | /WE low only inside /CE with /OE high; exactly one clock; address and lanes stable from the clock before /WE falls to the edge where it rises |
| X6 | A held host SRAM request completes within 10 clocks while the Zorro side leaves the bus free |
| M1–M5 | Queue invariant; index changes only by an owner's accepted write or a link reset; link reset effect; accepted writes carry the current epoch; RP_IRQ_N follows the enabled sources |
| F17–F20 | (z2_core) SRAM strobe only in a write phase with /CE; reservation covers every acting state; every local-bus action waits for the floor and a quiet host; /WE request exactly one clock with a stable address |

**Results:** prove (k-induction) PASS; bmc 64 steps PASS; cover: all reachable, including a Zorro action 5 clocks after a host write. **Mutation check:** 7 of 8 deliberately broken variants are caught with real counterexamples. The eighth (Zorro read go without `h_quiet`) is equivalent: X4 shows the check is redundant given ZRES ([verification-results.md](verification-results.md) §5.3).

## 6. Open items (HDL)

| Item | Where |
|---|---|
| SPI slave, clock-domain crossing, protocol framing and CRC; ATTN use | Sheet 4 (host link). Required verification (owner, 2026-11-19), all on the **real** SPI slave RTL, not a model:<br>**HL-1** SPI protocol and byte order at the pins (an SPI master model with RP2040 PL022 timing at the chosen SCK, modes, CS framing; vectors V1 and V5).<br>**HL-2** Clock-domain crossing: a structured synchroniser or handshake, proven by formal or a CDC check, plus random clock-ratio simulation.<br>**HL-3** Host-request buffering sized for the H-4 latency (≥ one Zorro cycle, bounded by the watchdog) at the maximum SCK, with overflow impossible or reported (ATTN).<br>**HL-4** Ordering: transactions executed in order, a write completes before a later index or doorbell write (G4), no reordering across the CDC.<br>**HL-5** tb_z2 and tb_shm re-run through the real SPI slave.<br>**HL-6** Stress: continuous SPI traffic during Amiga copy loops (M-13 in simulation) |
| Host status word for the RP2040's LEDs (C-26, 2026-11-19) | Sheet 4: the host interface exposes `fault_ind` (watchdog flag or an enabled interrupt pending, ORed with CONTROL b5) so the RP2040 can drive the FAULT LED. READY stays on the FPGA (pin 65) and does not depend on the host link |
| G-STA of the host read capture path (LD → FPGA): the host path is absent from synthesis until the SPI slave exists (stub) | Sheet 4; timing budget §2.3 (≈ 19 ns margin estimated) |
| 50 MHz register-path slack 2.7 ns worst (START decision: decode comparator → `hold_q`); watch as logic grows | Concern C-23 |
| Zero-wait mode for SRAM cycles: passes in the model, unproven on hardware | G-ZEROWAIT |
