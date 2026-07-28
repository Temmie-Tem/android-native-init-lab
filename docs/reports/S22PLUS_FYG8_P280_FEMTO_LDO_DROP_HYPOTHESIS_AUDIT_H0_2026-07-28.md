# S22+ FYG8 P2.80 Femto LDO-Drop Hypothesis Audit H0

Date: 2026-07-28 KST

## Verdict

`PASS_P280_FEMTO_LDO_DROP_HYPOTHESIS_AUDIT_HOST_ONLY`

The exact FYG8 source and stock module expose a coherent mechanism that can
produce P2.80's `0xb22` result. The mechanism is not yet live-proven:

1. initial DWC3 setup powers and initializes the femto HS PHY;
2. the no-cable runtime-suspend path may disable its clocks and regulators;
3. the runtime-resume path later enables only its clocks;
4. peripheral start marks the cable connected only after that resume; and
5. the DWC3 core can still clear `DEVCTRLHLT` while the HS electrical path
   remains unavailable.

This unit performed no device contact, build, image change, approval, transfer,
reboot, or flash.

| Claim | Result |
|---|---|
| femto disconnect-suspend disables clocks and regulator votes | **VERIFIED** |
| femto runtime resume restores regulator votes | **REJECTED** |
| the exact P2.80 run executed the regulator-off branch | **OPEN, STRONGLY SOURCE-SUPPORTED** |
| `msm_hsphy_init()` is called only once per boot | **REJECTED** |
| `msm_hsphy_enable_power(false)` return zero proves every rail physically disabled | **REJECTED** |
| current P2.80 role/bind tracing could have captured the initial drop | **REJECTED** |
| writing parent `power/control=on` at the current E3 role phase repairs an earlier drop | **REJECTED** |
| the P2.80 trace machinery can support an early versioned discriminator | **VERIFIED** |

## Exact Inputs

The audited source is the owned FYG8 OSRC extraction:

```text
/tmp/p280-postlive-phy-20260728/kernel_platform/msm-kernel/
```

Its durable input is:

```text
workspace/private/inputs/s22plus_kernel_source/
  SM-S906N_15_base_osrc/Kernel.tar.gz
```

The exact stock femto module is:

```text
/tmp/p280-postlive-modules-20260728/lib/modules/phy-msm-snps-hs.ko
sha256=22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94
```

It is unstripped and contains exact local text bodies:

```text
0000000000000d80 t msm_hsphy_enable_power
00000000000011f4 t msm_hsphy_init
00000000000019d4 t msm_hsphy_set_suspend
0000000000001ccc t msm_hsphy_notify_connect
```

The module runtime name is `phy_msm_snps_hs`, so a successor can use
module-qualified Kprobe targets instead of ambiguous global symbol lookup.

## Verified Femto Asymmetry

In `drivers/usb/phy/phy-msm-snps-hs.c`, `msm_hsphy_init()` calls
`msm_hsphy_enable_power(phy, true)`, enables clocks, resets the PHY, and
programs its analog and UTMI controls.

The disconnect branch of `msm_hsphy_set_suspend(..., 1)` takes the following
path when all of these are false:

- `cable_connected`;
- `PHY_HOST_MODE`;
- `dpdm_enable`; and
- `EUD_SPOOF_DISCONNECT`.

It then calls:

```c
msm_hsphy_enable_clocks(phy, false);
msm_hsphy_enable_power(phy, false);
```

The resume branch of `msm_hsphy_set_suspend(..., 0)` does only:

```c
msm_hsphy_enable_clocks(phy, true);
phy->suspended = false;
```

It contains no matching `msm_hsphy_enable_power(phy, true)`.
`msm_hsphy_notify_connect()` only sets `cable_connected=true`; it does not
restore regulator votes.

The exact module disassembly agrees with the source. It also establishes these
field offsets for a versioned fetch contract:

| Field | Offset |
|---|---:|
| `usb_phy.flags` | 16 |
| `clocks_enabled` | 484 |
| `power_enabled` | 485 |
| `suspended` | 486 |
| `cable_connected` | 487 |
| `dpdm_enable` | 488 |

## Initial Runtime-PM Ordering

`dwc3-msm-core.c` initializes the parent in low-power state, selects a
1000-millisecond autosuspend delay, enables autosuspend, registers the role
switch, and queues `dwc3_otg_sm_work()`.

The initial `DRD_STATE_UNDEFINED` work:

1. enables parent runtime PM;
2. gets a parent runtime-PM reference;
3. calls `dwc3_msm_core_init()`;
4. changes the state to idle; and
5. calls `pm_runtime_put_sync(mdwc->dev)` when ID is floating and
   `B_SESS_VLD` is absent.

The exact PM core matters here. `pm_runtime_put_sync()` enters `rpm_idle()`,
which invokes `rpm_suspend(..., RPM_AUTO)`. The autosuspend-expiration check
therefore still honors the configured delay and `last_busy`; it is not an
immediate synchronous suspend that bypasses the one-second policy.

If that timer expires before a cable producer or the PID1 role write changes
the state, parent runtime suspend calls
`usb_phy_set_suspend(mdwc->hs_phy, 1)`, reaching the femto disconnect branch.

P2.80 adds two supporting facts:

- its role phase could pass only after an exact initial `mode` read of
  `none`; and
- its generated runtime loads all 60 modules and completes the E2 gate loop
  before entering the E3 role phase.

The materialized module indexes are:

```text
55 phy-msm-snps-hs.ko
56 phy-msm-snps-eusb2.ko
57 qc_usb_audio.ko
58 dwc3-msm.ko
59 ucsi_glink.ko
```

This makes the one-second no-cable autosuspend ordering a strong explanation,
but not a retained observation. The exact live run did not record the
initial timer, suspend callback, branch conditions, or regulator helper.

## Why the Existing Trace Was Too Late

The P2.80 runtime arms Phase R tracing only inside `p280_phase_role()`, after:

- all 60 modules have loaded;
- all E2 gates have settled;
- configfs has mounted;
- the gadget and `ttyGS0` have been constructed; and
- the banner has been queued.

Any `msm_hsphy_init()`, initial `msm_hsphy_set_suspend(..., 1)`, or regulator
drop caused by `dwc3-msm.ko` insertion occurred before that window. Adding
femto event names only to the existing role event array would therefore miss
the proposed cause and could incorrectly report that it never happened.

## Corrections to the Strong Form of the Hypothesis

### PHY init is not globally one-shot

The parent helper `dwc3_msm_core_init()` calls `usb_phy_init(mdwc->hs_phy)`.
The child DWC3 `dwc3_core_init()` independently calls
`usb_phy_init(dwc->usb2_phy)`, and system-resume paths can call DWC3 core init
again. The parent `mdwc->dwc3` guard does not make the PHY callback globally
one-shot.

A successor parser must not require exactly one `msm_hsphy_init()` event.
It should recognize an ordered sequence while permitting the parent and child
initialization calls. This avoids another unstable-cardinality contract.

### Helper return zero is not analog proof

`msm_hsphy_enable_power(false)` overwrites `ret` while disabling several
regulators and changing loads and voltages. An earlier regulator failure can
be replaced by a later zero result. The helper then clears
`power_enabled` and returns the last result.

Consequently:

- helper entry with `on=0` proves the off path was attempted;
- return zero plus `power_enabled=0` proves the driver's software transition;
- neither alone proves every physical rail reached zero.

The first discriminator should name this result
`FEMTO_POWER_DROP_PATH_OBSERVED`, not `LDO_PHYSICALLY_OFF`.

### Other power-on call sites exist

The driver also powers the PHY for DPDM/charger detection, EUD preservation,
probe-time handling, and system-resume initialization. No such post-drop
repair is evidenced in P2.80's bare-PID1 runtime, but their existence means
the report must not claim that `msm_hsphy_init()` is the only source-level
power-on path.

## Why Late `power/control=on` Is Not a Repair

Writing `on` to the parent device's `power/control` calls
`pm_runtime_forbid()`. That increments the usage count and requests
`rpm_resume()`.

If the proposed regulator drop has already occurred, parent resume reaches
`usb_phy_set_suspend(..., 0)`, whose femto callback restores clocks only.
It does not re-run `msm_hsphy_init()` or restore regulator votes. A write at
the current E3 role phase is therefore too late to repair this mechanism.

An early write near module insertion might prevent the initial autosuspend,
but it is a race-sensitive intervention and would erase the causal event that
the next run needs to measure. Do not combine that mitigation with the first
discriminator. If the drop is proven, compare a deterministic early-role
ordering or an explicit kernel repair in a separate unit.

## Minimal Successor Discriminator

Reuse the P2.80 tracefs lifecycle, ownership cleanup, bounded buffers, and
fail-soft diagnostic rules. Add no second generic tracing framework.

Use two versioned windows:

### Window I: initialization and first autosuspend

Arm after generated modules `0..57` are loaded and immediately before loading
module `58`, `dwc3-msm.ko`. Observe module-qualified events for:

1. `msm_hsphy_init` entry and return;
2. `msm_hsphy_set_suspend` entry, including `suspend` and pre-state fields;
3. `msm_hsphy_enable_power` entry and return, including `on`; and
4. `msm_hsphy_notify_connect` entry.

Keep the window open through DWC3-MSM insertion and a separately justified
bounded initial-settle interval. Derive any post-call field fetch from exact
module disassembly; do not assume a return probe still exposes the entry
pointer.

### Window R: existing peripheral start

Extend the existing role window to determine whether it observes:

1. parent resume;
2. `msm_hsphy_set_suspend(..., 0)`;
3. any intervening `msm_hsphy_enable_power(..., 1)`; and
4. `msm_hsphy_notify_connect()`.

Retain the final exact UDC `current_speed` class that P2.80 previously read and
discarded.

The parser should classify ordered subsequences, not global singleton counts:

| Observation | Meaning |
|---|---|
| no disconnect-suspend/off path | the LDO-drop hypothesis is not supported |
| off path followed by a later power-on before connect | another repair path exists |
| off attempt, software power-disabled state, then resume/connect with no power-on | strong causal match for `0xb22` |
| missing or unclean trace ownership | instrumentation indeterminate |

The last row remains a software/control-path proof. It does not claim direct
analog rail measurement.

## Build and Authority Boundary

The successor changes the source-bound event descriptor, runtime
orchestration, parser, and retained classification contract. Under the current
F1 identity model it requires a new versioned candidate and fresh Full-LTO A/B
qualification before any future D0 or F1. Treating it as an unbound
userspace-only patch would bypass the existing candidate identity contract.

No web search is needed for this decision. Exact owned FYG8 source, exact
stock-module disassembly, generated candidate runtime, and the closed P2.80
result are stronger and target-specific.

## Next

Design the two-window versioned contract before implementation. Its first
static gate must prove:

- exact source and module identities;
- module-qualified body symbols rather than CFI thunks;
- the insertion hook is before generated module index 58;
- repeated init calls are accepted;
- event order and field offsets are derived from the exact module; and
- P2.80's historical source and artifacts remain byte-identical.

This report authorizes no build, image generation, device action, or live run.
