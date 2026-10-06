# P415: preserve existing native_data evidence before another writable boot

P415 `v0.4.0-rc.15` adds one mountless historical-file capture before any
prospective Debian boot, log rotation or journal recovery. It is the next
bounded unit toward the operator's requested device-local persistent evidence
and separation of startup from USB reporting. The durable writer and changed
Debian startup semantics are not implemented or activated by this unit.

P413 proved installed PID1 and rcS entry, then lost transport and returned to
healthy original Android through its consumed recovery. Its post-run
native_data cleanliness and later service progression remain unknown. Reading
existing records first preserves an opportunity that another writable boot
could destroy. P413's journals and artifacts remain unchanged and consumed.

## Scope and interpretation

The separate [root-evidence policy](../operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
uses the existing V3 one-shot Android-origin owner and original-A return. Common
contract revision 38 and exact-target adoption add only partition-protected,
mountless reads of the fixed private file list. The original inspector's
clean-only mount and digest-only tree comparison are unchanged.

The reader binds exact UFS/GPT/partition/UUID/features, sets only native_data's
kernel RO flag, and runs the static library parser as uid/gid 65534 with no
capabilities or filesystem-opening syscalls. Its custom I/O manager cannot
write and bounds reads to 64 MiB/16,384 calls. Each used group descriptor is
checksum-verified before its inode-table location is trusted. Directory and
inode checksums remain enabled. No mount, journal replay, filesystem write,
installed-code execution or root admission occurs.

Twelve fixed paths cover the boot counter, wtmp, current dmesg/messages and
specified rotations. Raw suffixes, file bounds and metadata constraints are
sealed in the image. P415 does not select the optional future per-run receipt.
Full raw records remain private. A valid acquisition does not require every
file to exist or be readable; it preserves explicit per-file status without
claiming the missing execution evidence.

The returned view consists of checkpointed home blocks. A committed journal
may contain newer inode, directory or data changes. Missing/older records
therefore cannot establish non-execution. Counters and service logs alone also
cannot substitute for authenticated PID1, same-boot SSH or clean shutdown.
Current clean state and interpretation of historical logs remain separate.

## Validation and independent review

The revised helper passed 12 real ARM64 Linux VM cases: clean, dirty,
committed-journal-only, missing path, symlink, hardlink, oversize, directory
checksum, inode checksum, group-descriptor checksum, wrong UUID and wrong GPT.
Every case retained identical whole allocated backing-disk bytes and scoped
partition protection. The journal-only case returned the older checkpointed
counter without replaying its valid committed transaction. VM board discovery
is explicitly substituted and does not establish Samsung hardware behavior.

Independent review reproduced an integrity defect in the first reader: a
corrupt group descriptor checksum could pass because libext2fs did not check it
before trusting the inode table. The retained original ARM64 reproduction
records the defect. The revised reader checks each used descriptor and the new
negative case returns explicit read errors without modifying the disk.
Review also found contradictory decoder statuses and integration omissions;
these were corrected before qualification.

Twelve focused tests passed, including actual C/PTY framing, one pre-EXEC
intent, DETACH/raw rederivation, truncated evidence despite exit zero, strict
binary accounting and original-A recovery without repeating an uncertain
reader. Eighty-four affected owner/task/adapter/protocol/root-inspection/
userspace/journal/Android32 regression tests also passed. Touched Python passed
`py_compile`; the repository boundary check and whitespace checks passed.

The second full build passed actual A/B equality and reopened package audit.
The strict qualifier and adapter joined the actual AP bytes, fixed helper/table,
library provenance, sealed scope and Android32 return basis. The helper is an
ARM64 statically linked ELF. The image contains neither a formatter/checker nor
a Debian rootfs archive.

| Qualified item | SHA-256 |
| --- | --- |
| Boot-only AP, 32,266,281 bytes | `0df58ae4c501cca4edf0340fc3698a5d6c8bec47200a249112d55edb5bce23d8` |
| Qualified image record | `ce5dc4a60eb99024ad7015d751f2258fd756c177692a68a09aaff7fce82c052a` |
| Frozen 251-path review closure | `997a79c38d10f1f2dfd077699bf8ba051b9838907f96e3be83a17a2fcae9da82` |

Independent review returned **PASS_GO**, with no unresolved findings, for
this exact legacy reader capability. Its final private result has SHA-256
`02d344283b18653769d542343c84eee43ddb2102e9b43d6e803637f07ed8eae0`.
The dedicated `s22plus_native_root_evidence_v1_review.json` binds the reviewed
96 host/authority and 165 runtime source maps. Historical review records were
not repinned.

Offline preparation passed with device command, USB/lane, host acquisition,
subprocess and grant-opening entrypoints blocked. The candidate is unclaimed
and no F1 owner is pending. The concrete task is one `root-evidence` operation,
1800 seconds, attended recovery, no E/reentry/HUD/reconnect. Its SHA-256 is
`b7a4613f033a048c62362ddc351d02f1e9a322e8cec1561be7fb2d7393f2a012`.
Preparation uses retained target/recovery bindings and proves no fresh device
health. It opens no grant. Execution must perform the original fresh exact
health and recovery checks after the operator returns the finite grant.

## Private evidence

The H0 root is
`workspace/private/outputs/s22plus-debian-durable-evidence-p415-h0-20261007-1/`.
It retains source snapshots, library provenance, all initial failed checks,
revised ARM64 results, focused/regression logs and independent review. Full
packages remain under `workspace/private/outputs/s22plus-native-root-evidence-v1/p415/`.
The first package build is retained as stale H0 output after an integration
binding correction; it is not the qualified candidate.

This unit has performed zero Samsung device actions. A90 and S20+ targets,
artifacts, journals and existing unrelated working-tree changes are untouched.
The first live operation still requires exact current Android health, usable
attended physical Download recovery and the concrete returned finite grant.
