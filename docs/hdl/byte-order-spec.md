# Canonical byte order: Amiga, FPGA, RP2040 and Windows (revision A)

**Status:** normative, 2026-11-19 (owner requirement 1 of the sheet-3 review).
- Applies to every structure in shared memory, the FPGA registers, the SPI host link (sheet 4), the RP2040 firmware and the Windows software.
- **Verified in hardware simulation:** tb_shm S12 ([../../hdl/sim/tb_shm.v](../../hdl/sim/tb_shm.v)) runs the vectors of §6 through both ports.
- Vectors: [../test/cross-endian-vectors.csv](../test/cross-endian-vectors.csv).

## 1. Rule

**Shared memory is a byte array, and every multi-byte value in it is big-endian ("Amiga order").**

- The MC68000 is big-endian and is the slowest participant (7 MHz), so it never swaps.
- The RP2040 (Cortex-M0+) and the x86 are little-endian. They swap when they read or write a multi-byte field, using `be16`/`be32` helper functions; this is cheap for them.
- Byte arrays (strings, opaque payloads, files) are never swapped.

## 2. The 16-bit word and its byte lanes (hardware, fixed)

| SRAM byte address | Word | Bits | Zorro | U301 lane | Host port |
|---|---|---|---|---|---|
| 2n (even) | n | 15..8 | D15–D8, /UDS | /UB | `h_be[1]`, `h_wdata/h_rdata[15:8]` |
| 2n + 1 (odd) | n | 7..0 | D7–D0, /LDS | /LB | `h_be[0]`, `h_wdata/h_rdata[7:0]` |

- **Amiga.** `MOVE.W` at even address 2n reads (byte 2n << 8) | byte 2n+1. `MOVE.B` to an even address writes only byte 2n (/UDS); to an odd address, only byte 2n+1 (/LDS).
- **Host port.** `h_addr` is the word number n. In the PC's flat view, byte address A is word A >> 1, upper lane if A is even.
- **FPGA registers** are 16-bit words with the same lane rule. An index register {EPOCH, INDEX} has EPOCH in byte 0, the upper lane.
- **Byte-lane order and data-line permutation.** The data lines may be permuted within a byte lane at layout: that is invisible, because both sides use the same wiring. The **lanes** themselves may not be swapped. S12 vector V3 (walking one) detects a lane swap.

## 3. Multi-byte values

| Type | Layout at offset o | Alignment |
|---|---|---|
| 16-bit | byte o = bits 15–8, byte o+1 = bits 7–0 | o even |
| 32-bit | bytes o..o+3 = bits 31–24, 23–16, 15–8, 7–0. Word at o = high half | o a multiple of 4. The 68000 needs even alignment; 4-byte alignment keeps 68020+ and the PC side simple |
| 64-bit (if ever needed) | big-endian, 8 bytes | o a multiple of 8 |

**Atomicity.**
- A 16-bit aligned access is atomic from either side (G1).
- A 32-bit value is two Zorro cycles (high word first), or two host words, so it is **not atomic** across the two halves (G3).
- Any 32-bit field that can change while the other side reads it must be protected by the queue ownership rules (the producer owns the slot until it publishes the index) or a sequence counter.

## 4. Structures

| Structure | Rule |
|---|---|
| Queue slot header (architecture review §7.4: seq, type, flags, len, status, ref_seq, crc16, reserved) | Each field 16-bit big-endian at its even offset |
| Queue payload | Byte array. A message type that carries integers defines them as big-endian at aligned offsets |
| Control block in the fixed window (magic, version, ring geometry, side state) | Fields big-endian. The magic is defined as a byte sequence, so a byte-order error shows at once |
| CRC-16 | Computed over the byte array in ascending byte-address order; the result is stored big-endian |
| Text | Byte arrays (ASCII or UTF-8 as the message defines); never swapped |

## 5. SPI host link (normative for the sheet-4 SPI slave and the RP2040 firmware)

| Item | Rule |
|---|---|
| Word on the wire | Most significant bit first, so the byte 2n (upper lane) is sent first, then byte 2n+1 |
| Burst of words | Ascending word address. **The SPI byte stream therefore equals the shared-memory byte array**, and the RP2040 and the PC can copy it into a `uint8_t[]` without any swapping |
| Register values | 16-bit, MSB first. The firmware forms `value = (b0 << 8) | b1` |
| Addresses and lengths in SPI command headers | Defined by the sheet-4 protocol. They must state their width and be big-endian, for consistency |
| PC API (`read(addr, len)` / `write(addr, data)`) | Byte addresses and byte arrays. A byte write to one lane uses the host byte enables (`h_be`). The Windows library offers `rd_be16`, `rd_be32`, `wr_be16`, `wr_be32` helpers |

## 6. Cross-endian test vectors (for BridgeDiag on the Amiga, the RP2040 firmware and the Windows test utility)

Full table with every view: [../test/cross-endian-vectors.csv](../test/cross-endian-vectors.csv). Each tool writes a vector from its own side and checks it from the others. S12 checks V1–V4 and V6 between the Zorro side and the host port in simulation now.

| ID | Bytes at ascending addresses | Amiga sees | Host word(s) | Little-endian CPU, correct (`be16`/`be32`) | Little-endian CPU, **wrong** (native cast) |
|---|---|---|---|---|---|
| V1 | 01 23 45 67 89 AB CD EF | MOVE.W = $0123; MOVE.L = $01234567 | $0123, $4567, $89AB, $CDEF | be16 = 0x0123; be32 = 0x01234567 | 0x2301; 0x67452301 |
| V2 | C3 3C (host writes the lanes separately); A5 5A (Amiga writes bytes) | $C33C; MOVE.B at even = $A5 | h_be = 10 then 01 → $C33C; $A55A | – | Lane swap shows as $3CC3 / $5AA5 |
| V3 | Word k = 1 << k, k = 0..15 | $0001 … $8000 | identical | identical via be16 | 0x0100 for k = 0 (lane swap) |
| V4 | 12 34 00 01 80 01 00 10 (header: seq $1234, type $0001, flags $8001, len $0010) | fields as written | $1234, $0001, $8001, $0010 | seq 0x1234, flags 0x8001 | 0x3412, 0x0180 |
| V5 | Index register Q0_PROD = {EPOCH $05, INDEX $2A} | $052A | register value 0x052A; SPI bytes 05 2A | epoch = b0, index = b1 | 0x2A05 |
| V6 | DE AD BE EF (32-bit counter, written with MOVE.L) | $DEADBEEF | $DEAD, $BEEF | 0xDEADBEEF | 0xEFBEADDE |

## 7. Responsibilities

| Component | Must |
|---|---|
| FPGA (this repository) | Keep the lane mapping of §2 (tb_shm S12 is the regression) |
| Sheet-4 SPI slave | MSB first, ascending addresses (§5); a test with V1 and V5 at the SPI pins |
| RP2040 firmware | Byte arrays end to end; no casting of the buffer to wider types; `be16`/`be32` helpers; self-test with the vectors at start-up (optional) and in BridgeDiag mode |
| Windows software | Same helpers; the test utility runs V1–V6 against the Amiga BridgeDiag tool |
| Amiga software | Native big-endian access; the driver maps the board non-cacheable (R-16); BridgeDiag writes and checks every vector |
