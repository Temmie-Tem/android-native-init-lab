# S22+ FYG8 R4W1-C Endpoint Stabilization Source Host GO

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `SOURCE_GO_TO_NEW_LIVE_BINDING_PACKET`

Scope: host-only implementation, static validation, full artifact reopening,
and independent read-only review after the two pre-consumption endpoint-arrival
failures. No device was enumerated or contacted during this correction. No ADB
action, reboot, Download transition, Odin transfer, flash, partition write,
candidate consumption, or live-policy activation occurred.

## Correction

The live helper now performs a bounded expected-device stabilization before
the unchanged hardened Odin ticket wait:

- it reuses the Android ADB USB topology and serial digest;
- only Samsung Download product `04e8:685d` is eligible;
- the direct USB character node must produce three identical samples over at
  least 0.5 seconds;
- ctime-only settling resets the consecutive count;
- disappearance, replacement, malformed identity, timeout, or binding mismatch
  is fatal;
- stabilization and the original Odin wait share one finite deadline.

Continuity is then enforced through transfer launch. The stabilized pathname,
`st_dev`, inode, `st_rdev`, and ctime must equal the hardened ticket. The final
USB binding check brackets all sysfs reads with complete node snapshots,
requires both snapshots and the ticket identity to match, and again requires
the exact topology, serial digest, and product `685d`. Candidate, Magisk, and
stock callbacks use this combined check as the final device check before the
sealed Odin process starts.

The shared Odin transition core remains byte-identical:

`ab418aac5ce4c854f433e2132bd9536a610991384ec82c50dc0ba063f1888a9b`

## Exact Source Snapshot

```text
live helper
  size    90950
  SHA256  65c137586b2decf160800f841b7243f3332108332043dbcaa548d7698e080c99

live focused test
  size    64948
  SHA256  c5966fb411983bed5b72e39400e8c8d15304ec0257e34e435ad5aae075ca1fbb

inactive live template
  size    9637
  SHA256  06f28538c4fa358dabd5e35c6bab5e0cd5a83c6e78c39d9ba1a6c1516ced5497

binding packet generator
  size    11595
  SHA256  1a7ab0cd1ef1883e4db7e676203155a2ee402510914e7ccba5b749ed040e62e3

binding packet focused test
  size    7111
  SHA256  8c8a4edc01fa1814946c2e1a424bef501cb87bad152e9a39084877011305ffbd
```

The generator pins the exact helper and focused-test identities above. The
template identity is pinned by the helper and inherited by the generator.

## Independent Review

The existing `gpt-5.6-sol` xhigh independent read-only session reviewed each
corrected snapshot without executing tests or device commands:

1. `SOURCE_NO_GO`: pathname-only acceptance discarded the stabilized node
   tuple.
2. `SOURCE_NO_GO`: the final USB binding check did not compare its current node
   tuple with the ticket.
3. `SOURCE_NO_GO`: the USB identity function cached its first stat across sysfs
   reads without a post-read stat.
4. `SOURCE_GO`: pre/post sysfs snapshots, exact ticket equality, product
   enforcement, all three transfer callbacks, and the new race tests closed all
   HIGH, MEDIUM, and LOW blockers.

## Validation

```text
focused live test                         49 passed
exact six-file relevant regression set   181 passed
ResourceWarning treated as error          PASS
py_compile                                PASS
git diff --check                          PASS
full 9.68 GB offline artifact gate        PASS
offline verdict                           PASS_R4W1C_LIVE_GATE_OFFLINE_CHECK
connected policy                          active
connected PASS                            present
live policy                               inactive/retired
candidate consumed                        false
device contact/write/reboot/flash         false/false/false/false
```

The full gate reopened the exact candidate, Magisk rollback, stock cleanup,
Odin4, source pins, and FYG8 firmware ZIP SHA256
`f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`.

## Decision

Commit this host-only source packet. While the live policy remains inactive,
the pinned generator may emit a new private binding packet from the existing
connected PASS. That exact packet and rendered clause require separate
independent review. Only a later exact ACTIVE clause commit can reopen a fresh
one-shot live gate. This report grants no device contact or live authority.
