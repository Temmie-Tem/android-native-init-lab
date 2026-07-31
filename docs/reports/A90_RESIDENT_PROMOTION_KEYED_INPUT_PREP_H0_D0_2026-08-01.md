# A90 Resident Promotion Keyed Input Preparation

Date: 2026-08-01 KST

Result: `STOP_D0_RETAINED_WORK_PRESERVED_AWAITING_EXACT_CLEANUP_APPROVAL`

## Outcome

The resident-promotion input contract now correctly separates the clean
deterministic Debian A/B base from the fresh per-run keyed execution image. A
new private keyed 2 GiB image was created from the exact corrected A/B base;
its observer key, ext4 label, ownership, read-only filesystem check, new inode,
and absent runtime paths all passed. This host step granted no live authority.

One connected D0 read selected exactly the A90 bridge. It proved exact V2321
version/build, `selftest fail=0`, zero pstore entries, and exact candidate and
rollback host artifacts. The new run-derived final and stage paths were
absent. The fixed predecessor work path was present, so preparation stopped
before manifest finalization, staging, flash, reboot, or cleanup.

The retained 2 GiB work file was hashed on-device, streamed read-only over the
already-active A90 USB NCM link into a new private mode-0600 host file, and
hashed again on both sides. Byte count and SHA256 matched, and the device file
remained unchanged. One accidental read-only `run --help` probe returned 127
while inspecting the CLI; it changed no device state. The separately connected
S22+ received no command.

## Repeated cleanup bottleneck removed

The reviewed cleanup helper already required one exact manifest, host
preservation, target, health, path, size, mode, link-count, mount, loop-backing,
approval, and no-retry closure. It additionally hardcoded one runtime-mutated
work SHA256 in source, forcing a code edit and review for every experiment.

That duplicate constant was removed. The exact SHA256 now comes from the
private manifest and must equal the reopened host-preserved bytes. The same
value is bound into approval preparation, the device preflight, the unlink
command, durable intent, host recheck before dispatch, inspection, and final
result. The deletion target remains the single fixed work path and no recursive
or generic cleanup surface was added.

Focused cleanup tests pass 19/19, including mismatched manifest/preserved hash
rejection and final-result hash retention. Python compilation and
`git diff --check` pass. Independent changed-closure review initially found the
missing final-result hash field; after the field and regression assertion were
added, re-review returned `PASS` with no remaining blocker.

## Next gate

Prepare one private data-only cleanup manifest and its exact D1 approval token.
No unlink is authorized yet. After a single approved unlink and exact V2321
return-health check, repeat connected D0 and only then finalize the resident
promotion manifest. No F1 approval or candidate authority exists in this unit.
