# S22+ P408 streamed preparation — first run, 2026-09-27

## Result

P408 `v0.4.0-rc.8` completed all **17 protected preparation stages** on the
selected operator-owned `SM-S906N/g0q/S906NKSS7FYG8`. Scientific result:
`PASS_STAGED_PREFLIGHT_OBSERVED / PROVED_PROTECTED_PREPARATION`.

The existing native UFS/ACM startup became accessible before the diagnostic.
Authenticated fixed health preceded its unique command intent. The pinned
read-only checker, exact installed-root comparison, two loader checks and
ordinary cleanup passed. This is actual Samsung execution evidence for that
fixed preparation workload. It is not switch_root, Debian host PID 1 or SSH
proof, and does not establish the cause of P407's earlier silent bootstrap.

Native CONTROL and the original-A transfer completed normally. The first
final-health bracket then failed with ADB `device not found`. The existing
owner continued **health only**, using the already completed A transfer.
A fresh complete bracket proved a distinct rooted Android boot, original
partition digests, full GPT and Android32 capacity. Terminal:
`ANDROID_CLOSED_HEALTHY`, `recovered=true`. No second A transfer occurred.

The one-operation/1800-second grant and P408 image are consumed and explicitly
closed. There is no remaining F1 owner or permission to repeat the candidate.
A90 and S20+ were not contacted by this run.

## Functional evidence

- All 17 stage begin/end pairs were received and validated, in order, through
  the authenticated root console. Every stage ended `pass`; EXIT, DETACH and
  actual descriptor closure were complete.
- Only native_data's partition RAM RO flag was set, with readback. Its ext4
  superblock was clean, RECOVER clear and orphan head zero. The pinned
  `e2fsck -fn` child exited zero with the required five pass-stage outputs.
- The protected mount, both installation records and original witness passed.
  All 8,969 archive entries and 8,175 boot-input entries matched, with zero
  missing, metadata or content discrepancies. Comparison hashed 199,362,324
  file bytes. Inventory contained 8,973 entries: the archive plus two markers,
  the witness and the validated empty `lost+found`.
- Fixed `ld-linux-aarch64.so.1 --verify /sbin/init` and `--list /sbin/init`
  children each exited zero with the expected complete output. Actual child
  wait, setup/exec framing, pipe completion and settlement were validated;
  exit status alone did not establish semantic success.
- Parent mount protection, ordinary unmount, final partition RO, unchanged
  superblock/GPT readback and owned cleanup all passed. No installed init,
  writable filesystem mount, module reload, mdev scan or service was invoked
  by the diagnostic command.
- Final original-A health included exact boot/supporting partition hashes,
  full GPT and reported Android filesystem capacity of 34,357,624,832 bytes.
  Android recovery health is separate from the preparation result and is not
  an additional native_data content observation.

The helper's code and declared protected-child environment differ from the
consumed cold-bootstrap path. This result establishes a working preparation
capability after native startup; it does not retrospectively prove which
instruction P404/P405/P407 reached or rule out their earlier lifecycle faults.
The next bounded functional milestone is direct root/PID-1 handoff observation,
including mount/device ownership and the post-handoff return path.

## Canonical timeline

Times are seconds from the original grant opening; no deadline was renewed.

| Seconds | Durable event |
| ---: | --- |
| 15.103 | Fresh exact rooted Android preflight complete |
| 15.249 | One Android-to-Download intent |
| 18.884 | Download request and measured departure complete |
| 28.143 | One fresh P408 N transfer intent |
| 29.646 | P408 transfer complete |
| 54.650 | Authenticated fixed preparation EXEC intent |
| 57.769 | All stages, complete observation and DETACH recorded |
| 59.189 | Same-boot native CONTROL intent |
| 59.796 | CONTROL and measured native departure complete |
| 65.704 | One original-A transfer intent |
| 67.227 | Original-A transfer complete |
| 108.798 | Initial final-health ADB read failed; research stopped |
| 108.859 | Health-only recovery continuation began |
| 115.902 | Fresh rooted Android/GPT/Android32 final health complete |
| 322.189 | H0 raw rederivation and explicit grant closure complete |

The normal native-return and A-transfer proofs remain intact. The terminal's
`recovered=true` and diagnostic `normal_return=false` reflect the final-health
recovery branch; they are not claims of another transfer or a stalled native
runtime. The initial failed raw capture is retained without relabelling.

## Retained evidence and checks

Private evidence base:
`workspace/private/outputs/s22plus-staged-preflight-p408-h0-20260926-1/`.
The live operation is `prepared-1/task/operation-0001/`. Source commit:
`28811fb6f74347963a5a67b07a69ac74998d59a9`.

| Record | SHA-256 |
| --- | --- |
| Approved task | `f5e0ff27a99665241e129d4b6e6fe940ad998a827d5bf9a560f409582f6f6369` |
| Grant | `0073de77607ed1048f96beec52af36aa151b5a108761cb72b56646002d79cee7` |
| Actual P408 AP | `ce8c22fe2482ae6fe8b6823fd7b7c4c44f2163fa2390611121614e5475c9ec4c` |
| Terminal | `a7442e50a3674df086feb47821291c0ad786c71493c9ae24b9d6039a4b7bba79` |
| Closure audit | `9c70ef50495b11c7f7eb815d49c7e012fb4ff9bc322c074d771c3a86a0636732` |
| Closed grant | `5b213f6804d8f97fd12e0b11787fffac6b4d31b250e25a3997169245c1754884` |

H0 rederivation verified all 617 raw capture receipts and streams, the 232
saved pre-effect source files, both actual transfer results, native sessions,
the diagnostic command and final Android32 health. The terminal and 20-row
journal remained unchanged during reconstruction. A standard saved host-source
manifest was also published from the unchanged reviewed bytes for later
historical consumers; the earlier source snapshot retains runtime provenance.
Raw logs, identifiers and loader addresses remain private.

See the [H0 qualification](S22PLUS_NATIVE_STAGED_PREFLIGHT_P408_H0_2026-09-26.md)
and [binding capability](../operations/S22PLUS_NATIVE_STAGED_PREFLIGHT_V1.md).
Documentation links, whitespace and repository privacy checks pass. No source
or execution machinery was changed to obtain this result.
