# V3440 S22+ RDX USB Viability Gate Source Ready

## Verdict

`HOST_SOURCE_READY_NO_LIVE_AUTHORIZATION`.

V3440 converts the RDX/S-Boot idea into one bounded zero-flash discriminator.
The checked helper can observe USB identities without policy, but it cannot
trigger a panic or send a USB protocol command while its `AGENTS.md` exception
is inactive. No panic, reboot, flash, partition write, RDX entry, or USB
protocol command occurred in this host unit.

## Source Audit

The public references were fetched and pinned for host-only inspection:
[bkerler/sboot_dump](https://github.com/bkerler/sboot_dump) and
[linux-msm/qdl](https://github.com/linux-msm/qdl).

```text
bkerler/sboot_dump = 8c9f6eb79ffbe702152ca7810f6382bf5e1bfd58
linux-msm/qdl       = a00d81bc639908875862582f0d3cb0775d92e269
```

`sboot_dump` supports Samsung QC only as tested on the Galaxy S7. Its default
no-argument path targets `04e8:685d`, sends `PrEaMbLe\0`, then `PrObE\0`, and
prints the returned upload-area table. It does not request `DaTaXfEr` in that
mode. It is not suitable for direct live use here because it accepts
`NeGaTiVeAcKmNt` as a connected state, has weak malformed-response handling,
and detaches USB kernel drivers internally.

V3440 therefore implements only the discovery subset with stricter gates:

- exact single endpoint `04e8:685d`;
- exactly one CDC-data interface with one IN and one OUT endpoint;
- only `PrEaMbLe\0` and `PrObE\0` are code-allowlisted;
- exact `AcKnOwLeDgMeNt\0` is mandatory before `PrObE`;
- negative/malformed responses stop before the second command;
- probe response is capped at 32768 bytes and parsed with bounded entries;
- any detached interface is released and reattached in `finally`;
- no data-transfer acknowledgement, address, range, memory segment, power,
  reboot, partition, or storage command exists in the helper.

`qdl ramdump` is a distinct Qualcomm Sahara path. V3440 recognizes exact
`05c6:900e` but intentionally does not invoke `qdl` or begin a Sahara session.
A discovered Sahara endpoint would be enough to design a separate bounded
collector.

## Checked Helper

```text
path=workspace/public/src/scripts/revalidation/s22plus_v3440_rdx_usb_viability_gate.py
sha256=cab62dcc89cb7f39d16e99b3d19106f1e5a418436d05a6d5fa7076aab136e4f8
schema=s22plus_v3440_rdx_usb_viability_v1
```

Host USB runtime:

```text
PyUSB=1.2.1
wheel_sha256=2b4c7cb86dbadf044dfb9d3a4ff69fd217013dbe78a792177a3feb172449ea36
libusb_backend=true
```

The wheel was verified against [PyPI metadata](https://pypi.org/project/pyusb/1.2.1/)
and unpacked only under the
untracked private tools directory. The helper verifies the retained wheel hash,
runtime version, and libusb backend before it can arm a panic.

## Proposed Live Flow

1. Verify exactly one normal Android target, `SM-S906N`/`g0q`/FYG8, boot
   complete, Magisk `uid=0`, boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
   and stock DTBO SHA256
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`.
2. Flush a private session record, then write one run marker and trigger one
   SysRq panic.
3. Poll host USB sysfs for at most 120 seconds and durably flush identity
   changes.
4. For `04e8:685d`, run only the two-command S-Boot discovery probe. For
   `05c6:900e`, record Sahara identity without invoking qdl. Otherwise classify
   `NO_PROOF_NO_RDX_USB_ENDPOINT`.
5. Tell the operator to use the physical RDX EXIT action. Wait for Android and
   recheck the unchanged boot/DTBO hashes.

The standardized eight timeline phase names remain present even though the run
has no flash. `result.json` records explicit mappings such as
`panic_arm_start_no_candidate_flash` and
`rdx_exit_wait_start_no_rollback_flash`; no synthetic flash is claimed.

## Current Read-Only Snapshot

The connected phone is in normal Android mode:

```text
USB=04e8:6860 SAMSUNG_Android
classification=NO_SUPPORTED_RDX_ENDPOINT
ADB=one authorized SM-S906N target
```

This is expected before the panic and is not RDX evidence.

## Policy State

The proposed clause is staged at:

```text
docs/operations/S22PLUS_V3440_RDX_USB_VIABILITY_AGENTS_EXCEPTION_DRAFT_2026-07-11.md
draft_sha256=d192edccd68c5829ec784d3ec53eae25a4f427d49ec9fec6dadcca8a4297c0e8
state=DRAFT_INACTIVE
```

The draft requires independent panic and USB-probe acknowledgements. It allows
one panic and one discovery attempt only. It explicitly excludes RAM transfer,
qdl invocation, flash, partition operations, and a retry. Full or bounded RAM
dump collection requires a separate future design and authorization even if
V3440 discovers a working endpoint.

## Validation

```text
py_compile                         PASS
focused unittest                  11/11 PASS
offline-check                     PASS
policy_active                     false
device_contact in offline-check   false
memory_transfer                   false
current USB snapshot              PASS (04e8:6860, not RDX)
```

## Next Gate

Review and commit this exact source first. A fresh explicit operator approval
may then promote the exact draft into `AGENTS.md`. Only after the promoted
source hash and both acknowledgement tokens match may the attended V3440 live
run start. During that run the operator must leave the device on the RDX screen
until the helper reports that USB observation is complete, then use physical
RDX EXIT so the final Android baseline can be verified.
