# Sheet 1 / HDL: /SLAVEn decode hazard analysis (concern C-02)

**Status:** revision B, 2026-11-18. The analysis below is complete at the structural and model level. **Two numbers are still missing:**
- the FPGA minimum and maximum path delays (gate **G-STA**, Lattice Diamond);
- the address-to-/AS setup actually present at an A2000 slot (measurement **M-7**).

The checks that produce evidence are written (§7) but have **not yet been executed**, because the simulator toolchain has not been run on this machine. Nothing here is claimed as proven until those runs and the gate are complete.

Evidence tags follow [../sources.md](../sources.md).

## 1. Question

Can /SLAVEn (or XRDY, or the data-buffer enable) assert for an address that does not belong to this card? The three triggers considered are:
- address lines that change late;
- propagation skew between address bits and /AS;
- address transitions close to /AS assertion.

A false /SLAVEn coinciding with another board's /SLAVEn is a collision. Buster detects it and asserts /BERR [V S50, S10].

## 2. Signal chain

```text
slot A23..A16 ─ U101/U102 (1.1–4.1 ns) ─ FPGA pin ─ decode LUT cone (sel_k) ─┐
slot /AS ────── U102      (1.1–4.1 ns) ─ FPGA pin ──────────────────────────── z2_asgate2 (1 LUT) ─ pin ─ U104 ─ R117 ─ slot /SLAVEn
```

- **Buffers.** A16 is on U101; A17–A23 and /AS are on U102. The full datasheet range is applied to every channel: tpd 1.1–4.1 ns, SN74LVC16244A at 3.3 V ±0.3 V, −40 to 85 °C [V S45]. The 1 ns intra-device output skew is not relied on.
- **Decode.** `sel_k = match_en & (A23..A19 == cmp[23:19]) & (~care_lo | A18..A16 == cmp[18:16])` ([../../hdl/rtl/z2_decode.v](../../hdl/rtl/z2_decode.v)). `match_en`, `cmp` and `care_lo` are registers.

## 3. Structural properties (enforced in the RTL, checked on the netlist)

| ID | Property | How it is enforced | How it is checked |
|---|---|---|---|
| S1 | /AS (and /BERR) enter **only** the final gate: `slave_n = as_n \| ~sel_k`, and `xrdy`, `dbuf_oe_n = as_n \| ~berr_n \| ~term` | Final gates are separate modules with `keep_hierarchy` / `syn_hier "hard"`. The terms are `keep` / `syn_keep` nets | [`check_decode_structure.py`](../../hdl/syn/check_decode_structure.py): `as_n` and `berr_n` feed only the three gate instances |
| S2 | With as_n = 1 (or berr_n = 0), the final LUT outputs 1 for **every** term value | Function of the gate | Same script: every truth-table entry with as_n = 1 is checked |
| S3 | `sel_k` depends only on A23..A16 and registered state. **That state is frozen while a bus cycle is in progress** | `z2_core` updates `match_en/cmp/care_lo` only when the FSM is idle with /AS negated (synchronised) | Formal property F12 ([../../hdl/rtl/z2_core.v](../../hdl/rtl/z2_core.v)) |
| S4 | /CFGINn no longer enters the combinational decode | Sampled into `match_en` between cycles (rev B) | Formal F12; tb_chain scenario S1/S9 |
| S5 | A decode glitch can never enable the data drivers | Read drive needs `oe_rd_q`, a register set by the FSM ≥ 3 clocks after it sampled `sel_c` as stable; DIR is registered | Formal F1/F2; tb_z2 checker C2 |

**Why S4 matters.** In rev A, `/CFGINn` was used combinationally. An upstream board that asserts its /CFGOUTn **before** its own configuring write ends would assert this card's /SLAVEn at $E8004x during that write. The result would be a collision.

## 4. Consequences

### 4.1 While /AS is negated: no assertion, independent of timing

By S1/S2, the final gate holds /SLAVEn, XRDY and the buffer enable inactive for any activity of the address bits or decode cone. This holds while as_n = 1 is present at the gate input.

**Assumption [K, TBV].** A LUT does not glitch when one input changes and the selected output value stays the same. Here the as_n = 1 half of the truth table is all ones. This is a property of mux-based LUTs. It is not stated in the MachXO2 data sheet [S49].

It is tested by:
- the netlist structure check;
- tb_hazard E1, with random LUT and buffer delays;
- an optional post-route timing simulation;
- the scope measurements M-6/M-7.

### 4.2 While /AS is asserted: a setup requirement

/SLAVEn = ~sel_k, so `sel_k` must have settled before as_n reaches the final gate. The slot-level requirements are:

```text
setup:  t_su,slot >= (t_bufA,max - t_bufAS,min) + (t_sel,max - t_AS->gate,min)
hold:   t_h,slot  >= (t_bufAS,max + t_AS->gate,max) - (t_bufA,min + t_sel,min)
```

| Term | Value | Source |
|---|---|---|
| t_bufA,max − t_bufAS,min | 4.1 − 1.1 = 3.0 ns, plus trace mismatch ±0.5 ns = **3.5 ns** | [V S45], [E] |
| t_sel,max: FPGA address pin → final-gate input | ≈ 7 ns: input buffer plus 2–3 LUT levels with routing | [E] **G-STA** |
| t_AS→gate,min: /AS pin → final-gate input | ≈ 1.5–2 ns | [E] **G-STA** (minimum / hold analysis) |
| **Required slot setup** | **≈ 8.5 ns** | [E], to be recomputed from STA |
| Available at the CPU | Address valid ≥ **30 ns** before /AS (#11, MC68000 8 MHz part) | [V S57] |
| Available at the slot | 30 ns minus the unknown A2000 address-vs-/AS buffer skew | **M-7** |
| Hold available at the CPU | Address valid ≥ **40 ns** after /AS negation (#13) | [V S57] |

The A2000 buffers the address and /AS on separate paths. If the slot setup is ≥ 15 ns, the estimated margin is ≈ 6 ns. The hold requirement, ≈ 10 ns by the same estimate, is far inside the 40 ns guarantee.

### 4.3 If the inequality were violated

- **/SLAVEn.** A pulse up to (required − actual setup) wide could appear. Buster would see it only if it overlaps another board's /SLAVEn, which would be a collision and /BERR.
- **XRDY.** It could pulse low for the same time. It is wired-OR, and the motherboard samples it no earlier than about S4 (≈ 70 ns after /AS), so the pulse would be harmless.
- **Data buffers.** They cannot be enabled (S5).
- **FSM.** It samples `sel_c` 40–80 ns after /AS, long after any glitch.
  - If a protocol violation makes `sel_c` change during /AS, the FSM never holds XRDY for a cycle it has ignored (`hold_q` is cleared in ST_IGNORE).
  - The bus therefore cannot hang.

## 5. Transitions near /AS: what the testbenches do

| Test | Model | Expected |
|---|---|---|
| tb_z2 T6 (RTL, board models) | Previous cycle often selected. Next address unselected, differing in 1–3 high bits. Slot setup 20/10/5 ns plus 0–15 ns per-bit spread. U101/U102 skew from the datasheet range | **Pass/fail:** no false /SLAVEn, /SLAVEn ≤ 35 ns for selected cycles, no glitch |
| tb_z2 T6 characterisation | Setup 2/0/−5 ns, no spread | Counts reported, not failed. Shows the dependency on setup at RTL level (buffer skew only) |
| tb_hazard E1 (gate level) | Yosys LUT netlist. Every LUT has a random 0.3–2.5 ns transport delay [A]. Buffers 1.4–4.9 ns. Address wandering through the selected code with /AS negated | **Pass/fail:** zero assertions of /SLAVEn, XRDY or buffer enable |
| tb_hazard E2 (gate level) | /AS asserted s ns after the last address bit settles; s = −8…+14 ns | Table of false /SLAVEn rate against s. Gives the model's required setup, to compare with §4.2 |

Transport delays preserve every glitch, so the model is pessimistic. The LUT and routing delay range is an assumption [A] until G-STA provides real minimum and maximum values.

## 6. Options if STA shows too little margin (address predecode)

| # | Option | Effect | Cost / risk |
|---|---|---|---|
| O1 | Pin and placement: A16–A23 and /AS in one bank next to the decode. Diamond UGROUP / LOCATE for the decode LUTs | Cuts t_sel,max and the skew | Free; done at sheet 2 |
| O2 | Faster speed grade (−5/−6), same footprint | All delays shorter | Price, availability (R-22) |
| O3 | **Writable-LUT predecode.** Two 16×1 distributed-RAM LUTs (MachXO2 PFU RAM, asynchronous read) indexed by A23..A20 and A19..A16, loaded between cycles with "this nibble matches". sel = hit_hi & hit_lo, one decode level | Address → /SLAVEn in 2 LUT levels | About 2 PFUs. Each table rewrite (16 writes) must happen with the window disabled; only at configuration and reset events |
| O4 | Delay the /AS input to the final gate to balance the paths | Lowers the required setup | Spends /SLAVEn margin; fragile across place-and-route. **Not recommended** |
| O5 | Registered /SLAVEn on a ≥ 133 MHz PLL clock | No hazard at all | About 31 ns of the 35 ns budget used. **Not recommended** |

**Decision.** Keep the current structure. Apply O1 at sheet 2. Use O3 or O2 only if G-STA leaves < 3 ns margin in either inequality.

## 7. Evidence and status

| Item | Status |
|---|---|
| RTL structure S1–S5 ([../../hdl/rtl](../../hdl/rtl)) | Written |
| `check_decode_structure.py` on the Yosys netlist | Written, **not yet run** |
| tb_z2 T6, tb_hazard E1/E2 | Written, **not yet run** |
| Formal F4, F12 (SymbiYosys) | Written, **not yet run** |
| Diamond minimum/maximum path delays, post-map structure check (G-STA) | **Pending:** needs Lattice Diamond and its free licence |
| M-7 slot address setup, scope | **Pending:** hardware, after gate G-PSU |

## 8. Result

- **By construction** (pending the tool runs above): /SLAVEn, XRDY and the data-buffer enable cannot assert while /AS is negated at the FPGA. The data buffers cannot be enabled by any decode transient.
- **Conditionally:** for a stable address, /SLAVEn asserts only for a selected address **provided the slot address setup is at least S_req**, estimated at ≈ 8.5 ns. S_req becomes a number only with G-STA; the available setup becomes a number only with M-7.
- **Not yet demonstrated:**
  - the numeric S_req;
  - the A2000 setup;
  - LUT single-input glitch freedom on MachXO2 silicon [K].

C-02 therefore stays **HIGH / open** until G-STA and M-7 close it.
