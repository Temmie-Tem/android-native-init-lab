# S22+ P408 streamed preparation — H0, 2026-09-26

## Selected unit

P408 `v0.4.0-rc.8` brings up the existing P406-style native UFS/ACM runtime
before running a fixed protected preparation command. The
[forensic audit](S22PLUS_BOOTSTRAP_FORENSICS_H0_2026-09-26.md) did not establish
the cause of P407's silent bootstrap. This candidate makes the checker, root
comparison, loader checks and cleanup observable after native authentication.
It does not repeat P407's automatic pre-observer bootstrap or reproduce its
whole environment. It is a fresh diagnostic candidate for the selected S22+
FYG8 target, with no installation, writable filesystem mount or PID 1 handoff.

The [separate capability](../operations/S22PLUS_NATIVE_STAGED_PREFLIGHT_V1.md)
defines one attended V3 `staged-preflight`, one operation, at most 1800 original
BOOTTIME seconds and one original-A return. The unique pre-EXEC intent consumes
the protected preparation before any command byte is sent. This H0 work opens
no grant, performs no connected D0 preparation and makes no device effect.
Fresh machine binding and a returned finite attended start remain necessary
before the experimental transfer. Previous candidates and grants stay consumed.

## Implementation and evidence boundary

The new helper reuses the root-inspector library and P403 child accounting.
After exact UFS/LU0/GPT binding it sets only entry-41's RAM block-RO flag and
verifies ioctl/sysfs readback. A dirty, RECOVER or orphan state skips subsequent
checker/mount work. On a clean root, the pinned static `e2fsck -fn` runs before
mounting. Both ramdisk composition and runtime checks reject ambient checker
configuration. The checker keeps UID/GID 0 for the private mode-0400 node while
all capabilities and supplementary groups are zero and no_new_privs is set.

The root then mounts `ro,noload,nodiscard,nodev,nosuid,noexec`. Both installation
markers, the original witness, all 8,969 archive entries, metadata/content and
the bounded inventory must match. Loader work additionally requires exact root
closure, empty root-owned `lost+found`, the pinned loader cache and no preload.
Only fixed `ld-linux-aarch64.so.1 --verify /sbin/init` and `--list /sbin/init`
children run. Each uses its own readonly executable bind mount/chroot,
UID/GID 65534, zero groups/capabilities, no_new_privs and closed extra fds.
Parent noexec and partition RO remain in force. Installed init is not executed.

The 17 stages emit flushed begin and pass/stop/error records. Child streams
are hex-encoded to prevent marker injection. Actual exec framing, wait status,
pipe completion, resource bounds and descendant settlement are independent
from semantic success. A zero exit alone cannot pass. Ordinary unmount,
owned cleanup and unchanged superblock/GPT readback are required for complete
observation. Uncertainty remains NO_PROOF under the existing outer command
group supervisor and physical original-A recovery owner.

The host retains fsynced raw RX before parsing. Its separate diagnostic parser
can recover complete authenticated frames up to the first bad or partial frame,
then retain valid stage records from that prefix. It requires the original
run, nonce, boot identity and unique pre-EXEC intent. This diagnostic result
cannot prove complete EXIT/DETACH/descriptor closure, cleanup, native health,
recovery or replay authority. The strict completion decoder remains strict.

`PASS_STAGED_PREFLIGHT_OBSERVED` means complete observation and cleanup;
`PROVED_PROTECTED_PREPARATION` additionally requires all three child workloads.
Neither proves switch_root, Debian host PID 1, networking or SSH. The stage
record identifies the last observed boundary, not necessarily the faulting
instruction. A failure before native ACM still has no authenticated stage log.

## Validation

- Actual static ARM64 helper and native runtime compile; A/B boot images and
  boot-only APs are byte-identical. The inspector table, checker, native helper,
  kernel and ramdisk composition are joined to the selected artifact inputs.
- Final real ARM64 Linux VM cases cover complete preparation, dirty root,
  directory-checksum damage and metadata mismatch. Each reaches the expected
  semantic result. The entire writable backing disk remains unchanged;
  native_data alone reports RO while whole disk and userdata remain writable.
- Nine real child faults cover setup failure, early zero exit, nonzero exit,
  signal, timeout, overflow, descendant, exec failure and wrong output.
  Settled negatives skip later work and complete guards; unknown or unsettled
  cases cannot be promoted to complete observation. The outer test supervisor
  proves group settlement. Actual checker credentials after exec are sampled
  through `/proc` and match the declared zero-capability policy.
- 109 focused tests pass across stage parsing, original inspection/userspace
  probes, actual C/PTY console, strict/raw replay, owner no-replay and console
  backpressure. The independently found missing-health-prefix exception was
  normalized to a bounded validation failure; two focused C/PTY tests pass
  after that fix, including authenticated captures cut before/within STATUS 4.
- The C/PTY test injects a host read interruption after raw fsync. It proves
  retained-prefix handling, not physical USB disconnect behavior. Corrupt,
  unauthenticated and partial tails preserve only earlier valid frames; the
  strict parser continues to reject missing completion.
- Recompiling the ordinary inspector with the optional hooks disabled matches
  retained P406 bytes. The default userspace probe keeps its original workload
  and predicates but is not byte-identical after the predicate refactor;
  consumed P403 artifacts and their provenance are preserved unchanged.

The VM substitutes virtual block discovery and uses the retained ARM64 virt
kernel. It is not Samsung execution proof. Current physical and virt helper
sources/headers are separately bound; the final virt helper is byte-identical
to the one used for the retained fault tests. No A90 or S20+ device was contacted.

## Retained private evidence

Evidence base: `workspace/private/outputs/s22plus-staged-preflight-p408-h0-20260926-1/`.
Selected package: `s22plus-native-staged-preflight-v1/p408/build-1/`.
The final source snapshot preserves 232 unique files, covering 78 host
execution receipts, 163 runtime receipts and the selected validation sources.
Raw captures, generated bindings, filesystem identifiers and binaries stay
private. Earlier incomplete H0 attempts are retained separately.

| Evidence | SHA-256 |
| --- | --- |
| Actual selected AP | `ce8c22fe2482ae6fe8b6823fd7b7c4c44f2163fa2390611121614e5475c9ec4c` |
| `qualified-1/image.json` | `fa42e52b9ef5d7cc66096d2d497478dee649434544ca2882948b544c58bb5e7c` |
| `qualified-1/qualification.json` | `b356d60e5e119ba17b6a8447c83d48fccb63a5d5175b613ab8f5c69b49b52602` |
| `source-closure-1.json` | `6b72d7a6fd50bfcee98c4cd9ed96d7f263f7308f1ef24076222ecda52409d565` |
| `vm-qualification-1.json` | `63725124486e029858cf41cf04f3d8fcb2bfc5b1e26155082a12926f80f0b47d` |
| Independent `PASS_GO` | `a627fce2a70aa663d5a22ea1ae2ca827518dc5cca159cc89c055871637535ece` |

The [independent review](../../workspace/public/src/device-action/bindings/s22plus_native_staged_preflight_v1_review.json)
is `PASS_GO`, with no remaining blockers. It rederived actual AP
A/B qualification and strict image admission, checked every saved source,
recompiled the physical/virtual helper and all nine fault binaries to retained
bytes, and independently verified final VM raw results and writable disk
digests. The missing-health-prefix finding is closed by the bounded rejection
and real RX-cut tests. Selected Python compilation, links, whitespace and
repository privacy checks pass.

The source-bound capability review binds exact saved working-tree bytes;
unrelated pre-existing edits remain outside this selected commit. Qualification
is complete for H0. No connected preparation, fresh health claim, task grant,
experimental transfer or device preparation result is implied.
