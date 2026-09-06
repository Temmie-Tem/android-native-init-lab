# P347: output/timing qualification PASS and healthy rollback

Target: `SM-S906N/g0q/S906NKSS7FYG8` only. The operator authorized the
identified repairs, D0/D1 preparation and issuance of a fresh F1 approval code.
The operator subsequently returned the exact code. P347 is now CLOSED with
`PASS_F1_V2_P347_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`: all five qualification
sessions passed, candidate and exact rollback each transferred once, and final
rooted FYG8 health passed. P345/P346 retain their original consumed outcomes.

## Implemented capability

The [P346 audit](S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md)
reproduced two important false-success mechanisms: a nonblocking child output
pipe silently losing BusyBox awk output, and denied clock_nanosleep returning
zero from sleep/usleep. Unsupported query applets and shell status masking
were separately identified.

P347 keeps the existing five same-descriptor sessions and fixed parent/nonce
witnesses. It changes the child output pipe's write end to blocking before
exec; parent reads remain nonblocking. The existing 15-second deadline,
128-KiB output cap, authenticated cancellation and bounded descendant cleanup
remain in force. Output setup failure exits 126.

A versioned child fragment reuses the fixed view, limits and privilege drops
and adds only clock_nanosleep with CLOCK_REALTIME and flags 0. Other clocks,
flags and denied calls remain denied. P345's child and loader remain unchanged;
the new reusable source is `s22plus_fyg8_readonly_child_v2.inc.c` and its loader.

Sequence-4 ash uses pipefail. Canary ID/uptime reads and the final version
snapshot substitution explicitly check exit status; no global set-e is added.
The last qualification session now requires exactly 120,000 bytes of awk
output plus the existing pipeline marker, 120,017 bytes total. Both the live
semantic checker and retained receipt checker require the timeout's duration
to reach 15,000 ms. Final output loss and a forged short-timeout receipt reject.

This does not qualify arbitrary BusyBox applets. In particular, ulimit,
uptime and free remain unsupported under their denied query syscalls; the
capability uses checked finite snapshot reads. No blanket sysinfo/prlimit64
allowance, wider filesystem view, network/control authority, later lease,
reconnect, retry, persistent installation or recovery exception was added.

## H0 validation and independent review

- Runtime 3/3: actual host-mapped filter and real C supervisor, AArch64 compile/
  syscall-number checks, exact 120,000-byte output, output-cap truncation,
  200-ms sleep, pipeline/substitution failures, exit 7, active cancel, the
  unchanged 15-second timeout and a successful next command.
- Full five-session qualification ran with an isolated host user mapping to
  UID/GID 65534 so its canary command remained unchanged. Its real filter,
  supervisor and Python qualifier passed, followed by complete raw-frame
  reopening and semantic validation. This fixture does not claim target mount
  setup, target privilege-drop execution or USB behavior.
- Successor 2/2: actual common receipt reopening/projection, source drift and
  consumed-input rejection, missing-output and short-timeout rejection.
- Common and predecessor regression: 138/138.
- Raw-first boundary regression: 35/35. Actual audit and new-wrapper source
  drift rejection also passed.
- Touched Python compilation, source/artifact checks, documentation links,
  whitespace and repository identifier-boundary validation passed.

The independent reviewer repeated runtime 3/3, successor 2/2 and the raw-first
audit and returned `PASS_GO` for the H0 changed capability. The review binds
27 static source receipts, the target contract, evidence registry and raw-first
auditor. Private receipt: `workspace/private/outputs/s22plus_fyg8_p347/independent-review.json`.

The raw-first additions bind P347's exact wrappers to the existing raw writer
and parser ordering. The changed inventory digests were checked against HEAD:
the only legacy/closed population deltas are the new H0 child loader and
changed evidence-registry bytes; the device-source inventory delta is only the
evidence registry. No unrelated target's source was repinned.

Before derivation, `h0-source-freeze.json` recorded all 27 source keys and
confirmed every one of the nine changed candidate inputs was included. Other
changes were classified separately. After A/B creation and reopening, the
P344/P345/P346 build result bytes, modes, inode, mtime and ctime were unchanged.

## Qualified artifacts

P344 remains the pinned packaging construction base. No Full-LTO kernel build
was required: the existing reviewed same-length Image identity transform and
A/B userspace/boot/AP construction were used. Both init outputs are static
AArch64 ELF; A/B userspace and AP bytes match. The AP contains exactly one
regular `boot.img.lz4` member. P345 and P346 AP/run identities are rejected.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| P347 candidate AP | 28631081 | 02c5d905c823f03f560f30c2cc5a734c5c113930b6f9ad15f09c2130245803b0 |
| Image | 41490944 | 0678765bee776bcfff550e8f02985e32b8a8ee1dbcafff962b42bba33f016c19 |
| init | 149432 | 3d9d3bfc5edd0dbc26e3ec4294751f86056c1c9478fa7720bfd6fc65280ed171 |
| Build result | 66561 | 88c378e7feed0ee4a0d39049b3eef95505befb0f7f961a52bb934b393dc3c071 |
| Candidate static | 30203 | 96579152ec8a1b852bd8a3b6d060f50ce8744d1d96d79c27dc574f3ca2dcc2f4 |
| Ready1 manifest | 7839 | 61fad98d373529d613d8d84b428fec121350ddf54335c636b1125f3d095bbb33 |
| Exact Magisk rollback | 23367721 | d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56 |

The final ordinary bundle verifier passed with bundle SHA-256
`c4a3b5e288a38f80fd572ef108c170d9b45b211e2bdf5b03c83ae18fc9ca74eb`.
The manifest is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p347_process_v2_ready_1.json`.
Builds and logs are under `workspace/private/outputs/s22plus_fyg8_p347/`.

An H0 sizing fixture exercised the actual prepared writer/read path at 31,208
bytes, below the unchanged 32,768-byte limit. Its historical D0 inputs conferred
no new authority and the temporary serialized record was removed.

## Connected preparation

First preparation, `p347-ready1-prepared-20260906-1`, stopped before target
selection because adb devices emitted stderr. The retained capture proves
return code 0, no timeout/overflow and exactly the two successful host ADB
server startup notices. The 77-byte stderr SHA-256 is
`d84aaa3222b49c6dfc6c07666347890c6ad2ff255b911fa83525c5814e54963c`.
No target-specific command or health proof occurred in that invocation. The
original raw receipts were preserved; strict stderr validation was not changed.

Fresh ordinary preparation `p347-ready1-prepared-20260906-2` established exact
rooted FYG8 Android health, original boot/supporting hashes and absent Download,
then stopped with the expected baseline-decoder rejection. Typed stop result:
3,251 bytes, SHA-256
`5e5515dea5e96a9ef163b813bd8a81ddbaba008244779bc14e61904e98d5538d`.
It remains non-reusable and makes no final-health claim.

Under the operator's D1 preauthorization, the existing reviewed P296/P320
primitive was invoked once with fresh P347 metadata, the exact closed P346
parent and that preserved D0 stop. Its self-test passed. The durable start
preceded the single normal reboot. Changed boot ID, exact root/Android health,
original boot/supporting hashes and absent Download passed on return.
The primitive result is 2,121 bytes, SHA-256
`62ce227baaa3ffeedb68ce1bec13268b029dd2dffec5402b6a74670c4c61efcc`,
verdict `PASS_P347_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`. There was no second
reboot, Download control, Odin invocation or partition transfer. The fixed
invocation is `workspace/private/outputs/s22plus_fyg8_p347/baseline_invocation.py`;
raw evidence and its consumed ordinal are under
`workspace/private/runs/device-action-d1-p347-baseline/`.

Fresh preparation `p347-ready1-prepared-20260906-3` then returned
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Its D0 result is 3,261 bytes,
SHA-256 `105452f57d1542b219f6333b0b5c37586821940811a53e101f1d9f4feb1bc4cb`.
The prepared record is 31,208 bytes, SHA-256
`4cf13344cb6a0b4895d1d8a4e5f2f3fe05aa22519b13bc63a9225016b6a317e7`.
The actual `load_prepared` consumer reopened its complete 57-source closure,
artifact/target/D0 binding and approval code successfully. Its six effect and
authority flags remain false. No F1 journal or live state was created.

At preparation, the code was supplied directly to the operator and kept in the
private prepared record. It was subsequently returned for the single execution
below and is now consumed; it grants no replay or later command authority. Healthy ordinary reboot return is not a claim of
automatic recovery from a failed experimental listener. A90 and S20+ received
no command. The P346 inventory incident and original NO_PROOF are unchanged.


## Approved F1 execution and final closure

The first ordinary execute invocation stopped during host adb inventory with
the same exact successful server-start stderr notices described above. Its
raw receipt proves return code 0 with no timeout/overflow; only version and
inventory calls occurred, with no target-specific command or F1 transaction.
The original log and capture were preserved. After that positively identified
host initialization, the unchanged approved runner allocated its next ordinary
execute-preflight directory. No source, prepared binding or approval changed;
this was not a candidate retry.

Fresh exact preflight passed, the transaction durably recorded approval, and
candidate `28631081B/02c5d905` transferred once. The actual device qualification
completed all five sessions on the same descriptor:

| Session | Outcome | Duration | Output |
| --- | --- | ---: | ---: |
| Read-only canary | PASS, numeric child UID/GID and denied probe | 100 ms | 139 bytes |
| Expected nonzero exit | exit 7, expected outcome | 101 ms | 0 bytes |
| sleep 30 timeout | timeout flag, signal 9 | 15156 ms | 0 bytes |
| Authenticated cancel | cancelled flag, active ACK, signal 9 | 202 ms | 19 bytes |
| Post-cancel output/pipeline | exact complete output, exit 0 | 1012 ms | 120017 bytes |

The observer is accepted with `qualification_complete=true`, five sessions and
fifteen commands. This supplies device evidence for the repaired bounded
runtime, not an unrestricted shell, later lease, persistent residency or
automatic recovery. It does not claim a 30-second sleep completed: the fixed
15-second supervisor deadline terminated it as intended.

After observation, the operator entered physical Download on the existing
connection. The original runner detected the exact rollback endpoint and
transferred Magisk `23367721B/d2373bf8` once. Final Android/root health,
original boot/supporting partition hashes and absent Download passed. No
separate recover invocation, replay or extra candidate command was needed.

Terminal verdict: `PASS_F1_V2_P347_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`.
The journal is CLOSED with 19 records; `recovery_required=false` and
`later_action_lease_active=false`.

| Retained evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| Observer receipt | 39180 | e2a11315e55972fe97bd6595363a011bf014b03887ea0813a2a2241cae988205 |
| Raw observer RX | 124676 | 20f675487080d9828d9852cf8b554c69d0cd4ecb94b7118252b0141f6672d466 |
| Live result | 33570 | 9e2db4b72caf2476bce73be0c9f5464421655b86df4556f0f80338b43bd02e2f |
| Live state | 29774 | 5670068480a52fdaad0a42091115a0771ab9a07db0aff15c2ceb5bf951dc9e8c |

Canonical timeline (UTC):

- `live_session_start`: `2026-09-06T03:08:20.493909Z`
- `candidate_flash_start`: `2026-09-06T03:08:42.199297Z`
- `candidate_flash_done`: `2026-09-06T03:08:43.807054Z`
- `candidate_boot_ready`: `2026-09-06T03:09:28.717279Z`
- `rollback_flash_start`: `2026-09-06T03:13:12.126976Z`
- `rollback_flash_done`: `2026-09-06T03:13:13.660985Z`
- `rollback_boot_ready`: `2026-09-06T03:13:48.107199Z`
- `live_session_end`: `2026-09-06T03:13:48.125190Z`

Final H0 reopening through the actual `load_prepared` and
`validate_live_result` consumers passed against the unchanged execution closure,
retained observation, transfer receipts, final health and journal. Exactly one
P347 F1 CAMPAIGN_CLOSED row was appended to the existing ledger; the prior bytes
were preserved and the complete row parser passed. A90 and S20+ received no
command. P347 is consumed and may not be executed again.
