# Sheet 3: SRAM and local-bus timing budget (revision A)

**Status:** 2026-11-19.
- The FPGA figures come from the exploratory Diamond runs, with Diamond-placed pins (§4). They are not final until the sheet-2 pinout is analysed (G-STA).
- SRAM limits: ISSI IS61/64WV25616EDBLL datasheet Rev. A2, −10 column, VDD 2.4–3.6 V [V S61].
- Transceiver figures: [V S46], as used on sheet 1 ([sheet1-timing-budget.md](sheet1-timing-budget.md)).
- **Clock:** 50 MHz [A] (20 ns). "s" or "g" = the FPGA clock edge at which the access starts; pin values change tCO after an edge.

## 1. Inputs

| Quantity | Min | Max | Source |
|---|---|---|---|
| FPGA clock-to-out, SRAM pins (SA, /CE, /OE, /WE, /UB, /LB) | 2.74 | 10.09 | Diamond, worst of 4 runs (§4) |
| FPGA clock-to-out, LD pins (data and enable) | 2.69 | 12.44 | Diamond, worst of 4 runs |
| U301 tAA / tACE / tDOE / tBA (access) | – | 10 / 10 / 4.5 / 6.5 | [V S61] |
| U301 tOHA (output hold after address change) | 2.0 | – | [V S61] |
| U301 tHZOE / tHZCE / tHZB / tHZWE (to High-Z) | – | 4 / 4 / 3 / 5 | [V S61] |
| U301 tSA / tAW / tPWE1 / tSD / tHD / tHA | 0 / 8 / 8 / 6 / 0 / 0 | – | [V S61] |
| U103 A→B / B→A propagation | 0.6 | 4.4 / 6.0 | [V S46] |
| U103 OE→A enable / disable | – | 8.1 / 8.2 | [V S46] |
| PCB trace, FPGA ↔ U301 | – | 1.0 | [E] (≈ 150 mm at 6–7 ns/m) |

U301's access times are specified into 30 pF. The local bus carries U301 (CI/O 8 pF), U103's A port and the FPGA, so the 10 ns figures are used unchanged [A]. The margins below are tens of nanoseconds, so this is not critical.

## 2. Access timing against the SRAM limits (worst-case combination)

### 2.1 Zorro read (FSM go at edge g; U301 pins at g + 1)

| Requirement | Calculation | Result |
|---|---|---|
| Data valid at the U301 pins | (g+1) + tCO max + max(tAA, tACE, tDOE, tBA) = 20 + 10.09 + 10 | **g + 40.1 ns** |
| Data valid at the slot (U103 A→B, trace) | 40.1 + 4.4 + 1.0 | g + 45.5 ns |
| XRDY can be released (hold_q at g + 3) | 60 + clock-to-XRDY path > 0 | ≥ g + 60 ns |
| **Margin: data at the slot before XRDY release** | 60 − 45.5 | **≥ 14.5 ns** |

The CPU latches data at least one 7 MHz state after the motherboard sees XRDY [V S57], so the real margin is larger.

### 2.2 Zorro write (go at edge g: U103 drives LD; address, /CE and lanes at the pins from g + 1; /WE low g + 4 to g + 5)

| Limit | Calculation (ns after g) | Margin |
|---|---|---|
| tSA ≥ 0: address before /WE falls | (80 + 2.74) − (20 + 10.09) | **52.7 ns** |
| tAW ≥ 8: address to end of write | (100 + 2.74) − 30.09 − 8 | **64.7 ns** |
| tPWE1 ≥ 8: /WE width | 20 − (10.09 − 2.74) − 8 | **4.7 ns** (worst-case skew between the pin's two edges, taken as the whole group spread) |
| tSD ≥ 6: data before /WE rises | Data on LD by g + 12.44 + 8.1 + 6.0 = g + 26.5; (100 + 2.74) − 26.5 − 6 | **70.2 ns** |
| tHD, tHA ≥ 0 | Data are held by the master until after the strobes; the address changes only at the next go | ≫ 0 |
| /OE high during the write | `zq_oe` = 0 in write phases (formal F5/F17) | – |

The tPWE1 figure assumes /WE's falling edge has the fastest tCO of the whole group (2.74 ns) and its rising edge the slowest (10.09 ns). A real pin's two edges differ by far less, so 4.7 ns is a deliberately pessimistic floor. It is still positive.

### 2.3 Host read (start at edge s; capture at s + 2)

| Requirement | Calculation | Result |
|---|---|---|
| Data valid at the FPGA LD pins | s + 10.09 + 10 + 1.0 | s + 21.1 ns |
| Capture edge | s + 40 | |
| **Available for the FPGA input path (pad to register setup)** | 40 − 21.1 | **18.9 ns**. MachXO2 input paths need a few ns [K]. To be confirmed by G-STA once the sheet-4 host path exists in synthesis |
| Hold after capture | /OE and /CE rise at ≥ s + 40 + 2.74; data then hold until High-Z | ≥ 2.7 ns before any change [A: FPGA input hold ≈ 0] |

### 2.4 Host write (start at s: address, /CE, lanes, LD data; /WE low s + 1 to s + 2; release at s + 3)

| Limit | Calculation (ns after s) | Margin |
|---|---|---|
| tSA ≥ 0 | (20 + 2.74) − 10.09 | **12.7 ns** |
| tAW ≥ 8 | (40 + 2.74) − 10.09 − 8 | **24.7 ns** |
| tPWE1 ≥ 8 | 20 − 7.35 − 8 | **4.7 ns** (same pessimistic skew as §2.2) |
| tSD ≥ 6 | (40 + 2.74) − 12.44 − 6 | **24.3 ns** |
| tHD ≥ 0 | LD released at ≥ 60 + 2.69; /WE high by ≤ 40 + 10.09 | **12.6 ns** |
| tHA ≥ 0 | The address changes at ≥ s + 4: 80 + 2.74 − 50.09 | **32.7 ns** |
| /OE high ≥ 4 ns before /WE falls (datasheet note 2) | /OE held high for the whole write | – |

### 2.5 Bus turnaround (at least GUARD = 2 clocks between different LD drivers; formal X3)

| From → to | Release completes | Next driver on (≥ 40 ns + tCO min) | Margin |
|---|---|---|---|
| U301 read → anything | tCO max + tHZOE/tHZCE = 10.09 + 4 = 14.1 ns | ≥ 42.7 ns | **28.6 ns** |
| FPGA LD drive → anything | tCO max (LD) = 12.4 ns | ≥ 42.7 ns | **30.3 ns** |
| U103 B→A (write phase) → anything | FPGA comb ≤ 18 + U107 3.8 + U103 OE→A disable 8.2 = 30.0 ns | ≥ 42.7 ns | **12.7 ns** |

## 3. FPGA clock-to-out allocations (LPF `CLOCK_TO_OUT`)

| Group | Allocation | Derived from | Worst result |
|---|---|---|---|
| SRAM_OUT | 12 ns | §2 keeps every SRAM AC limit with ≥ one clock of margin except tPWE1 (≥ 4.7 ns at 12 ns) | 10.09 ns |
| LD_OUT | 16 ns | Register-read data reach the slot before XRDY can be released: 20 + 3 (fastest XRDY path) − 4.4 (U103) − 1.0 (trace) ≈ 17 ns. Host-write tSD alone allows ≈ 35 ns | 12.44 ns |

## 4. Diamond results used (exploratory, Diamond-placed pins, 15 pF, LVCMOS33)

| Run | Device | SRAM_OUT max / min | LD_OUT max / min | 50 MHz worst path, slack |
|---|---|---|---|---|
| Stage 3 z2_top | −4 C | 9.949 / 2.931 | 12.073 / 2.928 | 16.989 ns, 2.73 ns |
| Stage 3 z2_top | −4 I | 9.600 / 2.741 | 12.439 / 2.798 | 16.308 ns, 3.41 ns |
| Fit test, 105 signals | −4 C | 9.941 / 3.011 | 11.812 / 2.685 | 15.575 ns, 4.15 ns |
| Fit test, 107 signals | −4 C | 10.088 / 2.931 | 12.258 / 2.855 | 15.736 ns, 3.98 ns |

All four runs: 0 setup and 0 hold errors, and every sheet-1 MAXDELAY path still meets 18 ns (worst 15.09 ns).

## 5. Zorro-side latency (XRDY-gated mode, the default)

| Access | Local-bus action | XRDY release | Slot /AS → XRDY (simulation) |
|---|---|---|---|
| SRAM read | START + 6 | go + 3 | 226–270 ns across seeds and delay corners; ≈ 20 ns spread from the /AS-to-clock phase |
| SRAM write | DS seen + 1 | go + 5 | Set by the write strobe (S4) |
| Register read (unchanged from rev B) | START + 6 | go + 1 | – |

These figures are the same with and without host traffic (tb_shm S3).

## 6. Zero-wait mode (opt-in, gate G-ZEROWAIT)

- **Simulation.** SRAM read and write in zero-wait mode return correct data in the model (tb_shm S11).
- **Write path.** From the write strobe to /WE rising is about 7 clocks plus synchronisation: ≈ 170 ns, against ≈ 211 ns of 68000 strobe width [D from S57].
- **Read path.** Data reach the slot about 210 ns after /AS, against a CPU latch point about 230–270 ns after /AS [D].
- **Status.** Both margins are thin and depend on A2000 buffer delays not yet measured (M-3, M-7). Zero-wait stays disabled until G-ZEROWAIT is passed by measurement.
