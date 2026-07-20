# S22+ FYG8 R4W1-C Odin Enumeration-Diff Observer Policy Ready

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `POST_ACTIVATION_GO`

Scope: host-only policy activation, exact artifact reopening, static and test
validation, and two independent read-only reviews. No device, USB, ADB, reboot,
Download transition, Odin execution, enumeration, transfer, flash, partition
write, one-shot consumption, cleanup, or acceptance decision occurred.

## Commit Chain

```text
source qualification   5056c2cda8b74802f9802b9266cd997ca3e43341
binding qualification  a0779ab14b6fd14cfad5a67c40202cdff2f97ea6
policy activation      d939f84ec99bf271880f33baf97fcffb8074180f
```

The activation commit has the binding commit as its sole parent and changes
only `AGENTS.md`: 42 additions, zero deletions. Forty-one lines are the exact
canonical BEGIN-END block and the final line is its blank separator.

## Installed Authority

```text
installed clause size     5444
installed clause SHA256   9f42de1cb609f9897799f82d1e59f11fd1ec24cc018da3ed9099adb1e89d497e
normalized template SHA   93d8959a7df8b52574ed4d734122d5799b5f36d0077e82532feed49d75aa2677
current AGENTS.md size     464803
current AGENTS.md SHA256   dd3fafe35416aaca74308147841ca3ea4a7048b7944cf511ef28f0ed57e32cb8
marker counts              BEGIN=1 END=1 ACTIVE=1 RETIRED=0 placeholders=0
```

The installed block is byte-for-byte equal to
`workspace/private/outputs/s22plus-r4w1c-enum-diff-binding-90707b79c670.clause.md`.
Its source, focused test, inactive draft, binding generator, generator test,
private packet, private clause, parent `AGENTS.md`, and data-only Odin identity
all match the exact pins in the binding report. The private packet remains
permanently `PENDING`; activation did not rewrite it.

## Validation

```text
py_compile with ResourceWarning fatal              PASS
observer offline check                             PASS
offline verdict                                    PASS_R4W1C_ENUM_DIFF_OBSERVER_SOURCE_OFFLINE_CHECK
focused observer tests                             80 passed
exact related R4W1-C regression suite              185 passed
installed/private clause byte comparison           PASS
installed normalized digest reproduction           PASS
git diff --check                                    PASS
observer consumed state                            absent
observer run directories                           absent
observer signature evidence                        absent
observer authority lock                            absent
```

The offline source audit confirms one subprocess creation site, one exact
`[/usr/bin/odin4, -l]` call site with a ten-second bound, execution through the
held verified Odin descriptor, and no alternate execution or transfer CLI
surface.

## Independent Reviews

Review `019f7fd4-9527-7e23-92af-c48738894e33` examined the exact uncommitted
policy-only diff and independently reopened every bound artifact. It found no
HIGH, MEDIUM, or LOW issue and returned `POST_ACTIVATION_GO`.

Review `019f7fda-a51c-7d11-9055-59bc2f0327af` started fresh from committed
object `d939f84e`, verified its sole parent and exact one-file diff, reproduced
the clause and normalized digests, checked neighboring policy separation, and
proved the consumed state and run evidence absent. It also found no HIGH,
MEDIUM, or LOW issue and returned `POST_ACTIVATION_GO`.

Both reviews were host-only and read-only. They did not run Python, tests, the
generator, device or USB discovery, ADB, Odin, or network operations, and did
not edit files.

## Live Boundary

The ACTIVE exception permits exactly one attended observation:

1. one exact FYG8 Android/Magisk/partition and USB-topology baseline;
2. durable exclusive one-shot consumption before one `adb reboot download`;
3. stable exact Samsung Download enumeration at the bound topology;
4. fresh physical confirmation of the same handset/cable/hub/port;
5. one bounded exact `odin4 -l` with complete pre/post evidence closure;
6. physical Download exit and exact Android return.

It authorizes no AP, candidate, Odin transfer, flash, partition write, cleanup,
acceptance decision, or second observer. The retained connected policy cannot
supply observer authority, and the former R4W1-C live policy remains RETIRED.

The next live entry requires a fresh exact acknowledgement:

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-OBSERVE`

After stable normal Download is reached, the helper itself requires the
separate fresh physical-continuity confirmation:

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-NORMAL-DOWNLOAD-CONFIRMED`

Only an already-consumed interrupted observer may use the recovery token:

`S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-RECOVER-CONSUMED-OBSERVER`

Generic or earlier approvals do not carry. This checkpoint makes the one-shot
observer live-ready; it does not claim that the observer has run.
