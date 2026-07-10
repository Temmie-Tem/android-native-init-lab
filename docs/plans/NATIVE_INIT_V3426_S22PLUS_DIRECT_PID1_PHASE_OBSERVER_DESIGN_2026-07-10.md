# V3426 S22+ Direct-PID1 Phase Observer Design

## Decision

`HOST DESIGN GO; NO LIVE; OBSERVER FIRST; TRANSITION NOT SELECTED`.

The next S22+ discriminator is not another USB candidate. It is an observer-only
stage that proves direct-PID1 execution and current-session retained-ring capture
without depending on ACM enumeration. A later USB stage is forbidden until this
observer has crossed a separately selected session transition and its exact marker
is recovered from stock/Magisk `/proc/last_kmsg`.

This unit is host-only. It creates no candidate source, boot image, AP, live
helper, flash exception, reset plan, or device action.

## Independent Review

Claude Opus reviewed the architecture twice at high effort. The first verdict was
`GO-WITH-MUST-FIX`; the second was `GO` for this host-only unit and `NO-LIVE` for
any candidate. The accepted corrections are:

1. Prove `/dev/kmsg` write-to-hook return ordering from exact source.
2. Add a pre-stimulus fresh-open `/proc/ap_klog` negative control.
3. Re-read both PRECHECK and FINAL from fresh `ap_klog` snapshots.
4. Bind every marker to run, module, contract, phase, sequence, and context.
5. Use self-delimiting length+CRC frames and reject malformed current-run data.
6. Order phases by embedded sequence, not circular-buffer byte position.
7. Treat PRECHECK eviction before FINAL confirmation as deterministic failure.
8. Permit inventoried historical foreign-run frames but never let them satisfy
   the current run.
9. Keep all transition classes `UNVERIFIABLE` until one is separately selected.

## Source-Proved Channel

The exact FYG8 `sec_log_buf.ko` is the capture owner:

```text
size=76688
sha256=b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61
vermagic=5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 SMP preempt mod_unload modversions aarch64
modules.load position=2
hard dependencies=none
soft dependencies=none
DT compatible=samsung,kernel_log_buf
stock bind=8.samsung,kernel_log_buf
```

The official source establishes this probe order:

```text
parse DT -> map/prepare reserved ring
  -> copy pre-probe ring into last_kmsg snapshot
  -> create /proc/last_kmsg
  -> copy early printk into current ring
  -> register strategy-3 android_vh_logbuf hooks
  -> create /proc/ap_klog
  -> probe epilog
```

`/proc/ap_klog` allocates a new buffer on open and copies the current reserved
ring into it. Its release path frees that snapshot when the refcount reaches
zero. `/proc/last_kmsg` is different: it exposes the pre-probe copy and must not
be used as same-session capture evidence.

The exact FYG8 printk source also closes the synchrony question:

```text
/dev/kmsg write
  -> devkmsg_emit
  -> vprintk_emit / vprintk_store / log_store
  -> commit printk record
  -> trace_android_vh_logbuf
  -> sec_log_buf callback writes current reserved ring
  -> return to /dev/kmsg writer
```

Therefore one fresh `ap_klog` open after the marker write returns is a causal
capture test. Acceptance retries are not allowed.

## Stage A Gates

| Gate | Requirement | Evidence class |
|---|---|---|
| G0 | Host pins run id, module, contract, contexts, and expected frames | host identity |
| G1 | Only required volatile filesystems are ready | environment |
| G2 | Exact module hash, size, vermagic, and kernel identity | identity |
| G3 | Load only `sec_log_buf.ko` | load |
| G4 | EOF-complete `/proc/modules`, exact runtime name, `Live` | registration |
| G5 | Exact platform driver/device bind | bind |
| G6 | Both proc nodes exist | probe completion |
| G7 | Fresh-open `ap_klog` contains no current-run marker | negative control |
| G8 | Emit PRECHECK once | capture stimulus |
| G9 | Fresh-open `ap_klog`: exactly one valid PRECHECK | current capture |
| G10 | Emit FINAL once, only after G9 PASS | retention stimulus |
| G11 | Fresh-open `ap_klog`: exactly one PRECHECK and FINAL | current-ring commit |

G11 is the end of Stage A. It proves current-session capture and that FINAL was
present in the current reserved ring. It does not prove any reset preservation.

## Marker Contract

The binary-safe ASCII frame is:

```text
[[S22PO1|LLLL|run=<32hex>;phase=<PRECHECK|FINAL>;seq=<8hex>;module=<64hex>;contract=<64hex>;context=<64hex>|crc=<8hex>]]
```

`LLLL` is the four-hex-digit payload byte count. CRC32 covers the canonical
payload only. The parser resynchronizes on the unique start sentinel. A malformed
frame carrying the current run id is fatal. PRECHECK sequence is 1 and FINAL is
2; byte offsets in the circular ring do not define order.

The host generates the 128-bit run id with `secrets.token_hex(16)` and pins both
expected frames before a future run. Raw current-run tokens outside a valid frame
are also fatal, covering a start-sentinel truncation at circular-ring wrap.

Historical foreign-run frames may be present in the baseline because retention
is the feature under test. They are inventoried but cannot satisfy the pinned
run. Current-run duplicates, wrong identity/context, malformed frames, wrong
sequence, FINAL before its gate, or PRECHECK eviction at G11 are failures.

## Stage B Boundary

Stage B is not a candidate. It is a future positive-evidence classification
performed after a separately authorized and named transition. The host cannot
observe the candidate's internal G11 PASS before that transition, so positive
and negative outcomes are intentionally asymmetric:

```text
PASS     = first later stock/Magisk /proc/last_kmsg contains exactly one valid
           current-run PRECHECK and FINAL bound to the pinned module and contract
NO_PROOF = both are absent; Stage A not reached and transition loss are not
           distinguishable; stop without causal attribution
FAIL     = partial, duplicate, malformed, wrong-run, wrong-contract, or bad sequence
```

The unique FINAL is emitted only after internal current-ring verification, so an
exact positive proves both Stage A and cross-session preservation. Absence cannot
prove which hidden condition failed. Same-session `/proc/last_kmsg` is
structurally incapable of proving current capture and is never accepted.

## Unverifiable Ledger

Source does not establish whether the reserved ring survives any of these:

- warm reboot;
- cold boot;
- panic reset;
- watchdog reset;
- RDX transition;
- bootloader/download transition;
- bootloader or TrustZone reserved-memory clearing.

No transition is selected in V3426. A future unit must select exactly one class,
prove its recovery/rollback envelope, and obtain a fresh narrow authorization.
Until then the contract remains `NO-LIVE`.

## Explicit Exclusions

The first observer rung excludes `sec_debug.ko`, USB, DWC3, configfs, sysfs
writes, Max77705, panic, watchdog, persistent mounts, block writes, and Android
startup. `sec_debug.ko` is not the capture owner and would add policy/panic
behavior. O3/O3F/O3R1 artifacts and marker families are permanently retired.

## Host Deliverables

```text
workspace/public/src/scripts/revalidation/s22plus_v3426_phase_observer_design.py
tests/test_s22plus_v3426_phase_observer_design.py
docs/plans/s22plus-v3426-phase-observer-contract.json
```

The validator rechecks the exact source archive, module identity and metadata,
probe order, current-ring proc semantics, strategy-3 hook path, and synchronous
`/dev/kmsg` return path. The test suite covers the happy path and all material
rejection classes without contacting the device.
