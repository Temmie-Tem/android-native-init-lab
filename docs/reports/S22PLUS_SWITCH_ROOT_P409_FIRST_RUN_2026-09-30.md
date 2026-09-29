# S22+ P409 readonly root-transition witness — first run, 2026-09-30

## Result

P409 `v0.4.0-rc.9` proved a readonly host-PID1 root transition on the selected
operator-owned `SM-S906N/g0q/S906NKSS7FYG8`. Scientific result:
**`PASS_SWITCH_ROOT_WITNESS / PROVED_READONLY_HOST_PID1_ROOT_TRANSITION`**.

The actual native PID1 accepted the fixed terminal request, replaced itself
with the preparation executable, settled its native workers, verified the
protected installed root, moved the declared mounts and ran the selected
BusyBox switch_root. A separately executed static RAM witness authenticated
its post-exec PID1/root/executable/mount/descriptor facts over the same ACM
connection. This supplies actual Samsung evidence beyond the earlier P408
child preparation and P409's ARM64 VM qualification.

The witness accepted its sole fixed Download request, native departure was
proved and original Android A transferred once. The first final-health boot
read failed with ADB `device not found`; the existing owner continued **health
only**. A complete fresh bracket proved rooted original Android, unchanged
partition digests, full GPT and Android32 capacity. Terminal:
**`ANDROID_CLOSED_HEALTHY`, `recovered=true`**. No second A transfer occurred.

The one-operation/1800-second grant and P409 candidate are consumed and
explicitly closed. The F1 owner is absent. A90 and S20+ were not contacted.
This run executes the static RAM witness, not installed Debian init. Debian
services, writable lifetime, NCM/SSH access and persistence remain unproved.

## Functional evidence

- Fresh exact rooted Android health preceded the only mode-entry intent.
  One new P409 N transferred, then first-boot authentication and fixed native
  health preceded the compound transition intent.
- Eight ordered transition boundaries were authenticated: actual PID1 entry,
  worker settlement, exact root admission, storage recheck, RAM witness ready,
  moved mounts/work unmount, fixed BusyBox exec and the separate post-exec
  witness. Thirty protected-preparation log records accompanied them; no stop
  record or stage errno was reported.
- The three known native workers settled. The later witness proved no other
  userspace process, and only descriptors 0–3 remained. The initial native
  process identity was replaced; an ordinary root-console EXEC child was not
  treated as host PID1.
- The partition RO flag and readonly/noload/nodev/nosuid/noexec root protection
  passed. Ext4 was clean with RECOVER clear and orphan head zero. The fixed
  readonly checker and exact installed-root comparison passed: 8,969 expected
  entries matched, with zero missing, metadata or content discrepancies.
  All 8,175 boot-input entries matched; 199,362,324 file bytes were hashed.
  The inventory contained 8,973 entries including the four declared extras.
- After worker retirement and root checks, storage protection, superblock and
  sealed GPT rechecks passed. The old `/run` and inspection work tmpfs were
  ordinarily unmounted before BusyBox executed. The witness verified seven
  surviving declared mounts against the pre-exec mount IDs and normalized
  digest, readonly ext4 root, partition RO, and its distinct RAM executable
  inode and SHA-256. The same boot and transport remained bound throughout.
- The witness's only return request was durably joined to the original
  transition intent before transmission. Its ACK, measured USB departure,
  exact Download arrival and original-A transfer are separate retained proofs.
- Final Android health proved a boot distinct from initial Android, original
  boot/supporting partition hashes, full GPT and filesystem capacity of
  34,357,624,832 bytes. It does not retrospectively measure native filesystem
  cleanup or qualify automatic recovery from a future stalled handoff.

This proves the shared native retirement, protected root transition and
post-exec observation mechanism on Samsung. The next functional unit is actual
installed Debian init with one service/device owner and authenticated basic
access. Its changed root mode, userspace and USB ownership still require their
own prospective scope; the consumed P409 grant supplies no next effect.

## Canonical timeline

Seconds are measured from the original grant opening; no deadline was renewed.

| Seconds | Durable event |
| ---: | --- |
| 8.065 | Fresh exact rooted Android preflight complete |
| 8.232 | One Android-to-Download intent |
| 11.837 | Request and measured Android departure complete |
| 23.689 | One fresh P409 N transfer intent |
| 25.476 | P409 transfer complete |
| 39.920 | Authenticated fixed actual-PID1 transition intent |
| 42.904 | Sole witness-return continuation intent, after post-exec proof |
| 43.500 | Witness, fixed return exchange and native departure recorded |
| 51.007 | One original-A transfer intent |
| 52.801 | Original-A transfer complete |
| 87.697 | Initial final-health ADB boot read failed; research stopped |
| 87.775 | Health-only recovery continuation began |
| 95.495 | Fresh rooted Android/GPT/Android32 final health complete |
| 227.705 | H0 raw rederivation and explicit grant closure complete |

The failed capture is the first final-health attempt's `wait-061-boot` read:
exit 1, empty stdout and the exact target-not-found stderr, without timeout,
overflow or producer exception. Its raw evidence is preserved. The terminal's
`recovered=true` and feature `normal_return=false` reflect the final-health
recovery branch. They do not describe another transfer or a failed native
witness return, whose authenticated ACK and timely departure are proved.

## Retained evidence and checks

Private evidence base:
`workspace/private/outputs/s22plus-switch-root-h0-20260930-1/`.
Operation: `prepared-2/task/operation-0001/`. Execution source commit:
`2fdc74cb1b15c2edd4dcd1b5303fb7775a235a08`.

| Record | SHA-256 |
| --- | --- |
| Approved task | `ad08d06a0f49aad51a8cc027e0b3c7d5950c7e9a3f09c6fd4dec289734fa96df` |
| Grant | `cfbbd4bf4d8691b9273edcbdcc23abdf0fadc794c9eea7ed69de9899c1176cbf` |
| Actual P409 AP | `cd61bc7ebdd9406ac6b2b7e213ec2001f3c317ba98358d6a5237c1822d499320` |
| Terminal | `d226f6f2aff584ac01c0d303c0ad500f3fb762737f033f4fbe8ca641e679346b` |
| Closure audit | `1b2cbe7d07f0038d0a66f5bb521f01cd35e673474de8d7c45ff7ea61a4a5b403` |
| Closed grant | `50c44354e4f1d21c88ab4ccd1b2399dce32e4996f4f3e1c3b44de8e027780194` |

H0 reconstruction verified all 553 raw capture receipts and both streams,
247 saved pre-effect files, the separate 83-file host/review snapshot, both
actual transfers, initial/final Android health and the full authenticated
transition/return transcript. Its 2,254-byte preparation log was extracted only
after re-authentication. Terminal and all 17 journal records remained unchanged.
The global P409 consumption claim was verified; no new device command was used
for closure. Raw identifiers, generated bindings and logs remain private.

See the [H0 preparation](S22PLUS_SWITCH_ROOT_P409_H0_2026-09-30.md) and
[binding readonly witness scope](../operations/S22PLUS_SWITCH_ROOT_WITNESS_V1.md).
Execution-critical source and capability review were unchanged during the run.
