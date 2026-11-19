# Host-link protocol (RP2040 ↔ FPGA SPI), version 1.0

**Status:** normative specification for sheet 4, draft for review (gate G-SHEET4). 2026-11-19.

**Owner decisions applied:**
- S4-1: SCK-clocked slave with an asynchronous FIFO; 10 MHz initial, 20 MHz performance target.
- S4-2: GPIO chip select, SPI mode 0.
- S4-4: CRC-16/CCITT.
- S4-5: split reads with ATTN.

**Reference implementation:** [../../tools/hostlink/hostlink.py](../../tools/hostlink/hostlink.py). It is the oracle for the RTL testbenches and the model for the RP2040 firmware and Windows tools.

**Unchanged contracts.** The protocol rides on the host-port contract H-1 to H-6 and the ordering rules of [shared-memory-spec.md](shared-memory-spec.md), and it does not change them. Byte order follows [byte-order-spec.md](byte-order-spec.md).

## 1. Versioning (owner requirement 9)

| Item | v1.0 |
|---|---|
| Major version | **1**, carried in the first byte of every frame: SYNC = `0xA0 \| major` = **0xA1** (command) and RSYNC = `0x50 \| major` = **0x51** (response). The FPGA rejects a command whose SYNC carries another major version. A master recognises the FPGA's major version from any response byte 0 |
| Minor version | **0**, reported by IDENTIFY. A minor version adds commands or status fields without changing existing ones; masters must ignore unknown status bits and extra payload bytes |
| IDENTIFY payload | "Z2" (0x5A 0x32), PROTO_MAJOR, PROTO_MINOR, HDL_VER, MAX_WORDS, RX_FIFO_DEPTH, FEATURES (b0 CRC-16, b1 split reads, b2 SCK-launch option) |
| Rule | A master that reads an unknown major version stops issuing commands and reports the mismatch to the PC. Any change to frame layout, CRC or command semantics increments the major version |

## 2. Physical layer

| Item | Requirement | Source / note |
|---|---|---|
| Signals | RP_SCK, RP_CS_N, RP_MOSI (RP2040 → FPGA); RP_MISO, RP_ATTN (FPGA → RP2040); RP_IRQ_N (FPGA → RP2040, the z2_mbx host interrupt, unchanged) | Sheet 4 translators |
| Output reference (proposed S4-6) | Every FPGA → RP2040 signal passes U402, whose B-side supply is **RP2040 GP24**, driven high by firmware. Until GP24 is high, ATTN, IRQ_N and MISO are not driven toward the RP2040: ATTN reads not ready and IRQ_N reads no interrupt (sheet-4 resistors). Firmware drives GP24 high (12 mA drive) and waits ≥ 100 µs before it uses the link | [sheet4-design-notes.md](../stage2/sheet4-design-notes.md) §6.3, §9 |
| Mode | SPI mode 0 (CPOL 0, CPHA 0), 8-bit words, MSB first | S4-2 |
| Chip select | **RP2040 GPIO** (GP9 as SIO), held low for the whole frame. The PL022's own SSPFSSOUT is not used: with SPH = 0 it pulses between words [V S65] | S4-2 |
| SCK | ≤ **10 MHz** initial operating target; **20 MHz** performance target. Both subject to STA (sheet-4 STA results) and hardware measurement M-15 | S4-1 |
| tCSS | CS_N↓ to the first SCK↑: ≥ 100 ns | Lets the FPGA release the SCK-domain reset (CS_N is its asynchronous reset) |
| tCSH | Last SCK↓ to CS_N↑: ≥ 100 ns | The last byte reaches the FIFO before the frame ends |
| tCSW | CS_N high between frames: ≥ 1 µs | The core detects the frame end and drains the FIFO |
| Idle levels | SCK low, MOSI low, CS_N high. Default resistors on the FPGA side hold these when the X4 is **unpowered** (the translators isolate; sheet 4, R-51). They do **not** hold CS_N high while the RP2040 is in reset or booting with the X4 powered: its pads are then inputs with pull-down [V S65], and the powered translator passes that low, so the FPGA sees CS_N asserted with no clock (§11). Firmware drives CS_N high (GPIO output) before it enables the SPI pins | §11 |
| ATTN | **Active high = READY.** Low while a frame is in progress, while a command executes, after reset until ready, and whenever the FPGA is unconfigured (weak pull-down plus the sheet-4 pull-down) | S4-5; fail-safe |

## 3. Transaction model (split transactions)

1. **Wait for ATTN = 1** (READY).
2. **Command frame:** CS_N low; clock the command (§4); CS_N high. The MISO bytes clocked during this frame are the current response buffer (the previous response); the master may ignore them.
3. **Wait for ATTN = 1** again: the command has executed and its response is ready. Timeout §8.
4. **Response frame:** a GET_RESPONSE command, clocked for at least the expected response length. MISO carries the response (§4.2).
5. Check RSYNC, CRC and that the echoed SEQ equals the command's SEQ.

**Rules:**
- **R1.** Only a valid, accepted command replaces the response buffer.
- **R2.** GET_RESPONSE never replaces it, so it can be repeated after a response CRC error.
- **R3.** An invalid or rejected frame (§6) has **no side effects** and does not change the response buffer. The master sees the old SEQ and resends.
- **R4.** The FPGA never needs the master to pause SCK. Every byte clocked is accepted into the RX FIFO at line rate. Flow control is ATTN, between frames (owner requirement 3).

## 4. Frame formats, CRC and byte order

### 4.1 Command frame (MOSI)

| Byte | Field |
|---|---|
| 0 | SYNC = 0xA1 |
| 1 | CMD |
| 2 | SEQ (chosen by the master, echoed in the response) |
| 3–4 | LEN: payload length in bytes, big-endian, 0 to 259 |
| 5 … 4+LEN | Payload |
| 5+LEN, 6+LEN | CRC-16, high byte first |
| further bytes | Padding (any value). Clocked so the response can be read in the same frame; ignored |

### 4.2 Response frame (MISO)

| Byte | Field |
|---|---|
| 0 | RSYNC = 0x51. The FPGA writes it **last**, so a partially built buffer never shows 0x51 |
| 1 | STATUS: b0 fault indication (`fault_ind`, C-26); b1 host interrupt pending (RP_IRQ_N asserted); b2 an error counter is non-zero; b7..b3 0 |
| 2 | SEQ of the command this response belongs to |
| 3 | RCODE: 0x00 OK, 0x01 ERR_CMD (unknown command), 0x02 ERR_LEN (LEN does not fit CMD), 0x03 ERR_ARG (argument out of range); nothing executed unless OK |
| 4–5 | LEN of the response payload, big-endian, 0 to 256 |
| 6 … 5+LEN | Payload |
| 6+LEN, 7+LEN | CRC-16, high byte first |
| further bytes | Undefined (earlier buffer contents); the master ignores them. *Corrected 2026-11-19: earlier drafts said 0x00, which the RTL does not do* |

### 4.3 CRC (owner decision S4-4)

| Parameter | Value |
|---|---|
| Variant | **CRC-16/IBM-3740** (also known as CRC-16/CCITT-FALSE) |
| Polynomial | 0x1021 (x¹⁶ + x¹² + x⁵ + 1) |
| Initial value | 0xFFFF |
| Input and output reflection | none: bits processed MSB first, the same order as on the wire |
| Final XOR | 0x0000 |
| Check value | CRC("123456789") = **0x29B1** (verified in `hostlink.py`) |
| Coverage | Every byte from SYNC/RSYNC to the end of the payload |
| Transmission | High byte first |
| Receiver test | The CRC over the covered bytes **plus the two CRC bytes** is 0x0000 |

### 4.4 Byte order

- Multi-byte fields are big-endian.
- SRAM data words are sent as two bytes, upper lane (D15–D8, byte 2n) first. Byte order spec vectors V1 and V5 apply at the SPI pins (HL-1).
- Word addresses are 18-bit, sent as 3 bytes, big-endian; bits 23..18 must be 0.

## 5. Commands

| CMD | Name | Payload (LEN) | Response payload | Side effects; repeatable? |
|---|---|---|---|---|
| 0x01 | IDENTIFY | – (0) | 8 bytes (§1) | None; yes |
| 0x02 | STATUS | – (0) | FLAGS (= STATUS byte), CRC_ERRORS (2), FRAME_ERRORS (2), BUSY_REJECTS (2), reserved 0: 8 bytes. Counters saturate at 0xFFFF | None; yes |
| 0x03 | GET_RESPONSE | – (0) | – (the buffer is sent unchanged, rule R2) | None; yes |
| 0x04 | RESET_LINK | – (0) | – | Clears the three counters. SRAM and mailbox state untouched; yes |
| 0x05 | ECHO | 0–256 bytes | The same bytes | None; yes (link test, HL-1) |
| 0x10 | SRAM_WRITE | ADDR (3) + N words (2N), N = 1–128; LEN = 3 + 2N | – | N host-port writes, both lanes, ascending addresses; ADDR + N ≤ 2¹⁸. Yes: absolute data |
| 0x11 | SRAM_READ | ADDR (3) + N (1), N = 1–128 (0x80 = 128; 0 is ERR_ARG) | 2N bytes | N host-port reads; yes |
| 0x12 | SRAM_WRITE_BE | ADDR (3) + BE (1: b1 upper, b0 lower lane; 0 is ERR_ARG) + DATA (2) | – | One host-port write with `h_be` = BE; yes |
| 0x20 | REG_WRITE | IDX (1, 0–15) + BE (1) + VALUE (2) | – | One shared-register write (shared-memory spec §4.3; ownership rules apply and are reported in H_EVENTS). Yes, **except** QCTL $A55A: a repeat performs a second link reset, which is harmless because both sides resynchronise on EPOCH |
| 0x21 | REG_READ | IDX (1) | VALUE (2) | None (reads have no side effects, R-17); yes |
| other | – | – | RCODE ERR_CMD | None |

## 6. Validation: no partial commit (owner requirement 1)

**Staging before commit.** Payload bytes are staged in an FPGA buffer as they arrive. **Nothing executes until the whole frame has been received and validated.** Execution then reads the staged payload, so posted SRAM writes and the CRC check cannot conflict: a write is never issued before the CRC that covers it has been checked.

**Checks at the frame end (CS_N high, FIFO drained),** in this order. The first failure decides.

| # | Check | On failure |
|---|---|---|
| V1 | No FIFO entry of this frame carries the "byte dropped" flag (§9) | Reject (FRAME_ERRORS) |
| V2 | The frame started while READY | Reject (BUSY_REJECTS) |
| V3 | SYNC = 0xA1 | Reject (FRAME_ERRORS) |
| V4 | LEN ≤ 259, and at least 7 + LEN bytes received | Reject (FRAME_ERRORS) |
| V5 | CRC residue = 0 | Reject (CRC_ERRORS) |
| V6 | CMD known; LEN valid for CMD; arguments in range | Response ERR_CMD, ERR_LEN or ERR_ARG; nothing executed |

**Outcomes:**
- A **rejected** frame changes nothing except its counter (rule R3).
- A frame passing V1–V6 executes completely, in order (§7).

## 7. Ordering and atomicity (owner requirement 6)

| Rule | Statement |
|---|---|
| O-1 | Commands execute one at a time, in the order of their frames. Each host-port transaction completes (`h_ack`) before the next starts (H-1, H-3) |
| O-2 | SRAM_WRITE writes its words in ascending address order. A Zorro access between two of them can see a partly written burst, as with any multi-word write. Software publishes data with the sheet-3 queue protocol: payload first, then the index write in a **later** command (Q-5) |
| O-3 | The response, and therefore ATTN, is produced only after every transaction of the command has completed. A write is never reported before `h_ack` (H-3) |
| O-4 | All-or-nothing with respect to validation (§6): a corrupted, truncated, busy or oversized frame has no effect |
| O-5 | Sheet-3 rules are unchanged: single writer per register (Q-1), epoch-tagged index writes (Q-2), link reset (Q-6). The Zorro side keeps priority and determinism (formal X4); the SPI side cannot change Zorro timing |

## 8. Flow control, timeouts and recovery (owner requirement 3, S4-5)

**Flow control:**
- The master starts a frame **only when ATTN = 1**. ATTN falls within 100 ns of CS_N↓ and stays low until the command's response is ready.
- A **continuously busy Zorro bus** only lengthens the execution phase. Each host-port transaction waits at most one Zorro cycle, bounded by the XRDY watchdog (H-4: simulation maximum 2.62 µs). The SPI never has to stall, nothing queues in the FPGA beyond one frame, and no buffer grows.
- Worst case for a 128-word command: 128 × 2.62 µs ≈ 335 µs.

**Timeouts and recovery (master side; the FPGA has no protocol timeouts):**

| Event | Master action |
|---|---|
| ATTN not high within **1 ms** of CS_N↑ | Wait 10 ms, then IDENTIFY. After 3 failures, report LINK_DOWN to the PC. Recovery from there: FPGA reload over the RP2040 JTAG option (D-12), or a power cycle |
| Response RSYNC ≠ 0x51 or CRC error | GET_RESPONSE again (rule R2), up to 3 times |
| Echoed SEQ ≠ command SEQ | The command was rejected (§6): resend it, up to 3 times. Commands are repeatable (§5) |
| RCODE ≠ OK | Report it to the caller; nothing was executed |
| Unknown major version | Stop and report |

**ATTN as the acknowledgement path:**
- The command frame's CS_N↓ acknowledges the previous response.
- ATTN↑ notifies completion.
- GET_RESPONSE fetches the result, and a repeat re-fetches it without side effects.

## 9. Buffer sizing (owner requirement 2)

| Buffer | Size | Argument |
|---|---|---|
| Largest command frame | 266 bytes (SRAM_WRITE of 128 words) | §4.1, §5 |
| Largest response frame | 264 bytes (SRAM_READ of 128 words) | §4.2 |
| **RX FIFO** (SCK → clk_core, Gray pointers) | **16 entries** of {byte, start-of-frame, byte-dropped} | The core reads one entry per clock in **every** state and never stalls the FIFO. A byte takes 8 SCK periods: 400 ns at 20 MHz, 128 ns at the PL022's 62.5 MHz maximum, versus 20 ns per core read. Occupancy is bounded by the pointer-synchroniser latency (≤ 3 core clocks), so **≤ 2 entries at any SCK the RP2040 can generate**. If the core clock ever stopped, a full FIFO drops bytes and flags the next entry, so the frame is rejected (V1): safety does not depend on the rate argument |
| **Staging buffer** | 512 bytes (payload ≤ 259) | A frame announcing LEN > 259 is rejected at the header; bytes beyond the payload are not stored |
| **Response buffer** | 512 bytes (response ≤ 264) | Built after execution; static while frames are clocked (rule R2) |
| Sustained contention | One command in flight; the master waits for ATTN | No queue can grow; throughput degrades and latency stays bounded (§8) |

## 10. Diagnostics

- STATUS counters: CRC_ERRORS, FRAME_ERRORS, BUSY_REJECTS.
- The STATUS byte in every response flags a non-zero counter.
- RESET_LINK clears the counters.

## 11. Power, reset and independent events (owner requirement 7)

| Condition | Behaviour | Mechanism |
|---|---|---|
| FPGA unconfigured or erased | ATTN low: no frames start. RP_IRQ_N high: no interrupt. MISO undefined, but ignored | FPGA weak pull-down plus sheet-4 default resistors: ATTN pull-down, RP_IRQ_N pull-up stronger than the weak pull-down (R-51) |
| FPGA reset or reconfiguration during a frame or command | The frame is lost; the master times out (§8) and re-IDENTIFYs. A write in flight may leave one word undefined (H-5); the RP2040 quiesces before a JTAG reload | POR; H-5 |
| X4 unpowered | No frames; FPGA inputs held at idle levels; nothing back-feeds the X4 | SN74AVC4T774 VCC isolation and Ioff [V S66]; A-side defaults CS_N high, SCK and MOSI low |
| Carrier unpowered, X4 running (Amiga off) | No frames. At the RP2040: ATTN low (not ready), IRQ_N high (no interrupt). The master reports LINK_DOWN after the §8 retries | U402 isolated (its VCCA is off); RP2040-side resistors R424 (IRQ_N to GP24's supply) and R425 (ATTN to GND) |
| RP2040 unpowered while the X4's header 3.3 V stays up (the X4's K4 key switches the RP2040's I/O and core supply P3V_RP, [V S1 sh.21]) | As for "RP2040 in reset" below. No output can drive the unpowered RP2040, because U402's B supply is the RP2040's own GP24 | Proposed S4-6; B-side pull-downs on every RP2040 → FPGA input |
| RP2040 in reset or booting, X4 powered | The FPGA sees CS_N **asserted** with SCK and MOSI low: a frame opens but no byte arrives. When firmware first drives CS_N high, the frame ends and counts in FRAME_ERRORS (V3: no SYNC byte), or in BUSY_REJECTS (V2) if a command was executing, which then completes normally; nothing new executes and the response buffer is unchanged. ATTN stays low while CS_N is low (it is gated by CS_N high). No interrupt is produced (RP_IRQ_N is an FPGA output) | RP2040 pads reset to input with pull-down [V S65]; the powered translator drives the A side, so the A-side resistors cannot hold CS_N high. Test tb_spi P16. *Corrected 2026-11-19: earlier drafts said the default resistors hold CS_N high here* |
| RP2040 reset in mid-frame | SCK stops and CS_N stays asserted until firmware drives it high; then the partial frame is discarded (V4 or V5) and nothing commits | §6; tb_spi P16 |
| SCK stops in mid-byte | Incomplete bytes are never stored; CS_N↑ resets the SCK-domain counters | RTL |
| Amiga reset (/BUSRST) | The link and response buffer are unaffected; host-side mailbox state survives (Q-7) | Sheet 3 |
| After FPGA power-on | The response buffer holds an IDENTIFY response (SEQ 0xFF); then ATTN rises | RTL |

## 12. Normative test vectors

Generated by `python -I tools/hostlink/hostlink.py vectors`. The CRC residue of every frame is 0.

| Vector | Bytes (hex, transmission order) | CRC-16 |
|---|---|---|
| CRC check "123456789" | `31 32 33 34 35 36 37 38 39` (ASCII) | 0x29B1 |
| IDENTIFY, SEQ 0x00 | `a1 01 00 00 00 e7 8d` | 0xE78D |
| STATUS, SEQ 0x01 | `a1 02 01 00 00 4b 61` | 0x4B61 |
| GET_RESPONSE, SEQ 0x02 | `a1 03 02 00 00 64 85` | 0x6485 |
| SRAM_WRITE 2 words at word $00010: $1234 $ABCD (byte order V1) | `a1 10 07 00 07 00 00 10 12 34 ab cd ef c7` | 0xEFC7 |
| SRAM_READ 2 words at word $00010, SEQ 0x08 | `a1 11 08 00 04 00 00 10 02 a8 e2` | 0xA8E2 |
| Response OK to SEQ 0x08, data $1234 $ABCD, STATUS 0x00 | `51 00 08 00 00 04 12 34 ab cd d9 e3` | 0xD9E3 |
| REG_WRITE idx 10 (QCTL) = $A55A, both lanes, SEQ 0x09 | `a1 20 09 00 04 0a 03 a5 5a 1a 72` | 0x1A72 |
| REG_READ idx 13 (AMIGA_STATUS), SEQ 0x0A | `a1 21 0a 00 01 0d 82 4a` | 0x824A |
| ECHO 01 02 03, SEQ 0x0B | `a1 05 0b 00 03 01 02 03 b0 ec` | 0xB0EC |

## 13. Open items

| Item | Status |
|---|---|
| SCK-to-MISO timing at 10 and 20 MHz, including FPGA clock insertion, translators, PCB and RP2040 input sampling (owner requirement 4) | Sheet-4 timing budget, STA, then M-15 on hardware |
| MISO launch edge: standard (SCK↓) or early (SCK↑, more setup time if the RP2040's input sampling allows it) | FEATURES b2 reports it. Decided by STA and M-15 |
| RP2040 firmware and Windows implementations | Stage 4; they must pass the vectors above and follow the firmware obligations FW-1 to FW-8 ([sheet4-design-notes.md](../stage2/sheet4-design-notes.md) §9) |
| Budget result (sheet 4 rev A) | 10 MHz closes with the standard launch (margin ≥ 10.92 ns); 20 MHz needs the early launch (≥ 12.18 ns), whose hold side depends on when the RP2040 samples MISO ([sheet4-timing-budget.md](../stage2/sheet4-timing-budget.md) §3.3). Until M-15: 10 MHz, standard launch |
| RP_VIO level and the K4 back-power check | M-16 |
