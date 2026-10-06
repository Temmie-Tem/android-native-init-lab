# P415 first run: protected evidence capture and healthy Android return

Date: 2026-10-07 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P415 `v0.4.0-rc.15`, the separately reviewed
[mountless evidence reader](../operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md).

## Result

P415 completed its one fixed read-only capture and normal original-A return.
Scientific result: **PASS_ROOT_EVIDENCE_OBSERVED**. Final terminal:
**ANDROID_CLOSED_HEALTHY**, `recovered=false`. Exactly one reader N and one
original A were transferred. There was no execution, transport or health stop,
no repeated effect and no additional recovery transfer.

The capture observed `state=1 recover=1 orphan=0`: native_data requires journal
recovery before clean-root admission. P415 mounted no filesystem, replayed no
journal and wrote no native_data content. Its acquisition result does not
claim an installed-root comparison, Debian boot or service progression.

The returned view was the checkpointed home blocks. Eleven of the twelve
sealed paths were absent there; the one present file, `var/log/wtmp`, was empty.
No captured raw file contents establish additional P413 execution progress.
Missing or older home-block records cannot prove non-execution, since newer
inode, directory or data changes may remain only in the unreplayed journal.
P413's independently authenticated installed-PID1/rcS-entry proof is unchanged.

## Protected observation

Exact endpoint/UFS/GPT/entry-41/UUID/features and partition-only kernel RO
passed before the unprivileged static reader. The single pre-EXEC control
intent joined its authenticated native boot, command, nonce and sequence.
The child settled successfully with exit status zero and complete framing.
The reader used **275,456 bytes in 45 read calls**, within its 64 MiB/16,384-call
limits. Final superblock and GPT readback were unchanged; partition RO remained
set through observation. No mount, unmount, RO clear, journal replay, installed
code execution or filesystem-data write was selected.

| Fixed path group | Checkpointed home-block result |
| --- | --- |
| `var/lib/lab/boot-count` | Absent |
| `var/log/wtmp` | Regular file, zero bytes, complete empty-file digest |
| Current `var/log/dmesg` and `var/log/messages` | Absent |
| `var/log/messages.0` through `.2` | Absent |
| `var/log/dmesg.0` and `.1.gz` through `.4.gz` | Absent |

These are file observations, not a claim that the directory state is the latest
committed state. The optional future per-run receipt path was not selected.
No arbitrary path, additional capture or repeat command was used.

The native session proved health, fixed acquisition, DETACH and actual close.
A fresh authenticated same-boot session then completed the fixed CONTROL and
measured Download departure. Original A was transferred once through its bound
boot-only package and verified endpoint. Final rooted Android health proved
the exact original boot/supporting partition digests and a new Android boot,
with matching full Android32 GPT, native_data presence and
**34,357,624,832-byte** reported userdata capacity.

## Canonical timeline

Elapsed seconds are from the original 1800-second grant. The canonical
`rollback_*` labels denote this operation's planned original-A return;
there was no emergency recovery or renewed deadline.

| Seconds | Canonical event / evidence |
| ---: | --- |
| 0.000 | `live_session_start`: exact returned attended grant opened |
| 3.131 | Fresh exact original-A preflight completed |
| 3.350 / 5.182 | Android Download intent / completion |
| 17.028 | `candidate_flash_start`: sole N transfer intent |
| 18.651 | `candidate_flash_done` |
| 31.398 | Sole partition-RO/reader EXEC intent |
| 32.415 | `candidate_boot_ready`: native health, capture and DETACH complete |
| 34.040 / 34.771 | Same-boot CONTROL intent / measured Download completion |
| 40.885 | `rollback_flash_start`: sole planned A transfer intent |
| 42.435 | `rollback_flash_done` |
| 78.987 | `rollback_boot_ready`: exact rooted Android32/GPT health complete |
| 202.152 | `live_session_end`: H0 evidence audit and finite-grant closure |

## Retained evidence and closure

Execution source commit: `b8741e0c2a9dc324a7c8fa81270b9ffcee38bf1e`.
The [H0 qualification report](S22PLUS_NATIVE_ROOT_EVIDENCE_P415_H0_2026-10-07.md)
retains the separate prelive review and artifact provenance.

Private orchestration root:
`workspace/private/outputs/s22plus-native-root-evidence-p415-live-20261007-1/`.
The approved immutable task and operation remain at their original bound path:
`workspace/private/outputs/s22plus-debian-durable-evidence-p415-h0-20261007-1/prepared-1/task/`.
No preparation, approval or consumed record was moved or repurposed.

H0 closure revalidated both streams of all **588 operation captures**, all
**251 frozen source paths**, initial/final Android proofs, exact N/A transfers,
reader and same-boot return observations, and the permanent consumed claim.
No raw producer fault was present. With command acquisition blocked,
`Session.repair_close` reproduced the terminal while all **18 journal rows**
and terminal bytes remained unchanged.

| Record | SHA-256 |
| --- | --- |
| Terminal | `1fd453ffee3b538ae4197fd2a7ed4c7557102d3227b9818c4f005fb41ec5d63f` |
| Closure audit | `f648f607c10fa34df7aff36843eb2a44844f126233f230be5cdd7ff1d1d2329c` |
| Closed finite task | `5bc53ffd5af7ef9f2cbf69a80f336f5cc5e68e96aadde132e2106d140ac37b5e` |

The candidate and one-operation grant are consumed and closed; the F1 owner is
absent. Raw evidence stays private. A90 and S20+ received no commands or
transfers, and unrelated working-tree changes were preserved.

Future writable Debian work needs a separate current scope for the observed
dirty native_data and fresh clean-root admission. This run grants no journal
replay, new boot, persistent receipt writer or startup continuation after USB
loss. It establishes a working protected retrieval path and the current limit
of the available historical evidence; the planned durable per-run records
remain the next functional improvement.
