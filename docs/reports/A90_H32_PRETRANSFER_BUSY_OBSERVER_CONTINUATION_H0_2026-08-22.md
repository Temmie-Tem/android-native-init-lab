# A90 H32 pre-transfer busy-observer continuation — H0

The fixed H32 reconciler was invoked once for a read-only V2321 observation
after exact Native `04e8:6861` binding. Its first `boot-id` command returned
`rc=-16`, `status=busy`, with the exact automatic-menu text
`[busy] auto menu active; send hide/q before command`. No `41` record was
published, and this attempt performed no candidate or rollback write, reboot,
or F1 action.

The failed observer closure is the exact directory
`a90-h32-f1-20260822-01-reconcile-h31-pretransfer-abort-1-logs`; its six
stdout/stderr log hashes are bound by set digest
`d5a0f200c928d88630eb2056f57e9f7964a8706ae3da70819cf8b16a6f3b7d81`. The
observer ADB home and `.android` directories were empty private directories.

The continuation implementation is H32-specific: it validates that exact
failed log set, publishes one durable sidecar intent, delegates one raw
`hide\n` and the existing three-second H28 settle/health observation, then can
publish only H32 `41-pretransfer-abort.json` and remove only the active guard.
The H32 candidate guard remains consumed. A sidecar intent without a
successful hide receipt is never retried. The implementation has no image,
partition, rollback, reboot, ADB, or recovery-transition primitive.

Independent review passed with H/M/L `0/0/0` for execution closure
`547e8b35b106e1bc75fa2d9bbf6288d0c97dca45f1b081519974bdadd42b58eb`.
The attended continuation then sent `hide` exactly once and observed exact
healthy V2321 `0.9.285 / v2321-usb-clean-identity-rodata`. It durably published
`41-pretransfer-abort.json` with decision `PRETRANSFER_ABORTED_NO_BOOT_WRITE`.
Candidate and rollback transfer/write flags remain false, the active guard is
absent, and the H32 candidate guard remains present. H32 cannot replay and this
closure grants no H33, D0, approval, or F1 authority.
