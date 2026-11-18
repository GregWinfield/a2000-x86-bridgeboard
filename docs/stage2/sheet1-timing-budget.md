# Sheet 1: timing budget, revision B (C-01, C-04, C-05, C-13)

**Status:** revision B, 2026-11-18.
- Buffer and gate delays are datasheet maxima [V].
- The FPGA share is an **allocation of 18 ns that is not proven**. Gate G-STA requires worst-case post-place-and-route analysis in Lattice Diamond (§9).
- Every total below that uses the 18 ns figure is a budget, not a result.

Evidence tags follow [../sources.md](../sources.md). This document supersedes §4 of the revision A design notes.

## 1. Component delays used

| Part | Path | Min–max (ns) | Conditions | Source |
|---|---|---|---|---|
| U101/U102 SN74LVC16244A | A→Y | 1.1–4.1 | VCC 3.3 V ±0.3 V, −40 to 85 °C | [V S45] |
| U103 SN74LVCH16T245 | A→B / B→A | 0.6–4.4 / 0.6–6.0 | VCCA 3.3 V ±0.3 V, VCCB 5 V ±0.5 V | [V S46] |
| | OE→B enable / disable | 0.8–6.4 / 0.8–6.3 | same | [V S46] |
| | OE→A enable / disable | 0.8–8.1 / 1.6–8.2 | same | [V S46] |
| U104 SN74LVC8T245 (rev B) | A→B | 0.5–4.4 | VCCA 3.3 V ±0.3 V, VCCB 5 V ±0.5 V | [V S53] |
| | OE→B enable / disable | 0.9–6.8 / 0.8–6.3 | same | [V S53] |
| U105 SN74LVC07A | A→Y | 1.0–3.6 | 3.3 V ±0.3 V | [V S48] |
| U106 SN74LVC1G00 | A/B→Y | 1.0–4.7 | 3.3 V ±0.3 V, CL 30/50 pF, −40 to 85 °C | [V S54] |
| U107 SN74LVC32A | A/B→Y | 1.0–3.8 | 3.3 V ±0.3 V, −40 to 85 °C | [V S55] |
| U108/U109 TPS3808 | SENSE→RESET (falling) | ≤ 20 µs | | [V S56] |
| | Release delay, CT open | 12–28 ms | | [V S56] |
| FPGA pin-to-pin, combinational | | **≤ 18 (allocation)**; 7.24 datasheet floor (one LUT, −4, LVCMOS25 8 mA, 0 pF, best case) | | [A] / [V S49] |
| PCB traces, 22 Ω + slot load | | 0.3–0.5 per trace; 2.0 for R117 + ~30 pF to the TTL threshold | | [E] |

## 2. /SLAVEn (C-01): limits 35 ns assertion, 50 ns negation [V S50]

| # | Stage | Max (ns) | Note |
|---|---|---|---|
| 1 | J101 → U102 trace | 0.3 | [E] |
| 2 | U102 A→Y | 4.1 | [V S45] |
| 3 | U102 → FPGA trace | 0.5 | [E] |
| 4 | **FPGA /AS → ZF_SLAVE_N** (also A16–A23 → ZF_SLAVE_N) | **18.0** | Allocation, G-STA |
| 5 | FPGA → U104 trace | 0.5 | [E] |
| 6 | **U104 A→B** (rev A was the LVC2T45 at tPHL 4.0 / tPLH 4.4) | 4.4 | [V S53] (one figure for both edges) |
| 7 | R117 22 Ω + slot load to threshold | 2.0 | [E] |
| | **Total, assertion and negation** | **29.8** | Margin **5.2 ns** to 35 and 20.2 ns to 50 |
| | Total with the FPGA datasheet floor (7.24 ns) | 19.0 | Not a bound: best case only |

**Effect of the C-04 change.** U104's ~OE (CARD_EN_N) is static during operation, so it is **not** in this path. It changes only:
- at arming, inside /BUSRST;
- on a fault, when the card is being withdrawn from the bus anyway.

The replacement costs +0.4 ns against the old part's tPHL, reducing the margin from 5.6 ns to 5.2 ns.

**What would break the budget.** The FPGA share above 23.2 ns, or the [E] items more than about 5 ns above estimate.

## 3. XRDY (limit: negated within 60 ns of /AS) [V S50]

| Stage | Max (ns) | Note |
|---|---|---|
| U102 + traces | 5.1 | |
| FPGA /AS → ZF_XRDY | 18.0 | Allocation, G-STA |
| **U107 (rev B gate)** | 3.8 | [V S55] |
| U105 + trace | 4.1 | [V S48] |
| Fall to threshold (motherboard pull-up) | 2.0 | [E] |
| **Total** | **33.0** | Margin **27 ns** (rev A: ≈ 29 ns total) |

**Release paths.**
- XRDY is released by /AS negation, /BERR assertion, or the FSM `hold_q` dropping.
- The watchdog forces release **2.0 µs** (100 clocks at 50 MHz) after the FSM starts counting. With synchronisation latency, XRDY is held for at most ≈ 2.1 µs. The testbench bound is 2.3 µs.

## 4. Data-buffer enable and release (C-05, C-13)

### 4.1 Release

Release is triggered by any of: /AS negation, /UDS and /LDS both negated, DOE negation, READ falling, /BERR assertion, or CARD_EN_N.

| Stage | Max (ns) |
|---|---|
| U102 + traces | 5.1 |
| FPGA (any of the six inputs) → ZF_DBUF_OE_N | 18.0 (allocation) |
| U107 | 3.8 |
| U103 OE→B disable | 6.3 |
| **Total** | **33.2** |

Requirements this release must meet:

| Requirement | Limit | Margin |
|---|---|---|
| MC68000 data-in high impedance after AS/DS negated (#29A, 8 MHz) | ≤ 187 ns [V S57] | ≥ 150 ns |
| **RMW:** card off before the master can drive the write portion. The read strobe negates entering S7; R/W goes low at S14; data at S15 | S7→S14 = 7 half-clocks ≈ 493 ns at 7.09 MHz, minus #12 (≤ 62 ns) = ≥ 431 ns [V S57] | **≥ 398 ns** |
| Rev A (no strobe term): release only from READ falling at S14 | — | Up to 33 ns of possible contention if the motherboard drives at S14. **Fixed in rev B** |

### 4.2 Read enable

The read enable requires all of: /AS, select, READ, DOE, a data strobe, no /BERR, card enabled, `dir_q = 1`, and `oe_rd_q`.

| Event | Timing |
|---|---|
| `oe_rd_q` set | ≥ 6 clocks (~120 ns) after the FPGA sees /AS |
| Transceiver drives the bus | max(DOE, `oe_rd_q`) + FPGA + U107 + U103 OE→B enable (6.4 ns) |
| XRDY released | One clock after the data are on LD, so in XRDY-gated mode the motherboard inserts wait states until then |

`ready` does **not** wait for DOE. Its timing relative to DOE is TBV by measurement M-3. If the A2000 asserted DOE only after DTACK, the result would be a deadlock, which the watchdog resolves; that is not expected [S10].

## 5. Direction changes (C-05)

| Interval | Guard | Worst case it must cover |
|---|---|---|
| Enable register off → DIR change | ≥ 2 clocks (40 ns), plus 1 controller clock | tCO [A] ≤ 9 + U107 3.8 + U103 OE disable 8.2 (A side) = **21 ns** |
| DIR change → enable register on | ≥ 2 clocks (40 ns) | tCO skew between the DIR and OE registers [A] ≤ 9 ns; TI: change DIR only with OE high [V S46] |
| FPGA LD drive off → U103 B→A on | ≥ 2 clocks (`oe_quiet`) | FPGA output disable (tCO-class) ≤ 9 ns [A] |

The guards are enforced by counters in `z2_core` and proven by formal properties F8/F9. They are also checked at the U103 model pins in simulation (assertion "DIR changed while enabled").

## 6. Write capture

| Step | Timing |
|---|---|
| Data valid on the Zorro bus before DS | ≥ 40 ns (#26) [V S57] |
| FPGA response | Synchronises DS (20–40 ns), enables B→A, waits 2 clocks, captures: ≥ 100 ns after DS at the FPGA |
| U103 B→A plus OE→A enable | 6.0 + 8.1 = 14.1 ns, well inside the 40 ns wait |
| DS asserted width (write) | ≥ 140 ns (#14A, 8 MHz) [V S57] |

In XRDY-gated mode the cycle is also stretched until the capture.

## 7. Read-modify-write (TAS) sequence (C-13)

MC68000 RMW cycle [V S57 §4.1.3/§5.1.3]. "→ card" shows the rev B FSM action. All times are approximate at 7.09 MHz.

| State | Bus | Card |
|---|---|---|
| S0–S2 | R/W high; address; **/AS and one DS asserted** (TAS is byte only) | /SLAVEn (combinational); XRDY held; FSM samples select; DIR → A→B (guarded); drives LD; `oe_rd_q`; transceiver on with DOE·DS |
| S4 (+ waits) | DTACK sampled | XRDY released one clock after data on LD → motherboard DTACK |
| Entering S7 | CPU latches data; **DS negated, /AS held** | Read term drops on DS (§4.1). FSM clears `oe_rd_q` and `ld_oe`; DIR returns to B→A after the guard |
| S8–S13 | Internal modify; bus unchanged | Waiting in ST_BETWN |
| S14 | **R/W low** | FSM sees READ low after a read phase and holds XRDY again (`hold_q`) for the write portion |
| S15 | CPU drives data | Card's B port has been off since S7 + 33 ns |
| S16 (+ waits) | **DS asserted**; DTACK sampled | New phase: B→A enable, capture after 2 clocks, byte lane from the strobe, XRDY released |
| Entering S19 | /AS, DS negated | End of cycle; RMW_CYCLES incremented |

**Assumption [A].** Automatic DTACK for the write portion follows XRDY as in a normal cycle. Rev B re-holds XRDY at S14, about 280 ns before S16. The behaviour of the real A2000 is checked by measurement M-10.

## 8. Card enable and start-up (C-03, C-04)

| Event | Time | Note |
|---|---|---|
| Rail good → EN_OK released | 12–28 ms (CT open) per supervisor [V S56] | Both must release; wired-AND |
| FPGA configured after its POR | 1.4 ms (XO2-2000) [V S49] | Independent of EN_OK |
| FPGA arms | First synchronised /BUSRST, filtered over 4 samples (80 ns), while EN_OK is true | |
| CARD_EN_N | NAND 4.7 ns; U104 OE enable 6.8 ns | All inside /BUSRST |
| A2000 power-on reset | ≈ 0.7 s, derived from C814 22 µF / R805 47 kΩ / PST518B on the R6 schematic | [D] from [V S51]; **TBV M-9** |
| Rail fault → card off | ≤ 20 µs (supervisor) + 4.7 + 6.3 ns | During the 20 µs the FPGA is still powered and in control |

**Supervisor threshold against the FPGA supply.**
- The MachXO2 HC core operates at 2.375–3.6 V [V S49 Table 3.2], so the FPGA is within its operating range at the +3V3 trip point (3.07 V ±1.5 %) [V S56].
- LVCMOS33 outputs at VCCIO ≥ 3.02 V still exceed the 2.0 V VIH of the LVC inputs they drive [K].

**If EN_OK is late.** If EN_OK is released only after the A2000 reset has ended, the card stays disarmed and transparent until the next reset. This is a safe failure: the card is absent, nothing collides, and the chain is not blocked.

## 9. Gate G-STA: what the post-place-and-route analysis must cover (C-01)

| Item | Requirement |
|---|---|
| Tool, device | Lattice Diamond, LCMXO2-2000HC-**4**TG144C (and any grade or device actually bought). Script [../../hdl/syn/diamond_sta.tcl](../../hdl/syn/diamond_sta.tcl); constraints [../../hdl/syn/z2_top.lpf](../../hdl/syn/z2_top.lpf) |
| Paths | Every LPF MAXDELAY: /AS, A16–A23 → ZF_SLAVE_N; /AS, /BERR, A16–A23 → ZF_XRDY; /AS, /BERR, DOE, READ, /UDS, /LDS → ZF_DBUF_OE_N; /CFGINn → ZF_CFGOUT_N |
| Edges | Assertion **and** release of each output: both transitions of each input are timed |
| Maximum corner | Slow: worst process, minimum VCC/VCCIO (3.135 V), maximum junction temperature (85 °C commercial; 100 °C if the industrial grade is chosen). The report header must show the conditions |
| Minimum corner | Fast / hold analysis. Minimum delays of /AS → ZF_SLAVE_N and A16–A23 → ZF_SLAVE_N feed the hazard inequality ([sheet1-hazard-analysis.md](sheet1-hazard-analysis.md) §4.2) |
| Loading | FPGA outputs drive one LVC input (U104/U107/U105, ~5 pF [K TBV]) + ~2 pF of trace. Analyse at **10 pF**: either the Diamond output-load preference or a derating from the Lattice IBIS model (method TBV on the first run). The 7.24 ns data-sheet floor is at 0 pF |
| Temperature assumption | Inside a closed A2000 with the X4 running, ambient is unknown (R-09). Measure in Stage 6. If TJ > 85 °C is possible, use the industrial grade |
| Structure | Post-map netlist: each `z2_asgate*` is one LUT with /AS (/BERR) as controlling input |
| Pass | Every maximum ≤ 18 ns (or a re-budget keeping ≥ 3 ns margin to 35/50/60 ns). Minimum and maximum recorded; hazard S_req ≤ (M-7 setup − 3 ns) |
| Not acceptable | Pin assignment not final, or numbers from a tool other than Diamond. `nextpnr-machxo2` is experimental and may only be used for early exploration |

## 10. Status summary

| Budget | Status |
|---|---|
| Buffer and gate contributions (all parts) | **Verified** from datasheets |
| /SLAVEn 29.8 / 35 ns; XRDY 33.0 / 60 ns; release 33.2 ns | **Budgeted** with the 18 ns FPGA allocation (not proven) |
| FPGA share | **Open:** G-STA (Diamond not installed yet) |
| Hazard setup S_req | **Model worst case 11.0 ns** (tb_hazard E3); G-STA + M-7 |
| RMW turnaround (≥ 398 ns margin), direction guards, write capture | Designed and analysed. **Simulation passes; formal guard properties proven** (2026-11-18) |
| A2000 DOE / auto-DTACK behaviour in RMW | **Assumed**; M-3 and M-10 |
