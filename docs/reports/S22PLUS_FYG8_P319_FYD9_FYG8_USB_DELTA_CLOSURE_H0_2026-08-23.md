# S22+ FYG8 P3.19 FYD9-to-FYG8 USB delta closure H0

Status: `P319_FYD9_FYG8_USB_DELTA_CLOSURE_IMPLEMENTED_REVIEW_PENDING`.

This unit is host-only. It contacted no device, ADB, USB endpoint, Odin,
partition, A90, or S20+. It created no candidate, package, ready/run/approval
manifest, connected authority, recovery authority, or replay authority.

## Exact source boundary

The existing source-overlay auditor had already reconstructed the exact FYD9
base plus FYG8 overlay and reported `51 = 22 changed + 29 identical` members.
It did not classify the 22 changed regular files or state the FYG8-only USB
semantics. This follow-up leaves that execution-critical predecessor unchanged
and reads the same pinned archives directly:

| Input | Size | SHA-256 |
|---|---:|---|
| FYD9 `Kernel.tar.gz` | 566,244,738 | `86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf` |
| FYG8 delta | 1,421,025 | `23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a` |

The new auditor independently scanned all 166,037 FYD9 archive members,
normalized all 51 FYG8 overlay members, proved that every overlay member
replaces an existing FYD9 member, and verified all 22 changed regular files
against the already materialized P290 source tree.

The exact changed-file census is:

| Category | Files |
|---|---:|
| g0q DTS thermal thresholds | 11 |
| NFC/SNVM | 5 |
| USB notify | 2 |
| Venus media | 2 |
| DEFEX | 2 |
| **Total** | **22** |

There are no added members. The remaining 29 overlay members are directories
whose type and path are identical to the FYD9 base.

## All DTS revisions, not only r12

The 11 DTS revisions changed are `r01`, `r02`, and `r04` through `r12`.
Every revision has exactly the same bounded change: thirteen raw
`temperature` values move from `0x14c08` (85,000) to `0x13880` (80,000), with
zero other changed lines. No changed DTS line contains a USB, Max77705, Type-C,
PDIC, MUIC, DWC3, SSUSB, or EUD token.

Therefore r12 is not a unique USB-bearing delta. Its existing exact-target
binding remains the execution authority; the other ten revisions are now
censused for completeness and do not expand the target profile.

## The two FYG8 USB files

FYG8 changes exactly two USB source files, both in the Samsung notify layer:

| File | FYD9 | FYG8 | Exact unified diff |
|---|---|---|---|
| `usb_notify.c` | 96,378B / `f9b94f7e` | 96,602B / `cdb489a2` | 1,056B / `bd4cef5c`, +8/-1 |
| `usb_notify_sysfs.c` | 31,527B / `f3eb53ba` | 31,895B / `e538e784` | 1,484B / `24b438c5`, +27/-3 |

No FYG8 overlay member replaces DWC3, Type-C manager, Max77705 MUIC, or EUD
source.

### `reserve_state_check()`

The pre-existing wait has two release predicates:

1. `lock_state != USB_NOTIFY_INIT_STATE`; or
2. the reserved event becomes `NOTIFY_EVENT_VBUS`.

FYG8 adds a post-wait branch. If the VBUS predicate releases the wait while
the lock state is still initial, the source performs exactly:

- `first_restrict = true`;
- `set_notify_disable(..., NOTIFY_BLOCK_TYPE_HOST)`; and
- `skip_possible_usb = 1`.

The existing following condition then suppresses
`EXTERNAL_NOTIFY_POSSIBLE_USB`. The August 11 role-producer report described
the policy wait but did not name this FYG8 post-wait branch. The accurate
correction is not “bare PID1 waits forever”: reserved VBUS can release the
wait, after which FYG8 installs the HOST restriction and suppresses the
POSSIBLE_USB notification.

### `usb_sl_store()`

FYG8 also:

- admits only `USB_NOTIFY_LOCK_USB_RESTRICT`,
  `USB_NOTIFY_LOCK_USB_WORK`, and `USB_NOTIFY_UNLOCK` numeric values; and
- allows an existing `first_restrict` to be released by UNLOCK or USB_WORK
  without requiring the previous state to equal USB_RESTRICT.

This is the paired recovery behavior for the new automatic first restriction.

## What the delta does and does not prove

Both selected Waipio defconfig inputs set `USB_NOTIFY_LAYER=m` and
`USB_NOTIFIER=m`. Neither names
`CONFIG_DISABLE_LOCKSCREEN_USB_RESTRICTION`, and that bool has no Kconfig
default, so the audited source configuration does not disable the restriction
branch. This report does not promote that source result into a new claim about
uninspected shipped-machine-code reachability.

The exact downstream source keeps the critical boundaries separate:

- HOST and CLIENT are distinct disable-state bits;
- the new branch sets only `NOTIFY_BLOCK_TYPE_HOST`, whose transition emits
  `NOTIFY_EVENT_HOST_DISABLE`, clears the CLIENT bit, and sets the HOST bit;
- `EXTERNAL_NOTIFY_POSSIBLE_USB` maps to
  `MANAGER_NOTIFY_PDIC_DELAY_DONE`, so suppressing it withholds one
  alternate-mode readiness input; and
- DWC3 `mode_store()` places its CLIENT veto under
  `#ifdef CONFIG_USB_NOTIFIER`; the module value `m` defines the module-form
  macro rather than satisfying that plain `#ifdef`.

Consequently this exact FYG8 delta is relevant to HOST delivery and
alternate-mode readiness, but it **does not prove gadget silence** and does
not re-establish the connector-side MUX as the operational P3.19 frontier.
No indirect-effect absence is claimed.

## Existing Download positive control

The Download positive control was already present in the exact August 19
stock-choreography report. Its bound evidence distinguishes:

- normal boot: XBL `muic_init` writes `0x3f` `COM_OPEN`; and
- Download: ABL/Odin calls `MuicSetPath(1)`, writes `0x09` `COM_USB`, then
  enumerates.

Thus the missing item was the FYG8 notify-layer delta, not the Download-path
positive control. An adjacent-family public reset default is not required for
this conclusion because the exact FYG8 boot stages overwrite CONTROL1 before
the kernel path under discussion.

## Receipt and validation boundary

The final private no-clobber receipt is:

- `fyd9-fyg8-usb-delta-audit-20260823-03/result.json`;
- 24,861B;
- SHA-256 `3590ab4076df73762edc699dadcadf888b7f6a3e7cc0ab0072a01406a281e82c`;
- mode `0400`, link count 1.

The auditor is 35,966B with SHA-256
`d11ccaae3c5cffe7b195325028f53285ba9ae9ead897436910fb6e91fa8ff4a1`.
The 24,617B / `457d5fafa05d` `-01` and 24,666B / `244a85f78a77`
`-02` development receipts remain preserved. `-02` narrowed “observed effect”
to “source effect” and added private parent-chain validation; `-03` additionally
proves the HOST transition clears CLIENT and sets only HOST.

The receipt binds the two source archives, all 22 applied file bytes, the
eleven DTS diffs, the two exact USB diffs, seven downstream/config sources,
and the two predecessor reports. Mutation controls reject a changed reserve
hook, a changed DTS threshold, and a widened DWC3 client gate.

The new focused module adds 12 tests, so the mechanically discovered current
`test_s22plus_fyg8_p319*.py` population is 545 rather than the preceding 533.
Historical 532-test repin results remain historical measurements and are not
rewritten.

The fresh broad selection ran all 545 methods in 226.687 seconds: 544 passed,
zero failed, and one errored only because the already recorded external path
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` is unavailable.
That materialization input absence is separate from this delta closure.
The first broad pass also exposed one stale prose count: the behavioral
raw-first report still said 51 target-external names after the reviewed
request-cut successor had registered the dormant S20+ health source as member
52. Only that report table and its explanatory note were corrected; the
raw-first auditor, receipt, and S20+ bytes were not changed.

## Review and current frontier

This unit changes no candidate byte and does not alter the two remaining P3.19
integration blockers: `FRESH_BASELINE_MISSING` and four-key
`REQUALIFICATION_REQUIRED`. It corrects the completeness boundary around the
operational role-chain frontier; it does not create a new live experiment.

Independent changed-closure review is still required. Until then this report
and its ledger row are `IMPLEMENTED_REVIEW_PENDING`, not `PASS_GO`, and grant
no D0, D1, F1, recovery, replay, causal-result, candidate-success, device, or
live authority.
