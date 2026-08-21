# A90 H29 uncertain System return and postrollback recovery

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G
Disposition: `RECOVERY_CLOSED_V2321_HEALTHY_H29_UNPROVED`

## Incident

The attended H29 F1 wrote and prefix-read back the exact H29 boot image once.
Its sole TWRP System-return command returned nonzero, so no H29 Native
observation was obtained. The owner then wrote and prefix-read back the exact
V2321 rollback once; its sole TWRP System-return command was likewise
uncertain. Both attempts are consumed and must never be replayed.

The old receipt classifier treated this exact shape as an unclassified write
failure and immediately selected rollback. The repaired classifier instead
parks `bootWrittenReadbackExact=true` plus a sole attempted but unconfirmed
System return as `BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN`.

H29 therefore remains unproved, not refuted. This run does not show that H29
reached userspace or that its kernel was accepted.

## Recovery closure

After the operator manually selected TWRP System, Native V2321 became visible.
A bounded ACM-only observation read an initial boot ID, exact
`0.9.285 / v2321-usb-clean-identity-rodata`, self-test, status, and a final boot
ID. The boot IDs matched, self-test reported zero failures, pstore reported no
entries, and recovery remained available.

The first terminal-finalizer attempt correctly stopped before observation
because the managed bridge launch was not the exact reviewed form. The second
attempt completed the five reads but stopped because another Samsung USB
endpoint was present. After that device was disconnected, exactly one Samsung
endpoint remained and the same no-effect finalizer succeeded. It transferred
no image, issued no reboot, used no ADB, and sent no recovery or partition
command.

Canonical `41-recovery-closed.json` is 1,088 bytes at SHA-256
`d6f012df46645cb2b27a6d3a549c6b971eef0018e14a4d11e02b55bfb6667845`.
It records `V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED`, candidate replay
false, and rollback replay false. The active-run guard was released only after
that durable record; the H29 candidate guard remains consumed.

## Validation and authority

The reusable finalizer and receipt repair received independent `PASS_GO` at
execution closure
`dfc0d3ca73fa8428a0ee397660549e18af29940ebfd4ac39bc79ecb02a17502c`.
The final review file is SHA-256
`a9f559e34281efc629a0ff2f73e773ad017c851792374a46c1afb844cdf89ec2`.
After recovery, the four focused public host modules passed 89/89 using a
repository-private temporary directory because the unrelated system `/tmp`
tmpfs was full; touched Python passed `py_compile` and `git diff --check`.

This closes only the H29 recovery obligation. It grants no candidate replay,
rollback replay, D0, D1, F1, new manifest, or new approval authority. A future
rebuilt-kernel attempt requires fresh candidate bytes, qualification, manifest,
connected preflight, and attended approval.
