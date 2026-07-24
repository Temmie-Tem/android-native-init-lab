# S22+ FYG8 P2.58 UDC frontier focused analysis (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P258_UDC_GATE_CONTRACT_BUG_H0`
Live authority: none

## Verdict

P2.57 made real forward progress through the SSUSB parent and built-in DWC3
child. Its stage `0x87` result does **not** prove that
`/sys/class/udc/a600000.dwc3` was absent.

The exact runtime did not test exact UDC membership. It required the entire
UDC class to contain one and only one non-dot entry:

```c
return entries == 1U && exact == 1U ? 0 : -ENODEV;
```

That predicate contradicts the FYG8 topology already measured under stock:

```text
/sys/class/udc/a600000.dwc3
/sys/class/udc/dummy_udc.0
```

It also contradicts the exact candidate configuration,
`CONFIG_USB_DUMMY_HCD=y`. The built-in dummy HCD defaults to one emulated
controller, no stock boot command line or bootconfig override disables it, and
its UDC is initialized before PID 1.

The expected successful topology therefore has `entries=2, exact=1`, which
the P2.57 predicate rejects. Stage `0x87 detail=110` means only that the
singleton predicate did not become true before its observation ended. It
cannot distinguish:

- only `dummy_udc.0`;
- both `dummy_udc.0` and `a600000.dwc3`; or
- another non-singleton class state.

The leading root cause is a host-deterministic observation-contract bug, not
an established DWC3 gadget-publication failure.

P2.57 also has a secondary timing ambiguity: DWC3 role work is asynchronous
and the shared deadline can leave the UDC check little or no dwell. The next
bounded contract should fix both defects in one host-reviewed candidate:
exact-target membership regardless of unrelated UDCs, plus one dedicated
five-second dwell after DWC3 bind. It must not add modules, force a role,
write configfs, or broaden into ACM.

## Scope And Evidence

This unit was host-only and read-only. It inspected:

- the exact P2.57 retained result and materialized runtime;
- the exact candidate `.config`;
- stock FYG8 UDC topology reports and the stock topology collector;
- stock command line and vendor bootconfig captures;
- source-matched FYG8 DWC3, UDC-core, and dummy-HCD control flow;
- P2.40/P2.41 design, implementation, and static checker; and
- Android common DWC3 and dummy-HCD source as primary cross-checks.

No source, kernel, image, manifest, device binding, or live authorization was
created.

## Exact Predicate Reconstruction

`p241_check_udc()` enumerates every non-dot directory entry in
`/sys/class/udc`, increments `exact` for `a600000.dwc3`, and returns success
only for `entries == 1 && exact == 1`.

Its truth table is:

| UDC class contents | `entries` | `exact` | P2.57 result | Correct target-membership result |
|---|---:|---:|---|---|
| empty | 0 | 0 | fail | fail |
| `dummy_udc.0` only | 1 | 0 | fail | fail |
| `a600000.dwc3` only | 1 | 1 | pass | pass |
| dummy plus `a600000.dwc3` | 2 | 1 | **fail** | **pass** |
| target plus any unrelated UDC | >1 | 1 | **fail** | **pass** |

The gate conflates exact target identity with global class cardinality. Global
cardinality is neither required for later configfs binding nor stable as a
generic UDC invariant.

## Why `dummy_udc.0` Is Expected

The exact candidate configuration contains:

```text
CONFIG_USB_GADGET=y
CONFIG_USB_DWC3=y
CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_DUMMY_HCD=y
```

The dummy-HCD source defaults its controller count to one and registers the
dummy UDC during built-in driver initialization. The FYG8 boot image has an
empty boot-header command line, and the vendor bootconfig and retained stock
command-line captures contain no `dummy_hcd`, `dummy_udc`, `nousb`, or
`usbcore.nousb` override.

Independent stock reports already record both class members and explicitly
warn to bind the real DWC3 UDC, never `dummy_udc.0`. Bare PID 1 starts after
built-in initcalls, so removing Android userspace does not itself suppress
dummy-HCD initialization.

This does not prove that dummy-HCD could never suffer an unrelated kernel
initialization failure. It does prove that the P2.57 success condition assumes
the opposite of the compiled default and observed stock topology.

## What P2.57 Still Proves

The retained sequence remains valid through:

```text
all 60 exact module insertions
all preceding gates
SSUSB parent bind
DWC3 child bind
```

Those stages are independent of the broken UDC cardinality predicate. The
formal F1 verdict also remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, because terminal success was not
accepted and rollback/final health were required.

What must be retired is only the interpretation:

```text
RETIRED: detail 110 proves a600000.dwc3 was absent
VALID:   detail 110 proves the P2.57 UDC predicate never passed
```

No conclusion about role-worker completion, gadget-init return, or real UDC
publication can be derived from this run.

## Secondary Async Measurement Defect

Exact FYG8 source still establishes a real later boundary:

```text
dwc3_probe()
  -> dwc3_setup_role_switch()
  -> dwc3_set_mode(DEVICE)
       -> queue_work(system_freezable_wq, drd_work)
  -> probe returns; DWC3 bind becomes visible

__dwc3_set_mode()
  -> PM/resets/PHY setup
  -> dwc3_gadget_init()
  -> usb_add_gadget()
  -> UDC class entry
```

The P2.57 runtime uses one global 20-second gate deadline. If SSUSB appears
during its extra classifier grace, `post_grace_drain` checks downstream gates
without another sleep. Even in the ordinary path, a late DWC3 bind receives
only the remaining global budget.

This timing defect cannot explain the retained result until the predicate is
corrected, because the expected two-UDC state fails immediately and forever.
It should nevertheless be fixed in the same versioned contract to avoid
spending another Full-LTO/F1 cycle on a known ambiguity.

## Why Static Validation Missed It

The P2.41 checker verifies that the runtime contains:

```text
p241_check_udc
/sys/class/udc
a600000.dwc3
```

It compiles and links the runtime and checks forbidden operations, but it does
not execute the directory predicate against topology fixtures. The design and
implementation reports repeated the same singleton assumption, while earlier
stock reports already contained the contradictory two-entry observation.
The unchanged checker was rerun during P2.58 and still returned
`PASS_P241_E2_SOURCE_IMPLEMENTATION_HOST_ONLY`, confirming that its current
contract cannot detect this semantic error.

The missing test class was semantic, not syntactic:

```text
dummy only                         -> fail
real only                          -> pass
dummy + real                       -> pass
real + unrelated controller       -> pass
missing/malformed/read error       -> fail closed
```

## Next Minimal Design

P2.58A should replace the UDC predicate and repair its dwell in one bounded
unit:

1. Enumerate `/sys/class/udc` with the existing bounded `getdents64` parser.
2. Require exactly one entry named `a600000.dwc3`.
3. Allow unrelated, valid UDC entries, including `dummy_udc.0`.
4. Validate the exact target path with
   `newfstatat(..., AT_SYMLINK_NOFOLLOW)` and a bounded `readlinkat`, requiring
   target basename `a600000.dwc3`.
5. Treat malformed dirents, duplicate exact matches, read errors, and identity
   mismatch as fail-closed errors.
6. After the DWC3 bind gate first succeeds, start one fresh five-second
   `CLOCK_MONOTONIC` UDC deadline at the existing maximum 100 ms cadence.
7. Keep earlier-gate regression checks active and preserve the exact
   60-module/no-write plan.
8. Add host topology fixtures for all rows in the semantic matrix above.

This is one correction to one observation boundary. It does not justify role
forcing, configfs writes, the Samsung notifier chain, debugfs reads, ACM, or
new modules.

If the corrected exact-membership gate still times out for a dedicated five
seconds, only then instrument:

```text
__dwc3_set_mode entry
desired/current role
pm_runtime_get_sync return
dwc3_core_soft_reset return
dwc3_gadget_init return
```

## Hypothesis Ledger

| Hypothesis | Status after P2.58 |
|---|---|
| P2.57 proved the real DWC3 UDC absent | `RULED_OUT` |
| P2.57 UDC predicate conflicts with stock/candidate topology | `CONFIRMED` |
| `dummy_udc.0` is expected in this candidate | `STRONGLY_VERIFIED` |
| DWC3 core bind completed | `LIVE_VERIFIED` |
| DWC3 role/gadget work completed | `UNRESOLVED` |
| Real DWC3 UDC was published during P2.57 | `UNRESOLVED` |
| P2.57 granted a dedicated UDC timeout | `RULED_OUT` |
| Full Samsung role policy is now required | `NOT_ESTABLISHED` |

## Primary Cross-Checks

- [Android common dummy-HCD source](https://android.googlesource.com/kernel/common/+/77a829804e5c5723bcc86a50febd4179aea39c98/drivers/usb/gadget/dummy_hcd.c)
- [Android common DWC3 DRD source](https://android.googlesource.com/kernel/common/+/64d83f06774668081258bd7f3241267239bb9ab2/drivers/usb/dwc3/drd.c)
- [Android common DWC3 core source](https://android.googlesource.com/kernel/common/+/5bad7993b0ff764e1ff37d00e370c0ed85661ea3/drivers/usb/dwc3/core.c)
- [Android common UDC core source](https://android.googlesource.com/kernel/common/+/4664fb427c8fd0080f40109f5e2b2090a6fb0c84/drivers/usb/gadget/udc/core.c)
- [Linux USB gadget documentation](https://docs.kernel.org/next/driver-api/usb/gadget.html)
