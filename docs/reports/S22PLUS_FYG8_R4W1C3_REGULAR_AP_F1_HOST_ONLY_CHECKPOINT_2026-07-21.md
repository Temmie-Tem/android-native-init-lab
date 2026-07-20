# S22+ FYG8 R4W1-C3 Regular-Path F1 Host-Only Checkpoint

Date: 2026-07-21 KST

Verdict: `PASS_R4W1C3_REGULAR_AP_F1_HOST_ONLY`

Scope: host-only. No ADB, USB enumeration, Odin execution, reboot, Download
transition, transfer, flash, consumed-state creation, or device write occurred.
The C3 policy remains inactive and this report grants no live authority.

## Problem Closed

R4W1-C2 passed candidate, Magisk, and stock AP content through sealed memfds and
gave Odin `/proc/self/fd/N` as the AP name. Odin rejected that extensionless name
before `Setup Connection`; no device session or partition transfer occurred.

C3 keeps every candidate byte unchanged and replaces only that host transport.
`s22plus_boot_only_f1_transport.py` now:

- opens direct regular inputs with `O_NOFOLLOW` and holds the descriptors;
- requires exact size and SHA256;
- requires an AP pathname ending in `.tar.md5`;
- requires exactly one regular `boot.img.lz4` archive member;
- rejects `/proc/*` Odin/AP arguments;
- passes the real absolute AP pathname to Odin; and
- revalidates descriptor/path inode, size, mtime, and ctime after return.

The threat model remains the proportional local-attended model in
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`; this is not a defense against a
malicious same-UID owner racing every host syscall.

## Exact Inputs

- candidate boot: size `100663296`, SHA256
  `1d394028714c48cfc0fd220acade9ead9a49ea21a81c59b2b87f88e61de704b0`
- candidate AP: size `27064361`, SHA256
  `85514e79e3400de30b7146606a9e86c3655fc7a8766daba5f054ae1bd54fd42f`
- Magisk rollback AP: size `23367721`, SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- stock cleanup AP: size `100669481`, SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
- full FYG8 firmware: size `9680091538`, SHA256
  `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`
- Odin4: size `3746744`, SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`

The fresh candidate static checker returned
`PASS_R4W1C_WATCHDOG_CARRIER_TWO_REPRO_STATIC_CONTRACT`.

## Validation

The related 31-test suite passed:

- common timeline and marker mechanics: 12;
- regular-path F1 transport: 6;
- R4W1-C watchdog carrier static checker: 6;
- C3 inactive gate and policy binding: 7.

The full `--offline-check` reopened the 9.68 GB firmware evidence and all APs,
returned `PASS_R4W1C3_REGULAR_AP_F1_HOST_ONLY`, and reported:

- `policy_active=false`;
- `device_contact=false`;
- `odin_transfer=false`;
- `anonymous_proc_fd_inputs=false`.

The first composite run exposed one stale SHA pin for the old
`s22plus_odin_transition_core.py`. C3 does not import or call that core. The gate
was narrowed to its real fixed dependencies rather than modifying old evidence
or adding an unused compatibility dependency; the full offline run then passed.

## Inactive Live Shape

The target adapter is intentionally inactive. If later reviewed and bound, it
would perform only:

1. exact Android/Magisk and USB-topology preflight;
2. one exact candidate boot-only transfer after durable consumption;
3. at most 120 seconds of passive observation;
4. attended physical Download entry;
5. exact Magisk boot-only rollback, with stock cleanup only after a definite
   Magisk transfer failure on the same endpoint; and
6. exact final health plus two byte-identical `/proc/last_kmsg` reads.

PASS additionally requires accepted retained R4W1-B marker evidence. Passive
time, candidate transfer alone, or stock cleanup cannot produce PASS.

## Review Boundary

A separate high-effort read-only model review was started, then intentionally
stopped before verdict when its duration and breadth became disproportionate to
this checkpoint. It supplies no approval. The exact policy draft remains
`DRAFT_INACTIVE`, no clause was added to `AGENTS.md`, and no acknowledgement is
currently actionable.

Next: perform one fresh D0 connected read-only target check. Only a clean D0
result should reopen a bounded C3 source/binding decision.
