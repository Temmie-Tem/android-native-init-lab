# V3438 S22+ Ramoops Backend False-Negative Host Postmortem

## Verdict

`HOST_POSTMORTEM_PASS_V3437_BACKEND_GATE_FALSE_NEGATIVE`.

V3437's ramoops backend registered successfully. The helper stopped because it
required an early boot log string that had already been overwritten from the
kernel ring. The contract result remains the historical fail-closed
`FAIL_PREPANIC_GATE_ROLLBACK`; the corrected technical conclusion is
`PROVEN_BY_POST_REGISTER_PARAMETER_UPDATE`.

The analyzer itself is host-only and reads only pinned local inputs. During this
unit, the already-restored stock Android supplied two additional read-only ADB
captures: duplicate candidate `/proc/last_kmsg` reads and a stock backend/sysfs
snapshot. Those captures performed no device write. The unit performed no image
build, flash, reboot, panic, or live candidate action.

## Machine-Checked Artifact

```text
docs/plans/s22plus-v3438-ramoops-backend-postmortem.json
workspace/public/src/scripts/revalidation/s22plus_v3438_ramoops_backend_postmortem.py
tests/test_s22plus_v3438_ramoops_backend_postmortem.py
```

The analyzer pins the exact FYG8 source archive, running Magisk kernel, stock
module load list, `sec_pmsg.ko`, V3437 helper, session, timeline, live log, and
duplicate-read candidate `/proc/last_kmsg` evidence.

## Source Proof

The exact FYG8 `fs/pstore/ram.c` path is ordered as follows:

```text
ramoops_probe
  -> pstore_register(&cxt->pstore)
  -> if error: return through fail path
  -> mem_size = pdata->mem_size
  -> record_size = pdata->record_size
  -> console_size = pdata->console_size
  -> pmsg_size = pdata->pmsg_size
  -> "ramoops: using ..."
```

The module defaults before a successful DT probe are:

```text
mem_size=0
record_size=4096
console_size=4096
pmsg_size=4096
```

V3437 observed:

```text
mem_size=2097152
record_size=262144
console_size=524288
pmsg_size=1048576
```

Those values are the exact candidate DT layout and cannot be reached through
the inspected driver path unless `pstore_register()` has returned success.

The pstore core then assigns `backend = new_backend` and emits
`Registered ramoops as persistent store backend` before returning zero. The
running kernel binary SHA256
`bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
contains both this pstore success string and the ramoops `using` success string.

## Platform Device Proof

The exact FYG8 `drivers/of/platform.c` has a reserved-memory allowlist containing
`compatible = "ramoops"`. At `arch_initcall_sync` it creates a platform device
for each available matching node. V3437 proved the candidate live node was
`status=okay`; the driver therefore had the required platform-device creation
path.

This is consistent with the post-register parameter update and rules out the
earlier hypothesis that the DT node existed but could never bind.

## Why The Log Gate Failed

V3437's helper captured either of these strings:

```text
Registered ramoops as persistent store backend
ramoops: using
```

but its final hard predicate accepted only the first. More importantly, neither
early string remained by Android userspace time. The duplicate-read candidate
`/proc/last_kmsg` is 2,097,136 bytes and begins mid-ring at timestamp
`3.453647`; ramoops driver/platform registration occurs in earlier built-in
initcalls. Heavy Samsung boot logging had overwritten both messages.

Therefore any mandatory early-dmesg-string predicate is unstable on this build.
The helper behaved fail-closed but produced a false negative.

## Competing Samsung Backend

The final stock read-only snapshot is:

```text
pstore_backend=samsung,pstore_pmsg
ramoops.mem_size=0
ramoops.record_size=4096
ramoops.console_size=4096
ramoops.pmsg_size=4096
```

`sec_pmsg.ko` imports `pstore_register`, matches `samsung,pstore_pmsg`, and is
stock module-load entry 109 after `sec_debug.ko` at 105. Candidate ramoops is
built in and its reserved-memory platform device is created during kernel
initcalls, before the vendor module sequence. The V3437 parameter side effect
therefore shows ramoops won the single pstore-backend registration race for that
candidate boot. The later `sec_pmsg` probe result was not captured directly.

## Corrected Boundaries

Proven:

- candidate DTBO reached the live tree with the exact intended layout;
- a ramoops platform device was eligible for creation and binding;
- ramoops successfully registered with pstore;
- V3437 stopped because of an unstable log-only proof gate;
- no panic occurred and stock DTBO rollback completed.

Still unproven:

- direct candidate readback of `/sys/module/pstore/parameters/backend=ramoops`;
- direct candidate platform-driver binding symlink;
- the later Samsung `sec_pmsg` probe result under the candidate;
- console/dmesg/pmsg record retention after a panic.

## Next Unit

V3439 should correct the helper without rebuilding the DTBO:

1. Require exact candidate DTBO and post-register ramoops parameters.
2. Require `/sys/module/pstore/parameters/backend=ramoops`.
3. Require the bound ramoops platform-device/driver link.
4. Treat early dmesg strings as optional corroboration only.
5. Preserve the existing run-bound marker, duplicate pstore read, evidence-first
   rollback, and fail-closed safety rules.

V3439 is not authorized live. Reusing the same candidate requires a fresh,
narrow DTBO and intentional-panic exception after host review.

## Validation

```text
py_compile                              PASS
generated postmortem --check            PASS
V3437+V3438 focused tests               27/27 PASS
V3426-V3438 regression tests           176/176 PASS (64.907 s)
git diff --check                        PASS
```
