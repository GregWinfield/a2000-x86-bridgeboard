# A2000 PSU measurement record (gate G-PSU, requirement ER-5)

**Rule:** no powered bridgeboard prototype may be installed in an A2000 until this record is completed for **that** machine and reviewed. Procedure: [01-architecture-review.md](../01-architecture-review.md) §8.6. Keep one completed copy per machine, e.g. `docs/test/records/psu-<machine-id>-<date>.md`.

## 1. Machine and PSU identification

| Item | Value |
|---|---|
| Machine ID / owner reference | |
| A2000 model and board revision | |
| PSU make / model / part no. (label photo attached?) | |
| Label ratings: +5 V / +12 V / −5 V / −12 V / total W | |
| Original or replacement PSU (ATX adapter, new build, …) | |
| Capacitor service history | |
| Installed drives (type, count) and expansion cards (slot, model) | |
| Spare 4-pin Molex available (connector condition) | |

**Stop and review** if the +12 V label rating is below 5 A, if no spare Molex exists, or if the PSU shows any damage or odour.

## 2. Instruments

| Instrument | Model | Calibration / notes |
|---|---|---|
| DMM | | |
| Oscilloscope (≥ 20 MHz bandwidth limit for ripple) | | |
| Electronic load, or 4.7 Ω ≥ 50 W resistor (12 V ≈ 2.55 A) | | |

## 3. Baseline (normal configuration, no dummy load)

| Condition | +5 V (V) | +12 V (V) | Notes |
|---|---|---|---|
| Idle at Workbench | | | |
| Hard-disk spin-up (cold boot) | | | Record the minimum |
| Floppy access | | | |
| Heavy disk activity | | | |

## 4. Static load test: 2.5 A on +12 V at a spare Molex, 30 minutes, case closed

| Time (min) | +5 V (V) | +12 V (V) | 12 V ripple (mV p-p) | 5 V ripple (mV p-p) | PSU exhaust temp (°C) |
|---|---|---|---|---|---|
| 0 | | | | | |
| 10 | | | | | |
| 30 | | | | | |

**Pass criteria (provisional [A]):**
- +12 V between 11.4 and 12.6 V;
- +5 V between 4.75 and 5.25 V, including during disk spin-up under load;
- ripple ≤ 120 mV p-p on 12 V and ≤ 50 mV p-p on 5 V (ATX-style guideline [K]);
- no instability, reset or odour.

## 5. Step load test (2.5 A on/off, ≥ 20 cycles)

| Observation | Result |
|---|---|
| Worst +12 V droop (V, duration) | |
| Worst +5 V disturbance (V) | |
| Any Amiga reset, crash or video disturbance? | |

## 6. Result

| | |
|---|---|
| Pass / Fail / Conditional | |
| Conditions or limits (e.g. reduced SBC current limit, no 5.25" HDD) | |
| Measured by / date | |
| Reviewed by / date | |
