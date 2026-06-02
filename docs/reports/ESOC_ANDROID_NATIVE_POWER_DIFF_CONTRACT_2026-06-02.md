# Live contract — Android-good vs native power/clock/sequence diff at modem-powerup window (2026-06-02)

**Handoff for the loop.** Follows `v1657-mdm2ap-silent-natural-path` (the clean
natural-path silence is now confirmed: PON fired low→high, GPIO135 asserted,
GPIO142/errfatal IRQ stayed 0). This contract pins the ONE next gate. It is the
last AP-side read-only check before any write is justified. Trigger, measurement,
labels, and hard stops are fixed here; the loop owns the mechanical cycles only.

## Why this, why now
Host-side static/config layers are CLOSED at parity (bootloader, eSoC provider
source, DTB — see `ESOC_PON_SOURCE_ANALYSIS`, `ESOC_DTB_PARITY`). The natural path
is confirmed silent (V1657). The XBL artifact track (V1643–V1656) was read-only
and reached a dead-end exactly as forecast: it found SDX/PON/PMIC context tokens
but **cannot identify a concrete register/GPIO/rail owner** (V1655 limit). The
rail inventory (V1641) lists the SDX50M main rail as **"not identified on disk —
identify owner before write."**

So a write gate has NO concrete target yet. Before any write, close the one
remaining unmeasured AP-side dimension: **does Android enable a power/clock
resource, or run a subsystem-bring-up sequence, that native omits in the
powerup window?**

## The experiment
Capture the SAME observables on BOTH sides at the SAME window
(`__subsystem_get(esoc0)` → through the Android modem-PON window, ≥ several
seconds past `mdm_subsys_powerup`), then host-only diff.

- **Android-good side**: reuse the proven rollbackable Magisk `post-fs-data`
  handoff (V1521 / V1555 / V1521 engine), read-only sampler, then restore
  `stage3/boot_linux_v724.img` and verify selftest `fail=0`.
- **Native side**: reuse the V1657 natural-path PM-first route (no forced RC1, no
  spoof), same observables, same window.

### Measure (both sides, same window)
1. **`regulator_summary` full** — every rail's enable state + use_count. The
   target: rails ON/used in Android that are OFF/zero/absent in native.
2. **Targeted clocks only** for pcie1 / refclk / modem-related — do NOT read full
   `clk_summary` in the critical window (V1514 proved it overruns timing). Use
   named-clock reads.
3. **Subsystem sequence** — `subsys0`(mss/internal modem) vs `subsys9`(esoc0)
   state/order: does Android bring up another subsystem or glink/SMP2P channel
   BEFORE esoc0 that native skips.
4. GPIO135/142 + msm_pcie_wake / mdm status / errfatal IRQ deltas (already have).

## Labels (fixed — one run per side sets them)
- `power-vote-gap`: a rail/clock is enabled in Android but not native in the
  window ⇒ that is the concrete write-target candidate ⇒ STOP and hand back for a
  SEPARATELY user-authorized bounded targeted write gate. Do NOT write here.
- `sequence-gap`: power/clock parity but Android brings up something before esoc0
  that native omits ⇒ route-fix candidate (no write) ⇒ hand back.
- `full-power-parity-hardware-wall`: rails + clocks + sequence all match, yet
  Android's modem answers MDM2AP and native's does not ⇒ the cause is below AP
  control (SDX50M's own modem-side PMIC/PON, NOT in the AP regulator tree) ⇒
  declare the hardware wall, STOP, do NOT enter a write gate. Wi-Fi remains
  Android-handoff-only on this route.

Transport loss or failed rollback = FAIL, not a result.

## Honest scope limit (state it in the report)
The SDX50M's own main rail is NOT in the AP regulator tree (DTS mdm3 has no
modem regulator-supply; provider has zero regulator code). If the true blocker is
that modem-side rail being off, this diff CANNOT see it and will read
`full-power-parity-hardware-wall`. The diff can only find/rule-out **AP-side**
resources (PCIe/refclk/level-shifter rails, clocks, subsystem sequencing). Both
outcomes are decision-useful: a found gap gives a real target; parity promotes
"hardware wall" from suspicion to proof.

## Discipline (do not repeat V1370–V1559)
- ONE Android-good capture + ONE native capture + ONE host diff sets the label.
  Do NOT spin window/timing variants.
- `full-power-parity` is a terminal PASS classification — STOP, do not loop.
- No autonomous write gate from any label. `power-vote-gap` → hand back to the
  user for explicit approval of a targeted bounded write.

## Hard stops (unchanged)
Read-only both sides. No regulator/PMIC/GPIO/GDSC writes, no forced RC1/case
writes, no fake-ONLINE/system-info spoof, no eSoC notify/`BOOT_DONE`, no global
PCI rescan, no platform bind/unbind, no Wi-Fi HAL/scan/connect, no credentials,
no DHCP/routes, no external ping. Only the approved Android-handoff↔v724 and
test-boot↔v724 rollbacks. sda29 read-only.

## Refs
`ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md` (prior gate),
`ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md`, `ESOC_DTB_PARITY_2026-06-02.md`;
V1657 (mdm2ap-silent-natural-path), V1641 (rail inventory, owner unidentified),
V1655/V1656 (XBL dead-end), V1521/V1555 (Android post-fs-data handoff engine),
V1552 (tracefs regulator/irq observer), V1306/V1540 (pcie1 GDSC/vreg context),
V1514 (clk_summary timing overrun caution).
