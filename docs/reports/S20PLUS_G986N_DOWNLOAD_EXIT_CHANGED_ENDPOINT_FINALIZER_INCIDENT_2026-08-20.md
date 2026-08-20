# S20+ Download-exit changed-endpoint finalizer incident

Date: 2026-08-20

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **CLOSED - EXACT ANDROID HEALTHY TERMINAL, GUARD RELEASED, NO REPLAY**

## Incident

After an attended empty-baseline arm and exact endpoint confirmation, the
active payload-free Download return helper sent exactly one fixed
`odin4 --reboot -d <USBFS>` command. The durable result recorded return code
zero, empty stderr, one consumed effect, `post_state=changed`, and
`RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_UNKNOWN`. Candidate/AP/partition
arguments were absent. The operator then directly observed normal Android.

The original read-only `--finalize` accepted only a predecessor result with
`post_state=absent` and `...NORMAL_HEALTH`. It rejected this truthful changed
endpoint result before calling Android health. The shared action guard remains
held. Odin replay is forbidden and was not attempted.

## Narrow remediation

Frozen review candidate:

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_g986n_download_exit_d1.py` | 34,025 | `72411a9e7983849dca0cbb3775f4f070c9642b9c8efb929fd519826e954b336a` |
| `tests/test_s20plus_g986n_download_exit_d1.py` | 20,631 | `f9c54830c4c08eccf81cbde8b802ba5b1ee7d99db3461ba49473a7a72e7a2bb7` |

The rotated finalizer accepts one additional predecessor shape only:

- exact original no-payload intent and endpoint receipt;
- exact raw stdout/stderr size-independent SHA-256 readback;
- literal integer return code zero and effect count one;
- `post_state=changed` paired only with the exact UNKNOWN source verdict;
- `no_replay=true` and `replay_permitted=false`; and
- no extra journal node.

It sends no Odin command. It performs only the existing bounded exact-target
Android inventory/devpath/health reads. On success, a new no-clobber
`final-result.json` preserves `source_verdict`, records
`exit_dispatch_proven=false`, reports exact healthy normal Android, and then
releases the matching guard. It does not claim the Download endpoint transition
or dispatch attribution was proved. Any nonzero or bool-substituted count,
other endpoint state, raw mismatch, extra node, foreign target, or health
failure retains the guard.

The first independent review returned `NO_GO` because the candidate used
ordinary JSON parsing and did not revalidate the complete arm/baseline/binding,
intent, and result schemas. A hostile forged binding, wrong intent
version/action, and extra result field could reach health and release the
guard. The rotated candidate uses duplicate-safe canonical JSON reads, exact
key sets and typed integers, and full canonical arm/baseline/binding
revalidation before health. The focused suite passes **14/14**, including the
reviewer's forged-source case, duplicate/noncanonical JSON, nonzero result,
health failure, extra node, and no-Odin changed-endpoint closure.

The second independent review returned `NO_GO` because the shared guard still
used ordinary last-key-wins JSON parsing. A duplicate guard containing a
foreign and then current `run_dir` could be accepted and deleted. The current
candidate reads and re-reads the exact guard through the same bounded canonical
duplicate-safe reader, compares its complete schema/value and stable inode
identity before unlink, and retains malformed or foreign guards. The focused
suite now passes **15/15**, including the duplicate-foreign-guard fixture.

The third independent review returned `NO_GO` because an intermediate symlink
could redirect the otherwise exact guard path between the retained routine
namespace and a moved directory. The current candidate opens the exact direct
guard parent with `O_DIRECTORY|O_NOFOLLOW`, compares the opened directory
identity with the direct path, and performs both canonical guard reads, final
metadata comparison, unlink, and directory fsync relative to that same file
descriptor. An indirect ancestor is rejected before Android health and the
guard is retained. The focused suite now passes **16/16**, including the
intermediate-parent-symlink fixture.

Fresh independent review of the exact frozen source and test hashes above
returned `PASS_GO`. It confirmed that the retained changed/UNKNOWN predecessor
is the only new accepted state, guard access and release remain bound to the
same direct parent directory descriptor, and no Odin path is reachable from
the finalizer.

The first retained-run finalizer invocation after that review failed closed:
no terminal was published and the guard remained. Read-only diagnosis showed
that exact S20+ Android was healthy but its ADB devpath hash was the other
already allowlisted paired-controller topology recorded by the durable
Download endpoint, rather than the older Android-only topology constant. The
next narrow candidate therefore passes that already validated durable endpoint
topology into the health reader and requires exact equality. It does not add a
new topology, accept an unbound endpoint, or add any device effect. This
topology-binding rotation requires fresh independent review before another
retained-run finalizer invocation.

Fresh independent review of the exact rotated hashes above returned
`PASS_GO`. It confirmed that the expected topology is accepted only from the
pre-existing two-member allowlist and is supplied to finalization only from the
strictly validated durable Download endpoint; all exact target/build/health
checks remain mandatory and no Odin path was added.

## Authority boundary

This incident finalizer changes no payload, candidate, partition, root,
reboot, Download-entry, or N3-U0 authority. It is a recovery-only read path for
one already consumed exit action. The exact source/tests/contract rotation has
received independent `PASS_GO` for the guard/schema closure. The subsequent
endpoint-topology health rotation also received independent `PASS_GO`; it may
grant only one health-only continuation of the already consumed retained run
and never grants dispatch replay.

The first live finalizer attempt sent only bounded ADB health reads, failed
closed, and retained the guard. No Odin, reboot, transfer, or payload command
was sent while designing or diagnosing this remediation.

## Live closure

After the topology rotation received independent `PASS_GO`, the retained
finalizer was invoked once more. It returned
`PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY_AFTER_UNCERTAIN_DISPATCH`,
preserved the source UNKNOWN verdict, recorded
`exit_dispatch_proven=false`, `effect_command_count=1`, `no_replay=true`, and
`replay_permitted=false`, and proved exact healthy
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2` Android on the durable endpoint topology.
The terminal is a direct mode-0400, link-count-one file. The matching shared
guard is absent. This closure sent no Odin, reboot, transfer, or payload
command.
