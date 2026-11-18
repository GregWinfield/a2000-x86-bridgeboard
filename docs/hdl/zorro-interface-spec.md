# HDL interface specification: Zorro II slave and AutoConfig (Stage 2 minimum system)

**Status:** revision B, 2026-11-18.
- The RTL now exists in [../../hdl/rtl/](../../hdl/rtl/) (MIT, D-13).
- The verification suite (simulation, formal, netlist checks) **passes** (2026-11-18, [verification-results.md](verification-results.md)).
- Post-place-and-route timing (G-STA) is pending.

**Target:** Lattice LCMXO2-2000HC-4TG144C (D-02).
**Board interface:** sheet 1 revision B ([../stage2/sheet1-design-notes.md](../stage2/sheet1-design-notes.md)). Net names match the schematic.
**References:**
- Zorro III spec App. K (S10).
- Haynie, 100-pin expansion notes (S52).
- MC68000 user's manual (S57).
- MNT VA2000 (MIT, S12) was read for corroboration only. Nothing is copied.

## 1. Scope

**Stage 2 delivers:**
- a Zorro II slave that AutoConfigures as 64 KB (mode A, default) or 512 KB (mode B);
- test registers and an interrupt test;
- XRDY wait states (default on, ER-2);
- **read-modify-write support (C-13)**;
- **reset-boundary arming (C-03/C-04)**.

**Out of scope for Stage 2:** SRAM arbitration, SPI slave, mailboxes and power control (Stage 3+).

## 2. Files and module partition

| File | Module | Function |
|---|---|---|
| `z2_sync.v` | `z2_sync` | 2-flip-flop synchroniser with explicit INIT values |
| `z2_asgate.v` | `z2_asgate2`, `z2_asgate3` | The single-LUT final gates. /AS (and /BERR) are the controlling inputs. Kept hierarchy (C-02) |
| `z2_decode.v` | `z2_decode` | Combinational select and output terms (§5) |
| `z2_core.v` | `z2_core` | Synchronisers, /BUSRST filter, arming, AutoConfig, bus FSM, registers, watchdog. Formal properties under `` `ifdef FORMAL `` |
| `z2_top.v` | `z2_top` | Pins, power-on reset, LD tristate, /OVR and /DTACK held inactive |

## 3. Top-level ports (`z2_top`)

| Port | Dir | Net (sheet 1) | Notes |
|---|---|---|---|
| `ZB_A[23:1]` | in | ZB_A1–ZB_A23 | Stable throughout /AS |
| `ZB_AS_N`, `ZB_UDS_N`, `ZB_LDS_N`, `ZB_READ`, `ZB_DOE` | in | same | Synchronised **and** used combinationally (§5) |
| `ZB_BERR_N` | in | ZB_BERR_N | **New (rev B):** releases XRDY and the buffer enable combinationally; aborts the FSM cycle |
| `ZB_CFGIN_N`, `ZB_BUSRST_N` | in | same | /CFGINn is sampled between cycles; /BUSRST is filtered (§4) |
| `ZB_E7M` | in | ZB_E7M | Monitor only (R-29). ZB_CDAC was removed in rev B |
| `EN_OK` | in | EN_OK | **New:** both supervisors released and JP101 open |
| `ZF_ARM` | out | ZF_ARM | **New:** 1 = join the bus. R122 pull-down |
| `ZF_SLAVE_N`, `ZF_XRDY`, `ZF_DBUF_OE_N` | out | same | Combinational (§5). LVCMOS33, 8 mA, FAST |
| `ZF_DBUF_DIR`, `ZF_CFGOUT_N`, `ZF_INT2_N`, `ZF_INT6_N` | out | same | Registered, except `ZF_CFGOUT_N` (combinational from /CFGINn) |
| `ZF_OVR_N`, `ZF_DTACK_N` | out | same | Constant 1 in Rev 1. May be left unrouted at sheet 2 (C-14) |
| `LD[15:0]` | inout | LD0–LD15 | No FPGA pull or keeper (U103 bus-hold) |
| `clk_core` | in | (sheet 2) | 50 MHz [A] |
| `DIP_MODE_B`, `DIP_INT6`, `DIP_DISABLE` | in | (sheet 6) | Sampled during /BUSRST and at power-on |
| `LED[3:0]` | out | (sheet 6) | armed, configured, interrupt, watchdog flag (ORed with CONTROL test bits) |

## 4. Clocking, reset and arming

- **Clock.** All synchronous logic runs at 50 MHz [A].
- **Synchroniser start values.** The asynchronous inputs pass through `z2_sync` with these INIT values: strobes, READ, /CFGINn, **/BUSRST and /BERR start negated**, EN_OK starts false.
- **Power-on reset.** GSR loads the INIT values. `por` stays high for 15 clocks after configuration.
- **/BUSRST.**
  - It must be seen in **4 consecutive synchronised samples** (≥ 80 ns) before the filtered state changes. Real pulses are ≥ 17.5 µs (RESET instruction) or about 0.7 s (power-on); the filter rejects glitches.
  - While asserted, the Zorro reset `zrst` clears:
    - `configured`, `shutup`, `base`;
    - the FSM and all enables;
    - CONTROL, IRQ_STATUS, ZCYCLES, WAITSTATS, RMW_CYCLES.
  - /CFGOUTn negates about 0.1 µs after /BUSRST at the pin.
  - **Survive /BUSRST** (power-on only): SCRATCH0/1, TICKS, WDOG_EVENTS, BERR_EVENTS, the watchdog flag.
  - Rev A specified an asynchronous assertion. Rev B uses a synchronous, filtered assertion for glitch immunity; the difference is immaterial against real reset widths.
- **Arming (C-03/C-04).**

  ```text
  armed <= 0                 when por
  armed <= 0                 when EN_OK (synchronised) is false     // next clock; hardware gate is instant
  armed <= ~DIP_DISABLE      while the filtered /BUSRST is asserted
  ZF_ARM = armed
  ```

  - The card therefore joins the bus only at a Zorro reset boundary.
  - A reloaded FPGA, or one whose EN_OK went false, stays off the bus until the next /BUSRST.
  - When not armed, `match_en` is cleared, so no combinational output can assert. The hardware gate (U104/U107) also forces every Zorro driver off.
- **DIP latches.** `mode_b` is latched while `zrst` is active. The arming decision uses the live `DIP_DISABLE` during reset.

## 5. Combinational paths (no clock in the path; [../../hdl/rtl/z2_decode.v](../../hdl/rtl/z2_decode.v))

```text
sel_k     = match_en & (A[23:19] == cmp[23:19]) & (~care_lo | A[18:16] == cmp[18:16])
xrdy_term = sel_k & hold_q
oe_term   = sel_k & ( (oe_rd_q &  dir_q &  READ & DOE & ~(UDS_N & LDS_N))
                    | (oe_wr_q & ~dir_q & ~READ) )

ZF_SLAVE_N   = AS_N | ~sel_k                    // z2_asgate2: one LUT
ZF_XRDY      = AS_N | ~BERR_N | ~xrdy_term      // z2_asgate3: 0 = hold off DTACK
ZF_DBUF_OE_N = AS_N | ~BERR_N | ~oe_term        // z2_asgate3: 0 = transceiver enabled
ZF_CFGOUT_N  = CFGIN_N | ~(configured | shutup)
```

**Registered decode state.** It is updated **only while the FSM is idle with /AS negated** (synchronised), and frozen during a cycle (formal F12):

```text
match_en = armed & (configured | (~shutup & CFGIN asserted))
cmp      = configured ? base[23:16] : 8'hE8
care_lo  = ~(configured & mode_b)               // mode B compares A23..A19 only
```

**Rules.**
1. **Final-gate structure (C-02).** /AS and /BERR enter only the final gates. With /AS negated (or /BERR asserted) the outputs are inactive whatever the decode cone does.
   - /CFGINn is not in the combinational cone. Upstream /CFGOUTn changes take effect only between cycles.
   - [../stage2/sheet1-hazard-analysis.md](../stage2/sheet1-hazard-analysis.md).
2. **When the card may drive Zorro data.** All of the following must hold: /AS asserted, selected, READ, DOE, a data strobe, no /BERR, `dir_q = 1` and `oe_rd_q`. The release is combinational on each of them.
   - The **strobe term** ends the read drive at the read portion of an RMW cycle (S7), long before the write portion [V S52, S57].
3. **When the card may drive LD from Zorro.** Only with `dir_q = 0`, `oe_wr_q` and READ low.
4. **Read and write terms are mutually exclusive** through the registered `dir_q`. A READ transition inside a cycle can only remove an enable.
5. **XRDY** is held only for a selected cycle, never during /BERR, and never longer than the watchdog bound (§7.5).
6. `ZF_OVR_N` and `ZF_DTACK_N` are constant 1 (automatic motherboard DTACK).

## 6. Timing constraints

[../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf): `MAXDELAY 18 ns` on:
- /AS and A16–A23 → ZF_SLAVE_N;
- /AS, /BERR and A16–A23 → ZF_XRDY;
- /AS, /BERR, DOE, READ, /UDS and /LDS → ZF_DBUF_OE_N;

and 25 ns on /CFGINn → ZF_CFGOUT_N.

**Gate G-STA** (conditions in [../stage2/sheet1-timing-budget.md](../stage2/sheet1-timing-budget.md) §9). The exploratory Diamond run of 2026-11-19 meets every constraint, worst 15.31 ns after the I/O-standard correction ([../stage2/sheet1-sta-results.md](../stage2/sheet1-sta-results.md)). The final run must report:
- every one of these paths, at the slow corner, both edges, at 10 pF load;
- the minimum delays needed by the hazard inequality.

## 7. Bus-cycle FSM (synchronous, `clk_core`)

### 7.1 Structure

Cycles are handled per **data-strobe phase**, so one /AS cycle may contain one phase (read or write) or two (68000 TAS: a read then a write).

```text
IDLE --(/AS sync)--> START --(sel sampled)--> WAITDS | IGNORE
WAITDS / BETWN --(DS & READ)--> RD_DIR --> RD_DRV --> RD_HLD --(DS negated)--> BETWN
WAITDS / BETWN --(DS & ~READ)--> WR_DIR --> WR_CAP --> WR_HLD --(DS negated)--> BETWN
any state --(/BERR)--> ABORT ;  any non-IDLE state --(/AS negated)--> IDLE (end of cycle)
```

| State | Action |
|---|---|
| START | One clock after /AS is seen. **Sample `sel_c`** (stable for ≥ 40 ns by then), latch A23–A1, choose the target (AutoConfig if not configured, else the board window). An unselected cycle goes to IGNORE with `hold_q = 0`, so XRDY can never be held for a cycle the FSM is not serving |
| RD_DIR | Request DIR = A→B. When DIR has been stable for GUARD clocks, put the read data on LD (`ld_oe`) and set `oe_rd_q`. On a watchdog trip, drive $FFFF |
| RD_DRV | Release XRDY (`hold_q = 0`) one clock after the data are on LD |
| RD_HLD | Hold until the strobe is negated. Then clear `oe_rd_q` and `ld_oe` and request DIR = B→A |
| BETWN | /AS still asserted. If the last phase was a read and **READ is now low** (RMW S14), hold XRDY again for the write portion |
| WR_DIR | Requires DIR = B→A stable for GUARD clocks and the LD drivers off for GUARD clocks. Then set `oe_wr_q` (U103 drives LD from Zorro) |
| WR_CAP | Wait GUARD clocks, capture LD with the byte lanes of the strobes (/UDS → D15–D8, /LDS → D7–D0), commit, release XRDY |
| ABORT | /BERR seen: clear every enable and pending configure/shut-up, release XRDY, wait for /AS negation |
| end of cycle | On synchronised /AS negation from any state: clear every enable. Apply a pending configure or shut-up (so /CFGOUTn changes **between** cycles). Count ZCYCLES, WAITSTATS, RMW_CYCLES |

### 7.2 Direction and local-bus rules (proven by formal F5, F8, F9)

- **DIR changes** only when `oe_rd_q`, `oe_wr_q` and `ld_oe` have all been 0 for ≥ GUARD (2) clocks.
- **An enable is raised** only after DIR has been stable for ≥ GUARD clocks. `oe_wr_q` also needs `ld_oe` off for GUARD clocks.
- **FPGA LD drive:** `ld_oe == oe_rd_q`, and only with `dir_q = 1` (U103 A port is then an input).
- **U103 drives LD** only with `dir_q = 0` and `oe_wr_q`.
- In Stage 3, the SRAM may drive LD only when neither is set.

### 7.3 Read timing

Read data are always available in Stage 2.
- In XRDY-gated mode the motherboard inserts wait states until the data are on LD, about 140 ns after /AS at the FPGA.
- `ready` does not wait for DOE (M-3).

### 7.4 Write timing

Data are valid ≥ 40 ns before DS (#26). The capture happens ≥ 100 ns after DS at the FPGA, and XRDY stretches the cycle until then.

### 7.5 XRDY watchdog

- Counts clocks while a selected cycle holds XRDY. At **100 clocks (2.0 µs)** it trips:
  - XRDY is released in every state for the rest of the cycle;
  - reads return $FFFF and writes are discarded;
  - STATUS b8 is set and WDOG_EVENTS is incremented.
- It re-arms only after XRDY has been released, **not** at a new strobe phase, so a master toggling the strobes cannot defeat it.
- **Bound:** XRDY is held ≤ WDOG_LIMIT + 6 clocks of FSM time (formal F16). In simulation the bound is checked at ≤ 2.3 µs.

## 8. AutoConfig

### 8.1 Format [V S10]

- Responds at $E80000–$E8FFFF while `match_en` is set and unconfigured.
- Register NN: high nibble at $E8_00NN, low nibble at NN+2, on D15–D12. D11–D0 = 1.
- All registers except $00/$02 are inverted. Offsets not listed read as logical 0 (physical $F).

### 8.2 Read registers (logical values)

| Reg | Name | Mode A (64 KB) | Mode B (512 KB) |
|---|---|---|---|
| $00 | er_Type | $C1 | $C4 |
| $04 | er_Product | $01 | $01 |
| $08 | er_Flags | $00 | $80 |
| $10 / $14 | er_Manufacturer | $07 / $DB (2011, TBV R-18) | same |
| $18–$24 | er_SerialNumber | $00000001 (placeholder) | same |
| others | | $00 | $00 |

### 8.3 Write registers

Writes are byte writes on D15–D12 using /UDS.

| Write | Effect |
|---|---|
| $E8004A | base[19:16] |
| $E80048 | base[23:20]; configured at the **end** of that cycle |
| $E8004C | Shut-up at the end of the cycle |

$48 alone also configures. A /BERR during the configuring write cancels it.

### 8.4 /CFGOUTn

`ZF_CFGOUT_N = /CFGINn | ~(configured | shutup)`. When the card is not armed, U104 is disabled and the A2000's pull-down passes the chain ([../stage2/sheet1-design-notes.md](../stage2/sheet1-design-notes.md) §6). The former "DIP disable = pass-through in HDL" behaviour is now "DIP disable = never arm".

## 9. Stage 2 test registers (board window, same offsets in both modes)

16-bit, big-endian, even offsets. **Reads have no side effects** (R-17). Registers occupy $0000–$0FFF. The rest of the window (the Stage 3 SRAM) reads $0000 and ignores writes.

| Offset | Name | Access | Reset | Description |
|---|---|---|---|---|
| $0000 | MAGIC | R | $4252 | "BR" |
| $0002 | VERSION | R | $0A01 | [15:8] hardware revision, [7:0] HDL version |
| $0004 | STATUS | R | – | b0 mode B; b1 INT_SEL; b2 zero-wait; b4 DIP mode B; b5 DIP INT6; b6 DIP disable; b8 watchdog tripped (sticky); **b9 EN_OK; b10 armed** |
| $0006 | CONTROL | R/W | $0000 (b2 from DIP) | b0 ZERO_WAIT_EN (gate G-ZEROWAIT); b1 IRQ_EN; b2 INT_SEL; b7..4 LED test; b8 write 1 clears the watchdog flag (high byte) |
| $0008 / $000A | SCRATCH0 / 1 | R/W | $0000 at power-on | Byte lanes honoured; survive /BUSRST; TAS target for RMW tests |
| $000C | ZCYCLES | R | 0 | Board-window cycles |
| $000E | TICKS | R | 0 | clk/1024 |
| $0010 | IRQ_STATUS | R/W1C | 0 | b0 test interrupt pending |
| $0012 | IRQ_SET | W | – | b0 = 1 sets pending |
| $0014 | WAITSTATS | R | 0 | Cycles with XRDY held |
| $0016 | WDOG_EVENTS | R | 0 (power-on) | Watchdog releases |
| **$0018** | **RMW_CYCLES** | R | 0 | **Cycles with two data phases (C-13)** |
| **$001A** | **BERR_EVENTS** | R | 0 (power-on) | **/BERR assertions seen while armed** (collision monitor, M-4) |

**Interrupt.** Registered: asserted while `armed & IRQ_EN & IRQ_STATUS.b0` on the line chosen by INT_SEL, and gated in hardware by U107.

## 10. Safe defaults summary

| Condition | /SLAVEn | /CFGOUTn | /INTx, XRDY | Data bus |
|---|---|---|---|---|
| Carrier unpowered, FPGA blank or configuring, not armed, DIP disable, DISABLE jumper | Hi-Z → negated (A2000 1 kΩ pull-up) | Hi-Z → chain passes (A2000 1 kΩ pull-down) | Released | Isolated |
| Armed, before AutoConfig | Responds only at $E8xxxx with /CFGINn asserted | Negated | Per cycle | Per cycle |
| /BUSRST | Negated | Negated (driven) | Released | Isolated |
| Shut up | Never | Asserted | Released | Isolated |

## 11. Verification (gate G-SIM: **passed 2026-11-18**, [verification-results.md](verification-results.md))

Run everything with `bash hdl/run_checks.sh` (OSS CAD Suite on PATH or `OSS_CAD_SUITE` set). The run fails on any `ASSERT-FAIL` line. Requirement-to-evidence map: [verification-matrix.md](verification-matrix.md).

| Check | File | What it shows |
|---|---|---|
| Bus-functional simulation | `hdl/sim/tb_z2.v` + `z2_master.v` (68000 S-state model, 7.09 MHz, [V S57] timings) + `card_sheet1.v` (sheet-1 parts with datasheet delays) | AutoConfig, registers, byte lanes, **RMW (TAS)**, DOE sweep, **address transitions near /AS**, /BERR, aborted cycles, watchdog, zero-wait, interrupts, /BUSRST mid-cycle, shut-up, DIP and jumper disable, FPGA reload, power loss. 4 random-skew seeds plus all-maximum and all-minimum delay corners at 18 ns and 7.24 ns FPGA delay |
| Simulation assertions | tb_z2 C1–C7; U103 DIR monitor; LD contention monitor | No Zorro data contention; drive only for a valid read of this card (+ release allowance); no false /SLAVEn; /SLAVEn ≤ 35 / ≤ 50 ns; XRDY only when selected, ≤ 60 ns, ≤ 2.3 µs; DIR never changes while enabled; a disabled card looks empty |
| AutoConfig chain | `hdl/sim/tb_chain.v` | Ten scenarios in three slots with A2000-R6 terminations and Buster collision detection |
| Netlist structure | `hdl/syn/synth_decode.ys` + `check_decode_structure.py` | Final-gate structure S1/S2 (C-02) |
| Gate-level hazard | `hdl/sim/tb_hazard.v` | E1: no assertion with /AS negated under random LUT delays. E2: setup sweep |
| Formal | `hdl/formal/z2_core.sby` | prove (k-induction) F1–F16; bmc with the pin-level XRDY bound; cover |
| STA | `hdl/syn/diamond_sta.tcl`, `z2_top.lpf` | G-STA (Lattice Diamond) |
